"""Command-line entrypoint for generic eval suite workflows."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from openminion_eval.datasets import (
    build_eval_dataset_template,
    hash_eval_dataset,
    load_eval_dataset,
    write_eval_dataset_template,
)
from openminion_eval.integration_quarantine import (
    build_integration_quarantine_map,
    integration_probe_tiers,
)
from openminion_eval.memory_context_scorecard.cli import (
    add_memory_context_scorecard_parser,
)
from openminion_eval.memory_effectiveness import (
    MemoryEffectivenessTrace,
    MemoryTraceClaim,
    MemoryTraceToolCall,
    build_memory_scorecard,
    load_memory_effectiveness_cases,
    score_memory_case,
    write_memory_scorecard,
)
from openminion_eval.reports import (
    render_baseline_diff_html,
    render_baseline_diff_markdown,
    render_suite_result_html,
    render_suite_result_markdown,
)
from openminion_eval.scorer import EvalScorer
from openminion_eval.subject_adapters import (
    CliSubject,
    HttpSubject,
    load_replay_subject,
    parse_http_headers,
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

    _add_run_parser(subparsers)
    _add_diff_parser(subparsers)
    _add_dataset_parser(subparsers)
    _add_report_parser(subparsers)
    _add_scorers_parser(subparsers)
    _add_integration_parser(subparsers)
    _add_memory_effectiveness_parser(subparsers)
    add_memory_context_scorecard_parser(subparsers)
    return parser


def _add_run_parser(subparsers: Any) -> None:
    run_parser = subparsers.add_parser(
        "run", help="run a JSON or JSONL dataset through the package eval suite"
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
    subject_group = run_parser.add_mutually_exclusive_group()
    subject_group.add_argument(
        "--http-url",
        default=None,
        help="POST each turn to a JSON HTTP endpoint and read its output field",
    )
    subject_group.add_argument(
        "--command",
        default=None,
        help="run each turn through a local command string over stdin",
    )
    subject_group.add_argument(
        "--replay-jsonl",
        type=Path,
        default=None,
        help="replay outputs from JSONL records with user/input and actual/output",
    )
    run_parser.add_argument(
        "--http-header",
        action="append",
        default=[],
        metavar="NAME=VALUE",
        help="HTTP header for --http-url; may be repeated",
    )
    run_parser.add_argument(
        "--http-output-field",
        default="output",
        help="JSON response field to read for --http-url (default: output)",
    )
    run_parser.add_argument(
        "--subject-timeout",
        type=float,
        default=30.0,
        help="black-box subject timeout in seconds (default: 30)",
    )
    run_parser.set_defaults(func=_run_command)


def _add_diff_parser(subparsers: Any) -> None:
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


def _add_dataset_parser(subparsers: Any) -> None:
    dataset_parser = subparsers.add_parser(
        "dataset",
        help="validate, hash, or create eval datasets",
    )
    dataset_subparsers = dataset_parser.add_subparsers(
        dest="dataset_command", required=True
    )
    validate_parser = dataset_subparsers.add_parser(
        "validate", help="validate a JSON or JSONL dataset"
    )
    validate_parser.add_argument("dataset", type=Path)
    validate_parser.set_defaults(func=_dataset_validate_command)

    hash_parser = dataset_subparsers.add_parser(
        "hash", help="print a stable dataset hash"
    )
    hash_parser.add_argument("dataset", type=Path)
    hash_parser.set_defaults(func=_dataset_hash_command)

    init_parser = dataset_subparsers.add_parser("init", help="write a starter dataset")
    init_parser.add_argument(
        "--family",
        default="generic",
        help="starter family name such as routing, tools, freshness, or policy",
    )
    init_parser.add_argument("--out", type=Path, default=None)
    init_parser.set_defaults(func=_dataset_init_command)


def _add_report_parser(subparsers: Any) -> None:
    report_parser = subparsers.add_parser(
        "report",
        help="render human-readable reports from eval artifacts",
    )
    report_subparsers = report_parser.add_subparsers(
        dest="report_command", required=True
    )
    suite_parser = report_subparsers.add_parser(
        "suite", help="render a suite-result artifact"
    )
    suite_parser.add_argument("artifact", type=Path)
    _add_report_output_args(suite_parser)
    suite_parser.set_defaults(func=_report_suite_command)

    diff_parser = report_subparsers.add_parser(
        "diff", help="render a baseline diff report"
    )
    diff_parser.add_argument("previous", type=Path)
    diff_parser.add_argument("current", type=Path)
    _add_report_output_args(diff_parser)
    diff_parser.set_defaults(func=_report_diff_command)


def _add_report_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("markdown", "html"),
        default="markdown",
        help="report format (default: markdown)",
    )
    parser.add_argument("--out", type=Path, default=None)


def _add_scorers_parser(subparsers: Any) -> None:
    scorers_parser = subparsers.add_parser(
        "scorers",
        help="inspect built-in scorer registry metadata",
    )
    scorer_subparsers = scorers_parser.add_subparsers(
        dest="scorers_command", required=True
    )
    list_parser = scorer_subparsers.add_parser("list", help="list available scorers")
    list_parser.set_defaults(func=_scorers_list_command)


def _add_integration_parser(subparsers: Any) -> None:
    integration_parser = subparsers.add_parser(
        "integration",
        help="inspect repo-local integration probe tiers",
    )
    integration_subparsers = integration_parser.add_subparsers(
        dest="integration_command", required=True
    )
    list_parser = integration_subparsers.add_parser(
        "list", help="list source-tree integration probes"
    )
    list_parser.add_argument("--root", type=Path, default=Path.cwd())
    list_parser.add_argument("--tier", choices=integration_probe_tiers(), default=None)
    list_parser.set_defaults(func=_integration_list_command)


def _add_memory_effectiveness_parser(subparsers: Any) -> None:
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


def _run_command(args: argparse.Namespace) -> int:
    dataset = load_eval_dataset(args.dataset)
    suite = EvalSuite(threshold=args.threshold, subject=_subject_from_args(args))
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


def _dataset_validate_command(args: argparse.Namespace) -> int:
    dataset = load_eval_dataset(args.dataset)
    _write_json(
        {
            "valid": True,
            "dataset_name": dataset.name,
            "dataset_version": dataset.dataset_version,
            "case_count": len(dataset.cases),
            "dataset_hash": hash_eval_dataset(dataset),
        }
    )
    return 0


def _dataset_hash_command(args: argparse.Namespace) -> int:
    dataset = load_eval_dataset(args.dataset)
    _write_json({"dataset_hash": hash_eval_dataset(dataset)})
    return 0


def _dataset_init_command(args: argparse.Namespace) -> int:
    if args.out is None:
        _write_json(build_eval_dataset_template(family=args.family))
        return 0
    output = write_eval_dataset_template(args.out, family=args.family)
    _write_json({"artifact": str(output), "family": args.family})
    return 0


def _report_suite_command(args: argparse.Namespace) -> int:
    result, manifest = load_suite_result(args.artifact)
    if args.format == "html":
        report = render_suite_result_html(result, manifest)
    else:
        report = render_suite_result_markdown(result, manifest)
    _write_text(report, args.out)
    return 0


def _report_diff_command(args: argparse.Namespace) -> int:
    previous, _previous_manifest = load_suite_result(args.previous)
    current, _current_manifest = load_suite_result(args.current)
    diff = compare_suite_results(previous, current)
    if args.format == "html":
        report = render_baseline_diff_html(diff)
    else:
        report = render_baseline_diff_markdown(diff)
    _write_text(report, args.out)
    return 0


def _scorers_list_command(args: argparse.Namespace) -> int:
    _write_json({"scorers": [asdict(item) for item in EvalScorer().list_scorers()]})
    return 0


def _integration_list_command(args: argparse.Namespace) -> int:
    dispositions = build_integration_quarantine_map(args.root, tier=args.tier)
    _write_json(
        {
            "root": str(args.root),
            "tier": args.tier,
            "probe_count": len(dispositions),
            "probes": [item.to_dict() for item in dispositions],
        }
    )
    return 0


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
                operation=str(item.get("operation", "") or ""),
                memory_location=str(item.get("memory_location", "") or ""),
            )
            for item in _objects(tool_calls, "tool_calls")
        ),
        diagnostics=tuple(data.get("diagnostics", ())),
        namespace=str(data.get("namespace", "")),
        timestamp=str(data.get("timestamp", "")),
        context_memory_ids=tuple(data.get("context_memory_ids", ())),
        cited_memory_ids=tuple(data.get("cited_memory_ids", ())),
        provider_id=str(data.get("provider_id", "") or ""),
        model_id=str(data.get("model_id", "") or ""),
        token_count=data.get("token_count"),
        cost_usd=data.get("cost_usd"),
        latency_ms=data.get("latency_ms"),
        entity_proposal_ids=tuple(data.get("entity_proposal_ids", ())),
        fact_proposal_ids=tuple(data.get("fact_proposal_ids", ())),
        lifecycle_event_ids=tuple(data.get("lifecycle_event_ids", ())),
        artifact_ids=tuple(data.get("artifact_ids", ())),
        citation_spans=tuple(data.get("citation_spans", ())),
        trajectory_steps=tuple(data.get("trajectory_steps", ())),
        graph_path_ids=tuple(data.get("graph_path_ids", ())),
        valid_time_refs=tuple(data.get("valid_time_refs", ())),
        transaction_time_refs=tuple(data.get("transaction_time_refs", ())),
        redaction_status=data.get("redaction_status", "sanitized"),  # type: ignore[arg-type]
        private_trace_refs=tuple(data.get("private_trace_refs", ())),
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


def _write_text(payload: str, path: Path | None) -> None:
    if path is None:
        sys.stdout.write(payload)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")


def _subject_from_args(args: argparse.Namespace) -> Any | None:
    if args.http_url is not None:
        return HttpSubject(
            args.http_url,
            headers=parse_http_headers(args.http_header),
            timeout_seconds=args.subject_timeout,
            output_field=args.http_output_field,
        )
    if args.command is not None:
        return CliSubject(args.command, timeout_seconds=args.subject_timeout)
    if args.replay_jsonl is not None:
        return load_replay_subject(args.replay_jsonl)
    return None
