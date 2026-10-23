from datetime import UTC, date, datetime, timedelta

import pytest

from app.modules.grading.service import ActivityScoreCalculator


@pytest.mark.parametrize(
    ("days_late", "expected"),
    [
        (0, 10),
        (1, 9),
        (7, 9),
        (8, 8),
        (14, 8),
        (15, 7),
        (21, 7),
        (22, 6),
        (28, 6),
        (29, 5),
        (35, 5),
        (36, 4),
        (42, 4),
        (43, 3),
        (49, 3),
        (50, 2),
    ],
)
def test_activity_score_bucket_boundaries(days_late: int, expected: int) -> None:
    due = date(2027, 1, 1)
    submitted = datetime(2027, 1, 1, 5, tzinfo=UTC) + timedelta(days=days_late)

    score, actual_days = ActivityScoreCalculator.score_for_submission(due, submitted)

    assert score == expected
    assert actual_days == days_late


def test_activity_score_uses_asia_jakarta_calendar_date() -> None:
    due = date(2027, 1, 1)
    submitted = datetime(2027, 1, 1, 18, 0, tzinfo=UTC)

    score, days_late = ActivityScoreCalculator.score_for_submission(due, submitted)

    assert days_late == 1
    assert score == 9


def test_missing_submission_is_not_scored_before_period_closes() -> None:
    score, days_late = ActivityScoreCalculator.score_for_target(
        date(2027, 1, 1),
        None,
        cutoff_date=date(2027, 2, 1),
        period_closed=False,
    )

    assert score is None
    assert days_late is None


def test_closed_period_scores_only_targets_past_due() -> None:
    overdue_score, _ = ActivityScoreCalculator.score_for_target(
        date(2027, 1, 1),
        None,
        cutoff_date=date(2027, 2, 1),
        period_closed=True,
    )
    future_score, _ = ActivityScoreCalculator.score_for_target(
        date(2027, 3, 1),
        None,
        cutoff_date=date(2027, 2, 1),
        period_closed=True,
    )

    assert overdue_score == 1
    assert future_score is None
