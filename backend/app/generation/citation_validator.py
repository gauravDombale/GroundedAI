"""
Citation enforcement layer.

After the LLM generates a response, this module:
1. Verifies every citation exists in the valid source ID set.
2. Verifies every citation is referenced in the answer text.
3. If validation fails, either regenerates (up to max_retries) or raises.
"""
import re

import structlog

from app.core.config import get_settings
from app.generation.llm import LLMResponse
from app.generation.prompt import PromptBundle

logger = structlog.get_logger(__name__)

# Matches [doc1], [doc2], etc.
CITATION_PATTERN = re.compile(r"\[(doc\d+)\]")


def extract_inline_citations(answer: str) -> set[str]:
    """Extract all [docN] references from the answer text."""
    return set(CITATION_PATTERN.findall(answer))


def validate_citations(
    response: LLMResponse,
    valid_source_ids: list[str],
) -> tuple[bool, list[str]]:
    """
    Validate that:
    - All citations in response.citations exist in valid_source_ids.
    - All citations in response.citations appear inline in the answer.
    - No inline citations in the answer are absent from valid_source_ids (hallucination).

    Returns:
        (is_valid, list_of_hallucinated_ids)
    """
    valid_set = set(valid_source_ids)
    listed_citations = set(response.citations)
    inline_citations = extract_inline_citations(response.answer)

    # Citations not in the retrieved context → hallucination
    hallucinated = (listed_citations | inline_citations) - valid_set

    if hallucinated:
        logger.warning(
            "citation.hallucination_detected",
            hallucinated=sorted(hallucinated),
            valid=valid_source_ids,
        )
        return False, sorted(hallucinated)

    return True, []


async def enforce_citations(
    prompt: PromptBundle,
    initial_response: LLMResponse,
) -> LLMResponse:
    """
    Enforce citation correctness, regenerating if hallucinations are found.

    Args:
        prompt: The original prompt bundle.
        initial_response: First LLM response to validate.

    Returns:
        A validated LLMResponse with no hallucinated citations.

    Raises:
        ValueError: If citations cannot be corrected within max_retries.
    """
    from app.generation.llm import call_llm  # avoid circular import

    settings = get_settings()
    response = initial_response

    for attempt in range(settings.max_retries_citation + 1):
        is_valid, hallucinated = validate_citations(response, prompt.source_ids)

        if is_valid:
            logger.info(
                "citation.validated",
                attempt=attempt,
                citations=response.citations,
            )
            return response

        if attempt >= settings.max_retries_citation:
            raise ValueError(
                f"Hallucinated citations after {attempt + 1} attempts: {hallucinated}"
            )

        # Augment prompt with correction instruction
        correction_note = (
            f"\n\nIMPORTANT CORRECTION: The following citation IDs do NOT exist in the "
            f"context and must NOT be used: {hallucinated}. "
            f"Valid citation IDs are: {prompt.source_ids}. "
            f"Rewrite your answer using only valid citations."
        )
        corrected_prompt = PromptBundle(
            system=prompt.system,
            user=prompt.user + correction_note,
            source_ids=prompt.source_ids,
        )
        logger.info("citation.regenerating", attempt=attempt + 1, hallucinated=hallucinated)
        response = await call_llm(corrected_prompt)

    # Should not reach here
    raise ValueError("Citation enforcement loop exited unexpectedly")
