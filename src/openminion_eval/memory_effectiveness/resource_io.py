"""Internal JSON loading helpers for packaged memory-effectiveness resources."""

from __future__ import annotations

import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import Any, Mapping

from openminion_eval.family_support import require_mapping

JsonResource = str | Path | Traversable


def packaged_resource(package: str, name: str) -> Traversable:
    return resources.files(package).joinpath(name)


def load_json_mapping(source: JsonResource) -> Mapping[str, Any]:
    text, context = _read_text(source)
    return require_mapping(json.loads(text), context=context)


def _read_text(source: JsonResource) -> tuple[str, str]:
    if isinstance(source, (str, Path)):
        path = Path(source)
        return path.read_text(encoding="utf-8"), str(path)
    return source.read_text(encoding="utf-8"), str(source)
