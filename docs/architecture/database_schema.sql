-- Quainy Vouch database schema draft
-- Phase 2 target: PostgreSQL with pgvector for production persistence.
-- Deterministic providers may remain for tests, but product data should persist here.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS accounts_email_idx ON accounts (email);

CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    website_url TEXT,
    industry TEXT,
    description TEXT,
    audience_summary TEXT,
    default_timezone TEXT NOT NULL DEFAULT 'UTC',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS account_sessions (
    token_hash TEXT PRIMARY KEY,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS account_sessions_account_idx ON account_sessions (account_id, created_at DESC);

CREATE TABLE IF NOT EXISTS users (
    id TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id TEXT REFERENCES accounts(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'reviewer', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (organization_id, id)
);

CREATE INDEX IF NOT EXISTS users_org_role_idx ON users (organization_id, role);
CREATE INDEX IF NOT EXISTS users_account_idx ON users (account_id);

CREATE TABLE IF NOT EXISTS onboarding_states (
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    account_id TEXT NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    completed_steps JSONB NOT NULL DEFAULT '[]',
    profile_skipped BOOLEAN NOT NULL DEFAULT FALSE,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (organization_id, account_id)
);

CREATE TABLE IF NOT EXISTS approval_policies (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    required_reviewer_count INTEGER NOT NULL DEFAULT 1,
    require_approval_before_export BOOLEAN NOT NULL DEFAULT TRUE,
    require_approval_before_publish BOOLEAN NOT NULL DEFAULT TRUE,
    allow_risk_override BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS ai_provider_settings (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    generation_provider TEXT NOT NULL DEFAULT 'deterministic'
        CHECK (generation_provider IN ('deterministic', 'openai', 'openai_compatible', 'local')),
    generation_model TEXT NOT NULL DEFAULT 'deterministic-structured-v1',
    generation_base_url TEXT,
    generation_api_key_env_var TEXT,
    embedding_provider TEXT NOT NULL DEFAULT 'deterministic'
        CHECK (embedding_provider IN ('deterministic', 'openai', 'openai_compatible', 'local')),
    embedding_model TEXT NOT NULL DEFAULT 'local-hash',
    embedding_base_url TEXT,
    embedding_api_key_env_var TEXT,
    local_runtime TEXT NOT NULL DEFAULT 'none'
        CHECK (local_runtime IN ('none', 'ollama', 'vllm', 'lm_studio', 'custom')),
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at TIMESTAMPTZ NOT NULL,
    updated_by TEXT
);

CREATE INDEX IF NOT EXISTS ai_provider_settings_provider_idx
    ON ai_provider_settings (generation_provider, generation_model);

CREATE TABLE IF NOT EXISTS company_profiles (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    one_liner TEXT,
    mission TEXT,
    product_summary TEXT,
    audience TEXT,
    voice_rules JSONB NOT NULL DEFAULT '[]',
    preferred_phrases JSONB NOT NULL DEFAULT '[]',
    banned_phrases JSONB NOT NULL DEFAULT '[]',
    approved_claims JSONB NOT NULL DEFAULT '[]',
    forbidden_claims JSONB NOT NULL DEFAULT '[]',
    content_pillars JSONB NOT NULL DEFAULT '[]',
    sensitive_topics JSONB NOT NULL DEFAULT '[]',
    examples_good JSONB NOT NULL DEFAULT '[]',
    examples_bad JSONB NOT NULL DEFAULT '[]',
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    uri TEXT,
    visibility TEXT NOT NULL DEFAULT 'workspace',
    approval_status TEXT NOT NULL CHECK (approval_status IN ('approved', 'disabled', 'archived')),
    freshness_days INTEGER NOT NULL DEFAULT 180,
    raw_text TEXT NOT NULL DEFAULT '',
    last_ingested_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS sources_organization_status_idx ON sources (organization_id, approval_status);

CREATE TABLE IF NOT EXISTS source_documents (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    raw_text TEXT NOT NULL,
    normalized_text TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    document_date TIMESTAMPTZ,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS source_documents_source_hash_idx ON source_documents (source_id, content_hash);

CREATE TABLE IF NOT EXISTS source_chunks (
    id TEXT PRIMARY KEY,
    source_document_id TEXT NOT NULL REFERENCES source_documents(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    embedding VECTOR,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS source_chunks_org_source_idx ON source_chunks (organization_id, source_id);

CREATE TABLE IF NOT EXISTS content_opportunities (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    reason_today TEXT NOT NULL,
    source_ids JSONB NOT NULL DEFAULT '[]',
    freshness_score NUMERIC NOT NULL,
    relevance_score NUMERIC NOT NULL,
    confidence_score NUMERIC NOT NULL,
    status TEXT NOT NULL DEFAULT 'suggested',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS content_opportunities_org_status_idx ON content_opportunities (organization_id, status);

CREATE TABLE IF NOT EXISTS calendar_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('company', 'public')),
    event_date TIMESTAMPTZ NOT NULL,
    description TEXT,
    relevance_terms JSONB NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS event_date TIMESTAMPTZ;
ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS created_by TEXT;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'calendar_events' AND column_name = 'starts_at'
    ) THEN
        ALTER TABLE calendar_events ALTER COLUMN starts_at DROP NOT NULL;
        UPDATE calendar_events SET event_date = starts_at WHERE event_date IS NULL AND starts_at IS NOT NULL;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS calendar_events_org_start_idx ON calendar_events (organization_id, event_date);

CREATE TABLE IF NOT EXISTS trend_signals (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    industry TEXT,
    source_uri TEXT,
    relevance_terms JSONB NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS trend_signals_org_observed_idx ON trend_signals (organization_id, created_at DESC);

ALTER TABLE trend_signals ADD COLUMN IF NOT EXISTS industry TEXT;
ALTER TABLE trend_signals ADD COLUMN IF NOT EXISTS source_uri TEXT;
ALTER TABLE trend_signals ADD COLUMN IF NOT EXISTS created_by TEXT;
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trend_signals' AND column_name = 'source_name'
    ) THEN
        ALTER TABLE trend_signals ALTER COLUMN source_name DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trend_signals' AND column_name = 'observed_at'
    ) THEN
        ALTER TABLE trend_signals ALTER COLUMN observed_at DROP NOT NULL;
    END IF;
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'trend_signals' AND column_name = 'source_url'
    ) THEN
        UPDATE trend_signals SET source_uri = source_url WHERE source_uri IS NULL AND source_url IS NOT NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS content_briefs (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL REFERENCES content_opportunities(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    objective TEXT NOT NULL,
    audience TEXT NOT NULL,
    key_message TEXT NOT NULL,
    supporting_points JSONB NOT NULL DEFAULT '[]',
    claims JSONB NOT NULL DEFAULT '[]',
    do_not_say JSONB NOT NULL DEFAULT '[]',
    source_ids JSONB NOT NULL DEFAULT '[]',
    risks JSONB NOT NULL DEFAULT '[]',
    prompt_version TEXT NOT NULL,
    builder_metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS drafts (
    id TEXT PRIMARY KEY,
    content_brief_id TEXT NOT NULL REFERENCES content_briefs(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    content_type TEXT NOT NULL,
    body TEXT NOT NULL,
    hook TEXT,
    hashtags JSONB NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'needs_review',
    source_ids JSONB NOT NULL DEFAULT '[]',
    source_map JSONB NOT NULL DEFAULT '{}',
    risk_report JSONB NOT NULL DEFAULT '[]',
    quality_report JSONB NOT NULL DEFAULT '[]',
    duplicate_report JSONB NOT NULL DEFAULT '{}',
    generation_metadata JSONB NOT NULL DEFAULT '{}',
    approval_metadata JSONB NOT NULL DEFAULT '{}',
    scheduled_for TIMESTAMPTZ,
    exported_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    publish_result JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS drafts_org_status_idx ON drafts (organization_id, status);
CREATE INDEX IF NOT EXISTS drafts_brief_idx ON drafts (content_brief_id);

CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    support_status TEXT NOT NULL CHECK (support_status IN ('supported', 'weakly_supported', 'unsupported', 'not_factual')),
    supporting_chunk_ids JSONB NOT NULL DEFAULT '[]',
    risk_reason TEXT
);

CREATE TABLE IF NOT EXISTS approval_decisions (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'request_changes', 'regenerate', 'schedule', 'export', 'publish')),
    reviewer_id TEXT,
    edited_body TEXT,
    reason TEXT,
    override_reason TEXT,
    labels JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS approval_decisions_draft_idx ON approval_decisions (draft_id);

CREATE TABLE IF NOT EXISTS post_memory (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    platform TEXT NOT NULL,
    content_type TEXT NOT NULL,
    final_body TEXT NOT NULL,
    source_draft_id TEXT REFERENCES drafts(id) ON DELETE SET NULL,
    topic_labels JSONB NOT NULL DEFAULT '[]',
    idea_fingerprint TEXT NOT NULL,
    embedding VECTOR,
    approved_at TIMESTAMPTZ,
    exported_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    performance_snapshot JSONB NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS post_memory_org_platform_idx ON post_memory (organization_id, platform, content_type);

CREATE TABLE IF NOT EXISTS preference_suggestions (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    kind TEXT NOT NULL CHECK (kind IN ('voice_phrase', 'rejected_pattern', 'memory_update')),
    title TEXT NOT NULL,
    rationale TEXT NOT NULL,
    proposed_update JSONB NOT NULL DEFAULT '{}',
    evidence JSONB NOT NULL DEFAULT '[]',
    confidence NUMERIC NOT NULL DEFAULT 0.5,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'dismissed')),
    created_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS preference_suggestions_org_status_idx ON preference_suggestions (organization_id, status);

CREATE TABLE IF NOT EXISTS linkedin_integrations (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    selected_page_urn TEXT,
    selected_page_name TEXT,
    oauth_status TEXT NOT NULL DEFAULT 'not_connected',
    permissions JSONB NOT NULL DEFAULT '[]',
    publishing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS publish_results (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    provider TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('published', 'failed')),
    page_urn TEXT NOT NULL,
    page_name TEXT,
    provider_post_id TEXT,
    published_url TEXT,
    failure_reason TEXT,
    requested_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS publish_results_draft_idx ON publish_results (draft_id, requested_at DESC);

CREATE TABLE IF NOT EXISTS background_jobs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id TEXT,
    kind TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    result JSONB NOT NULL DEFAULT '{}',
    error_message TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    max_attempts INTEGER NOT NULL DEFAULT 3,
    queued_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS background_jobs_org_updated_idx ON background_jobs (organization_id, updated_at DESC);
CREATE INDEX IF NOT EXISTS background_jobs_status_idx ON background_jobs (status, updated_at);

CREATE TABLE IF NOT EXISTS background_job_logs (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    message TEXT NOT NULL,
    level TEXT NOT NULL DEFAULT 'info',
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS background_job_logs_job_created_idx ON background_job_logs (job_id, created_at);

CREATE TABLE IF NOT EXISTS model_call_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id TEXT,
    provider TEXT NOT NULL,
    model TEXT NOT NULL,
    prompt_version TEXT NOT NULL,
    schema_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')),
    prompt_hash TEXT NOT NULL,
    source_ids JSONB NOT NULL DEFAULT '[]',
    request_metadata JSONB NOT NULL DEFAULT '{}',
    response_metadata JSONB NOT NULL DEFAULT '{}',
    token_usage JSONB NOT NULL DEFAULT '{}',
    cost_usd NUMERIC,
    error_message TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS model_call_logs_org_created_idx ON model_call_logs (organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS model_call_logs_provider_idx ON model_call_logs (provider, model, created_at DESC);

CREATE TABLE IF NOT EXISTS audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS audit_logs_org_created_idx ON audit_logs (organization_id, created_at DESC);
