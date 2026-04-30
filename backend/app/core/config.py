"""
Application configuration — loaded from environment variables via pydantic-settings.
All settings are read once at startup; use `get_settings()` for cached access.
"""
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_env: Literal["development", "production"] = "development"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"

    # OpenAI / LiteLLM
    openai_api_key: str = Field(..., description="OpenAI API key")
    litellm_model: str = "gpt-4o"
    litellm_embedding_model: str = "text-embedding-3-large"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "rag_documents"
    qdrant_vector_size: int = 3072  # text-embedding-3-large output dim

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "rag_bm25"

    # PostgreSQL
    database_url: str = "postgresql+asyncpg://raguser:ragpass@localhost:5432/ragdb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"
    redis_ttl_seconds: int = 3600

    # MinIO / S3
    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "rag-documents"
    s3_region: str = "us-east-1"

    # Langfuse
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = "http://localhost:4317"
    otel_service_name: str = "rag-backend"

    # Reranker
    reranker_model: str = "BAAI/bge-reranker-large"
    reranker_device: Literal["cpu", "cuda", "mps"] = "cpu"

    # Retrieval
    bm25_top_k: int = 20
    vector_top_k: int = 20
    rerank_top_k: int = 5
    rrf_k: int = 60

    # Generation
    max_context_chunks: int = 5
    max_retries_citation: int = 2

    # Evaluation thresholds
    eval_faithfulness_threshold: float = 0.85
    eval_relevance_threshold: float = 0.80

    @field_validator("log_level")
    @classmethod
    def uppercase_log_level(cls, v: str) -> str:
        return v.upper()


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance. Safe to call anywhere."""
    return Settings()  # type: ignore[call-arg]
