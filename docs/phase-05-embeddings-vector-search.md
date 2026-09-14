# Harbor — Phase 5: Embeddings and Vector Search

## Objective

Phase 5 adds semantic retrieval capabilities to Harbor.

Documents processed by the Phase 4 ingestion pipeline are converted
into numerical embedding vectors and stored in Supabase PostgreSQL
using pgvector.

## Embedding Model

Harbor currently uses:

sentence-transformers/all-MiniLM-L6-v2

Embedding dimension:

384

The model runs locally during development.

## Retrieval Pipeline

Document
→ Loader
→ Cleaner
→ Chunker
→ Embedding Model
→ Supabase pgvector

Query
→ Query Embedding
→ Cosine Similarity Search
→ Relevant Knowledge Chunks

## Database Tables

### knowledge_documents

Stores one row for each original source document.

Important fields:

- id
- source_name
- file_type
- content_hash
- metadata
- status
- last_indexed_at

### knowledge_chunks

Stores retrieval-ready chunks.

Important fields:

- id
- document_id
- chunk_index
- content
- metadata
- embedding

The embedding column uses:

vector(384)

## Configuration

Harbor resolves backend/.env using an absolute path derived from
config.py.

This avoids failures when commands are launched from Harbor/,
backend/, tests, or scripts.

## Idempotent Indexing

Harbor calculates a SHA-256 hash from cleaned document content.

If the document is unchanged:

- indexing is skipped

If the document changes:

1. old chunks are deleted
2. source metadata is updated
3. the document is re-chunked
4. embeddings are regenerated
5. replacement vectors are inserted

## Vector Search

Harbor uses cosine similarity.

pgvector's <=> operator gives cosine distance.

Similarity is calculated as:

1 - cosine_distance

## Similarity Threshold

Current development threshold:

0.35

This is only a starting value and will later be evaluated using
real retrieval test cases.

## Top-K

The semantic search RPC supports a configurable match count.

For example:

Top-K = 5

returns up to five qualifying chunks.

## Vector Index

Harbor uses an HNSW index with:

vector_cosine_ops

This improves approximate nearest-neighbor search as the knowledge base
grows.

## Security

The Supabase service-role key remains backend-only.

The frontend must never receive:

- Supabase service-role credentials
- JWT secret keys
- backend-only configuration

## Current Limitations

Phase 5 performs semantic retrieval only.

It does not yet:

- generate final LLM answers
- enforce grounded generation
- generate final citations
- evaluate groundedness
- evaluate citation correctness

Precise PDF page metadata will also be improved before the final
citation pipeline.

## Next Phase

Phase 6 will add:

- LLM integration
- retrieved-context construction
- grounded RAG prompts
- explicit no-answer behavior
- citations
- retrieval evaluation
- retrieval hit rate
- groundedness
- citation correctness