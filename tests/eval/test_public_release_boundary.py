from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest


def _openminion_runtime_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "openminion" or alias.name.startswith("openminion."):
                    imports.append(f"{path}:{node.lineno}:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "openminion" or module.startswith("openminion."):
                imports.append(f"{path}:{node.lineno}:{module}")
    return imports


def test_public_eval_tests_do_not_import_openminion_runtime() -> None:
    tests_root = Path(__file__).resolve().parent
    ignored_public_files = {
        tests_root / "test_memory_eval.py",
        tests_root / "test_eval_adjacent_owner_dispositions.py",
    }
    offenders = []
    for path in sorted(tests_root.rglob("test_*.py")):
        if "integration" in path.relative_to(tests_root).parts:
            continue
        if path in ignored_public_files:
            continue
        offenders.extend(_openminion_runtime_imports(path))

    assert offenders == []


def test_memory_harness_is_not_shipped_in_public_package() -> None:
    with pytest.raises(ModuleNotFoundError) as excinfo:
        importlib.import_module("openminion_eval.memory_eval")

    assert excinfo.value.name == "openminion_eval.memory_eval"


def test_memory_scorer_is_not_shipped_in_public_scorer_module() -> None:
    scorer_module = importlib.import_module("openminion_eval.scorer")

    assert not hasattr(scorer_module, "MemoryEvalScorer")
