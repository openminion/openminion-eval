from __future__ import annotations

from pathlib import Path


def test_release_check_covers_docs_and_boundary_contract() -> None:
    release_check_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_release_package.py"
    )
    release_check = release_check_path.read_text()

    assert "_assert_package_docs_shape" in release_check
    assert 'REPO_ROOT / "docs" / "artifact-workflows.md"' in release_check
    assert 'REPO_ROOT / "docs" / "artifact-schemas.md"' in release_check
    assert 'REPO_ROOT / "docs" / "certification-readiness-matrix.md"' in release_check
    assert 'REPO_ROOT / "docs" / "eval-cases.md"' in release_check
    assert 'REPO_ROOT / "docs" / "eval-families.md"' in release_check
    assert 'REPO_ROOT / "docs" / "memory-effectiveness.md"' in release_check
    assert 'REPO_ROOT / "docs" / "memory-context-scorecard.md"' in release_check
    assert 'REPO_ROOT / "docs" / "ci-recipes.md"' in release_check
    assert 'REPO_ROOT / "docs" / "artifacts-and-manual-grading.md"' in release_check
    assert 'REPO_ROOT / "docs" / "standalone-claim-alignment.md"' in release_check
    assert 'REPO_ROOT / "docs" / "source-tree-owner-map.md"' in release_check
    assert '"docs" / "reference"' not in release_check
    assert '"README.md"' in release_check
    assert "openminion_eval.cases" in release_check
    assert "registered_cases" in release_check
    assert "select_transcripts" in release_check
    assert "load_eval_dataset_jsonl" in release_check
    assert "load_red_team_security_artifact" in release_check
    assert "load_synthetic_golden_artifact" in release_check
    assert "BoundaryArtifactValidationError root export missing" in release_check
    assert "boundary artifact version drifted" in release_check
    assert "EvalScorer root export missing" in release_check
    assert "EvalScorerSpec root export missing" in release_check
    assert "EvalScorerInfo root export missing" in release_check
    assert "threshold-aware scorer metadata drifted" in release_check
    assert "scorer registry metadata drifted" in release_check
    assert "CliSubject root export missing" in release_check
    assert "HttpSubject root export missing" in release_check
    assert "ReplaySubject root export missing" in release_check
    assert "dataset template root export drifted" in release_check
    assert "IntegrationProbeDisposition root export missing" in release_check
    assert "render_suite_result_markdown root export missing" in release_check
    assert "suite diff version drifted" in release_check
    assert "EvalSuiteDiffArtifact root export missing" in release_check
    assert "build_suite_diff_artifact root export missing" in release_check
    assert "load_suite_diff root export missing" in release_check
    assert "write_suite_diff root export missing" in release_check
    assert "render_suite_diff_artifact_markdown root export missing" in release_check
    assert "suite diff IO smoke failed" in release_check
    assert "suite diff report renderer smoke failed" in release_check
    assert "suite-diff CLI artifact missing" in release_check
    assert "suite-diff report CLI artifact missing" in release_check
    assert "artifact bundle CLI index missing" in release_check
    assert "artifact bundle copied JSON missing" in release_check
    assert "artifact bundle rendered report missing" in release_check
    assert "manual queue CLI artifact missing" in release_check
    assert "manual apply CLI artifact missing" in release_check
    assert "load_manual_results" in release_check
    assert "load_manual_review_queue" in release_check
    assert "render_memory_scorecard_markdown root export missing" in release_check
    assert "render_delegated_memory_scorecard_markdown root export missing" in (
        release_check
    )
    assert "render_memory_context_scorecard_markdown root export missing" in (
        release_check
    )
    assert "built-in family registry is empty" in release_check
    assert "manual review queue export drifted" in release_check
    assert "manual review queue IO smoke failed" in release_check
    assert "manual results IO smoke failed" in release_check
    assert "runtime reliability scoring smoke failed" in release_check
    assert "build_runtime_reliability_report root export missing" in release_check
    assert '"families"' in release_check
    assert "py.typed missing from installed wheel" in release_check
    assert "__version__ root export missing" in release_check
    assert '"openminion-eval"' in release_check
    assert '"openminion_eval"' in release_check
    assert "README advertises unpublished PyPI package surface" in release_check
    assert "openminion_eval.memory_eval" in release_check
    assert "MemoryEffectivenessCase root export missing" in release_check
    assert "MemoryBenchmarkSource root export missing" in release_check
    assert "benchmark adapter version drifted" in release_check
    assert "load_packaged_memory_benchmark_sample root export missing" in release_check
    assert "default_memory_benchmark_manifest_path root export missing" in release_check
    assert "benchmark adapter packaged sample missing" in release_check
    assert "benchmark adapter packaged sample failed to load" in release_check
    assert '"--benchmark"' in release_check
    assert "benchmark score CLI artifact missing" in release_check
    assert "load_memory_effectiveness_cases root export missing" in release_check
    assert (
        "default_memory_effectiveness_cases_path root export missing" in release_check
    )
    assert "memory effectiveness fixture count drifted" in release_check
    assert "memory effectiveness scoring smoke failed" in release_check
    assert '"memory-effectiveness"' in release_check
    assert "memory-effectiveness CLI artifact missing" in release_check
    assert '"artifact"' in release_check
    assert '"validate"' in release_check
    assert "build_delegated_memory_scorecard root export missing" in release_check
    assert "build_delegated_memory_scorecard_diff root export missing" in release_check
    assert "compare_delegated_memory_scorecards root export missing" in release_check
    assert "delegated memory diff version drifted" in release_check
    assert "load_delegated_memory_scorecard root export missing" in release_check
    assert "load_delegated_memory_scorecard_diff root export missing" in release_check
    assert "write_delegated_memory_scorecard root export missing" in release_check
    assert "write_delegated_memory_scorecard_diff root export missing" in (
        release_check
    )
    assert '"delegated-score"' in release_check
    assert "delegated memory scorecard IO smoke failed" in release_check
    assert "delegated memory scorecard diff smoke failed" in release_check
    assert "delegated memory diff IO smoke failed" in release_check
    assert "delegated memory diff report renderer smoke failed" in release_check
    assert "delegated memory report renderer smoke failed" in release_check
    assert "delegated-memory CLI artifact missing" in release_check
    assert "delegated-memory report CLI artifact missing" in release_check
    assert "delegated-memory diff CLI artifact missing" in release_check
    assert "delegated-memory diff report CLI artifact missing" in release_check
    assert '"delegated-diff"' in release_check
    assert "MemoryContextScorecardV1 root export missing" in release_check
    assert "build_memory_context_scorecard root export missing" in release_check
    assert "memory context scorecard packaged fixture missing" in release_check
    assert "memory context scorecard smoke failed" in release_check
    assert "memory context scorecard report renderer smoke failed" in release_check
    assert '"memory-context-scorecard"' in release_check
    assert "memory-context-scorecard CLI artifact missing" in release_check
    assert "memory-context report CLI artifact missing" in release_check
    assert "expected_returncode=1" in release_check
    assert "openminion-eval" in release_check
