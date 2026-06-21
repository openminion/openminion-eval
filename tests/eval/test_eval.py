"""Tests for openminion-eval."""

from time import sleep

import pytest

from openminion_eval.config import EvalConfig, load_config
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION, EvalRunContext
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer
from openminion_eval.suite import EvalSuite, select_transcripts
from openminion_eval.schemas import (
    EvalTranscript,
    EvalResult,
    EvalSuiteResult,
    EvalSummary,
)


def test_eval_runner_replay():
    runner = EvalRunner()
    transcript = EvalTranscript(
        name="test",
        turns=[
            {"user": "Hello", "expected": "Hi there!"},
            {"user": "How are you?", "expected": "I'm doing well."},
            {"user": "Goodbye", "expected": "See you later!"},
        ],
        tags=["basic"],
    )

    results = runner.replay_sync(transcript)

    assert len(results) == 3
    assert results[0].user_input == "Hello"
    assert results[1].user_input == "How are you?"
    assert results[2].user_input == "Goodbye"


def test_eval_scorer_exact_match():
    scorer = EvalScorer()

    result = EvalResult(
        turn_index=0,
        user_input="Hello",
        expected="Hello",
        actual="Hello",
        score=0.0,
        scorer_name="pending",
    )

    scored = scorer.score(result, scorer_name="exact_match")
    assert scored.score == 1.0
    assert scored.scorer_name == "exact_match"
    assert result.score == 0.0
    assert result.scorer_name == "pending"


def test_eval_scorer_exact_match_fail():
    scorer = EvalScorer()

    result = EvalResult(
        turn_index=0,
        user_input="Hello",
        expected="Hello",
        actual="Goodbye",
        score=0.0,
        scorer_name="pending",
    )

    scored = scorer.score(result, scorer_name="exact_match")
    assert scored.score == 0.0


def test_eval_scorer_substring_match():
    scorer = EvalScorer()

    result = EvalResult(
        turn_index=0,
        user_input="Hello",
        expected="Hello world",
        actual="Hello world, how are you?",
        score=0.0,
        scorer_name="pending",
    )

    scored = scorer.score(result, scorer_name="substring_match")
    assert scored.score > 0.0


def test_eval_suite_run():
    suite = EvalSuite(threshold=0.80)
    transcripts = [
        EvalTranscript(
            name="basic_qna",
            turns=[
                {"user": "What is 2+2?", "expected": "4"},
            ],
            tags=["basic"],
        ),
    ]

    result = suite.run(transcripts, scorer_name="substring_match")

    assert result.total_transcripts == 1
    assert len(result.summaries) == 1
    assert result.summaries[0].total_turns == 1


def test_eval_suite_threshold():
    suite = EvalSuite(threshold=0.80)
    transcript = EvalTranscript(
        name="test",
        turns=[
            {"user": "Hello", "expected": "xyz"},
        ],
    )

    result = suite.run([transcript], scorer_name="exact_match")

    assert result.failed_transcripts == 1


def _summary(name: str, passed: bool) -> EvalSummary:
    return EvalSummary(
        transcript_name=name,
        total_turns=1,
        average_score=1.0 if passed else 0.0,
        min_score=1.0 if passed else 0.0,
        max_score=1.0 if passed else 0.0,
        results=[],
        passed=passed,
    )


def _suite_result(summaries: list[EvalSummary]) -> EvalSuiteResult:
    passed = sum(1 for summary in summaries if summary.passed)
    return EvalSuiteResult(
        suite_name="previous",
        total_transcripts=len(summaries),
        passed_transcripts=passed,
        failed_transcripts=len(summaries) - passed,
        summaries=summaries,
        all_passed=passed == len(summaries),
    )


