import asyncio
import os
import selectors
import sys
from collections.abc import Coroutine, Iterator
from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, func, inspect, select, text, update
from sqlalchemy.exc import DatabaseError, IntegrityError

from app.core.config import Settings
from app.db.migrations import build_alembic_config
from app.db.session import Database
from app.modules.assessments.models import AssessmentStatus, AssistanceType, ThemeOutcome
from app.modules.assessments.schemas import IncidentInput, ThemeAssessmentDraftCreate
from app.modules.assessments.service import (
    AssessmentConflictError,
    AssessmentResourceNotFoundError,
    ThemeAssessmentService,
)
from app.modules.audit.models import AuditEvent
from app.modules.calendar.access import ParticipantActor
from app.modules.calendar.admin_schemas import DeadlineChangeRequest, DeadlineDecisionRequest
from app.modules.calendar.admin_service import (
    CalendarVersionConflictError,
    DeadlineChangeService,
)
from app.modules.calendar.models import Target, TargetStatus
from app.modules.calendar.service import ParticipantTargetService
from app.modules.cohorts.access import DepartmentActor
from app.modules.cohorts.models import AssignmentRole
from app.modules.cohorts.schemas import AssignmentCreate
from app.modules.cohorts.service import DepartmentProgramService, ResourceNotFoundError
from app.modules.curriculum.models import Theme
from app.modules.mentoring.access import MentorActor
from app.modules.mentoring.models import (
    MentoringSession,
    SessionMethod,
    SessionStatus,
    SessionTheme,
)
from app.modules.mentoring.schemas import SessionCreate, SessionSchedule, SessionTransition
from app.modules.mentoring.service import MentoringSessionService, SessionVersionConflictError

MIGRATION_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")
SAMPLE_FACULTY_ID = UUID("10000000-0000-4000-8000-000000000001")
SAMPLE_DEPARTMENT_ID = UUID("10000000-0000-4000-8000-000000000002")


