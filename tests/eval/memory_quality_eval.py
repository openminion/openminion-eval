from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

from tests.eval.integration.memory_eval import (
    MemoryEvalEngineConfig,
    MemoryEvalHarness,
    MemoryEvalReport,
    MemoryEvalScenario,
    MemoryEvalScenarioResult,
)


ADJACENT_EVAL_DISPOSITION = "memory_family_adjacent_report"


@dataclass(frozen=True)
class MemoryQualityScenario:
    scenario_id: str
    label: str
    scenario_family: str
    source_fixture: Path
    memory_scenario_id: str
    evaluation_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class MemoryQualityRubricDimension:
    dimension_id: str
    label: str
    description: str
    score_range: tuple[float, float]


@dataclass(frozen=True)
class MemoryQualityScenarioReport:
    scenario_id: str
    memory_scenario_id: str
    scenario_family: str
    source_fixture: str
    scores: dict[str, float]
    source_metrics: dict[str, float | int | bool]
    observations: dict[str, Any]


@dataclass(frozen=True)
class MemoryQualityTargetReport:
    report_version: str
    generated_at: str
    target_id: str
    agent_id: str
    config_path: str
    manifest_version: str
    rubric_version: str
    engine_name: str
    execution_mode: str
    scenario_results: tuple[MemoryQualityScenarioReport, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def openminion_root() -> Path:
    return Path(__file__).resolve().parents[2]


def default_memory_quality_fixture_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "memory_quality"


def default_memory_quality_manifest_path() -> Path:
    return default_memory_quality_fixture_root() / "manifest.json"


def default_memory_quality_rubric_path() -> Path:
    return default_memory_quality_fixture_root() / "rubric.json"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _fixture_display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(openminion_root()))
    except ValueError:
        return str(path)