def test_eval_suite_parallel_preserves_input_order_and_error_metadata() -> None:
    class TimedSubject:
        contract_version = EVAL_INTERFACE_VERSION

        def run(self, user_input: str, context: EvalRunContext) -> str:
            if user_input == "slow":
                sleep(0.02)
            if user_input == "boom":
                raise RuntimeError("subject failed")
            return f"{context.transcript_name}:{user_input}"

    suite = EvalSuite(subject=TimedSubject(), threshold=1.0)
    transcripts = [
        EvalTranscript(
            name="slow_case",
            turns=[{"user": "slow", "expected": "slow_case:slow"}],
        ),
        EvalTranscript(
            name="fast_case",
            turns=[{"user": "fast", "expected": "fast_case:fast"}],
        ),
        EvalTranscript(
            name="error_case",
            turns=[{"user": "boom", "expected": "error_case:boom"}],
        ),
    ]

    result = suite.run(transcripts, scorer_name="exact_match", max_workers=3)

    assert [summary.transcript_name for summary in result.summaries] == [
        "slow_case",
        "fast_case",
        "error_case",
    ]
    assert result.summaries[0].passed is True
    assert result.summaries[1].passed is True
    error_result = result.summaries[2].results[0]
    assert error_result.metadata["executor_error"] == "subject failed"
    assert result.summaries[2].scorer_error_count == 1


def test_select_transcripts_failed_only_preserves_order() -> None:
    transcripts = [
        EvalTranscript(name="first", turns=[]),
        EvalTranscript(name="second", turns=[]),
        EvalTranscript(name="third", turns=[]),
    ]
    previous = _suite_result(
        [
            _summary("third", passed=False),
            _summary("first", passed=True),
            _summary("second", passed=False),
        ]
    )

    selected = select_transcripts(
        transcripts, previous_result=previous, failed_only=True
    )

    assert [transcript.name for transcript in selected] == ["second", "third"]


def test_eval_suite_partial_rerun_name_and_tag_filters() -> None:
    suite = EvalSuite(threshold=0.0)
    transcripts = [
        EvalTranscript(name="alpha", turns=[], tags=["fast", "public"]),
        EvalTranscript(name="beta", turns=[], tags=["retry", "public"]),
        EvalTranscript(name="gamma", turns=[], tags=["retry", "slow"]),
        EvalTranscript(name="delta", turns=[], tags=["retry", "public"]),
    ]
    previous = _suite_result(
        [
            _summary("alpha", passed=True),
            _summary("beta", passed=False),
            _summary("gamma", passed=False),
            _summary("delta", passed=False),
        ]
    )

    result = suite.run(
        transcripts,
        previous_result=previous,
        failed_only=True,
        include_tags=["retry"],
        exclude_tags=["slow"],
        exclude_names=["delta"],
    )

    assert [summary.transcript_name for summary in result.summaries] == ["beta"]


def test_select_transcripts_failed_only_requires_previous_result() -> None:
    with pytest.raises(ValueError, match="previous_result is required"):
        select_transcripts([EvalTranscript(name="case", turns=[])], failed_only=True)


def test_custom_scorer():
    scorer = EvalScorer()

    def custom_scorer(actual: str, expected: str) -> float:
        return 0.95

    scorer.register_scorer("custom", custom_scorer)

    result = EvalResult(
        turn_index=0,
        user_input="test",
        expected="expected",
        actual="actual",
        score=0.0,
        scorer_name="pending",
    )

    scored = scorer.score(result, scorer_name="custom")
    assert scored.score == 0.95


def test_eval_scorer_rejects_reserved_llm_judge_registration() -> None:
    scorer = EvalScorer()

    with pytest.raises(ValueError, match="Reserved scorer name: llm_judge"):
        scorer.register_scorer("llm_judge", lambda actual, expected: 1.0)


def test_eval_scorer_rejects_removed_llm_judge_path() -> None:
    scorer = EvalScorer()
    result = EvalResult(
        turn_index=0,
        user_input="test",
        expected="expected",
        actual="actual",
        score=0.0,
        scorer_name="pending",
    )

    with pytest.raises(ValueError, match="Unknown scorer: llm_judge"):
        scorer.score(result, scorer_name="llm_judge")


def test_load_config_returns_noop_compatibility_surface() -> None:
    config = load_config("ignored", key="ignored")

    assert isinstance(config, EvalConfig)
    assert config == EvalConfig()
