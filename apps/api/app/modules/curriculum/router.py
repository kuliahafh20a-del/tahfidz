"""Reference endpoints for the effective policy and curriculum."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.modules.curriculum.schemas import (
    AssessmentRubricResponse,
    CurriculumResponse,
    PolicySummary,
)
from app.modules.curriculum.service import ReferenceService

router = APIRouter(prefix="/reference", tags=["reference"])


def get_reference_service(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> ReferenceService:
    """Bind reference queries to the request-scoped database session."""
    return ReferenceService(session)


ReferenceServiceDependency = Annotated[ReferenceService, Depends(get_reference_service)]


def reference_not_found(error: LookupError) -> HTTPException:
    """Return a stable error without leaking database details."""
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail={"code": "reference_not_available"},
    )


@router.get("/assessment-rubric", response_model=AssessmentRubricResponse)
async def assessment_rubric(service: ReferenceServiceDependency) -> AssessmentRubricResponse:
    """Return the rubric from the currently effective policy version."""
    try:
        return await service.assessment_rubric()
    except LookupError as error:
        raise reference_not_found(error) from error


@router.get("/curriculum", response_model=CurriculumResponse)
async def curriculum(service: ReferenceServiceDependency) -> CurriculumResponse:
    """Return the complete published Juz 30 curriculum tree."""
    try:
        return await service.current_curriculum()
    except LookupError as error:
        raise reference_not_found(error) from error


@router.get("/policies/current", response_model=PolicySummary)
async def current_policy(service: ReferenceServiceDependency) -> PolicySummary:
    """Return the effective policy version summary."""
    try:
        return await service.current_policy()
    except LookupError as error:
        raise reference_not_found(error) from error
