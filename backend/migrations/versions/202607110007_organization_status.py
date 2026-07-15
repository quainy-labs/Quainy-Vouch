"""Add organization lifecycle status.

Revision ID: 202607110007
Revises: 202607110006
Create Date: 2026-07-11
"""

from __future__ import annotations

from alembic import op


revision = "202607110007"
down_revision = "202607110006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE organizations
        ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'deactivated'))
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE organizations DROP COLUMN IF EXISTS status")
