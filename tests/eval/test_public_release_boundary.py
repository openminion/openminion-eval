from __future__ import annotations

import importlib

import pytest


def test_memory_harness_is_not_shipped_in_public_package() -> None:
    with pytest.raises(ModuleNotFoundError) as excinfo:
        importlib.import_module("openminion_eval.memory_eval")

    assert excinfo.value.name == "openminion_eval.memory_eval"
