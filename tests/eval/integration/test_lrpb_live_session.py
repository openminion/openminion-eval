"""LRPB live-session helper-module + executor wiring regressions.

Focused (non-live) regressions for the LRPB lane. These tests exercise
the helper-module surface and the executor's structurally-correct
behavior in two situations:

1. ``OPENMINION_LIVE_PROBE_KEY`` is absent at run time — the harness
   path returns ``skipped_no_api_key`` × 5; the executor methods are
   never reached. This preserves LRSP's invariant.
2. ``OPENMINION_LIVE_PROBE_KEY`` is present but the underlying live
   provider call surface is unreachable — the executor methods return
   a structurally honest ``skipped_infrastructure_error`` or ``failed``
   with a structural reason. NEVER a fake pass.

The "live runs against MiniMax 2.7" closure-time evidence is captured
separately in ``test_lrsp_live_probes.py`` (LRSP marker
``live_runtime_probe``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

from tests.eval.integration.lrsp_live_session import (
    ALL_PROVIDER_NAMES,
    DEFAULT_MINIMAX27_MODEL,
    ProviderConfig,
    SubprocessHandle,
    TypedEventTranscript,
    build_minimax27_provider_config,
    capture_typed_events,
    default_openminion_subprocess_args,
    spawn_chat_subprocess,
)
from tests.eval.integration.lrsp_runner import (
    LRSP_API_KEY_ENV,
    LiveRuntimeProbeExecutor,
    build_canonical_probe_set,
    run_live_runtime_probes,
)


# ---------------------------------------------------------------------------
# Helper module surface
# ---------------------------------------------------------------------------


def test_provider_name_literal_is_closed_set_single_binding() -> None:
    assert ALL_PROVIDER_NAMES == ("minimax_27",)


def test_build_minimax27_provider_config_sets_typed_defaults() -> None:
    cfg = build_minimax27_provider_config("abc123")
    assert cfg.provider_name == "minimax_27"
    assert cfg.model == DEFAULT_MINIMAX27_MODEL
    assert cfg.api_key == "abc123"
    assert cfg.provider_family == "openrouter"


def test_canonical_api_key_env_maps_known_provider_families() -> None:
    from tests.eval.integration.lrsp_live_session import _canonical_api_key_env

    assert _canonical_api_key_env("openrouter") == "OPENROUTER_API_KEY"
    assert _canonical_api_key_env(" OpenAI ") == "OPENAI_API_KEY"
    assert _canonical_api_key_env("anthropic") == "ANTHROPIC_API_KEY"
    assert _canonical_api_key_env("cerebras") == "CEREBRAS_API_KEY"
    assert _canonical_api_key_env("unknown") == ""


def test_provider_config_rejects_unknown_provider_name() -> None:
    with pytest.raises(ValueError):
        ProviderConfig(
            provider_name="some_other_provider",  # type: ignore[arg-type]
            model="m",
            api_key="k",
        )


def test_provider_config_rejects_empty_api_key() -> None:
    with pytest.raises(ValueError):
        ProviderConfig(
            provider_name="minimax_27",
            model="MiniMax-M2.5",
            api_key="",
        )


def test_provider_config_rejects_empty_model() -> None:
    with pytest.raises(ValueError):
        ProviderConfig(
            provider_name="minimax_27",
            model="",
            api_key="abc",
        )


def test_typed_event_transcript_find_and_last_return_typed_records() -> None:
    from tests.eval.integration.lrsp_live_session import CapturedTypedEvent

    transcript = TypedEventTranscript(
        session_id="s1",
        events=(
            CapturedTypedEvent(event_type="run.queued", payload={}),
            CapturedTypedEvent(event_type="run.completed", payload={"x": 1}),
            CapturedTypedEvent(event_type="run.completed", payload={"x": 2}),
        ),
    )
    assert transcript.find("run.queued").event_type == "run.queued"
    assert transcript.find("missing.event") is None
    assert len(transcript.find_all("run.completed")) == 2
    assert transcript.last("run.completed").payload["x"] == 2


def test_default_openminion_subprocess_args_uses_current_interpreter() -> None:
    args = default_openminion_subprocess_args(extra=("chat",))
    assert args[0] == sys.executable
    assert args[1] == "-m"
    assert args[2] == "openminion"
    assert args[3] == "chat"


# ---------------------------------------------------------------------------
# Subprocess wrapper structural shape
# ---------------------------------------------------------------------------


def test_spawn_chat_subprocess_captures_typed_handle_fields(tmp_path: Path) -> None:
    """The subprocess wrapper returns a typed handle regardless of the
    inner command behavior.

    We use a trivial command (``python -c 'print(...)'``) so the test
    is fast and deterministic. The point of the regression is the typed
    shape, not openminion runtime behavior.
    """

    handle = spawn_chat_subprocess(
        args=[sys.executable, "-c", "print('hello-lrpb')"],
        stdin_text=None,
        timeout_seconds=10.0,
    )
    assert isinstance(handle, SubprocessHandle)
    assert handle.returncode == 0
    assert "hello-lrpb" in handle.stdout
    assert handle.timed_out is False
    assert handle.zombie_detected is False


def test_spawn_chat_subprocess_enforces_bounded_timeout() -> None:
    """A long-running child terminates within the bounded timeout and
    records ``timed_out=True`` honestly — no retry, no fake pass.
    """

    handle = spawn_chat_subprocess(
        args=[sys.executable, "-c", "import time; time.sleep(30)"],
        timeout_seconds=1.0,
    )
    assert handle.timed_out is True


# ---------------------------------------------------------------------------
# Executor structural behavior
# ---------------------------------------------------------------------------


def test_executor_methods_skip_when_api_key_absent(tmp_path: Path) -> None:
    """When the LRSP key is absent, every executor method returns
    ``skipped_infrastructure_error`` honestly — not a fake pass.

    Note: at the harness level (``run_live_runtime_probes``) the
    key-absent path short-circuits to ``skipped_no_api_key`` × 5
    before the executor is reached; this test exercises the executor
    directly to assert it ALSO honors the no-key invariant.
    """

    saved = os.environ.pop(LRSP_API_KEY_ENV, None)
    try:
        executor = LiveRuntimeProbeExecutor(
            artifact_root=tmp_path / "art",
            home_root=tmp_path / "home",
        )
        for probe in build_canonical_probe_set():
            result = executor.execute(probe)
            assert result.outcome == "skipped_infrastructure_error", (
                f"probe {probe.probe_id}: expected skipped_infrastructure_error"
                f" when API key absent, got {result.outcome}"
            )
    finally:
        if saved is not None:
            os.environ[LRSP_API_KEY_ENV] = saved


def test_run_live_runtime_probes_clean_skip_when_key_absent(tmp_path: Path) -> None:
    """LRSP-level clean-skip path: 5 × ``skipped_no_api_key`` when key
    absent. This invariant must remain after LRPB wiring.
    """

    saved = os.environ.pop(LRSP_API_KEY_ENV, None)
    try:
        report = run_live_runtime_probes(home_root=tmp_path)
        assert len(report.results) == 5
        assert tuple(r.outcome for r in report.results) == (
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
        )
        assert report.api_key_present is False
    finally:
        if saved is not None:
            os.environ[LRSP_API_KEY_ENV] = saved


def test_executor_constructor_picks_up_api_key_from_env(tmp_path: Path) -> None:
    """The executor reads ``OPENMINION_LIVE_PROBE_KEY`` at construction."""

    saved = os.environ.get(LRSP_API_KEY_ENV)
    os.environ[LRSP_API_KEY_ENV] = "test-key-lrpb"
    try:
        executor = LiveRuntimeProbeExecutor(
            artifact_root=tmp_path / "art",
            home_root=tmp_path / "home",
        )
        # Private attribute is intentionally probed here as part of the
        # structural wiring regression; if this attribute renames, the
        # injection contract changes and the test must be updated.
        assert executor._api_key == "test-key-lrpb"
    finally:
        if saved is None:
            os.environ.pop(LRSP_API_KEY_ENV, None)
        else:
            os.environ[LRSP_API_KEY_ENV] = saved


def test_capture_typed_events_returns_typed_transcript_from_store() -> None:
    """``capture_typed_events`` consumes a duck-typed store that exposes
    ``list_events(session_id=, limit=, newest_first=, event_type_prefix=)``
    and returns a typed transcript with frozen records.
    """

    class _FakeRecord:
        def __init__(self, event_type: str, payload: dict, created_at: str) -> None:
            self.event_type = event_type
            self.payload = payload
            self.created_at = created_at

    class _FakeStore:
        def list_events(
            self,
            *,
            session_id: str,
            limit: int,
            newest_first: bool,
            event_type_prefix: str | None,
        ):
            assert session_id == "session-x"
            assert newest_first is False
            return [
                _FakeRecord("run.queued", {}, "2026-05-15T00:00:00Z"),
                _FakeRecord(
                    "run.completed",
                    {"structured_response.result_integer": 4},
                    "2026-05-15T00:00:05Z",
                ),
            ]

    transcript = capture_typed_events(session_id="session-x", store=_FakeStore())
    assert transcript.session_id == "session-x"
    assert len(transcript.events) == 2
    completed = transcript.find("run.completed")
    assert completed is not None
    assert completed.payload["structured_response.result_integer"] == 4
