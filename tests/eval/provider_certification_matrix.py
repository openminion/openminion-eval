from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from openminion_eval.family_support import utc_now_iso
from openminion_eval.reporting import (
    FamilyCertificationSignal,
    apply_family_signals_to_certification_cells,
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


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_matching_file(directory: Path, prefix: str) -> Path | None:
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{prefix}-*.json"))
    return matches[-1] if matches else None


def _skill_provider_index() -> tuple[dict[str, dict[str, Any]], str]:
    path = (
        runtime_root()
        / "skill-provider-matrix"
        / "20260411T222226Z-466325"
        / "summary.json"
    )
    payload = _load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("results", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def _nnse_summary_index() -> tuple[dict[str, dict[str, Any]], str]:
    path = runtime_root() / "nl-named-skill-representative-baseline" / "summary.json"
    payload = _load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("targets", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def _quality_summary_index(target_set: str) -> tuple[dict[str, dict[str, Any]], str]:
    path = runtime_root() / f"skill-quality-{target_set}-baseline" / "summary.json"
    payload = _load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("targets", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def _latest_dense_routing_artifact(target_id: str) -> Path | None:
    for directory_name in (
        "skill-complex-official-matrix",
        "skill-complex-provider-reruns",
    ):
        candidate = _latest_matching_file(runtime_root() / directory_name, target_id)
        if candidate is not None:
            return candidate
    return None


def _manual_index(
    manual_cells: tuple[ProviderCertificationManualCell, ...],
) -> dict[tuple[str, str], ProviderCertificationManualCell]:
    return {(cell.target_id, cell.dimension): cell for cell in manual_cells}


def _cell(
    *, status: str, evidence_paths: list[str], notes: list[str]
) -> ProviderCertificationCell:
    return ProviderCertificationCell(
        status=status,
        evidence_paths=tuple(dict.fromkeys(path for path in evidence_paths if path)),
        notes=tuple(note for note in notes if note),
    )


def _derive_access_cell(
    *,
    target: ProviderCertificationTarget,
    skill_provider_index: dict[str, dict[str, Any]],
    skill_provider_summary_path: str,
    manual_index: dict[tuple[str, str], ProviderCertificationManualCell],
) -> ProviderCertificationCell:
    evidence_paths: list[str] = []
    notes: list[str] = []
    if target.target_id in skill_provider_index:
        result = skill_provider_index[target.target_id]
        if str(result.get("status", "")).strip() == "pass":
            evidence_paths.append(skill_provider_summary_path)
            notes.append("live skill-support smoke passed")
            return _cell(status="ready", evidence_paths=evidence_paths, notes=notes)
    explicit_tool_manual = manual_index.get((target.target_id, "explicit_tool"))
    if explicit_tool_manual is not None:
        evidence_paths.append(explicit_tool_manual.evidence_path)
        notes.append("access implied by explicit-tool live proof")
        return _cell(status="ready", evidence_paths=evidence_paths, notes=notes)
    return _cell(status="untested", evidence_paths=evidence_paths, notes=notes)


def _derive_manual_or_untested_cell(
    *,
    target_id: str,
    dimension: str,
    manual_index: dict[tuple[str, str], ProviderCertificationManualCell],
) -> ProviderCertificationCell:
    manual = manual_index.get((target_id, dimension))
    if manual is None:
        return _cell(status="untested", evidence_paths=[], notes=[])
    return _cell(
        status=manual.status,
        evidence_paths=[manual.evidence_path],
        notes=[manual.note],
    )


def _derive_skill_routing_cell_with_manual(
    *,
    target_id: str,
    manual_index: dict[tuple[str, str], ProviderCertificationManualCell],
) -> ProviderCertificationCell:
    manual = manual_index.get((target_id, "skill_routing"))
    if manual is not None:
        return _cell(
            status=manual.status,
            evidence_paths=[manual.evidence_path],
            notes=[manual.note],
        )
    artifact_path = _latest_dense_routing_artifact(target_id)
    if artifact_path is None:
        return _cell(status="untested", evidence_paths=[], notes=[])
    payload = _load_json(artifact_path)
    results = payload.get("results", [])
    all_pass = bool(results) and all(
        str(item.get("result", "")).strip() == "pass"
        for item in results
        if isinstance(item, dict)
    )
    return _cell(
        status="green" if all_pass else "gapped",
        evidence_paths=[str(artifact_path)],
        notes=["dense skill routing artifact"],
    )


def _derive_nl_named_skill_cell(
    *,
    target_id: str,
    nnse_index: dict[str, dict[str, Any]],
    nnse_summary_path: str,
) -> ProviderCertificationCell:
    target_summary = nnse_index.get(target_id)
    if target_summary is None:
        return _cell(status="untested", evidence_paths=[], notes=[])
    attempt_count = int(target_summary.get("attempt_count", 0))
    accuracy_count = int(target_summary.get("selection_accuracy_count", 0))
    wrong_skill_count = int(target_summary.get("wrong_skill_count", 0))
    empty_fallback_count = int(target_summary.get("empty_fallback_count", 0))
    if attempt_count and accuracy_count == attempt_count and wrong_skill_count == 0:
        status = "green"
    elif accuracy_count == 0:
        status = "blocked"
    else:
        status = "gapped"
    notes = [
        f"accuracy={accuracy_count}/{attempt_count}",
        f"empty_fallback={empty_fallback_count}",
        f"wrong_skill={wrong_skill_count}",
    ]
    return _cell(
        status=status,
        evidence_paths=[nnse_summary_path, str(target_summary.get("report_path", ""))],
        notes=notes,
    )


def _classify_output_quality(summary: dict[str, Any]) -> str:
    scenario_count = int(summary.get("scenario_count", 0) or 0)
    if scenario_count <= 0:
        return "untested"
    ratios = [
        int(summary.get("responses_with_numbered_steps", 0) or 0) / scenario_count,
        int(summary.get("responses_with_verification_language", 0) or 0)
        / scenario_count,
        int(summary.get("responses_with_guardrail_language", 0) or 0) / scenario_count,
    ]
    min_ratio = min(ratios)
    if min_ratio >= 0.7:
        return "strong"
    if min_ratio >= 0.5:
        return "adequate"
    return "weak"


def _derive_output_quality_cell(
    *,
    target_id: str,
    official_quality_index: dict[str, dict[str, Any]],
    official_quality_summary_path: str,
    representative_quality_index: dict[str, dict[str, Any]],
    representative_quality_summary_path: str,
) -> ProviderCertificationCell:
    target_summary = official_quality_index.get(target_id)
    summary_path = official_quality_summary_path
    if target_summary is None:
        target_summary = representative_quality_index.get(target_id)
        summary_path = representative_quality_summary_path
    if target_summary is None:
        return _cell(status="untested", evidence_paths=[], notes=[])
    report_path = str(target_summary.get("report_path", "") or "")
    report_payload = _load_json(Path(report_path))
    quality_status = _classify_output_quality(report_payload.get("summary", {}))
    notes = [
        "numbered/verif/guardrail="
        f"{report_payload['summary']['responses_with_numbered_steps']}/"
        f"{report_payload['summary']['responses_with_verification_language']}/"
        f"{report_payload['summary']['responses_with_guardrail_language']}"
    ]
    return _cell(
        status=quality_status,
        evidence_paths=[summary_path, report_path],
        notes=notes,
    )


def _apply_family_signals(
    *,
    cell: ProviderCertificationCell,
    family_signals: Iterable[FamilyCertificationSignal],
    target_id: str,
    dimension: str,
) -> ProviderCertificationCell:
    status, evidence_paths, notes = apply_family_signals_to_certification_cells(
        base_status=cell.status,
        base_evidence_paths=cell.evidence_paths,
        base_notes=cell.notes,
        signals=family_signals,
        target_id=target_id,
        dimension=dimension,
    )
    return ProviderCertificationCell(
        status=status, evidence_paths=evidence_paths, notes=notes
    )


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
        access = _derive_access_cell(
            target=target,
            skill_provider_index=skill_provider_index,
            skill_provider_summary_path=skill_provider_summary_path,
            manual_index=manual_idx,
        )
        explicit_tool = _derive_manual_or_untested_cell(
            target_id=target.target_id,
            dimension="explicit_tool",
            manual_index=manual_idx,
        )
        nl_tool_parity = _derive_manual_or_untested_cell(
            target_id=target.target_id,
            dimension="nl_tool_parity",
            manual_index=manual_idx,
        )
        skill_routing = _derive_skill_routing_cell_with_manual(
            target_id=target.target_id,
            manual_index=manual_idx,
        )
        nl_named_skill = _derive_nl_named_skill_cell(
            target_id=target.target_id,
            nnse_index=nnse_index,
            nnse_summary_path=nnse_summary_path,
        )
        output_quality = _derive_output_quality_cell(
            target_id=target.target_id,
            official_quality_index=official_quality_index,
            official_quality_summary_path=official_quality_summary_path,
            representative_quality_index=representative_quality_index,
            representative_quality_summary_path=representative_quality_summary_path,
        )
        confirmation_policy = _derive_manual_or_untested_cell(
            target_id=target.target_id,
            dimension="confirmation_policy",
            manual_index=manual_idx,
        )
        rows.append(
            ProviderCertificationRow(
                target_id=target.target_id,
                provider_family=target.provider_family,
                provider_lane=target.provider_lane,
                model_label=target.model_label,
                access=_apply_family_signals(
                    cell=access,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="access",
                ),
                explicit_tool=_apply_family_signals(
                    cell=explicit_tool,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="explicit_tool",
                ),
                nl_tool_parity=_apply_family_signals(
                    cell=nl_tool_parity,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="nl_tool_parity",
                ),
                skill_routing=_apply_family_signals(
                    cell=skill_routing,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="skill_routing",
                ),
                nl_named_skill=_apply_family_signals(
                    cell=nl_named_skill,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="nl_named_skill",
                ),
                output_quality=_apply_family_signals(
                    cell=output_quality,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="output_quality",
                ),
                confirmation_policy=_apply_family_signals(
                    cell=confirmation_policy,
                    family_signals=family_signals,
                    target_id=target.target_id,
                    dimension="confirmation_policy",
                ),
            )
        )

    def _count_status(dimension: str, status: str) -> int:
        return sum(1 for row in rows if getattr(row, dimension).status == status)

    summary = {
        "target_count": len(rows),
        "dimension_counts": {
            dimension: {
                status: _count_status(dimension, status)
                for status in (
                    "ready",
                    "blocked",
                    "untested",
                    "green",
                    "gapped",
                    "strong",
                    "adequate",
                    "weak",
                )
                if _count_status(dimension, status) > 0
            }
            for dimension in (
                "access",
                "explicit_tool",
                "nl_tool_parity",
                "skill_routing",
                "nl_named_skill",
                "output_quality",
                "confirmation_policy",
            )
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
