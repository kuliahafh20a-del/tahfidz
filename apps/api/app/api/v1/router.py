"""Root router for the versioned API contract."""

from fastapi import APIRouter

from app.modules.auth.router import router as auth_router
from app.modules.cohorts.router import router as department_router
from app.modules.curriculum.router import router as reference_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(reference_router)
router.include_router(department_router)


@router.get("", tags=["system"])
async def api_version() -> dict[str, str]:
    """Expose a stable smoke endpoint for the v1 route group."""
    return {"name": "YAQin API", "version": "v1"}
