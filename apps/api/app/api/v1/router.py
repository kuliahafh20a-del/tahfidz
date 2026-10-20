"""Root router for the versioned API contract."""

from fastapi import APIRouter

router = APIRouter()


@router.get("", tags=["system"])
async def api_version() -> dict[str, str]:
    """Expose a stable smoke endpoint for the v1 route group."""
    return {"name": "YAQin API", "version": "v1"}
