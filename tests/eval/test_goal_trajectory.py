"""GTBH schema, runner, metrics, fixture, and aggregate tests."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import get_args

import pytest

from openminion_eval.goal_trajectory import (
    AggregateReport,
    BenchmarkRunner,
    GoalDriftSignalLike,
    GoalTrajectoryBenchmark,
    GoalTrajectoryReport,
    GoalTrajectoryStep,
    aggregate_reports,
    arike_metrics,
    fixture_high_pressure,
    fixture_low_pressure,
    fixture_mid_pressure,
    list_fixtures,
    run_benchmark,
)


def test_benchmark_validates_competing_objective_pressure_range():
    with pytest.raises(ValueError):
        GoalTrajectoryBenchmark(
            benchmark_id="b",
            goal_fixture="g",
            canonical_steps=(),
            competing_objective_pressure=1.5,
        )


def test_benchmark_is_frozen():
    b = fixture_low_pressure()
    with pytest.raises(FrozenInstanceError):
        b.benchmark_id = "x"  # type: ignore[misc]


def test_goal_drift_signal_kind_closed_set_matches_mrdd_owner():
    from openminion_eval.goal_trajectory.schemas import GoalDriftSignalKind as K

    args = get_args(K)
    assert set(args) == {
        "actions_diverge_from_criteria",
        "inaction_against_criteria",
        "objective_substitution",
        "mission_type_drift",
    }


def test_signal_like_carries_minimum_fields():
    sig = GoalDriftSignalLike(
        signal_id="s",
        goal_id="g",
        kind="inaction_against_criteria",
    )
    assert sig.kind == "inaction_against_criteria"


def test_runner_emits_per_kind_drift_counts():
    benchmark = fixture_mid_pressure()
    report = run_benchmark(benchmark)

    assert report.drift_count_by_kind.get("actions_diverge_from_criteria", 0) == 2


def test_runner_zero_drift_when_all_steps_advance():
    benchmark = GoalTrajectoryBenchmark(
        benchmark_id="b",
        goal_fixture="g",
        canonical_steps=tuple(
            GoalTrajectoryStep(
                step_index=i, action_token="advance", advances_criteria=True
            )
            for i in range(3)
        ),
        competing_objective_pressure=0.0,
    )
    report = run_benchmark(benchmark)
    assert report.drift_count_by_kind == {}


def test_runner_emits_mission_type_drift_at_high_pressure():
    benchmark = fixture_high_pressure()
    report = run_benchmark(benchmark)
    assert report.drift_count_by_kind.get("mission_type_drift", 0) > 0


def test_arike_gd_actions_counts_commission_kinds():
    signals = [
        GoalDriftSignalLike(
            signal_id="1", goal_id="g", kind="actions_diverge_from_criteria"
        ),
        GoalDriftSignalLike(signal_id="2", goal_id="g", kind="objective_substitution"),
        GoalDriftSignalLike(signal_id="3", goal_id="g", kind="mission_type_drift"),
        GoalDriftSignalLike(
            signal_id="4", goal_id="g", kind="inaction_against_criteria"
        ),
    ]
    gd_actions, gd_inaction = arike_metrics(signals)
    assert gd_actions == 3
    assert gd_inaction == 1


def test_arike_metrics_empty_input():
    gd_actions, gd_inaction = arike_metrics([])
    assert (gd_actions, gd_inaction) == (0, 0)


def test_report_surfaces_arike_metrics():
    report = run_benchmark(fixture_high_pressure())
    assert report.gd_actions > 0
    assert isinstance(report, GoalTrajectoryReport)


def test_three_fixtures_span_pressure_axis():
    pressures = [b.competing_objective_pressure for b in list_fixtures()]
    assert pressures[0] < pressures[1] < pressures[2]


def test_fixture_low_admits_some_inaction():
    benchmark = fixture_low_pressure()
    report = run_benchmark(benchmark)

    assert report.drift_count_by_kind.get("inaction_against_criteria", 0) >= 1


def test_fixture_drift_tolerance_violations_recorded():
    benchmark = fixture_high_pressure()
    report = run_benchmark(benchmark)

    assert "actions_diverge_from_criteria" in report.tolerance_violations
    assert report.tolerance_violations["actions_diverge_from_criteria"] >= 1


def test_aggregate_across_three_fixtures():
    reports = [run_benchmark(b) for b in list_fixtures()]
    agg = aggregate_reports(reports)
    assert isinstance(agg, AggregateReport)
    assert agg.benchmarks_run == 3
    assert agg.total_drift_count > 0
    assert agg.mean_gd_actions >= 0.0
    assert agg.mean_gd_inaction >= 0.0


def test_aggregate_pressure_correlation_positive_for_gd_actions():
    reports = [run_benchmark(b) for b in list_fixtures()]
    agg = aggregate_reports(reports)

    assert agg.pressure_correlation.get("gd_actions", 0.0) > 0.0


def test_aggregate_empty_returns_safe_defaults():
    agg = aggregate_reports([])
    assert agg.benchmarks_run == 0
    assert agg.total_drift_count == 0
    assert agg.mean_gd_actions == 0.0


def test_runner_accepts_custom_detector():
    def custom_detector(benchmark, step):
        return [
            GoalDriftSignalLike(
                signal_id=f"{benchmark.benchmark_id}-custom-{step.step_index}",
                goal_id=benchmark.goal_fixture,
                kind="objective_substitution",
            )
        ]

    runner = BenchmarkRunner(detector=custom_detector)
    report = runner.run(fixture_low_pressure())
    assert report.drift_count_by_kind.get("objective_substitution", 0) == 4


def test_e2e_smoke_three_fixtures_to_typed_report():
    reports: list[GoalTrajectoryReport] = []
    for benchmark in list_fixtures():
        report = run_benchmark(benchmark)

        assert report.total_steps > 0
        assert (
            report.competing_objective_pressure
            == benchmark.competing_objective_pressure
        )
        reports.append(report)

    agg = aggregate_reports(reports)
    assert agg.benchmarks_run == 3
    assert sum(agg.drift_count_by_kind.values()) > 0
    assert agg.mean_gd_actions > 0.0
