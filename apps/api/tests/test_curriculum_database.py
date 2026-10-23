import os
from collections.abc import Iterator
from datetime import UTC, datetime
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from app.core.config import Settings
from app.db.migrations import build_alembic_config

MIGRATION_DATABASE_URL = os.getenv("MIGRATION_TEST_DATABASE_URL")


@pytest.fixture(scope="module")
def curriculum_engine() -> Iterator[Engine]:
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
def test_seed_covers_all_juz30_in_44_themes(curriculum_engine: Engine) -> None:
    with curriculum_engine.connect() as connection:
        assert set(inspect(connection).get_table_names(schema="app")) >= {
            "policy_versions",
            "curriculum_versions",
            "parts",
            "themes",
            "theme_ranges",
        }
        distribution = connection.execute(
            text(
                "SELECT p.sequence_no, count(t.id) AS theme_count "
                "FROM app.parts p JOIN app.themes t ON t.part_id = p.id "
                "JOIN app.curriculum_versions c ON c.id = p.curriculum_version_id "
                "WHERE c.status = 'published' GROUP BY p.sequence_no "
                "ORDER BY p.sequence_no"
            )
        ).all()
        coverage = connection.execute(
            text(
                "SELECT count(DISTINCT t.id), count(r.id), "
                "sum(r.ayah_end - r.ayah_start + 1), "
                "min(app.juz30_verse_ordinal(r.surah_no, r.ayah_start)), "
                "max(app.juz30_verse_ordinal(r.surah_no, r.ayah_end)) "
                "FROM app.theme_ranges r JOIN app.themes t ON t.id = r.theme_id "
                "JOIN app.parts p ON p.id = t.part_id "
                "JOIN app.curriculum_versions c ON c.id = p.curriculum_version_id "
                "WHERE c.status = 'published'"
            )
        ).one()

    assert distribution == [(1, 10), (2, 8), (3, 6), (4, 5), (5, 15)]
    assert coverage == (44, 48, 564, 1, 564)


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_seeded_policy_requires_integer_scores(curriculum_engine: Engine) -> None:
    with curriculum_engine.connect() as connection:
        policy = (
            connection.execute(
                text(
                    "SELECT version, status, rules FROM app.policy_versions "
                    "WHERE status = 'published'"
                )
            )
            .mappings()
            .one()
        )

    assert policy["version"] == "2026.1"
    assert policy["rules"]["score"]["step"] == 1
    assert policy["rules"]["score"]["allow_fractional"] is False
    assert policy["rules"]["score"]["display_decimals"] == 0
    assert policy["rules"]["video_assessment"]["maximum_errors_for_enough"] == 3
    assert policy["rules"]["exam_package"] == {
        "approved": False,
        "required_item_count": None,
        "expected_total_weight": None,
    }


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_published_reference_data_is_immutable(curriculum_engine: Engine) -> None:
    with curriculum_engine.connect() as connection, connection.begin():
        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "UPDATE app.policy_versions SET version = 'changed' WHERE status = 'published'"
                )
            )

        connection.execute(
            text(
                "INSERT INTO app.policy_versions "
                "(id, version, status, rules, approved_by, approved_at, effective_from) "
                "SELECT :id, '2027.1', 'published', rules, approved_by, approved_at, "
                "effective_from + interval '1 year' FROM app.policy_versions "
                "WHERE version = '2026.1'"
            ),
            {"id": uuid4()},
        )
        published_count = connection.scalar(
            text("SELECT count(*) FROM app.policy_versions WHERE status = 'published'")
        )

        assert published_count == 2

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "UPDATE app.themes SET title = 'changed' WHERE id = ("
                    "SELECT t.id FROM app.themes t JOIN app.parts p ON p.id = t.part_id "
                    "JOIN app.curriculum_versions c ON c.id = p.curriculum_version_id "
                    "WHERE c.status = 'published' LIMIT 1)"
                )
            )


@pytest.mark.migration
@pytest.mark.skipif(
    MIGRATION_DATABASE_URL is None,
    reason="MIGRATION_TEST_DATABASE_URL is required for PostgreSQL constraint tests",
)
def test_invalid_ayah_and_invalid_publish_are_rejected(curriculum_engine: Engine) -> None:
    curriculum_id = uuid4()
    part_id = uuid4()
    theme_id = uuid4()
    with curriculum_engine.connect() as connection, connection.begin():
        connection.execute(
            text(
                "INSERT INTO app.curriculum_versions (id, version, status, title) "
                "VALUES (:id, :version, 'draft', 'Invalid draft')"
            ),
            {"id": curriculum_id, "version": f"invalid-{curriculum_id}"},
        )
        connection.execute(
            text(
                "INSERT INTO app.parts (id, curriculum_version_id, sequence_no, title) "
                "VALUES (:id, :curriculum_id, 1, 'Part')"
            ),
            {"id": part_id, "curriculum_id": curriculum_id},
        )
        connection.execute(
            text(
                "INSERT INTO app.themes (id, part_id, sequence_no, title) "
                "VALUES (:id, :part_id, 1, 'Theme')"
            ),
            {"id": theme_id, "part_id": part_id},
        )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "INSERT INTO app.theme_ranges "
                    "(id, theme_id, sequence_no, surah_no, ayah_start, ayah_end) "
                    "VALUES (:id, :theme_id, 1, 114, 1, 7)"
                ),
                {"id": uuid4(), "theme_id": theme_id},
            )

        with pytest.raises(IntegrityError), connection.begin_nested():
            connection.execute(
                text(
                    "UPDATE app.curriculum_versions "
                    "SET status = 'published', published_at = :published_at WHERE id = :id"
                ),
                {"id": curriculum_id, "published_at": datetime.now(UTC)},
            )
