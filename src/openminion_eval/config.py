"""Compatibility config surface for ``openminion_eval``."""

from __future__ import annotations

from dataclasses import dataclass
import os

_TRUE_ENV_VALUES = frozenset({"1", "true", "yes", "on"})


@dataclass(frozen=True)
class EvalConfig:
    """No-op config placeholder for the current public package surface."""


def load_config(*_args: object, **_kwargs: object) -> EvalConfig:
    return EvalConfig()


def env_flag_enabled(name: str) -> bool:
    """Return whether a package-owned boolean environment flag is enabled."""

    return os.environ.get(name, "").strip().lower() in _TRUE_ENV_VALUES


def env_value(name: str) -> str | None:
    """Return a non-empty package-owned environment value when configured."""

    value = os.environ.get(name)
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None
