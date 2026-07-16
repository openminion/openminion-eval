"""Eval schemas for OpenMinion."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EvalTranscript:
    name: str
    turns: list[dict]  # [{"user": "...", "expected": "..."}]
    tags: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvalDatasetCase:
    case_id: str
    transcript: EvalTranscript


@dataclass(frozen=True)
class EvalDataset:
    dataset_version: str
    name: str
    cases: list[EvalDatasetCase]
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def transcripts(self) -> list[EvalTranscript]:
        return [case.transcript for case in self.cases]


@dataclass(frozen=True)
class RedTeamSecurityFixture:
    fixture_id: str
    category: str
    prompt: str
    expected_behavior: str
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RedTeamSecurityResult:
    fixture_id: str
    outcome: str
    observed_behavior: str
    score: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RedTeamSecurityArtifact:
    artifact_version: str
    name: str
    fixtures: list[RedTeamSecurityFixture]
    results: list[RedTeamSecurityResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyntheticGoldenProvenance:
    source: str
    generated_by: str
    generated_at: str
    generation_method: str
    source_artifact_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyntheticGolden:
    golden_id: str
    input: str
    expected_output: str
    provenance: SyntheticGoldenProvenance
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class SyntheticGoldenArtifact:
    artifact_version: str
    name: str
    goldens: list[SyntheticGolden]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalResult:
    turn_index: int
    user_input: str
    expected: str
    actual: str
    score: float
    scorer_name: str
    scorer_reason: str = ""
    scorer_threshold: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EvalCaseTrace:
    transcript_name: str
    turn_index: int
    user_input: str
    actual: str
    expected: str
    duration_ms: float
    executor_error: str | None
    scorer_name: str
    score: float
    scorer_reason: str = ""
    scorer_threshold: float | None = None


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
