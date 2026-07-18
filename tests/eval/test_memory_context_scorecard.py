from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pytest

from openminion_eval.memory_context_scorecard import (
    AblationOutcome,
    MemoryContextScorecardV1,
    MemoryContextMetricStatus,
    ScorecardMetricFixture,
    TaskOracle,
    build_memory_context_scorecard,
    load_memory_context_scorecard,
    load_memory_context_scorecard_fixtures,
    write_memory_context_scorecard,
)
from openminion_eval.cli import main


FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "memory_context_scorecard" / "cases.json"
)


def _paired_metric(
    *,
    status: MemoryContextMetricStatus = "pass",
    provider_backed: bool = False,
    disabled_outcome: AblationOutcome | None = None,
    enabled_outcome: AblationOutcome | None = None,
    variance_evidence_ref: str = "",
) -> ScorecardMetricFixture:
    return ScorecardMetricFixture(
        metric_name="memory_influence",
        value=1.0,
        threshold=0.5,
        status=status,
        blocking=True,
        evidence_refs=("trace://memory/1",),
        disabled_outcome=disabled_outcome
        or AblationOutcome(
            output_ref="output://disabled",
            oracle_passed=False,
            score=0.0,
        ),
        enabled_outcome=enabled_outcome
        or AblationOutcome(
            output_ref="output://enabled",
            oracle_passed=True,
            score=1.0,
        ),
        oracle=TaskOracle(
            oracle_id="oracle-memory",
            kind="exact_text",
            expected_value="uses memory",
        ),
        provider_backed=provider_backed,
        variance_evidence_ref=variance_evidence_ref,
    )


def test_scorecard_schema_rejects_missing_metrics() -> None:
    with pytest.raises(ValueError, match="metrics is required"):
        MemoryContextScorecardV1(
            report_version="memory-context-scorecard.v1",
            generated_at="2026-07-17T00:00:00Z",
            run_id="run",
            fixture_ids=("case",),
            metrics=(),
            summary={},
        )


def test_scorecard_schema_rejects_unknown_status() -> None:
    with pytest.raises(ValueError, match="invalid metric status"):
        _paired_metric(status=cast(MemoryContextMetricStatus, "blocked"))


def test_blocking_influence_requires_pair_and_oracle() -> None:
    with pytest.raises(ValueError, match="requires paired outcomes and oracle"):
        ScorecardMetricFixture(
            metric_name="memory_influence",
            value=1.0,
            threshold=0.5,
            status="pass",
            blocking=True,
            evidence_refs=("trace://memory/1",),
        )


def test_passing_pair_requires_behavior_delta() -> None:
    with pytest.raises(ValueError, match="requires a non-zero paired delta"):
        _paired_metric(
            disabled_outcome=AblationOutcome(
                output_ref="output://disabled",
                oracle_passed=True,
                score=1.0,
            ),
            enabled_outcome=AblationOutcome(
                output_ref="output://enabled",
                oracle_passed=True,
                score=1.0,
            ),
        )


def test_provider_backed_blocking_requires_variance_evidence() -> None:
    with pytest.raises(ValueError, match="variance_evidence_ref"):
        _paired_metric(provider_backed=True)


def test_fixture_loader_accepts_controlled_pair() -> None:
    fixtures = load_memory_context_scorecard_fixtures(FIXTURE_PATH)

    assert fixtures[0].case_id == "fixture-pair-valid"
    metric = fixtures[0].metrics[0]
    assert metric.disabled_outcome is not None
    assert metric.enabled_outcome is not None
    assert metric.oracle is not None
    assert fixtures[0].task_input_ref == "fixture://task"


def test_scorecard_report_contains_delta_and_trace_refs() -> None:
    fixtures = load_memory_context_scorecard_fixtures(FIXTURE_PATH)

    report = build_memory_context_scorecard(
        fixtures,
        run_id="test-run",
        generated_at="1970-01-01T00:00:00Z",
    )

    assert report.report_version == "memory-context-scorecard.v1"
    assert report.summary["all_blocking_passed"] is True
    assert report.metrics[0].delta == 1.0
    assert report.metrics[0].provenance_trace_ids == ("prov-1",)


def test_scorecard_round_trips_as_deterministic_json(tmp_path: Path) -> None:
    fixtures = load_memory_context_scorecard_fixtures(FIXTURE_PATH)
    report = build_memory_context_scorecard(
        fixtures,
        run_id="test-run",
        generated_at="1970-01-01T00:00:00Z",
    )
    output = tmp_path / "scorecard.json"

    write_memory_context_scorecard(output, report)
    loaded = load_memory_context_scorecard(output)

    assert loaded == report
    assert json.loads(output.read_text(encoding="utf-8"))["run_id"] == "test-run"


def test_packaged_known_bad_fixtures_load_and_flag_blocking_failures() -> None:
    report = build_memory_context_scorecard(
        load_memory_context_scorecard_fixtures(),
        run_id="packaged",
        generated_at="1970-01-01T00:00:00Z",
    )

    assert report.summary["fixture_count"] == 6
    assert report.summary["blocking_fail_count"] == 11
    assert report.summary["all_blocking_passed"] is False
    by_metric = {metric.metric_name: metric for metric in report.metrics}
    assert by_metric["block_usefulness"].delta == 0.0
    assert by_metric["memory_influence"].delta == 0.0
    assert by_metric["non_replay_safety"].status == "fail"
    assert by_metric["permission_safety"].status == "fail"


def test_scorecard_cli_writes_deterministic_report(tmp_path: Path, capsys) -> None:
    output = tmp_path / "scorecard.json"

    exit_code = main(
        [
            "memory-context-scorecard",
            "--fixtures",
            str(FIXTURE_PATH),
            "--run-id",
            "cli-test",
            "--out",
            str(output),
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["artifact"] == str(output)
    assert stdout["all_blocking_passed"] is True
    assert load_memory_context_scorecard(output).run_id == "cli-test"


def test_scorecard_cli_returns_one_for_packaged_known_bad(
    tmp_path: Path, capsys
) -> None:
    output = tmp_path / "known-bad.json"

    exit_code = main(
        ["memory-context-scorecard", "--run-id", "known-bad", "--out", str(output)]
    )

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert stdout["blocking_fail_count"] == 11
    assert output.exists()
