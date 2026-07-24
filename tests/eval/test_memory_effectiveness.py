from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
from typing import Any

import pytest

from openminion_eval.memory_effectiveness.fixtures import (
    default_memory_effectiveness_cases_path,
)
from openminion_eval import (
    MemoryEffectivenessCase,
    MemoryEffectivenessTrace,
    MemoryExpectation,
    MemoryTraceClaim,
    MemoryTraceToolCall,
    build_memory_scorecard,
    compare_memory_scorecards,
    hash_memory_effectiveness_cases,
    load_memory_effectiveness_cases,
    load_memory_scorecard,
    score_memory_case,
    write_memory_scorecard,
)
from openminion_eval.cli import main


class _TextResource:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._payload = payload

    def read_text(self, encoding: str | None = None) -> str:
        return json.dumps(self._payload)

    def __str__(self) -> str:
        return "memory://effectiveness-cases"


def _repo_convention_case() -> MemoryEffectivenessCase:
    return MemoryEffectivenessCase(
        case_id="repo-convention-test",
        family="repo_convention",
        prompt="Which validation should run?",
        expectations=MemoryExpectation(
            required_saved_ids=("mem-release-check",),
            required_retrieved_ids=("mem-release-check",),
            required_used_ids=("mem-release-check",),
            required_claim_memory_ids=("mem-release-check",),
            required_tool_memory_ids=("mem-release-check",),
            expected_namespace="agent:openminion/project:sophiagraph",
            critical=True,
        ),
    )


def _enabled_trace(
    *, namespace: str = "agent:openminion/project:sophiagraph"
) -> MemoryEffectivenessTrace:
    return MemoryEffectivenessTrace(
        case_id="repo-convention-test",
        run_id="enabled",
        memory_mode="enabled",
        saved_memory_ids=("mem-release-check",),
        retrieved_memory_ids=("mem-release-check",),
        used_memory_ids=("mem-release-check",),
        supporting_claims=(
            MemoryTraceClaim(
                claim="The repo runs make check before release.",
                memory_id="mem-release-check",
            ),
        ),
        tool_calls=(
            MemoryTraceToolCall(
                tool="shell",
                arguments_ref="sha256:release-check",
                memory_ids=("mem-release-check",),
            ),
        ),
        namespace=namespace,
    )


def test_memory_effectiveness_dtos_validate_required_fields() -> None:
    with pytest.raises(ValueError, match="case_id is required"):
        MemoryEffectivenessTrace(case_id="", run_id="run", memory_mode="enabled")
    with pytest.raises(ValueError, match="invalid memory_mode"):
        MemoryEffectivenessTrace(
            case_id="case",
            run_id="run",
            memory_mode="automatic",  # type: ignore[arg-type]
        )
    with pytest.raises(ValueError, match="duplicate ids"):
        MemoryTraceToolCall(
            tool="shell",
            arguments_ref="sha256:x",
            memory_ids=("mem-1", "mem-1"),
        )


def test_memory_effectiveness_fixtures_cover_required_families() -> None:
    cases = load_memory_effectiveness_cases()
    by_family: dict[str, set[str]] = {}
    for case in cases:
        by_family.setdefault(case.family, set()).update(case.tags)

    assert set(by_family) == {
        "preference_learning",
        "repo_convention",
        "procedure_memory",
        "graph_relation_use",
        "stale_and_conflict",
        "privacy_and_export",
        "noisy_memory",
        "negative_no_memory",
    }
    assert all({"positive", "negative"}.issubset(tags) for tags in by_family.values())
    assert hash_memory_effectiveness_cases(cases) == hash_memory_effectiveness_cases(
        load_memory_effectiveness_cases()
    )


def test_memory_effectiveness_loader_accepts_non_filesystem_resource() -> None:
    payload = json.loads(default_memory_effectiveness_cases_path().read_text())

    cases = load_memory_effectiveness_cases(_TextResource(payload))

    assert cases[0].case_id
    assert hash_memory_effectiveness_cases(cases) == hash_memory_effectiveness_cases(
        load_memory_effectiveness_cases()
    )


def test_score_memory_case_passes_complete_enabled_trace() -> None:
    result = score_memory_case(_repo_convention_case(), _enabled_trace())

    assert result.status == "passed"
    assert result.critical_failures == ()
    assert result.overall_score == pytest.approx(1.0)


def test_score_memory_case_reports_partial_save_and_retrieval_misses() -> None:
    result = score_memory_case(
        _repo_convention_case(),
        MemoryEffectivenessTrace(
            case_id="repo-convention-test",
            run_id="enabled",
            memory_mode="enabled",
            saved_memory_ids=(),
            retrieved_memory_ids=(),
            used_memory_ids=("mem-release-check",),
            namespace="agent:openminion/project:sophiagraph",
        ),
    )

    assert result.status == "failed"
    assert "save_missing:mem-release-check" in result.critical_failures
    assert "retrieval_missing:mem-release-check" in result.critical_failures


