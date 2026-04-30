"""
Reciprocal Rank Fusion (RRF) for hybrid BM25 + vector retrieval.

RRF score formula:  score(d) = Σ 1 / (k + rank(d))
where k is a smoothing constant (default 60, per the original paper).
"""
import asyncio
from collections import defaultdict

import structlog

from app.core.config import get_settings
from app.retrieval.bm25_retriever import RetrievedChunk, get_bm25_retriever
from app.retrieval.vector_retriever import get_vector_retriever

logger = structlog.get_logger(__name__)


def reciprocal_rank_fusion(
    ranked_lists: list[list[RetrievedChunk]],
    k: int = 60,
) -> list[RetrievedChunk]:
    """
    Merge multiple ranked lists via Reciprocal Rank Fusion.

    Args:
        ranked_lists: Each list is a ranked result set from one retriever.
        k: RRF smoothing constant (paper recommends 60).

    Returns:
        Single merged list sorted by descending RRF score.
    """
    rrf_scores: dict[str, float] = defaultdict(float)
    chunk_map: dict[str, RetrievedChunk] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            rrf_scores[chunk.chunk_id] += 1.0 / (k + rank)
            if chunk.chunk_id not in chunk_map:
                chunk_map[chunk.chunk_id] = chunk

    # Sort by descending RRF score
    merged: list[RetrievedChunk] = []
    for chunk_id, score in sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True):
        chunk = chunk_map[chunk_id]
        merged.append(
            RetrievedChunk(
                chunk_id=chunk.chunk_id,
                document_id=chunk.document_id,
                text=chunk.text,
                score=score,
                metadata={**chunk.metadata, "rrf_score": score, "source": "hybrid"},
            )
        )

    return merged


async def hybrid_retrieve(query: str, top_k: int | None = None) -> list[RetrievedChunk]:
    """
    Run BM25 and vector retrieval in parallel, then fuse with RRF.

    Args:
        query: User query.
        top_k: Final number of results after fusion (before reranking).

    Returns:
        Fused ranked list of RetrievedChunk objects.
    """
    settings = get_settings()
    k = top_k or (settings.bm25_top_k + settings.vector_top_k)

    bm25 = get_bm25_retriever()
    vector = get_vector_retriever()

    # Parallel retrieval
    bm25_results, vector_results = await asyncio.gather(
        bm25.retrieve(query),
        vector.retrieve(query),
        return_exceptions=False,
    )

    fused = reciprocal_rank_fusion(
        [bm25_results, vector_results],  # type: ignore[list-item]
        k=settings.rrf_k,
    )

    logger.info(
        "hybrid.fused",
        query=query[:80],
        bm25_count=len(bm25_results),  # type: ignore[arg-type]
        vector_count=len(vector_results),  # type: ignore[arg-type]
        fused_count=len(fused),
    )

    return fused[:k]
