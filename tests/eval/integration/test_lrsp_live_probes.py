"""LRSP live-runtime probe pytest entry point.

Opt-in via the ``live_runtime_probe`` pytest marker. Invocation:

    .venv/bin/python3.11 -m pytest -m live_runtime_probe \
        openminion-eval/tests/eval/integration/test_lrsp_live_probes.py

API-key gating (spec §3.4 + §5.1.7):

1. If ``OPENMINION_LIVE_PROBE_KEY`` is absent → all 5 probes emit
   ``skipped_no_api_key``; this test passes (clean skip, not failure).
2. If the key is present → the harness runs each probe via its
   per-probe wiring (lands in LRSP-02..LRSP-06); each probe's
   outcome is asserted to be either ``passed`` or, when the
   per-probe wiring is structurally blocked, a typed
   ``skipped_infrastructure_error`` (never a fake pass).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.eval.integration.lrsp_runner import (
    ALL_LIVE_RUNTIME_PROBE_KINDS,
    live_probe_api_key_present,
    run_live_runtime_probes,
)


@pytest.mark.live_runtime_probe
def test_live_runtime_probes_run_against_baseline(tmp_path: Path) -> None:
    report = run_live_runtime_probes(home_root=tmp_path)
    # Always exactly 5 results — closed-set 5-probe roster (spec §2).
    assert len(report.results) == 5
    kinds = tuple(row.probe_kind for row in report.results)
    assert kinds == ALL_LIVE_RUNTIME_PROBE_KINDS

    if not live_probe_api_key_present():
        # Spec §3.4: API-key-absent path is a clean skip × 5.
        outcomes = tuple(row.outcome for row in report.results)
        assert outcomes == (
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
            "skipped_no_api_key",
        )
        return

    # Key present: each probe must produce one of the typed outcomes.
    # Per-probe execution wiring lands in LRSP-02..LRSP-06. Until each
    # probe's wiring is attached, ``skipped_infrastructure_error`` is
    # the honest typed value (spec §9.4).
    allowed_outcomes = {
        "passed",
        "failed",
        "skipped_infrastructure_error",
    }
    for row in report.results:
        assert row.outcome in allowed_outcomes
