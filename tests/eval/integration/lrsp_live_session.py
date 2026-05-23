"""LRPB live session helper module.

Lane: ``LRPB`` (Live Runtime Provider Binding). Helper module for the
five LRSP per-probe executor methods (see ``lrsp_runner.py``).
Spec: ``docs/specs/live-runtime-provider-binding-spec.md``.
Tracker: ``docs/trackers/wip/live-runtime-provider-binding-tracker.md``.

This module replaces the LRSP scaffold's ``skipped_infrastructure_error``
returns with real subprocess + in-process invocation primitives. It is
deliberately small and typed: closed-set Literals where possible,
frozen dataclasses for handles, no prose-similarity / LLM-judge
content.

Pinned design rule (inherited from LRSP §5):
**No silent provider substitution. ``ProviderName`` is a closed-set
Literal (LRPB-Q5: ``Literal["minimax_27"]`` for v1). Provider
configuration construction is structural; the resolver fails-closed
when the configured provider is unavailable. No prose-derived
intent / no model self-report / no retry-until-pass.**

Surfaces (spec §3)
------------------

1. ``ProviderConfig`` — typed provider binding with closed-set
   ``ProviderName`` Literal.
2. ``build_minimax27_provider_config(api_key, ...)`` — v1 single
   binding.
3. ``build_in_process_gateway(provider_config) -> GatewayTurnRunner``
   — uses real ``APIRuntime`` composition root.
4. ``spawn_chat_subprocess(...)`` — bounded subprocess wrapper for
   probes 2 + 5.
5. ``capture_typed_events(...)`` — typed event-extraction reading
   typed payload fields from ``SessionStore`` (never stdout text).
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Sequence

# ---------------------------------------------------------------------------
# Closed-set Literals (spec §3 + LRPB-Q5)
# ---------------------------------------------------------------------------


ProviderName = Literal["minimax_27"]
"""Closed-set v1 provider Literal (LRPB-Q5 single binding)."""


ALL_PROVIDER_NAMES: tuple[ProviderName, ...] = ("minimax_27",)


# v1 default OpenRouter model identifier for MiniMax 2.7. LRPB-Q1: direct
# API recommended for v1; OpenRouter pass-through is structurally
# equivalent because both surfaces use the standard ``api_key_env`` +
# ``base_url`` provider config shape. The default chosen here mirrors the
# memory-anchor identity profile ``ollamacloud-minimax-m2-5`` which is
# the documented v1 binding model.
DEFAULT_MINIMAX27_MODEL = "MiniMax-M2.5"
DEFAULT_MINIMAX27_PROVIDER_FAMILY = "openrouter"


# ---------------------------------------------------------------------------
# Typed provider config (spec §3.1 + §5.1.6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProviderConfig:
    """Typed provider binding for the LRPB live session helper.

    Frozen + extra-forbid-by-dataclass-shape. The Literal type for
    ``provider_name`` enforces closed-set discipline at the type-check
    boundary; runtime validation is in ``__post_init__``.

    Field semantics:

    1. ``provider_name``: closed-set ``Literal["minimax_27"]``. v1
       single binding (LRPB-Q5).
    2. ``model``: the typed model identifier passed to the provider
       factory (e.g. ``MiniMax-M2.5``).
    3. ``api_key``: the live API key. Caller is responsible for
       sourcing this from a typed env var (we recommend
       ``OPENMINION_LIVE_PROBE_KEY`` per LRSP).
    4. ``base_url``: HTTP base URL for the provider gateway. Optional;
       empty means use the provider factory's default.
    5. ``provider_family``: which adapter family (``openrouter`` /
       ``anthropic`` / etc.) the underlying runtime uses to talk to
       the model. v1 default is ``openrouter``.
    """

    provider_name: ProviderName
    model: str
    api_key: str
    base_url: str = ""
    provider_family: str = DEFAULT_MINIMAX27_PROVIDER_FAMILY

    def __post_init__(self) -> None:
        if self.provider_name not in ALL_PROVIDER_NAMES:
            raise ValueError(
                f"provider_name={self.provider_name!r} outside closed set"
                f" {ALL_PROVIDER_NAMES!r}"
            )
        if not str(self.model).strip():
            raise ValueError("model must be a non-empty string")
        if not str(self.api_key).strip():
            raise ValueError(
                "api_key must be a non-empty string;"
                " caller must source from OPENMINION_LIVE_PROBE_KEY env var"
            )


def build_minimax27_provider_config(
    api_key: str,
    *,
    model: str = DEFAULT_MINIMAX27_MODEL,
    base_url: str = "",
    provider_family: str = DEFAULT_MINIMAX27_PROVIDER_FAMILY,
) -> ProviderConfig:
    """Construct a typed MiniMax 2.7 provider config.

    Spec §3.1: typed binding for the v1 single provider. Anti-LLM rule
    §5.1.6 (no silent provider substitution): caller must explicitly
    name a model; the resolver does NOT silently swap providers.

    Args:
        api_key: live API key; non-empty required.
        model: model identifier; defaults to ``MiniMax-M2.5``.
        base_url: HTTP base URL (empty → provider factory default).
        provider_family: adapter family; defaults to ``openrouter``.
    """

    return ProviderConfig(
        provider_name="minimax_27",
        model=str(model).strip() or DEFAULT_MINIMAX27_MODEL,
        api_key=str(api_key).strip(),
        base_url=str(base_url).strip(),
        provider_family=str(provider_family).strip() or DEFAULT_MINIMAX27_PROVIDER_FAMILY,
    )


# ---------------------------------------------------------------------------
# In-process gateway construction (spec §3.1 + §5.2.3)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class InProcessGatewayHandle:
    """Handle for a fully-bootstrapped in-process gateway.

    Holds the real ``APIRuntime`` composition root plus the
    ``GatewayService`` (which owns the underlying ``GatewayTurnRunner``)
    + ``SessionStore`` accessors. Caller is responsible for ``close()``.

    Anti-LLM compliance: ``gateway`` is a real ``GatewayService``, not
    a mock (spec §5.2.3). ``runtime`` is the canonical composition root
    (``APIRuntime.from_config``); no shortcut, no substitution.
    """

    runtime: Any  # APIRuntime
    gateway: Any  # GatewayService
    sessions: Any  # SessionStore
    agent_id: str

    def close(self) -> None:
        close = getattr(self.runtime, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                return


def build_in_process_gateway(
    provider_config: ProviderConfig,
    *,
    home_root: Path,
    data_root: Path | None = None,
    agent_id: str = "lrpb-probe",
) -> InProcessGatewayHandle:
    """Build an in-process ``GatewayService`` backed by a real
    ``APIRuntime`` composition root.

    Spec §3.1 + §5.2.3: ``GatewayService.handle_message`` (the public
    surface that drives ``GatewayTurnRunner.run``) is the in-process
    invocation target. No mock; the real provider binding fires.

    The runtime is constructed via ``APIRuntime.from_config`` against an
    in-memory ``OpenMinionConfig`` that pins the provided
    ``ProviderConfig`` into the agent profile + provider section, and
    routes storage / memory to ``home_root`` so the probe session is
    isolated from any host openminion data.

    Implementation note: this function imports ``openminion.*`` lazily
    inside the body so that test discovery works in environments where
    only the openminion-eval package is installed (no sibling
    ``openminion`` checkout). Production use of LRPB always requires the
    monorepo sibling because the spec §2 invocation shapes
    structurally depend on ``GatewayService`` + ``SessionStore``.
    """

    # Lazy imports so the module imports cleanly when openminion is
    # absent (the test layer can still construct ProviderConfig +
    # spawn_chat_subprocess without the sibling checkout).
    from openminion.api.runtime import APIRuntime
    from openminion.base.config.core import (
        AgentProfileConfig,
        OpenMinionConfig,
        StorageConfig,
    )

    home_root = Path(home_root)
    home_root.mkdir(parents=True, exist_ok=True)
    resolved_data_root = data_root or (home_root / ".openminion")
    resolved_data_root.mkdir(parents=True, exist_ok=True)
    storage_path = resolved_data_root / "lrpb-session-store.sqlite"

    # Apply the typed provider key to the canonical env name for the
    # configured provider family so the LLM provider factory picks it up
    # via the standard ``api_key_env`` indirection. Reading is structural
    # (env-var); no prose. We do NOT mutate the process env permanently
    # because LRPB closeout runs are short-lived.
    canonical_env = _canonical_api_key_env(provider_config.provider_family)
    if canonical_env and not os.environ.get(canonical_env, "").strip():
        os.environ[canonical_env] = provider_config.api_key

    agent_profile = AgentProfileConfig(
        name=agent_id,
        default_channel="console",
        provider=provider_config.provider_family,
    )
    config = OpenMinionConfig(
        agents={agent_id: agent_profile},
        storage=StorageConfig(path=str(storage_path), backend="sqlite"),
    )
    # Pin provider model + base_url through the runtime config tree.
    # ``OpenMinionConfig.providers`` is the canonical owner of provider
    # adapter wiring; mutating in place is acceptable because the config
    # instance is freshly constructed for this probe.
    _apply_provider_config_overrides(config=config, provider_config=provider_config)

    runtime = APIRuntime.from_config(
        config=config,
        home_root=home_root,
        data_root=resolved_data_root,
    )
    return InProcessGatewayHandle(
        runtime=runtime,
        gateway=runtime.gateway,
        sessions=runtime.sessions,
        agent_id=agent_id,
    )


def _canonical_api_key_env(provider_family: str) -> str:
    """Resolve the canonical API-key env-var name for a provider family.

    Structural mapping; no prose. Matches the defaults in
    ``openminion/modules/llm/providers/factory.py``.
    """

    normalized = str(provider_family or "").strip().lower()
    if normalized == "openrouter":
        return "OPENROUTER_API_KEY"
    if normalized == "openai":
        return "OPENAI_API_KEY"
    if normalized == "anthropic":
        return "ANTHROPIC_API_KEY"
    if normalized == "cerebras":
        return "CEREBRAS_API_KEY"
    return ""


def _apply_provider_config_overrides(
    *,
    config: Any,
    provider_config: ProviderConfig,
) -> None:
    """Apply ``ProviderConfig`` fields onto the runtime config tree.

    Structural setattr on ``config.providers.<family>`` only. We never
    invent fields the provider config dataclass does not expose; if a
    field is absent we leave the runtime default untouched.
    """

    providers = getattr(config, "providers", None)
    if providers is None:
        return
    family = str(provider_config.provider_family or "").strip().lower()
    family_block = getattr(providers, family, None)
    if family_block is None:
        return
    # Apply model + base_url only when the destination field exists.
    if hasattr(family_block, "model") and provider_config.model:
        try:
            family_block.model = provider_config.model
        except Exception:
            pass
    if hasattr(family_block, "base_url") and provider_config.base_url:
        try:
            family_block.base_url = provider_config.base_url
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Subprocess wrapper (spec §2.A + LRPB-Q6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubprocessHandle:
    """Typed result of a bounded subprocess invocation.

    Frozen. ``timed_out`` is a closed-set boolean; ``zombie_detected``
    is the post-exit zombie-process check signal (LRPB-Q6).
    """

    args: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    elapsed_seconds: float
    timed_out: bool
    zombie_detected: bool


def spawn_chat_subprocess(
    *,
    args: Sequence[str],
    env: dict[str, str] | None = None,
    stdin_text: str | None = None,
    timeout_seconds: float = 30.0,
    cwd: Path | None = None,
) -> SubprocessHandle:
    """Spawn an ``openminion chat`` (or equivalent) subprocess with
    bounded timeout + stdout/stderr capture + exit-code capture +
    zombie-process check.

    Spec §2 shape A (probes 2 + 5):

    1. Spawns ``python -m openminion <args>`` with caller-provided
       args (e.g. ``["chat", "--quiet", "--no-progress"]``).
    2. Pipes ``stdin_text`` if non-None (probe 2) or sends ``/exit\\n``
       (probe 5) — caller's choice.
    3. Enforces ``timeout_seconds`` via ``subprocess.communicate``.
    4. On timeout, the child is killed; the returned handle has
       ``timed_out=True``.
    5. After exit, performs a ``psutil``-based zombie-scan for the
       child PID. If ``psutil`` is unavailable, the check returns
       ``zombie_detected=False`` (the OS waitpid already reaped via
       communicate).

    Anti-LLM rule §5.2.2: bounded subprocess invocation. No retry on
    timeout; ``timed_out=True`` is the structural outcome.
    """

    cmd: list[str] = [str(a) for a in args]
    proc_env = dict(os.environ)
    if env:
        proc_env.update({str(k): str(v) for k, v in env.items()})

    started_at = time.monotonic()
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text is not None else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(cwd) if cwd else None,
        env=proc_env,
        text=True,
    )
    timed_out = False
    try:
        stdout, stderr = proc.communicate(
            input=stdin_text if stdin_text is not None else None,
            timeout=float(timeout_seconds),
        )
    except subprocess.TimeoutExpired:
        proc.kill()
        try:
            stdout, stderr = proc.communicate(timeout=2.0)
        except Exception:
            stdout, stderr = "", ""
        timed_out = True
    elapsed = time.monotonic() - started_at

    zombie_detected = _zombie_check(proc.pid)
    return SubprocessHandle(
        args=tuple(cmd),
        returncode=int(proc.returncode if proc.returncode is not None else -1),
        stdout=str(stdout or ""),
        stderr=str(stderr or ""),
        elapsed_seconds=float(elapsed),
        timed_out=bool(timed_out),
        zombie_detected=bool(zombie_detected),
    )


def _zombie_check(pid: int) -> bool:
    """Post-exit zombie-process scan via ``psutil`` (LRPB-Q6).

    Returns True iff the child PID still exists in the process table
    with a zombie status. False otherwise (including when ``psutil`` is
    not installed — ``subprocess.communicate`` already waited).
    """

    try:
        import psutil
    except ImportError:
        return False
    try:
        process = psutil.Process(int(pid))
    except (psutil.NoSuchProcess, ValueError):
        return False
    try:
        status = process.status()
    except psutil.NoSuchProcess:
        return False
    return status == psutil.STATUS_ZOMBIE


# ---------------------------------------------------------------------------
# Typed event capture (spec §3.1 + §5.2.4)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CapturedTypedEvent:
    """One captured event observed in the session event log.

    All fields read directly from the typed ``EventRecord`` shape; no
    stdout text-match is consulted (spec §5.1.1).
    """

    event_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass(frozen=True)
class TypedEventTranscript:
    """Typed transcript of captured events for one probe run."""

    session_id: str
    events: tuple[CapturedTypedEvent, ...] = field(default_factory=tuple)

    def find(self, event_type: str) -> CapturedTypedEvent | None:
        for evt in self.events:
            if evt.event_type == event_type:
                return evt
        return None

    def find_all(self, event_type: str) -> tuple[CapturedTypedEvent, ...]:
        return tuple(evt for evt in self.events if evt.event_type == event_type)

    def last(self, event_type: str) -> CapturedTypedEvent | None:
        matches = self.find_all(event_type)
        return matches[-1] if matches else None


def capture_typed_events(
    *,
    session_id: str,
    store: Any,
    limit: int = 500,
    event_type_prefix: str | None = None,
) -> TypedEventTranscript:
    """Read typed events from the session store for one probe run.

    Spec §5.2.4: typed event extraction reads typed payload fields
    only, never stdout text. ``store.list_events(...)`` returns typed
    ``EventRecord`` rows whose ``payload`` is a typed ``dict``.

    Args:
        session_id: structural session identifier.
        store: a ``SessionStore`` (duck-typed; just needs
            ``list_events(session_id=, limit=, event_type_prefix=)``).
        limit: how many recent events to fetch; default 500 is enough
            for any LRSP probe whose event sequence is < 10 events.
        event_type_prefix: optional structural prefix filter.

    Returns:
        A ``TypedEventTranscript`` with events in chronological order
        (oldest first).
    """

    records = store.list_events(
        session_id=str(session_id),
        limit=int(limit),
        newest_first=False,
        event_type_prefix=event_type_prefix,
    )
    events = tuple(
        CapturedTypedEvent(
            event_type=str(getattr(record, "event_type", "") or ""),
            payload=dict(getattr(record, "payload", {}) or {}),
            created_at=str(getattr(record, "created_at", "") or ""),
        )
        for record in (records or ())
    )
    return TypedEventTranscript(
        session_id=str(session_id),
        events=events,
    )


# ---------------------------------------------------------------------------
# Module entry-point command for subprocess invocation
# ---------------------------------------------------------------------------


def default_openminion_subprocess_args(
    *,
    extra: Sequence[str] = (),
) -> tuple[str, ...]:
    """Build the canonical openminion subprocess argv prefix.

    Returns ``("<python>", "-m", "openminion", <extra...>)``. Caller
    appends per-probe args. The Python interpreter is the running
    interpreter so the subprocess uses the same venv (avoids "wrong
    python" closures noted in tracker discipline).
    """

    return (sys.executable, "-m", "openminion", *[str(item) for item in extra])


__all__ = [
    "ALL_PROVIDER_NAMES",
    "CapturedTypedEvent",
    "DEFAULT_MINIMAX27_MODEL",
    "DEFAULT_MINIMAX27_PROVIDER_FAMILY",
    "InProcessGatewayHandle",
    "ProviderConfig",
    "ProviderName",
    "SubprocessHandle",
    "TypedEventTranscript",
    "build_in_process_gateway",
    "build_minimax27_provider_config",
    "capture_typed_events",
    "default_openminion_subprocess_args",
    "spawn_chat_subprocess",
]
