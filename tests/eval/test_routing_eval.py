from __future__ import annotations

from pathlib import Path

from openminion_eval.routing import (
    RoutingObservation,
    build_routing_report,
    load_routing_cases,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "routing" / "cases.json"


def test_routing_fixture_loads() -> None:
    cases = load_routing_cases(FIXTURE)
    assert [case.expected_mode for case in cases] == ["respond", "decompose"]


def test_routing_report_scores_typed_mode_outcomes() -> None:
    cases = load_routing_cases(FIXTURE)
    report = build_routing_report(
        cases=cases,
        observations={
            "single-answer": RoutingObservation(observed_mode="respond"),
            "multi-step-research": RoutingObservation(observed_mode="decompose"),
        },
    )
    assert report.summary.passed_count == 2
    assert report.summary.metrics["routing_match_count"] == 2
