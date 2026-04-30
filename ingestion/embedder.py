"""
Embedder using OpenAI text-embedding-3-large (3072-dim).
Batches requests to stay within API rate limits.
"""
import asyncio
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from chunker import TextChunk

logger = structlog.get_logger(__name__)

EMBEDDING_MODEL = "text-embedding-3-large"
BATCH_SIZE = 16   # OpenAI recommends ≤ 2048 texts per call; 16 is safe for long chunks


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10), reraise=True)
async def _embed_batch(client: AsyncOpenAI, texts: list[str]) -> list[list[float]]:
    """Embed a single batch of texts."""
    response = await client.embeddings.create(
        model=EMBEDDING_MODEL,
        input=texts,
    )
    return [item.embedding for item in response.data]


async def embed_chunks(
    chunks: list[TextChunk],
    api_key: str,
) -> list[dict[str, Any]]:
    """
    Embed all chunks and return list of dicts ready for Qdrant upsert.

    Args:
        chunks: TextChunk list from the chunker.
        api_key: OpenAI API key.

    Returns:
        List of dicts with keys: text, embedding, metadata.
    """
    client = AsyncOpenAI(api_key=api_key)
    texts = [c.text for c in chunks]
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        embeddings = await _embed_batch(client, batch)
        all_embeddings.extend(embeddings)
        logger.debug("embedder.batch", start=i, end=i + len(batch), total=len(texts))
        await asyncio.sleep(0.2)  # gentle rate limiting

    results: list[dict[str, Any]] = []
    for chunk, embedding in zip(chunks, all_embeddings):
        results.append(
            {
                "text": chunk.text,
                "embedding": embedding,
                "chunk_index": chunk.chunk_index,
                "filename": chunk.filename,
                "file_type": chunk.file_type,
                "page_number": chunk.page_number,
                "section_title": chunk.section_title,
                "token_count": chunk.token_count,
                "document_id": chunk.metadata.get("document_id", ""),
            }
        )

    logger.info("embedder.done", chunk_count=len(results))
    return results
