"""Typed AMEB Phase 2 report and task records."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from openminion.modules.brain.schemas import (
    Deliverable,
    FailureCondition,
    SuccessCriterion,
)
from openminion.modules.brain.schemas.missions import (
    ExploratoryDisclosure,
    MissionType,
    MissionVerifierExpectation,
)
from openminion.services.runtime.run_status import RunTerminalState


BenchmarkContaminationClass = Literal[
    "private_curated",
    "public_filtered",
    "public_modified",
    "synthetic",
]

BenchmarkDifficulty = Literal["simple", "moderate", "complex", "expert"]

BenchmarkOracleOutcome = Literal["pass", "fail", "partial", "disclosed"]

BenchmarkFailureTaxonomy = Literal[
    "oracle_failed",
    "budget_exhausted",
    "capability_boundary_hit",
    "clarification_blocked",
    "infrastructure_error",
    "partial_completion",
    "regression_detected",
]


@dataclass(frozen=True)
class BenchmarkTaskSpec:
    """Typed spec for one corpus task; drives the Phase 2 runner."""

    task_id: str
    mission_type: MissionType
    difficulty: BenchmarkDifficulty
    contamination_class: BenchmarkContaminationClass
    summary: str
    success_criteria: tuple[SuccessCriterion, ...]
    deliverables: tuple[Deliverable, ...]
    failure_conditions: tuple[FailureCondition, ...]


@dataclass(frozen=True)
class BenchmarkVerifierEvidence:
    """One captured-evidence ``VerifierResult`` row for a task."""

    family: str
    target_id: str
    target_kind: Literal["success_criterion", "deliverable"]
    passed: bool
    verdict: Literal["pass", "fail"]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class BenchmarkTaskOutcome:
    """Typed captured-evidence outcome for one corpus task."""

    task_id: str
    mission_type: MissionType
    difficulty: BenchmarkDifficulty
    contamination_class: BenchmarkContaminationClass
    goal_id: str
    run_id: str
    oracle_outcome: BenchmarkOracleOutcome
    failure_taxonomy: BenchmarkFailureTaxonomy | None
    run_terminal_state: RunTerminalState
    verifier_expectation: MissionVerifierExpectation
    exploratory_disclosure: ExploratoryDisclosure | None
    verifier_results: tuple[BenchmarkVerifierEvidence, ...]
    completion_confirmed: bool
    captured_at: str
    captured_evidence_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mission_type": self.mission_type,
            "difficulty": self.difficulty,
            "contamination_class": self.contamination_class,
            "goal_id": self.goal_id,
            "run_id": self.run_id,
            "oracle_outcome": self.oracle_outcome,
            "failure_taxonomy": self.failure_taxonomy,
            "run_terminal_state": self.run_terminal_state,
            "verifier_expectation": self.verifier_expectation.model_dump(mode="json"),
            "exploratory_disclosure": (
                self.exploratory_disclosure.model_dump(mode="json")
                if self.exploratory_disclosure is not None
                else None
            ),
            "verifier_results": [
                {
                    "family": row.family,
                    "target_id": row.target_id,
                    "target_kind": row.target_kind,
                    "passed": row.passed,
                    "verdict": row.verdict,
                    "reasons": list(row.reasons),
                }
                for row in self.verifier_results
            ],
            "completion_confirmed": self.completion_confirmed,
            "captured_at": self.captured_at,
            "captured_evidence_note": self.captured_evidence_note,
        }


@dataclass(frozen=True)
class BenchmarkDomainCoverage:
    """Typed per-``MissionType`` coverage row."""

    mission_type: MissionType
    task_count: int
    pass_count: int
    partial_count: int
    fail_count: int
    disclosed_count: int
    contamination_disclosure_flag: bool
    confidence_interval_note: str


BenchmarkPhase2Outcome = Literal[
    "baseline_captured",
    "baseline_partial",
    "measurement_blocked",
]


@dataclass(frozen=True)
class BenchmarkBaselineReport:
    """Aggregated Phase 2 captured-evidence baseline report."""

    report_version: str
    generated_at: str
    audited_head_sha: str
    eval_package_ref: str
    model_id: str
    runtime_context_note: str
    outcomes: tuple[BenchmarkTaskOutcome, ...]
    domain_coverage: tuple[BenchmarkDomainCoverage, ...]
    phase2_outcome: BenchmarkPhase2Outcome
    phase2_rationale: str
    supplemental_observations_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "audited_head_sha": self.audited_head_sha,
            "eval_package_ref": self.eval_package_ref,
            "model_id": self.model_id,
            "runtime_context_note": self.runtime_context_note,
            "outcomes": [row.to_dict() for row in self.outcomes],
            "domain_coverage": [
                {
                    "mission_type": row.mission_type,
                    "task_count": row.task_count,
                    "pass_count": row.pass_count,
                    "partial_count": row.partial_count,
                    "fail_count": row.fail_count,
                    "disclosed_count": row.disclosed_count,
                    "contamination_disclosure_flag": row.contamination_disclosure_flag,
                    "confidence_interval_note": row.confidence_interval_note,
                }
                for row in self.domain_coverage
            ],
            "phase2_outcome": self.phase2_outcome,
            "phase2_rationale": self.phase2_rationale,
            "supplemental_observations_note": self.supplemental_observations_note,
        }


__all__ = [
    "BenchmarkBaselineReport",
    "BenchmarkContaminationClass",
    "BenchmarkDifficulty",
    "BenchmarkDomainCoverage",
    "BenchmarkFailureTaxonomy",
    "BenchmarkOracleOutcome",
    "BenchmarkPhase2Outcome",
    "BenchmarkTaskOutcome",
    "BenchmarkTaskSpec",
    "BenchmarkVerifierEvidence",
]
