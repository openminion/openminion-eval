from __future__ import annotations

from pathlib import Path


def test_release_check_covers_docs_and_boundary_contract() -> None:
    release_check = (
        Path(__file__).resolve().parents[2] / "scripts" / "check_release_package.py"
    ).read_text()

    assert "_assert_package_docs_shape" in release_check
    assert '"certification-readiness-matrix.md"' in release_check
    assert '"README.md"' in release_check
    assert "openminion_eval.memory_eval" in release_check
    assert "openminion-eval" in release_check
