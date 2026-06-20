"""Command-line entrypoint for generic eval suite workflows."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
from typing import Any

from openminion_eval.datasets import hash_eval_dataset, load_eval_dataset
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


def _write_json(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
