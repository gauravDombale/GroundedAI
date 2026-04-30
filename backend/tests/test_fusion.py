"""Unit tests for RRF fusion logic."""
import pytest

from app.retrieval.bm25_retriever import RetrievedChunk
from app.retrieval.fusion import reciprocal_rank_fusion


def make_chunk(chunk_id: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        text=f"Text for {chunk_id}",
        score=score,
    )


class TestReciprocalRankFusion:
    def test_single_list_preserves_order(self) -> None:
        chunks = [make_chunk(f"c{i}") for i in range(5)]
        result = reciprocal_rank_fusion([chunks])
        assert [r.chunk_id for r in result] == [f"c{i}" for i in range(5)]

    def test_overlapping_chunks_get_boosted(self) -> None:
        # c1 appears in both lists → should score higher than c2 (only in list1)
        list1 = [make_chunk("c1"), make_chunk("c2")]
        list2 = [make_chunk("c1"), make_chunk("c3")]
        result = reciprocal_rank_fusion([list1, list2])
        # c1 appears in rank 1 of both → highest RRF score
        assert result[0].chunk_id == "c1"

    def test_empty_lists(self) -> None:
        assert reciprocal_rank_fusion([[], []]) == []

    def test_deduplication(self) -> None:
        list1 = [make_chunk("c1"), make_chunk("c2")]
        list2 = [make_chunk("c1"), make_chunk("c2")]
        result = reciprocal_rank_fusion([list1, list2])
        chunk_ids = [r.chunk_id for r in result]
        assert len(chunk_ids) == len(set(chunk_ids))

    def test_rrf_score_attached(self) -> None:
        chunks = [make_chunk("c1"), make_chunk("c2")]
        result = reciprocal_rank_fusion([chunks])
        for r in result:
            assert "rrf_score" in r.metadata
            assert r.metadata["rrf_score"] > 0
