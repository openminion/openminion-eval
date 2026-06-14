"""Shared helpers for canonical eval-family reports."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Literal, Mapping

from openminion_eval.config import env_flag_enabled
from openminion_eval.constants import DETERMINISTIC_REPORTS_ENV

FAMILY_REPORT_VERSION = "1"
DETERMINISTIC_REPORT_TIMESTAMP = "1970-01-01T00:00:00Z"
OnMissingObservation = Literal["raise", "mark_fail"]


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


class MissingObservationError(KeyError):
    """Raised when a family report lacks a case observation."""

    def __init__(self, family_label: str, case_id: str) -> None:
        self.family_label = family_label
        self.case_id = case_id
        super().__init__(f"{family_label}: no observation for case {case_id!r}")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def report_generated_at() -> str:
    if env_flag_enabled(DETERMINISTIC_REPORTS_ENV):
        return DETERMINISTIC_REPORT_TIMESTAMP
    return utc_now_iso()


def build_family_results(
    cases: Iterable[Any],
    observations: Mapping[str, Any],
    evaluator: Callable[[Any, Any], FamilyEvalCaseResult],
    *,
    family_label: str,
    on_missing: OnMissingObservation = "raise",
) -> tuple[FamilyEvalCaseResult, ...]:
    if on_missing not in ("raise", "mark_fail"):
        raise ValueError(f"unsupported missing-observation policy: {on_missing!r}")

    results: list[FamilyEvalCaseResult] = []
    for case in cases:
        case_id = str(case.case_id)
        if case_id not in observations:
            if on_missing == "raise":
                raise MissingObservationError(family_label, case_id)
            results.append(
                FamilyEvalCaseResult(
                    case_id=case_id,
                    passed=False,
                    metrics={"error": "observation_missing"},
                )
            )
            continue
        results.append(evaluator(case, observations[case_id]))
    return tuple(results)


def load_versioned_json_fixture(
    path: str | Path,
    *,
    expected_version: str = FAMILY_REPORT_VERSION,
) -> dict[str, Any]:
    payload = require_mapping(
        json.loads(Path(path).read_text(encoding="utf-8")),
        context=str(path),
    )
    version = str(payload.get("version", "") or "").strip()
    if version != expected_version:
        raise ValueError(
            f"unsupported fixture version: expected {expected_version!r}, got {version!r}"
        )
    return payload


def load_versioned_cases(
    path: str | Path,
    *,
    case_key: str,
    family_label: str,
    factory: Callable[[Mapping[str, Any]], Any],
) -> tuple[Any, ...]:
    payload = load_versioned_json_fixture(path)
    cases: list[Any] = []
    seen_ids: set[str] = set()
    for item in payload.get(case_key, []):
        mapping = require_mapping(item, context=f"{family_label} item")
        case_id = str(mapping.get("case_id", "") or "").strip()
        if not case_id or case_id in seen_ids:
            raise ValueError(
                f"invalid or duplicate {family_label} case_id: {case_id!r}"
            )
        seen_ids.add(case_id)
        cases.append(factory(mapping))
    return tuple(cases)


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


def count_truthy_metrics(
    results: Iterable[FamilyEvalCaseResult],
    metric_names: Mapping[str, str],
) -> dict[str, int]:
    result_list = list(results)
    return {
        summary_key: sum(
            1 for result in result_list if bool(result.metrics.get(metric_name))
        )
        for summary_key, metric_name in metric_names.items()
    }


def require_mapping(payload: Any, *, context: str) -> Mapping[str, Any]:
    if not isinstance(payload, dict):
        raise ValueError(f"{context} must be a mapping")
    return payload
