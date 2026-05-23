from __future__ import annotations

from pathlib import Path

from openminion_eval.closure import (
    ClosureObservation,
    build_closure_report,
    load_closure_cases,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "closure" / "cases.json"


def test_closure_fixture_loads() -> None:
    cases = load_closure_cases(FIXTURE)
    assert [case.expected_action for case in cases] == ["answer", "clarify"]


def test_closure_report_scores_typed_outcomes_not_prose() -> None:
    cases = load_closure_cases(FIXTURE)
    report = build_closure_report(
        cases=cases,
        observations={
            "answer-now": ClosureObservation(
                closure_action="answer",
                answer_complete=True,
            ),
            "need-clarification": ClosureObservation(
                closure_action="clarify",
                answer_complete=True,
            ),
        },
    )
    assert report.summary.passed_count == 2
    assert report.summary.metrics["unnecessary_followup_count"] == 0
