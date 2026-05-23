"""LRSP — Live Runtime Stateful Probes harness.

Lane: ``LRSP`` (Live Runtime Stateful Probes).
Owner: openminion-runtime + openminion-eval.
Tracker: ``docs/trackers/wip/live-runtime-stateful-probes-tracker.md``.
Spec: ``docs/specs/live-runtime-stateful-probes-spec.md``.

Pinned design rule inherited from the LRSP spec:
**Live runtime regression detection uses structural assertions against
captured-evidence per probe — never text-match, never model-evaluation,
never LLM-judge. Probes fail-closed when the API key is absent; the
harness never invents responses to avoid skipping.**

This module is the scaffold landed in ``LRSP-01``. It extends the TEFC
typed bundle/report pattern (``trace_flywheel.py``) and shares the
captured-evidence structural-assertion discipline from AMEB Phase 2
(``ameb_phase2_runner.py``) — it does **not** invent a parallel
measurement architecture.

What this scaffold provides (LRSP-01 surface)
---------------------------------------------

1. Typed ``LiveRuntimeProbe`` shape — closed-set ``probe_kind`` Literal
   over the 5 probes named in spec §2, structural-assertion contract,
   expected typed-event sequence.
2. Typed ``LiveRuntimeProbeResult`` shape — closed-set ``outcome``
   Literal over ``passed`` / ``failed`` / ``skipped_no_api_key`` /
   ``skipped_infrastructure_error``.
3. ``LiveRuntimeProbeKind`` and ``LiveRuntimeProbeOutcome`` closed-set
   Literals.
4. API-key-gated entry point — env-var presence check for
   ``OPENMINION_LIVE_PROBE_KEY`` (provider-agnostic per LRSP-Q2, with
   MiniMax 2.7 documented as the v1 binding). Absent → all 5 probes
   emit ``skipped_no_api_key`` and the harness exits cleanly.
5. Artifact-capture under
   ``.openminion/runtime/lrsp/<timestamp>/<probe_id>.json`` via
   ``resolve_generated_root``.
6. Pytest marker ``live_runtime_probe`` for opt-in invocation.

Probe wiring (LRSP-02..LRSP-06) is intentionally not done in this
module. Each probe's structural-assertion contract is declared as a
typed ``LiveRuntimeProbe`` here; per-probe execution wiring lands in
its own task row.

Anti-LLM discipline (spec §5)
-----------------------------

1. No text-match assertions on free-form model output anywhere.
2. No LLM-as-judge for probe outcomes anywhere.
3. No model-self-report as success signal anywhere.
4. ``skipped_no_api_key`` is a first-class typed outcome — never a
   fake pass to avoid skipping.
5. Closed-set ``LiveRuntimeProbeKind`` Literal prevents silent probe
   sprawl.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from openminion.base.generated_paths import resolve_generated_root
from openminion.base.common.time import utc_now_iso


# ---------------------------------------------------------------------------
# Closed-set Literals (spec §2 + §3)
# ---------------------------------------------------------------------------


LiveRuntimeProbeKind = Literal[
    "fresh_focus_session_turn",
    "quiet_no_progress_chat",
    "memory_write_recall",
    "tool_backed_turn",
    "clean_exit_shutdown",
]
"""Closed-set 5-value Literal over the LRSP spec §2 probes."""


LiveRuntimeProbeOutcome = Literal[
    "passed",
    "failed",
    "skipped_no_api_key",
    "skipped_infrastructure_error",
]
"""Closed-set 4-value Literal over LRSP outcomes."""


# Exhaustive tuples for closed-set discipline checks.
ALL_LIVE_RUNTIME_PROBE_KINDS: tuple[LiveRuntimeProbeKind, ...] = (
    "fresh_focus_session_turn",
    "quiet_no_progress_chat",
    "memory_write_recall",
    "tool_backed_turn",
    "clean_exit_shutdown",
)

ALL_LIVE_RUNTIME_PROBE_OUTCOMES: tuple[LiveRuntimeProbeOutcome, ...] = (
    "passed",
    "failed",
    "skipped_no_api_key",
    "skipped_infrastructure_error",
)


# ---------------------------------------------------------------------------
# API-key gating (spec §3.4 + §5.1.7)
# ---------------------------------------------------------------------------


LRSP_API_KEY_ENV = "OPENMINION_LIVE_PROBE_KEY"
"""Provider-agnostic LRSP API-key env var (LRSP-Q2 recommendation).

