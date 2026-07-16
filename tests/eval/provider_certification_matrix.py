from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from openminion_eval.family_support import utc_now_iso
from openminion_eval.reporting import FamilyCertificationSignal
from tests.eval.provider_certification_support import (
    apply_family_signals_to_cell_parts as _apply_family_signals_to_cell_parts,
    build_row_cell_parts as _build_row_cell_parts,
    latest_dense_routing_artifact as _latest_dense_routing_artifact_for_root,
    manual_index as _manual_index,
    nnse_summary_index as _nnse_summary_index_for_root,
    quality_summary_index as _quality_summary_index_for_root,
    skill_provider_index as _skill_provider_index_for_root,
)


@dataclass(frozen=True)
class ProviderCertificationTarget:
    target_id: str
    provider_family: str
    provider_lane: str
    model_label: str


@dataclass(frozen=True)
class ProviderCertificationManualCell:
    target_id: str
    dimension: str
    status: str
    evidence_path: str
    note: str


@dataclass(frozen=True)
class ProviderCertificationCell:
    status: str
    evidence_paths: tuple[str, ...]
    notes: tuple[str, ...]


@dataclass(frozen=True)
class ProviderCertificationRow:
    target_id: str
    provider_family: str
    provider_lane: str
    model_label: str
    access: ProviderCertificationCell
    explicit_tool: ProviderCertificationCell
    nl_tool_parity: ProviderCertificationCell
    skill_routing: ProviderCertificationCell
    nl_named_skill: ProviderCertificationCell
    output_quality: ProviderCertificationCell
    confirmation_policy: ProviderCertificationCell


@dataclass(frozen=True)
class ProviderCertificationReport:
    report_version: str
    generated_at: str
    inventory_version: str
    manual_evidence_version: str
    rows: tuple[ProviderCertificationRow, ...]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


ADJACENT_EVAL_DISPOSITION = "cross_family_composite_report"
_DIMENSIONS = (
    "access",
    "explicit_tool",
    "nl_tool_parity",
    "skill_routing",
    "nl_named_skill",
    "output_quality",
    "confirmation_policy",
)
_STATUSES = (
    "ready",
    "blocked",
    "untested",
    "green",
    "gapped",
    "strong",
    "adequate",
    "weak",
)


def openminion_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve_package_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return openminion_root() / path


def framework_root() -> Path:
    return openminion_root().parent


def runtime_root() -> Path:
    return framework_root() / ".openminion" / "runtime"


def default_provider_certification_fixture_root() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "provider_certification"


def default_provider_inventory_path() -> Path:
    return default_provider_certification_fixture_root() / "targets.json"


def default_provider_manual_evidence_path() -> Path:
    return default_provider_certification_fixture_root() / "manual_evidence.json"


