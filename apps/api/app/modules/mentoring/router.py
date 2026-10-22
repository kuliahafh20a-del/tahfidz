"""Participant proposals and mentor session-management endpoints."""

from datetime import datetime
from typing import Annotated, Literal, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
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
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.calendar.access import ParticipantActorDependency
from app.modules.cohorts.router import raise_idempotency_error
from app.modules.mentoring.access import MentorActorDependency
from app.modules.mentoring.models import SessionStatus
from app.modules.mentoring.schemas import (
    SessionCreate,
    SessionResponse,
    SessionSchedule,
    SessionTransition,
)
from app.modules.mentoring.service import (
    MentoringSessionService,
    SessionConflictError,
    SessionResourceNotFoundError,
    SessionVersionConflictError,
)
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)

router = APIRouter(tags=["mentoring sessions"])


def get_mentoring_session_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> MentoringSessionService:
    return MentoringSessionService(session)


MentoringSessionServiceDependency = Annotated[
    MentoringSessionService,
    Depends(get_mentoring_session_service),
]
PaginationDependency = Annotated[PaginationParams, Depends()]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def raise_session_error(error: Exception) -> NoReturn:
    if isinstance(error, SessionResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND", "message": "Sesi tidak tersedia."},
        ) from error
    if isinstance(error, SessionVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "message": "Sesi telah berubah. Muat ulang sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi sesi tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "PREREQUISITE_NOT_MET", "message": str(error)},
    ) from error


@router.post(
    "/sessions",
    response_model=SuccessEnvelope[SessionResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_session(
    payload: SessionCreate,
    request: Request,
    actor: ParticipantActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
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
            return success(request, SessionResponse.model_validate(claim.replay_body))
        result = await service.create(actor, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (SessionResourceNotFoundError, SessionConflictError) as error:
        raise_session_error(error)


@router.get("/me/sessions", response_model=SuccessEnvelope[CursorPage[SessionResponse]])
async def list_my_sessions(
    request: Request,
    actor: ParticipantActorDependency,
    service: MentoringSessionServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[SessionResponse]]:
    require_query_allowlist(request, {"cursor", "limit"})
    try:
        items = await service.list_participant(actor)
    except SessionResourceNotFoundError as error:
        raise_session_error(error)
    page = paginate_sequence(
        items,
        pagination,
        CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
        scope=f"participant:{actor.user_id}:sessions",
    )
    return success(request, page)


@router.get("/sessions/{session_id}", response_model=SuccessEnvelope[SessionResponse])
async def read_session(
    session_id: UUID,
    request: Request,
    actor: ParticipantActorDependency,
    service: MentoringSessionServiceDependency,
) -> SuccessEnvelope[SessionResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.get_for_participant(actor, session_id)
        return success(request, result, version=result.row_version)
    except SessionResourceNotFoundError as error:
        raise_session_error(error)


@router.post(
    "/sessions/{session_id}/cancel",
    response_model=SuccessEnvelope[SessionResponse],
)
async def cancel_session(
    session_id: UUID,
    payload: SessionTransition,
    request: Request,
    actor: ParticipantActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
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
            return success(request, SessionResponse.model_validate(claim.replay_body))
        result = await service.cancel(actor, session_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (SessionResourceNotFoundError, SessionConflictError) as error:
        raise_session_error(error)


@router.get("/mentor/queue", response_model=SuccessEnvelope[CursorPage[SessionResponse]])
async def mentor_queue(
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
    work_type: Annotated[
        Literal["session", "video_eligibility", "video_assessment", "follow_up"], Query()
    ] = "session",
    session_status: Annotated[SessionStatus | None, Query(alias="status")] = None,
    scheduled_from: Annotated[datetime | None, Query()] = None,
    scheduled_to: Annotated[datetime | None, Query()] = None,
    query: Annotated[str | None, Query(alias="q", min_length=1, max_length=100)] = None,
) -> SuccessEnvelope[CursorPage[SessionResponse]]:
    require_query_allowlist(
        request,
        {"work_type", "status", "scheduled_from", "scheduled_to", "q", "cursor", "limit"},
    )
    items = (
        await service.mentor_queue(
            actor,
            session_status=session_status,
            scheduled_from=scheduled_from,
            scheduled_to=scheduled_to,
            query=query,
        )
        if work_type == "session"
        else []
    )
    scope = (
        f"mentor:{actor.user_id}:queue:{work_type}:{session_status or 'all'}:"
        f"{scheduled_from or 'all'}:{scheduled_to or 'all'}:{query or 'all'}"
    )
    return success(
        request,
        paginate_sequence(
            items,
            pagination,
            CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
            scope=scope,
        ),
    )


@router.patch("/sessions/{session_id}", response_model=SuccessEnvelope[SessionResponse])
async def schedule_session(
    session_id: UUID,
    payload: SessionSchedule,
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
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
            return success(request, SessionResponse.model_validate(claim.replay_body))
        result = await service.schedule(actor, session_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (SessionResourceNotFoundError, SessionConflictError) as error:
        raise_session_error(error)


async def _mentor_transition(
    session_id: UUID,
    payload: SessionTransition,
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: UUID,
    *,
    action: str,
) -> SuccessEnvelope[SessionResponse]:
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
            return success(request, SessionResponse.model_validate(claim.replay_body))
        result = await service.transition(
            actor,
            session_id,
            payload,
            request_id(request),
            action=action,
        )
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.row_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (SessionResourceNotFoundError, SessionConflictError) as error:
        raise_session_error(error)


@router.post("/sessions/{session_id}/start", response_model=SuccessEnvelope[SessionResponse])
async def start_session(
    session_id: UUID,
    payload: SessionTransition,
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
    return await _mentor_transition(
        session_id,
        payload,
        request,
        actor,
        service,
        idempotency,
        idempotency_key,
        action="start",
    )


@router.post("/sessions/{session_id}/complete", response_model=SuccessEnvelope[SessionResponse])
async def complete_session(
    session_id: UUID,
    payload: SessionTransition,
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
    return await _mentor_transition(
        session_id,
        payload,
        request,
        actor,
        service,
        idempotency,
        idempotency_key,
        action="complete",
    )


@router.post("/sessions/{session_id}/no-show", response_model=SuccessEnvelope[SessionResponse])
async def no_show_session(
    session_id: UUID,
    payload: SessionTransition,
    request: Request,
    actor: MentorActorDependency,
    service: MentoringSessionServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[SessionResponse]:
    return await _mentor_transition(
        session_id,
        payload,
        request,
        actor,
        service,
        idempotency,
        idempotency_key,
        action="no-show",
    )
