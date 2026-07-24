"""Deterministic memory-effectiveness scorers."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any, Iterable

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
    component_scores = _score_components(case, trace)
    save, retrieval, usage, longitudinal = component_scores
    usage_seen = _usage_seen_ids(trace)
    operation = _expected_or_observed_operation(expectation, trace)
    memory_location = _expected_or_observed_memory_location(expectation, trace)
    retrieval_metrics = _retrieval_metrics(expectation, trace)
    overuse_penalty = _overuse_penalty(expectation, trace)
    underuse_penalty = _underuse_penalty(expectation, trace)
    critical_failures = _critical_failures(
        case=case,
        trace=trace,
        component_scores=component_scores,
        usage_seen=usage_seen,
        operation=operation,
        memory_location=memory_location,
        overuse_penalty=overuse_penalty,
        underuse_penalty=underuse_penalty,
    )

    component_failures = tuple(
        failure for score in component_scores for failure in score.failures
    )
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
        operation=operation,
        memory_location=memory_location,
        retrieval_metrics=retrieval_metrics,
        overuse_penalty=overuse_penalty,
        underuse_penalty=underuse_penalty,
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
    metadata_payload = dict(metadata or {})
    retrieval_metrics = _aggregate_metric_maps(
        tuple(case.retrieval_metrics for case in cases)
    )
    return MemoryEffectivenessScorecard(
        suite_id=suite_id,
        run_id=run_id,
        cases=cases,
        component_scores=component_scores,
        overall_score=round(overall, 6),
        critical_failures=critical,
        metadata=metadata_payload,
        operation_scores=_aggregate_case_scores(cases, "operation"),
        memory_location_scores=_aggregate_case_scores(cases, "memory_location"),
        retrieval_metrics=retrieval_metrics,
        overuse_penalties={
            case.case_id: case.overuse_penalty for case in cases if case.overuse_penalty
        },
        underuse_penalties={
            case.case_id: case.underuse_penalty
            for case in cases
            if case.underuse_penalty
        },
        efficiency_metadata=_efficiency_metadata(metadata_payload),
        baseline_trend=_baseline_trend(metadata_payload, round(overall, 6)),
        public_report_sections=_public_report_sections(
            overall=round(overall, 6),
            retrieval_metrics=retrieval_metrics,
            critical_failures=critical,
        ),
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


def _score_components(
    case: MemoryEffectivenessCase,
    trace: MemoryEffectivenessTrace,
) -> tuple[
    MemoryComponentScore,
    MemoryComponentScore,
    MemoryComponentScore,
    MemoryComponentScore,
]:
    expectation = case.expectations
    return (
        _score_required("save", expectation.required_saved_ids, trace.saved_memory_ids),
        _score_required(
            "retrieval",
            expectation.required_retrieved_ids,
            trace.retrieved_memory_ids,
        ),
        _score_required(
            "usage", _usage_expected_ids(expectation), _usage_seen_ids(trace)
        ),
        _score_longitudinal(case, trace),
    )


def _usage_expected_ids(expectation: object) -> tuple[str, ...]:
    return tuple(
        sorted(
            set(getattr(expectation, "required_used_ids", ()) or ())
            | set(getattr(expectation, "required_claim_memory_ids", ()) or ())
            | set(getattr(expectation, "required_tool_memory_ids", ()) or ())
        )
    )


def _usage_seen_ids(trace: MemoryEffectivenessTrace) -> tuple[str, ...]:
    return tuple(
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


def _critical_failures(
    *,
    case: MemoryEffectivenessCase,
    trace: MemoryEffectivenessTrace,
    component_scores: tuple[MemoryComponentScore, ...],
    usage_seen: tuple[str, ...],
    operation: str,
    memory_location: str,
    overuse_penalty: float,
    underuse_penalty: float,
) -> tuple[str, ...]:
    expectation = case.expectations
    failures: list[str] = []
    forbidden_seen = _seen_forbidden_ids(case, trace)
    if forbidden_seen:
        failures.append("forbidden_memory_used:" + ",".join(sorted(forbidden_seen)))
    if (
        expectation.expected_namespace
        and trace.namespace != expectation.expected_namespace
    ):
        failures.append(f"namespace_mismatch:{trace.namespace or '<empty>'}")
    if expectation.expect_no_memory_claim and usage_seen:
        failures.append("hallucinated_memory_claim:" + ",".join(sorted(usage_seen)))
    if expectation.critical:
        for score in component_scores:
            failures.extend(score.failures)
    if trace.memory_mode == "disabled" and (
        trace.saved_memory_ids or trace.retrieved_memory_ids or usage_seen
    ):
        failures.append("disabled_run_contains_memory_trace")
    if trace.redaction_status != "sanitized":
        failures.append(f"trace_not_sanitized:{trace.redaction_status}")
    if trace.private_trace_refs:
        failures.append(
            "private_trace_refs_present:" + ",".join(trace.private_trace_refs)
        )
    failures.extend(_structured_expectation_failures(expectation, trace))
    failures.extend(
        _critical_dimension_failures(
            expectation=expectation,
            operation=operation,
            memory_location=memory_location,
            overuse_penalty=overuse_penalty,
            underuse_penalty=underuse_penalty,
        )
    )
    return tuple(failures)


def _critical_dimension_failures(
    *,
    expectation: object,
    operation: str,
    memory_location: str,
    overuse_penalty: float,
    underuse_penalty: float,
) -> tuple[str, ...]:
    failures: list[str] = []
    if (
        getattr(expectation, "expected_operation", "")
        and operation
        and operation != getattr(expectation, "expected_operation")
    ):
        failures.append(f"operation_mismatch:{operation}")
    if (
        getattr(expectation, "expected_memory_location", "")
        and memory_location
        and memory_location != getattr(expectation, "expected_memory_location")
    ):
        failures.append(f"memory_location_mismatch:{memory_location}")
    if overuse_penalty:
        failures.append(f"memory_overuse:{overuse_penalty:g}")
    if underuse_penalty:
        failures.append(f"memory_underuse:{underuse_penalty:g}")
    return tuple(failures)


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


def _expected_or_observed_operation(
    expectation: object,
    trace: MemoryEffectivenessTrace,
) -> str:
    expected = str(getattr(expectation, "expected_operation", "") or "").strip()
    if expected:
        return expected
    for tool_call in trace.tool_calls:
        if tool_call.operation:
            return tool_call.operation
    return ""


def _expected_or_observed_memory_location(
    expectation: object,
    trace: MemoryEffectivenessTrace,
) -> str:
    expected = str(getattr(expectation, "expected_memory_location", "") or "").strip()
    if expected:
        return expected
    for tool_call in trace.tool_calls:
        if tool_call.memory_location:
            return tool_call.memory_location
    return ""


def _retrieval_metrics(
    expectation: object,
    trace: MemoryEffectivenessTrace,
) -> dict[str, float | int | None]:
    expected = tuple(getattr(expectation, "expected_retrieved_order", ()) or ())
    if not expected:
        expected = tuple(getattr(expectation, "required_retrieved_ids", ()) or ())
    observed = tuple(trace.retrieved_memory_ids)
    expected_set = set(expected)
    observed_set = set(observed)
    hit_count = len(expected_set.intersection(observed_set))
    retrieval_count = len(observed)
    expected_count = len(expected)
    first_rank = _first_expected_rank(expected, observed)
    context_order_score = _order_score(expected, trace.context_memory_ids or observed)
    cited = tuple(trace.cited_memory_ids)
    required_cited = set(getattr(expectation, "required_cited_memory_ids", ()) or ())
    cited_hits = len(required_cited.intersection(cited))
    citation_precision = (
        round(cited_hits / len(cited), 6)
        if cited
        else 1.0
        if not required_cited
        else 0.0
    )
    noise = max(0, retrieval_count - hit_count)
    return {
        "expected_count": expected_count,
        "retrieved_count": retrieval_count,
        "hit_count": hit_count,
        "recall_at_k": round(hit_count / expected_count, 6) if expected_count else 1.0,
        "precision_at_k": round(hit_count / retrieval_count, 6)
        if retrieval_count
        else 1.0
        if not expected_count
        else 0.0,
        "mrr": round(1 / first_rank, 6) if first_rank else 0.0,
        "expected_id_rank": first_rank,
        "context_order_score": context_order_score,
        "noise_sensitivity": round(1 - (noise / retrieval_count), 6)
        if retrieval_count
        else 1.0,
        "citation_precision": citation_precision,
    }


def _first_expected_rank(
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> int | None:
    expected_set = set(expected)
    for index, memory_id in enumerate(observed, start=1):
        if memory_id in expected_set:
            return index
    return None


def _order_score(
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> float:
    if not expected:
        return 1.0
    observed_expected = tuple(item for item in observed if item in set(expected))
    matches = sum(
        1
        for index, memory_id in enumerate(expected)
        if index < len(observed_expected) and observed_expected[index] == memory_id
    )
    return round(matches / len(expected), 6)


def _overuse_penalty(expectation: object, trace: MemoryEffectivenessTrace) -> float:
    max_unnecessary = getattr(expectation, "max_unnecessary_memory_calls", None)
    if max_unnecessary is None:
        return 0.0
    expected_ids = set(getattr(expectation, "required_retrieved_ids", ()) or ())
    expected_ids.update(getattr(expectation, "expected_retrieved_order", ()) or ())
    unnecessary = tuple(
        memory_id
        for memory_id in trace.retrieved_memory_ids
        if memory_id not in expected_ids
    )
    excess = max(0, len(unnecessary) - int(max_unnecessary))
    if not trace.retrieved_memory_ids:
        return 0.0
    return round(excess / len(trace.retrieved_memory_ids), 6)


def _underuse_penalty(expectation: object, trace: MemoryEffectivenessTrace) -> float:
    expected_ids = set(getattr(expectation, "required_used_ids", ()) or ())
    expected_ids.update(getattr(expectation, "required_claim_memory_ids", ()) or ())
    expected_ids.update(getattr(expectation, "required_tool_memory_ids", ()) or ())
    if not expected_ids:
        return 0.0
    usage_seen = (
        set(trace.used_memory_ids)
        | {claim.memory_id for claim in trace.supporting_claims}
        | {
            memory_id
            for tool_call in trace.tool_calls
            for memory_id in tool_call.memory_ids
        }
    )
    missing = len(expected_ids.difference(usage_seen))
    return round(missing / len(expected_ids), 6)


def _structured_expectation_failures(
    expectation: object,
    trace: MemoryEffectivenessTrace,
) -> tuple[str, ...]:
    failures: list[str] = []
    failures.extend(
        _missing_failures(
            "context_memory_missing",
            tuple(getattr(expectation, "required_context_memory_ids", ()) or ()),
            trace.context_memory_ids,
        )
    )
    failures.extend(
        _missing_failures(
            "cited_memory_missing",
            tuple(getattr(expectation, "required_cited_memory_ids", ()) or ()),
            trace.cited_memory_ids,
        )
    )
    for label, expected, observed in (
        (
            "entity_proposal_missing",
            getattr(expectation, "required_entity_proposal_ids", ()) or (),
            trace.entity_proposal_ids,
        ),
        (
            "fact_proposal_missing",
            getattr(expectation, "required_fact_proposal_ids", ()) or (),
            trace.fact_proposal_ids,
        ),
        (
            "lifecycle_event_missing",
            getattr(expectation, "required_lifecycle_event_ids", ()) or (),
            trace.lifecycle_event_ids,
        ),
        (
            "artifact_missing",
            getattr(expectation, "required_artifact_ids", ()) or (),
            trace.artifact_ids,
        ),
        (
            "citation_span_missing",
            getattr(expectation, "required_citation_spans", ()) or (),
            trace.citation_spans,
        ),
        (
            "graph_path_missing",
            getattr(expectation, "required_graph_path_ids", ()) or (),
            trace.graph_path_ids,
        ),
        (
            "valid_time_missing",
            getattr(expectation, "required_valid_time_refs", ()) or (),
            trace.valid_time_refs,
        ),
        (
            "transaction_time_missing",
            getattr(expectation, "required_transaction_time_refs", ()) or (),
            trace.transaction_time_refs,
        ),
    ):
        failures.extend(_missing_failures(label, tuple(expected), tuple(observed)))
    trajectory_failure = _trajectory_failure(expectation, trace)
    if trajectory_failure:
        failures.append(trajectory_failure)
    return tuple(failures)


def _missing_failures(
    label: str,
    expected: tuple[str, ...],
    observed: tuple[str, ...],
) -> tuple[str, ...]:
    observed_set = set(observed)
    return tuple(f"{label}:{item}" for item in expected if item not in observed_set)


def _trajectory_failure(
    expectation: object,
    trace: MemoryEffectivenessTrace,
) -> str:
    expected = tuple(getattr(expectation, "expected_trajectory_steps", ()) or ())
    if not expected:
        return ""
    observed = trace.trajectory_steps
    mode = str(getattr(expectation, "trajectory_match_mode", "strict"))
    if mode == "strict" and observed == expected:
        return ""
    if mode == "unordered" and set(observed) == set(expected):
        return ""
    if mode == "superset" and set(expected).issubset(observed):
        return ""
    if mode == "subset" and set(observed).issubset(expected):
        return ""
    return f"trajectory_mismatch:{mode}"


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


def _aggregate_case_scores(
    cases: tuple[MemoryEffectivenessCaseResult, ...],
    field_name: str,
) -> dict[str, float]:
    grouped: dict[str, list[float]] = {}
    for case in cases:
        key = str(getattr(case, field_name, "") or "").strip()
        if key:
            grouped.setdefault(key, []).append(case.overall_score)
    return {
        key: round(sum(scores) / len(scores), 6)
        for key, scores in sorted(grouped.items())
    }


def _aggregate_metric_maps(
    maps: tuple[dict[str, float | int | None], ...],
) -> dict[str, float | int | None]:
    numeric_values: dict[str, list[float]] = {}
    for metrics in maps:
        for key, value in metrics.items():
            if isinstance(value, int | float):
                numeric_values.setdefault(key, []).append(float(value))
    return {
        key: round(sum(values) / len(values), 6)
        for key, values in sorted(numeric_values.items())
        if values
    }


def _efficiency_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    keys = ("provider_id", "model_id", "token_count", "cost_usd", "latency_ms")
    return {key: metadata[key] for key in keys if key in metadata}


def _baseline_trend(metadata: dict[str, Any], overall_score: float) -> dict[str, Any]:
    baseline = metadata.get("baseline_score")
    threshold = float(metadata.get("regression_threshold", 0.0) or 0.0)
    if baseline is None:
        return {
            "overall_score": overall_score,
            "baseline_score": None,
            "delta": None,
            "regressed": False,
        }
    baseline_score = float(baseline)
    delta = round(overall_score - baseline_score, 6)
    return {
        "overall_score": overall_score,
        "baseline_score": baseline_score,
        "delta": delta,
        "regressed": delta < -threshold,
    }


def _public_report_sections(
    *,
    overall: float,
    retrieval_metrics: dict[str, float | int | None],
    critical_failures: tuple[str, ...],
) -> dict[str, str]:
    recall = retrieval_metrics.get("recall_at_k", 0.0)
    precision = retrieval_metrics.get("precision_at_k", 0.0)
    return {
        "summary": f"Overall memory-effectiveness score: {overall:.3f}",
        "retrieval": f"Recall@k: {float(recall):.3f}; precision@k: {float(precision):.3f}",
        "critical_failures": str(len(critical_failures)),
    }


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
        operation_scores=dict(data.get("operation_scores", {})),
        memory_location_scores=dict(data.get("memory_location_scores", {})),
        retrieval_metrics=dict(data.get("retrieval_metrics", {})),
        overuse_penalties=dict(data.get("overuse_penalties", {})),
        underuse_penalties=dict(data.get("underuse_penalties", {})),
        efficiency_metadata=dict(data.get("efficiency_metadata", {})),
        baseline_trend=dict(data.get("baseline_trend", {})),
        public_report_sections=dict(data.get("public_report_sections", {})),
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
        operation=str(data.get("operation", "") or ""),
        memory_location=str(data.get("memory_location", "") or ""),
        retrieval_metrics=dict(data.get("retrieval_metrics", {})),
        overuse_penalty=float(data.get("overuse_penalty", 0.0)),
        underuse_penalty=float(data.get("underuse_penalty", 0.0)),
    )
