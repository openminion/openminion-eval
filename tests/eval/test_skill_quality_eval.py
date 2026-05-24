from __future__ import annotations

import json
from pathlib import Path

from openminion_eval.skills import (
    SkillQualityRubricDimension,
    SkillQualityScenario,
    build_skill_quality_target_report,
    default_skill_quality_manifest_path,
    iter_routing_target_records,
    load_skill_quality_manifest,
    load_skill_quality_rubric,
    official_skill_quality_target_ids,
    representative_skill_quality_target_ids,
)


def test_skill_quality_manifest_and_rubric_load_cleanly() -> None:
    assert default_skill_quality_manifest_path().name == "manifest.json"
    manifest_version, scenarios = load_skill_quality_manifest()
    rubric_version, rubric_dimensions = load_skill_quality_rubric()

    assert manifest_version == "1"
    assert rubric_version == "1"
    assert len(scenarios) == 10
    assert len(rubric_dimensions) == 5
    assert {scenario.scenario_id for scenario in scenarios} == {
        "claude-api",
        "news_digest",
        "mcp_builder",
        "web_artifacts_builder",
        "webapp-testing",
        "github_pr",
        "data_export",
        "figma_code_connect_components",
        "figma_generate_design",
        "playwright",
    }


def test_skill_quality_target_sets_match_expected_inventory() -> None:
    assert official_skill_quality_target_ids() == ("minimax-m2-5", "minimax-m2-7")
    assert representative_skill_quality_target_ids() == (
        "ollamacloud-glm-5",
        "ollamacloud-minimax-m2-7",
        "openrouter-minimax-m2-7",
        "openrouter-claude-haiku-4-5",
        "openrouter-gpt-4o",
    )


def test_iter_routing_target_records_accepts_aggregate_and_per_target_payload(
    tmp_path: Path,
) -> None:
    aggregate_path = tmp_path / "summary.json"
    aggregate_path.write_text(
        json.dumps(
            {
                "targets": [
                    {
                        "target": "aggregate-target",
                        "agent_id": "aggregate-agent",
                        "config_path": "/tmp/aggregate.json",
                        "results": [],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    direct_path = tmp_path / "direct-target.json"
    direct_path.write_text(
        json.dumps(
            {
                "target": "direct-target",
                "agent_id": "direct-agent",
                "config_path": "/tmp/direct.json",
                "results": [],
            }
        ),
        encoding="utf-8",
    )

    records = iter_routing_target_records([aggregate_path, direct_path])
    assert [record["target"] for record in records] == [
        "aggregate-target",
        "direct-target",
    ]
    assert all(record["routing_artifact"].endswith(".json") for record in records)


def test_build_skill_quality_target_report_reads_transcript_and_builds_slots(
    tmp_path: Path,
) -> None:
    session_id = "skill-quality-session"
    agent_id = "demo-agent"
    transcript_path = tmp_path / f"{session_id}.txt"
    transcript_path.write_text(
        (
            f"[{session_id}|{agent_id}] {agent_id}: 1. Step one\n"
            "2. Step two\n"
            "3. Step three\n"
            "4. Step four\n"
            "Verification: run the tests.\n"
            "Guardrail: do not skip auth checks.\n"
        ),
        encoding="utf-8",
    )

    scenario = SkillQualityScenario(
        scenario_id="demo-skill",
        skill_id="demo-skill",
        fixture_path=tmp_path / "SKILL.md",
        prompt="Use the demo-skill workflow for this task.",
        evaluation_dimensions=("on_skill_fidelity", "guardrail_quality"),
    )
    scenario.fixture_path.write_text("# demo", encoding="utf-8")
    rubric_dimensions = (
        SkillQualityRubricDimension(
            dimension_id="on_skill_fidelity",
            label="On-skill fidelity",
            reviewer_prompt="stay on skill",
            scale=("weak", "mixed", "strong"),
        ),
        SkillQualityRubricDimension(
            dimension_id="guardrail_quality",
            label="Guardrail quality",
            reviewer_prompt="guardrail useful",
            scale=("weak", "mixed", "strong"),
        ),
    )

    report = build_skill_quality_target_report(
        {
            "target": "demo-target",
            "agent_id": agent_id,
            "config_path": "/tmp/demo.json",
            "routing_artifact": "/tmp/routing.json",
            "results": [
                {
                    "scenario": "demo-skill",
                    "expected_skill_id": "demo-skill",
                    "selected_skill_id": "demo-skill",
                    "selected_skill_ids": ["demo-skill"],
                    "transcript": str(transcript_path),
                    "events": "/tmp/demo-events.json",
                }
            ],
        },
        manifest_version="1",
        scenarios=(scenario,),
        rubric_version="1",
        rubric_dimensions=rubric_dimensions,
    )

    assert report.target_id == "demo-target"
    assert report.summary["scenario_count"] == 1
    assert report.summary["routing_match_count"] == 1
    assert report.summary["responses_with_numbered_steps"] == 1
    assert report.summary["responses_with_verification_language"] == 1
    assert report.summary["responses_with_guardrail_language"] == 1
    assert report.scenario_results[0].assistant_output.startswith("1. Step one")
    assert report.scenario_results[0].rubric_slots[0]["status"] == "pending_review"
