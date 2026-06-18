"""Fixture-driven tests for the memory evaluation harness."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from openminion_eval import EvalRunner
from tests.eval.integration.memory_eval import (
    MemoryEvalEngineConfig,
    MemoryEvalFixtureLoader,
    MemoryEvalHarness,
)
from tests.eval.integration.memory_scorer import MemoryEvalScorer
from tests.eval.memory_quality_eval import (
    build_memory_quality_target_report,
    load_memory_quality_manifest,
    load_memory_quality_rubric,
    official_memory_quality_target_ids,
    representative_memory_quality_target_ids,
    run_memory_quality_source_report,
)
from openminion.base.config import OpenMinionConfig
from openminion.modules.memory.config import from_base_config
from openminion.modules.memory.service import MemoryService
from openminion.modules.storage.runtime.migrations import migrate_database
from openminion.modules.storage.runtime.session_store import SessionStore
from openminion.modules.storage.runtime.sqlite import connect_database
from openminion.services.agent.memory.gateway_adapter import MemoryServiceGatewayAdapter
from openminion.services.context.session import SessionContextService


FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "memory"
BASELINE_PATH = Path(__file__).parent / "baselines" / "memory_quality_baseline.json"
QUALITY_BASELINE_SUMMARY_PATH = (
    Path(__file__).parent
    / "baselines"
    / "memory_quality_representative_baseline"
    / "summary.json"
)


def _load_scenarios(*relative_dirs: str):
    loader = MemoryEvalFixtureLoader()
    scenarios = []
    for relative_dir in relative_dirs:
        scenarios.extend(loader.load_directory(FIXTURE_ROOT / relative_dir))
    return scenarios


def _make_engine_config(**overrides) -> MemoryEvalEngineConfig:
    def _session_context_factory(temp_root: Path) -> SessionContextService:
        db_path = temp_root / "state" / "openminion.db"
        migrate_database(db_path)
        connection = connect_database(db_path)
        return SessionContextService(
            SessionStore(connection),
            keep_recent_messages=20,
            max_compact_per_turn=100,
        )

    def _adapter_factory(
        service: MemoryService,
        engine_config: MemoryEvalEngineConfig,
    ) -> MemoryServiceGatewayAdapter:
        return MemoryServiceGatewayAdapter(
            service,
            agent_id=engine_config.agent_id,
            project_id=engine_config.project_id,
            memory_config=engine_config.memory_config,
            **engine_config.adapter_kwargs,
        )

    memory_config = from_base_config(
        base_config=OpenMinionConfig(),
        home_root=Path("fixtures/openminion-home"),
        data_root=Path("fixtures/openminion-data"),
    )

    return MemoryEvalEngineConfig(
        adapter_factory=_adapter_factory,
        session_context_factory=_session_context_factory,
        memory_config=memory_config,
        **overrides,
    )


def test_eval_runner_uses_injected_executor() -> None:
    runner = EvalRunner(agent_executor=lambda user_input: f"real:{user_input}")
    results = runner.replay_sync(
        transcript=type(
            "Transcript",
            (),
            {"turns": [{"user": "hello", "expected": "real:hello"}]},
        )()
    )

    assert results[0].actual == "real:hello"


def test_memory_eval_scorer_metrics() -> None:
    assert MemoryEvalScorer.recall_at_k(["a", "b", "c"], ["a", "d"], 3) == 0.5
    assert (
        pytest.approx(
            MemoryEvalScorer.precision_at_k(["a", "b", "c"], ["a", "d"], 3),
            rel=1e-3,
        )
        == 1.0 / 3.0
    )
    assert (
        MemoryEvalScorer.contradiction_leak_count(
            "deploy key rotates every 90 days",
            ["old key never rotates"],
        )
        == 0
    )
    assert (
        MemoryEvalScorer.contradiction_leak_count(
            "## Agent Memory\n"
            "  • actually tmux is never required during pairing sessions.\n"
            "  • tmux is required during pairing sessions.\n",
            ["tmux is required during pairing sessions"],
        )
        == 0
    )
    assert (
        MemoryEvalScorer.contradiction_leak_count(
            "## Agent Memory\n"
            "  • use mocks for network tests.\n"
            "  • avoid mocks for network tests.\n",
            ["use mocks for network tests"],
        )
        == 0
    )
    assert (
        MemoryEvalScorer.contradiction_leak_count(
            "## Agent Memory\n  • tmux is required during pairing sessions.\n",
            ["tmux is required during pairing sessions"],
        )
        == 1
    )
    assert MemoryEvalScorer.latency_gate(150.0, 200.0) is True


def test_memory_eval_fixture_loader_supports_generated_records() -> None:
    loader = MemoryEvalFixtureLoader()
    scenario = loader.load(FIXTURE_ROOT / "latency" / "scaling_100.yaml")

    assert scenario.scenario_id == "latency-scaling-100"
    assert scenario.setup.generated_records[0].count == 100


def test_memory_eval_fixture_loader_supports_seeded_candidates() -> None:
    loader = MemoryEvalFixtureLoader()
    scenario = loader.load(
        FIXTURE_ROOT / "capsule_precision" / "candidate_promotion_quality.yaml"
    )

    assert scenario.scenario_id == "candidate-promotion-quality"
    assert len(scenario.setup.candidates) == 4
    assert scenario.setup.candidates[0].meta["reconfirmation_count"] == 2
    assert scenario.setup.candidates[1].meta["retrieval_hit_count"] == 3


@pytest.mark.memory_eval
def test_memory_eval_harness_runs_lightweight_dimensions() -> None:
    harness = MemoryEvalHarness()
    scenarios = _load_scenarios(
        "cross_session_recall",
        "paraphrase_retrieval",
        "stale_suppression",
        "contradiction_leak",
        "capsule_precision",
    )

    report = harness.run(scenarios, engine_config=_make_engine_config())
    results = {item.scenario_id: item.metrics for item in report.scenario_results}

    assert (
        results["cross-session-basic-two-session"]["cross_session_recall.recall_at_5"]
        >= 0.8
    )
    assert (
        results["paraphrase-synonym-substitution"][
            "paraphrase_retrieval.paraphrase_recall_at_5"
        ]
        >= 0.6
    )
    assert (
        results["stale-suppression-keyed-supersession"][
            "stale_memory_suppression.leak_count"
        ]
        == 0
    )
    assert (
        results["stale-suppression-disuse-decay"]["stale_memory_suppression.leak_count"]
        == 0
    )
    assert results["contradiction-keyed-conflict"]["contradiction_leak.leak_count"] == 0
    assert (
        results["contradiction-paraphrased-conflict"]["contradiction_leak.leak_count"]
        == 0
    )
    assert (
        results["contradiction-type-aware-threshold"]["contradiction_leak.leak_count"]
        == 0
    )
    assert (
        results["capsule-precision-relevant-vs-irrelevant"][
            "capsule_precision.capsule_precision"
        ]
        >= 0.7
    )
    assert results["typed-memory-ranking"]["capsule_precision.capsule_precision"] >= 0.5
    assert (
        results["ranking-signal-composition"]["capsule_precision.capsule_precision"]
        >= 0.6
    )
    assert (
        results["candidate-promotion-quality"]["cross_session_recall.recall_at_5"]
        >= 1.0
    )
    assert (
        results["candidate-promotion-quality"]["capsule_precision.capsule_precision"]
        >= 0.8
    )
    assert (
        results["handoff-session-close-open"]["cross_session_recall.recall_at_5"] >= 1.0
    )
    assert (
        results["handoff-session-close-open"]["capsule_precision.capsule_precision"]
        >= 0.2
    )
    assert (
        results["capsule-reflection-insight-quality"][
            "capsule_precision.capsule_precision"
        ]
        >= 0.5
    )
    assert (
        results["promoted-correction-quality"]["capsule_precision.capsule_precision"]
        >= 0.5
    )
    assert (
        results["preference-stability-boost"]["cross_session_recall.recall_at_5"] >= 1.0
    )
    assert (
        results["outcome-feedback-precision-bias"][
            "capsule_precision.capsule_precision"
        ]
        >= 0.5
    )
    assert (
        results["outcome-utility-balanced-ranking"][
            "capsule_precision.capsule_precision"
        ]
        >= 0.3
    )
    assert (
        results["outcome-feedback-recall-boost"]["cross_session_recall.recall_at_5"]
        >= 1.0
    )


@pytest.mark.memory_eval
def test_memory_eval_harness_compare_flags_regression() -> None:
    harness = MemoryEvalHarness()
    scenarios = _load_scenarios("capsule_precision")
    baseline = harness.run(scenarios, engine_config=_make_engine_config())
    truncated = harness.run(
        scenarios,
        engine_config=_make_engine_config(
            name="mismatched-agent-scope",
            agent_id="other-agent",
        ),
    )

    comparison = harness.compare(baseline, truncated)
    statuses = {
        (entry.scenario_id, entry.metric_name): entry.status
        for entry in comparison.entries
    }

    assert (
        statuses[
            (
                "capsule-precision-relevant-vs-irrelevant",
                "capsule_precision.capsule_precision",
            )
        ]
        == "regressed"
    )


@pytest.mark.memory_eval
def test_memory_eval_semantic_session_summary_relevance_fixture() -> None:
    harness = MemoryEvalHarness()
    scenarios = _load_scenarios("cross_session_recall")

    report = harness.run(scenarios, engine_config=_make_engine_config())
    results = {item.scenario_id: item.metrics for item in report.scenario_results}

    assert (
        results["semantic-session-summary-relevance"][
            "cross_session_recall.recall_at_5"
        ]
        >= 1.0
    )


@pytest.mark.memory_eval
def test_memory_eval_baseline_snapshot_covers_all_dimensions() -> None:
    assert BASELINE_PATH.exists()
    payload = BASELINE_PATH.read_text(encoding="utf-8")

    for dimension in (
        "cross_session_recall",
        "paraphrase_retrieval",
        "stale_memory_suppression",
        "contradiction_leak",
        "capsule_precision",
        "latency_regression",
    ):
        assert dimension in payload
    assert "handoff-session-close-open" in payload
    assert "typed-memory-ranking" in payload
    assert "ranking-signal-composition" in payload
    assert "candidate-promotion-quality" in payload
    assert "promoted-correction-quality" in payload
    assert "preference-stability-boost" in payload
    assert "outcome-feedback-precision-bias" in payload
    assert "outcome-utility-balanced-ranking" in payload
    assert "outcome-feedback-recall-boost" in payload
    assert "stale-suppression-disuse-decay" in payload
    assert "contradiction-paraphrased-conflict" in payload
    assert "contradiction-type-aware-threshold" in payload
    assert "capsule-reflection-insight-quality" in payload


def test_memory_quality_manifest_and_rubric_load_cleanly() -> None:
    manifest_version, scenarios = load_memory_quality_manifest()
    rubric_version, rubric_dimensions = load_memory_quality_rubric()

    assert manifest_version == "1"
    assert rubric_version == "1"
    assert [scenario.scenario_id for scenario in scenarios] == [
        "preference_recall",
        "tool_outcome_recall",
        "artifact_continuity",
        "plan_resumption",
        "consolidation_quality",
    ]
    assert {dimension.dimension_id for dimension in rubric_dimensions} == {
        "recall_precision",
        "recall_relevance",
        "behavioral_influence",
        "promotion_quality",
        "noise_level",
    }


def test_memory_quality_target_sets_match_expected_inventory() -> None:
    assert official_memory_quality_target_ids() == ("minimax-m2-5", "minimax-m2-7")
    assert representative_memory_quality_target_ids() == (
        "minimax-m2-5",
        "minimax-m2-7",
        "ollamacloud-glm-5",
        "ollamacloud-minimax-m2-7",
        "openrouter-minimax-m2-7",
        "openrouter-claude-haiku-4-5",
        "openrouter-gpt-4o",
    )


def test_memory_quality_representative_baseline_snapshot_exists() -> None:
    assert QUALITY_BASELINE_SUMMARY_PATH.exists()
    payload = json.loads(QUALITY_BASELINE_SUMMARY_PATH.read_text(encoding="utf-8"))

    assert payload["execution_mode"] == "deterministic_memory_harness"
    assert payload["target_count"] == 7
    assert [target["target_id"] for target in payload["targets"]] == list(
        representative_memory_quality_target_ids()
    )
    assert all(
        set(target["dimension_summary"])
        == {
            "behavioral_influence",
            "noise_level",
            "promotion_quality",
            "recall_precision",
            "recall_relevance",
        }
        for target in payload["targets"]
    )


@pytest.mark.memory_eval
def test_memory_quality_report_assembles_from_existing_memory_harness() -> None:
    manifest_version, scenarios = load_memory_quality_manifest()
    rubric_version, rubric_dimensions = load_memory_quality_rubric()
    source_report = run_memory_quality_source_report(
        scenarios,
        engine_config=_make_engine_config(),
    )

    report = build_memory_quality_target_report(
        {
            "target_id": "demo-target",
            "agent_id": "demo-agent",
            "config_path": "fixtures/demo.json",
        },
        manifest_version=manifest_version,
        scenarios=scenarios,
        rubric_version=rubric_version,
        rubric_dimensions=rubric_dimensions,
        source_report=source_report,
    )

    assert report.target_id == "demo-target"
    assert report.execution_mode == "deterministic_memory_harness"
    assert report.summary["scenario_count"] == 5
    assert set(report.summary["dimension_summary"]) == {
        "behavioral_influence",
        "noise_level",
        "promotion_quality",
        "recall_precision",
        "recall_relevance",
    }
    assert all(
        0.0 <= score <= 1.0 for score in report.summary["dimension_summary"].values()
    )
    assert {
        scenario_report.scenario_id for scenario_report in report.scenario_results
    } == {
        "preference_recall",
        "tool_outcome_recall",
        "artifact_continuity",
        "plan_resumption",
        "consolidation_quality",
    }


@pytest.mark.memory_eval_benchmark
def test_memory_eval_latency_benchmark_suite() -> None:
    if os.environ.get("OPENMINION_RUN_MEMORY_EVAL_BENCHMARKS", "") != "1":
        pytest.skip("memory eval benchmarks disabled")

    harness = MemoryEvalHarness()
    scenarios = _load_scenarios("latency")
    report = harness.run(scenarios, engine_config=_make_engine_config())
    results = {item.scenario_id: item.metrics for item in report.scenario_results}

    assert results["latency-scaling-500"]["latency_regression.capsule_within_bound"]
    assert results["latency-scaling-500"]["latency_regression.retrieval_within_bound"]
    assert results["latency-scaling-1000"]["latency_regression.search_within_bound"]
