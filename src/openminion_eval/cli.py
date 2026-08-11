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
from openminion_eval.cases import (
    GradeOutcome,
    grade_case,
    registered_cases,
)
from openminion_eval.manual import (
    apply_manual_adjudications,
    build_manual_review_queue,
    load_manual_adjudications,
    write_manual_review_queue,
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
    render_artifact_index_html,
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
    render_suite_diff_artifact_html,
    render_suite_diff_artifact_markdown,
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
    SUITE_DIFF_VERSION,
    build_suite_diff_artifact,
    build_run_manifest,
    compare_suite_results,
    load_suite_diff,
    load_suite_result,
    write_suite_diff,
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
    _add_manual_parser(subparsers)
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

    suite_diff_parser = report_subparsers.add_parser(
        "suite-diff",
        help="render a suite-diff artifact",
    )
    suite_diff_parser.add_argument("artifact", type=Path)
    _add_report_output_args(suite_diff_parser)
    suite_diff_parser.set_defaults(func=_report_suite_diff_command)

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

    bundle_parser = report_subparsers.add_parser(
        "bundle",
        help="write an HTML index for one or more artifact files",
    )
    bundle_parser.add_argument("artifacts", nargs="+", type=Path)
    bundle_parser.add_argument("--out", type=Path, required=True)
    bundle_parser.set_defaults(func=_report_bundle_command)


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

    inspect_parser = artifact_subparsers.add_parser(
        "inspect",
        help="summarize a known openminion-eval artifact",
    )
    inspect_parser.add_argument("artifact", type=Path)
    inspect_parser.set_defaults(func=_artifact_inspect_command)


def _add_manual_parser(subparsers: Any) -> None:
    manual_parser = subparsers.add_parser(
        "manual",
        help="create and apply local manual-review artifacts",
    )
    manual_subparsers = manual_parser.add_subparsers(
        dest="manual_command", required=True
    )
    queue_parser = manual_subparsers.add_parser(
        "queue",
        help="write the current manual-review queue",
    )
    queue_parser.add_argument("--out", type=Path, required=True)
    queue_parser.set_defaults(func=_manual_queue_command)

    apply_parser = manual_subparsers.add_parser(
        "apply",
        help="apply manual adjudications to the current starter-case results",
    )
    apply_parser.add_argument("adjudications", type=Path)
    apply_parser.add_argument("--out", type=Path, required=True)
    apply_parser.set_defaults(func=_manual_apply_command)


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
    artifact = build_suite_diff_artifact(previous, current)
    payload = asdict(artifact)
    if args.out is not None:
        write_suite_diff(args.out, artifact)
    else:
        _write_json(payload)

    failing_categories = {"new_fail", "regressed", "missing_transcript"}
    return 1 if failing_categories.intersection(artifact.categories) else 0


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


def _report_suite_diff_command(args: argparse.Namespace) -> int:
    diff = load_suite_diff(args.artifact)
    report = (
        render_suite_diff_artifact_html(diff)
        if args.format == "html"
        else render_suite_diff_artifact_markdown(diff)
    )
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


def _report_bundle_command(args: argparse.Namespace) -> int:
    items = [_inspect_artifact(path) for path in args.artifacts]
    _write_text(render_artifact_index_html(items), args.out)
    return 0


def _artifact_validate_command(args: argparse.Namespace) -> int:
    try:
        info = _inspect_artifact(args.artifact)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"artifact validation error: {exc}\n")
        return 2
    _write_json({"valid": True, **info})
    return 0


def _artifact_inspect_command(args: argparse.Namespace) -> int:
    try:
        info = _inspect_artifact(args.artifact)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as exc:
        sys.stderr.write(f"artifact inspection error: {exc}\n")
        return 2
    _write_json(info)
    return 0


