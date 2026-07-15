from __future__ import annotations

from pathlib import Path

from openminion_eval.cases.registry import (
    EvalCase,
    GradeFnReturn,
    GradeMode,
    GradeOutcome,
    _resolve_repo_root,
)


def _workspace_anchor(case: EvalCase) -> Path | None:
    if len(case.anchor_paths) < 3:
        return None
    return _resolve_repo_root() / case.anchor_paths[2]


def _grade_coding_minimax_markdown_table(case: EvalCase) -> GradeFnReturn:
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


def _grade_recovery_after_tool_failure(case: EvalCase) -> GradeOutcome:
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
    root = _resolve_repo_root()
    catalog = (
        root
        / "openminion"
        / "src"
        / "openminion"
        / "modules"
        / "tool"
        / "contracts"
        / "model_ids.py"
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


STARTER_CASES: tuple[EvalCase, ...] = (
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
        anchor_paths=(
            "openminion/src/openminion/services/agent/execution/required_lane/post_execution.py",
        ),
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
        anchor_paths=("openminion/src/openminion/modules/tool/contracts/model_ids.py",),
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
        anchor_paths=("openminion/src/openminion/modules/memory/portability",),
        grade_fn=_grade_memory_recall_across_session,
        tags=("memory-portability",),
    ),
)
