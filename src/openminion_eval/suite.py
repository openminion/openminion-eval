"""Eval suite for OpenMinion."""

from typing import Optional
from openminion_eval.schemas import (
    EvalTranscript,
    EvalSummary,
    EvalSuiteResult,
)
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION


class EvalSuite:
    """Suite that runs N transcripts and aggregates scores."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        runner: Optional[EvalRunner] = None,
        scorer: Optional[EvalScorer] = None,
        threshold: float = 0.80,
    ) -> None:
        self._runner = runner or EvalRunner()
        self._scorer = scorer or EvalScorer()
        self._threshold = threshold

    def run(
        self,
        transcripts: list[EvalTranscript],
        scorer_name: str = "substring_match",
    ) -> EvalSuiteResult:
        """
        Run evaluation on multiple transcripts.

        Args:
            transcripts: List of transcripts to evaluate.
            scorer_name: Name of scorer to use.

        Returns:
            EvalSuiteResult with aggregated results.
        """
        summaries = []

        for transcript in transcripts:
            # Replay transcript
            results = self._runner.replay_sync(transcript)

            # Score results
            results = self._scorer.score_results(results, scorer_name)

            # Calculate summary
            scores = [r.score for r in results]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            summary = EvalSummary(
                transcript_name=transcript.name,
                total_turns=len(results),
                average_score=avg_score,
                min_score=min(scores) if scores else 0.0,
                max_score=max(scores) if scores else 0.0,
                results=results,
                passed=avg_score >= self._threshold,
                threshold=self._threshold,
            )
            summaries.append(summary)

        passed = sum(1 for s in summaries if s.passed)

        return EvalSuiteResult(
            suite_name="default",
            total_transcripts=len(transcripts),
            passed_transcripts=passed,
            failed_transcripts=len(transcripts) - passed,
            summaries=summaries,
            all_passed=passed == len(transcripts),
        )

    def run_single(
        self,
        transcript: EvalTranscript,
        scorer_name: str = "substring_match",
    ) -> EvalSummary:
        """Run evaluation on a single transcript."""
        result = self.run([transcript], scorer_name)
        return result.summaries[0]


def load_golden_transcripts(path: str) -> list[EvalTranscript]:
    """Load golden transcripts from a directory."""
    import json
    from pathlib import Path
    from openminion_eval.schemas import EvalTranscript

    transcripts = []
    transcripts_dir = Path(path)

    if not transcripts_dir.exists():
        return []

    for file in transcripts_dir.glob("*.json"):
        with open(file) as f:
            data = json.load(f)
            transcripts.append(
                EvalTranscript(
                    name=data.get("name", file.stem),
                    turns=data.get("turns", []),
                    tags=data.get("tags", []),
                )
            )

    return transcripts
