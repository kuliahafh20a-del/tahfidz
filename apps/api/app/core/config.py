"""Validated runtime configuration loaded from environment variables."""

from enum import StrEnum
from functools import lru_cache
from typing import Literal, Self
from urllib.parse import urlsplit, urlunsplit
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
    session_secret: SecretStr = Field(
        default=SecretStr("development-session-secret-change-me-32"),
        min_length=32,
        alias="SESSION_SECRET",
    )
    csrf_secret: SecretStr = Field(
        default=SecretStr("development-csrf-secret-change-me-32chars"),
        min_length=32,
        alias="CSRF_SECRET",
    )
    session_ttl_seconds: int = Field(
        default=43_200,
        ge=300,
        le=604_800,
        alias="SESSION_TTL_SECONDS",
    )
    recovery_token_ttl_seconds: int = Field(
        default=1_800,
        ge=300,
        le=86_400,
        alias="RECOVERY_TOKEN_TTL_SECONDS",
    )
    login_rate_limit_attempts: int = Field(
        default=5,
        ge=1,
        le=100,
        alias="LOGIN_RATE_LIMIT_ATTEMPTS",
    )
    login_rate_limit_window_seconds: int = Field(
        default=900,
        ge=60,
        le=86_400,
        alias="LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    )
    recovery_rate_limit_attempts: int = Field(
        default=3,
        ge=1,
        le=100,
        alias="RECOVERY_RATE_LIMIT_ATTEMPTS",
    )
    recovery_rate_limit_window_seconds: int = Field(
        default=3_600,
        ge=60,
        le=86_400,
        alias="RECOVERY_RATE_LIMIT_WINDOW_SECONDS",
    )
    video_allowed_hosts: str = Field(
        default="youtube.com,www.youtube.com,youtu.be",
        min_length=1,
        alias="VIDEO_ALLOWED_HOSTS",
    )
    object_storage_endpoint: str = Field(
        default="http://object-storage:9000",
        alias="OBJECT_STORAGE_ENDPOINT",
    )
    object_storage_public_endpoint: str = Field(
        default="http://localhost:9000",
        alias="OBJECT_STORAGE_PUBLIC_ENDPOINT",
    )
    object_storage_bucket: str = Field(
        default="yaqin-private",
        min_length=3,
        max_length=63,
        pattern=r"^[a-z0-9][a-z0-9.-]*[a-z0-9]$",
        alias="OBJECT_STORAGE_BUCKET",
    )
    object_storage_region: str = Field(
        default="us-east-1",
        min_length=1,
        max_length=64,
        alias="OBJECT_STORAGE_REGION",
    )
    object_storage_access_key: SecretStr = Field(
        default=SecretStr("change-me"),
        min_length=3,
        alias="OBJECT_STORAGE_ACCESS_KEY",
    )
    object_storage_secret_key: SecretStr = Field(
        default=SecretStr("change-me"),
        min_length=8,
        alias="OBJECT_STORAGE_SECRET_KEY",
    )
    signed_url_ttl_seconds: int = Field(
        default=300,
        ge=60,
        le=900,
        alias="SIGNED_URL_TTL_SECONDS",
    )
    audio_allowed_content_types: str = Field(
        default="audio/mp4,audio/mpeg,audio/ogg,audio/webm",
        min_length=1,
        alias="AUDIO_ALLOWED_CONTENT_TYPES",
    )
    audio_max_size_bytes: int = Field(
        default=10_485_760,
        ge=1,
        le=104_857_600,
        alias="AUDIO_MAX_SIZE_BYTES",
    )
    media_worker_poll_seconds: float = Field(
        default=2.0,
        ge=0.1,
        le=60.0,
        alias="MEDIA_WORKER_POLL_SECONDS",
    )
    media_validation_max_attempts: int = Field(
        default=5,
        ge=1,
        le=20,
        alias="MEDIA_VALIDATION_MAX_ATTEMPTS",
    )

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

    @field_validator("video_allowed_hosts")
    @classmethod
    def validate_video_allowed_hosts(cls, value: str) -> str:
        hosts = [item.strip().lower().rstrip(".") for item in value.split(",")]
        if not hosts or any(not item or ":" in item or "/" in item for item in hosts):
            raise ValueError("VIDEO_ALLOWED_HOSTS must be a comma-separated hostname list")
        return ",".join(dict.fromkeys(hosts))

    @field_validator("object_storage_endpoint", "object_storage_public_endpoint")
    @classmethod
    def validate_object_storage_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("object storage endpoint must be an absolute HTTP(S) URL")
        if parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("object storage endpoint must not contain credentials or query data")
        path = parsed.path.rstrip("/")
        return urlunsplit((parsed.scheme, parsed.netloc.lower(), path, "", ""))

    @field_validator("audio_allowed_content_types")
    @classmethod
    def validate_audio_allowed_content_types(cls, value: str) -> str:
        content_types = [item.strip().lower() for item in value.split(",")]
        if not content_types or any(
            not item.startswith("audio/") or ";" in item or " " in item for item in content_types
        ):
            raise ValueError("AUDIO_ALLOWED_CONTENT_TYPES must contain audio MIME types")
        return ",".join(dict.fromkeys(content_types))

    @model_validator(mode="after")
    def reject_development_password_outside_development(self) -> Self:
        """Prevent the documented local password from reaching shared environments."""
        if self.app_env in {AppEnvironment.STAGING, AppEnvironment.PRODUCTION}:
            password = make_url(self.database_url_value).password
            if password in {None, "", "change-me-local-only", "change-me"}:
                raise ValueError("DATABASE_URL must use a non-placeholder password")
            forbidden_auth_secrets = {
                "change-me-with-at-least-32-random-characters",
                "development-session-secret-change-me-32",
                "development-csrf-secret-change-me-32chars",
            }
            if self.session_secret_value in forbidden_auth_secrets:
                raise ValueError("SESSION_SECRET must not use a placeholder")
            if self.csrf_secret_value in forbidden_auth_secrets:
                raise ValueError("CSRF_SECRET must not use a placeholder")
            if self.object_storage_access_key_value == "change-me":
                raise ValueError("OBJECT_STORAGE_ACCESS_KEY must not use a placeholder")
            if self.object_storage_secret_key_value == "change-me":
                raise ValueError("OBJECT_STORAGE_SECRET_KEY must not use a placeholder")
        return self

    @property
    def database_url_value(self) -> str:
        """Return the connection URL only at the database integration boundary."""
        return self.database_url.get_secret_value()

    @property
    def session_secret_value(self) -> str:
        """Reveal the session HMAC secret only inside the authentication boundary."""
        return self.session_secret.get_secret_value()

    @property
    def csrf_secret_value(self) -> str:
        """Reveal the CSRF HMAC secret only inside the authentication boundary."""
        return self.csrf_secret.get_secret_value()

    @property
    def secure_auth_cookie(self) -> bool:
        """Require HTTPS cookies outside local development and isolated tests."""
        return self.app_env not in {AppEnvironment.DEVELOPMENT, AppEnvironment.TEST}

    @property
    def video_allowed_host_values(self) -> frozenset[str]:
        return frozenset(self.video_allowed_hosts.split(","))

    @property
    def object_storage_access_key_value(self) -> str:
        return self.object_storage_access_key.get_secret_value()

    @property
    def object_storage_secret_key_value(self) -> str:
        return self.object_storage_secret_key.get_secret_value()

    @property
    def audio_allowed_content_type_values(self) -> frozenset[str]:
        return frozenset(self.audio_allowed_content_types.split(","))

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
