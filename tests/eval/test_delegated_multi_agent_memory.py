from __future__ import annotations

import json

import pytest

import openminion_eval
from openminion_eval.cli import main
from openminion_eval.memory_effectiveness import (
    DELEGATED_MEMORY_FIXTURE_VERSION,
    DelegatedMemoryEvalTrace,
    build_delegated_memory_scorecard_diff,
    build_delegated_memory_scorecard,
    compare_delegated_memory_scorecards,
    load_delegated_memory_cases,
    load_delegated_memory_scorecard_diff,
    load_delegated_memory_scorecard,
    score_delegated_memory_case,
    write_delegated_memory_scorecard_diff,
    write_delegated_memory_scorecard,
)
from openminion_eval.reports import (
    render_delegated_memory_diff_html,
    render_delegated_memory_diff_markdown,
    render_delegated_memory_scorecard_html,
    render_delegated_memory_scorecard_markdown,
)


def test_packaged_suite_has_all_named_scenarios() -> None:
    cases = load_delegated_memory_cases()
    assert len(cases) == 8
    assert {case.mode for case in cases} == {
        "disabled",
        "private_only",
        "delegated_shared",
    }
    assert openminion_eval.load_delegated_memory_cases is load_delegated_memory_cases


def test_security_failure_overrides_perfect_utility() -> None:
    case = load_delegated_memory_cases()[0]
    result = score_delegated_memory_case(
        case,
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            retrieved_memory_ids=("project-approved",),
            sibling_scratch_ids=("sibling-scratch",),
        ),
    )
    assert result.utility_recall == 1.0
    assert not result.passed
    assert result.critical_failures == ("sibling_scratch_leak:sibling-scratch",)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("direct_id_bypass_ids", "direct_id_bypass:record"),
        ("revoked_future_operation_ids", "revoked_future_operation:record"),
        ("forbidden_reshare_ids", "forbidden_reshare:record"),
        ("accepted_poisoning_ids", "poisoning_accepted:record"),
    ],
)
def test_each_security_class_is_critical(field: str, expected: str) -> None:
    case = load_delegated_memory_cases()[-1]
    trace = DelegatedMemoryEvalTrace(case_id=case.case_id, **{field: ("record",)})
    assert score_delegated_memory_case(case, trace).critical_failures == (expected,)


def test_prior_delivery_is_not_a_revocation_failure() -> None:
    case = load_delegated_memory_cases()[4]
    result = score_delegated_memory_case(
        case,
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            prior_delivery_ids=("post-revoke",),
        ),
    )
    assert result.passed


def test_scorecard_compares_all_modes_and_keeps_efficiency() -> None:
    cases = load_delegated_memory_cases()
    traces = tuple(
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            retrieved_memory_ids=case.required_recall_ids,
            latency_ms=2.5,
            token_count=10,
        )
        for case in cases
    )
    scorecard = build_delegated_memory_scorecard(cases, traces)
    assert scorecard.passed
    assert scorecard.utility_recall == 1.0
    assert {result.mode for result in scorecard.results} == {
        "disabled",
        "private_only",
        "delegated_shared",
    }
    assert sum(result.token_count for result in scorecard.results) == 80


def test_scorecard_artifact_round_trips(tmp_path) -> None:
    cases = load_delegated_memory_cases()
    scorecard = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )

    output = write_delegated_memory_scorecard(
        tmp_path / "delegated-memory-scorecard.json",
        scorecard,
    )

    assert load_delegated_memory_scorecard(output) == scorecard
    assert openminion_eval.load_delegated_memory_scorecard is (
        load_delegated_memory_scorecard
    )


def test_report_cli_renders_delegated_memory_scorecard(tmp_path, capsys) -> None:
    cases = load_delegated_memory_cases()
    scorecard = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )
    artifact = write_delegated_memory_scorecard(tmp_path / "scorecard.json", scorecard)
    report = tmp_path / "scorecard.md"

    exit_code = main(
        ["report", "delegated-memory", str(artifact), "--out", str(report)]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert "# OpenMinion Delegated-Memory Scorecard" in report.read_text(
        encoding="utf-8"
    )


def test_delegated_scorecard_diff_and_report_rendering(tmp_path) -> None:
    cases = load_delegated_memory_cases()
    passing = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )
    regressed = build_delegated_memory_scorecard(
        cases,
        tuple(DelegatedMemoryEvalTrace(case_id=case.case_id) for case in cases),
    )

    comparisons = compare_delegated_memory_scorecards(passing, regressed)
    diff = build_delegated_memory_scorecard_diff(passing, regressed)
    markdown = render_delegated_memory_scorecard_markdown(regressed)
    html = render_delegated_memory_scorecard_html(regressed)
    diff_markdown = render_delegated_memory_diff_markdown(diff)
    diff_html = render_delegated_memory_diff_html(diff)

    assert diff.entries == comparisons
    assert {item.category for item in diff.entries} == {
        "regressed",
        "unchanged_pass",
    }
    assert diff.categories == {"regressed": 3, "unchanged_pass": 5}
    assert "required_recall_missing" in diff.entries[0].critical_failures[0]
    assert "# OpenMinion Delegated-Memory Scorecard" in markdown
    assert "| bounded-project-recall | delegated_shared | fail |" in markdown
    assert "<table>" in html
    assert "# OpenMinion Delegated-Memory Diff" in diff_markdown
    assert "| bounded-project-recall | regressed |" in diff_markdown
    assert "<table>" in diff_html
    assert openminion_eval.compare_delegated_memory_scorecards is (
        compare_delegated_memory_scorecards
    )
    assert openminion_eval.build_delegated_memory_scorecard_diff is (
        build_delegated_memory_scorecard_diff
    )


