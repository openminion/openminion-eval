"""Build deterministic memory/context scorecard reports."""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict
from pathlib import Path

from openminion_eval.family_support import report_generated_at
from openminion_eval.memory_context_scorecard.schemas import (
    AblationOutcome,
    ContextBudgetCalibrationV1,
    ContextBudgetRecommendation,
    MemoryContextMetric,
    MemoryContextOperationalCanaryV1,
    MemoryContextScorecardV1,
    OperationalCanaryCaseResult,
    ScorecardCaseFixture,
    TaskOracle,
    budget_calibration_signal_from_value,
    metric_name_from_value,
    metric_status_from_value,
    operational_canary_status_from_value,
    task_oracle_kind_from_value,
)

MEMORY_CONTEXT_SCORECARD_VERSION = "memory-context-scorecard.v1"
MEMORY_CONTEXT_OPERATIONAL_CANARY_VERSION = "memory-context-operational-canary.v1"
CONTEXT_BUDGET_CALIBRATION_VERSION = "context-budget-calibration.v1"


def build_memory_context_scorecard(
    fixtures: Iterable[ScorecardCaseFixture],
    *,
    run_id: str = "memory-context-scorecard-local",
    generated_at: str | None = None,
    metadata: dict | None = None,
) -> MemoryContextScorecardV1:
    fixture_list = tuple(fixtures)
    metrics = tuple(
        _metric_from_fixture(metric) for case in fixture_list for metric in case.metrics
    )
    pass_count = sum(1 for metric in metrics if metric.status == "pass")
    fail_count = sum(1 for metric in metrics if metric.status == "fail")
    warn_count = sum(1 for metric in metrics if metric.status == "warn")
    advisory_count = sum(1 for metric in metrics if metric.status == "advisory")
    blocking_fail_count = sum(
        1 for metric in metrics if metric.blocking and metric.status == "fail"
    )
    return MemoryContextScorecardV1(
        report_version=MEMORY_CONTEXT_SCORECARD_VERSION,
        generated_at=generated_at or report_generated_at(),
        run_id=run_id,
        fixture_ids=tuple(case.case_id for case in fixture_list),
        metrics=metrics,
        summary={
            "fixture_count": len(fixture_list),
            "metric_count": len(metrics),
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "advisory_count": advisory_count,
            "blocking_fail_count": blocking_fail_count,
            "all_blocking_passed": blocking_fail_count == 0,
        },
        metadata=dict(metadata or {}),
    )


def write_memory_context_scorecard(
    path: str | Path, scorecard: MemoryContextScorecardV1
) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(scorecard), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def build_operational_canary(
    scorecard: MemoryContextScorecardV1,
    *,
    run_id: str = "memory-context-operational-canary-local",
    generated_at: str | None = None,
    metadata: dict | None = None,
) -> MemoryContextOperationalCanaryV1:
    cases = tuple(
        _canary_case_from_metric(index, metric)
        for index, metric in enumerate(scorecard.metrics, start=1)
    )
    pass_count = sum(1 for item in cases if item.status == "pass")
    warn_count = sum(1 for item in cases if item.status == "warn")
    fail_count = sum(1 for item in cases if item.status == "fail")
    return MemoryContextOperationalCanaryV1(
        report_version=MEMORY_CONTEXT_OPERATIONAL_CANARY_VERSION,
        generated_at=generated_at or report_generated_at(),
        run_id=run_id,
        cases=cases,
        summary={
            "case_count": len(cases),
            "pass_count": pass_count,
            "warn_count": warn_count,
            "fail_count": fail_count,
            "all_passed": fail_count == 0,
        },
        metadata={
            "source_scorecard_run_id": scorecard.run_id,
            **dict(metadata or {}),
        },
    )


def write_operational_canary(
    path: str | Path, report: MemoryContextOperationalCanaryV1
) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_operational_canary(path: str | Path) -> MemoryContextOperationalCanaryV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return MemoryContextOperationalCanaryV1(
        report_version=str(payload.get("report_version", "")),
        generated_at=str(payload.get("generated_at", "")),
        run_id=str(payload.get("run_id", "")),
        cases=tuple(
            _canary_case_from_payload(item) for item in payload.get("cases", ())
        ),
        summary=dict(payload.get("summary", {})),
        metadata=dict(payload.get("metadata", {})),
    )


