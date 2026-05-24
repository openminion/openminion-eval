"""Eval scorer for OpenMinion."""

from dataclasses import replace
from typing import Callable, Optional
from openminion_eval.schemas import EvalResult
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION


class EvalScorer:
    """Scorer with pluggable scoring functions."""

    contract_version = EVAL_INTERFACE_VERSION
    _RESERVED_SCORER_NAMES = frozenset({"llm_judge"})

    def __init__(self) -> None:
        self._scorers: dict[str, Callable[[str, str], float]] = {
            "exact_match": self._exact_match,
            "substring_match": self._substring_match,
        }

    def _exact_match(self, actual: str, expected: str) -> float:
        """Score 1.0 if exact match, 0.0 otherwise."""
        return 1.0 if actual.strip() == expected.strip() else 0.0

    def _substring_match(self, actual: str, expected: str) -> float:
        """Score based on substring presence."""
        actual_lower = actual.lower()
        expected_lower = expected.lower()

        if expected_lower in actual_lower:
            # Calculate how much of expected is covered
            coverage = len(expected_lower) / max(len(actual_lower), 1)
            return min(coverage, 1.0)
        return 0.0

    def register_scorer(
        self,
        name: str,
        scorer: Callable[[str, str], float],
    ) -> None:
        """Register a custom scorer."""
        if name in self._RESERVED_SCORER_NAMES:
            raise ValueError(f"Reserved scorer name: {name}")
        self._scorers[name] = scorer

    def score(
        self,
        result: EvalResult,
        expected: Optional[str] = None,
        scorer_name: str = "substring_match",
    ) -> EvalResult:
        """
        Score an eval result.

        Args:
            result: The eval result to score.
            expected: Optional override for expected value.
            scorer_name: Name of the scorer to use.

        Returns:
            Updated EvalResult with score.
        """
        actual = result.actual
        exp = expected or result.expected

        scorer = self._scorers.get(scorer_name)
        if scorer is None:
            raise ValueError(f"Unknown scorer: {scorer_name}")
        score = scorer(actual, exp)

        return replace(result, score=score, scorer_name=scorer_name)

    def score_results(
        self,
        results: list[EvalResult],
        scorer_name: str = "substring_match",
    ) -> list[EvalResult]:
        """Score a list of results."""
        return [self.score(r, scorer_name=scorer_name) for r in results]
