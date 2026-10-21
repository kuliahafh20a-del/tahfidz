"""Root router for the versioned API contract."""

from fastapi import APIRouter

from app.modules.curriculum.router import router as reference_router

router = APIRouter()
router.include_router(reference_router)


@router.get("", tags=["system"])
async def api_version() -> dict[str, str]:
    """Expose a stable smoke endpoint for the v1 route group."""
    return {"name": "YAQin API", "version": "v1"}
