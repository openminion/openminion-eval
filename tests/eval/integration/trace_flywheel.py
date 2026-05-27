"""Repo-local workflow-grade trace/eval flywheel helpers."""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Sequence

from openminion.base.generated_paths import resolve_generated_root
from openminion.modules.brain.runtime.self_eval_rubric import SelfEvalSubmission
from openminion_eval.family_support import utc_now_iso
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer
from openminion_eval.schemas import EvalResult, EvalSummary, EvalTranscript


@dataclass(frozen=True)
class WorkflowEvalRubric:
    """Typed grading contract for one workflow-grade flywheel lane."""

    rubric_id: str
    scorer_name: str
    threshold: float
    expected_status: str


@dataclass(frozen=True)
class WorkflowCheckObservation:
    """One structural workflow observation consumed by the flywheel."""

    check_id: str
    expected_status: str
    actual_status: str
    passed: bool
    details: str


@dataclass(frozen=True)
class WorkflowTraceEvalBundle:
    """Typed workflow evidence bundle for a bounded flywheel pass."""

    bundle_version: str
    workflow_id: str
    workflow_label: str
    trace_source_kind: str
    determinism_class: str
    artifact_output_root: str
    config_path: str
    agent_id: str
    session_prefix: str
    observations: tuple[WorkflowCheckObservation, ...]
    self_eval_submission: SelfEvalSubmission | None = None


@dataclass(frozen=True)
class WorkflowTraceEvalReport:
    """Workflow-grade flywheel report over a typed evidence bundle."""

    report_version: str
    generated_at: str
    bundle: WorkflowTraceEvalBundle
    rubric: WorkflowEvalRubric
    summary: EvalSummary
    all_passed: bool

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if self.bundle.self_eval_submission is not None:
            payload["bundle"]["self_eval_submission"] = (
                self.bundle.self_eval_submission.model_dump(mode="json")
            )
        return payload


def default_inference_validation_output_root(repo_root: Path) -> Path:
    """Return the canonical generated-root output for the TEFC first pass."""
    return (
        resolve_generated_root(home_root=repo_root)
        / "trace-eval-flywheel"
        / "inference-validation-smoke"
    )


def build_inference_validation_bundle(
    *,
    check_results: Sequence[Any],
    artifact_output_root: str | Path,
    config_path: str | Path,
    agent_id: str,
    session_prefix: str,
) -> WorkflowTraceEvalBundle:
    """Freeze the bounded TEFC first-pass workflow evidence bundle."""
    observations = tuple(
        WorkflowCheckObservation(
            check_id=str(getattr(result, "name")),
            expected_status="pass",
            actual_status="pass" if bool(getattr(result, "ok")) else "fail",
            passed=bool(getattr(result, "ok")),
            details=str(getattr(result, "details", "") or "").strip(),
        )
        for result in check_results
    )
    return WorkflowTraceEvalBundle(
        bundle_version="1",
        workflow_id="inference_validation_smoke",
        workflow_label="Inference Validation Smoke",
        trace_source_kind="workflow_smoke_checks",
        determinism_class="deterministic_local",
        artifact_output_root=str(Path(artifact_output_root).expanduser().resolve()),
        config_path=str(Path(config_path).expanduser().resolve()),
        agent_id=str(agent_id).strip(),
        session_prefix=str(session_prefix).strip(),
        observations=observations,
    )


