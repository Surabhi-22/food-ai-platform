"""
Redis client and caching utilities.

Provides async Redis connection, cache get/set/invalidate operations,
and a decorator for caching API responses with configurable TTL.
"""

import json
import logging
from functools import wraps
from typing import Any

import redis.asyncio as aioredis

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# ── Redis Client ─────────────────────────────────────────────────────────────

_redis_client: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """Get or create the async Redis client singleton."""
    global _redis_client
    if _redis_client is None:
        _redis_client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
        logger.info("Redis client initialized: %s", settings.REDIS_URL)
    return _redis_client


async def close_redis() -> None:
    """Close the Redis connection pool."""
    global _redis_client
    if _redis_client is not None:
        await _redis_client.close()
        _redis_client = None
        logger.info("Redis connection closed")


# ── Cache Operations ─────────────────────────────────────────────────────────

FORECAST_CACHE_PREFIX = "forecast"
FORECAST_CACHE_TTL = 3600  # 1 hour in seconds


def _cache_key(prefix: str, *parts: str) -> str:
    """Build a namespaced cache key."""
    return f"{prefix}:{':'.join(str(p) for p in parts)}"


async def cache_get(key: str) -> dict | list | None:
    """
    Retrieve a cached value by key.

    Returns:
        Deserialized Python object, or None if cache miss.
    """
    try:
        client = await get_redis()
        data = await client.get(key)
        if data is not None:
            logger.debug("Cache HIT: %s", key)
            return json.loads(data)
        logger.debug("Cache MISS: %s", key)
        return None
    except Exception as e:
        logger.warning("Redis cache_get error for key %s: %s", key, e)
        return None


async def cache_set(key: str, value: Any, ttl: int = FORECAST_CACHE_TTL) -> None:
    """
    Store a value in cache with TTL.

    Args:
        key: Cache key.
        value: JSON-serializable Python object.
        ttl: Time-to-live in seconds (default: 1 hour).
    """
    try:
        client = await get_redis()
        serialized = json.dumps(value, default=str)
        await client.set(key, serialized, ex=ttl)
        logger.debug("Cache SET: %s (TTL=%ds)", key, ttl)
    except Exception as e:
        logger.warning("Redis cache_set error for key %s: %s", key, e)


async def cache_delete(key: str) -> None:
    """Delete a single cache entry."""
    try:
        client = await get_redis()
        await client.delete(key)
        logger.debug("Cache DELETE: %s", key)
    except Exception as e:
        logger.warning("Redis cache_delete error for key %s: %s", key, e)


async def cache_invalidate_pattern(pattern: str) -> int:
    """
    Invalidate all cache entries matching a glob pattern.

    Args:
        pattern: Redis key pattern (e.g., "forecast:vendor_id:*").

    Returns:
        Number of keys deleted.
    """
    try:
        client = await get_redis()
        keys = []
        async for key in client.scan_iter(match=pattern, count=100):
            keys.append(key)
        if keys:
            await client.delete(*keys)
            logger.info("Cache INVALIDATE: %d keys matching '%s'", len(keys), pattern)
        return len(keys)
    except Exception as e:
        logger.warning("Redis cache_invalidate error for pattern %s: %s", pattern, e)
        return 0


async def invalidate_vendor_forecasts(vendor_id: str) -> int:
    """Invalidate all cached forecast data for a specific vendor."""
    pattern = f"{FORECAST_CACHE_PREFIX}:{vendor_id}:*"
    return await cache_invalidate_pattern(pattern)


# ── Rate Limiting ────────────────────────────────────────────────────────────

RATE_LIMIT_PREFIX = "ratelimit"
RATE_LIMIT_WINDOW = 60       # 1 minute window
RATE_LIMIT_MAX_REQUESTS = 60  # 60 requests per minute


async def check_rate_limit(
    identifier: str,
    max_requests: int = RATE_LIMIT_MAX_REQUESTS,
    window_seconds: int = RATE_LIMIT_WINDOW,
) -> tuple[bool, int, int]:
    """
    Check and increment rate limit counter for an identifier.

    Uses a sliding window counter with Redis INCR + EXPIRE.

    Args:
        identifier: Unique identifier (e.g., vendor_id).
        max_requests: Maximum allowed requests in the window.
        window_seconds: Window duration in seconds.

    Returns:
        Tuple of (is_allowed, current_count, remaining).
    """
    try:
        client = await get_redis()
        key = f"{RATE_LIMIT_PREFIX}:{identifier}"

        pipe = client.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_seconds)
        results = await pipe.execute()

        current_count = results[0]
        remaining = max(0, max_requests - current_count)
        is_allowed = current_count <= max_requests

        if not is_allowed:
            logger.warning(
                "Rate limit exceeded for %s: %d/%d requests",
                identifier, current_count, max_requests,
            )

        return is_allowed, current_count, remaining

    except Exception as e:
        logger.warning("Rate limit check failed for %s: %s — allowing request", identifier, e)
        return True, 0, max_requests
