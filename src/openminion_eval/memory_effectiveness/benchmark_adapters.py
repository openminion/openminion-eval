"""Optional public benchmark adapters for memory-effectiveness cases."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from importlib import resources
from pathlib import Path
from typing import Any, Literal, Mapping, get_args

from openminion_eval.family_support import require_mapping
from openminion_eval.memory_effectiveness.fixtures import case_from_mapping
from openminion_eval.memory_effectiveness.schemas import MemoryEffectivenessCase


MemoryBenchmarkFamily = Literal["locomo", "longmemeval", "beam"]

BENCHMARK_ADAPTER_VERSION = "1"
_BENCHMARK_FAMILIES = get_args(MemoryBenchmarkFamily)
_RESOURCE_PACKAGE = "openminion_eval.memory_effectiveness.resources"
_SAMPLE_MANIFEST_NAMES: dict[MemoryBenchmarkFamily, str] = {
    "locomo": "benchmark_locomo_sample.json",
    "longmemeval": "benchmark_longmemeval_sample.json",
    "beam": "benchmark_beam_sample.json",
}


@dataclass(frozen=True)
class MemoryBenchmarkSource:
    benchmark_family: MemoryBenchmarkFamily
    source_url: str
    source_revision: str
    source_license: str
    fixture_hash: str
    fixture_version: str
    case_category: str

    def __post_init__(self) -> None:
        if self.benchmark_family not in _BENCHMARK_FAMILIES:
            raise ValueError(f"invalid benchmark_family: {self.benchmark_family!r}")
        for field_name in (
            "source_url",
            "source_revision",
            "source_license",
            "fixture_hash",
            "fixture_version",
            "case_category",
        ):
            value = str(getattr(self, field_name) or "").strip()
            if not value:
                raise ValueError(f"{field_name} is required")
            object.__setattr__(self, field_name, value)


@dataclass(frozen=True)
class MemoryBenchmarkImportResult:
    source: MemoryBenchmarkSource
    cases: tuple[MemoryEffectivenessCase, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source, MemoryBenchmarkSource):
            raise TypeError("source must be MemoryBenchmarkSource")
        if not self.cases:
            raise ValueError("benchmark import must include at least one case")
        for case in self.cases:
            if not isinstance(case, MemoryEffectivenessCase):
                raise TypeError("cases must contain MemoryEffectivenessCase")


def default_memory_benchmark_manifest_path(
    family: MemoryBenchmarkFamily,
) -> Path:
    if family not in _SAMPLE_MANIFEST_NAMES:
        raise ValueError(f"invalid benchmark family: {family!r}")
    with resources.as_file(
        resources.files(_RESOURCE_PACKAGE).joinpath(_SAMPLE_MANIFEST_NAMES[family])
    ) as path:
        return path


def load_memory_benchmark_cases(
    path: str | Path,
) -> MemoryBenchmarkImportResult:
    source = Path(path)
    payload = require_mapping(
        json.loads(source.read_text(encoding="utf-8")), context=str(source)
    )
    version = str(payload.get("adapter_version", "") or "").strip()
    if version != BENCHMARK_ADAPTER_VERSION:
        raise ValueError(f"unsupported benchmark adapter version: {version!r}")

    case_payloads = payload.get("cases", ())
    if not isinstance(case_payloads, list):
        raise ValueError("benchmark cases must be a list")

    source_meta = _source_from_mapping(payload, case_payloads=case_payloads)
    cases = tuple(
        case_from_mapping(require_mapping(item, context="benchmark case"))
        for item in case_payloads
    )
    _validate_unique_case_ids(cases)
    return MemoryBenchmarkImportResult(source=source_meta, cases=cases)


def load_packaged_memory_benchmark_sample(
    family: MemoryBenchmarkFamily,
) -> MemoryBenchmarkImportResult:
    return load_memory_benchmark_cases(default_memory_benchmark_manifest_path(family))


def hash_benchmark_manifest_cases(case_payloads: list[Any]) -> str:
    encoded = json.dumps(
        case_payloads,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _source_from_mapping(
    data: Mapping[str, Any],
    *,
    case_payloads: list[Any],
) -> MemoryBenchmarkSource:
    fixture_hash = str(data.get("fixture_hash", "") or "").strip()
    if not fixture_hash:
        raise ValueError("fixture_hash is required")
    actual_hash = hash_benchmark_manifest_cases(case_payloads)
    if fixture_hash != actual_hash:
        raise ValueError(
            "fixture_hash mismatch: "
            f"expected {fixture_hash!r}, computed {actual_hash!r}"
        )
    return MemoryBenchmarkSource(
        benchmark_family=data.get("benchmark_family"),  # type: ignore[arg-type]
        source_url=str(data.get("source_url", "") or "").strip(),
        source_revision=str(data.get("source_revision", "") or "").strip(),
        source_license=str(data.get("source_license", "") or "").strip(),
        fixture_hash=fixture_hash,
        fixture_version=str(data.get("fixture_version", "") or "").strip(),
        case_category=str(data.get("case_category", "") or "").strip(),
    )


def _validate_unique_case_ids(cases: tuple[MemoryEffectivenessCase, ...]) -> None:
    seen: set[str] = set()
    for case in cases:
        if case.case_id in seen:
            raise ValueError(f"duplicate benchmark case_id: {case.case_id!r}")
        seen.add(case.case_id)
