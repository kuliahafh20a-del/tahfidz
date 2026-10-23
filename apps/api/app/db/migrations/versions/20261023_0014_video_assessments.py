"""Add academic video assessments.

Revision ID: 20261023_0014
Revises: 20261023_0013
Create Date: 2026-10-23 12:00:00+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261023_0014"
down_revision: str | None = "20261023_0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "video_assessments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("video_version_id", sa.Uuid(), nullable=False),
        sa.Column("eligibility_review_id", sa.Uuid(), nullable=False),
        sa.Column("audio_asset_id", sa.Uuid(), nullable=True),
        sa.Column("counted_errors", sa.Integer(), server_default="0", nullable=False),
        sa.Column("outcome", sa.String(length=16), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "counted_errors >= 0", name="ck_video_assessments__counted_errors_nonnegative"
        ),
        sa.CheckConstraint(
            "outcome IS NULL OR outcome IN ('enough', 'not_enough')",
            name="ck_video_assessments__outcome",
        ),
        sa.CheckConstraint(
            "notes IS NULL OR length(btrim(notes)) > 0",
            name="ck_video_assessments__notes_not_blank",
        ),
        sa.ForeignKeyConstraint(
            ["id"],
            ["app.assessment_records.id"],
            name="fk_video_assessments__assessment_records",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["video_version_id"],
            ["app.video_versions.id"],
            name="fk_video_assessments__video_versions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["eligibility_review_id"],
            ["app.eligibility_reviews.id"],
            name="fk_video_assessments__eligibility_reviews",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["audio_asset_id"],
            ["app.media_assets.id"],
            name="fk_video_assessments__media_assets",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_video_assessments"),
        schema="app",
    )
    op.create_index(
        "ix_video_assessments__video_version_id",
        "video_assessments",
        ["video_version_id"],
        schema="app",
    )
    op.execute(
        """
        CREATE FUNCTION app.validate_video_assessment_links()
        RETURNS trigger LANGUAGE plpgsql AS $$
        DECLARE review_video uuid; review_status text; review_decision text;
        BEGIN
          SELECT video_version_id, status, decision
            INTO review_video, review_status, review_decision
            FROM app.eligibility_reviews WHERE id = NEW.eligibility_review_id;
          IF review_video IS DISTINCT FROM NEW.video_version_id
             OR review_status IS DISTINCT FROM 'final'
             OR review_decision IS DISTINCT FROM 'eligible' THEN
            RAISE EXCEPTION 'video assessment requires matching final eligible review';
          END IF;
          RETURN NEW;
        END $$
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER trg_video_assessments_validate_links
        AFTER INSERT OR UPDATE OF video_version_id, eligibility_review_id
        ON app.video_assessments DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION app.validate_video_assessment_links()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS trg_video_assessments_validate_links ON app.video_assessments"
    )
    op.execute("DROP FUNCTION IF EXISTS app.validate_video_assessment_links()")
    op.drop_table("video_assessments", schema="app")
