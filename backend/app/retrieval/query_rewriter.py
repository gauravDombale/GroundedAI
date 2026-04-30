"""
LLM-based query rewriter.
Expands/clarifies the user query before retrieval to improve recall.
"""
import structlog
from openai import AsyncOpenAI

from app.core.config import get_settings

logger = structlog.get_logger(__name__)

_REWRITE_SYSTEM = """\
You are a search query optimizer for a document retrieval system.
Your job is to rewrite a user query to maximize recall from a hybrid BM25 + vector search.

Rules:
- Expand abbreviations and acronyms.
- Add relevant synonyms when useful.
- Keep the rewritten query concise (≤ 30 words).
- Return ONLY the rewritten query — no explanation, no quotes.
"""


async def rewrite_query(query: str) -> str:
    """
    Rewrite query for better retrieval coverage.

    Returns the rewritten query string, or the original if rewriting fails.
    """
    settings = get_settings()

    try:
        client = AsyncOpenAI(api_key=settings.openai_api_key)
        response = await client.chat.completions.create(
            model=settings.litellm_model,
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": query},
            ],
            temperature=0.0,
            max_tokens=60,
        )
        rewritten = (response.choices[0].message.content or query).strip()
        logger.info("query.rewritten", original=query[:80], rewritten=rewritten[:80])
        return rewritten
    except Exception as exc:
        logger.warning("query.rewrite_failed", error=str(exc))
        return query
