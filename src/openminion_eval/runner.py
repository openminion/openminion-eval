"""Eval runner for OpenMinion."""

import asyncio
from collections.abc import Callable, Coroutine
from time import perf_counter
from typing import Any, cast

from openminion_eval.interfaces import (
    EVAL_INTERFACE_VERSION,
    AsyncEvalSubjectInterface,
    EvalRunContext,
    EvalSubject,
    EvalSubjectInterface,
    ensure_eval_subject_compatibility,
)
from openminion_eval.schemas import EvalResult, EvalTranscript


class EvalRunner:
    """Replay transcripts through an executor."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Callable[[str], str] | None = None,
        subject: EvalSubject | None = None,
        run_id: str | None = None,
        seed: int | None = None,
        deterministic: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        if subject is not None:
            ensure_eval_subject_compatibility(subject)
        self._agent_executor = agent_executor or self._default_executor
        self._subject_run: Callable[[str, EvalRunContext], str] | None = None
        self._subject_run_async: (
            Callable[[str, EvalRunContext], Coroutine[Any, Any, str]] | None
        ) = None
        if subject is not None:
            if callable(getattr(subject, "run", None)):
                self._subject_run = cast(EvalSubjectInterface, subject).run
            if callable(getattr(subject, "run_async", None)):
                self._subject_run_async = cast(
                    AsyncEvalSubjectInterface, subject
                ).run_async
        self._run_id = run_id
        self._seed = seed
        self._deterministic = deterministic
        self._metadata = dict(metadata or {})

    def _default_executor(self, user_input: str) -> str:
        return f"Mock response to: {user_input}"

    async def replay(self, transcript: EvalTranscript) -> list[EvalResult]:
        """Replay a transcript and return results for each turn."""
        return [
            await self._run_turn_async(
                transcript=transcript,
                turn=turn,
                index=index,
            )
            for index, turn in enumerate(transcript.turns)
        ]

    def replay_sync(self, transcript: EvalTranscript) -> list[EvalResult]:
        return [
            self._run_turn_sync(
                transcript=transcript,
                turn=turn,
                index=index,
            )
            for index, turn in enumerate(transcript.turns)
        ]

    def _run_turn_sync(
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
            actual = self._execute_sync(user_input, context)
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

    def _execute_sync(self, user_input: str, context: EvalRunContext) -> str:
        if self._subject_run is not None:
            return str(self._subject_run(user_input, context))
        if self._subject_run_async is not None:
            return str(asyncio.run(self._subject_run_async(user_input, context)))
        return self._agent_executor(user_input)

    async def _execute_async(self, user_input: str, context: EvalRunContext) -> str:
        if self._subject_run_async is not None:
            return str(await self._subject_run_async(user_input, context))
        if self._subject_run is not None:
            return str(self._subject_run(user_input, context))
        return self._agent_executor(user_input)

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
