"""Closure eval family using typed closure outcomes."""

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
class ClosureObservation:
    closure_action: str
    answer_complete: bool
    unnecessary_followup: bool = False


@dataclass(frozen=True)
class ClosureCase:
    case_id: str
    prompt: str
    expected_action: str


ClosureReport = FamilyEvalReport


def load_closure_cases(path: str | Path) -> tuple[ClosureCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="closure",
        factory=lambda item: ClosureCase(
            case_id=str(item.get("case_id", "") or "").strip(),
            prompt=str(item.get("prompt", "") or "").strip(),
            expected_action=str(item.get("expected_action", "") or "").strip(),
        ),
    )


def evaluate_closure_case(
    case: ClosureCase, observation: ClosureObservation
) -> FamilyEvalCaseResult:
    action_match = observation.closure_action == case.expected_action
    passed = (
        action_match
        and observation.answer_complete
        and not observation.unnecessary_followup
    )
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "action_match": action_match,
            "answer_complete": observation.answer_complete,
            "unnecessary_followup": observation.unnecessary_followup,
        },
    )


def build_closure_report(
    *, cases: tuple[ClosureCase, ...], observations: dict[str, ClosureObservation]
) -> ClosureReport:
    results = tuple(
        evaluate_closure_case(case, observations[case.case_id]) for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics=count_truthy_metrics(
            results,
            {
                "action_match_count": "action_match",
                "answer_complete_count": "answer_complete",
                "unnecessary_followup_count": "unnecessary_followup",
            },
        ),
    )
    return ClosureReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=utc_now_iso(),
        family_id="closure",
        cases=results,
        summary=summary,
    )


def write_closure_report(path: str | Path, report: ClosureReport) -> Path:
    return write_json_report(path, report)
