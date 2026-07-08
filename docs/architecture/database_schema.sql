-- Quainy Vouch database schema draft
-- Phase 0.2: Data Model And Architecture Lock
-- Target: PostgreSQL with pgvector in production, SQLite-compatible shapes where possible for local mode.

CREATE TABLE organizations (
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

CREATE TABLE company_profiles (
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

CREATE TABLE sources (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source_type TEXT NOT NULL,
    title TEXT NOT NULL,
    uri TEXT,
    visibility TEXT NOT NULL DEFAULT 'workspace',
    approval_status TEXT NOT NULL CHECK (approval_status IN ('approved', 'disabled', 'archived')),
    freshness_days INTEGER NOT NULL DEFAULT 180,
    last_ingested_at TIMESTAMPTZ,
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX sources_organization_status_idx ON sources (organization_id, approval_status);

CREATE TABLE source_documents (
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

CREATE UNIQUE INDEX source_documents_source_hash_idx ON source_documents (source_id, content_hash);

CREATE TABLE source_chunks (
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

CREATE INDEX source_chunks_org_source_idx ON source_chunks (organization_id, source_id);

CREATE TABLE content_opportunities (
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
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX content_opportunities_org_status_idx ON content_opportunities (organization_id, status);

CREATE TABLE content_briefs (
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

CREATE TABLE drafts (
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
    scheduled_for TIMESTAMPTZ,
    exported_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX drafts_org_status_idx ON drafts (organization_id, status);
CREATE INDEX drafts_brief_idx ON drafts (content_brief_id);

CREATE TABLE claims (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    text TEXT NOT NULL,
    claim_type TEXT NOT NULL,
    confidence NUMERIC NOT NULL,
    support_status TEXT NOT NULL CHECK (support_status IN ('supported', 'weakly_supported', 'unsupported', 'not_factual')),
    supporting_chunk_ids JSONB NOT NULL DEFAULT '[]',
    risk_reason TEXT
);

CREATE TABLE approval_decisions (
    id TEXT PRIMARY KEY,
    draft_id TEXT NOT NULL REFERENCES drafts(id) ON DELETE CASCADE,
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'request_changes', 'regenerate', 'schedule', 'export')),
    reviewer_id TEXT,
    edited_body TEXT,
    reason TEXT,
    labels JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX approval_decisions_draft_idx ON approval_decisions (draft_id);

CREATE TABLE post_memory (
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

CREATE INDEX post_memory_org_platform_idx ON post_memory (organization_id, platform, content_type);

CREATE TABLE audit_logs (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    actor_id TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX audit_logs_org_created_idx ON audit_logs (organization_id, created_at DESC);
