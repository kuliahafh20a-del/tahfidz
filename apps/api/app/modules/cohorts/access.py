"""Department authorization boundary awaiting session authentication in TASK-008."""

from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.time import utc_now
from app.db.session import get_session
from app.modules.identity.models import Role, RoleGrant


@dataclass(frozen=True, slots=True)
class DepartmentActor:
    """A session-derived department administrator scope."""

    user_id: UUID
    organization_id: UUID


async def get_department_actor(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> DepartmentActor:
    """Require a verified actor placed on request state by the authentication layer."""
    actor = getattr(request.state, "department_actor", None)
    if not isinstance(actor, DepartmentActor):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "authentication_required"},
        )

    now = utc_now()
    grant = await session.scalar(
        select(RoleGrant.id).where(
            RoleGrant.user_id == actor.user_id,
            RoleGrant.organization_id == actor.organization_id,
            RoleGrant.role == Role.DEPARTMENT_ADMIN,
            RoleGrant.valid_from <= now,
            (RoleGrant.valid_to.is_(None) | (RoleGrant.valid_to > now)),
        )
    )
    if grant is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "department_scope_required"},
        )
    return actor


DepartmentActorDependency = Annotated[DepartmentActor, Depends(get_department_actor)]
