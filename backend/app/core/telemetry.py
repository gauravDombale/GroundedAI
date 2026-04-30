"""
Observability bootstrap — Langfuse tracing + OpenTelemetry setup.
Call `setup_telemetry()` once during app lifespan startup.
"""
import logging

import structlog
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


def setup_telemetry() -> None:
    """Configure OpenTelemetry tracing and structured logging."""
    settings = get_settings()

    # ── Structured logging ────────────────────────────────────────────────────
    log_level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(level=log_level)

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
            if settings.app_env == "development"
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # ── OpenTelemetry ─────────────────────────────────────────────────────────
    resource = Resource.create({"service.name": settings.otel_service_name})
    provider = TracerProvider(resource=resource)

    try:
        otlp_exporter = OTLPSpanExporter(
            endpoint=settings.otel_exporter_otlp_endpoint,
            insecure=True,
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
        logger.info("otel.configured", endpoint=settings.otel_exporter_otlp_endpoint)
    except Exception as exc:
        logger.warning("otel.skipped", reason=str(exc))

    trace.set_tracer_provider(provider)
    logger.info("telemetry.ready", service=settings.otel_service_name)


def get_tracer() -> trace.Tracer:
    return trace.get_tracer(get_settings().otel_service_name)


def instrument_app(app: object) -> None:
    """Attach FastAPI OTel instrumentation. Call after app creation."""
    FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
