"""Black-box subject adapters for standalone eval runs."""

from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import shlex
import subprocess
from typing import Any, Mapping, Sequence
from urllib import request

from openminion_eval.interfaces import EVAL_INTERFACE_VERSION, EvalRunContext


class CliSubject:
    """Run each eval turn through a local command over stdin."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        command: str | Sequence[str],
        *,
        timeout_seconds: float = 30.0,
        cwd: str | Path | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        self._command = _command_parts(command)
        self._timeout_seconds = timeout_seconds
        self._cwd = None if cwd is None else Path(cwd)
        self._env = dict(env or {})

    def run(self, user_input: str, context: EvalRunContext) -> str:
        env = os.environ.copy()
        env.update(self._env)
        env.update(_context_env(context))
        completed = subprocess.run(
            self._command,
            input=user_input,
            text=True,
            capture_output=True,
            check=False,
            timeout=self._timeout_seconds,
            cwd=self._cwd,
            env=env,
        )
        if completed.returncode != 0:
            detail = completed.stderr.strip() or completed.stdout.strip()
            raise RuntimeError(
                f"subject command exited {completed.returncode}: {detail}"
            )
        return completed.stdout.strip()

    async def run_async(self, user_input: str, context: EvalRunContext) -> str:
        return self.run(user_input, context)


class HttpSubject:
    """Run each eval turn against a JSON HTTP endpoint."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(
        self,
        url: str,
        *,
        method: str = "POST",
        headers: Mapping[str, str] | None = None,
        timeout_seconds: float = 30.0,
        input_field: str = "input",
        output_field: str = "output",
    ) -> None:
        self._url = url
        self._method = method.upper()
        self._headers = dict(headers or {})
        self._timeout_seconds = timeout_seconds
        self._input_field = input_field
        self._output_field = output_field

    def run(self, user_input: str, context: EvalRunContext) -> str:
        body = json.dumps(
            {
                self._input_field: user_input,
                "context": asdict(context),
            }
        ).encode("utf-8")
        headers = {"Content-Type": "application/json", **self._headers}
        http_request = request.Request(
            self._url,
            data=body,
            headers=headers,
            method=self._method,
        )
        with request.urlopen(http_request, timeout=self._timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("HTTP subject response must be a JSON object")
        return _string_field(payload, self._output_field, "HTTP subject response")

    async def run_async(self, user_input: str, context: EvalRunContext) -> str:
        return self.run(user_input, context)


class ReplaySubject:
    """Replay expected black-box outputs from a JSONL fixture."""

    contract_version = EVAL_INTERFACE_VERSION

    def __init__(self, responses: Mapping[str, str]) -> None:
        self._responses = dict(responses)

    @classmethod
    def from_jsonl(cls, path: str | Path) -> ReplaySubject:
        responses: dict[str, str] = {}
        for line_number, raw_line in enumerate(
            Path(path).read_text(encoding="utf-8").splitlines(),
            start=1,
        ):
            if not raw_line.strip():
                continue
            payload = json.loads(raw_line)
            if not isinstance(payload, dict):
                raise ValueError(f"replay record {line_number} must be an object")
            user_input = _first_string(payload, ("user", "input"), line_number)
            output = _first_string(payload, ("actual", "output"), line_number)
            responses[user_input] = output
        return cls(responses)

    def run(self, user_input: str, context: EvalRunContext) -> str:
        if user_input not in self._responses:
            raise KeyError(f"no replay output for input: {user_input!r}")
        return self._responses[user_input]

    async def run_async(self, user_input: str, context: EvalRunContext) -> str:
        return self.run(user_input, context)


def parse_http_headers(values: Sequence[str]) -> dict[str, str]:
    headers: dict[str, str] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"HTTP header must use NAME=VALUE: {value!r}")
        name, header_value = value.split("=", 1)
        if not name:
            raise ValueError("HTTP header name is required")
        headers[name] = header_value
    return headers


def load_replay_subject(path: str | Path) -> ReplaySubject:
    return ReplaySubject.from_jsonl(path)


def _command_parts(command: str | Sequence[str]) -> list[str]:
    parts = shlex.split(command) if isinstance(command, str) else list(command)
    if not parts:
        raise ValueError("subject command is required")
    return parts


def _context_env(context: EvalRunContext) -> dict[str, str]:
    env = {
        "OPENMINION_EVAL_TRANSCRIPT": context.transcript_name,
        "OPENMINION_EVAL_TURN_INDEX": str(context.turn_index),
        "OPENMINION_EVAL_DETERMINISTIC": "1" if context.deterministic else "0",
    }
    if context.run_id is not None:
        env["OPENMINION_EVAL_RUN_ID"] = context.run_id
    if context.seed is not None:
        env["OPENMINION_EVAL_SEED"] = str(context.seed)
    return env


def _string_field(payload: Mapping[str, Any], key: str, owner: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str):
        raise ValueError(f"{owner} {key!r} must be a string")
    return value


def _first_string(payload: Mapping[str, Any], keys: tuple[str, ...], line: int) -> str:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    choices = " or ".join(keys)
    raise ValueError(f"replay record {line} must include {choices}")
