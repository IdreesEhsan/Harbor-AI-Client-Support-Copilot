-- ============================================================
-- Harbor
-- Phase 5: Knowledge Base Vector Storage and Semantic Search
-- ============================================================

-- Current embedding model:
-- sentence-transformers/all-MiniLM-L6-v2
--
-- Embedding dimension:
-- 384
--
-- IMPORTANT:
-- The vector dimension must match the embedding model.
-- ============================================================


-- ============================================================
-- 1. ENABLE PGVECTOR
-- ============================================================

create extension if not exists vector;


-- ============================================================
-- 2. KNOWLEDGE DOCUMENTS
-- ============================================================

create table if not exists knowledge_documents (
    id uuid primary key default gen_random_uuid(),

    -- Original knowledge-base filename.
    source_name text not null unique,

    -- Examples: txt, pdf, docx.
    file_type text not null,

    -- Optional human-readable title.
    title text,

    -- SHA-256 hash of cleaned content.
    content_hash text not null,

    -- Flexible source-level metadata.
    metadata jsonb not null default '{}'::jsonb,

    -- Tracks indexing status.
    status text not null default 'indexed'
        check (
            status in (
                'pending',
                'indexed',
                'failed'
            )
        ),

    created_at timestamptz not null default now(),

    updated_at timestamptz not null default now(),

    last_indexed_at timestamptz
);


-- ============================================================
-- 3. KNOWLEDGE CHUNKS
-- ============================================================

create table if not exists knowledge_chunks (
    id uuid primary key,

    document_id uuid not null
        references knowledge_documents(id)
        on delete cascade,

    -- Position inside the source document.
    chunk_index integer not null,

    -- Retrieval-ready chunk content.
    content text not null,

    -- Chunk strategy, source details, page markers, etc.
    metadata jsonb not null default '{}'::jsonb,

    -- MiniLM-L6-v2 produces 384-dimensional vectors.
    embedding vector(384) not null,

    created_at timestamptz not null default now(),

    unique (
        document_id,
        chunk_index
    )
);


-- ============================================================
-- 4. STANDARD INDEX
-- ============================================================

create index if not exists idx_knowledge_chunks_document_id
on knowledge_chunks(document_id);


-- ============================================================
-- 5. HNSW VECTOR INDEX
-- ============================================================

create index if not exists idx_knowledge_chunks_embedding_hnsw
on knowledge_chunks
using hnsw (
    embedding vector_cosine_ops
);


-- ============================================================
-- 6. SEMANTIC SEARCH RPC
-- ============================================================

create or replace function match_knowledge_chunks(
    query_embedding vector(384),
    match_threshold double precision default 0.35,
    match_count integer default 5
)
returns table (
    id uuid,
    document_id uuid,
    source_name text,
    content text,
    chunk_index integer,
    metadata jsonb,
    similarity double precision
)
language sql
stable
as $$
    select
        kc.id,
        kc.document_id,
        kd.source_name,
        kc.content,
        kc.chunk_index,
        kc.metadata,

        -- <=> gives cosine distance.
        -- 1 - distance gives cosine similarity.
        1 - (kc.embedding <=> query_embedding) as similarity

    from knowledge_chunks as kc

    join knowledge_documents as kd
        on kd.id = kc.document_id

    where
        1 - (kc.embedding <=> query_embedding)
        >= match_threshold

    order by
        kc.embedding <=> query_embedding

    limit match_count;
$$;