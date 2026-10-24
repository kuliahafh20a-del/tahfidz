"""Create immutable published policy and Juz 30 curriculum references.

Revision ID: 20261021_0003
Revises: 20261021_0002
Create Date: 2026-10-21 02:00:00+00:00
"""

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID, uuid5

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261021_0003"
down_revision: str | None = "20261021_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SEED_NAMESPACE = UUID("20000000-0000-4000-8000-000000000006")
BOOTSTRAP_APPROVER_ID = uuid5(SEED_NAMESPACE, "bootstrap-policy-approver")
POLICY_ID = uuid5(SEED_NAMESPACE, "policy:2026.1")
CURRICULUM_ID = uuid5(SEED_NAMESPACE, "curriculum:juz30-2026.1")
PUBLISHED_AT = datetime(2026, 10, 21, tzinfo=UTC)

POLICY_RULES = {
    "schema_version": 1,
    "score": {
        "minimum": 1,
        "maximum": 10,
        "step": 1,
        "allow_fractional": False,
        "display_decimals": 0,
        "bands": [
            {
                "minimum": 1,
                "maximum": 4,
                "description": "Perlu perbaikan mendasar.",
            },
            {
                "minimum": 5,
                "maximum": 7,
                "description": "Cukup dengan catatan.",
            },
            {
                "minimum": 8,
                "maximum": 10,
                "description": "Baik sampai sangat baik.",
            },
        ],
    },
    "video_assessment": {"maximum_errors_for_enough": 3},
    "exam_package": {
        "approved": False,
        "required_item_count": None,
        "expected_total_weight": None,
        "aggregation_method": None,
    },
}

# Every inclusive range is ordered and together covers QS 78:1 through QS 114:6 once.
PARTS: tuple[tuple[str, tuple[tuple[str, tuple[tuple[int, int, int], ...]], ...]], ...] = (
    (
        "Bagian 1",
        (
            ("An-Naba ayat 1-16", ((78, 1, 16),)),
            ("An-Naba ayat 17-30", ((78, 17, 30),)),
            ("An-Naba ayat 31-40", ((78, 31, 40),)),
            ("An-Nazi'at ayat 1-14", ((79, 1, 14),)),
            ("An-Nazi'at ayat 15-26", ((79, 15, 26),)),
            ("An-Nazi'at ayat 27-33", ((79, 27, 33),)),
            ("An-Nazi'at ayat 34-46", ((79, 34, 46),)),
            ("'Abasa ayat 1-16", ((80, 1, 16),)),
            ("'Abasa ayat 17-32", ((80, 17, 32),)),
            ("'Abasa ayat 33-42", ((80, 33, 42),)),
        ),
    ),
    (
        "Bagian 2",
        (
            ("At-Takwir ayat 1-14", ((81, 1, 14),)),
            ("At-Takwir ayat 15-29", ((81, 15, 29),)),
            ("Al-Infitar", ((82, 1, 19),)),
            ("Al-Mutaffifin ayat 1-17", ((83, 1, 17),)),
            ("Al-Mutaffifin ayat 18-36", ((83, 18, 36),)),
            ("Al-Inshiqaq", ((84, 1, 25),)),
            ("Al-Buruj ayat 1-11", ((85, 1, 11),)),
            ("Al-Buruj ayat 12-22", ((85, 12, 22),)),
        ),
    ),
    (
        "Bagian 3",
        (
            ("At-Tariq", ((86, 1, 17),)),
            ("Al-A'la", ((87, 1, 19),)),
            ("Al-Ghashiyah", ((88, 1, 26),)),
            ("Al-Fajr ayat 1-15", ((89, 1, 15),)),
            ("Al-Fajr ayat 16-30", ((89, 16, 30),)),
            ("Al-Balad", ((90, 1, 20),)),
        ),
    ),
    (
        "Bagian 4",
        (
            ("Ash-Shams", ((91, 1, 15),)),
            ("Al-Lail", ((92, 1, 21),)),
            ("Ad-Duha dan Ash-Sharh", ((93, 1, 11), (94, 1, 8))),
            ("At-Tin", ((95, 1, 8),)),
            ("Al-'Alaq", ((96, 1, 19),)),
        ),
    ),
    (
        "Bagian 5",
        (
            ("Al-Qadr", ((97, 1, 5),)),
            ("Al-Bayyinah", ((98, 1, 8),)),
            ("Az-Zalzalah", ((99, 1, 8),)),
            ("Al-'Adiyat", ((100, 1, 11),)),
            ("Al-Qari'ah", ((101, 1, 11),)),
            ("At-Takathur", ((102, 1, 8),)),
            ("Al-'Asr dan Al-Humazah", ((103, 1, 3), (104, 1, 9))),
            ("Al-Fil dan Quraysh", ((105, 1, 5), (106, 1, 4))),
            ("Al-Ma'un dan Al-Kawthar", ((107, 1, 7), (108, 1, 3))),
            (
                "Al-Masad, An-Nasr, dan Al-Kafirun",
                ((109, 1, 6), (110, 1, 3), (111, 1, 5)),
            ),
            ("Al-Ikhlas, Al-Falaq, dan An-Nas", ((112, 1, 4), (113, 1, 5), (114, 1, 6))),
        ),
    ),
)


