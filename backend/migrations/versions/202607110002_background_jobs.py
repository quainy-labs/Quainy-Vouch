"""Add persistent background jobs.

Revision ID: 202607110002
Revises: 202607110001
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op


revision = "202607110002"
down_revision = "202607110001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
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
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS background_jobs_org_updated_idx ON background_jobs (organization_id, updated_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS background_jobs_status_idx ON background_jobs (status, updated_at)")
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS background_job_logs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES background_jobs(id) ON DELETE CASCADE,
            organization_id TEXT NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
            message TEXT NOT NULL,
            level TEXT NOT NULL DEFAULT 'info',
            metadata JSONB NOT NULL DEFAULT '{}',
            created_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS background_job_logs_job_created_idx ON background_job_logs (job_id, created_at)")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS background_job_logs")
    op.execute("DROP TABLE IF EXISTS background_jobs")
