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
from app.modules.mentoring.access import MentorActorDependency
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)
from app.modules.video.schemas import (
    EligibilityDraftUpdate,
    EligibilityFinalize,
    VideoAttemptCreate,
    VideoAttemptResponse,
    VideoEligibilityResponse,
    VideoVersionCreate,
)
from app.modules.video.service import (
    EligibilityVersionConflictError,
    VideoConflictError,
    VideoEligibilityService,
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


def get_video_eligibility_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> VideoEligibilityService:
    return VideoEligibilityService(session)


EligibilityServiceDependency = Annotated[
    VideoEligibilityService, Depends(get_video_eligibility_service)
]


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
    if isinstance(error, EligibilityVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ELIGIBILITY_VERSION_CONFLICT",
                "message": "Review kelayakan telah berubah. Muat ulang sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi review tidak lagi berlaku."]},
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


@router.get(
    "/mentor/video-versions",
    response_model=SuccessEnvelope[list[VideoEligibilityResponse]],
)
async def list_mentor_video_versions(
    request: Request,
    actor: MentorActorDependency,
    service: EligibilityServiceDependency,
) -> SuccessEnvelope[list[VideoEligibilityResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_for_mentor(actor))


@router.get(
    "/me/video-results",
    response_model=SuccessEnvelope[list[VideoEligibilityResponse]],
)
async def list_participant_video_results(
    request: Request,
    actor: ParticipantActorDependency,
    service: EligibilityServiceDependency,
) -> SuccessEnvelope[list[VideoEligibilityResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_for_participant(actor))


@router.get(
    "/video-versions/{video_version_id}",
    response_model=SuccessEnvelope[VideoEligibilityResponse],
)
async def read_video_version(
    video_version_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: EligibilityServiceDependency,
) -> SuccessEnvelope[VideoEligibilityResponse]:
    require_query_allowlist(request, set())
    try:
        return success(request, await service.get_for_mentor(actor, video_version_id))
    except VideoResourceNotFoundError as error:
        raise_video_error(error)


@router.put(
    "/video-versions/{video_version_id}/eligibility-draft",
    response_model=SuccessEnvelope[VideoEligibilityResponse],
)
async def save_eligibility_draft(
    video_version_id: UUID,
    payload: EligibilityDraftUpdate,
    request: Request,
    actor: MentorActorDependency,
    service: EligibilityServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoEligibilityResponse]:
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
            return success(request, VideoEligibilityResponse.model_validate(claim.replay_body))
        result = await service.save_draft(actor, video_version_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(
            request,
            result,
            version=result.review.row_version if result.review else None,
        )
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (
        VideoResourceNotFoundError,
        VideoConflictError,
        EligibilityVersionConflictError,
    ) as error:
        raise_video_error(error)


@router.post(
    "/video-versions/{video_version_id}/eligibility",
    response_model=SuccessEnvelope[VideoEligibilityResponse],
)
async def finalize_eligibility(
    video_version_id: UUID,
    payload: EligibilityFinalize,
    request: Request,
    actor: MentorActorDependency,
    service: EligibilityServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoEligibilityResponse]:
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
            return success(request, VideoEligibilityResponse.model_validate(claim.replay_body))
        result = await service.finalize(actor, video_version_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(
            request,
            result,
            version=result.review.row_version if result.review else None,
        )
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (
        VideoResourceNotFoundError,
        VideoConflictError,
        EligibilityVersionConflictError,
    ) as error:
        raise_video_error(error)
