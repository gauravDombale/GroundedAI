"""
Storage layer for the ingestion pipeline.
Writes to Qdrant (vectors), PostgreSQL (metadata), and MinIO/S3 (raw files).
"""
import hashlib
import uuid
from pathlib import Path
from typing import Any

import asyncpg
import boto3
import structlog
from botocore.exceptions import ClientError
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import PointStruct

logger = structlog.get_logger(__name__)


# ─── MinIO / S3 ───────────────────────────────────────────────────────────────

def upload_to_s3(
    file_path: Path,
    endpoint_url: str,
    access_key: str,
    secret_key: str,
    bucket: str,
    region: str,
) -> str:
    """Upload a file to MinIO/S3 and return the S3 key."""
    s3 = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
    )

    # Ensure bucket exists
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError:
        s3.create_bucket(Bucket=bucket)
        logger.info("s3.bucket_created", bucket=bucket)

    s3_key = f"documents/{file_path.name}"
    s3.upload_file(str(file_path), bucket, s3_key)
    logger.info("s3.uploaded", key=s3_key, size=file_path.stat().st_size)
    return s3_key


def sha256_file(file_path: Path) -> str:
    """Compute SHA-256 hash of a file for deduplication."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for block in iter(lambda: f.read(65536), b""):
            h.update(block)
    return h.hexdigest()


# ─── PostgreSQL ───────────────────────────────────────────────────────────────

async def insert_document(
    pool: asyncpg.Pool,
    filename: str,
    file_type: str,
    s3_key: str,
    file_size: int,
    sha256: str,
) -> str:
    """Insert a document record and return its UUID."""
    doc_id = str(uuid.uuid4())
    await pool.execute(
        """
        INSERT INTO documents (id, filename, file_type, s3_key, file_size, sha256)
        VALUES ($1, $2, $3, $4, $5, $6)
        ON CONFLICT (sha256) DO NOTHING
        """,
        doc_id, filename, file_type, s3_key, file_size, sha256,
    )
    logger.info("postgres.document_inserted", doc_id=doc_id, filename=filename)
    return doc_id


async def insert_chunks(
    pool: asyncpg.Pool,
    document_id: str,
    embedded_chunks: list[dict[str, Any]],
) -> list[str]:
    """Insert chunk metadata into PostgreSQL. Returns list of chunk UUIDs."""
    chunk_ids: list[str] = []
    for i, chunk in enumerate(embedded_chunks):
        chunk_id = str(uuid.uuid4())
        chunk_ids.append(chunk_id)
        await pool.execute(
            """
            INSERT INTO chunks
                (id, document_id, chunk_index, text, token_count, page_number, section_title)
            VALUES ($1, $2, $3, $4, $5, $6, $7)
            """,
            chunk_id,
            document_id,
            chunk["chunk_index"],
            chunk["text"],
            chunk["token_count"],
            chunk.get("page_number"),
            chunk.get("section_title"),
        )
    logger.info("postgres.chunks_inserted", document_id=document_id, count=len(chunk_ids))
    return chunk_ids


# ─── Qdrant ───────────────────────────────────────────────────────────────────

async def upsert_to_qdrant(
    client: AsyncQdrantClient,
    collection: str,
    chunk_ids: list[str],
    embedded_chunks: list[dict[str, Any]],
) -> None:
    """Upsert embedded chunk vectors into Qdrant."""
    points = [
        PointStruct(
            id=chunk_id,
            vector=chunk["embedding"],
            payload={
                "chunk_id": chunk_id,
                "document_id": chunk["document_id"],
                "text": chunk["text"],
                "filename": chunk["filename"],
                "page_number": chunk.get("page_number"),
                "section_title": chunk.get("section_title"),
            },
        )
        for chunk_id, chunk in zip(chunk_ids, embedded_chunks)
    ]

    await client.upsert(collection_name=collection, points=points)
    logger.info("qdrant.upserted", collection=collection, count=len(points))
