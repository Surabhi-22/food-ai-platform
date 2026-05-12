"""
RAG-based vendor chatbot powered by GPT-4o.

Retrieves relevant vendor data via semantic search in Pinecone,
builds a grounded prompt with retrieved context, and generates
responses that are strictly based on the vendor's own data.

Academic Reference:
    - Retrieval-Augmented Generation (Lewis et al., 2020)
    - Grounded response generation (Shuster et al., 2021)
"""

import logging
from datetime import datetime, timezone
from uuid import UUID

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.chat_session import ChatSession
from app.rag.vector_store import semantic_search

logger = logging.getLogger(__name__)
settings = get_settings()

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a business analytics assistant for a food vendor on the AI-Powered Food Demand Forecasting platform.

RULES:
1. Answer ONLY from the provided context data. Do not make up facts or numbers.
2. If the answer is not in the provided context, clearly state: "I don't have enough data to answer that. Try rephrasing or check the Analytics dashboard."
3. Be concise, specific, and actionable. Use numbers and dates from the context.
4. Format currency as Rs. (Indian Rupees) with comma separators.
5. When discussing quantities, round to whole numbers.
6. If asked about future demand, reference the forecast data with confidence intervals.
7. When recommending preparation quantities, add a 15% safety buffer.
8. Always be encouraging and supportive of the vendor's business decisions.

