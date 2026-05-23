"""Tool-result usage eval family."""

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
class ToolResultUsageObservation:
    cited_facts: tuple[str, ...]
    unsupported_claims: tuple[str, ...]


@dataclass(frozen=True)
class ToolResultUsageCase:
    case_id: str
    prompt: str
    required_facts: tuple[str, ...]
    forbidden_claims: tuple[str, ...] = ()


ToolResultUsageReport = FamilyEvalReport


def load_tool_result_usage_cases(path: str | Path) -> tuple[ToolResultUsageCase, ...]:
    payload = load_versioned_json_fixture(path)
    cases: list[ToolResultUsageCase] = []
    seen_ids: set[str] = set()
    for item in payload.get("cases", []):
        case_id = str(item.get("case_id", "") or "").strip()
        if not case_id or case_id in seen_ids:
            raise ValueError(f"invalid or duplicate tool-result case_id: {case_id!r}")
        seen_ids.add(case_id)
        cases.append(
            ToolResultUsageCase(
                case_id=case_id,
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
            )
        )
    return tuple(cases)


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
    unsupported_clean = not forbidden_hits and not unsupported
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
) -> ToolResultUsageReport:
    results = tuple(
        evaluate_tool_result_usage_case(case, observations[case.case_id])
        for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics={
            "grounded_count": sum(
                1 for result in results if bool(result.metrics["grounded"])
            ),
            "unsupported_clean_count": sum(
                1 for result in results if bool(result.metrics["unsupported_clean"])
            ),
            "unsupported_claim_case_count": sum(
                1 for result in results if bool(result.metrics["unsupported_claims"])
            ),
        },
    )
    return ToolResultUsageReport(
        report_version="1",
        generated_at=utc_now_iso(),
        family_id="tools.result_usage",
        cases=results,
        summary=summary,
    )


def write_tool_result_usage_report(
    path: str | Path, report: ToolResultUsageReport
) -> Path:
    return write_json_report(path, report)
