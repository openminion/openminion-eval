"""Deterministic memory-effectiveness scorers."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

from openminion_eval.memory_effectiveness.schemas import (
    MemoryComponent,
    MemoryComponentScore,
    MemoryEffectivenessCase,
    MemoryEffectivenessCaseResult,
    MemoryEffectivenessScorecard,
    MemoryEffectivenessTrace,
    MemoryPairedRunComparison,
)

SCORECARD_VERSION = "1"
_COMPONENTS: tuple[MemoryComponent, ...] = (
    "save",
    "retrieval",
    "usage",
    "longitudinal",
)


def score_memory_case(
    case: MemoryEffectivenessCase,
    trace: MemoryEffectivenessTrace,
) -> MemoryEffectivenessCaseResult:
    if case.case_id != trace.case_id:
        raise ValueError(
            f"trace case_id {trace.case_id!r} does not match case {case.case_id!r}"
        )

    expectation = case.expectations
    critical_failures: list[str] = []

    save = _score_required(
        "save", expectation.required_saved_ids, trace.saved_memory_ids
    )
    retrieval = _score_required(
        "retrieval",
        expectation.required_retrieved_ids,
        trace.retrieved_memory_ids,
    )
    usage_expected = tuple(
        sorted(
            set(expectation.required_used_ids)
            | set(expectation.required_claim_memory_ids)
            | set(expectation.required_tool_memory_ids)
        )
    )
    usage_seen = tuple(
        sorted(
            set(trace.used_memory_ids)
            | {claim.memory_id for claim in trace.supporting_claims}
            | {
                memory_id
                for tool_call in trace.tool_calls
                for memory_id in tool_call.memory_ids
            }
        )
    )
    usage = _score_required("usage", usage_expected, usage_seen)
    longitudinal = _score_longitudinal(case, trace)

    forbidden_seen = _seen_forbidden_ids(case, trace)
    if forbidden_seen:
        critical_failures.append(
            "forbidden_memory_used:" + ",".join(sorted(forbidden_seen))
        )
    if (
        expectation.expected_namespace
        and trace.namespace != expectation.expected_namespace
    ):
        critical_failures.append(f"namespace_mismatch:{trace.namespace or '<empty>'}")
    if expectation.expect_no_memory_claim and usage_seen:
        critical_failures.append(
            "hallucinated_memory_claim:" + ",".join(sorted(usage_seen))
        )
    if expectation.critical:
        for score in (save, retrieval, usage, longitudinal):
            critical_failures.extend(score.failures)
    if trace.memory_mode == "disabled" and (
        trace.saved_memory_ids or trace.retrieved_memory_ids or usage_seen
    ):
        critical_failures.append("disabled_run_contains_memory_trace")

    component_failures = tuple(
        failure
        for score in (save, retrieval, usage, longitudinal)
        for failure in score.failures
    )
    component_scores = (save, retrieval, usage, longitudinal)
    status = (
        "passed"
        if all(score.score == 1.0 for score in component_scores)
        and not critical_failures
        else "failed"
    )
    return MemoryEffectivenessCaseResult(
        case_id=case.case_id,
        status=status,
        component_scores=component_scores,
        critical_failures=tuple(critical_failures),
        diagnostics=component_failures + tuple(trace.diagnostics),
    )


def build_memory_scorecard(
    *,
    suite_id: str,
    run_id: str,
    case_results: Iterable[MemoryEffectivenessCaseResult],
    metadata: dict | None = None,
) -> MemoryEffectivenessScorecard:
    cases = tuple(case_results)
    component_scores = tuple(
        _aggregate_component(component, cases) for component in _COMPONENTS
    )
    overall = sum(case.overall_score for case in cases) / len(cases) if cases else 0.0
    critical = tuple(failure for case in cases for failure in case.critical_failures)
    if critical:
        overall = min(overall, 0.99)
    return MemoryEffectivenessScorecard(
        suite_id=suite_id,
        run_id=run_id,
        cases=cases,
        component_scores=component_scores,
        overall_score=round(overall, 6),
        critical_failures=critical,
        metadata=dict(metadata or {}),
    )


def compare_memory_scorecards(
    disabled: MemoryEffectivenessScorecard,
    enabled: MemoryEffectivenessScorecard,
) -> tuple[MemoryPairedRunComparison, ...]:
    disabled_by_case = {case.case_id: case for case in disabled.cases}
    enabled_by_case = {case.case_id: case for case in enabled.cases}
    comparisons: list[MemoryPairedRunComparison] = []
    for case_id in sorted(disabled_by_case.keys() | enabled_by_case.keys()):
        disabled_score = (
            disabled_by_case[case_id].overall_score
            if case_id in disabled_by_case
            else 0.0
        )
        enabled_score = (
            enabled_by_case[case_id].overall_score
            if case_id in enabled_by_case
            else 0.0
        )
        critical = tuple(
            enabled_by_case.get(case_id, _empty_result(case_id)).critical_failures
        )
        delta = round(enabled_score - disabled_score, 6)
        comparisons.append(
            MemoryPairedRunComparison(
                case_id=case_id,
                disabled_score=round(disabled_score, 6),
                enabled_score=round(enabled_score, 6),
                delta=delta,
                improved=delta > 0 and not critical,
                critical_failures=critical,
            )
        )
    return tuple(comparisons)


def write_memory_scorecard(
    path: str | Path,
    scorecard: MemoryEffectivenessScorecard,
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_version": SCORECARD_VERSION,
        "scorecard": asdict(scorecard),
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_memory_scorecard(path: str | Path) -> MemoryEffectivenessScorecard:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = payload.get("artifact_version")
    if version != SCORECARD_VERSION:
        raise ValueError(f"unsupported memory scorecard version: {version!r}")
    return _scorecard_from_dict(payload["scorecard"])


def _score_required(
    component: MemoryComponent,
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> MemoryComponentScore:
    if not expected:
        return MemoryComponentScore(component=component, passed=1, total=1, score=1.0)
    observed_set = set(observed)
    missing = tuple(item for item in expected if item not in observed_set)
    passed = len(expected) - len(missing)
    return MemoryComponentScore(
        component=component,
        passed=passed,
        total=len(expected),
        score=round(passed / len(expected), 6),
        failures=tuple(f"{component}_missing:{item}" for item in missing),
    )


def _score_longitudinal(
    case: MemoryEffectivenessCase,
    trace: MemoryEffectivenessTrace,
) -> MemoryComponentScore:
    if not case.expectations.requires_longitudinal_improvement:
        return MemoryComponentScore(
            component="longitudinal", passed=1, total=1, score=1.0
        )
    passed = int("correction_adopted" in trace.diagnostics or trace.used_memory_ids)
    return MemoryComponentScore(
        component="longitudinal",
        passed=passed,
        total=1,
        score=float(passed),
        failures=() if passed else ("longitudinal_missing:correction_adoption",),
    )


def _seen_forbidden_ids(
    case: MemoryEffectivenessCase,
    trace: MemoryEffectivenessTrace,
) -> set[str]:
    observed = (
        set(trace.saved_memory_ids)
        | set(trace.retrieved_memory_ids)
        | set(trace.used_memory_ids)
        | {claim.memory_id for claim in trace.supporting_claims}
        | {
            memory_id
            for tool_call in trace.tool_calls
            for memory_id in tool_call.memory_ids
        }
    )
    return observed.intersection(case.expectations.forbidden_memory_ids)


def _aggregate_component(
    component: MemoryComponent,
    cases: tuple[MemoryEffectivenessCaseResult, ...],
) -> MemoryComponentScore:
    component_items = [
        score
        for case in cases
        for score in case.component_scores
        if score.component == component
    ]
    total = sum(score.total for score in component_items)
    passed = sum(score.passed for score in component_items)
    failures = tuple(failure for score in component_items for failure in score.failures)
    return MemoryComponentScore(
        component=component,
        passed=passed,
        total=total,
        score=round(passed / total, 6) if total else 0.0,
        failures=failures,
    )


def _empty_result(case_id: str) -> MemoryEffectivenessCaseResult:
    return MemoryEffectivenessCaseResult(
        case_id=case_id,
        status="unsupported_by_design",
        component_scores=tuple(
            MemoryComponentScore(component=component, passed=0, total=1, score=0.0)
            for component in _COMPONENTS
        ),
    )


def _scorecard_from_dict(data: dict) -> MemoryEffectivenessScorecard:
    return MemoryEffectivenessScorecard(
        suite_id=data["suite_id"],
        run_id=data["run_id"],
        cases=tuple(_case_result_from_dict(item) for item in data["cases"]),
        component_scores=tuple(
            MemoryComponentScore(**item) for item in data["component_scores"]
        ),
        overall_score=float(data["overall_score"]),
        critical_failures=tuple(data.get("critical_failures", ())),
        metadata=dict(data.get("metadata", {})),
    )


def _case_result_from_dict(data: dict) -> MemoryEffectivenessCaseResult:
    return MemoryEffectivenessCaseResult(
        case_id=data["case_id"],
        status=data["status"],
        component_scores=tuple(
            MemoryComponentScore(**item) for item in data["component_scores"]
        ),
        critical_failures=tuple(data.get("critical_failures", ())),
        diagnostics=tuple(data.get("diagnostics", ())),
    )
