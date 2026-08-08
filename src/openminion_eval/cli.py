"""Command-line entrypoint for generic eval suite workflows."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
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
from openminion_eval.memory_context_scorecard import (
    CONTEXT_BUDGET_CALIBRATION_VERSION,
    MEMORY_CONTEXT_OPERATIONAL_CANARY_VERSION,
    MEMORY_CONTEXT_SCORECARD_VERSION,
    load_context_budget_calibration,
    load_memory_context_scorecard,
    load_operational_canary,
)
from openminion_eval.memory_effectiveness import (
    DELEGATED_MEMORY_DIFF_VERSION,
    DELEGATED_MEMORY_SCORECARD_VERSION,
    load_delegated_memory_scorecard,
    load_delegated_memory_scorecard_diff,
    load_memory_scorecard,
)
from openminion_eval.memory_effectiveness.cli import (
    add_memory_effectiveness_parser,
)
from openminion_eval.reports import (
    render_baseline_diff_html,
    render_baseline_diff_markdown,
    render_delegated_memory_diff_html,
    render_delegated_memory_diff_markdown,
    render_delegated_memory_scorecard_html,
    render_delegated_memory_scorecard_markdown,
    render_memory_context_scorecard_html,
    render_memory_context_scorecard_markdown,
    render_memory_scorecard_html,
    render_memory_scorecard_markdown,
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
    _add_artifact_parser(subparsers)
    _add_report_parser(subparsers)
    _add_scorers_parser(subparsers)
    _add_integration_parser(subparsers)
    add_memory_effectiveness_parser(subparsers)
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

    memory_parser = report_subparsers.add_parser(
        "memory-scorecard",
        help="render a memory-effectiveness scorecard artifact",
    )
    memory_parser.add_argument("artifact", type=Path)
    _add_report_output_args(memory_parser)
    memory_parser.set_defaults(func=_report_memory_scorecard_command)

    delegated_parser = report_subparsers.add_parser(
        "delegated-memory",
        help="render a delegated-memory scorecard artifact",
    )
    delegated_parser.add_argument("artifact", type=Path)
    _add_report_output_args(delegated_parser)
    delegated_parser.set_defaults(func=_report_delegated_memory_command)

    delegated_diff_parser = report_subparsers.add_parser(
        "delegated-diff",
        help="render a delegated-memory diff artifact",
    )
    delegated_diff_parser.add_argument("artifact", type=Path)
    _add_report_output_args(delegated_diff_parser)
    delegated_diff_parser.set_defaults(func=_report_delegated_memory_diff_command)

    context_parser = report_subparsers.add_parser(
        "memory-context",
        help="render a memory/context scorecard artifact",
    )
    context_parser.add_argument("artifact", type=Path)
    _add_report_output_args(context_parser)
    context_parser.set_defaults(func=_report_memory_context_command)


def _add_report_output_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=("markdown", "html"),
        default="markdown",
        help="report format (default: markdown)",
    )
    parser.add_argument("--out", type=Path, default=None)


def _add_artifact_parser(subparsers: Any) -> None:
    artifact_parser = subparsers.add_parser(
        "artifact",
        help="validate package JSON artifacts",
    )
    artifact_subparsers = artifact_parser.add_subparsers(
        dest="artifact_command", required=True
    )
    validate_parser = artifact_subparsers.add_parser(
        "validate",
        help="validate a known openminion-eval artifact",
    )
    validate_parser.add_argument("artifact", type=Path)
    validate_parser.set_defaults(func=_artifact_validate_command)


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


def _report_memory_scorecard_command(args: argparse.Namespace) -> int:
    scorecard = load_memory_scorecard(args.artifact)
    report = (
        render_memory_scorecard_html(scorecard)
        if args.format == "html"
        else render_memory_scorecard_markdown(scorecard)
    )
    _write_text(report, args.out)
    return 0


def _report_delegated_memory_command(args: argparse.Namespace) -> int:
    scorecard = load_delegated_memory_scorecard(args.artifact)
    report = (
        render_delegated_memory_scorecard_html(scorecard)
        if args.format == "html"
        else render_delegated_memory_scorecard_markdown(scorecard)
    )
    _write_text(report, args.out)
    return 0


def _report_delegated_memory_diff_command(args: argparse.Namespace) -> int:
    diff = load_delegated_memory_scorecard_diff(args.artifact)
    report = (
        render_delegated_memory_diff_html(diff)
        if args.format == "html"
        else render_delegated_memory_diff_markdown(diff)
    )
    _write_text(report, args.out)
    return 0


def _report_memory_context_command(args: argparse.Namespace) -> int:
    scorecard = load_memory_context_scorecard(args.artifact)
    report = (
        render_memory_context_scorecard_html(scorecard)
        if args.format == "html"
        else render_memory_context_scorecard_markdown(scorecard)
    )
    _write_text(report, args.out)
    return 0


def _artifact_validate_command(args: argparse.Namespace) -> int:
    try:
        info = _validate_artifact(args.artifact)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"artifact validation error: {exc}\n")
        return 2
    _write_json({"valid": True, "artifact": str(args.artifact), **info})
    return 0


def _validate_artifact(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("artifact must be a JSON object")
    version = str(payload.get("version") or payload.get("report_version") or "")
    artifact_version = str(payload.get("artifact_version") or "")
    if artifact_version and "manifest" in payload and "result" in payload:
        load_suite_result(path)
        return {"artifact_kind": "suite-result", "version": artifact_version}
    if artifact_version and "scorecard" in payload:
        load_memory_scorecard(path)
        return {
            "artifact_kind": "memory-effectiveness-scorecard",
            "version": artifact_version,
        }
    if version == DELEGATED_MEMORY_SCORECARD_VERSION:
        load_delegated_memory_scorecard(path)
        return {"artifact_kind": "delegated-memory-scorecard", "version": version}
    if version == DELEGATED_MEMORY_DIFF_VERSION:
        load_delegated_memory_scorecard_diff(path)
        return {"artifact_kind": "delegated-memory-diff", "version": version}
    if version == MEMORY_CONTEXT_SCORECARD_VERSION:
        load_memory_context_scorecard(path)
        return {"artifact_kind": "memory-context-scorecard", "version": version}
    if version == MEMORY_CONTEXT_OPERATIONAL_CANARY_VERSION:
        load_operational_canary(path)
        return {
            "artifact_kind": "memory-context-operational-canary",
            "version": version,
        }
    if version == CONTEXT_BUDGET_CALIBRATION_VERSION:
        load_context_budget_calibration(path)
        return {"artifact_kind": "context-budget-calibration", "version": version}
    raise ValueError("unsupported artifact shape")


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
