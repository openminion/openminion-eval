"""Eval scorer for OpenMinion."""

from dataclasses import dataclass, replace
from typing import Callable, Optional, Sequence
from openminion_eval.schemas import EvalResult
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION


@dataclass(frozen=True)
class EvalScorerSpec:
    name: str
    threshold: float | None = None


@dataclass(frozen=True)
class EvalScorerInfo:
    name: str
    description: str
    reserved: bool = False


class EvalScorer:
    """Scorer with pluggable scoring functions."""

    contract_version = EVAL_INTERFACE_VERSION
    _RESERVED_SCORER_NAMES = frozenset({"llm_judge"})

    def __init__(self) -> None:
        self._scorers: dict[str, Callable[[str, str], float]] = {
            "exact_match": self._exact_match,
            "substring_match": self._substring_match,
        }
        self._descriptions = {
            "exact_match": "Scores 1.0 when actual text exactly matches expected text after trimming.",
            "substring_match": "Scores 1.0 when expected text appears inside actual text.",
        }

    def _exact_match(self, actual: str, expected: str) -> float:
        return 1.0 if actual.strip() == expected.strip() else 0.0

    def _substring_match(self, actual: str, expected: str) -> float:
        """Score 1.0 when the expected text appears, 0.0 otherwise."""
        actual_lower = actual.lower()
        expected_lower = expected.lower()
        return 1.0 if expected_lower in actual_lower else 0.0

    def register_scorer(
        self,
        name: str,
        scorer: Callable[[str, str], float],
        *,
        description: str = "Custom scorer registered by the host application.",
    ) -> None:
        if name in self._RESERVED_SCORER_NAMES:
            raise ValueError(f"Reserved scorer name: {name}")
        self._scorers[name] = scorer
        self._descriptions[name] = description

    def list_scorers(self) -> tuple[EvalScorerInfo, ...]:
        names = sorted(self._scorers)
        return tuple(
            EvalScorerInfo(
                name=name,
                description=self._descriptions.get(name, ""),
                reserved=name in self._RESERVED_SCORER_NAMES,
            )
            for name in names
        )

    def score(
        self,
        result: EvalResult,
        expected: Optional[str] = None,
        scorer_name: str = "substring_match",
        threshold: float | None = None,
    ) -> EvalResult:
        actual = result.actual
        exp = expected or result.expected

        scorer = self._scorers.get(scorer_name)
        if scorer is None:
            raise ValueError(f"Unknown scorer: {scorer_name}")
        score = scorer(actual, exp)
        reason_threshold = 1.0 if threshold is None else threshold
        reason = "passed" if score >= reason_threshold else "failed"

        return replace(
            result,
            score=score,
            scorer_name=scorer_name,
            scorer_reason=reason,
            scorer_threshold=threshold,
        )

    def score_results(
        self,
        results: list[EvalResult],
        scorer_name: str = "substring_match",
        threshold: float | None = None,
    ) -> list[EvalResult]:
        return [
            self.score(r, scorer_name=scorer_name, threshold=threshold) for r in results
        ]

    def score_with_scorers(
        self,
        result: EvalResult,
        scorers: Sequence[EvalScorerSpec],
        *,
        expected: Optional[str] = None,
    ) -> list[EvalResult]:
        return [
            self.score(
                result,
                expected=expected,
                scorer_name=scorer.name,
                threshold=scorer.threshold,
            )
            for scorer in scorers
        ]
