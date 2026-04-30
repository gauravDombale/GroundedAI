"""
Vector retriever backed by Qdrant 1.17.x.
Uses OpenAI text-embedding-3-large (3072-dim) for query embedding.
"""

import structlog
from openai import AsyncOpenAI
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, ScoredPoint, VectorParams

from app.core.config import get_settings
from app.retrieval.bm25_retriever import RetrievedChunk

logger = structlog.get_logger(__name__)


class VectorRetriever:
    """Qdrant-backed dense vector retriever."""

    def __init__(self) -> None:
        settings = get_settings()
        self._qdrant = AsyncQdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port,
        )
        self._openai = AsyncOpenAI(api_key=settings.openai_api_key)
        self._collection = settings.qdrant_collection
        self._embedding_model = settings.litellm_embedding_model
        self._vector_size = settings.qdrant_vector_size

    async def ensure_collection(self) -> None:
        """Create Qdrant collection if it doesn't exist."""
        collections = await self._qdrant.get_collections()
        names = [c.name for c in collections.collections]
        if self._collection in names:
            return

        await self._qdrant.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(
                size=self._vector_size,
                distance=Distance.COSINE,
            ),
        )
        logger.info("qdrant.collection_created", collection=self._collection)

    async def embed_query(self, query: str) -> list[float]:
        """Embed query using OpenAI text-embedding-3-large."""
        response = await self._openai.embeddings.create(
            model=self._embedding_model,
            input=query,
        )
        return response.data[0].embedding

    async def retrieve(self, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        """
        Dense vector similarity search.

        Args:
            query: User query string.
            top_k: Number of results (defaults to settings.vector_top_k).

        Returns:
            List of RetrievedChunk objects ranked by cosine similarity.
        """
        settings = get_settings()
        k = top_k or settings.vector_top_k

        query_vector = await self.embed_query(query)

        results: list[ScoredPoint] = await self._qdrant.search(
            collection_name=self._collection,
            query_vector=query_vector,
            limit=k,
            with_payload=True,
        )

        chunks = [
            RetrievedChunk(
                chunk_id=str(point.id),
                document_id=point.payload.get("document_id", ""),  # type: ignore[union-attr]
                text=point.payload.get("text", ""),  # type: ignore[union-attr]
                score=point.score,
                metadata={
                    "filename": point.payload.get("filename", ""),  # type: ignore[union-attr]
                    "page_number": point.payload.get("page_number"),  # type: ignore[union-attr]
                    "section_title": point.payload.get("section_title"),  # type: ignore[union-attr]
                    "source": "vector",
                },
            )
            for point in results
        ]

        logger.debug("vector.retrieved", query=query[:80], count=len(chunks))
        return chunks

    async def close(self) -> None:
        await self._qdrant.close()


_retriever: VectorRetriever | None = None


def get_vector_retriever() -> VectorRetriever:
    global _retriever
    if _retriever is None:
        _retriever = VectorRetriever()
    return _retriever
