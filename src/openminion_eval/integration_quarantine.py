"""Integration-probe quarantine metadata for source-tree validation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

INTEGRATION_QUARANTINE_VERSION = "1"


@dataclass(frozen=True)
class IntegrationProbeDisposition:
    path: str
    disposition: str
    rationale: str
    tier: str
    requirements: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_integration_quarantine_map(
    root: str | Path,
    *,
    tier: str | None = None,
) -> tuple[IntegrationProbeDisposition, ...]:
    integration_root = Path(root) / "tests" / "eval" / "integration"
    probes = sorted(
        path for path in integration_root.glob("*.py") if path.name != "__init__.py"
    )
    dispositions = tuple(_disposition(root, path) for path in probes)
    if tier is None:
        return dispositions
    return tuple(item for item in dispositions if item.tier == tier)


def integration_probe_tiers() -> tuple[str, ...]:
    return ("local", "host-runtime", "live-provider")


def _disposition(root: str | Path, path: Path) -> IntegrationProbeDisposition:
    tier, requirements = _probe_tier(path.name)
    return IntegrationProbeDisposition(
        path=str(path.relative_to(root)),
        disposition="source-only",
        rationale=(
            "Integration probes are repo-local validation support, not stable "
            "package APIs. Use the tier and requirements fields to decide which "
            "optional gate can run in a given environment."
        ),
        tier=tier,
        requirements=requirements,
    )


def _probe_tier(filename: str) -> tuple[str, tuple[str, ...]]:
    if "live" in filename or filename == "lrsp_live_session.py":
        return (
            "live-provider",
            (
                "OpenMinion sibling checkout",
                "live provider credentials",
                "network access",
            ),
        )
    if filename in _HOST_RUNTIME_PROBES:
        return (
            "host-runtime",
            (
                "OpenMinion sibling checkout",
                "host runtime fixtures",
            ),
        )
    return (
        "local",
        (
            "openminion-eval source tree",
            "pytest",
        ),
    )


_HOST_RUNTIME_PROBES = frozenset(
    {
        "ameb_phase2_runner.py",
        "memory_eval.py",
        "test_ameb_phase2_alvb_retrigger.py",
        "test_ameb_phase2_gtgs_retrigger.py",
        "trace_flywheel.py",
    }
)
