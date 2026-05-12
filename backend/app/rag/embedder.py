"""
Vendor data embedding pipeline for RAG.

Pulls order, menu, and forecast data from PostgreSQL, converts structured
data into natural language text chunks, and generates vector embeddings
using OpenAI text-embedding-3-small.

Academic Reference:
    - Retrieval-Augmented Generation (Lewis et al., 2020)
    - Dense passage retrieval (Karpukhin et al., 2020)
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import numpy as np
from openai import AsyncOpenAI
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.forecast import Forecast
from app.models.menu_item import MenuItem
from app.models.order import Order, OrderItem, OrderStatus

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Embedding Configuration ─────────────────────────────────────────────────

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
BATCH_SIZE = 100  # OpenAI recommends batching up to 2048 inputs


# ── Data Chunk Types ─────────────────────────────────────────────────────────

class DataChunk:
    """A text chunk with metadata for vector storage."""

    def __init__(
        self,
        chunk_id: str,
        text: str,
        metadata: dict,
    ):
        self.chunk_id = chunk_id
        self.text = text
        self.metadata = metadata

    def __repr__(self) -> str:
        return f"<DataChunk id={self.chunk_id} type={self.metadata.get('data_type')} len={len(self.text)}>"


# ── Text Chunking from Structured Data ───────────────────────────────────────

async def create_order_chunks(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
) -> list[DataChunk]:
    """
    Create natural language text chunks from order data.

    Each chunk describes one day's sales for one menu item, e.g.:
    "On 2024-12-10, menu item Chicken Biryani sold 45 units
     generating Rs.6,750 revenue."
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    query = (
        select(
            func.date(Order.created_at).label("order_date"),
            MenuItem.name.label("item_name"),
            MenuItem.category.label("category"),
            MenuItem.price.label("unit_price"),
            func.sum(OrderItem.quantity).label("total_qty"),
            func.sum(OrderItem.quantity * OrderItem.unit_price).label("total_revenue"),
            func.count(func.distinct(Order.id)).label("order_count"),
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .where(
            and_(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= cutoff,
            )
        )
        .group_by(
            func.date(Order.created_at),
            MenuItem.id,
            MenuItem.name,
            MenuItem.category,
            MenuItem.price,
        )
        .order_by(func.date(Order.created_at).desc())
    )

    result = await db.execute(query)
    rows = result.all()

    chunks = []
    for row in rows:
        date_str = str(row.order_date)
        qty = int(row.total_qty)
        revenue = float(row.total_revenue)
        price = float(row.unit_price)

        text = (
            f"On {date_str}, menu item {row.item_name} ({row.category}) "
            f"sold {qty} units at Rs.{price:.0f} each, "
            f"generating Rs.{revenue:,.0f} revenue "
            f"across {row.order_count} orders."
        )

        chunk = DataChunk(
            chunk_id=f"order_{vendor_id}_{date_str}_{row.item_name}".replace(" ", "_"),
            text=text,
            metadata={
                "vendor_id": str(vendor_id),
                "data_type": "order",
                "date": date_str,
                "item_name": row.item_name,
                "category": row.category,
                "quantity": qty,
                "revenue": revenue,
            },
        )
        chunks.append(chunk)

    logger.info("Created %d order chunks for vendor %s", len(chunks), vendor_id)
    return chunks


async def create_menu_chunks(
    db: AsyncSession,
    vendor_id: UUID,
) -> list[DataChunk]:
    """
    Create text chunks from menu item data.

    Each chunk describes a menu item with its pricing and COGS.
    """
    result = await db.execute(
        select(MenuItem).where(MenuItem.vendor_id == vendor_id)
    )
    items = result.scalars().all()

    chunks = []
    for item in items:
        status = "active and available" if item.is_active else "currently inactive"
        cogs = float(item.cogs_percentage)
        price = float(item.price)
        profit_margin = 100 - cogs

        text = (
            f"Menu item: {item.name}. Category: {item.category}. "
            f"Price: Rs.{price:.0f}. Cost of goods: {cogs:.0f}%. "
            f"Profit margin: {profit_margin:.0f}%. "
            f"Status: {status}."
        )

        chunk = DataChunk(
            chunk_id=f"menu_{vendor_id}_{item.id}",
            text=text,
            metadata={
                "vendor_id": str(vendor_id),
                "data_type": "menu",
                "item_name": item.name,
                "category": item.category,
                "price": price,
                "cogs_percentage": cogs,
                "is_active": item.is_active,
            },
        )
        chunks.append(chunk)

    logger.info("Created %d menu chunks for vendor %s", len(chunks), vendor_id)
    return chunks


async def create_forecast_chunks(
    db: AsyncSession,
    vendor_id: UUID,
) -> list[DataChunk]:
    """
    Create text chunks from forecast predictions.

    Each chunk describes a demand prediction for a specific item and date.
    """
    result = await db.execute(
        select(Forecast)
        .where(Forecast.vendor_id == vendor_id)
        .options(selectinload(Forecast.menu_item))
        .order_by(Forecast.forecast_date.desc())
        .limit(100)
    )
    forecasts = result.scalars().all()

    chunks = []
    for f in forecasts:
        item_name = f.menu_item.name if f.menu_item else "Unknown Item"
        category = f.menu_item.category if f.menu_item else "Unknown"
        date_str = str(f.forecast_date)
        qty = float(f.predicted_quantity)
        revenue = float(f.predicted_revenue)
        lower = float(f.confidence_lower)
        upper = float(f.confidence_upper)

        text = (
            f"Forecast for {date_str}: {item_name} ({category}) "
            f"predicted {qty:.0f} units, revenue Rs.{revenue:,.0f}. "
            f"Confidence interval: {lower:.0f} to {upper:.0f} units. "
            f"Model version: {f.model_version}."
        )

        chunk = DataChunk(
            chunk_id=f"forecast_{vendor_id}_{date_str}_{f.menu_item_id}",
            text=text,
            metadata={
                "vendor_id": str(vendor_id),
                "data_type": "forecast",
                "date": date_str,
                "item_name": item_name,
                "category": category,
                "predicted_quantity": qty,
                "predicted_revenue": revenue,
            },
        )
        chunks.append(chunk)

    logger.info("Created %d forecast chunks for vendor %s", len(chunks), vendor_id)
    return chunks


async def create_summary_chunks(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
) -> list[DataChunk]:
    """
    Create high-level summary chunks for the vendor's business.

    These provide aggregate context for general questions.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)

    # Total revenue and order count
    stats_query = select(
        func.count(Order.id).label("order_count"),
        func.sum(Order.total_amount).label("total_revenue"),
    ).where(
        and_(
            Order.vendor_id == vendor_id,
            Order.status == OrderStatus.CONFIRMED,
            Order.created_at >= cutoff,
        )
    )
    stats_result = await db.execute(stats_query)
    stats = stats_result.one()

    # Top items
    top_items_query = (
        select(
            MenuItem.name,
            func.sum(OrderItem.quantity).label("total_qty"),
        )
        .join(OrderItem, Order.id == OrderItem.order_id)
        .join(MenuItem, OrderItem.menu_item_id == MenuItem.id)
        .where(
            and_(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= cutoff,
            )
        )
        .group_by(MenuItem.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    top_result = await db.execute(top_items_query)
    top_items = top_result.all()

    # Menu item count
    menu_count_result = await db.execute(
        select(func.count()).select_from(MenuItem).where(
            MenuItem.vendor_id == vendor_id,
            MenuItem.is_active == True,  # noqa: E712
        )
    )
    menu_count = menu_count_result.scalar() or 0

    chunks = []

    # Business overview chunk
    order_count = stats.order_count or 0
    total_revenue = float(stats.total_revenue or 0)
    avg_order = total_revenue / order_count if order_count > 0 else 0

    overview_text = (
        f"Business overview for last {days_back} days: "
        f"{order_count} confirmed orders, total revenue Rs.{total_revenue:,.0f}, "
        f"average order value Rs.{avg_order:,.0f}. "
        f"{menu_count} active menu items on the menu."
    )
    chunks.append(DataChunk(
        chunk_id=f"summary_overview_{vendor_id}",
        text=overview_text,
        metadata={"vendor_id": str(vendor_id), "data_type": "summary", "item_name": "business_overview"},
    ))

    # Top sellers chunk
    if top_items:
        top_list = ", ".join(
            f"{item.name} ({int(item.total_qty)} units)" for item in top_items
        )
        top_text = f"Top selling items in the last {days_back} days: {top_list}."
        chunks.append(DataChunk(
            chunk_id=f"summary_top_items_{vendor_id}",
            text=top_text,
            metadata={"vendor_id": str(vendor_id), "data_type": "summary", "item_name": "top_sellers"},
        ))

    # Weekly trends
    weekly_query = (
        select(
            func.date_trunc("week", Order.created_at).label("week"),
            func.sum(Order.total_amount).label("weekly_revenue"),
            func.count(Order.id).label("weekly_orders"),
        )
        .where(
            and_(
                Order.vendor_id == vendor_id,
                Order.status == OrderStatus.CONFIRMED,
                Order.created_at >= cutoff,
            )
        )
        .group_by(func.date_trunc("week", Order.created_at))
        .order_by(func.date_trunc("week", Order.created_at).desc())
        .limit(4)
    )
    weekly_result = await db.execute(weekly_query)
    weeks = weekly_result.all()

    if weeks:
        week_parts = []
        for w in weeks:
            week_str = str(w.week.date()) if hasattr(w.week, "date") else str(w.week)
            week_parts.append(
                f"Week of {week_str}: Rs.{float(w.weekly_revenue):,.0f} from {w.weekly_orders} orders"
            )
        weekly_text = "Weekly revenue trend: " + ". ".join(week_parts) + "."
        chunks.append(DataChunk(
            chunk_id=f"summary_weekly_{vendor_id}",
            text=weekly_text,
            metadata={"vendor_id": str(vendor_id), "data_type": "summary", "item_name": "weekly_trend"},
        ))

    logger.info("Created %d summary chunks for vendor %s", len(chunks), vendor_id)
    return chunks


# ── Embedding Generation ────────────────────────────────────────────────────

async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Generate embeddings for a list of texts using OpenAI text-embedding-3-small.

    Batches requests in groups of BATCH_SIZE to respect API limits.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each is a list of floats).
    """
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured — returning zero vectors")
        return [[0.0] * EMBEDDING_DIMENSIONS for _ in texts]

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    all_embeddings = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        logger.debug("Embedding batch %d-%d of %d texts", i, i + len(batch), len(texts))

        response = await client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )

        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    logger.info("Generated %d embeddings (dim=%d)", len(all_embeddings), EMBEDDING_DIMENSIONS)
    return all_embeddings


