from __future__ import annotations

from pathlib import Path

from tests.eval.provider_certification_matrix import (
    build_provider_certification_report,
    load_provider_certification_manual_cells,
    load_provider_certification_targets,
)


def test_provider_certification_inventory_and_manual_cells_load_cleanly() -> None:
    inventory_version, targets = load_provider_certification_targets()
    manual_version, manual_cells = load_provider_certification_manual_cells()

    assert inventory_version == "1"
    assert manual_version == "1"
    assert len(targets) == 12
    assert {target.target_id for target in targets} == {
        "minimax-m2-5",
        "minimax-m2-7",
        "ollamacloud-glm-5",
        "ollamacloud-minimax-m2-5",
        "ollamacloud-minimax-m2-7",
        "ollamacloud-kimi-k2-5",
        "ollamacloud-qwen3-5-397b",
        "openrouter-claude-haiku-3",
        "openrouter-claude-haiku-4-5",
        "openrouter-gpt-4o",
        "openrouter-gpt-5-4-mini",
        "openrouter-minimax-m2-7",
    }
    assert any(
        cell.target_id == "minimax-m2-5" and cell.dimension == "confirmation_policy"
        for cell in manual_cells
    )


def test_build_provider_certification_report_covers_all_inventory_targets() -> None:
    inventory_version, targets = load_provider_certification_targets()
    manual_version, manual_cells = load_provider_certification_manual_cells()

    report = build_provider_certification_report(
        inventory_version=inventory_version,
        targets=targets,
        manual_evidence_version=manual_version,
        manual_cells=manual_cells,
    )

    assert report.summary["target_count"] == 12
    assert len(report.rows) == 12
    row_index = {row.target_id: row for row in report.rows}

    assert row_index["minimax-m2-5"].explicit_tool.status == "green"
    assert row_index["minimax-m2-5"].confirmation_policy.status == "green"
    assert row_index["minimax-m2-5"].output_quality.status == "weak"
    assert row_index["minimax-m2-7"].output_quality.status == "adequate"
    assert row_index["openrouter-gpt-4o"].output_quality.status == "strong"
    assert row_index["openrouter-gpt-4o"].nl_named_skill.status == "green"
    assert row_index["ollamacloud-minimax-m2-7"].nl_named_skill.status == "gapped"
    assert row_index["ollamacloud-minimax-m2-5"].nl_named_skill.status == "untested"
    assert row_index["openrouter-claude-haiku-3"].explicit_tool.status == "green"
    assert row_index["ollamacloud-kimi-k2-5"].access.status == "ready"
    assert row_index["ollamacloud-kimi-k2-5"].skill_routing.status == "untested"


def test_provider_certification_manual_evidence_paths_exist() -> None:
    _version, manual_cells = load_provider_certification_manual_cells()
    for cell in manual_cells:
        assert Path(cell.evidence_path).exists()