def run_async[T](operation: Coroutine[object, object, T]) -> T:
    if sys.platform == "win32":
        return asyncio.run(
            operation,
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    return asyncio.run(operation)


@pytest.fixture(scope="module")
def cohort_engine() -> Iterator[Engine]:
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    database_url = settings.database_url_value
    command.upgrade(build_alembic_config(database_url), "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="module")
def program_context(cohort_engine: Engine) -> dict[str, Any]:
    ids: dict[str, Any] = {
        "second_department": uuid4(),
        "department_admin": uuid4(),
        "participant": uuid4(),
        "participant_two": uuid4(),
        "mentor": uuid4(),
        "lecturer": uuid4(),
        "outside_mentor": uuid4(),
        "cohort": uuid4(),
        "second_cohort": uuid4(),
        "enrollment": uuid4(),
    }
    with cohort_engine.connect() as connection, connection.begin():
        references = (
            connection.execute(
                text(
                    "SELECT "
                    "(SELECT id FROM app.curriculum_versions WHERE status = 'published' "
                    "ORDER BY published_at DESC LIMIT 1) AS curriculum_id, "
                    "(SELECT id FROM app.policy_versions WHERE status = 'published' "
                    "ORDER BY effective_from DESC LIMIT 1) AS policy_id"
                )
            )
            .mappings()
            .one()
        )
        ids.update(references)

        connection.execute(
            text(
                "INSERT INTO app.organizations (id, parent_id, kind, name, code, status) "
                "VALUES (:id, :parent_id, 'department', 'Jurusan Lain', :code, 'active')"
            ),
            {
                "id": ids["second_department"],
                "parent_id": SAMPLE_FACULTY_ID,
                "code": f"DEPT-{ids['second_department']}",
            },
        )
        for key in (
            "department_admin",
            "participant",
            "participant_two",
            "mentor",
            "lecturer",
            "outside_mentor",
        ):
            connection.execute(
                text(
                    "INSERT INTO app.users (id, login_identifier, name, account_status) "
                    "VALUES (:id, :login, :name, 'active')"
                ),
                {
                    "id": ids[key],
                    "login": f"{ids[key]}@example.test",
                    "name": key.replace("_", " ").title(),
                },
            )

        grant_start = datetime(2026, 1, 1, tzinfo=UTC)
        for user_key, role, organization_id in (
            ("department_admin", "department_admin", SAMPLE_DEPARTMENT_ID),
            ("mentor", "mentor", SAMPLE_DEPARTMENT_ID),
            ("lecturer", "lecturer", SAMPLE_DEPARTMENT_ID),
            ("outside_mentor", "mentor", ids["second_department"]),
        ):
            connection.execute(
                text(
                    "INSERT INTO app.role_grants "
                    "(id, user_id, organization_id, role, valid_from) "
                    "VALUES (:id, :user_id, :organization_id, :role, :valid_from)"
                ),
                {
                    "id": uuid4(),
                    "user_id": ids[user_key],
                    "organization_id": organization_id,
                    "role": role,
                    "valid_from": grant_start,
                },
            )

        for cohort_key, organization_id, name in (
            ("cohort", SAMPLE_DEPARTMENT_ID, "Angkatan Integrasi"),
            ("second_cohort", ids["second_department"], "Angkatan Jurusan Lain"),
        ):
            connection.execute(
                text(
                    "INSERT INTO app.cohorts "
                    "(id, organization_id, curriculum_version_id, policy_version_id, "
                    "name, start_date, status) "
                    "VALUES (:id, :organization_id, :curriculum_id, :policy_id, "
                    ":name, DATE '2027-01-01', 'active')"
                ),
                {
                    "id": ids[cohort_key],
                    "organization_id": organization_id,
                    "curriculum_id": ids["curriculum_id"],
                    "policy_id": ids["policy_id"],
                    "name": name,
                },
            )

        connection.execute(
            text(
                "INSERT INTO app.enrollments "
                "(id, user_id, cohort_id, nim_snapshot, status) "
                "VALUES (:id, :user_id, :cohort_id, 'NIM-001', 'active')"
            ),
            {
                "id": ids["enrollment"],
                "user_id": ids["participant"],
                "cohort_id": ids["cohort"],
            },
        )
    return ids


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_program_schema_and_department_cohort_constraint(
    cohort_engine: Engine,
    program_context: dict[str, Any],
) -> None:
    with cohort_engine.connect() as connection, connection.begin():
        assert set(inspect(connection).get_table_names(schema="app")) >= {
            "cohorts",
            "enrollments",
            "assignments",
        }
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.cohorts "
                    "(id, organization_id, curriculum_version_id, policy_version_id, "
                    "name, start_date, status) "
                    "VALUES (:id, :organization_id, :curriculum_id, :policy_id, "
                    "'Invalid Faculty Cohort', DATE '2027-01-01', 'draft')"
                ),
                {
                    "id": uuid4(),
                    "organization_id": SAMPLE_FACULTY_ID,
                    "curriculum_id": program_context["curriculum_id"],
                    "policy_id": program_context["policy_id"],
                },
            )


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_enrollment_rejects_duplicate_participant_and_nim(
    cohort_engine: Engine,
    program_context: dict[str, Any],
) -> None:
    with cohort_engine.connect() as connection, connection.begin():
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.enrollments "
                    "(id, user_id, cohort_id, nim_snapshot, status) "
                    "VALUES (:id, :user_id, :cohort_id, 'NIM-002', 'active')"
                ),
                {
                    "id": uuid4(),
                    "user_id": program_context["participant"],
                    "cohort_id": program_context["cohort"],
                },
            )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.enrollments "
                    "(id, user_id, cohort_id, nim_snapshot, status) "
                    "VALUES (:id, :user_id, :cohort_id, 'nim-lowercase', 'active')"
                ),
                {
                    "id": uuid4(),
                    "user_id": program_context["participant_two"],
                    "cohort_id": program_context["second_cohort"],
                },
            )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.enrollments "
                    "(id, user_id, cohort_id, nim_snapshot, status) "
                    "VALUES (:id, :user_id, :cohort_id, 'NIM-001', 'active')"
                ),
                {
                    "id": uuid4(),
                    "user_id": program_context["participant_two"],
                    "cohort_id": program_context["cohort"],
                },
            )


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for assessment constraint tests",
)
def test_theme_assessment_requires_exactly_one_subtype_and_integer_score(
    cohort_engine: Engine,
    program_context: dict[str, Any],
) -> None:
    with cohort_engine.connect() as connection, connection.begin():
        statement = text(
            "INSERT INTO app.assessment_records "
            "(id, enrollment_id, assessor_id, policy_version_id, kind, actual_at, "
            "manual_score, status) VALUES "
            "(:id, :enrollment_id, :assessor_id, :policy_id, 'theme', now(), "
            ":manual_score, 'draft')"
        )
        values = {
            "enrollment_id": program_context["enrollment"],
            "assessor_id": program_context["mentor"],
            "policy_id": program_context["policy_id"],
        }
        with pytest.raises(DatabaseError), connection.begin_nested():
            connection.execute(statement, {**values, "id": uuid4(), "manual_score": 7})
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(statement, {**values, "id": uuid4(), "manual_score": 7.5})


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_assignments_require_scoped_grant_and_preserve_history(
    cohort_engine: Engine,
    program_context: dict[str, Any],
) -> None:
    first_assignment = uuid4()
    second_assignment = uuid4()
    first_start = datetime(2026, 1, 1, tzinfo=UTC)
    switch_at = datetime(2027, 7, 1, tzinfo=UTC)
    with cohort_engine.connect() as connection, connection.begin():
        connection.execute(
            text(
                "INSERT INTO app.assignments "
                "(id, enrollment_id, staff_id, role, valid_from, reason) "
                "VALUES (:id, :enrollment_id, :staff_id, 'mentor', :valid_from, 'Initial')"
            ),
            {
                "id": first_assignment,
                "enrollment_id": program_context["enrollment"],
                "staff_id": program_context["mentor"],
                "valid_from": first_start,
            },
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.assignments "
                    "(id, enrollment_id, staff_id, role, valid_from) "
                    "VALUES (:id, :enrollment_id, :staff_id, 'lecturer', :valid_from)"
                ),
                {
                    "id": uuid4(),
                    "enrollment_id": program_context["enrollment"],
                    "staff_id": program_context["outside_mentor"],
                    "valid_from": first_start,
                },
            )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.assignments "
                    "(id, enrollment_id, staff_id, role, valid_from) "
                    "VALUES (:id, :enrollment_id, :staff_id, 'mentor', :valid_from)"
                ),
                {
                    "id": uuid4(),
                    "enrollment_id": program_context["enrollment"],
                    "staff_id": program_context["mentor"],
                    "valid_from": datetime(2027, 3, 1, tzinfo=UTC),
                },
            )

        connection.execute(
            text("UPDATE app.assignments SET valid_to = :valid_to WHERE id = :id"),
            {"valid_to": switch_at, "id": first_assignment},
        )
        connection.execute(
            text(
                "INSERT INTO app.assignments "
                "(id, enrollment_id, staff_id, role, valid_from, reason) "
                "VALUES (:id, :enrollment_id, :staff_id, 'mentor', :valid_from, 'Rotation')"
            ),
            {
                "id": second_assignment,
                "enrollment_id": program_context["enrollment"],
                "staff_id": program_context["mentor"],
                "valid_from": switch_at,
            },
        )
        history = connection.execute(
            text(
                "SELECT id, valid_to FROM app.assignments "
                "WHERE enrollment_id = :enrollment_id ORDER BY valid_from"
            ),
            {"enrollment_id": program_context["enrollment"]},
        ).all()

    assert history == [(first_assignment, switch_at), (second_assignment, None)]


