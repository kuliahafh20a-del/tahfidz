"""Programmatic Alembic configuration shared by CLI and migration tests."""

from pathlib import Path

from alembic.config import Config

from app.core.config import get_settings

API_ROOT = Path(__file__).resolve().parents[3]


def build_alembic_config(database_url: str | None = None) -> Config:
    """Build Alembic configuration with a validated runtime URL."""
    configuration = Config(str(API_ROOT / "alembic.ini"))
    url = database_url or get_settings().database_url_value
    configuration.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return configuration
