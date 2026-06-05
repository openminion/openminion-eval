from __future__ import annotations

from pathlib import Path


def test_package_local_docs_examples_and_release_smoke_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "docs" / "README.md").is_file()
    assert (root / "docs" / "reference" / "certification-readiness-matrix.md").is_file()
    assert (root / "examples" / "basic_usage.py").is_file()
    assert (root / "scripts" / "release_check.py").is_file()
    assert (root / "src" / "openminion_eval" / "README.md").is_file()
    assert (root / "API_COMPATIBILITY.md").is_file()
    assert (root / "RELEASING.md").is_file()


def test_readme_mentions_package_local_docs_and_example() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()

    assert "examples/basic_usage.py" in readme
    assert "docs/README.md" in readme
    assert "docs/reference/certification-readiness-matrix.md" in readme
    assert "API_COMPATIBILITY.md" in readme
    assert "RELEASING.md" in readme
    assert "scripts/release_check.py" in readme


def test_root_layout_stays_clean_and_intentional() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "docs" / "reference").is_dir()
    assert (root / "docs" / "assets").is_dir()
    assert (root / "src" / "openminion_eval" / "README.md").is_file()

    assert not (root / "fixtures").exists()
    assert not (root / "handoff").exists()
