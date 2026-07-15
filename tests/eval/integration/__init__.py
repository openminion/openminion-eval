"""Repo-local integration tooling for openminion-eval."""

from __future__ import annotations

from importlib import import_module
from typing import Any


_MEMORY_EVAL_EXPORTS = {
    "MemoryEvalComparison",
    "MemoryEvalComparisonEntry",
    "MemoryEvalEngineConfig",
    "MemoryEvalFixtureLoader",
    "MemoryEvalGeneratedRecords",
    "MemoryEvalGroundTruth",
    "MemoryEvalHarness",
    "MemoryEvalReport",
    "MemoryEvalScenario",
    "MemoryEvalScenarioResult",
    "MemoryEvalSeedCandidate",
    "MemoryEvalSeedRecord",
    "MemoryEvalSession",
    "MemoryEvalSetup",
    "MemoryEvalTurn",
}
_MEMORY_SCORER_EXPORTS = {"MemoryEvalScorer"}
_TRACE_FLYWHEEL_EXPORTS = {
    "WorkflowCheckObservation",
    "WorkflowEvalRubric",
    "WorkflowTraceEvalBundle",
    "WorkflowTraceEvalReport",
    "build_inference_validation_bundle",
    "build_trace_eval_flywheel_report",
    "default_inference_validation_output_root",
    "run_inference_validation_flywheel",
    "write_trace_eval_flywheel_report",
}

__all__ = sorted(
    _MEMORY_EVAL_EXPORTS | _MEMORY_SCORER_EXPORTS | _TRACE_FLYWHEEL_EXPORTS
)


def __getattr__(name: str) -> Any:
    if name in _MEMORY_EVAL_EXPORTS:
        return getattr(import_module(".memory_eval", __name__), name)
    if name in _MEMORY_SCORER_EXPORTS:
        return getattr(import_module(".memory_scorer", __name__), name)
    if name in _TRACE_FLYWHEEL_EXPORTS:
        return getattr(import_module(".trace_flywheel", __name__), name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
