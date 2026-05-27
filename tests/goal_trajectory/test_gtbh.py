"""GTBH regression — schema + runner + metrics + fixtures + aggregate + E2E."""

from __future__ import annotations

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
from openminion_eval.goal_trajectory.schemas import GoalDriftSignalKind  # noqa: F401


# --- GTBH-01 schema ---


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
    with pytest.raises(Exception):
        b.benchmark_id = "x"  # type: ignore[misc]


def test_goal_drift_signal_kind_closed_set_matches_mrdd_owner():
    """GTBH's mirror of MRDD's closed-set vocab must list exactly 4 values."""

    import typing

    from openminion_eval.goal_trajectory.schemas import GoalDriftSignalKind as K

    args = typing.get_args(K)
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


# --- GTBH-02 runner ---


def test_runner_emits_per_kind_drift_counts():
    benchmark = fixture_mid_pressure()
    report = run_benchmark(benchmark)
    # Mid-pressure has 2 competing steps → 2 actions_diverge_from_criteria
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


# --- GTBH-03 Arike metrics ---


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


# --- GTBH-04 fixtures ---


def test_three_fixtures_span_pressure_axis():
    pressures = [b.competing_objective_pressure for b in list_fixtures()]
    assert pressures[0] < pressures[1] < pressures[2]


def test_fixture_low_admits_some_inaction():
    benchmark = fixture_low_pressure()
    report = run_benchmark(benchmark)
    # Low-pressure has at least one inaction step
    assert report.drift_count_by_kind.get("inaction_against_criteria", 0) >= 1


def test_fixture_drift_tolerance_violations_recorded():
    benchmark = fixture_high_pressure()
    report = run_benchmark(benchmark)
    # 5 competing steps × actions_diverge → exceed tolerance of 1
    assert "actions_diverge_from_criteria" in report.tolerance_violations
    assert report.tolerance_violations["actions_diverge_from_criteria"] >= 1


# --- GTBH-05 aggregate ---


def test_aggregate_across_three_fixtures():
    reports = [run_benchmark(b) for b in list_fixtures()]
    agg = aggregate_reports(reports)
    assert isinstance(agg, AggregateReport)
    assert agg.benchmarks_run == 3
    assert agg.total_drift_count > 0
    assert agg.mean_gd_actions >= 0.0
    assert agg.mean_gd_inaction >= 0.0


def test_aggregate_pressure_correlation_positive_for_gd_actions():
    """Higher pressure should correlate positively with gd_actions."""

    reports = [run_benchmark(b) for b in list_fixtures()]
    agg = aggregate_reports(reports)
    # We expect positive correlation since high-pressure fixture has more drift
    assert agg.pressure_correlation.get("gd_actions", 0.0) > 0.0


def test_aggregate_empty_returns_safe_defaults():
    agg = aggregate_reports([])
    assert agg.benchmarks_run == 0
    assert agg.total_drift_count == 0
    assert agg.mean_gd_actions == 0.0


# --- GTBH-02 custom detector ---


def test_runner_accepts_custom_detector():
    """A test-supplied detector replaces the default rule-based one."""

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


# --- GTBH-06 E2E smoke ---


def test_e2e_smoke_three_fixtures_to_typed_report():
    """End-to-end: 3 fixtures → 3 typed reports → 1 typed aggregate."""

    reports: list[GoalTrajectoryReport] = []
    for benchmark in list_fixtures():
        report = run_benchmark(benchmark)
        # Each report carries the typed Arike metrics + pressure.
        assert report.total_steps > 0
        assert (
            report.competing_objective_pressure
            == benchmark.competing_objective_pressure
        )
        reports.append(report)

    agg = aggregate_reports(reports)
    assert agg.benchmarks_run == 3
    # At least one kind of drift was observed across the suite.
    assert sum(agg.drift_count_by_kind.values()) > 0
    # GD_actions present across the high/mid fixtures.
    assert agg.mean_gd_actions > 0.0
