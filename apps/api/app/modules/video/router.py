"""Participant video-attempt endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import IdempotencyKey, SuccessEnvelope, request_id, success
from app.api.pagination import require_query_allowlist
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.calendar.access import ParticipantActorDependency
from app.modules.cohorts.router import raise_idempotency_error
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)
from app.modules.video.schemas import (
    VideoAttemptCreate,
    VideoAttemptResponse,
    VideoVersionCreate,
)
from app.modules.video.service import (
    VideoConflictError,
    VideoResourceNotFoundError,
    VideoSubmissionService,
    VideoUrlNotAllowedError,
    VideoVersionConflictError,
)

router = APIRouter(tags=["video submissions"])


def get_video_submission_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VideoSubmissionService:
    return VideoSubmissionService(session, settings.video_allowed_host_values)


VideoServiceDependency = Annotated[VideoSubmissionService, Depends(get_video_submission_service)]


def raise_video_error(error: Exception) -> NoReturn:
    if isinstance(error, VideoResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, VideoVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VIDEO_VERSION_CONFLICT",
                "message": "Kiriman telah berubah. Muat ulang sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi kiriman tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    if isinstance(error, VideoUrlNotAllowedError):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "VIDEO_URL_NOT_ALLOWED",
                "message": "Host tautan video tidak diizinkan.",
                "field_errors": {"video_url": [str(error)]},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "PREREQUISITE_NOT_MET", "message": str(error)},
    ) from error


@router.post(
    "/video-attempts",
    response_model=SuccessEnvelope[VideoAttemptResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_video_attempt(
    payload: VideoAttemptCreate,
    request: Request,
    actor: ParticipantActorDependency,
    service: VideoServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAttemptResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, VideoAttemptResponse.model_validate(claim.replay_body))
        result = await service.create_attempt(actor, payload.part_id, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (VideoResourceNotFoundError, VideoConflictError) as error:
        raise_video_error(error)


@router.get(
    "/video-attempts/{attempt_id}",
    response_model=SuccessEnvelope[VideoAttemptResponse],
)
async def read_video_attempt(
    attempt_id: UUID,
    request: Request,
    actor: ParticipantActorDependency,
    service: VideoServiceDependency,
) -> SuccessEnvelope[VideoAttemptResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_attempt(actor, attempt_id)
        return success(request, result, version=result.row_version)
    except VideoResourceNotFoundError as error:
        raise_video_error(error)


@router.post(
    "/video-attempts/{attempt_id}/versions",
    response_model=SuccessEnvelope[VideoAttemptResponse],
    status_code=status.HTTP_201_CREATED,
)
async def submit_video_version(
    attempt_id: UUID,
    payload: VideoVersionCreate,
    request: Request,
    actor: ParticipantActorDependency,
    service: VideoServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAttemptResponse]:
    try:
        claim = await idempotency.claim(
            actor_id=actor.user_id,
            idempotency_key=idempotency_key,
            method=request.method,
            normalized_path=request.url.path,
            payload=payload.model_dump(mode="json"),
            request_id=request_id(request),
        )
        if claim.replay_body is not None:
            return success(request, VideoAttemptResponse.model_validate(claim.replay_body))
        result = await service.submit_version(actor, attempt_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (
        VideoResourceNotFoundError,
        VideoConflictError,
        VideoUrlNotAllowedError,
    ) as error:
        raise_video_error(error)
