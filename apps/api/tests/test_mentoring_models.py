from datetime import UTC, datetime

from app.db.base import Base
from app.modules.mentoring.models import (
    MentoringSession,
    SessionMethod,
    SessionStatus,
    SessionTheme,
)


def test_session_models_register_required_constraints() -> None:
    sessions = Base.metadata.tables["app.sessions"]
    session_themes = Base.metadata.tables["app.session_themes"]

    assert MentoringSession.__table__ is sessions
    assert SessionTheme.__table__ is session_themes
    assert any(
        constraint.name == "uq_session_themes__session_id_theme_id"
        for constraint in session_themes.constraints
    )
    assert any(
        constraint.name == "ck_sessions__status_timestamps" for constraint in sessions.constraints
    )


def test_new_session_defaults_to_proposed_without_actual_date() -> None:
    record = MentoringSession(
        enrollment_id="70000000-0000-4000-8000-000000000001",
        part_id="70000000-0000-4000-8000-000000000002",
        mentor_id="70000000-0000-4000-8000-000000000003",
        proposed_at=datetime(2027, 1, 1, tzinfo=UTC),
        method=SessionMethod.VIDEO_CALL,
    )

    assert record.status is None or record.status is SessionStatus.PROPOSED
    assert record.scheduled_at is None
    assert record.actual_at is None
