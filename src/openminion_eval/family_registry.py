"""Static registry for built-in eval families."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

FAMILY_REGISTRY_VERSION = "2"


@dataclass(frozen=True)
class EvalFamilyMetadata:
    family_id: str
    observation_schema: str
    report_writer: str
    capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_FAMILIES: tuple[EvalFamilyMetadata, ...] = (
    EvalFamilyMetadata(
        family_id="tool_selection",
        observation_schema="ToolSelectionObservation",
        report_writer="build_tool_selection_report",
        capabilities=("selection", "routing"),
    ),
    EvalFamilyMetadata(
        family_id="tool_result_usage",
        observation_schema="ToolResultUsageObservation",
        report_writer="build_tool_result_usage_report",
        capabilities=("tool_output", "grounding"),
    ),
    EvalFamilyMetadata(
        family_id="freshness",
        observation_schema="FreshnessObservation",
        report_writer="build_freshness_report",
        capabilities=("freshness",),
    ),
    EvalFamilyMetadata(
        family_id="routing",
        observation_schema="RoutingObservation",
        report_writer="build_routing_report",
        capabilities=("routing",),
    ),
    EvalFamilyMetadata(
        family_id="closure",
        observation_schema="ClosureObservation",
        report_writer="build_closure_report",
        capabilities=("closure",),
    ),
    EvalFamilyMetadata(
        family_id="policy",
        observation_schema="PolicyObservation",
        report_writer="build_policy_report",
        capabilities=("policy",),
    ),
    EvalFamilyMetadata(
        family_id="skills",
        observation_schema="SkillQualityScenarioReport",
        report_writer="write_skill_quality_report",
        capabilities=("skills", "quality"),
    ),
    EvalFamilyMetadata(
        family_id="runtime_reliability",
        observation_schema="RuntimeReliabilityObservation",
        report_writer="build_runtime_reliability_report",
        capabilities=(
            "project_lifecycle",
            "dependency_readiness",
            "invocation_lifecycle",
            "remote_transport",
            "infrastructure_monitoring",
        ),
    ),
    EvalFamilyMetadata(
        family_id="goal_trajectory",
        observation_schema="GoalTrajectoryStep",
        report_writer="run_benchmark",
        capabilities=("goals", "drift", "long_horizon"),
    ),
    EvalFamilyMetadata(
        family_id="memory_effectiveness",
        observation_schema="MemoryEffectivenessTrace",
        report_writer="build_memory_scorecard",
        capabilities=("memory", "retrieval", "citation"),
    ),
    EvalFamilyMetadata(
        family_id="memory_context",
        observation_schema="AblationOutcome",
        report_writer="build_memory_context_scorecard",
        capabilities=("memory", "context", "ablation", "governance"),
    ),
    EvalFamilyMetadata(
        family_id="delegated_memory",
        observation_schema="DelegatedMemoryEvalTrace",
        report_writer="build_delegated_memory_scorecard",
        capabilities=("memory", "delegation", "isolation", "revocation"),
    ),
)


def list_builtin_families() -> tuple[EvalFamilyMetadata, ...]:
    return BUILTIN_FAMILIES


def get_builtin_family(family_id: str) -> EvalFamilyMetadata:
    for family in BUILTIN_FAMILIES:
        if family.family_id == family_id:
            return family
    raise KeyError(f"unknown eval family: {family_id}")
