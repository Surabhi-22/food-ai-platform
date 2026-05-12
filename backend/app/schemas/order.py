"""Order request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.order import OrderStatus


class OrderItemCreateRequest(BaseModel):
    """Single item in an order creation request."""
    menu_item_id: UUID
    quantity: int = Field(..., gt=0)


class OrderCreateRequest(BaseModel):
    """Request body for creating a new order."""
    customer_id: UUID | None = None
    items: list[OrderItemCreateRequest] = Field(..., min_length=1)


class OrderStatusUpdateRequest(BaseModel):
    """Request body for updating order status."""
    status: OrderStatus


class OrderItemResponse(BaseModel):
    """Order item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    menu_item_id: UUID | None
    quantity: int
    unit_price: Decimal
    item_name: str | None = None


class OrderResponse(BaseModel):
    """Full order response with items."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    customer_id: UUID | None
    status: OrderStatus
    total_amount: Decimal
    items: list[OrderItemResponse] = []
    created_at: datetime
    updated_at: datetime


class OrderListResponse(BaseModel):
    """Paginated list of orders."""
    items: list[OrderResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class OrderFilterParams(BaseModel):
    """Query parameters for filtering orders."""
    status: OrderStatus | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