async def assert_department_scope(
    settings: Settings,
    program_context: dict[str, Any],
) -> None:
    database = Database(settings)
    try:
        async with database.session_factory() as session:
            service = DepartmentProgramService(session)
            own_actor = DepartmentActor(program_context["department_admin"], SAMPLE_DEPARTMENT_ID)
            other_actor = DepartmentActor(uuid4(), program_context["second_department"])

            enrollment = await service.get_enrollment(own_actor, program_context["enrollment"])
            assert enrollment.nim_snapshot == "NIM-001"

            targets = ParticipantTargetService(session)
            assert await targets.generate_for_enrollment(program_context["enrollment"]) == 40
            assert await targets.generate_for_enrollment(program_context["enrollment"]) == 0

            target = await session.scalar(
                select(Target)
                .where(Target.enrollment_id == program_context["enrollment"])
                .order_by(Target.effective_due_date)
            )
            assert target is not None
            original_due_date = target.initial_due_date
            deadline_service = DeadlineChangeService(session)
            proposal = await deadline_service.propose(
                own_actor,
                program_context["cohort"],
                DeadlineChangeRequest(
                    target_ids=[target.id],
                    new_due_date=date(2027, 1, 8),
                    reason="Penyesuaian kalender akademik",
                    impact_note="Target bergeser tujuh hari",
                    expected_version=1,
                ),
                uuid4(),
            )
            await session.commit()
            assert proposal.calendar_version == 2
            with pytest.raises(CalendarVersionConflictError):
                await deadline_service.preview(
                    own_actor,
                    program_context["cohort"],
                    DeadlineChangeRequest(
                        target_ids=[target.id],
                        new_due_date=date(2027, 1, 15),
                        reason="Versi lama",
                        expected_version=1,
                    ),
                )
            decision = await deadline_service.decide(
                own_actor,
                proposal.changes[0].id,
                DeadlineDecisionRequest(expected_version=1, decision_note="Sesuai mandat"),
                uuid4(),
                approve=True,
            )
            await session.commit()
            await session.refresh(target)
            audit_count = await session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.object_reference == str(proposal.changes[0].id)
                )
            )
            assert decision.calendar_version == 3
            assert target.initial_due_date == original_due_date
            assert target.effective_due_date == date(2027, 1, 8)
            assert audit_count == 2

            with pytest.raises(IntegrityError):
                await session.execute(
                    update(Target)
                    .where(Target.id == target.id)
                    .values(effective_due_date=date(2027, 1, 15))
                )
            await session.rollback()

            active_targets = list(
                await session.scalars(
                    select(Target)
                    .where(
                        Target.enrollment_id == program_context["enrollment"],
                        Target.status == TargetStatus.ACTIVE,
                    )
                    .order_by(Target.id)
                    .limit(2)
                )
            )
            session_service = MentoringSessionService(session)
            participant_actor = ParticipantActor(
                program_context["participant"], SAMPLE_DEPARTMENT_ID
            )
            mentor_actor = MentorActor(program_context["mentor"], SAMPLE_DEPARTMENT_ID)
            session_proposal = await session_service.create(
                participant_actor,
                SessionCreate(
                    theme_ids=[item.theme_id for item in active_targets],
                    method=SessionMethod.VIDEO_CALL,
                    proposed_at=datetime(2027, 2, 1, 2, tzinfo=UTC),
                    participant_note="Fokus kelancaran ayat akhir",
                ),
                uuid4(),
            )
            await session.commit()
            assert session_proposal.status is SessionStatus.PROPOSED
            assert len(session_proposal.themes) == 2

            scheduled = await session_service.schedule(
                mentor_actor,
                session_proposal.id,
                SessionSchedule(
                    scheduled_at=datetime(2027, 2, 1, 3, tzinfo=UTC),
                    method=SessionMethod.VIDEO_CALL,
                    mentor_note="Tautan dikirim terpisah",
                    expected_version=1,
                ),
                uuid4(),
            )
            await session.commit()
            assert scheduled.status is SessionStatus.SCHEDULED
            assert scheduled.actual_at is None
            assert all(item.status is TargetStatus.ACTIVE for item in active_targets)

            with pytest.raises(SessionVersionConflictError):
                await session_service.schedule(
                    mentor_actor,
                    session_proposal.id,
                    SessionSchedule(
                        scheduled_at=datetime(2027, 2, 1, 4, tzinfo=UTC),
                        method=SessionMethod.IN_PERSON,
                        expected_version=1,
                    ),
                    uuid4(),
                )
            started = await session_service.transition(
                mentor_actor,
                session_proposal.id,
                SessionTransition(expected_version=2, note="Peserta hadir"),
                uuid4(),
                action="start",
            )
            await session.commit()
            assert started.status is SessionStatus.IN_PROGRESS
            assert started.actual_at is not None

            assessment_service = ThemeAssessmentService(session)
            draft = await assessment_service.create_draft(
                mentor_actor,
                session_proposal.id,
                ThemeAssessmentDraftCreate(
                    theme_id=active_targets[0].theme_id,
                    actual_at=started.actual_at,
                    manual_score=8,
                    outcome=ThemeOutcome.ENOUGH,
                    mentor_note="Hafalan lancar dan siap dituntaskan",
                    incidents=[
                        IncidentInput(
                            location_text="QS An-Naba ayat 12",
                            primary_category="tajwid",
                            context="Panjang bacaan sempat kurang",
                            assistance=AssistanceType.CUE,
                            self_corrected=True,
                            counted=False,
                            counting_reason="Koreksi mandiri setelah isyarat ringan",
                        )
                    ],
                ),
                uuid4(),
            )
            await session.commit()
            assert draft.status is AssessmentStatus.DRAFT
            assert draft.attempt_no == 1
            assert draft.policy_version_id == program_context["policy_id"]

            final = await assessment_service.finalize(
                mentor_actor,
                draft.assessment_id,
                draft.row_version,
                uuid4(),
            )
            await session.commit()
            await session.refresh(active_targets[0])
            assessment_audits = await session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.object_type == "theme_assessment",
                    AuditEvent.object_reference == str(draft.assessment_id),
                )
            )
            assert final.status is AssessmentStatus.FINAL
            assert final.manual_score == 8
            assert final.counted_incidents == 0
            assert active_targets[0].status is TargetStatus.COMPLETED
            assert assessment_audits == 2
            with pytest.raises(AssessmentResourceNotFoundError):
                await assessment_service.get_for_mentor(
                    MentorActor(
                        program_context["outside_mentor"],
                        program_context["second_department"],
                    ),
                    final.assessment_id,
                )

            repeat_theme = await session.get(Theme, active_targets[1].theme_id)
            assert repeat_theme is not None
            assert started.actual_at is not None
            repeat_session_ids = [session_proposal.id]
            repeat_actual_times = [started.actual_at]
            for _index in range(4):
                actual_at = datetime.now(UTC)
                repeat_actual_times.append(actual_at)
                repeat_session = MentoringSession(
                    enrollment_id=program_context["enrollment"],
                    part_id=repeat_theme.part_id,
                    mentor_id=program_context["mentor"],
                    proposed_at=actual_at,
                    scheduled_at=actual_at,
                    actual_at=actual_at,
                    method=SessionMethod.VIDEO_CALL,
                    status=SessionStatus.IN_PROGRESS,
                )
                session.add(repeat_session)
                await session.flush()
                session.add(
                    SessionTheme(
                        session_id=repeat_session.id,
                        theme_id=active_targets[1].theme_id,
                    )
                )
                await session.flush()
                repeat_session_ids.append(repeat_session.id)

            fifth_result = None
            for attempt_index, repeat_session_id in enumerate(repeat_session_ids, start=1):
                repeat_record = await session.get(MentoringSession, repeat_session_id)
                assert repeat_record is not None and repeat_record.actual_at is not None
                repeat_draft = await assessment_service.create_draft(
                    mentor_actor,
                    repeat_session_id,
                    ThemeAssessmentDraftCreate(
                        theme_id=active_targets[1].theme_id,
                        actual_at=repeat_record.actual_at,
                        manual_score=5,
                        outcome=ThemeOutcome.REPEAT,
                        mentor_note="Perlu mengulang kelancaran",
                    ),
                    uuid4(),
                )
                assert repeat_draft.attempt_no == attempt_index
                fifth_result = await assessment_service.finalize(
                    mentor_actor,
                    repeat_draft.assessment_id,
                    repeat_draft.row_version,
                    uuid4(),
                )
                await session.flush()
            assert fifth_result is not None
            assert fifth_result.attempt_no == 5
            assert fifth_result.outcome is ThemeOutcome.FOLLOW_UP

            activity = await targets.activity_score(participant_actor)
            repeat_activity = next(
                item
                for item in activity.source_context.themes
                if item.theme_id == active_targets[1].theme_id
            )
            assert repeat_activity.first_valid_submission_at == min(repeat_actual_times)
            assert repeat_activity.score == 10

            sixth_time = datetime.now(UTC)
            sixth_session = MentoringSession(
                enrollment_id=program_context["enrollment"],
                part_id=repeat_theme.part_id,
                mentor_id=program_context["mentor"],
                proposed_at=sixth_time,
                scheduled_at=sixth_time,
                actual_at=sixth_time,
                method=SessionMethod.VIDEO_CALL,
                status=SessionStatus.IN_PROGRESS,
            )
            session.add(sixth_session)
            await session.flush()
            session.add(
                SessionTheme(
                    session_id=sixth_session.id,
                    theme_id=active_targets[1].theme_id,
                )
            )
            await session.flush()
            with pytest.raises(AssessmentConflictError, match="sixth"):
                await assessment_service.create_draft(
                    mentor_actor,
                    sixth_session.id,
                    ThemeAssessmentDraftCreate(
                        theme_id=active_targets[1].theme_id,
                        actual_at=sixth_time,
                        manual_score=5,
                        outcome=ThemeOutcome.REPEAT,
                    ),
                    uuid4(),
                )

            completed = await session_service.transition(
                mentor_actor,
                session_proposal.id,
                SessionTransition(expected_version=3, note="Sesi selesai"),
                uuid4(),
                action="complete",
            )
            await session.commit()
            session_audits = await session.scalar(
                select(func.count(AuditEvent.id)).where(
                    AuditEvent.object_type == "session",
                    AuditEvent.object_reference == str(session_proposal.id),
                )
            )
            assert completed.status is SessionStatus.COMPLETED
            assert session_audits == 4

            first_rotation = await service.create_assignment(
                own_actor,
                program_context["enrollment"],
                AssignmentCreate(
                    role=AssignmentRole.MENTOR,
                    assignee_user_id=program_context["mentor"],
                    valid_from=datetime(2028, 1, 1, tzinfo=UTC),
                    reason="Rotasi pertama",
                ),
            )
            second_rotation = await service.create_assignment(
                own_actor,
                program_context["enrollment"],
                AssignmentCreate(
                    role=AssignmentRole.MENTOR,
                    assignee_user_id=program_context["mentor"],
                    valid_from=datetime(2028, 7, 1, tzinfo=UTC),
                    reason="Rotasi kedua",
                ),
            )
            history = await service.list_assignments(own_actor, program_context["enrollment"])
            first_in_history = next(item for item in history if item.id == first_rotation.id)

            assert first_in_history.valid_to == datetime(2028, 7, 1, tzinfo=UTC)
            assert second_rotation.valid_to is None

            with pytest.raises(ResourceNotFoundError):
                await service.get_enrollment(other_actor, program_context["enrollment"])
    finally:
        await database.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL authorization tests",
)
def test_service_hides_enrollment_across_departments(
    program_context: dict[str, Any],
) -> None:
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    run_async(assert_department_scope(settings, program_context))
