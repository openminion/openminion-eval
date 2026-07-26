"""CLI support for deterministic memory/context scorecard reports."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from openminion_eval.memory_context_scorecard.fixtures import (
    load_memory_context_scorecard_fixtures,
)
from openminion_eval.memory_context_scorecard.scoring import (
    build_context_budget_calibration,
    build_memory_context_scorecard,
    build_operational_canary,
    load_operational_canary,
    write_context_budget_calibration,
    write_memory_context_scorecard,
    write_operational_canary,
)
from openminion_eval.paths import generated_root


def add_memory_context_scorecard_parser(subparsers: Any) -> None:
    parser = subparsers.add_parser(
        "memory-context-scorecard",
        help="write a deterministic memory/context quality scorecard report",
    )
    parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="optional scorecard fixture JSON; defaults to packaged fixtures",
    )
    parser.add_argument(
        "--run-id",
        default="memory-context-scorecard-local",
        help="run id for scorecard artifacts",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write report JSON to PATH; defaults under generated root",
    )
    parser.set_defaults(func=memory_context_scorecard_command)

    canary_parser = subparsers.add_parser(
        "memory-context-operational-canary",
        help="write a deterministic memory/context operational canary report",
    )
    canary_parser.add_argument(
        "--fixtures",
        type=Path,
        default=None,
        help="optional scorecard fixture JSON; defaults to packaged fixtures",
    )
    canary_parser.add_argument(
        "--run-id",
        default="memory-context-operational-canary-local",
        help="run id for canary artifacts",
    )
    canary_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write report JSON to PATH; defaults under generated root",
    )
    canary_parser.set_defaults(func=memory_context_operational_canary_command)

    calibration_parser = subparsers.add_parser(
        "context-budget-calibration",
        help="write context-budget recommendations from an operational canary",
    )
    calibration_parser.add_argument(
        "--canary",
        type=Path,
        required=True,
        help="memory-context-operational-canary.v1 JSON artifact",
    )
    calibration_parser.add_argument(
        "--run-id",
        default="context-budget-calibration-local",
        help="run id for calibration artifacts",
    )
    calibration_parser.add_argument(
        "--evidence-window",
        default="local",
        help="human-readable evidence window label",
    )
    calibration_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write report JSON to PATH; defaults under generated root",
    )
    calibration_parser.set_defaults(func=context_budget_calibration_command)


def memory_context_scorecard_command(args: argparse.Namespace) -> int:
    fixtures = load_memory_context_scorecard_fixtures(args.fixtures)
    scorecard = build_memory_context_scorecard(
        fixtures,
        run_id=args.run_id,
        metadata={
            "fixture_source": "packaged"
            if args.fixtures is None
            else str(args.fixtures)
        },
    )
    output = args.out or (
        generated_root() / "memory-context-scorecard" / f"{args.run_id}.json"
    )
    write_memory_context_scorecard(output, scorecard)
    sys.stdout.write(
        json.dumps(
            {
                "report_version": scorecard.report_version,
                "run_id": scorecard.run_id,
                "fixture_count": scorecard.summary["fixture_count"],
                "metric_count": scorecard.summary["metric_count"],
                "blocking_fail_count": scorecard.summary["blocking_fail_count"],
                "all_blocking_passed": scorecard.summary["all_blocking_passed"],
                "artifact": str(output),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0 if bool(scorecard.summary["all_blocking_passed"]) else 1


def memory_context_operational_canary_command(args: argparse.Namespace) -> int:
    fixtures = load_memory_context_scorecard_fixtures(args.fixtures)
    scorecard = build_memory_context_scorecard(
        fixtures,
        run_id=f"{args.run_id}-source-scorecard",
        metadata={
            "fixture_source": "packaged"
            if args.fixtures is None
            else str(args.fixtures)
        },
    )
    report = build_operational_canary(
        scorecard,
        run_id=args.run_id,
        metadata={"fixture_source": scorecard.metadata["fixture_source"]},
    )
    output = args.out or (
        generated_root() / "memory-context-operational-canary" / f"{args.run_id}.json"
    )
    write_operational_canary(output, report)
    sys.stdout.write(
        json.dumps(
            {
                "report_version": report.report_version,
                "run_id": report.run_id,
                "case_count": report.summary["case_count"],
                "fail_count": report.summary["fail_count"],
                "all_passed": report.summary["all_passed"],
                "artifact": str(output),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0 if bool(report.summary["all_passed"]) else 1


def context_budget_calibration_command(args: argparse.Namespace) -> int:
    canary = load_operational_canary(args.canary)
    report = build_context_budget_calibration(
        canary,
        run_id=args.run_id,
        evidence_window=args.evidence_window,
        metadata={"source_canary": str(args.canary)},
    )
    output = args.out or (
        generated_root() / "context-budget-calibration" / f"{args.run_id}.json"
    )
    write_context_budget_calibration(output, report)
    sys.stdout.write(
        json.dumps(
            {
                "report_version": report.report_version,
                "run_id": report.run_id,
                "recommendation_count": report.summary["recommendation_count"],
                "change_count": report.summary["change_count"],
                "writes_runtime_config": report.summary["writes_runtime_config"],
                "artifact": str(output),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    return 0