async def embed_query(query: str) -> list[float]:
    """Generate an embedding for a single query string."""
    embeddings = await generate_embeddings([query])
    return embeddings[0]


# ── Complete Embedding Pipeline ──────────────────────────────────────────────

async def embed_vendor_data(
    db: AsyncSession,
    vendor_id: UUID,
    days_back: int = 90,
) -> tuple[list[DataChunk], list[list[float]]]:
    """
    Complete pipeline: pull vendor data, create chunks, generate embeddings.

    Steps:
        1. Create text chunks from orders, menu items, forecasts, and summaries
        2. Generate embeddings for all chunks in batches of 100
        3. Return chunks and embeddings for vector store upsert

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        days_back: Days of historical data to embed.

    Returns:
        Tuple of (chunks, embeddings).
    """
    logger.info("Starting embedding pipeline for vendor %s", vendor_id)

    # Collect all chunks
    order_chunks = await create_order_chunks(db, vendor_id, days_back)
    menu_chunks = await create_menu_chunks(db, vendor_id)
    forecast_chunks = await create_forecast_chunks(db, vendor_id)
    summary_chunks = await create_summary_chunks(db, vendor_id, days_back)

    all_chunks = order_chunks + menu_chunks + forecast_chunks + summary_chunks

    if not all_chunks:
        logger.warning("No data chunks created for vendor %s", vendor_id)
        return [], []

    # Generate embeddings
    texts = [chunk.text for chunk in all_chunks]
    embeddings = await generate_embeddings(texts)

    logger.info(
        "Embedding pipeline complete: %d chunks (%d orders, %d menu, %d forecasts, %d summaries)",
        len(all_chunks), len(order_chunks), len(menu_chunks),
        len(forecast_chunks), len(summary_chunks),
    )

    return all_chunks, embeddings
