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
    assert "built-in family registry is empty" in release_check
    assert "manual review queue export drifted" in release_check
    assert "py.typed missing from installed wheel" in release_check
    assert "__version__ root export missing" in release_check
    assert '"openminion-eval"' in release_check
    assert '"openminion_eval"' in release_check
    assert "README advertises unpublished PyPI package surface" in release_check
    assert "openminion_eval.memory_eval" in release_check
    assert "openminion-eval" in release_check
