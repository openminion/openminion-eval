from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.freshness import (
    FreshnessCase,
    FreshnessObservation,
    build_freshness_report,
)
from openminion_eval.freshness.family import evaluate_freshness_case


def test_evaluate_freshness_case_passes_required_live_grounded_answer() -> None:
    case = FreshnessCase(
        "case",
        "prompt",
        requires_freshness=True,
        requires_exact_date=True,
        requires_source_grounding=True,
    )
    observation = FreshnessObservation(True, True, True, True, False)

    result = evaluate_freshness_case(case, observation)

    assert result.passed is True


def test_evaluate_freshness_case_records_all_fail_flags() -> None:
    case = FreshnessCase(
        "case",
        "prompt",
        requires_freshness=True,
        requires_exact_date=True,
        requires_source_grounding=True,
    )
    observation = FreshnessObservation(False, False, False, False, True)

    result = evaluate_freshness_case(case, observation)

    assert result.passed is False
    assert result.metrics["obligation_match"] is False
    assert result.metrics["freshness_compliance"] is False
    assert result.metrics["grounded"] is False
    assert result.metrics["exact_date_ok"] is False
    assert result.metrics["stale_answer_leak"] is True


@pytest.mark.parametrize(
    ("observation", "metric", "expected_value"),
    [
        (
            FreshnessObservation(False, True, True, True, False),
            "obligation_match",
            False,
        ),
        (
            FreshnessObservation(True, False, True, True, False),
            "freshness_compliance",
            False,
        ),
        (FreshnessObservation(True, True, False, True, False), "grounded", False),
        (FreshnessObservation(True, True, True, False, False), "exact_date_ok", False),
        (
            FreshnessObservation(True, True, True, True, True),
            "stale_answer_leak",
            True,
        ),
    ],
)
def test_evaluate_freshness_case_fails_each_metric_independently(
    observation: FreshnessObservation,
    metric: str,
    expected_value: bool,
) -> None:
    case = FreshnessCase(
        "case",
        "prompt",
        requires_freshness=True,
        requires_exact_date=True,
        requires_source_grounding=True,
    )

    result = evaluate_freshness_case(case, observation)

    assert result.passed is False
    assert result.metrics[metric] is expected_value


def test_freshness_report_raises_on_observation_case_id_mismatch() -> None:
    case = FreshnessCase("expected", "prompt", requires_freshness=False)

    with pytest.raises(MissingObservationError):
        build_freshness_report(
            cases=(case,),
            observations={
                "other": FreshnessObservation(False, False, False, False, False)
            },
        )


def test_evaluate_freshness_case_accepts_empty_payload_values() -> None:
    case = FreshnessCase("", "", requires_freshness=False)
    result = evaluate_freshness_case(
        case,
        FreshnessObservation(False, False, False, False, False),
    )

    assert result.passed is True
