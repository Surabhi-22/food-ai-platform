"""Chat request/response schemas."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """A single chat message."""
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str = Field(..., min_length=1)
    timestamp: str | None = None


class ChatRequest(BaseModel):
    """Request body for sending a chat message."""
    session_id: UUID | None = None
    message: str = Field(..., min_length=1, max_length=2000)


class SourceChunk(BaseModel):
    """A retrieved context chunk used as a source for the response."""
    text: str
    data_type: str
    score: float
    item_name: str = ""


class ChatResponse(BaseModel):
    """Chat response from the RAG pipeline."""
    session_id: UUID
    reply: str
    sources: list[str] = []
    source_chunks: list[SourceChunk] = []


class ChatHistoryResponse(BaseModel):
    """Chat history with recent messages."""
    vendor_id: UUID
    session_id: UUID | None
    messages: list[ChatMessage]
    total_messages: int


class ChatSessionResponse(BaseModel):
    """Full chat session with message history."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    vendor_id: UUID
    messages: list[dict]
    message_count: int = 0
    preview: str = ""
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    """List of chat sessions for a vendor."""
    sessions: list[ChatSessionResponse]
    total: int


class EmbeddingRefreshResponse(BaseModel):
    """Response from embedding refresh operation."""
    vendor_id: UUID
    status: str
    chunks_created: int
    vectors_upserted: int
