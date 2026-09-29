"""Shared JSON payload parsing for memory-effectiveness artifacts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from openminion_eval.memory_effectiveness.schemas import (
    MemoryAcceptanceArtifact,
    MemoryCalibrationArtifact,
    MemoryEvaluationFixtureSet,
)


def json_objects(items: list | tuple, label: str) -> tuple[dict[str, Any], ...]:
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"{label} item {index} must be an object")
        objects.append(item)
    return tuple(objects)


def string_tuple(data: Mapping[str, Any], key: str) -> tuple[str, ...]:
    values = data.get(key, ())
    return strings_from_value(values, key)


def strings_from_value(values: object, label: str) -> tuple[str, ...]:
    if not isinstance(values, list | tuple):
        raise TypeError(f"{label} must be a list")
    return tuple(str(value) for value in values)


def canonical_payload_hash(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def build_memory_calibration_artifact(
    fixture: MemoryEvaluationFixtureSet,
    *,
    observed_case_ids: tuple[str, ...],
    capability_set: tuple[str, ...],
    score_domain_id: str,
    adapter_hash: str,
    index_hash: str,
    score_components: tuple[str, ...],
    omission_reason_codes: tuple[str, ...],
    selected_parameters: Mapping[str, bool | float | int | str],
) -> MemoryCalibrationArtifact:
    if tuple(observed_case_ids) != fixture.development_case_ids:
        raise ValueError("calibration must use the frozen development case ids")
    return MemoryCalibrationArtifact(
        development_case_ids=fixture.development_case_ids,
        observed_case_ids=observed_case_ids,
        fixture_hash=fixture.fixture_hash,
        development_hash=fixture.development_hash,
        resource_hash=fixture.resource_hash,
        capability_set=capability_set,
        score_domain_id=score_domain_id,
        adapter_hash=adapter_hash,
        index_hash=index_hash,
        score_components=score_components,
        omission_reason_codes=omission_reason_codes,
        selected_parameters=tuple(sorted(selected_parameters.items())),
    )


def build_memory_acceptance_artifact(
    fixture: MemoryEvaluationFixtureSet,
    calibration: MemoryCalibrationArtifact,
    *,
    acceptance_case_ids: tuple[str, ...],
) -> MemoryAcceptanceArtifact:
    if tuple(acceptance_case_ids) != fixture.acceptance_case_ids:
        raise ValueError("acceptance must use the frozen acceptance case ids")
    reused = set(acceptance_case_ids) & set(calibration.observed_case_ids)
    if reused:
        raise ValueError(
            "acceptance cases were observed during calibration: "
            + ",".join(sorted(reused))
        )
    if (
        calibration.fixture_hash != fixture.fixture_hash
        or calibration.development_hash != fixture.development_hash
        or calibration.resource_hash != fixture.resource_hash
    ):
        raise ValueError("calibration fixture identity does not match acceptance")
    calibration_identity_hash = canonical_payload_hash(asdict(calibration))
    return MemoryAcceptanceArtifact(
        acceptance_case_ids=acceptance_case_ids,
        fixture_hash=fixture.fixture_hash,
        acceptance_hash=fixture.acceptance_hash,
        resource_hash=fixture.resource_hash,
        capability_set=calibration.capability_set,
        score_domain_id=calibration.score_domain_id,
        adapter_hash=calibration.adapter_hash,
        index_hash=calibration.index_hash,
        score_components=calibration.score_components,
        omission_reason_codes=calibration.omission_reason_codes,
        calibration_identity_hash=calibration_identity_hash,
    )
