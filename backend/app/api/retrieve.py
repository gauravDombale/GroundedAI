"""
/api/v1/retrieve — Hybrid BM25 + vector retrieval endpoint.
"""
import time

import structlog
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.reranking.cross_encoder import rerank
from app.retrieval.fusion import hybrid_retrieve
from app.retrieval.query_rewriter import rewrite_query

logger = structlog.get_logger(__name__)
router = APIRouter()


class ChunkResult(BaseModel):
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    query: str
    rewritten_query: str
    results: list[ChunkResult]
    latency_ms: int


@router.get("/retrieve", response_model=RetrieveResponse, summary="Hybrid retrieval")
async def retrieve(
    q: str = Query(..., min_length=3, description="User query"),
    top_k: int = Query(default=5, ge=1, le=50, description="Number of results"),
    rewrite: bool = Query(default=True, description="Enable query rewriting"),
) -> RetrieveResponse:
    """
    Execute hybrid BM25 + vector retrieval with RRF fusion and cross-encoder reranking.

    Returns the top-k most relevant chunks for the given query.
    """
    start = time.perf_counter()

    try:
        rewritten = await rewrite_query(q) if rewrite else q
        raw_chunks = await hybrid_retrieve(rewritten)
        reranked = rerank(rewritten, raw_chunks, top_k=top_k)
    except Exception as exc:
        logger.error("retrieve.error", query=q[:80], error=str(exc))
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {exc}") from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info("retrieve.ok", query=q[:80], count=len(reranked), latency_ms=latency_ms)

    return RetrieveResponse(
        query=q,
        rewritten_query=rewritten,
        results=[
            ChunkResult(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                text=c.text,
                score=c.score,
                metadata=c.metadata,
            )
            for c in reranked
        ],
        latency_ms=latency_ms,
    )
