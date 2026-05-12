"""Vendor ORM model — the primary tenant entity."""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Vendor(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "vendors"

    business_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    customers = relationship(
        "Customer", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )
    menu_items = relationship(
        "MenuItem", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )
    orders = relationship(
        "Order", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )
    forecasts = relationship(
        "Forecast", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )
    chat_sessions = relationship(
        "ChatSession", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )
    ml_run_logs = relationship(
        "MLRunLog", back_populates="vendor", cascade="all, delete-orphan", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<Vendor id={self.id} business_name='{self.business_name}'>"
