"""GTBH typed contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Mirrors openminion.modules.brain.schemas.goals.GoalDriftSignalKind.
GoalDriftSignalKind = Literal[
    "actions_diverge_from_criteria",
    "inaction_against_criteria",
    "objective_substitution",
    "mission_type_drift",
]


@dataclass(frozen=True)
class GoalDriftSignalLike:
    signal_id: str
    goal_id: str
    kind: GoalDriftSignalKind
    description: str = ""
    detected_at: str = ""


@dataclass(frozen=True)
class GoalTrajectoryStep:
    step_index: int
    action_token: str
    advances_criteria: bool = False
    introduces_competing_objective: bool = False


@dataclass(frozen=True)
class GoalTrajectoryBenchmark:
    benchmark_id: str
    goal_fixture: str
    canonical_steps: tuple[GoalTrajectoryStep, ...]
    competing_objective_pressure: float
    drift_tolerance: dict[str, int] = field(default_factory=dict)
    expected_drift_kinds: tuple[GoalDriftSignalKind, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not 0.0 <= self.competing_objective_pressure <= 1.0:
            raise ValueError("competing_objective_pressure must be in [0, 1]")


@dataclass(frozen=True)
class GoalTrajectoryReport:
    benchmark_id: str
    total_steps: int
    drift_count_by_kind: dict[str, int]
    gd_actions: int
    gd_inaction: int
    competing_objective_pressure: float
    tolerance_violations: dict[str, int] = field(default_factory=dict)


__all__ = [
    "GoalDriftSignalKind",
    "GoalDriftSignalLike",
    "GoalTrajectoryBenchmark",
    "GoalTrajectoryReport",
    "GoalTrajectoryStep",
]
