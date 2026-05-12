"""
Forecast and ML metrics request/response schemas.

Includes schemas for forecast items, summaries, ML run logs,
and retraining job responses.
"""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


# ── Forecast Item Schemas ────────────────────────────────────────────────────

class ForecastItem(BaseModel):
    """Single forecast item with all prediction details."""
    model_config = ConfigDict(from_attributes=True)

    menu_item_id: UUID
    menu_item_name: str
    category: str
    forecast_date: date
    predicted_quantity: Decimal
    predicted_revenue: Decimal
    predicted_profit: Decimal
    confidence_lower: Decimal
    confidence_upper: Decimal
    cluster_label: str
    inventory_required: Decimal
    model_version: str


class ForecastDateGroup(BaseModel):
    """Forecasts grouped by date, sorted by predicted_revenue desc."""
    forecast_date: date
    items: list[ForecastItem]
    total_predicted_quantity: Decimal
    total_predicted_revenue: Decimal


class ForecastListResponse(BaseModel):
    """Complete forecast response grouped by date."""
    vendor_id: UUID
    forecast_groups: list[ForecastDateGroup]
    total_items: int
    date_range_start: date
    date_range_end: date
    cached: bool = False


# ── Backward Compatibility ───────────────────────────────────────────────────

class ForecastResponse(BaseModel):
    """Single forecast prediction response (legacy format)."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    menu_item_id: UUID
    forecast_date: date
    predicted_quantity: Decimal
    predicted_revenue: Decimal
    confidence_lower: Decimal
    confidence_upper: Decimal
    model_version: str
    created_at: datetime
    item_name: str | None = None


# ── Forecast Summary ─────────────────────────────────────────────────────────

class LowStockAlert(BaseModel):
    """Alert for items where predicted demand exceeds typical supply."""
    menu_item_id: UUID
    menu_item_name: str
    category: str
    predicted_demand_3day: Decimal
    avg_daily_supply: Decimal
    deficit: Decimal
    severity: str  # "high", "medium", "low"


class ForecastSummaryResponse(BaseModel):
    """Aggregated 3-day forecast summary with insights."""
    vendor_id: UUID
    total_revenue_3day: Decimal
    total_profit_3day: Decimal
    total_quantity_3day: Decimal
    top_item: ForecastItem | None
    low_stock_alerts: list[LowStockAlert]
    model_version: str
    forecast_generated_at: datetime | None
    cached: bool = False


# ── ML Retrain Schemas ───────────────────────────────────────────────────────

class RetrainResponse(BaseModel):
    """Response for manual retraining trigger."""
    job_id: str
    vendor_id: UUID
    status: str  # "queued", "running", "completed", "failed"
    message: str


class RetrainStatusResponse(BaseModel):
    """Status of a retraining job."""
    job_id: str
    vendor_id: UUID
    status: str
    metrics: dict | None = None
    forecasts_generated: int = 0
    error: str | None = None


# ── ML Metrics Schemas ───────────────────────────────────────────────────────

class MLRunMetric(BaseModel):
    """Single ML run log entry with metrics."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_type: str
    rmse: Decimal | None
    mae: Decimal | None
    mape: Decimal | None
    trained_at: datetime
    status: str


class MLMetricsResponse(BaseModel):
    """List of ML run metrics for a vendor."""
    vendor_id: UUID
    runs: list[MLRunMetric]
    total_runs: int
    latest_mape: Decimal | None
    avg_mape_last_5: Decimal | None


# ── Scheduler Status ─────────────────────────────────────────────────────────

class SchedulerStatusResponse(BaseModel):
    """Current scheduler status."""
    running: bool
    next_run_time: str | None
    vendor_failure_counts: dict[str, int]
