# Phase 2 — Database Foundation

## Objective

Connect Harbor's FastAPI backend to Supabase PostgreSQL and prepare
the database for authentication, conversation history, memory, and
future RAG functionality.

## Technologies

- PostgreSQL
- Supabase
- Supabase Python SDK
- pgvector
- FastAPI
- Pydantic Settings

## Tables

### users

Stores Harbor user accounts.

### conversations

Stores conversations belonging to users.

### messages

Stores persistent user, assistant, system, and tool messages.

### conversation_summaries

Stores summarized long-term conversation context.

## Relationships

User
    |
    +--- Conversations
             |
             +--- Messages
             |
             +--- Conversation Summary

## Vector Support

The PostgreSQL pgvector extension is enabled during Phase 2.

The RAG vector table will be created later after Harbor's embedding
model and vector dimension have been selected.

## Security

Supabase server/service credentials are stored only in the backend
environment.

Secrets must never be committed to Git or exposed to the React
frontend.

## Health Checks

GET /api/v1/health

Checks whether the FastAPI application is running.

GET /api/v1/ready

Checks whether required database infrastructure is accessible.