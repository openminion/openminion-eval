"""Build deterministic memory/context scorecard reports."""

from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Iterable

from openminion_eval.family_support import report_generated_at
from openminion_eval.memory_context_scorecard.schemas import (
    AblationOutcome,
    MemoryContextMetric,
    MemoryContextScorecardV1,
    ScorecardCaseFixture,
    TaskOracle,
    metric_name_from_value,
    metric_status_from_value,
    task_oracle_kind_from_value,
)

MEMORY_CONTEXT_SCORECARD_VERSION = "memory-context-scorecard.v1"


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
        raise ValueError("ablation outcome must be an object")
    return AblationOutcome(
        output_ref=str(value.get("output_ref", "")),
        oracle_passed=bool(value.get("oracle_passed", False)),
        score=float(value.get("score", 0.0)),
    )


def _oracle_from_payload(value: object) -> TaskOracle | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("oracle must be an object")
    return TaskOracle(
        oracle_id=str(value.get("oracle_id", "")),
        kind=task_oracle_kind_from_value(value.get("kind")),
        expected_value=str(value.get("expected_value", "")),
        field_path=str(value.get("field_path", "") or ""),
    )
