"""Load deterministic memory/context scorecard fixtures."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from openminion_eval.memory_context_scorecard.schemas import (
    AblationOutcome,
    ScorecardCaseFixture,
    ScorecardMetricFixture,
    TaskOracle,
)

FIXTURE_VERSION = "memory-context-scorecard-fixtures.v1"


def default_memory_context_scorecard_cases_path() -> Path:
    return Path(
        resources.files("openminion_eval.memory_context_scorecard")
        / "resources"
        / "cases.json"
    )


def load_memory_context_scorecard_fixtures(
    path: str | Path | None = None,
) -> tuple[ScorecardCaseFixture, ...]:
    payload = json.loads(
        Path(path or default_memory_context_scorecard_cases_path()).read_text(
            encoding="utf-8"
        )
    )
    if not isinstance(payload, dict):
        raise ValueError("scorecard fixture payload must be an object")
    version = str(payload.get("version", "") or "").strip()
    if version != FIXTURE_VERSION:
        raise ValueError(f"unsupported scorecard fixture version: {version!r}")
    items = payload.get("cases", [])
    if not isinstance(items, list):
        raise ValueError("scorecard fixture cases must be a list")
    cases = tuple(_case_from_mapping(_require_mapping(item)) for item in items)
    ids = [case.case_id for case in cases]
    if len(set(ids)) != len(ids):
        raise ValueError("scorecard fixture case IDs must be unique")
    return cases


def _case_from_mapping(data: Mapping[str, Any]) -> ScorecardCaseFixture:
    metrics = data.get("metrics", [])
    if not isinstance(metrics, list):
        raise ValueError("scorecard fixture metrics must be a list")
    return ScorecardCaseFixture(
        case_id=str(data.get("case_id", "")),
        task_input_ref=str(data.get("task_input_ref", "")),
        tool_fixture_ref=str(data.get("tool_fixture_ref", "")),
        model_config_ref=str(data.get("model_config_ref", "")),
        seed=str(data.get("seed", "")),
        metrics=tuple(_metric_from_mapping(_require_mapping(item)) for item in metrics),
    )


def _metric_from_mapping(data: Mapping[str, Any]) -> ScorecardMetricFixture:
    return ScorecardMetricFixture(
        metric_name=data.get("metric_name"),  # type: ignore[arg-type]
        value=float(data.get("value", 0.0)),
        threshold=float(data.get("threshold", 0.0)),
        status=data.get("status"),  # type: ignore[arg-type]
        blocking=bool(data.get("blocking", False)),
        evidence_refs=tuple(data.get("evidence_refs", ())),
        context_trace_ids=tuple(data.get("context_trace_ids", ())),
        provenance_trace_ids=tuple(data.get("provenance_trace_ids", ())),
        disabled_outcome=_outcome_or_none(data.get("disabled_outcome")),
        enabled_outcome=_outcome_or_none(data.get("enabled_outcome")),
        oracle=_oracle_or_none(data.get("oracle")),
        provider_backed=bool(data.get("provider_backed", False)),
        variance_evidence_ref=str(data.get("variance_evidence_ref", "") or ""),
    )


def _outcome_or_none(value: Any) -> AblationOutcome | None:
    if value is None:
        return None
    data = _require_mapping(value)
    return AblationOutcome(
        output_ref=str(data.get("output_ref", "")),
        oracle_passed=bool(data.get("oracle_passed", False)),
        score=float(data.get("score", 0.0)),
    )


def _oracle_or_none(value: Any) -> TaskOracle | None:
    if value is None:
        return None
    data = _require_mapping(value)
    return TaskOracle(
        oracle_id=str(data.get("oracle_id", "")),
        kind=data.get("kind"),  # type: ignore[arg-type]
        expected_value=str(data.get("expected_value", "")),
        field_path=str(data.get("field_path", "") or ""),
    )


def _require_mapping(value: Any) -> Mapping[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("scorecard fixture item must be an object")
    return value
