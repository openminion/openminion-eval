"""Versioned dataset loaders for generic eval suites."""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Any

from openminion_eval.schemas import EvalDataset, EvalDatasetCase, EvalTranscript


DATASET_VERSION = "1"


class EvalDatasetValidationError(ValueError):
    """Raised when an eval dataset artifact does not match the public contract."""


def load_eval_dataset(path: str | Path) -> EvalDataset:
    source = Path(path)
    if source.suffix == ".jsonl":
        return load_eval_dataset_jsonl(source)
    return load_eval_dataset_json(source)


def load_eval_dataset_json(path: str | Path) -> EvalDataset:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EvalDatasetValidationError("dataset JSON must be an object")
    version = _required_string(payload, "dataset_version", "dataset")
    _ensure_supported_version(version)
    name = _required_string(payload, "name", "dataset")
    raw_cases = payload.get("cases", payload.get("transcripts"))
    if not isinstance(raw_cases, list):
        raise EvalDatasetValidationError("dataset cases must be a list")
    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict):
        raise EvalDatasetValidationError("dataset metadata must be an object")
    return _build_dataset(version=version, name=name, records=raw_cases, metadata=metadata)


def load_eval_dataset_jsonl(
    path: str | Path,
    *,
    name: str | None = None,
    dataset_version: str = DATASET_VERSION,
    metadata: dict[str, Any] | None = None,
) -> EvalDataset:
    _ensure_supported_version(dataset_version)
    records = []
    for index, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise EvalDatasetValidationError(
                f"invalid JSONL record at line {index}: {exc.msg}"
            ) from exc
        if not isinstance(record, dict):
            raise EvalDatasetValidationError(
                f"JSONL record at line {index} must be an object"
            )
        records.append(record)
    return _build_dataset(
        version=dataset_version,
        name=name or Path(path).stem,
        records=records,
        metadata=dict(metadata or {}),
    )


def hash_eval_dataset(dataset: EvalDataset) -> str:
    payload = {
        "dataset_version": dataset.dataset_version,
        "name": dataset.name,
        "cases": [
            {
                "id": case.case_id,
                "transcript": asdict(case.transcript),
            }
            for case in dataset.cases
        ],
        "metadata": dataset.metadata,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _build_dataset(
    *,
    version: str,
    name: str,
    records: list[Any],
    metadata: dict[str, Any],
) -> EvalDataset:
    seen: set[str] = set()
    cases: list[EvalDatasetCase] = []
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise EvalDatasetValidationError(f"case {index} must be an object")
        case_id = _required_string(record, "id", f"case {index}")
        if case_id in seen:
            raise EvalDatasetValidationError(f"duplicate case id: {case_id}")
        seen.add(case_id)
        transcript_name = record.get("name", case_id)
        if not isinstance(transcript_name, str) or not transcript_name:
            raise EvalDatasetValidationError(f"case {case_id} name must be a string")
        turns = record.get("turns")
        if not isinstance(turns, list):
            raise EvalDatasetValidationError(f"case {case_id} turns must be a list")
        tags = record.get("tags", [])
        if not isinstance(tags, list) or not all(isinstance(tag, str) for tag in tags):
            raise EvalDatasetValidationError(
                f"case {case_id} tags must be a list of strings"
            )
        cases.append(
            EvalDatasetCase(
                case_id=case_id,
                transcript=EvalTranscript(
                    name=transcript_name,
                    turns=turns,
                    tags=list(tags),
                ),
            )
        )
    return EvalDataset(
        dataset_version=version,
        name=name,
        cases=cases,
        metadata=metadata,
    )


def _required_string(payload: dict[str, Any], key: str, owner: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise EvalDatasetValidationError(f"{owner} {key} must be a non-empty string")
    return value


def _ensure_supported_version(version: str) -> None:
    if version != DATASET_VERSION:
        raise EvalDatasetValidationError(f"unsupported dataset version: {version!r}")
