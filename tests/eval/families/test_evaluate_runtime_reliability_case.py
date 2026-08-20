from __future__ import annotations

import json
from typing import cast

import pytest

from openminion_eval.family_support import MissingObservationError
from openminion_eval.runtime_reliability import (
    RuntimeReliabilityCase,
    RuntimeReliabilityObservation,
    build_runtime_reliability_report,
    load_runtime_reliability_cases,
)
from openminion_eval.runtime_reliability.family import (
    RuntimeCapability,
    evaluate_runtime_reliability_case,
)


@pytest.mark.parametrize(
    ("capability", "expected_facts"),
    [
        ("project_lifecycle", {"resumed": True, "terminal_verified": True}),
        ("dependency_readiness", {"dependency_ready": False, "blocked": True}),
        ("invocation_lifecycle", {"fenced": True, "recovered": True}),
        ("remote_transport", {"authorized": True, "delivery_confirmed": True}),
        ("infrastructure_monitoring", {"healthy": False, "alerted": True}),
    ],
)
def test_runtime_reliability_scores_recent_runtime_capabilities(
    capability: str,
    expected_facts: dict[str, bool],
) -> None:
    case = RuntimeReliabilityCase(
        case_id="case",
        capability=cast(RuntimeCapability, capability),
        expected_facts=expected_facts,
        required_identifiers=("run_id", "trace_id"),
    )
    observation = RuntimeReliabilityObservation(
        facts=expected_facts,
        identifiers={"run_id": "run-1", "trace_id": "trace-1"},
    )

    result = evaluate_runtime_reliability_case(case, observation)

    assert result.passed is True
    assert result.metrics["fact_match"] is True
    assert result.metrics["identifiers_present"] is True


def test_runtime_reliability_reports_fact_and_identifier_failures() -> None:
    case = RuntimeReliabilityCase(
        case_id="case",
        capability="invocation_lifecycle",
        expected_facts={"fenced": True, "recovered": True},
        required_identifiers=("invocation_id",),
    )

    result = evaluate_runtime_reliability_case(
        case,
        RuntimeReliabilityObservation(
            facts={"fenced": False, "recovered": True},
        ),
    )

    assert result.passed is False
    assert result.metrics["mismatched_fact_count"] == 1
    assert result.metrics["missing_identifier_count"] == 1


def test_runtime_reliability_does_not_treat_missing_none_fact_as_match() -> None:
    case = RuntimeReliabilityCase(
        case_id="case",
        capability="infrastructure_monitoring",
        expected_facts={"incident_id": None},
    )

    result = evaluate_runtime_reliability_case(
        case,
        RuntimeReliabilityObservation(facts={}),
    )

    assert result.passed is False
    assert result.metrics["mismatched_fact_count"] == 1


def test_runtime_reliability_report_preserves_missing_observation_contract() -> None:
    case = RuntimeReliabilityCase("case", "project_lifecycle", {"resumed": True})

    with pytest.raises(MissingObservationError):
        build_runtime_reliability_report(cases=(case,), observations={})


def test_runtime_reliability_case_loader_validates_capabilities(tmp_path) -> None:
    fixture = tmp_path / "cases.json"
    fixture.write_text(
        json.dumps(
            {
                "version": "1",
                "cases": [
                    {
                        "case_id": "project-resume",
                        "capability": "project_lifecycle",
                        "expected_facts": {"resumed": True},
                        "required_identifiers": ["run_id"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    cases = load_runtime_reliability_cases(fixture)

    assert cases == (
        RuntimeReliabilityCase(
            case_id="project-resume",
            capability="project_lifecycle",
            expected_facts={"resumed": True},
            required_identifiers=("run_id",),
        ),
    )
