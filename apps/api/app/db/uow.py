"""Explicit transaction boundaries for application use cases."""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from types import TracebackType

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

SessionFactory = Callable[[], AsyncSession]


class SqlAlchemyUnitOfWork:
    """A request/use-case transaction that commits only when asked explicitly."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory
        self._session: AsyncSession | None = None
        self._transaction: AsyncSessionTransaction | None = None
        self._finished = False

    @property
    def session(self) -> AsyncSession:
        """Expose the active session only while inside the unit-of-work context."""
        if self._session is None:
            raise RuntimeError("Unit of Work has not been entered")
        return self._session

    async def __aenter__(self) -> SqlAlchemyUnitOfWork:
        self._session = self._session_factory()
        self._transaction = await self._session.begin()
        self._finished = False
        return self

    async def commit(self) -> None:
        """Commit all domain changes atomically."""
        if self._transaction is None or self._finished:
            raise RuntimeError("Unit of Work has no active transaction")
        await self._transaction.commit()
        self._finished = True

    async def rollback(self) -> None:
        """Roll back all domain changes atomically."""
        if self._transaction is None or self._finished:
            return
        await self._transaction.rollback()
        self._finished = True

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        del exc_type, exc_value, traceback
        try:
            if not self._finished:
                await self.rollback()
        finally:
            if self._session is not None:
                await self._session.close()
            self._session = None
            self._transaction = None


@asynccontextmanager
async def transaction(session_factory: SessionFactory) -> AsyncIterator[AsyncSession]:
    """Provide an auto-commit boundary for small infrastructure operations."""
    async with session_factory() as session, session.begin():
        yield session
