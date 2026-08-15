"""Shared JSON payload parsing for memory-effectiveness artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def json_objects(items: list | tuple, label: str) -> tuple[dict[str, Any], ...]:
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"{label} item {index} must be an object")
        objects.append(item)
    return tuple(objects)


def string_tuple(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = data.get(key, ())
    return strings_from_value(values, key)


def strings_from_value(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, list | tuple):
        raise TypeError(f"{label} must be a list")
    return tuple(str(value) for value in values)
