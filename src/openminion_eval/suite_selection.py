from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from openminion_eval.schemas import EvalSuiteResult, EvalTranscript


def select_transcripts(
    transcripts: Sequence[EvalTranscript],
    *,
    previous_result: EvalSuiteResult | None = None,
    failed_only: bool = False,
    include_names: Sequence[str] | None = None,
    exclude_names: Sequence[str] | None = None,
    include_tags: Sequence[str] | None = None,
    exclude_tags: Sequence[str] | None = None,
) -> list[EvalTranscript]:
    """Select transcripts for partial reruns while preserving input order."""
    failed_names: set[str] | None = None
    if failed_only:
        if previous_result is None:
            raise ValueError("previous_result is required when failed_only=True")
        failed_names = {
            summary.transcript_name
            for summary in previous_result.summaries
            if not summary.passed
        }

    include_name_set = set(include_names or ())
    exclude_name_set = set(exclude_names or ())
    include_tag_set = set(include_tags or ())
    exclude_tag_set = set(exclude_tags or ())

    selected: list[EvalTranscript] = []
    for transcript in transcripts:
        tags = set(transcript.tags)
        if failed_names is not None and transcript.name not in failed_names:
            continue
        if include_name_set and transcript.name not in include_name_set:
            continue
        if transcript.name in exclude_name_set:
            continue
        if include_tag_set and not tags.intersection(include_tag_set):
            continue
        if exclude_tag_set and tags.intersection(exclude_tag_set):
            continue
        selected.append(transcript)
    return selected


def load_golden_transcripts(path: str) -> list[EvalTranscript]:
    """Load golden transcripts from a directory."""
    transcripts_dir = Path(path)
    if not transcripts_dir.exists():
        return []

    transcripts: list[EvalTranscript] = []
    for file in sorted(transcripts_dir.glob("*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        transcripts.append(
            EvalTranscript(
                name=data.get("name", file.stem),
                turns=data.get("turns", []),
                tags=data.get("tags", []),
            )
        )
    return transcripts
