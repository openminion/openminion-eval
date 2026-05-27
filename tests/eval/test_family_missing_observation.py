from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.routing import RoutingCase, build_routing_report


def test_missing_observation_raises_typed_error() -> None:
    case = RoutingCase(
        case_id="missing-case", prompt="route this", expected_mode="respond"
    )

    with pytest.raises(MissingObservationError) as excinfo:
        build_routing_report(cases=(case,), observations={})

    assert excinfo.value.family_label == "routing"
    assert excinfo.value.case_id == "missing-case"


def test_missing_observation_can_be_marked_as_failed_result() -> None:
    case = RoutingCase(
        case_id="missing-case", prompt="route this", expected_mode="respond"
    )

    report = build_routing_report(
        cases=(case,),
        observations={},
        on_missing="mark_fail",
        now_provider=lambda: "fixed",
    )

    assert report.cases[0].passed is False
    assert report.cases[0].metrics == {"error": "observation_missing"}
    assert report.summary.failed_count == 1
