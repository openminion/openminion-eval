from __future__ import annotations

from pathlib import Path

import conftest


def test_cleanup_python_artifacts_removes_repo_local_cache_dirs(tmp_path: Path) -> None:
    cache_dirs = [
        tmp_path / "__pycache__",
        tmp_path / ".pytest_cache",
        tmp_path / ".ruff_cache",
        tmp_path / "build",
        tmp_path / "dist",
        tmp_path / "src" / "openminion_eval.egg-info",
    ]
    for path in cache_dirs:
        path.mkdir(parents=True)
        (path / "sentinel.txt").write_text("x")

    conftest._cleanup_python_artifacts(tmp_path)

    for path in cache_dirs:
        assert not path.exists()
