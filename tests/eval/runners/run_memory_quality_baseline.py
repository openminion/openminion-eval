#!/usr/bin/env python3.11
from __future__ import annotations

import argparse
import json
from pathlib import Path

from runner_support import (
    FRAMEWORK_ROOT,
    configure_repo_paths,
    generated_output_root,
)

configure_repo_paths()

from tests.eval.memory_quality_eval import (  # noqa: E402
    build_memory_quality_target_report,
    load_memory_quality_manifest,
    load_memory_quality_rubric,
    official_memory_quality_target_ids,
    representative_memory_quality_target_ids,
    run_memory_quality_source_report,
    write_memory_quality_report,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate memory quality baseline reports."
    )
    parser.add_argument(
        "--target-set",
        choices=("official", "representative"),
        default="representative",
        help="Which provider-shaped target inventory to report.",
    )
    parser.add_argument(
        "--output-root",
        help="Optional output directory. Defaults under .openminion/runtime/.",
    )
    return parser.parse_args()


def _target_ids(target_set: str) -> tuple[str, ...]:
    if target_set == "official":
        return official_memory_quality_target_ids()
    if target_set == "representative":
        return representative_memory_quality_target_ids()
    raise ValueError(f"unsupported target set: {target_set!r}")


def _default_output_root(target_set: str) -> Path:
    return generated_output_root(f"memory-quality-{target_set}-baseline")


def _target_record(target_id: str) -> dict[str, str]:
    config_name = {
        "minimax-m2-5": "per-agent-minimax-official.json",
        "minimax-m2-7": "per-agent-minimax-official.json",
        "ollamacloud-glm-5": "per-agent-ollamacloud-glm-5.json",
        "ollamacloud-minimax-m2-7": "per-agent-ollamacloud-minimax-m2-7.json",
        "openrouter-minimax-m2-7": "per-agent-openrouter-minimax-m2-7.json",
        "openrouter-claude-haiku-4-5": "per-agent-openrouter-claude-haiku-4-5.json",
        "openrouter-gpt-4o": "per-agent-openrouter-gpt-4o.json",
    }.get(target_id, "")
    return {
        "target_id": target_id,
        "agent_id": target_id,
        "config_path": f"test-configs/{config_name}" if config_name else "",
    }


def _report_display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(FRAMEWORK_ROOT))
    except ValueError:
        return str(path)


def main() -> int:
    args = parse_args()
    manifest_version, scenarios = load_memory_quality_manifest()
    rubric_version, rubric_dimensions = load_memory_quality_rubric()
    source_report = run_memory_quality_source_report(scenarios)
    target_ids = _target_ids(args.target_set)

    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else _default_output_root(args.target_set)
    )
    output_root.mkdir(parents=True, exist_ok=True)

    summary_targets: list[dict[str, object]] = []
    for target_id in target_ids:
        report = build_memory_quality_target_report(
            _target_record(target_id),
            manifest_version=manifest_version,
            scenarios=scenarios,
            rubric_version=rubric_version,
            rubric_dimensions=rubric_dimensions,
            source_report=source_report,
        )
        output_path = write_memory_quality_report(
            output_root / f"{target_id}.json",
            report,
        )
        summary_targets.append(
            {
                "target_id": target_id,
                "agent_id": report.agent_id,
                "config_path": report.config_path,
                "report_path": _report_display_path(output_path),
                "scenario_count": report.summary["scenario_count"],
                "overall_score": report.summary["overall_score"],
                "dimension_summary": report.summary["dimension_summary"],
            }
        )

    summary_path = output_root / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "manifest_version": manifest_version,
                "rubric_version": rubric_version,
                "target_set": args.target_set,
                "target_count": len(summary_targets),
                "execution_mode": "deterministic_memory_harness",
                "targets": summary_targets,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"[ok] wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
