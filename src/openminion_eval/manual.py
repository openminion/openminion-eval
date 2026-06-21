"""Local JSON manual grading artifacts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Sequence

from openminion_eval.cases import EvalCase, EvalCaseResult, GradeMode, GradeOutcome

MANUAL_REVIEW_ARTIFACT_VERSION = "1"


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
        return asdict(self)


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


def load_manual_adjudications(path: str | Path) -> tuple[ManualAdjudication, ...]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("artifact_version") != MANUAL_REVIEW_ARTIFACT_VERSION:
        raise ValueError("unsupported manual adjudication artifact version")
    items = payload.get("adjudications")
    if not isinstance(items, list):
        raise ValueError("manual adjudication artifact requires an adjudications list")
    return tuple(_adjudication_from_dict(item) for item in items)


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
