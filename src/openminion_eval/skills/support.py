"""Shared support helpers for canonical skill-eval family owners."""

from __future__ import annotations

from pathlib import Path


_OFFICIAL_SKILL_TARGET_IDS = ("minimax-m2-5", "minimax-m2-7")
_REPRESENTATIVE_SKILL_TARGET_IDS = (
    "ollamacloud-glm-5",
    "ollamacloud-minimax-m2-7",
    "openrouter-minimax-m2-7",
    "openrouter-claude-haiku-4-5",
    "openrouter-gpt-4o",
)
_REPRESENTATIVE_NL_NAMED_SKILL_TARGET_IDS = (
    "minimax-m2-5",
    "minimax-m2-7",
    "ollamacloud-glm-5",
    "ollamacloud-minimax-m2-7",
    "openrouter-minimax-m2-7",
    "openrouter-claude-haiku-4-5",
    "openrouter-gpt-4o",
)


def skill_resources_root() -> Path:
    return Path(__file__).resolve().parent / "resources"


def packaged_skill_fixture_path(relative_path: str | Path) -> Path:
    return (skill_resources_root() / Path(relative_path)).resolve()


def official_skill_matrix_target_ids() -> tuple[str, ...]:
    return _OFFICIAL_SKILL_TARGET_IDS


def representative_skill_quality_target_ids() -> tuple[str, ...]:
    return _REPRESENTATIVE_SKILL_TARGET_IDS


def representative_nl_named_skill_target_ids() -> tuple[str, ...]:
    return _REPRESENTATIVE_NL_NAMED_SKILL_TARGET_IDS


def extract_assistant_messages(
    *, transcript: str, session_id: str, agent_id: str
) -> list[str]:
    prefix = f"[{session_id}|{agent_id}] {agent_id}:"
    next_user_marker = f"\n[{session_id}|{agent_id}] you>"
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
    "extract_assistant_messages",
    "official_skill_matrix_target_ids",
    "packaged_skill_fixture_path",
    "representative_nl_named_skill_target_ids",
    "representative_skill_quality_target_ids",
    "skill_resources_root",
]
