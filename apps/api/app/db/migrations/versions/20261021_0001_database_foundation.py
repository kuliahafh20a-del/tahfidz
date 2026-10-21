"""Create PostgreSQL schemas and UUID foundation.

Revision ID: 20261021_0001
Revises:
Create Date: 2026-10-21 00:00:00+00:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261021_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create isolated domain/operations schemas and UUID support."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE SCHEMA IF NOT EXISTS app")
    op.execute("CREATE SCHEMA IF NOT EXISTS ops")


def downgrade() -> None:
    """Remove only schemas owned by this application revision."""
    op.execute("DROP SCHEMA IF EXISTS ops CASCADE")
    op.execute("DROP SCHEMA IF EXISTS app CASCADE")
