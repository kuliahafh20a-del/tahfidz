"""Alembic migration package."""

from app.db.migrations.runner import build_alembic_config

__all__ = ["build_alembic_config"]
