"""Department administration endpoints for cohorts and assignments."""

from typing import Annotated, NoReturn
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

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


def raise_domain_error(error: Exception) -> NoReturn:
    if isinstance(error, ResourceNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "resource_not_found"},
        ) from error
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail={"code": "domain_conflict", "message": str(error)},
    ) from error


@router.get("/cohorts", response_model=list[CohortResponse])
async def list_cohorts(
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
) -> list[CohortResponse]:
    return await service.list_cohorts(actor)


@router.post(
    "/cohorts",
    response_model=CohortResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_cohort(
    payload: CohortCreate,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> CohortResponse:
    try:
        return await service.create_cohort(actor, payload)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get("/enrollments", response_model=list[EnrollmentResponse])
async def list_enrollments(
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    cohort_id: Annotated[UUID | None, Query()] = None,
) -> list[EnrollmentResponse]:
    return await service.list_enrollments(actor, cohort_id)


@router.post(
    "/enrollments",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_enrollment(
    payload: EnrollmentCreate,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> EnrollmentResponse:
    try:
        return await service.create_enrollment(actor, payload)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get("/enrollments/{enrollment_id}", response_model=EnrollmentDetail)
async def get_enrollment(
    enrollment_id: UUID,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
) -> EnrollmentDetail:
    try:
        return await service.get_enrollment(actor, enrollment_id)
    except ResourceNotFoundError as error:
        raise_domain_error(error)


@router.patch("/enrollments/{enrollment_id}", response_model=EnrollmentResponse)
async def update_enrollment(
    enrollment_id: UUID,
    payload: EnrollmentUpdate,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> EnrollmentResponse:
    try:
        return await service.update_enrollment(actor, enrollment_id, payload)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.get(
    "/enrollments/{enrollment_id}/assignments",
    response_model=list[AssignmentResponse],
)
async def list_assignments(
    enrollment_id: UUID,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
) -> list[AssignmentResponse]:
    try:
        return await service.list_assignments(actor, enrollment_id)
    except ResourceNotFoundError as error:
        raise_domain_error(error)


@router.post(
    "/enrollments/{enrollment_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_assignment(
    enrollment_id: UUID,
    payload: AssignmentCreate,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> AssignmentResponse:
    try:
        return await service.create_assignment(actor, enrollment_id, payload)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)


@router.post(
    "/assignments/{assignment_id}/end",
    response_model=AssignmentResponse,
)
async def end_assignment(
    assignment_id: UUID,
    payload: AssignmentEnd,
    actor: DepartmentActorDependency,
    service: DepartmentProgramServiceDependency,
    _csrf: CsrfProtectionDependency,
) -> AssignmentResponse:
    try:
        return await service.end_assignment(actor, assignment_id, payload)
    except (ResourceNotFoundError, DomainConflictError) as error:
        raise_domain_error(error)
