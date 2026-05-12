"""ChatSession ORM model — vendor chat history with JSONB messages."""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    vendor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False, index=True
    )
    messages: Mapped[list[dict]] = mapped_column(
        JSONB, nullable=False, server_default="[]"
    )

    # Relationships
    vendor = relationship("Vendor", back_populates="chat_sessions")

    def __repr__(self) -> str:
        msg_count = len(self.messages) if self.messages else 0
        return f"<ChatSession id={self.id} messages={msg_count}>"
