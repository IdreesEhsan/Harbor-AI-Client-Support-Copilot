-- Harbor
-- Initial PostgreSQL Database Schema
-- Phase 2
--
-- Provides the database foundation for:
-- users
-- conversations
-- conversation history
-- conversation summary memory
--
-- pgvector is enabled now for future RAG functionality.


create extension if not exists vector;

-- create the users table
create table if not exists users (
    id uuid primary key default gen_random_uuid(),

    email text unique not null,
    password_hash text not null,
    full_name text,

    is_active boolean not null default true,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- create the conversations table
create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),

    user_id uuid not null references users(id) on delete cascade,

    title text,

    status text not null default 'active'
        check (status in ('active', 'closed', 'escalated')),

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- create messages table
create table if not exists messages (
    id uuid primary key default gen_random_uuid(),

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    role text not null
        check (role in ('user', 'assistant', 'system', 'tool')),

    content text not null,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default now()
);

-- create conversation_summaries table
create table if not exists conversation_summaries (
    id uuid primary key default gen_random_uuid(),

    conversation_id uuid not null unique
        references conversations(id)
        on delete cascade,

    summary text not null,

    summarized_until timestamptz,

    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

-- Add indexes
create index if not exists idx_conversations_user_id
on conversations(user_id);


create index if not exists idx_messages_conversation_id
on messages(conversation_id);


create index if not exists idx_messages_created_at
on messages(created_at);


create index if not exists idx_conversations_created_at
on conversations(created_at);