def build_trace_eval_flywheel_report(
    bundle: WorkflowTraceEvalBundle,
    *,
    scorer_name: str = "exact_match",
    threshold: float = 1.0,
) -> WorkflowTraceEvalReport:
    """Compose the typed workflow bundle through the canonical eval substrate."""
    rubric = WorkflowEvalRubric(
        rubric_id=f"{bundle.workflow_id}.exact_status",
        scorer_name=scorer_name,
        threshold=float(threshold),
        expected_status="pass",
    )
    transcript = EvalTranscript(
        name=bundle.workflow_id,
        turns=[
            {"user": observation.check_id, "expected": rubric.expected_status}
            for observation in bundle.observations
        ],
        tags=[
            bundle.workflow_id,
            bundle.trace_source_kind,
            bundle.determinism_class,
        ],
    )
    status_by_check_id = {
        observation.check_id: observation.actual_status
        for observation in bundle.observations
    }
    runner = EvalRunner(agent_executor=lambda check_id: status_by_check_id[check_id])
    results = runner.replay_sync(transcript)
    observation_by_check_id = {
        observation.check_id: observation for observation in bundle.observations
    }
    annotated_results: list[EvalResult] = []
    for result in results:
        observation = observation_by_check_id[result.user_input]
        annotated_results.append(
            replace(
                result,
                metadata={
                    **result.metadata,
                    "check_id": observation.check_id,
                    "details": observation.details,
                    "passed": observation.passed,
                    "actual_status": observation.actual_status,
                    "expected_status": observation.expected_status,
                    "trace_source_kind": bundle.trace_source_kind,
                    "determinism_class": bundle.determinism_class,
                },
            )
        )
    scorer = EvalScorer()
    scored_results = scorer.score_results(annotated_results, scorer_name=scorer_name)
    scores = [result.score for result in scored_results]
    average_score = sum(scores) / len(scores) if scores else 0.0
    summary = EvalSummary(
        transcript_name=transcript.name,
        total_turns=len(scored_results),
        average_score=average_score,
        min_score=min(scores) if scores else 0.0,
        max_score=max(scores) if scores else 0.0,
        results=scored_results,
        passed=average_score >= rubric.threshold,
        threshold=rubric.threshold,
    )
    return WorkflowTraceEvalReport(
        report_version="1",
        generated_at=utc_now_iso(),
        bundle=bundle,
        rubric=rubric,
        summary=summary,
        all_passed=summary.passed,
    )


def write_trace_eval_flywheel_report(
    path: str | Path,
    report: WorkflowTraceEvalReport,
) -> Path:
    """Write the TEFC flywheel report as stable JSON evidence."""
    output_path = Path(path).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        __import__("json").dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def _collect_inference_validation_results(
    *,
    py_bin: Path,
    openminion_dir: Path,
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    session_prefix: str,
) -> Sequence[Any]:
    from tests.e2e.runners.run_inference_validation_smoke import (
        check_chat_turn,
        check_gateway_turn,
        check_import_smoke,
        check_retrieve_debug,
    )

    return (
        check_import_smoke(py_bin, repo_root),
        check_retrieve_debug(py_bin, openminion_dir, config_path, repo_root),
        check_chat_turn(
            py_bin,
            openminion_dir,
            config_path,
            agent_id,
            f"{session_prefix}-chat",
        ),
        check_gateway_turn(
            py_bin,
            openminion_dir,
            config_path,
            agent_id,
            f"{session_prefix}-gateway",
        ),
    )


def run_inference_validation_flywheel(
    *,
    py_bin: Path,
    openminion_dir: Path,
    repo_root: Path,
    config_path: Path,
    agent_id: str,
    session_prefix: str,
    output_root: Path | None = None,
) -> WorkflowTraceEvalReport:
    """Run the bounded inference-validation workflow through the TEFC flywheel."""
    resolved_output_root = output_root or default_inference_validation_output_root(
        repo_root
    )
    check_results = _collect_inference_validation_results(
        py_bin=py_bin,
        openminion_dir=openminion_dir,
        repo_root=repo_root,
        config_path=config_path,
        agent_id=agent_id,
        session_prefix=session_prefix,
    )
    bundle = build_inference_validation_bundle(
        check_results=check_results,
        artifact_output_root=resolved_output_root,
        config_path=config_path,
        agent_id=agent_id,
        session_prefix=session_prefix,
    )
    return build_trace_eval_flywheel_report(bundle)