def create_reference_tables() -> tuple[sa.Table, sa.Table, sa.Table, sa.Table, sa.Table]:
    """Create policy and curriculum tables in dependency order."""
    policy_versions = op.create_table(
        "policy_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("approved_by", sa.Uuid(), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'published', 'inactive')",
            name="ck_policy_versions__status",
        ),
        sa.CheckConstraint(
            "length(btrim(version)) > 0",
            name="ck_policy_versions__version_not_blank",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(rules) = 'object'",
            name="ck_policy_versions__rules_object",
        ),
        sa.CheckConstraint(
            "status NOT IN ('approved', 'published') "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="ck_policy_versions__approval_required",
        ),
        sa.CheckConstraint(
            "status <> 'published' OR effective_from IS NOT NULL",
            name="ck_policy_versions__effective_from_required",
        ),
        sa.ForeignKeyConstraint(
            ["approved_by"],
            ["app.users.id"],
            name="fk_policy_versions__users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_policy_versions"),
        sa.UniqueConstraint("version", name="uq_policy_versions__version"),
        schema="app",
    )
    curriculum_versions = op.create_table(
        "curriculum_versions",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="draft", nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'inactive')",
            name="ck_curriculum_versions__status",
        ),
        sa.CheckConstraint(
            "length(btrim(version)) > 0",
            name="ck_curriculum_versions__version_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_curriculum_versions__title_not_blank",
        ),
        sa.CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name="ck_curriculum_versions__published_at_required",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_curriculum_versions"),
        sa.UniqueConstraint("version", name="uq_curriculum_versions__version"),
        schema="app",
    )
    parts = op.create_table(
        "parts",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("curriculum_version_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "sequence_no BETWEEN 1 AND 5",
            name="ck_parts__sequence_range",
        ),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_parts__title_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["curriculum_version_id"],
            ["app.curriculum_versions.id"],
            name="fk_parts__curriculum_versions",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_parts"),
        sa.UniqueConstraint(
            "curriculum_version_id",
            "sequence_no",
            name="uq_parts__curriculum_version_id_sequence_no",
        ),
        schema="app",
    )

    themes = op.create_table(
        "themes",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("part_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.SmallInteger(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.CheckConstraint("sequence_no > 0", name="ck_themes__sequence_positive"),
        sa.CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_themes__title_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["part_id"],
            ["app.parts.id"],
            name="fk_themes__parts",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_themes"),
        sa.UniqueConstraint(
            "part_id",
            "sequence_no",
            name="uq_themes__part_id_sequence_no",
        ),
        schema="app",
    )

    theme_ranges = op.create_table(
        "theme_ranges",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("theme_id", sa.Uuid(), nullable=False),
        sa.Column("sequence_no", sa.SmallInteger(), nullable=False),
        sa.Column("surah_no", sa.SmallInteger(), nullable=False),
        sa.Column("ayah_start", sa.SmallInteger(), nullable=False),
        sa.Column("ayah_end", sa.SmallInteger(), nullable=False),
        sa.CheckConstraint(
            "sequence_no > 0",
            name="ck_theme_ranges__sequence_positive",
        ),
        sa.CheckConstraint(
            "surah_no BETWEEN 78 AND 114",
            name="ck_theme_ranges__surah_juz30",
        ),
        sa.CheckConstraint(
            "ayah_start > 0",
            name="ck_theme_ranges__ayah_start_positive",
        ),
        sa.CheckConstraint(
            "ayah_end >= ayah_start",
            name="ck_theme_ranges__ayah_order",
        ),
        sa.CheckConstraint(
            "ayah_end <= app.juz30_ayah_count(surah_no)",
            name="ck_theme_ranges__ayah_within_surah",
        ),
        sa.ForeignKeyConstraint(
            ["theme_id"],
            ["app.themes.id"],
            name="fk_theme_ranges__themes",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_theme_ranges"),
        sa.UniqueConstraint(
            "theme_id",
            "sequence_no",
            name="uq_theme_ranges__theme_id_sequence_no",
        ),
        schema="app",
    )
    return policy_versions, curriculum_versions, parts, themes, theme_ranges


def create_juz30_functions() -> None:
    """Create immutable helpers used by constraints and publication validation."""
    op.execute(
        """
        CREATE FUNCTION app.juz30_ayah_count(surah smallint)
        RETURNS smallint
        LANGUAGE sql
        IMMUTABLE
        STRICT
        AS $$
            SELECT CASE surah
                WHEN 78 THEN 40 WHEN 79 THEN 46 WHEN 80 THEN 42
                WHEN 81 THEN 29 WHEN 82 THEN 19 WHEN 83 THEN 36
                WHEN 84 THEN 25 WHEN 85 THEN 22 WHEN 86 THEN 17
                WHEN 87 THEN 19 WHEN 88 THEN 26 WHEN 89 THEN 30
                WHEN 90 THEN 20 WHEN 91 THEN 15 WHEN 92 THEN 21
                WHEN 93 THEN 11 WHEN 94 THEN 8 WHEN 95 THEN 8
                WHEN 96 THEN 19 WHEN 97 THEN 5 WHEN 98 THEN 8
                WHEN 99 THEN 8 WHEN 100 THEN 11 WHEN 101 THEN 11
                WHEN 102 THEN 8 WHEN 103 THEN 3 WHEN 104 THEN 9
                WHEN 105 THEN 5 WHEN 106 THEN 4 WHEN 107 THEN 7
                WHEN 108 THEN 3 WHEN 109 THEN 6 WHEN 110 THEN 3
                WHEN 111 THEN 5 WHEN 112 THEN 4 WHEN 113 THEN 5
                WHEN 114 THEN 6
                ELSE NULL
            END::smallint
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app.juz30_verse_ordinal(surah smallint, ayah smallint)
        RETURNS integer
        LANGUAGE sql
        IMMUTABLE
        STRICT
        AS $$
            SELECT CASE surah
                WHEN 78 THEN 0 WHEN 79 THEN 40 WHEN 80 THEN 86
                WHEN 81 THEN 128 WHEN 82 THEN 157 WHEN 83 THEN 176
                WHEN 84 THEN 212 WHEN 85 THEN 237 WHEN 86 THEN 259
                WHEN 87 THEN 276 WHEN 88 THEN 295 WHEN 89 THEN 321
                WHEN 90 THEN 351 WHEN 91 THEN 371 WHEN 92 THEN 386
                WHEN 93 THEN 407 WHEN 94 THEN 418 WHEN 95 THEN 426
                WHEN 96 THEN 434 WHEN 97 THEN 453 WHEN 98 THEN 458
                WHEN 99 THEN 466 WHEN 100 THEN 474 WHEN 101 THEN 485
                WHEN 102 THEN 496 WHEN 103 THEN 504 WHEN 104 THEN 507
                WHEN 105 THEN 516 WHEN 106 THEN 521 WHEN 107 THEN 525
                WHEN 108 THEN 532 WHEN 109 THEN 535 WHEN 110 THEN 541
                WHEN 111 THEN 544 WHEN 112 THEN 549 WHEN 113 THEN 553
                WHEN 114 THEN 558
                ELSE NULL
            END + ayah
        $$
        """
    )


def create_reference_triggers() -> None:
    """Enforce publication completeness and immutability in PostgreSQL."""
    op.execute(
        """
        CREATE FUNCTION app.prevent_published_policy_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status = 'published' THEN
                RAISE EXCEPTION 'published policy versions are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_policy_versions_immutable
        BEFORE UPDATE OR DELETE ON app.policy_versions
        FOR EACH ROW EXECUTE FUNCTION app.prevent_published_policy_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.validate_curriculum_publication()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE
            distribution integer[];
            coverage_valid boolean;
        BEGIN
            IF NEW.status = 'published'
               AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'published') THEN
                SELECT array_agg(theme_count ORDER BY sequence_no)
                  INTO distribution
                  FROM (
                    SELECT part.sequence_no, count(theme.id)::integer AS theme_count
                      FROM app.parts AS part
                      LEFT JOIN app.themes AS theme ON theme.part_id = part.id
                     WHERE part.curriculum_version_id = NEW.id
                     GROUP BY part.sequence_no
                  ) AS counts;

                IF distribution IS DISTINCT FROM ARRAY[10, 8, 6, 5, 11] THEN
                    RAISE EXCEPTION 'published curriculum requires theme distribution 10,8,6,5,11'
                        USING ERRCODE = 'check_violation';
                END IF;

                IF EXISTS (
                    SELECT 1
                      FROM app.parts AS part
                      JOIN app.themes AS theme ON theme.part_id = part.id
                     WHERE part.curriculum_version_id = NEW.id
                     GROUP BY part.id
                    HAVING min(theme.sequence_no) <> 1
                        OR max(theme.sequence_no) <> count(theme.id)
                ) THEN
                    RAISE EXCEPTION 'theme sequences must be contiguous within each part'
                        USING ERRCODE = 'check_violation';
                END IF;

                IF EXISTS (
                    SELECT 1
                      FROM app.parts AS part
                      JOIN app.themes AS theme ON theme.part_id = part.id
                      LEFT JOIN app.theme_ranges AS theme_range ON theme_range.theme_id = theme.id
                     WHERE part.curriculum_version_id = NEW.id
                     GROUP BY theme.id
                    HAVING count(theme_range.id) = 0
                        OR min(theme_range.sequence_no) <> 1
                        OR max(theme_range.sequence_no) <> count(theme_range.id)
                ) THEN
                    RAISE EXCEPTION 'every theme requires contiguous verse ranges'
                        USING ERRCODE = 'check_violation';
                END IF;

                WITH ordered_ranges AS (
                    SELECT
                        app.juz30_verse_ordinal(theme_range.surah_no, theme_range.ayah_start)
                            AS start_ordinal,
                        app.juz30_verse_ordinal(theme_range.surah_no, theme_range.ayah_end)
                            AS end_ordinal,
                        lag(app.juz30_verse_ordinal(
                            theme_range.surah_no,
                            theme_range.ayah_end
                        )) OVER (
                            ORDER BY part.sequence_no, theme.sequence_no, theme_range.sequence_no
                        ) AS previous_end
                      FROM app.parts AS part
                      JOIN app.themes AS theme ON theme.part_id = part.id
                      JOIN app.theme_ranges AS theme_range ON theme_range.theme_id = theme.id
                     WHERE part.curriculum_version_id = NEW.id
                )
                SELECT min(start_ordinal) = 1
                       AND max(end_ordinal) = 564
                       AND bool_and(start_ordinal = coalesce(previous_end + 1, 1))
                  INTO coverage_valid
                  FROM ordered_ranges;

                IF coverage_valid IS DISTINCT FROM TRUE THEN
                    RAISE EXCEPTION 'published curriculum must cover Juz 30 exactly once in order'
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_curriculum_versions_validate_publish
        BEFORE INSERT OR UPDATE OF status ON app.curriculum_versions
        FOR EACH ROW EXECUTE FUNCTION app.validate_curriculum_publication()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.prevent_published_curriculum_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF OLD.status = 'published' THEN
                RAISE EXCEPTION 'published curriculum versions are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_curriculum_versions_immutable
        BEFORE UPDATE OR DELETE ON app.curriculum_versions
        FOR EACH ROW EXECUTE FUNCTION app.prevent_published_curriculum_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.prevent_published_part_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE locked boolean;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                SELECT status = 'published' INTO locked
                  FROM app.curriculum_versions WHERE id = NEW.curriculum_version_id;
            ELSIF TG_OP = 'DELETE' THEN
                SELECT status = 'published' INTO locked
                  FROM app.curriculum_versions WHERE id = OLD.curriculum_version_id;
            ELSE
                SELECT bool_or(status = 'published') INTO locked
                  FROM app.curriculum_versions
                 WHERE id IN (OLD.curriculum_version_id, NEW.curriculum_version_id);
            END IF;
            IF locked THEN
                RAISE EXCEPTION 'published curriculum parts are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_parts_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON app.parts
        FOR EACH ROW EXECUTE FUNCTION app.prevent_published_part_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.prevent_published_theme_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE locked boolean;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                SELECT curriculum.status = 'published' INTO locked
                  FROM app.parts AS part
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE part.id = NEW.part_id;
            ELSIF TG_OP = 'DELETE' THEN
                SELECT curriculum.status = 'published' INTO locked
                  FROM app.parts AS part
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE part.id = OLD.part_id;
            ELSE
                SELECT bool_or(curriculum.status = 'published') INTO locked
                  FROM app.parts AS part
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE part.id IN (OLD.part_id, NEW.part_id);
            END IF;
            IF locked THEN
                RAISE EXCEPTION 'published curriculum themes are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_themes_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON app.themes
        FOR EACH ROW EXECUTE FUNCTION app.prevent_published_theme_mutation()
        """
    )

    op.execute(
        """
        CREATE FUNCTION app.prevent_published_theme_range_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        DECLARE locked boolean;
        BEGIN
            IF TG_OP = 'INSERT' THEN
                SELECT curriculum.status = 'published' INTO locked
                  FROM app.themes AS theme
                  JOIN app.parts AS part ON part.id = theme.part_id
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE theme.id = NEW.theme_id;
            ELSIF TG_OP = 'DELETE' THEN
                SELECT curriculum.status = 'published' INTO locked
                  FROM app.themes AS theme
                  JOIN app.parts AS part ON part.id = theme.part_id
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE theme.id = OLD.theme_id;
            ELSE
                SELECT bool_or(curriculum.status = 'published') INTO locked
                  FROM app.themes AS theme
                  JOIN app.parts AS part ON part.id = theme.part_id
                  JOIN app.curriculum_versions AS curriculum
                    ON curriculum.id = part.curriculum_version_id
                 WHERE theme.id IN (OLD.theme_id, NEW.theme_id);
            END IF;
            IF locked THEN
                RAISE EXCEPTION 'published curriculum verse ranges are immutable'
                    USING ERRCODE = 'check_violation';
            END IF;
            IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_theme_ranges_immutable
        BEFORE INSERT OR UPDATE OR DELETE ON app.theme_ranges
        FOR EACH ROW EXECUTE FUNCTION app.prevent_published_theme_range_mutation()
        """
    )


def seed_initial_references(
    policy_versions: sa.Table,
    curriculum_versions: sa.Table,
    parts: sa.Table,
    themes: sa.Table,
    theme_ranges: sa.Table,
) -> None:
    """Seed the approved integer rubric and complete ordered Juz 30 curriculum."""
    users = sa.table(
        "users",
        sa.column("id", sa.Uuid()),
        sa.column("login_identifier", sa.String()),
        sa.column("name", sa.String()),
        sa.column("account_status", sa.String()),
        schema="app",
    )
    op.bulk_insert(
        users,
        [
            {
                "id": BOOTSTRAP_APPROVER_ID,
                "login_identifier": "system:bootstrap-policy-approver",
                "name": "Bootstrap Policy Approver",
                "account_status": "inactive",
            }
        ],
    )
    op.bulk_insert(
        policy_versions,
        [
            {
                "id": POLICY_ID,
                "version": "2026.1",
                "status": "published",
                "rules": POLICY_RULES,
                "approved_by": BOOTSTRAP_APPROVER_ID,
                "approved_at": PUBLISHED_AT,
                "effective_from": PUBLISHED_AT,
            }
        ],
    )
    op.bulk_insert(
        curriculum_versions,
        [
            {
                "id": CURRICULUM_ID,
                "version": "juz30-2026.1",
                "status": "draft",
                "title": "Kurikulum Juz 30 - 40 Tema",
                "published_at": None,
            }
        ],
    )

    part_rows: list[dict[str, object]] = []
    theme_rows: list[dict[str, object]] = []
    range_rows: list[dict[str, object]] = []
    for part_sequence, (part_title, part_themes) in enumerate(PARTS, start=1):
        part_id = uuid5(SEED_NAMESPACE, f"part:{part_sequence}")
        part_rows.append(
            {
                "id": part_id,
                "curriculum_version_id": CURRICULUM_ID,
                "sequence_no": part_sequence,
                "title": part_title,
            }
        )
        for theme_sequence, (theme_title, ranges) in enumerate(part_themes, start=1):
            theme_id = uuid5(SEED_NAMESPACE, f"theme:{part_sequence}:{theme_sequence}")
            theme_rows.append(
                {
                    "id": theme_id,
                    "part_id": part_id,
                    "sequence_no": theme_sequence,
                    "title": theme_title,
                    "description": None,
                }
            )
            for range_sequence, (surah_no, ayah_start, ayah_end) in enumerate(
                ranges,
                start=1,
            ):
                range_rows.append(
                    {
                        "id": uuid5(
                            SEED_NAMESPACE,
                            f"range:{part_sequence}:{theme_sequence}:{range_sequence}",
                        ),
                        "theme_id": theme_id,
                        "sequence_no": range_sequence,
                        "surah_no": surah_no,
                        "ayah_start": ayah_start,
                        "ayah_end": ayah_end,
                    }
                )

    op.bulk_insert(parts, part_rows)
    op.bulk_insert(themes, theme_rows)
    op.bulk_insert(theme_ranges, range_rows)
    op.execute(
        sa.text(
            "UPDATE app.curriculum_versions "
            "SET status = 'published', published_at = :published_at "
            "WHERE id = :curriculum_id"
        ).bindparams(
            published_at=PUBLISHED_AT,
            curriculum_id=CURRICULUM_ID,
        )
    )


def upgrade() -> None:
    """Create, validate, publish, and lock initial reference data."""
    create_juz30_functions()
    policy_versions, curriculum_versions, parts, themes, theme_ranges = create_reference_tables()
    create_reference_triggers()
    seed_initial_references(
        policy_versions,
        curriculum_versions,
        parts,
        themes,
        theme_ranges,
    )


def downgrade() -> None:
    """Remove versioned references and the bootstrap approval identity."""
    op.execute("DROP TRIGGER IF EXISTS trg_theme_ranges_immutable ON app.theme_ranges")
    op.execute("DROP FUNCTION IF EXISTS app.prevent_published_theme_range_mutation()")
    op.execute("DROP TRIGGER IF EXISTS trg_themes_immutable ON app.themes")
    op.execute("DROP FUNCTION IF EXISTS app.prevent_published_theme_mutation()")
    op.execute("DROP TRIGGER IF EXISTS trg_parts_immutable ON app.parts")
    op.execute("DROP FUNCTION IF EXISTS app.prevent_published_part_mutation()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_curriculum_versions_immutable ON app.curriculum_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS app.prevent_published_curriculum_mutation()")
    op.execute(
        "DROP TRIGGER IF EXISTS trg_curriculum_versions_validate_publish ON app.curriculum_versions"
    )
    op.execute("DROP FUNCTION IF EXISTS app.validate_curriculum_publication()")
    op.execute("DROP TRIGGER IF EXISTS trg_policy_versions_immutable ON app.policy_versions")
    op.execute("DROP FUNCTION IF EXISTS app.prevent_published_policy_mutation()")
    op.drop_table("theme_ranges", schema="app")
    op.drop_table("themes", schema="app")
    op.drop_table("parts", schema="app")
    op.drop_table("curriculum_versions", schema="app")
    op.drop_table("policy_versions", schema="app")
    op.execute(
        sa.text(
            "DELETE FROM app.users "
            "WHERE id = :approver_id "
            "AND login_identifier = 'system:bootstrap-policy-approver'"
        ).bindparams(approver_id=BOOTSTRAP_APPROVER_ID)
    )
    op.execute("DROP FUNCTION IF EXISTS app.juz30_verse_ordinal(smallint, smallint)")
    op.execute("DROP FUNCTION IF EXISTS app.juz30_ayah_count(smallint)")
