"""
ML Pipeline Scheduler.

Uses APScheduler with AsyncIOScheduler to run the complete ML pipeline
for all active vendors on a daily schedule (2:00 AM UTC).

Features:
    - Per-vendor isolation: one vendor's failure doesn't block others
    - Consecutive failure tracking with Sentry alerting
    - Graceful shutdown on application exit
    - Manual trigger support for on-demand retraining
"""

import logging
import traceback
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import sentry_sdk
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.redis import invalidate_vendor_forecasts
from app.db.session import async_session_factory
from app.models.ml_run_log import MLRunLog, MLRunStatus
from app.models.vendor import Vendor

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Scheduler Instance ──────────────────────────────────────────────────────

scheduler = AsyncIOScheduler(
    timezone="UTC",
    job_defaults={
        "coalesce": True,           # Combine missed runs into one
        "max_instances": 1,         # Only one instance of each job at a time
        "misfire_grace_time": 3600, # 1 hour grace period for missed jobs
    },
)

# Track consecutive failures per vendor for alerting
_vendor_failure_counts: dict[str, int] = {}
CONSECUTIVE_FAILURE_ALERT_THRESHOLD = 3


# ── Vendor Pipeline Runner ──────────────────────────────────────────────────

async def retrain_single_vendor(vendor_id: UUID, vendor_name: str = "unknown") -> dict:
    """
    Run the complete ML pipeline for a single vendor.

    Steps:
        1. Preprocessing (load orders, fill gaps, normalize)
        2. Feature engineering (18 features)
        3. K-Means clustering (demand segments)
        4. XGBoost training (5-fold TimeSeriesSplit)
        5. LSTM training (14-day sequences, EarlyStopping)
        6. Evaluate model accuracy
        7. Generate 3-day ensemble forecasts
        8. Store forecasts in PostgreSQL
        9. Invalidate Redis forecast cache
        10. Log run metrics to ml_run_logs

    Args:
        vendor_id: UUID of the vendor to retrain.
        vendor_name: Business name for logging.

    Returns:
        Dictionary with status, metrics, and forecast count.
    """
    vendor_key = str(vendor_id)
    logger.info("━" * 60)
    logger.info("Starting ML pipeline for vendor: %s (%s)", vendor_name, vendor_id)
    logger.info("━" * 60)

    async with async_session_factory() as db:
        # Create initial run log entry
        ml_log = MLRunLog(
            vendor_id=vendor_id,
            model_type="ensemble_v1",
            status=MLRunStatus.RUNNING,
        )
        db.add(ml_log)
        await db.flush()
        run_id = ml_log.id

        try:
            # Import here to avoid circular imports
            from app.ml.forecaster import run_full_pipeline

            result = await run_full_pipeline(db, vendor_id, days_back=90, forecast_days=3)

            if result["status"] == "no_data":
                logger.warning("No order data for vendor %s — skipping", vendor_name)
                ml_log.status = MLRunStatus.COMPLETED
                ml_log.rmse = Decimal("0")
                ml_log.mae = Decimal("0")
                ml_log.mape = Decimal("0")
                await db.commit()

                # Reset failure counter
                _vendor_failure_counts[vendor_key] = 0

                return {
                    "vendor_id": vendor_key,
                    "status": "skipped_no_data",
                    "run_id": str(run_id),
                }

            # Extract ensemble metrics
            xgb_metrics = result.get("xgboost_metrics", {})
            lstm_metrics = result.get("lstm_metrics", {})

            # Use XGBoost metrics as primary (it has 60% weight)
            avg_rmse = (
                xgb_metrics.get("rmse", 0) * 0.6 +
                lstm_metrics.get("rmse", 0) * 0.4
            )
            avg_mae = (
                xgb_metrics.get("mae", 0) * 0.6 +
                lstm_metrics.get("mae", 0) * 0.4
            )
            avg_mape = (
                xgb_metrics.get("mape", 0) * 0.6 +
                lstm_metrics.get("mape", 0) * 0.4
            )

            # Update run log with metrics
            ml_log.status = MLRunStatus.COMPLETED
            ml_log.rmse = Decimal(str(round(avg_rmse, 4)))
            ml_log.mae = Decimal(str(round(avg_mae, 4)))
            ml_log.mape = Decimal(str(round(avg_mape, 4)))
            await db.commit()

            # Invalidate cached forecasts for this vendor
            await invalidate_vendor_forecasts(vendor_key)

            # Reset failure counter on success
            _vendor_failure_counts[vendor_key] = 0

            forecast_count = len(result.get("forecasts", []))
            logger.info(
                "✓ Pipeline complete for %s — RMSE: %.4f, MAE: %.4f, MAPE: %.2f%%, Forecasts: %d",
                vendor_name, avg_rmse, avg_mae, avg_mape, forecast_count,
            )

            return {
                "vendor_id": vendor_key,
                "status": "success",
                "run_id": str(run_id),
                "metrics": {
                    "rmse": round(avg_rmse, 4),
                    "mae": round(avg_mae, 4),
                    "mape": round(avg_mape, 4),
                },
                "forecasts_generated": forecast_count,
                "items_forecasted": result.get("items_forecasted", 0),
            }

        except Exception as e:
            error_msg = f"ML pipeline failed for vendor {vendor_name} ({vendor_id}): {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())

            # Update run log as failed
            ml_log.status = MLRunStatus.FAILED
            await db.commit()

            # Track consecutive failures
            _vendor_failure_counts[vendor_key] = _vendor_failure_counts.get(vendor_key, 0) + 1
            failure_count = _vendor_failure_counts[vendor_key]

            if failure_count >= CONSECUTIVE_FAILURE_ALERT_THRESHOLD:
                alert_msg = (
                    f"ALERT: ML pipeline has failed {failure_count} consecutive times "
                    f"for vendor {vendor_name} ({vendor_id})"
                )
                logger.critical(alert_msg)

                if settings.SENTRY_DSN:
                    sentry_sdk.capture_message(alert_msg, level="error")

            return {
                "vendor_id": vendor_key,
                "status": "failed",
                "run_id": str(run_id),
                "error": str(e),
                "consecutive_failures": failure_count,
            }


