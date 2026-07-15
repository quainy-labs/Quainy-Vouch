"""Allow native Gemini generation provider.

Revision ID: 202607110008
Revises: 202607110007
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op


revision = "202607110008"
down_revision = "202607110007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE ai_provider_settings DROP CONSTRAINT IF EXISTS ai_provider_settings_generation_provider_check")
    op.execute(
        """
        ALTER TABLE ai_provider_settings
        ADD CONSTRAINT ai_provider_settings_generation_provider_check
        CHECK (generation_provider IN ('deterministic', 'openai', 'gemini', 'openai_compatible', 'local'))
        """
    )


def downgrade() -> None:
    op.execute("UPDATE ai_provider_settings SET generation_provider = 'deterministic' WHERE generation_provider = 'gemini'")
    op.execute("ALTER TABLE ai_provider_settings DROP CONSTRAINT IF EXISTS ai_provider_settings_generation_provider_check")
    op.execute(
        """
        ALTER TABLE ai_provider_settings
        ADD CONSTRAINT ai_provider_settings_generation_provider_check
        CHECK (generation_provider IN ('deterministic', 'openai', 'openai_compatible', 'local'))
        """
    )
