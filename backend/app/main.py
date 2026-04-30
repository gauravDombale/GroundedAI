"""
FastAPI application factory with full lifespan management.
Mounts all routers and configures middleware, metrics, and tracing.
"""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from app.api import ask, health, retrieve
from app.core.config import get_settings
from app.core.telemetry import instrument_app, setup_telemetry

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Startup/shutdown lifecycle handler."""
    settings = get_settings()
    logger.info("app.starting", env=settings.app_env)

    # Ensure databases are initialized
    from app.retrieval.bm25_retriever import get_bm25_retriever
    from app.retrieval.vector_retriever import get_vector_retriever
    await get_bm25_retriever().ensure_index()
    await get_vector_retriever().ensure_collection()

    # Warm up reranker model (downloads on first run)
    from app.reranking.cross_encoder import get_reranker
    get_reranker()
    logger.info("reranker.ready", model=settings.reranker_model)

    yield

    logger.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    # Initialize telemetry first
    setup_telemetry()

    app = FastAPI(
        title="Production RAG — Ask My Docs",
        description=(
            "Hybrid BM25 + vector retrieval with cross-encoder reranking "
            "and citation-grounded answer generation."
        ),
        version="0.1.0",
        docs_url="/docs" if settings.app_env == "development" else None,
        redoc_url="/redoc" if settings.app_env == "development" else None,
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Prometheus metrics ────────────────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── OpenTelemetry Instrumentation ─────────────────────────────────────────
    instrument_app(app)

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(retrieve.router, prefix="/api/v1", tags=["Retrieval"])
    app.include_router(ask.router, prefix="/api/v1", tags=["Generation"])

    return app


app = create_app()