def build_context_budget_calibration(
    canary: MemoryContextOperationalCanaryV1,
    *,
    run_id: str = "context-budget-calibration-local",
    generated_at: str | None = None,
    evidence_window: str = "local",
    metadata: dict | None = None,
) -> ContextBudgetCalibrationV1:
    recommendations = tuple(
        _recommendation_from_canary_case(index, case)
        for index, case in enumerate(canary.cases, start=1)
        if case.scorecard_metric in {"budget_stability", "context_budget_stability"}
    )
    if not recommendations:
        recommendations = (
            ContextBudgetRecommendation(
                recommendation_id="budget-rec-1",
                budget_profile="default",
                signal="stable",
                current_cap_tokens=0,
                recommended_cap_tokens=0,
                confidence=0.5,
                evidence_refs=("canary-summary",),
                reason_code="no_budget_specific_signal",
            ),
        )
    change_count = sum(
        1
        for item in recommendations
        if item.current_cap_tokens != item.recommended_cap_tokens
    )
    return ContextBudgetCalibrationV1(
        report_version=CONTEXT_BUDGET_CALIBRATION_VERSION,
        generated_at=generated_at or report_generated_at(),
        run_id=run_id,
        evidence_window=evidence_window,
        recommendations=recommendations,
        summary={
            "recommendation_count": len(recommendations),
            "change_count": change_count,
            "writes_runtime_config": False,
        },
        metadata={"source_canary_run_id": canary.run_id, **dict(metadata or {})},
    )


