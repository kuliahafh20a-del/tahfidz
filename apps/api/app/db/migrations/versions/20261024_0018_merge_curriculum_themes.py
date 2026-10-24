"""Merge four groups in the published curriculum into 40 themes.

Revision ID: 20261024_0018
Revises: 20261024_0017
Create Date: 2026-10-24 17:30:00+07:00
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20261024_0018"
down_revision: str | None = "20261024_0017"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


MERGES = (
    (
        "Al-Kafirun",
        "Al-Masad, An-Nasr, dan Al-Kafirun",
        ("Al-Kafirun", "An-Nasr", "Al-Masad"),
    ),
    ("Al-Ma'un", "Al-Ma'un dan Al-Kawthar", ("Al-Ma'un", "Al-Kawthar")),
    ("Al-'Asr", "Al-'Asr dan Al-Humazah", ("Al-'Asr", "Al-Humazah")),
)


def upgrade() -> None:
    """Merge theme records and preserve each enrollment's strongest status."""
    op.execute(
        "ALTER TABLE app.curriculum_versions DISABLE TRIGGER trg_curriculum_versions_immutable"
    )
    op.execute("ALTER TABLE app.themes DISABLE TRIGGER trg_themes_immutable")
    op.execute("ALTER TABLE app.theme_ranges DISABLE TRIGGER trg_theme_ranges_immutable")

    for survivor, new_title, members in MERGES:
        member_sql = ", ".join(f"'{title.replace(chr(39), chr(39) * 2)}'" for title in members)
        survivor_sql = survivor.replace("'", "''")
        title_sql = new_title.replace("'", "''")

        op.execute(
            f"""
            UPDATE app.targets AS survivor_target
               SET status = aggregate.status
              FROM (
                SELECT target.enrollment_id,
                       CASE max(CASE target.status
                           WHEN 'completed' THEN 4 WHEN 'active' THEN 3
                           WHEN 'scheduled' THEN 2 ELSE 1 END)
                         WHEN 4 THEN 'completed' WHEN 3 THEN 'active'
                         WHEN 2 THEN 'scheduled' ELSE 'closed' END AS status
                  FROM app.targets AS target
                  JOIN app.themes AS theme ON theme.id = target.theme_id
                 WHERE theme.title IN ({member_sql})
                 GROUP BY target.enrollment_id
              ) AS aggregate
              JOIN app.themes AS survivor_theme ON survivor_theme.title = '{survivor_sql}'
             WHERE survivor_target.enrollment_id = aggregate.enrollment_id
               AND survivor_target.theme_id = survivor_theme.id
            """
        )
        op.execute(
            f"""
            DELETE FROM app.targets AS target
             USING app.themes AS theme
             WHERE target.theme_id = theme.id
               AND theme.title IN ({member_sql})
               AND theme.title <> '{survivor_sql}'
            """
        )
        op.execute(
            f"""
            UPDATE app.session_themes AS session_theme
               SET theme_id = survivor.id
              FROM app.themes AS old_theme, app.themes AS survivor
             WHERE session_theme.theme_id = old_theme.id
               AND old_theme.title IN ({member_sql})
               AND old_theme.title <> '{survivor_sql}'
               AND survivor.title = '{survivor_sql}'
            """
        )
        op.execute(
            f"""
            CREATE TEMP TABLE merged_theme_ranges ON COMMIT DROP AS
            SELECT range.surah_no, range.ayah_start, range.ayah_end,
                   row_number() OVER (ORDER BY range.surah_no, range.ayah_start) AS sequence_no
              FROM app.theme_ranges AS range
              JOIN app.themes AS theme ON theme.id = range.theme_id
             WHERE theme.title IN ({member_sql});

            DELETE FROM app.theme_ranges
             WHERE theme_id IN (SELECT id FROM app.themes WHERE title IN ({member_sql}));

            INSERT INTO app.theme_ranges (theme_id, sequence_no, surah_no, ayah_start, ayah_end)
            SELECT survivor.id, ranges.sequence_no, ranges.surah_no,
                   ranges.ayah_start, ranges.ayah_end
              FROM merged_theme_ranges AS ranges
              CROSS JOIN (SELECT id FROM app.themes WHERE title = '{survivor_sql}') AS survivor;

            DROP TABLE merged_theme_ranges;

            DELETE FROM app.themes
             WHERE title IN ({member_sql}) AND title <> '{survivor_sql}';
            UPDATE app.themes SET title = '{title_sql}' WHERE title = '{survivor_sql}';
            """
        )

    op.execute(
        "UPDATE app.themes SET sequence_no = sequence_no + 100 "
        "WHERE part_id IN (SELECT id FROM app.parts WHERE sequence_no = 5)"
    )
    op.execute(
        """
        WITH ordered AS (
            SELECT theme.id, row_number() OVER (
                PARTITION BY theme.part_id ORDER BY range.surah_no, range.ayah_start
            ) AS sequence_no
            FROM app.themes AS theme
            JOIN app.theme_ranges AS range ON range.theme_id = theme.id AND range.sequence_no = 1
            JOIN app.parts AS part ON part.id = theme.part_id
            WHERE part.sequence_no = 5
        )
        UPDATE app.themes AS theme SET sequence_no = ordered.sequence_no
        FROM ordered WHERE theme.id = ordered.id
        """
    )
    op.execute(
        "UPDATE app.curriculum_versions "
        "SET title = 'Kurikulum Juz 30 - 40 Tema' WHERE status = 'published'"
    )
    op.execute("ALTER TABLE app.theme_ranges ENABLE TRIGGER trg_theme_ranges_immutable")
    op.execute("ALTER TABLE app.themes ENABLE TRIGGER trg_themes_immutable")
    op.execute(
        "ALTER TABLE app.curriculum_versions ENABLE TRIGGER trg_curriculum_versions_immutable"
    )


def downgrade() -> None:
    """The merge preserves results but cannot reconstruct four independent targets safely."""
    raise RuntimeError("the 40-theme curriculum merge is irreversible")
