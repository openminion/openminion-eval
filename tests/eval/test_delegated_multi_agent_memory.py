from __future__ import annotations

import pytest

import openminion_eval
from openminion_eval.memory_effectiveness import (
    DelegatedMemoryEvalTrace,
    build_delegated_memory_scorecard,
    load_delegated_memory_cases,
    score_delegated_memory_case,
)


def test_packaged_suite_has_all_named_scenarios() -> None:
    cases = load_delegated_memory_cases()
    assert len(cases) == 8
    assert {case.mode for case in cases} == {
        "disabled",
        "private_only",
        "delegated_shared",
    }
    assert openminion_eval.load_delegated_memory_cases is load_delegated_memory_cases


def test_security_failure_overrides_perfect_utility() -> None:
    case = load_delegated_memory_cases()[0]
    result = score_delegated_memory_case(
        case,
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            retrieved_memory_ids=("project-approved",),
            sibling_scratch_ids=("sibling-scratch",),
        ),
    )
    assert result.utility_recall == 1.0
    assert not result.passed
    assert result.critical_failures == ("sibling_scratch_leak:sibling-scratch",)


@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("direct_id_bypass_ids", "direct_id_bypass:record"),
        ("revoked_future_operation_ids", "revoked_future_operation:record"),
        ("forbidden_reshare_ids", "forbidden_reshare:record"),
        ("accepted_poisoning_ids", "poisoning_accepted:record"),
    ],
)
def test_each_security_class_is_critical(field: str, expected: str) -> None:
    case = load_delegated_memory_cases()[-1]
    trace = DelegatedMemoryEvalTrace(case_id=case.case_id, **{field: ("record",)})
    assert score_delegated_memory_case(case, trace).critical_failures == (expected,)


def test_prior_delivery_is_not_a_revocation_failure() -> None:
    case = load_delegated_memory_cases()[4]
    result = score_delegated_memory_case(
        case,
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            prior_delivery_ids=("post-revoke",),
        ),
    )
    assert result.passed


def test_scorecard_compares_all_modes_and_keeps_efficiency() -> None:
    cases = load_delegated_memory_cases()
    traces = tuple(
        DelegatedMemoryEvalTrace(
            case_id=case.case_id,
            retrieved_memory_ids=case.required_recall_ids,
            latency_ms=2.5,
            token_count=10,
        )
        for case in cases
    )
    scorecard = build_delegated_memory_scorecard(cases, traces)
    assert scorecard.passed
    assert scorecard.utility_recall == 1.0
    assert {result.mode for result in scorecard.results} == {
        "disabled",
        "private_only",
        "delegated_shared",
    }
    assert sum(result.token_count for result in scorecard.results) == 80


def test_fixture_version_and_trace_inputs_fail_closed(tmp_path) -> None:
    fixture = tmp_path / "cases.json"
    fixture.write_text('{"version":"unknown","cases":[]}', encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported"):
        load_delegated_memory_cases(str(fixture))
    with pytest.raises(ValueError, match="negative"):
        DelegatedMemoryEvalTrace(case_id="case", token_count=-1)
