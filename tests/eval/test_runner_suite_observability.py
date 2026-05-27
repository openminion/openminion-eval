from __future__ import annotations

from openminion_eval.runner import EvalRunner
from openminion_eval.schemas import EvalTranscript
from openminion_eval.suite import EvalSuite


def test_runner_records_duration_and_successful_executor_error_state() -> None:
    runner = EvalRunner(agent_executor=lambda user_input: f"ok: {user_input}")
    transcript = EvalTranscript(name="demo", turns=[{"user": "hi", "expected": "ok"}])

    result = runner.replay_sync(transcript)[0]

    assert result.metadata["duration_ms"] > 0
    assert result.metadata["executor_error"] is None


def test_runner_records_executor_error_without_aborting() -> None:
    def raise_executor(_user_input: str) -> str:
        raise RuntimeError("boom")

    runner = EvalRunner(agent_executor=raise_executor)
    transcript = EvalTranscript(name="demo", turns=[{"user": "hi", "expected": "ok"}])

    result = runner.replay_sync(transcript)[0]

    assert result.actual == ""
    assert result.metadata["duration_ms"] > 0
    assert result.metadata["executor_error"] == "boom"


def test_suite_on_case_callback_and_error_count() -> None:
    seen = []
    suite = EvalSuite(
        runner=EvalRunner(agent_executor=lambda _user_input: "expected"),
        threshold=1.0,
    )
    transcript = EvalTranscript(
        name="demo",
        turns=[{"user": "hi", "expected": "expected"}],
    )

    result = suite.run([transcript], on_case=seen.append)

    assert len(seen) == 1
    assert seen[0].score == 1.0
    assert result.summaries[0].scorer_error_count == 0


def test_suite_counts_executor_errors_in_summary() -> None:
    def raise_executor(_user_input: str) -> str:
        raise RuntimeError()

    suite = EvalSuite(runner=EvalRunner(agent_executor=raise_executor))
    transcript = EvalTranscript(name="demo", turns=[{"user": "hi", "expected": "ok"}])

    result = suite.run([transcript])

    assert result.summaries[0].scorer_error_count == 1
