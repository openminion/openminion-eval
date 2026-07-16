"""Provider-free boundary artifact contracts for red-team and golden data."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from openminion_eval.schemas import (
    RedTeamSecurityArtifact,
    RedTeamSecurityFixture,
    RedTeamSecurityResult,
    SyntheticGolden,
    SyntheticGoldenArtifact,
    SyntheticGoldenProvenance,
)


BOUNDARY_ARTIFACT_VERSION = "1"
RED_TEAM_SECURITY_OUTCOMES = frozenset({"passed", "failed", "inconclusive"})


class BoundaryArtifactValidationError(ValueError):
    """Raised when a boundary artifact does not match the public contract."""


def load_red_team_security_artifact(path: str | Path) -> RedTeamSecurityArtifact:
    payload = _load_object(path, "red-team security artifact")
    version = _required_boundary_string(payload, "artifact_version", "artifact")
    _ensure_supported_boundary_version(version)
    name = _required_boundary_string(payload, "name", "artifact")
    fixtures = payload.get("fixtures")
    if not isinstance(fixtures, list):
        raise BoundaryArtifactValidationError("red-team fixtures must be a list")
    results = payload.get("results", [])
    if not isinstance(results, list):
        raise BoundaryArtifactValidationError("red-team results must be a list")
    metadata = _metadata(payload, "artifact")
    parsed_fixtures = [
        _red_team_fixture(item, index) for index, item in enumerate(fixtures)
    ]
    _ensure_unique(
        [fixture.fixture_id for fixture in parsed_fixtures],
        owner="red-team fixture",
    )
    parsed_results = [
        _red_team_result(item, index) for index, item in enumerate(results)
    ]
    _ensure_result_fixture_ids(parsed_results, parsed_fixtures)
    return RedTeamSecurityArtifact(
        artifact_version=version,
        name=name,
        fixtures=parsed_fixtures,
        results=parsed_results,
        metadata=metadata,
    )


def write_red_team_security_artifact(
    artifact: RedTeamSecurityArtifact, path: str | Path
) -> None:
    _write_boundary_json(artifact, path)


def load_synthetic_golden_artifact(path: str | Path) -> SyntheticGoldenArtifact:
    payload = _load_object(path, "synthetic golden artifact")
    version = _required_boundary_string(payload, "artifact_version", "artifact")
    _ensure_supported_boundary_version(version)
    name = _required_boundary_string(payload, "name", "artifact")
    goldens = payload.get("goldens")
    if not isinstance(goldens, list):
        raise BoundaryArtifactValidationError("synthetic goldens must be a list")
    metadata = _metadata(payload, "artifact")
    parsed_goldens = [
        _synthetic_golden(item, index) for index, item in enumerate(goldens)
    ]
    _ensure_unique(
        [golden.golden_id for golden in parsed_goldens],
        owner="synthetic golden",
    )
    return SyntheticGoldenArtifact(
        artifact_version=version,
        name=name,
        goldens=parsed_goldens,
        metadata=metadata,
    )


def write_synthetic_golden_artifact(
    artifact: SyntheticGoldenArtifact, path: str | Path
) -> None:
    _write_boundary_json(artifact, path)


def _load_object(path: str | Path, owner: str) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise BoundaryArtifactValidationError(f"{owner} JSON must be an object")
    return payload


def _red_team_fixture(payload: Any, index: int) -> RedTeamSecurityFixture:
    if not isinstance(payload, dict):
        raise BoundaryArtifactValidationError(f"fixture {index} must be an object")
    owner = f"fixture {index}"
    return RedTeamSecurityFixture(
        fixture_id=_required_boundary_string(payload, "id", owner),
        category=_required_boundary_string(payload, "category", owner),
        prompt=_required_boundary_string(payload, "prompt", owner),
        expected_behavior=_required_boundary_string(
            payload, "expected_behavior", owner
        ),
        tags=_tags(payload, owner),
        metadata=_metadata(payload, owner),
    )


def _red_team_result(payload: Any, index: int) -> RedTeamSecurityResult:
    if not isinstance(payload, dict):
        raise BoundaryArtifactValidationError(f"result {index} must be an object")
    owner = f"result {index}"
    outcome = _required_boundary_string(payload, "outcome", owner)
    if outcome not in RED_TEAM_SECURITY_OUTCOMES:
        raise BoundaryArtifactValidationError(f"{owner} outcome is unsupported")
    score = payload.get("score")
    if score is not None and (
        isinstance(score, bool) or not isinstance(score, int | float)
    ):
        raise BoundaryArtifactValidationError(f"{owner} score must be a number")
    return RedTeamSecurityResult(
        fixture_id=_required_boundary_string(payload, "fixture_id", owner),
        outcome=outcome,
        observed_behavior=_required_boundary_string(
            payload, "observed_behavior", owner
        ),
        score=float(score) if score is not None else None,
        metadata=_metadata(payload, owner),
    )


def _synthetic_golden(payload: Any, index: int) -> SyntheticGolden:
    if not isinstance(payload, dict):
        raise BoundaryArtifactValidationError(f"golden {index} must be an object")
    owner = f"golden {index}"
    provenance = payload.get("provenance")
    if not isinstance(provenance, dict):
        raise BoundaryArtifactValidationError(f"{owner} provenance must be an object")
    return SyntheticGolden(
        golden_id=_required_boundary_string(payload, "id", owner),
        input=_required_boundary_string(payload, "input", owner),
        expected_output=_required_boundary_string(payload, "expected_output", owner),
        provenance=_synthetic_provenance(provenance, owner),
        tags=_tags(payload, owner),
        metadata=_metadata(payload, owner),
    )


def _synthetic_provenance(
    payload: dict[str, Any], owner: str
) -> SyntheticGoldenProvenance:
    source_artifact_hash = payload.get("source_artifact_hash")
    if source_artifact_hash is not None and not isinstance(source_artifact_hash, str):
        raise BoundaryArtifactValidationError(
            f"{owner} provenance source_artifact_hash must be a string"
        )
    return SyntheticGoldenProvenance(
        source=_required_boundary_string(payload, "source", f"{owner} provenance"),
        generated_by=_required_boundary_string(
            payload, "generated_by", f"{owner} provenance"
        ),
        generated_at=_required_boundary_string(
            payload, "generated_at", f"{owner} provenance"
        ),
        generation_method=_required_boundary_string(
            payload, "generation_method", f"{owner} provenance"
        ),
        source_artifact_hash=source_artifact_hash,
        metadata=_metadata(payload, f"{owner} provenance"),
    )


def _write_boundary_json(
    artifact: RedTeamSecurityArtifact | SyntheticGoldenArtifact, path: str | Path
) -> None:
    Path(path).write_text(
        json.dumps(_artifact_payload(artifact), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _artifact_payload(
    artifact: RedTeamSecurityArtifact | SyntheticGoldenArtifact,
) -> dict[str, Any]:
    if isinstance(artifact, RedTeamSecurityArtifact):
        return {
            "artifact_version": artifact.artifact_version,
            "name": artifact.name,
            "fixtures": [
                {
                    "id": fixture.fixture_id,
                    "category": fixture.category,
                    "prompt": fixture.prompt,
                    "expected_behavior": fixture.expected_behavior,
                    "tags": fixture.tags,
                    "metadata": fixture.metadata,
                }
                for fixture in artifact.fixtures
            ],
            "results": [
                {
                    "fixture_id": result.fixture_id,
                    "outcome": result.outcome,
                    "observed_behavior": result.observed_behavior,
                    "score": result.score,
                    "metadata": result.metadata,
                }
                for result in artifact.results
            ],
            "metadata": artifact.metadata,
        }
    return {
        "artifact_version": artifact.artifact_version,
        "name": artifact.name,
        "goldens": [
            {
                "id": golden.golden_id,
                "input": golden.input,
                "expected_output": golden.expected_output,
                "provenance": {
                    "source": golden.provenance.source,
                    "generated_by": golden.provenance.generated_by,
                    "generated_at": golden.provenance.generated_at,
                    "generation_method": golden.provenance.generation_method,
                    "source_artifact_hash": golden.provenance.source_artifact_hash,
                    "metadata": golden.provenance.metadata,
                },
                "tags": golden.tags,
                "metadata": golden.metadata,
            }
            for golden in artifact.goldens
        ],
        "metadata": artifact.metadata,
    }


def _required_boundary_string(payload: dict[str, Any], key: str, owner: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise BoundaryArtifactValidationError(
            f"{owner} {key} must be a non-empty string"
        )
    return value


def _ensure_unique(values: list[str], *, owner: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise BoundaryArtifactValidationError(f"duplicate {owner} id: {value}")
        seen.add(value)


def _ensure_result_fixture_ids(
    results: list[RedTeamSecurityResult],
    fixtures: list[RedTeamSecurityFixture],
) -> None:
    fixture_ids = {fixture.fixture_id for fixture in fixtures}
    for result in results:
        if result.fixture_id not in fixture_ids:
            raise BoundaryArtifactValidationError(
                f"result references unknown fixture id: {result.fixture_id}"
            )


def _tags(payload: dict[str, Any], owner: str) -> list[str]:
    tags = payload.get("tags", [])
    if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
        raise BoundaryArtifactValidationError(f"{owner} tags must be a list of strings")
    return list(tags)


def _metadata(payload: dict[str, Any], owner: str) -> dict[str, Any]:
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise BoundaryArtifactValidationError(f"{owner} metadata must be an object")
    return dict(metadata)


def _ensure_supported_boundary_version(version: str) -> None:
    if version != BOUNDARY_ARTIFACT_VERSION:
        raise BoundaryArtifactValidationError(
            f"unsupported boundary artifact version: {version!r}"
        )
