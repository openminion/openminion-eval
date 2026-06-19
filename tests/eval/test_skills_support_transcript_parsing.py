from __future__ import annotations

import json
from pathlib import Path

from openminion_eval.skills.support import extract_assistant_messages
from openminion_eval.suite import load_golden_transcripts


def test_extract_assistant_messages_collects_multiple_assistant_turns() -> None:
    transcript = (
        "[session|agent] agent: first answer\n"
        "[session|agent] you> follow up\n"
        "[session|agent] agent: second answer\n"
    )
    assert extract_assistant_messages(
        transcript=transcript,
        session_id="session",
        agent_id="agent",
    ) == ["first answer", "second answer"]


def test_extract_assistant_messages_returns_empty_when_session_does_not_match() -> None:
    transcript = "[other|agent] agent: first answer\n"
    assert (
        extract_assistant_messages(
            transcript=transcript,
            session_id="session",
            agent_id="agent",
        )
        == []
    )


def test_extract_assistant_messages_returns_empty_without_assistant_prefix() -> None:
    assert (
        extract_assistant_messages(
            transcript="[session|agent] you> hi there\n",
            session_id="session",
            agent_id="agent",
        )
        == []
    )


def test_extract_assistant_messages_skips_blank_assistant_bodies() -> None:
    transcript = "[session|agent] agent:\n[session|agent] you> hi there\n"
    assert (
        extract_assistant_messages(
            transcript=transcript,
            session_id="session",
            agent_id="agent",
        )
        == []
    )


def test_load_golden_transcripts_orders_json_files_deterministically(
    tmp_path: Path,
) -> None:
    alpha = tmp_path / "alpha.json"
    zebra = tmp_path / "zebra.json"
    zebra.write_text(json.dumps({"name": "zebra", "turns": []}), encoding="utf-8")
    alpha.write_text(json.dumps({"name": "alpha", "turns": []}), encoding="utf-8")

    first = [item.name for item in load_golden_transcripts(str(tmp_path))]
    second = [item.name for item in load_golden_transcripts(str(tmp_path))]

    assert first == ["alpha", "zebra"]
    assert second == first


def test_load_golden_transcripts_reads_utf8_content(tmp_path: Path) -> None:
    transcript = tmp_path / "utf8.json"
    transcript.write_text(
        json.dumps(
            {
                "name": "caf\u00e9",
                "turns": [{"user": "hola", "expected": "adi\u00f3s"}],
                "tags": ["na\u00efve"],
            }
        ),
        encoding="utf-8",
    )

    loaded = load_golden_transcripts(str(tmp_path))

    assert loaded[0].name == "caf\u00e9"
    assert loaded[0].turns[0]["expected"] == "adi\u00f3s"
    assert loaded[0].tags == ["na\u00efve"]
