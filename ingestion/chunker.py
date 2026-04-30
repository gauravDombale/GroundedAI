"""
Text chunker using LlamaIndex SentenceSplitter.
Target: 300–800 tokens per chunk, 50–100 token overlap.
"""
from dataclasses import dataclass, field
from typing import Any

import structlog
from llama_index.core.node_parser import SentenceSplitter

logger = structlog.get_logger(__name__)

CHUNK_SIZE = 512        # tokens (sits within 300–800 target)
CHUNK_OVERLAP = 64      # tokens (within 50–100 target)


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    filename: str
    file_type: str
    page_number: int | None
    section_title: str | None
    token_count: int
    metadata: dict[str, Any] = field(default_factory=dict)


def chunk_document(elements: list[dict[str, Any]], document_id: str) -> list[TextChunk]:
    """
    Split document elements into fixed-size, overlapping chunks.

    Args:
        elements: List of text elements from a loader.
        document_id: UUID of the parent document (for storage linkage).

    Returns:
        List of TextChunk objects ready for embedding.
    """
    splitter = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    # Combine all elements into a single text while tracking metadata
    combined_text = "\n\n".join(e["text"] for e in elements)
    filename = elements[0]["filename"] if elements else "unknown"
    file_type = elements[0]["file_type"] if elements else "unknown"

    nodes = splitter.split_text(combined_text)

    chunks: list[TextChunk] = []
    for i, text in enumerate(nodes):
        token_count = len(text.split())  # approximate; precise count via tiktoken
        chunks.append(
            TextChunk(
                text=text,
                chunk_index=i,
                filename=filename,
                file_type=file_type,
                page_number=None,          # page mapping at element level
                section_title=None,        # section mapping at element level
                token_count=token_count,
                metadata={"document_id": document_id},
            )
        )

    logger.info(
        "chunker.done",
        document_id=document_id,
        element_count=len(elements),
        chunk_count=len(chunks),
    )
    return chunks
