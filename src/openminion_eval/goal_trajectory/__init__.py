"""GTBH goal-trajectory benchmark harness.

Measures MRDD `GoalDriftSignal` emission against fixture trajectories
per Arike 2025 AIES `GD_actions` / `GD_inaction` formulation.
"""

from openminion_eval.goal_trajectory.schemas import (
    GoalDriftSignalKind,
    GoalDriftSignalLike,
    GoalTrajectoryBenchmark,
    GoalTrajectoryReport,
    GoalTrajectoryStep,
)
from openminion_eval.goal_trajectory.metrics import (
    arike_metrics,
)
from openminion_eval.goal_trajectory.runner import (
    BenchmarkRunner,
    run_benchmark,
)
from openminion_eval.goal_trajectory.fixtures import (
    fixture_low_pressure,
    fixture_mid_pressure,
    fixture_high_pressure,
    list_fixtures,
)
from openminion_eval.goal_trajectory.aggregate import (
    AggregateReport,
    aggregate_reports,
)

__all__ = [
    "AggregateReport",
    "BenchmarkRunner",
    "GoalDriftSignalKind",
    "GoalDriftSignalLike",
    "GoalTrajectoryBenchmark",
    "GoalTrajectoryReport",
    "GoalTrajectoryStep",
    "aggregate_reports",
    "arike_metrics",
    "fixture_high_pressure",
    "fixture_low_pressure",
    "fixture_mid_pressure",
    "list_fixtures",
    "run_benchmark",
]
