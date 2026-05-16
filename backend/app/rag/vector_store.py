"""
Pinecone vector store operations for RAG.

Manages vendor-namespaced vector embeddings with strict data isolation.
Each vendor's data lives in its own Pinecone namespace to prevent
cross-tenant data leakage.

Academic Reference:
    - Approximate nearest neighbor search (Johnson et al., 2019)
    - Namespace isolation for multi-tenant RAG (Gao et al., 2023)
"""

import logging
from uuid import UUID

from pinecone import Pinecone, ServerlessSpec

from app.core.config import get_settings
from app.rag.embedder import DataChunk, embed_query, EMBEDDING_DIMENSIONS

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Pinecone Client ──────────────────────────────────────────────────────────

_pinecone_client: Pinecone | None = None
_pinecone_index = None

INDEX_NAME = "food-platform-vectors"


def _get_pinecone_client() -> Pinecone:
    """Get or create the Pinecone client singleton."""
    global _pinecone_client
    if _pinecone_client is None:
        if not settings.PINECONE_API_KEY or settings.PINECONE_API_KEY in (
            "your-pinecone-api-key",
            "",
        ):
            raise ConnectionError("Pinecone API key not configured")
        _pinecone_client = Pinecone(api_key=settings.PINECONE_API_KEY)
        logger.info("Pinecone client initialized")
    return _pinecone_client


