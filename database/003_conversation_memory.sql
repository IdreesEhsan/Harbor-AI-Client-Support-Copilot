-- Phase 8: persistent conversation history and memory.

create table if not exists conversations (
    id uuid primary key default gen_random_uuid(),

    user_id uuid not null
        references users(id)
        on delete cascade,

    title text,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now()
);


create table if not exists messages (
    id uuid primary key default gen_random_uuid(),

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    role text not null
        check (
            role in (
                'user',
                'assistant',
                'system'
            )
        ),

    content text not null,

    created_at timestamptz
        not null
        default now()
);


create table if not exists conversation_summaries (
    id uuid primary key default gen_random_uuid(),

    conversation_id uuid not null
        references conversations(id)
        on delete cascade,

    summary text not null,

    summarized_until timestamptz,

    created_at timestamptz
        not null
        default now(),

    updated_at timestamptz
        not null
        default now()
);

alter table conversations
    add column if not exists title text;

alter table conversations
    add column if not exists updated_at timestamptz
    not null default now();


alter table messages
    add column if not exists role text;

alter table messages
    add column if not exists content text;

alter table messages
    add column if not exists created_at timestamptz
    not null default now();


alter table conversation_summaries
    add column if not exists summarized_until timestamptz;

alter table conversation_summaries
    add column if not exists updated_at timestamptz
    not null default now();


create index if not exists idx_conversations_user_id
on conversations(user_id);


create index if not exists idx_conversations_updated_at
on conversations(updated_at desc);


create index if not exists idx_messages_conversation_id
on messages(conversation_id);


create index if not exists idx_messages_conversation_created_at
on messages(
    conversation_id,
    created_at
);


create index if not exists idx_conversation_summaries_conversation
on conversation_summaries(conversation_id);


create unique index if not exists
idx_conversation_summaries_unique_conversation
on conversation_summaries(conversation_id);