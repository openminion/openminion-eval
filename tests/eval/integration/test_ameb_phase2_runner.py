"""Tests for the AMEB Phase 2 captured-evidence baseline runner.

These tests exercise the typed runner over the frozen 8-task corpus and
assert the structural shape the published Phase 2 artifact relies on:

1. The runner consumes only TGCR + MTRR typed surfaces (no LLM-judge,
   no prose-similarity, no model-claimed success).
2. Every corpus task produces a typed ``BenchmarkTaskOutcome`` row with
   a captured ``RunTerminalState`` value (one of TGCR's typed enum).
3. Exploratory tasks emit ``ExploratoryDisclosure`` at run start per
   MTRR-Q4 and never confirm completion.
4. Autonomous-completion tasks run their full verifier expectation
   against a no-evidence ``ActionResult`` and the fail-closed verdict
   maps to ``RUN_TERMINAL_FAILED``.
5. The Phase 2 outcome is ``baseline_partial`` — honest captured state
   when no end-to-end agent-loop binding exists at HEAD ``f5b16747``.
"""

from __future__ import annotations

from openminion.modules.brain.schemas.missions import (
    ExploratoryDisclosure,
    MissionType,
    get_mission_verifier_expectation,
)
from openminion.services.runtime.run_status import (
    RUN_TERMINAL_BLOCKED,
    RUN_TERMINAL_FAILED,
    is_run_terminal_state,
)

from tests.eval.integration.ameb_phase2_runner import (
    BenchmarkBaselineReport,
    BenchmarkTaskOutcome,
    build_ameb_corpus,
    build_domain_coverage,
    execute_task,
    run_phase2_baseline,
)


def test_corpus_has_eight_tasks_with_canonical_ids() -> None:
    corpus = build_ameb_corpus()
    assert len(corpus) == 8
    ids = [spec.task_id for spec in corpus]
    assert ids == [
        "ameb-coding-01",
        "ameb-coding-02",
        "ameb-research-01",
        "ameb-research-02",
        "ameb-ops-01",
        "ameb-ops-02",
        "ameb-explore-01",
        "ameb-explore-02",
    ]


def test_corpus_mission_type_distribution_matches_frozen_artifact() -> None:
    corpus = build_ameb_corpus()
    counts: dict[MissionType, int] = {
        "coding": 0,
        "research": 0,
        "operations": 0,
        "exploratory": 0,
    }
    for spec in corpus:
        counts[spec.mission_type] += 1
    assert counts == {
        "coding": 2,
        "research": 2,
        "operations": 2,
        "exploratory": 2,
    }


def test_corpus_contamination_distribution_matches_frozen_artifact() -> None:
    corpus = build_ameb_corpus()
    public_tasks = [
        spec
        for spec in corpus
        if spec.contamination_class in {"public_filtered", "public_modified"}
    ]
    public_ids = sorted(spec.task_id for spec in public_tasks)
    assert public_ids == ["ameb-explore-02", "ameb-research-02"]


def test_execute_task_returns_typed_terminal_state_per_task() -> None:
    corpus = build_ameb_corpus()
    for spec in corpus:
        outcome = execute_task(spec)
        assert isinstance(outcome, BenchmarkTaskOutcome)
        assert outcome.task_id == spec.task_id
        assert outcome.goal_id == f"goal-{spec.task_id}"
        assert outcome.run_id == f"run-{spec.task_id}"
        assert is_run_terminal_state(outcome.run_terminal_state)


def test_exploratory_tasks_emit_disclosure_and_block() -> None:
    corpus = build_ameb_corpus()
    explorations = [s for s in corpus if s.mission_type == "exploratory"]
    assert len(explorations) == 2
    for spec in explorations:
        outcome = execute_task(spec)
        assert outcome.oracle_outcome == "disclosed"
        assert outcome.run_terminal_state == RUN_TERMINAL_BLOCKED
        assert outcome.completion_confirmed is False
        assert isinstance(outcome.exploratory_disclosure, ExploratoryDisclosure)
        assert outcome.exploratory_disclosure.mission_type == "exploratory"
        # No verifier results expected — MTRR-Q4: disclosure-only path.
        assert outcome.verifier_results == ()


def test_autonomous_completion_tasks_fail_closed_under_no_evidence() -> None:
    corpus = build_ameb_corpus()
    autonomous_specs = [
        spec
        for spec in corpus
        if get_mission_verifier_expectation(spec.mission_type).autonomous_completion_supported
    ]
    assert len(autonomous_specs) == 6  # coding + research + operations (2 each)
    for spec in autonomous_specs:
        outcome = execute_task(spec)
        # Under a no-evidence ActionResult the verifier surface must
        # reject; non-conflation rule means partial completion can also
        # not be reached without a passing verifier, so every result
        # must be a failed verdict.
        assert outcome.completion_confirmed is False
        assert outcome.run_terminal_state == RUN_TERMINAL_FAILED
        assert outcome.oracle_outcome in {"fail", "partial"}
        # Every criterion + every deliverable must have a verifier result.
        expected_targets = (
            len(spec.success_criteria) + len(spec.deliverables)
        )
        assert len(outcome.verifier_results) == expected_targets
        # Fail-closed: zero verifier results passed in this baseline.
        assert all(not row.passed for row in outcome.verifier_results)


def test_run_phase2_baseline_returns_typed_partial_report() -> None:
    report = run_phase2_baseline()
    assert isinstance(report, BenchmarkBaselineReport)
    assert report.audited_head_sha.startswith("f5b16747")
    assert len(report.outcomes) == 8
    assert len(report.domain_coverage) == 4
    assert report.phase2_outcome == "baseline_partial"
    # Domain coverage contamination flag must fire for research +
    # exploratory (the two domains carrying public_*-class tasks).
    flags = {row.mission_type: row.contamination_disclosure_flag for row in report.domain_coverage}
    assert flags == {
        "coding": False,
        "research": True,
        "operations": False,
        "exploratory": True,
    }


def test_phase2_report_is_json_serializable() -> None:
    report = run_phase2_baseline()
    payload = report.to_dict()
    # Round-trip JSON to confirm the typed report is durable evidence.
    import json

    serialized = json.dumps(payload, sort_keys=True)
    deserialized = json.loads(serialized)
    assert deserialized["phase2_outcome"] == "baseline_partial"
    assert len(deserialized["outcomes"]) == 8


def test_domain_coverage_counts_match_outcomes() -> None:
    report = run_phase2_baseline()
    coverage = build_domain_coverage(report.outcomes)
    by_type = {row.mission_type: row for row in coverage}
    assert by_type["coding"].task_count == 2
    assert by_type["research"].task_count == 2
    assert by_type["operations"].task_count == 2
    assert by_type["exploratory"].task_count == 2
    # Exploratory: 2 disclosed, 0 pass/partial/fail.
    explore_row = by_type["exploratory"]
    assert explore_row.disclosed_count == 2
    assert explore_row.pass_count == 0
    assert explore_row.partial_count == 0
    assert explore_row.fail_count == 0
