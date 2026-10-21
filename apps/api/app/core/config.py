"""Validated runtime configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache
from typing import Literal, Self
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url
from sqlalchemy.exc import ArgumentError


class AppEnvironment(StrEnum):
    """Deployment environments supported by the API."""

    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class Settings(BaseSettings):
    """Application settings with validation at the process boundary."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
        case_sensitive=True,
    )

    app_env: AppEnvironment = Field(default=AppEnvironment.DEVELOPMENT, alias="APP_ENV")
    app_version: str = Field(default="0.1.0", min_length=1, alias="APP_VERSION")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", alias="LOG_LEVEL"
    )

    database_url: SecretStr = Field(alias="DATABASE_URL")
    database_pool_size: int = Field(default=5, ge=1, le=50, alias="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=5, ge=0, le=50, alias="DATABASE_MAX_OVERFLOW")
    database_pool_timeout_seconds: int = Field(
        default=10, ge=1, le=120, alias="DATABASE_POOL_TIMEOUT_SECONDS"
    )
    database_pool_recycle_seconds: int = Field(
        default=1800, ge=30, le=86_400, alias="DATABASE_POOL_RECYCLE_SECONDS"
    )
    database_statement_timeout_ms: int = Field(
        default=15_000, ge=100, le=300_000, alias="DATABASE_STATEMENT_TIMEOUT_MS"
    )
    database_idle_transaction_timeout_ms: int = Field(
        default=30_000,
        ge=100,
        le=300_000,
        alias="DATABASE_IDLE_TRANSACTION_TIMEOUT_MS",
    )
    business_timezone: str = Field(default="Asia/Jakarta", alias="BUSINESS_TIMEZONE")

    @field_validator("database_url", mode="before")
    @classmethod
    def validate_database_url(cls, value: object) -> SecretStr:
        """Accept PostgreSQL URLs only and select psycopg's async-capable dialect."""
        raw_value = value.get_secret_value() if isinstance(value, SecretStr) else str(value)
        try:
            url = make_url(raw_value)
        except ArgumentError as error:
            raise ValueError("DATABASE_URL must be a valid SQLAlchemy URL") from error

        if url.drivername not in {"postgresql", "postgresql+psycopg"}:
            raise ValueError("DATABASE_URL must use PostgreSQL with the psycopg driver")
        if not url.database:
            raise ValueError("DATABASE_URL must include a database name")

        normalized = url.set(drivername="postgresql+psycopg")
        return SecretStr(normalized.render_as_string(hide_password=False))

    @field_validator("business_timezone")
    @classmethod
    def validate_business_timezone(cls, value: str) -> str:
        """Reject misspelled or unavailable IANA timezone names during startup."""
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError as error:
            raise ValueError("BUSINESS_TIMEZONE must be a valid IANA timezone") from error
        return value

    @model_validator(mode="after")
    def reject_development_password_outside_development(self) -> Self:
        """Prevent the documented local password from reaching shared environments."""
        if self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}:
            password = make_url(self.database_url_value).password
            if password in {None, "", "change-me-local-only", "change-me"}:
                raise ValueError("DATABASE_URL must use a non-placeholder password")
        return self

    @property
    def database_url_value(self) -> str:
        """Return the connection URL only at the database integration boundary."""
        return self.database_url.get_secret_value()

    @property
    def database_connect_options(self) -> str:
        """Return PostgreSQL session safeguards applied to every pooled connection."""
        return " ".join(
            (
                "-c timezone=UTC",
                f"-c statement_timeout={self.database_statement_timeout_ms}",
                "-c idle_in_transaction_session_timeout="
                f"{self.database_idle_transaction_timeout_ms}",
            )
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Load and cache settings once per application process."""
    return Settings()  # type: ignore[call-arg]  # populated by BaseSettings sources


def clear_settings_cache() -> None:
    """Clear cached settings for tests and controlled process reconfiguration."""
    get_settings.cache_clear()
