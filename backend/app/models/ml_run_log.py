"""MLRunLog ORM model — ML training run metadata and metrics."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, UUIDPrimaryKeyMixin


class MLRunStatus(str, enum.Enum):
    """Status of an ML training run."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class MLRunLog(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "ml_run_logs"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_type: Mapped[str] = mapped_column(String(50), nullable=False)
    rmse: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    mae: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    trained_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[MLRunStatus] = mapped_column(
        Enum(MLRunStatus, name="ml_run_status", create_constraint=True, native_enum=True),
        nullable=False,
        server_default=MLRunStatus.PENDING.value,
    )

    # Relationships
    vendor = relationship("Vendor", back_populates="ml_run_logs")

    def __repr__(self) -> str:
        return f"<MLRunLog id={self.id} model={self.model_type} status={self.status}>"
