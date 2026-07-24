"""Fixture loading for deterministic memory-effectiveness cases."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from importlib.resources.abc import Traversable
from typing import Any, Mapping

from openminion_eval.family_support import require_mapping
from openminion_eval.memory_effectiveness.resource_io import (
    JsonResource,
    load_json_mapping,
    packaged_resource,
)
from openminion_eval.memory_effectiveness.schemas import (
    MemoryEffectivenessCase,
    MemoryExpectation,
)

FIXTURE_VERSION = "1"
_RESOURCE_PACKAGE = "openminion_eval.memory_effectiveness.resources"
_DEFAULT_FIXTURE_NAME = "cases.json"


def default_memory_effectiveness_cases_path() -> Traversable:
    return packaged_resource(_RESOURCE_PACKAGE, _DEFAULT_FIXTURE_NAME)


def load_memory_effectiveness_cases(
    path: JsonResource | None = None,
) -> tuple[MemoryEffectivenessCase, ...]:
    source = default_memory_effectiveness_cases_path() if path is None else path
    payload = load_json_mapping(source)
    version = str(payload.get("version", "") or "").strip()
    if version != FIXTURE_VERSION:
        raise ValueError(
            f"unsupported memory-effectiveness fixture version: {version!r}"
        )

    seen: set[str] = set()
    cases: list[MemoryEffectivenessCase] = []
    for item in payload.get("cases", []):
        case = case_from_mapping(require_mapping(item, context="memory case"))
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


def case_from_mapping(data: Mapping[str, Any]) -> MemoryEffectivenessCase:
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
        expected_operation=str(data.get("expected_operation", "") or "").strip(),
        expected_memory_location=str(
            data.get("expected_memory_location", "") or ""
        ).strip(),
        expected_retrieved_order=_strings(data, "expected_retrieved_order"),
        required_context_memory_ids=_strings(data, "required_context_memory_ids"),
        required_cited_memory_ids=_strings(data, "required_cited_memory_ids"),
        max_unnecessary_memory_calls=_optional_int(
            data, "max_unnecessary_memory_calls"
        ),
        required_entity_proposal_ids=_strings(data, "required_entity_proposal_ids"),
        required_fact_proposal_ids=_strings(data, "required_fact_proposal_ids"),
        required_lifecycle_event_ids=_strings(data, "required_lifecycle_event_ids"),
        required_artifact_ids=_strings(data, "required_artifact_ids"),
        required_citation_spans=_strings(data, "required_citation_spans"),
        expected_trajectory_steps=_strings(data, "expected_trajectory_steps"),
        trajectory_match_mode=str(data.get("trajectory_match_mode", "strict")),
        required_graph_path_ids=_strings(data, "required_graph_path_ids"),
        required_valid_time_refs=_strings(data, "required_valid_time_refs"),
        required_transaction_time_refs=_strings(data, "required_transaction_time_refs"),
    )


def _strings(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    return tuple(str(item) for item in data.get(key, ()))


def _optional_int(data: Mapping[str, Any], key: str) -> int | None:
    value = data.get(key)
    if value is None:
        return None
    return int(value)


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
