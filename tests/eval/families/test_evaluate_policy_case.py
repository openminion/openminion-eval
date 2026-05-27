from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.policy import (
    PolicyCase,
    PolicyObservation,
    build_policy_report,
)
from openminion_eval.policy.family import evaluate_policy_case


def test_evaluate_policy_case_passes_confirmation_and_block_match() -> None:
    case = PolicyCase("case", "prompt", expects_confirmation=True, expects_block=True)
    observation = PolicyObservation(
        confirmation_required=True,
        blocked=True,
        blocked_reason="policy_denied",
    )

    result = evaluate_policy_case(case, observation)

    assert result.passed is True


def test_evaluate_policy_case_records_all_fail_flags() -> None:
    case = PolicyCase("case", "prompt", expects_confirmation=True, expects_block=True)
    observation = PolicyObservation(confirmation_required=False, blocked=False)

    result = evaluate_policy_case(case, observation)

    assert result.passed is False
    assert result.metrics["confirmation_match"] is False
    assert result.metrics["block_match"] is False


@pytest.mark.parametrize(
    ("case", "observation", "metric"),
    [
        (
            PolicyCase("case", "prompt", expects_confirmation=True),
            PolicyObservation(confirmation_required=False, blocked=False),
            "confirmation_match",
        ),
        (
            PolicyCase(
                "case", "prompt", expects_confirmation=False, expects_block=True
            ),
            PolicyObservation(confirmation_required=False, blocked=False),
            "block_match",
        ),
        (
            PolicyCase(
                "case", "prompt", expects_confirmation=False, expects_block=True
            ),
            PolicyObservation(confirmation_required=False, blocked=True),
            "explanation_present",
        ),
    ],
)
def test_evaluate_policy_case_fails_each_metric_independently(
    case: PolicyCase,
    observation: PolicyObservation,
    metric: str,
) -> None:
    result = evaluate_policy_case(case, observation)

    assert result.passed is False
    assert result.metrics[metric] is False


def test_policy_report_raises_on_observation_case_id_mismatch() -> None:
    case = PolicyCase("expected", "prompt", expects_confirmation=False)

    with pytest.raises(MissingObservationError):
        build_policy_report(
            cases=(case,),
            observations={"other": PolicyObservation(False, False)},
        )


def test_evaluate_policy_case_accepts_empty_payload_values() -> None:
    case = PolicyCase("", "", expects_confirmation=False)
    result = evaluate_policy_case(case, PolicyObservation(False, False))

    assert result.passed is True
