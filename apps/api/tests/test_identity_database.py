import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.migrations import build_alembic_config

MIGRATION_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")
SAMPLE_FACULTY_ID = UUID("10000000-0000-4000-8000-000000000001")
SAMPLE_DEPARTMENT_ID = UUID("10000000-0000-4000-8000-000000000002")


@pytest.fixture(scope="module")
def identity_engine() -> Iterator[Engine]:
    assert MIGRATION_DATABASE_URL is not None
    settings = Settings.model_validate({"DATABASE_URL": MIGRATION_DATABASE_URL})
    database_url = settings.database_url_value
    command.upgrade(build_alembic_config(database_url), "head")
    engine = create_engine(database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_identity_schema_and_sample_organizations(identity_engine: Engine) -> None:
    with identity_engine.connect() as connection:
        schema_inspector = inspect(connection)
        assert set(schema_inspector.get_table_names(schema="app")) >= {
            "organizations",
            "users",
            "role_grants",
        }
        organizations = connection.execute(
            text(
                "SELECT id, parent_id, kind, code "
                "FROM app.organizations WHERE id IN (:faculty_id, :department_id)"
            ),
            {
                "faculty_id": SAMPLE_FACULTY_ID,
                "department_id": SAMPLE_DEPARTMENT_ID,
            },
        ).mappings()

        by_id = {organization["id"]: organization for organization in organizations}
        assert by_id[SAMPLE_FACULTY_ID]["kind"] == "faculty"
        assert by_id[SAMPLE_FACULTY_ID]["parent_id"] is None
        assert by_id[SAMPLE_DEPARTMENT_ID]["kind"] == "department"
        assert by_id[SAMPLE_DEPARTMENT_ID]["parent_id"] == SAMPLE_FACULTY_ID


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_login_identifier_is_unique_without_case(identity_engine: Engine) -> None:
    with identity_engine.connect() as connection, connection.begin():
        connection.execute(
            text(
                "INSERT INTO app.users (id, login_identifier, name, account_status) "
                "VALUES (:id, :login_identifier, :name, 'active')"
            ),
            {
                "id": uuid4(),
                "login_identifier": "student@example.com",
                "name": "Student One",
            },
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.users (id, login_identifier, name, account_status) "
                    "VALUES (:id, :login_identifier, :name, 'active')"
                ),
                {
                    "id": uuid4(),
                    "login_identifier": "STUDENT@EXAMPLE.COM",
                    "name": "Student Duplicate",
                },
            )


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_hierarchy_rejects_self_parent_and_cycles(identity_engine: Engine) -> None:
    with identity_engine.connect() as connection, connection.begin():
        self_parent_id = uuid4()
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.organizations "
                    "(id, parent_id, kind, name, code, status) "
                    "VALUES (:id, :id, 'department', 'Invalid', :code, 'active')"
                ),
                {"id": self_parent_id, "code": f"SELF-{self_parent_id}"},
            )

        department_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO app.organizations "
                "(id, parent_id, kind, name, code, status) "
                "VALUES (:id, :parent_id, 'department', 'Temporary Department', "
                ":code, 'active')"
            ),
            {
                "id": department_id,
                "parent_id": SAMPLE_FACULTY_ID,
                "code": f"DEPT-{department_id}",
            },
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "UPDATE app.organizations "
                    "SET kind = 'department', parent_id = :department_id "
                    "WHERE id = :faculty_id"
                ),
                {
                    "department_id": department_id,
                    "faculty_id": SAMPLE_FACULTY_ID,
                },
            )


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_role_grants_enforce_admin_scope_and_non_overlapping_periods(
    identity_engine: Engine,
) -> None:
    with identity_engine.connect() as connection, connection.begin():
        user_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO app.users (id, login_identifier, name, account_status) "
                "VALUES (:id, :login_identifier, :name, 'active')"
            ),
            {
                "id": user_id,
                "login_identifier": f"{user_id}@example.com",
                "name": "Scoped User",
            },
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.role_grants "
                    "(user_id, organization_id, role, valid_from) "
                    "VALUES (:user_id, :organization_id, 'faculty_admin', :valid_from)"
                ),
                {
                    "user_id": user_id,
                    "organization_id": SAMPLE_DEPARTMENT_ID,
                    "valid_from": datetime(2026, 1, 1, tzinfo=UTC),
                },
            )

        connection.execute(
            text(
                "INSERT INTO app.role_grants "
                "(user_id, organization_id, role, valid_from, valid_to) "
                "VALUES (:user_id, :organization_id, 'mentor', :valid_from, :valid_to)"
            ),
            {
                "user_id": user_id,
                "organization_id": SAMPLE_DEPARTMENT_ID,
                "valid_from": datetime(2026, 1, 1, tzinfo=UTC),
                "valid_to": datetime(2027, 1, 1, tzinfo=UTC),
            },
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.role_grants "
                    "(user_id, organization_id, role, valid_from, valid_to) "
                    "VALUES (:user_id, :organization_id, 'mentor', :valid_from, :valid_to)"
                ),
                {
                    "user_id": user_id,
                    "organization_id": SAMPLE_DEPARTMENT_ID,
                    "valid_from": datetime(2026, 6, 1, tzinfo=UTC),
                    "valid_to": datetime(2027, 6, 1, tzinfo=UTC),
                },
            )
