from __future__ import annotations

from pathlib import Path

from openminion_eval.integration_quarantine import build_integration_quarantine_map


def test_integration_quarantine_map_covers_every_probe() -> None:
    root = Path(__file__).resolve().parents[2]
    expected = sorted(
        str(path.relative_to(root))
        for path in (root / "tests" / "eval" / "integration").glob("*.py")
        if path.name != "__init__.py"
    )

    dispositions = build_integration_quarantine_map(root)

    assert [item.path for item in dispositions] == expected
    assert {item.disposition for item in dispositions} == {"source-only"}
    assert all("not stable package APIs" in item.rationale for item in dispositions)
