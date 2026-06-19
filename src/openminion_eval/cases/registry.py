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


def _grade_coding_minimax_markdown_table(case: EvalCase) -> GradeFnReturn:
    """Check a seeded coding workspace when one is attached."""
    workspace = _workspace_anchor(case)
    if workspace is None:
        return (
            GradeOutcome.UNGRADED,
            "portable starter case; attach a workspace anchor for structural grading",
        )
    test_files = list(workspace.rglob("test_*.py")) if workspace.exists() else []
    if not test_files:
        return GradeOutcome.FAIL, "no test_*.py in workspace"
    return (
        GradeOutcome.UNGRADED,
        "structural pre-check passed; real pass/fail needs live `pytest -q` "
        "in the workspace (future LIVE-mode variant)",
    )


def _grade_research_to_code_drift(case: EvalCase) -> GradeFnReturn:
    """Check a seeded research workspace for the expected API surface."""
    workspace = _workspace_anchor(case)
    if workspace is None:
        return (
            GradeOutcome.UNGRADED,
            "portable starter case; attach a workspace anchor for structural grading",
        )
    if not workspace.exists():
        return GradeOutcome.FAIL, "workspace anchor does not exist"
    expected_api = "build_summary"
    drift_api = "generate_summary"
    for py_file in workspace.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if expected_api in text and drift_api not in text:
            return GradeOutcome.PASS, ""
        if drift_api in text:
            return GradeOutcome.FAIL, "workspace still references drift API"
    return GradeOutcome.FAIL, "workspace missing expected API"


def _workspace_anchor(case: EvalCase) -> Path | None:
    if len(case.anchor_paths) < 3:
        return None
    return _resolve_repo_root() / case.anchor_paths[2]


def _grade_recovery_after_tool_failure(case: EvalCase) -> GradeOutcome:
    """Check that the typed recovery termination reason is still exposed."""
    root = _resolve_repo_root()
    target = (
        root
        / "openminion"
        / "src"
        / "openminion"
        / "services"
        / "agent"
        / "execution"
        / "required_lane"
        / "post_execution.py"
    )
    if not target.exists():
        return GradeOutcome.FAIL
    text = target.read_text(encoding="utf-8", errors="ignore")
    return GradeOutcome.PASS if "empty_provider_response" in text else GradeOutcome.FAIL


def _grade_multi_tool_complex_task(case: EvalCase) -> GradeOutcome:
    """Check that the canonical multi-tool baseline is still exposed."""
    root = _resolve_repo_root()
    catalog = (
        root
        / "openminion"
        / "src"
        / "openminion"
        / "modules"
        / "tool"
        / "contracts"
        / "model_tool_ids.py"
    )
    if not catalog.exists():
        return GradeOutcome.FAIL
    text = catalog.read_text(encoding="utf-8", errors="ignore")
    required = ("MODEL_FILE_READ", "MODEL_FILE_WRITE", "MODEL_EXEC_RUN")
    return (
        GradeOutcome.PASS
        if all(token in text for token in required)
        else GradeOutcome.FAIL
    )


def _grade_memory_recall_across_session(case: EvalCase) -> GradeOutcome:
    """Check that the memory portability surface is still reachable."""
    root = _resolve_repo_root()
    portability = (
        root
        / "openminion"
        / "src"
        / "openminion"
        / "modules"
        / "memory"
        / "portability"
    )
    return GradeOutcome.PASS if portability.is_dir() else GradeOutcome.FAIL


_STARTER_CASES: tuple[EvalCase, ...] = (
    EvalCase(
        case_id="coding_minimax_markdown_table",
        category="coding",
        description=(
            "Coding quality starter case — checks whether a generated project "
            "includes tests that treat Markdown table headers separately from "
            "data rows."
        ),
        prompt=(
            "Build a fizzbuzz CLI with tests; include a Markdown table of "
            "results in the README."
        ),
        grade_mode=GradeMode.STRUCTURAL,
        grade_fn=_grade_coding_minimax_markdown_table,
        tags=("markdown-table-tests", "model-quality"),
    ),
    EvalCase(
        case_id="research_to_code_drift",
        category="research",
        description=(
            "Research-to-code starter case — checks whether implementation "
            "keeps the expected public function name from the research prompt "
            "instead of drifting to a different API."
        ),
        prompt=(
            "Research the 3 most-recent papers on retrieval-augmented "
            "generation and update build_summary.py to render them."
        ),
        grade_mode=GradeMode.STRUCTURAL,
        grade_fn=_grade_research_to_code_drift,
        tags=("api-drift", "research-code"),
    ),
    EvalCase(
        case_id="recovery_after_tool_failure",
        category="recovery",
        description=(
            "Recovery starter case — assert the typed `empty_provider_response` "
            "termination reason exists in the post-execution path."
        ),
        prompt=(
            "Call a tool that returns no output, then ask the agent to "
            "summarize what just happened."
        ),
        grade_mode=GradeMode.STRUCTURAL,
        grade_fn=_grade_recovery_after_tool_failure,
        tags=("tool-failure-recovery",),
    ),
    EvalCase(
        case_id="multi_tool_complex_task",
        category="multi_tool",
        description=(
            "Multi-tool baseline — assert the canonical tool registry exposes "
            "file.read, file.write, exec.run."
        ),
        prompt=("Read the file `notes.md`, append a TODO line, and run pytest."),
        grade_mode=GradeMode.STRUCTURAL,
        grade_fn=_grade_multi_tool_complex_task,
        tags=("multi-tool",),
    ),
    EvalCase(
        case_id="memory_recall_across_session",
        category="memory",
        description=(
            "Memory baseline — assert the memory portability surface "
            "(export/import bundle) is reachable from the package layout."
        ),
        prompt=(
            "Remember that my preferred indent is 4 spaces. In a new session, "
            "write a Python function and check the indentation."
        ),
        grade_mode=GradeMode.STRUCTURAL,
        grade_fn=_grade_memory_recall_across_session,
        tags=("memory-portability",),
    ),
)


def registered_cases() -> tuple[EvalCase, ...]:
    """Return the flat tuple of starter cases."""
    return _STARTER_CASES