You have access to the vendor's:
- Order history (item-level sales data)
- Menu items (prices, categories, cost of goods)
- Demand forecasts (predicted quantities and revenue)
- Business summaries (weekly trends, top sellers)"""

MAX_HISTORY_MESSAGES = 5  # Keep last 5 messages for context window management
MAX_CONTEXT_CHARS = 6000  # Max characters for retrieved context


class VendorChatbot:
    """
    RAG chatbot that answers vendor questions using their own business data.

    Pipeline:
        1. Semantic search for relevant data chunks in Pinecone
        2. Build grounded prompt with retrieved context + chat history
        3. Call GPT-4o for response generation
        4. Persist updated chat history to database
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None

    async def chat(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        user_message: str,
        session_id: UUID | None = None,
    ) -> dict:
        """
        Process a chat message and generate a response.

        Args:
            db: Async database session.
            vendor_id: UUID of the vendor.
            user_message: The user's message.
            session_id: Optional existing session ID to continue.

        Returns:
            Dictionary with keys: session_id, reply, sources, source_chunks.
        """
        # 1. Load or create chat session
        session = await self._get_or_create_session(db, vendor_id, session_id)

        # 2. Retrieve relevant context via semantic search
        context_chunks = await semantic_search(
            vendor_id=vendor_id,
            query_text=user_message,
            top_k=8,
        )

        # 3. Build the prompt
        messages = self._build_prompt(user_message, context_chunks, session.messages)

        # 4. Generate response
        if self.client:
            reply_text = await self._call_gpt4o(messages)
        else:
            reply_text = self._fallback_response(user_message, context_chunks)

        # 5. Extract source references
        sources = list(set(
            chunk.get("data_type", "unknown") for chunk in context_chunks
        ))
        source_details = [
            {
                "text": chunk["text"][:200],
                "data_type": chunk["data_type"],
                "score": round(chunk["score"], 4),
                "item_name": chunk.get("item_name", ""),
            }
            for chunk in context_chunks[:5]  # Top 5 sources
        ]

        # 6. Persist chat history
        await self._save_messages(db, session, user_message, reply_text)

        return {
            "session_id": session.id,
            "reply": reply_text,
            "sources": sources,
            "source_chunks": source_details,
        }

    async def chat_stream(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        user_message: str,
        session_id: UUID | None = None,
    ):
        """
        Generate a streaming response using GPT-4o with stream=True.

        Yields chunks of the response as they are generated.
        Used by the SSE endpoint.

        Args:
            db: Database session.
            vendor_id: Vendor UUID.
            user_message: User's message.
            session_id: Optional session to continue.

        Yields:
            String chunks of the response.
        """
        session = await self._get_or_create_session(db, vendor_id, session_id)

        context_chunks = await semantic_search(
            vendor_id=vendor_id,
            query_text=user_message,
            top_k=8,
        )

        messages = self._build_prompt(user_message, context_chunks, session.messages)

        full_response = ""

        if self.client:
            stream = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                stream=True,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content
        else:
            fallback = self._fallback_response(user_message, context_chunks)
            full_response = fallback
            # Simulate streaming for fallback
            words = fallback.split()
            for i in range(0, len(words), 3):
                chunk_text = " ".join(words[i : i + 3]) + " "
                yield chunk_text

        # Save complete response to history
        await self._save_messages(db, session, user_message, full_response)

        # Yield session info as final chunk
        yield f"\n\n[SESSION_ID:{session.id}]"

    def _build_prompt(
        self,
        user_message: str,
        context_chunks: list[dict],
        chat_history: list[dict] | None,
    ) -> list[ChatCompletionMessageParam]:
        """
        Build the GPT-4o prompt with system instructions, context, history, and query.

        Structure:
            1. System prompt with rules
            2. Retrieved context as numbered list
            3. Last 5 messages of chat history
            4. Current user message
        """
        messages = [{"role": "system", "content": SYSTEM_PROMPT}]

        # Add retrieved context
        if context_chunks:
            context_parts = []
            total_chars = 0
            for i, chunk in enumerate(context_chunks, 1):
                text = chunk.get("text", "")
                if total_chars + len(text) > MAX_CONTEXT_CHARS:
                    break
                context_parts.append(f"{i}. [{chunk.get('data_type', 'data').upper()}] {text}")
                total_chars += len(text)

            context_block = "\n".join(context_parts)
            messages.append({
                "role": "system",
                "content": f"RETRIEVED BUSINESS DATA:\n{context_block}",
            })

        # Add chat history (last N messages)
        if chat_history:
            recent = chat_history[-MAX_HISTORY_MESSAGES * 2 :]  # user+assistant pairs
            for msg in recent:
                role = msg.get("role", "user")
                if role in ("user", "assistant"):
                    messages.append({
                        "role": role,
                        "content": msg.get("content", ""),
                    })

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    async def _call_gpt4o(self, messages: list[ChatCompletionMessageParam]) -> str:
        """Call OpenAI GPT-4o and return the response text."""
        if not self.client:
            return "OpenAI client not configured."
            
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
                top_p=0.9,
            )

            reply = response.choices[0].message.content
            usage = response.usage

            logger.info(
                "GPT-4o response: %d tokens (prompt=%d, completion=%d)",
                usage.total_tokens, usage.prompt_tokens, usage.completion_tokens,
            )

            return reply

        except Exception as e:
            logger.error("GPT-4o API call failed: %s", e)
            return (
                "I'm sorry, I encountered an error processing your request. "
                "Please try again in a moment."
            )

    def _fallback_response(
        self,
        user_message: str,
        context_chunks: list[dict],
    ) -> str:
        """
        Generate a response without OpenAI API using retrieved context.

        Used when API keys are not configured (development/testing).
        """
        if not context_chunks:
            return (
                "I don't have enough data to answer that question yet. "
                "As more orders come in, I'll be able to provide better insights. "
                "Try asking about your menu items, recent sales, or demand forecasts."
            )

        # Build a response from context chunks
        lower_msg = user_message.lower()
        relevant_texts = [c["text"] for c in context_chunks[:4]]

        if any(word in lower_msg for word in ["prepare", "tomorrow", "forecast", "predict"]):
            forecast_chunks = [c for c in context_chunks if c.get("data_type") == "forecast"]
            if forecast_chunks:
                items = [c["text"] for c in forecast_chunks[:3]]
                return (
                    "Based on your demand forecasts, here's what to prepare:\n\n"
                    + "\n".join(f"• {item}" for item in items)
                    + "\n\nI recommend adding a 15% safety buffer to these quantities."
                )

        if any(word in lower_msg for word in ["best", "top", "selling", "popular"]):
            summary_chunks = [c for c in context_chunks if c.get("data_type") == "summary"]
            if summary_chunks:
                return "Here's what the data shows:\n\n" + "\n".join(
                    f"• {c['text']}" for c in summary_chunks[:3]
                )

        if any(word in lower_msg for word in ["revenue", "profit", "sales", "money", "earn"]):
            order_chunks = [c for c in context_chunks if c.get("data_type") == "order"]
            if order_chunks:
                return "Here are your recent sales figures:\n\n" + "\n".join(
                    f"• {c['text']}" for c in order_chunks[:4]
                )

        if any(word in lower_msg for word in ["stock", "inventory", "overstock", "waste"]):
            return (
                "Based on your data, here are the relevant insights:\n\n"
                + "\n".join(f"• {t}" for t in relevant_texts[:3])
                + "\n\nCheck the Inventory Insights dashboard for detailed stock recommendations."
            )

        # Generic response with context
        return (
            "Here's what I found in your business data:\n\n"
            + "\n".join(f"• {t}" for t in relevant_texts[:3])
            + "\n\nWould you like more details on any of these?"
        )

    async def _get_or_create_session(
        self,
        db: AsyncSession,
        vendor_id: UUID,
        session_id: UUID | None,
    ) -> ChatSession:
        """Load an existing session or create a new one."""
        if session_id:
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.vendor_id == vendor_id,
                )
            )
            session = result.scalar_one_or_none()
            if session:
                return session

        session = ChatSession(vendor_id=vendor_id, messages=[])
        db.add(session)
        await db.flush()
        await db.refresh(session)
        return session

    async def _save_messages(
        self,
        db: AsyncSession,
        session: ChatSession,
        user_message: str,
        assistant_reply: str,
    ) -> None:
        """Persist user message and assistant reply to the chat session."""
        now = datetime.now(timezone.utc).isoformat()

        current = list(session.messages) if session.messages else []
        current.append({"role": "user", "content": user_message, "timestamp": now})
        current.append({"role": "assistant", "content": assistant_reply, "timestamp": now})

        session.messages = current
        session.updated_at = datetime.now(timezone.utc)
        await db.flush()


# ── Singleton Instance ───────────────────────────────────────────────────────

chatbot = VendorChatbot()
