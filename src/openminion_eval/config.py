"""Reserved compatibility config surface for ``openminion_eval``.

The standalone public package currently has no runtime-loaded configuration
contract. This module stays in place as a narrow compatibility seam for any
external code that may already import ``openminion_eval.config`` directly while
the package remains pre-1.0.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalConfig:
    """No-op config placeholder for the current public package surface."""


def load_config(*_args: object, **_kwargs: object) -> EvalConfig:
    """Return the current no-op package config.

    Arguments are accepted for compatibility only and are ignored because the
    standalone public eval package does not currently load runtime config.
    """

    return EvalConfig()
