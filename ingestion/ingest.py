"""
CLI ingestion entrypoint: python ingest.py <folder>

Ingests all PDF, Markdown, and HTML files from the given folder into:
  - MinIO/S3 (raw files)
  - PostgreSQL (document + chunk metadata)
  - Qdrant (chunk embeddings)
  - Elasticsearch (BM25 index)
"""
import asyncio
import os
import sys
from pathlib import Path

import asyncpg
import click
import structlog
from dotenv import load_dotenv
from elasticsearch import AsyncElasticsearch
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from chunker import chunk_document
from embedder import embed_chunks
from loaders.html_loader import load_html
from loaders.markdown_loader import load_markdown
from loaders.pdf_loader import load_pdf
from storage import (
    insert_chunks,
    insert_document,
    sha256_file,
    upload_to_s3,
    upsert_to_elasticsearch,
    upsert_to_qdrant,
)

load_dotenv()
logger = structlog.get_logger(__name__)
console = Console()

SUPPORTED_EXTENSIONS = {".pdf", ".md", ".markdown", ".html", ".htm"}


def load_file(file_path: Path) -> list[dict]:
    """Dispatch to the correct loader based on file extension."""
    ext = file_path.suffix.lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in {".md", ".markdown"}:
        return load_markdown(file_path)
    elif ext in {".html", ".htm"}:
        return load_html(file_path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


async def ingest_file(
    file_path: Path,
    pg_pool: asyncpg.Pool,
    qdrant: AsyncQdrantClient,
    es_client: AsyncElasticsearch,
    settings: dict,
) -> None:
    """Full ingestion pipeline for a single file."""
    logger.info("ingest.file.start", path=str(file_path))

    # 1. Upload to S3/MinIO
    s3_key = upload_to_s3(
        file_path,
        endpoint_url=settings["S3_ENDPOINT_URL"],
        access_key=settings["S3_ACCESS_KEY"],
        secret_key=settings["S3_SECRET_KEY"],
        bucket=settings["S3_BUCKET"],
        region=settings["S3_REGION"],
    )

    # 2. Insert document record (with dedup)
    sha256 = sha256_file(file_path)
    doc_id = await insert_document(
        pg_pool,
        filename=file_path.name,
        file_type=file_path.suffix.lstrip("."),
        s3_key=s3_key,
        file_size=file_path.stat().st_size,
        sha256=sha256,
    )

    # 3. Load + chunk
    elements = load_file(file_path)
    if not elements:
        logger.warning("ingest.file.empty", path=str(file_path))
        return

    chunks = chunk_document(elements, document_id=doc_id)

    # 4. Embed
    embedded = await embed_chunks(chunks, api_key=settings["OPENAI_API_KEY"])

    # 5. Store chunk metadata in PostgreSQL
    chunk_ids = await insert_chunks(pg_pool, doc_id, embedded)

    # 6. Upsert vectors to Qdrant
    await upsert_to_qdrant(qdrant, settings["QDRANT_COLLECTION"], chunk_ids, embedded)

    # 7. Upsert chunks to Elasticsearch (BM25)
    await upsert_to_elasticsearch(es_client, settings["ELASTICSEARCH_INDEX"], chunk_ids, embedded)

    logger.info(
        "ingest.file.done",
        path=str(file_path),
        doc_id=doc_id,
        chunk_count=len(chunks),
    )


async def run_ingestion(folder: Path, settings: dict) -> None:
    files = [f for f in folder.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS]
    if not files:
        console.print(f"[red]No supported files found in {folder}[/red]")
        sys.exit(1)

    console.print(f"[green]Found {len(files)} file(s) to ingest[/green]")

    # Setup connections
    pg_pool = await asyncpg.create_pool(settings["DATABASE_URL"])
    qdrant = AsyncQdrantClient(
        host=settings["QDRANT_HOST"],
        port=int(settings["QDRANT_PORT"]),
    )
    es_client = AsyncElasticsearch(settings["ELASTICSEARCH_URL"])

    # Ensure Qdrant collection exists
    collections = await qdrant.get_collections()
    if settings["QDRANT_COLLECTION"] not in [c.name for c in collections.collections]:
        await qdrant.create_collection(
            collection_name=settings["QDRANT_COLLECTION"],
            vectors_config=VectorParams(size=3072, distance=Distance.COSINE),
        )

    # Ensure Elasticsearch index exists
    if not await es_client.indices.exists(index=settings["ELASTICSEARCH_INDEX"]):
        await es_client.indices.create(
            index=settings["ELASTICSEARCH_INDEX"],
            body={
                "settings": {"similarity": {"default": {"type": "BM25"}}},
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "document_id": {"type": "keyword"},
                        "text": {"type": "text", "analyzer": "english"},
                        "filename": {"type": "keyword"},
                        "page_number": {"type": "integer"},
                        "section_title": {"type": "text"},
                    }
                },
            },
        )

    errors: list[str] = []
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Ingesting...", total=len(files))
        for file_path in files:
            progress.update(task, description=f"[cyan]{file_path.name}[/cyan]")
            try:
                await ingest_file(file_path, pg_pool, qdrant, es_client, settings)
            except Exception as exc:
                logger.error("ingest.file.error", path=str(file_path), error=str(exc))
                errors.append(f"{file_path.name}: {exc}")
            progress.advance(task)

    await pg_pool.close()
    await qdrant.close()
    await es_client.close()

    if errors:
        console.print(f"\n[red]Completed with {len(errors)} error(s):[/red]")
        for err in errors:
            console.print(f"  [red]✗[/red] {err}")
        sys.exit(1)
    else:
        console.print(f"\n[green]✓ Successfully ingested {len(files)} file(s)[/green]")


@click.command()
@click.argument("folder", type=click.Path(exists=True, file_okay=False, path_type=Path))
def main(folder: Path) -> None:
    """
    Ingest all PDF, Markdown, and HTML documents from FOLDER.

    Example:
        python ingest.py ./sample_docs
    """
    settings = {
        "OPENAI_API_KEY": os.environ["OPENAI_API_KEY"],
        "DATABASE_URL": os.environ.get("DATABASE_URL", "postgresql://raguser:ragpass@localhost:5432/ragdb"),
        "QDRANT_HOST": os.environ.get("QDRANT_HOST", "localhost"),
        "QDRANT_PORT": os.environ.get("QDRANT_PORT", "6333"),
        "QDRANT_COLLECTION": os.environ.get("QDRANT_COLLECTION", "rag_documents"),
        "ELASTICSEARCH_URL": os.environ.get("ELASTICSEARCH_URL", "http://localhost:9200"),
        "ELASTICSEARCH_INDEX": os.environ.get("ELASTICSEARCH_INDEX", "rag_bm25"),
        "S3_ENDPOINT_URL": os.environ.get("S3_ENDPOINT_URL", "http://localhost:9000"),
        "S3_ACCESS_KEY": os.environ.get("S3_ACCESS_KEY", "minioadmin"),
        "S3_SECRET_KEY": os.environ.get("S3_SECRET_KEY", "minioadmin"),
        "S3_BUCKET": os.environ.get("S3_BUCKET", "rag-documents"),
        "S3_REGION": os.environ.get("S3_REGION", "us-east-1"),
    }

    asyncio.run(run_ingestion(folder, settings))


if __name__ == "__main__":
    main()
