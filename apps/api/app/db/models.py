"""Import every mapped model and expose complete migration metadata."""

from sqlalchemy import MetaData

from app.db.base import Base
from app.modules.curriculum.models import (
    CurriculumVersion,
    Part,
    PolicyVersion,
    Theme,
    ThemeRange,
)
from app.modules.identity.models import RoleGrant, User
from app.modules.organizations.models import Organization

MODEL_TYPES = (
    Organization,
    User,
    RoleGrant,
    PolicyVersion,
    CurriculumVersion,
    Part,
    Theme,
    ThemeRange,
)
metadata: MetaData = Base.metadata

__all__ = ["MODEL_TYPES", "metadata"]
