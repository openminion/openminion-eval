from __future__ import annotations

import pytest

from openminion_eval.closure import (
    ClosureCase,
    ClosureObservation,
    build_closure_report,
)
from openminion_eval.closure.family import evaluate_closure_case
from openminion_eval.family_support import MissingObservationError


def test_evaluate_closure_case_passes_complete_expected_action() -> None:
    case = ClosureCase("case", "prompt", "answer")
    observation = ClosureObservation("answer", answer_complete=True)

    result = evaluate_closure_case(case, observation)

    assert result.passed is True


def test_evaluate_closure_case_records_all_fail_flags() -> None:
    case = ClosureCase("case", "prompt", "answer")
    observation = ClosureObservation(
        "clarify",
        answer_complete=False,
        unnecessary_followup=True,
    )

    result = evaluate_closure_case(case, observation)

    assert result.passed is False
    assert result.metrics == {
        "action_match": False,
        "answer_complete": False,
        "unnecessary_followup": True,
    }


@pytest.mark.parametrize(
    ("observation", "metric", "expected_value"),
    [
        (ClosureObservation("clarify", True), "action_match", False),
        (ClosureObservation("answer", False), "answer_complete", False),
        (
            ClosureObservation("answer", True, unnecessary_followup=True),
            "unnecessary_followup",
            True,
        ),
    ],
)
def test_evaluate_closure_case_fails_each_metric_independently(
    observation: ClosureObservation,
    metric: str,
    expected_value: bool,
) -> None:
    case = ClosureCase("case", "prompt", "answer")

    result = evaluate_closure_case(case, observation)

    assert result.passed is False
    assert result.metrics[metric] is expected_value


def test_closure_report_raises_on_observation_case_id_mismatch() -> None:
    case = ClosureCase("expected", "prompt", "answer")

    with pytest.raises(MissingObservationError):
        build_closure_report(
            cases=(case,),
            observations={"other": ClosureObservation("answer", True)},
        )


def test_evaluate_closure_case_accepts_empty_payload_values() -> None:
    case = ClosureCase("", "", "")
    result = evaluate_closure_case(case, ClosureObservation("", True))

    assert result.passed is True
