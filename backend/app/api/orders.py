"""
Orders API routes.
POST /orders — create order with items, compute total
GET /orders/{vendor_id} — paginated order list with filters
PATCH /orders/{order_id}/status — update status, trigger ML on confirmed
"""

import math
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_vendor
from app.core.exceptions import NotFoundError
from app.core.redis import cache_invalidate_pattern
from app.crud import crud_orders
from app.db.session import get_db
from app.models.order import Order, OrderStatus
from app.models.vendor import Vendor
from app.schemas.order import (
    OrderCreateRequest,
    OrderFilterParams,
    OrderItemResponse,
    OrderListResponse,
    OrderResponse,
    OrderStatusUpdateRequest,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


def _build_order_response(order: Order) -> OrderResponse:
    """Convert an Order ORM object to an OrderResponse schema."""
    order_items = []
    for oi in order.items:
        item_name = None
        if oi.menu_item is not None:
            item_name = oi.menu_item.name
        order_items.append(
            OrderItemResponse(
                id=oi.id,
                menu_item_id=oi.menu_item_id,
                quantity=oi.quantity,
                unit_price=oi.unit_price,
                item_name=item_name,
            )
        )
    return OrderResponse(
        id=order.id,
        vendor_id=order.vendor_id,
        customer_id=order.customer_id,
        status=order.status,
        total_amount=order.total_amount,
        items=order_items,
        created_at=order.created_at,
        updated_at=order.updated_at,
    )


@router.post(
    "",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new order",
)
async def create_order(
    body: OrderCreateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Create a new order with line items.
    """
    order = await crud_orders.create_order(db=db, vendor_id=vendor.id, body=body)
    return _build_order_response(order)


@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders for the authenticated vendor",
)
async def list_orders(
    filters: OrderFilterParams = Depends(),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> OrderListResponse:
    """Paginated order list with optional filters for status and date range."""
    orders, total, total_pages = await crud_orders.get_orders(
        db=db, vendor_id=vendor.id, filters=filters
    )

    return OrderListResponse(
        items=[_build_order_response(o) for o in orders],
        total=total,
        page=filters.page,
        page_size=filters.page_size,
        total_pages=total_pages,
    )


@router.patch(
    "/{order_id}/status",
    response_model=OrderResponse,
    summary="Update order status",
)
async def update_order_status(
    order_id: UUID,
    body: OrderStatusUpdateRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> OrderResponse:
    """
    Update the status of an order.
    When status changes to 'confirmed', triggers the ML pipeline.
    """
    order = await crud_orders.get_order(db=db, order_id=order_id, vendor_id=vendor.id)
    if order is None:
        raise NotFoundError("Order", order_id)

    valid_transitions = {
        OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
        OrderStatus.CONFIRMED: {OrderStatus.CANCELLED},
        OrderStatus.CANCELLED: set(),
    }

    if body.status not in valid_transitions.get(order.status, set()):
        from app.core.exceptions import BadRequestError
        raise BadRequestError(
            f"Cannot transition from '{order.status.value}' to '{body.status.value}'"
        )

    order = await crud_orders.update_order_status(db=db, order=order, new_status=body.status)

    if body.status == OrderStatus.CONFIRMED:
        await _trigger_ml_pipeline(vendor.id, order.id, db)
        
        # Invalidate analytics cache
        from app.api.analytics import ANALYTICS_CACHE_PREFIX
        await cache_invalidate_pattern(f"{ANALYTICS_CACHE_PREFIX}:{vendor.id}:*")

    return _build_order_response(order)


async def _trigger_ml_pipeline(vendor_id: UUID, order_id: UUID, db: AsyncSession) -> None:
    """
    Trigger the ML pipeline when an order is confirmed.
    Creates an MLRunLog entry with PENDING status.
    In production, this would dispatch a Celery task.
    """
    from app.models.ml_run_log import MLRunLog, MLRunStatus

    ml_log = MLRunLog(
        vendor_id=vendor_id,
        model_type="xgboost_demand",
        status=MLRunStatus.PENDING,
    )
    db.add(ml_log)
    await db.commit()
