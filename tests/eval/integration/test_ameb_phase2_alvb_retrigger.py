"""ALVB-04: AMEB Phase 2 re-trigger evidence regression.

Drives the AMEB Phase 2 corpus through the now-wired
``services/runtime/verifier_binding.py`` production surface (the first
production caller of ``run_verifier`` / ``is_run_completion_confirmed``
in ``openminion/src/``). Asserts that:

1. At least one ``VerifierResult`` row comes back with typed
   **passing** evidence — proving the bind isn't fail-closed-only the
   way the 2026-05-14 ``baseline_partial`` artifact captured at HEAD
   ``f5b16747``. The Phase 2 harness's
   ``_empty_action_result(...)`` no-evidence path is still fail-closed
   (correct, structural). This regression injects an
   ``ActionResult`` with **real artifacts** for one corpus task to
   demonstrate that the binding actually surfaces typed passing
   evidence when evidence exists. That's the structural property the
   gap closure requires.

2. The typed ``bind_run_terminal_event(...)`` emits both a
   ``run.checkpoint`` event AND a ``run.<state>`` event with
   ``terminal_state_provenance="typed_verifier_reduction"`` in the
   payload — the production-surface provenance tag that AMEB Phase 2
   was structurally missing.

3. The fail-closed path (no artifacts) still terminates correctly as
   ``RUN_TERMINAL_FAILED`` with the same typed provenance — i.e. the
   binding is total over both success and failure paths.

**Honest scope-of-evidence:** this regression does NOT re-run the full
AMEB Phase 2 corpus and re-close it as ``baseline_captured``. That's a
separate AMEB re-open lane (ALVB-Q7 + spec §4 out-of-scope). What this
regression proves is the structural gap closure: the production
verifier-binding surface (a) exists in ``openminion/src/``, (b) is
called by production-shaped code (the gateway choke point + this
harness), and (c) can return typed passing evidence on the success path
— not just fail-closed on the no-evidence path.

The exploratory mission types (``ameb-explore-01``, ``ameb-explore-02``)
deliberately remain out of scope here: MTRR-Q4 defines them as
disclosure-only (no completion verifier), so the binding's typed-Goal
path does not apply to them. They terminate via legacy
``RUN_TERMINAL_BLOCKED`` machinery unchanged.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from openminion.modules.brain.diagnostics.events import CanonicalEventLogger
from openminion.modules.brain.runtime.verification.policy import (
    VerifierInvocation,
    VerifierResult,
    run_verifier,
)
from openminion.modules.brain.schemas import (
    ActionResult,
    VerificationMode,
    WorkingState,
)
from openminion.modules.brain.schemas.commands import ToolCommand
from openminion.modules.brain.schemas.state import ArtifactRef
from openminion.modules.storage.runtime.migrations import migrate_database
from openminion.modules.storage.runtime.session_store import SessionStore
from openminion.modules.storage.runtime.sqlite import connect_database
from openminion.services.runtime.run_status import (
    RUN_CHECKPOINT_EVENT_TYPE,
    RUN_STATE_COMPLETED,
    RUN_STATE_FAILED,
    RUN_TERMINAL_COMPLETED,
    RUN_TERMINAL_FAILED,
    Run,
)
from openminion.services.runtime.verifier_binding import (
    TERMINAL_STATE_PROVENANCE_FIELD,
    TERMINAL_STATE_PROVENANCE_TYPED,
    bind_run_terminal_event,
)

from tests.eval.integration.ameb_phase2_runner import (
    _coding_simple_spec,
    _build_goal_from_spec,
)


class _StubSessionApi:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict]] = []

    def append_event(
        self,
        session_id: str,
        event_type: str,
        payload: dict,
        **_: object,
    ) -> str:
        self.events.append((event_type, dict(payload)))
        return f"event-{len(self.events)}"


def _working_state(run_id: str) -> WorkingState:
    return WorkingState(
        session_id=f"sess-{run_id}",
        agent_id=f"agent-{run_id}",
        budgets_remaining={
            "ticks": 1,
            "tool_calls": 1,
            "a2a_calls": 0,
            "tokens": 100,
            "time_ms": 1000,
        },
        trace_id=f"trace-{run_id}",
    )


def _passing_action_result(command_id: str) -> ActionResult:
    """Synthetic ActionResult carrying real evidence — proves the
    binding's success-path produces typed passing VerifierResult rows.
    """
    return ActionResult(
        command_id=command_id,
        status="success",
        outputs={"tests_passed": True, "ruff_clean": True},
        artifact_refs=[ArtifactRef(ref="artifact://patch-1")],
    )


def _empty_action_result(command_id: str) -> ActionResult:
    """No-evidence ActionResult — matches Phase 2's fail-closed shape."""
    return ActionResult(
        command_id=command_id,
        status="failed",
        outputs={},
        artifact_refs=[],
    )


