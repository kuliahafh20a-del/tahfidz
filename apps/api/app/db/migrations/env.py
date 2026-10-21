"""Alembic environment for asynchronous PostgreSQL migrations."""

import asyncio
import selectors
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection, pool, text
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import get_settings
from app.db.models import metadata

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = metadata


def get_database_url() -> str:
    """Use an injected URL in tests/CLI or fall back to validated settings."""
    configured_url = config.get_main_option("sqlalchemy.url")
    return configured_url or get_settings().database_url_value


def configure_context(connection: Connection | None, *, url: str | None = None) -> None:
    """Apply migration policy consistently in online and offline modes."""
    context.configure(
        connection=connection,
        url=url,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
        compare_server_default=True,
        version_table="alembic_version",
        version_table_schema="alembic",
        literal_binds=connection is None,
        dialect_opts={"paramstyle": "named"} if connection is None else None,
    )


def run_migrations_offline() -> None:
    """Emit deterministic SQL without opening a database connection."""
    configure_context(None, url=get_database_url())
    with context.begin_transaction():
        context.execute("CREATE SCHEMA IF NOT EXISTS alembic")
        context.run_migrations()


def run_migrations(connection: Connection) -> None:
    """Run migration operations on a synchronous Alembic connection facade."""
    configure_context(connection)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create the migration engine and bridge Alembic onto its async connection."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    try:
        async with connectable.connect() as connection:
            await connection.execute(text("CREATE SCHEMA IF NOT EXISTS alembic"))
            await connection.commit()
            await connection.run_sync(run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    """Run all pending migrations against PostgreSQL."""
    if sys.platform == "win32":
        asyncio.run(
            run_async_migrations(),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
