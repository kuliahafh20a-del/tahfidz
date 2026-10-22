from datetime import date

import pytest
from pydantic import ValidationError

from app.db.base import Base
from app.modules.video.models import VideoAttempt, VideoAttemptStatus, VideoVersion
from app.modules.video.schemas import VideoVersionCreate
from app.modules.video.service import (
    VideoConflictError,
    VideoSubmissionService,
    VideoUrlNotAllowedError,
)


def test_video_models_register_slot_and_version_constraints() -> None:
    attempts = Base.metadata.tables["app.video_attempts"]
    versions = Base.metadata.tables["app.video_versions"]

    assert VideoAttempt.__table__ is attempts
    assert VideoVersion.__table__ is versions
    assert any(
        constraint.name == "uq_video_attempts__enrollment_part_cycle_revision"
        for constraint in attempts.constraints
    )
    assert any(
        constraint.name == "uq_video_versions__attempt_id_version_no"
        for constraint in versions.constraints
    )


def test_video_url_requires_https_without_credentials_or_custom_port() -> None:
    valid = VideoVersionCreate(
        video_url="https://WWW.YOUTUBE.COM/watch?v=test#fragment",
        recorded_on=date(2026, 10, 20),
        completeness_declared=True,
        expected_version=1,
    )
    assert valid.video_url == "https://www.youtube.com/watch?v=test"

    for unsafe in (
        "http://youtube.com/watch?v=test",
        "https://user:secret@youtube.com/watch?v=test",
        "https://youtube.com:8443/watch?v=test",
    ):
        with pytest.raises(ValidationError):
            VideoVersionCreate(
                video_url=unsafe,
                recorded_on=date(2026, 10, 20),
                completeness_declared=True,
                expected_version=1,
            )


def test_host_allowlist_uses_exact_hostname_without_fetching() -> None:
    service = VideoSubmissionService(None, frozenset({"youtube.com"}))  # type: ignore[arg-type]
    service._validate_host("https://youtube.com/watch?v=test")
    with pytest.raises(VideoUrlNotAllowedError):
        service._validate_host("https://youtube.com.attacker.example/watch?v=test")


def test_server_allocates_revision_then_new_cycle_only_after_closed_slot() -> None:
    assert VideoSubmissionService._next_slot(None) == (1, 0)
    for revision in range(3):
        latest = VideoAttempt(
            enrollment_id="73000000-0000-4000-8000-000000000001",
            part_id="73000000-0000-4000-8000-000000000002",
            cycle_no=1,
            revision_no=revision,
            status=VideoAttemptStatus.CLOSED,
        )
        assert VideoSubmissionService._next_slot(latest) == (1, revision + 1)

    latest.revision_no = 3
    assert VideoSubmissionService._next_slot(latest) == (2, 0)
    latest.status = VideoAttemptStatus.SUBMITTED
    with pytest.raises(VideoConflictError):
        VideoSubmissionService._next_slot(latest)
