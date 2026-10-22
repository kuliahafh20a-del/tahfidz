"""Root router for the versioned API contract."""

from fastapi import APIRouter, Request

from app.api.contracts import SuccessEnvelope, success
from app.api.errors import ERROR_RESPONSES
from app.modules.auth.router import router as auth_router
from app.modules.calendar.admin_router import router as calendar_admin_router
from app.modules.calendar.router import router as participant_router
from app.modules.cohorts.router import router as department_router
from app.modules.curriculum.router import router as reference_router

router = APIRouter(responses=ERROR_RESPONSES)
router.include_router(auth_router)
router.include_router(reference_router)
router.include_router(department_router)
router.include_router(participant_router)
router.include_router(calendar_admin_router)


@router.get("", tags=["system"], response_model=SuccessEnvelope[dict[str, str]])
async def api_version(request: Request) -> SuccessEnvelope[dict[str, str]]:
    """Expose a stable smoke endpoint for the v1 route group."""
    return success(request, {"name": "YAQin API", "version": "v1"})
