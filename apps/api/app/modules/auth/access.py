"""Reusable authenticated-session and CSRF request boundaries."""

from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status

from app.modules.auth.dependencies import AuthServiceDependency
from app.modules.auth.service import (
    AuthenticatedSession,
    AuthenticationRequiredError,
    CsrfTokenInvalidError,
)

SESSION_COOKIE_NAME = "yaqin_session"


async def get_authenticated_session(
    service: AuthServiceDependency,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> AuthenticatedSession:
    try:
        return await service.authenticate(session_token)
    except AuthenticationRequiredError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required"},
            headers={"Cache-Control": "no-store"},
        ) from error


AuthenticatedSessionDependency = Annotated[
    AuthenticatedSession,
    Depends(get_authenticated_session),
]


async def require_csrf(
    authenticated: AuthenticatedSessionDependency,
    service: AuthServiceDependency,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> AuthenticatedSession:
    try:
        service.require_csrf(authenticated, csrf_token)
    except CsrfTokenInvalidError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_token_invalid"},
            headers={"Cache-Control": "no-store"},
        ) from error
    return authenticated


CsrfProtectionDependency = Annotated[AuthenticatedSession, Depends(require_csrf)]
