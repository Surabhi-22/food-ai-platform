"""
Chat API routes for the RAG-based AI chatbot.

POST   /chat              → Send message, get AI response
POST   /chat/stream        → Streaming response via Server-Sent Events
GET    /chat/history       → Get last 20 messages
DELETE /chat/history       → Clear chat history
GET    /chat/sessions      → List all chat sessions
GET    /chat/sessions/{id} → Get a specific session
POST   /chat/embeddings/refresh → Refresh vendor's RAG embeddings
"""

import asyncio
import logging
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import delete, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_vendor
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.chat_session import ChatSession
from app.models.vendor import Vendor
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatSessionListResponse,
    ChatSessionResponse,
    EmbeddingRefreshResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["AI Chatbot"])


# ── POST /chat ──────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=ChatResponse,
    summary="Send a message to the AI chatbot",
)
async def send_chat_message(
    body: ChatRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Send a message to the RAG-based AI chatbot.

    Pipeline:
        1. Semantic search for top 8 relevant vendor data chunks
        2. Build GPT-4o prompt with system rules, context, and history
        3. Generate grounded response (answers only from vendor's data)
        4. Persist chat history to database
        5. Return response with source references
    """
    from app.rag.chatbot import chatbot

    result = await chatbot.chat(
        db=db,
        vendor_id=vendor.id,
        user_message=body.message,
        session_id=body.session_id,
    )

    await db.commit()

    return ChatResponse(
        session_id=result["session_id"],
        reply=result["reply"],
        sources=result["sources"],
        source_chunks=result.get("source_chunks", []),
    )


# ── POST /chat/stream ──────────────────────────────────────────────────

@router.post(
    "/stream",
    summary="Stream AI chatbot response via Server-Sent Events",
)
async def stream_chat_message(
    body: ChatRequest,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
):
    """
    Send a message and receive a streaming response via Server-Sent Events.

    Uses OpenAI's stream=True parameter for real-time token generation.
    Each SSE event contains a chunk of the response text.

    Event format:
        data: <text chunk>

    Final event:
        data: [DONE]
    """
    from app.rag.chatbot import chatbot

    async def event_generator():
        try:
            async for chunk in chatbot.chat_stream(
                db=db,
                vendor_id=vendor.id,
                user_message=body.message,
                session_id=body.session_id,
            ):
                # Check for session info marker
                if chunk.startswith("\n\n[SESSION_ID:"):
                    session_id = chunk.strip().replace("[SESSION_ID:", "").rstrip("]").strip()
                    yield f"data: {{\n\"session_id\": \"{session_id}\"}}\n\n"
                else:
                    # Escape newlines for SSE
                    escaped = chunk.replace("\n", "\\n")
                    yield f"data: {escaped}\n\n"

            await db.commit()
            yield "data: [DONE]\n\n"

        except Exception as e:
            logger.error("Streaming error: %s", e)
            yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── GET /chat/history ───────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=ChatHistoryResponse,
    summary="Get chat history (last 20 messages)",
)
async def get_chat_history(
    session_id: UUID | None = Query(None, description="Specific session ID"),
    limit: int = Query(20, ge=1, le=100, description="Max messages to return"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    """
    Retrieve the last N messages from the vendor's chat history.

    If session_id is provided, returns messages from that specific session.
    Otherwise, returns the most recent messages across all sessions.
    """
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.vendor_id == vendor.id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError("Chat session", session_id)

        messages_raw = session.messages or []
        messages = [
            ChatMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=m.get("timestamp"),
            )
            for m in messages_raw[-limit:]
        ]

        return ChatHistoryResponse(
            vendor_id=vendor.id,
            session_id=session.id,
            messages=messages,
            total_messages=len(messages),
        )

    # Get most recent session
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.vendor_id == vendor.id)
        .order_by(ChatSession.updated_at.desc())
        .limit(1)
    )
    session = result.scalar_one_or_none()

    if session is None:
        return ChatHistoryResponse(
            vendor_id=vendor.id,
            session_id=None,
            messages=[],
            total_messages=0,
        )

    messages_raw = session.messages or []
    messages = [
        ChatMessage(
            role=m.get("role", "user"),
            content=m.get("content", ""),
            timestamp=m.get("timestamp"),
        )
        for m in messages_raw[-limit:]
    ]

    return ChatHistoryResponse(
        vendor_id=vendor.id,
        session_id=session.id,
        messages=messages,
        total_messages=len(messages),
    )


# ── DELETE /chat/history ────────────────────────────────────────────────

@router.delete(
    "/history",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear all chat history",
)
async def clear_chat_history(
    session_id: UUID | None = Query(None, description="Clear specific session only"),
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Delete chat history for the authenticated vendor.

    If session_id is provided, deletes only that session.
    Otherwise, deletes all chat sessions for the vendor.
    """
    if session_id:
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.vendor_id == vendor.id,
            )
        )
        session = result.scalar_one_or_none()
        if session is None:
            raise NotFoundError("Chat session", session_id)
        await db.delete(session)
    else:
        await db.execute(
            delete(ChatSession).where(ChatSession.vendor_id == vendor.id)
        )

    await db.commit()
    logger.info("Cleared chat history for vendor %s (session=%s)", vendor.id, session_id or "all")


