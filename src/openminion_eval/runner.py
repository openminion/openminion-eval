"""Eval runner for OpenMinion."""

from typing import Optional, Callable
from openminion_eval.schemas import EvalTranscript, EvalResult
from openminion_eval.interfaces import EVAL_INTERFACE_VERSION


class EvalRunner:
    """Runner that replays a session transcript through the agent runtime."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Optional[Callable[[str], str]] = None,
    ) -> None:
        """
        Initialize the eval runner.

        Args:
            agent_executor: Optional function that takes a user input and returns
                           the agent's response. If not provided, uses a mock.
        """
        self._agent_executor = agent_executor or self._default_executor

    def _default_executor(self, user_input: str) -> str:
        """Default mock executor for testing."""
        return f"Mock response to: {user_input}"

    async def replay(self, transcript: EvalTranscript) -> list[EvalResult]:
        """
        Replay a transcript and return results for each turn.

        Args:
            transcript: The transcript to replay.

        Returns:
            List of EvalResult for each turn.
        """
        results = []

        for i, turn in enumerate(transcript.turns):
            user_input = turn.get("user", "")
            expected = turn.get("expected", "")

            # Execute the turn through the agent
            actual = self._agent_executor(user_input)

            results.append(
                EvalResult(
                    turn_index=i,
                    user_input=user_input,
                    expected=expected,
                    actual=actual,
                    score=0.0,  # Score will be set by scorer
                    scorer_name="pending",
                    metadata={},
                )
            )

        return results

    def replay_sync(self, transcript: EvalTranscript) -> list[EvalResult]:
        """Synchronous version of replay."""
        results = []

        for i, turn in enumerate(transcript.turns):
            user_input = turn.get("user", "")
            expected = turn.get("expected", "")
            actual = self._agent_executor(user_input)

            results.append(
                EvalResult(
                    turn_index=i,
                    user_input=user_input,
                    expected=expected,
                    actual=actual,
                    score=0.0,
                    scorer_name="pending",
                    metadata={},
                )
            )

        return results
