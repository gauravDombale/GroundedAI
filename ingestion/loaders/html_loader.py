"""
HTML document loader using Unstructured.
Strips boilerplate and extracts semantic content.
"""
from pathlib import Path
from typing import Any

import structlog
from unstructured.partition.html import partition_html

logger = structlog.get_logger(__name__)


def load_html(file_path: Path) -> list[dict[str, Any]]:
    """
    Load an HTML file and extract clean text elements.

    Args:
        file_path: Path to the .html file.

    Returns:
        List of element dicts with text + metadata.
    """
    logger.info("loader.html.start", path=str(file_path))
    elements = partition_html(filename=str(file_path))

    docs: list[dict[str, Any]] = []
    current_section: str | None = None

    for el in elements:
        el_type = type(el).__name__
        text = str(el).strip()
        if not text or len(text) < 20:  # skip nav links / single-word elements
            continue

        if el_type == "Title":
            current_section = text

        docs.append(
            {
                "text": text,
                "filename": file_path.name,
                "file_type": "html",
                "page_number": None,
                "section_title": current_section,
            }
        )

    logger.info("loader.html.done", path=str(file_path), element_count=len(docs))
    return docs
