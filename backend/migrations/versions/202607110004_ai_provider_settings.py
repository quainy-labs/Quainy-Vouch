"""Add organization AI provider settings.

Revision ID: 202607110004
Revises: 202607110003
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op


revision = "202607110004"
down_revision = "202607110003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ai_provider_settings_provider_idx ON ai_provider_settings (generation_provider, generation_model)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ai_provider_settings")
