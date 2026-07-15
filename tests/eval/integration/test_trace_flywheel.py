from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from tests.eval.integration.trace_flywheel import (
    build_inference_validation_bundle,
    build_trace_eval_flywheel_report,
    default_inference_validation_output_root,
    run_inference_validation_flywheel,
    write_trace_eval_flywheel_report,
)
from openminion.modules.brain.runtime.improvement.rubric import SelfEvalSubmission


def _check(name: str, ok: bool, details: str = "") -> SimpleNamespace:
    return SimpleNamespace(name=name, ok=ok, details=details)


def test_build_trace_eval_flywheel_report_passes_all_checks(tmp_path: Path) -> None:
    bundle = build_inference_validation_bundle(
        check_results=(
            _check("import_smoke", True, "imports ok"),
            _check("retrieve_debug", True, "retrieve ok"),
            _check("chat_single_turn", True, "chat ok"),
            _check("gateway_single_turn", True, "gateway ok"),
        ),
        artifact_output_root=tmp_path,
        config_path=tmp_path / "config.json",
        agent_id="eval-agent",
        session_prefix="tefc",
    )

    report = build_trace_eval_flywheel_report(bundle)

    assert report.all_passed is True
    assert report.summary.passed is True
    assert report.summary.average_score == 1.0
    assert report.rubric.scorer_name == "exact_match"
    assert (
        report.summary.results[0].metadata["trace_source_kind"]
        == "workflow_smoke_checks"
    )
    assert (
        report.summary.results[0].metadata["determinism_class"] == "deterministic_local"
    )


def test_build_trace_eval_flywheel_report_records_failed_checks(tmp_path: Path) -> None:
    bundle = build_inference_validation_bundle(
        check_results=(
            _check("import_smoke", True, "imports ok"),
            _check("retrieve_debug", False, "retrieve failed"),
            _check("chat_single_turn", True, "chat ok"),
        ),
        artifact_output_root=tmp_path,
        config_path=tmp_path / "config.json",
        agent_id="eval-agent",
        session_prefix="tefc",
    )

    report = build_trace_eval_flywheel_report(bundle)

    assert report.all_passed is False
    assert report.summary.passed is False
    assert report.summary.average_score == 2 / 3
    assert report.summary.results[1].actual == "fail"
    assert report.summary.results[1].metadata["details"] == "retrieve failed"


def test_run_inference_validation_flywheel_collects_smoke_results(
    monkeypatch,
    tmp_path: Path,
) -> None:
    from tests.eval.integration import trace_flywheel

    monkeypatch.setattr(
        trace_flywheel,
        "_collect_inference_validation_results",
        lambda **_: (
            _check("import_smoke", True, "imports ok"),
            _check("retrieve_debug", True, "retrieve ok"),
            _check("chat_single_turn", True, "chat ok"),
            _check("gateway_single_turn", False, "gateway failed"),
        ),
    )

    report = run_inference_validation_flywheel(
        py_bin=tmp_path / "python3.11",
        openminion_dir=tmp_path / "openminion",
        repo_root=tmp_path / "framework",
        config_path=tmp_path / "config.json",
        agent_id="eval-agent",
        session_prefix="tefc",
        output_root=tmp_path / "generated",
    )

    assert report.bundle.workflow_id == "inference_validation_smoke"
    assert report.bundle.artifact_output_root.endswith("generated")
    assert report.summary.total_turns == 4
    assert report.all_passed is False


def test_write_trace_eval_flywheel_report_persists_json(tmp_path: Path) -> None:
    bundle = build_inference_validation_bundle(
        check_results=(_check("import_smoke", True, "imports ok"),),
        artifact_output_root=tmp_path,
        config_path=tmp_path / "config.json",
        agent_id="eval-agent",
        session_prefix="tefc",
    )
    report = build_trace_eval_flywheel_report(bundle)

    output_path = write_trace_eval_flywheel_report(tmp_path / "summary.json", report)

    assert output_path.exists() is True
    payload = output_path.read_text(encoding="utf-8")
    assert '"workflow_id": "inference_validation_smoke"' in payload


def test_default_inference_validation_output_root_uses_generated_root(
    tmp_path: Path,
) -> None:
    output_root = default_inference_validation_output_root(tmp_path)
    assert str(output_root).endswith("trace-eval-flywheel/inference-validation-smoke")


def test_bundle_optionally_carries_one_self_eval_submission(tmp_path: Path) -> None:
    bundle = build_inference_validation_bundle(
        check_results=(_check("import_smoke", True, "imports ok"),),
        artifact_output_root=tmp_path,
        config_path=tmp_path / "config.json",
        agent_id="eval-agent",
        session_prefix="tefc",
    )
    self_eval = SelfEvalSubmission(
        rubric_id="research_quality_v1",
        per_criterion_passed={
            "goal_satisfied": True,
            "evidence_collected": True,
            "risk_disclosed": False,
        },
        evidence_refs=["memory:1"],
    )
    enriched_bundle = bundle.__class__(
        **{**bundle.__dict__, "self_eval_submission": self_eval}
    )

    assert enriched_bundle.self_eval_submission == self_eval
    report = build_trace_eval_flywheel_report(enriched_bundle)
    assert report.bundle.self_eval_submission == self_eval
