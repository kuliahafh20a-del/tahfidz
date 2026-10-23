"""HTTP routes for academic video assessments and private feedback playback."""

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
from app.modules.media.storage import S3ObjectStorage
from app.modules.mentoring.access import MentorActorDependency
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)
from app.modules.video_assessments.schemas import (
    VideoAssessmentDraftCreate,
    VideoAssessmentDraftUpdate,
    VideoAssessmentFinalize,
    VideoAssessmentPlayback,
    VideoAssessmentResponse,
)
from app.modules.video_assessments.service import (
    VideoAssessmentConflictError,
    VideoAssessmentNotFoundError,
    VideoAssessmentService,
    VideoAssessmentVersionConflictError,
)

router = APIRouter(tags=["video assessments"])


def get_video_assessment_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> VideoAssessmentService:
    return VideoAssessmentService(session, S3ObjectStorage(settings))


VideoAssessmentServiceDependency = Annotated[
    VideoAssessmentService, Depends(get_video_assessment_service)
]


def raise_video_assessment_error(error: Exception) -> NoReturn:
    if isinstance(error, VideoAssessmentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": str(error)},
        ) from error
    if isinstance(error, VideoAssessmentVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "ASSESSMENT_VERSION_CONFLICT",
                "message": "Penilaian telah berubah. Muat ulang sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi penilaian tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "PREREQUISITE_NOT_MET", "message": str(error)},
    ) from error


@router.post(
    "/video-versions/{video_version_id}/assessment",
    response_model=SuccessEnvelope[VideoAssessmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_video_assessment(
    video_version_id: UUID,
    payload: VideoAssessmentDraftCreate,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAssessmentResponse]:
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
            return success(request, VideoAssessmentResponse.model_validate(claim.replay_body))
        result = await service.create_draft(actor, video_version_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (VideoAssessmentNotFoundError, VideoAssessmentConflictError) as error:
        raise_video_assessment_error(error)


@router.get(
    "/video-assessments/{assessment_id}",
    response_model=SuccessEnvelope[VideoAssessmentResponse],
)
async def read_video_assessment(
    assessment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
) -> SuccessEnvelope[VideoAssessmentResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_for_mentor(actor, assessment_id)
    except VideoAssessmentNotFoundError as error:
        raise_video_assessment_error(error)
    return success(request, result, version=result.row_version)


@router.patch(
    "/video-assessments/{assessment_id}",
    response_model=SuccessEnvelope[VideoAssessmentResponse],
)
async def update_video_assessment(
    assessment_id: UUID,
    payload: VideoAssessmentDraftUpdate,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAssessmentResponse]:
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
            return success(request, VideoAssessmentResponse.model_validate(claim.replay_body))
        result = await service.update_draft(actor, assessment_id, payload, request_id(request))
        await idempotency.complete(
            claim, response_body=result.model_dump(mode="json"), response_status=status.HTTP_200_OK
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (VideoAssessmentNotFoundError, VideoAssessmentConflictError) as error:
        raise_video_assessment_error(error)


@router.post(
    "/video-assessments/{assessment_id}/finalize",
    response_model=SuccessEnvelope[VideoAssessmentResponse],
)
async def finalize_video_assessment(
    assessment_id: UUID,
    payload: VideoAssessmentFinalize,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAssessmentResponse]:
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
            return success(request, VideoAssessmentResponse.model_validate(claim.replay_body))
        result = await service.finalize(
            actor, assessment_id, payload.expected_version, request_id(request)
        )
        await idempotency.complete(
            claim, response_body=result.model_dump(mode="json"), response_status=status.HTTP_200_OK
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (VideoAssessmentNotFoundError, VideoAssessmentConflictError) as error:
        raise_video_assessment_error(error)


@router.get(
    "/mentor/video-assessments",
    response_model=SuccessEnvelope[list[VideoAssessmentResponse]],
)
async def list_mentor_video_assessments(
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
) -> SuccessEnvelope[list[VideoAssessmentResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_for_mentor(actor))


@router.get(
    "/me/video-assessment-results",
    response_model=SuccessEnvelope[list[VideoAssessmentResponse]],
)
async def list_my_video_assessment_results(
    request: Request,
    actor: ParticipantActorDependency,
    service: VideoAssessmentServiceDependency,
) -> SuccessEnvelope[list[VideoAssessmentResponse]]:
    require_query_allowlist(request, set())
    return success(request, await service.list_for_participant(actor))


@router.get(
    "/enrollments/{enrollment_id}/video-assessment-history",
    response_model=SuccessEnvelope[list[VideoAssessmentResponse]],
)
async def read_video_assessment_history(
    enrollment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
) -> SuccessEnvelope[list[VideoAssessmentResponse]]:
    require_query_allowlist(request, set())
    try:
        return success(request, await service.history_for_mentor(actor, enrollment_id))
    except VideoAssessmentNotFoundError as error:
        raise_video_assessment_error(error)


@router.post(
    "/video-assessments/{assessment_id}/audio/playback-url",
    response_model=SuccessEnvelope[VideoAssessmentPlayback],
)
async def mentor_video_assessment_audio(
    assessment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: VideoAssessmentServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAssessmentPlayback]:
    try:
        return success(
            request, await service.playback_for_mentor(actor, assessment_id, request_id(request))
        )
    except (VideoAssessmentNotFoundError, VideoAssessmentConflictError) as error:
        raise_video_assessment_error(error)


@router.post(
    "/me/video-assessments/{assessment_id}/audio/playback-url",
    response_model=SuccessEnvelope[VideoAssessmentPlayback],
)
async def participant_video_assessment_audio(
    assessment_id: UUID,
    request: Request,
    actor: ParticipantActorDependency,
    service: VideoAssessmentServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[VideoAssessmentPlayback]:
    try:
        return success(
            request,
            await service.playback_for_participant(actor, assessment_id, request_id(request)),
        )
    except (VideoAssessmentNotFoundError, VideoAssessmentConflictError) as error:
        raise_video_assessment_error(error)
