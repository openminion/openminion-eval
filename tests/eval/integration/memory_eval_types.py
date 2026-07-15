"""Typed records for the fixture-driven memory eval harness."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from openminion.modules.memory.service import MemoryService


@dataclass(frozen=True)
class MemoryEvalSeedRecord:
    scope: str
    type: str
    content: dict[str, Any] | str
    ref: str | None = None
    key: str | None = None
    title: str | None = None
    confidence: float = 1.0
    source: str = "validated"
    meta: dict[str, Any] = field(default_factory=dict)
    superseded_by: str | None = None
    supersession_reason: str | None = None
    last_hit_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MemoryEvalSeedCandidate:
    session_id: str
    proposed_scope: str
    type: str
    content: dict[str, Any] | str
    candidate_id: str | None = None
    title: str | None = None
    key: str | None = None
    status: str = "proposed"
    confidence: float = 0.5
    source: str = "agent_inferred"
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MemoryEvalGeneratedRecords:
    scope: str
    type: str
    count: int
    content_prefix: str = "generated record"
    title_prefix: str = "Generated Record"
    confidence: float = 0.8


@dataclass(frozen=True)
class MemoryEvalSetup:
    records: list[MemoryEvalSeedRecord] = field(default_factory=list)
    candidates: list[MemoryEvalSeedCandidate] = field(default_factory=list)
    generated_records: list[MemoryEvalGeneratedRecords] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryEvalTurn:
    user: str
    assistant: str | None = None


@dataclass(frozen=True)
class MemoryEvalSession:
    id: str
    turns: list[MemoryEvalTurn]


@dataclass(frozen=True)
class MemoryEvalGroundTruth:
    must_recall: list[str] = field(default_factory=list)
    must_not_surface: list[str] = field(default_factory=list)
    relevance_labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryEvalScenario:
    version: str
    scenario_id: str
    description: str
    eval_dimensions: list[str]
    requires_features: list[str] = field(default_factory=list)
    setup: MemoryEvalSetup = field(default_factory=MemoryEvalSetup)
    sessions: list[MemoryEvalSession] = field(default_factory=list)
    ground_truth: MemoryEvalGroundTruth = field(default_factory=MemoryEvalGroundTruth)


@dataclass(frozen=True)
class MemoryEvalEngineConfig:
    name: str = "default"
    agent_id: str = "eval-agent"
    project_id: str | None = None
    memory_config: Any | None = None
    adapter_kwargs: dict[str, Any] = field(default_factory=dict)
    adapter_factory: (
        Callable[["MemoryService", "MemoryEvalEngineConfig"], Any] | None
    ) = None
    session_context_factory: Callable[[Path], Any] | None = None
    vector_adapter_factory: Callable[[MemoryEvalScenario], Any] | None = None


@dataclass(frozen=True)
class MemoryEvalScenarioResult:
    scenario_id: str
    dimensions: list[str]
    metrics: dict[str, float | int | bool]
    query_count: int


@dataclass(frozen=True)
class MemoryEvalReport:
    engine_name: str
    generated_at: str
    scenario_results: list[MemoryEvalScenarioResult]

    def to_snapshot(self, *, commit: str) -> dict[str, Any]:
        grouped: dict[str, dict[str, Any]] = {}
        for result in self.scenario_results:
            for metric_name, value in result.metrics.items():
                dimension = metric_name.split(".", 1)[0]
                bucket = grouped.setdefault(
                    dimension,
                    {"scenarios": [], "scores": {}},
                )
                if result.scenario_id not in bucket["scenarios"]:
                    bucket["scenarios"].append(result.scenario_id)
                scenario_scores = bucket["scores"].setdefault(result.scenario_id, {})
                scenario_scores[metric_name] = value
        return {
            "timestamp": self.generated_at,
            "commit": commit,
            "engine_name": self.engine_name,
            "dimensions": grouped,
        }


@dataclass(frozen=True)
class MemoryEvalComparisonEntry:
    scenario_id: str
    metric_name: str
    before: float | int | bool
    after: float | int | bool
    status: str


@dataclass(frozen=True)
class MemoryEvalComparison:
    entries: list[MemoryEvalComparisonEntry]


__all__ = [
    "MemoryEvalComparison",
    "MemoryEvalComparisonEntry",
    "MemoryEvalEngineConfig",
    "MemoryEvalGeneratedRecords",
    "MemoryEvalGroundTruth",
    "MemoryEvalReport",
    "MemoryEvalScenario",
    "MemoryEvalScenarioResult",
    "MemoryEvalSeedCandidate",
    "MemoryEvalSeedRecord",
    "MemoryEvalSession",
    "MemoryEvalSetup",
    "MemoryEvalTurn",
]
