"""Canonical package paths for the standalone openminion-eval package."""

from __future__ import annotations

from pathlib import Path


def package_root() -> Path:
    return Path(__file__).resolve().parent


def skill_resources_root() -> Path:
    return package_root() / "skills" / "resources"


def skill_fixture_root(family_name: str) -> Path:
    return skill_resources_root() / family_name


__all__ = ["package_root", "skill_fixture_root", "skill_resources_root"]
