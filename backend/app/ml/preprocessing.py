"""
Data preprocessing pipeline for demand forecasting.

Loads raw order data from PostgreSQL, handles missing values,
normalizes quantities, and outputs clean DataFrames ready for
feature engineering.

Academic Reference:
    - Time-series imputation via forward-fill (Moritz & Bartz-Beielstein, 2017)
    - Min-Max normalization for bounded neural network inputs (Bishop, 2006)
"""

import logging
import os
import pickle
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderStatus
from app.models.menu_item import MenuItem

logger = logging.getLogger(__name__)

# Directory for persisting scaler artifacts per vendor
SCALER_DIR = Path(__file__).parent / "artifacts" / "scalers"
SCALER_DIR.mkdir(parents=True, exist_ok=True)


def _scaler_path(vendor_id: UUID) -> Path:
    """Return the file path for a vendor's persisted MinMaxScaler."""
    return SCALER_DIR / f"scaler_{vendor_id}.pkl"


def save_scaler(vendor_id: UUID, scaler: MinMaxScaler) -> None:
    """Persist a fitted MinMaxScaler to disk for a given vendor."""
    path = _scaler_path(vendor_id)
    with open(path, "wb") as f:
        pickle.dump(scaler, f)
    logger.info("Saved scaler for vendor %s to %s", vendor_id, path)


def load_scaler(vendor_id: UUID) -> MinMaxScaler | None:
    """Load a previously fitted MinMaxScaler for a vendor. Returns None if not found."""
    path = _scaler_path(vendor_id)
    if not path.exists():
        return None
    with open(path, "rb") as f:
        scaler = pickle.load(f)
    logger.info("Loaded scaler for vendor %s from %s", vendor_id, path)
    return scaler


async def load_raw_orders(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
) -> pd.DataFrame:
    """
    Load raw order + order_item data from PostgreSQL for a given vendor.

    Joins orders → order_items to produce a denormalized DataFrame with
    one row per (date, menu_item_id) aggregation.

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        days_back: Number of historical days to load.

    Returns:
        DataFrame with columns: [date, menu_item_id, quantity, revenue]
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # Query confirmed orders with their line items
    query = (
        select(
            Order.created_at,
            OrderItem.menu_item_id,
            OrderItem.quantity,
            OrderItem.unit_price,
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .where(
            and_(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= cutoff,
            )
        )
        .order_by(Order.created_at)
    )

    result = await db.execute(query)
    rows = result.all()

    if not rows:
        logger.warning("No confirmed orders found for vendor %s in the last %d days", vendor_id, days_back)
        return pd.DataFrame(columns=["date", "menu_item_id", "quantity", "revenue"])

    # Build DataFrame from query results
    data = []
    for row in rows:
        created_at, menu_item_id, quantity, unit_price = row
        revenue = float(Decimal(str(quantity)) * Decimal(str(unit_price)))
        data.append({
            "date": created_at.date() if hasattr(created_at, "date") else created_at,
            "menu_item_id": str(menu_item_id),
            "quantity": int(quantity),
            "revenue": revenue,
        })

    df = pd.DataFrame(data)

    # Aggregate by (date, menu_item_id) — sum quantities and revenue per day
    df = (
        df.groupby(["date", "menu_item_id"], as_index=False)
        .agg({"quantity": "sum", "revenue": "sum"})
    )

    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values(["menu_item_id", "date"]).reset_index(drop=True)

    logger.info(
        "Loaded %d aggregated rows for vendor %s (%d unique items, %d days)",
        len(df), vendor_id, df["menu_item_id"].nunique(),
        (df["date"].max() - df["date"].min()).days + 1,
    )
    return df


def fill_time_gaps(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fill missing dates in the time series with forward-fill.

    For each menu_item_id, creates a continuous daily date range and
    fills any gaps using forward-fill followed by zero-fill for any
    remaining NaN values at the start of the series.

    Args:
        df: DataFrame with columns [date, menu_item_id, quantity, revenue]

    Returns:
        DataFrame with no time gaps, sorted by (menu_item_id, date).
    """
    if df.empty:
        return df

    filled_frames = []
    date_range = pd.date_range(start=df["date"].min(), end=df["date"].max(), freq="D")

    for item_id, group in df.groupby("menu_item_id"):
        group = group.set_index("date").reindex(date_range)
        group["menu_item_id"] = item_id

        # Forward-fill: propagate last known value into gaps
        group["quantity"] = group["quantity"].ffill().fillna(0).astype(int)
        group["revenue"] = group["revenue"].ffill().fillna(0.0)

        group = group.reset_index().rename(columns={"index": "date"})
        filled_frames.append(group)

    result = pd.concat(filled_frames, ignore_index=True)
    result = result.sort_values(["menu_item_id", "date"]).reset_index(drop=True)

    logger.info("Filled time gaps: %d → %d rows", len(df), len(result))
    return result


