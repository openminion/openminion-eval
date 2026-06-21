from __future__ import annotations

import pytest

from openminion_eval import EvalRunner, EvalSuite
from openminion_eval.schemas import EvalTranscript


def test_custom_subject_scorer_threshold_passes() -> None:
    transcript = EvalTranscript(
        name="math",
        turns=[{"user": "2 + 2", "expected": "4"}],
        tags=["ci"],
    )
    suite = EvalSuite(
        runner=EvalRunner(agent_executor=lambda _prompt: "4"),
        threshold=1.0,
    )

    result = suite.run([transcript], scorer_name="exact_match")

    assert result.all_passed is True


def test_baseline_diff_failure_text_is_deterministic() -> None:
    transcript = EvalTranscript(
        name="regression",
        turns=[{"user": "2 + 2", "expected": "4"}],
        tags=["ci"],
    )
    suite = EvalSuite(
        runner=EvalRunner(agent_executor=lambda _prompt: "5"),
        threshold=1.0,
    )

    result = suite.run([transcript], scorer_name="exact_match")

    with pytest.raises(AssertionError, match="regression failed threshold"):
        assert result.all_passed is True, "regression failed threshold"
