"""
/api/v1/ask — Full RAG pipeline endpoint.
Retrieval → Reranking → Generation → Citation Enforcement → Response.
"""
import time

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.cache.redis_cache import cached_ask, cache_ask_result
from app.generation.citation_validator import enforce_citations
from app.generation.llm import call_llm
from app.generation.prompt import build_prompt
from app.reranking.cross_encoder import rerank
from app.retrieval.fusion import hybrid_retrieve
from app.retrieval.query_rewriter import rewrite_query

logger = structlog.get_logger(__name__)
router = APIRouter()


class AskRequest(BaseModel):
    query: str = Field(..., min_length=3, max_length=1000, description="User question")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of context chunks")
    rewrite: bool = Field(default=True, description="Enable query rewriting")


class AskResponse(BaseModel):
    query: str
    rewritten_query: str
    answer: str
    citations: list[str]
    latency_ms: int
    cache_hit: bool = False


@router.post("/ask", response_model=AskResponse, summary="Ask a question")
async def ask(request: AskRequest) -> AskResponse:
    """
    Full RAG pipeline:
    1. Query rewriting
    2. Hybrid BM25 + vector retrieval
    3. Cross-encoder reranking
    4. Citation-grounded LLM answer generation
    5. Citation hallucination enforcement

    Returns a structured answer with verified source citations.
    """
    start = time.perf_counter()

    # ── Cache check ───────────────────────────────────────────────────────────
    cached = await cached_ask(request.query)
    if cached:
        logger.info("ask.cache_hit", query=request.query[:80])
        return AskResponse(cache_hit=True, latency_ms=0, **cached)

    try:
        # ── Step 1: Query rewrite ─────────────────────────────────────────────
        rewritten = await rewrite_query(request.query) if request.rewrite else request.query

        # ── Step 2: Hybrid retrieval ──────────────────────────────────────────
        raw_chunks = await hybrid_retrieve(rewritten)
        if not raw_chunks:
            return AskResponse(
                query=request.query,
                rewritten_query=rewritten,
                answer="I don't have enough information to answer this question.",
                citations=[],
                latency_ms=int((time.perf_counter() - start) * 1000),
            )

        # ── Step 3: Reranking ─────────────────────────────────────────────────
        reranked = rerank(rewritten, raw_chunks, top_k=request.top_k)

        # ── Step 4: Build prompt ──────────────────────────────────────────────
        prompt = build_prompt(request.query, reranked)

        # ── Step 5: LLM generation ────────────────────────────────────────────
        llm_response = await call_llm(prompt)

        # ── Step 6: Citation enforcement ──────────────────────────────────────
        validated = await enforce_citations(prompt, llm_response)

    except ValueError as exc:
        logger.error("ask.citation_enforcement_failed", error=str(exc))
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.error("ask.pipeline_error", error=str(exc), query=request.query[:80])
        raise HTTPException(status_code=500, detail=f"Pipeline error: {exc}") from exc

    latency_ms = int((time.perf_counter() - start) * 1000)
    logger.info(
        "ask.ok",
        query=request.query[:80],
        citations=validated.citations,
        latency_ms=latency_ms,
    )

    result = AskResponse(
        query=request.query,
        rewritten_query=rewritten,
        answer=validated.answer,
        citations=validated.citations,
        latency_ms=latency_ms,
    )

    # ── Cache result ──────────────────────────────────────────────────────────
    await cache_ask_result(request.query, result.model_dump(exclude={"cache_hit", "latency_ms"}))

    return result
