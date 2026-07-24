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
MemoryTrajectoryMatchMode = Literal["strict", "unordered", "subset", "superset"]
MemoryTraceRedactionStatus = Literal["sanitized", "unredacted", "unknown"]

_FAMILIES = get_args(MemoryEffectivenessCaseFamily)
_TRACE_MODES = get_args(MemoryTraceMode)
_COMPONENTS = get_args(MemoryComponent)
_STATUSES = get_args(MemoryCaseStatus)
_REDACTION_STATUSES = get_args(MemoryTraceRedactionStatus)


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
    operation: str = ""
    memory_location: str = ""

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
    context_memory_ids: tuple[str, ...] = ()
    cited_memory_ids: tuple[str, ...] = ()
    provider_id: str = ""
    model_id: str = ""
    token_count: int | None = None
    cost_usd: float | None = None
    latency_ms: float | None = None
    entity_proposal_ids: tuple[str, ...] = ()
    fact_proposal_ids: tuple[str, ...] = ()
    lifecycle_event_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()
    citation_spans: tuple[str, ...] = ()
    trajectory_steps: tuple[str, ...] = ()
    graph_path_ids: tuple[str, ...] = ()
    valid_time_refs: tuple[str, ...] = ()
    transaction_time_refs: tuple[str, ...] = ()
    redaction_status: MemoryTraceRedactionStatus = "sanitized"
    private_trace_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        _require_literal(self.memory_mode, _TRACE_MODES, "memory_mode")
        for field_name in (
            "saved_memory_ids",
            "retrieved_memory_ids",
            "used_memory_ids",
            "diagnostics",
            "context_memory_ids",
            "cited_memory_ids",
            "entity_proposal_ids",
            "fact_proposal_ids",
            "lifecycle_event_ids",
            "artifact_ids",
            "citation_spans",
            "trajectory_steps",
            "graph_path_ids",
            "valid_time_refs",
            "transaction_time_refs",
            "private_trace_refs",
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
        _require_literal(
            self.redaction_status,
            _REDACTION_STATUSES,
            "redaction_status",
        )


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
    expected_operation: str = ""
    expected_memory_location: str = ""
    expected_retrieved_order: tuple[str, ...] = ()
    required_context_memory_ids: tuple[str, ...] = ()
    required_cited_memory_ids: tuple[str, ...] = ()
    max_unnecessary_memory_calls: int | None = None
    required_entity_proposal_ids: tuple[str, ...] = ()
    required_fact_proposal_ids: tuple[str, ...] = ()
    required_lifecycle_event_ids: tuple[str, ...] = ()
    required_artifact_ids: tuple[str, ...] = ()
    required_citation_spans: tuple[str, ...] = ()
    expected_trajectory_steps: tuple[str, ...] = ()
    trajectory_match_mode: MemoryTrajectoryMatchMode = "strict"
    required_graph_path_ids: tuple[str, ...] = ()
    required_valid_time_refs: tuple[str, ...] = ()
    required_transaction_time_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field_name in (
            "required_saved_ids",
            "required_retrieved_ids",
            "required_used_ids",
            "required_claim_memory_ids",
            "required_tool_memory_ids",
            "forbidden_memory_ids",
            "expected_retrieved_order",
            "required_context_memory_ids",
            "required_cited_memory_ids",
            "required_entity_proposal_ids",
            "required_fact_proposal_ids",
            "required_lifecycle_event_ids",
            "required_artifact_ids",
            "required_citation_spans",
            "expected_trajectory_steps",
            "required_graph_path_ids",
            "required_valid_time_refs",
            "required_transaction_time_refs",
        ):
            object.__setattr__(
                self,
                field_name,
                _normalize_ids(tuple(getattr(self, field_name)), field_name),
            )
        _require_literal(
            self.trajectory_match_mode,
            get_args(MemoryTrajectoryMatchMode),
            "trajectory_match_mode",
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
    operation: str = ""
    memory_location: str = ""
    retrieval_metrics: dict[str, float | int | None] = field(default_factory=dict)
    overuse_penalty: float = 0.0
    underuse_penalty: float = 0.0

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
    operation_scores: dict[str, float] = field(default_factory=dict)
    memory_location_scores: dict[str, float] = field(default_factory=dict)
    retrieval_metrics: dict[str, float | int | None] = field(default_factory=dict)
    overuse_penalties: dict[str, float] = field(default_factory=dict)
    underuse_penalties: dict[str, float] = field(default_factory=dict)
    efficiency_metadata: dict[str, Any] = field(default_factory=dict)
    baseline_trend: dict[str, Any] = field(default_factory=dict)
    public_report_sections: dict[str, str] = field(default_factory=dict)

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
