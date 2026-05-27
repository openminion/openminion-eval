from __future__ import annotations

import pytest

from openminion_eval.reporting import (
    FamilyCertificationSignal,
    apply_family_signals_to_certification_cells,
)


def test_family_certification_signals_reject_unordered_inputs() -> None:
    signal = FamilyCertificationSignal(
        target_id="target",
        dimension="dimension",
        status="green",
        evidence_path="evidence.json",
    )

    with pytest.raises(TypeError):
        apply_family_signals_to_certification_cells(
            base_status="untested",
            base_evidence_paths=(),
            base_notes=(),
            signals=frozenset({signal}),
            target_id="target",
            dimension="dimension",
        )


def test_family_certification_signals_preserve_sequence_order() -> None:
    signals = [
        FamilyCertificationSignal(
            target_id="target",
            dimension="dimension",
            status="yellow",
            evidence_path="first.json",
            note="first",
        ),
        FamilyCertificationSignal(
            target_id="target",
            dimension="dimension",
            status="green",
            evidence_path="second.json",
            note="second",
        ),
    ]

    status, paths, notes = apply_family_signals_to_certification_cells(
        base_status="untested",
        base_evidence_paths=(),
        base_notes=(),
        signals=signals,
        target_id="target",
        dimension="dimension",
    )

    assert status == "green"
    assert paths == ("first.json", "second.json")
    assert notes == ("first", "second")
