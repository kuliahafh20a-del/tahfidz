"""API schemas for department cohort and assignment administration."""

from datetime import date, datetime
from typing import Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.api.contracts import ExpectedVersion
from app.core.time import utc_now
from app.modules.cohorts.models import AssignmentRole, CohortStatus, EnrollmentStatus


class UserReference(BaseModel):
    """Minimal account information needed by the J01 workspace."""

    id: UUID
    name: str
    login_identifier: str

    model_config = ConfigDict(from_attributes=True)


class CohortCreate(BaseModel):
    """Create one department-owned cohort."""

    curriculum_version_id: UUID
    policy_version_id: UUID
    name: str = Field(min_length=1, max_length=200)
    start_date: date
    close_date: date | None = None
    status: CohortStatus = CohortStatus.DRAFT

    @model_validator(mode="after")
    def validate_dates(self) -> Self:
        if self.close_date is not None and self.close_date < self.start_date:
            raise ValueError("close_date must be on or after start_date")
        return self


class CohortResponse(BaseModel):
    """A cohort visible inside one department scope."""

    id: UUID
    organization_id: UUID
    curriculum_version_id: UUID
    policy_version_id: UUID
    name: str
    start_date: date
    close_date: date | None
    status: CohortStatus

    model_config = ConfigDict(from_attributes=True)


class EnrollmentCreate(BaseModel):
    """Enroll an existing participant account in a scoped cohort."""

    user_id: UUID
    cohort_id: UUID
    nim_snapshot: str = Field(min_length=1, max_length=64)
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE


class EnrollmentUpdate(ExpectedVersion):
    """Mutable enrollment fields that preserve identity and cohort history."""

    nim_snapshot: str | None = Field(default=None, min_length=1, max_length=64)
    status: EnrollmentStatus | None = None

    @model_validator(mode="after")
    def require_change(self) -> Self:
        if self.nim_snapshot is None and self.status is None:
            raise ValueError("at least one enrollment field is required")
        return self


class EnrollmentResponse(BaseModel):
    """Participant enrollment summary for J01."""

    id: UUID
    cohort_id: UUID
    user: UserReference
    nim_snapshot: str
    status: EnrollmentStatus
    joined_at: datetime
    row_version: int = Field(ge=1)

    model_config = ConfigDict(from_attributes=True)


class AssignmentCreate(BaseModel):
    """Assign one qualified staff account and close the prior active interval."""

    role: AssignmentRole
    assignee_user_id: UUID
    valid_from: datetime
    valid_to: datetime | None = None
    reason: str | None = Field(default=None, max_length=2_000)

    @model_validator(mode="after")
    def validate_interval(self) -> Self:
        if self.valid_to is not None and self.valid_to <= self.valid_from:
            raise ValueError("valid_to must be after valid_from")
        return self


class AssignmentEnd(BaseModel):
    """Close an active assignment without deleting its history."""

    ended_at: datetime = Field(default_factory=utc_now)
    reason: str | None = Field(default=None, max_length=2_000)


class AssignmentResponse(BaseModel):
    """One historical or active Mentor/Lecturer assignment."""

    id: UUID
    enrollment_id: UUID
    staff: UserReference
    role: AssignmentRole
    valid_from: datetime
    valid_to: datetime | None
    reason: str | None

    model_config = ConfigDict(from_attributes=True)


class EnrollmentDetail(EnrollmentResponse):
    """Enrollment summary with complete assignment history."""

    assignments: list[AssignmentResponse]
