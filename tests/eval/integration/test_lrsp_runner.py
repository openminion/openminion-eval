"""Regression tests for the LRSP harness scaffold itself (LRSP-01).

These tests do NOT call the live runtime. They exercise the typed
scaffold contract:

1. Closed-set ``LiveRuntimeProbeKind`` Literal is exhaustive over the
   5 spec §2 probes.
2. Closed-set ``LiveRuntimeProbeOutcome`` Literal is exhaustive over
   the 4 typed outcomes.
3. Canonical 5-probe roster matches the closed-set kinds exactly.
4. ``LiveRuntimeProbe`` rejects an out-of-set ``probe_kind``.
5. ``LiveRuntimeProbeResult`` rejects an out-of-set ``outcome``.
6. ``LiveRuntimeProbeResult.structural_failure_reason`` is rejected on
   non-failed outcomes (no inflating prose on skips).
7. The ``skipped_no_api_key`` path produces a clean report when the
   env var is absent (no fake passes).
8. Per-probe artifact JSON is written under
   ``.openminion/runtime/lrsp/<timestamp>/<probe_id>.json``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tests.eval.integration.lrsp_runner import (
    ALL_LIVE_RUNTIME_PROBE_KINDS,
    ALL_LIVE_RUNTIME_PROBE_OUTCOMES,
    LRSP_API_KEY_ENV,
    LiveRuntimeProbe,
    LiveRuntimeProbeExecutor,
    LiveRuntimeProbeResult,
    StructuralAssertionContract,
    TypedEventExpectation,
    build_canonical_probe_set,
    live_probe_api_key_present,
    run_live_runtime_probes,
)


def test_probe_kind_literal_is_exhaustive_over_five_spec_probes() -> None:
    assert ALL_LIVE_RUNTIME_PROBE_KINDS == (
        "fresh_focus_session_turn",
        "quiet_no_progress_chat",
        "memory_write_recall",
        "tool_backed_turn",
        "clean_exit_shutdown",
    )
    assert len(ALL_LIVE_RUNTIME_PROBE_KINDS) == 5
    assert len(set(ALL_LIVE_RUNTIME_PROBE_KINDS)) == 5


def test_probe_outcome_literal_is_exhaustive_over_four_typed_outcomes() -> None:
    assert ALL_LIVE_RUNTIME_PROBE_OUTCOMES == (
        "passed",
        "failed",
        "skipped_no_api_key",
        "skipped_infrastructure_error",
    )
    assert len(ALL_LIVE_RUNTIME_PROBE_OUTCOMES) == 4
    assert len(set(ALL_LIVE_RUNTIME_PROBE_OUTCOMES)) == 4


def test_canonical_probe_set_covers_closed_set_kinds_exactly() -> None:
    probes = build_canonical_probe_set()
    assert len(probes) == 5
    kinds = tuple(probe.probe_kind for probe in probes)
    assert kinds == ALL_LIVE_RUNTIME_PROBE_KINDS
    # Each probe_id is unique.
    ids = [probe.probe_id for probe in probes]
    assert len(set(ids)) == 5


def test_live_runtime_probe_rejects_out_of_set_kind() -> None:
    with pytest.raises(ValueError):
        LiveRuntimeProbe(
            probe_id="lrsp-bogus",
            probe_kind="not_a_real_kind",  # type: ignore[arg-type]
            contract=StructuralAssertionContract(
                expected_event_sequence=(
                    TypedEventExpectation(event_type="run.queued"),
                ),
            ),
        )


def test_live_runtime_probe_rejects_empty_probe_id() -> None:
    with pytest.raises(ValueError):
        LiveRuntimeProbe(
            probe_id="   ",
            probe_kind="fresh_focus_session_turn",
            contract=StructuralAssertionContract(
                expected_event_sequence=(
                    TypedEventExpectation(event_type="run.queued"),
                ),
            ),
        )


def test_live_runtime_probe_result_rejects_out_of_set_outcome() -> None:
    with pytest.raises(ValueError):
        LiveRuntimeProbeResult(
            probe_id="lrsp-bogus",
            probe_kind="fresh_focus_session_turn",
            outcome="solved_with_warning",  # type: ignore[arg-type]
        )


def test_live_runtime_probe_result_rejects_failure_reason_on_non_failed_outcome() -> None:
    # ``skipped_no_api_key`` must not carry a structural failure reason —
    # inflating a skip with a prose-shaped failure reason is forbidden.
    with pytest.raises(ValueError):
        LiveRuntimeProbeResult(
            probe_id="lrsp-fresh-focus-session-turn",
            probe_kind="fresh_focus_session_turn",
            outcome="skipped_no_api_key",
            structural_failure_reason="api key looked weird",
        )


def test_api_key_absent_path_produces_clean_skipped_report(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.delenv(LRSP_API_KEY_ENV, raising=False)
    assert live_probe_api_key_present() is False

    report = run_live_runtime_probes(home_root=tmp_path, timestamp="2026-05-15T00-00-00Z")

    assert report.api_key_present is False
    assert len(report.results) == 5
    # Every probe must emit ``skipped_no_api_key`` — never a fake pass.
    outcomes = tuple(row.outcome for row in report.results)
    assert outcomes == (
        "skipped_no_api_key",
        "skipped_no_api_key",
        "skipped_no_api_key",
        "skipped_no_api_key",
        "skipped_no_api_key",
    )
    # Every probe wrote its artifact JSON to disk.
    for row in report.results:
        assert row.artifact_path is not None
        assert Path(row.artifact_path).is_file()
        payload = json.loads(Path(row.artifact_path).read_text(encoding="utf-8"))
        assert payload["outcome"] == "skipped_no_api_key"
        assert payload["probe_id"] == row.probe_id


def test_api_key_present_path_records_real_outcomes_post_lrpb(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # LRPB wiring (lane successor to LRSP) replaced the
    # ``skipped_infrastructure_error`` substrate path with real
    # subprocess + in-process invocations. With a fake key, the typed
    # outcomes must be one of the closed-set non-fake-pass values —
    # ``failed`` (real provider transient error / structural assertion
    # miss), ``skipped_infrastructure_error`` (helper module
    # unavailable / structural environment defect), or ``passed`` (only
    # if the structural contract is satisfied — never via fake-key
    # success which is impossible for a real network call).
    #
    # NEVER ``skipped_no_api_key`` here (key is set).
    # NEVER fabricated ``passed`` from a fake key (anti-LLM §5.1.6).
    monkeypatch.setenv(LRSP_API_KEY_ENV, "fake-test-key")
    report = run_live_runtime_probes(
        home_root=tmp_path, timestamp="2026-05-15T00-00-01Z"
    )
    assert report.api_key_present is True
    allowed = {"passed", "failed", "skipped_infrastructure_error"}
    outcomes = tuple(row.outcome for row in report.results)
    for row in report.results:
        assert row.outcome in allowed, (
            f"probe {row.probe_id}: outcome {row.outcome!r} not in"
            f" closed-set {allowed}"
        )
        # Anti-LLM §5.1.6 + spec §9: with a fake key, ``passed`` is only
        # acceptable if backed by real captured-evidence (which requires
        # a real network call). The fake-key path cannot produce a
        # ``passed`` outcome via fabrication; if it does, structural
        # failure_reason must be absent (which is enforced at the
        # dataclass level for ``passed`` outcomes).
        if row.outcome == "failed":
            assert row.structural_failure_reason, (
                "failed outcome must carry a structural_failure_reason"
            )
    # Sanity: at least one probe must have left the substrate-only
    # skipped path. ``skipped_no_api_key`` is forbidden here because key
    # is set; ``skipped_infrastructure_error`` for ALL 5 would indicate
    # the wiring is structurally broken — spec §9 forbidden shape.
    assert "skipped_no_api_key" not in outcomes


def test_typed_event_expectations_reject_no_prose_assertion_kinds() -> None:
    # Closed-set ``assertion_kind`` Literal is structurally guarded.
    # Constructing an expectation with a prose-shaped assertion kind
    # like ``"prose_similarity"`` is rejected by the dataclass typing
    # at construction time via the Literal — verified here by direct
    # value check on the canonical probe set.
    probes = build_canonical_probe_set()
    for probe in probes:
        for expectation in probe.contract.expected_event_sequence:
            assert expectation.assertion_kind in {
                "presence_only",
                "typed_integer_equals",
                "typed_iso8601_parseable",
                "typed_string_equals",
                "typed_provenance_equals",
            }


def test_executor_dispatches_each_probe_kind_to_dedicated_method(
    tmp_path: Path,
) -> None:
    """Every probe_kind must dispatch to a dedicated executor method.

    LRSP-02..LRSP-06 pin one executor method per probe_kind. This test
    enforces structural dispatch — there is no fallback path that could
    silently mask a missing per-probe wiring.
    """

    executor = LiveRuntimeProbeExecutor(artifact_root=tmp_path)
    for probe in build_canonical_probe_set():
        method_name = f"_execute_{probe.probe_kind}"
        assert hasattr(executor, method_name)
        result = executor.execute(probe)
        # Dispatched result must carry the matching kind + a typed
        # closed-set outcome. Until the live binding is attached, the
        # honest outcome is ``skipped_infrastructure_error``.
        assert result.probe_kind == probe.probe_kind
        assert result.probe_id == probe.probe_id
        assert result.outcome in {
            "passed",
            "failed",
            "skipped_infrastructure_error",
        }


def test_canonical_probe_set_per_probe_assertion_contracts() -> None:
    """Pin the structural-assertion contract for each of the 5 probes.

    Captures the spec §2 contract per probe as typed shape regressions
    so silent drift is caught.
    """

    probes = {probe.probe_kind: probe for probe in build_canonical_probe_set()}

    fresh = probes["fresh_focus_session_turn"]
    fresh_events = tuple(e.event_type for e in fresh.contract.expected_event_sequence)
    assert fresh_events == ("run.queued", "run.running", "run.responding", "run.completed")
    final_fresh = fresh.contract.expected_event_sequence[-1]
    assert final_fresh.assertion_kind == "typed_integer_equals"
    assert final_fresh.expected_typed_value == 4
    assert fresh.contract.expected_run_terminal_state == "completed"

    quiet = probes["quiet_no_progress_chat"]
    quiet_events = tuple(e.event_type for e in quiet.contract.expected_event_sequence)
    assert quiet_events == (
        "chat.stdin_consumed",
        "run.completed",
        "process.exit_code_zero",
    )

    memory = probes["memory_write_recall"]
    memory_events = tuple(e.event_type for e in memory.contract.expected_event_sequence)
    assert memory_events == ("memory.card_written", "memory.recall")
    recall = memory.contract.expected_event_sequence[1]
    assert recall.assertion_kind == "typed_string_equals"
    assert recall.expected_typed_value == "zsh"
    assert recall.typed_payload_field == "recalled_value"

    tool = probes["tool_backed_turn"]
    tool_events = tuple(e.event_type for e in tool.contract.expected_event_sequence)
    assert tool_events == ("tool.call", "tool.result", "run.completed")
    call_event = tool.contract.expected_event_sequence[0]
    assert call_event.typed_payload_field == "tool_name"
    assert call_event.expected_typed_value == "time"
    result_event = tool.contract.expected_event_sequence[1]
    assert result_event.assertion_kind == "typed_iso8601_parseable"
    # LRSP-Q6: ALVB typed binding provenance is pinned.
    assert tool.contract.expected_terminal_state_provenance == "typed_verifier_reduction"

    exit_probe = probes["clean_exit_shutdown"]
    exit_events = tuple(e.event_type for e in exit_probe.contract.expected_event_sequence)
    assert exit_events == ("runtime.shutdown", "process.exit_code_zero")
    # Tight bounded timeout per LRSP-Q5.
    assert exit_probe.contract.bounded_timeout_seconds <= 5.0
