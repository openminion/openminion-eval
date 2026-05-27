from __future__ import annotations

from pathlib import Path

import conftest
from openminion_eval.constants import AGGRESSIVE_CLEAN_ENV


def test_pytest_sessionfinish_leaves_cache_by_default(
    tmp_path: Path, monkeypatch
) -> None:
    cache_dir = tmp_path / ".pytest_cache"
    cache_dir.mkdir()
    monkeypatch.delenv(AGGRESSIVE_CLEAN_ENV, raising=False)
    monkeypatch.setattr(conftest, "_PROJECT_ROOT", tmp_path)

    conftest.pytest_sessionfinish(None, 0)

    assert cache_dir.exists()


def test_pytest_sessionfinish_aggressive_cleanup_is_opt_in(
    tmp_path: Path, monkeypatch
) -> None:
    cache_dir = tmp_path / ".pytest_cache"
    pycache_dir = tmp_path / "pkg" / "__pycache__"
    cache_dir.mkdir()
    pycache_dir.mkdir(parents=True)
    monkeypatch.setenv(AGGRESSIVE_CLEAN_ENV, "1")
    monkeypatch.setattr(conftest, "_PROJECT_ROOT", tmp_path)

    conftest.pytest_sessionfinish(None, 0)

    assert not cache_dir.exists()
    assert not pycache_dir.exists()
