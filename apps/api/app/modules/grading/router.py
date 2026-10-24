"""Participant grade recap, history, and snapshot publication endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import SuccessEnvelope, success
from app.api.pagination import require_query_allowlist
from app.db.session import get_session
from app.modules.auth.access import AuthenticatedSessionDependency, CsrfProtectionDependency
from app.modules.calendar.access import ParticipantActorDependency
from app.modules.grading.schemas import GradeHistoryResponse, GradeSnapshotResponse
from app.modules.grading.service import (
    ActivityEnrollmentNotFoundError,
    GradeScopeDeniedError,
    GradeSnapshotNotFoundError,
    GradeSnapshotService,
)

router = APIRouter(tags=["grading"])


def get_grade_snapshot_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> GradeSnapshotService:
    return GradeSnapshotService(session)


GradeServiceDependency = Annotated[GradeSnapshotService, Depends(get_grade_snapshot_service)]


def _not_found(error: Exception) -> NoReturn:
    code = (
        "GRADE_SNAPSHOT_NOT_FOUND"
        if isinstance(error, GradeSnapshotNotFoundError)
        else "ACTIVE_ENROLLMENT_NOT_FOUND"
    )
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": code, "message": "Rekap nilai belum tersedia."},
    ) from error


def _forbidden(error: GradeScopeDeniedError) -> NoReturn:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail={"code": "GRADE_SCOPE_DENIED", "message": "Rekap nilai di luar lingkup aktif."},
    ) from error


def _no_store(response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"


@router.get("/me/grades", response_model=SuccessEnvelope[GradeSnapshotResponse])
async def latest_grade(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: GradeServiceDependency,
) -> SuccessEnvelope[GradeSnapshotResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.latest_for_participant(actor))
    except (ActivityEnrollmentNotFoundError, GradeSnapshotNotFoundError) as error:
        _not_found(error)


@router.get("/me/grades/history", response_model=SuccessEnvelope[GradeHistoryResponse])
async def grade_history(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: GradeServiceDependency,
) -> SuccessEnvelope[GradeHistoryResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.history_for_participant(actor))
    except ActivityEnrollmentNotFoundError as error:
        _not_found(error)


@router.post(
    "/me/grades/publish",
    response_model=SuccessEnvelope[GradeSnapshotResponse],
    status_code=status.HTTP_201_CREATED,
)
async def publish_grade(
    request: Request,
    response: Response,
    actor: ParticipantActorDependency,
    service: GradeServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[GradeSnapshotResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(
            request,
            await service.publish_for_participant(actor, request_id=request.state.request_id),
            version=1,
        )
    except ActivityEnrollmentNotFoundError as error:
        _not_found(error)


@router.get(
    "/enrollments/{enrollment_id}/grades",
    response_model=SuccessEnvelope[GradeSnapshotResponse],
)
async def scoped_latest_grade(
    enrollment_id: UUID,
    request: Request,
    response: Response,
    authenticated: AuthenticatedSessionDependency,
    service: GradeServiceDependency,
) -> SuccessEnvelope[GradeSnapshotResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.latest_for_enrollment(authenticated, enrollment_id))
    except GradeSnapshotNotFoundError as error:
        _not_found(error)
    except GradeScopeDeniedError as error:
        _forbidden(error)


@router.get(
    "/enrollments/{enrollment_id}/grades/history",
    response_model=SuccessEnvelope[GradeHistoryResponse],
)
async def scoped_grade_history(
    enrollment_id: UUID,
    request: Request,
    response: Response,
    authenticated: AuthenticatedSessionDependency,
    service: GradeServiceDependency,
) -> SuccessEnvelope[GradeHistoryResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(request, await service.history_for_enrollment(authenticated, enrollment_id))
    except GradeScopeDeniedError as error:
        _forbidden(error)


@router.post(
    "/enrollments/{enrollment_id}/grades/publish",
    response_model=SuccessEnvelope[GradeSnapshotResponse],
    status_code=status.HTTP_201_CREATED,
)
async def scoped_publish_grade(
    enrollment_id: UUID,
    request: Request,
    response: Response,
    authenticated: AuthenticatedSessionDependency,
    service: GradeServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[GradeSnapshotResponse]:
    require_query_allowlist(request, set())
    _no_store(response)
    try:
        return success(
            request,
            await service.publish_for_enrollment(
                authenticated, enrollment_id, request_id=request.state.request_id
            ),
            version=1,
        )
    except GradeScopeDeniedError as error:
        _forbidden(error)
