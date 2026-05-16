"""Menu item request/response schemas."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MenuItemCreateRequest(BaseModel):
    """Request body for creating a menu item."""
    name: str = Field(..., min_length=1, max_length=255, examples=["Chicken Biryani"])
    category: str = Field(..., min_length=1, max_length=100, examples=["Main Course"])
    price: Decimal = Field(..., gt=Decimal("0"), decimal_places=2, examples=[249.99])
    cogs_percentage: Decimal = Field(default=Decimal("30.00"), ge=Decimal("0"), le=Decimal("100"), decimal_places=2)
    description: str | None = Field(None, max_length=1000)
    is_active: bool = True


class MenuItemUpdateRequest(BaseModel):
    """Request body for updating a menu item. All fields optional."""
    name: str | None = Field(None, min_length=1, max_length=255)
    category: str | None = Field(None, min_length=1, max_length=100)
    price: Decimal | None = Field(None, gt=Decimal("0"), decimal_places=2)
    cogs_percentage: Decimal | None = Field(None, ge=Decimal("0"), le=Decimal("100"), decimal_places=2)
    description: str | None = Field(None, max_length=1000)
    is_active: bool | None = None


class MenuItemResponse(BaseModel):
    """Menu item response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    name: str
    category: str
    price: Decimal
    cogs_percentage: Decimal
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MenuItemListResponse(BaseModel):
    """Paginated list of menu items."""
    items: list[MenuItemResponse]
    total: int
