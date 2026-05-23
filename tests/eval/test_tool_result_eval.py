from __future__ import annotations

from pathlib import Path

from openminion_eval.tools import (
    ToolResultUsageObservation,
    build_tool_result_usage_report,
    load_tool_result_usage_cases,
    write_tool_result_usage_report,
)


FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "tools"
    / "tool_result_usage_cases.json"
)


def test_tool_result_usage_fixture_loads() -> None:
    cases = load_tool_result_usage_cases(FIXTURE)
    assert [case.case_id for case in cases] == [
        "weather-grounded-answer",
        "search-grounded-summary",
    ]


def test_tool_result_usage_report_tracks_grounding_and_unsupported_claims(
    tmp_path: Path,
) -> None:
    cases = load_tool_result_usage_cases(FIXTURE)
    report = build_tool_result_usage_report(
        cases=cases,
        observations={
            "weather-grounded-answer": ToolResultUsageObservation(
                cited_facts=("16C", "San Diego"),
                unsupported_claims=(),
            ),
            "search-grounded-summary": ToolResultUsageObservation(
                cited_facts=("source=serpapi",),
                unsupported_claims=(),
            ),
        },
    )
    assert report.family_id == "tools.result_usage"
    assert report.summary.case_count == 2
    assert report.summary.passed_count == 2
    assert report.summary.metrics["grounded_count"] == 2
    out = write_tool_result_usage_report(tmp_path / "result-usage.json", report)
    assert out.exists()
