"""
Model evaluation and performance monitoring.

Compares model predictions against actual demand, logs metrics
to the ml_run_logs table, and triggers alerts when accuracy
degrades below threshold.

Academic Reference:
    - Forecast accuracy metrics (Hyndman & Koehler, 2006)
    - Monitoring ML model drift (Dasu et al., 2006)
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import numpy as np
import pandas as pd
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.forecast import Forecast
from app.models.order import Order, OrderItem, OrderStatus
from app.models.ml_run_log import MLRunLog, MLRunStatus

logger = logging.getLogger(__name__)

# ── Alert Thresholds ─────────────────────────────────────────────────────────
MAPE_ALERT_THRESHOLD = 20.0  # Alert if MAPE exceeds 20%
RMSE_ALERT_THRESHOLD = 50.0  # Alert if RMSE exceeds 50 units


def calculate_rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def calculate_mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error."""
    return float(np.mean(np.abs(y_true - y_pred)))


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Percentage Error (excludes zero actuals)."""
    mask = y_true != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def calculate_smape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Symmetric Mean Absolute Percentage Error.
    More robust than MAPE for near-zero values.
    """
    denominator = (np.abs(y_true) + np.abs(y_pred)) / 2
    mask = denominator != 0
    if mask.sum() == 0:
        return 0.0
    return float(np.mean(np.abs(y_true[mask] - y_pred[mask]) / denominator[mask]) * 100)


