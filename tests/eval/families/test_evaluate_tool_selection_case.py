from __future__ import annotations

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.tools import (
    ToolSelectionCase,
    ToolSelectionObservation,
    build_tool_selection_report,
)
from openminion_eval.tools.selection import evaluate_tool_selection_case


def test_evaluate_tool_selection_case_passes_expected_family() -> None:
    case = ToolSelectionCase("case", "prompt", "search")
    observation = ToolSelectionObservation("search", ("search",))

    result = evaluate_tool_selection_case(case, observation)

    assert result.passed is True


def test_evaluate_tool_selection_case_records_all_fail_flags() -> None:
    case = ToolSelectionCase(
        "case",
        "prompt",
        "search",
        forbidden_families=("forbidden",),
    )
    observation = ToolSelectionObservation("weather", ("weather", "forbidden"))

    result = evaluate_tool_selection_case(case, observation)

    assert result.passed is False
    assert result.metrics["correct_family"] is False
    assert result.metrics["forbidden_family_hit"] is True


@pytest.mark.parametrize(
    ("case", "observation", "metric", "expected_value"),
    [
        (
            ToolSelectionCase("case", "prompt", "search"),
            ToolSelectionObservation("weather", ("weather",)),
            "correct_family",
            False,
        ),
        (
            ToolSelectionCase("case", "prompt", "search"),
            ToolSelectionObservation(None, ()),
            "missing_tool",
            True,
        ),
        (
            ToolSelectionCase("case", "prompt", "", allowed_no_tool=True),
            ToolSelectionObservation("search", ("search",)),
            "unnecessary_tool",
            True,
        ),
        (
            ToolSelectionCase(
                "case",
                "prompt",
                "search",
                forbidden_families=("weather",),
            ),
            ToolSelectionObservation("search", ("search", "weather")),
            "forbidden_family_hit",
            True,
        ),
    ],
)
def test_evaluate_tool_selection_case_fails_each_metric_independently(
    case: ToolSelectionCase,
    observation: ToolSelectionObservation,
    metric: str,
    expected_value: bool,
) -> None:
    result = evaluate_tool_selection_case(case, observation)

    assert result.passed is False
    assert result.metrics[metric] is expected_value


def test_tool_selection_report_raises_on_observation_case_id_mismatch() -> None:
    case = ToolSelectionCase("expected", "prompt", "search")

    with pytest.raises(MissingObservationError):
        build_tool_selection_report(
            cases=(case,),
            observations={"other": ToolSelectionObservation("search", ("search",))},
        )


def test_evaluate_tool_selection_case_accepts_empty_payload_values() -> None:
    case = ToolSelectionCase("", "", "", allowed_no_tool=True)
    result = evaluate_tool_selection_case(case, ToolSelectionObservation(None, ()))

    assert result.passed is True
