from __future__ import annotations

import pytest

from openminion_eval import (
    FAMILY_REGISTRY_VERSION,
    get_builtin_family,
    list_builtin_families,
)


def test_builtin_family_registry_has_complete_static_metadata() -> None:
    families = list_builtin_families()

    assert {family.family_id for family in families} >= {
        "tool_selection",
        "tool_result_usage",
        "freshness",
        "routing",
        "closure",
        "policy",
        "skills",
        "runtime_reliability",
        "goal_trajectory",
        "memory_effectiveness",
        "memory_context",
        "delegated_memory",
    }
    for family in families:
        assert family.observation_schema
        assert family.report_writer
        assert family.capabilities


def test_builtin_family_lookup_is_explicit() -> None:
    assert FAMILY_REGISTRY_VERSION == "2"
    assert get_builtin_family("routing").report_writer == "build_routing_report"
    assert get_builtin_family("runtime_reliability").capabilities == (
        "project_lifecycle",
        "dependency_readiness",
        "invocation_lifecycle",
        "remote_transport",
        "infrastructure_monitoring",
    )

    with pytest.raises(KeyError, match="unknown eval family"):
        get_builtin_family("provider_dynamic_plugin")
