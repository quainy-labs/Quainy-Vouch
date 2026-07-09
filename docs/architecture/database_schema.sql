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

CREATE TABLE users (
    id TEXT NOT NULL,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    email TEXT,
    role TEXT NOT NULL CHECK (role IN ('owner', 'editor', 'reviewer', 'viewer')),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (organization_id, id)
);

CREATE INDEX users_org_role_idx ON users (organization_id, role);

CREATE TABLE approval_policies (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    required_reviewer_count INTEGER NOT NULL DEFAULT 1,
    require_approval_before_export BOOLEAN NOT NULL DEFAULT TRUE,
    require_approval_before_publish BOOLEAN NOT NULL DEFAULT TRUE,
    allow_risk_override BOOLEAN NOT NULL DEFAULT TRUE,
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
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX content_opportunities_org_status_idx ON content_opportunities (organization_id, status);

CREATE TABLE calendar_events (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    event_type TEXT NOT NULL CHECK (event_type IN ('company', 'public')),
    starts_at TIMESTAMPTZ NOT NULL,
    ends_at TIMESTAMPTZ,
    description TEXT,
    relevance_terms JSONB NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX calendar_events_org_start_idx ON calendar_events (organization_id, starts_at);

CREATE TABLE trend_signals (
    id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    summary TEXT NOT NULL,
    source_name TEXT NOT NULL,
    source_url TEXT,
    observed_at TIMESTAMPTZ NOT NULL,
    relevance_terms JSONB NOT NULL DEFAULT '[]',
    created_by TEXT,
    created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX trend_signals_org_observed_idx ON trend_signals (organization_id, observed_at DESC);

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
    approval_metadata JSONB NOT NULL DEFAULT '{}',
    scheduled_for TIMESTAMPTZ,
    exported_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    publish_result JSONB NOT NULL DEFAULT '{}',
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
    decision TEXT NOT NULL CHECK (decision IN ('approve', 'reject', 'request_changes', 'regenerate', 'schedule', 'export', 'publish')),
    reviewer_id TEXT,
    edited_body TEXT,
    reason TEXT,
    override_reason TEXT,
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

CREATE TABLE preference_suggestions (
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

CREATE INDEX preference_suggestions_org_status_idx ON preference_suggestions (organization_id, status);

CREATE TABLE linkedin_integrations (
    organization_id TEXT PRIMARY KEY REFERENCES organizations(id) ON DELETE CASCADE,
    selected_page_urn TEXT,
    selected_page_name TEXT,
    oauth_status TEXT NOT NULL DEFAULT 'not_connected',
    permissions JSONB NOT NULL DEFAULT '[]',
    publishing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE publish_results (
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

CREATE INDEX publish_results_draft_idx ON publish_results (draft_id, requested_at DESC);

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
