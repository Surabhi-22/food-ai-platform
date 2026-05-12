"""Analytics response schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class DailyRevenuePoint(BaseModel):
    """Single data point for daily revenue chart."""
    date: date
    revenue: Decimal
    order_count: int


class RevenueAnalyticsResponse(BaseModel):
    """Revenue analytics for a date range."""
    daily_revenue: list[DailyRevenuePoint]
    total_revenue: Decimal
    total_orders: int
    avg_daily_revenue: Decimal
    period_days: int


class TopItemEntry(BaseModel):
    """Single entry in the top items leaderboard."""
    menu_item_id: str
    item_name: str
    category: str
    total_quantity: int
    total_revenue: Decimal
    order_count: int


class TopItemsResponse(BaseModel):
    """Top selling items response."""
    items: list[TopItemEntry]
    period_days: int


class InventoryDeltaEntry(BaseModel):
    """Inventory insight for a single menu item."""
    menu_item_id: str
    item_name: str
    category: str
    predicted_demand: Decimal
    actual_sales: Decimal
    delta: Decimal
    recommendation: str


class InventoryInsightsResponse(BaseModel):
    """Inventory delta analysis response."""
    items: list[InventoryDeltaEntry]
    analysis_date: date
    total_items_analyzed: int
