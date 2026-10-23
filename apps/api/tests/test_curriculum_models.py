from typing import Any

import pytest
from pydantic import ValidationError

from app.db.base import Base
from app.modules.curriculum.schemas import PolicyRules

VALID_RULES: dict[str, Any] = {
    "schema_version": 1,
    "score": {
        "minimum": 1,
        "maximum": 10,
        "step": 1,
        "allow_fractional": False,
        "display_decimals": 0,
        "bands": [
            {"minimum": 1, "maximum": 4, "description": "Perlu perbaikan mendasar."},
            {"minimum": 5, "maximum": 7, "description": "Cukup dengan catatan."},
            {"minimum": 8, "maximum": 10, "description": "Baik sampai sangat baik."},
        ],
    },
}


def test_curriculum_models_are_registered() -> None:
    assert set(Base.metadata.tables) >= {
        "app.policy_versions",
        "app.curriculum_versions",
        "app.parts",
        "app.themes",
        "app.theme_ranges",
    }


def test_policy_rules_accept_the_approved_integer_scale() -> None:
    rules = PolicyRules.model_validate(VALID_RULES)

    assert rules.score.minimum == 1
    assert rules.score.maximum == 10
    assert rules.score.step == 1
    assert rules.score.allow_fractional is False
    assert rules.score.display_decimals == 0
    assert rules.video_assessment.maximum_errors_for_enough == 3
    assert rules.exam_package.approved is False
    assert rules.exam_package.required_item_count is None
    assert rules.exam_package.expected_total_weight is None


def test_approved_exam_package_policy_requires_count_and_total_weight() -> None:
    rules = {
        **VALID_RULES,
        "exam_package": {
            "approved": True,
            "required_item_count": None,
            "expected_total_weight": None,
        },
    }

    with pytest.raises(ValidationError):
        PolicyRules.model_validate(rules)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("allow_fractional", True),
        ("display_decimals", 1),
        ("step", 2),
    ],
)
def test_policy_rules_reject_non_integer_score_settings(
    field: str,
    value: bool | int,
) -> None:
    score = dict(VALID_RULES["score"])
    score[field] = value
    rules = {"schema_version": 1, "score": score}

    with pytest.raises(ValidationError):
        PolicyRules.model_validate(rules)
