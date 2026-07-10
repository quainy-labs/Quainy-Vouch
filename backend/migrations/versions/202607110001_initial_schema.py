"""Initial production schema.

Revision ID: 202607110001
Revises:
Create Date: 2026-07-11
"""

from __future__ import annotations

from pathlib import Path

from alembic import op


revision = "202607110001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    root = Path(__file__).resolve().parents[3]
    schema_sql = root / "docs" / "architecture" / "database_schema.sql"
    raw_connection = op.get_bind().connection
    with raw_connection.cursor() as cursor:
        cursor.execute(schema_sql.read_text())


def downgrade() -> None:
    raise NotImplementedError("The baseline production schema migration is not reversible.")
