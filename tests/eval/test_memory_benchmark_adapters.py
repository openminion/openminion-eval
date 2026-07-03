from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

import openminion_eval
from openminion_eval.memory_effectiveness import benchmark_adapters
from openminion_eval import (
    BENCHMARK_ADAPTER_VERSION,
    MemoryBenchmarkSource,
    MemoryEffectivenessCase,
    default_memory_benchmark_manifest_path,
    hash_benchmark_manifest_cases,
    load_memory_benchmark_cases,
    load_packaged_memory_benchmark_sample,
)


class _TextResource:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read_text(self, encoding: str | None = None) -> str:
        return json.dumps(self._payload)

    def __str__(self) -> str:
        return "memory://benchmark-resource"


def _manifest_payload(family: str = "locomo") -> dict[str, object]:
    return json.loads(default_memory_benchmark_manifest_path(family).read_text())


def _write_manifest(tmp_path: Path, payload: dict[str, object]) -> Path:
    path = tmp_path / "benchmark.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return path


def test_packaged_benchmark_samples_load_as_memory_cases() -> None:
    for family in ("locomo", "longmemeval", "beam"):
        result = load_packaged_memory_benchmark_sample(family)

        assert result.source.benchmark_family == family
        assert result.source.source_url.startswith("https://")
        assert result.source.source_revision
        assert result.source.source_license
        assert result.source.fixture_version
        assert result.cases
        assert all(isinstance(case, MemoryEffectivenessCase) for case in result.cases)
        assert all("benchmark_sample" in case.tags for case in result.cases)


def test_packaged_benchmark_loader_accepts_non_filesystem_resource(monkeypatch) -> None:
    payload = _manifest_payload("locomo")
    monkeypatch.setattr(
        benchmark_adapters,
        "default_memory_benchmark_manifest_path",
        lambda family: _TextResource(payload),
    )

    result = load_packaged_memory_benchmark_sample("locomo")

    assert result.source.benchmark_family == "locomo"
    assert result.cases[0].case_id


def test_packaged_benchmark_hash_matches_case_payloads() -> None:
    payload = _manifest_payload("beam")

    assert payload["fixture_hash"] == hash_benchmark_manifest_cases(payload["cases"])


def test_root_exports_include_benchmark_adapter_surface() -> None:
    assert BENCHMARK_ADAPTER_VERSION == "1"
    assert MemoryBenchmarkSource.__name__ == "MemoryBenchmarkSource"
    assert openminion_eval.load_packaged_memory_benchmark_sample is (
        load_packaged_memory_benchmark_sample
    )


def test_benchmark_loader_rejects_fixture_hash_mismatch(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["fixture_hash"] = "bad"

    with pytest.raises(ValueError, match="fixture_hash mismatch"):
        load_memory_benchmark_cases(_write_manifest(tmp_path, payload))


def test_benchmark_loader_rejects_missing_fixture_hash(tmp_path: Path) -> None:
    payload = _manifest_payload()
    del payload["fixture_hash"]

    with pytest.raises(ValueError, match="fixture_hash is required"):
        load_memory_benchmark_cases(_write_manifest(tmp_path, payload))


def test_benchmark_loader_rejects_missing_source_license(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["source_license"] = ""

    with pytest.raises(ValueError, match="source_license is required"):
        load_memory_benchmark_cases(_write_manifest(tmp_path, payload))


def test_benchmark_loader_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    payload = _manifest_payload()
    cases = list(payload["cases"])
    cases.append(dict(cases[0]))
    payload["cases"] = cases
    payload["fixture_hash"] = hash_benchmark_manifest_cases(cases)

    with pytest.raises(ValueError, match="duplicate benchmark case_id"):
        load_memory_benchmark_cases(_write_manifest(tmp_path, payload))


def test_benchmark_loader_rejects_unsupported_adapter_version(tmp_path: Path) -> None:
    payload = _manifest_payload()
    payload["adapter_version"] = "99"

    with pytest.raises(ValueError, match="unsupported benchmark adapter version"):
        load_memory_benchmark_cases(_write_manifest(tmp_path, payload))


def test_benchmark_adapter_code_has_no_provider_or_judge_path() -> None:
    source_root = Path(__file__).resolve().parents[2] / "src" / "openminion_eval"
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (source_root / "memory_effectiveness").glob("*.py")
    )

    forbidden = {
        "generate_ground_truth",
        "infer_answer",
        "semantic_match",
        "llm_judge",
        "openai",
        "anthropic",
    }
    source_lower = source.lower()
    assert not [token for token in forbidden if token in source_lower]
