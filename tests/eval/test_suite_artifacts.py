from __future__ import annotations

import json

from openminion_eval import (
    EvalBaselineDiff,
    EvalRunManifest,
    build_run_manifest,
    compare_suite_results,
    hash_transcripts,
    load_suite_result,
    write_suite_result,
)
from openminion_eval.schemas import (
    EvalResult,
    EvalSuiteResult,
    EvalSummary,
    EvalTranscript,
)


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
                scorer_name="exact_match",
            )
        ],
        passed=passed,
        threshold=0.8,
    )


def _suite(summaries: list[EvalSummary]) -> EvalSuiteResult:
    passed = sum(1 for summary in summaries if summary.passed)
    return EvalSuiteResult(
        suite_name="suite",
        total_transcripts=len(summaries),
        passed_transcripts=passed,
        failed_transcripts=len(summaries) - passed,
        summaries=summaries,
        all_passed=passed == len(summaries),
    )


def test_hash_transcripts_is_stable_and_input_sensitive() -> None:
    transcripts = [
        EvalTranscript(
            name="basic",
            turns=[{"user": "hello", "expected": "hi"}],
            tags=["smoke"],
        )
    ]

    assert hash_transcripts(transcripts) == hash_transcripts(transcripts)
    assert hash_transcripts(transcripts) != hash_transcripts(
        [
            EvalTranscript(
                name="basic",
                turns=[{"user": "hello", "expected": "bye"}],
                tags=["smoke"],
            )
        ]
    )


def test_build_run_manifest_accepts_deterministic_fields() -> None:
    manifest = build_run_manifest(
        [EvalTranscript(name="basic", turns=[])],
        scorer_name="exact_match",
        threshold=0.75,
        run_id="run-1",
        generated_at="2026-06-19T00:00:00+00:00",
        package_version="0.0.1",
        git_sha="abc123",
        deterministic=True,
        seed=42,
        metadata={"owner": "eval"},
    )

    assert manifest == EvalRunManifest(
        run_id="run-1",
        generated_at="2026-06-19T00:00:00+00:00",
        package_version="0.0.1",
        git_sha="abc123",
        input_hash=hash_transcripts([EvalTranscript(name="basic", turns=[])]),
        scorer_name="exact_match",
        threshold=0.75,
        deterministic=True,
        seed=42,
        metadata={"owner": "eval"},
    )


def test_suite_result_artifact_round_trips_with_sorted_json(tmp_path) -> None:
    result = _suite([_summary("basic", passed=True, score=1.0)])
    manifest = build_run_manifest(
        [EvalTranscript(name="basic", turns=[])],
        scorer_name="exact_match",
        threshold=0.8,
        run_id="run-1",
        generated_at="2026-06-19T00:00:00+00:00",
        package_version="0.0.1",
    )

    path = write_suite_result(tmp_path / "suite.json", result, manifest)

    payload = json.loads(path.read_text())
    assert list(payload) == ["artifact_version", "manifest", "result"]
    assert load_suite_result(path) == (result, manifest)


def test_compare_suite_results_reports_every_category() -> None:
    previous = _suite(
        [
            _summary("fixed", passed=False, score=0.2),
            _summary("missing", passed=True, score=1.0),
            _summary("regressed", passed=True, score=1.0),
            _summary("unchanged_fail", passed=False, score=0.2),
            _summary("unchanged_pass", passed=True, score=1.0),
        ]
    )
    current = _suite(
        [
            _summary("fixed", passed=True, score=1.0),
            _summary("new_fail", passed=False, score=0.2),
            _summary("new_pass", passed=True, score=1.0),
            _summary("regressed", passed=False, score=0.2),
            _summary("unchanged_fail", passed=False, score=0.2),
            _summary("unchanged_pass", passed=True, score=1.0),
        ]
    )

    diff = compare_suite_results(previous, current)

    assert isinstance(diff, EvalBaselineDiff)
    assert diff.categories == {
        "fixed": 1,
        "missing_transcript": 1,
        "new_fail": 1,
        "new_pass": 1,
        "regressed": 1,
        "unchanged_fail": 1,
        "unchanged_pass": 1,
    }
