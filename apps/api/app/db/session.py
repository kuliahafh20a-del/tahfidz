"""Async SQLAlchemy engine, connection pool, and session lifecycle."""

from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


class Database:
    """Own the process-wide engine and async session factory."""

    def __init__(self, settings: Settings) -> None:
        self.engine: AsyncEngine = create_async_engine(
            settings.database_url_value,
            pool_pre_ping=True,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout_seconds,
            pool_recycle=settings.database_pool_recycle_seconds,
            connect_args={"options": settings.database_connect_options},
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            autoflush=False,
            expire_on_commit=False,
        )

    async def ping(self) -> None:
        """Verify that a pooled database connection can execute a cheap query."""
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def dispose(self) -> None:
        """Close all pooled connections during process shutdown."""
        await self.engine.dispose()


_database: Database | None = None


def get_database() -> Database:
    """Create the process database lazily so imports never open connections."""
    global _database
    if _database is None:
        _database = Database(get_settings())
    return _database


async def get_session() -> AsyncIterator[AsyncSession]:
    """Yield a request-scoped session and prevent leaked open transactions."""
    async with get_database().session_factory() as session:
        try:
            yield session
        finally:
            if session.in_transaction():
                await session.rollback()


async def close_database() -> None:
    """Dispose the lazy singleton without creating it during shutdown."""
    global _database
    database, _database = _database, None
    if database is not None:
        await database.dispose()
