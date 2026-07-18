"""Typed scorecard contract for deterministic memory/context quality gates."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, get_args


MemoryContextMetricName = Literal[
    "recall_precision",
    "block_usefulness",
    "contradiction_replacement",
    "handoff_recall",
    "budget_stability",
    "memory_influence",
    "governance_regression",
    "selected_source_precision",
    "continuation_completeness",
    "stale_reference_safety",
    "non_replay_safety",
    "permission_safety",
    "lineage_accuracy",
    "context_budget_stability",
    "first_turn_usefulness",
]
MemoryContextMetricStatus = Literal["pass", "warn", "fail", "advisory"]
TaskOracleKind = Literal["exact_text", "boolean", "structured_field"]

_METRIC_NAMES = get_args(MemoryContextMetricName)
_STATUSES = get_args(MemoryContextMetricStatus)
_ORACLE_KINDS = get_args(TaskOracleKind)
_PAIR_REQUIRED_BLOCKING_METRICS = frozenset({"block_usefulness", "memory_influence"})


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
        raise ValueError(f"{label} must not contain empty values")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{label} must not contain duplicates")
    return normalized


@dataclass(frozen=True)
class TaskOracle:
    oracle_id: str
    kind: TaskOracleKind
    expected_value: str
    field_path: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "oracle_id", _require_non_empty(self.oracle_id, "oracle_id")
        )
        _require_literal(self.kind, _ORACLE_KINDS, "oracle kind")
        object.__setattr__(
            self,
            "expected_value",
            _require_non_empty(self.expected_value, "expected_value"),
        )
        if self.kind == "structured_field":
            object.__setattr__(
                self, "field_path", _require_non_empty(self.field_path, "field_path")
            )


@dataclass(frozen=True)
class AblationOutcome:
    output_ref: str
    oracle_passed: bool
    score: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "output_ref", _require_non_empty(self.output_ref, "output_ref")
        )
        if not 0.0 <= float(self.score) <= 1.0:
            raise ValueError("ablation score must be between 0 and 1")


@dataclass(frozen=True)
class ScorecardMetricFixture:
    metric_name: MemoryContextMetricName
    value: float
    threshold: float
    status: MemoryContextMetricStatus
    blocking: bool
    evidence_refs: tuple[str, ...]
    context_trace_ids: tuple[str, ...] = ()
    provenance_trace_ids: tuple[str, ...] = ()
    disabled_outcome: AblationOutcome | None = None
    enabled_outcome: AblationOutcome | None = None
    oracle: TaskOracle | None = None
    provider_backed: bool = False
    variance_evidence_ref: str = ""

    def __post_init__(self) -> None:
        _require_literal(self.metric_name, _METRIC_NAMES, "metric name")
        _require_literal(self.status, _STATUSES, "metric status")
        if not 0.0 <= float(self.value) <= 1.0:
            raise ValueError("metric value must be between 0 and 1")
        if not 0.0 <= float(self.threshold) <= 1.0:
            raise ValueError("metric threshold must be between 0 and 1")
        object.__setattr__(
            self,
            "evidence_refs",
            _normalize_ids(tuple(self.evidence_refs), "evidence_refs"),
        )
        if not self.evidence_refs:
            raise ValueError("evidence_refs is required")
        object.__setattr__(
            self,
            "context_trace_ids",
            _normalize_ids(tuple(self.context_trace_ids), "context_trace_ids"),
        )
        object.__setattr__(
            self,
            "provenance_trace_ids",
            _normalize_ids(tuple(self.provenance_trace_ids), "provenance_trace_ids"),
        )
        if self.blocking and self.metric_name in _PAIR_REQUIRED_BLOCKING_METRICS:
            if not (self.disabled_outcome and self.enabled_outcome and self.oracle):
                raise ValueError(
                    f"blocking {self.metric_name} requires paired outcomes and oracle"
                )
            if self.status == "pass" and not _controlled_pair_has_delta(
                self.disabled_outcome, self.enabled_outcome
            ):
                raise ValueError(
                    f"passing {self.metric_name} requires a non-zero paired delta"
                )
        if self.blocking and self.provider_backed and not self.variance_evidence_ref:
            raise ValueError(
                "provider-backed blocking metrics require variance_evidence_ref"
            )


@dataclass(frozen=True)
class ScorecardCaseFixture:
    case_id: str
    task_input_ref: str
    tool_fixture_ref: str
    model_config_ref: str
    seed: str
    metrics: tuple[ScorecardMetricFixture, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "case_id", _require_non_empty(self.case_id, "case_id"))
        for field_name in (
            "task_input_ref",
            "tool_fixture_ref",
            "model_config_ref",
            "seed",
        ):
            object.__setattr__(
                self,
                field_name,
                _require_non_empty(getattr(self, field_name), field_name),
            )
        if not self.metrics:
            raise ValueError("metrics is required")
        names = [metric.metric_name for metric in self.metrics]
        if len(set(names)) != len(names):
            raise ValueError("metrics must not contain duplicate metric names")


@dataclass(frozen=True)
class MemoryContextMetric:
    metric_name: MemoryContextMetricName
    status: MemoryContextMetricStatus
    value: float
    threshold: float
    blocking: bool
    evidence_refs: tuple[str, ...]
    context_trace_ids: tuple[str, ...] = ()
    provenance_trace_ids: tuple[str, ...] = ()
    disabled_outcome: AblationOutcome | None = None
    enabled_outcome: AblationOutcome | None = None
    delta: float | None = None
    oracle: TaskOracle | None = None
    provider_backed: bool = False
    variance_evidence_ref: str = ""

    def __post_init__(self) -> None:
        _require_literal(self.metric_name, _METRIC_NAMES, "metric name")
        _require_literal(self.status, _STATUSES, "metric status")
        if not 0.0 <= float(self.value) <= 1.0:
            raise ValueError("metric value must be between 0 and 1")


@dataclass(frozen=True)
class MemoryContextScorecardV1:
    report_version: str
    generated_at: str
    run_id: str
    fixture_ids: tuple[str, ...]
    metrics: tuple[MemoryContextMetric, ...]
    summary: dict[str, int | float | bool | str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.report_version != "memory-context-scorecard.v1":
            raise ValueError(f"unsupported report_version: {self.report_version!r}")
        object.__setattr__(
            self, "generated_at", _require_non_empty(self.generated_at, "generated_at")
        )
        object.__setattr__(self, "run_id", _require_non_empty(self.run_id, "run_id"))
        object.__setattr__(
            self, "fixture_ids", _normalize_ids(tuple(self.fixture_ids), "fixture_ids")
        )
        if not self.metrics:
            raise ValueError("metrics is required")


def _controlled_pair_has_delta(
    disabled: AblationOutcome, enabled: AblationOutcome
) -> bool:
    return round(float(enabled.score) - float(disabled.score), 6) != 0.0
