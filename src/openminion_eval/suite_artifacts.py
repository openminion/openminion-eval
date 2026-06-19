"""Suite artifact helpers for the public eval package."""

from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from importlib import metadata as importlib_metadata
from pathlib import Path
from typing import Any, Sequence
import uuid

from openminion_eval.schemas import (
    EvalBaselineDiff,
    EvalBaselineDiffEntry,
    EvalResult,
    EvalRunManifest,
    EvalSuiteResult,
    EvalSummary,
    EvalTranscript,
)


SUITE_ARTIFACT_VERSION = "1"


def hash_transcripts(transcripts: Sequence[EvalTranscript]) -> str:
    payload = [asdict(transcript) for transcript in transcripts]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_run_manifest(
    transcripts: Sequence[EvalTranscript],
    *,
    scorer_name: str,
    threshold: float,
    run_id: str | None = None,
    generated_at: str | None = None,
    package_version: str | None = None,
    git_sha: str | None = None,
    deterministic: bool = False,
    seed: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> EvalRunManifest:
    if package_version is None:
        try:
            package_version = importlib_metadata.version("openminion-eval")
        except importlib_metadata.PackageNotFoundError:
            package_version = "0+unknown"

    return EvalRunManifest(
        run_id=run_id or str(uuid.uuid4()),
        generated_at=generated_at or datetime.now(timezone.utc).isoformat(),
        package_version=package_version,
        git_sha=git_sha,
        input_hash=hash_transcripts(transcripts),
        scorer_name=scorer_name,
        threshold=threshold,
        deterministic=deterministic,
        seed=seed,
        metadata=dict(metadata or {}),
    )


def write_suite_result(
    path: str | Path,
    result: EvalSuiteResult,
    manifest: EvalRunManifest,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_version": SUITE_ARTIFACT_VERSION,
        "manifest": asdict(manifest),
        "result": asdict(result),
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_suite_result(path: str | Path) -> tuple[EvalSuiteResult, EvalRunManifest]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    artifact_version = payload.get("artifact_version")
    if artifact_version != SUITE_ARTIFACT_VERSION:
        raise ValueError(f"Unsupported suite artifact version: {artifact_version!r}")
    return (
        _suite_result_from_dict(payload["result"]),
        _manifest_from_dict(payload["manifest"]),
    )


def compare_suite_results(
    previous: EvalSuiteResult,
    current: EvalSuiteResult,
) -> EvalBaselineDiff:
    previous_by_name = {summary.transcript_name: summary for summary in previous.summaries}
    current_by_name = {summary.transcript_name: summary for summary in current.summaries}
    names = sorted(previous_by_name.keys() | current_by_name.keys())
    entries = [
        _diff_entry(
            name,
            previous_by_name.get(name),
            current_by_name.get(name),
        )
        for name in names
    ]
    return EvalBaselineDiff(
        previous_suite_name=previous.suite_name,
        current_suite_name=current.suite_name,
        entries=entries,
    )


def _diff_entry(
    transcript_name: str,
    previous: EvalSummary | None,
    current: EvalSummary | None,
) -> EvalBaselineDiffEntry:
    category = _diff_category(previous, current)
    return EvalBaselineDiffEntry(
        transcript_name=transcript_name,
        category=category,
        previous_passed=None if previous is None else previous.passed,
        current_passed=None if current is None else current.passed,
        previous_average_score=None if previous is None else previous.average_score,
        current_average_score=None if current is None else current.average_score,
    )


def _diff_category(previous: EvalSummary | None, current: EvalSummary | None) -> str:
    if previous is None:
        return "new_pass" if current and current.passed else "new_fail"
    if current is None:
        return "missing_transcript"
    if previous.passed and current.passed:
        return "unchanged_pass"
    if not previous.passed and not current.passed:
        return "unchanged_fail"
    if not previous.passed and current.passed:
        return "fixed"
    return "regressed"


def _manifest_from_dict(data: dict[str, Any]) -> EvalRunManifest:
    return EvalRunManifest(**data)


def _suite_result_from_dict(data: dict[str, Any]) -> EvalSuiteResult:
    summaries = [_summary_from_dict(summary) for summary in data["summaries"]]
    return EvalSuiteResult(
        suite_name=data["suite_name"],
        total_transcripts=data["total_transcripts"],
        passed_transcripts=data["passed_transcripts"],
        failed_transcripts=data["failed_transcripts"],
        summaries=summaries,
        all_passed=data["all_passed"],
    )


def _summary_from_dict(data: dict[str, Any]) -> EvalSummary:
    results = [EvalResult(**result) for result in data["results"]]
    return EvalSummary(
        transcript_name=data["transcript_name"],
        total_turns=data["total_turns"],
        average_score=data["average_score"],
        min_score=data["min_score"],
        max_score=data["max_score"],
        results=results,
        passed=data["passed"],
        threshold=data.get("threshold", 0.80),
        scorer_error_count=data.get("scorer_error_count", 0),
    )
