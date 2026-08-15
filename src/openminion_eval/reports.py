"""Human-readable report renderers for suite artifacts."""

from __future__ import annotations

from html import escape
from typing import Mapping, Sequence

from openminion_eval.memory_context_scorecard import MemoryContextScorecardV1
from openminion_eval.memory_effectiveness import (
    DelegatedMemoryEvalScorecard,
    DelegatedMemoryScorecardDiff,
    MemoryEffectivenessScorecard,
)
from openminion_eval.schemas import (
    EvalBaselineDiff,
    EvalRunManifest,
    EvalSuiteResult,
    EvalSummary,
)
from openminion_eval.suite_artifacts import EvalSuiteDiffArtifact


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


def render_suite_diff_artifact_markdown(diff: EvalSuiteDiffArtifact) -> str:
    lines = [
        "# OpenMinion Eval Suite Diff",
        "",
        "## Summary",
        "",
        f"- Previous suite: `{diff.previous_suite_name}`",
        f"- Current suite: `{diff.current_suite_name}`",
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


def render_suite_diff_artifact_html(diff: EvalSuiteDiffArtifact) -> str:
    markdown = render_suite_diff_artifact_markdown(diff)
    return _html_page("OpenMinion Eval Suite Diff", markdown)


def render_memory_scorecard_markdown(scorecard: MemoryEffectivenessScorecard) -> str:
    lines = [
        "# OpenMinion Memory-Effectiveness Scorecard",
        "",
        "## Summary",
        "",
        f"- Suite: `{scorecard.suite_id}`",
        f"- Run ID: `{scorecard.run_id}`",
        f"- Overall score: {scorecard.overall_score:.3f}",
        f"- Critical failures: {len(scorecard.critical_failures)}",
        "",
        "## Components",
        "",
        "| Component | Passed | Total | Score | Failures |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for component in scorecard.component_scores:
        lines.append(
            "| "
            f"{_cell(component.component)} | "
            f"{component.passed} | "
            f"{component.total} | "
            f"{component.score:.3f} | "
            f"{_cell(', '.join(component.failures))} |"
        )
    lines.extend(
        [
            "",
            "## Cases",
            "",
            "| Case | Status | Overall | Critical Failures |",
            "| --- | --- | ---: | --- |",
        ]
    )
    for case in scorecard.cases:
        lines.append(
            "| "
            f"{_cell(case.case_id)} | "
            f"{case.status} | "
            f"{case.overall_score:.3f} | "
            f"{_cell(', '.join(case.critical_failures))} |"
        )
    return "\n".join(lines) + "\n"


def render_delegated_memory_scorecard_markdown(
    scorecard: DelegatedMemoryEvalScorecard,
) -> str:
    lines = [
        "# OpenMinion Delegated-Memory Scorecard",
        "",
        "## Summary",
        "",
        f"- Suite: `{scorecard.suite_id}`",
        f"- Passed: {_yes_no(scorecard.passed)}",
        f"- Utility recall: {scorecard.utility_recall:.3f}",
        f"- Critical failures: {len(scorecard.critical_failures)}",
        "",
        "## Cases",
        "",
        "| Case | Mode | Status | Utility Recall | Critical Failures |",
        "| --- | --- | --- | ---: | --- |",
    ]
    for result in scorecard.results:
        lines.append(
            "| "
            f"{_cell(result.case_id)} | "
            f"{result.mode} | "
            f"{'pass' if result.passed else 'fail'} | "
            f"{result.utility_recall:.3f} | "
            f"{_cell(', '.join(result.critical_failures))} |"
        )
    return "\n".join(lines) + "\n"


def render_delegated_memory_diff_markdown(
    diff: DelegatedMemoryScorecardDiff,
) -> str:
    lines = [
        "# OpenMinion Delegated-Memory Diff",
        "",
        "## Summary",
        "",
        f"- Previous suite: `{diff.previous_suite_id}`",
        f"- Current suite: `{diff.current_suite_id}`",
    ]
    for category, count in sorted(diff.categories.items()):
        lines.append(f"- {category}: {count}")
    lines.extend(
        [
            "",
            "## Entries",
            "",
            "| Case | Category | Previous | Current | Previous Recall | Current Recall | Delta | Critical Failures |",
            "| --- | --- | --- | --- | ---: | ---: | ---: | --- |",
        ]
    )
    for entry in diff.entries:
        lines.append(
            "| "
            f"{_cell(entry.case_id)} | "
            f"{entry.category} | "
            f"{_status(entry.previous_passed)} | "
            f"{_status(entry.current_passed)} | "
            f"{_score(entry.previous_utility_recall)} | "
            f"{_score(entry.current_utility_recall)} | "
            f"{_score(entry.delta)} | "
            f"{_cell(', '.join(entry.critical_failures))} |"
        )
    return "\n".join(lines) + "\n"


def render_memory_context_scorecard_markdown(
    scorecard: MemoryContextScorecardV1,
) -> str:
    lines = [
        "# OpenMinion Memory/Context Scorecard",
        "",
        "## Summary",
        "",
        f"- Report version: `{scorecard.report_version}`",
        f"- Run ID: `{scorecard.run_id}`",
        f"- Generated at: `{scorecard.generated_at}`",
        f"- All blocking passed: {_yes_no(bool(scorecard.summary.get('all_blocking_passed', False)))}",
        f"- Blocking failures: {scorecard.summary.get('blocking_fail_count', 0)}",
        "",
        "## Metrics",
        "",
        "| Metric | Status | Value | Threshold | Blocking | Evidence |",
        "| --- | --- | ---: | ---: | --- | --- |",
    ]
    for metric in scorecard.metrics:
        lines.append(
            "| "
            f"{_cell(metric.metric_name)} | "
            f"{metric.status} | "
            f"{metric.value:.3f} | "
            f"{metric.threshold:.3f} | "
            f"{_yes_no(metric.blocking)} | "
            f"{_cell(', '.join(metric.evidence_refs))} |"
        )
    return "\n".join(lines) + "\n"


def render_memory_scorecard_html(scorecard: MemoryEffectivenessScorecard) -> str:
    markdown = render_memory_scorecard_markdown(scorecard)
    return _html_page("OpenMinion Memory-Effectiveness Scorecard", markdown)


def render_delegated_memory_scorecard_html(
    scorecard: DelegatedMemoryEvalScorecard,
) -> str:
    markdown = render_delegated_memory_scorecard_markdown(scorecard)
    return _html_page("OpenMinion Delegated-Memory Scorecard", markdown)


def render_delegated_memory_diff_html(diff: DelegatedMemoryScorecardDiff) -> str:
    markdown = render_delegated_memory_diff_markdown(diff)
    return _html_page("OpenMinion Delegated-Memory Diff", markdown)


def render_memory_context_scorecard_html(scorecard: MemoryContextScorecardV1) -> str:
    markdown = render_memory_context_scorecard_markdown(scorecard)
    return _html_page("OpenMinion Memory/Context Scorecard", markdown)


def render_artifact_index_html(items: Sequence[Mapping[str, object]]) -> str:
    rows = [
        "| Artifact | Kind | Version | Summary |",
        "| --- | --- | --- | --- |",
    ]
    for item in items:
        rows.append(
            "| "
            f"{_cell(str(item.get('artifact', '')))} | "
            f"{_cell(str(item.get('artifact_kind', '')))} | "
            f"{_cell(str(item.get('version', '')))} | "
            f"{_cell(str(item.get('summary', '')))} |"
        )
    markdown = "\n".join(["# OpenMinion Eval Artifact Index", "", *rows]) + "\n"
    return _html_page("OpenMinion Eval Artifact Index", markdown)


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
    body = "\n".join(_markdown_blocks(markdown))
    styles = _html_styles()
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>"
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title>"
        f"<style>{styles}</style>"
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def _html_styles() -> str:
    return (
        ":root{color-scheme:light dark;--bg:#f8fafc;--fg:#0f172a;"
        "--muted:#64748b;--line:#cbd5e1;--panel:#ffffff;--pass:#047857;"
        "--fail:#b91c1c;--warn:#b45309}"
        "@media(prefers-color-scheme:dark){:root{--bg:#0b1220;--fg:#e5e7eb;"
        "--muted:#94a3b8;--line:#334155;--panel:#111827}}"
        "body{margin:0 auto;max-width:1120px;padding:32px 24px;"
        "background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,"
        "-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}"
        "h1{font-size:32px;margin:0 0 24px}h2{font-size:22px;margin-top:28px}"
        "h3{font-size:18px;margin-top:24px}p,ul{max-width:840px}"
        "code{padding:.1rem .3rem;border:1px solid var(--line);border-radius:4px}"
        "table{width:100%;border-collapse:collapse;margin:16px 0 28px;"
        "background:var(--panel)}th,td{border:1px solid var(--line);"
        "padding:8px 10px;text-align:left;vertical-align:top}th{font-weight:650}"
        ".status-pass{color:var(--pass);font-weight:650}.status-fail,"
        ".status-regressed,.status-new_fail,.status-missing_transcript{"
        "color:var(--fail);font-weight:650}.status-warn{color:var(--warn);"
        "font-weight:650}@media print{body{background:white;color:black}}"
    )


def _markdown_blocks(markdown: str) -> list[str]:
    lines = markdown.splitlines()
    blocks: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue
        if (
            line.startswith("| ")
            and index + 1 < len(lines)
            and _is_table_rule(lines[index + 1])
        ):
            table, index = _table_block(lines, index)
            blocks.append(table)
            continue
        if line.startswith("- "):
            items, index = _list_block(lines, index)
            blocks.append(items)
            continue
        heading = _heading_block(line)
        if heading is not None:
            blocks.append(heading)
        else:
            blocks.append(f"<p>{_inline_html(line)}</p>")
        index += 1
    return blocks


def _heading_block(line: str) -> str | None:
    for level, marker in ((3, "### "), (2, "## "), (1, "# ")):
        if line.startswith(marker):
            text = line[len(marker) :]
            return f"<h{level}>{_inline_html(text)}</h{level}>"
    return None


def _list_block(lines: list[str], start: int) -> tuple[str, int]:
    items: list[str] = []
    index = start
    while index < len(lines) and lines[index].startswith("- "):
        items.append(f"<li>{_inline_html(lines[index][2:])}</li>")
        index += 1
    return "<ul>\n" + "\n".join(items) + "\n</ul>", index


def _table_block(lines: list[str], start: int) -> tuple[str, int]:
    header = _table_cells(lines[start])
    rows: list[list[str]] = []
    index = start + 2
    while index < len(lines) and lines[index].startswith("| "):
        rows.append(_table_cells(lines[index]))
        index += 1
    header_html = "".join(f"<th>{_inline_html(cell)}</th>" for cell in header)
    body_rows = [
        "<tr>" + "".join(_data_cell(cell) for cell in row) + "</tr>" for row in rows
    ]
    table = (
        "<table>\n<thead><tr>"
        + header_html
        + "</tr></thead>\n<tbody>\n"
        + "\n".join(body_rows)
        + "\n</tbody>\n</table>"
    )
    return table, index


def _data_cell(cell: str) -> str:
    class_name = _status_class(cell)
    attrs = "" if not class_name else f' class="{class_name}"'
    return f"<td{attrs}>{_inline_html(cell)}</td>"


def _status_class(value: str) -> str:
    token = value.strip().lower().replace(" ", "_")
    if token in {
        "fail",
        "failed",
        "regressed",
        "new_fail",
        "missing_transcript",
        "unchanged_fail",
    }:
        return f"status-{token}"
    if token in {"pass", "passed", "yes", "fixed", "new_pass", "unchanged_pass"}:
        return "status-pass"
    if token in {"warn", "warning"}:
        return "status-warn"
    return ""


def _table_cells(row: str) -> list[str]:
    protected = row.replace("\\|", "\u0000")
    return [
        cell.strip().replace("\u0000", "|")
        for cell in protected.strip().strip("|").split("|")
    ]


def _is_table_rule(line: str) -> bool:
    cells = _table_cells(line)
    return bool(cells) and all(
        set(cell.replace(":", "").strip()) <= {"-"} for cell in cells
    )


def _inline_html(value: str) -> str:
    parts = value.split("`")
    rendered: list[str] = []
    for index, part in enumerate(parts):
        text = escape(part)
        rendered.append(f"<code>{text}</code>" if index % 2 else text)
    return "".join(rendered)


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
