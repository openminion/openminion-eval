"""Routing eval family using typed mode outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from openminion_eval.family_support import (
    FAMILY_REPORT_VERSION,
    FamilyEvalCaseResult,
    FamilyEvalReport,
    FamilyEvalSummary,
    OnMissingObservation,
    build_family_results,
    count_truthy_metrics,
    count_pass_fail,
    load_versioned_cases,
    report_generated_at,
    write_json_report,
)


@dataclass(frozen=True)
class RoutingObservation:
    observed_mode: str
    over_clarified: bool = False
    over_delegated: bool = False
    missed_decompose: bool = False


@dataclass(frozen=True)
class RoutingCase:
    case_id: str
    prompt: str
    expected_mode: str


RoutingReport = FamilyEvalReport


def load_routing_cases(path: str | Path) -> tuple[RoutingCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="routing",
        factory=lambda item: RoutingCase(
            case_id=str(item.get("case_id", "") or "").strip(),
            prompt=str(item.get("prompt", "") or "").strip(),
            expected_mode=str(item.get("expected_mode", "") or "").strip(),
        ),
    )


def evaluate_routing_case(
    case: RoutingCase, observation: RoutingObservation
) -> FamilyEvalCaseResult:
    routing_match = observation.observed_mode == case.expected_mode
    passed = (
        routing_match
        and not observation.over_clarified
        and not observation.over_delegated
        and not observation.missed_decompose
    )
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "routing_match": routing_match,
            "over_clarified": observation.over_clarified,
            "over_delegated": observation.over_delegated,
            "missed_decompose": observation.missed_decompose,
        },
    )


def build_routing_report(
    *,
    cases: tuple[RoutingCase, ...],
    observations: dict[str, RoutingObservation],
    on_missing: OnMissingObservation = "raise",
    now_provider: Callable[[], str] = report_generated_at,
) -> RoutingReport:
    results = build_family_results(
        cases,
        observations,
        evaluate_routing_case,
        family_label="routing",
        on_missing=on_missing,
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics=count_truthy_metrics(
            results,
            {
                "routing_match_count": "routing_match",
                "over_clarified_count": "over_clarified",
                "over_delegated_count": "over_delegated",
                "missed_decompose_count": "missed_decompose",
            },
        ),
    )
    return RoutingReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=now_provider(),
        family_id="routing",
        cases=results,
        summary=summary,
    )


def write_routing_report(path: str | Path, report: RoutingReport) -> Path:
    return write_json_report(path, report)
