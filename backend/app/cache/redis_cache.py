"""
Redis-backed query result cache.
Serializes/deserializes AskResponse payloads as JSON.
"""
import json
from typing import Any

import redis.asyncio as aioredis
import structlog

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_redis_client: aioredis.Redis | None = None  # type: ignore[type-arg]


async def get_redis() -> aioredis.Redis:  # type: ignore[type-arg]
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = await aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    return _redis_client


def _cache_key(query: str) -> str:
    """Normalize query to a consistent cache key."""
    return f"rag:ask:{query.strip().lower()[:200]}"


async def cached_ask(query: str) -> dict[str, Any] | None:
    """
    Retrieve a cached ask result.

    Returns:
        Cached dict payload, or None if cache miss.
    """
    try:
        r = await get_redis()
        raw = await r.get(_cache_key(query))
        if raw:
            return json.loads(raw)  # type: ignore[no-any-return]
    except Exception as exc:
        logger.warning("cache.get_failed", error=str(exc))
    return None


async def cache_ask_result(query: str, payload: dict[str, Any]) -> None:
    """
    Store an ask result in Redis.

    Args:
        query: The user query (used as cache key).
        payload: The serializable response dict.
    """
    settings = get_settings()
    try:
        r = await get_redis()
        await r.setex(
            _cache_key(query),
            settings.redis_ttl_seconds,
            json.dumps(payload),
        )
        logger.debug("cache.stored", key=_cache_key(query), ttl=settings.redis_ttl_seconds)
    except Exception as exc:
        logger.warning("cache.set_failed", error=str(exc))
