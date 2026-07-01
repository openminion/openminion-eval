from __future__ import annotations

import json
from pathlib import Path

from tests.eval import provider_certification_matrix as certification_matrix
from tests.eval.provider_certification_matrix import (
    build_provider_certification_report,
    load_provider_certification_manual_cells,
    load_provider_certification_targets,
    openminion_root,
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


def _write_quality_report(
    tmp_path: Path,
    name: str,
    *,
    scenario_count: int,
    numbered: int,
    verification: int,
    guardrail: int,
) -> str:
    report_path = tmp_path / f"{name}.json"
    report_path.write_text(
        json.dumps(
            {
                "summary": {
                    "scenario_count": scenario_count,
                    "responses_with_numbered_steps": numbered,
                    "responses_with_verification_language": verification,
                    "responses_with_guardrail_language": guardrail,
                }
            }
        ),
        encoding="utf-8",
    )
    return str(report_path)


def test_build_provider_certification_report_covers_all_inventory_targets(
    monkeypatch, tmp_path: Path
) -> None:
    inventory_version, targets = load_provider_certification_targets()
    manual_version, manual_cells = load_provider_certification_manual_cells()
    quality_reports = {
        "weak": _write_quality_report(
            tmp_path,
            "quality-weak",
            scenario_count=10,
            numbered=4,
            verification=4,
            guardrail=4,
        ),
        "adequate": _write_quality_report(
            tmp_path,
            "quality-adequate",
            scenario_count=10,
            numbered=6,
            verification=6,
            guardrail=6,
        ),
        "strong": _write_quality_report(
            tmp_path,
            "quality-strong",
            scenario_count=10,
            numbered=8,
            verification=8,
            guardrail=8,
        ),
    }
    monkeypatch.setattr(
        certification_matrix,
        "_skill_provider_index",
        lambda: (
            {
                "minimax-m2-5": {"status": "pass"},
                "openrouter-claude-haiku-3": {"status": "pass"},
                "ollamacloud-kimi-k2-5": {"status": "pass"},
            },
            "fixture://skill-provider",
        ),
    )
    monkeypatch.setattr(
        certification_matrix,
        "_nnse_summary_index",
        lambda: (
            {
                "openrouter-gpt-4o": {
                    "attempt_count": 3,
                    "selection_accuracy_count": 3,
                    "wrong_skill_count": 0,
                    "empty_fallback_count": 0,
                    "report_path": "fixture://nnse/openrouter-gpt-4o",
                },
                "ollamacloud-minimax-m2-7": {
                    "attempt_count": 3,
                    "selection_accuracy_count": 2,
                    "wrong_skill_count": 1,
                    "empty_fallback_count": 0,
                    "report_path": "fixture://nnse/ollamacloud-minimax-m2-7",
                },
            },
            "fixture://nnse",
        ),
    )

    def _quality_index(target_set: str) -> tuple[dict[str, dict[str, str]], str]:
        if target_set == "official":
            return (
                {
                    "minimax-m2-5": {"report_path": quality_reports["weak"]},
                    "minimax-m2-7": {"report_path": quality_reports["adequate"]},
                },
                "fixture://quality/official",
            )
        return (
            {
                "openrouter-gpt-4o": {"report_path": quality_reports["strong"]},
            },
            "fixture://quality/representative",
        )

    monkeypatch.setattr(
        certification_matrix,
        "_quality_summary_index",
        _quality_index,
    )
    monkeypatch.setattr(
        certification_matrix,
        "_latest_dense_routing_artifact",
        lambda _target_id: None,
    )

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
        assert not Path(cell.evidence_path).is_absolute()
        assert (openminion_root() / cell.evidence_path).exists()
