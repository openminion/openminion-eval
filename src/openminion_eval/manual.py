"""Local JSON manual grading artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from openminion_eval.cases import EvalCase, EvalCaseResult, GradeMode, GradeOutcome

MANUAL_REVIEW_ARTIFACT_VERSION = "1"
MANUAL_REVIEW_QUEUE_KIND = "manual-review-queue"
MANUAL_RESULTS_KIND = "manual-results"


@dataclass(frozen=True)
class ManualReviewItem:
    case_id: str
    category: str
    prompt: str
    description: str
    tags: tuple[str, ...]


@dataclass(frozen=True)
class ManualReviewQueue:
    artifact_version: str
    items: tuple[ManualReviewItem, ...]

    def to_dict(self) -> dict[str, Any]:
        return {"artifact_kind": MANUAL_REVIEW_QUEUE_KIND, **asdict(self)}


@dataclass(frozen=True)
class ManualAdjudication:
    case_id: str
    outcome: GradeOutcome
    detail: str = ""


def build_manual_review_queue(cases: Sequence[EvalCase]) -> ManualReviewQueue:
    items = tuple(
        ManualReviewItem(
            case_id=case.case_id,
            category=case.category,
            prompt=case.prompt,
            description=case.description,
            tags=tuple(case.tags),
        )
        for case in cases
        if case.grade_mode is GradeMode.MANUAL
    )
    return ManualReviewQueue(
        artifact_version=MANUAL_REVIEW_ARTIFACT_VERSION,
        items=items,
    )


def write_manual_review_queue(path: str | Path, queue: ManualReviewQueue) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(queue.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def load_manual_review_queue(path: str | Path) -> ManualReviewQueue:
    payload = _load_manual_object(path)
    _ensure_manual_version(payload)
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("manual review queue requires an items list")
    parsed: list[ManualReviewItem] = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("manual review queue items must be mappings")
        tags = item.get("tags", [])
        if not isinstance(tags, list | tuple) or not all(
            isinstance(tag, str) for tag in tags
        ):
            raise ValueError("manual review queue tags must be strings")
        parsed.append(
            ManualReviewItem(
                case_id=_required_manual_string(item, "case_id"),
                category=_required_manual_string(item, "category"),
                prompt=_required_manual_string(item, "prompt"),
                description=str(item.get("description", "")),
                tags=tuple(tags),
            )
        )
    return ManualReviewQueue(
        artifact_version=MANUAL_REVIEW_ARTIFACT_VERSION,
        items=tuple(parsed),
    )


def load_manual_adjudications(path: str | Path) -> tuple[ManualAdjudication, ...]:
    payload = _load_manual_object(path)
    _ensure_manual_version(payload)
    items = payload.get("adjudications")
    if not isinstance(items, list):
        raise ValueError("manual adjudication artifact requires an adjudications list")
    return tuple(_adjudication_from_dict(item) for item in items)


def load_manual_results(path: str | Path) -> tuple[EvalCaseResult, ...]:
    payload = _load_manual_object(path)
    _ensure_manual_version(payload)
    items = payload.get("results")
    if not isinstance(items, list):
        raise ValueError("manual results artifact requires a results list")
    return tuple(_result_from_dict(item) for item in items)


def write_manual_results(
    path: str | Path,
    results: Sequence[EvalCaseResult],
) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_kind": MANUAL_RESULTS_KIND,
        "artifact_version": MANUAL_REVIEW_ARTIFACT_VERSION,
        "summary": {
            outcome.value: sum(1 for result in results if result.outcome is outcome)
            for outcome in GradeOutcome
        },
        "results": [
            {
                "case_id": result.case_id,
                "category": result.category,
                "grade_mode": result.grade_mode.value,
                "outcome": result.outcome.value,
                "detail": result.detail,
                "metadata": dict(result.metadata),
            }
            for result in results
        ],
    }
    target.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return target


def apply_manual_adjudications(
    results: Sequence[EvalCaseResult],
    adjudications: Sequence[ManualAdjudication],
) -> tuple[EvalCaseResult, ...]:
    adjudication_by_case = {item.case_id: item for item in adjudications}
    updated: list[EvalCaseResult] = []
    for result in results:
        adjudication = adjudication_by_case.get(result.case_id)
        if adjudication is None:
            updated.append(result)
            continue
        updated.append(
            EvalCaseResult(
                case_id=result.case_id,
                category=result.category,
                grade_mode=result.grade_mode,
                outcome=adjudication.outcome,
                detail=adjudication.detail,
                metadata=dict(result.metadata),
            )
        )
    return tuple(updated)


def _adjudication_from_dict(item: Any) -> ManualAdjudication:
    if not isinstance(item, dict):
        raise ValueError("manual adjudication entries must be mappings")
    case_id = str(item.get("case_id", "")).strip()
    if not case_id:
        raise ValueError("manual adjudication entry requires case_id")
    try:
        outcome = GradeOutcome(str(item.get("outcome", "")).strip())
    except ValueError as exc:
        raise ValueError("manual adjudication entry has unsupported outcome") from exc
    return ManualAdjudication(
        case_id=case_id,
        outcome=outcome,
        detail=str(item.get("detail", "")),
    )


def _result_from_dict(item: Any) -> EvalCaseResult:
    if not isinstance(item, dict):
        raise ValueError("manual result entries must be mappings")
    metadata = item.get("metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("manual result metadata must be a mapping")
    try:
        grade_mode = GradeMode(str(item.get("grade_mode", "")))
        outcome = GradeOutcome(str(item.get("outcome", "")))
    except ValueError as exc:
        raise ValueError(
            "manual result entry has unsupported grade mode or outcome"
        ) from exc
    return EvalCaseResult(
        case_id=_required_manual_string(item, "case_id"),
        category=_required_manual_string(item, "category"),
        grade_mode=grade_mode,
        outcome=outcome,
        detail=str(item.get("detail", "")),
        metadata=dict(metadata),
    )


def _load_manual_object(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manual artifact must be a JSON object")
    return payload


def _ensure_manual_version(payload: dict[str, Any]) -> None:
    if payload.get("artifact_version") != MANUAL_REVIEW_ARTIFACT_VERSION:
        raise ValueError("unsupported manual artifact version")


def _required_manual_string(payload: dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"manual artifact {key} must be a non-empty string")
    return value.strip()
