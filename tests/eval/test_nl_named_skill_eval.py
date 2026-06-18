from __future__ import annotations

from pathlib import Path

from openminion_eval.skills import (
    NLNamedSkillPromptVariant,
    NLNamedSkillRubricDimension,
    NLNamedSkillScenario,
    build_nl_named_skill_target_report,
    load_nl_named_skill_manifest,
    load_nl_named_skill_prompt_variants,
    load_nl_named_skill_rubric,
    official_nl_named_skill_target_ids,
    render_nl_named_skill_prompt,
    representative_nl_named_skill_target_ids,
)


def test_nl_named_skill_manifest_and_contract_load_cleanly() -> None:
    manifest_version, scenarios = load_nl_named_skill_manifest()
    variant_version, prompt_variants = load_nl_named_skill_prompt_variants()
    rubric_version, rubric_dimensions = load_nl_named_skill_rubric()

    assert manifest_version == "1"
    assert variant_version == "1"
    assert rubric_version == "1"
    assert len(scenarios) == 10
    assert [variant.variant_id for variant in prompt_variants] == [
        "simple",
        "complex",
        "minimal",
    ]
    assert {dimension.dimension_id for dimension in rubric_dimensions} == {
        "selection_accuracy",
        "selection_confidence",
        "fallback_behavior",
        "prompt_sensitivity",
    }


def test_nl_named_skill_target_sets_match_expected_inventory() -> None:
    assert official_nl_named_skill_target_ids() == ("minimax-m2-5", "minimax-m2-7")
    assert representative_nl_named_skill_target_ids() == (
        "minimax-m2-5",
        "minimax-m2-7",
        "ollamacloud-glm-5",
        "ollamacloud-minimax-m2-7",
        "openrouter-minimax-m2-7",
        "openrouter-claude-haiku-4-5",
        "openrouter-gpt-4o",
    )


def test_render_nl_named_skill_prompt_variants() -> None:
    scenario = NLNamedSkillScenario(
        scenario_id="claude-api",
        skill_id="claude-api",
        fixture_path=Path("fixtures/claude-api/SKILL.md"),
        task_brief="building a chatbot",
    )
    variant = NLNamedSkillPromptVariant(
        variant_id="complex",
        label="Complex",
        prompt_template=(
            "Use skill {skill_id} and give me the first 4 adapted steps for "
            "{task_brief}."
        ),
    )

    assert render_nl_named_skill_prompt(scenario=scenario, variant=variant) == (
        "Use skill claude-api and give me the first 4 adapted steps for "
        "building a chatbot."
    )


def test_build_nl_named_skill_target_report_summarizes_variant_sensitivity(
    tmp_path: Path,
) -> None:
    session_id = "named-skill-session"
    agent_id = "demo-agent"

    success_transcript = tmp_path / f"{session_id}-success.txt"
    success_transcript.write_text(
        f"[{session_id}|{agent_id}] {agent_id}: selected claude-api\n",
        encoding="utf-8",
    )
    failure_transcript = tmp_path / f"{session_id}-failure.txt"
    failure_transcript.write_text(
        f"[{session_id}|{agent_id}] {agent_id}: I need more detail.\n",
        encoding="utf-8",
    )

    scenario = NLNamedSkillScenario(
        scenario_id="claude-api",
        skill_id="claude-api",
        fixture_path=tmp_path / "SKILL.md",
        task_brief="building a chatbot",
    )
    scenario.fixture_path.write_text("# demo", encoding="utf-8")
    prompt_variants = (
        NLNamedSkillPromptVariant(
            variant_id="simple",
            label="Simple",
            prompt_template="Use skill {skill_id}.",
        ),
        NLNamedSkillPromptVariant(
            variant_id="complex",
            label="Complex",
            prompt_template="Use skill {skill_id} for {task_brief}.",
        ),
        NLNamedSkillPromptVariant(
            variant_id="minimal",
            label="Minimal",
            prompt_template="{skill_id}",
        ),
    )
    rubric_dimensions = (
        NLNamedSkillRubricDimension(
            dimension_id="selection_accuracy",
            label="Selection accuracy",
            description="exact match",
        ),
        NLNamedSkillRubricDimension(
            dimension_id="selection_confidence",
            label="Selection confidence",
            description="correct event",
        ),
        NLNamedSkillRubricDimension(
            dimension_id="fallback_behavior",
            label="Fallback behavior",
            description="empty or wrong",
        ),
        NLNamedSkillRubricDimension(
            dimension_id="prompt_sensitivity",
            label="Prompt sensitivity",
            description="stable or variant-sensitive",
        ),
    )

    report = build_nl_named_skill_target_report(
        {
            "target_id": "demo-target",
            "agent_id": agent_id,
            "config_path": "fixtures/demo.json",
            "attempts": [
                {
                    "scenario_id": "claude-api",
                    "prompt_variant_id": "simple",
                    "prompt": "Use skill claude-api.",
                    "session_id": session_id,
                    "transcript": str(success_transcript),
                    "events": "fixtures/simple-events.json",
                    "skill_selected_event": True,
                    "selected_skill_id": "claude-api",
                    "selected_skill_ids": ["claude-api"],
                },
                {
                    "scenario_id": "claude-api",
                    "prompt_variant_id": "complex",
                    "prompt": "Use skill claude-api for building a chatbot.",
                    "session_id": session_id,
                    "transcript": str(success_transcript),
                    "events": "fixtures/complex-events.json",
                    "skill_selected_event": True,
                    "selected_skill_id": "claude-api",
                    "selected_skill_ids": ["claude-api"],
                },
                {
                    "scenario_id": "claude-api",
                    "prompt_variant_id": "minimal",
                    "prompt": "claude-api",
                    "session_id": session_id,
                    "transcript": str(failure_transcript),
                    "events": "fixtures/minimal-events.json",
                    "skill_selected_event": False,
                    "selected_skill_id": "",
                    "selected_skill_ids": [],
                },
            ],
        },
        manifest_version="1",
        scenarios=(scenario,),
        prompt_variant_version="1",
        prompt_variants=prompt_variants,
        rubric_version="1",
        rubric_dimensions=rubric_dimensions,
    )

    assert report.summary["attempt_count"] == 3
    assert report.summary["selection_accuracy_count"] == 2
    assert report.summary["selection_confidence_count"] == 2
    assert report.summary["empty_fallback_count"] == 1
    assert report.summary["wrong_skill_count"] == 0
    assert (
        report.summary["prompt_sensitivity_by_scenario"]["claude-api"]
        == "variant_sensitive"
    )
    assert report.summary["variant_summary"]["simple"]["selection_accuracy_count"] == 1
    assert report.attempts[-1].dimensions["fallback_behavior"] == "empty"
    assert report.attempts[0].dimensions["prompt_sensitivity"] == "variant_sensitive"
