from datetime import UTC, date, datetime

import pytest

from app.db.base import Base
from app.modules.cohorts.models import Assignment, Cohort, Enrollment


def test_program_models_are_registered() -> None:
    assert set(Base.metadata.tables) >= {
        "app.cohorts",
        "app.enrollments",
        "app.assignments",
    }


def test_cohort_and_enrollment_normalize_human_identifiers() -> None:
    cohort = Cohort(
        organization_id="10000000-0000-4000-8000-000000000002",
        curriculum_version_id="20000000-0000-4000-8000-000000000001",
        policy_version_id="20000000-0000-4000-8000-000000000002",
        name="  Angkatan 2027  ",
        start_date=date(2027, 1, 1),
    )
    enrollment = Enrollment(
        user_id="30000000-0000-4000-8000-000000000001",
        cohort_id="30000000-0000-4000-8000-000000000002",
        nim_snapshot="  ab-123  ",
    )

    assert cohort.name == "Angkatan 2027"
    assert enrollment.nim_snapshot == "AB-123"


def test_assignment_normalizes_timezone_and_optional_reason() -> None:
    assignment = Assignment(
        enrollment_id="30000000-0000-4000-8000-000000000001",
        staff_id="30000000-0000-4000-8000-000000000002",
        role="mentor",
        valid_from=datetime(2027, 1, 1, 7, tzinfo=UTC),
        reason="   ",
    )

    assert assignment.valid_from == datetime(2027, 1, 1, 7, tzinfo=UTC)
    assert assignment.reason is None


def test_assignment_rejects_naive_time() -> None:
    with pytest.raises(ValueError, match="timezone information"):
        Assignment(
            enrollment_id="30000000-0000-4000-8000-000000000001",
            staff_id="30000000-0000-4000-8000-000000000002",
            role="mentor",
            valid_from=datetime(2027, 1, 1),
        )
