"""Focused tests for the starter EvalCase registry and CLI."""

from __future__ import annotations

import pytest

from openminion_eval.cases.registry import (
    EvalCase,
    EvalCaseResult,
    GradeMode,
    GradeOutcome,
    grade_case,
    registered_cases,
)
from openminion_eval.cases.cli import _exit_code_from, _render_markdown


def test_starter_cases_cover_five_distinct_categories() -> None:
    cases = registered_cases()
    assert len(cases) == 5, f"expected 5 starter cases, got {len(cases)}"
    categories = {c.category for c in cases}
    assert categories == {
        "coding",
        "research",
        "recovery",
        "multi_tool",
        "memory",
    }, f"unexpected categories: {categories}"


def test_every_case_has_stable_id_and_description() -> None:
    seen_ids: set[str] = set()
    for case in registered_cases():
        assert case.case_id, "case_id required"
        assert case.case_id not in seen_ids, f"duplicate id {case.case_id}"
        seen_ids.add(case.case_id)
        assert case.description.strip(), f"case {case.case_id} missing description"
        assert case.prompt.strip(), f"case {case.case_id} missing prompt"


def test_grade_case_returns_recognized_outcome_for_every_starter() -> None:
    valid = {
        GradeOutcome.PASS,
        GradeOutcome.FAIL,
        GradeOutcome.SKIPPED,
        GradeOutcome.UNGRADED,
    }
    for case in registered_cases():
        result = grade_case(case)
        assert isinstance(result, EvalCaseResult)
        assert result.outcome in valid, (
            f"case {case.case_id} produced unexpected outcome {result.outcome}"
        )
        assert result.case_id == case.case_id
        assert result.category == case.category


def test_markdown_report_has_one_row_per_case() -> None:
    results = [grade_case(c) for c in registered_cases()]
    report = _render_markdown(results)
    assert "# OpenMinion Eval Report" in report
    assert "## Cases" in report
    # The table header + one row per case.
    table_rows = [
        line
        for line in report.splitlines()
        if line.startswith("| `") and "|" in line[2:]
    ]
    assert len(table_rows) == len(results), (
        f"expected {len(results)} table rows, got {len(table_rows)}"
    )


def test_exit_code_treats_fail_as_only_failure_signal() -> None:
    def _fake_result(outcome: GradeOutcome) -> EvalCaseResult:
        return EvalCaseResult(
            case_id="t",
            category="t",
            grade_mode=GradeMode.STRUCTURAL,
            outcome=outcome,
        )

    assert _exit_code_from([_fake_result(GradeOutcome.PASS)]) == 0
    assert _exit_code_from([_fake_result(GradeOutcome.SKIPPED)]) == 0
    assert _exit_code_from([_fake_result(GradeOutcome.UNGRADED)]) == 0
    assert _exit_code_from([_fake_result(GradeOutcome.FAIL)]) == 1
    # Mixed: presence of FAIL produces exit-code 1.
    assert (
        _exit_code_from(
            [_fake_result(GradeOutcome.PASS), _fake_result(GradeOutcome.FAIL)]
        )
        == 1
    )


def test_live_cases_skipped_without_env_flag(monkeypatch) -> None:
    monkeypatch.delenv("OPENMINION_EVAL_LIVE", raising=False)
    live_case = EvalCase(
        case_id="live_demo",
        category="coding",
        description="demo",
        prompt="p",
        grade_mode=GradeMode.LIVE,
        grade_fn=lambda _c: GradeOutcome.PASS,
    )
    result = grade_case(live_case)
    assert result.outcome is GradeOutcome.SKIPPED
    assert "OPENMINION_EVAL_LIVE=1" in result.detail


def test_live_case_normalizes_tuple_grade_result(monkeypatch) -> None:
    monkeypatch.setenv("OPENMINION_EVAL_LIVE", "1")
    live_case = EvalCase(
        case_id="live_tuple_demo",
        category="coding",
        description="demo",
        prompt="p",
        grade_mode=GradeMode.LIVE,
        grade_fn=lambda _c: (GradeOutcome.PASS, "live detail"),
    )

    result = grade_case(live_case)

    assert result.outcome is GradeOutcome.PASS
    assert result.detail == "live detail"


def test_live_case_without_grade_fn_is_ungraded(monkeypatch) -> None:
    monkeypatch.setenv("OPENMINION_EVAL_LIVE", "1")
    live_case = EvalCase(
        case_id="live_ungraded_demo",
        category="coding",
        description="demo",
        prompt="p",
        grade_mode=GradeMode.LIVE,
    )

    result = grade_case(live_case)

    assert result.outcome is GradeOutcome.UNGRADED
    assert result.detail == "live case has no grade_fn configured"


def test_manual_case_records_ungraded_with_detail() -> None:
    manual_case = EvalCase(
        case_id="manual_demo",
        category="coding",
        description="demo",
        prompt="p",
        grade_mode=GradeMode.MANUAL,
    )
    result = grade_case(manual_case)
    assert result.outcome is GradeOutcome.UNGRADED
    assert "manual" in result.detail.lower()


def test_anchor_path_missing_skips_with_detail(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("OPENMINION_REPO_ROOT", str(tmp_path))
    case = EvalCase(
        case_id="missing_anchor_demo",
        category="coding",
        description="demo",
        prompt="p",
        grade_mode=GradeMode.STRUCTURAL,
        anchor_paths=("nonexistent/path.txt",),
        grade_fn=lambda _c: GradeOutcome.PASS,
    )
    result = grade_case(case)
    assert result.outcome is GradeOutcome.SKIPPED
    assert "missing anchors" in result.detail


def test_smoke_cli_main_returns_zero_on_starter_set(capsys) -> None:
    """The CLI's `main()` must run the starter set end-to-end and exit 0
    (no case currently in FAIL state for the structural starters)."""
    from openminion_eval.cases.cli import main

    exit_code = main([])
    captured = capsys.readouterr()
    assert "# OpenMinion Eval Report" in captured.out
    # Every starter case is structural; UNGRADED/PASS only, never FAIL.
    assert exit_code == 0, captured.out


@pytest.mark.parametrize(
    "category",
    ["coding", "research", "recovery", "multi_tool", "memory"],
)
def test_starter_includes_one_case_per_category(category: str) -> None:
    matching = [c for c in registered_cases() if c.category == category]
    assert len(matching) == 1, (
        f"expected exactly 1 starter case for {category}, got {len(matching)}"
    )
