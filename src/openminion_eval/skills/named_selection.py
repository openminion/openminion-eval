"""Named-skill routing eval helpers and report builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any

from openminion_eval.family_support import utc_now_iso
from openminion_eval.skills.support import (
    extract_assistant_messages,
    official_skill_matrix_target_ids,
    packaged_skill_fixture_path,
    representative_nl_named_skill_target_ids as _representative_nl_named_skill_target_ids,
    skill_resources_root,
)


@dataclass(frozen=True)
class NLNamedSkillPromptVariant:
    variant_id: str
    label: str
    prompt_template: str


@dataclass(frozen=True)
class NLNamedSkillScenario:
    scenario_id: str
    skill_id: str
    fixture_path: Path
    task_brief: str


@dataclass(frozen=True)
class NLNamedSkillRubricDimension:
    dimension_id: str
    label: str
    description: str


@dataclass(frozen=True)
class NLNamedSkillAttemptReport:
    scenario_id: str
    skill_id: str
    prompt_variant_id: str
    prompt_variant_label: str
    prompt: str
    selected_skill_id: str
    selected_skill_ids: tuple[str, ...]
    assistant_output: str
    selection_accuracy: bool
    selection_confidence: bool
    fallback_behavior: str
    artifacts: dict[str, str]
    dimensions: dict[str, Any]


@dataclass(frozen=True)
class NLNamedSkillTargetReport:
    report_version: str
    generated_at: str
    target_id: str
    agent_id: str
    config_path: str
    manifest_version: str
    rubric_version: str
    prompt_variant_version: str
    attempts: tuple[NLNamedSkillAttemptReport, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def default_nl_named_skill_fixture_root() -> Path:
    return skill_resources_root() / "nl_named_skill"


def default_nl_named_skill_manifest_path() -> Path:
    return default_nl_named_skill_fixture_root() / "manifest.json"


def default_nl_named_skill_prompt_variant_path() -> Path:
    return default_nl_named_skill_fixture_root() / "prompt_variants.json"


def default_nl_named_skill_rubric_path() -> Path:
    return default_nl_named_skill_fixture_root() / "rubric.json"


CANONICAL_EVAL_FAMILY = "skills"


def load_nl_named_skill_manifest(
    path: str | Path | None = None,
) -> tuple[str, tuple[NLNamedSkillScenario, ...]]:
    manifest_path = (
        Path(path) if path is not None else default_nl_named_skill_manifest_path()
    )
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(f"unsupported NL named-skill manifest version: {version!r}")

    scenarios: list[NLNamedSkillScenario] = []
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
                f"missing fixture for NL named-skill scenario {scenario_id}: {fixture_path}"
            )
        scenarios.append(
            NLNamedSkillScenario(
                scenario_id=scenario_id,
                skill_id=str(item.get("skill_id", "") or "").strip(),
                fixture_path=fixture_path,
                task_brief=str(item.get("task_brief", "") or "").strip(),
            )
        )
    return version, tuple(scenarios)


def load_nl_named_skill_prompt_variants(
    path: str | Path | None = None,
) -> tuple[str, tuple[NLNamedSkillPromptVariant, ...]]:
    variant_path = (
        Path(path) if path is not None else default_nl_named_skill_prompt_variant_path()
    )
    payload = json.loads(variant_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(
            f"unsupported NL named-skill prompt variant version: {version!r}"
        )

    variants: list[NLNamedSkillPromptVariant] = []
    seen_ids: set[str] = set()
    for item in payload.get("variants", []):
        variant_id = str(item.get("variant_id", "") or "").strip()
        if not variant_id or variant_id in seen_ids:
            raise ValueError(f"invalid or duplicate variant_id: {variant_id!r}")
        seen_ids.add(variant_id)
        variants.append(
            NLNamedSkillPromptVariant(
                variant_id=variant_id,
                label=str(item.get("label", "") or "").strip(),
                prompt_template=str(item.get("prompt_template", "") or "").strip(),
            )
        )
    return version, tuple(variants)


def load_nl_named_skill_rubric(
    path: str | Path | None = None,
) -> tuple[str, tuple[NLNamedSkillRubricDimension, ...]]:
    rubric_path = (
        Path(path) if path is not None else default_nl_named_skill_rubric_path()
    )
    payload = json.loads(rubric_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(f"unsupported NL named-skill rubric version: {version!r}")

    dimensions: list[NLNamedSkillRubricDimension] = []
    seen_ids: set[str] = set()
    for item in payload.get("dimensions", []):
        dimension_id = str(item.get("dimension_id", "") or "").strip()
        if not dimension_id or dimension_id in seen_ids:
            raise ValueError(f"invalid or duplicate dimension_id: {dimension_id!r}")
        seen_ids.add(dimension_id)
        dimensions.append(
            NLNamedSkillRubricDimension(
                dimension_id=dimension_id,
                label=str(item.get("label", "") or "").strip(),
                description=str(item.get("description", "") or "").strip(),
            )
        )
    return version, tuple(dimensions)


def render_nl_named_skill_prompt(
    *,
    scenario: NLNamedSkillScenario,
    variant: NLNamedSkillPromptVariant,
) -> str:
    return variant.prompt_template.format(
        skill_id=scenario.skill_id,
        task_brief=scenario.task_brief,
    ).strip()


def official_nl_named_skill_target_ids() -> tuple[str, ...]:
    return official_skill_matrix_target_ids()


def representative_nl_named_skill_target_ids() -> tuple[str, ...]:
    return _representative_nl_named_skill_target_ids()


def _assistant_output_from_attempt(
    attempt: dict[str, Any],
    *,
    agent_id: str,
) -> str:
    transcript_path = Path(str(attempt.get("transcript", "") or "")).expanduser()
    if transcript_path.exists():
        transcript = transcript_path.read_text(encoding="utf-8")
        session_id = str(attempt.get("session_id", "") or transcript_path.stem).strip()
        messages = extract_assistant_messages(
            transcript=transcript,
            session_id=session_id,
            agent_id=agent_id,
        )
        if messages:
            return "\n\n".join(messages)
    return str(attempt.get("assistant_preview", "") or "").strip()


def _prompt_sensitivity_by_scenario(
    attempts: list[NLNamedSkillAttemptReport],
) -> dict[str, str]:
    scenario_map: dict[str, list[bool]] = {}
    for attempt in attempts:
        scenario_map.setdefault(attempt.scenario_id, []).append(
            attempt.selection_accuracy
        )
    result: dict[str, str] = {}
    for scenario_id, outcomes in scenario_map.items():
        if all(outcomes):
            result[scenario_id] = "stable_success"
        elif any(outcomes):
            result[scenario_id] = "variant_sensitive"
        else:
            result[scenario_id] = "stable_failure"
    return result


def build_nl_named_skill_target_report(
    target_record: dict[str, Any],
    *,
    manifest_version: str,
    scenarios: tuple[NLNamedSkillScenario, ...],
    prompt_variant_version: str,
    prompt_variants: tuple[NLNamedSkillPromptVariant, ...],
    rubric_version: str,
    rubric_dimensions: tuple[NLNamedSkillRubricDimension, ...],
) -> NLNamedSkillTargetReport:
    scenario_lookup = {scenario.scenario_id: scenario for scenario in scenarios}
    variant_lookup = {variant.variant_id: variant for variant in prompt_variants}
    dimension_ids = {dimension.dimension_id for dimension in rubric_dimensions}
    required_dimensions = {
        "selection_accuracy",
        "selection_confidence",
        "fallback_behavior",
        "prompt_sensitivity",
    }
    if dimension_ids != required_dimensions:
        raise ValueError(
            "NL named-skill rubric dimensions must exactly match "
            f"{sorted(required_dimensions)}, got {sorted(dimension_ids)}"
        )

    target_id = str(target_record.get("target_id", "") or "").strip()
    agent_id = str(target_record.get("agent_id", "") or "").strip()
    config_path = str(target_record.get("config_path", "") or "").strip()

    attempts: list[NLNamedSkillAttemptReport] = []
    for item in target_record.get("attempts", []):
        if not isinstance(item, dict):
            continue
        scenario_id = str(item.get("scenario_id", "") or "").strip()
        if scenario_id not in scenario_lookup:
            raise ValueError(f"unknown NL named-skill scenario: {scenario_id!r}")
        prompt_variant_id = str(item.get("prompt_variant_id", "") or "").strip()
        if prompt_variant_id not in variant_lookup:
            raise ValueError(
                f"unknown NL named-skill prompt variant: {prompt_variant_id!r}"
            )
        scenario = scenario_lookup[scenario_id]
        variant = variant_lookup[prompt_variant_id]
        selected_skill_id = str(item.get("selected_skill_id", "") or "").strip()
        selected_skill_ids = tuple(
            str(entry).strip()
            for entry in item.get("selected_skill_ids", [])
            if str(entry).strip()
        )
        selection_accuracy = selected_skill_id == scenario.skill_id
        selection_confidence = (
            bool(item.get("skill_selected_event"))
            and selected_skill_id == scenario.skill_id
        )
        if selection_accuracy:
            fallback_behavior = "correct"
        elif selected_skill_id:
            fallback_behavior = "wrong_skill"
        else:
            fallback_behavior = "empty"

        dimensions = {
            "selection_accuracy": selection_accuracy,
            "selection_confidence": selection_confidence,
            "fallback_behavior": fallback_behavior,
            "prompt_sensitivity": None,
        }
        attempts.append(
            NLNamedSkillAttemptReport(
                scenario_id=scenario_id,
                skill_id=scenario.skill_id,
                prompt_variant_id=prompt_variant_id,
                prompt_variant_label=variant.label,
                prompt=str(item.get("prompt", "") or "").strip(),
                selected_skill_id=selected_skill_id,
                selected_skill_ids=selected_skill_ids,
                assistant_output=_assistant_output_from_attempt(
                    item, agent_id=agent_id
                ),
                selection_accuracy=selection_accuracy,
                selection_confidence=selection_confidence,
                fallback_behavior=fallback_behavior,
                artifacts={
                    "transcript": str(item.get("transcript", "") or ""),
                    "events": str(item.get("events", "") or ""),
                },
                dimensions=dimensions,
            )
        )

    expected_attempt_count = len(scenarios) * len(prompt_variants)
    if len(attempts) != expected_attempt_count:
        raise ValueError(
            f"expected {expected_attempt_count} NL named-skill attempts for {target_id}, "
            f"got {len(attempts)}"
        )

    sensitivity_map = _prompt_sensitivity_by_scenario(attempts)
    updated_attempts: list[NLNamedSkillAttemptReport] = []
    for attempt in attempts:
        dimensions = dict(attempt.dimensions)
        dimensions["prompt_sensitivity"] = sensitivity_map[attempt.scenario_id]
        updated_attempts.append(
            NLNamedSkillAttemptReport(
                scenario_id=attempt.scenario_id,
                skill_id=attempt.skill_id,
                prompt_variant_id=attempt.prompt_variant_id,
                prompt_variant_label=attempt.prompt_variant_label,
                prompt=attempt.prompt,
                selected_skill_id=attempt.selected_skill_id,
                selected_skill_ids=attempt.selected_skill_ids,
                assistant_output=attempt.assistant_output,
                selection_accuracy=attempt.selection_accuracy,
                selection_confidence=attempt.selection_confidence,
                fallback_behavior=attempt.fallback_behavior,
                artifacts=attempt.artifacts,
                dimensions=dimensions,
            )
        )

    variant_summary: dict[str, dict[str, int]] = {}
    for variant in prompt_variants:
        relevant = [
            attempt
            for attempt in updated_attempts
            if attempt.prompt_variant_id == variant.variant_id
        ]
        variant_summary[variant.variant_id] = {
            "attempt_count": len(relevant),
            "selection_accuracy_count": sum(
                1 for attempt in relevant if attempt.selection_accuracy
            ),
            "selection_confidence_count": sum(
                1 for attempt in relevant if attempt.selection_confidence
            ),
            "empty_fallback_count": sum(
                1 for attempt in relevant if attempt.fallback_behavior == "empty"
            ),
            "wrong_skill_count": sum(
                1 for attempt in relevant if attempt.fallback_behavior == "wrong_skill"
            ),
        }

    summary = {
        "attempt_count": len(updated_attempts),
        "scenario_count": len(scenarios),
        "prompt_variant_count": len(prompt_variants),
        "selection_accuracy_count": sum(
            1 for attempt in updated_attempts if attempt.selection_accuracy
        ),
        "selection_confidence_count": sum(
            1 for attempt in updated_attempts if attempt.selection_confidence
        ),
        "empty_fallback_count": sum(
            1 for attempt in updated_attempts if attempt.fallback_behavior == "empty"
        ),
        "wrong_skill_count": sum(
            1
            for attempt in updated_attempts
            if attempt.fallback_behavior == "wrong_skill"
        ),
        "variant_summary": variant_summary,
        "prompt_sensitivity_by_scenario": sensitivity_map,
    }

    return NLNamedSkillTargetReport(
        report_version="1",
        generated_at=utc_now_iso(),
        target_id=target_id,
        agent_id=agent_id,
        config_path=config_path,
        manifest_version=manifest_version,
        rubric_version=rubric_version,
        prompt_variant_version=prompt_variant_version,
        attempts=tuple(updated_attempts),
        summary=summary,
    )


def write_nl_named_skill_report(
    path: str | Path, report: NLNamedSkillTargetReport
) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "NLNamedSkillAttemptReport",
    "NLNamedSkillPromptVariant",
    "NLNamedSkillRubricDimension",
    "NLNamedSkillScenario",
    "CANONICAL_EVAL_FAMILY",
    "NLNamedSkillTargetReport",
    "build_nl_named_skill_target_report",
    "default_nl_named_skill_fixture_root",
    "default_nl_named_skill_manifest_path",
    "default_nl_named_skill_prompt_variant_path",
    "default_nl_named_skill_rubric_path",
    "load_nl_named_skill_manifest",
    "load_nl_named_skill_prompt_variants",
    "load_nl_named_skill_rubric",
    "official_nl_named_skill_target_ids",
    "representative_nl_named_skill_target_ids",
    "render_nl_named_skill_prompt",
    "write_nl_named_skill_report",
]
