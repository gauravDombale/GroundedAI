"""Unit tests for the prompt builder."""

from app.generation.prompt import PromptBundle, build_prompt
from app.retrieval.bm25_retriever import RetrievedChunk


def make_chunk(chunk_id: str, text: str, filename: str = "test.pdf") -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id="doc-1",
        text=text,
        score=0.9,
        metadata={"filename": filename, "page_number": 1, "source": "hybrid"},
    )


class TestBuildPrompt:
    def test_returns_prompt_bundle(self) -> None:
        chunks = [make_chunk("c1", "RAG combines retrieval and generation.")]
        result = build_prompt("What is RAG?", chunks)
        assert isinstance(result, PromptBundle)

    def test_source_ids_sequential(self) -> None:
        chunks = [make_chunk(f"c{i}", f"Text {i}") for i in range(3)]
        result = build_prompt("question", chunks)
        assert result.source_ids == ["doc1", "doc2", "doc3"]

    def test_context_includes_chunk_text(self) -> None:
        chunks = [make_chunk("c1", "Important information about AI.")]
        result = build_prompt("Tell me about AI.", chunks)
        assert "Important information about AI." in result.user

    def test_query_in_user_message(self) -> None:
        chunks = [make_chunk("c1", "Some text.")]
        result = build_prompt("What is machine learning?", chunks)
        assert "What is machine learning?" in result.user

    def test_empty_chunks(self) -> None:
        result = build_prompt("question", [])
        assert result.source_ids == []
        assert "QUESTION: question" in result.user