def test_score_memory_case_blocks_wrong_namespace_leak() -> None:
    result = score_memory_case(
        _repo_convention_case(),
        _enabled_trace(namespace="agent:openminion/project:other"),
    )

    assert result.status == "failed"
    assert result.critical_failures == (
        "namespace_mismatch:agent:openminion/project:other",
    )


def test_score_memory_case_blocks_hallucinated_memory_claim() -> None:
    case = MemoryEffectivenessCase(
        case_id="negative-no-memory",
        family="negative_no_memory",
        prompt="Do you remember this unstored thing?",
        expectations=MemoryExpectation(
            expect_no_memory_claim=True,
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id="negative-no-memory",
            run_id="enabled",
            memory_mode="enabled",
            used_memory_ids=("fake-memory",),
        ),
    )

    assert result.status == "failed"
    assert result.critical_failures == ("hallucinated_memory_claim:fake-memory",)


def test_score_memory_case_blocks_stale_or_private_forbidden_ids() -> None:
    case = MemoryEffectivenessCase(
        case_id="privacy-leak",
        family="privacy_and_export",
        prompt="Publish public notes.",
        expectations=MemoryExpectation(
            forbidden_memory_ids=("mem-private-secret",),
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id="privacy-leak",
            run_id="enabled",
            memory_mode="enabled",
            retrieved_memory_ids=("mem-private-secret",),
        ),
    )

    assert result.status == "failed"
    assert result.critical_failures == ("forbidden_memory_used:mem-private-secret",)


def test_score_memory_case_fails_closed_for_unredacted_live_trace() -> None:
    case = MemoryEffectivenessCase(
        case_id="unsafe-live-trace",
        family="privacy_and_export",
        prompt="Score a sanitized trace.",
        expectations=MemoryExpectation(),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id=case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            redaction_status="unredacted",
            private_trace_refs=("raw-email-1",),
        ),
    )

    assert result.status == "failed"
    assert "trace_not_sanitized:unredacted" in result.critical_failures
    assert "private_trace_refs_present:raw-email-1" in result.critical_failures


def test_scorecard_persistence_and_paired_comparison(tmp_path: Path) -> None:
    case = _repo_convention_case()
    disabled = build_memory_scorecard(
        suite_id="memory",
        run_id="disabled",
        case_results=[
            score_memory_case(
                case,
                MemoryEffectivenessTrace(
                    case_id=case.case_id,
                    run_id="disabled",
                    memory_mode="disabled",
                    namespace="agent:openminion/project:sophiagraph",
                ),
            )
        ],
    )
    enabled = build_memory_scorecard(
        suite_id="memory",
        run_id="enabled",
        case_results=[score_memory_case(case, _enabled_trace())],
    )
    output = write_memory_scorecard(tmp_path / "scorecard.json", enabled)

    loaded = load_memory_scorecard(output)
    comparisons = compare_memory_scorecards(disabled, loaded)

    assert loaded.overall_score == pytest.approx(1.0)
    assert comparisons[0].delta > 0
    assert comparisons[0].improved is True


def test_scorecard_records_operation_location_and_retrieval_metrics() -> None:
    case = MemoryEffectivenessCase(
        case_id="retrieve-ranked-context",
        family="repo_convention",
        prompt="Use the memory convention.",
        expectations=MemoryExpectation(
            required_retrieved_ids=("mem-a", "mem-b"),
            expected_retrieved_order=("mem-a", "mem-b"),
            required_used_ids=("mem-a",),
            expected_operation="retrieve",
            expected_memory_location="context",
            required_context_memory_ids=("mem-a", "mem-b"),
            required_cited_memory_ids=("mem-a",),
            max_unnecessary_memory_calls=1,
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id=case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            retrieved_memory_ids=("noise", "mem-a", "mem-b"),
            used_memory_ids=("mem-a",),
            context_memory_ids=("mem-a", "mem-b"),
            cited_memory_ids=("mem-a",),
            tool_calls=(
                MemoryTraceToolCall(
                    tool="memory.search",
                    arguments_ref="sha256:query",
                    memory_ids=("mem-a",),
                    operation="retrieve",
                    memory_location="context",
                ),
            ),
        ),
    )
    scorecard = build_memory_scorecard(
        suite_id="memory",
        run_id="run",
        case_results=(result,),
        metadata={
            "provider_id": "minimax",
            "model_id": "minimax-m2.7",
            "token_count": 123,
            "cost_usd": 0.25,
            "latency_ms": 456.0,
            "baseline_score": 0.5,
            "regression_threshold": 0.01,
        },
    )

    assert result.status == "passed"
    assert result.operation == "retrieve"
    assert result.memory_location == "context"
    assert result.retrieval_metrics["recall_at_k"] == pytest.approx(1.0)
    assert result.retrieval_metrics["precision_at_k"] == pytest.approx(2 / 3)
    assert result.retrieval_metrics["mrr"] == pytest.approx(0.5)
    assert result.retrieval_metrics["context_order_score"] == pytest.approx(1.0)
    assert scorecard.operation_scores == {"retrieve": pytest.approx(1.0)}
    assert scorecard.memory_location_scores == {"context": pytest.approx(1.0)}
    assert scorecard.efficiency_metadata["provider_id"] == "minimax"
    assert scorecard.baseline_trend["delta"] == pytest.approx(0.5)
    assert "retrieval" in scorecard.public_report_sections


