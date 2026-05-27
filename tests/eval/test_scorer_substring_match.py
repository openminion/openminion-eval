from __future__ import annotations

from openminion_eval.schemas import EvalResult
from openminion_eval.scorer import EvalScorer


def _result(*, actual: str, expected: str) -> EvalResult:
    return EvalResult(
        turn_index=0,
        user_input="test",
        expected=expected,
        actual=actual,
        score=0.0,
        scorer_name="pending",
    )


def test_substring_match_scores_full_credit_for_expected_substring() -> None:
    scorer = EvalScorer()

    scored = scorer.score(
        _result(actual="The answer is 4.", expected="4"),
        scorer_name="substring_match",
    )

    assert scored.score == 1.0


def test_substring_match_scores_zero_when_expected_text_is_absent() -> None:
    scorer = EvalScorer()

    scored = scorer.score(
        _result(actual="No four here", expected="4"),
        scorer_name="substring_match",
    )

    assert scored.score == 0.0


def test_substring_match_is_case_insensitive() -> None:
    scorer = EvalScorer()

    scored = scorer.score(
        _result(actual="Result: SUCCESS", expected="success"),
        scorer_name="substring_match",
    )

    assert scored.score == 1.0
