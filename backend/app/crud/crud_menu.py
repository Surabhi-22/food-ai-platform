"""
Menu items CRUD operations.
"""

from uuid import UUID
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.menu_item import MenuItem
from app.schemas.menu import MenuItemCreateRequest, MenuItemUpdateRequest


async def create_menu_item(
    db: AsyncSession, vendor_id: UUID, body: MenuItemCreateRequest
) -> MenuItem:
    item = MenuItem(
        vendor_id=vendor_id,
        name=body.name,
        category=body.category,
        price=body.price,
        cogs_percentage=body.cogs_percentage,
        is_active=body.is_active,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def get_menu_items(
    db: AsyncSession,
    vendor_id: UUID,
    category: str | None = None,
    is_active: bool | None = None,
) -> tuple[list[MenuItem], int]:
    query = select(MenuItem).where(MenuItem.vendor_id == vendor_id)
    count_query = select(func.count()).select_from(MenuItem).where(MenuItem.vendor_id == vendor_id)

    if category is not None:
        query = query.where(MenuItem.category == category)
        count_query = count_query.where(MenuItem.category == category)
    if is_active is not None:
        query = query.where(MenuItem.is_active == is_active)
        count_query = count_query.where(MenuItem.is_active == is_active)

    query = query.order_by(MenuItem.category, MenuItem.name)

    result = await db.execute(query)
    items = result.scalars().all()

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    return list(items), total


async def get_menu_item(
    db: AsyncSession, item_id: UUID, vendor_id: UUID
) -> MenuItem | None:
    result = await db.execute(
        select(MenuItem).where(MenuItem.id == item_id, MenuItem.vendor_id == vendor_id)
    )
    return result.scalar_one_or_none()


async def update_menu_item(
    db: AsyncSession, item: MenuItem, body: MenuItemUpdateRequest
) -> MenuItem:
    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return item


async def soft_delete_menu_item(db: AsyncSession, item: MenuItem) -> None:
    item.is_active = False
    await db.commit()
