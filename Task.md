# TASK.md — Production RAG System

## Objective

Build a production-grade "Ask My Docs" system with:

* Hybrid retrieval (BM25 + vector search)
* Cross-encoder reranking
* Citation-grounded responses
* CI-gated evaluation pipeline

---

## Tech Stack

### Backend

* Python
* FastAPI
* Uvicorn (ASGI server)
* asyncio

### LLM + Orchestration

* OpenAI API or LiteLLM (provider abstraction)
* LlamaIndex (primary RAG orchestration)

### Retrieval Layer

* BM25: Elasticsearch or OpenSearch
* Vector DB: Qdrant

### Embeddings

* OpenAI: text-embedding-3-large
* OR HuggingFace: BGE-large / Instructor-xl

### Reranking

* Cross-encoder:

  * BAAI/bge-reranker-large
  * OR Cohere Rerank API

### Document Processing

* Unstructured.io
* Apache Tika (fallback)

### Storage

* PostgreSQL (metadata)
* Redis (cache)
* S3 / MinIO (document storage)

### Evaluation

* RAGAS or DeepEval
* JSONL datasets

### Observability

* Langfuse (tracing)
* OpenTelemetry (logs)
* Prometheus + Grafana (metrics)

### CI/CD

* GitHub Actions

### Optional Frontend

* Next.js
* TailwindCSS

---

## Phase 0: Project Setup

### Tasks

* Initialize monorepo:

  * `/backend`
  * `/ingestion`
  * `/evaluation`
  * `/infra`
* Setup Python project (poetry or uv)
* Add pre-commit hooks (black, ruff, mypy)

### Deliverables

* Working FastAPI app with `/health` endpoint

---

## Phase 1: Document Ingestion Pipeline

### Tasks

* Implement document loaders:

  * PDF
  * Markdown
  * HTML
* Normalize text
* Implement chunking:

  * Target: 300–800 tokens
  * Overlap: 50–100 tokens
* Generate embeddings
* Store:

  * Text + metadata → PostgreSQL
  * Embeddings → Qdrant
  * Raw docs → S3/MinIO

### Deliverables

* CLI: `python ingest.py <folder>`
* Successfully indexed documents

---

## Phase 2: Hybrid Retrieval

### Tasks

* Setup BM25 index (Elasticsearch/OpenSearch)
* Index all chunks
* Implement:

  * BM25 retriever
  * Vector retriever
* Implement fusion:

  * Reciprocal Rank Fusion (RRF)

### Deliverables

* API: `/retrieve`
* Returns merged top-k results

---

## Phase 3: Reranking Layer

### Tasks

* Integrate cross-encoder:

  * bge-reranker-large
* Re-rank top 50 → top 5–10

### Deliverables

* Improved retrieval relevance
* Benchmarked improvement over baseline

---

## Phase 4: Answer Generation

### Tasks

* Design prompt template:

  * Must include:

    * Context
    * Source IDs
* Enforce:

  * "Answer ONLY from context"
  * "Cite sources inline"

### Output Format

```json
{
  "answer": "...",
  "citations": ["doc1", "doc2"]
}
```

### Deliverables

* `/ask` endpoint
* Deterministic citation behavior

---

## Phase 5: Citation Enforcement

### Tasks

* Post-process LLM output:

  * Validate citations exist in retrieved docs
* Reject / regenerate if hallucinated

### Deliverables

* Zero hallucinated citations in test set

---

## Phase 6: Evaluation Pipeline

### Tasks

* Create evaluation dataset:

  * question
  * ground_truth
  * contexts
* Implement metrics:

  * faithfulness
  * answer relevance
  * context recall

### Tools

* RAGAS or DeepEval

### Deliverables

* `eval.py` script
* JSON report output

---

## Phase 7: CI/CD Gating

### Tasks

* Setup GitHub Actions
* Run evaluation on PR
* Define thresholds:

  * Faithfulness > 0.85
  * Relevance > 0.80

### Deliverables

* PR fails if metrics drop

---

## Phase 8: Observability

### Tasks

* Integrate Langfuse
* Track:

  * Queries
  * Retrieved docs
  * LLM responses

### Deliverables

* Debuggable traces

---

## Phase 9: Optimization

### Tasks

* Add caching (Redis)
* Add query rewriting
* Add semantic deduplication

---

## Phase 10: Stretch Goals

* Multi-hop retrieval
* Query decomposition
* Agentic workflows
* Role-based document access

---

## Definition of Done

* End-to-end system working
* Evaluation metrics above threshold
* CI pipeline enforcing quality
* No hallucinated citations

---

## Final Advice (Hard Truth)

Most people fail this project because:

* They skip reranking ❌
* They don’t enforce citations ❌
* They don’t build evaluation ❌

If you nail those three, this becomes a **top 1% portfolio project**.

---

## Notes

* Prioritize correctness over latency first
* Reranking is mandatory for quality
* Evaluation is not optional

---