def normalize_quantity(
    df: pd.DataFrame,
    vendor_id: UUID,
    fit: bool = True,
) -> tuple[pd.DataFrame, MinMaxScaler]:
    """
    Normalize the quantity column using Min-Max scaling to [0, 1].

    Fits a new scaler or loads an existing one depending on the `fit` flag.
    The scaler is persisted per vendor so inference uses the same transformation.

    Args:
        df: DataFrame with a 'quantity' column.
        vendor_id: UUID of the vendor for scaler persistence.
        fit: If True, fit a new scaler. If False, load an existing one.

    Returns:
        Tuple of (DataFrame with 'quantity_normalized' column, fitted scaler).
    """
    if df.empty:
        scaler = MinMaxScaler()
        df["quantity_normalized"] = []
        return df, scaler

    if fit:
        scaler = MinMaxScaler(feature_range=(0, 1))
        df["quantity_normalized"] = scaler.fit_transform(df[["quantity"]])
        save_scaler(vendor_id, scaler)
    else:
        scaler = load_scaler(vendor_id)
        if scaler is None:
            logger.warning("No saved scaler found for vendor %s, fitting new one", vendor_id)
            scaler = MinMaxScaler(feature_range=(0, 1))
            df["quantity_normalized"] = scaler.fit_transform(df[["quantity"]])
            save_scaler(vendor_id, scaler)
        else:
            df["quantity_normalized"] = scaler.transform(df[["quantity"]])

    logger.info(
        "Normalized quantity: min=%.4f, max=%.4f, mean=%.4f",
        df["quantity_normalized"].min(),
        df["quantity_normalized"].max(),
        df["quantity_normalized"].mean(),
    )
    return df, scaler


async def preprocess_pipeline(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
) -> tuple[pd.DataFrame, MinMaxScaler]:
    """
    Complete preprocessing pipeline.

    Steps:
        1. Load raw orders from PostgreSQL
        2. Fill time-series gaps via forward-fill
        3. Normalize quantities with Min-Max scaling

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        days_back: Historical days to process.

    Returns:
        Tuple of (clean DataFrame, fitted MinMaxScaler).
    """
    logger.info("Starting preprocessing pipeline for vendor %s", vendor_id)

    # Step 1: Load raw data
    df = await load_raw_orders(db, vendor_id, days_back)
    if df.empty:
        logger.warning("Empty dataset for vendor %s — returning empty DataFrame", vendor_id)
        return df, MinMaxScaler()

    # Step 2: Fill time gaps
    df = fill_time_gaps(df)

    # Step 3: Normalize
    df, scaler = normalize_quantity(df, vendor_id, fit=True)

    logger.info(
        "Preprocessing complete: %d rows, %d items, date range %s to %s",
        len(df), df["menu_item_id"].nunique(),
        df["date"].min().strftime("%Y-%m-%d"),
        df["date"].max().strftime("%Y-%m-%d"),
    )
    return df, scaler
