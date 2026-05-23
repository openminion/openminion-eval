"""LRSP anti-LLM forbidden-field regression discipline.

LRSP extends the autonomy + binding chain as the 9th cross-roster
forbidden-field guard consumer (TGCR + APBR + MTRR + ASRR + AATR + SPRR
+ ALVB + GTGS + LRSP). All 9 rosters must remain tuple-equal — the
shared closed-set 8-name list is the canonical pinned shape:

    ("verdict", "reasoning", "narrative", "judgment",
     "description_text", "completion_summary", "summary_text", "notes")

LRSP's typed records (``LiveRuntimeProbe`` /
``LiveRuntimeProbeResult``) carry no prose-shaped fields. This module
encodes that as a structural assertion:

1. Construction with any forbidden prose-shaped attribute fails
   (frozen dataclass; the field doesn't exist).
2. The closed roster is tuple-equal to each of the 8 prior lanes'
   ``FORBIDDEN_FIELDS`` rosters.
3. The closed roster matches the canonical 8-name shape.
"""

from __future__ import annotations

from dataclasses import fields as dc_fields
from typing import Sequence

import pytest

from tests.eval.integration.lrsp_runner import (
    LiveRuntimeProbe,
    LiveRuntimeProbeResult,
    StructuralAssertionContract,
    TypedEventExpectation,
)

FORBIDDEN_FIELDS: Sequence[str] = (
    "verdict",
    "reasoning",
    "narrative",
    "judgment",
    "description_text",
    "completion_summary",
    "summary_text",
    "notes",
)


def _live_runtime_probe_field_names() -> set[str]:
    return {f.name for f in dc_fields(LiveRuntimeProbe)}


def _live_runtime_probe_result_field_names() -> set[str]:
    return {f.name for f in dc_fields(LiveRuntimeProbeResult)}


def test_forbidden_field_list_is_non_empty_and_unique() -> None:
    assert len(FORBIDDEN_FIELDS) > 0
    assert len(set(FORBIDDEN_FIELDS)) == len(FORBIDDEN_FIELDS)


def test_forbidden_field_list_matches_canonical_eight_name_roster() -> None:
    assert tuple(FORBIDDEN_FIELDS) == (
        "verdict",
        "reasoning",
        "narrative",
        "judgment",
        "description_text",
        "completion_summary",
        "summary_text",
        "notes",
    )


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_FIELDS)
def test_live_runtime_probe_does_not_carry_forbidden_prose_field(
    forbidden_field: str,
) -> None:
    assert forbidden_field not in _live_runtime_probe_field_names()


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_FIELDS)
def test_live_runtime_probe_result_does_not_carry_forbidden_prose_field(
    forbidden_field: str,
) -> None:
    assert forbidden_field not in _live_runtime_probe_result_field_names()


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_FIELDS)
def test_live_runtime_probe_rejects_construction_with_forbidden_field(
    forbidden_field: str,
) -> None:
    base_kwargs = {
        "probe_id": "lrsp-test",
        "probe_kind": "fresh_focus_session_turn",
        "contract": StructuralAssertionContract(
            expected_event_sequence=(
                TypedEventExpectation(event_type="run.queued"),
            ),
        ),
        forbidden_field: "any-prose-shaped-value",
    }
    with pytest.raises(TypeError):
        LiveRuntimeProbe(**base_kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("forbidden_field", FORBIDDEN_FIELDS)
def test_live_runtime_probe_result_rejects_construction_with_forbidden_field(
    forbidden_field: str,
) -> None:
    base_kwargs = {
        "probe_id": "lrsp-test",
        "probe_kind": "fresh_focus_session_turn",
        "outcome": "skipped_no_api_key",
        forbidden_field: "any-prose-shaped-value",
    }
    with pytest.raises(TypeError):
        LiveRuntimeProbeResult(**base_kwargs)  # type: ignore[arg-type]


def _load_forbidden_fields_roster(relative_path: str) -> tuple[str, ...]:
    """Load ``FORBIDDEN_FIELDS`` from an openminion test file by path.

    The openminion-eval and openminion checkouts both define a
    top-level ``tests`` package, so ``import tests.brain.*`` is
    ambiguous depending on sys.path order. Loading the upstream
    rosters via file path makes the cross-roster guard robust to
    monorepo layout.
    """

    import importlib.util
    from pathlib import Path

    framework_root = Path(__file__).resolve().parents[4]
    module_path = framework_root / "openminion" / relative_path
    spec = importlib.util.spec_from_file_location(
        f"_lrsp_cross_roster_{module_path.stem}",
        module_path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return tuple(getattr(module, "FORBIDDEN_FIELDS"))


def test_forbidden_field_roster_matches_nine_lane_cross_roster_guard() -> None:
    """LRSP joins TGCR/APBR/MTRR/ASRR/AATR/SPRR/ALVB/GTGS as the 9th lane.

    All 9 rosters must remain tuple-equal — the shared closed-set
    8-name list is the canonical pinned shape. Any drift here breaks
    the cross-roster guard and is a real regression signal.
    """

    tgcr = _load_forbidden_fields_roster("tests/brain/test_tgcr_forbidden_fields.py")
    apbr = _load_forbidden_fields_roster("tests/brain/test_apbr_forbidden_fields.py")
    mtrr = _load_forbidden_fields_roster("tests/brain/test_mtrr_forbidden_fields.py")
    asrr = _load_forbidden_fields_roster("tests/brain/test_asrr_forbidden_fields.py")
    aatr = _load_forbidden_fields_roster("tests/brain/test_aatr_forbidden_fields.py")
    sprr = _load_forbidden_fields_roster("tests/brain/test_sprr_forbidden_fields.py")
    alvb = _load_forbidden_fields_roster(
        "tests/services/runtime/test_alvb_forbidden_fields.py"
    )
    gtgs = _load_forbidden_fields_roster(
        "tests/services/gateway/test_gtgs_forbidden_fields.py"
    )

    assert tuple(FORBIDDEN_FIELDS) == tgcr
    assert tuple(FORBIDDEN_FIELDS) == apbr
    assert tuple(FORBIDDEN_FIELDS) == mtrr
    assert tuple(FORBIDDEN_FIELDS) == asrr
    assert tuple(FORBIDDEN_FIELDS) == aatr
    assert tuple(FORBIDDEN_FIELDS) == sprr
    assert tuple(FORBIDDEN_FIELDS) == alvb
    assert tuple(FORBIDDEN_FIELDS) == gtgs
