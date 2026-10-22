"""FastAPI application factory and ASGI entry point."""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Final

from fastapi import FastAPI, HTTPException, status
from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError

from app.api.errors import install_error_handlers
from app.api.middleware import install_request_context
from app.api.v1.router import router as v1_router
from app.db.session import close_database, get_database

APP_NAME: Final = "YAQin API"
APP_VERSION: Final = "0.1.0"


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    """Release pooled database connections without connecting during startup."""
    del application
    yield
    await close_database()


def create_app() -> FastAPI:
    """Create the API without performing network or database work at import time."""
    expose_contract = os.getenv("APP_ENV", "development") in {"development", "staging", "test"}
    application = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
        description="API aplikasi pendampingan hafalan Juz 30.",
        lifespan=lifespan,
        openapi_url="/openapi.json" if expose_contract else None,
        docs_url="/docs" if expose_contract else None,
        redoc_url=None,
    )
    install_request_context(application)
    install_error_handlers(application)

    @application.get("/", tags=["system"])
    async def root() -> dict[str, str]:
        return {"name": APP_NAME, "version": APP_VERSION}

    @application.get("/health/live", tags=["health"])
    async def liveness() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/health/ready", tags=["health"])
    async def readiness() -> dict[str, str]:
        """Report readiness without exposing connection or credential details."""
        try:
            await get_database().ping()
        except (OSError, SQLAlchemyError, ValidationError) as error:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"status": "not_ready"},
            ) from error
        return {"status": "ready"}

    application.include_router(v1_router, prefix="/api/v1")
    return application


app = create_app()
