"""Fixture loading for deterministic memory-effectiveness cases."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any, Mapping

from openminion_eval.family_support import require_mapping
from openminion_eval.memory_effectiveness.schemas import (
    MemoryEffectivenessCase,
    MemoryExpectation,
)

FIXTURE_VERSION = "1"
_RESOURCE_PACKAGE = "openminion_eval.memory_effectiveness.resources"
_DEFAULT_FIXTURE_NAME = "cases.json"


def default_memory_effectiveness_cases_path() -> Path:
    with resources.as_file(
        resources.files(_RESOURCE_PACKAGE).joinpath(_DEFAULT_FIXTURE_NAME)
    ) as path:
        return path


def load_memory_effectiveness_cases(
    path: str | Path | None = None,
) -> tuple[MemoryEffectivenessCase, ...]:
    source = default_memory_effectiveness_cases_path() if path is None else Path(path)
    payload = require_mapping(
        json.loads(source.read_text(encoding="utf-8")), context=str(source)
    )
    version = str(payload.get("version", "") or "").strip()
    if version != FIXTURE_VERSION:
        raise ValueError(
            f"unsupported memory-effectiveness fixture version: {version!r}"
        )

    seen: set[str] = set()
    cases: list[MemoryEffectivenessCase] = []
    for item in payload.get("cases", []):
        case = _case_from_mapping(require_mapping(item, context="memory case"))
        if case.case_id in seen:
            raise ValueError(
                f"duplicate memory-effectiveness case_id: {case.case_id!r}"
            )
        seen.add(case.case_id)
        cases.append(case)
    _validate_family_coverage(cases)
    return tuple(cases)


def hash_memory_effectiveness_cases(cases: tuple[MemoryEffectivenessCase, ...]) -> str:
    payload = [asdict(case) for case in cases]
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _case_from_mapping(data: Mapping[str, Any]) -> MemoryEffectivenessCase:
    return MemoryEffectivenessCase(
        case_id=str(data.get("case_id", "") or "").strip(),
        family=data.get("family"),  # type: ignore[arg-type]
        prompt=str(data.get("prompt", "") or "").strip(),
        teaching_turns=tuple(str(item) for item in data.get("teaching_turns", ())),
        followup_turns=tuple(str(item) for item in data.get("followup_turns", ())),
        tags=tuple(str(item) for item in data.get("tags", ())),
        expectations=_expectation_from_mapping(
            require_mapping(data.get("expectations", {}), context="expectations")
        ),
    )


def _expectation_from_mapping(data: Mapping[str, Any]) -> MemoryExpectation:
    return MemoryExpectation(
        required_saved_ids=_strings(data, "required_saved_ids"),
        required_retrieved_ids=_strings(data, "required_retrieved_ids"),
        required_used_ids=_strings(data, "required_used_ids"),
        required_claim_memory_ids=_strings(data, "required_claim_memory_ids"),
        required_tool_memory_ids=_strings(data, "required_tool_memory_ids"),
        forbidden_memory_ids=_strings(data, "forbidden_memory_ids"),
        expected_namespace=str(data.get("expected_namespace", "") or "").strip(),
        expect_no_memory_claim=bool(data.get("expect_no_memory_claim", False)),
        requires_longitudinal_improvement=bool(
            data.get("requires_longitudinal_improvement", False)
        ),
        critical=bool(data.get("critical", False)),
        description=str(data.get("description", "") or ""),
    )


def _strings(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in data.get(key, ()))


def _validate_family_coverage(cases: list[MemoryEffectivenessCase]) -> None:
    by_family: dict[str, set[str]] = {}
    for case in cases:
        by_family.setdefault(case.family, set()).update(case.tags)
    missing = [
        family
        for family, tags in sorted(by_family.items())
        if not {"positive", "negative"}.issubset(tags)
    ]
    if missing:
        raise ValueError(
            "memory-effectiveness fixtures require positive and negative tags for "
            f"every family: {missing!r}"
        )
