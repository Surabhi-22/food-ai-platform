"""
Forecasts & ML API routes.

GET  /forecasts                    — detailed forecasts grouped by date
GET  /forecasts/summary            — 3-day summary with top item + alerts
POST /ml/retrain                   — manually trigger retraining
GET  /ml/metrics                   — last 10 ML run logs
GET  /ml/scheduler/status          — scheduler health info

All forecast endpoints use Redis caching (TTL: 1 hour) and
rate limiting (60 requests/minute per vendor).
"""

import json
import logging
import uuid as uuid_mod
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, status
from fastapi.responses import JSONResponse
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_vendor
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.redis import (
    FORECAST_CACHE_PREFIX,
    FORECAST_CACHE_TTL,
    cache_get,
    cache_set,
    check_rate_limit,
    invalidate_vendor_forecasts,
)
from app.db.session import get_db
from app.models.forecast import Forecast
from app.models.menu_item import MenuItem
from app.models.ml_run_log import MLRunLog, MLRunStatus
from app.models.order import Order, OrderItem, OrderStatus
from app.models.vendor import Vendor
from app.schemas.forecast import (
    ForecastDateGroup,
    ForecastItem,
    ForecastListResponse,
    ForecastSummaryResponse,
    LowStockAlert,
    MLMetricsResponse,
    MLRunMetric,
    RetrainResponse,
    SchedulerStatusResponse,
)

logger = logging.getLogger(__name__)

forecast_router = APIRouter(prefix="/forecasts", tags=["Forecasts"])
ml_router = APIRouter(prefix="/ml", tags=["ML Pipeline"])


# ── Rate Limit Helper ────────────────────────────────────────────────────────

async def _enforce_rate_limit(vendor_id: UUID) -> None:
    """Check rate limit and raise 429 if exceeded."""
    is_allowed, count, remaining = await check_rate_limit(
        identifier=f"forecast:{vendor_id}",
        max_requests=60,
        window_seconds=60,
    )
    if not is_allowed:
        raise BadRequestError(
            f"Rate limit exceeded: {count}/60 requests per minute. "
            f"Please wait before making more requests."
        )


# ── GET /forecasts ──────────────────────────────────────────────────────

