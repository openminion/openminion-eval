"""Runtime reliability evals over explicit host facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal, Mapping, cast

from openminion_eval.family_support import (
    FAMILY_REPORT_VERSION,
    FamilyEvalCaseResult,
    FamilyEvalReport,
    FamilyEvalSummary,
    OnMissingObservation,
    build_family_results,
    count_pass_fail,
    load_versioned_cases,
    report_generated_at,
    write_json_report,
)


RuntimeCapability = Literal[
    "project_lifecycle",
    "dependency_readiness",
    "invocation_lifecycle",
    "remote_transport",
    "infrastructure_monitoring",
]


@dataclass(frozen=True)
class RuntimeReliabilityCase:
    case_id: str
    capability: RuntimeCapability
    expected_facts: dict[str, Any]
    required_identifiers: tuple[str, ...] = ()


@dataclass(frozen=True)
class RuntimeReliabilityObservation:
    facts: dict[str, Any]
    identifiers: dict[str, str] = field(default_factory=dict)


RuntimeReliabilityReport = FamilyEvalReport


def load_runtime_reliability_cases(
    path: str | Path,
) -> tuple[RuntimeReliabilityCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="runtime reliability",
        factory=_case_from_mapping,
    )


def evaluate_runtime_reliability_case(
    case: RuntimeReliabilityCase,
    observation: RuntimeReliabilityObservation,
) -> FamilyEvalCaseResult:
    mismatched = tuple(
        key
        for key, expected in case.expected_facts.items()
        if key not in observation.facts or observation.facts[key] != expected
    )
    missing_identifiers = tuple(
        key
        for key in case.required_identifiers
        if not str(observation.identifiers.get(key, "")).strip()
    )
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=not mismatched and not missing_identifiers,
        metrics={
            "capability": case.capability,
            "fact_match": not mismatched,
            "identifiers_present": not missing_identifiers,
            "mismatched_fact_count": len(mismatched),
            "missing_identifier_count": len(missing_identifiers),
        },
    )


def build_runtime_reliability_report(
    *,
    cases: tuple[RuntimeReliabilityCase, ...],
    observations: Mapping[str, RuntimeReliabilityObservation],
    on_missing: OnMissingObservation = "raise",
    now_provider: Callable[[], str] = report_generated_at,
) -> RuntimeReliabilityReport:
    results = build_family_results(
        cases,
        observations,
        evaluate_runtime_reliability_case,
        family_label="runtime reliability",
        on_missing=on_missing,
    )
    passed_count, failed_count = count_pass_fail(results)
    return RuntimeReliabilityReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=now_provider(),
        family_id="runtime_reliability",
        cases=results,
        summary=FamilyEvalSummary(
            case_count=len(results),
            passed_count=passed_count,
            failed_count=failed_count,
            metrics={
                "fact_match_count": sum(
                    bool(result.metrics.get("fact_match")) for result in results
                ),
                "identifier_complete_count": sum(
                    bool(result.metrics.get("identifiers_present"))
                    for result in results
                ),
            },
        ),
    )


def write_runtime_reliability_report(
    path: str | Path,
    report: RuntimeReliabilityReport,
) -> Path:
    return write_json_report(path, report)


def _case_from_mapping(item: Mapping[str, Any]) -> RuntimeReliabilityCase:
    expected_facts = item.get("expected_facts")
    if not isinstance(expected_facts, dict):
        raise ValueError("runtime reliability expected_facts must be a mapping")
    required_identifiers = item.get("required_identifiers", [])
    if not isinstance(required_identifiers, list) or not all(
        isinstance(value, str) for value in required_identifiers
    ):
        raise ValueError(
            "runtime reliability required_identifiers must be a list of strings"
        )
    capability = str(item.get("capability", ""))
    allowed = {
        "project_lifecycle",
        "dependency_readiness",
        "invocation_lifecycle",
        "remote_transport",
        "infrastructure_monitoring",
    }
    if capability not in allowed:
        raise ValueError(f"unsupported runtime reliability capability: {capability!r}")
    return RuntimeReliabilityCase(
        case_id=str(item.get("case_id", "")).strip(),
        capability=cast(RuntimeCapability, capability),
        expected_facts=dict(expected_facts),
        required_identifiers=tuple(required_identifiers),
    )
