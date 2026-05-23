"""Eval interface contracts with versioned compatibility checking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from typing import ClassVar

if TYPE_CHECKING:
    from typing import Callable, Optional


EVAL_INTERFACE_VERSION = "v1"


class EvalRunnerInterface(Protocol):
    """Eval Runner interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Optional[Callable[[str], str]] = None,
    ) -> None: ...

    async def replay(
        self, transcript: Any
    ) -> list[Any]: ...  # EvalTranscript -> EvalResult

    def replay_sync(
        self, transcript: Any
    ) -> list[Any]: ...  # EvalTranscript -> EvalResult


class EvalScorerInterface(Protocol):
    """Eval Scorer interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(self) -> None: ...

    def register_scorer(
        self,
        name: str,
        scorer: Callable[[str, str], float],
    ) -> None: ...

    def score(
        self,
        result: Any,  # EvalResult
        expected: Optional[str] = None,
        scorer_name: str = "substring_match",
    ) -> Any: ...  # returns EvalResult

    def score_results(
        self,
        results: list[Any],  # List[EvalResult]
        scorer_name: str = "substring_match",
    ) -> list[Any]: ...  # List[EvalResult]


class EvalSuiteInterface(Protocol):
    """Eval Suite interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        runner: Optional[Any] = None,  # EvalRunner
        scorer: Optional[Any] = None,  # EvalScorer
        threshold: float = 0.80,
    ) -> None: ...

    def run(
        self,
        transcripts: list[Any],  # List[EvalTranscript]
        scorer_name: str = "substring_match",
    ) -> Any: ...  # EvlSuiteResult

    def run_single(
        self,
        transcript: Any,  # EvalTranscript
        scorer_name: str = "substring_match",
    ) -> Any: ...  # EvalSummary


def ensure_eval_runner_compatibility(
    runner: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval runner implements the required interface."""
    errors = []

    # Check contract version
    if not hasattr(runner, "contract_version"):
        errors.append("Missing contract_version attribute")
    elif runner.contract_version != EVAL_INTERFACE_VERSION:
        errors.append(
            f"Version mismatch: expected {EVAL_INTERFACE_VERSION}, "
            f"got {runner.contract_version}"
        )

    # Check required methods
    required_methods = ["replay", "replay_sync"]

    for method in required_methods:
        if not hasattr(runner, method) or not callable(getattr(runner, method)):
            errors.append(f"Missing required method: {method}")

    if errors:
        if strict:

            class EvalError(Exception):
                def __init__(self, code, message):
                    self.code = code
                    self.message = message

            raise EvalError(
                "EVAL_RUNNER_INTERFACE_VIOLATION", f"Eval runner incompatible: {errors}"
            )
        return False, errors

    return True, []


def ensure_eval_scorer_compatibility(
    scorer: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval scorer implements the required interface."""
    errors = []

    # Check contract version
    if not hasattr(scorer, "contract_version"):
        errors.append("Missing contract_version attribute")
    elif scorer.contract_version != EVAL_INTERFACE_VERSION:
        errors.append(
            f"Version mismatch: expected {EVAL_INTERFACE_VERSION}, "
            f"got {scorer.contract_version}"
        )

    # Check required methods
    required_methods = ["score", "score_results", "register_scorer"]

    for method in required_methods:
        if not hasattr(scorer, method) or not callable(getattr(scorer, method)):
            errors.append(f"Missing required method: {method}")

    if errors:
        if strict:

            class EvalError(Exception):
                def __init__(self, code, message):
                    self.code = code
                    self.message = message

            raise EvalError(
                "EVAL_SCORER_INTERFACE_VIOLATION", f"Eval scorer incompatible: {errors}"
            )
        return False, errors

    return True, []


def ensure_eval_suite_compatibility(
    suite: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval suite implements the required interface."""
    errors = []

    # Check contract version
    if not hasattr(suite, "contract_version"):
        errors.append("Missing contract_version attribute")
    elif suite.contract_version != EVAL_INTERFACE_VERSION:
        errors.append(
            f"Version mismatch: expected {EVAL_INTERFACE_VERSION}, "
            f"got {suite.contract_version}"
        )

    # Check required methods
    required_methods = ["run", "run_single"]

    for method in required_methods:
        if not hasattr(suite, method) or not callable(getattr(suite, method)):
            errors.append(f"Missing required method: {method}")

    if errors:
        if strict:

            class EvalError(Exception):
                def __init__(self, code, message):
                    self.code = code
                    self.message = message

            raise EvalError(
                "EVAL_SUITE_INTERFACE_VIOLATION", f"Eval suite incompatible: {errors}"
            )
        return False, errors

    return True, []