def load_provider_certification_targets(
    path: str | Path | None = None,
) -> tuple[str, tuple[ProviderCertificationTarget, ...]]:
    inventory_path = (
        Path(path) if path is not None else default_provider_inventory_path()
    )
    payload = json.loads(inventory_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(
            f"unsupported provider certification inventory version: {version!r}"
        )
    targets: list[ProviderCertificationTarget] = []
    seen_ids: set[str] = set()
    for item in payload.get("targets", []):
        target_id = str(item.get("target_id", "") or "").strip()
        if not target_id or target_id in seen_ids:
            raise ValueError(f"invalid or duplicate target_id: {target_id!r}")
        seen_ids.add(target_id)
        targets.append(
            ProviderCertificationTarget(
                target_id=target_id,
                provider_family=str(item.get("provider_family", "") or "").strip(),
                provider_lane=str(item.get("provider_lane", "") or "").strip(),
                model_label=str(item.get("model_label", "") or "").strip(),
            )
        )
    return version, tuple(targets)


def load_provider_certification_manual_cells(
    path: str | Path | None = None,
) -> tuple[str, tuple[ProviderCertificationManualCell, ...]]:
    evidence_path = (
        Path(path) if path is not None else default_provider_manual_evidence_path()
    )
    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != "1":
        raise ValueError(
            f"unsupported provider certification manual evidence version: {version!r}"
        )
    cells: list[ProviderCertificationManualCell] = []
    seen_keys: set[tuple[str, str]] = set()
    for item in payload.get("cells", []):
        target_id = str(item.get("target_id", "") or "").strip()
        dimension = str(item.get("dimension", "") or "").strip()
        key = (target_id, dimension)
        if not target_id or not dimension or key in seen_keys:
            raise ValueError(f"invalid or duplicate manual cell: {key!r}")
        seen_keys.add(key)
        evidence_path_text = str(item.get("evidence_path", "") or "").strip()
        if not evidence_path_text:
            raise ValueError(f"manual cell missing evidence_path: {key!r}")
        if not _resolve_package_path(evidence_path_text).exists():
            raise ValueError(
                f"manual evidence path does not exist for {key!r}: {evidence_path_text}"
            )
        cells.append(
            ProviderCertificationManualCell(
                target_id=target_id,
                dimension=dimension,
                status=str(item.get("status", "") or "").strip(),
                evidence_path=evidence_path_text,
                note=str(item.get("note", "") or "").strip(),
            )
        )
    return version, tuple(cells)


def _skill_provider_index() -> tuple[dict[str, dict[str, Any]], str]:
    return _skill_provider_index_for_root(runtime_root())


def _nnse_summary_index() -> tuple[dict[str, dict[str, Any]], str]:
    return _nnse_summary_index_for_root(runtime_root())


def _quality_summary_index(target_set: str) -> tuple[dict[str, dict[str, Any]], str]:
    return _quality_summary_index_for_root(runtime_root(), target_set)


def _latest_dense_routing_artifact(target_id: str) -> Path | None:
    return _latest_dense_routing_artifact_for_root(runtime_root(), target_id)


def _build_cell(
    *,
    cell_parts_value: tuple[str, tuple[str, ...], tuple[str, ...]],
    family_signals: Iterable[FamilyCertificationSignal],
    target_id: str,
    dimension: str,
) -> ProviderCertificationCell:
    status, evidence_paths, notes = _apply_family_signals_to_cell_parts(
        cell_parts_value=cell_parts_value,
        family_signals=family_signals,
        target_id=target_id,
        dimension=dimension,
    )
    return ProviderCertificationCell(status, evidence_paths, notes)


def _count_status(
    rows: list[ProviderCertificationRow], dimension: str, status: str
) -> int:
    return sum(1 for row in rows if getattr(row, dimension).status == status)


def build_provider_certification_report(
    *,
    inventory_version: str,
    targets: tuple[ProviderCertificationTarget, ...],
    manual_evidence_version: str,
    manual_cells: tuple[ProviderCertificationManualCell, ...],
    family_signals: Iterable[FamilyCertificationSignal] = (),
) -> ProviderCertificationReport:
    manual_idx = _manual_index(manual_cells)
    skill_provider_index, skill_provider_summary_path = _skill_provider_index()
    nnse_index, nnse_summary_path = _nnse_summary_index()
    official_quality_index, official_quality_summary_path = _quality_summary_index(
        "official"
    )
    representative_quality_index, representative_quality_summary_path = (
        _quality_summary_index("representative")
    )

    rows: list[ProviderCertificationRow] = []
    for target in targets:
        raw_cells = _build_row_cell_parts(
            target=target,
            manual_index=manual_idx,
            skill_provider_index=skill_provider_index,
            skill_provider_summary_path=skill_provider_summary_path,
            latest_dense_routing_artifact=_latest_dense_routing_artifact(
                target.target_id
            ),
            nnse_index=nnse_index,
            nnse_summary_path=nnse_summary_path,
            official_quality_index=official_quality_index,
            official_quality_summary_path=official_quality_summary_path,
            representative_quality_index=representative_quality_index,
            representative_quality_summary_path=representative_quality_summary_path,
        )
        cells = {
            dimension: _build_cell(
                cell_parts_value=raw_cells[dimension],
                family_signals=family_signals,
                target_id=target.target_id,
                dimension=dimension,
            )
            for dimension in _DIMENSIONS
        }
        rows.append(
            ProviderCertificationRow(
                target_id=target.target_id,
                provider_family=target.provider_family,
                provider_lane=target.provider_lane,
                model_label=target.model_label,
                access=cells["access"],
                explicit_tool=cells["explicit_tool"],
                nl_tool_parity=cells["nl_tool_parity"],
                skill_routing=cells["skill_routing"],
                nl_named_skill=cells["nl_named_skill"],
                output_quality=cells["output_quality"],
                confirmation_policy=cells["confirmation_policy"],
            )
        )

    summary = {
        "target_count": len(rows),
        "dimension_counts": {
            dimension: {
                status: _count_status(rows, dimension, status)
                for status in _STATUSES
                if _count_status(rows, dimension, status) > 0
            }
            for dimension in _DIMENSIONS
        },
    }

    return ProviderCertificationReport(
        report_version="1",
        generated_at=utc_now_iso(),
        inventory_version=inventory_version,
        manual_evidence_version=manual_evidence_version,
        rows=tuple(rows),
        summary=summary,
    )


def write_provider_certification_report(
    path: str | Path, report: ProviderCertificationReport
) -> Path:
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


__all__ = [
    "ADJACENT_EVAL_DISPOSITION",
    "ProviderCertificationCell",
    "ProviderCertificationManualCell",
    "ProviderCertificationReport",
    "ProviderCertificationRow",
    "ProviderCertificationTarget",
    "build_provider_certification_report",
    "default_provider_certification_fixture_root",
    "default_provider_inventory_path",
    "default_provider_manual_evidence_path",
    "framework_root",
    "load_provider_certification_manual_cells",
    "load_provider_certification_targets",
    "runtime_root",
    "write_provider_certification_report",
]
