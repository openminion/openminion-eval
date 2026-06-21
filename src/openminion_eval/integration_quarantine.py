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

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def build_integration_quarantine_map(
    root: str | Path,
) -> tuple[IntegrationProbeDisposition, ...]:
    integration_root = Path(root) / "tests" / "eval" / "integration"
    probes = sorted(
        path for path in integration_root.glob("*.py") if path.name != "__init__.py"
    )
    return tuple(
        IntegrationProbeDisposition(
            path=str(path.relative_to(root)),
            disposition="source-only",
            rationale=(
                "Integration probes depend on host runtime state, live credentials, "
                "or source-tree fixtures and are not stable package APIs."
            ),
        )
        for path in probes
    )
