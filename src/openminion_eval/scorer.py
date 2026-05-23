"""Eval scorer for OpenMinion."""

import re
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

        result.score = score
        result.scorer_name = scorer_name
        return result

    def score_results(
        self,
        results: list[EvalResult],
        scorer_name: str = "substring_match",
    ) -> list[EvalResult]:
        """Score a list of results."""
        return [self.score(r, scorer_name=scorer_name) for r in results]


class MemoryEvalScorer:
    """Memory-specific scoring helpers for fixture-driven evals."""

    _NEGATION_TOKENS = {
        "avoid",
        "cant",
        "can't",
        "cannot",
        "disable",
        "disabled",
        "dont",
        "don't",
        "forbid",
        "forbidden",
        "never",
        "no",
        "not",
        "skip",
        "stop",
        "without",
    }
    _DISCOURSE_TOKENS = {
        "actually",
        "current",
        "now",
        "updated",
    }
    _FUNCTION_TOKENS = {
        "a",
        "an",
        "and",
        "are",
        "be",
        "been",
        "being",
        "for",
        "in",
        "is",
        "of",
        "on",
        "or",
        "the",
        "this",
        "that",
        "to",
        "was",
        "were",
        "with",
    }

    @staticmethod
    def recall_at_k(retrieved: list[str], ground_truth: list[str], k: int) -> float:
        """Fraction of ground-truth items found in top-k retrieved strings."""
        if not ground_truth:
            return 1.0
        top_k = [item.lower() for item in retrieved[: max(1, int(k))]]
        hits = 0
        for item in ground_truth:
            normalized = str(item or "").lower().strip()
            if normalized and any(normalized in candidate for candidate in top_k):
                hits += 1
        return float(hits) / float(len(ground_truth))

    @staticmethod
    def precision_at_k(retrieved: list[str], ground_truth: list[str], k: int) -> float:
        """Fraction of top-k retrieved strings that match ground truth."""
        top_k = [item.lower() for item in retrieved[: max(1, int(k))]]
        if not top_k:
            return 0.0
        normalized_truth = [str(item or "").lower().strip() for item in ground_truth]
        hits = 0
        for candidate in top_k:
            if any(truth and truth in candidate for truth in normalized_truth):
                hits += 1
        return float(hits) / float(len(top_k))

    @staticmethod
    def substring_recall(text: str, required: list[str]) -> float:
        """Fraction of required substrings found in text."""
        if not required:
            return 1.0
        haystack = str(text or "").lower()
        hits = 0
        for item in required:
            normalized = str(item or "").lower().strip()
            if normalized and normalized in haystack:
                hits += 1
        return float(hits) / float(len(required))

    @staticmethod
    def contradiction_leak_count(capsule_text: str, superseded_items: list[str]) -> int:
        """Count superseded items that still appear in the capsule text."""
        haystack = str(capsule_text or "").lower()
        segments = MemoryEvalScorer._segments(capsule_text)
        return sum(
            1
            for item in superseded_items
            if (normalized := str(item or "").lower().strip())
            and normalized in haystack
            and not MemoryEvalScorer._has_contradicting_resolution(
                segments=segments,
                superseded_item=normalized,
            )
        )

    @staticmethod
    def _segments(text: str) -> list[str]:
        return [
            segment.strip()
            for segment in re.split(r"[\n\r]+", str(text or "").lower())
            if segment.strip()
        ]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r"[a-z0-9']+", str(text or "").lower())

    @staticmethod
    def _polarity(tokens: list[str]) -> int:
        return (
            -1
            if any(token in MemoryEvalScorer._NEGATION_TOKENS for token in tokens)
            else 1
        )

    @staticmethod
    def _core_tokens(tokens: list[str]) -> set[str]:
        return {
            token
            for token in tokens
            if token not in MemoryEvalScorer._NEGATION_TOKENS
            and token not in MemoryEvalScorer._DISCOURSE_TOKENS
            and token not in MemoryEvalScorer._FUNCTION_TOKENS
        }

    @staticmethod
    def _has_contradicting_resolution(
        *,
        segments: list[str],
        superseded_item: str,
    ) -> bool:
        superseded_tokens = MemoryEvalScorer._tokenize(superseded_item)
        superseded_core = MemoryEvalScorer._core_tokens(superseded_tokens)
        if not superseded_core:
            return False
        superseded_polarity = MemoryEvalScorer._polarity(superseded_tokens)
        for segment in segments:
            if segment == superseded_item:
                continue
            candidate_tokens = MemoryEvalScorer._tokenize(segment)
            if not candidate_tokens:
                continue
            candidate_polarity = MemoryEvalScorer._polarity(candidate_tokens)
            if candidate_polarity == superseded_polarity:
                continue
            candidate_core = MemoryEvalScorer._core_tokens(candidate_tokens)
            if not candidate_core:
                continue
            overlap = len(candidate_core & superseded_core) / float(
                len(superseded_core)
            )
            if overlap >= 0.75:
                return True
        return False

    @staticmethod
    def latency_gate(measurement_ms: float, p95_bound_ms: float) -> bool:
        """Return True when the measurement stays within the requested bound."""
        return float(measurement_ms) <= float(p95_bound_ms)

    @staticmethod
    def capsule_precision(
        capsule_text: str,
        relevance_labels: dict[str, str],
    ) -> tuple[float, float]:
        """Return capsule precision and noise rate from substring labels."""
        haystack = str(capsule_text or "").lower()
        surfaced_relevant = 0
        surfaced_irrelevant = 0
        total_surfaced = 0
        for label, state in relevance_labels.items():
            normalized = str(label or "").lower().strip()
            if not normalized or normalized not in haystack:
                continue
            total_surfaced += 1
            if str(state).lower().strip() == "relevant":
                surfaced_relevant += 1
            else:
                surfaced_irrelevant += 1
        if total_surfaced == 0:
            return 0.0, 0.0
        precision = float(surfaced_relevant) / float(total_surfaced)
        noise_rate = float(surfaced_irrelevant) / float(total_surfaced)
        return precision, noise_rate
