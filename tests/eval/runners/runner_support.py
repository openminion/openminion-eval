from __future__ import annotations

from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[3]
PACKAGE_SRC = PACKAGE_ROOT / "src"
PACKAGE_TESTS = PACKAGE_ROOT / "tests"
FRAMEWORK_ROOT = PACKAGE_ROOT.parent
OPENMINION_SRC = FRAMEWORK_ROOT / "openminion" / "src"


def configure_repo_paths(*, include_tests: bool = False) -> None:
    repo_local = PACKAGE_TESTS if include_tests else PACKAGE_ROOT
    for path in (PACKAGE_SRC, repo_local, OPENMINION_SRC):
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))


def generated_output_root(name: str) -> Path:
    from openminion.base.generated_paths import resolve_generated_root

    return resolve_generated_root(home_root=FRAMEWORK_ROOT) / name
