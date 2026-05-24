"""Tool-selection eval family."""

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
class ToolSelectionObservation:
    selected_family: str | None
    selected_families: tuple[str, ...]


@dataclass(frozen=True)
class ToolSelectionCase:
    case_id: str
    prompt: str
    expected_family: str
    allowed_no_tool: bool = False
    forbidden_families: tuple[str, ...] = ()


ToolSelectionReport = FamilyEvalReport


def load_tool_selection_cases(path: str | Path) -> tuple[ToolSelectionCase, ...]:
    return load_versioned_cases(
        path,
        case_key="cases",
        family_label="tool-selection",
        factory=lambda item: ToolSelectionCase(
            case_id=str(item.get("case_id", "") or "").strip(),
            prompt=str(item.get("prompt", "") or "").strip(),
            expected_family=str(item.get("expected_family", "") or "").strip(),
            allowed_no_tool=bool(item.get("allowed_no_tool", False)),
            forbidden_families=tuple(
                str(value).strip()
                for value in item.get("forbidden_families", [])
                if str(value).strip()
            ),
        ),
    )


def evaluate_tool_selection_case(
    case: ToolSelectionCase,
    observation: ToolSelectionObservation,
) -> FamilyEvalCaseResult:
    selected_family = str(observation.selected_family or "").strip()
    selected_families = tuple(
        str(value).strip()
        for value in observation.selected_families
        if str(value).strip()
    )
    has_tool = bool(selected_family or selected_families)
    chosen_family = selected_family or (
        selected_families[0] if selected_families else ""
    )
    correct_family = chosen_family == case.expected_family
    unnecessary_tool = bool(case.allowed_no_tool and has_tool)
    missing_tool = bool((not case.allowed_no_tool) and not has_tool)
    forbidden_hit = any(
        family in selected_families for family in case.forbidden_families
    )
    passed = bool(
        correct_family
        and not unnecessary_tool
        and not missing_tool
        and not forbidden_hit
    )
    return FamilyEvalCaseResult(
        case_id=case.case_id,
        passed=passed,
        metrics={
            "expected_family": case.expected_family,
            "selected_family": chosen_family,
            "correct_family": correct_family,
            "unnecessary_tool": unnecessary_tool,
            "missing_tool": missing_tool,
            "forbidden_family_hit": forbidden_hit,
        },
    )


def build_tool_selection_report(
    *,
    cases: tuple[ToolSelectionCase, ...],
    observations: dict[str, ToolSelectionObservation],
) -> ToolSelectionReport:
    results = tuple(
        evaluate_tool_selection_case(case, observations[case.case_id]) for case in cases
    )
    passed_count, failed_count = count_pass_fail(results)
    summary = FamilyEvalSummary(
        case_count=len(results),
        passed_count=passed_count,
        failed_count=failed_count,
        metrics={
            "correct_family_count": sum(
                1
                for case, result in zip(cases, results)
                if case.expected_family and bool(result.metrics["correct_family"])
            ),
            **count_truthy_metrics(
                results,
                {
                    "unnecessary_tool_count": "unnecessary_tool",
                    "missing_tool_count": "missing_tool",
                    "forbidden_family_hit_count": "forbidden_family_hit",
                },
            ),
        },
    )
    return ToolSelectionReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=utc_now_iso(),
        family_id="tools.selection",
        cases=results,
        summary=summary,
    )


def write_tool_selection_report(path: str | Path, report: ToolSelectionReport) -> Path:
    return write_json_report(path, report)
