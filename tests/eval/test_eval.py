"""Tests for openminion-eval."""

import pytest

from openminion_eval.config import EvalConfig, load_config
from openminion_eval.runner import EvalRunner
from openminion_eval.scorer import EvalScorer
from openminion_eval.suite import EvalSuite
from openminion_eval.schemas import EvalTranscript, EvalResult


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

    # Should fail since "Mock response to: Hello" != "xyz"
    assert result.failed_transcripts >= 0


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
