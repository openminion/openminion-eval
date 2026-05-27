from __future__ import annotations

from openminion_eval.tools import (
    ToolResultUsageCase,
    ToolResultUsageObservation,
)
from openminion_eval.tools.result_usage import evaluate_tool_result_usage_case


def test_only_forbidden_unsupported_claims_fail_result_usage() -> None:
    case = ToolResultUsageCase(
        case_id="case",
        prompt="prompt",
        required_facts=("fact",),
        forbidden_claims=("x",),
    )
    observation = ToolResultUsageObservation(
        cited_facts=("fact",),
        unsupported_claims=("y",),
    )

    result = evaluate_tool_result_usage_case(case, observation)

    assert result.passed is True
    assert result.metrics["unsupported_clean"] is True
    assert result.metrics["forbidden_hits"] == ()
