from __future__ import annotations

import tomllib
from pathlib import Path


def test_package_local_docs_examples_and_release_smoke_exist() -> None:
    root = Path(__file__).resolve().parents[2]

    assert (root / "docs" / "README.md").is_file()
    assert (root / "docs" / "certification-readiness-matrix.md").is_file()
    assert (root / "docs" / "eval-cases.md").is_file()
    assert (root / "docs" / "eval-families.md").is_file()
    assert (root / "docs" / "ci-recipes.md").is_file()
    assert (root / "docs" / "artifacts-and-manual-grading.md").is_file()
    assert (root / "docs" / "source-tree-owner-map.md").is_file()
    assert (root / "docs" / "standalone-claim-alignment.md").is_file()
    assert (root / "examples" / "basic_usage.py").is_file()
    assert (root / "scripts" / "release_check.py").is_file()
    assert (root / "src" / "openminion_eval" / "README.md").is_file()
    assert (root / "src" / "openminion_eval" / "py.typed").is_file()
    assert (root / "API_COMPATIBILITY.md").is_file()
    assert (root / "RELEASING.md").is_file()


def test_readme_mentions_package_local_docs_and_example() -> None:
    readme = (Path(__file__).resolve().parents[2] / "README.md").read_text()

    assert "examples/basic_usage.py" in readme
    assert "docs/README.md" in readme
    assert "docs/certification-readiness-matrix.md" in readme
    assert "docs/eval-cases.md" in readme
    assert "docs/eval-families.md" in readme
    assert "docs/ci-recipes.md" in readme
    assert "docs/artifacts-and-manual-grading.md" in readme
    assert "docs/source-tree-owner-map.md" in readme
    assert "docs/standalone-claim-alignment.md" in readme
    assert "API_COMPATIBILITY.md" in readme
    assert "RELEASING.md" in readme
    assert "scripts/release_check.py" in readme


def test_root_layout_stays_clean_and_intentional() -> None:
    root = Path(__file__).resolve().parents[2]

    assert not (root / "docs" / "reference").exists()
    assert (root / "docs" / "assets").is_dir()
    assert (root / "src" / "openminion_eval" / "README.md").is_file()

    assert not (root / "fixtures").exists()
    assert not (root / "handoff").exists()


def test_package_metadata_declares_public_urls() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
    )

    assert pyproject["project"]["urls"] == {
        "Homepage": "https://github.com/openminion/openminion-eval",
        "Repository": "https://github.com/openminion/openminion-eval",
        "Issues": "https://github.com/openminion/openminion-eval/issues",
        "Documentation": "https://github.com/openminion/openminion-eval#readme",
    }


def test_package_metadata_includes_pep_561_marker() -> None:
    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[2] / "pyproject.toml").read_text()
    )

    assert pyproject["tool"]["setuptools"]["package-data"]["openminion_eval"] == [
        "py.typed"
    ]


def test_source_tree_owner_map_covers_public_root_modules() -> None:
    owner_map = (
        Path(__file__).resolve().parents[2] / "docs" / "source-tree-owner-map.md"
    ).read_text()

    for module_name in (
        "datasets.py",
        "suite_artifacts.py",
        "manual.py",
        "family_registry.py",
        "cli.py",
        "py.typed",
        "integration_quarantine.py",
    ):
        assert module_name in owner_map
