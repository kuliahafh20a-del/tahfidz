import asyncio
import os
import selectors
import sys
from collections.abc import Coroutine, Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.migrations import build_alembic_config
from app.db.session import Database
from app.modules.cohorts.access import DepartmentActor
from app.modules.cohorts.models import AssignmentRole
from app.modules.cohorts.schemas import AssignmentCreate
from app.modules.cohorts.service import DepartmentProgramService, ResourceNotFoundError

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
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_assignments_require_scoped_grant_and_preserve_history(
    cohort_engine: Engine,
    program_context: dict[str, Any],
) -> None:
    first_assignment = uuid4()
    second_assignment = uuid4()
    first_start = datetime(2027, 1, 1, tzinfo=UTC)
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
            own_actor = DepartmentActor(uuid4(), SAMPLE_DEPARTMENT_ID)
            other_actor = DepartmentActor(uuid4(), program_context["second_department"])

            enrollment = await service.get_enrollment(own_actor, program_context["enrollment"])
            assert enrollment.nim_snapshot == "NIM-001"

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
