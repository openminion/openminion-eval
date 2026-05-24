"""Eval schemas for OpenMinion."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalTranscript:
    """A transcript for evaluation."""

    name: str
    turns: list[dict]  # [{"user": "...", "expected": "..."}]
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalResult:
    """Result of evaluating a single turn."""

    turn_index: int
    user_input: str
    expected: str
    actual: str
    score: float
    scorer_name: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalSummary:
    """Summary of evaluation results."""

    transcript_name: str
    total_turns: int
    average_score: float
    min_score: float
    max_score: float
    results: list[EvalResult]
    passed: bool
    threshold: float = 0.80


@dataclass
class EvalSuiteResult:
    """Result of running an eval suite."""

    suite_name: str
    total_transcripts: int
    passed_transcripts: int
    failed_transcripts: int
    summaries: list[EvalSummary]
    all_passed: bool
