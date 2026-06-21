"""Eval suite for OpenMinion."""

from concurrent.futures import ThreadPoolExecutor
import asyncio
from typing import Any, Callable, Optional, Sequence
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION
from openminion_eval.schemas import (
    EvalResult,
    EvalTranscript,
    EvalSummary,
    EvalSuiteResult,
)
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer


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
        max_workers: int | None = None,
        previous_result: EvalSuiteResult | None = None,
        failed_only: bool = False,
        include_names: Sequence[str] | None = None,
        exclude_names: Sequence[str] | None = None,
        include_tags: Sequence[str] | None = None,
        exclude_tags: Sequence[str] | None = None,
    ) -> EvalSuiteResult:
        selected = select_transcripts(
            transcripts,
            previous_result=previous_result,
            failed_only=failed_only,
            include_names=include_names,
            exclude_names=exclude_names,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
        )
        if max_workers is not None and max_workers > 1:
            summaries = self._run_parallel(
                selected,
                scorer_name=scorer_name,
                on_case=on_case,
                max_workers=max_workers,
            )
        else:
            summaries = [
                self._run_transcript_sync(
                    transcript,
                    scorer_name=scorer_name,
                    on_case=on_case,
                )
                for transcript in selected
            ]
        return self._suite_result(summaries)

    def _run_parallel(
        self,
        transcripts: list[EvalTranscript],
        *,
        scorer_name: str,
        on_case: Callable[[EvalResult], None] | None,
        max_workers: int,
    ) -> list[EvalSummary]:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [
                executor.submit(
                    self._run_transcript_sync,
                    transcript,
                    scorer_name=scorer_name,
                    on_case=None,
                )
                for transcript in transcripts
            ]
            summaries = []
            for transcript, future in zip(transcripts, futures):
                try:
                    summary = future.result()
                except Exception as exc:  # noqa: BLE001
                    summary = self._error_summary(
                        transcript,
                        scorer_name=scorer_name,
                        error=exc,
                        on_case=None,
                    )
                if on_case is not None:
                    for result in summary.results:
                        on_case(result)
                summaries.append(summary)
        return summaries

    def _run_transcript_sync(
        self,
        transcript: EvalTranscript,
        *,
        scorer_name: str,
        on_case: Callable[[EvalResult], None] | None,
    ) -> EvalSummary:
        try:
            results = self._runner.replay_sync(transcript)
            results = self._scorer.score_results(
                results,
                scorer_name,
                threshold=self._threshold,
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_summary(
                transcript,
                scorer_name=scorer_name,
                error=exc,
                on_case=on_case,
            )
        return self._summary_from_results(
            transcript_name=transcript.name,
            results=results,
            on_case=on_case,
        )

    def _suite_result(self, summaries: list[EvalSummary]) -> EvalSuiteResult:
        passed = sum(1 for s in summaries if s.passed)
        return EvalSuiteResult(
            suite_name="default",
            total_transcripts=len(summaries),
            passed_transcripts=passed,
            failed_transcripts=len(summaries) - passed,
            summaries=summaries,
            all_passed=passed == len(summaries),
        )

    async def run_async(
        self,
        transcripts: list[EvalTranscript],
        scorer_name: str = "substring_match",
        on_case: Callable[[EvalResult], None] | None = None,
        max_concurrency: int | None = None,
        previous_result: EvalSuiteResult | None = None,
        failed_only: bool = False,
        include_names: Sequence[str] | None = None,
        exclude_names: Sequence[str] | None = None,
        include_tags: Sequence[str] | None = None,
        exclude_tags: Sequence[str] | None = None,
    ) -> EvalSuiteResult:
        selected = select_transcripts(
            transcripts,
            previous_result=previous_result,
            failed_only=failed_only,
            include_names=include_names,
            exclude_names=exclude_names,
            include_tags=include_tags,
            exclude_tags=exclude_tags,
        )
        if max_concurrency is not None and max_concurrency > 1:
            semaphore = asyncio.Semaphore(max_concurrency)

            async def run_one(transcript: EvalTranscript) -> EvalSummary:
                async with semaphore:
                    return await self._run_transcript_async(
                        transcript,
                        scorer_name=scorer_name,
                        on_case=None,
                    )

            summaries = await asyncio.gather(
                *(run_one(transcript) for transcript in selected)
            )
            if on_case is not None:
                for summary in summaries:
                    for result in summary.results:
                        on_case(result)
        else:
            summaries = []
            for transcript in selected:
                summaries.append(
                    await self._run_transcript_async(
                        transcript,
                        scorer_name=scorer_name,
                        on_case=on_case,
                    )
                )
        return self._suite_result(list(summaries))

    async def _run_transcript_async(
        self,
        transcript: EvalTranscript,
        *,
        scorer_name: str,
        on_case: Callable[[EvalResult], None] | None,
    ) -> EvalSummary:
        try:
            results = await self._runner.replay(transcript)
            results = self._scorer.score_results(
                results,
                scorer_name,
                threshold=self._threshold,
            )
        except Exception as exc:  # noqa: BLE001
            return self._error_summary(
                transcript,
                scorer_name=scorer_name,
                error=exc,
                on_case=on_case,
            )
        return self._summary_from_results(
            transcript_name=transcript.name,
            results=results,
            on_case=on_case,
        )

    def _summary_from_results(
        self,
        *,
        transcript_name: str,
        results: list[EvalResult],
        on_case: Callable[[EvalResult], None] | None,
    ) -> EvalSummary:
        for result in results:
            if on_case is not None:
                on_case(result)

        scores = [r.score for r in results]
        avg_score = sum(scores) / len(scores) if scores else 0.0
        scorer_error_count = sum(
            1 for result in results if result.metadata.get("executor_error") is not None
        )
        return EvalSummary(
            transcript_name=transcript_name,
            total_turns=len(results),
            average_score=avg_score,
            min_score=min(scores) if scores else 0.0,
            max_score=max(scores) if scores else 0.0,
            results=results,
            passed=avg_score >= self._threshold,
            threshold=self._threshold,
            scorer_error_count=scorer_error_count,
        )

    def _error_summary(
        self,
        transcript: EvalTranscript,
        *,
        scorer_name: str,
        error: Exception,
        on_case: Callable[[EvalResult], None] | None,
    ) -> EvalSummary:
        first_turn = transcript.turns[0] if transcript.turns else {}
        result = EvalResult(
            turn_index=0,
            user_input=str(first_turn.get("user", "")),
            expected=str(first_turn.get("expected", "")),
            actual="",
            score=0.0,
            scorer_name=scorer_name,
            scorer_reason="failed",
            scorer_threshold=self._threshold,
            metadata={
                "duration_ms": 0.001,
                "executor_error": str(error),
            },
        )
        return self._summary_from_results(
            transcript_name=transcript.name,
            results=[result],
            on_case=on_case,
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
