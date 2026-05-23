from __future__ import annotations

from pathlib import Path

from openminion_eval.freshness import (
    FreshnessObservation,
    build_freshness_report,
    load_freshness_cases,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "freshness" / "cases.json"


def test_freshness_fixture_loads() -> None:
    cases = load_freshness_cases(FIXTURE)
    assert [case.case_id for case in cases] == ["latest-weather", "timeless-definition"]


def test_freshness_report_uses_fixture_labels_and_trace_facts() -> None:
    cases = load_freshness_cases(FIXTURE)
    report = build_freshness_report(
        cases=cases,
        observations={
            "latest-weather": FreshnessObservation(
                classified_freshness_sensitive=True,
                live_lookup_performed=True,
                evidence_attached=True,
                exact_date_in_answer=True,
                unsupported_current_claim=False,
            ),
            "timeless-definition": FreshnessObservation(
                classified_freshness_sensitive=False,
                live_lookup_performed=False,
                evidence_attached=False,
                exact_date_in_answer=False,
                unsupported_current_claim=False,
            ),
        },
    )
    assert report.summary.passed_count == 2
    assert report.summary.metrics["stale_answer_leak_count"] == 0
