import asyncio
from collections.abc import Callable
from typing import cast

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.uow import SqlAlchemyUnitOfWork


class FakeTransaction:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeSession:
    def __init__(self, transaction: FakeTransaction) -> None:
        self.transaction = transaction
        self.closed = False

    async def begin(self) -> FakeTransaction:
        return self.transaction

    async def close(self) -> None:
        self.closed = True


def session_factory(session: FakeSession) -> Callable[[], AsyncSession]:
    return lambda: cast(AsyncSession, session)


def test_unit_of_work_commits_explicitly_and_closes_session() -> None:
    async def scenario() -> None:
        transaction = FakeTransaction()
        session = FakeSession(transaction)
        unit_of_work = SqlAlchemyUnitOfWork(session_factory(session))

        async with unit_of_work:
            assert unit_of_work.session is cast(AsyncSession, session)
            await unit_of_work.commit()

        assert transaction.commits == 1
        assert transaction.rollbacks == 0
        assert session.closed is True

    asyncio.run(scenario())


def test_unit_of_work_rolls_back_when_not_committed() -> None:
    async def scenario() -> None:
        transaction = FakeTransaction()
        session = FakeSession(transaction)

        async with SqlAlchemyUnitOfWork(session_factory(session)):
            pass

        assert transaction.commits == 0
        assert transaction.rollbacks == 1
        assert session.closed is True

    asyncio.run(scenario())


def test_unit_of_work_rolls_back_after_exception() -> None:
    async def scenario() -> None:
        transaction = FakeTransaction()
        session = FakeSession(transaction)

        try:
            async with SqlAlchemyUnitOfWork(session_factory(session)):
                raise RuntimeError("domain failure")
        except RuntimeError:
            pass

        assert transaction.rollbacks == 1
        assert session.closed is True

    asyncio.run(scenario())
