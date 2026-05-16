"""
Ensemble demand forecaster.

Combines XGBoost (60%) and LSTM (40%) predictions to generate
3-day demand forecasts with confidence intervals, revenue projections,
profit estimates, and inventory requirements.

Academic Reference:
    - Ensemble methods for improved forecast accuracy (Timmermann, 2006)
    - Prediction intervals for demand forecasting (Chatfield, 2000)
"""

import logging
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.features import FEATURE_COLUMNS, TARGET_COLUMN, build_features
from app.ml.preprocessing import preprocess_pipeline, load_scaler
from app.ml.xgboost_model import predict_xgboost, train_xgboost
from app.ml.lstm_model import predict_lstm, create_sequences, train_lstm, LSTM_PARAMS
from app.ml.clustering import train_clusters
from app.models.forecast import Forecast
from app.models.menu_item import MenuItem

logger = logging.getLogger(__name__)

# ── Ensemble Configuration ───────────────────────────────────────────────────

XGBOOST_WEIGHT = 0.60  # 60% weight for XGBoost
LSTM_WEIGHT = 0.40     # 40% weight for LSTM
SAFETY_STOCK_MULTIPLIER = 1.15  # 15% safety stock buffer
CONFIDENCE_Z_SCORE = 1.96  # 95% confidence interval
FORECAST_DAYS = 3
MODEL_VERSION = "v1.0.0-ensemble"


async def run_full_pipeline(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
    forecast_days: int = FORECAST_DAYS,
) -> dict:
    """
    Execute the complete ML pipeline: preprocess → features → train → forecast.

    Steps:
        1. Preprocess raw order data
        2. Engineer features (temporal, lag, rolling, weather, events)
        3. Cluster menu items by demand pattern
        4. Train XGBoost model with TimeSeriesSplit CV
        5. Train LSTM model with EarlyStopping
        6. Generate ensemble forecasts for next N days
        7. Save forecasts to database

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        days_back: Historical days to process.
        forecast_days: Number of days to forecast ahead.

    Returns:
        Dictionary with training metrics and forecast results.
    """
    logger.info("=" * 60)
    logger.info("Starting full ML pipeline for vendor %s", vendor_id)
    logger.info("=" * 60)

    # Step 1: Preprocess
    df, scaler = await preprocess_pipeline(db, vendor_id, days_back)
    if df.empty:
        logger.warning("No data available for vendor %s — aborting pipeline", vendor_id)
        return {"status": "no_data", "forecasts": []}

    # Step 2: Feature engineering
    df_features = await build_features(df, include_weather=True, weather_days=days_back)

    # Step 3: Clustering
    cluster_results = train_clusters(df, vendor_id)
    logger.info("Clustering complete: %d items clustered", len(cluster_results))

    # Step 4: Train XGBoost
    xgb_results = train_xgboost(df_features, vendor_id)
    logger.info("XGBoost — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%",
                xgb_results["metrics"]["rmse"],
                xgb_results["metrics"]["mae"],
                xgb_results["metrics"]["mape"])

    # Step 5: Train LSTM
    lstm_results = train_lstm(df_features, vendor_id)
    logger.info("LSTM — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%",
                lstm_results["metrics"]["rmse"],
                lstm_results["metrics"]["mae"],
                lstm_results["metrics"]["mape"])

    # Step 6: Generate forecasts
    forecasts = await generate_forecasts(
        db=db,
        vendor_id=vendor_id,
        df_features=df_features,
        xgb_results=xgb_results,
        lstm_results=lstm_results,
        forecast_days=forecast_days,
    )

    # Step 7: Save forecasts to database
    await save_forecasts_to_db(db, vendor_id, forecasts)

    return {
        "status": "success",
        "xgboost_metrics": xgb_results["metrics"],
        "lstm_metrics": lstm_results["metrics"],
        "feature_importance": xgb_results.get("feature_importance", {}),
        "forecasts": forecasts,
        "items_forecasted": len(set(f["menu_item_id"] for f in forecasts)),
        "cluster_summary": cluster_results.to_dict("records") if not cluster_results.empty else [],
    }


