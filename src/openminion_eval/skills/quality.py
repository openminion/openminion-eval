"""Skill-quality eval fixtures, rubric loaders, and scoring helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any, Callable, Iterable

from openminion_eval.family_support import report_generated_at
from openminion_eval.paths import skill_fixture_root
from openminion_eval.skills.constants import (
    CANONICAL_EVAL_FAMILY,
    FAMILY_REPORT_VERSION,
    SKILL_QUALITY_PENDING_REVIEW_STATUS,
)
from openminion_eval.skills.support import (
    assistant_output_from_record,
    official_skill_matrix_target_ids,
    packaged_skill_fixture_path,
    representative_skill_quality_target_ids as _representative_skill_quality_target_ids,
)


_NUMBERED_LINE_RE = re.compile(r"^\s*(?:\d+[.)]|[-*])\s+", re.MULTILINE)
_VERIFICATION_RE = re.compile(
    r"\b(verify|verification|validate|validation|check|test|confirm)\b",
    re.IGNORECASE,
)
_GUARDRAIL_RE = re.compile(
    r"\b(guardrail|avoid|ensure|make sure|do not|don't|never)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class SkillQualityScenario:
    scenario_id: str
    skill_id: str
    fixture_path: Path
    prompt: str
    evaluation_dimensions: tuple[str, ...]


@dataclass(frozen=True)
class SkillQualityRubricDimension:
    dimension_id: str
    label: str
    reviewer_prompt: str
    scale: tuple[str, ...]


@dataclass(frozen=True)
class SkillQualityScenarioReport:
    scenario_id: str
    skill_id: str
    selected_skill_id: str
    selected_skill_ids: tuple[str, ...]
    assistant_output: str
    routing_match: bool
    artifacts: dict[str, str]
    observations: dict[str, Any]
    rubric_slots: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class SkillQualityTargetReport:
    report_version: str
    generated_at: str
    target_id: str
    agent_id: str
    config_path: str
    routing_artifact: str
    manifest_version: str
    rubric_version: str
    scenario_results: tuple[SkillQualityScenarioReport, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_skill_quality_fixture_root() -> Path:
    return skill_fixture_root("skill_quality")


def default_skill_quality_manifest_path() -> Path:
    return default_skill_quality_fixture_root() / "manifest.json"


def default_rubric_path() -> Path:
    return default_skill_quality_fixture_root() / "rubric.json"


def load_skill_quality_manifest(
    path: str | Path | None = None,
) -> tuple[str, tuple[SkillQualityScenario, ...]]:
    manifest_path = (
        Path(path) if path is not None else default_skill_quality_manifest_path()
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != FAMILY_REPORT_VERSION:
        raise ValueError(f"unsupported skill quality manifest version: {version!r}")

    scenarios: list[SkillQualityScenario] = []
    seen_ids: set[str] = set()
    for item in payload.get("scenarios", []):
        scenario_id = str(item.get("scenario_id", "") or "").strip()
        if not scenario_id or scenario_id in seen_ids:
            raise ValueError(f"invalid or duplicate scenario_id: {scenario_id!r}")
        seen_ids.add(scenario_id)
        fixture_path = packaged_skill_fixture_path(
            str(item.get("fixture_path", "") or "")
        )
        if not fixture_path.exists():
            raise ValueError(
                f"missing fixture for skill quality scenario {scenario_id}: {fixture_path}"
            )
        scenarios.append(
            SkillQualityScenario(
                scenario_id=scenario_id,
                skill_id=str(item.get("skill_id", "") or "").strip(),
                fixture_path=fixture_path,
                prompt=str(item.get("prompt", "") or "").strip(),
                evaluation_dimensions=tuple(
                    str(value).strip()
                    for value in item.get("evaluation_dimensions", [])
                    if str(value).strip()
                ),
            )
        )
    return version, tuple(scenarios)


def load_skill_quality_rubric(
    path: str | Path | None = None,
) -> tuple[str, tuple[SkillQualityRubricDimension, ...]]:
    rubric_path = Path(path) if path is not None else default_rubric_path()
    payload = json.loads(rubric_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != FAMILY_REPORT_VERSION:
        raise ValueError(f"unsupported skill quality rubric version: {version!r}")

    dimensions: list[SkillQualityRubricDimension] = []
    seen_ids: set[str] = set()
    for item in payload.get("dimensions", []):
        dimension_id = str(item.get("dimension_id", "") or "").strip()
        if not dimension_id or dimension_id in seen_ids:
            raise ValueError(f"invalid or duplicate dimension_id: {dimension_id!r}")
        seen_ids.add(dimension_id)
        dimensions.append(
            SkillQualityRubricDimension(
                dimension_id=dimension_id,
                label=str(item.get("label", "") or "").strip(),
                reviewer_prompt=str(item.get("reviewer_prompt", "") or "").strip(),
                scale=tuple(
                    str(value).strip()
                    for value in item.get("scale", [])
                    if str(value).strip()
                ),
            )
        )
    return version, tuple(dimensions)


def official_skill_quality_target_ids() -> tuple[str, ...]:
    return official_skill_matrix_target_ids()


def representative_skill_quality_target_ids() -> tuple[str, ...]:
    return _representative_skill_quality_target_ids()


def collect_routing_artifact_paths(paths: Iterable[str | Path]) -> list[Path]:
    discovered: list[Path] = []
    seen: set[str] = set()
    for raw_path in paths:
        candidate = Path(raw_path).expanduser().resolve()
        if candidate.is_dir():
            for child in sorted(candidate.glob("*.json")):
                if str(child) not in seen:
                    discovered.append(child)
                    seen.add(str(child))
            continue
        if candidate.is_file() and str(candidate) not in seen:
            discovered.append(candidate)
            seen.add(str(candidate))
    return discovered


def iter_routing_target_records(
    paths: Iterable[str | Path],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for path in collect_routing_artifact_paths(paths):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload.get("targets"), list):
            for item in payload["targets"]:
                if isinstance(item, dict):
                    records.append({**item, "routing_artifact": str(path)})
            continue
        if isinstance(payload.get("results"), list):
            records.append({**payload, "routing_artifact": str(path)})
            continue
        raise ValueError(f"unsupported routing artifact payload: {path}")
    return records


def _response_observations(text: str) -> dict[str, Any]:
    normalized = str(text or "")
    line_count = len([line for line in normalized.splitlines() if line.strip()])
    numbered_line_count = len(_NUMBERED_LINE_RE.findall(normalized))
    return {
        "character_count": len(normalized),
        "line_count": line_count,
        "numbered_line_count": numbered_line_count,
        "contains_verification_language": bool(_VERIFICATION_RE.search(normalized)),
        "contains_guardrail_language": bool(_GUARDRAIL_RE.search(normalized)),
    }


def build_skill_quality_target_report(
    target_record: dict[str, Any],
    *,
    manifest_version: str,
    scenarios: tuple[SkillQualityScenario, ...],
    rubric_version: str,
    rubric_dimensions: tuple[SkillQualityRubricDimension, ...],
    now_provider: Callable[[], str] = report_generated_at,
) -> SkillQualityTargetReport:
    scenario_lookup = {scenario.scenario_id: scenario for scenario in scenarios}
    rubric_lookup = {
        dimension.dimension_id: dimension for dimension in rubric_dimensions
    }
    seen_scenarios: set[str] = set()
    reports: list[SkillQualityScenarioReport] = []

    target_id = str(
        target_record.get("target", "") or target_record.get("target_id", "")
    ).strip()
    agent_id = str(target_record.get("agent_id", "") or "").strip()
    config_path = str(target_record.get("config_path", "") or "").strip()
    routing_artifact = str(target_record.get("routing_artifact", "") or "").strip()

    for result in target_record.get("results", []):
        if not isinstance(result, dict):
            continue
        scenario_id = str(result.get("scenario", "") or "").strip()
        expected_skill_id = str(result.get("expected_skill_id", "") or "").strip()
        if not expected_skill_id:
            continue
        if scenario_id not in scenario_lookup:
            raise ValueError(
                f"routing artifact includes unknown quality scenario {scenario_id!r}"
            )
        if scenario_id in seen_scenarios:
            raise ValueError(f"duplicate quality scenario result for {scenario_id!r}")
        scenario = scenario_lookup[scenario_id]
        assistant_output = assistant_output_from_record(result, agent_id=agent_id)
        selected_skill_ids = tuple(
            str(item).strip()
            for item in result.get("selected_skill_ids", [])
            if str(item).strip()
        )
        selected_skill_id = str(result.get("selected_skill_id", "") or "").strip()
        rubric_slots = []
        for dimension_id in scenario.evaluation_dimensions:
            if dimension_id not in rubric_lookup:
                raise ValueError(
                    f"scenario {scenario_id!r} references unknown rubric dimension {dimension_id!r}"
                )
            dimension = rubric_lookup[dimension_id]
            rubric_slots.append(
                {
                    "dimension_id": dimension.dimension_id,
                    "label": dimension.label,
                    "reviewer_prompt": dimension.reviewer_prompt,
                    "scale": list(dimension.scale),
                    "status": SKILL_QUALITY_PENDING_REVIEW_STATUS,
                    "rating": None,
                    "notes": "",
                }
            )
        reports.append(
            SkillQualityScenarioReport(
                scenario_id=scenario_id,
                skill_id=scenario.skill_id,
                selected_skill_id=selected_skill_id,
                selected_skill_ids=selected_skill_ids,
                assistant_output=assistant_output,
                routing_match=selected_skill_id == expected_skill_id,
                artifacts={
                    "transcript": str(result.get("transcript", "") or ""),
                    "events": str(result.get("events", "") or ""),
                },
                observations=_response_observations(assistant_output),
                rubric_slots=tuple(rubric_slots),
            )
        )
        seen_scenarios.add(scenario_id)

    expected_scenarios = {scenario.scenario_id for scenario in scenarios}
    if seen_scenarios != expected_scenarios:
        missing = sorted(expected_scenarios - seen_scenarios)
        extra = sorted(seen_scenarios - expected_scenarios)
        raise ValueError(
            f"quality report scenario mismatch for {target_id or agent_id}: missing={missing} extra={extra}"
        )

    summary = {
        "scenario_count": len(reports),
        "routing_match_count": sum(1 for report in reports if report.routing_match),
        "responses_with_numbered_steps": sum(
            1 for report in reports if report.observations["numbered_line_count"] >= 4
        ),
        "responses_with_verification_language": sum(
            1
            for report in reports
            if report.observations["contains_verification_language"]
        ),
        "responses_with_guardrail_language": sum(
            1
            for report in reports
            if report.observations["contains_guardrail_language"]
        ),
    }
    return SkillQualityTargetReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=now_provider(),
        target_id=target_id,
        agent_id=agent_id,
        config_path=config_path,
        routing_artifact=routing_artifact,
        manifest_version=manifest_version,
        rubric_version=rubric_version,
        scenario_results=tuple(reports),
        summary=summary,
    )


def write_skill_quality_report(
    path: str | Path, report: SkillQualityTargetReport
) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "SkillQualityRubricDimension",
    "SkillQualityScenario",
    "SkillQualityScenarioReport",
    "CANONICAL_EVAL_FAMILY",
    "SkillQualityTargetReport",
    "build_skill_quality_target_report",
    "collect_routing_artifact_paths",
    "default_skill_quality_manifest_path",
    "default_rubric_path",
    "iter_routing_target_records",
    "load_skill_quality_manifest",
    "load_skill_quality_rubric",
    "official_skill_quality_target_ids",
    "representative_skill_quality_target_ids",
    "write_skill_quality_report",
]
