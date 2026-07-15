"""Registry, grading, and starter cases for package eval cases."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable, Mapping

from openminion_eval.config import env_flag_enabled, env_value
from openminion_eval.constants import EVAL_LIVE_ENV, OPENMINION_REPO_ROOT_ENV


class GradeMode(str, Enum):
    STRUCTURAL = "structural"  # asserts over a trace / workspace; no LLM call
    LIVE = "live"  # drives a fresh agent turn; gated by OPENMINION_EVAL_LIVE=1
    MANUAL = "manual"  # human-graded; harness records "ungraded"


class GradeOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    SKIPPED = "skipped"
    UNGRADED = "ungraded"  # MANUAL mode or LIVE mode without env flag


GradeFnReturn = GradeOutcome | tuple[GradeOutcome, str]
GradeFn = Callable[["EvalCase"], GradeFnReturn]


@dataclass(frozen=True)
class EvalCase:
    """One graded eval case."""

    case_id: str
    category: str
    description: str
    prompt: str
    grade_mode: GradeMode
    anchor_paths: tuple[str, ...] = ()
    grade_fn: GradeFn | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class EvalCaseResult:
    case_id: str
    category: str
    grade_mode: GradeMode
    outcome: GradeOutcome
    detail: str = ""
    metadata: Mapping[str, str] = field(default_factory=dict)


def _resolve_repo_root() -> Path:
    """Resolve the repo root for anchor-path resolution.

    Precedence:

    1. ``OPENMINION_REPO_ROOT`` environment value.
    2. Walk up from this file until a ``docs/trackers`` directory is found.
    3. Fall back to the current working directory.
    """
    override = env_value(OPENMINION_REPO_ROOT_ENV)
    if override:
        return Path(override).expanduser().resolve()
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "docs" / "trackers").exists():
            return parent
    return Path.cwd()


def _anchor_exists(case: EvalCase) -> tuple[bool, str]:
    """Check that every anchor_paths entry exists; return (ok, detail)."""
    if not case.anchor_paths:
        return True, ""
    root = _resolve_repo_root()
    missing: list[str] = []
    for relative in case.anchor_paths:
        absolute = root / relative
        if not absolute.exists():
            missing.append(relative)
    if missing:
        return False, "missing anchors: " + ", ".join(missing)
    return True, ""


def _normalize_grade_result(raw: GradeFnReturn) -> tuple[GradeOutcome, str]:
    """Accept either a bare GradeOutcome or a (GradeOutcome, detail) tuple."""
    if isinstance(raw, tuple):
        outcome, detail = raw
        return outcome, str(detail)
    return raw, ""


def grade_case(case: EvalCase) -> EvalCaseResult:
    """Run the case under its declared grade_mode and return a result."""
    if case.grade_mode is GradeMode.MANUAL:
        return EvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            grade_mode=case.grade_mode,
            outcome=GradeOutcome.UNGRADED,
            detail="manual case; human grading required",
        )
    if case.grade_mode is GradeMode.LIVE:
        if not env_flag_enabled(EVAL_LIVE_ENV):
            return EvalCaseResult(
                case_id=case.case_id,
                category=case.category,
                grade_mode=case.grade_mode,
                outcome=GradeOutcome.SKIPPED,
                detail=f"live cases require {EVAL_LIVE_ENV}=1",
            )
        if case.grade_fn is None:
            return EvalCaseResult(
                case_id=case.case_id,
                category=case.category,
                grade_mode=case.grade_mode,
                outcome=GradeOutcome.UNGRADED,
                detail="live case has no grade_fn configured",
            )
        raw = case.grade_fn(case)
        outcome, detail = _normalize_grade_result(raw)
        return EvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            grade_mode=case.grade_mode,
            outcome=outcome,
            detail=detail,
        )
    # STRUCTURAL
    if case.anchor_paths:
        ok, missing_detail = _anchor_exists(case)
        if not ok:
            return EvalCaseResult(
                case_id=case.case_id,
                category=case.category,
                grade_mode=case.grade_mode,
                outcome=GradeOutcome.SKIPPED,
                detail=missing_detail,
            )
    if case.grade_fn is None:
        return EvalCaseResult(
            case_id=case.case_id,
            category=case.category,
            grade_mode=case.grade_mode,
            outcome=GradeOutcome.UNGRADED,
            detail="structural case has no grade_fn",
        )
    raw = case.grade_fn(case)
    outcome, detail = _normalize_grade_result(raw)
    return EvalCaseResult(
        case_id=case.case_id,
        category=case.category,
        grade_mode=case.grade_mode,
        outcome=outcome,
        detail=detail,
    )


def registered_cases() -> tuple[EvalCase, ...]:
    """Return the flat tuple of starter cases."""
    from openminion_eval.cases.starters import STARTER_CASES

    return STARTER_CASES
