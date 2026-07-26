from __future__ import annotations

import json
from pathlib import Path

import pytest

from openminion_eval.cli import main
from openminion_eval.memory_context_scorecard import (
    ContextBudgetCalibrationV1,
    MemoryContextOperationalCanaryV1,
    build_context_budget_calibration,
    build_memory_context_scorecard,
    build_operational_canary,
    load_context_budget_calibration,
    load_memory_context_scorecard_fixtures,
    load_operational_canary,
)

FIXTURE_PATH = (
    Path(__file__).parent / "fixtures" / "memory_context_scorecard" / "cases.json"
)


def _canary() -> MemoryContextOperationalCanaryV1:
    scorecard = build_memory_context_scorecard(
        load_memory_context_scorecard_fixtures(FIXTURE_PATH),
        run_id="source-scorecard",
        generated_at="1970-01-01T00:00:00Z",
    )
    return build_operational_canary(
        scorecard,
        run_id="canary",
        generated_at="1970-01-01T00:00:00Z",
    )


def test_operational_canary_round_trips(tmp_path: Path, capsys) -> None:
    output = tmp_path / "canary.json"

    exit_code = main(
        [
            "memory-context-operational-canary",
            "--fixtures",
            str(FIXTURE_PATH),
            "--run-id",
            "canary-cli",
            "--out",
            str(output),
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    loaded = load_operational_canary(output)
    assert exit_code == 0
    assert stdout["report_version"] == "memory-context-operational-canary.v1"
    assert loaded.run_id == "canary-cli"
    assert loaded.summary["all_passed"] is True
    assert loaded.cases[0].redaction_status == "redacted"
    assert loaded.cases[0].disabled_score is not None
    assert loaded.cases[0].enabled_score is not None


def test_operational_canary_rejects_unpaired_pass() -> None:
    canary = _canary()
    case = canary.cases[0]

    with pytest.raises(ValueError, match="paired disabled/enabled"):
        type(case)(
            **{
                **case.__dict__,
                "disabled_score": None,
                "enabled_score": None,
            }
        )


def test_context_budget_calibration_round_trips(tmp_path: Path, capsys) -> None:
    canary_path = tmp_path / "canary.json"
    canary_path.write_text(
        json.dumps(_canary(), default=lambda value: value.__dict__) + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "calibration.json"

    exit_code = main(
        [
            "context-budget-calibration",
            "--canary",
            str(canary_path),
            "--run-id",
            "calibration-cli",
            "--evidence-window",
            "fixture-window",
            "--out",
            str(output),
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    loaded = load_context_budget_calibration(output)
    assert exit_code == 0
    assert stdout["report_version"] == "context-budget-calibration.v1"
    assert stdout["writes_runtime_config"] is False
    assert loaded.run_id == "calibration-cli"
    assert loaded.evidence_window == "fixture-window"
    assert loaded.summary["writes_runtime_config"] is False


def test_context_budget_calibration_rejects_empty_recommendations() -> None:
    with pytest.raises(ValueError, match="recommendations is required"):
        ContextBudgetCalibrationV1(
            report_version="context-budget-calibration.v1",
            generated_at="1970-01-01T00:00:00Z",
            run_id="empty",
            evidence_window="local",
            recommendations=(),
            summary={},
        )


def test_context_budget_calibration_uses_stable_fallback() -> None:
    report = build_context_budget_calibration(
        _canary(),
        run_id="fallback",
        generated_at="1970-01-01T00:00:00Z",
    )

    assert report.report_version == "context-budget-calibration.v1"
    assert report.recommendations
    assert report.summary["writes_runtime_config"] is False
