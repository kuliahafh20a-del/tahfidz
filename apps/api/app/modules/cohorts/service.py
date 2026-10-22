"""Scoped application services for participant and assignment administration."""

from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.exc import StaleDataError

from app.modules.cohorts.access import DepartmentActor
from app.modules.cohorts.models import Assignment, Cohort, Enrollment
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


class ResourceNotFoundError(LookupError):
    """Hide whether an identifier exists outside the actor's department."""


class DomainConflictError(ValueError):
    """Report a uniqueness, interval, or role-capacity conflict."""


class VersionConflictError(DomainConflictError):
    """Reject stale mutation payloads without overwriting newer data."""

    def __init__(self, current_version: int) -> None:
        super().__init__("enrollment was updated by another request")
        self.current_version = current_version


class DepartmentProgramService:
    """Apply department scope before every read or mutation."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_cohorts(self, actor: DepartmentActor) -> list[CohortResponse]:
        cohorts = await self.session.scalars(
            select(Cohort)
            .where(Cohort.organization_id == actor.organization_id)
            .order_by(Cohort.start_date.desc(), Cohort.name)
        )
        return [CohortResponse.model_validate(cohort) for cohort in cohorts]

    async def create_cohort(
        self,
        actor: DepartmentActor,
        payload: CohortCreate,
    ) -> CohortResponse:
        cohort = Cohort(
            organization_id=actor.organization_id,
            **payload.model_dump(),
        )
        self.session.add(cohort)
        await self._commit("cohort conflicts with existing or unpublished reference data")
        return CohortResponse.model_validate(cohort)

    async def list_enrollments(
        self,
        actor: DepartmentActor,
        cohort_id: UUID | None = None,
    ) -> list[EnrollmentResponse]:
        statement = self._scoped_enrollments(actor).options(selectinload(Enrollment.user))
        if cohort_id is not None:
            statement = statement.where(Enrollment.cohort_id == cohort_id)
        enrollments = await self.session.scalars(statement.order_by(Enrollment.joined_at.desc()))
        return [EnrollmentResponse.model_validate(item) for item in enrollments]

    async def get_enrollment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> EnrollmentDetail:
        enrollment = await self.session.scalar(
            self._scoped_enrollments(actor)
            .where(Enrollment.id == enrollment_id)
            .options(
                selectinload(Enrollment.user),
                selectinload(Enrollment.assignments).selectinload(Assignment.staff),
            )
        )
        if enrollment is None:
            raise ResourceNotFoundError("enrollment not found")
        return EnrollmentDetail.model_validate(enrollment)

    async def create_enrollment(
        self,
        actor: DepartmentActor,
        payload: EnrollmentCreate,
    ) -> EnrollmentResponse:
        await self._require_scoped_cohort(actor, payload.cohort_id)
        enrollment = Enrollment(**payload.model_dump())
        self.session.add(enrollment)
        await self._commit("participant or NIM is already enrolled in this cohort")
        from app.modules.calendar.service import ParticipantTargetService

        await ParticipantTargetService(self.session).generate_for_enrollment(enrollment.id)
        return await self._enrollment_response(actor, enrollment.id)

    async def update_enrollment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
        payload: EnrollmentUpdate,
    ) -> EnrollmentResponse:
        enrollment = await self.session.scalar(
            self._scoped_enrollments(actor).where(Enrollment.id == enrollment_id).with_for_update()
        )
        if enrollment is None:
            raise ResourceNotFoundError("enrollment not found")
        if payload.expected_version != enrollment.row_version:
            raise VersionConflictError(enrollment.row_version)
        for field, value in payload.model_dump(
            exclude={"expected_version"},
            exclude_none=True,
        ).items():
            setattr(enrollment, field, value)
        try:
            await self.session.commit()
        except StaleDataError as error:
            await self.session.rollback()
            current_version = await self.session.scalar(
                select(Enrollment.row_version).where(Enrollment.id == enrollment_id)
            )
            raise VersionConflictError(current_version or payload.expected_version) from error
        except IntegrityError as error:
            await self.session.rollback()
            raise DomainConflictError(
                "enrollment update conflicts with an existing participant or NIM"
            ) from error
        return await self._enrollment_response(actor, enrollment.id)

    async def list_assignments(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> list[AssignmentResponse]:
        await self._require_scoped_enrollment(actor, enrollment_id)
        assignments = await self.session.scalars(
            select(Assignment)
            .where(Assignment.enrollment_id == enrollment_id)
            .options(selectinload(Assignment.staff))
            .order_by(Assignment.valid_from.desc())
        )
        return [AssignmentResponse.model_validate(item) for item in assignments]

    async def create_assignment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
        payload: AssignmentCreate,
    ) -> AssignmentResponse:
        await self._require_scoped_enrollment(actor, enrollment_id)
        previous = await self.session.scalars(
            select(Assignment)
            .where(
                Assignment.enrollment_id == enrollment_id,
                Assignment.role == payload.role,
                Assignment.valid_from < payload.valid_from,
                Assignment.valid_to.is_(None) | (Assignment.valid_to > payload.valid_from),
            )
            .with_for_update()
        )
        for assignment in previous:
            assignment.valid_to = payload.valid_from

        assignment = Assignment(
            enrollment_id=enrollment_id,
            staff_id=payload.assignee_user_id,
            role=payload.role,
            valid_from=payload.valid_from,
            valid_to=payload.valid_to,
            reason=payload.reason,
        )
        self.session.add(assignment)
        await self._commit("assignment overlaps or staff lacks a covering role grant")
        return await self._assignment_response(actor, assignment.id)

    async def end_assignment(
        self,
        actor: DepartmentActor,
        assignment_id: UUID,
        payload: AssignmentEnd,
    ) -> AssignmentResponse:
        assignment = await self.session.scalar(
            select(Assignment)
            .join(Enrollment, Enrollment.id == Assignment.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Assignment.id == assignment_id,
                Cohort.organization_id == actor.organization_id,
            )
            .with_for_update()
        )
        if assignment is None:
            raise ResourceNotFoundError("assignment not found")
        if assignment.valid_to is not None:
            raise DomainConflictError("assignment is already closed")
        if payload.ended_at <= assignment.valid_from:
            raise DomainConflictError("assignment end must be after its start")
        assignment.valid_to = payload.ended_at
        if payload.reason is not None:
            assignment.reason = payload.reason
        await self._commit("assignment could not be closed")
        return await self._assignment_response(actor, assignment.id)

    def _scoped_enrollments(self, actor: DepartmentActor) -> Select[Enrollment]:
        return (
            select(Enrollment)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(Cohort.organization_id == actor.organization_id)
        )

    async def _require_scoped_cohort(self, actor: DepartmentActor, cohort_id: UUID) -> Cohort:
        cohort = await self.session.scalar(
            select(Cohort).where(
                Cohort.id == cohort_id,
                Cohort.organization_id == actor.organization_id,
            )
        )
        if cohort is None:
            raise ResourceNotFoundError("cohort not found")
        return cohort

    async def _require_scoped_enrollment(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> Enrollment:
        enrollment = await self.session.scalar(
            self._scoped_enrollments(actor).where(Enrollment.id == enrollment_id)
        )
        if enrollment is None:
            raise ResourceNotFoundError("enrollment not found")
        return enrollment

    async def _enrollment_response(
        self,
        actor: DepartmentActor,
        enrollment_id: UUID,
    ) -> EnrollmentResponse:
        enrollment = await self.session.scalar(
            self._scoped_enrollments(actor)
            .where(Enrollment.id == enrollment_id)
            .options(selectinload(Enrollment.user))
        )
        if enrollment is None:
            raise ResourceNotFoundError("enrollment not found")
        return EnrollmentResponse.model_validate(enrollment)

    async def _assignment_response(
        self,
        actor: DepartmentActor,
        assignment_id: UUID,
    ) -> AssignmentResponse:
        assignment = await self.session.scalar(
            select(Assignment)
            .join(Enrollment, Enrollment.id == Assignment.enrollment_id)
            .join(Cohort, Cohort.id == Enrollment.cohort_id)
            .where(
                Assignment.id == assignment_id,
                Cohort.organization_id == actor.organization_id,
            )
            .options(selectinload(Assignment.staff))
        )
        if assignment is None:
            raise ResourceNotFoundError("assignment not found")
        return AssignmentResponse.model_validate(assignment)

    async def _commit(self, message: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise DomainConflictError(message) from error
