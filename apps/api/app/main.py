"""FastAPI application factory and ASGI entry point."""

from typing import Final

from fastapi import FastAPI

from app.api.v1.router import router as v1_router

APP_NAME: Final = "YAQin API"
APP_VERSION: Final = "0.1.0"


def create_app() -> FastAPI:
    """Create the API without performing network or database work at import time."""
    application = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="API aplikasi pendampingan hafalan Juz 30.",
    )

    @application.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {"name": APP_NAME, "version": APP_VERSION}

    @application.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    application.include_router(v1_router, prefix="/api/v1")
    return application


app = create_app()
