"""FastAPI dependency wiring for authentication infrastructure."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_session
from app.modules.auth.security import PasswordManager
from app.modules.auth.service import AuthService


@lru_cache(maxsize=1)
def get_password_manager() -> PasswordManager:
    """Create the memory-hard password hasher once per process."""
    return PasswordManager()


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings, get_password_manager())


AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
