"""
Cross-encoder reranker using BAAI/bge-reranker-large (sentence-transformers 3.x).

Downloads the model on first use. Subsequent calls use the cached model.
Supports CPU, CUDA, and Apple MPS.
"""
from functools import lru_cache

import structlog
from sentence_transformers import CrossEncoder

from app.core.config import get_settings
from app.retrieval.bm25_retriever import RetrievedChunk

logger = structlog.get_logger(__name__)


@lru_cache(maxsize=1)
def get_reranker() -> CrossEncoder:
    """Load and cache the cross-encoder model."""
    settings = get_settings()
    logger.info("reranker.loading", model=settings.reranker_model, device=settings.reranker_device)
    model = CrossEncoder(
        settings.reranker_model,
        device=settings.reranker_device,
        max_length=512,
    )
    logger.info("reranker.loaded")
    return model


def rerank(
    query: str,
    chunks: list[RetrievedChunk],
    top_k: int | None = None,
) -> list[RetrievedChunk]:
    """
    Rerank retrieved chunks using a cross-encoder model.

    Args:
        query: Original user query.
        chunks: Candidate chunks from hybrid retrieval (typically top 40).
        top_k: Number of chunks to return (defaults to settings.rerank_top_k).

    Returns:
        Re-ranked list of RetrievedChunk with updated scores.
    """
    settings = get_settings()
    k = top_k or settings.rerank_top_k

    if not chunks:
        return []

    model = get_reranker()

    # Build (query, passage) pairs for the cross-encoder
    pairs = [(query, chunk.text) for chunk in chunks]
    scores: list[float] = model.predict(pairs, convert_to_numpy=False)  # type: ignore[assignment]

    # Attach new scores and sort
    scored = sorted(
        zip(chunks, scores),
        key=lambda x: x[1],
        reverse=True,
    )

    reranked = [
        RetrievedChunk(
            chunk_id=chunk.chunk_id,
            document_id=chunk.document_id,
            text=chunk.text,
            score=float(score),
            metadata={**chunk.metadata, "rerank_score": float(score)},
        )
        for chunk, score in scored[:k]
    ]

    logger.info(
        "reranker.done",
        input_count=len(chunks),
        output_count=len(reranked),
        top_score=reranked[0].score if reranked else None,
    )
    return reranked
