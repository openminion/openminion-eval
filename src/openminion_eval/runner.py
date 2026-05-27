"""Eval runner for OpenMinion."""

from time import perf_counter
from typing import Callable, Optional

from openminion_eval.interfaces import EVAL_INTERFACE_VERSION
from openminion_eval.schemas import EvalResult, EvalTranscript


class EvalRunner:
    """Replay transcripts through an executor."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Optional[Callable[[str], str]] = None,
    ) -> None:
        self._agent_executor = agent_executor or self._default_executor

    def _default_executor(self, user_input: str) -> str:
        return f"Mock response to: {user_input}"

    async def replay(self, transcript: EvalTranscript) -> list[EvalResult]:
        """Replay a transcript and return results for each turn."""
        return self.replay_sync(transcript)

    def replay_sync(self, transcript: EvalTranscript) -> list[EvalResult]:
        results = []

        for i, turn in enumerate(transcript.turns):
            user_input = turn.get("user", "")
            expected = turn.get("expected", "")
            start = perf_counter()
            executor_error = None
            try:
                actual = self._agent_executor(user_input)
            except Exception as exc:  # noqa: BLE001
                actual = ""
                executor_error = str(exc)
            duration_ms = max((perf_counter() - start) * 1000.0, 0.001)

            results.append(
                EvalResult(
                    turn_index=i,
                    user_input=user_input,
                    expected=expected,
                    actual=actual,
                    score=0.0,
                    scorer_name="pending",
                    metadata={
                        "duration_ms": duration_ms,
                        "executor_error": executor_error,
                    },
                )
            )

        return results
