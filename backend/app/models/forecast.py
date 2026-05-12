"""Forecast ORM model — ML prediction outputs."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Forecast(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "forecasts"

    __table_args__ = (
        Index("ix_forecasts_vendor_date", "vendor_id", "forecast_date"),
    )

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    menu_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    forecast_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    predicted_quantity: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    predicted_revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    confidence_lower: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    confidence_upper: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)

    # Relationships
    vendor = relationship("Vendor", back_populates="forecasts")
    menu_item = relationship("MenuItem", back_populates="forecasts")

    def __repr__(self) -> str:
        return f"<Forecast id={self.id} date={self.forecast_date} qty={self.predicted_quantity}>"
