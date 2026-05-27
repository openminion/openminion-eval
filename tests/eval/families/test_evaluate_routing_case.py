from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.routing import (
    RoutingCase,
    RoutingObservation,
    build_routing_report,
)
from openminion_eval.routing.family import evaluate_routing_case


def test_evaluate_routing_case_passes_matching_mode() -> None:
    case = RoutingCase("case", "prompt", "respond")
    result = evaluate_routing_case(case, RoutingObservation("respond"))

    assert result.passed is True
    assert result.metrics["routing_match"] is True


def test_evaluate_routing_case_records_all_fail_flags() -> None:
    case = RoutingCase("case", "prompt", "respond")
    result = evaluate_routing_case(
        case,
        RoutingObservation(
            "decompose",
            over_clarified=True,
            over_delegated=True,
            missed_decompose=True,
        ),
    )

    assert result.passed is False
    assert result.metrics == {
        "routing_match": False,
        "over_clarified": True,
        "over_delegated": True,
        "missed_decompose": True,
    }


@pytest.mark.parametrize(
    "flag",
    ["over_clarified", "over_delegated", "missed_decompose"],
)
def test_evaluate_routing_case_fails_each_metric_independently(flag: str) -> None:
    case = RoutingCase("case", "prompt", "respond")
    observation = RoutingObservation("respond", **{flag: True})

    result = evaluate_routing_case(case, observation)

    assert result.passed is False
    assert result.metrics[flag] is True


def test_routing_report_raises_on_observation_case_id_mismatch() -> None:
    case = RoutingCase("expected", "prompt", "respond")

    with pytest.raises(MissingObservationError):
        build_routing_report(
            cases=(case,),
            observations={"other": RoutingObservation("respond")},
        )


def test_evaluate_routing_case_accepts_empty_payload_values() -> None:
    case = RoutingCase("", "", "")
    result = evaluate_routing_case(case, RoutingObservation(""))

    assert result.passed is True
