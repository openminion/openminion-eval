"""GTBH typed contracts.

`GoalDriftSignalKind` mirrors MRDD's closed-set vocabulary verbatim
(canonical owner: `openminion.modules.brain.schemas.goals.GoalDriftSignalKind`).
This standalone copy exists because `openminion-eval` ships as an
independent package with `dependencies = []` — it cannot import from
the main openminion tree at runtime.  The values MUST stay in lock-step
with the MRDD owner; widening requires a separate review on the MRDD
side and a mirrored update here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


# Closed-set vocabulary — keep in lock-step with MRDD's
# `openminion.modules.brain.schemas.goals.GoalDriftSignalKind`.
GoalDriftSignalKind = Literal[
    "actions_diverge_from_criteria",
    "inaction_against_criteria",
    "objective_substitution",
    "mission_type_drift",
]


@dataclass(frozen=True)
class GoalDriftSignalLike:
    """Duck-typed view of MRDD's GoalDriftSignal for cross-package use.

    Carries the structural fields GTBH needs from a `GoalDriftSignal`
    emission.  When running against the live openminion runtime, a
    GoalDriftSignal instance can be converted into this shape with
    a tiny shim; the benchmark harness reads only these fields.
    """

    signal_id: str
    goal_id: str
    kind: GoalDriftSignalKind
    description: str = ""
    detected_at: str = ""


@dataclass(frozen=True)
class GoalTrajectoryStep:
    """One step in a fixture trajectory."""

    step_index: int
    action_token: str
    advances_criteria: bool = False
    introduces_competing_objective: bool = False


@dataclass(frozen=True)
class GoalTrajectoryBenchmark:
    """Typed fixture benchmark — drives a goal through `canonical_steps`
    + applies `competing_objective_pressure` per Arike 2025."""

    benchmark_id: str
    goal_fixture: str
    canonical_steps: tuple[GoalTrajectoryStep, ...]
    competing_objective_pressure: float
    drift_tolerance: dict[str, int] = field(default_factory=dict)
    expected_drift_kinds: tuple[GoalDriftSignalKind, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:  # pragma: no cover - simple guards
        if not 0.0 <= self.competing_objective_pressure <= 1.0:
            raise ValueError("competing_objective_pressure must be in [0, 1]")


@dataclass(frozen=True)
class GoalTrajectoryReport:
    """Typed per-benchmark report — Arike 2025 vocabulary."""

    benchmark_id: str
    total_steps: int
    drift_count_by_kind: dict[str, int]
    gd_actions: int  # Arike GD_actions count (commission)
    gd_inaction: int  # Arike GD_inaction count (omission)
    competing_objective_pressure: float
    tolerance_violations: dict[str, int] = field(default_factory=dict)


__all__ = [
    "GoalDriftSignalKind",
    "GoalDriftSignalLike",
    "GoalTrajectoryBenchmark",
    "GoalTrajectoryReport",
    "GoalTrajectoryStep",
]
