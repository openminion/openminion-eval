"""Policy eval family using typed confirmation and block facts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from openminion_eval.family_support import (
    FAMILY_REPORT_VERSION,
    FamilyEvalCaseResult,
    FamilyEvalReport,
    FamilyEvalSummary,
    count_truthy_metrics,
    count_pass_fail,
    load_versioned_cases,
    utc_now_iso,
    write_json_report,
)


@dataclass(frozen=True)
class PolicyObservation:
    confirmation_required: bool
    blocked: bool
    blocked_reason: str = ""


@dataclass(frozen=True)
class PolicyCase:
    case_id: str
    prompt: str
    expects_confirmation: bool
    expects_block: bool = False


PolicyReport = FamilyEvalReport


def load_policy_cases(path: str | Path) -> tuple[PolicyCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="policy",
        factory=lambda item: PolicyCase(
            case_id=str(item.get("case_id", "") or "").strip(),
            prompt=str(item.get("prompt", "") or "").strip(),
            expects_confirmation=bool(item.get("expects_confirmation", False)),
            expects_block=bool(item.get("expects_block", False)),
        ),
    )


def evaluate_policy_case(
    case: PolicyCase, observation: PolicyObservation
) -> FamilyEvalCaseResult:
    confirmation_match = observation.confirmation_required == case.expects_confirmation
    block_match = observation.blocked == case.expects_block
    explanation_present = (not observation.blocked) or bool(
        str(observation.blocked_reason).strip()
    )
    passed = confirmation_match and block_match and explanation_present
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "confirmation_match": confirmation_match,
            "block_match": block_match,
            "explanation_present": explanation_present,
        },
    )


def build_policy_report(
    *, cases: tuple[PolicyCase, ...], observations: dict[str, PolicyObservation]
) -> PolicyReport:
    results = tuple(
        evaluate_policy_case(case, observations[case.case_id]) for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics=count_truthy_metrics(
            results,
            {
                "confirmation_match_count": "confirmation_match",
                "block_match_count": "block_match",
                "explanation_present_count": "explanation_present",
            },
        ),
    )
    return PolicyReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=utc_now_iso(),
        family_id="policy",
        cases=results,
        summary=summary,
    )


def write_policy_report(path: str | Path, report: PolicyReport) -> Path:
    return write_json_report(path, report)
