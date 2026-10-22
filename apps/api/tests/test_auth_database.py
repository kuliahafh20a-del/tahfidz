import asyncio
import os
import selectors
import sys
from collections.abc import Coroutine, Iterator
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, text

from app.core.config import Settings
from app.db.migrations import build_alembic_config
from app.db.session import Database
from app.modules.auth.security import PasswordManager
from app.modules.auth.service import (
    AuthenticationRequiredError,
    AuthService,
    CsrfTokenInvalidError,
    InvalidCredentialsError,
    RateLimitExceededError,
    RecoveryTokenInvalidError,
)
from app.modules.identity.models import AccountStatus, Role, RoleGrant, User

MIGRATION_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")
DEPARTMENT_ID = UUID("10000000-0000-4000-8000-000000000002")


def run_async[T](operation: Coroutine[object, object, T]) -> T:
    if sys.platform == "win32":
        return asyncio.run(
            operation,
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    return asyncio.run(operation)


@pytest.fixture(scope="module")
def auth_engine() -> Iterator[Engine]:
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    command.upgrade(build_alembic_config(settings.database_url_value), "head")
    engine = create_engine(settings.database_url_value)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL auth tests",
)
def test_auth_schema_stores_hashes_not_raw_capabilities(auth_engine: Engine) -> None:
    inspector = inspect(auth_engine)
    assert set(inspector.get_table_names(schema="app")) >= {
        "auth_sessions",
        "password_recovery_tokens",
        "auth_rate_limit_events",
    }
    session_columns = {
        column["name"] for column in inspector.get_columns("auth_sessions", schema="app")
    }
    assert "token_hash" in session_columns
    assert "csrf_token_hash" in session_columns
    assert "token" not in session_columns


async def assert_auth_lifecycle(settings: Settings) -> None:
    database = Database(settings)
    password_manager = PasswordManager()
    identifier = f"auth-{uuid4()}@example.test"
    try:
        async with database.session_factory() as session:
            user = User(
                login_identifier=identifier,
                name="Auth Integration User",
                account_status=AccountStatus.ACTIVE,
                password_hash=password_manager.hash("initial secure password"),
            )
            session.add(user)
            await session.flush()
            session.add(
                RoleGrant(
                    user_id=user.id,
                    organization_id=DEPARTMENT_ID,
                    role=Role.DEPARTMENT_ADMIN,
                )
            )
            await session.commit()

            service = AuthService(session, settings, password_manager)
            issued = await service.login(identifier, "initial secure password", "127.0.0.10")
            assert issued.payload.active_context is not None
            assert issued.payload.active_context.role is Role.DEPARTMENT_ADMIN

            stored_hash = await session.scalar(
                text("SELECT token_hash FROM app.auth_sessions WHERE user_id = :user_id"),
                {"user_id": user.id},
            )
            assert stored_hash != issued.session_token
            assert issued.session_token not in str(stored_hash)

            with pytest.raises(CsrfTokenInvalidError):
                await service.rotate(issued.session_token, "wrong-csrf-token", None)
            rotated = await service.rotate(
                issued.session_token,
                issued.payload.csrf_token,
                None,
            )
            assert rotated.session_token != issued.session_token
            with pytest.raises(AuthenticationRequiredError):
                await service.authenticate(issued.session_token)
            assert (await service.authenticate(rotated.session_token)).user_id == user.id

            challenge = await service.request_password_recovery(identifier, "127.0.0.11")
            assert challenge is not None
            await service.reset_password(
                challenge.token,
                "replacement secure password",
                "127.0.0.11",
            )
            with pytest.raises(RecoveryTokenInvalidError):
                await service.reset_password(
                    challenge.token,
                    "another secure password",
                    "127.0.0.12",
                )
            with pytest.raises(AuthenticationRequiredError):
                await service.authenticate(rotated.session_token)
            with pytest.raises(InvalidCredentialsError):
                await service.login(identifier, "initial secure password", "127.0.0.13")
            replacement = await service.login(
                identifier,
                "replacement secure password",
                "127.0.0.13",
            )
            assert replacement.payload.user.login_identifier == identifier
            user.account_status = AccountStatus.INACTIVE
            await session.commit()
            with pytest.raises(AuthenticationRequiredError):
                await service.authenticate(replacement.session_token)
    finally:
        await database.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL auth tests",
)
def test_session_rotation_recovery_and_password_reset(auth_engine: Engine) -> None:
    del auth_engine
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    run_async(assert_auth_lifecycle(settings))


async def assert_login_rate_limit(settings: Settings) -> None:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            service = AuthService(session, settings)
            for _ in range(settings.login_rate_limit_attempts):
                with pytest.raises(InvalidCredentialsError):
                    await service.login("absent@example.test", "wrong", "192.0.2.10")
            with pytest.raises(RateLimitExceededError):
                await service.login("absent@example.test", "wrong", "192.0.2.10")
    finally:
        await database.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL auth tests",
)
def test_login_rate_limit_uses_database_state(auth_engine: Engine) -> None:
    del auth_engine
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate(
        {
            "DATABASE_URL": MIGRATION_DATABASE_URL,
            "LOGIN_RATE_LIMIT_ATTEMPTS": 2,
        }
    )
    run_async(assert_login_rate_limit(settings))
