from __future__ import annotations

from pathlib import Path

from openminion_eval.policy import (
    PolicyObservation,
    build_policy_report,
    load_policy_cases,
)


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "policy" / "cases.json"


def test_policy_fixture_loads() -> None:
    cases = load_policy_cases(FIXTURE)
    assert [case.case_id for case in cases] == [
        "dangerous-write",
        "blocked-secret-exfiltration",
    ]


def test_policy_report_scores_typed_confirmation_and_block_facts() -> None:
    cases = load_policy_cases(FIXTURE)
    report = build_policy_report(
        cases=cases,
        observations={
            "dangerous-write": PolicyObservation(
                confirmation_required=True,
                blocked=False,
            ),
            "blocked-secret-exfiltration": PolicyObservation(
                confirmation_required=False,
                blocked=True,
                blocked_reason="policy_denied",
            ),
        },
    )
    assert report.summary.passed_count == 2
    assert report.summary.metrics["block_match_count"] == 2