def write_context_budget_calibration(
    path: str | Path, report: ContextBudgetCalibrationV1
) -> Path:
    target = Path(path).expanduser().resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(asdict(report), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_context_budget_calibration(path: str | Path) -> ContextBudgetCalibrationV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return ContextBudgetCalibrationV1(
        report_version=str(payload.get("report_version", "")),
        generated_at=str(payload.get("generated_at", "")),
        run_id=str(payload.get("run_id", "")),
        evidence_window=str(payload.get("evidence_window", "")),
        recommendations=tuple(
            _recommendation_from_payload(item)
            for item in payload.get("recommendations", ())
        ),
        summary=dict(payload.get("summary", {})),
        metadata=dict(payload.get("metadata", {})),
    )


def load_memory_context_scorecard(path: str | Path) -> MemoryContextScorecardV1:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return MemoryContextScorecardV1(
        report_version=str(payload.get("report_version", "")),
        generated_at=str(payload.get("generated_at", "")),
        run_id=str(payload.get("run_id", "")),
        fixture_ids=tuple(payload.get("fixture_ids", ())),
        metrics=tuple(
            _metric_from_payload(item) for item in payload.get("metrics", ())
        ),
        summary=dict(payload.get("summary", {})),
        metadata=dict(payload.get("metadata", {})),
    )


def _canary_case_from_metric(
    index: int, metric: MemoryContextMetric
) -> OperationalCanaryCaseResult:
    status = (
        "pass"
        if metric.status == "pass"
        else "fail"
        if metric.status == "fail"
        else "warn"
    )
    return OperationalCanaryCaseResult(
        case_id=f"canary-case-{index}",
        task_type=str(metric.metric_name),
        status=status,
        scorecard_metric=metric.metric_name,
        score=float(metric.value),
        threshold=float(metric.threshold),
        memory_enabled=True,
        blocks_enabled=bool(metric.context_trace_ids),
        session_length_bucket="fixture",
        context_budget_policy="default",
        evidence_refs=metric.evidence_refs,
        provider="provider-backed" if metric.provider_backed else "",
        model="",
        source_trace_refs=metric.context_trace_ids + metric.provenance_trace_ids,
        redaction_status="redacted",
        disabled_score=metric.disabled_outcome.score
        if metric.disabled_outcome
        else None,
        enabled_score=metric.enabled_outcome.score if metric.enabled_outcome else None,
    )


def _canary_case_from_payload(data: dict[str, object]) -> OperationalCanaryCaseResult:
    return OperationalCanaryCaseResult(
        case_id=str(data.get("case_id", "")),
        task_type=str(data.get("task_type", "")),
        status=operational_canary_status_from_value(data.get("status")),
        scorecard_metric=metric_name_from_value(data.get("scorecard_metric")),
        score=float(data.get("score", 0.0)),
        threshold=float(data.get("threshold", 0.0)),
        memory_enabled=bool(data.get("memory_enabled", False)),
        blocks_enabled=bool(data.get("blocks_enabled", False)),
        session_length_bucket=str(data.get("session_length_bucket", "")),
        context_budget_policy=str(data.get("context_budget_policy", "")),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        provider=str(data.get("provider", "") or ""),
        model=str(data.get("model", "") or ""),
        source_trace_refs=tuple(data.get("source_trace_refs", ())),
        redaction_status=str(data.get("redaction_status", "") or "redacted"),
        disabled_score=_optional_float(data.get("disabled_score")),
        enabled_score=_optional_float(data.get("enabled_score")),
    )


def _recommendation_from_canary_case(
    index: int, case: OperationalCanaryCaseResult
) -> ContextBudgetRecommendation:
    if case.status == "fail":
        signal = "underuse" if case.score < case.threshold else "overuse"
        recommended = 1200 if signal == "underuse" else 800
    else:
        signal = "stable"
        recommended = 1000
    return ContextBudgetRecommendation(
        recommendation_id=f"budget-rec-{index}",
        budget_profile=case.context_budget_policy,
        signal=budget_calibration_signal_from_value(signal),
        current_cap_tokens=1000,
        recommended_cap_tokens=recommended,
        confidence=round(abs(float(case.score) - float(case.threshold)), 4),
        evidence_refs=case.evidence_refs,
        reason_code=f"{case.scorecard_metric}_{signal}",
    )


def _recommendation_from_payload(
    data: dict[str, object],
) -> ContextBudgetRecommendation:
    return ContextBudgetRecommendation(
        recommendation_id=str(data.get("recommendation_id", "")),
        budget_profile=str(data.get("budget_profile", "")),
        signal=budget_calibration_signal_from_value(data.get("signal")),
        current_cap_tokens=int(data.get("current_cap_tokens", 0)),
        recommended_cap_tokens=int(data.get("recommended_cap_tokens", 0)),
        confidence=float(data.get("confidence", 0.0)),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        reason_code=str(data.get("reason_code", "")),
    )


def _optional_float(value: object) -> float | None:
    return None if value is None else float(value)


def _metric_from_fixture(metric) -> MemoryContextMetric:
    delta = None
    if metric.disabled_outcome is not None and metric.enabled_outcome is not None:
        delta = round(metric.enabled_outcome.score - metric.disabled_outcome.score, 6)
    return MemoryContextMetric(
        metric_name=metric.metric_name,
        status=metric.status,
        value=metric.value,
        threshold=metric.threshold,
        blocking=metric.blocking,
        evidence_refs=metric.evidence_refs,
        context_trace_ids=metric.context_trace_ids,
        provenance_trace_ids=metric.provenance_trace_ids,
        disabled_outcome=metric.disabled_outcome,
        enabled_outcome=metric.enabled_outcome,
        delta=delta,
        oracle=metric.oracle,
        provider_backed=metric.provider_backed,
        variance_evidence_ref=metric.variance_evidence_ref,
    )


def _metric_from_payload(data: dict[str, object]) -> MemoryContextMetric:
    disabled = data.get("disabled_outcome")
    enabled = data.get("enabled_outcome")
    oracle = data.get("oracle")
    return MemoryContextMetric(
        metric_name=metric_name_from_value(data.get("metric_name")),
        status=metric_status_from_value(data.get("status")),
        value=float(data.get("value", 0.0)),
        threshold=float(data.get("threshold", 0.0)),
        blocking=bool(data.get("blocking", False)),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        context_trace_ids=tuple(data.get("context_trace_ids", ())),
        provenance_trace_ids=tuple(data.get("provenance_trace_ids", ())),
        disabled_outcome=_outcome_from_payload(disabled),
        enabled_outcome=_outcome_from_payload(enabled),
        delta=data.get("delta"),
        oracle=_oracle_from_payload(oracle),
        provider_backed=bool(data.get("provider_backed", False)),
        variance_evidence_ref=str(data.get("variance_evidence_ref", "") or ""),
    )


def _outcome_from_payload(value: object) -> AblationOutcome | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("ablation outcome must be an object")
    return AblationOutcome(
        output_ref=str(value.get("output_ref", "")),
        oracle_passed=bool(value.get("oracle_passed", False)),
        score=float(value.get("score", 0.0)),
    )


def _oracle_from_payload(value: object) -> TaskOracle | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError("oracle must be an object")
    return TaskOracle(
        oracle_id=str(value.get("oracle_id", "")),
        kind=task_oracle_kind_from_value(value.get("kind")),
        expected_value=str(value.get("expected_value", "")),
        field_path=str(value.get("field_path", "") or ""),
    )
