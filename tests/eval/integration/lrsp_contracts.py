"""Typed LRSP probe contracts, canonical roster, and artifact helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Any, Literal

from openminion.base.generated_paths import resolve_generated_root
from openminion.base.time import utc_now_iso


LiveRuntimeProbeKind = Literal[
    "fresh_focus_session_turn",
    "quiet_no_progress_chat",
    "memory_write_recall",
    "tool_backed_turn",
    "clean_exit_shutdown",
]
"""Closed-set 5-value Literal over the LRSP spec section 2 probes."""


LiveRuntimeProbeOutcome = Literal[
    "passed",
    "failed",
    "skipped_no_api_key",
    "skipped_infrastructure_error",
]
"""Closed-set 4-value Literal over LRSP outcomes."""


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


LRSP_API_KEY_ENV = "OPENMINION_LIVE_PROBE_KEY"
"""Provider-agnostic LRSP API-key env var."""


def live_probe_api_key_present() -> bool:
    """Return whether the LRSP API key env var is structurally present."""

    return bool(os.environ.get(LRSP_API_KEY_ENV, "").strip())


@dataclass(frozen=True)
class TypedEventExpectation:
    """One typed event the probe expects to observe in order."""

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
    """Closed-set structural-assertion contract for one probe."""

    expected_event_sequence: tuple[TypedEventExpectation, ...]
    expected_run_terminal_state: (
        Literal[
            "completed",
            "failed",
            "blocked",
            "needs_human",
            "budget_exhausted",
        ]
        | None
    ) = None
    expected_terminal_state_provenance: str | None = None
    bounded_timeout_seconds: float = 30.0


@dataclass(frozen=True)
class LiveRuntimeProbe:
    """Typed probe definition with closed-set kind and structural contract."""

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
    """Typed captured-evidence outcome for one probe run."""

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
            raise ValueError(f"outcome={self.outcome!r} is outside the closed set")
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
            expected_run_terminal_state=None,
            bounded_timeout_seconds=5.0,
        ),
    )


def build_canonical_probe_set() -> tuple[LiveRuntimeProbe, ...]:
    """Return the closed-set 5-probe LRSP roster."""

    return (
        _fresh_focus_session_turn_probe(),
        _quiet_no_progress_chat_probe(),
        _memory_write_recall_probe(),
        _tool_backed_turn_probe(),
        _clean_exit_shutdown_probe(),
    )


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


__all__ = [
    "ALL_LIVE_RUNTIME_PROBE_KINDS",
    "ALL_LIVE_RUNTIME_PROBE_OUTCOMES",
    "LRSP_API_KEY_ENV",
    "CapturedEventRef",
    "LiveRuntimeProbe",
    "LiveRuntimeProbeKind",
    "LiveRuntimeProbeOutcome",
    "LiveRuntimeProbeResult",
    "LiveRuntimeProbeRunReport",
    "StructuralAssertionContract",
    "TypedEventExpectation",
    "build_canonical_probe_set",
    "default_lrsp_artifact_root",
    "live_probe_api_key_present",
    "write_probe_result_artifact",
]
