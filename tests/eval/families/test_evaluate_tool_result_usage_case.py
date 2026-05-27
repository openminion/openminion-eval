from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.tools import (
    ToolResultUsageCase,
    ToolResultUsageObservation,
    build_tool_result_usage_report,
)
from openminion_eval.tools.result_usage import evaluate_tool_result_usage_case


def test_evaluate_tool_result_usage_case_passes_grounded_result() -> None:
    case = ToolResultUsageCase("case", "prompt", required_facts=("fact",))
    observation = ToolResultUsageObservation(
        cited_facts=("fact",), unsupported_claims=()
    )

    result = evaluate_tool_result_usage_case(case, observation)

    assert result.passed is True


def test_evaluate_tool_result_usage_case_records_all_fail_flags() -> None:
    case = ToolResultUsageCase(
        "case",
        "prompt",
        required_facts=("fact",),
        forbidden_claims=("bad",),
    )
    observation = ToolResultUsageObservation(
        cited_facts=(), unsupported_claims=("bad",)
    )

    result = evaluate_tool_result_usage_case(case, observation)

    assert result.passed is False
    assert result.metrics["grounded"] is False
    assert result.metrics["unsupported_clean"] is False


@pytest.mark.parametrize(
    ("observation", "metric", "expected_value"),
    [
        (
            ToolResultUsageObservation(cited_facts=(), unsupported_claims=()),
            "grounded",
            False,
        ),
        (
            ToolResultUsageObservation(
                cited_facts=("fact",), unsupported_claims=("bad",)
            ),
            "unsupported_clean",
            False,
        ),
    ],
)
def test_evaluate_tool_result_usage_case_fails_each_metric_independently(
    observation: ToolResultUsageObservation,
    metric: str,
    expected_value: bool,
) -> None:
    case = ToolResultUsageCase(
        "case",
        "prompt",
        required_facts=("fact",),
        forbidden_claims=("bad",),
    )

    result = evaluate_tool_result_usage_case(case, observation)

    assert result.passed is False
    assert result.metrics[metric] is expected_value


def test_tool_result_usage_report_raises_on_observation_case_id_mismatch() -> None:
    case = ToolResultUsageCase("expected", "prompt", required_facts=("fact",))

    with pytest.raises(MissingObservationError):
        build_tool_result_usage_report(
            cases=(case,),
            observations={
                "other": ToolResultUsageObservation(
                    cited_facts=("fact",),
                    unsupported_claims=(),
                )
            },
        )


def test_evaluate_tool_result_usage_case_accepts_empty_payload_values() -> None:
    case = ToolResultUsageCase("", "", required_facts=())
    result = evaluate_tool_result_usage_case(
        case,
        ToolResultUsageObservation(cited_facts=(), unsupported_claims=()),
    )

    assert result.passed is True
