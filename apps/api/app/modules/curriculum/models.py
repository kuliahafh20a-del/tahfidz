"""Persistent policy versions and immutable published Juz 30 curricula."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Enum,
    ForeignKey,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UTCDateTime, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.modules.identity.models import User


class PolicyStatus(StrEnum):
    """Lifecycle states for an academic policy version."""

    DRAFT = "draft"
    APPROVED = "approved"
    PUBLISHED = "published"
    INACTIVE = "inactive"


class CurriculumStatus(StrEnum):
    """Lifecycle states for a curriculum version."""

    DRAFT = "draft"
    PUBLISHED = "published"
    INACTIVE = "inactive"


class PolicyVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A validated, immutable-after-publish collection of academic rules."""

    __tablename__ = "policy_versions"
    __table_args__ = (
        CheckConstraint("length(btrim(version)) > 0", name="version_not_blank"),
        CheckConstraint("jsonb_typeof(rules) = 'object'", name="rules_object"),
        CheckConstraint(
            "status NOT IN ('approved', 'published') "
            "OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)",
            name="approval_required",
        ),
        CheckConstraint(
            "status <> 'published' OR effective_from IS NOT NULL",
            name="effective_from_required",
        ),
        {"schema": "app"},
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[PolicyStatus] = mapped_column(
        Enum(
            PolicyStatus,
            name="policy_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=PolicyStatus.DRAFT,
        server_default=PolicyStatus.DRAFT.value,
    )
    rules: Mapped[dict[str, object]] = mapped_column(JSONB, nullable=False)
    approved_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("app.users.id", ondelete="RESTRICT"),
        nullable=True,
    )
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    effective_from: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    approver: Mapped[User | None] = relationship()


class CurriculumVersion(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One complete, publishable version of the Juz 30 curriculum."""

    __tablename__ = "curriculum_versions"
    __table_args__ = (
        CheckConstraint("length(btrim(version)) > 0", name="version_not_blank"),
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "status <> 'published' OR published_at IS NOT NULL",
            name="published_at_required",
        ),
        {"schema": "app"},
    )

    version: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[CurriculumStatus] = mapped_column(
        Enum(
            CurriculumStatus,
            name="curriculum_status",
            native_enum=False,
            create_constraint=False,
            values_callable=lambda members: [member.value for member in members],
            length=16,
        ),
        nullable=False,
        default=CurriculumStatus.DRAFT,
        server_default=CurriculumStatus.DRAFT.value,
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)

    parts: Mapped[list[Part]] = relationship(
        back_populates="curriculum_version",
        cascade="all, delete-orphan",
        order_by="Part.sequence_no",
    )


class Part(UUIDPrimaryKeyMixin, Base):
    """One of the five ordered curriculum sections."""

    __tablename__ = "parts"
    __table_args__ = (
        CheckConstraint("sequence_no BETWEEN 1 AND 5", name="sequence_range"),
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        UniqueConstraint(
            "curriculum_version_id",
            "sequence_no",
            name="uq_parts__curriculum_version_id_sequence_no",
        ),
        {"schema": "app"},
    )

    curriculum_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.curriculum_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)

    curriculum_version: Mapped[CurriculumVersion] = relationship(back_populates="parts")
    themes: Mapped[list[Theme]] = relationship(
        back_populates="part",
        cascade="all, delete-orphan",
        order_by="Theme.sequence_no",
    )


class Theme(UUIDPrimaryKeyMixin, Base):
    """One ordered weekly memorization theme within a curriculum part."""

    __tablename__ = "themes"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="sequence_positive"),
        CheckConstraint("length(btrim(title)) > 0", name="title_not_blank"),
        UniqueConstraint(
            "part_id",
            "sequence_no",
            name="uq_themes__part_id_sequence_no",
        ),
        {"schema": "app"},
    )

    part_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.parts.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    part: Mapped[Part] = relationship(back_populates="themes")
    ranges: Mapped[list[ThemeRange]] = relationship(
        back_populates="theme",
        cascade="all, delete-orphan",
        order_by="ThemeRange.sequence_no",
    )


class ThemeRange(UUIDPrimaryKeyMixin, Base):
    """One ordered, inclusive verse range belonging to a theme."""

    __tablename__ = "theme_ranges"
    __table_args__ = (
        CheckConstraint("sequence_no > 0", name="sequence_positive"),
        CheckConstraint("surah_no BETWEEN 78 AND 114", name="surah_juz30"),
        CheckConstraint("ayah_start > 0", name="ayah_start_positive"),
        CheckConstraint("ayah_end >= ayah_start", name="ayah_order"),
        CheckConstraint(
            "ayah_end <= app.juz30_ayah_count(surah_no)",
            name="ayah_within_surah",
        ),
        UniqueConstraint(
            "theme_id",
            "sequence_no",
            name="uq_theme_ranges__theme_id_sequence_no",
        ),
        {"schema": "app"},
    )

    theme_id: Mapped[UUID] = mapped_column(
        ForeignKey("app.themes.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    surah_no: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ayah_start: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ayah_end: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    theme: Mapped[Theme] = relationship(back_populates="ranges")
