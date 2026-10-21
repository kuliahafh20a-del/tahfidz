"""Import every mapped model and expose complete migration metadata."""

from sqlalchemy import MetaData

from app.db.base import Base
from app.modules.identity.models import RoleGrant, User
from app.modules.organizations.models import Organization

MODEL_TYPES = (Organization, User, RoleGrant)
metadata: MetaData = Base.metadata

__all__ = ["MODEL_TYPES", "metadata"]