# ── Batch Retraining ────────────────────────────────────────────────────────

async def retrain_all_vendors() -> dict:
    """
    Retrain ML models for all active vendors.

    This is the main scheduled job that runs daily at 2:00 AM UTC.
    Each vendor is processed independently — one vendor's failure
    does not block others.

    Returns:
        Summary dictionary with per-vendor results.
    """
    logger.info("=" * 70)
    logger.info("SCHEDULED JOB: retrain_all_vendors started at %s", datetime.now(timezone.utc))
    logger.info("=" * 70)

    async with async_session_factory() as db:
        # Get all vendors that have at least one confirmed order
        from app.models.order import Order, OrderStatus

        vendor_query = (
            select(Vendor.id, Vendor.business_name)
            .join(Order, Vendor.id == Order.vendor_id)
            .where(Order.status == OrderStatus.CONFIRMED)
            .group_by(Vendor.id, Vendor.business_name)
            .having(func.count(Order.id) >= 10)  # Minimum 10 orders for meaningful training
        )

        result = await db.execute(vendor_query)
        vendors = result.all()

    if not vendors:
        logger.info("No eligible vendors found for retraining")
        return {"status": "no_vendors", "results": []}

    logger.info("Found %d eligible vendors for retraining", len(vendors))

    results = []
    success_count = 0
    failure_count = 0

    for vendor_id, business_name in vendors:
        try:
            vendor_result = await retrain_single_vendor(vendor_id, business_name)
            results.append(vendor_result)

            if vendor_result["status"] in ("success", "skipped_no_data"):
                success_count += 1
            else:
                failure_count += 1

        except Exception as e:
            logger.error("Unexpected error processing vendor %s: %s", business_name, e)
            results.append({
                "vendor_id": str(vendor_id),
                "status": "fatal_error",
                "error": str(e),
            })
            failure_count += 1

    logger.info("=" * 70)
    logger.info(
        "SCHEDULED JOB COMPLETE: %d/%d vendors succeeded, %d failed",
        success_count, len(vendors), failure_count,
    )
    logger.info("=" * 70)

    return {
        "status": "completed",
        "total_vendors": len(vendors),
        "success_count": success_count,
        "failure_count": failure_count,
        "results": results,
    }


# ── Scheduler Lifecycle ─────────────────────────────────────────────────────

def start_scheduler() -> None:
    """
    Start the APScheduler with the daily retraining job.

    Schedule: Every day at 2:00 AM UTC.
    This is called during FastAPI application startup.
    """
    scheduler.add_job(
        retrain_all_vendors,
        trigger=CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="daily_retrain_all_vendors",
        name="Daily ML Pipeline Retraining",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("ML Scheduler started — daily retraining at 02:00 UTC")

    # Log next run time
    job = scheduler.get_job("daily_retrain_all_vendors")
    if job and job.next_run_time:
        logger.info("Next scheduled run: %s", job.next_run_time)


def stop_scheduler() -> None:
    """
    Gracefully shut down the scheduler.

    Waits for running jobs to complete before stopping.
    Called during FastAPI application shutdown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("ML Scheduler shut down gracefully")


def get_scheduler_status() -> dict:
    """Get current scheduler status and next run time."""
    job = scheduler.get_job("daily_retrain_all_vendors")
    return {
        "running": scheduler.running,
        "job_id": "daily_retrain_all_vendors",
        "next_run_time": str(job.next_run_time) if job and job.next_run_time else None,
        "vendor_failure_counts": dict(_vendor_failure_counts),
    }
