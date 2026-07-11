"""Add model call logs.

Revision ID: 202607110003
Revises: 202607110002
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op


revision = "202607110003"
down_revision = "202607110002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS model_call_logs_org_created_idx ON model_call_logs (organization_id, created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS model_call_logs_provider_idx ON model_call_logs (provider, model, created_at DESC)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS model_call_logs")
