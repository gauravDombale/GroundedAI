"""
Prompt template for citation-grounded answer generation.

The prompt instructs the LLM to:
  1. Answer only from the provided context.
  2. Cite source IDs inline using [SOURCE_ID] notation.
  3. Return structured JSON with `answer` and `citations` fields.
"""
from dataclasses import dataclass

from app.retrieval.bm25_retriever import RetrievedChunk

SYSTEM_PROMPT = """\
You are a precise document Q&A assistant.

RULES (non-negotiable):
1. Answer ONLY using the information in the context blocks below.
2. If the answer is not in the context, say: "I don't have enough information to answer this question."
3. Cite your sources inline using the format [SOURCE_ID] immediately after each claim.
4. You MUST use at least one citation in every non-trivial answer.
5. Do NOT fabricate information, URLs, or statistics.

OUTPUT FORMAT — respond with ONLY valid JSON, no markdown fences:
{
  "answer": "Your answer with inline citations like this [doc1] and this [doc2].",
  "citations": ["doc1", "doc2"]
}
"""


@dataclass
class PromptBundle:
    system: str
    user: str
    source_ids: list[str]


def build_prompt(query: str, chunks: list[RetrievedChunk]) -> PromptBundle:
    """
    Build a prompt bundle from the query and retrieved chunks.

    Args:
        query: The user's question.
        chunks: Top-k reranked chunks to use as context.

    Returns:
        PromptBundle with system and user messages + list of valid source IDs.
    """
    source_ids: list[str] = []
    context_blocks: list[str] = []

    for i, chunk in enumerate(chunks):
        source_id = f"doc{i + 1}"
        source_ids.append(source_id)

        filename = chunk.metadata.get("filename", "unknown")
        page = chunk.metadata.get("page_number")
        section = chunk.metadata.get("section_title", "")

        location = f"{filename}"
        if page:
            location += f", page {page}"
        if section:
            location += f", section: {section}"

        context_blocks.append(
            f"[{source_id}] ({location})\n{chunk.text.strip()}"
        )

    context_str = "\n\n---\n\n".join(context_blocks)
    user_message = f"CONTEXT:\n\n{context_str}\n\nQUESTION: {query}"

    return PromptBundle(
        system=SYSTEM_PROMPT,
        user=user_message,
        source_ids=source_ids,
    )
