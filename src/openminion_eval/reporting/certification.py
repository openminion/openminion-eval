"""Additive cross-family certification helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class FamilyCertificationSignal:
    target_id: str
    dimension: str
    status: str
    evidence_path: str
    note: str = ""


def apply_family_signals_to_certification_cells(
    *,
    base_status: str,
    base_evidence_paths: tuple[str, ...],
    base_notes: tuple[str, ...],
    signals: Iterable[FamilyCertificationSignal],
    target_id: str,
    dimension: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    matching = [
        signal
        for signal in signals
        if signal.target_id == target_id and signal.dimension == dimension
    ]
    if not matching:
        return base_status, base_evidence_paths, base_notes
    merged_status = matching[-1].status or base_status
    merged_paths = tuple(
        dict.fromkeys(
            base_evidence_paths
            + tuple(signal.evidence_path for signal in matching if signal.evidence_path)
        )
    )
    merged_notes = tuple(
        note
        for note in dict.fromkeys(
            base_notes + tuple(signal.note for signal in matching if signal.note)
        )
    )
    return merged_status, merged_paths, merged_notes
