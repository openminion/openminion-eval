"""Deterministic utility and isolation scoring for delegated memory."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Literal, cast

from openminion_eval.memory_effectiveness.artifact_payloads import (
    json_objects,
    strings_from_value,
)

DelegatedMemoryEvalMode = Literal["disabled", "private_only", "delegated_shared"]
DelegatedMemoryDiffCategory = Literal[
    "unchanged_pass",
    "unchanged_fail",
    "improved",
    "regressed",
    "new_case",
    "missing_case",
]

DELEGATED_MEMORY_FIXTURE_VERSION = "delegated-multi-agent-memory.v1"
DELEGATED_MEMORY_SCORECARD_VERSION = "delegated-memory-scorecard.v1"
DELEGATED_MEMORY_DIFF_VERSION = "delegated-memory-diff.v1"

_MODES = frozenset({"disabled", "private_only", "delegated_shared"})


def _ids(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(str(value).strip() for value in values)
    if any(not value for value in normalized) or len(set(normalized)) != len(
        normalized
    ):
        raise ValueError(f"{label} must contain unique non-empty ids")
    return normalized


@dataclass(frozen=True, slots=True)
class DelegatedMemoryEvalCase:
    """Expected useful and forbidden recall for one explicit access posture."""

    case_id: str
    scenario: str
    mode: DelegatedMemoryEvalMode
    required_recall_ids: tuple[str, ...] = ()
    forbidden_recall_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or not self.scenario:
            raise ValueError("case_id and scenario are required")
        if self.mode not in _MODES:
            raise ValueError(f"invalid delegated memory eval mode: {self.mode!r}")
        object.__setattr__(
            self,
            "required_recall_ids",
            _ids(self.required_recall_ids, "required_recall_ids"),
        )
        object.__setattr__(
            self,
            "forbidden_recall_ids",
            _ids(self.forbidden_recall_ids, "forbidden_recall_ids"),
        )


@dataclass(frozen=True, slots=True)
class DelegatedMemoryEvalTrace:
    """Sanitized structural facts observed during one eval case."""

    case_id: str
    retrieved_memory_ids: tuple[str, ...] = ()
    sibling_scratch_ids: tuple[str, ...] = ()
    direct_id_bypass_ids: tuple[str, ...] = ()
    revoked_future_operation_ids: tuple[str, ...] = ()
    forbidden_reshare_ids: tuple[str, ...] = ()
    accepted_poisoning_ids: tuple[str, ...] = ()
    provenance_failures: tuple[str, ...] = ()
    forgetting_failures: tuple[str, ...] = ()
    prior_delivery_ids: tuple[str, ...] = ()
    latency_ms: float = 0.0
    token_count: int = 0

    def __post_init__(self) -> None:
        if not self.case_id:
            raise ValueError("case_id is required")
        for name in (
            "retrieved_memory_ids",
            "sibling_scratch_ids",
            "direct_id_bypass_ids",
            "revoked_future_operation_ids",
            "forbidden_reshare_ids",
            "accepted_poisoning_ids",
            "provenance_failures",
            "forgetting_failures",
            "prior_delivery_ids",
        ):
            object.__setattr__(self, name, _ids(tuple(getattr(self, name)), name))
        if self.latency_ms < 0 or self.token_count < 0:
            raise ValueError("latency_ms and token_count cannot be negative")


@dataclass(frozen=True, slots=True)
class DelegatedMemoryEvalResult:
    case_id: str
    mode: DelegatedMemoryEvalMode
    utility_recall: float
    passed: bool
    critical_failures: tuple[str, ...]
    latency_ms: float
    token_count: int


@dataclass(frozen=True, slots=True)
class DelegatedMemoryEvalScorecard:
    suite_id: str
    results: tuple[DelegatedMemoryEvalResult, ...]
    utility_recall: float
    passed: bool
    critical_failures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DelegatedMemoryScorecardComparison:
    case_id: str
    category: DelegatedMemoryDiffCategory
    previous_passed: bool | None
    current_passed: bool | None
    previous_utility_recall: float | None
    current_utility_recall: float | None
    delta: float | None
    critical_failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DelegatedMemoryScorecardDiff:
    version: str
    previous_suite_id: str
    current_suite_id: str
    categories: dict[str, int]
    entries: tuple[DelegatedMemoryScorecardComparison, ...]

    def __post_init__(self) -> None:
        if self.version != DELEGATED_MEMORY_DIFF_VERSION:
            raise ValueError(
                f"unsupported delegated memory diff version: {self.version!r}"
            )
        if not self.previous_suite_id or not self.current_suite_id:
            raise ValueError("previous_suite_id and current_suite_id are required")


def score_delegated_memory_case(
    case: DelegatedMemoryEvalCase,
    trace: DelegatedMemoryEvalTrace,
) -> DelegatedMemoryEvalResult:
    """Score typed trace facts without a provider or semantic judge."""

    if case.case_id != trace.case_id:
        raise ValueError("case_id mismatch")
    retrieved = set(trace.retrieved_memory_ids)
    required = set(case.required_recall_ids)
    utility = len(required & retrieved) / len(required) if required else 1.0
    forbidden = sorted(set(case.forbidden_recall_ids) & retrieved)
    failures: list[str] = []
    if forbidden:
        failures.append("unauthorized_disclosure:" + ",".join(forbidden))
    for label, values in (
        ("sibling_scratch_leak", trace.sibling_scratch_ids),
        ("direct_id_bypass", trace.direct_id_bypass_ids),
        ("revoked_future_operation", trace.revoked_future_operation_ids),
        ("forbidden_reshare", trace.forbidden_reshare_ids),
        ("poisoning_accepted", trace.accepted_poisoning_ids),
        ("provenance_invalid", trace.provenance_failures),
        ("forgetting_invalid", trace.forgetting_failures),
    ):
        if values:
            failures.append(f"{label}:" + ",".join(values))
    if utility < 1.0:
        failures.append(f"required_recall_missing:{utility:.6f}")
    return DelegatedMemoryEvalResult(
        case_id=case.case_id,
        mode=case.mode,
        utility_recall=round(utility, 6),
        passed=not failures,
        critical_failures=tuple(failures),
        latency_ms=trace.latency_ms,
        token_count=trace.token_count,
    )


def build_delegated_memory_scorecard(
    cases: tuple[DelegatedMemoryEvalCase, ...],
    traces: tuple[DelegatedMemoryEvalTrace, ...],
    *,
    suite_id: str = DELEGATED_MEMORY_FIXTURE_VERSION,
) -> DelegatedMemoryEvalScorecard:
    """Build a deterministic suite result with a critical security gate."""

    traces_by_case = {trace.case_id: trace for trace in traces}
    if len(traces_by_case) != len(traces):
        raise ValueError("duplicate trace case_id")
    missing = [case.case_id for case in cases if case.case_id not in traces_by_case]
    if missing:
        raise ValueError("missing traces: " + ",".join(missing))
    results = tuple(
        score_delegated_memory_case(case, traces_by_case[case.case_id])
        for case in cases
    )
    failures = tuple(
        f"{result.case_id}:{failure}"
        for result in results
        for failure in result.critical_failures
    )
    utility = (
        sum(result.utility_recall for result in results) / len(results)
        if results
        else 0.0
    )
    return DelegatedMemoryEvalScorecard(
        suite_id=suite_id,
        results=results,
        utility_recall=round(utility, 6),
        passed=not failures,
        critical_failures=failures,
    )


def compare_delegated_memory_scorecards(
    previous: DelegatedMemoryEvalScorecard,
    current: DelegatedMemoryEvalScorecard,
) -> tuple[DelegatedMemoryScorecardComparison, ...]:
    previous_by_case = {result.case_id: result for result in previous.results}
    current_by_case = {result.case_id: result for result in current.results}
    return tuple(
        _compare_delegated_memory_case(
            case_id,
            previous_by_case.get(case_id),
            current_by_case.get(case_id),
        )
        for case_id in sorted(previous_by_case.keys() | current_by_case.keys())
    )


def build_delegated_memory_scorecard_diff(
    previous: DelegatedMemoryEvalScorecard,
    current: DelegatedMemoryEvalScorecard,
) -> DelegatedMemoryScorecardDiff:
    entries = compare_delegated_memory_scorecards(previous, current)
    categories = {
        category: sum(1 for item in entries if item.category == category)
        for category in sorted({item.category for item in entries})
    }
    return DelegatedMemoryScorecardDiff(
        version=DELEGATED_MEMORY_DIFF_VERSION,
        previous_suite_id=previous.suite_id,
        current_suite_id=current.suite_id,
        categories=categories,
        entries=entries,
    )


def default_delegated_memory_cases_path() -> Traversable:
    return files("openminion_eval.memory_effectiveness").joinpath(
        "resources/delegated_multi_agent_memory_cases.json"
    )


def load_delegated_memory_cases(
    path: str | Path | Traversable | None = None,
) -> tuple[DelegatedMemoryEvalCase, ...]:
    if path is None:
        source = default_delegated_memory_cases_path()
    elif isinstance(path, (str, Path)):
        source = Path(path)
    else:
        source = path
    payload = json.loads(source.read_text(encoding="utf-8"))
    if payload.get("version") != DELEGATED_MEMORY_FIXTURE_VERSION:
        raise ValueError("unsupported delegated memory fixture version")
    return tuple(
        DelegatedMemoryEvalCase(
            case_id=item["case_id"],
            scenario=item["scenario"],
            mode=item["mode"],
            required_recall_ids=tuple(item.get("required_recall_ids", ())),
            forbidden_recall_ids=tuple(item.get("forbidden_recall_ids", ())),
        )
        for item in payload["cases"]
    )


def write_delegated_memory_scorecard(
    path: str | Path,
    scorecard: DelegatedMemoryEvalScorecard,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": DELEGATED_MEMORY_SCORECARD_VERSION,
        **asdict(scorecard),
    }
    output_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def load_delegated_memory_scorecard(path: str | Path) -> DelegatedMemoryEvalScorecard:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("delegated memory scorecard must be a JSON object")
    if payload.get("version") != DELEGATED_MEMORY_SCORECARD_VERSION:
        raise ValueError("unsupported delegated memory scorecard version")
    results = payload.get("results", ())
    if not isinstance(results, list | tuple):
        raise TypeError("delegated memory scorecard results must be a list")
    return DelegatedMemoryEvalScorecard(
        suite_id=str(payload.get("suite_id", "")),
        results=tuple(
            _delegated_memory_result_from_payload(item)
            for item in json_objects(results, "results")
        ),
        utility_recall=float(payload.get("utility_recall", 0.0)),
        passed=bool(payload.get("passed", False)),
        critical_failures=strings_from_value(
            payload.get("critical_failures", ()),
            "critical_failures",
        ),
    )


def write_delegated_memory_scorecard_diff(
    path: str | Path,
    diff: DelegatedMemoryScorecardDiff,
) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(diff), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def load_delegated_memory_scorecard_diff(
    path: str | Path,
) -> DelegatedMemoryScorecardDiff:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("delegated memory diff must be a JSON object")
    if payload.get("version") != DELEGATED_MEMORY_DIFF_VERSION:
        raise ValueError("unsupported delegated memory diff version")
    entries = payload.get("entries", ())
    if not isinstance(entries, list | tuple):
        raise TypeError("delegated memory diff entries must be a list")
    categories = payload.get("categories", {})
    if not isinstance(categories, dict):
        raise TypeError("delegated memory diff categories must be an object")
    normalized_categories = {
        _delegated_memory_diff_category(key): int(value)
        for key, value in categories.items()
    }
    return DelegatedMemoryScorecardDiff(
        version=str(payload.get("version", "")),
        previous_suite_id=str(payload.get("previous_suite_id", "")),
        current_suite_id=str(payload.get("current_suite_id", "")),
        categories=normalized_categories,
        entries=tuple(
            _comparison_from_payload(item) for item in json_objects(entries, "entries")
        ),
    )


def _delegated_memory_result_from_payload(
    data: dict[str, Any],
) -> DelegatedMemoryEvalResult:
    return DelegatedMemoryEvalResult(
        case_id=str(data.get("case_id", "")),
        mode=_delegated_memory_mode(data.get("mode")),
        utility_recall=float(data.get("utility_recall", 0.0)),
        passed=bool(data.get("passed", False)),
        critical_failures=strings_from_value(
            data.get("critical_failures", ()),
            "critical_failures",
        ),
        latency_ms=float(data.get("latency_ms", 0.0)),
        token_count=int(data.get("token_count", 0)),
    )


def _delegated_memory_mode(value: object) -> DelegatedMemoryEvalMode:
    if value in _MODES:
        return cast(DelegatedMemoryEvalMode, value)
    raise ValueError(f"invalid delegated memory eval mode: {value!r}")


def _delegated_memory_diff_category(value: object) -> DelegatedMemoryDiffCategory:
    categories = {
        "unchanged_pass",
        "unchanged_fail",
        "improved",
        "regressed",
        "new_case",
        "missing_case",
    }
    if value in categories:
        return cast(DelegatedMemoryDiffCategory, value)
    raise ValueError(f"invalid delegated memory diff category: {value!r}")


def _comparison_from_payload(
    data: dict[str, Any],
) -> DelegatedMemoryScorecardComparison:
    return DelegatedMemoryScorecardComparison(
        case_id=str(data.get("case_id", "")),
        category=_delegated_memory_diff_category(data.get("category")),
        previous_passed=_optional_bool(data.get("previous_passed")),
        current_passed=_optional_bool(data.get("current_passed")),
        previous_utility_recall=_optional_float(data.get("previous_utility_recall")),
        current_utility_recall=_optional_float(data.get("current_utility_recall")),
        delta=_optional_float(data.get("delta")),
        critical_failures=strings_from_value(
            data.get("critical_failures", ()),
            "critical_failures",
        ),
    )


def _optional_bool(value: object) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    raise TypeError("delegated memory diff pass fields must be booleans or null")


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _compare_delegated_memory_case(
    case_id: str,
    previous: DelegatedMemoryEvalResult | None,
    current: DelegatedMemoryEvalResult | None,
) -> DelegatedMemoryScorecardComparison:
    if previous is None:
        return _delegated_comparison(case_id, "new_case", previous, current)
    if current is None:
        return _delegated_comparison(case_id, "missing_case", previous, current)
    if previous.passed and not current.passed:
        category: DelegatedMemoryDiffCategory = "regressed"
    elif not previous.passed and current.passed:
        category = "improved"
    elif current.passed:
        category = "unchanged_pass"
    else:
        category = "unchanged_fail"
    return _delegated_comparison(case_id, category, previous, current)


def _delegated_comparison(
    case_id: str,
    category: DelegatedMemoryDiffCategory,
    previous: DelegatedMemoryEvalResult | None,
    current: DelegatedMemoryEvalResult | None,
) -> DelegatedMemoryScorecardComparison:
    previous_utility = None if previous is None else previous.utility_recall
    current_utility = None if current is None else current.utility_recall
    delta = (
        None
        if previous_utility is None or current_utility is None
        else round(current_utility - previous_utility, 6)
    )
    return DelegatedMemoryScorecardComparison(
        case_id=case_id,
        category=category,
        previous_passed=None if previous is None else previous.passed,
        current_passed=None if current is None else current.passed,
        previous_utility_recall=previous_utility,
        current_utility_recall=current_utility,
        delta=delta,
        critical_failures=() if current is None else current.critical_failures,
    )


__all__ = [
    "DELEGATED_MEMORY_DIFF_VERSION",
    "DELEGATED_MEMORY_FIXTURE_VERSION",
    "DELEGATED_MEMORY_SCORECARD_VERSION",
    "DelegatedMemoryDiffCategory",
    "DelegatedMemoryEvalCase",
    "DelegatedMemoryEvalMode",
    "DelegatedMemoryEvalResult",
    "DelegatedMemoryEvalScorecard",
    "DelegatedMemoryEvalTrace",
    "DelegatedMemoryScorecardComparison",
    "DelegatedMemoryScorecardDiff",
    "build_delegated_memory_scorecard_diff",
    "build_delegated_memory_scorecard",
    "compare_delegated_memory_scorecards",
    "default_delegated_memory_cases_path",
    "load_delegated_memory_cases",
    "load_delegated_memory_scorecard_diff",
    "load_delegated_memory_scorecard",
    "score_delegated_memory_case",
    "write_delegated_memory_scorecard_diff",
    "write_delegated_memory_scorecard",
]
