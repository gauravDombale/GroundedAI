-- PostgreSQL initialization script
-- Runs once on first container startup

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- trigram similarity for BM25 fallback

-- Documents table: raw document metadata
CREATE TABLE IF NOT EXISTS documents (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename    TEXT NOT NULL,
    file_type   TEXT NOT NULL,             -- pdf | markdown | html
    s3_key      TEXT NOT NULL UNIQUE,      -- object path in MinIO/S3
    file_size   BIGINT,
    sha256      TEXT NOT NULL UNIQUE,      -- deduplication
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Chunks table: processed text chunks with metadata
CREATE TABLE IF NOT EXISTS chunks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id     UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INT NOT NULL,
    text            TEXT NOT NULL,
    token_count     INT,
    page_number     INT,
    section_title   TEXT,
    qdrant_id       TEXT UNIQUE,   -- vector ID in Qdrant
    es_id           TEXT UNIQUE,   -- document ID in Elasticsearch
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_chunks_qdrant_id ON chunks(qdrant_id);

-- Query log: for observability and evaluation
CREATE TABLE IF NOT EXISTS query_log (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    query           TEXT NOT NULL,
    rewritten_query TEXT,
    retrieved_ids   TEXT[],        -- chunk IDs returned
    answer          TEXT,
    citations       TEXT[],
    latency_ms      INT,
    cache_hit       BOOLEAN DEFAULT FALSE,
    langfuse_trace  TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_query_log_created_at ON query_log(created_at DESC);
