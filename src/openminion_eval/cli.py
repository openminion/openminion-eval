"""Command-line entrypoint for generic eval suite workflows."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from openminion_eval.datasets import hash_eval_dataset, load_eval_dataset
from openminion_eval.memory_effectiveness import (
    MemoryEffectivenessTrace,
    MemoryTraceClaim,
    MemoryTraceToolCall,
    build_memory_scorecard,
    load_memory_effectiveness_cases,
    score_memory_case,
    write_memory_scorecard,
)
from openminion_eval.suite import EvalSuite
from openminion_eval.suite_artifacts import (
    build_run_manifest,
    compare_suite_results,
    load_suite_result,
    write_suite_result,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openminion-eval",
        description="Run generic eval suites and compare suite artifacts.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser(
        "run",
        help="run a JSON or JSONL dataset through the package eval suite",
    )
    run_parser.add_argument("dataset", type=Path, help="dataset JSON or JSONL file")
    run_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write a suite-result JSON artifact to PATH",
    )
    run_parser.add_argument(
        "--scorer",
        default="substring_match",
        help="scorer name to use (default: substring_match)",
    )
    run_parser.add_argument(
        "--threshold",
        type=float,
        default=0.80,
        help="minimum average score for transcript pass/fail (default: 0.80)",
    )
    run_parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="optional worker count for parallel transcript execution",
    )
    run_parser.set_defaults(func=_run_command)

    diff_parser = subparsers.add_parser(
        "diff",
        help="compare two suite-result JSON artifacts",
    )
    diff_parser.add_argument("previous", type=Path, help="previous suite artifact")
    diff_parser.add_argument("current", type=Path, help="current suite artifact")
    diff_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write the diff JSON summary to PATH instead of stdout",
    )
    diff_parser.set_defaults(func=_diff_command)

    memory_parser = subparsers.add_parser(
        "memory-effectiveness",
        help="score structured memory-effectiveness trace artifacts",
    )
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", required=True
    )
    score_parser = memory_subparsers.add_parser(
        "score",
        help="score a trace JSON artifact against packaged memory cases",
    )
    score_parser.add_argument("trace", type=Path, help="trace JSON file")
    score_parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="optional case fixture JSON; defaults to packaged cases",
    )
    score_parser.add_argument(
        "--suite-id",
        default="openminion-sophiagraph-memory-effectiveness",
        help="suite id for scorecard artifacts",
    )
    score_parser.add_argument(
        "--run-id",
        default="memory-effectiveness-local",
        help="run id for scorecard artifacts",
    )
    score_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write scorecard JSON artifact to PATH",
    )
    score_parser.set_defaults(func=_memory_score_command)
    return parser


def _run_command(args: argparse.Namespace) -> int:
    dataset = load_eval_dataset(args.dataset)
    suite = EvalSuite(threshold=args.threshold)
    result = suite.run(
        dataset.transcripts,
        scorer_name=args.scorer,
        max_workers=args.max_workers,
    )
    manifest = build_run_manifest(
        dataset.transcripts,
        scorer_name=args.scorer,
        threshold=args.threshold,
        metadata={
            "dataset_hash": hash_eval_dataset(dataset),
            "dataset_name": dataset.name,
            "dataset_version": dataset.dataset_version,
        },
    )
    if args.out is not None:
        write_suite_result(args.out, result, manifest)

    _write_json(
        {
            "suite_name": result.suite_name,
            "dataset_name": dataset.name,
            "total_transcripts": result.total_transcripts,
            "passed_transcripts": result.passed_transcripts,
            "failed_transcripts": result.failed_transcripts,
            "all_passed": result.all_passed,
            "artifact": None if args.out is None else str(args.out),
        }
    )
    return 0 if result.all_passed else 1


def _diff_command(args: argparse.Namespace) -> int:
    previous, _previous_manifest = load_suite_result(args.previous)
    current, _current_manifest = load_suite_result(args.current)
    diff = compare_suite_results(previous, current)
    payload = {
        "previous_suite_name": diff.previous_suite_name,
        "current_suite_name": diff.current_suite_name,
        "categories": diff.categories,
        "entries": [asdict(entry) for entry in diff.entries],
    }
    if args.out is not None:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    else:
        _write_json(payload)

    failing_categories = {"new_fail", "regressed", "missing_transcript"}
    return 1 if failing_categories.intersection(diff.categories) else 0


def _memory_score_command(args: argparse.Namespace) -> int:
    cases = load_memory_effectiveness_cases(args.cases)
    traces = _load_memory_traces(args.trace)
    traces_by_case = {trace.case_id: trace for trace in traces}
    results = [
        score_memory_case(case, traces_by_case[case.case_id])
        for case in cases
        if case.case_id in traces_by_case
    ]
    unmatched_cases = tuple(
        case.case_id for case in cases if case.case_id not in traces_by_case
    )
    scorecard = build_memory_scorecard(
        suite_id=args.suite_id,
        run_id=args.run_id,
        case_results=results,
        metadata={"trace": str(args.trace), "unmatched_cases": unmatched_cases},
    )
    if args.out is not None:
        write_memory_scorecard(args.out, scorecard)
    _write_json(
        {
            "suite_id": scorecard.suite_id,
            "run_id": scorecard.run_id,
            "case_count": len(scorecard.cases),
            "unmatched_case_count": len(unmatched_cases),
            "overall_score": scorecard.overall_score,
            "critical_failure_count": len(scorecard.critical_failures),
            "artifact": None if args.out is None else str(args.out),
        }
    )
    return 1 if scorecard.critical_failures or unmatched_cases else 0


def _load_memory_traces(path: Path) -> tuple[MemoryEffectivenessTrace, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "traces" in payload:
        items = payload["traces"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("trace artifact must be a list or contain a 'traces' list")
    if not isinstance(items, list):
        raise ValueError("trace artifact 'traces' value must be a list")
    traces: list[MemoryEffectivenessTrace] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"trace item {index} must be an object")
        traces.append(_memory_trace_from_dict(item))
    return tuple(traces)


def _memory_trace_from_dict(data: dict[str, Any]) -> MemoryEffectivenessTrace:
    supporting_claims = data.get("supporting_claims", ())
    tool_calls = data.get("tool_calls", ())
    if not isinstance(supporting_claims, list | tuple):
        raise ValueError("supporting_claims must be a list")
    if not isinstance(tool_calls, list | tuple):
        raise ValueError("tool_calls must be a list")
    return MemoryEffectivenessTrace(
        case_id=str(data.get("case_id", "")),
        run_id=str(data.get("run_id", "")),
        memory_mode=data.get("memory_mode"),  # type: ignore[arg-type]
        saved_memory_ids=tuple(data.get("saved_memory_ids", ())),
        retrieved_memory_ids=tuple(data.get("retrieved_memory_ids", ())),
        used_memory_ids=tuple(data.get("used_memory_ids", ())),
        supporting_claims=tuple(
            MemoryTraceClaim(
                claim=str(item.get("claim", "")),
                memory_id=str(item.get("memory_id", "")),
            )
            for item in _objects(supporting_claims, "supporting_claims")
        ),
        tool_calls=tuple(
            MemoryTraceToolCall(
                tool=str(item.get("tool", "")),
                arguments_ref=str(item.get("arguments_ref", "")),
                memory_ids=tuple(item.get("memory_ids", ())),
            )
            for item in _objects(tool_calls, "tool_calls")
        ),
        diagnostics=tuple(data.get("diagnostics", ())),
        namespace=str(data.get("namespace", "")),
        timestamp=str(data.get("timestamp", "")),
    )


def _objects(items: list | tuple, label: str) -> tuple[dict[str, Any], ...]:
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"{label} item {index} must be an object")
        objects.append(item)
    return tuple(objects)


def _write_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
