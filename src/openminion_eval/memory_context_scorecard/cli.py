"""CLI support for deterministic memory/context scorecard reports."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

from openminion_eval.memory_context_scorecard.fixtures import (
    load_memory_context_scorecard_fixtures,
)
from openminion_eval.memory_context_scorecard.scoring import (
    build_memory_context_scorecard,
    write_memory_context_scorecard,
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
