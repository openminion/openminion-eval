from openminion_eval.reporting import FamilyCertificationSignal
from tests.eval import provider_certification_matrix as certification_matrix
from tests.eval.provider_certification_matrix import (
    ProviderCertificationManualCell,
    ProviderCertificationTarget,
    build_provider_certification_report,
)


def test_provider_certification_report_accepts_additive_family_signals(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        certification_matrix,
        "_skill_provider_index",
        lambda: ({}, "fixture://skill-provider"),
    )
    monkeypatch.setattr(
        certification_matrix,
        "_nnse_summary_index",
        lambda: ({}, "fixture://nnse"),
    )
    monkeypatch.setattr(
        certification_matrix,
        "_quality_summary_index",
        lambda target_set: ({}, f"fixture://quality/{target_set}"),
    )
    monkeypatch.setattr(
        certification_matrix,
        "_latest_dense_routing_artifact",
        lambda _target_id: None,
    )

    target = ProviderCertificationTarget(
        target_id="demo-target",
        provider_family="demo",
        provider_lane="demo",
        model_label="Demo",
    )
    manual_cells = (
        ProviderCertificationManualCell(
            target_id="demo-target",
            dimension="confirmation_policy",
            status="untested",
            evidence_path=__file__,
            note="manual placeholder",
        ),
    )
    report = build_provider_certification_report(
        inventory_version="1",
        targets=(target,),
        manual_evidence_version="1",
        manual_cells=manual_cells,
        family_signals=(
            FamilyCertificationSignal(
                target_id="demo-target",
                dimension="explicit_tool",
                status="green",
                evidence_path=__file__,
                note="tool family report",
            ),
        ),
    )
    row = report.rows[0]
    assert row.explicit_tool.status == "green"
    assert __file__ in row.explicit_tool.evidence_paths
    assert "tool family report" in row.explicit_tool.notes
