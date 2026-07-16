from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from collections.abc import Iterable

from openminion_eval.reporting import (
    FamilyCertificationSignal,
    apply_family_signals_to_certification_cells,
)


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def latest_matching_file(directory: Path, prefix: str) -> Path | None:
    if not directory.exists():
        return None
    matches = sorted(directory.glob(f"{prefix}-*.json"))
    return matches[-1] if matches else None


def skill_provider_index(runtime_root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = (
        runtime_root
        / "skill-provider-matrix"
        / "20260411T222226Z-466325"
        / "summary.json"
    )
    payload = load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("results", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def nnse_summary_index(runtime_root: Path) -> tuple[dict[str, dict[str, Any]], str]:
    path = runtime_root / "nl-named-skill-representative-baseline" / "summary.json"
    payload = load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("targets", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def quality_summary_index(
    runtime_root: Path, target_set: str
) -> tuple[dict[str, dict[str, Any]], str]:
    path = runtime_root / f"skill-quality-{target_set}-baseline" / "summary.json"
    payload = load_json(path)
    index = {
        str(item.get("target_id", "") or "").strip(): item
        for item in payload.get("targets", [])
        if str(item.get("target_id", "") or "").strip()
    }
    return index, str(path)


def latest_dense_routing_artifact(runtime_root: Path, target_id: str) -> Path | None:
    for directory_name in (
        "skill-complex-official-matrix",
        "skill-complex-provider-reruns",
    ):
        candidate = latest_matching_file(runtime_root / directory_name, target_id)
        if candidate is not None:
            return candidate
    return None


def manual_index(manual_cells: tuple[Any, ...]) -> dict[tuple[str, str], Any]:
    return {(cell.target_id, cell.dimension): cell for cell in manual_cells}


def cell_parts(
    *, status: str, evidence_paths: Iterable[str], notes: Iterable[str]
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    return (
        status,
        tuple(dict.fromkeys(path for path in evidence_paths if path)),
        tuple(note for note in notes if note),
    )


def derive_access_cell_parts(
    *,
    target: Any,
    skill_provider_index: dict[str, dict[str, Any]],
    skill_provider_summary_path: str,
    manual_index: dict[tuple[str, str], Any],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    evidence_paths: list[str] = []
    notes: list[str] = []
    if target.target_id in skill_provider_index:
        result = skill_provider_index[target.target_id]
        if str(result.get("status", "")).strip() == "pass":
            evidence_paths.append(skill_provider_summary_path)
            notes.append("live skill-support smoke passed")
            return cell_parts(
                status="ready", evidence_paths=evidence_paths, notes=notes
            )
    explicit_tool_manual = manual_index.get((target.target_id, "explicit_tool"))
    if explicit_tool_manual is not None:
        evidence_paths.append(explicit_tool_manual.evidence_path)
        notes.append("access implied by explicit-tool live proof")
        return cell_parts(status="ready", evidence_paths=evidence_paths, notes=notes)
    return cell_parts(status="untested", evidence_paths=evidence_paths, notes=notes)


def derive_manual_or_untested_cell_parts(
    *,
    target_id: str,
    dimension: str,
    manual_index: dict[tuple[str, str], Any],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    manual = manual_index.get((target_id, dimension))
    if manual is None:
        return cell_parts(status="untested", evidence_paths=(), notes=())
    return cell_parts(
        status=manual.status,
        evidence_paths=(manual.evidence_path,),
        notes=(manual.note,),
    )


def derive_skill_routing_cell_parts(
    *,
    target_id: str,
    manual_index: dict[tuple[str, str], Any],
    latest_dense_routing_artifact: Path | None,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    manual = manual_index.get((target_id, "skill_routing"))
    if manual is not None:
        return cell_parts(
            status=manual.status,
            evidence_paths=(manual.evidence_path,),
            notes=(manual.note,),
        )
    if latest_dense_routing_artifact is None:
        return cell_parts(status="untested", evidence_paths=(), notes=())
    payload = load_json(latest_dense_routing_artifact)
    results = payload.get("results", [])
    all_pass = bool(results) and all(
        str(item.get("result", "")).strip() == "pass"
        for item in results
        if isinstance(item, dict)
    )
    return cell_parts(
        status="green" if all_pass else "gapped",
        evidence_paths=(str(latest_dense_routing_artifact),),
        notes=("dense skill routing artifact",),
    )


def derive_nl_named_skill_cell_parts(
    *,
    target_id: str,
    nnse_index: dict[str, dict[str, Any]],
    nnse_summary_path: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    target_summary = nnse_index.get(target_id)
    if target_summary is None:
        return cell_parts(status="untested", evidence_paths=(), notes=())
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
    return cell_parts(
        status=status,
        evidence_paths=(
            nnse_summary_path,
            str(target_summary.get("report_path", "")),
        ),
        notes=(
            f"accuracy={accuracy_count}/{attempt_count}",
            f"empty_fallback={empty_fallback_count}",
            f"wrong_skill={wrong_skill_count}",
        ),
    )


def classify_output_quality(summary: dict[str, Any]) -> str:
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


def derive_output_quality_cell_parts(
    *,
    target_id: str,
    official_quality_index: dict[str, dict[str, Any]],
    official_quality_summary_path: str,
    representative_quality_index: dict[str, dict[str, Any]],
    representative_quality_summary_path: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    target_summary = official_quality_index.get(target_id)
    summary_path = official_quality_summary_path
    if target_summary is None:
        target_summary = representative_quality_index.get(target_id)
        summary_path = representative_quality_summary_path
    if target_summary is None:
        return cell_parts(status="untested", evidence_paths=(), notes=())
    report_path = str(target_summary.get("report_path", "") or "")
    report_payload = load_json(Path(report_path))
    summary = report_payload.get("summary", {})
    return cell_parts(
        status=classify_output_quality(summary),
        evidence_paths=(summary_path, report_path),
        notes=(
            "numbered/verif/guardrail="
            f"{summary['responses_with_numbered_steps']}/"
            f"{summary['responses_with_verification_language']}/"
            f"{summary['responses_with_guardrail_language']}",
        ),
    )


def build_row_cell_parts(
    *,
    target: Any,
    manual_index: dict[tuple[str, str], Any],
    skill_provider_index: dict[str, dict[str, Any]],
    skill_provider_summary_path: str,
    latest_dense_routing_artifact: Path | None,
    nnse_index: dict[str, dict[str, Any]],
    nnse_summary_path: str,
    official_quality_index: dict[str, dict[str, Any]],
    official_quality_summary_path: str,
    representative_quality_index: dict[str, dict[str, Any]],
    representative_quality_summary_path: str,
) -> dict[str, tuple[str, tuple[str, ...], tuple[str, ...]]]:
    target_id = target.target_id
    return {
        "access": derive_access_cell_parts(
            target=target,
            skill_provider_index=skill_provider_index,
            skill_provider_summary_path=skill_provider_summary_path,
            manual_index=manual_index,
        ),
        "explicit_tool": derive_manual_or_untested_cell_parts(
            target_id=target_id,
            dimension="explicit_tool",
            manual_index=manual_index,
        ),
        "nl_tool_parity": derive_manual_or_untested_cell_parts(
            target_id=target_id,
            dimension="nl_tool_parity",
            manual_index=manual_index,
        ),
        "skill_routing": derive_skill_routing_cell_parts(
            target_id=target_id,
            manual_index=manual_index,
            latest_dense_routing_artifact=latest_dense_routing_artifact,
        ),
        "nl_named_skill": derive_nl_named_skill_cell_parts(
            target_id=target_id,
            nnse_index=nnse_index,
            nnse_summary_path=nnse_summary_path,
        ),
        "output_quality": derive_output_quality_cell_parts(
            target_id=target_id,
            official_quality_index=official_quality_index,
            official_quality_summary_path=official_quality_summary_path,
            representative_quality_index=representative_quality_index,
            representative_quality_summary_path=representative_quality_summary_path,
        ),
        "confirmation_policy": derive_manual_or_untested_cell_parts(
            target_id=target_id,
            dimension="confirmation_policy",
            manual_index=manual_index,
        ),
    }


def apply_family_signals_to_cell_parts(
    *,
    cell_parts_value: tuple[str, tuple[str, ...], tuple[str, ...]],
    family_signals: Iterable[FamilyCertificationSignal],
    target_id: str,
    dimension: str,
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    status, evidence_paths, notes = cell_parts_value
    return apply_family_signals_to_certification_cells(
        base_status=status,
        base_evidence_paths=evidence_paths,
        base_notes=notes,
        signals=family_signals,
        target_id=target_id,
        dimension=dimension,
    )
