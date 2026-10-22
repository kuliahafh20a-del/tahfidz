"""Department calendar and controlled deadline-change endpoints."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.contracts import IdempotencyKey, SuccessEnvelope, request_id, success
from app.api.pagination import require_query_allowlist
from app.db.session import get_session
from app.modules.auth.access import CsrfProtectionDependency
from app.modules.calendar.admin_schemas import (
    CohortCalendarResponse,
    DeadlineChangeBatchResponse,
    DeadlineChangePreview,
    DeadlineChangeRequest,
    DeadlineDecisionRequest,
)
from app.modules.calendar.admin_service import (
    CalendarConflictError,
    CalendarResourceNotFoundError,
    CalendarVersionConflictError,
    DeadlineChangeService,
)
from app.modules.cohorts.access import DepartmentActorDependency
from app.modules.cohorts.router import raise_idempotency_error
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)

router = APIRouter(prefix="/department", tags=["department calendar"])


def get_deadline_change_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DeadlineChangeService:
    return DeadlineChangeService(session)


DeadlineChangeServiceDependency = Annotated[
    DeadlineChangeService,
    Depends(get_deadline_change_service),
]


def raise_calendar_error(error: Exception) -> NoReturn:
    if isinstance(error, CalendarResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "RESOURCE_NOT_FOUND"},
        ) from error
    if isinstance(error, CalendarVersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "message": "Kalender telah berubah. Muat versi terbaru sebelum melanjutkan.",
                "field_errors": {"expected_version": ["Versi kalender tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "DEADLINE_CHANGE_CONFLICT", "message": str(error)},
    ) from error


@router.get(
    "/cohorts/{cohort_id}/calendar",
    response_model=SuccessEnvelope[CohortCalendarResponse],
)
async def get_cohort_calendar(
    cohort_id: UUID,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
) -> SuccessEnvelope[CohortCalendarResponse]:
    require_query_allowlist(request, set())
    try:
        result = await service.calendar(actor, cohort_id)
        return success(request, result, version=result.calendar_version)
    except CalendarResourceNotFoundError as error:
        raise_calendar_error(error)


@router.post(
    "/cohorts/{cohort_id}/deadline-changes/preview",
    response_model=SuccessEnvelope[DeadlineChangePreview],
)
async def preview_deadline_change(
    cohort_id: UUID,
    payload: DeadlineChangeRequest,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[DeadlineChangePreview]:
    try:
        result = await service.preview(actor, cohort_id, payload)
        return success(request, result, version=result.calendar_version)
    except (CalendarResourceNotFoundError, CalendarConflictError) as error:
        raise_calendar_error(error)


@router.post(
    "/cohorts/{cohort_id}/deadline-changes",
    response_model=SuccessEnvelope[DeadlineChangeBatchResponse],
    status_code=status.HTTP_201_CREATED,
)
async def propose_deadline_change(
    cohort_id: UUID,
    payload: DeadlineChangeRequest,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[DeadlineChangeBatchResponse]:
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
            return success(request, DeadlineChangeBatchResponse.model_validate(claim.replay_body))
        result = await service.propose(actor, cohort_id, payload, request_id(request))
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result, version=result.calendar_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (CalendarResourceNotFoundError, CalendarConflictError) as error:
        raise_calendar_error(error)


async def _decide(
    change_id: UUID,
    payload: DeadlineDecisionRequest,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: UUID,
    *,
    approve: bool,
) -> SuccessEnvelope[DeadlineChangeBatchResponse]:
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
            return success(request, DeadlineChangeBatchResponse.model_validate(claim.replay_body))
        result = await service.decide(
            actor,
            change_id,
            payload,
            request_id(request),
            approve=approve,
        )
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result, version=result.calendar_version)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (CalendarResourceNotFoundError, CalendarConflictError) as error:
        raise_calendar_error(error)


@router.post(
    "/deadline-changes/{change_id}/approve",
    response_model=SuccessEnvelope[DeadlineChangeBatchResponse],
)
async def approve_deadline_change(
    change_id: UUID,
    payload: DeadlineDecisionRequest,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[DeadlineChangeBatchResponse]:
    return await _decide(
        change_id,
        payload,
        request,
        actor,
        service,
        idempotency,
        idempotency_key,
        approve=True,
    )


@router.post(
    "/deadline-changes/{change_id}/reject",
    response_model=SuccessEnvelope[DeadlineChangeBatchResponse],
)
async def reject_deadline_change(
    change_id: UUID,
    payload: DeadlineDecisionRequest,
    request: Request,
    actor: DepartmentActorDependency,
    service: DeadlineChangeServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[DeadlineChangeBatchResponse]:
    return await _decide(
        change_id,
        payload,
        request,
        actor,
        service,
        idempotency,
        idempotency_key,
        approve=False,
    )
