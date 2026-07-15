"""Split AI provider local runtimes by use.

Revision ID: 202607110005
Revises: 202607110004
Create Date: 2026-07-13
"""

from __future__ import annotations

from alembic import op


revision = "202607110005"
down_revision = "202607110004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE ai_provider_settings
        ADD COLUMN IF NOT EXISTS generation_local_runtime TEXT NOT NULL DEFAULT 'none'
            CHECK (generation_local_runtime IN ('none', 'ollama', 'vllm', 'lm_studio', 'custom'))
        """
    )
    op.execute(
        """
        ALTER TABLE ai_provider_settings
        ADD COLUMN IF NOT EXISTS embedding_local_runtime TEXT NOT NULL DEFAULT 'none'
            CHECK (embedding_local_runtime IN ('none', 'ollama', 'vllm', 'lm_studio', 'custom'))
        """
    )
    op.execute(
        """
        UPDATE ai_provider_settings
        SET
            generation_local_runtime = local_runtime,
            embedding_local_runtime = local_runtime
        WHERE local_runtime IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE ai_provider_settings DROP COLUMN IF EXISTS embedding_local_runtime")
    op.execute("ALTER TABLE ai_provider_settings DROP COLUMN IF EXISTS generation_local_runtime")