def _inspect_artifact(path: Path) -> dict[str, str]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("artifact must be a JSON object")
    version = str(payload.get("version") or payload.get("report_version") or "")
    artifact_version = str(payload.get("artifact_version") or "")
    if artifact_version and "manifest" in payload and "result" in payload:
        result, manifest = load_suite_result(path)
        return {
            "artifact": str(path),
            "artifact_kind": "suite-result",
            "version": artifact_version,
            "run_id": manifest.run_id,
            "summary": (
                f"{result.passed_transcripts}/{result.total_transcripts} passed"
            ),
        }
    if version == SUITE_DIFF_VERSION:
        diff = load_suite_diff(path)
        return {
            "artifact": str(path),
            "artifact_kind": "suite-diff",
            "version": version,
            "summary": _category_summary(diff.categories),
        }
    if artifact_version and "scorecard" in payload:
        scorecard = load_memory_scorecard(path)
        return {
            "artifact": str(path),
            "artifact_kind": "memory-effectiveness-scorecard",
            "version": artifact_version,
            "run_id": scorecard.run_id,
            "summary": (
                f"score {scorecard.overall_score:.3f}; "
                f"{len(scorecard.critical_failures)} critical failures"
            ),
        }
    if version == DELEGATED_MEMORY_SCORECARD_VERSION:
        scorecard = load_delegated_memory_scorecard(path)
        return {
            "artifact": str(path),
            "artifact_kind": "delegated-memory-scorecard",
            "version": version,
            "summary": (
                f"passed={scorecard.passed}; utility {scorecard.utility_recall:.3f}"
            ),
        }
    if version == DELEGATED_MEMORY_DIFF_VERSION:
        diff = load_delegated_memory_scorecard_diff(path)
        return {
            "artifact": str(path),
            "artifact_kind": "delegated-memory-diff",
            "version": version,
            "summary": _category_summary(diff.categories),
        }
    if version == MEMORY_CONTEXT_SCORECARD_VERSION:
        scorecard = load_memory_context_scorecard(path)
        return {
            "artifact": str(path),
            "artifact_kind": "memory-context-scorecard",
            "version": version,
            "run_id": scorecard.run_id,
            "summary": (
                f"{scorecard.summary.get('blocking_fail_count', 0)} blocking failures"
            ),
        }
    if version == MEMORY_CONTEXT_OPERATIONAL_CANARY_VERSION:
        canary = load_operational_canary(path)
        return {
            "artifact": str(path),
            "artifact_kind": "memory-context-operational-canary",
            "version": version,
            "run_id": canary.run_id,
            "summary": f"{canary.summary.get('fail_count', 0)} failures",
        }
    if version == CONTEXT_BUDGET_CALIBRATION_VERSION:
        calibration = load_context_budget_calibration(path)
        return {
            "artifact": str(path),
            "artifact_kind": "context-budget-calibration",
            "version": version,
            "run_id": calibration.run_id,
            "summary": f"{calibration.summary.get('change_count', 0)} changes",
        }
    raise ValueError("unsupported artifact shape")


def _category_summary(categories: dict[str, int]) -> str:
    return ", ".join(
        f"{category}={count}" for category, count in sorted(categories.items())
    )


def _manual_queue_command(args: argparse.Namespace) -> int:
    queue = build_manual_review_queue(registered_cases())
    output = write_manual_review_queue(args.out, queue)
    _write_json({"artifact": str(output), "item_count": len(queue.items)})
    return 0


def _manual_apply_command(args: argparse.Namespace) -> int:
    adjudications = load_manual_adjudications(args.adjudications)
    results = tuple(grade_case(case) for case in registered_cases())
    updated = apply_manual_adjudications(results, adjudications)
    payload = {
        "artifact_version": "1",
        "summary": _manual_result_counts(updated),
        "results": [_case_result_payload(result) for result in updated],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_json({"artifact": str(args.out), **payload["summary"]})
    return 1 if payload["summary"].get("fail", 0) else 0


def _manual_result_counts(results: tuple[Any, ...]) -> dict[str, int]:
    return {
        outcome.value: sum(1 for result in results if result.outcome is outcome)
        for outcome in GradeOutcome
    }


def _case_result_payload(result: Any) -> dict[str, object]:
    return {
        "case_id": result.case_id,
        "category": result.category,
        "grade_mode": result.grade_mode.value,
        "outcome": result.outcome.value,
        "detail": result.detail,
        "metadata": dict(result.metadata),
    }


def _scorers_list_command(_args: argparse.Namespace) -> int:
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
