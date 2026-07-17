"""Generate or verify the committed memory eval baseline snapshot."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import tempfile

from runner_support import configure_repo_paths

configure_repo_paths()

from tests.eval.integration.memory_eval import (  # noqa: E402
    MemoryEvalEngineConfig,
    MemoryEvalHarness,
)
from openminion.base.config import OpenMinionConfig  # noqa: E402
from openminion.modules.memory.config import from_base_config  # noqa: E402
from openminion.modules.memory.service import MemoryService  # noqa: E402
from openminion.services.agent.memory.gateway_adapter import (  # noqa: E402
    MemoryServiceGatewayAdapter,
)

_VOLATILE_LATENCY_METRICS = frozenset(
    {
        "latency_regression.capsule_build_p95_ms",
        "latency_regression.retrieval_p95_ms",
        "latency_regression.search_p95_ms",
    }
)


def _adapter_factory(
    service: MemoryService,
    engine_config: MemoryEvalEngineConfig,
) -> MemoryServiceGatewayAdapter:
    return MemoryServiceGatewayAdapter(
        service,
        agent_id=engine_config.agent_id,
        project_id=engine_config.project_id,
        memory_config=engine_config.memory_config,
        **engine_config.adapter_kwargs,
    )


def _runtime_roots(repo_root: Path) -> tuple[Path, Path]:
    scratch_root = repo_root / "workspace-tmp" / "memory-eval-baseline"
    return (
        scratch_root / "openminion-home",
        scratch_root / "openminion-data",
    )


def _stable_snapshot(payload: dict) -> dict:
    stable = deepcopy(payload)
    stable.pop("timestamp", None)
    scores = (
        stable.get("dimensions", {}).get("latency_regression", {}).get("scores", {})
    )
    for scenario_scores in scores.values():
        for metric_name in _VOLATILE_LATENCY_METRICS:
            scenario_scores.pop(metric_name, None)
    return stable


def _build_snapshot(
    *,
    output_path: Path,
    repo_root: Path,
    fixture_root: Path,
) -> None:
    harness = MemoryEvalHarness()
    home_root, data_root = _runtime_roots(repo_root)
    memory_config = from_base_config(
        base_config=OpenMinionConfig(),
        home_root=home_root,
        data_root=data_root,
    )
    scenarios = []
    for relative_dir in (
        "cross_session_recall",
        "paraphrase_retrieval",
        "stale_suppression",
        "contradiction_leak",
        "capsule_precision",
        "latency",
    ):
        scenarios.extend(harness.loader.load_directory(fixture_root / relative_dir))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    harness.write_snapshot(
        output_path,
        scenarios,
        engine_config=MemoryEvalEngineConfig(
            adapter_factory=_adapter_factory,
            memory_config=memory_config,
        ),
        commit="workspace",
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate or verify the memory eval baseline snapshot."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if regenerating would change the committed baseline.",
    )
    args = parser.parse_args()

    openminion_root = Path(__file__).resolve().parents[3]
    repo_root = openminion_root.parent
    fixture_root = openminion_root / "tests" / "eval" / "fixtures" / "memory"
    output_path = (
        openminion_root
        / "tests"
        / "eval"
        / "baselines"
        / "memory_quality_baseline.json"
    )
    if args.check:
        if not output_path.exists():
            print(f"[check] missing baseline: {output_path}")
            return 1
        with tempfile.TemporaryDirectory() as tmpdir:
            candidate_path = Path(tmpdir) / output_path.name
            _build_snapshot(
                output_path=candidate_path,
                repo_root=repo_root,
                fixture_root=fixture_root,
            )
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            baseline = json.loads(output_path.read_text(encoding="utf-8"))
            if _stable_snapshot(candidate) != _stable_snapshot(baseline):
                print(f"[check] baseline differs: {output_path}")
                return 1
        print(f"[ok] baseline up to date: {output_path}")
        return 0

    _build_snapshot(
        output_path=output_path,
        repo_root=repo_root,
        fixture_root=fixture_root,
    )
    print(f"[ok] wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
