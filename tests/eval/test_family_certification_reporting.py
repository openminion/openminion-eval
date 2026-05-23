from openminion_eval.reporting import FamilyCertificationSignal
from tests.eval.provider_certification_matrix import (
    ProviderCertificationManualCell,
    ProviderCertificationTarget,
    build_provider_certification_report,
)


def test_provider_certification_report_accepts_additive_family_signals() -> None:
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
