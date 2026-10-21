"""Timezone helpers for absolute timestamps and Asia/Jakarta business dates."""

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

BUSINESS_TIMEZONE = ZoneInfo("Asia/Jakarta")


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""
    return datetime.now(UTC)


def ensure_utc(value: datetime) -> datetime:
    """Normalize an aware timestamp to UTC and reject ambiguous naive values."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must include timezone information")
    return value.astimezone(UTC)


def business_date(value: datetime, timezone: ZoneInfo = BUSINESS_TIMEZONE) -> date:
    """Convert an absolute timestamp to the configured academic calendar date."""
    return ensure_utc(value).astimezone(timezone).date()
