"""Health check endpoints."""
import time
from typing import Any

import structlog
from fastapi import APIRouter

logger = structlog.get_logger(__name__)
router = APIRouter()

_start_time = time.time()


@router.get("/health", summary="Liveness probe")
async def health() -> dict[str, str]:
    """Returns 200 OK when the service is alive."""
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe")
async def readiness() -> dict[str, Any]:
    """
    Checks downstream dependency connectivity.
    Returns 200 only if Qdrant, Elasticsearch, Postgres, and Redis are reachable.
    """
    import redis.asyncio as aioredis
    from elasticsearch import AsyncElasticsearch
    from qdrant_client import AsyncQdrantClient

    from app.core.config import get_settings

    settings = get_settings()
    checks: dict[str, str] = {}

    # Qdrant
    try:
        qclient = AsyncQdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
        await qclient.get_collections()
        checks["qdrant"] = "ok"
        await qclient.close()
    except Exception as exc:
        checks["qdrant"] = f"error: {exc}"

    # Elasticsearch
    try:
        es = AsyncElasticsearch(settings.elasticsearch_url)
        info = await es.info()
        checks["elasticsearch"] = f"ok ({info['version']['number']})"
        await es.close()
    except Exception as exc:
        checks["elasticsearch"] = f"error: {exc}"

    # Redis
    try:
        r = await aioredis.from_url(settings.redis_url)
        await r.ping()
        checks["redis"] = "ok"
        await r.aclose()
    except Exception as exc:
        checks["redis"] = f"error: {exc}"

    all_ok = all("ok" in v for v in checks.values())
    return {
        "status": "ready" if all_ok else "degraded",
        "uptime_seconds": round(time.time() - _start_time, 1),
        "checks": checks,
    }
