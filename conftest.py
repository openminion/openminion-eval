"""Pytest path bootstrap and cleanup hooks for openminion-eval."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_ROOT = _PROJECT_ROOT / "src"
_FRAMEWORK_ROOT = _PROJECT_ROOT.parent
_OPENMINION_SRC = _FRAMEWORK_ROOT / "openminion" / "src"
_OPENMINION_ROOT = _FRAMEWORK_ROOT / "openminion"

for path in (_SRC_ROOT, _PROJECT_ROOT):
    candidate = str(path)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

for path in (_OPENMINION_SRC, _OPENMINION_ROOT):
    if not path.exists():
        continue
    candidate = str(path)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

from openminion_eval.config import env_flag_enabled  # noqa: E402
from openminion_eval.constants import AGGRESSIVE_CLEAN_ENV  # noqa: E402


def _cleanup_python_artifacts(root: Path) -> None:
    """Remove repo-local Python cache/build residue under the package root."""

    for pattern in (
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        "build",
        "dist",
        "*.egg-info",
    ):
        for path in root.rglob(pattern):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)


def pytest_sessionfinish(session, exitstatus: int) -> None:  # type: ignore[no-untyped-def]
    """Return the repo tree to a clean local state after package-local pytest runs."""

    if env_flag_enabled(AGGRESSIVE_CLEAN_ENV):
        _cleanup_python_artifacts(_PROJECT_ROOT)
