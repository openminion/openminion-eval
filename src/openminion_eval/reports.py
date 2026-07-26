"""Human-readable report renderers for suite artifacts."""

from __future__ import annotations

from html import escape

from openminion_eval.schemas import (
    EvalBaselineDiff,
    EvalRunManifest,
    EvalSuiteResult,
    EvalSummary,
)


def render_suite_result_markdown(
    result: EvalSuiteResult,
    manifest: EvalRunManifest | None = None,
) -> str:
    lines = [
        "# OpenMinion Eval Suite Report",
        "",
        "## Summary",
        "",
        f"- Suite: `{result.suite_name}`",
        f"- Total transcripts: {result.total_transcripts}",
        f"- Passed: {result.passed_transcripts}",
        f"- Failed: {result.failed_transcripts}",
        f"- All passed: {_yes_no(result.all_passed)}",
    ]
    if manifest is not None:
        lines.extend(
            [
                f"- Run ID: `{manifest.run_id}`",
                f"- Scorer: `{manifest.scorer_name}`",
                f"- Threshold: {manifest.threshold:.3f}",
            ]
        )
    lines.extend(
        [
            "",
            "## Transcripts",
            "",
            "| Transcript | Status | Avg | Min | Max | Turns | Errors |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for summary in result.summaries:
        lines.append(_summary_row(summary))
    lines.extend(_failure_sections(result))
    return "\n".join(lines) + "\n"


def render_baseline_diff_markdown(diff: EvalBaselineDiff) -> str:
    lines = [
        "# OpenMinion Eval Baseline Diff",
        "",
        "## Summary",
        "",
    ]
    for category, count in sorted(diff.categories.items()):
        lines.append(f"- {category}: {count}")
    lines.extend(
        [
            "",
            "## Entries",
            "",
            "| Transcript | Category | Previous | Current | Previous Avg | Current Avg |",
            "| --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    for entry in diff.entries:
        lines.append(
            "| "
            f"{_cell(entry.transcript_name)} | "
            f"{_cell(entry.category)} | "
            f"{_status(entry.previous_passed)} | "
            f"{_status(entry.current_passed)} | "
            f"{_score(entry.previous_average_score)} | "
            f"{_score(entry.current_average_score)} |"
        )
    return "\n".join(lines) + "\n"


def render_suite_result_html(
    result: EvalSuiteResult,
    manifest: EvalRunManifest | None = None,
) -> str:
    markdown = render_suite_result_markdown(result, manifest)
    return _html_page("OpenMinion Eval Suite Report", markdown)


def render_baseline_diff_html(diff: EvalBaselineDiff) -> str:
    markdown = render_baseline_diff_markdown(diff)
    return _html_page("OpenMinion Eval Baseline Diff", markdown)


def _summary_row(summary: EvalSummary) -> str:
    status = "pass" if summary.passed else "fail"
    return (
        "| "
        f"{_cell(summary.transcript_name)} | "
        f"{status} | "
        f"{summary.average_score:.3f} | "
        f"{summary.min_score:.3f} | "
        f"{summary.max_score:.3f} | "
        f"{summary.total_turns} | "
        f"{summary.scorer_error_count} |"
    )


def _failure_sections(result: EvalSuiteResult) -> list[str]:
    failed = [summary for summary in result.summaries if not summary.passed]
    if not failed:
        return []
    lines = ["", "## Failing Turns", ""]
    for summary in failed:
        lines.extend(["", f"### {summary.transcript_name}", ""])
        for case_result in summary.results:
            if case_result.score >= summary.threshold:
                continue
            lines.extend(
                [
                    f"- Turn: {case_result.turn_index}",
                    f"  - Score: {case_result.score:.3f}",
                    f"  - Expected: `{case_result.expected}`",
                    f"  - Actual: `{case_result.actual}`",
                ]
            )
    return lines


def _html_page(title: str, markdown: str) -> str:
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        '<head><meta charset="utf-8"><title>'
        f"{escape(title)}</title></head>\n"
        f"<body><pre>{escape(markdown)}</pre></body>\n"
        "</html>\n"
    )


def _cell(value: str) -> str:
    return value.replace("|", "\\|")


def _score(value: float | None) -> str:
    return "" if value is None else f"{value:.3f}"


def _status(value: bool | None) -> str:
    if value is None:
        return ""
    return "pass" if value else "fail"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
