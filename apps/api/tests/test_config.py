import pytest
from pydantic import ValidationError

from app.core.config import AppEnvironment, Settings


def test_settings_normalize_postgresql_url_and_pool_options() -> None:
    settings = Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://yaqin:secret@localhost:5432/yaqin_test",
            "DATABASE_POOL_SIZE": 7,
            "DATABASE_STATEMENT_TIMEOUT_MS": 5000,
        }
    )

    assert settings.database_url_value.startswith("postgresql+psycopg://")
    assert settings.database_pool_size == 7
    assert "statement_timeout=5000" in settings.database_connect_options
    assert "timezone=UTC" in settings.database_connect_options
    assert "postgresql://yaqin:secret" not in repr(settings)
    assert "session-secret-change" not in repr(settings)


@pytest.mark.parametrize(
    "database_url",
    (
        "sqlite:///local.db",
        "mysql://yaqin:secret@localhost/yaqin",
        "not-a-url",
    ),
)
def test_settings_reject_non_postgresql_database_urls(database_url: str) -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings.model_validate({"DATABASE_URL": database_url})


def test_settings_reject_placeholder_password_in_production() -> None:
    with pytest.raises(ValidationError, match="non-placeholder password"):
        Settings.model_validate(
            {
                "APP_ENV": AppEnvironment.PRODUCTION,
                "DATABASE_URL": ("postgresql+psycopg://yaqin:change-me-local-only@localhost/yaqin"),
            }
        )


def test_settings_reject_placeholder_auth_secrets_in_production() -> None:
    with pytest.raises(ValidationError, match="SESSION_SECRET"):
        Settings.model_validate(
            {
                "APP_ENV": AppEnvironment.PRODUCTION,
                "DATABASE_URL": "postgresql://yaqin:a-real-password@localhost/yaqin",
                "SESSION_SECRET": "change-me-with-at-least-32-random-characters",
                "CSRF_SECRET": "a-real-csrf-secret-with-at-least-32-characters",
            }
        )


def test_settings_reject_placeholder_storage_secrets_in_production() -> None:
    with pytest.raises(ValidationError, match="OBJECT_STORAGE_ACCESS_KEY"):
        Settings.model_validate(
            {
                "APP_ENV": AppEnvironment.PRODUCTION,
                "DATABASE_URL": "postgresql://yaqin:a-real-password@localhost/yaqin",
                "SESSION_SECRET": "a-real-session-secret-with-at-least-32-characters",
                "CSRF_SECRET": "a-real-csrf-secret-with-at-least-32-characters",
                "OBJECT_STORAGE_ACCESS_KEY": "change-me",
                "OBJECT_STORAGE_SECRET_KEY": "a-real-storage-secret",
            }
        )


def test_settings_reject_unknown_business_timezone() -> None:
    with pytest.raises(ValidationError, match="IANA timezone"):
        Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
                "BUSINESS_TIMEZONE": "Mars/Olympus_Mons",
            }
        )


def test_settings_normalize_video_host_allowlist() -> None:
    settings = Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
            "VIDEO_ALLOWED_HOSTS": " YouTube.com, youtu.be,YOUTUBE.COM ",
        }
    )

    assert settings.video_allowed_host_values == frozenset({"youtube.com", "youtu.be"})

    with pytest.raises(ValidationError, match="hostname list"):
        Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
                "VIDEO_ALLOWED_HOSTS": "https://youtube.com",
            }
        )


def test_settings_validate_private_media_boundaries() -> None:
    settings = Settings.model_validate(
        {
            "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
            "OBJECT_STORAGE_ENDPOINT": "http://OBJECT-STORAGE:9000/",
            "OBJECT_STORAGE_PUBLIC_ENDPOINT": "https://media.example.test/",
            "AUDIO_ALLOWED_CONTENT_TYPES": " AUDIO/MP4,audio/mpeg,audio/mp4 ",
            "AUDIO_MAX_SIZE_BYTES": 1024,
        }
    )

    assert settings.object_storage_endpoint == "http://object-storage:9000"
    assert settings.object_storage_public_endpoint == "https://media.example.test"
    assert settings.audio_allowed_content_type_values == frozenset({"audio/mp4", "audio/mpeg"})
    assert settings.audio_max_size_bytes == 1024

    with pytest.raises(ValidationError, match="audio MIME types"):
        Settings.model_validate(
            {
                "DATABASE_URL": "postgresql://yaqin:secret@localhost/yaqin",
                "AUDIO_ALLOWED_CONTENT_TYPES": "application/octet-stream",
            }
        )
