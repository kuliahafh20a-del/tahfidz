"""Browser authentication, session rotation, CSRF, and account recovery endpoints."""

from typing import Annotated, NoReturn

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status

from app.api.contracts import SuccessEnvelope, success
from app.core.config import Settings, get_settings
from app.modules.auth.access import SESSION_COOKIE_NAME
from app.modules.auth.delivery import RecoveryTokenDeliveryDependency
from app.modules.auth.dependencies import AuthServiceDependency
from app.modules.auth.schemas import (
    GenericAuthResponse,
    LoginRequest,
    PasswordRecoveryRequest,
    PasswordResetRequest,
    SessionResponse,
    SessionRotateRequest,
)
from app.modules.auth.service import (
    ActiveContextInvalidError,
    AuthenticationRequiredError,
    CsrfTokenInvalidError,
    InvalidCredentialsError,
    IssuedSession,
    RateLimitExceededError,
    RecoveryTokenInvalidError,
)

router = APIRouter(prefix="/auth", tags=["authentication"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]
GENERIC_RECOVERY_MESSAGE = (
    "Jika akun memenuhi syarat, instruksi pemulihan akan dikirim melalui kanal terdaftar."
)


def _client_address(request: Request) -> str:
    return request.client.host if request.client is not None else "unknown"


def _set_session_cookie(response: Response, issued: IssuedSession, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=issued.session_token,
        max_age=settings.session_ttl_seconds,
        expires=issued.payload.expires_at,
        path="/",
        secure=settings.secure_auth_cookie,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


def _delete_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        secure=settings.secure_auth_cookie,
        httponly=True,
        samesite="lax",
    )
    response.headers["Cache-Control"] = "no-store"


def _raise_auth_error(error: Exception) -> NoReturn:
    if isinstance(error, RateLimitExceededError):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={"code": "rate_limit_exceeded"},
            headers={"Retry-After": str(error.retry_after), "Cache-Control": "no-store"},
        ) from error
    if isinstance(error, InvalidCredentialsError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_credentials", "message": "Identifier atau kata sandi salah."},
            headers={"Cache-Control": "no-store"},
        ) from error
    if isinstance(error, AuthenticationRequiredError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required"},
            headers={"Cache-Control": "no-store"},
        ) from error
    if isinstance(error, CsrfTokenInvalidError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "csrf_token_invalid"},
            headers={"Cache-Control": "no-store"},
        ) from error
    if isinstance(error, ActiveContextInvalidError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "active_context_invalid"},
            headers={"Cache-Control": "no-store"},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail={"code": "recovery_token_invalid"},
        headers={"Cache-Control": "no-store"},
    ) from error


@router.post("/login", response_model=SuccessEnvelope[SessionResponse])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[SessionResponse]:
    try:
        issued = await service.login(payload.identifier, payload.password, _client_address(request))
    except (InvalidCredentialsError, RateLimitExceededError) as error:
        _raise_auth_error(error)
    _set_session_cookie(response, issued, settings)
    return success(request, issued.payload)


@router.get("/session", response_model=SuccessEnvelope[SessionResponse])
async def read_session(
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
) -> SuccessEnvelope[SessionResponse]:
    try:
        payload = await service.session_payload(session_token)
    except AuthenticationRequiredError as error:
        _raise_auth_error(error)
    response.headers["Cache-Control"] = "no-store"
    return success(request, payload)


@router.post("/session/rotate", response_model=SuccessEnvelope[SessionResponse])
async def rotate_session(
    payload: SessionRotateRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    settings: SettingsDependency,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> SuccessEnvelope[SessionResponse]:
    try:
        issued = await service.rotate(session_token, csrf_token, payload.active_context)
    except (
        AuthenticationRequiredError,
        CsrfTokenInvalidError,
        ActiveContextInvalidError,
    ) as error:
        _raise_auth_error(error)
    _set_session_cookie(response, issued, settings)
    return success(request, issued.payload)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    service: AuthServiceDependency,
    settings: SettingsDependency,
    session_token: Annotated[str | None, Cookie(alias=SESSION_COOKIE_NAME)] = None,
    csrf_token: Annotated[str | None, Header(alias="X-CSRF-Token")] = None,
) -> None:
    try:
        await service.logout(session_token, csrf_token)
    except (AuthenticationRequiredError, CsrfTokenInvalidError) as error:
        _raise_auth_error(error)
    _delete_session_cookie(response, settings)


@router.post(
    "/password-recovery",
    response_model=SuccessEnvelope[GenericAuthResponse],
    status_code=status.HTTP_202_ACCEPTED,
)
async def request_password_recovery(
    payload: PasswordRecoveryRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
    delivery: RecoveryTokenDeliveryDependency,
) -> SuccessEnvelope[GenericAuthResponse]:
    try:
        challenge = await service.request_password_recovery(
            payload.identifier,
            _client_address(request),
        )
    except RateLimitExceededError as error:
        _raise_auth_error(error)
    if challenge is not None:
        await delivery.deliver(challenge)
    response.headers["Cache-Control"] = "no-store"
    return success(request, GenericAuthResponse(message=GENERIC_RECOVERY_MESSAGE))


@router.post("/password-reset", response_model=SuccessEnvelope[GenericAuthResponse])
async def reset_password(
    payload: PasswordResetRequest,
    request: Request,
    response: Response,
    service: AuthServiceDependency,
) -> SuccessEnvelope[GenericAuthResponse]:
    try:
        await service.reset_password(payload.token, payload.new_password, _client_address(request))
    except (RecoveryTokenInvalidError, RateLimitExceededError) as error:
        _raise_auth_error(error)
    response.headers["Cache-Control"] = "no-store"
    return success(
        request,
        GenericAuthResponse(message="Kata sandi berhasil diperbarui. Silakan masuk kembali."),
    )
