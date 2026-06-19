"""Eval schemas for OpenMinion."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalTranscript:
    name: str
    turns: list[dict]  # [{"user": "...", "expected": "..."}]
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalResult:
    turn_index: int
    user_input: str
    expected: str
    actual: str
    score: float
    scorer_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalSummary:
    transcript_name: str
    total_turns: int
    average_score: float
    min_score: float
    max_score: float
    results: list[EvalResult]
    passed: bool
    threshold: float = 0.80
    scorer_error_count: int = 0


@dataclass
class EvalSuiteResult:
    suite_name: str
    total_transcripts: int
    passed_transcripts: int
    failed_transcripts: int
    summaries: list[EvalSummary]
    all_passed: bool


@dataclass(frozen=True)
class EvalRunManifest:
    run_id: str
    generated_at: str
    package_version: str
    git_sha: str | None
    input_hash: str
    scorer_name: str
    threshold: float
    deterministic: bool = False
    seed: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalBaselineDiffEntry:
    transcript_name: str
    category: str
    previous_passed: bool | None
    current_passed: bool | None
    previous_average_score: float | None
    current_average_score: float | None


@dataclass(frozen=True)
class EvalBaselineDiff:
    previous_suite_name: str
    current_suite_name: str
    entries: list[EvalBaselineDiffEntry]

    @property
    def categories(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.entries:
            counts[entry.category] = counts.get(entry.category, 0) + 1
        return counts
