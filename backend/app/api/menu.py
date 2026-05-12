"""
Menu items CRUD API routes (vendor-scoped).
All endpoints require authentication and are scoped to the current vendor.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.deps import get_current_vendor
from app.core.exceptions import NotFoundError
from app.crud import crud_menu
from app.db.session import get_db
from app.models.vendor import Vendor
from app.schemas.menu import (
    MenuItemCreateRequest,
    MenuItemListResponse,
    MenuItemResponse,
    MenuItemUpdateRequest,
)

router = APIRouter(prefix="/menu", tags=["Menu Items"])


@router.post(
    "",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new menu item",
)
async def create_menu_item(
    body: MenuItemCreateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Create a new menu item for the authenticated vendor."""
    item = await crud_menu.create_menu_item(db=db, vendor_id=vendor.id, body=body)
    return MenuItemResponse.model_validate(item)


@router.get(
    "",
    response_model=MenuItemListResponse,
    summary="List all menu items for the vendor",
)
async def list_menu_items(
    category: str | None = Query(None, description="Filter by category"),
    is_active: bool | None = Query(None, description="Filter by active status"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> MenuItemListResponse:
    """Retrieve all menu items for the authenticated vendor with optional filters."""
    items, total = await crud_menu.get_menu_items(
        db=db, vendor_id=vendor.id, category=category, is_active=is_active
    )

    return MenuItemListResponse(
        items=[MenuItemResponse.model_validate(item) for item in items],
        total=total,
    )


@router.get(
    "/{item_id}",
    response_model=MenuItemResponse,
    summary="Get a single menu item",
)
async def get_menu_item(
    item_id: UUID,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Retrieve a single menu item by ID (vendor-scoped)."""
    item = await crud_menu.get_menu_item(db=db, item_id=item_id, vendor_id=vendor.id)
    if item is None:
        raise NotFoundError("Menu item", item_id)
    return MenuItemResponse.model_validate(item)


@router.put(
    "/{item_id}",
    response_model=MenuItemResponse,
    summary="Update a menu item",
)
async def update_menu_item(
    item_id: UUID,
    body: MenuItemUpdateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> MenuItemResponse:
    """Update an existing menu item. Only provided fields are modified."""
    item = await crud_menu.get_menu_item(db=db, item_id=item_id, vendor_id=vendor.id)
    if item is None:
        raise NotFoundError("Menu item", item_id)

    updated_item = await crud_menu.update_menu_item(db=db, item=item, body=body)
    return MenuItemResponse.model_validate(updated_item)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a menu item",
)
async def delete_menu_item(
    item_id: UUID,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a menu item by setting is_active to false."""
    item = await crud_menu.get_menu_item(db=db, item_id=item_id, vendor_id=vendor.id)
    if item is None:
        raise NotFoundError("Menu item", item_id)

    await crud_menu.soft_delete_menu_item(db=db, item=item)
