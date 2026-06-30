"""Shared support helpers for canonical skill-eval family owners."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from openminion_eval.paths import skill_resources_root as _skill_resources_root
from openminion_eval.skills.constants import (
    FAMILY_REPORT_VERSION,
    TRANSCRIPT_AGENT_PREFIX_TEMPLATE,
    TRANSCRIPT_NEXT_USER_MARKER_TEMPLATE,
)


_OFFICIAL_SKILL_TARGET_IDS = ("minimax-m2-5", "minimax-m2-7")
_REPRESENTATIVE_SKILL_TARGET_IDS = (
    "ollamacloud-glm-5",
    "ollamacloud-minimax-m2-7",
    "openrouter-minimax-m2-7",
    "openrouter-claude-haiku-4-5",
    "openrouter-gpt-4o",
)
_REPRESENTATIVE_NL_NAMED_SKILL_TARGET_IDS = (
    *_OFFICIAL_SKILL_TARGET_IDS,
    *_REPRESENTATIVE_SKILL_TARGET_IDS,
)


def skill_resources_root() -> Path:
    return _skill_resources_root()


def packaged_skill_fixture_path(relative_path: str | Path) -> Path:
    return (skill_resources_root() / Path(relative_path)).resolve()


def load_skill_json(path: str | Path, description: str) -> tuple[str, dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = str(payload.get("version", "") or "").strip()
    if version != FAMILY_REPORT_VERSION:
        raise ValueError(f"unsupported {description} version: {version!r}")
    return version, payload


def unique_skill_id(item: Mapping[str, Any], field: str, seen_ids: set[str]) -> str:
    value = str(item.get(field, "") or "").strip()
    if not value or value in seen_ids:
        raise ValueError(f"invalid or duplicate {field}: {value!r}")
    seen_ids.add(value)
    return value


def required_skill_fixture(
    relative_path: object, description: str, scenario_id: str
) -> Path:
    fixture_path = packaged_skill_fixture_path(str(relative_path or ""))
    if not fixture_path.exists():
        raise ValueError(
            f"missing fixture for {description} {scenario_id}: {fixture_path}"
        )
    return fixture_path


def official_skill_matrix_target_ids() -> tuple[str, ...]:
    return _OFFICIAL_SKILL_TARGET_IDS


def representative_skill_quality_target_ids() -> tuple[str, ...]:
    return _REPRESENTATIVE_SKILL_TARGET_IDS


def representative_nl_named_skill_target_ids() -> tuple[str, ...]:
    return _REPRESENTATIVE_NL_NAMED_SKILL_TARGET_IDS


def assistant_output_from_record(
    record: Mapping[str, object],
    *,
    agent_id: str,
    session_id: str = "",
) -> str:
    transcript_value = str(record.get("transcript", "") or "").strip()
    if transcript_value:
        transcript_path = Path(transcript_value).expanduser()
        if transcript_path.is_file():
            transcript = transcript_path.read_text(encoding="utf-8")
            resolved_session_id = session_id or transcript_path.stem
            messages = extract_assistant_messages(
                transcript=transcript,
                session_id=resolved_session_id,
                agent_id=agent_id,
            )
            if messages:
                return "\n\n".join(messages)
    return str(record.get("assistant_preview", "") or "").strip()


def extract_assistant_messages(
    *, transcript: str, session_id: str, agent_id: str
) -> list[str]:
    prefix = TRANSCRIPT_AGENT_PREFIX_TEMPLATE.format(
        session_id=session_id,
        agent_id=agent_id,
    )
    next_user_marker = TRANSCRIPT_NEXT_USER_MARKER_TEMPLATE.format(
        session_id=session_id,
        agent_id=agent_id,
    )
    messages: list[str] = []
    start = 0
    while True:
        match = transcript.find(prefix, start)
        if match < 0:
            break
        body_start = match + len(prefix)
        body_end = transcript.find(next_user_marker, body_start)
        if body_end < 0:
            body_end = len(transcript)
        lines = transcript[body_start:body_end].splitlines()
        cleaned = "\n".join(line.strip() for line in lines if line.strip())
        if cleaned:
            messages.append(cleaned)
        start = body_end
    return messages


__all__ = [
    "assistant_output_from_record",
    "extract_assistant_messages",
    "official_skill_matrix_target_ids",
    "packaged_skill_fixture_path",
    "representative_nl_named_skill_target_ids",
    "representative_skill_quality_target_ids",
    "skill_resources_root",
]
