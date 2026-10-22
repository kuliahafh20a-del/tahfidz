from datetime import date

from app.db.base import Base
from app.modules.calendar.models import Target, TargetStatus


def test_target_model_is_registered_with_unique_participant_theme_pair() -> None:
    table = Base.metadata.tables["app.targets"]

    assert Target.__table__ is table
    assert {column.name for column in table.columns} == {
        "id",
        "enrollment_id",
        "theme_id",
        "initial_due_date",
        "effective_due_date",
        "status",
    }
    assert any(
        constraint.name == "uq_targets__enrollment_id_theme_id" for constraint in table.constraints
    )


def test_target_defaults_to_scheduled() -> None:
    target = Target(
        enrollment_id="30000000-0000-4000-8000-000000000001",
        theme_id="30000000-0000-4000-8000-000000000002",
        initial_due_date=date(2027, 1, 1),
        effective_due_date=date(2027, 1, 1),
    )

    assert target.status is None or target.status is TargetStatus.SCHEDULED
