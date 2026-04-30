"""
Unit tests for citation validation logic.
These tests run without any external services.
"""

from app.generation.citation_validator import (
    extract_inline_citations,
    validate_citations,
)
from app.generation.llm import LLMResponse


class TestExtractInlineCitations:
    def test_single_citation(self) -> None:
        assert extract_inline_citations("This is true [doc1].") == {"doc1"}

    def test_multiple_citations(self) -> None:
        result = extract_inline_citations("Fact [doc1] and also [doc2] and [doc3].")
        assert result == {"doc1", "doc2", "doc3"}

    def test_no_citations(self) -> None:
        assert extract_inline_citations("No citations here.") == set()

    def test_duplicate_citations(self) -> None:
        result = extract_inline_citations("[doc1] again [doc1].")
        assert result == {"doc1"}


class TestValidateCitations:
    def _response(self, answer: str, citations: list[str]) -> LLMResponse:
        return LLMResponse(answer=answer, citations=citations, raw_content="")

    def test_valid_citations(self) -> None:
        resp = self._response(
            answer="The answer is X [doc1] and Y [doc2].",
            citations=["doc1", "doc2"],
        )
        is_valid, hallucinated = validate_citations(resp, ["doc1", "doc2", "doc3"])
        assert is_valid is True
        assert hallucinated == []

    def test_hallucinated_citation_in_list(self) -> None:
        resp = self._response(
            answer="The answer [doc1].",
            citations=["doc1", "doc99"],  # doc99 is hallucinated
        )
        is_valid, hallucinated = validate_citations(resp, ["doc1", "doc2"])
        assert is_valid is False
        assert "doc99" in hallucinated

    def test_hallucinated_inline_citation(self) -> None:
        resp = self._response(
            answer="The answer [doc1] and also [doc999].",  # doc999 is hallucinated
            citations=["doc1"],
        )
        is_valid, hallucinated = validate_citations(resp, ["doc1", "doc2"])
        assert is_valid is False
        assert "doc999" in hallucinated

    def test_empty_citations_are_valid(self) -> None:
        resp = self._response(
            answer="I don't have enough information.",
            citations=[],
        )
        is_valid, hallucinated = validate_citations(resp, ["doc1", "doc2"])
        assert is_valid is True
        assert hallucinated == []
