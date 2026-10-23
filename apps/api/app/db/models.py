"""Import every mapped model and expose complete migration metadata."""

from sqlalchemy import MetaData

from app.db.base import Base
from app.modules.assessments.models import (
    AssessmentRecord,
    ExamAssessment,
    Incident,
    ThemeAssessment,
    VideoAssessment,
)
from app.modules.audit.models import AuditEvent
from app.modules.auth.models import AuthRateLimitEvent, AuthSession, PasswordRecoveryToken
from app.modules.calendar.models import DeadlineChange, Target
from app.modules.cohorts.models import Assignment, Cohort, Enrollment
from app.modules.curriculum.models import (
    CurriculumVersion,
    Part,
    PolicyVersion,
    Theme,
    ThemeRange,
)
from app.modules.exams.models import Exam, ExamItem, QuestionVersion
from app.modules.identity.models import RoleGrant, User
from app.modules.media.models import MediaAsset
from app.modules.mentoring.models import MentoringSession, SessionTheme
from app.modules.operations.models import IdempotencyRecord
from app.modules.organizations.models import Organization
from app.modules.video.models import (
    EligibilityCheck,
    EligibilityReview,
    VideoAttempt,
    VideoVersion,
)

MODEL_TYPES = (
    Organization,
    User,
    RoleGrant,
    PolicyVersion,
    CurriculumVersion,
    Part,
    Theme,
    ThemeRange,
    Cohort,
    Enrollment,
    Assignment,
    Target,
    DeadlineChange,
    MentoringSession,
    SessionTheme,
    AssessmentRecord,
    ThemeAssessment,
    VideoAssessment,
    ExamAssessment,
    Incident,
    AuditEvent,
    AuthSession,
    PasswordRecoveryToken,
    AuthRateLimitEvent,
    IdempotencyRecord,
    VideoAttempt,
    VideoVersion,
    EligibilityReview,
    EligibilityCheck,
    MediaAsset,
    QuestionVersion,
    Exam,
    ExamItem,
)
metadata: MetaData = Base.metadata

__all__ = ["MODEL_TYPES", "metadata"]