def test_score_memory_case_penalizes_overuse_and_underuse() -> None:
    case = MemoryEffectivenessCase(
        case_id="overuse-underuse",
        family="noisy_memory",
        prompt="Use only the relevant memory.",
        expectations=MemoryExpectation(
            required_retrieved_ids=("mem-a",),
            required_used_ids=("mem-a",),
            max_unnecessary_memory_calls=0,
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id=case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            retrieved_memory_ids=("mem-a", "noise"),
        ),
    )

    assert result.status == "failed"
    assert result.overuse_penalty == pytest.approx(0.5)
    assert result.underuse_penalty == pytest.approx(1.0)
    assert "memory_overuse:0.5" in result.critical_failures
    assert "memory_underuse:1" in result.critical_failures


def test_score_memory_case_enforces_compliance_pack_evidence() -> None:
    case = MemoryEffectivenessCase(
        case_id="compliance-evidence",
        family="privacy_and_export",
        prompt="Export the memory artifact with citations.",
        expectations=MemoryExpectation(
            required_entity_proposal_ids=("entity-1",),
            required_fact_proposal_ids=("fact-1",),
            required_lifecycle_event_ids=("lifecycle-1",),
            required_artifact_ids=("artifact-1",),
            required_citation_spans=("span-1",),
            required_graph_path_ids=("graph-path-1",),
            required_valid_time_refs=("valid-1",),
            required_transaction_time_refs=("tx-1",),
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id=case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            entity_proposal_ids=("entity-1",),
            fact_proposal_ids=("fact-1",),
            lifecycle_event_ids=("lifecycle-1",),
            artifact_ids=("artifact-1",),
            citation_spans=("span-1",),
            graph_path_ids=("graph-path-1",),
            valid_time_refs=("valid-1",),
            transaction_time_refs=("tx-1",),
        ),
    )

    assert result.status == "passed"
    assert result.critical_failures == ()


def test_score_memory_case_fails_missing_compliance_pack_evidence() -> None:
    case = MemoryEffectivenessCase(
        case_id="missing-compliance-evidence",
        family="privacy_and_export",
        prompt="Export the memory artifact with citations.",
        expectations=MemoryExpectation(
            required_entity_proposal_ids=("entity-1",),
            required_citation_spans=("span-1",),
            required_graph_path_ids=("graph-path-1",),
            critical=True,
        ),
    )
    result = score_memory_case(
        case,
        MemoryEffectivenessTrace(
            case_id=case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            entity_proposal_ids=("entity-1",),
        ),
    )

    assert result.status == "failed"
    assert "citation_span_missing:span-1" in result.critical_failures
    assert "graph_path_missing:graph-path-1" in result.critical_failures


def test_score_memory_case_supports_trajectory_match_modes() -> None:
    strict_case = MemoryEffectivenessCase(
        case_id="strict-trajectory",
        family="procedure_memory",
        prompt="Follow the remembered process.",
        expectations=MemoryExpectation(
            expected_trajectory_steps=("discover", "retrieve", "apply"),
            trajectory_match_mode="strict",
            critical=True,
        ),
    )
    unordered_case = MemoryEffectivenessCase(
        case_id="unordered-trajectory",
        family="procedure_memory",
        prompt="Use all remembered process parts.",
        expectations=MemoryExpectation(
            expected_trajectory_steps=("discover", "retrieve", "apply"),
            trajectory_match_mode="unordered",
            critical=True,
        ),
    )

    strict_result = score_memory_case(
        strict_case,
        MemoryEffectivenessTrace(
            case_id=strict_case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            trajectory_steps=("retrieve", "discover", "apply"),
        ),
    )
    unordered_result = score_memory_case(
        unordered_case,
        MemoryEffectivenessTrace(
            case_id=unordered_case.case_id,
            run_id="enabled",
            memory_mode="enabled",
            trajectory_steps=("retrieve", "discover", "apply"),
        ),
    )

    assert strict_result.status == "failed"
    assert "trajectory_mismatch:strict" in strict_result.critical_failures
    assert unordered_result.status == "passed"


