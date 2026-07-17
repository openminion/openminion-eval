#!/usr/bin/env python3.11
from __future__ import annotations

import json
from pathlib import Path

from runner_support import configure_repo_paths, generated_output_root

configure_repo_paths(include_tests=True)

from tests.eval.provider_certification_matrix import (  # noqa: E402
    build_provider_certification_report,
    load_provider_certification_manual_cells,
    load_provider_certification_targets,
    write_provider_certification_report,
)


def _default_output_root() -> Path:
    return generated_output_root("provider-certification-matrix")


def main() -> int:
    inventory_version, targets = load_provider_certification_targets()
    manual_version, manual_cells = load_provider_certification_manual_cells()
    report = build_provider_certification_report(
        inventory_version=inventory_version,
        targets=targets,
        manual_evidence_version=manual_version,
        manual_cells=manual_cells,
    )

    output_root = _default_output_root()
    output_root.mkdir(parents=True, exist_ok=True)
    report_path = write_provider_certification_report(
        output_root / "summary.json", report
    )

    markdown_rows = []
    for row in report.rows:
        markdown_rows.append(
            f"| {row.target_id} | {row.access.status} | {row.explicit_tool.status} | {row.nl_tool_parity.status} | "
            f"{row.skill_routing.status} | {row.nl_named_skill.status} | {row.output_quality.status} | "
            f"{row.confirmation_policy.status} |"
        )

    matrix_md = (
        "| Target | Access | Explicit Tool | NL Tool Parity | Skill Routing | "
        "NL Named Skill | Output Quality | Confirmation Policy |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- |\n"
        + "\n".join(markdown_rows)
        + "\n"
    )
    matrix_path = output_root / "matrix.md"
    matrix_path.write_text(matrix_md, encoding="utf-8")

    print(
        json.dumps(
            {
                "report_path": str(report_path),
                "matrix_path": str(matrix_path),
                "target_count": report.summary["target_count"],
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
