from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path

import pytest

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
