"""
FastAPI application factory with full lifespan management.
Mounts all routers and configures middleware, metrics, and tracing.
"""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

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

    # Initialize telemetry first
    setup_telemetry()
    instrument_app(app)

    # Warm up reranker model (downloads on first run)
    from app.reranking.cross_encoder import get_reranker
    get_reranker()
    logger.info("reranker.ready", model=settings.reranker_model)

    yield

    logger.info("app.shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

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
        allow_origins=["http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Prometheus metrics ────────────────────────────────────────────────────
    Instrumentator().instrument(app).expose(app, endpoint="/metrics")

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(health.router, tags=["Health"])
    app.include_router(retrieve.router, prefix="/api/v1", tags=["Retrieval"])
    app.include_router(ask.router, prefix="/api/v1", tags=["Generation"])

    return app


app = create_app()
