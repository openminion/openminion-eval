"""Eval interface contracts with versioned compatibility checking."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol
from typing import ClassVar

if TYPE_CHECKING:
    from typing import Callable, Optional


EVAL_INTERFACE_VERSION = "v1"


class EvalInterfaceError(Exception):
    """Raised when an eval owner fails the declared public interface contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class EvalRunnerInterface(Protocol):
    """Eval runner interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        agent_executor: Optional[Callable[[str], str]] = None,
    ) -> None: ...

    async def replay(self, transcript: Any) -> list[Any]: ...

    def replay_sync(self, transcript: Any) -> list[Any]: ...


class EvalScorerInterface(Protocol):
    """Eval scorer interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(self) -> None: ...

    def register_scorer(
        self,
        name: str,
        scorer: Callable[[str, str], float],
    ) -> None: ...

    def score(
        self,
        result: Any,
        expected: Optional[str] = None,
        scorer_name: str = "substring_match",
    ) -> Any: ...

    def score_results(
        self,
        results: list[Any],
        scorer_name: str = "substring_match",
    ) -> list[Any]: ...


class EvalSuiteInterface(Protocol):
    """Eval suite interface contract."""

    contract_version: ClassVar[str] = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        runner: Optional[Any] = None,
        scorer: Optional[Any] = None,
        threshold: float = 0.80,
    ) -> None: ...

    def run(
        self,
        transcripts: list[Any],
        scorer_name: str = "substring_match",
        on_case: Optional[Callable[[Any], None]] = None,
    ) -> Any: ...

    def run_single(
        self,
        transcript: Any,
        scorer_name: str = "substring_match",
    ) -> Any: ...


def _validate_contract_and_methods(
    obj: Any,
    *,
    required_methods: list[str],
    error_code: str,
    label: str,
    strict: bool,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    if not hasattr(obj, "contract_version"):
        errors.append("Missing contract_version attribute")
    elif obj.contract_version != EVAL_INTERFACE_VERSION:
        errors.append(
            f"Version mismatch: expected {EVAL_INTERFACE_VERSION}, got {obj.contract_version}"
        )
    for method in required_methods:
        if not hasattr(obj, method) or not callable(getattr(obj, method)):
            errors.append(f"Missing required method: {method}")
    if errors and strict:
        raise EvalInterfaceError(error_code, f"{label} incompatible: {errors}")
    return not errors, errors


def ensure_eval_runner_compatibility(
    runner: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval runner implements the required interface."""
    return _validate_contract_and_methods(
        runner,
        required_methods=["replay", "replay_sync"],
        error_code="EVAL_RUNNER_INTERFACE_VIOLATION",
        label="Eval runner",
        strict=strict,
    )


def ensure_eval_scorer_compatibility(
    scorer: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval scorer implements the required interface."""
    return _validate_contract_and_methods(
        scorer,
        required_methods=["score", "score_results", "register_scorer"],
        error_code="EVAL_SCORER_INTERFACE_VIOLATION",
        label="Eval scorer",
        strict=strict,
    )


def ensure_eval_suite_compatibility(
    suite: Any, strict: bool = True
) -> tuple[bool, list[str]]:
    """Validate eval suite implements the required interface."""
    return _validate_contract_and_methods(
        suite,
        required_methods=["run", "run_single"],
        error_code="EVAL_SUITE_INTERFACE_VIOLATION",
        label="Eval suite",
        strict=strict,
    )
