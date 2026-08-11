from __future__ import annotations

import os
from pathlib import Path
import sys

from tests.eval.runners.runner_support import (
    OPENMINION_SRC,
    PACKAGE_ROOT,
    PACKAGE_SRC,
    SOPHIAGRAPH_SRC,
    configure_repo_paths,
    generated_output_root,
    isolate_runtime_roots,
)


def test_runner_roots_replace_ambient_workspace_paths(monkeypatch) -> None:
    monkeypatch.setenv("OPENMINION_HOME", "/unsafe/home")
    monkeypatch.setenv("OPENMINION_DATA_ROOT", "/unsafe/data")
    monkeypatch.setenv("OPENMINION_GENERATED_ROOT", "/unsafe/generated")

    generated_root = isolate_runtime_roots(prefix="openminion-eval-test-")
    home_root = Path(os.environ["OPENMINION_HOME"])

    assert home_root != Path("/unsafe/home")
    assert Path(os.environ["OPENMINION_DATA_ROOT"]) == home_root / ".openminion"
    assert Path(os.environ["OPENMINION_GENERATED_ROOT"]) == generated_root
    assert generated_output_root("report") == (generated_root / "report").resolve()


def test_every_executable_eval_runner_uses_isolated_roots() -> None:
    runners_root = Path(__file__).resolve().parent
    runners = sorted(runners_root.glob("run_*.py"))
    assert runners

    for runner in runners:
        text = runner.read_text(encoding="utf-8")
        assert "isolate_runtime_roots(" in text, runner.name


def test_configure_repo_paths_includes_package_and_sibling_sources(
    monkeypatch,
) -> None:
    expected = (PACKAGE_SRC, PACKAGE_ROOT, OPENMINION_SRC, SOPHIAGRAPH_SRC)
    expected_strings = {str(path) for path in expected}
    monkeypatch.setattr(
        sys,
        "path",
        [entry for entry in sys.path if entry not in expected_strings],
    )

    configure_repo_paths()

    assert all(str(path) in sys.path for path in expected)
