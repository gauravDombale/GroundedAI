"""
LLM call layer using LiteLLM for provider abstraction.
Handles async completion, retries, and structured JSON output parsing.
"""
import json

import structlog
from litellm import acompletion
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import get_settings
from app.generation.prompt import PromptBundle

logger = structlog.get_logger(__name__)


class LLMResponse:
    __slots__ = ("answer", "citations", "raw_content")

    def __init__(self, answer: str, citations: list[str], raw_content: str) -> None:
        self.answer = answer
        self.citations = citations
        self.raw_content = raw_content


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
async def call_llm(prompt: PromptBundle) -> LLMResponse:
    """
    Call LiteLLM with retry logic.

    Args:
        prompt: PromptBundle containing system + user messages.

    Returns:
        LLMResponse with parsed answer and citations.

    Raises:
        ValueError: If the LLM response is not valid JSON.
    """
    settings = get_settings()

    response = await acompletion(
        model=settings.litellm_model,
        api_key=settings.openai_api_key,
        messages=[
            {"role": "system", "content": prompt.system},
            {"role": "user", "content": prompt.user},
        ],
        temperature=0.0,
        max_tokens=1024,
        response_format={"type": "json_object"},
    )

    raw_content: str = response.choices[0].message.content or ""

    try:
        parsed = json.loads(raw_content)
        answer = parsed.get("answer", "")
        citations = parsed.get("citations", [])

        if not isinstance(citations, list):
            citations = []

        return LLMResponse(
            answer=answer,
            citations=[str(c) for c in citations],
            raw_content=raw_content,
        )
    except json.JSONDecodeError as exc:
        logger.error("llm.json_parse_failed", raw=raw_content[:200], error=str(exc))
        raise ValueError(f"LLM returned non-JSON response: {raw_content[:100]}") from exc