async def generate_forecasts(
    db: AsyncSession,
    vendor_id: UUID,
    df_features: pd.DataFrame,
    xgb_results: dict,
    lstm_results: dict,
    forecast_days: int = FORECAST_DAYS,
) -> list[dict]:
    """
    Generate ensemble demand forecasts for the next N days.

    Combines XGBoost (60%) and LSTM (40%) predictions with:
    - Revenue forecast = predicted_quantity × menu_item.price
    - Profit estimate = revenue × (1 - cogs_percentage/100)
    - Confidence intervals = ±1.96 × prediction std
    - Inventory requirement = predicted_quantity × 1.15

    Args:
        db: Database session.
        vendor_id: Vendor UUID.
        df_features: Feature-engineered DataFrame.
        xgb_results: XGBoost training results.
        lstm_results: LSTM training results.
        forecast_days: Days ahead to forecast.

    Returns:
        List of forecast dictionaries per (item, date) combination.
    """
    # Load menu item metadata (prices, COGS)
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_active == True,  # noqa: E712
        )
    )
    menu_items = {str(mi.id): mi for mi in result.scalars().all()}

    if not menu_items:
        logger.warning("No active menu items for vendor %s", vendor_id)
        return []

    forecasts = []
    today = date.today()
    available_features = [f for f in FEATURE_COLUMNS if f in df_features.columns]

    for item_id, item_df in df_features.groupby("menu_item_id"):
        if str(item_id) not in menu_items:
            continue

        menu_item = menu_items[str(item_id)]
        item_df = item_df.sort_values("date").reset_index(drop=True)

        if len(item_df) < 2:
            continue

        # Get the last row's features as the base for future prediction
        last_features = item_df[available_features].iloc[-1:].values

        # XGBoost predictions for each forecast day
        xgb_preds = []
        for day_offset in range(1, forecast_days + 1):
            forecast_date = today + timedelta(days=day_offset)
            # Create feature row for future date
            future_features = _create_future_features(
                item_df, available_features, forecast_date, day_offset
            )
            try:
                xgb_pred = predict_xgboost(vendor_id, future_features)
                xgb_preds.append(float(xgb_pred[0]))
            except (FileNotFoundError, Exception) as e:
                logger.warning("XGBoost prediction failed: %s", e)
                xgb_preds.append(float(item_df[TARGET_COLUMN].mean()))

        # LSTM predictions
        lstm_preds = []
        sequence_length = LSTM_PARAMS["sequence_length"]

        if lstm_results.get("model") is not None and len(item_df) >= sequence_length:
            X_raw = item_df[available_features].values.astype(np.float32)
            X_raw = np.asarray(np.nan_to_num(X_raw, nan=0.0), dtype=np.float32)

            for day_offset in range(forecast_days):
                seq_start = max(0, len(X_raw) - sequence_length + day_offset)
                seq_end = seq_start + sequence_length

                if seq_end <= len(X_raw):
                    seq = X_raw[seq_start:seq_end]
                else:
                    # Pad with last available features
                    available = X_raw[seq_start:]
                    padding = np.tile(X_raw[-1:], (sequence_length - len(available), 1))
                    seq = np.vstack([available, padding])

                seq = seq.reshape(1, sequence_length, -1)
                try:
                    pred = predict_lstm(vendor_id, seq)
                    lstm_preds.append(float(pred[0]))
                except (FileNotFoundError, Exception) as e:
                    logger.warning("LSTM prediction failed: %s", e)
                    lstm_preds.append(float(item_df[TARGET_COLUMN].mean()))
        else:
            # Fallback: use historical mean
            lstm_preds = [float(item_df[TARGET_COLUMN].mean())] * forecast_days

        # Ensemble predictions and generate forecast entries
        historical_std = float(item_df[TARGET_COLUMN].std()) if len(item_df) > 1 else 1.0

        for day_idx in range(forecast_days):
            forecast_date = today + timedelta(days=day_idx + 1)

            # Weighted ensemble: 60% XGBoost + 40% LSTM
            xgb_val = xgb_preds[day_idx] if day_idx < len(xgb_preds) else xgb_preds[-1]
            lstm_val = lstm_preds[day_idx] if day_idx < len(lstm_preds) else lstm_preds[-1]

            ensemble_pred = (XGBOOST_WEIGHT * xgb_val) + (LSTM_WEIGHT * lstm_val)
            ensemble_pred = max(ensemble_pred, 0)  # Cannot be negative

            # Confidence intervals: ±1.96 × std
            prediction_std = historical_std * (1 + 0.1 * day_idx)  # Uncertainty grows with horizon
            confidence_lower = max(ensemble_pred - CONFIDENCE_Z_SCORE * prediction_std, 0)
            confidence_upper = ensemble_pred + CONFIDENCE_Z_SCORE * prediction_std

            # Revenue = predicted_quantity × price
            price = float(menu_item.price)
            predicted_revenue = ensemble_pred * price

            # Profit = revenue × (1 - cogs_percentage / 100)
            cogs_pct = float(menu_item.cogs_percentage)
            predicted_profit = predicted_revenue * (1 - cogs_pct / 100)

            # Inventory = predicted_quantity × 1.15 (safety stock)
            inventory_requirement = ensemble_pred * SAFETY_STOCK_MULTIPLIER

            forecasts.append({
                "menu_item_id": str(item_id),
                "menu_item_name": menu_item.name,
                "forecast_date": forecast_date,
                "predicted_quantity": round(ensemble_pred, 2),
                "predicted_revenue": round(predicted_revenue, 2),
                "predicted_profit": round(predicted_profit, 2),
                "confidence_lower": round(confidence_lower, 2),
                "confidence_upper": round(confidence_upper, 2),
                "inventory_requirement": round(inventory_requirement, 2),
                "xgboost_prediction": round(xgb_val, 2),
                "lstm_prediction": round(lstm_val, 2),
                "model_version": MODEL_VERSION,
            })

    logger.info(
        "Generated %d forecasts for %d items over %d days",
        len(forecasts),
        len(set(f["menu_item_id"] for f in forecasts)),
        forecast_days,
    )
    return forecasts


