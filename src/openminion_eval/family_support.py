"""Shared helpers for canonical eval families."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Iterable, Mapping


@dataclass(frozen=True)
class FamilyEvalCaseResult:
    case_id: str
    passed: bool
    metrics: dict[str, float | int | bool | str]


@dataclass(frozen=True)
class FamilyEvalSummary:
    case_count: int
    passed_count: int
    failed_count: int
    metrics: dict[str, float | int | bool | str]


@dataclass(frozen=True)
class FamilyEvalReport:
    report_version: str
    generated_at: str
    family_id: str
    cases: tuple[FamilyEvalCaseResult, ...]
    summary: FamilyEvalSummary

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_versioned_json_fixture(
    path: str | Path,
    *,
    expected_version: str = "1",
) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != expected_version:
        raise ValueError(
            f"unsupported fixture version: expected {expected_version!r}, got {version!r}"
        )
    return payload


def write_json_report(path: str | Path, report: FamilyEvalReport) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def count_pass_fail(cases: Iterable[FamilyEvalCaseResult]) -> tuple[int, int]:
    passed = sum(1 for case in cases if case.passed)
    failed = sum(1 for case in cases if not case.passed)
    return passed, failed


def require_mapping(payload: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{context} must be a mapping")
    return payload
