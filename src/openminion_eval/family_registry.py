"""Static registry for built-in eval families."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

FAMILY_REGISTRY_VERSION = "1"


@dataclass(frozen=True)
class EvalFamilyMetadata:
    family_id: str
    fixture_name: str
    observation_schema: str
    report_writer: str
    capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


BUILTIN_FAMILIES: tuple[EvalFamilyMetadata, ...] = (
    EvalFamilyMetadata(
        family_id="tool_selection",
        fixture_name="tool_selection_cases.json",
        observation_schema="ToolSelectionObservation",
        report_writer="build_tool_selection_report",
        capabilities=("selection", "routing"),
    ),
    EvalFamilyMetadata(
        family_id="tool_result_usage",
        fixture_name="tool_result_usage_cases.json",
        observation_schema="ToolResultUsageObservation",
        report_writer="build_tool_result_usage_report",
        capabilities=("tool_output", "grounding"),
    ),
    EvalFamilyMetadata(
        family_id="freshness",
        fixture_name="cases.json",
        observation_schema="FreshnessObservation",
        report_writer="build_freshness_report",
        capabilities=("freshness",),
    ),
    EvalFamilyMetadata(
        family_id="routing",
        fixture_name="cases.json",
        observation_schema="RoutingObservation",
        report_writer="build_routing_report",
        capabilities=("routing",),
    ),
    EvalFamilyMetadata(
        family_id="closure",
        fixture_name="cases.json",
        observation_schema="ClosureObservation",
        report_writer="build_closure_report",
        capabilities=("closure",),
    ),
    EvalFamilyMetadata(
        family_id="policy",
        fixture_name="cases.json",
        observation_schema="PolicyObservation",
        report_writer="build_policy_report",
        capabilities=("policy",),
    ),
    EvalFamilyMetadata(
        family_id="skills",
        fixture_name="manifest.json",
        observation_schema="SkillQualityScenarioReport",
        report_writer="write_skill_quality_report",
        capabilities=("skills", "quality"),
    ),
)


def list_builtin_families() -> tuple[EvalFamilyMetadata, ...]:
    return BUILTIN_FAMILIES


def get_builtin_family(family_id: str) -> EvalFamilyMetadata:
    for family in BUILTIN_FAMILIES:
        if family.family_id == family_id:
            return family
    raise KeyError(f"unknown eval family: {family_id}")