def load_memory_quality_manifest(
    path: str | Path | None = None,
) -> tuple[str, tuple[MemoryQualityScenario, ...]]:
    manifest_path = (
        Path(path) if path is not None else default_memory_quality_manifest_path()
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(f"unsupported memory quality manifest version: {version!r}")

    scenarios: list[MemoryQualityScenario] = []
    seen_ids: set[str] = set()
    for item in payload.get("scenarios", []):
        scenario_id = str(item.get("scenario_id", "") or "").strip()
        if not scenario_id or scenario_id in seen_ids:
            raise ValueError(f"invalid or duplicate scenario_id: {scenario_id!r}")
        seen_ids.add(scenario_id)
        source_fixture = openminion_root() / str(item.get("source_fixture", "") or "")
        if not source_fixture.exists():
            raise ValueError(
                f"missing memory quality source fixture {scenario_id}: {source_fixture}"
            )
        dimensions = tuple(
            str(value).strip()
            for value in item.get("evaluation_dimensions", [])
            if str(value).strip()
        )
        if not dimensions:
            raise ValueError(f"scenario {scenario_id!r} has no dimensions")
        scenarios.append(
            MemoryQualityScenario(
                scenario_id=scenario_id,
                label=str(item.get("label", "") or "").strip(),
                scenario_family=str(item.get("scenario_family", "") or "").strip(),
                source_fixture=source_fixture,
                memory_scenario_id=str(
                    item.get("memory_scenario_id", "") or ""
                ).strip(),
                evaluation_dimensions=dimensions,
            )
        )
    return version, tuple(scenarios)


def load_memory_quality_rubric(
    path: str | Path | None = None,
) -> tuple[str, tuple[MemoryQualityRubricDimension, ...]]:
    rubric_path = (
        Path(path) if path is not None else default_memory_quality_rubric_path()
    )
    payload = json.loads(rubric_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(f"unsupported memory quality rubric version: {version!r}")

    dimensions: list[MemoryQualityRubricDimension] = []
    seen_ids: set[str] = set()
    for item in payload.get("dimensions", []):
        dimension_id = str(item.get("dimension_id", "") or "").strip()
        if not dimension_id or dimension_id in seen_ids:
            raise ValueError(f"invalid or duplicate dimension_id: {dimension_id!r}")
        seen_ids.add(dimension_id)
        raw_range = item.get("score_range", [0.0, 1.0])
        if not isinstance(raw_range, list) or len(raw_range) != 2:
            raise ValueError(f"invalid score_range for dimension {dimension_id!r}")
        dimensions.append(
            MemoryQualityRubricDimension(
                dimension_id=dimension_id,
                label=str(item.get("label", "") or "").strip(),
                description=str(item.get("description", "") or "").strip(),
                score_range=(float(raw_range[0]), float(raw_range[1])),
            )
        )
    return version, tuple(dimensions)


def load_memory_quality_source_scenarios(
    scenarios: tuple[MemoryQualityScenario, ...],
    *,
    harness: MemoryEvalHarness | None = None,
) -> list[MemoryEvalScenario]:
    active_harness = harness or MemoryEvalHarness()
    return [
        active_harness.loader.load(scenario.source_fixture) for scenario in scenarios
    ]


def run_memory_quality_source_report(
    scenarios: tuple[MemoryQualityScenario, ...],
    *,
    harness: MemoryEvalHarness | None = None,
    engine_config: MemoryEvalEngineConfig | None = None,
) -> MemoryEvalReport:
    active_harness = harness or MemoryEvalHarness()
    return active_harness.run(
        load_memory_quality_source_scenarios(scenarios, harness=active_harness),
        engine_config=engine_config,
    )


def official_memory_quality_target_ids() -> tuple[str, ...]:
    return ("minimax-m2-5", "minimax-m2-7")


def representative_memory_quality_target_ids() -> tuple[str, ...]:
    return (
        "minimax-m2-5",
        "minimax-m2-7",
        "ollamacloud-glm-5",
        "ollamacloud-minimax-m2-7",
        "openrouter-minimax-m2-7",
        "openrouter-claude-haiku-4-5",
        "openrouter-gpt-4o",
    )


def _metric(metrics: dict[str, float | int | bool], *names: str) -> float | None:
    for name in names:
        if name not in metrics:
            continue
        value = metrics[name]
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return float(value)
    return None


def _bounded(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(1.0, float(value)))


def _dimension_scores(
    *,
    scenario: MemoryQualityScenario,
    result: MemoryEvalScenarioResult,
) -> dict[str, float]:
    metrics = result.metrics
    recall_precision = _bounded(
        _metric(
            metrics,
            "cross_session_recall.precision_at_5",
            "capsule_precision.capsule_precision",
        )
    )
    recall_relevance = _bounded(
        _metric(
            metrics,
            "cross_session_recall.recall_at_5",
            "paraphrase_retrieval.paraphrase_recall_at_5",
            "capsule_precision.capsule_precision",
        )
    )
    noise_score = _metric(metrics, "capsule_precision.capsule_noise_rate")
    low_noise = _bounded(
        1.0 - noise_score if noise_score is not None else recall_precision
    )
    promotion_quality = _bounded(
        (
            recall_relevance
            + _bounded(_metric(metrics, "capsule_precision.capsule_precision"))
        )
        / 2.0
    )
    behavioral_influence = _bounded(min(recall_relevance, low_noise))
    all_scores = {
        "recall_precision": recall_precision,
        "recall_relevance": recall_relevance,
        "behavioral_influence": behavioral_influence,
        "promotion_quality": promotion_quality,
        "noise_level": low_noise,
    }
    return {
        dimension_id: all_scores[dimension_id]
        for dimension_id in scenario.evaluation_dimensions
    }


def build_memory_quality_target_report(
    target_record: dict[str, Any],
    *,
    manifest_version: str,
    scenarios: tuple[MemoryQualityScenario, ...],
    rubric_version: str,
    rubric_dimensions: tuple[MemoryQualityRubricDimension, ...],
    source_report: MemoryEvalReport,
) -> MemoryQualityTargetReport:
    rubric_ids = {dimension.dimension_id for dimension in rubric_dimensions}
    required_ids = {
        "recall_precision",
        "recall_relevance",
        "behavioral_influence",
        "promotion_quality",
        "noise_level",
    }
    if rubric_ids != required_ids:
        raise ValueError(
            "memory quality rubric dimensions must exactly match "
            f"{sorted(required_ids)}, got {sorted(rubric_ids)}"
        )
    result_lookup = {
        result.scenario_id: result for result in source_report.scenario_results
    }
    scenario_reports: list[MemoryQualityScenarioReport] = []
    for scenario in scenarios:
        if scenario.memory_scenario_id not in result_lookup:
            raise ValueError(
                f"missing memory eval result for {scenario.memory_scenario_id!r}"
            )
        result = result_lookup[scenario.memory_scenario_id]
        scores = _dimension_scores(scenario=scenario, result=result)
        scenario_reports.append(
            MemoryQualityScenarioReport(
                scenario_id=scenario.scenario_id,
                memory_scenario_id=scenario.memory_scenario_id,
                scenario_family=scenario.scenario_family,
                source_fixture=_fixture_display_path(scenario.source_fixture),
                scores=scores,
                source_metrics=dict(result.metrics),
                observations={
                    "query_count": result.query_count,
                    "measurement_boundary": (
                        "deterministic_memory_context_quality; "
                        "no runtime memory modification"
                    ),
                },
            )
        )

    dimension_totals: dict[str, list[float]] = {}
    for scenario_report in scenario_reports:
        for dimension_id, score in scenario_report.scores.items():
            dimension_totals.setdefault(dimension_id, []).append(score)
    dimension_summary = {
        dimension_id: sum(values) / len(values)
        for dimension_id, values in sorted(dimension_totals.items())
        if values
    }
    overall_score = (
        sum(dimension_summary.values()) / len(dimension_summary)
        if dimension_summary
        else 0.0
    )

    target_id = str(target_record.get("target_id", "") or "").strip()
    return MemoryQualityTargetReport(
        report_version="1",
        generated_at=_utc_now_iso(),
        target_id=target_id,
        agent_id=str(target_record.get("agent_id", "") or target_id).strip(),
        config_path=str(target_record.get("config_path", "") or "").strip(),
        manifest_version=manifest_version,
        rubric_version=rubric_version,
        engine_name=source_report.engine_name,
        execution_mode="deterministic_memory_harness",
        scenario_results=tuple(scenario_reports),
        summary={
            "scenario_count": len(scenario_reports),
            "dimension_summary": dimension_summary,
            "overall_score": overall_score,
            "baseline_scope": (
                "provider-shaped deterministic baseline; live model behavioral "
                "influence scoring can consume the same contract later"
            ),
        },
    )


def write_memory_quality_report(
    path: str | Path,
    report: MemoryQualityTargetReport,
) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "MemoryQualityRubricDimension",
    "MemoryQualityScenario",
    "MemoryQualityScenarioReport",
    "MemoryQualityTargetReport",
    "build_memory_quality_target_report",
    "default_memory_quality_fixture_root",
    "default_memory_quality_manifest_path",
    "default_memory_quality_rubric_path",
    "load_memory_quality_manifest",
    "load_memory_quality_rubric",
    "load_memory_quality_source_scenarios",
    "official_memory_quality_target_ids",
    "representative_memory_quality_target_ids",
    "run_memory_quality_source_report",
    "write_memory_quality_report",
]
