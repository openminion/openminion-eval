from __future__ import annotations

from pathlib import Path


def test_release_check_covers_docs_and_boundary_contract() -> None:
    release_check_path = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_release_package.py"
    )
    release_check = release_check_path.read_text()

    assert "_assert_package_docs_shape" in release_check
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
    assert "threshold-aware scorer metadata drifted" in release_check
    assert "built-in family registry is empty" in release_check
    assert "manual review queue export drifted" in release_check
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
    assert "load_memory_effectiveness_cases root export missing" in release_check
    assert (
        "default_memory_effectiveness_cases_path root export missing" in release_check
    )
    assert "memory effectiveness fixture count drifted" in release_check
    assert "memory effectiveness scoring smoke failed" in release_check
    assert "MemoryContextScorecardV1 root export missing" in release_check
    assert "build_memory_context_scorecard root export missing" in release_check
    assert "memory context scorecard packaged fixture missing" in release_check
    assert "memory context scorecard smoke failed" in release_check
    assert '"memory-context-scorecard"' in release_check
    assert "memory-context-scorecard CLI artifact missing" in release_check
    assert "expected_returncode=1" in release_check
    assert "openminion-eval" in release_check
