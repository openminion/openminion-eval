from __future__ import annotations

import json
from time import sleep

from openminion_eval.constants import DETERMINISTIC_REPORTS_ENV
from openminion_eval.routing import (
    RoutingCase,
    RoutingObservation,
    build_routing_report,
)


def _report_json() -> str:
    case = RoutingCase(case_id="case", prompt="prompt", expected_mode="respond")
    report = build_routing_report(
        cases=(case,),
        observations={"case": RoutingObservation(observed_mode="respond")},
    )
    return json.dumps(report.to_dict(), sort_keys=True)


def test_family_reports_are_byte_stable_in_deterministic_mode(monkeypatch) -> None:
    monkeypatch.setenv(DETERMINISTIC_REPORTS_ENV, "1")

    first = _report_json()
    second = _report_json()

    assert first == second
    assert "1970-01-01T00:00:00Z" in first


def test_family_reports_keep_wall_clock_default(monkeypatch) -> None:
    monkeypatch.delenv(DETERMINISTIC_REPORTS_ENV, raising=False)

    first = _report_json()
    sleep(0.001)
    second = _report_json()

    assert first != second