def test_memory_effectiveness_cli_scores_trace_artifact(tmp_path: Path, capsys) -> None:
    case = _repo_convention_case()
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "version": "1",
                "cases": [
                    {
                        "case_id": case.case_id,
                        "family": case.family,
                        "prompt": case.prompt,
                        "tags": ["positive", "negative"],
                        "expectations": asdict(case.expectations),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps({"traces": [asdict(_enabled_trace())]}),
        encoding="utf-8",
    )
    out_path = tmp_path / "scorecard.json"

    exit_code = main(
        [
            "memory-effectiveness",
            "score",
            str(trace_path),
            "--cases",
            str(cases_path),
            "--out",
            str(out_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 0
    assert payload["overall_score"] == 1.0
    assert out_path.exists()


def test_memory_effectiveness_cli_preserves_structured_trace_fields(
    tmp_path: Path,
) -> None:
    case = MemoryEffectivenessCase(
        case_id="structured-trace",
        family="graph_relation_use",
        prompt="Use graph-backed memory evidence.",
        expectations=MemoryExpectation(
            required_retrieved_ids=("mem-a",),
            required_context_memory_ids=("mem-a",),
            required_graph_path_ids=("path-a",),
            expected_operation="retrieve",
            expected_memory_location="context",
            critical=True,
        ),
    )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "version": "1",
                "cases": [
                    {
                        "case_id": case.case_id,
                        "family": case.family,
                        "prompt": case.prompt,
                        "tags": ["positive", "negative"],
                        "expectations": asdict(case.expectations),
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "traces": [
                    {
                        "case_id": case.case_id,
                        "run_id": "enabled",
                        "memory_mode": "enabled",
                        "retrieved_memory_ids": ["mem-a"],
                        "context_memory_ids": ["mem-a"],
                        "graph_path_ids": ["path-a"],
                        "provider_id": "minimax",
                        "model_id": "minimax-m2.7",
                        "token_count": 42,
                        "cost_usd": 0.01,
                        "latency_ms": 12.5,
                        "tool_calls": [
                            {
                                "tool": "memory.search",
                                "arguments_ref": "sha256:query",
                                "memory_ids": ["mem-a"],
                                "operation": "retrieve",
                                "memory_location": "context",
                            }
                        ],
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    out_path = tmp_path / "scorecard.json"

    exit_code = main(
        [
            "memory-effectiveness",
            "score",
            str(trace_path),
            "--cases",
            str(cases_path),
            "--out",
            str(out_path),
        ]
    )
    loaded = load_memory_scorecard(out_path)

    assert exit_code == 0
    assert loaded.cases[0].operation == "retrieve"
    assert loaded.cases[0].memory_location == "context"
    assert loaded.operation_scores["retrieve"] == pytest.approx(1.0)


def test_memory_effectiveness_cli_fails_when_trace_matches_no_cases(
    tmp_path: Path, capsys
) -> None:
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(
        json.dumps(
            {
                "version": "1",
                "cases": [
                    {
                        "case_id": "expected-case",
                        "family": "repo_convention",
                        "prompt": "Which validation should run?",
                        "tags": ["positive", "negative"],
                        "expectations": {},
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(
        json.dumps(
            {
                "traces": [
                    {
                        "case_id": "other-case",
                        "run_id": "enabled",
                        "memory_mode": "enabled",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "memory-effectiveness",
            "score",
            str(trace_path),
            "--cases",
            str(cases_path),
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert payload["case_count"] == 0
    assert payload["unmatched_case_count"] == 1


def test_memory_effectiveness_cli_rejects_malformed_trace_items(
    tmp_path: Path,
) -> None:
    trace_path = tmp_path / "trace.json"
    trace_path.write_text(json.dumps({"traces": ["not-an-object"]}), encoding="utf-8")

    with pytest.raises(ValueError, match="trace item 0 must be an object"):
        main(["memory-effectiveness", "score", str(trace_path)])


def test_memory_effectiveness_code_stays_provider_free() -> None:
    root = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "openminion_eval"
        / "memory_effectiveness"
    )
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    forbidden = {
        "llm_judge",
        "semantic_score",
        "infer_preference",
        "infer_relation",
        "auto_classify_privacy",
        "summarize_memory",
        "text_to_graph",
        "openai",
        "anthropic",
        "cohere",
    }
    assert not forbidden.intersection(source)
