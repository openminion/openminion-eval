"""Tool-result usage eval family."""

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
class ToolResultUsageObservation:
    cited_facts: tuple[str, ...]
    unsupported_claims: tuple[str, ...]


@dataclass(frozen=True)
class ToolResultUsageCase:
    """Required grounding facts with selective forbidden-claim enforcement."""

    case_id: str
    prompt: str
    required_facts: tuple[str, ...]
    forbidden_claims: tuple[str, ...] = ()


ToolResultUsageReport = FamilyEvalReport


def load_tool_result_usage_cases(path: str | Path) -> tuple[ToolResultUsageCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="tool-result",
        factory=lambda item: ToolResultUsageCase(
            case_id=str(item.get("case_id", "") or "").strip(),
            prompt=str(item.get("prompt", "") or "").strip(),
            required_facts=tuple(
                str(value).strip()
                for value in item.get("required_facts", [])
                if str(value).strip()
            ),
            forbidden_claims=tuple(
                str(value).strip()
                for value in item.get("forbidden_claims", [])
                if str(value).strip()
            ),
        ),
    )


def evaluate_tool_result_usage_case(
    case: ToolResultUsageCase,
    observation: ToolResultUsageObservation,
) -> FamilyEvalCaseResult:
    cited = {
        str(value).strip() for value in observation.cited_facts if str(value).strip()
    }
    unsupported = {
        str(value).strip()
        for value in observation.unsupported_claims
        if str(value).strip()
    }
    required = {value for value in case.required_facts if value}
    forbidden = {value for value in case.forbidden_claims if value}
    missing_facts = tuple(sorted(required - cited))
    forbidden_hits = tuple(sorted(forbidden & unsupported))
    grounded = not missing_facts
    unsupported_clean = not forbidden_hits
    passed = grounded and unsupported_clean
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "required_fact_count": len(required),
            "cited_fact_count": len(cited),
            "missing_facts": missing_facts,
            "unsupported_claims": tuple(sorted(unsupported)),
            "forbidden_hits": forbidden_hits,
            "grounded": grounded,
            "unsupported_clean": unsupported_clean,
        },
    )


def build_tool_result_usage_report(
    *,
    cases: tuple[ToolResultUsageCase, ...],
    observations: dict[str, ToolResultUsageObservation],
    on_missing: OnMissingObservation = "raise",
    now_provider: Callable[[], str] = report_generated_at,
) -> ToolResultUsageReport:
    results = build_family_results(
        cases,
        observations,
        evaluate_tool_result_usage_case,
        family_label="tools.result_usage",
        on_missing=on_missing,
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics={
            **count_truthy_metrics(
                results,
                {
                    "grounded_count": "grounded",
                    "unsupported_clean_count": "unsupported_clean",
                },
            ),
            "unsupported_claim_case_count": sum(
                1
                for result in results
                if bool(result.metrics.get("unsupported_claims"))
            ),
        },
    )
    return ToolResultUsageReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=now_provider(),
        family_id="tools.result_usage",
        cases=results,
        summary=summary,
    )


def write_tool_result_usage_report(
    path: str | Path, report: ToolResultUsageReport
) -> Path:
    return write_json_report(path, report)
