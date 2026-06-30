"""Named-skill routing eval helpers and report builders."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import json
from pathlib import Path
from typing import Any, Callable

from openminion_eval.family_support import report_generated_at
from openminion_eval.paths import skill_fixture_root
from openminion_eval.skills.constants import (
    CANONICAL_EVAL_FAMILY,
    FALLBACK_BEHAVIOR_CORRECT,
    FALLBACK_BEHAVIOR_EMPTY,
    FALLBACK_BEHAVIOR_WRONG_SKILL,
    FAMILY_REPORT_VERSION,
    PROMPT_SENSITIVITY_STABLE_FAILURE,
    PROMPT_SENSITIVITY_STABLE_SUCCESS,
    PROMPT_SENSITIVITY_VARIANT_SENSITIVE,
)
from openminion_eval.skills.support import (
    assistant_output_from_record,
    load_skill_json,
    official_skill_matrix_target_ids,
    required_skill_fixture,
    representative_nl_named_skill_target_ids as _representative_nl_named_skill_target_ids,
    unique_skill_id,
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
    return skill_fixture_root("nl_named_skill")


def default_nl_named_skill_manifest_path() -> Path:
    return default_nl_named_skill_fixture_root() / "manifest.json"


def default_nl_named_skill_prompt_variant_path() -> Path:
    return default_nl_named_skill_fixture_root() / "prompt_variants.json"


def default_nl_named_skill_rubric_path() -> Path:
    return default_nl_named_skill_fixture_root() / "rubric.json"


def load_nl_named_skill_manifest(
    path: str | Path | None = None,
) -> tuple[str, tuple[NLNamedSkillScenario, ...]]:
    manifest_path = (
        Path(path) if path is not None else default_nl_named_skill_manifest_path()
    )
    version, payload = load_skill_json(manifest_path, "NL named-skill manifest")

    scenarios: list[NLNamedSkillScenario] = []
    seen_ids: set[str] = set()
    for item in payload.get("scenarios", []):
        scenario_id = unique_skill_id(item, "scenario_id", seen_ids)
        fixture_path = required_skill_fixture(
            item.get("fixture_path"),
            "NL named-skill scenario",
            scenario_id,
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
    version, payload = load_skill_json(variant_path, "NL named-skill prompt variant")

    variants: list[NLNamedSkillPromptVariant] = []
    seen_ids: set[str] = set()
    for item in payload.get("variants", []):
        variant_id = unique_skill_id(item, "variant_id", seen_ids)
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
    version, payload = load_skill_json(rubric_path, "NL named-skill rubric")

    dimensions: list[NLNamedSkillRubricDimension] = []
    seen_ids: set[str] = set()
    for item in payload.get("dimensions", []):
        dimension_id = unique_skill_id(item, "dimension_id", seen_ids)
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
            result[scenario_id] = PROMPT_SENSITIVITY_STABLE_SUCCESS
        elif any(outcomes):
            result[scenario_id] = PROMPT_SENSITIVITY_VARIANT_SENSITIVE
        else:
            result[scenario_id] = PROMPT_SENSITIVITY_STABLE_FAILURE
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
    now_provider: Callable[[], str] = report_generated_at,
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
    seen_attempt_keys: set[tuple[str, str]] = set()
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
        attempt_key = (scenario_id, prompt_variant_id)
        if attempt_key in seen_attempt_keys:
            raise ValueError(
                "duplicate NL named-skill attempt for "
                f"scenario={scenario_id!r} prompt_variant={prompt_variant_id!r}"
            )
        seen_attempt_keys.add(attempt_key)
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
            fallback_behavior = FALLBACK_BEHAVIOR_CORRECT
        elif selected_skill_id:
            fallback_behavior = FALLBACK_BEHAVIOR_WRONG_SKILL
        else:
            fallback_behavior = FALLBACK_BEHAVIOR_EMPTY

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
                assistant_output=assistant_output_from_record(
                    item,
                    agent_id=agent_id,
                    session_id=str(item.get("session_id", "") or "").strip(),
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

    expected_attempt_keys = {
        (scenario.scenario_id, variant.variant_id)
        for scenario in scenarios
        for variant in prompt_variants
    }
    if seen_attempt_keys != expected_attempt_keys:
        missing = sorted(expected_attempt_keys - seen_attempt_keys)
        extra = sorted(seen_attempt_keys - expected_attempt_keys)
        raise ValueError(
            "NL named-skill attempt coverage mismatch for "
            f"{target_id or agent_id}: missing={missing} extra={extra}"
        )

    sensitivity_map = _prompt_sensitivity_by_scenario(attempts)
    updated_attempts: list[NLNamedSkillAttemptReport] = []
    for attempt in attempts:
        dimensions = dict(attempt.dimensions)
        dimensions["prompt_sensitivity"] = sensitivity_map[attempt.scenario_id]
        updated_attempts.append(replace(attempt, dimensions=dimensions))

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
                1
                for attempt in relevant
                if attempt.fallback_behavior == FALLBACK_BEHAVIOR_EMPTY
            ),
            "wrong_skill_count": sum(
                1
                for attempt in relevant
                if attempt.fallback_behavior == FALLBACK_BEHAVIOR_WRONG_SKILL
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
            1
            for attempt in updated_attempts
            if attempt.fallback_behavior == FALLBACK_BEHAVIOR_EMPTY
        ),
        "wrong_skill_count": sum(
            1
            for attempt in updated_attempts
            if attempt.fallback_behavior == FALLBACK_BEHAVIOR_WRONG_SKILL
        ),
        "variant_summary": variant_summary,
        "prompt_sensitivity_by_scenario": sensitivity_map,
    }

    return NLNamedSkillTargetReport(
        report_version=FAMILY_REPORT_VERSION,
        generated_at=now_provider(),
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
