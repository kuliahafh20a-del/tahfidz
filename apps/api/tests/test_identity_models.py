from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.db.models import metadata
from app.modules.identity import AccountStatus, Role, RoleGrant, User
from app.modules.organizations import Organization, OrganizationKind, OrganizationStatus


def test_model_metadata_contains_identity_tables_in_app_schema() -> None:
    assert set(metadata.tables) >= {
        "app.organizations",
        "app.users",
        "app.role_grants",
    }


def test_organization_normalizes_name_and_code() -> None:
    organization = Organization(
        kind=OrganizationKind.FACULTY,
        name="  Fakultas Teknik  ",
        code="  ft  ",
        status=OrganizationStatus.ACTIVE,
    )

    assert organization.name == "Fakultas Teknik"
    assert organization.code == "FT"

    with pytest.raises(ValueError, match="must not be blank"):
        Organization(
            kind=OrganizationKind.FACULTY,
            name="   ",
            status=OrganizationStatus.ACTIVE,
        )


def test_user_normalizes_case_insensitive_login_identifier() -> None:
    user = User(
        login_identifier="  Student@Example.COM  ",
        name="  Student One  ",
        account_status=AccountStatus.ACTIVE,
    )

    assert user.login_identifier == "student@example.com"
    assert user.name == "Student One"


def test_role_grant_checks_time_and_organization_scope() -> None:
    organization_id = uuid4()
    other_organization_id = uuid4()
    valid_from = datetime(2026, 1, 1, tzinfo=UTC)
    valid_to = datetime(2027, 1, 1, tzinfo=UTC)
    grant = RoleGrant(
        user_id=uuid4(),
        organization_id=organization_id,
        role=Role.MENTOR,
        valid_from=valid_from,
        valid_to=valid_to,
    )

    assert grant.applies_to(
        organization_id,
        datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert not grant.applies_to(
        other_organization_id,
        datetime(2026, 6, 1, tzinfo=UTC),
    )
    assert not grant.is_active_at(valid_to)
