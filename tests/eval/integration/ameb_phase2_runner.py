"""Typed Phase 2 AMEB baseline runner for captured-evidence task scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from openminion.base.common.time import utc_now_iso
from openminion.modules.brain.diagnostics.canonical_events import CanonicalEventLogger
from openminion.modules.brain.runtime.policy_verify import (
    VerifierInvocation,
    VerifierResult,
    is_run_completion_confirmed,
    run_verifier,
)
from openminion.modules.brain.schemas import (
    ActionResult,
    Deliverable,
    FailureCondition,
    Goal,
    SuccessCriterion,
    VerificationMode,
    WorkingState,
)
from openminion.modules.brain.schemas.commands import ToolCommand
from openminion.modules.brain.schemas.missions import (
    ExploratoryDisclosure,
    MissionType,
    MissionVerifierExpectation,
    get_mission_verifier_expectation,
    should_emit_exploratory_disclosure,
)
from openminion.services.gateway.typed_goal_source import BenchmarkHarnessTurnIntent
from openminion.services.runtime.run_status import (
    RUN_TERMINAL_BLOCKED,
    RUN_TERMINAL_COMPLETED,
    RUN_TERMINAL_FAILED,
    RunTerminalState,
    is_run_terminal_state,
)


# ---------------------------------------------------------------------------
# Typed captured-evidence schemas
# ---------------------------------------------------------------------------


BenchmarkContaminationClass = Literal[
    "private_curated",
    "public_filtered",
    "public_modified",
    "synthetic",
]

BenchmarkDifficulty = Literal["simple", "moderate", "complex", "expert"]

BenchmarkOracleOutcome = Literal["pass", "fail", "partial", "disclosed"]

# Closed seven-value failure taxonomy per the frozen 2026-05-13 artifact §4.
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
    """Typed spec for one corpus task — drives the Phase 2 runner."""

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


# Phase 2 outcomes per the AMEB spec §5.
BenchmarkPhase2Outcome = Literal[
    "baseline_captured",
    "baseline_partial",
    "measurement_blocked",
]


@dataclass(frozen=True)
class BenchmarkBaselineReport:
    """Aggregated Phase 2 captured-evidence baseline report.

    Maps 1:1 onto the §1-§7 sections of the published Phase 2 baseline
    artifact.
    """

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


# ---------------------------------------------------------------------------
# Stub session + working-state helpers (verifier surface needs these inputs)
# ---------------------------------------------------------------------------


class _StubSessionApi:
    """Captures ``CanonicalEventLogger`` emissions without a real store.

    The verifier surface emits ``verifier.completed`` (and the existing
    ``verify.completed``) events; the harness records them as a flat
    event list for evidence capture. Same pattern as
    ``tests/brain/test_tgcr_verifier_contract.py``.
    """

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def append_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict[str, Any],
        **_: Any,
    ) -> str:
        self.events.append((event_type, dict(payload)))
        return f"event-{len(self.events)}"


def _build_working_state(session_id: str, agent_id: str, trace_id: str) -> WorkingState:
    return WorkingState(
        session_id=session_id,
        agent_id=agent_id,
        budgets_remaining={
            "ticks": 1,
            "tool_calls": 1,
            "a2a_calls": 0,
            "tokens": 100,
            "time_ms": 1000,
        },
        trace_id=trace_id,
    )


def _build_logger(session_id: str, agent_id: str) -> CanonicalEventLogger:
    return CanonicalEventLogger(
        session_api=_StubSessionApi(),
        session_id=session_id,
        agent_id=agent_id,
    )


# ---------------------------------------------------------------------------
# Corpus — verbatim from the frozen 2026-05-13 artifact §2
# ---------------------------------------------------------------------------


def _coding_simple_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-coding-01",
        mission_type="coding",
        difficulty="simple",
        contamination_class="private_curated",
        summary="Update a bounded function and satisfy one focused test file.",
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-coding-01-sc-tests-pass",
                description="Focused pytest target passes after the edit.",
                structural_check="success_criteria.tests_passed=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-coding-01-sc-lint-clean",
                description="ruff check on touched surface stays clean.",
                structural_check="success_criteria.ruff_clean=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-coding-01-d-patch-artifact",
                description="Patch artifact describing edited file set.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-coding-01-fc-tests-failed",
                kind="success_criterion_unmet",
                description="Target test file did not pass after the edit.",
            ),
        ),
    )


def _coding_complex_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-coding-02",
        mission_type="coding",
        difficulty="complex",
        contamination_class="private_curated",
        summary="Change a multi-file workflow and satisfy focused tests + lint.",
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-coding-02-sc-tests-pass",
                description="Focused multi-file pytest target passes.",
                structural_check="success_criteria.tests_passed=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-coding-02-sc-changed-files-scoped",
                description="Changed-file set matches declared task scope.",
                structural_check="success_criteria.changed_files_in_scope=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-coding-02-sc-lint-clean",
                description="ruff check on touched surface stays clean.",
                structural_check="success_criteria.ruff_clean=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-coding-02-d-multi-file-patch",
                description="Multi-file patch artifact across declared workflow.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-coding-02-fc-scope-violation",
                kind="success_criterion_unmet",
                description="Changed-file set extended beyond declared scope.",
            ),
            FailureCondition(
                condition_id="ameb-coding-02-fc-budget",
                kind="budget_exhausted",
                description="Run exceeded the SBSP budget cap before completion.",
            ),
        ),
    )


def _research_moderate_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-research-01",
        mission_type="research",
        difficulty="moderate",
        contamination_class="private_curated",
        summary=(
            "Produce typed findings from repo-local reference docs with "
            "explicit source coverage."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-research-01-sc-source-count",
                description="Typed findings payload covers >= 2 sources.",
                structural_check="success_criteria.source_count_ge_2=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-research-01-sc-contradiction-free",
                description="Typed findings carry no contradictory pair.",
                structural_check="success_criteria.contradiction_free=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-research-01-d-findings",
                description="Typed findings[] payload with source refs.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-research-01-fc-coverage",
                kind="success_criterion_unmet",
                description="Findings payload did not cover the required >=2 sources.",
            ),
        ),
    )


def _research_complex_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-research-02",
        mission_type="research",
        difficulty="complex",
        contamination_class="public_modified",
        summary=(
            "Compare two external sources plus one repo-local source and "
            "emit contradiction-free typed findings."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-research-02-sc-source-count",
                description="Typed findings payload covers >= 3 sources.",
                structural_check="success_criteria.source_count_ge_3=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-research-02-sc-contradiction-free",
                description="Typed findings carry no contradictory pair.",
                structural_check="success_criteria.contradiction_free=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-research-02-sc-freshness",
                description="Freshness obligations met for external sources.",
                structural_check="success_criteria.freshness_met=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-research-02-d-comparative-findings",
                description="Typed comparative findings[] payload with source refs.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-research-02-fc-contradiction",
                kind="success_criterion_unmet",
                description="A contradictory finding pair was detected.",
            ),
        ),
    )


def _ops_moderate_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-ops-01",
        mission_type="operations",
        difficulty="moderate",
        contamination_class="private_curated",
        summary=(
            "Execute a bounded runtime/config workflow with observable side "
            "effect and idempotent rerun."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-ops-01-sc-side-effect-observed",
                description="Targeted command produced the declared side effect.",
                structural_check="success_criteria.side_effect_observed=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-ops-01-sc-idempotent-rerun",
                description="Second run leaves the system stable / no-op.",
                structural_check="success_criteria.idempotent_rerun=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-ops-01-d-health-status",
                description="Typed health/status check artifact.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-ops-01-fc-side-effect-missing",
                kind="success_criterion_unmet",
                description="Declared side effect was not observed.",
            ),
        ),
    )


def _ops_complex_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-ops-02",
        mission_type="operations",
        difficulty="complex",
        contamination_class="private_curated",
        summary=(
            "Recover a known-bad local state to a healthy typed status "
            "without violating safety gates."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-ops-02-sc-recovered",
                description="Local state typed-healthy after recovery.",
                structural_check="success_criteria.state_recovered=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-ops-02-sc-safety-gates-clean",
                description="Safety gates not violated during recovery.",
                structural_check="success_criteria.safety_gates_clean=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-ops-02-sc-idempotent-rerun",
                description="Recovery sequence is idempotent on rerun.",
                structural_check="success_criteria.idempotent_rerun=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-ops-02-d-recovery-trace",
                description="Recovery trace artifact with typed status.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-ops-02-fc-safety-violation",
                kind="capability_boundary",
                description="Recovery attempt violated a safety gate.",
            ),
            FailureCondition(
                condition_id="ameb-ops-02-fc-state-not-recovered",
                kind="success_criterion_unmet",
                description="Local state remained unhealthy after recovery.",
            ),
        ),
    )


def _explore_simple_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-explore-01",
        mission_type="exploratory",
        difficulty="simple",
        contamination_class="private_curated",
        summary=(
            "Reconnoiter a code area and emit typed ExploratoryDisclosure "
            "instead of false completion."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-explore-01-sc-disclosure-emitted",
                description="ExploratoryDisclosure emitted at run start.",
                structural_check="success_criteria.disclosure_emitted=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-explore-01-sc-no-false-completion",
                description="No completion-verifier success fired.",
                structural_check="success_criteria.no_false_completion=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-explore-01-d-evidence-refs",
                description="Evidence refs collected during reconnaissance.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-explore-01-fc-false-success",
                kind="success_criterion_unmet",
                description="Run claimed completion without verifier confirmation.",
            ),
        ),
    )


def _explore_complex_spec() -> BenchmarkTaskSpec:
    return BenchmarkTaskSpec(
        task_id="ameb-explore-02",
        mission_type="exploratory",
        difficulty="complex",
        contamination_class="public_filtered",
        summary=(
            "Investigate an open-ended external question and terminate "
            "with explicit exploratory disclosure plus evidence refs."
        ),
        success_criteria=(
            SuccessCriterion(
                criterion_id="ameb-explore-02-sc-disclosure-emitted",
                description="ExploratoryDisclosure emitted at run start.",
                structural_check="success_criteria.disclosure_emitted=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-explore-02-sc-evidence-collected",
                description="Evidence refs gathered during investigation.",
                structural_check="success_criteria.evidence_collected=true",
            ),
            SuccessCriterion(
                criterion_id="ameb-explore-02-sc-no-false-completion",
                description="No completion-verifier success fired.",
                structural_check="success_criteria.no_false_completion=true",
            ),
        ),
        deliverables=(
            Deliverable(
                deliverable_id="ameb-explore-02-d-investigation-refs",
                description="Typed investigation evidence refs.",
                verification_hint="artifact_presence",
            ),
        ),
        failure_conditions=(
            FailureCondition(
                condition_id="ameb-explore-02-fc-false-success",
                kind="success_criterion_unmet",
                description="Run claimed completion without verifier confirmation.",
            ),
        ),
    )


def build_ameb_corpus() -> tuple[BenchmarkTaskSpec, ...]:
    """Return the frozen 8-task corpus in the canonical order."""
    return (
        _coding_simple_spec(),
        _coding_complex_spec(),
        _research_moderate_spec(),
        _research_complex_spec(),
        _ops_moderate_spec(),
        _ops_complex_spec(),
        _explore_simple_spec(),
        _explore_complex_spec(),
    )


# ---------------------------------------------------------------------------
# Per-task execution: typed Goal -> VerifierResult -> RunTerminalState
# ---------------------------------------------------------------------------


def _build_goal_from_spec(spec: BenchmarkTaskSpec) -> Goal:
    return Goal(
        goal_id=f"goal-{spec.task_id}",
        description=spec.summary,
        success_criteria=list(spec.success_criteria),
        deliverables=list(spec.deliverables),
        failure_conditions=list(spec.failure_conditions),
    )


def build_benchmark_harness_turn_intent(
    spec: BenchmarkTaskSpec,
) -> BenchmarkHarnessTurnIntent:
    """Build the GTGS-owned typed intent for one AMEB corpus task.

    This is the first benchmark-harness-side production caller shape
    for GTGS: a closed, structured record that the gateway can consume
    without any freeform goal synthesis.
    """

    return BenchmarkHarnessTurnIntent(
        goal_id=f"goal-{spec.task_id}",
        corpus_task_id=spec.task_id,
        description=spec.summary,
        mission_type=spec.mission_type,
        success_criteria=tuple(spec.success_criteria),
        deliverables=tuple(spec.deliverables),
        failure_conditions=tuple(spec.failure_conditions),
    )


async def run_gateway_benchmark_turn(
    *,
    gateway,
    spec: BenchmarkTaskSpec,
    channel: str = "console",
    target: str = "ameb-phase2",
    session_id: str | None = None,
):
    """Drive one corpus task through the production gateway path.

    This helper is intentionally thin: it constructs the GTGS-owned
    benchmark-harness intent and threads it through ``GatewayService``.
    Scoring remains out of scope here; GTGS uses this as structural
    evidence that the typed-goal source now reaches ALVB's production
    choke point without test-side resolver injection.
    """

    return await gateway.run_once(
        channel=channel,
        target=target,
        message=spec.summary,
        session_id=session_id,
        typed_turn_intent=build_benchmark_harness_turn_intent(spec),
        capability_category="benchmark_harness",
    )


def _resolve_family_for_target(
    *,
    expectation: MissionVerifierExpectation,
    target_hint: str | None = None,
) -> str:
    """Pick a verifier family from the expectation list.

    For autonomous-completion-supported missions, the expectation
    enumerates one or more ``VerifierFamily`` values. We prefer
    ``artifact_presence`` when the deliverable hint is set; otherwise
    the first family in the expectation.
    """

    families = list(expectation.expected_verifier_families)
    if not families:
        # exploratory: caller handles disclosure-only path
        return "structural"
    if target_hint and target_hint in families:
        return target_hint
    return families[0]


def _empty_action_result(command_id: str) -> ActionResult:
    """Synthetic no-evidence ``ActionResult`` for fail-closed baseline.

    This is the structurally honest captured state when no agent loop has
    driven the goal: zero artifacts, zero outputs, status=failed. The
    verifier surface must reject this (and does, by design — see
    ``tests/brain/test_tgcr_verifier_contract.py``).
    """

    return ActionResult(
        command_id=command_id,
        status="failed",
        outputs={},
        artifact_refs=[],
        memory_refs=[],
    )


def _run_verifiers_for_goal(
    *,
    spec: BenchmarkTaskSpec,
    goal: Goal,
    run_id: str,
    expectation: MissionVerifierExpectation,
    state: WorkingState,
    logger: CanonicalEventLogger,
) -> tuple[list[VerifierResult], list[BenchmarkVerifierEvidence]]:
    verifier_results: list[VerifierResult] = []
    evidence: list[BenchmarkVerifierEvidence] = []

    # Skip live verifier dispatch for exploratory missions — MTRR-Q4
    # decision: ``autonomous_completion_supported=False`` means no
    # verifier expectation registered; the run ends on disclosure +
    # evidence-ref capture, not on verifier confirmation.
    if not expectation.autonomous_completion_supported:
        return verifier_results, evidence

    # Run a verifier per success criterion.
    for criterion in goal.success_criteria:
        cmd = ToolCommand(
            kind="tool",
            title=f"verify-{criterion.criterion_id}",
            tool_name="benchmark-no-op",
            success_criteria={"baseline": "captured"},
        )
        action_result = _empty_action_result(cmd.command_id)
        family = _resolve_family_for_target(expectation=expectation)
        invocation = VerifierInvocation(
            family=family,  # type: ignore[arg-type]
            goal_id=goal.goal_id,
            run_id=run_id,
            command=cmd,
            action_result=action_result,
            criterion=criterion,
            mode=VerificationMode.rule_based,
        )
        result = run_verifier(invocation, state=state, logger=logger)
        verifier_results.append(result)
        evidence.append(
            BenchmarkVerifierEvidence(
                family=result.family,
                target_id=result.target_id,
                target_kind="success_criterion",
                passed=result.passed,
                verdict=result.verdict,
                reasons=tuple(result.reasons),
            )
        )

    # Run a verifier per deliverable.
    for deliverable in goal.deliverables:
        cmd = ToolCommand(
            kind="tool",
            title=f"verify-{deliverable.deliverable_id}",
            tool_name="benchmark-no-op",
            success_criteria={},
        )
        action_result = _empty_action_result(cmd.command_id)
        family = _resolve_family_for_target(
            expectation=expectation,
            target_hint=deliverable.verification_hint,
        )
        invocation = VerifierInvocation(
            family=family,  # type: ignore[arg-type]
            goal_id=goal.goal_id,
            run_id=run_id,
            command=cmd,
            action_result=action_result,
            deliverable=deliverable,
            mode=VerificationMode.rule_based,
        )
        result = run_verifier(invocation, state=state, logger=logger)
        verifier_results.append(result)
        evidence.append(
            BenchmarkVerifierEvidence(
                family=result.family,
                target_id=result.target_id,
                target_kind="deliverable",
                passed=result.passed,
                verdict=result.verdict,
                reasons=tuple(result.reasons),
            )
        )

    return verifier_results, evidence


def _resolve_oracle_outcome_and_terminal(
    *,
    goal: Goal,
    expectation: MissionVerifierExpectation,
    disclosure: ExploratoryDisclosure | None,
    verifier_results: list[VerifierResult],
) -> tuple[
    BenchmarkOracleOutcome,
    BenchmarkFailureTaxonomy | None,
    RunTerminalState,
    bool,
]:
    """Map the captured-evidence rows to a typed outcome + terminal state.

    The mapping is structural:

    - exploratory mission + disclosure emitted: ``disclosed`` outcome,
      ``RUN_TERMINAL_BLOCKED`` (the run terminates on user/model
      termination per MTRR-Q4, never on completion verifier).
    - autonomous-completion mission + ``is_run_completion_confirmed`` is
      True: ``pass`` outcome, ``RUN_TERMINAL_COMPLETED``.
    - autonomous-completion mission + ``is_run_completion_confirmed`` is
      False + at least one verifier passed: ``partial`` outcome,
      ``RUN_TERMINAL_FAILED``, taxonomy = ``partial_completion``.
    - autonomous-completion mission + zero verifier passes: ``fail``
      outcome, ``RUN_TERMINAL_FAILED``, taxonomy = ``oracle_failed``.
    """

    if not expectation.autonomous_completion_supported:
        assert disclosure is not None, (
            "ExploratoryDisclosure must be emitted for non-autonomous mission types"
        )
        return ("disclosed", None, RUN_TERMINAL_BLOCKED, False)

    confirmed = is_run_completion_confirmed(goal=goal, results=verifier_results)
    if confirmed:
        return ("pass", None, RUN_TERMINAL_COMPLETED, True)

    if any(r.passed for r in verifier_results):
        return (
            "partial",
            "partial_completion",
            RUN_TERMINAL_FAILED,
            False,
        )
    return ("fail", "oracle_failed", RUN_TERMINAL_FAILED, False)


def execute_task(spec: BenchmarkTaskSpec) -> BenchmarkTaskOutcome:
    """Drive one task end-to-end through the typed verifier surface.

    No production agent loop is invoked. This captures the structurally
    honest fail-closed baseline state for one corpus task at openminion
    HEAD ``f5b16747``: typed Goal built, MissionVerifierExpectation
    looked up, ExploratoryDisclosure emitted (when applicable), each
    success criterion + deliverable verified via ``run_verifier`` with a
    no-evidence ``ActionResult``, ``is_run_completion_confirmed``
    consulted, ``RunTerminalState`` derived structurally.
    """

    goal = _build_goal_from_spec(spec)
    run_id = f"run-{spec.task_id}"
    state = _build_working_state(
        session_id=f"sess-{spec.task_id}",
        agent_id=f"agent-{spec.task_id}",
        trace_id=f"trace-{spec.task_id}",
    )
    logger = _build_logger(
        session_id=f"sess-{spec.task_id}",
        agent_id=f"agent-{spec.task_id}",
    )
    expectation = get_mission_verifier_expectation(spec.mission_type)
    disclosure = should_emit_exploratory_disclosure(spec.mission_type)

    verifier_results, evidence = _run_verifiers_for_goal(
        spec=spec,
        goal=goal,
        run_id=run_id,
        expectation=expectation,
        state=state,
        logger=logger,
    )

    (
        oracle_outcome,
        failure_taxonomy,
        terminal_state,
        completion_confirmed,
    ) = _resolve_oracle_outcome_and_terminal(
        goal=goal,
        expectation=expectation,
        disclosure=disclosure,
        verifier_results=verifier_results,
    )
    assert is_run_terminal_state(terminal_state), (
        f"Resolved terminal state {terminal_state!r} is not a TGCR-typed "
        f"RunTerminalState value"
    )

    captured_evidence_note = (
        "Captured-evidence baseline at openminion HEAD f5b16747: typed Goal "
        "exercised through run_verifier with no-evidence ActionResult "
        "(fail-closed). No production agent-loop binding for autonomous "
        "Goal execution exists at this HEAD; the verifier-surface "
        "exercise is structurally honest captured state, not a fabricated "
        "agent-run outcome."
    )

    return BenchmarkTaskOutcome(
        task_id=spec.task_id,
        mission_type=spec.mission_type,
        difficulty=spec.difficulty,
        contamination_class=spec.contamination_class,
        goal_id=goal.goal_id,
        run_id=run_id,
        oracle_outcome=oracle_outcome,
        failure_taxonomy=failure_taxonomy,
        run_terminal_state=terminal_state,
        verifier_expectation=expectation,
        exploratory_disclosure=disclosure,
        verifier_results=tuple(evidence),
        completion_confirmed=completion_confirmed,
        captured_at=utc_now_iso(),
        captured_evidence_note=captured_evidence_note,
    )


# ---------------------------------------------------------------------------
# Per-domain coverage aggregation
# ---------------------------------------------------------------------------


_PUBLIC_CONTAMINATION_CLASSES: frozenset[str] = frozenset(
    {"public_filtered", "public_modified"}
)


def build_domain_coverage(
    outcomes: tuple[BenchmarkTaskOutcome, ...],
) -> tuple[BenchmarkDomainCoverage, ...]:
    """Aggregate captured-evidence outcomes by ``MissionType``."""

    buckets: dict[MissionType, list[BenchmarkTaskOutcome]] = {
        "coding": [],
        "research": [],
        "operations": [],
        "exploratory": [],
    }
    for row in outcomes:
        buckets[row.mission_type].append(row)

    coverage: list[BenchmarkDomainCoverage] = []
    for mission_type, rows in buckets.items():
        pass_count = sum(1 for r in rows if r.oracle_outcome == "pass")
        partial_count = sum(1 for r in rows if r.oracle_outcome == "partial")
        fail_count = sum(1 for r in rows if r.oracle_outcome == "fail")
        disclosed_count = sum(1 for r in rows if r.oracle_outcome == "disclosed")
        contamination_flag = any(
            r.contamination_class in _PUBLIC_CONTAMINATION_CLASSES for r in rows
        )
        confidence_note = (
            "n=" + str(len(rows)) + "; baseline run is a single captured "
            "evidence pass per task (no repeats). Confidence interval is "
            "not computable from one observation; reruns required for "
            "interval estimation."
        )
        coverage.append(
            BenchmarkDomainCoverage(
                mission_type=mission_type,
                task_count=len(rows),
                pass_count=pass_count,
                partial_count=partial_count,
                fail_count=fail_count,
                disclosed_count=disclosed_count,
                contamination_disclosure_flag=contamination_flag,
                confidence_interval_note=confidence_note,
            )
        )
    return tuple(coverage)


# ---------------------------------------------------------------------------
# Top-level baseline run
# ---------------------------------------------------------------------------


def _resolve_phase2_outcome(
    outcomes: tuple[BenchmarkTaskOutcome, ...],
) -> tuple[BenchmarkPhase2Outcome, str]:
    """Pick the typed Phase 2 outcome and emit a structural rationale.

    Mapping (structural):

    - Every autonomous-completion mission task confirmed by the
      verifier surface AND every exploratory task emitted disclosure
      cleanly: ``baseline_captured``.
    - Verifier surface exercised end-to-end on every task and emitted
      typed VerifierResults / ExploratoryDisclosure cleanly, but the
      end-to-end agent-loop binding that would drive autonomous
      task completion was not exercised (no production caller of
      ``run_verifier`` / ``is_run_completion_confirmed`` exists at this
      HEAD): ``baseline_partial``.
    - Verifier surface could not be exercised on the corpus:
      ``measurement_blocked``.
    """

    if not outcomes or len(outcomes) != 8:
        return (
            "measurement_blocked",
            "Expected 8 corpus tasks; captured " + str(len(outcomes)) + ".",
        )

    autonomous_outcomes = [
        row
        for row in outcomes
        if row.verifier_expectation.autonomous_completion_supported
    ]
    exploratory_outcomes = [
        row
        for row in outcomes
        if not row.verifier_expectation.autonomous_completion_supported
    ]
    all_autonomous_confirmed = all(
        row.completion_confirmed for row in autonomous_outcomes
    )
    all_disclosed = all(
        row.oracle_outcome == "disclosed" for row in exploratory_outcomes
    )
    if all_autonomous_confirmed and all_disclosed:
        return (
            "baseline_captured",
            "Every autonomous-completion task confirmed by verifier surface; "
            "every exploratory task emitted disclosure cleanly.",
        )

    rationale = (
        "Verifier surface exercised end-to-end on all 8 corpus tasks at "
        "openminion HEAD f5b16747: typed Goals built (TGCR), "
        "MissionVerifierExpectation looked up (MTRR), ExploratoryDisclosure "
        "emitted for the 2 exploratory tasks (MTRR-Q4), VerifierInvocation "
        "/ VerifierResult / is_run_completion_confirmed exercised across "
        "every success-criterion and deliverable (TGCR). No production "
        "agent-loop binding for autonomous Goal execution exists at this "
        "HEAD (run_verifier and is_run_completion_confirmed have zero "
        "production callers; only tests at "
        "tests/brain/test_tgcr_verifier_contract.py and "
        "tests/integration/test_tgcr_goal_run_lifecycle.py invoke them). "
        "The captured-evidence outcome is therefore structurally honest "
        "fail-closed baseline: typed-oracle infrastructure is live and "
        "exercisable on the full corpus, end-to-end agent-loop binding "
        "is the documented gap. baseline_partial per the AMEB spec §5 "
        "closed outcome set."
    )
    return ("baseline_partial", rationale)


def run_phase2_baseline(
    *,
    audited_head_sha: str = "f5b16747d2ea298e875da75da37fbc8e9273d95f",
    eval_package_ref: str = "openminion-eval@local-source-tree",
    model_id: str = "no_agent_loop_invoked",
    runtime_context_note: str = (
        "No production agent loop invoked at openminion HEAD f5b16747. "
        "Typed verifier surface (run_verifier / is_run_completion_confirmed) "
        "exercised directly per corpus task with a fail-closed no-evidence "
        "ActionResult."
    ),
) -> BenchmarkBaselineReport:
    """Execute the full 8-task corpus and return the typed report."""

    corpus = build_ameb_corpus()
    outcomes = tuple(execute_task(spec) for spec in corpus)
    coverage = build_domain_coverage(outcomes)
    phase2_outcome, rationale = _resolve_phase2_outcome(outcomes)

    supplemental_note = (
        "Operator decision 2026-05-14: AATR ClarificationTrigger and APBR "
        "ProgressSignal / BudgetExtensionTrigger are out of scope for "
        "scoring. No agent loop was invoked during this baseline, so zero "
        "AATR / APBR typed events were emitted by the runtime. The §7 "
        "supplemental observations section on the artifact records this "
        "explicitly."
    )

    return BenchmarkBaselineReport(
        report_version="1",
        generated_at=utc_now_iso(),
        audited_head_sha=audited_head_sha,
        eval_package_ref=eval_package_ref,
        model_id=model_id,
        runtime_context_note=runtime_context_note,
        outcomes=outcomes,
        domain_coverage=coverage,
        phase2_outcome=phase2_outcome,
        phase2_rationale=rationale,
        supplemental_observations_note=supplemental_note,
    )


def write_report_json(report: BenchmarkBaselineReport, output_path: str | Path) -> Path:
    """Persist the typed baseline report as JSON for downstream consumers."""
    path = Path(output_path).expanduser().resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return path


__all__ = [
    "build_benchmark_harness_turn_intent",
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
    "build_ameb_corpus",
    "build_domain_coverage",
    "execute_task",
    "run_gateway_benchmark_turn",
    "run_phase2_baseline",
    "write_report_json",
]
