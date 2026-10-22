"""Department authorization derived from the verified active session context."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, status

from app.modules.auth.access import AuthenticatedSessionDependency
from app.modules.identity.models import Role


@dataclass(frozen=True, slots=True)
class DepartmentActor:
    """A session-derived department administrator scope."""

    user_id: UUID
    organization_id: UUID


async def get_department_actor(
    authenticated: AuthenticatedSessionDependency,
) -> DepartmentActor:
    """Require a currently granted department-admin context from the opaque session."""
    context = authenticated.active_context
    if context is None or context.role is not Role.DEPARTMENT_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "department_scope_required"},
        )
    return DepartmentActor(
        user_id=authenticated.user_id,
        organization_id=context.organization_id,
    )


DepartmentActorDependency = Annotated[DepartmentActor, Depends(get_department_actor)]
