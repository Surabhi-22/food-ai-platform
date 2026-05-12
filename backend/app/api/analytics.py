"""
Analytics API routes.
GET /analytics/revenue — daily revenue for last N days
GET /analytics/top-items — top 10 items by quantity sold
GET /analytics/inventory — stock vs predicted demand delta
"""

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_vendor
from app.core.redis import cache_get, cache_set
from app.db.session import get_db
from app.models.forecast import Forecast
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.models.vendor import Vendor
from app.schemas.analytics import (
    DailyRevenuePoint,
    InventoryDeltaEntry,
    InventoryInsightsResponse,
    RevenueAnalyticsResponse,
    TopItemEntry,
    TopItemsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

ANALYTICS_CACHE_TTL = 900  # 15 minutes
ANALYTICS_CACHE_PREFIX = "analytics"


@router.get(
    "/revenue",
    response_model=RevenueAnalyticsResponse,
    summary="Daily revenue analytics",
)
async def get_revenue_analytics(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> RevenueAnalyticsResponse:
    """
    Get daily revenue breakdown for the last N days.
    Only counts confirmed orders.
    """
    cache_key = f"{ANALYTICS_CACHE_PREFIX}:{vendor.id}:revenue:{days}"
    cached = await cache_get(cache_key)
    if isinstance(cached, dict):
        return RevenueAnalyticsResponse(**cached)

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            func.date(Order.created_at).label("order_date"),
            func.sum(Order.total_amount).label("revenue"),
            func.count(Order.id).label("order_count"),
        )
        .where(
            Order.vendor_id == vendor.id,
            Order.status == OrderStatus.CONFIRMED,
            Order.created_at >= start_date,
        )
        .group_by(func.date(Order.created_at))
        .order_by(func.date(Order.created_at))
    )

    result = await db.execute(query)
    rows = result.all()

    daily_revenue = []
    total_revenue = Decimal("0.00")
    total_orders = 0

    for row in rows:
        revenue = row.revenue or Decimal("0.00")
        count = row.order_count or 0
        daily_revenue.append(
            DailyRevenuePoint(
                date=row.order_date,
                revenue=revenue,
                order_count=count,
            )
        )
        total_revenue += revenue
        total_orders += count

    avg_daily = total_revenue / days if days > 0 else Decimal("0.00")

    response = RevenueAnalyticsResponse(
        daily_revenue=daily_revenue,
        total_revenue=total_revenue,
        total_orders=total_orders,
        avg_daily_revenue=avg_daily.quantize(Decimal("0.01")),
        period_days=days,
    )

    await cache_set(cache_key, response.model_dump(mode="json"), ttl=ANALYTICS_CACHE_TTL)
    return response


