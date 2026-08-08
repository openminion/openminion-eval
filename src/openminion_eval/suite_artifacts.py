"""Suite artifact helpers for the public eval package."""

from __future__ import annotations

from dataclasses import asdict, dataclass
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
    EvalCaseTrace,
    EvalResult,
    EvalRunManifest,
    EvalSuiteResult,
    EvalSummary,
    EvalTranscript,
)


SUITE_ARTIFACT_VERSION = "1"
SUITE_DIFF_VERSION = "suite-diff.v1"


@dataclass(frozen=True)
class EvalSuiteDiffArtifact:
    version: str
    previous_suite_name: str
    current_suite_name: str
    categories: dict[str, int]
    entries: list[EvalBaselineDiffEntry]

    def __post_init__(self) -> None:
        if self.version != SUITE_DIFF_VERSION:
            raise ValueError(f"unsupported suite diff version: {self.version!r}")
        if not self.previous_suite_name or not self.current_suite_name:
            raise ValueError("previous_suite_name and current_suite_name are required")


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


def build_suite_diff_artifact(
    previous: EvalSuiteResult,
    current: EvalSuiteResult,
) -> EvalSuiteDiffArtifact:
    diff = compare_suite_results(previous, current)
    return EvalSuiteDiffArtifact(
        version=SUITE_DIFF_VERSION,
        previous_suite_name=diff.previous_suite_name,
        current_suite_name=diff.current_suite_name,
        categories=diff.categories,
        entries=diff.entries,
    )


def write_suite_diff(path: str | Path, artifact: EvalSuiteDiffArtifact) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(artifact), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def build_case_traces(result: EvalSuiteResult) -> list[EvalCaseTrace]:
    traces: list[EvalCaseTrace] = []
    for summary in result.summaries:
        for case_result in summary.results:
            traces.append(
                EvalCaseTrace(
                    transcript_name=summary.transcript_name,
                    turn_index=case_result.turn_index,
                    user_input=case_result.user_input,
                    actual=case_result.actual,
                    expected=case_result.expected,
                    duration_ms=float(case_result.metadata.get("duration_ms", 0.0)),
                    executor_error=case_result.metadata.get("executor_error"),
                    scorer_name=case_result.scorer_name,
                    score=case_result.score,
                    scorer_reason=case_result.scorer_reason,
                    scorer_threshold=case_result.scorer_threshold,
                )
            )
    return traces


def write_case_traces_jsonl(path: str | Path, result: EvalSuiteResult) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(asdict(trace), sort_keys=True, separators=(",", ":"))
        for trace in build_case_traces(result)
    ]
    target.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
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


def load_suite_diff(path: str | Path) -> EvalSuiteDiffArtifact:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("suite diff artifact must be a JSON object")
    categories = payload.get("categories", {})
    entries = payload.get("entries", [])
    if not isinstance(categories, dict):
        raise TypeError("suite diff categories must be an object")
    if not isinstance(entries, list):
        raise TypeError("suite diff entries must be a list")
    return EvalSuiteDiffArtifact(
        version=str(payload.get("version", "")),
        previous_suite_name=str(payload.get("previous_suite_name", "")),
        current_suite_name=str(payload.get("current_suite_name", "")),
        categories={
            _diff_category_from_value(key): int(value)
            for key, value in categories.items()
        },
        entries=[_diff_entry_from_dict(item) for item in entries],
    )


def compare_suite_results(
    previous: EvalSuiteResult,
    current: EvalSuiteResult,
) -> EvalBaselineDiff:
    previous_by_name = {
        summary.transcript_name: summary for summary in previous.summaries
    }
    current_by_name = {
        summary.transcript_name: summary for summary in current.summaries
    }
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


def _diff_category_from_value(value: object) -> str:
    category = str(value)
    allowed = {
        "fixed",
        "missing_transcript",
        "new_fail",
        "new_pass",
        "regressed",
        "unchanged_fail",
        "unchanged_pass",
    }
    if category not in allowed:
        raise ValueError(f"unsupported suite diff category: {category!r}")
    return category


def _diff_entry_from_dict(data: Any) -> EvalBaselineDiffEntry:
    if not isinstance(data, dict):
        raise TypeError("suite diff entries must be objects")
    return EvalBaselineDiffEntry(
        transcript_name=str(data.get("transcript_name", "")),
        category=_diff_category_from_value(data.get("category")),
        previous_passed=_optional_bool(data.get("previous_passed")),
        current_passed=_optional_bool(data.get("current_passed")),
        previous_average_score=_optional_float(data.get("previous_average_score")),
        current_average_score=_optional_float(data.get("current_average_score")),
    )


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError("suite diff pass fields must be booleans or null")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


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
