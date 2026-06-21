from __future__ import annotations

import json

import pytest

from openminion_eval import (
    EvalCaseTrace,
    EvalResult,
    EvalScorer,
    EvalScorerSpec,
    EvalSummary,
    EvalSuiteResult,
    build_case_traces,
    write_case_traces_jsonl,
)


def _result() -> EvalResult:
    return EvalResult(
        turn_index=0,
        user_input="question",
        expected="answer",
        actual="answer",
        score=0.0,
        scorer_name="pending",
        metadata={"duration_ms": 3.5, "executor_error": None},
    )


def test_score_with_scorers_preserves_single_scorer_contract() -> None:
    scorer = EvalScorer()

    single = scorer.score(_result(), scorer_name="exact_match")
    scored = scorer.score_with_scorers(
        _result(),
        [
            EvalScorerSpec(name="exact_match", threshold=1.0),
            EvalScorerSpec(name="substring_match", threshold=0.5),
        ],
    )

    assert single.score == 1.0
    assert [result.scorer_name for result in scored] == [
        "exact_match",
        "substring_match",
    ]
    assert [result.scorer_reason for result in scored] == ["passed", "passed"]
    assert [result.scorer_threshold for result in scored] == [1.0, 0.5]


def test_reserved_model_judge_name_does_not_register_provider_adapter() -> None:
    scorer = EvalScorer()

    with pytest.raises(ValueError, match="Reserved scorer name"):
        scorer.register_scorer("llm_judge", lambda _actual, _expected: 1.0)


def test_case_trace_artifacts_are_stable_jsonl(tmp_path) -> None:
    result = EvalSuiteResult(
        suite_name="suite",
        total_transcripts=1,
        passed_transcripts=1,
        failed_transcripts=0,
        all_passed=True,
        summaries=[
            EvalSummary(
                transcript_name="case",
                total_turns=1,
                average_score=1.0,
                min_score=1.0,
                max_score=1.0,
                results=[
                    EvalResult(
                        turn_index=0,
                        user_input="question",
                        expected="answer",
                        actual="answer",
                        score=1.0,
                        scorer_name="exact_match",
                        scorer_reason="passed",
                        scorer_threshold=1.0,
                        metadata={"duration_ms": 2.0, "executor_error": None},
                    )
                ],
                passed=True,
            )
        ],
    )

    traces = build_case_traces(result)
    assert traces == [
        EvalCaseTrace(
            transcript_name="case",
            turn_index=0,
            user_input="question",
            expected="answer",
            actual="answer",
            duration_ms=2.0,
            executor_error=None,
            scorer_name="exact_match",
            score=1.0,
            scorer_reason="passed",
            scorer_threshold=1.0,
        )
    ]

    output = write_case_traces_jsonl(tmp_path / "traces.jsonl", result)
    payload = [json.loads(line) for line in output.read_text().splitlines()]
    assert payload == [
        {
            "actual": "answer",
            "duration_ms": 2.0,
            "executor_error": None,
            "expected": "answer",
            "score": 1.0,
            "scorer_name": "exact_match",
            "scorer_reason": "passed",
            "scorer_threshold": 1.0,
            "transcript_name": "case",
            "turn_index": 0,
            "user_input": "question",
        }
    ]
