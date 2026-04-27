-- Geshtu initial schema. See spec §3.
-- Idempotent where possible; runs on a fresh DB.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- ─── Identity (single-team mode: one row in `team`) ──────────

CREATE TABLE IF NOT EXISTS team (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID REFERENCES team(id) ON DELETE CASCADE,
    email TEXT UNIQUE NOT NULL,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_role_chk CHECK (role IN ('admin', 'member'))
);

CREATE TABLE IF NOT EXISTS access_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash TEXT NOT NULL UNIQUE,
    label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_access_tokens_user ON access_tokens(user_id) WHERE revoked_at IS NULL;

-- ─── Projects ────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    team_id UUID REFERENCES team(id) ON DELETE CASCADE,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ─── Conversation log ────────────────────────────────────────

CREATE TABLE IF NOT EXISTS sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    llm_model TEXT,
    title TEXT,
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_sessions_project ON sessions(project_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id, started_at DESC);

CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    token_count INT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT messages_role_chk CHECK (role IN ('user', 'assistant', 'system', 'tool'))
);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);

-- ─── Memory layer ────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS facts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    statement TEXT NOT NULL,
    entity TEXT,
    attribute TEXT,
    embedding vector(1024),
    confidence FLOAT NOT NULL DEFAULT 1.0,
    valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
    valid_until TIMESTAMPTZ,
    superseded_by UUID REFERENCES facts(id),
    refines UUID REFERENCES facts(id),
    source_session_id UUID REFERENCES sessions(id),
    source_message_id UUID REFERENCES messages(id),
    created_by UUID REFERENCES users(id),
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_facts_active ON facts(project_id) WHERE valid_until IS NULL;
CREATE INDEX IF NOT EXISTS idx_facts_embedding ON facts USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_facts_trgm ON facts USING gin (statement gin_trgm_ops);

CREATE TABLE IF NOT EXISTS decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    rationale TEXT NOT NULL,
    embedding vector(1024),
    decided_by UUID REFERENCES users(id),
    decided_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'active',
    reversed_by UUID REFERENCES decisions(id),
    source_session_id UUID REFERENCES sessions(id),
    source_message_id UUID REFERENCES messages(id),
    metadata JSONB NOT NULL DEFAULT '{}',
    CONSTRAINT decisions_status_chk CHECK (status IN ('active', 'reversed', 'superseded'))
);
CREATE INDEX IF NOT EXISTS idx_decisions_project ON decisions(project_id, decided_at DESC);
CREATE INDEX IF NOT EXISTS idx_decisions_embedding ON decisions USING hnsw (embedding vector_cosine_ops);
CREATE INDEX IF NOT EXISTS idx_decisions_trgm ON decisions USING gin (decision gin_trgm_ops);

CREATE TABLE IF NOT EXISTS session_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id UUID NOT NULL UNIQUE REFERENCES sessions(id) ON DELETE CASCADE,
    summary_md TEXT NOT NULL,
    open_questions TEXT[] NOT NULL DEFAULT '{}',
    next_actions TEXT[] NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS digests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    requested_by UUID REFERENCES users(id),
    since_timestamp TIMESTAMPTZ,
    depth TEXT NOT NULL,
    content_md TEXT NOT NULL,
    fact_count INT NOT NULL DEFAULT 0,
    decision_count INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT digests_depth_chk CHECK (depth IN ('quick', 'standard', 'deep'))
);
CREATE INDEX IF NOT EXISTS idx_digests_project ON digests(project_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_digests_cache ON digests(project_id, depth, since_timestamp, created_at DESC);

-- ─── Audit ───────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS access_log (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    operation TEXT NOT NULL,
    project_id UUID REFERENCES projects(id),
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_access_log_recent ON access_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_access_log_user ON access_log(user_id, created_at DESC);

-- ─── Schema version ──────────────────────────────────────────

CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

INSERT INTO schema_migrations(version) VALUES ('001_init')
ON CONFLICT DO NOTHING;