def calculate_r_squared(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Coefficient of determination (R²)."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    if ss_tot == 0:
        return 0.0
    return float(1 - ss_res / ss_tot)


async def evaluate_forecasts(
    db: AsyncSession,
    vendor_id: UUID,
    evaluation_days: int = 7,
) -> dict:
    """
    Evaluate forecast accuracy by comparing predictions against actual orders.

    Steps:
        1. Load forecasts made for the evaluation period
        2. Load actual confirmed orders for the same period
        3. Align predictions and actuals by (menu_item_id, date)
        4. Compute RMSE, MAE, MAPE, SMAPE, R² metrics
        5. Log results to ml_run_logs table
        6. Trigger alert if MAPE > threshold

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        evaluation_days: Number of past days to evaluate.

    Returns:
        Dictionary with evaluation metrics and alert status.
    """
    logger.info("Evaluating forecasts for vendor %s (last %d days)", vendor_id, evaluation_days)

    today = datetime.now(timezone.utc).date()
    eval_start = today - timedelta(days=evaluation_days)

    # Load forecasts for the evaluation period
    forecast_query = (
        select(
            Forecast.menu_item_id,
            Forecast.forecast_date,
            Forecast.predicted_quantity,
            Forecast.predicted_revenue,
            Forecast.model_version,
        )
        .where(
            and_(
                Forecast.vendor_id == vendor_id,
                Forecast.forecast_date >= eval_start,
                Forecast.forecast_date <= today,
            )
        )
    )

    forecast_result = await db.execute(forecast_query)
    forecast_rows = forecast_result.all()

    if not forecast_rows:
        logger.warning("No forecasts found for vendor %s in evaluation period", vendor_id)
        return {"status": "no_forecasts", "metrics": {}}

    # Build forecast DataFrame
    forecast_df = pd.DataFrame([
        {
            "menu_item_id": str(row.menu_item_id),
            "date": row.forecast_date,
            "predicted_quantity": float(row.predicted_quantity),
            "predicted_revenue": float(row.predicted_revenue),
            "model_version": row.model_version,
        }
        for row in forecast_rows
    ])

    # Load actual orders for the evaluation period
    actual_query = (
        select(
            OrderItem.menu_item_id,
            func.date(Order.created_at).label("order_date"),
            func.sum(OrderItem.quantity).label("actual_quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("actual_revenue"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            and_(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CONFIRMED,
                func.date(Order.created_at) >= eval_start,
                func.date(Order.created_at) <= today,
            )
        )
        .group_by(OrderItem.menu_item_id, func.date(Order.created_at))
    )

    actual_result = await db.execute(actual_query)
    actual_rows = actual_result.all()

    if not actual_rows:
        logger.warning("No actual orders found for evaluation period")
        return {"status": "no_actuals", "metrics": {}}

    actual_df = pd.DataFrame([
        {
            "menu_item_id": str(row.menu_item_id),
            "date": row.order_date,
            "actual_quantity": float(row.actual_quantity),
            "actual_revenue": float(row.actual_revenue),
        }
        for row in actual_rows
    ])

    # Merge forecasts and actuals
    merged = forecast_df.merge(
        actual_df,
        on=["menu_item_id", "date"],
        how="inner",
    )

    if merged.empty:
        logger.warning("No matching forecast-actual pairs found")
        return {"status": "no_matches", "metrics": {}}

    # Calculate metrics
    y_true_qty = merged["actual_quantity"].values
    y_pred_qty = merged["predicted_quantity"].values
    y_true_rev = merged["actual_revenue"].values
    y_pred_rev = merged["predicted_revenue"].values

    metrics = {
        "quantity_rmse": calculate_rmse(y_true_qty, y_pred_qty),
        "quantity_mae": calculate_mae(y_true_qty, y_pred_qty),
        "quantity_mape": calculate_mape(y_true_qty, y_pred_qty),
        "quantity_smape": calculate_smape(y_true_qty, y_pred_qty),
        "quantity_r_squared": calculate_r_squared(y_true_qty, y_pred_qty),
        "revenue_rmse": calculate_rmse(y_true_rev, y_pred_rev),
        "revenue_mae": calculate_mae(y_true_rev, y_pred_rev),
        "revenue_mape": calculate_mape(y_true_rev, y_pred_rev),
        "n_predictions": len(merged),
        "n_items": merged["menu_item_id"].nunique(),
        "evaluation_period_days": evaluation_days,
    }

    logger.info(
        "Evaluation results — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%, R²: %.4f (%d predictions)",
        metrics["quantity_rmse"],
        metrics["quantity_mae"],
        metrics["quantity_mape"],
        metrics["quantity_r_squared"],
        metrics["n_predictions"],
    )

    # Log metrics to ml_run_logs table
    model_version = forecast_df["model_version"].iloc[0] if not forecast_df.empty else "unknown"
    await log_metrics(db, vendor_id, metrics, model_version)

    # Check alert thresholds
    alert_triggered = False
    alert_reasons = []

    if metrics["quantity_mape"] > MAPE_ALERT_THRESHOLD:
        alert_triggered = True
        alert_reasons.append(
            f"MAPE ({metrics['quantity_mape']:.2f}%) exceeds threshold ({MAPE_ALERT_THRESHOLD}%)"
        )

    if metrics["quantity_rmse"] > RMSE_ALERT_THRESHOLD:
        alert_triggered = True
        alert_reasons.append(
            f"RMSE ({metrics['quantity_rmse']:.4f}) exceeds threshold ({RMSE_ALERT_THRESHOLD})"
        )

    if alert_triggered:
        logger.warning(
            "ALERT: Model performance degraded for vendor %s — %s",
            vendor_id, "; ".join(alert_reasons),
        )

    # Per-item breakdown
    item_metrics = []
    for item_id, group in merged.groupby("menu_item_id"):
        yt = group["actual_quantity"].values
        yp = group["predicted_quantity"].values
        item_metrics.append({
            "menu_item_id": item_id,
            "rmse": calculate_rmse(yt, yp),
            "mae": calculate_mae(yt, yp),
            "mape": calculate_mape(yt, yp),
            "n_predictions": len(group),
        })

    return {
        "status": "success",
        "metrics": metrics,
        "alert_triggered": alert_triggered,
        "alert_reasons": alert_reasons,
        "per_item_metrics": item_metrics,
    }


async def log_metrics(
    db: AsyncSession,
    vendor_id: UUID,
    metrics: dict,
    model_type: str = "ensemble",
) -> None:
    """
    Log evaluation metrics to the ml_run_logs table.

    Args:
        db: Async database session.
        vendor_id: Vendor UUID.
        metrics: Metrics dictionary with rmse, mae, mape keys.
        model_type: Model identifier (e.g., 'xgboost', 'lstm', 'ensemble').
    """
    ml_log = MLRunLog(
        vendor_id=vendor_id,
        model_type=model_type,
        rmse=Decimal(str(round(metrics.get("quantity_rmse", 0), 4))),
        mae=Decimal(str(round(metrics.get("quantity_mae", 0), 4))),
        mape=Decimal(str(round(metrics.get("quantity_mape", 0), 4))),
        status=MLRunStatus.COMPLETED,
    )
    db.add(ml_log)
    await db.flush()
    logger.info(
        "Logged %s metrics to ml_run_logs — RMSE: %s, MAE: %s, MAPE: %s",
        model_type, ml_log.rmse, ml_log.mae, ml_log.mape,
    )


async def get_model_performance_history(
    db: AsyncSession,
    vendor_id: UUID,
    limit: int = 20,
) -> list[dict]:
    """
    Retrieve recent model performance metrics for trend analysis.

    Args:
        db: Async database session.
        vendor_id: Vendor UUID.
        limit: Maximum number of records to return.

    Returns:
        List of metric dictionaries ordered by most recent first.
    """
    query = (
        select(MLRunLog)
        .where(
            and_(
                MLRunLog.vendor_id == vendor_id,
                MLRunLog.status == MLRunStatus.COMPLETED,
            )
        )
        .order_by(MLRunLog.trained_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    return [
        {
            "id": str(log.id),
            "model_type": log.model_type,
            "rmse": float(log.rmse) if log.rmse else None,
            "mae": float(log.mae) if log.mae else None,
            "mape": float(log.mape) if log.mape else None,
            "trained_at": log.trained_at.isoformat(),
            "status": log.status.value,
        }
        for log in logs
    ]
