"""
Markdown document loader.
Uses Unstructured for section-aware parsing.
"""
from pathlib import Path
from typing import Any

import structlog
from unstructured.partition.md import partition_md

logger = structlog.get_logger(__name__)


def load_markdown(file_path: Path) -> list[dict[str, Any]]:
    """
    Load a Markdown file and extract text elements with heading context.

    Args:
        file_path: Path to the .md file.

    Returns:
        List of element dicts with text + metadata.
    """
    logger.info("loader.md.start", path=str(file_path))
    elements = partition_md(filename=str(file_path))

    docs: list[dict[str, Any]] = []
    current_section: str | None = None

    for el in elements:
        el_type = type(el).__name__
        text = str(el).strip()
        if not text:
            continue

        if el_type == "Title":
            current_section = text

        docs.append(
            {
                "text": text,
                "filename": file_path.name,
                "file_type": "markdown",
                "page_number": None,
                "section_title": current_section,
            }
        )

    logger.info("loader.md.done", path=str(file_path), element_count=len(docs))
    return docs