def _run_verifiers_against_goal(
    *,
    goal,
    run_id: str,
    action_result_factory,
    state: WorkingState,
    logger: CanonicalEventLogger,
) -> list[VerifierResult]:
    """Drive run_verifier across every SuccessCriterion + Deliverable.

    Identical structural shape to the AMEB Phase 2 harness; differs
    only in the ActionResult factory so the success path is reachable.
    """
    results: list[VerifierResult] = []
    for criterion in goal.success_criteria:
        cmd = ToolCommand(
            kind="tool",
            title=f"verify-{criterion.criterion_id}",
            tool_name="alvb-retrigger",
            success_criteria={},
        )
        action_result = action_result_factory(cmd.command_id)
        invocation = VerifierInvocation(
            family="structural",
            goal_id=goal.goal_id,
            run_id=run_id,
            command=cmd,
            action_result=action_result,
            criterion=criterion,
            mode=VerificationMode.rule_based,
        )
        results.append(run_verifier(invocation, state=state, logger=logger))
    for deliverable in goal.deliverables:
        cmd = ToolCommand(
            kind="tool",
            title=f"verify-{deliverable.deliverable_id}",
            tool_name="alvb-retrigger",
            success_criteria={},
        )
        action_result = action_result_factory(cmd.command_id)
        invocation = VerifierInvocation(
            family="artifact_presence",
            goal_id=goal.goal_id,
            run_id=run_id,
            command=cmd,
            action_result=action_result,
            deliverable=deliverable,
            mode=VerificationMode.rule_based,
        )
        results.append(run_verifier(invocation, state=state, logger=logger))
    return results


