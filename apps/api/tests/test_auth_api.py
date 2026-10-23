from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from app.core.config import AppEnvironment, Settings, get_settings
from app.main import create_app
from app.modules.auth.delivery import get_recovery_token_delivery
from app.modules.auth.dependencies import get_auth_service
from app.modules.auth.schemas import RoleContext, RoleContextSelection
from app.modules.auth.service import (
    InvalidCredentialsError,
    IssuedSession,
    RateLimitExceededError,
    RecoveryChallenge,
)
from app.modules.identity.models import Role

USER_ID = UUID("50000000-0000-4000-8000-000000000001")
ORGANIZATION_ID = UUID("50000000-0000-4000-8000-000000000002")
EXPIRES_AT = datetime.now(UTC) + timedelta(hours=12)
SETTINGS = Settings.model_validate(
    {
        "APP_ENV": AppEnvironment.PRODUCTION,
        "DATABASE_URL": "postgresql://yaqin:a-real-test-password@localhost/yaqin",
        "SESSION_SECRET": "test-session-key-with-more-than-thirty-two-characters",
        "CSRF_SECRET": "test-csrf-key-with-more-than-thirty-two-characters",
        "OBJECT_STORAGE_ACCESS_KEY": "test-storage-access",
        "OBJECT_STORAGE_SECRET_KEY": "test-storage-secret",
    }
)


def issued_session() -> IssuedSession:
    context = RoleContext(
        role=Role.DEPARTMENT_ADMIN,
        organization_id=ORGANIZATION_ID,
        organization_name="Jurusan Contoh",
    )
    from app.modules.auth.schemas import SessionResponse, SessionUser

    return IssuedSession(
        session_token="opaque-session-value",
        payload=SessionResponse(
            user=SessionUser(
                id=USER_ID,
                display_name="Admin Jurusan",
                login_identifier="admin@example.test",
                roles=[context],
            ),
            active_context=context,
            csrf_token="session-bound-csrf",
            expires_at=EXPIRES_AT,
        ),
    )


class StubAuthService:
    def __init__(self) -> None:
        self.reject_login = False
        self.rate_limited = False
        self.logout_arguments: tuple[str | None, str | None] | None = None
        self.recovery_challenge: RecoveryChallenge | None = None

    async def login(self, identifier: str, password: str, client_address: str) -> IssuedSession:
        del identifier, password, client_address
        if self.rate_limited:
            raise RateLimitExceededError(900)
        if self.reject_login:
            raise InvalidCredentialsError
        return issued_session()

    async def session_payload(self, session_token: str | None):  # type: ignore[no-untyped-def]
        assert session_token == "opaque-session-value"
        return issued_session().payload

    async def rotate(
        self,
        session_token: str | None,
        csrf_token: str | None,
        selection: RoleContextSelection | None,
    ) -> IssuedSession:
        assert session_token == "opaque-session-value"
        assert csrf_token == "session-bound-csrf"
        del selection
        return issued_session()

    async def logout(self, session_token: str | None, csrf_token: str | None) -> None:
        self.logout_arguments = (session_token, csrf_token)

    async def request_password_recovery(
        self,
        identifier: str,
        client_address: str,
    ) -> RecoveryChallenge | None:
        del identifier, client_address
        if self.rate_limited:
            raise RateLimitExceededError(3600)
        return self.recovery_challenge

    async def reset_password(
        self,
        token: str,
        new_password: str,
        client_address: str,
    ) -> None:
        del token, new_password, client_address


class CapturingDelivery:
    def __init__(self) -> None:
        self.delivered: list[RecoveryChallenge] = []

    async def deliver(self, challenge: RecoveryChallenge) -> None:
        self.delivered.append(challenge)


def auth_client(
    service: StubAuthService,
    delivery: CapturingDelivery | None = None,
) -> TestClient:
    application = create_app()
    application.dependency_overrides[get_auth_service] = lambda: service
    application.dependency_overrides[get_settings] = lambda: SETTINGS
    if delivery is not None:
        application.dependency_overrides[get_recovery_token_delivery] = lambda: delivery
    return TestClient(application, base_url="https://testserver")


def test_login_sets_secure_opaque_cookie_and_no_store_response() -> None:
    service = StubAuthService()
    with auth_client(service) as client:
        response = client.post(
            "/api/v1/auth/login",
            json={"identifier": "admin@example.test", "password": "correct password"},
        )

    cookie = response.headers["set-cookie"]
    assert response.status_code == 200
    assert "yaqin_session=opaque-session-value" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["data"]["csrf_token"] == "session-bound-csrf"


def test_login_failure_is_generic_and_rate_limit_sets_retry_after() -> None:
    service = StubAuthService()
    service.reject_login = True
    with auth_client(service) as client:
        missing = client.post(
            "/api/v1/auth/login",
            json={"identifier": "missing@example.test", "password": "wrong password"},
        )
        existing = client.post(
            "/api/v1/auth/login",
            json={"identifier": "admin@example.test", "password": "wrong password"},
        )
        service.rate_limited = True
        limited = client.post(
            "/api/v1/auth/login",
            json={"identifier": "admin@example.test", "password": "wrong password"},
        )

    assert missing.status_code == existing.status_code == 401
    assert missing.json()["code"] == existing.json()["code"] == "INVALID_CREDENTIALS"
    assert missing.json()["message"] == existing.json()["message"]
    assert limited.status_code == 429
    assert limited.headers["retry-after"] == "900"


def test_logout_forwards_session_and_csrf_then_clears_cookie() -> None:
    service = StubAuthService()
    with auth_client(service) as client:
        client.cookies.set("yaqin_session", "opaque-session-value")
        response = client.post(
            "/api/v1/auth/logout",
            headers={"X-CSRF-Token": "session-bound-csrf"},
        )

    assert response.status_code == 204
    assert service.logout_arguments == ("opaque-session-value", "session-bound-csrf")
    assert "yaqin_session=" in response.headers["set-cookie"]


def test_recovery_response_is_identical_and_token_only_reaches_delivery_boundary() -> None:
    service = StubAuthService()
    delivery = CapturingDelivery()
    with auth_client(service, delivery) as client:
        missing = client.post(
            "/api/v1/auth/password-recovery",
            json={"identifier": "missing@example.test"},
        )
        service.recovery_challenge = RecoveryChallenge(
            identifier="admin@example.test",
            token="secret-recovery-token",
            expires_at=EXPIRES_AT,
        )
        existing = client.post(
            "/api/v1/auth/password-recovery",
            json={"identifier": "admin@example.test"},
        )

    assert missing.status_code == existing.status_code == 202
    assert missing.json()["data"] == existing.json()["data"]
    assert "secret-recovery-token" not in existing.text
    assert delivery.delivered == [service.recovery_challenge]
