"""Theme-assessment commands and participant/mentor result projections."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import IdempotencyKey, SuccessEnvelope, request_id, success
from app.api.pagination import (
    CursorCodec,
    CursorPage,
    PaginationParams,
    paginate_sequence,
    require_query_allowlist,
)
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.assessments.schemas import (
    MentorParticipantResponse,
    ThemeAssessmentDraftCreate,
    ThemeAssessmentDraftUpdate,
    ThemeAssessmentFinalize,
    ThemeAssessmentResponse,
)
from app.modules.assessments.service import (
    AssessmentConflictError,
    AssessmentResourceNotFoundError,
    AssessmentVersionConflictError,
    ThemeAssessmentService,
)
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.calendar.access import ParticipantActorDependency
from app.modules.cohorts.router import raise_idempotency_error
from app.modules.mentoring.access import MentorActorDependency
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)

router = APIRouter(tags=["theme assessments"])


def get_theme_assessment_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ThemeAssessmentService:
    return ThemeAssessmentService(session)


ThemeAssessmentServiceDependency = Annotated[
    ThemeAssessmentService, Depends(get_theme_assessment_service)
]
PaginationDependency = Annotated[PaginationParams, Depends()]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def raise_assessment_error(error: Exception) -> NoReturn:
    if isinstance(error, AssessmentResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "RESOURCE_NOT_FOUND",
                "message": "Penilaian tidak tersedia dalam assignment aktif.",
            },
        ) from error
    if isinstance(error, AssessmentVersionConflictError):
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
    "/sessions/{session_id}/theme-assessments",
    response_model=SuccessEnvelope[ThemeAssessmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_theme_assessment(
    session_id: UUID,
    payload: ThemeAssessmentDraftCreate,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ThemeAssessmentResponse]:
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
            return success(request, ThemeAssessmentResponse.model_validate(claim.replay_body))
        result = await service.create_draft(actor, session_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (AssessmentResourceNotFoundError, AssessmentConflictError) as error:
        raise_assessment_error(error)


@router.get(
    "/sessions/{session_id}/theme-assessments",
    response_model=SuccessEnvelope[list[ThemeAssessmentResponse]],
)
async def list_session_theme_assessments(
    session_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
) -> SuccessEnvelope[list[ThemeAssessmentResponse]]:
    require_query_allowlist(request, set())
    try:
        return success(request, await service.list_for_session(actor, session_id))
    except AssessmentResourceNotFoundError as error:
        raise_assessment_error(error)


@router.get(
    "/theme-assessments/{assessment_id}",
    response_model=SuccessEnvelope[ThemeAssessmentResponse],
)
async def read_theme_assessment(
    assessment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
) -> SuccessEnvelope[ThemeAssessmentResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_for_mentor(actor, assessment_id)
        return success(request, result, version=result.row_version)
    except AssessmentResourceNotFoundError as error:
        raise_assessment_error(error)


@router.patch(
    "/theme-assessments/{assessment_id}",
    response_model=SuccessEnvelope[ThemeAssessmentResponse],
)
async def update_theme_assessment(
    assessment_id: UUID,
    payload: ThemeAssessmentDraftUpdate,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ThemeAssessmentResponse]:
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
            return success(request, ThemeAssessmentResponse.model_validate(claim.replay_body))
        result = await service.update_draft(actor, assessment_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (AssessmentResourceNotFoundError, AssessmentConflictError) as error:
        raise_assessment_error(error)


@router.post(
    "/theme-assessments/{assessment_id}/finalize",
    response_model=SuccessEnvelope[ThemeAssessmentResponse],
)
async def finalize_theme_assessment(
    assessment_id: UUID,
    payload: ThemeAssessmentFinalize,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[ThemeAssessmentResponse]:
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
            return success(request, ThemeAssessmentResponse.model_validate(claim.replay_body))
        result = await service.finalize(
            actor, assessment_id, payload.expected_version, request_id(request)
        )
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (AssessmentResourceNotFoundError, AssessmentConflictError) as error:
        raise_assessment_error(error)


@router.get(
    "/me/theme-results",
    response_model=SuccessEnvelope[CursorPage[ThemeAssessmentResponse]],
)
async def list_my_theme_results(
    request: Request,
    actor: ParticipantActorDependency,
    service: ThemeAssessmentServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[ThemeAssessmentResponse]]:
    require_query_allowlist(request, {"cursor", "limit"})
    try:
        items = await service.list_participant_results(actor)
    except AssessmentResourceNotFoundError as error:
        raise_assessment_error(error)
    return success(
        request,
        paginate_sequence(
            items,
            pagination,
            CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
            scope=f"participant:{actor.user_id}:theme-results",
        ),
    )


@router.get(
    "/mentor/participants",
    response_model=SuccessEnvelope[CursorPage[MentorParticipantResponse]],
)
async def list_mentor_participants(
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[MentorParticipantResponse]]:
    require_query_allowlist(request, {"cursor", "limit"})
    items = await service.list_mentor_participants(actor)
    return success(
        request,
        paginate_sequence(
            items,
            pagination,
            CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
            scope=f"mentor:{actor.user_id}:participants",
        ),
    )


@router.get(
    "/mentor/participants/{enrollment_id}",
    response_model=SuccessEnvelope[MentorParticipantResponse],
)
async def read_mentor_participant(
    enrollment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
) -> SuccessEnvelope[MentorParticipantResponse]:
    require_query_allowlist(request, set())
    try:
        return success(request, await service.get_mentor_participant(actor, enrollment_id))
    except AssessmentResourceNotFoundError as error:
        raise_assessment_error(error)


@router.get(
    "/enrollments/{enrollment_id}/assessment-history",
    response_model=SuccessEnvelope[CursorPage[ThemeAssessmentResponse]],
)
async def read_assessment_history(
    enrollment_id: UUID,
    request: Request,
    actor: MentorActorDependency,
    service: ThemeAssessmentServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[ThemeAssessmentResponse]]:
    require_query_allowlist(request, {"cursor", "limit"})
    try:
        items = await service.assessment_history(actor, enrollment_id)
    except AssessmentResourceNotFoundError as error:
        raise_assessment_error(error)
    return success(
        request,
        paginate_sequence(
            items,
            pagination,
            CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
            scope=f"mentor:{actor.user_id}:enrollment:{enrollment_id}:assessment-history",
        ),
    )
