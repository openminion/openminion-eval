from __future__ import annotations

from pathlib import Path

from openminion_eval.tools import (
    ToolSelectionObservation,
    build_tool_selection_report,
    load_tool_selection_cases,
    write_tool_selection_report,
)


FIXTURE = (
    Path(__file__).resolve().parent / "fixtures" / "tools" / "tool_selection_cases.json"
)


def test_tool_selection_fixture_loads() -> None:
    cases = load_tool_selection_cases(FIXTURE)
    assert [case.case_id for case in cases] == [
        "search-latest-release",
        "weather-forecast",
        "no-tool-small-talk",
    ]


def test_tool_selection_report_scores_choice_and_no_tool_cases(tmp_path: Path) -> None:
    cases = load_tool_selection_cases(FIXTURE)
    report = build_tool_selection_report(
        cases=cases,
        observations={
            "search-latest-release": ToolSelectionObservation(
                selected_family="search",
                selected_families=("search",),
            ),
            "weather-forecast": ToolSelectionObservation(
                selected_family="weather",
                selected_families=("weather",),
            ),
            "no-tool-small-talk": ToolSelectionObservation(
                selected_family=None,
                selected_families=(),
            ),
        },
    )
    assert report.family_id == "tools.selection"
    assert report.summary.case_count == 3
    assert report.summary.passed_count == 3
    assert report.summary.metrics["correct_family_count"] == 2
    out = write_tool_selection_report(tmp_path / "selection.json", report)
    assert out.exists()
