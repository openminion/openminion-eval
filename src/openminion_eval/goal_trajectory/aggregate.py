"""GTBH cross-goal aggregate reporting."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Sequence

from openminion_eval.goal_trajectory.schemas import GoalTrajectoryReport


@dataclass(frozen=True)
class AggregateReport:
    """Cross-benchmark aggregate statistics."""

    benchmarks_run: int
    total_drift_count: int
    mean_gd_actions: float
    mean_gd_inaction: float
    drift_count_by_kind: dict[str, int]
    pressure_correlation: dict[str, float]


def _safe_mean(values: list[int]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def aggregate_reports(reports: Sequence[GoalTrajectoryReport]) -> AggregateReport:
    n = len(reports)
    by_kind: dict[str, int] = defaultdict(int)
    gd_actions: list[int] = []
    gd_inaction: list[int] = []
    pressures: list[float] = []
    for r in reports:
        for kind, count in r.drift_count_by_kind.items():
            by_kind[kind] += count
        gd_actions.append(r.gd_actions)
        gd_inaction.append(r.gd_inaction)
        pressures.append(r.competing_objective_pressure)

    total_drift = sum(by_kind.values())
    mean_actions = _safe_mean(gd_actions)
    mean_inaction = _safe_mean(gd_inaction)

    pressure_corr: dict[str, float] = {}
    if n >= 2:
        pressure_corr["gd_actions"] = _simple_corr(pressures, gd_actions)
        pressure_corr["gd_inaction"] = _simple_corr(pressures, gd_inaction)

    return AggregateReport(
        benchmarks_run=n,
        total_drift_count=total_drift,
        mean_gd_actions=mean_actions,
        mean_gd_inaction=mean_inaction,
        drift_count_by_kind=dict(by_kind),
        pressure_correlation=pressure_corr,
    )


def _simple_corr(xs: list[float], ys: list[int]) -> float:
    n = len(xs)
    if n < 2 or len(ys) != n:
        return 0.0
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    cov = sum((xs[i] - mean_x) * (ys[i] - mean_y) for i in range(n))
    var_x = sum((xs[i] - mean_x) ** 2 for i in range(n))
    var_y = sum((ys[i] - mean_y) ** 2 for i in range(n))
    denom = (var_x * var_y) ** 0.5
    if denom == 0.0:
        return 0.0
    return cov / denom


__all__ = ["AggregateReport", "aggregate_reports"]
