from __future__ import annotations

import json
from pathlib import Path
import sys

from openminion_eval import EvalRunContext
from openminion_eval import subject_adapters
from openminion_eval.subject_adapters import (
    CliSubject,
    HttpSubject,
    ReplaySubject,
    parse_http_headers,
)


def _context() -> EvalRunContext:
    return EvalRunContext(transcript_name="subject", turn_index=0, run_id="run")


def test_cli_subject_runs_command_over_stdin() -> None:
    subject = CliSubject(
        [
            sys.executable,
            "-c",
            "import sys; print('answer:' + sys.stdin.read().strip())",
        ]
    )

    assert subject.run("hello", _context()) == "answer:hello"


def test_replay_subject_loads_jsonl_outputs(tmp_path: Path) -> None:
    path = tmp_path / "replay.jsonl"
    path.write_text('{"user": "hello", "actual": "hi"}\n', encoding="utf-8")

    subject = ReplaySubject.from_jsonl(path)

    assert subject.run("hello", _context()) == "hi"


def test_http_subject_posts_json_and_reads_output_field(monkeypatch) -> None:
    class Response:
        def __enter__(self) -> Response:
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return json.dumps({"result": "echo:hello"}).encode()

    def fake_urlopen(http_request, *, timeout: float) -> Response:
        assert http_request.full_url == "http://127.0.0.1/eval"
        assert timeout == 30.0
        assert json.loads(http_request.data.decode())["input"] == "hello"
        return Response()

    monkeypatch.setattr(subject_adapters.request, "urlopen", fake_urlopen)
    subject = HttpSubject("http://127.0.0.1/eval", output_field="result")

    assert subject.run("hello", _context()) == "echo:hello"


def test_parse_http_headers_requires_name_value_pairs() -> None:
    assert parse_http_headers(["Authorization=Bearer token"]) == {
        "Authorization": "Bearer token"
    }