def _create_future_features(
    item_df: pd.DataFrame,
    feature_cols: list[str],
    forecast_date: date,
    day_offset: int,
) -> "np.ndarray[tuple[int, int], np.dtype[np.float32]]":
    """
    Create a feature vector for a future date based on historical patterns.

    Uses the last known features as a base and updates temporal features
    to match the forecast date.
    """
    base = item_df[feature_cols].iloc[-1:].copy()

    # Update temporal features for the future date
    if "day_of_week" in base.columns:
        base["day_of_week"] = forecast_date.weekday()
    if "is_weekend" in base.columns:
        base["is_weekend"] = 1 if forecast_date.weekday() >= 5 else 0
    if "day_of_month" in base.columns:
        base["day_of_month"] = forecast_date.day
    if "month" in base.columns:
        base["month"] = forecast_date.month
    if "week_of_year" in base.columns:
        base["week_of_year"] = forecast_date.isocalendar()[1]
    if "quarter" in base.columns:
        base["quarter"] = (forecast_date.month - 1) // 3 + 1

    # Update lag features with recent actuals
    if "lag_1" in base.columns and len(item_df) >= 1:
        base["lag_1"] = item_df[TARGET_COLUMN].iloc[-1]
    if "lag_7" in base.columns and len(item_df) >= 7:
        base["lag_7"] = item_df[TARGET_COLUMN].iloc[-7]
    if "lag_14" in base.columns and len(item_df) >= 14:
        base["lag_14"] = item_df[TARGET_COLUMN].iloc[-14]

    return base.values.astype(np.float32)  # type: ignore[return-value]


async def save_forecasts_to_db(
    db: AsyncSession,
    vendor_id: UUID,
    forecasts: list[dict],
) -> None:
    """
    Persist forecast results to the forecasts table in PostgreSQL.

    Upserts forecasts — deletes existing forecasts for the same
    vendor/item/date combinations before inserting new ones.
    """
    if not forecasts:
        return

    # Delete existing forecasts for the forecast dates
    forecast_dates = list(set(f["forecast_date"] for f in forecasts))
    from sqlalchemy import delete
    await db.execute(
        delete(Forecast).where(
            and_(
                Forecast.vendor_id == vendor_id,
                Forecast.forecast_date.in_(forecast_dates),
            )
        )
    )

    # Insert new forecasts
    for f in forecasts:
        forecast_row = Forecast(
            vendor_id=vendor_id,
            menu_item_id=UUID(f["menu_item_id"]),
            forecast_date=f["forecast_date"],
            predicted_quantity=Decimal(str(f["predicted_quantity"])),
            predicted_revenue=Decimal(str(f["predicted_revenue"])),
            confidence_lower=Decimal(str(f["confidence_lower"])),
            confidence_upper=Decimal(str(f["confidence_upper"])),
            model_version=f["model_version"],
        )
        db.add(forecast_row)

    await db.flush()
    logger.info(
        "Saved %d forecasts to database for vendor %s",
        len(forecasts), vendor_id,
    )
