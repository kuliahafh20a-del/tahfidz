"""Department administration endpoints for cohorts and assignments."""

from typing import Annotated, NoReturn
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
from app.modules.cohorts.access import DepartmentActorDependency
from app.modules.cohorts.schemas import (
    AssignmentCreate,
    AssignmentEnd,
    AssignmentResponse,
    CohortCreate,
    CohortResponse,
    EnrollmentCreate,
    EnrollmentDetail,
    EnrollmentResponse,
    EnrollmentUpdate,
)
from app.modules.cohorts.service import (
    DepartmentProgramService,
    DomainConflictError,
    ResourceNotFoundError,
    VersionConflictError,
)
from app.modules.operations.service import (
    IdempotencyKeyReusedError,
    IdempotencyRequestInProgressError,
    IdempotencyStoreDependency,
)

router = APIRouter(prefix="/department", tags=["department administration"])


def get_department_program_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentProgramService:
    return DepartmentProgramService(session)


DepartmentProgramServiceDependency = Annotated[
    DepartmentProgramService,
    Depends(get_department_program_service),
]
PaginationDependency = Annotated[PaginationParams, Depends()]
SettingsDependency = Annotated[Settings, Depends(get_settings)]


def _cursor_codec(settings: Settings) -> CursorCodec:
    return CursorCodec(f"yaqin:cursor:{settings.csrf_secret_value}")


def raise_domain_error(error: Exception) -> NoReturn:
    if isinstance(error, ResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resource_not_found"},
        ) from error
    if isinstance(error, VersionConflictError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "VERSION_CONFLICT",
                "message": "Data telah diperbarui. Muat ulang sebelum menyimpan.",
                "field_errors": {"expected_version": ["Versi yang dikirim tidak lagi berlaku."]},
                "details": {"current_version": error.current_version},
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "domain_conflict", "message": str(error)},
    ) from error


def raise_idempotency_error(error: Exception) -> NoReturn:
    if isinstance(error, IdempotencyKeyReusedError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "IDEMPOTENCY_KEY_REUSED",
                "message": "Idempotency-Key sudah dipakai untuk operasi atau payload lain.",
            },
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={
            "code": "IDEMPOTENCY_REQUEST_IN_PROGRESS",
            "message": "Operasi pertama masih diproses. Periksa status sebelum mencoba kembali.",
        },
    ) from error


@router.get("/cohorts", response_model=SuccessEnvelope[CursorPage[CohortResponse]])
async def list_cohorts(
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[CohortResponse]]:
    require_query_allowlist(request, {"cursor", "limit"})
    items = await service.list_cohorts(actor)
    page = paginate_sequence(
        items,
        pagination,
        _cursor_codec(settings),
        scope=f"department:{actor.organization_id}:cohorts",
    )
    return success(request, page)


@router.post(
    "/cohorts",
    response_model=SuccessEnvelope[CohortResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_cohort(
    payload: CohortCreate,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[CohortResponse]:
    try:
        return success(request, await service.create_cohort(actor, payload))
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get("/enrollments", response_model=SuccessEnvelope[CursorPage[EnrollmentResponse]])
async def list_enrollments(
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
    cohort_id: Annotated[UUID | None, Query()] = None,
) -> SuccessEnvelope[CursorPage[EnrollmentResponse]]:
    require_query_allowlist(request, {"cohort_id", "cursor", "limit"})
    items = await service.list_enrollments(actor, cohort_id)
    page = paginate_sequence(
        items,
        pagination,
        _cursor_codec(settings),
        scope=f"department:{actor.organization_id}:enrollments:{cohort_id or 'all'}",
    )
    return success(request, page)


@router.post(
    "/enrollments",
    response_model=SuccessEnvelope[EnrollmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_enrollment(
    payload: EnrollmentCreate,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[EnrollmentResponse]:
    try:
        result = await service.create_enrollment(actor, payload)
        return success(request, result, version=result.row_version)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get(
    "/enrollments/{enrollment_id}",
    response_model=SuccessEnvelope[EnrollmentDetail],
)
async def get_enrollment(
    enrollment_id: UUID,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
) -> SuccessEnvelope[EnrollmentDetail]:
    try:
        result = await service.get_enrollment(actor, enrollment_id)
        return success(request, result, version=result.row_version)
    except ResourceNotFoundError as error:
        raise_domain_error(error)


@router.patch(
    "/enrollments/{enrollment_id}",
    response_model=SuccessEnvelope[EnrollmentResponse],
)
async def update_enrollment(
    enrollment_id: UUID,
    payload: EnrollmentUpdate,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[EnrollmentResponse]:
    try:
        result = await service.update_enrollment(actor, enrollment_id, payload)
        return success(request, result, version=result.row_version)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get(
    "/enrollments/{enrollment_id}/assignments",
    response_model=SuccessEnvelope[CursorPage[AssignmentResponse]],
)
async def list_assignments(
    enrollment_id: UUID,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    pagination: PaginationDependency,
    settings: SettingsDependency,
) -> SuccessEnvelope[CursorPage[AssignmentResponse]]:
    try:
        require_query_allowlist(request, {"cursor", "limit"})
        items = await service.list_assignments(actor, enrollment_id)
        page = paginate_sequence(
            items,
            pagination,
            _cursor_codec(settings),
            scope=f"department:{actor.organization_id}:assignments:{enrollment_id}",
        )
        return success(request, page)
    except ResourceNotFoundError as error:
        raise_domain_error(error)


@router.post(
    "/enrollments/{enrollment_id}/assignments",
    response_model=SuccessEnvelope[AssignmentResponse],
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    enrollment_id: UUID,
    payload: AssignmentCreate,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[AssignmentResponse]:
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
            return success(request, AssignmentResponse.model_validate(claim.replay_body))
        result = await service.create_assignment(actor, enrollment_id, payload)
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_201_CREATED,
        )
        return success(request, result)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.post(
    "/assignments/{assignment_id}/end",
    response_model=SuccessEnvelope[AssignmentResponse],
)
async def end_assignment(
    assignment_id: UUID,
    payload: AssignmentEnd,
    request: Request,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    idempotency: IdempotencyStoreDependency,
    idempotency_key: IdempotencyKey,
    _csrf: CsrfProtectionDependency,
) -> SuccessEnvelope[AssignmentResponse]:
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
            return success(request, AssignmentResponse.model_validate(claim.replay_body))
        result = await service.end_assignment(actor, assignment_id, payload)
        await idempotency.complete(
            claim,
            response_body=result.model_dump(mode="json"),
            response_status=status.HTTP_200_OK,
        )
        return success(request, result)
    except (IdempotencyKeyReusedError, IdempotencyRequestInProgressError) as error:
        raise_idempotency_error(error)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)