class AmebPhase2AlvbRetriggerTests(unittest.TestCase):
    """ALVB-04 evidence: drive the AMEB Phase 2 corpus through the
    production verifier-binding surface (services/runtime/verifier_binding.py).
    """

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp.name) / "state" / "openminion.db"
        migrate_database(db_path)
        self._connection = connect_database(db_path)
        self.sessions = SessionStore(self._connection)
        self.session = self.sessions.resolve_session(
            agent_id="alvb-retrigger",
            channel="console",
            target="alvb-04",
        )

    def tearDown(self) -> None:
        self._connection.close()
        self._tmp.cleanup()

    def test_success_path_yields_typed_passing_verifier_results(self) -> None:
        spec = _coding_simple_spec()
        goal = _build_goal_from_spec(spec)
        run_id = f"run-alvb-{spec.task_id}"
        run = Run(
            run_id=run_id,
            session_id=self.session.id,
            goal_id=goal.goal_id,
            state="running",
        )

        # Use an ActionResult with artifacts + outputs — the structural
        # verifier accepts this and returns passed=True.
        results = _run_verifiers_against_goal(
            goal=goal,
            run_id=run_id,
            action_result_factory=_passing_action_result,
            state=_working_state(run_id),
            logger=CanonicalEventLogger(
                session_api=_StubSessionApi(),
                session_id=f"sess-{run_id}",
                agent_id=f"agent-{run_id}",
            ),
        )

        # Honest scope-of-evidence assertion: at least one
        # VerifierResult row carries typed passing evidence (not the
        # fail-closed path that baseline_partial captured).
        passing = [r for r in results if r.passed]
        self.assertGreater(
            len(passing),
            0,
            (
                "ALVB-04 evidence requirement: at least one VerifierResult "
                "row must come back with typed passing evidence. "
                f"Got {len(passing)}/{len(results)} passing results — "
                "the binding would still be fail-closed-only."
            ),
        )

        # Now route through the production verifier-binding surface —
        # this is the first production-shaped caller (in openminion/src/)
        # of run_verifier + is_run_completion_confirmed.
        event = bind_run_terminal_event(
            run=run,
            goal=goal,
            verifier_results=results,
            sessions=self.sessions,
            checkpoint_id=f"{run_id}:terminal",
        )

        # Persisted RUN_STATE_COMPLETED with typed-reduction provenance.
        self.assertEqual(event.event_type, f"run.{RUN_STATE_COMPLETED}")
        self.assertEqual(event.payload["terminal_state"], RUN_TERMINAL_COMPLETED)
        self.assertEqual(
            event.payload[TERMINAL_STATE_PROVENANCE_FIELD],
            TERMINAL_STATE_PROVENANCE_TYPED,
        )

        # Typed RunCheckpoint emitted before the run.<state> event.
        events = self.sessions.list_events(
            session_id=self.session.id,
            limit=50,
            newest_first=False,
        )
        types = [e.event_type for e in events]
        self.assertIn(RUN_CHECKPOINT_EVENT_TYPE, types)
        cp_idx = types.index(RUN_CHECKPOINT_EVENT_TYPE)
        run_idx = types.index(f"run.{RUN_STATE_COMPLETED}")
        self.assertLess(cp_idx, run_idx)

    def test_fail_closed_path_still_terminates_as_failed(self) -> None:
        """Honest fail-closed baseline (the Phase 2 captured state)
        still terminates correctly through the production surface."""
        spec = _coding_simple_spec()
        goal = _build_goal_from_spec(spec)
        run_id = f"run-alvb-fail-{spec.task_id}"
        run = Run(
            run_id=run_id,
            session_id=self.session.id,
            goal_id=goal.goal_id,
            state="running",
        )
        results = _run_verifiers_against_goal(
            goal=goal,
            run_id=run_id,
            action_result_factory=_empty_action_result,
            state=_working_state(run_id),
            logger=CanonicalEventLogger(
                session_api=_StubSessionApi(),
                session_id=f"sess-{run_id}",
                agent_id=f"agent-{run_id}",
            ),
        )
        # Fail-closed: zero verifier rows passed.
        self.assertEqual(sum(1 for r in results if r.passed), 0)

        event = bind_run_terminal_event(
            run=run,
            goal=goal,
            verifier_results=results,
            sessions=self.sessions,
            checkpoint_id=f"{run_id}:terminal",
        )
        # Production surface still terminates with typed provenance —
        # just as RUN_STATE_FAILED instead of RUN_STATE_COMPLETED.
        self.assertEqual(event.event_type, f"run.{RUN_STATE_FAILED}")
        self.assertEqual(event.payload["terminal_state"], RUN_TERMINAL_FAILED)
        self.assertEqual(
            event.payload[TERMINAL_STATE_PROVENANCE_FIELD],
            TERMINAL_STATE_PROVENANCE_TYPED,
        )

    def test_production_surface_is_first_caller_in_src(self) -> None:
        """Structural evidence that ``run_verifier`` /
        ``is_run_completion_confirmed`` now have at least one production
        caller in ``openminion/src/``.

        The AMEB Phase 2 closure artifact recorded that these functions
        had zero callers in ``src/``. After ALVB,
        ``services/runtime/verifier_binding.py`` calls
        ``is_run_completion_confirmed`` directly — closing that gap.
        """
        from openminion.services.runtime import verifier_binding

        source = Path(verifier_binding.__file__).read_text()
        self.assertIn("is_run_completion_confirmed", source)
        # The bind is a production-surface module under
        # ``openminion/src/openminion/services/runtime/``.
        self.assertIn("openminion/services/runtime/", verifier_binding.__file__)


if __name__ == "__main__":
    unittest.main()
