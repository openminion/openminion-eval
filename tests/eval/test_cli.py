from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from openminion_eval.cli import main
from openminion_eval.schemas import (
    EvalResult,
    EvalRunManifest,
    EvalSuiteResult,
    EvalSummary,
)
from openminion_eval.suite_artifacts import load_suite_result, write_suite_result


REPO_ROOT = Path(__file__).resolve().parents[2]


def _dataset(path: Path, *, expected: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "dataset_version": "1",
                "name": "cli-smoke",
                "cases": [
                    {
                        "id": "hello",
                        "name": "hello",
                        "turns": [{"user": "hello", "expected": expected}],
                        "tags": ["smoke"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return path


def _jsonl_dataset(path: Path, *, expected: str) -> Path:
    path.write_text(
        json.dumps(
            {
                "id": "hello",
                "name": "hello",
                "turns": [{"user": "hello", "expected": expected}],
                "tags": ["smoke"],
            }
        ),
        encoding="utf-8",
    )
    return path


def _summary(name: str, passed: bool, score: float) -> EvalSummary:
    return EvalSummary(
        transcript_name=name,
        total_turns=1,
        average_score=score,
        min_score=score,
        max_score=score,
        results=[
            EvalResult(
                turn_index=0,
                user_input="user",
                expected="expected",
                actual="actual",
                score=score,
                scorer_name="substring_match",
            )
        ],
        passed=passed,
        threshold=0.8,
    )


def _suite(name: str, summaries: list[EvalSummary]) -> EvalSuiteResult:
    passed = sum(1 for summary in summaries if summary.passed)
    return EvalSuiteResult(
        suite_name=name,
        total_transcripts=len(summaries),
        passed_transcripts=passed,
        failed_transcripts=len(summaries) - passed,
        summaries=summaries,
        all_passed=passed == len(summaries),
    )


def _manifest() -> EvalRunManifest:
    return EvalRunManifest(
        run_id="run",
        generated_at="2026-06-19T00:00:00+00:00",
        package_version="0.0.1",
        git_sha=None,
        input_hash="hash",
        scorer_name="substring_match",
        threshold=0.8,
    )


def test_module_and_cases_help_entrypoints() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "src")

    module_help = subprocess.run(
        [sys.executable, "-m", "openminion_eval", "--help"],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    cases_help = subprocess.run(
        [sys.executable, "-m", "openminion_eval.cases", "--help"],
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert module_help.returncode == 0
    assert "openminion-eval" in module_help.stdout
    assert "run" in module_help.stdout
    assert "diff" in module_help.stdout
    assert cases_help.returncode == 0
    assert "openminion_eval.cases" in cases_help.stdout


def test_run_command_writes_suite_artifact_and_returns_zero_on_pass(
    tmp_path, capsys
) -> None:
    dataset = _dataset(tmp_path / "dataset.json", expected="Mock response")
    output = tmp_path / "suite.json"

    exit_code = main(["run", str(dataset), "--out", str(output)])

    stdout = json.loads(capsys.readouterr().out)
    result, manifest = load_suite_result(output)
    assert exit_code == 0
    assert stdout["all_passed"] is True
    assert stdout["artifact"] == str(output)
    assert result.all_passed is True
    assert manifest.metadata["dataset_name"] == "cli-smoke"
    assert manifest.metadata["dataset_version"] == "1"
    assert manifest.metadata["dataset_hash"]


def test_run_command_returns_one_on_threshold_failure(tmp_path, capsys) -> None:
    dataset = _jsonl_dataset(tmp_path / "dataset.jsonl", expected="not present")

    exit_code = main(["run", str(dataset)])

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert stdout["all_passed"] is False
    assert stdout["failed_transcripts"] == 1


def test_run_command_can_use_replay_jsonl_subject(tmp_path, capsys) -> None:
    dataset = _jsonl_dataset(tmp_path / "dataset.jsonl", expected="expected")
    replay = tmp_path / "replay.jsonl"
    replay.write_text('{"user": "hello", "actual": "expected"}\n', encoding="utf-8")

    exit_code = main(["run", str(dataset), "--replay-jsonl", str(replay)])

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["all_passed"] is True


def test_run_command_can_use_command_subject(tmp_path, capsys) -> None:
    dataset = _jsonl_dataset(tmp_path / "dataset.jsonl", expected="hello")

    exit_code = main(
        [
            "run",
            str(dataset),
            "--command",
            f"{sys.executable} -c 'import sys; print(sys.stdin.read().strip())'",
        ]
    )

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert stdout["all_passed"] is True


def test_diff_command_reports_categories_and_failure_exit(tmp_path, capsys) -> None:
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"
    write_suite_result(
        previous_path,
        _suite(
            "suite",
            [
                _summary("missing", passed=True, score=1.0),
                _summary("regressed", passed=True, score=1.0),
                _summary("unchanged", passed=True, score=1.0),
            ],
        ),
        _manifest(),
    )
    write_suite_result(
        current_path,
        _suite(
            "suite",
            [
                _summary("regressed", passed=False, score=0.0),
                _summary("unchanged", passed=True, score=1.0),
            ],
        ),
        _manifest(),
    )

    exit_code = main(["diff", str(previous_path), str(current_path)])

    stdout = json.loads(capsys.readouterr().out)
    assert exit_code == 1
    assert stdout["categories"] == {
        "missing_transcript": 1,
        "regressed": 1,
        "unchanged_pass": 1,
    }


def test_diff_command_writes_output_and_returns_zero_for_non_regression(
    tmp_path, capsys
) -> None:
    previous_path = tmp_path / "previous.json"
    current_path = tmp_path / "current.json"
    output_path = tmp_path / "diff.json"
    write_suite_result(
        previous_path,
        _suite("suite", [_summary("fixed", passed=False, score=0.0)]),
        _manifest(),
    )
    write_suite_result(
        current_path,
        _suite("suite", [_summary("fixed", passed=True, score=1.0)]),
        _manifest(),
    )

    exit_code = main(
        ["diff", str(previous_path), str(current_path), "--out", str(output_path)]
    )

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["categories"] == {
        "fixed": 1
    }


def test_dataset_validate_hash_and_init_commands(tmp_path, capsys) -> None:
    dataset = _jsonl_dataset(tmp_path / "dataset.jsonl", expected="hello")
    init_output = tmp_path / "routing.json"

    assert main(["dataset", "validate", str(dataset)]) == 0
    validate_stdout = json.loads(capsys.readouterr().out)
    assert validate_stdout["valid"] is True
    assert validate_stdout["case_count"] == 1

    assert main(["dataset", "hash", str(dataset)]) == 0
    hash_stdout = json.loads(capsys.readouterr().out)
    assert hash_stdout["dataset_hash"] == validate_stdout["dataset_hash"]

    assert (
        main(["dataset", "init", "--family", "routing", "--out", str(init_output)]) == 0
    )
    init_stdout = json.loads(capsys.readouterr().out)
    assert init_stdout["artifact"] == str(init_output)
    assert json.loads(init_output.read_text(encoding="utf-8"))["name"] == (
        "routing-starter"
    )


def test_report_suite_command_writes_markdown(tmp_path, capsys) -> None:
    artifact = tmp_path / "suite.json"
    report = tmp_path / "suite.md"
    write_suite_result(
        artifact,
        _suite("suite", [_summary("hello", passed=True, score=1.0)]),
        _manifest(),
    )

    exit_code = main(["report", "suite", str(artifact), "--out", str(report)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
    assert "# OpenMinion Eval Suite Report" in report.read_text(encoding="utf-8")


def test_scorers_list_command_reports_builtin_scorers(capsys) -> None:
    exit_code = main(["scorers", "list"])

    stdout = json.loads(capsys.readouterr().out)
    names = {item["name"] for item in stdout["scorers"]}
    assert exit_code == 0
    assert {"exact_match", "substring_match"}.issubset(names)


def test_integration_list_command_reports_tiers(capsys) -> None:
    exit_code = main(["integration", "list", "--root", str(REPO_ROOT)])

    stdout = json.loads(capsys.readouterr().out)
    tiers = {item["tier"] for item in stdout["probes"]}
    assert exit_code == 0
    assert stdout["probe_count"] > 0
    assert {"local", "host-runtime", "live-provider"}.issubset(tiers)
