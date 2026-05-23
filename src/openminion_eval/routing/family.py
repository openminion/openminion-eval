"""Routing eval family using typed mode outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openminion_eval.family_support import (
    FamilyEvalCaseResult,
    FamilyEvalReport,
    FamilyEvalSummary,
    count_pass_fail,
    load_versioned_json_fixture,
    utc_now_iso,
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
    payload = load_versioned_json_fixture(path)
    cases: list[RoutingCase] = []
    seen_ids: set[str] = set()
    for item in payload.get("cases", []):
        case_id = str(item.get("case_id", "") or "").strip()
        if not case_id or case_id in seen_ids:
            raise ValueError(f"invalid or duplicate routing case_id: {case_id!r}")
        seen_ids.add(case_id)
        cases.append(
            RoutingCase(
                case_id=case_id,
                prompt=str(item.get("prompt", "") or "").strip(),
                expected_mode=str(item.get("expected_mode", "") or "").strip(),
            )
        )
    return tuple(cases)


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
    *, cases: tuple[RoutingCase, ...], observations: dict[str, RoutingObservation]
) -> RoutingReport:
    results = tuple(
        evaluate_routing_case(case, observations[case.case_id]) for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics={
            "routing_match_count": sum(
                1 for r in results if bool(r.metrics["routing_match"])
            ),
            "over_clarified_count": sum(
                1 for r in results if bool(r.metrics["over_clarified"])
            ),
            "over_delegated_count": sum(
                1 for r in results if bool(r.metrics["over_delegated"])
            ),
            "missed_decompose_count": sum(
                1 for r in results if bool(r.metrics["missed_decompose"])
            ),
        },
    )
    return RoutingReport(
        report_version="1",
        generated_at=utc_now_iso(),
        family_id="routing",
        cases=results,
        summary=summary,
    )


def write_routing_report(path: str | Path, report: RoutingReport) -> Path:
    return write_json_report(path, report)
