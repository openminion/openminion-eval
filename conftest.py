"""Pytest conftest for openminion-eval.

Prepends the package src/ and the project root to sys.path so:

1. ``import openminion_eval.*`` works without an editable install.
2. Test helpers can be imported via the project root (for example
   ``tests.eval.*`` and the repo-local integration tooling at
   ``tests.eval.integration.*``).

When the surrounding monorepo is also present on disk (sibling
``openminion/`` checkout), its source roots are added too so that
repo-local integration tests can import ``openminion.modules.*`` /
``openminion.services.*``. Those paths are conditional on existence so
standalone installs (no monorepo sibling) do not get noisy ``sys.path``
entries.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent
_SRC_ROOT = _PROJECT_ROOT / "src"
_FRAMEWORK_ROOT = _PROJECT_ROOT.parent
_OPENMINION_SRC = _FRAMEWORK_ROOT / "openminion" / "src"
_OPENMINION_ROOT = _FRAMEWORK_ROOT / "openminion"

# Always-available roots: the package src/ and the project root (the
# project root makes ``tests.eval.*`` importable).
for path in (_SRC_ROOT, _PROJECT_ROOT):
    candidate = str(path)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

# Monorepo-only roots: present only when this package lives inside the
# agent-frameworks monorepo. Guard with .exists() so standalone installs
# (no sibling openminion/ checkout) do not get phantom sys.path entries.
for path in (_OPENMINION_SRC, _OPENMINION_ROOT):
    if not path.exists():
        continue
    candidate = str(path)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)


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

    _cleanup_python_artifacts(_PROJECT_ROOT)
