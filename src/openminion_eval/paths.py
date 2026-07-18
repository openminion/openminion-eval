"""Canonical package paths for the standalone openminion-eval package."""

from __future__ import annotations

from pathlib import Path

from openminion_eval.config import env_value
from openminion_eval.constants import OPENMINION_EVAL_GENERATED_ROOT_ENV


def package_root() -> Path:
    return Path(__file__).resolve().parent


def generated_root() -> Path:
    configured = env_value(OPENMINION_EVAL_GENERATED_ROOT_ENV)
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.cwd().resolve() / ".openminion-eval" / "generated"


def skill_resources_root() -> Path:
    return package_root() / "skills" / "resources"


def skill_fixture_root(family_name: str) -> Path:
    return skill_resources_root() / family_name


__all__ = [
    "generated_root",
    "package_root",
    "skill_fixture_root",
    "skill_resources_root",
]