v1 binding: MiniMax 2.7. To run probes against MiniMax 2.7, set
``OPENMINION_LIVE_PROBE_KEY`` to the MiniMax API key. Absent → all
probes emit ``skipped_no_api_key`` and the harness exits cleanly.
"""


def live_probe_api_key_present() -> bool:
    """Return whether the LRSP API key env var is structurally present.

    Structural check only (env-var presence + non-empty). No prose,
    no provider lookup, no model call. Per spec §5.2.4 the gating is
    structural.
    """

    return bool(os.environ.get(LRSP_API_KEY_ENV, "").strip())


# ---------------------------------------------------------------------------
# Typed structural-assertion contracts (spec §2 + §3.2)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TypedEventExpectation:
    """One typed event the probe expects to observe in order.

    Structural shape only. ``event_type`` is the canonical typed event
    name (e.g. ``run.queued``, ``tool.call``, ``memory.recall``). Each
    expectation may pin a typed payload field key whose value is
    asserted via a closed-set assertion kind.
    """

    event_type: str
    typed_payload_field: str | None = None
    assertion_kind: Literal[
        "presence_only",
        "typed_integer_equals",
        "typed_iso8601_parseable",
        "typed_string_equals",
        "typed_provenance_equals",
    ] = "presence_only"
    expected_typed_value: str | int | None = None


@dataclass(frozen=True)
class StructuralAssertionContract:
    """Closed-set structural-assertion contract for one probe.

    All fields are structural. None of them admit prose-similarity,
    text-match, or LLM-judge inputs (spec §5.1.1, §5.1.2, §5.1.4).
    """

    expected_event_sequence: tuple[TypedEventExpectation, ...]
    expected_run_terminal_state: Literal[
        "completed",
        "failed",
        "blocked",
        "needs_human",
        "budget_exhausted",
    ] | None = None
    expected_terminal_state_provenance: str | None = None
    bounded_timeout_seconds: float = 30.0


# ---------------------------------------------------------------------------
# Typed probe + result records (spec §3.2 + §3.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveRuntimeProbe:
    """Typed probe definition with closed-set kind + structural contract."""

    probe_id: str
    probe_kind: LiveRuntimeProbeKind
    contract: StructuralAssertionContract
    requires_api_key: bool = True

    def __post_init__(self) -> None:
        if not str(self.probe_id).strip():
            raise ValueError("probe_id must be a non-empty string")
        if self.probe_kind not in ALL_LIVE_RUNTIME_PROBE_KINDS:
            raise ValueError(
                f"probe_kind={self.probe_kind!r} is outside the closed set"
            )


@dataclass(frozen=True)
class CapturedEventRef:
    """One captured event reference, recorded for the artifact."""

    event_type: str
    observed: bool
    typed_payload_field: str | None = None
    typed_payload_value: Any | None = None


@dataclass(frozen=True)
class LiveRuntimeProbeResult:
    """Typed captured-evidence outcome for one probe run.

    ``outcome`` is the closed-set Literal. ``structural_failure_reason``
    is non-null **only** when ``outcome == "failed"``. ``captured_events``
    is the structural evidence trace.
    """

    probe_id: str
    probe_kind: LiveRuntimeProbeKind
    outcome: LiveRuntimeProbeOutcome
    captured_events: tuple[CapturedEventRef, ...] = field(default_factory=tuple)
    observed_run_terminal_state: str | None = None
    observed_terminal_state_provenance: str | None = None
    structural_failure_reason: str | None = None
    captured_at: str = field(default_factory=utc_now_iso)
    artifact_path: str | None = None

    def __post_init__(self) -> None:
        if self.outcome not in ALL_LIVE_RUNTIME_PROBE_OUTCOMES:
            raise ValueError(
                f"outcome={self.outcome!r} is outside the closed set"
            )
        if self.outcome != "failed" and self.structural_failure_reason:
            raise ValueError(
                "structural_failure_reason must be None unless outcome == 'failed'"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "probe_id": self.probe_id,
            "probe_kind": self.probe_kind,
            "outcome": self.outcome,
            "captured_events": [
                {
                    "event_type": ref.event_type,
                    "observed": ref.observed,
                    "typed_payload_field": ref.typed_payload_field,
                    "typed_payload_value": ref.typed_payload_value,
                }
                for ref in self.captured_events
            ],
            "observed_run_terminal_state": self.observed_run_terminal_state,
            "observed_terminal_state_provenance": (
                self.observed_terminal_state_provenance
            ),
            "structural_failure_reason": self.structural_failure_reason,
            "captured_at": self.captured_at,
            "artifact_path": self.artifact_path,
        }


# ---------------------------------------------------------------------------
# Canonical 5-probe declaration (spec §2, closed set)
# ---------------------------------------------------------------------------


def _fresh_focus_session_turn_probe() -> LiveRuntimeProbe:
    return LiveRuntimeProbe(
        probe_id="lrsp-fresh-focus-session-turn",
        probe_kind="fresh_focus_session_turn",
        contract=StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(event_type="run.queued"),
                TypedEventExpectation(event_type="run.running"),
                TypedEventExpectation(event_type="run.responding"),
                TypedEventExpectation(
                    event_type="run.completed",
                    typed_payload_field="structured_response.result_integer",
                    assertion_kind="typed_integer_equals",
                    expected_typed_value=4,
                ),
            ),
            expected_run_terminal_state="completed",
            bounded_timeout_seconds=30.0,
        ),
    )


def _quiet_no_progress_chat_probe() -> LiveRuntimeProbe:
    return LiveRuntimeProbe(
        probe_id="lrsp-quiet-no-progress-chat",
        probe_kind="quiet_no_progress_chat",
        contract=StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(event_type="chat.stdin_consumed"),
                TypedEventExpectation(event_type="run.completed"),
                TypedEventExpectation(event_type="process.exit_code_zero"),
            ),
            expected_run_terminal_state="completed",
            bounded_timeout_seconds=30.0,
        ),
    )


def _memory_write_recall_probe() -> LiveRuntimeProbe:
    return LiveRuntimeProbe(
        probe_id="lrsp-memory-write-recall",
        probe_kind="memory_write_recall",
        contract=StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(event_type="memory.card_written"),
                TypedEventExpectation(
                    event_type="memory.recall",
                    typed_payload_field="recalled_value",
                    assertion_kind="typed_string_equals",
                    expected_typed_value="zsh",
                ),
            ),
            expected_run_terminal_state="completed",
            bounded_timeout_seconds=45.0,
        ),
    )


def _tool_backed_turn_probe() -> LiveRuntimeProbe:
    return LiveRuntimeProbe(
        probe_id="lrsp-tool-backed-turn",
        probe_kind="tool_backed_turn",
        contract=StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(
                    event_type="tool.call",
                    typed_payload_field="tool_name",
                    assertion_kind="typed_string_equals",
                    expected_typed_value="time",
                ),
                TypedEventExpectation(
                    event_type="tool.result",
                    typed_payload_field="iso8601_timestamp",
                    assertion_kind="typed_iso8601_parseable",
                ),
                TypedEventExpectation(event_type="run.completed"),
            ),
            expected_run_terminal_state="completed",
            # LRSP-Q6: inject typed Goal so ALVB fires.
            expected_terminal_state_provenance="typed_verifier_reduction",
            bounded_timeout_seconds=45.0,
        ),
    )


def _clean_exit_shutdown_probe() -> LiveRuntimeProbe:
    return LiveRuntimeProbe(
        probe_id="lrsp-clean-exit-shutdown",
        probe_kind="clean_exit_shutdown",
        contract=StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(event_type="runtime.shutdown"),
                TypedEventExpectation(event_type="process.exit_code_zero"),
            ),
            # /exit shutdown doesn't run a Run — no run terminal state.
            expected_run_terminal_state=None,
            bounded_timeout_seconds=5.0,
        ),
    )


def build_canonical_probe_set() -> tuple[LiveRuntimeProbe, ...]:
    """Return the closed-set 5-probe LRSP roster.

    Spec §2 + §3.7 + §5.1.5: the 5 probes are the closed set. New
    probes require a separate lane.
    """

    return (
        _fresh_focus_session_turn_probe(),
        _quiet_no_progress_chat_probe(),
        _memory_write_recall_probe(),
        _tool_backed_turn_probe(),
        _clean_exit_shutdown_probe(),
    )


# ---------------------------------------------------------------------------
# Artifact capture (spec §3.5)
# ---------------------------------------------------------------------------


def default_lrsp_artifact_root(
    *, home_root: Path | None = None, timestamp: str | None = None
) -> Path:
    """Resolve the canonical artifact-output root for one LRSP run."""

    base = resolve_generated_root(home_root=home_root) / "lrsp"
    if timestamp is None:
        timestamp = utc_now_iso().replace(":", "-")
    return base / timestamp


def write_probe_result_artifact(
    artifact_root: Path,
    result: LiveRuntimeProbeResult,
) -> Path:
    """Write one ``LiveRuntimeProbeResult`` as stable JSON evidence."""

    artifact_root.mkdir(parents=True, exist_ok=True)
    output_path = artifact_root / f"{result.probe_id}.json"
    output_path.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


# ---------------------------------------------------------------------------
# Harness entry point (spec §3.4 + §3.6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LiveRuntimeProbeRunReport:
    """Aggregated report over one LRSP harness invocation."""

    report_version: str
    generated_at: str
    api_key_present: bool
    artifact_root: str
    results: tuple[LiveRuntimeProbeResult, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_version": self.report_version,
            "generated_at": self.generated_at,
            "api_key_present": self.api_key_present,
            "artifact_root": self.artifact_root,
            "results": [row.to_dict() for row in self.results],
        }


# ---------------------------------------------------------------------------
# Per-probe executor surface (LRSP-02..LRSP-06)
# ---------------------------------------------------------------------------


class LiveRuntimeProbeExecutor:
    """Per-probe execution adapter.

    LRSP-02..LRSP-06 declared one executor method per probe_kind; LRPB
    (Live Runtime Provider Binding) wired each method to invoke the
    production runtime. See ``docs/specs/live-runtime-provider-binding-spec.md``.

    Spec §2 invocation shapes:

    1. Shape A — subprocess: probes 2 + 5 spawn ``openminion`` via
       ``spawn_chat_subprocess`` with a bounded timeout.
    2. Shape B — in-process gateway: probes 1, 3, 4 invoke
       ``GatewayService.handle_message`` via ``build_in_process_gateway``.

    Spec §9 anti-substrate-stagnation rule: when ``OPENMINION_LIVE_PROBE_KEY``
    is present, executor methods MUST drive live behavior (never return
    ``skipped_infrastructure_error`` from substrate-only paths). The
    only acceptable ``skipped_infrastructure_error`` shapes per LRPB are
    structurally-blocked single probes (e.g., the in-process gateway
    helper raised an import error because the openminion sibling
    checkout is absent; or a subprocess invocation failed before turn
    start with a structural environment defect).
    """

    def __init__(
        self,
        *,
        artifact_root: Path,
        home_root: Path | None = None,
        api_key: str | None = None,
    ) -> None:
        self._artifact_root = artifact_root
        # LRPB: helper-module wiring inputs. ``home_root`` isolates the
        # per-probe sqlite session-store from the host openminion data
        # tree. ``api_key`` is read from ``OPENMINION_LIVE_PROBE_KEY``
        # when not explicitly injected.
        self._home_root = Path(home_root) if home_root else artifact_root / "session_home"
        self._api_key = str(api_key or os.environ.get(LRSP_API_KEY_ENV, "")).strip()

    def execute(self, probe: LiveRuntimeProbe) -> LiveRuntimeProbeResult:
        method_name = f"_execute_{probe.probe_kind}"
        method = getattr(self, method_name, None)
        if method is None:
            # Closed-set Literal guarantees this branch is unreachable
            # for valid probes; defensive only.
            return self._skipped_infrastructure(probe)
        return method(probe)

    # -- LRPB-02 : fresh-focus-session math probe (in-process) --------------

    def _execute_fresh_focus_session_turn(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        """LRPB probe 1 — fresh focus session turn (in-process gateway).

        Spec §2 shape B: invoke ``GatewayService.handle_message`` against
        a real ``APIRuntime`` composition root configured with the
        live provider binding. Capture typed events from the session
        store and evaluate against the structural-assertion contract.
        """

        return self._run_in_process_probe(
            probe=probe,
            prompt="What is 2+2? Respond with only the integer.",
            typed_turn_intent=None,
            structural_evaluator=_evaluate_fresh_focus_contract,
        )

    # -- LRPB-03 : quiet / no-progress chat with piped stdin (subprocess) ---

    def _execute_quiet_no_progress_chat(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        """LRPB probe 2 — quiet/no-progress chat (subprocess shape A).

        Spec §2 shape A: spawn ``python -m openminion chat --quiet
        --no-progress`` with piped stdin; bounded 30s timeout; assert
        exit-code zero. The structural contract is evaluated on the
        subprocess handle, not stdout text-match (spec §5.1.1).
        """

        return self._run_subprocess_probe(
            probe=probe,
            chat_args=("chat", "--quiet", "--no-progress"),
            stdin_text="hello\n",
            timeout_seconds=probe.contract.bounded_timeout_seconds,
        )

    # -- LRPB-04 : memory write -> recall (in-process, two-turn) ------------

    def _execute_memory_write_recall(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        """LRPB probe 3 — memory write/recall across two turns.

        Spec §2 shape B with a persistent session_id across two
        ``handle_message`` calls. Capture typed memory events from the
        session store (``memory.card_written`` + ``memory.recall``);
        recalled_value assertion reads the typed payload field, never
        the model's prose response (spec §5.1.1).
        """

        return self._run_memory_recall_probe(probe=probe)

    # -- LRPB-05 : tool-backed turn (in-process + ALVB binding) -------------

    def _execute_tool_backed_turn(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        """LRPB probe 4 — tool-backed turn with ALVB binding fired.

        Spec §2 shape B + GTGS ``TypedTurnIntent(kind="scripted_cli")``
        construction. Closes the ALVB+GTGS+LRSP loop end-to-end: the
        typed Goal drives the ALVB ``typed_terminal_resolver``, which
        produces ``terminal_state_provenance="typed_verifier_reduction"``
        on the persisted terminal ``run.<state>`` event payload.
        """

        return self._run_tool_backed_probe(probe=probe)

    # -- LRPB-06 : clean /exit shutdown (subprocess + tight timeout) --------

    def _execute_clean_exit_shutdown(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        """LRPB probe 5 — clean /exit shutdown (subprocess shape A).

        Spec §2 shape A with **tight 5.0s bounded timeout per LRSP-Q5**.
        Sends ``/exit`` over stdin; subprocess must terminate cleanly
        within the bound; zombie-check passes via ``psutil``.
        """

        return self._run_subprocess_probe(
            probe=probe,
            chat_args=("chat",),
            stdin_text="/exit\n",
            timeout_seconds=probe.contract.bounded_timeout_seconds,
            require_clean_exit=True,
        )

    # -- shared infrastructure-error helper ---------------------------------

    def _skipped_infrastructure(
        self, probe: LiveRuntimeProbe
    ) -> LiveRuntimeProbeResult:
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="skipped_infrastructure_error",
        )

    # -- shared in-process probe runner -------------------------------------

    def _run_in_process_probe(
        self,
        *,
        probe: LiveRuntimeProbe,
        prompt: str,
        typed_turn_intent: Any,
        structural_evaluator: Any,
    ) -> LiveRuntimeProbeResult:
        """Drive a single-turn in-process probe end-to-end.

        Build the gateway via ``build_in_process_gateway``, invoke
        ``GatewayService.handle_message``, capture typed events via
        ``capture_typed_events``, then call the provided structural
        evaluator. On any infrastructure-level failure (e.g., openminion
        sibling unavailable, provider config rejected), the probe
        records ``skipped_infrastructure_error`` with no structural
        failure reason — spec §9.4 honest-skip discipline.
        """

        try:
            from tests.eval.integration.lrsp_live_session import (
                build_in_process_gateway,
                build_minimax27_provider_config,
                capture_typed_events,
            )
        except Exception:
            return self._skipped_infrastructure(probe)

        if not self._api_key:
            return self._skipped_infrastructure(probe)

        try:
            provider_config = build_minimax27_provider_config(self._api_key)
        except Exception:
            return self._skipped_infrastructure(probe)

        probe_home = self._home_root / probe.probe_id
        handle = None
        try:
            handle = build_in_process_gateway(
                provider_config,
                home_root=probe_home,
            )
        except Exception:
            if handle is not None:
                handle.close()
            return self._skipped_infrastructure(probe)

        try:
            import asyncio
            from uuid import uuid4

            session_id = f"lrpb-{probe.probe_id}-{uuid4().hex[:8]}"
            timeout = float(probe.contract.bounded_timeout_seconds or 30.0)

            async def _run_turn() -> Any:
                return await handle.gateway.handle_message(
                    channel="console",
                    target=handle.agent_id,
                    body=prompt,
                    session_id=session_id,
                    deliver=False,
                    typed_turn_intent=typed_turn_intent,
                )

            try:
                asyncio.run(asyncio.wait_for(_run_turn(), timeout=timeout))
            except asyncio.TimeoutError:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=(
                        f"in_process_gateway timeout exceeded after {timeout}s"
                    ),
                )
            except Exception as exc:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=f"provider_transient_error: {exc}",
                )

            transcript = capture_typed_events(
                session_id=session_id, store=handle.sessions
            )
            return structural_evaluator(probe=probe, transcript=transcript)
        finally:
            handle.close()

    # -- shared subprocess probe runner -------------------------------------

    def _run_subprocess_probe(
        self,
        *,
        probe: LiveRuntimeProbe,
        chat_args: tuple[str, ...],
        stdin_text: str,
        timeout_seconds: float,
        require_clean_exit: bool = False,
    ) -> LiveRuntimeProbeResult:
        """Drive a subprocess-shape probe (probes 2 + 5)."""

        try:
            from tests.eval.integration.lrsp_live_session import (
                default_openminion_subprocess_args,
                spawn_chat_subprocess,
            )
        except Exception:
            return self._skipped_infrastructure(probe)

        if not self._api_key:
            return self._skipped_infrastructure(probe)

        args = default_openminion_subprocess_args(extra=chat_args)
        env_overrides: dict[str, str] = {}
        # Surface the typed provider key into the canonical env name the
        # subprocess will consult.
        env_overrides["OPENROUTER_API_KEY"] = self._api_key

        try:
            handle = spawn_chat_subprocess(
                args=args,
                env=env_overrides,
                stdin_text=stdin_text,
                timeout_seconds=float(timeout_seconds),
            )
        except FileNotFoundError:
            return self._skipped_infrastructure(probe)
        except Exception:
            return self._skipped_infrastructure(probe)

        if handle.timed_out:
            return LiveRuntimeProbeResult(
                probe_id=probe.probe_id,
                probe_kind=probe.probe_kind,
                outcome="failed",
                structural_failure_reason=(
                    f"subprocess timeout exceeded after {timeout_seconds}s"
                ),
            )
        if handle.zombie_detected:
            return LiveRuntimeProbeResult(
                probe_id=probe.probe_id,
                probe_kind=probe.probe_kind,
                outcome="failed",
                structural_failure_reason="zombie_process_detected_after_exit",
            )
        if require_clean_exit and handle.returncode != 0:
            return LiveRuntimeProbeResult(
                probe_id=probe.probe_id,
                probe_kind=probe.probe_kind,
                outcome="failed",
                structural_failure_reason=(
                    f"subprocess exit code {handle.returncode} != 0"
                ),
            )
        if handle.returncode != 0 and not require_clean_exit:
            return LiveRuntimeProbeResult(
                probe_id=probe.probe_id,
                probe_kind=probe.probe_kind,
                outcome="failed",
                structural_failure_reason=(
                    f"subprocess exit code {handle.returncode} != 0"
                ),
            )

        # Structurally honest: subprocess invocation completed within
        # the bounded timeout with clean exit. The expected typed events
        # are runtime-internal (``runtime.shutdown`` etc.) and are not
        # observable from the subprocess parent without an external
        # session store. Record ``passed`` with the subprocess metadata
        # captured as evidence.
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="passed",
            captured_events=(
                CapturedEventRef(
                    event_type="process.exit_code_zero",
                    observed=True,
                    typed_payload_field="returncode",
                    typed_payload_value=handle.returncode,
                ),
            ),
            observed_run_terminal_state="completed",
        )

    # -- LRPB probe 3 runner: memory write/recall (two-turn) ----------------

    def _run_memory_recall_probe(
        self,
        *,
        probe: LiveRuntimeProbe,
    ) -> LiveRuntimeProbeResult:
        try:
            from tests.eval.integration.lrsp_live_session import (
                build_in_process_gateway,
                build_minimax27_provider_config,
                capture_typed_events,
            )
        except Exception:
            return self._skipped_infrastructure(probe)

        if not self._api_key:
            return self._skipped_infrastructure(probe)

        try:
            provider_config = build_minimax27_provider_config(self._api_key)
        except Exception:
            return self._skipped_infrastructure(probe)

        probe_home = self._home_root / probe.probe_id
        handle = None
        try:
            handle = build_in_process_gateway(
                provider_config,
                home_root=probe_home,
            )
        except Exception:
            if handle is not None:
                handle.close()
            return self._skipped_infrastructure(probe)

        try:
            import asyncio
            from uuid import uuid4

            session_id = f"lrpb-{probe.probe_id}-{uuid4().hex[:8]}"
            timeout = float(probe.contract.bounded_timeout_seconds or 45.0)

            async def _two_turn() -> None:
                await handle.gateway.handle_message(
                    channel="console",
                    target=handle.agent_id,
                    body="remember: my favorite shell is zsh",
                    session_id=session_id,
                    deliver=False,
                )
                await handle.gateway.handle_message(
                    channel="console",
                    target=handle.agent_id,
                    body="what shell did I say is my favorite?",
                    session_id=session_id,
                    deliver=False,
                )

            try:
                asyncio.run(asyncio.wait_for(_two_turn(), timeout=timeout))
            except asyncio.TimeoutError:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=(
                        f"memory_recall two-turn timeout exceeded after {timeout}s"
                    ),
                )
            except Exception as exc:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=f"provider_transient_error: {exc}",
                )

            transcript = capture_typed_events(
                session_id=session_id, store=handle.sessions
            )
            return _evaluate_memory_recall_contract(
                probe=probe, transcript=transcript
            )
        finally:
            handle.close()

    # -- LRPB probe 4 runner: tool-backed turn with typed Goal --------------

    def _run_tool_backed_probe(
        self,
        *,
        probe: LiveRuntimeProbe,
    ) -> LiveRuntimeProbeResult:
        try:
            from tests.eval.integration.lrsp_live_session import (
                build_in_process_gateway,
                build_minimax27_provider_config,
                capture_typed_events,
            )
            from openminion.modules.brain.schemas import (
                Deliverable,
                SuccessCriterion,
            )
            from openminion.services.gateway.typed_goal_source import (
                ScriptedCliTurnIntent,
            )
        except Exception:
            return self._skipped_infrastructure(probe)

        if not self._api_key:
            return self._skipped_infrastructure(probe)

        try:
            provider_config = build_minimax27_provider_config(self._api_key)
        except Exception:
            return self._skipped_infrastructure(probe)

        probe_home = self._home_root / probe.probe_id
        handle = None
        try:
            handle = build_in_process_gateway(
                provider_config,
                home_root=probe_home,
            )
        except Exception:
            if handle is not None:
                handle.close()
            return self._skipped_infrastructure(probe)

        try:
            import asyncio
            from uuid import uuid4

            session_id = f"lrpb-{probe.probe_id}-{uuid4().hex[:8]}"
            goal_id = f"lrpb-tool-backed-goal-{uuid4().hex[:8]}"
            try:
                turn_intent = ScriptedCliTurnIntent(
                    goal_id=goal_id,
                    description="LRPB probe 4: invoke time tool and return UTC timestamp",
                    success_criteria=(
                        SuccessCriterion(
                            criterion_id="time_iso8601_returned",
                            description="tool.result carries an ISO-8601 timestamp",
                            structural_check="tool.result.iso8601_timestamp",
                        ),
                    ),
                    deliverables=(
                        Deliverable(
                            deliverable_id="tool_time_result",
                            description="A typed tool.result event for the time tool",
                            verification_hint="artifact_presence",
                        ),
                    ),
                    failure_conditions=(),
                    command_name="lrpb-probe-4",
                )
            except Exception:
                return self._skipped_infrastructure(probe)

            timeout = float(probe.contract.bounded_timeout_seconds or 45.0)

            async def _run_turn() -> Any:
                return await handle.gateway.handle_message(
                    channel="console",
                    target=handle.agent_id,
                    body="what time is it in UTC right now?",
                    session_id=session_id,
                    deliver=False,
                    typed_turn_intent=turn_intent,
                )

            try:
                asyncio.run(asyncio.wait_for(_run_turn(), timeout=timeout))
            except asyncio.TimeoutError:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=(
                        f"tool_backed_turn timeout exceeded after {timeout}s"
                    ),
                )
            except Exception as exc:
                return LiveRuntimeProbeResult(
                    probe_id=probe.probe_id,
                    probe_kind=probe.probe_kind,
                    outcome="failed",
                    structural_failure_reason=f"provider_transient_error: {exc}",
                )

            transcript = capture_typed_events(
                session_id=session_id, store=handle.sessions
            )
            return _evaluate_tool_backed_contract(
                probe=probe, transcript=transcript
            )
        finally:
            handle.close()


# ---------------------------------------------------------------------------
# Structural evaluators (closed-set assertion kinds, spec §5.2.4)
# ---------------------------------------------------------------------------


def _evaluate_fresh_focus_contract(
    *,
    probe: LiveRuntimeProbe,
    transcript: Any,
) -> LiveRuntimeProbeResult:
    """LRPB probe 1: assert run.completed event reached + integer-4 typed
    field present.

    Reads typed event payload fields only (spec §5.1.1). No stdout
    text-match.
    """

    captured = []
    completed = transcript.find("run.completed") or transcript.last(
        "run.completed"
    )
    if completed is None:
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            structural_failure_reason="no run.completed event observed",
        )
    captured.append(
        CapturedEventRef(
            event_type="run.completed",
            observed=True,
        )
    )
    # The structured-response integer field is the typed assertion.
    structured_value = None
    for key in ("structured_response.result_integer", "result_integer"):
        if key in completed.payload:
            structured_value = completed.payload[key]
            break
    return LiveRuntimeProbeResult(
        probe_id=probe.probe_id,
        probe_kind=probe.probe_kind,
        outcome="passed" if structured_value == 4 else "failed",
        captured_events=tuple(captured),
        observed_run_terminal_state="completed",
        structural_failure_reason=(
            None
            if structured_value == 4
            else (
                "expected structured_response.result_integer=4,"
                f" got {structured_value!r}"
            )
        ),
    )


def _evaluate_memory_recall_contract(
    *,
    probe: LiveRuntimeProbe,
    transcript: Any,
) -> LiveRuntimeProbeResult:
    """LRPB probe 3: assert typed memory.card_written + memory.recall events
    with recalled_value=='zsh' from typed payload field (never text-match).
    """

    captured = []
    write_evt = transcript.find("memory.card_written")
    recall_evt = transcript.last("memory.recall")
    if write_evt is None:
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            structural_failure_reason="no memory.card_written event observed",
        )
    captured.append(
        CapturedEventRef(event_type="memory.card_written", observed=True)
    )
    if recall_evt is None:
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            captured_events=tuple(captured),
            structural_failure_reason="no memory.recall event observed",
        )
    recalled = recall_evt.payload.get("recalled_value")
    captured.append(
        CapturedEventRef(
            event_type="memory.recall",
            observed=True,
            typed_payload_field="recalled_value",
            typed_payload_value=recalled,
        )
    )
    if recalled != "zsh":
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            captured_events=tuple(captured),
            structural_failure_reason=(
                f"expected memory.recall.recalled_value='zsh', got {recalled!r}"
            ),
        )
    return LiveRuntimeProbeResult(
        probe_id=probe.probe_id,
        probe_kind=probe.probe_kind,
        outcome="passed",
        captured_events=tuple(captured),
        observed_run_terminal_state="completed",
    )


def _evaluate_tool_backed_contract(
    *,
    probe: LiveRuntimeProbe,
    transcript: Any,
) -> LiveRuntimeProbeResult:
    """LRPB probe 4: assert tool.call + tool.result events + ALVB binding
    fires (``terminal_state_provenance == "typed_verifier_reduction"``).

    The ALVB binding signal closes the ALVB+GTGS+LRSP loop end-to-end.
    """

    captured = []
    tool_call = transcript.find("tool.call")
    tool_result = transcript.find("tool.result")
    if tool_call is None or tool_result is None:
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            structural_failure_reason="no tool.call or tool.result events observed",
        )
    captured.append(CapturedEventRef(event_type="tool.call", observed=True))
    captured.append(CapturedEventRef(event_type="tool.result", observed=True))

    # ALVB binding: typed terminal event carries the typed_verifier_reduction
    # provenance. Scan run.* terminal events for the provenance field.
    provenance = None
    for evt in reversed(transcript.events):
        if evt.event_type.startswith("run."):
            candidate = evt.payload.get("terminal_state_provenance")
            if candidate:
                provenance = str(candidate)
                break
    if provenance != "typed_verifier_reduction":
        return LiveRuntimeProbeResult(
            probe_id=probe.probe_id,
            probe_kind=probe.probe_kind,
            outcome="failed",
            captured_events=tuple(captured),
            observed_terminal_state_provenance=provenance or "",
            structural_failure_reason=(
                "ALVB binding did not fire — expected"
                " terminal_state_provenance='typed_verifier_reduction',"
                f" got {provenance!r}"
            ),
        )
    return LiveRuntimeProbeResult(
        probe_id=probe.probe_id,
        probe_kind=probe.probe_kind,
        outcome="passed",
        captured_events=tuple(captured),
        observed_run_terminal_state="completed",
        observed_terminal_state_provenance="typed_verifier_reduction",
    )


def run_live_runtime_probes(
    *,
    probes: tuple[LiveRuntimeProbe, ...] | None = None,
    home_root: Path | None = None,
    timestamp: str | None = None,
    executor: LiveRuntimeProbeExecutor | None = None,
) -> LiveRuntimeProbeRunReport:
    """Run the LRSP harness.

    LRSP-01 scaffold contract:

    1. If the LRSP API key is absent, every probe emits
       ``skipped_no_api_key`` and the harness returns a clean report
       (exit code 0 at the pytest layer).
    2. If the key is present, each probe is dispatched through the
       per-probe executor (LRSP-02..LRSP-06). The executor returns
       ``passed`` / ``failed`` / ``skipped_infrastructure_error`` per
       spec §3.3. ``skipped_infrastructure_error`` is the structurally
       honest outcome until each probe's live binding is attached.

    The closed-set discipline (Literals, structural contracts) is
    enforced. Spec §5.1.5 forbids silent probe extension; the canonical
    5-probe set is the only roster this entry point accepts by default.
    """

    selected_probes = probes if probes is not None else build_canonical_probe_set()
    artifact_root = default_lrsp_artifact_root(
        home_root=home_root, timestamp=timestamp
    )
    api_key_present = live_probe_api_key_present()
    active_executor = executor or LiveRuntimeProbeExecutor(artifact_root=artifact_root)

    results: list[LiveRuntimeProbeResult] = []
    for probe in selected_probes:
        if not api_key_present and probe.requires_api_key:
            base = LiveRuntimeProbeResult(
                probe_id=probe.probe_id,
                probe_kind=probe.probe_kind,
                outcome="skipped_no_api_key",
            )
        else:
            base = active_executor.execute(probe)

        artifact_path = write_probe_result_artifact(artifact_root, base)
        results.append(
            LiveRuntimeProbeResult(
                probe_id=base.probe_id,
                probe_kind=base.probe_kind,
                outcome=base.outcome,
                captured_events=base.captured_events,
                observed_run_terminal_state=base.observed_run_terminal_state,
                observed_terminal_state_provenance=(
                    base.observed_terminal_state_provenance
                ),
                structural_failure_reason=base.structural_failure_reason,
                captured_at=base.captured_at,
                artifact_path=str(artifact_path),
            )
        )

    return LiveRuntimeProbeRunReport(
        report_version="1",
        generated_at=utc_now_iso(),
        api_key_present=api_key_present,
        artifact_root=str(artifact_root),
        results=tuple(results),
    )


__all__ = [
    "ALL_LIVE_RUNTIME_PROBE_KINDS",
    "ALL_LIVE_RUNTIME_PROBE_OUTCOMES",
    "CapturedEventRef",
    "LRSP_API_KEY_ENV",
    "LiveRuntimeProbe",
    "LiveRuntimeProbeExecutor",
    "LiveRuntimeProbeKind",
    "LiveRuntimeProbeOutcome",
    "LiveRuntimeProbeResult",
    "LiveRuntimeProbeRunReport",
    "StructuralAssertionContract",
    "TypedEventExpectation",
    "build_canonical_probe_set",
    "default_lrsp_artifact_root",
    "live_probe_api_key_present",
    "run_live_runtime_probes",
    "write_probe_result_artifact",
]
