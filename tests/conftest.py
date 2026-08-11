from __future__ import annotations

import os
from pathlib import Path
import tempfile

import pytest


_COLLECTION_RUNTIME_TMP = tempfile.TemporaryDirectory(
    prefix="openminion-eval-pytest-collection-"
)
_COLLECTION_HOME = Path(_COLLECTION_RUNTIME_TMP.name).resolve()
_COLLECTION_DATA_ROOT = _COLLECTION_HOME / ".openminion"
os.environ["OPENMINION_HOME"] = str(_COLLECTION_HOME)
os.environ["OPENMINION_DATA_ROOT"] = str(_COLLECTION_DATA_ROOT)
os.environ["OPENMINION_GENERATED_ROOT"] = str(_COLLECTION_DATA_ROOT / "runtime")


def pytest_sessionfinish() -> None:
    _COLLECTION_RUNTIME_TMP.cleanup()


@pytest.fixture(autouse=True)
def _force_isolated_test_roots(monkeypatch, tmp_path: Path) -> None:
    data_root = tmp_path / ".openminion"
    monkeypatch.setenv("OPENMINION_HOME", str(tmp_path))
    monkeypatch.setenv("OPENMINION_DATA_ROOT", str(data_root))
    monkeypatch.delenv("OPENMINION_GENERATED_ROOT", raising=False)
