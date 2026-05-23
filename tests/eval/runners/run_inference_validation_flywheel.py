#!/usr/bin/env python3.11
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

PACKAGE_ROOT = Path(__file__).resolve().parents[3]  # openminion-eval/
PACKAGE_SRC = PACKAGE_ROOT / "src"
FRAMEWORK_ROOT = PACKAGE_ROOT.parent
OPENMINION_SRC = FRAMEWORK_ROOT / "openminion" / "src"
for path in (PACKAGE_SRC, PACKAGE_ROOT, OPENMINION_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from tests.eval.integration.trace_flywheel import (  # noqa: E402
    default_inference_validation_output_root,
    run_inference_validation_flywheel,
    write_trace_eval_flywheel_report,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run the bounded TEFC inference-validation flywheel."
    )
    parser.add_argument("--config", required=True, help="OpenMinion config path.")
    parser.add_argument("--agent", default="cortensor35", help="Agent id to validate.")
    parser.add_argument(
        "--python-bin",
        default=str(FRAMEWORK_ROOT / "openminion" / ".venv" / "bin" / "python3.11"),
        help="Python binary to execute OpenMinion.",
    )
    parser.add_argument(
        "--session-prefix",
        default="trace-eval-flywheel",
        help="Session prefix for generated smoke checks.",
    )
    parser.add_argument(
        "--output-root",
        default=None,
        help="Optional output root override.",
    )
    args = parser.parse_args()

    repo_root = FRAMEWORK_ROOT.resolve()
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else default_inference_validation_output_root(repo_root)
    )
    report = run_inference_validation_flywheel(
        py_bin=Path(args.python_bin).expanduser().resolve(),
        openminion_dir=repo_root / "openminion",
        repo_root=repo_root,
        config_path=Path(args.config).expanduser().resolve(),
        agent_id=args.agent,
        session_prefix=args.session_prefix,
        output_root=output_root,
    )
    report_path = write_trace_eval_flywheel_report(output_root / "summary.json", report)
    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "workflow_id": report.bundle.workflow_id,
                "all_passed": report.all_passed,
                "check_count": report.summary.total_turns,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
