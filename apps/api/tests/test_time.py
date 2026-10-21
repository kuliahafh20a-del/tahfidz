from datetime import UTC, datetime

import pytest
from sqlalchemy.engine.default import DefaultDialect

from app.core.time import business_date, ensure_utc
from app.db.base import UTCDateTime


def test_business_date_uses_asia_jakarta_calendar_boundary() -> None:
    late_utc = datetime(2026, 10, 20, 18, 30, tzinfo=UTC)

    assert business_date(late_utc).isoformat() == "2026-10-21"


def test_timezone_helpers_reject_naive_datetime() -> None:
    naive = datetime(2026, 10, 21, 1, 0)
    dialect = DefaultDialect()

    with pytest.raises(ValueError, match="timezone information"):
        ensure_utc(naive)

    with pytest.raises(ValueError, match="timezone information"):
        UTCDateTime().process_bind_param(naive, dialect)


def test_utc_datetime_normalizes_offset() -> None:
    jakarta_midnight = datetime.fromisoformat("2026-10-21T00:00:00+07:00")
    dialect = DefaultDialect()

    normalized = UTCDateTime().process_bind_param(jakarta_midnight, dialect)

    assert normalized == datetime(2026, 10, 20, 17, 0, tzinfo=UTC)
