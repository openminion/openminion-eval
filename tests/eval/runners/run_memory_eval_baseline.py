"""Generate or verify the committed memory eval baseline snapshot."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import tempfile

PACKAGE_ROOT = Path(__file__).resolve().parents[3]  # openminion-eval/
PACKAGE_SRC = PACKAGE_ROOT / "src"
FRAMEWORK_ROOT = PACKAGE_ROOT.parent  # agent-frameworks/
OPENMINION_SRC = FRAMEWORK_ROOT / "openminion" / "src"
for path in (PACKAGE_SRC, PACKAGE_ROOT, OPENMINION_SRC):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

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


def _build_snapshot(
    *,
    output_path: Path,
    repo_root: Path,
    fixture_root: Path,
) -> None:
    harness = MemoryEvalHarness()
    memory_config = from_base_config(
        base_config=OpenMinionConfig(),
        home_root=repo_root / ".tmp" / "openminion-home",
        data_root=repo_root / ".tmp" / "openminion-data",
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
            if candidate_path.read_text(encoding="utf-8") != output_path.read_text(
                encoding="utf-8"
            ):
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
