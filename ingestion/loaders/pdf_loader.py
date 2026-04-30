"""
PDF document loader using Unstructured.io.
Extracts text with page-level metadata preserved.
"""
from pathlib import Path
from typing import Any

import structlog
from unstructured.partition.pdf import partition_pdf

logger = structlog.get_logger(__name__)


def load_pdf(file_path: Path) -> list[dict[str, Any]]:
    """
    Load a PDF file and extract text elements.

    Args:
        file_path: Path to the PDF file.

    Returns:
        List of element dicts with keys: text, page_number, section_title, filename.
    """
    logger.info("loader.pdf.start", path=str(file_path))

    elements = partition_pdf(
        filename=str(file_path),
        strategy="hi_res",
        infer_table_structure=True,
        include_page_breaks=True,
    )

    docs: list[dict[str, Any]] = []
    for el in elements:
        text = str(el).strip()
        if not text:
            continue

        metadata = el.metadata if hasattr(el, "metadata") else {}
        docs.append(
            {
                "text": text,
                "filename": file_path.name,
                "file_type": "pdf",
                "page_number": getattr(metadata, "page_number", None),
                "section_title": getattr(metadata, "section", None),
            }
        )

    logger.info("loader.pdf.done", path=str(file_path), element_count=len(docs))
    return docs
