"""
Orders CRUD operations.
"""

from uuid import UUID
import math
from datetime import datetime
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import BadRequestError
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem, OrderStatus
from app.schemas.order import OrderCreateRequest, OrderFilterParams


async def create_order(
    db: AsyncSession, vendor_id: UUID, body: OrderCreateRequest
) -> Order:
    menu_item_ids = [item.menu_item_id for item in body.items]
    result = await db.execute(
        select(MenuItem).where(
            MenuItem.id.in_(menu_item_ids),
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_active == True,
        )
    )
    menu_items_map = {mi.id: mi for mi in result.scalars().all()}

    missing = set(menu_item_ids) - set(menu_items_map.keys())
    if missing:
        raise BadRequestError(
            f"Menu items not found or inactive: {[str(m) for m in missing]}"
        )

    order = Order(
        vendor_id=vendor_id,
        customer_id=body.customer_id,
        status=OrderStatus.PENDING,
        total_amount=0,
    )
    db.add(order)
    await db.flush()

    from decimal import Decimal
    total = Decimal("0")
    for item_req in body.items:
        menu_item = menu_items_map[item_req.menu_item_id]
        unit_price = menu_item.price
        line_total = unit_price * item_req.quantity
        total += line_total

        order_item = OrderItem(
            order_id=order.id,
            menu_item_id=item_req.menu_item_id,
            quantity=item_req.quantity,
            unit_price=unit_price,
        )
        db.add(order_item)

    order.total_amount = total
    await db.commit()
    await db.refresh(order)

    refreshed = await db.execute(
        select(Order)
        .where(Order.id == order.id)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
    )
    return refreshed.scalar_one()


async def get_orders(
    db: AsyncSession, vendor_id: UUID, filters: OrderFilterParams
) -> tuple[list[Order], int, int]:
    base_filter = Order.vendor_id == vendor_id
    conditions = [base_filter]

    if filters.status is not None:
        conditions.append(Order.status == filters.status)
    if filters.date_from is not None:
        conditions.append(Order.created_at >= filters.date_from)
    if filters.date_to is not None:
        conditions.append(Order.created_at <= filters.date_to)

    combined = and_(*conditions)

    count_result = await db.execute(
        select(func.count()).select_from(Order).where(combined)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(Order)
        .where(combined)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
        .order_by(Order.created_at.desc())
        .offset(filters.offset)
        .limit(filters.page_size)
    )
    orders = result.scalars().all()

    total_pages = math.ceil(total / filters.page_size) if total > 0 else 1

    return list(orders), total, total_pages


async def get_order(
    db: AsyncSession, order_id: UUID, vendor_id: UUID
) -> Order | None:
    result = await db.execute(
        select(Order)
        .where(Order.id == order_id, Order.vendor_id == vendor_id)
        .options(selectinload(Order.items).selectinload(OrderItem.menu_item))
    )
    return result.scalar_one_or_none()


async def update_order_status(
    db: AsyncSession, order: Order, new_status: OrderStatus
) -> Order:
    order.status = new_status
    await db.commit()
    await db.refresh(order)
    return order