def test_delegated_memory_cli_writes_scorecard_artifact(tmp_path, capsys) -> None:
    cases_path = tmp_path / "delegated-cases.json"
    trace_path = tmp_path / "delegated-trace.json"
    scorecard_path = tmp_path / "delegated-scorecard.json"
    cases_path.write_text(
        json.dumps(
            {
                "version": DELEGATED_MEMORY_FIXTURE_VERSION,
                "cases": [
                    {
                        "case_id": "delegated-cli-smoke",
                        "scenario": "child agent uses reviewed parent memory",
                        "mode": "delegated_shared",
                        "required_recall_ids": ["approved-parent-memory"],
                        "forbidden_recall_ids": ["sibling-private-memory"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trace_path.write_text(
        json.dumps(
            {
                "traces": [
                    {
                        "case_id": "delegated-cli-smoke",
                        "retrieved_memory_ids": ["approved-parent-memory"],
                        "latency_ms": 1.5,
                        "token_count": 12,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "memory-effectiveness",
            "delegated-score",
            str(trace_path),
            "--cases",
            str(cases_path),
            "--out",
            str(scorecard_path),
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["artifact"] == str(scorecard_path)
    assert stdout["utility_recall"] == 1.0
    assert load_delegated_memory_scorecard(scorecard_path).passed


def test_delegated_memory_cli_compares_scorecards(tmp_path, capsys) -> None:
    cases = load_delegated_memory_cases()
    previous = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )
    current = build_delegated_memory_scorecard(
        cases,
        tuple(DelegatedMemoryEvalTrace(case_id=case.case_id) for case in cases),
    )
    previous_path = write_delegated_memory_scorecard(
        tmp_path / "previous.json", previous
    )
    current_path = write_delegated_memory_scorecard(tmp_path / "current.json", current)
    diff_path = tmp_path / "diff.json"

    exit_code = main(
        [
            "memory-effectiveness",
            "delegated-diff",
            str(previous_path),
            str(current_path),
            "--out",
            str(diff_path),
        ]
    )

    assert capsys.readouterr().out == ""
    assert exit_code == 1
    assert load_delegated_memory_scorecard_diff(diff_path).categories == {
        "regressed": 3,
        "unchanged_pass": 5,
    }
    assert openminion_eval.load_delegated_memory_scorecard_diff is (
        load_delegated_memory_scorecard_diff
    )
    assert openminion_eval.write_delegated_memory_scorecard_diff is (
        write_delegated_memory_scorecard_diff
    )


def test_report_cli_renders_delegated_memory_diff(tmp_path, capsys) -> None:
    cases = load_delegated_memory_cases()
    previous = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )
    current = build_delegated_memory_scorecard(
        cases,
        tuple(DelegatedMemoryEvalTrace(case_id=case.case_id) for case in cases),
    )
    diff = build_delegated_memory_scorecard_diff(previous, current)
    artifact = write_delegated_memory_scorecard_diff(tmp_path / "diff.json", diff)
    report = tmp_path / "diff.md"

    exit_code = main(["report", "delegated-diff", str(artifact), "--out", str(report)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert "# OpenMinion Delegated-Memory Diff" in report.read_text(encoding="utf-8")


def test_artifact_validate_accepts_delegated_memory_diff(tmp_path, capsys) -> None:
    cases = load_delegated_memory_cases()
    scorecard = build_delegated_memory_scorecard(
        cases,
        tuple(
            DelegatedMemoryEvalTrace(
                case_id=case.case_id,
                retrieved_memory_ids=case.required_recall_ids,
            )
            for case in cases
        ),
    )
    diff = build_delegated_memory_scorecard_diff(scorecard, scorecard)
    artifact = write_delegated_memory_scorecard_diff(tmp_path / "diff.json", diff)

    exit_code = main(["artifact", "validate", str(artifact)])

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["artifact_kind"] == "delegated-memory-diff"


def test_fixture_version_and_trace_inputs_fail_closed(tmp_path) -> None:
    fixture = tmp_path / "cases.json"
    fixture.write_text('{"version":"unknown","cases":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_delegated_memory_cases(str(fixture))
    with pytest.raises(ValueError, match="negative"):
        DelegatedMemoryEvalTrace(case_id="case", token_count=-1)
    scorecard = tmp_path / "scorecard.json"
    scorecard.write_text('{"version":"unknown"}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_delegated_memory_scorecard(scorecard)