@router.get(
    "/top-items",
    response_model=TopItemsResponse,
    summary="Top selling menu items",
)
async def get_top_items(
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    limit: int = Query(10, ge=1, le=50, description="Number of top items"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> TopItemsResponse:
    """
    Get top N selling items by total quantity sold over the last N days.
    Only counts items from confirmed orders.
    """
    cache_key = f"{ANALYTICS_CACHE_PREFIX}:{vendor.id}:top_items:{days}:{limit}"
    cached = await cache_get(cache_key)
    if isinstance(cached, dict):
        return TopItemsResponse(**cached)

    start_date = datetime.now(timezone.utc) - timedelta(days=days)

    query = (
        select(
            OrderItem.menu_item_id,
            MenuItem.name.label("item_name"),
            MenuItem.category,
            func.sum(OrderItem.quantity).label("total_quantity"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
            func.count(func.distinct(OrderItem.order_id)).label("order_count"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .where(
            Order.vendor_id == vendor.id,
            Order.status == OrderStatus.CONFIRMED,
            Order.created_at >= start_date,
        )
        .group_by(OrderItem.menu_item_id, MenuItem.name, MenuItem.category)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(limit)
    )

    result = await db.execute(query)
    rows = result.all()

    items = [
        TopItemEntry(
            menu_item_id=str(row.menu_item_id),
            item_name=row.item_name,
            category=row.category,
            total_quantity=row.total_quantity or 0,
            total_revenue=row.total_revenue or Decimal("0.00"),
            order_count=row.order_count or 0,
        )
        for row in rows
    ]

    response = TopItemsResponse(items=items, period_days=days)
    await cache_set(cache_key, response.model_dump(mode="json"), ttl=ANALYTICS_CACHE_TTL)
    return response


@router.get(
    "/inventory",
    response_model=InventoryInsightsResponse,
    summary="Inventory vs predicted demand delta",
)
async def get_inventory_insights(
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> InventoryInsightsResponse:
    """
    Compare actual recent sales against predicted demand to identify
    overstocked and understocked items.
    """
    cache_key = f"{ANALYTICS_CACHE_PREFIX}:{vendor.id}:inventory"
    cached = await cache_get(cache_key)
    if isinstance(cached, dict):
        return InventoryInsightsResponse(**cached)

    today = date.today()
    week_ago = today - timedelta(days=7)

    sales_query = (
        select(
            OrderItem.menu_item_id,
            MenuItem.name.label("item_name"),
            MenuItem.category,
            func.sum(OrderItem.quantity).label("actual_sales"),
        )
        .join(Order, OrderItem.order_id == Order.id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .where(
            Order.vendor_id == vendor.id,
            Order.status == OrderStatus.CONFIRMED,
            Order.created_at >= datetime.combine(week_ago, datetime.min.time()).replace(tzinfo=timezone.utc),
        )
        .group_by(OrderItem.menu_item_id, MenuItem.name, MenuItem.category)
    )

    sales_result = await db.execute(sales_query)
    sales_rows = {row.menu_item_id: row for row in sales_result.all()}

    forecast_query = (
        select(
            Forecast.menu_item_id,
            func.sum(Forecast.predicted_quantity).label("predicted_demand"),
        )
        .where(
            Forecast.vendor_id == vendor.id,
            Forecast.forecast_date >= week_ago,
            Forecast.forecast_date <= today,
        )
        .group_by(Forecast.menu_item_id)
    )

    forecast_result = await db.execute(forecast_query)
    forecast_rows = {row.menu_item_id: row for row in forecast_result.all()}

    all_item_ids = set(sales_rows.keys()) | set(forecast_rows.keys())

    items_query = await db.execute(
        select(MenuItem).where(
            MenuItem.id.in_(all_item_ids),
            MenuItem.vendor_id == vendor.id,
        )
    )
    items_map = {mi.id: mi for mi in items_query.scalars().all()}

    entries = []
    for item_id in all_item_ids:
        mi = items_map.get(item_id)
        if mi is None:
            continue

        actual = Decimal(str(sales_rows[item_id].actual_sales)) if item_id in sales_rows else Decimal("0")
        predicted = Decimal(str(forecast_rows[item_id].predicted_demand)) if item_id in forecast_rows else Decimal("0")
        delta = actual - predicted

        if delta > 0:
            recommendation = "Demand exceeded forecast — consider increasing preparation"
        elif delta < 0:
            recommendation = "Overproduction detected — reduce preparation quantity"
        else:
            recommendation = "On track — demand matches forecast"

        entries.append(
            InventoryDeltaEntry(
                menu_item_id=str(item_id),
                item_name=mi.name,
                category=mi.category,
                predicted_demand=predicted,
                actual_sales=actual,
                delta=delta,
                recommendation=recommendation,
            )
        )

    entries.sort(key=lambda e: abs(e.delta), reverse=True)

    response = InventoryInsightsResponse(
        items=entries,
        analysis_date=today,
        total_items_analyzed=len(entries),
    )
    await cache_set(cache_key, response.model_dump(mode="json"), ttl=ANALYTICS_CACHE_TTL)
    return response
