from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.db.base import Base
from app.modules.assessments.models import (
    AssessmentKind,
    AssessmentRecord,
    AssessmentStatus,
    Incident,
    ThemeAssessment,
)
from app.modules.assessments.schemas import ThemeAssessmentDraftCreate


def test_assessment_models_register_required_constraints() -> None:
    records = Base.metadata.tables["app.assessment_records"]
    incidents = Base.metadata.tables["app.incidents"]
    themes = Base.metadata.tables["app.theme_assessments"]

    assert AssessmentRecord.__table__ is records
    assert Incident.__table__ is incidents
    assert ThemeAssessment.__table__ is themes
    assert any(
        constraint.name == "ck_assessment_records__manual_score_integer_range"
        for constraint in records.constraints
    )
    assert any(
        constraint.name == "uq_theme_assessments__session_theme_id"
        for constraint in themes.constraints
    )


def test_assessment_defaults_to_mutable_draft() -> None:
    record = AssessmentRecord(
        enrollment_id="71000000-0000-4000-8000-000000000001",
        assessor_id="71000000-0000-4000-8000-000000000002",
        policy_version_id="71000000-0000-4000-8000-000000000003",
        kind=AssessmentKind.THEME,
        actual_at=datetime(2027, 1, 1, tzinfo=UTC),
    )

    assert record.status is None or record.status is AssessmentStatus.DRAFT
    assert record.finalized_at is None


def test_theme_draft_rejects_fractional_score_and_naive_time() -> None:
    with pytest.raises(ValidationError):
        ThemeAssessmentDraftCreate.model_validate(
            {
                "theme_id": "71000000-0000-4000-8000-000000000004",
                "actual_at": "2027-01-01T08:00:00+07:00",
                "manual_score": 7.5,
            }
        )
    with pytest.raises(ValidationError):
        ThemeAssessmentDraftCreate.model_validate(
            {
                "theme_id": "71000000-0000-4000-8000-000000000004",
                "actual_at": "2027-01-01T08:00:00",
                "manual_score": 7,
            }
        )
