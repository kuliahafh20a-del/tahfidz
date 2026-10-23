"""Authenticated participant dashboard, calendar, and progress endpoints."""

from datetime import date
from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import SuccessEnvelope, success
from app.api.pagination import (
    CursorCodec,
    CursorPage,
    PaginationParams,
    paginate_sequence,
    require_query_allowlist,
)
from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.calendar.access import ParticipantActorDependency
from app.modules.calendar.models import TargetStatus
from app.modules.calendar.schemas import DashboardResponse, ProgressResponse, TargetResponse
from app.modules.calendar.service import (
    ParticipantEnrollmentNotFoundError,
    ParticipantTargetService,
)
from app.modules.grading.schemas import ActivityScoreResponse

router = APIRouter(prefix="/me", tags=["participant"])


def get_participant_target_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ParticipantTargetService:
    return ParticipantTargetService(session)


ParticipantTargetServiceDependency = Annotated[
    ParticipantTargetService,
    Depends(get_participant_target_service),
]
PaginationDependency = Annotated[PaginationParams, Depends()]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def _not_found(error: ParticipantEnrollmentNotFoundError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={
            "code": "ACTIVE_ENROLLMENT_NOT_FOUND",
            "message": "Kepesertaan aktif tidak ditemukan pada lingkup yang dipilih.",
        },
    ) from error


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/dashboard", response_model=SuccessEnvelope[DashboardResponse])
async def dashboard(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: ParticipantTargetServiceDependency,
) -> SuccessEnvelope[DashboardResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.dashboard(actor))
    except ParticipantEnrollmentNotFoundError as error:
        _not_found(error)


@router.get("/progress", response_model=SuccessEnvelope[ProgressResponse])
async def progress(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: ParticipantTargetServiceDependency,
) -> SuccessEnvelope[ProgressResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.progress(actor))
    except ParticipantEnrollmentNotFoundError as error:
        _not_found(error)


@router.get("/activity-score", response_model=SuccessEnvelope[ActivityScoreResponse])
async def activity_score(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: ParticipantTargetServiceDependency,
) -> SuccessEnvelope[ActivityScoreResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.activity_score(actor))
    except ParticipantEnrollmentNotFoundError as error:
        _not_found(error)


@router.get("/targets", response_model=SuccessEnvelope[CursorPage[TargetResponse]])
async def targets(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: ParticipantTargetServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
    part_id: Annotated[UUID | None, Query()] = None,
    target_status: Annotated[TargetStatus | None, Query(alias="status")] = None,
    due_from: Annotated[date | None, Query()] = None,
    due_to: Annotated[date | None, Query()] = None,
) -> SuccessEnvelope[CursorPage[TargetResponse]]:
    require_query_allowlist(
        request,
        {"part_id", "status", "due_from", "due_to", "cursor", "limit"},
    )
    _no_store(response)
    try:
        items = await service.list_targets(
            actor,
            part_id=part_id,
            target_status=target_status,
            due_from=due_from,
            due_to=due_to,
        )
    except ParticipantEnrollmentNotFoundError as error:
        _not_found(error)
    scope = (
        f"participant:{actor.user_id}:targets:{part_id or 'all'}:"
        f"{target_status or 'all'}:{due_from or 'all'}:{due_to or 'all'}"
    )
    page = paginate_sequence(
        items,
        pagination,
        CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}"),
        scope=scope,
    )
    return success(request, page)
