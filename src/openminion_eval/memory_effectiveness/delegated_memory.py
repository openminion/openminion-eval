"""Deterministic utility and isolation scoring for delegated memory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from importlib.resources import files
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Literal

DelegatedMemoryEvalMode = Literal["disabled", "private_only", "delegated_shared"]

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
    suite_id: str = "delegated-multi-agent-memory.v1",
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
    if payload.get("version") != "delegated-multi-agent-memory.v1":
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


__all__ = [
    "DelegatedMemoryEvalCase",
    "DelegatedMemoryEvalMode",
    "DelegatedMemoryEvalResult",
    "DelegatedMemoryEvalScorecard",
    "DelegatedMemoryEvalTrace",
    "build_delegated_memory_scorecard",
    "default_delegated_memory_cases_path",
    "load_delegated_memory_cases",
    "score_delegated_memory_case",
]
