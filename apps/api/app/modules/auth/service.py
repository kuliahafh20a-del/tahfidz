"""Authentication use cases with generic failures and database-backed state."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import Settings
from app.core.time import utc_now
from app.modules.auth.models import AuthRateLimitEvent, AuthSession, PasswordRecoveryToken
from app.modules.auth.schemas import (
    RoleContext,
    RoleContextSelection,
    SessionResponse,
    SessionUser,
)
from app.modules.auth.security import OpaqueTokenManager, PasswordManager
from app.modules.identity.models import AccountStatus, RoleGrant, User
from app.modules.organizations.models import Organization, OrganizationStatus


class InvalidCredentialsError(ValueError):
    """Keep all login failures externally indistinguishable."""


class AuthenticationRequiredError(ValueError):
    """The opaque session is absent, expired, revoked, or belongs to an inactive user."""


class CsrfTokenInvalidError(ValueError):
    """The mutation did not prove knowledge of the session-bound CSRF token."""


class RecoveryTokenInvalidError(ValueError):
    """The reset capability is absent, expired, or already consumed."""


class ActiveContextInvalidError(ValueError):
    """A requested role and organization pair is not currently granted."""


class RateLimitExceededError(ValueError):
    """An authentication boundary received too many attempts."""

    def __init__(self, retry_after: int) -> None:
        super().__init__("rate limit exceeded")
        self.retry_after = retry_after


@dataclass(frozen=True, slots=True)
class IssuedSession:
    session_token: str
    payload: SessionResponse


@dataclass(frozen=True, slots=True)
class AuthenticatedSession:
    session_id: UUID
    user_id: UUID
    active_context: RoleContext | None
    role_contexts: tuple[RoleContext, ...]
    csrf_token: str
    csrf_token_hash: str
    expires_at: datetime
    user: User


@dataclass(frozen=True, slots=True)
class RecoveryChallenge:
    """A token for delivery by trusted infrastructure; routers never return it."""

    identifier: str
    token: str
    expires_at: datetime


class AuthService:
    """Own password, session, CSRF, rate-limit, and recovery invariants."""

    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        password_manager: PasswordManager | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.passwords = password_manager or PasswordManager()
        self.session_tokens = OpaqueTokenManager(settings.session_secret_value)
        self.csrf_tokens = OpaqueTokenManager(settings.csrf_secret_value)

    async def login(self, identifier: str, password: str, client_address: str) -> IssuedSession:
        now = utc_now()
        normalized = identifier.strip().casefold()
        await self._consume_rate_limit(
            action="login",
            identity=normalized,
            client_address=client_address,
            limit=self.settings.login_rate_limit_attempts,
            window_seconds=self.settings.login_rate_limit_window_seconds,
            now=now,
        )
        user = await self.session.scalar(
            select(User).where(func.lower(User.login_identifier) == normalized)
        )
        password_hash = user.password_hash if user is not None and user.password_hash else None
        password_matches = self.passwords.verify(
            password_hash or self.passwords.dummy_hash, password
        )
        if (
            user is None
            or user.account_status is not AccountStatus.ACTIVE
            or password_hash is None
            or not password_matches
        ):
            await self.session.commit()
            raise InvalidCredentialsError("invalid credentials")

        role_contexts = await self._role_contexts(user.id, now)
        active_context = role_contexts[0] if role_contexts else None
        if self.passwords.needs_rehash(password_hash):
            user.password_hash = self.passwords.hash(password)
        user.last_login_at = now
        issued = self._new_session(user, active_context, now=now)
        self.session.add(issued[0])
        await self._clear_rate_limit("login", normalized, client_address)
        await self.session.commit()
        return IssuedSession(
            session_token=issued[1],
            payload=self._session_response(
                user,
                role_contexts,
                active_context,
                issued[2],
                issued[0].expires_at,
            ),
        )

    async def authenticate(self, session_token: str | None) -> AuthenticatedSession:
        if not session_token:
            raise AuthenticationRequiredError("session required")
        now = utc_now()
        record = await self.session.scalar(
            select(AuthSession)
            .where(AuthSession.token_hash == self.session_tokens.digest(session_token))
            .options(joinedload(AuthSession.user))
        )
        if record is None or record.revoked_at is not None or record.expires_at <= now:
            raise AuthenticationRequiredError("session invalid")
        if record.user.account_status is not AccountStatus.ACTIVE:
            record.revoked_at = now
            await self.session.commit()
            raise AuthenticationRequiredError("session invalid")

        role_contexts = await self._role_contexts(record.user_id, now)
        active_context = next(
            (
                item
                for item in role_contexts
                if item.role == record.active_role
                and item.organization_id == record.active_organization_id
            ),
            None,
        )
        csrf_token = self.csrf_tokens.digest(session_token)
        if not self.csrf_tokens.matches(record.csrf_token_hash, csrf_token):
            raise AuthenticationRequiredError("session invalid")
        return AuthenticatedSession(
            session_id=record.id,
            user_id=record.user_id,
            active_context=active_context,
            role_contexts=tuple(role_contexts),
            csrf_token=csrf_token,
            csrf_token_hash=record.csrf_token_hash,
            expires_at=record.expires_at,
            user=record.user,
        )

    async def session_payload(self, session_token: str | None) -> SessionResponse:
        authenticated = await self.authenticate(session_token)
        return self._session_response(
            authenticated.user,
            list(authenticated.role_contexts),
            authenticated.active_context,
            authenticated.csrf_token,
            authenticated.expires_at,
        )

    async def logout(self, session_token: str | None, csrf_token: str | None) -> None:
        authenticated = await self.authenticate(session_token)
        self.require_csrf(authenticated, csrf_token)
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == authenticated.session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
        await self.session.commit()

    async def rotate(
        self,
        session_token: str | None,
        csrf_token: str | None,
        selection: RoleContextSelection | None,
    ) -> IssuedSession:
        authenticated = await self.authenticate(session_token)
        self.require_csrf(authenticated, csrf_token)
        active_context = authenticated.active_context
        if selection is not None:
            active_context = next(
                (
                    item
                    for item in authenticated.role_contexts
                    if item.role == selection.role
                    and item.organization_id == selection.organization_id
                ),
                None,
            )
            if active_context is None:
                raise ActiveContextInvalidError("active context is not granted")

        now = utc_now()
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.id == authenticated.session_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        record, raw_token, csrf = self._new_session(
            authenticated.user,
            active_context,
            now=now,
            expires_at=authenticated.expires_at,
            rotated_from_id=authenticated.session_id,
        )
        self.session.add(record)
        await self.session.commit()
        return IssuedSession(
            session_token=raw_token,
            payload=self._session_response(
                authenticated.user,
                list(authenticated.role_contexts),
                active_context,
                csrf,
                record.expires_at,
            ),
        )

    async def request_password_recovery(
        self,
        identifier: str,
        client_address: str,
    ) -> RecoveryChallenge | None:
        now = utc_now()
        normalized = identifier.strip().casefold()
        await self._consume_rate_limit(
            action="recovery",
            identity=normalized,
            client_address=client_address,
            limit=self.settings.recovery_rate_limit_attempts,
            window_seconds=self.settings.recovery_rate_limit_window_seconds,
            now=now,
        )
        user = await self.session.scalar(
            select(User).where(func.lower(User.login_identifier) == normalized)
        )
        challenge: RecoveryChallenge | None = None
        if user is not None and user.account_status is AccountStatus.ACTIVE:
            await self.session.execute(
                update(PasswordRecoveryToken)
                .where(
                    PasswordRecoveryToken.user_id == user.id,
                    PasswordRecoveryToken.used_at.is_(None),
                )
                .values(used_at=now)
            )
            raw_token = self.session_tokens.generate()
            expires_at = now + timedelta(seconds=self.settings.recovery_token_ttl_seconds)
            self.session.add(
                PasswordRecoveryToken(
                    user_id=user.id,
                    token_hash=self.session_tokens.digest(raw_token),
                    expires_at=expires_at,
                )
            )
            challenge = RecoveryChallenge(normalized, raw_token, expires_at)
        await self.session.commit()
        return challenge

    async def reset_password(
        self,
        token: str,
        new_password: str,
        client_address: str,
    ) -> None:
        now = utc_now()
        token_fingerprint = self.session_tokens.digest(token)
        await self._consume_rate_limit(
            action="reset",
            identity=token_fingerprint,
            client_address=client_address,
            limit=self.settings.recovery_rate_limit_attempts,
            window_seconds=self.settings.recovery_rate_limit_window_seconds,
            now=now,
        )
        recovery = await self.session.scalar(
            select(PasswordRecoveryToken)
            .where(PasswordRecoveryToken.token_hash == token_fingerprint)
            .with_for_update()
        )
        if recovery is None or recovery.used_at is not None or recovery.expires_at <= now:
            await self.session.commit()
            raise RecoveryTokenInvalidError("recovery token invalid")
        user = await self.session.get(User, recovery.user_id, with_for_update=True)
        if user is None or user.account_status is not AccountStatus.ACTIVE:
            recovery.used_at = now
            await self.session.commit()
            raise RecoveryTokenInvalidError("recovery token invalid")

        user.password_hash = self.passwords.hash(new_password)
        recovery.used_at = now
        await self.session.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        await self.session.execute(
            update(PasswordRecoveryToken)
            .where(
                PasswordRecoveryToken.user_id == user.id,
                PasswordRecoveryToken.used_at.is_(None),
            )
            .values(used_at=now)
        )
        await self._clear_rate_limit("reset", token_fingerprint, client_address)
        await self.session.commit()

    def require_csrf(
        self,
        authenticated: AuthenticatedSession,
        csrf_token: str | None,
    ) -> None:
        if csrf_token is None or not self.csrf_tokens.matches(
            authenticated.csrf_token_hash,
            csrf_token,
        ):
            raise CsrfTokenInvalidError("csrf token invalid")

    def _new_session(
        self,
        user: User,
        active_context: RoleContext | None,
        *,
        now: datetime,
        expires_at: datetime | None = None,
        rotated_from_id: UUID | None = None,
    ) -> tuple[AuthSession, str, str]:
        raw_token = self.session_tokens.generate()
        csrf_token = self.csrf_tokens.digest(raw_token)
        expiry = expires_at or (now + timedelta(seconds=self.settings.session_ttl_seconds))
        record = AuthSession(
            user_id=user.id,
            token_hash=self.session_tokens.digest(raw_token),
            csrf_token_hash=self.csrf_tokens.digest(csrf_token),
            active_role=active_context.role if active_context else None,
            active_organization_id=active_context.organization_id if active_context else None,
            expires_at=expiry,
            last_seen_at=now,
            rotated_from_id=rotated_from_id,
        )
        return record, raw_token, csrf_token

    async def _role_contexts(self, user_id: UUID, now: datetime) -> list[RoleContext]:
        rows = await self.session.execute(
            select(RoleGrant.role, Organization.id, Organization.name)
            .join(Organization, Organization.id == RoleGrant.organization_id)
            .where(
                RoleGrant.user_id == user_id,
                RoleGrant.valid_from <= now,
                or_(RoleGrant.valid_to.is_(None), RoleGrant.valid_to > now),
                Organization.status == OrganizationStatus.ACTIVE,
            )
            .order_by(RoleGrant.role, Organization.name)
        )
        return [
            RoleContext(role=row.role, organization_id=row.id, organization_name=row.name)
            for row in rows
        ]

    def _session_response(
        self,
        user: User,
        role_contexts: list[RoleContext],
        active_context: RoleContext | None,
        csrf_token: str,
        expires_at: datetime,
    ) -> SessionResponse:
        return SessionResponse(
            user=SessionUser(
                id=user.id,
                display_name=user.name,
                login_identifier=user.login_identifier,
                roles=role_contexts,
            ),
            active_context=active_context,
            csrf_token=csrf_token,
            expires_at=expires_at,
        )

    async def _consume_rate_limit(
        self,
        *,
        action: str,
        identity: str,
        client_address: str,
        limit: int,
        window_seconds: int,
        now: datetime,
    ) -> None:
        identity_fingerprint = self.session_tokens.digest(f"identity:{action}:{identity}")
        client_fingerprint = self.session_tokens.digest(f"client:{action}:{client_address}")
        cutoff = now - timedelta(seconds=window_seconds)
        identity_count = await self.session.scalar(
            select(func.count(AuthRateLimitEvent.id)).where(
                AuthRateLimitEvent.action == action,
                AuthRateLimitEvent.identity_fingerprint == identity_fingerprint,
                AuthRateLimitEvent.occurred_at >= cutoff,
            )
        )
        client_count = await self.session.scalar(
            select(func.count(AuthRateLimitEvent.id)).where(
                AuthRateLimitEvent.action == action,
                AuthRateLimitEvent.client_fingerprint == client_fingerprint,
                AuthRateLimitEvent.occurred_at >= cutoff,
            )
        )
        if max(identity_count or 0, client_count or 0) >= limit:
            raise RateLimitExceededError(window_seconds)
        self.session.add(
            AuthRateLimitEvent(
                action=action,
                identity_fingerprint=identity_fingerprint,
                client_fingerprint=client_fingerprint,
                occurred_at=now,
            )
        )

    async def _clear_rate_limit(
        self,
        action: str,
        identity: str,
        client_address: str,
    ) -> None:
        identity_fingerprint = self.session_tokens.digest(f"identity:{action}:{identity}")
        client_fingerprint = self.session_tokens.digest(f"client:{action}:{client_address}")
        await self.session.execute(
            delete(AuthRateLimitEvent).where(
                AuthRateLimitEvent.action == action,
                AuthRateLimitEvent.identity_fingerprint == identity_fingerprint,
                AuthRateLimitEvent.client_fingerprint == client_fingerprint,
            )
        )
