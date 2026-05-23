"""Freshness eval family using typed obligation labels and runtime trace facts."""

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
class FreshnessObservation:
    classified_freshness_sensitive: bool
    live_lookup_performed: bool
    evidence_attached: bool
    exact_date_in_answer: bool
    unsupported_current_claim: bool


@dataclass(frozen=True)
class FreshnessCase:
    case_id: str
    prompt: str
    requires_freshness: bool
    requires_exact_date: bool = False
    requires_source_grounding: bool = False


FreshnessReport = FamilyEvalReport


def load_freshness_cases(path: str | Path) -> tuple[FreshnessCase, ...]:
    payload = load_versioned_json_fixture(path)
    cases: list[FreshnessCase] = []
    seen_ids: set[str] = set()
    for item in payload.get("cases", []):
        case_id = str(item.get("case_id", "") or "").strip()
        if not case_id or case_id in seen_ids:
            raise ValueError(f"invalid or duplicate freshness case_id: {case_id!r}")
        seen_ids.add(case_id)
        cases.append(
            FreshnessCase(
                case_id=case_id,
                prompt=str(item.get("prompt", "") or "").strip(),
                requires_freshness=bool(item.get("requires_freshness", False)),
                requires_exact_date=bool(item.get("requires_exact_date", False)),
                requires_source_grounding=bool(
                    item.get("requires_source_grounding", False)
                ),
            )
        )
    return tuple(cases)


def evaluate_freshness_case(
    case: FreshnessCase,
    observation: FreshnessObservation,
) -> FamilyEvalCaseResult:
    obligation_match = (
        observation.classified_freshness_sensitive == case.requires_freshness
    )
    compliance = (not case.requires_freshness) or observation.live_lookup_performed
    grounded = (not case.requires_source_grounding) or observation.evidence_attached
    exact_date_ok = (not case.requires_exact_date) or observation.exact_date_in_answer
    stale_leak = bool(case.requires_freshness and observation.unsupported_current_claim)
    passed = (
        obligation_match
        and compliance
        and grounded
        and exact_date_ok
        and not stale_leak
    )
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "obligation_match": obligation_match,
            "freshness_compliance": compliance,
            "grounded": grounded,
            "exact_date_ok": exact_date_ok,
            "stale_answer_leak": stale_leak,
        },
    )


def build_freshness_report(
    *,
    cases: tuple[FreshnessCase, ...],
    observations: dict[str, FreshnessObservation],
) -> FreshnessReport:
    results = tuple(
        evaluate_freshness_case(case, observations[case.case_id]) for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics={
            "obligation_match_count": sum(
                1 for r in results if bool(r.metrics["obligation_match"])
            ),
            "freshness_compliance_count": sum(
                1 for r in results if bool(r.metrics["freshness_compliance"])
            ),
            "grounded_count": sum(1 for r in results if bool(r.metrics["grounded"])),
            "stale_answer_leak_count": sum(
                1 for r in results if bool(r.metrics["stale_answer_leak"])
            ),
        },
    )
    return FreshnessReport(
        report_version="1",
        generated_at=utc_now_iso(),
        family_id="freshness",
        cases=results,
        summary=summary,
    )


def write_freshness_report(path: str | Path, report: FreshnessReport) -> Path:
    return write_json_report(path, report)
