"""Stable API schemas for policy and curriculum reference data."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RubricBand(BaseModel):
    """An inclusive integer score band and its approved description."""

    minimum: int = Field(ge=1, le=10)
    maximum: int = Field(ge=1, le=10)
    description: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_order(self) -> RubricBand:
        if self.maximum < self.minimum:
            raise ValueError("rubric maximum must be greater than or equal to minimum")
        return self


class IntegerScorePolicy(BaseModel):
    """The DEC-001 score scale exposed to every scoring interface."""

    minimum: int = 1
    maximum: int = 10
    step: int = 1
    allow_fractional: bool = False
    display_decimals: int = 0
    bands: list[RubricBand] = Field(min_length=3)

    @model_validator(mode="after")
    def validate_integer_policy(self) -> IntegerScorePolicy:
        if (
            self.minimum != 1
            or self.maximum != 10
            or self.step != 1
            or self.allow_fractional
            or self.display_decimals != 0
        ):
            raise ValueError("initial score policy must use whole numbers from 1 to 10")
        if [(band.minimum, band.maximum) for band in self.bands] != [
            (1, 4),
            (5, 7),
            (8, 10),
        ]:
            raise ValueError("rubric bands must cover 1-4, 5-7, and 8-10")
        return self


class VideoAssessmentPolicy(BaseModel):
    """Rules that turn counted video incidents into an academic result."""

    maximum_errors_for_enough: int = Field(default=3, ge=0)


class ExamPackagePolicy(BaseModel):
    """Open DEC-002 package settings; unapproved values cannot enable an exam."""

    approved: bool = False
    required_item_count: int | None = Field(default=None, ge=1)
    expected_total_weight: int | None = Field(default=None, ge=1, le=100)
    aggregation_method: Literal["simple_average", "weighted_average"] | None = None

    @model_validator(mode="after")
    def require_approved_values(self) -> ExamPackagePolicy:
        if self.approved and (
            self.required_item_count is None
            or self.expected_total_weight is None
            or self.aggregation_method is None
        ):
            raise ValueError(
                "approved exam package policy requires item count, total weight, and aggregation"
            )
        return self


class MentorAggregationPolicy(BaseModel):
    """DEC-002 gate for deriving M from final mentor assessments."""

    approved: bool = False
    aggregation_method: Literal["simple_average"] | None = None

    @model_validator(mode="after")
    def require_method_when_approved(self) -> MentorAggregationPolicy:
        if self.approved and self.aggregation_method is None:
            raise ValueError("approved mentor aggregation requires an aggregation method")
        return self


class GradeCalculationPolicy(BaseModel):
    """Versioned final-score weights and threshold."""

    approved: bool = False
    k_weight: float = 0.2
    m_weight: float = 0.4
    d_weight: float = 0.4
    graduation_threshold: float = 6.0

    @model_validator(mode="after")
    def validate_weights(self) -> GradeCalculationPolicy:
        if round(self.k_weight + self.m_weight + self.d_weight, 6) != 1:
            raise ValueError("grade component weights must total 1")
        return self


class PolicyRules(BaseModel):
    """Validated JSON document stored by a policy version."""

    schema_version: int = 1
    score: IntegerScorePolicy
    video_assessment: VideoAssessmentPolicy = Field(default_factory=VideoAssessmentPolicy)
    exam_package: ExamPackagePolicy = Field(default_factory=ExamPackagePolicy)
    mentor_aggregation: MentorAggregationPolicy = Field(default_factory=MentorAggregationPolicy)
    grade_calculation: GradeCalculationPolicy = Field(default_factory=GradeCalculationPolicy)


class PolicySummary(BaseModel):
    """The effective policy version without unrelated rule internals."""

    id: UUID
    version: str
    status: str
    effective_from: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentRubricResponse(BaseModel):
    """The effective score policy used by assessment forms."""

    policy_id: UUID
    policy_version: str
    score: IntegerScorePolicy


class ThemeRangeResponse(BaseModel):
    """An inclusive Juz 30 verse range."""

    sequence_no: int
    surah_no: int
    ayah_start: int
    ayah_end: int

    model_config = ConfigDict(from_attributes=True)


class ThemeResponse(BaseModel):
    """An ordered curriculum theme with one or more verse ranges."""

    sequence_no: int
    title: str
    description: str | None
    ranges: list[ThemeRangeResponse]

    model_config = ConfigDict(from_attributes=True)


class PartResponse(BaseModel):
    """One ordered curriculum part."""

    sequence_no: int
    title: str
    themes: list[ThemeResponse]

    model_config = ConfigDict(from_attributes=True)


class CurriculumResponse(BaseModel):
    """The complete effective curriculum reference tree."""

    id: UUID
    version: str
    title: str
    published_at: datetime
    parts: list[PartResponse]

    model_config = ConfigDict(from_attributes=True)
