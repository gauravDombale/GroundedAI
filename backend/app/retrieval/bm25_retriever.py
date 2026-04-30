"""
BM25 retriever backed by Elasticsearch 8.x.
Uses the async elasticsearch client for non-blocking I/O.
"""
from dataclasses import dataclass, field
from typing import Any

import structlog
from elasticsearch import AsyncElasticsearch

from app.core.config import get_settings

logger = structlog.get_logger(__name__)


@dataclass
class RetrievedChunk:
    chunk_id: str
    document_id: str
    text: str
    score: float
    metadata: dict[str, Any] = field(default_factory=dict)


class BM25Retriever:
    """Elasticsearch-backed BM25 retriever."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = AsyncElasticsearch(settings.elasticsearch_url)
        self._index = settings.elasticsearch_index

    async def ensure_index(self) -> None:
        """Create ES index with BM25 mappings if it doesn't exist."""
        exists = await self._client.indices.exists(index=self._index)
        if exists:
            return

        await self._client.indices.create(
            index=self._index,
            body={
                "settings": {
                    "number_of_shards": 1,
                    "number_of_replicas": 0,
                    "similarity": {"default": {"type": "BM25"}},
                },
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "text": {"type": "text", "analyzer": "english"},
                        "filename": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "section_title": {"type": "text"},
                    }
                },
            },
        )
        logger.info("bm25.index_created", index=self._index)

    async def index_chunk(self, chunk: dict[str, Any]) -> None:
        """Index a single chunk document."""
        await self._client.index(
            index=self._index,
            id=chunk["chunk_id"],
            document=chunk,
        )

    async def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """
        Full-text BM25 search.

        Args:
            query: The user search query.
            top_k: Number of results to return (defaults to settings.bm25_top_k).

        Returns:
            List of RetrievedChunk objects ranked by BM25 score.
        """
        settings = get_settings()
        k = top_k or settings.bm25_top_k

        response = await self._client.search(
            index=self._index,
            body={
                "query": {
                    "multi_match": {
                        "query": query,
                        "fields": ["text^3", "section_title^2", "filename"],
                        "type": "best_fields",
                        "fuzziness": "AUTO",
                    }
                },
                "size": k,
            },
        )

        hits = response["hits"]["hits"]
        results = [
            RetrievedChunk(
                chunk_id=hit["_source"]["chunk_id"],
                document_id=hit["_source"]["document_id"],
                text=hit["_source"]["text"],
                score=hit["_score"],
                metadata={
                    "filename": hit["_source"].get("filename", ""),
                    "page_number": hit["_source"].get("page_number"),
                    "section_title": hit["_source"].get("section_title"),
                    "source": "bm25",
                },
            )
            for hit in hits
        ]

        logger.debug("bm25.retrieved", query=query[:80], count=len(results))
        return results

    async def close(self) -> None:
        await self._client.close()


# Module-level singleton
_retriever: BM25Retriever | None = None


def get_bm25_retriever() -> BM25Retriever:
    global _retriever
    if _retriever is None:
        _retriever = BM25Retriever()
    return _retriever
