"""Eval runner for OpenMinion."""

import asyncio
from time import perf_counter
from typing import Any, Callable, Optional

from openminion_eval.interfaces import (
    EVAL_INTERFACE_VERSION,
    EvalRunContext,
    ensure_eval_subject_compatibility,
)
from openminion_eval.schemas import EvalResult, EvalTranscript


class EvalRunner:
    """Replay transcripts through an executor."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Optional[Callable[[str], str]] = None,
        subject: Any | None = None,
        run_id: str | None = None,
        seed: int | None = None,
        deterministic: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if subject is not None:
            ensure_eval_subject_compatibility(subject)
        self._agent_executor = agent_executor or self._default_executor
        self._subject = subject
        self._run_id = run_id
        self._seed = seed
        self._deterministic = deterministic
        self._metadata = dict(metadata or {})

    def _default_executor(self, user_input: str) -> str:
        return f"Mock response to: {user_input}"

    async def replay(self, transcript: EvalTranscript) -> list[EvalResult]:
        """Replay a transcript and return results for each turn."""
        results = []
        for i, turn in enumerate(transcript.turns):
            result = await self._run_turn_async(
                transcript=transcript, turn=turn, index=i
            )
            results.append(result)
        return results

    def replay_sync(self, transcript: EvalTranscript) -> list[EvalResult]:
        results = []

        for i, turn in enumerate(transcript.turns):
            results.append(
                self._run_turn_sync(transcript=transcript, turn=turn, index=i)
            )

        return results

    def _run_turn_sync(
        self,
        *,
        transcript: EvalTranscript,
        turn: dict,
        index: int,
    ) -> EvalResult:
        return self._record_turn(
            transcript=transcript,
            turn=turn,
            index=index,
            execute=lambda user_input, context: self._execute_sync(user_input, context),
        )

    async def _run_turn_async(
        self,
        *,
        transcript: EvalTranscript,
        turn: dict,
        index: int,
    ) -> EvalResult:
        user_input = turn.get("user", "")
        expected = turn.get("expected", "")
        context = self._context_for(transcript=transcript, index=index)
        start = perf_counter()
        executor_error = None
        try:
            actual = await self._execute_async(user_input, context)
        except Exception as exc:  # noqa: BLE001
            actual = ""
            executor_error = str(exc)
        duration_ms = max((perf_counter() - start) * 1000.0, 0.001)
        return self._result(
            index=index,
            user_input=user_input,
            expected=expected,
            actual=actual,
            duration_ms=duration_ms,
            executor_error=executor_error,
        )

    def _record_turn(
        self,
        *,
        transcript: EvalTranscript,
        turn: dict,
        index: int,
        execute: Callable[[str, EvalRunContext], str],
    ) -> EvalResult:
        user_input = turn.get("user", "")
        expected = turn.get("expected", "")
        context = self._context_for(transcript=transcript, index=index)
        start = perf_counter()
        executor_error = None
        try:
            actual = execute(user_input, context)
        except Exception as exc:  # noqa: BLE001
            actual = ""
            executor_error = str(exc)
        duration_ms = max((perf_counter() - start) * 1000.0, 0.001)
        return self._result(
            index=index,
            user_input=user_input,
            expected=expected,
            actual=actual,
            duration_ms=duration_ms,
            executor_error=executor_error,
        )

    def _execute_sync(self, user_input: str, context: EvalRunContext) -> str:
        if self._subject is None:
            return self._agent_executor(user_input)
        run = getattr(self._subject, "run", None)
        if callable(run):
            return str(run(user_input, context))
        return str(asyncio.run(self._subject.run_async(user_input, context)))

    async def _execute_async(self, user_input: str, context: EvalRunContext) -> str:
        if self._subject is None:
            return self._agent_executor(user_input)
        run_async = getattr(self._subject, "run_async", None)
        if callable(run_async):
            return str(await run_async(user_input, context))
        return str(self._subject.run(user_input, context))

    def _context_for(self, *, transcript: EvalTranscript, index: int) -> EvalRunContext:
        return EvalRunContext(
            transcript_name=str(getattr(transcript, "name", "default") or "default"),
            turn_index=index,
            run_id=self._run_id,
            seed=self._seed,
            deterministic=self._deterministic,
            metadata=dict(self._metadata),
        )

    def _result(
        self,
        *,
        index: int,
        user_input: str,
        expected: str,
        actual: str,
        duration_ms: float,
        executor_error: str | None,
    ) -> EvalResult:
        return EvalResult(
            turn_index=index,
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
