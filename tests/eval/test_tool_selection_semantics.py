from __future__ import annotations

import pytest

from openminion_eval.tools import (
    ToolSelectionCase,
    ToolSelectionObservation,
)
from openminion_eval.tools.selection import evaluate_tool_selection_case


@pytest.mark.parametrize(
    ("expected_family", "allowed_no_tool", "observation", "passed"),
    [
        (
            "search",
            False,
            ToolSelectionObservation("search", ("search",)),
            True,
        ),
        (
            "search",
            True,
            ToolSelectionObservation("search", ("search",)),
            True,
        ),
        (
            "search",
            True,
            ToolSelectionObservation(None, ()),
            False,
        ),
        (
            "",
            True,
            ToolSelectionObservation(None, ()),
            True,
        ),
        (
            "",
            True,
            ToolSelectionObservation("search", ("search",)),
            False,
        ),
    ],
)
def test_allowed_no_tool_truth_table(
    expected_family: str,
    allowed_no_tool: bool,
    observation: ToolSelectionObservation,
    passed: bool,
) -> None:
    case = ToolSelectionCase(
        case_id="case",
        prompt="prompt",
        expected_family=expected_family,
        allowed_no_tool=allowed_no_tool,
    )

    result = evaluate_tool_selection_case(case, observation)

    assert result.passed is passed


def test_tool_selection_case_documents_truth_table() -> None:
    assert ToolSelectionCase.__doc__ is not None
    assert "Truth table" in ToolSelectionCase.__doc__
