"""Eval suite for OpenMinion."""

from typing import Any, Callable, Optional
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION
from openminion_eval.schemas import (
    EvalResult,
    EvalTranscript,
    EvalSummary,
    EvalSuiteResult,
)
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer


class EvalSuite:
    """Run transcripts and aggregate scores."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        runner: Optional[EvalRunner] = None,
        scorer: Optional[EvalScorer] = None,
        threshold: float = 0.80,
        subject: Any | None = None,
        run_id: str | None = None,
        seed: int | None = None,
        deterministic: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._runner = runner or EvalRunner(
            subject=subject,
            run_id=run_id,
            seed=seed,
            deterministic=deterministic,
            metadata=metadata,
        )
        self._scorer = scorer or EvalScorer()
        self._threshold = threshold

    def run(
        self,
        transcripts: list[EvalTranscript],
        scorer_name: str = "substring_match",
        on_case: Callable[[EvalResult], None] | None = None,
    ) -> EvalSuiteResult:
        summaries = []

        for transcript in transcripts:
            results = self._runner.replay_sync(transcript)
            results = self._scorer.score_results(results, scorer_name)
            for result in results:
                if on_case is not None:
                    on_case(result)

            scores = [r.score for r in results]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            scorer_error_count = sum(
                1
                for result in results
                if result.metadata.get("executor_error") is not None
            )

            summary = EvalSummary(
                transcript_name=transcript.name,
                total_turns=len(results),
                average_score=avg_score,
                min_score=min(scores) if scores else 0.0,
                max_score=max(scores) if scores else 0.0,
                results=results,
                passed=avg_score >= self._threshold,
                threshold=self._threshold,
                scorer_error_count=scorer_error_count,
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

    async def run_async(
        self,
        transcripts: list[EvalTranscript],
        scorer_name: str = "substring_match",
        on_case: Callable[[EvalResult], None] | None = None,
    ) -> EvalSuiteResult:
        summaries = []

        for transcript in transcripts:
            results = await self._runner.replay(transcript)
            results = self._scorer.score_results(results, scorer_name)
            for result in results:
                if on_case is not None:
                    on_case(result)

            scores = [r.score for r in results]
            avg_score = sum(scores) / len(scores) if scores else 0.0
            scorer_error_count = sum(
                1
                for result in results
                if result.metadata.get("executor_error") is not None
            )

            summaries.append(
                EvalSummary(
                    transcript_name=transcript.name,
                    total_turns=len(results),
                    average_score=avg_score,
                    min_score=min(scores) if scores else 0.0,
                    max_score=max(scores) if scores else 0.0,
                    results=results,
                    passed=avg_score >= self._threshold,
                    threshold=self._threshold,
                    scorer_error_count=scorer_error_count,
                )
            )

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