def _get_index():
    """Get or create the Pinecone index."""
    global _pinecone_index
    if _pinecone_index is None:
        pc = _get_pinecone_client()

        try:
            # Create index if it doesn't exist
            existing = [idx.name for idx in pc.list_indexes()]
        except Exception as e:
            logger.warning("Pinecone list_indexes failed: %s — treating as unavailable", e)
            raise ConnectionError(f"Pinecone unavailable: {e}") from e

        if INDEX_NAME not in existing:
            try:
                logger.info("Creating Pinecone index: %s", INDEX_NAME)
                pc.create_index(
                    name=INDEX_NAME,
                    dimension=EMBEDDING_DIMENSIONS,
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
                logger.info("Pinecone index created: %s", INDEX_NAME)
            except Exception as e:
                logger.warning("Pinecone create_index failed: %s", e)
                raise ConnectionError(f"Pinecone index creation failed: {e}") from e

        _pinecone_index = pc.Index(INDEX_NAME)
        logger.info("Connected to Pinecone index: %s", INDEX_NAME)

    return _pinecone_index


def _vendor_namespace(vendor_id: UUID) -> str:
    """Generate the Pinecone namespace for a vendor (data isolation)."""
    return f"vendor_{vendor_id}"


# ── Upsert Embeddings ───────────────────────────────────────────────────────

async def upsert_embeddings(
    vendor_id: UUID,
    chunks: list[DataChunk],
    embeddings: list[list[float]],
    batch_size: int = 100,
) -> int:
    """
    Upsert embeddings into Pinecone with vendor namespace isolation.

    Each vector includes:
        - id: unique chunk identifier
        - values: embedding vector
        - metadata: structured metadata for filtering

    Args:
        vendor_id: UUID of the vendor.
        chunks: List of DataChunk objects.
        embeddings: Corresponding embedding vectors.
        batch_size: Number of vectors to upsert per batch.

    Returns:
        Number of vectors upserted.
    """
    if not chunks or not embeddings:
        logger.warning("No chunks or embeddings to upsert for vendor %s", vendor_id)
        return 0

    if len(chunks) != len(embeddings):
        raise ValueError(
            f"Chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )

    try:
        index = _get_index()
    except ConnectionError as e:
        logger.warning("Pinecone not available: %s — skipping upsert", e)
        return 0

    namespace = _vendor_namespace(vendor_id)

    # Prepare vectors
    vectors = []
    for chunk, embedding in zip(chunks, embeddings):
        # Pinecone metadata values must be strings, numbers, booleans, or lists
        clean_metadata = {}
        for key, value in chunk.metadata.items():
            if isinstance(value, (str, int, float, bool)):
                clean_metadata[key] = value
            else:
                clean_metadata[key] = str(value)

        # Add the original text to metadata for retrieval
        clean_metadata["text"] = chunk.text

        vectors.append({
            "id": chunk.chunk_id,
            "values": embedding,
            "metadata": clean_metadata,
        })

    # Batch upsert
    upserted = 0
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        upserted += len(batch)
        logger.debug("Upserted batch %d-%d to namespace %s", i, i + len(batch), namespace)

    logger.info(
        "Upserted %d vectors to Pinecone namespace '%s'",
        upserted, namespace,
    )
    return upserted


# ── Semantic Search ──────────────────────────────────────────────────────────

async def semantic_search(
    vendor_id: UUID,
    query_text: str,
    top_k: int = 8,
    data_type_filter: str | None = None,
) -> list[dict]:
    """
    Perform semantic search on a vendor's embedded data.

    Steps:
        1. Embed the query text using OpenAI
        2. Search only within the vendor's Pinecone namespace
        3. Return top_k most relevant chunks with similarity scores

    Args:
        vendor_id: UUID of the vendor (namespace isolation).
        query_text: Natural language query.
        top_k: Number of results to return.
        data_type_filter: Optional filter for data type ("order", "forecast", "menu").

    Returns:
        List of dictionaries with keys: text, score, metadata.
    """
    try:
        index = _get_index()
    except ConnectionError as e:
        logger.warning("Pinecone not available: %s — returning empty results", e)
        return []

    # Generate query embedding
    query_embedding = await embed_query(query_text)

    namespace = _vendor_namespace(vendor_id)

    # Build metadata filter if specified
    filter_dict = None
    if data_type_filter:
        filter_dict = {"data_type": {"$eq": data_type_filter}}

    # Query Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        namespace=namespace,
        include_metadata=True,
        filter=filter_dict,
    )

    # Parse results
    search_results = []
    for match in results.get("matches", []):
        metadata = match.get("metadata", {})
        search_results.append({
            "text": metadata.get("text", ""),
            "score": float(match.get("score", 0)),
            "data_type": metadata.get("data_type", "unknown"),
            "item_name": metadata.get("item_name", ""),
            "date": metadata.get("date", ""),
            "metadata": metadata,
        })

    logger.info(
        "Semantic search for vendor %s: query='%s' → %d results (top score: %.4f)",
        vendor_id,
        query_text[:50],
        len(search_results),
        search_results[0]["score"] if search_results else 0,
    )

    return search_results


# ── Delete Vendor Embeddings ─────────────────────────────────────────────────

async def delete_vendor_embeddings(vendor_id: UUID) -> bool:
    """
    Delete all embeddings for a vendor (for GDPR compliance or data refresh).

    Removes the entire vendor namespace from Pinecone.

    Args:
        vendor_id: UUID of the vendor.

    Returns:
        True if successful, False otherwise.
    """
    try:
        index = _get_index()
    except ConnectionError as e:
        logger.warning("Pinecone not available: %s — cannot delete", e)
        return False

    namespace = _vendor_namespace(vendor_id)

    try:
        index.delete(delete_all=True, namespace=namespace)
        logger.info("Deleted all vectors in namespace '%s'", namespace)
        return True
    except Exception as e:
        logger.error("Failed to delete namespace '%s': %s", namespace, e)
        return False


# ── Refresh Vendor Embeddings ────────────────────────────────────────────────

async def refresh_vendor_embeddings(
    db,
    vendor_id: UUID,
    days_back: int = 90,
) -> dict:
    """
    Full refresh of a vendor's embeddings.

    Steps:
        1. Delete existing embeddings
        2. Pull fresh data and create chunks
        3. Generate new embeddings
        4. Upsert to Pinecone

    Args:
        db: Async database session.
        vendor_id: UUID of the vendor.
        days_back: Days of historical data.

    Returns:
        Summary dictionary with chunk counts and status.
    """
    from app.rag.embedder import embed_vendor_data

    logger.info("Refreshing embeddings for vendor %s", vendor_id)

    # Step 1: Delete existing
    await delete_vendor_embeddings(vendor_id)

    # Step 2 & 3: Create chunks and generate embeddings
    chunks, embeddings = await embed_vendor_data(db, vendor_id, days_back)

    if not chunks:
        return {"status": "no_data", "chunks": 0}

    # Step 4: Upsert new embeddings
    upserted = await upsert_embeddings(vendor_id, chunks, embeddings)

    return {
        "status": "success",
        "chunks_created": len(chunks),
        "vectors_upserted": upserted,
    }