# ── GET /chat/sessions ─────────────────────────────────────────────────

@router.get(
    "/sessions",
    response_model=ChatSessionListResponse,
    summary="List all chat sessions",
)
async def list_chat_sessions(
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionListResponse:
    """List all chat sessions for the authenticated vendor, most recent first."""
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.vendor_id == vendor.id)
        .order_by(ChatSession.updated_at.desc())
    )
    sessions = result.scalars().all()

    session_responses = []
    for s in sessions:
        msg_count = len(s.messages) if s.messages else 0
        preview = ""
        if s.messages and len(s.messages) > 0:
            first_msg = s.messages[0]
            preview = first_msg.get("content", "")[:100]

        session_responses.append(
            ChatSessionResponse(
                id=s.id,
                vendor_id=s.vendor_id,
                messages=s.messages or [],
                message_count=msg_count,
                preview=preview,
                created_at=s.created_at,
                updated_at=s.updated_at,
            )
        )

    return ChatSessionListResponse(
        sessions=session_responses,
        total=len(session_responses),
    )


# ── GET /chat/sessions/{session_id} ────────────────────────────────────

@router.get(
    "/sessions/{session_id}",
    response_model=ChatSessionResponse,
    summary="Get a specific chat session",
)
async def get_chat_session(
    session_id: UUID,
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> ChatSessionResponse:
    """Retrieve a specific chat session by ID with full message history."""
    result = await db.execute(
        select(ChatSession).where(
            ChatSession.id == session_id,
            ChatSession.vendor_id == vendor.id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise NotFoundError("Chat session", session_id)

    msg_count = len(session.messages) if session.messages else 0
    preview = ""
    if session.messages and len(session.messages) > 0:
        preview = session.messages[0].get("content", "")[:100]

    return ChatSessionResponse(
        id=session.id,
        vendor_id=session.vendor_id,
        messages=session.messages or [],
        message_count=msg_count,
        preview=preview,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


# ── POST /chat/embeddings/refresh ──────────────────────────────────────

@router.post(
    "/embeddings/refresh",
    response_model=EmbeddingRefreshResponse,
    summary="Refresh vendor's RAG embeddings",
)
async def refresh_embeddings(
    vendor: Vendor = Depends(get_current_vendor),
    db: AsyncSession = Depends(get_db),
) -> EmbeddingRefreshResponse:
    """
    Trigger a full refresh of the vendor's RAG embeddings.

    This re-processes all orders, menu items, and forecasts,
    generates new embeddings, and upserts them to Pinecone.
    """
    from app.rag.vector_store import refresh_vendor_embeddings

    result = await refresh_vendor_embeddings(db, vendor.id)

    return EmbeddingRefreshResponse(
        vendor_id=vendor.id,
        status=result["status"],
        chunks_created=result.get("chunks_created", 0),
        vectors_upserted=result.get("vectors_upserted", 0),
    )
