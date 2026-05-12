"""MenuItem ORM model — food items on a vendor's menu."""

import uuid
from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class MenuItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "menu_items"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cogs_percentage: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=False, server_default="30.00"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    # Relationships
    vendor = relationship("Vendor", back_populates="menu_items")
    order_items = relationship(
        "OrderItem", back_populates="menu_item", cascade="save-update, merge", lazy="selectin"
    )
    forecasts = relationship(
        "Forecast", back_populates="menu_item", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<MenuItem id={self.id} name='{self.name}' price={self.price}>"
