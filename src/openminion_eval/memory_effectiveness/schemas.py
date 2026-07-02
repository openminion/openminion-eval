"""Typed memory-effectiveness eval contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, get_args


MemoryEffectivenessCaseFamily = Literal[
    "preference_learning",
    "repo_convention",
    "procedure_memory",
    "graph_relation_use",
    "stale_and_conflict",
    "privacy_and_export",
    "noisy_memory",
    "negative_no_memory",
]
MemoryTraceMode = Literal["disabled", "enabled"]
MemoryComponent = Literal["save", "retrieval", "usage", "longitudinal"]
MemoryCaseStatus = Literal["passed", "failed", "unsupported_by_design"]

_FAMILIES = get_args(MemoryEffectivenessCaseFamily)
_TRACE_MODES = get_args(MemoryTraceMode)
_COMPONENTS = get_args(MemoryComponent)
_STATUSES = get_args(MemoryCaseStatus)


def _require_literal(value: str, allowed: tuple[str, ...], label: str) -> None:
    if value not in allowed:
        raise ValueError(f"invalid {label}: {value!r}")


def _require_non_empty(value: str, label: str) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


def _normalize_ids(values: tuple[str, ...], label: str) -> tuple[str, ...]:
    normalized = tuple(str(value or "").strip() for value in values)
    if any(not value for value in normalized):
        raise ValueError(f"{label} must not contain empty ids")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must not contain duplicate ids")
    return normalized


@dataclass(frozen=True)
class MemoryTraceClaim:
    claim: str
    memory_id: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "claim", _require_non_empty(self.claim, "claim"))
        object.__setattr__(
            self, "memory_id", _require_non_empty(self.memory_id, "memory_id")
        )


@dataclass(frozen=True)
class MemoryTraceToolCall:
    tool: str
    arguments_ref: str
    memory_ids: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "tool", _require_non_empty(self.tool, "tool"))
        object.__setattr__(
            self,
            "arguments_ref",
            _require_non_empty(self.arguments_ref, "arguments_ref"),
        )
        object.__setattr__(
            self, "memory_ids", _normalize_ids(tuple(self.memory_ids), "memory_ids")
        )


@dataclass(frozen=True)
class MemoryEffectivenessTrace:
    case_id: str
    run_id: str
    memory_mode: MemoryTraceMode
    saved_memory_ids: tuple[str, ...] = ()
    retrieved_memory_ids: tuple[str, ...] = ()
    used_memory_ids: tuple[str, ...] = ()
    supporting_claims: tuple[MemoryTraceClaim, ...] = ()
    tool_calls: tuple[MemoryTraceToolCall, ...] = ()
    diagnostics: tuple[str, ...] = ()
    namespace: str = ""
    timestamp: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        _require_literal(self.memory_mode, _TRACE_MODES, "memory_mode")
        for field_name in (
            "saved_memory_ids",
            "retrieved_memory_ids",
            "used_memory_ids",
            "diagnostics",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_ids(tuple(getattr(self, field_name)), field_name),
            )
        for claim in self.supporting_claims:
            if not isinstance(claim, MemoryTraceClaim):
                raise TypeError("supporting_claims must contain MemoryTraceClaim")
        for call in self.tool_calls:
            if not isinstance(call, MemoryTraceToolCall):
                raise TypeError("tool_calls must contain MemoryTraceToolCall")


@dataclass(frozen=True)
class MemoryExpectation:
    required_saved_ids: tuple[str, ...] = ()
    required_retrieved_ids: tuple[str, ...] = ()
    required_used_ids: tuple[str, ...] = ()
    required_claim_memory_ids: tuple[str, ...] = ()
    required_tool_memory_ids: tuple[str, ...] = ()
    forbidden_memory_ids: tuple[str, ...] = ()
    expected_namespace: str = ""
    expect_no_memory_claim: bool = False
    requires_longitudinal_improvement: bool = False
    critical: bool = False
    description: str = ""

    def __post_init__(self) -> None:
        for field_name in (
            "required_saved_ids",
            "required_retrieved_ids",
            "required_used_ids",
            "required_claim_memory_ids",
            "required_tool_memory_ids",
            "forbidden_memory_ids",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_ids(tuple(getattr(self, field_name)), field_name),
            )


@dataclass(frozen=True)
class MemoryEffectivenessCase:
    case_id: str
    family: MemoryEffectivenessCaseFamily
    prompt: str
    expectations: MemoryExpectation
    teaching_turns: tuple[str, ...] = ()
    followup_turns: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        _require_literal(self.family, _FAMILIES, "family")
        object.__setattr__(self, "prompt", _require_non_empty(self.prompt, "prompt"))
        if not isinstance(self.expectations, MemoryExpectation):
            raise TypeError("expectations must be MemoryExpectation")
        object.__setattr__(self, "tags", tuple(str(tag) for tag in self.tags))


@dataclass(frozen=True)
class MemoryComponentScore:
    component: MemoryComponent
    passed: int
    total: int
    score: float
    failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_literal(self.component, _COMPONENTS, "component")
        if self.passed < 0 or self.total < 0 or self.passed > self.total:
            raise ValueError("passed/total counts are invalid")
        if not 0.0 <= float(self.score) <= 1.0:
            raise ValueError("score must be between 0 and 1")


@dataclass(frozen=True)
class MemoryEffectivenessCaseResult:
    case_id: str
    status: MemoryCaseStatus
    component_scores: tuple[MemoryComponentScore, ...]
    critical_failures: tuple[str, ...] = ()
    diagnostics: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        _require_literal(self.status, _STATUSES, "status")
        if {score.component for score in self.component_scores} != set(_COMPONENTS):
            raise ValueError(
                "component_scores must include every component exactly once"
            )

    @property
    def overall_score(self) -> float:
        weights = {"save": 0.20, "retrieval": 0.25, "usage": 0.35, "longitudinal": 0.20}
        scores = {score.component: score.score for score in self.component_scores}
        return sum(scores[component] * weight for component, weight in weights.items())


@dataclass(frozen=True)
class MemoryEffectivenessScorecard:
    suite_id: str
    run_id: str
    cases: tuple[MemoryEffectivenessCaseResult, ...]
    component_scores: tuple[MemoryComponentScore, ...]
    overall_score: float
    critical_failures: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "suite_id", _require_non_empty(self.suite_id, "suite_id")
        )
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        if not 0.0 <= float(self.overall_score) <= 1.0:
            raise ValueError("overall_score must be between 0 and 1")


@dataclass(frozen=True)
class MemoryPairedRunComparison:
    case_id: str
    disabled_score: float
    enabled_score: float
    delta: float
    improved: bool
    critical_failures: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
