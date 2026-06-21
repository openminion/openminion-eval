from __future__ import annotations

import pytest

from openminion_eval import get_builtin_family, list_builtin_families


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
    }
    for family in families:
        assert family.fixture_name
        assert family.observation_schema
        assert family.report_writer
        assert family.capabilities


def test_builtin_family_lookup_is_explicit() -> None:
    assert get_builtin_family("routing").report_writer == "build_routing_report"

    with pytest.raises(KeyError, match="unknown eval family"):
        get_builtin_family("provider_dynamic_plugin")
