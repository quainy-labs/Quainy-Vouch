"""Add publishing OAuth connections.

Revision ID: 202607110006
Revises: 202607110005
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op


revision = "202607110006"
down_revision = "202607110005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS publishing_connections (
            organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            provider TEXT NOT NULL CHECK (provider IN ('linkedin', 'reddit', 'instagram')),
            oauth_status TEXT NOT NULL DEFAULT 'not_connected',
            scopes JSONB NOT NULL DEFAULT '[]',
            access_token TEXT,
            refresh_token TEXT,
            token_type TEXT,
            expires_at TIMESTAMPTZ,
            account_id TEXT,
            account_name TEXT,
            selected_target_id TEXT,
            selected_target_name TEXT,
            selected_target_type TEXT,
            publishing_enabled BOOLEAN NOT NULL DEFAULT FALSE,
            updated_at TIMESTAMPTZ NOT NULL,
            PRIMARY KEY (organization_id, provider)
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS publishing_connections")
