import asyncio
import os
import selectors
import sys
from collections.abc import Coroutine

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.db.migrations import build_alembic_config
from app.db.session import Database

MIGRATION_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")


def run_async[T](operation: Coroutine[object, object, T]) -> T:
    if sys.platform == "win32":
        return asyncio.run(
            operation,
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    return asyncio.run(operation)


async def assert_async_database_foundation(settings: Settings) -> None:
    database = Database(settings)
    try:
        await database.ping()
        async with database.session_factory() as session:
            timezone = await session.scalar(text("SHOW timezone"))
            statement_timeout = await session.scalar(text("SHOW statement_timeout"))

        assert timezone == "UTC"
        assert statement_timeout == "15s"
    finally:
        await database.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL migration tests",
)
def test_upgrade_from_empty_database_and_rollback() -> None:
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    database_url = settings.database_url_value
    configuration = build_alembic_config(database_url)

    command.downgrade(configuration, "base")
    try:
        command.upgrade(configuration, "head")
        run_async(assert_async_database_foundation(settings))

        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                schema_inspector = inspect(connection)
                assert schema_inspector.has_schema("app")
                assert schema_inspector.has_schema("ops")
                assert schema_inspector.has_schema("alembic")
                revision = connection.scalar(
                    text("SELECT version_num FROM alembic.alembic_version")
                )
                assert revision == "20261022_0006"
        finally:
            engine.dispose()

        command.downgrade(configuration, "base")

        engine = create_engine(database_url)
        try:
            with engine.connect() as connection:
                schema_inspector = inspect(connection)
                assert not schema_inspector.has_schema("app")
                assert not schema_inspector.has_schema("ops")
                assert schema_inspector.has_schema("alembic")
        finally:
            engine.dispose()
    finally:
        command.upgrade(configuration, "head")