@forecast_router.get(
    "",
    response_model=ForecastListResponse,
    summary="Get demand forecasts grouped by date",
)
async def get_forecasts(
    days: int = Query(3, ge=1, le=30, description="Number of days to forecast"),
    menu_item_id: UUID | None = Query(None, description="Filter by specific menu item"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ForecastListResponse:
    """
    Retrieve demand forecasts for the authenticated vendor.

    Returns predictions grouped by date, sorted by predicted_revenue descending.
    Includes cluster labels, profit estimates, and inventory requirements.

    Results are cached in Redis for 1 hour.
    Rate limited to 60 requests/minute per vendor.
    """
    await _enforce_rate_limit(vendor.id)

    # Check Redis cache
    cache_suffix = f"{menu_item_id}" if menu_item_id else "all"
    cache_key = f"{FORECAST_CACHE_PREFIX}:{vendor.id}:list:{days}:{cache_suffix}"
    cached = await cache_get(cache_key)
    if cached is not None and isinstance(cached, dict):
        cached["cached"] = True
        return ForecastListResponse(**cached)

    today = date.today()
    end_date = today + timedelta(days=days)

    # Load forecasts with menu item metadata
    query = (
        select(Forecast)
        .where(
            Forecast.vendor_id == vendor.id,
            Forecast.forecast_date >= today,
            Forecast.forecast_date <= end_date,
        )
        .options(selectinload(Forecast.menu_item))
        .order_by(Forecast.forecast_date, Forecast.predicted_revenue.desc())
    )

    if menu_item_id is not None:
        query = query.where(Forecast.menu_item_id == menu_item_id)

    result = await db.execute(query)
    forecasts = result.scalars().all()

    # Load cluster labels
    cluster_labels = await _get_cluster_labels(db, vendor.id)

    # Group by date
    date_groups: dict[date, list[ForecastItem]] = {}
    for f in forecasts:
        item = f.menu_item
        if item is None:
            continue

        item_id_str = str(f.menu_item_id)
        cluster = cluster_labels.get(item_id_str, "MEDIUM_DEMAND")

        # Calculate profit = revenue × (1 - cogs_percentage/100)
        cogs_pct = float(item.cogs_percentage) if item.cogs_percentage else 30.0
        predicted_revenue = float(f.predicted_revenue)
        predicted_profit = predicted_revenue * (1 - cogs_pct / 100)

        # Inventory = predicted_quantity × 1.15
        predicted_qty = float(f.predicted_quantity)
        inventory_required = predicted_qty * 1.15

        forecast_item = ForecastItem(
            menu_item_id=f.menu_item_id,
            menu_item_name=item.name,
            category=item.category,
            forecast_date=f.forecast_date,
            predicted_quantity=f.predicted_quantity,
            predicted_revenue=f.predicted_revenue,
            predicted_profit=Decimal(str(round(predicted_profit, 2))),
            confidence_lower=f.confidence_lower,
            confidence_upper=f.confidence_upper,
            cluster_label=cluster,
            inventory_required=Decimal(str(round(inventory_required, 2))),
            model_version=f.model_version,
        )

        if f.forecast_date not in date_groups:
            date_groups[f.forecast_date] = []
        date_groups[f.forecast_date].append(forecast_item)

    # Build grouped response sorted by date, items by revenue desc
    forecast_groups = []
    for forecast_date in sorted(date_groups.keys()):
        items = sorted(
            date_groups[forecast_date],
            key=lambda x: float(x.predicted_revenue),
            reverse=True,
        )
        total_qty = sum(float(i.predicted_quantity) for i in items)
        total_rev = sum(float(i.predicted_revenue) for i in items)

        forecast_groups.append(
            ForecastDateGroup(
                forecast_date=forecast_date,
                items=items,
                total_predicted_quantity=Decimal(str(round(total_qty, 2))),
                total_predicted_revenue=Decimal(str(round(total_rev, 2))),
            )
        )

    response = ForecastListResponse(
        vendor_id=vendor.id,
        forecast_groups=forecast_groups,
        total_items=sum(len(g.items) for g in forecast_groups),
        date_range_start=today,
        date_range_end=end_date,
        cached=False,
    )

    # Cache the response
    await cache_set(cache_key, response.model_dump(mode="json"), ttl=FORECAST_CACHE_TTL)

    return response


# ── GET /forecasts/summary ──────────────────────────────────────────────

@forecast_router.get(
    "/summary",
    response_model=ForecastSummaryResponse,
    summary="Get 3-day forecast summary",
)
async def get_forecast_summary(
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ForecastSummaryResponse:
    """
    Aggregated 3-day forecast summary including:
    - Total projected revenue and profit
    - Top predicted item by revenue
    - Low stock alerts for items where demand exceeds supply

    Cached in Redis for 1 hour.
    """
    await _enforce_rate_limit(vendor.id)

    # Check cache
    cache_key = f"{FORECAST_CACHE_PREFIX}:{vendor.id}:summary"
    cached = await cache_get(cache_key)
    if cached is not None and isinstance(cached, dict):
        cached["cached"] = True
        return ForecastSummaryResponse(**cached)

    today = date.today()
    end_date = today + timedelta(days=3)

    # Load all 3-day forecasts
    result = await db.execute(
        select(Forecast)
        .where(
            Forecast.vendor_id == vendor.id,
            Forecast.forecast_date >= today,
            Forecast.forecast_date <= end_date,
        )
        .options(selectinload(Forecast.menu_item))
        .order_by(Forecast.predicted_revenue.desc())
    )
    forecasts = result.scalars().all()

    cluster_labels = await _get_cluster_labels(db, vendor.id)

    # Calculate totals
    total_revenue = Decimal("0")
    total_profit = Decimal("0")
    total_quantity = Decimal("0")
    top_item = None
    model_version = "unknown"
    generated_at = None

    for f in forecasts:
        if f.menu_item is None:
            continue

        cogs_pct = float(f.menu_item.cogs_percentage) if f.menu_item.cogs_percentage else 30.0
        rev = f.predicted_revenue
        profit = Decimal(str(round(float(rev) * (1 - cogs_pct / 100), 2)))

        total_revenue += rev
        total_profit += profit
        total_quantity += f.predicted_quantity
        model_version = f.model_version

        if generated_at is None or f.created_at > generated_at:
            generated_at = f.created_at

        if top_item is None:
            item_id_str = str(f.menu_item_id)
            cluster = cluster_labels.get(item_id_str, "MEDIUM_DEMAND")
            inventory_required = float(f.predicted_quantity) * 1.15
            top_item = ForecastItem(
                menu_item_id=f.menu_item_id,
                menu_item_name=f.menu_item.name,
                category=f.menu_item.category,
                forecast_date=f.forecast_date,
                predicted_quantity=f.predicted_quantity,
                predicted_revenue=f.predicted_revenue,
                predicted_profit=profit,
                confidence_lower=f.confidence_lower,
                confidence_upper=f.confidence_upper,
                cluster_label=cluster,
                inventory_required=Decimal(str(round(inventory_required, 2))),
                model_version=f.model_version,
            )

    # Generate low-stock alerts
    low_stock_alerts = await _compute_low_stock_alerts(db, vendor.id, forecasts)

    response = ForecastSummaryResponse(
        vendor_id=vendor.id,
        total_revenue_3day=total_revenue,
        total_profit_3day=total_profit,
        total_quantity_3day=total_quantity,
        top_item=top_item,
        low_stock_alerts=low_stock_alerts,
        model_version=model_version,
        forecast_generated_at=generated_at,
        cached=False,
    )

    await cache_set(cache_key, response.model_dump(mode="json"), ttl=FORECAST_CACHE_TTL)

    return response


# ── POST /ml/retrain ────────────────────────────────────────────────────

@ml_router.post(
    "/retrain",
    response_model=RetrainResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger ML pipeline retraining",
)
async def trigger_retrain(
    background_tasks: BackgroundTasks,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> RetrainResponse:
    """
    Manually trigger ML pipeline retraining for the authenticated vendor.

    The retraining runs asynchronously in a FastAPI BackgroundTask.
    Returns immediately with a job_id to track progress.
    """
    job_id = str(uuid_mod.uuid4())

    # Create initial ML run log entry
    ml_log = MLRunLog(
        vendor_id=vendor.id,
        model_type="manual_retrain",
        status=MLRunStatus.PENDING,
    )
    db.add(ml_log)
    await db.commit()
    run_id = str(ml_log.id)

    # Schedule background retraining
    background_tasks.add_task(
        _background_retrain,
        vendor_id=vendor.id,
        vendor_name=vendor.business_name,
        run_id=run_id,
    )

    logger.info("Manual retrain queued for vendor %s (job_id=%s)", vendor.business_name, job_id)

    return RetrainResponse(
        job_id=job_id,
        vendor_id=vendor.id,
        status="queued",
        message=f"Retraining job queued for {vendor.business_name}. "
                f"Check /ml/metrics for results.",
    )


async def _background_retrain(vendor_id: UUID, vendor_name: str, run_id: str) -> None:
    """Execute the ML pipeline in a background task."""
    from app.ml.scheduler import retrain_single_vendor

    logger.info("Background retrain starting for vendor %s", vendor_name)
    result = await retrain_single_vendor(vendor_id, vendor_name)
    logger.info("Background retrain completed for vendor %s: %s", vendor_name, result.get("status"))


# ── GET /ml/metrics ─────────────────────────────────────────────────────

@ml_router.get(
    "/metrics",
    response_model=MLMetricsResponse,
    summary="Get ML run history and metrics",
)
async def get_ml_metrics(
    limit: int = Query(10, ge=1, le=50, description="Number of runs to return"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> MLMetricsResponse:
    """
    Retrieve the last N ML training run logs for the authenticated vendor.

    Returns RMSE, MAE, and MAPE per run, plus aggregated stats.
    """
    query = (
        select(MLRunLog)
        .where(MLRunLog.vendor_id == vendor.id)
        .order_by(MLRunLog.trained_at.desc())
        .limit(limit)
    )

    result = await db.execute(query)
    logs = result.scalars().all()

    runs = [
        MLRunMetric(
            id=log.id,
            model_type=log.model_type,
            rmse=log.rmse,
            mae=log.mae,
            mape=log.mape,
            trained_at=log.trained_at,
            status=log.status.value,
        )
        for log in logs
    ]

    # Calculate latest and average MAPE
    latest_mape = None
    completed_mapes = []

    for log in logs:
        if log.status == MLRunStatus.COMPLETED and log.mape is not None:
            if latest_mape is None:
                latest_mape = log.mape
            completed_mapes.append(float(log.mape))

    avg_mape_last_5 = None
    if completed_mapes:
        last_5 = completed_mapes[:5]
        avg_mape_last_5 = Decimal(str(round(sum(last_5) / len(last_5), 4)))

    return MLMetricsResponse(
        vendor_id=vendor.id,
        runs=runs,
        total_runs=len(runs),
        latest_mape=latest_mape,
        avg_mape_last_5=avg_mape_last_5,
    )


# ── GET /ml/scheduler/status ───────────────────────────────────────────

@ml_router.get(
    "/scheduler/status",
    response_model=SchedulerStatusResponse,
    summary="Get ML scheduler status",
)
async def get_scheduler_status(
    vendor: Vendor = Depends(get_current_vendor),
) -> SchedulerStatusResponse:
    """Get the current status of the ML retraining scheduler."""
    from app.ml.scheduler import get_scheduler_status as _get_status

    status_data = _get_status()
    return SchedulerStatusResponse(**status_data)


# ── Helper Functions ────────────────────────────────────────────────────

async def _get_cluster_labels(db: AsyncSession, vendor_id: UUID) -> dict[str, str]:
    """
    Load cluster labels for a vendor's menu items.

    Falls back to loading from the saved cluster model artifact.
    Returns a dict mapping menu_item_id → cluster label string.
    """
    try:
        from app.ml.clustering import load_cluster_model
        model = load_cluster_model(vendor_id)
        if model is None:
            return {}

        # If we have the model, we need the item features to predict
        # For now, return empty dict — clusters are assigned during training
        # and would need item_features to map. Use a cached mapping instead.
        return {}

    except Exception:
        return {}


from typing import Sequence
async def _compute_low_stock_alerts(
    db: AsyncSession,
    vendor_id: UUID,
    forecasts: Sequence[Forecast],
) -> list[LowStockAlert]:
    """
    Compute low stock alerts by comparing predicted 3-day demand
    against the average daily supply (based on recent confirmed orders).
    """
    if not forecasts:
        return []

    # Get average daily quantity per item from last 14 days
    fourteen_days_ago = datetime.now(timezone.utc) - timedelta(days=14)

    avg_supply_query = (
        select(
            OrderItem.menu_item_id,
            (func.sum(OrderItem.quantity) / 14).label("avg_daily_supply"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .where(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.CONFIRMED,
            Order.created_at >= fourteen_days_ago,
        )
        .group_by(OrderItem.menu_item_id)
    )

    result = await db.execute(avg_supply_query)
    supply_map = {row.menu_item_id: float(row.avg_daily_supply) for row in result.all()}

    # Aggregate predicted demand per item (3-day total)
    demand_map: dict[UUID, float] = {}
    item_metadata: dict[UUID, tuple[str, str]] = {}

    for f in forecasts:
        if f.menu_item is None:
            continue
        mid = f.menu_item_id
        demand_map[mid] = demand_map.get(mid, 0) + float(f.predicted_quantity)
        if mid not in item_metadata:
            item_metadata[mid] = (f.menu_item.name, f.menu_item.category)

    alerts = []
    for item_id, predicted_3day in demand_map.items():
        avg_supply = supply_map.get(item_id, 0)
        avg_supply_3day = avg_supply * 3

        if avg_supply_3day <= 0:
            continue

        deficit = predicted_3day - avg_supply_3day

        if deficit > 0:
            ratio = predicted_3day / avg_supply_3day if avg_supply_3day > 0 else 999

            if ratio > 2.0:
                severity = "high"
            elif ratio > 1.5:
                severity = "medium"
            else:
                severity = "low"

            name, category = item_metadata.get(item_id, ("Unknown", "Unknown"))

            alerts.append(
                LowStockAlert(
                    menu_item_id=item_id,
                    menu_item_name=name,
                    category=category,
                    predicted_demand_3day=Decimal(str(round(predicted_3day, 2))),
                    avg_daily_supply=Decimal(str(round(avg_supply, 2))),
                    deficit=Decimal(str(round(deficit, 2))),
                    severity=severity,
                )
            )

    # Sort by severity (high first) then deficit
    severity_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (severity_order.get(a.severity, 3), -float(a.deficit)))

    return alerts
