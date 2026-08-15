"""CLI support for memory-effectiveness trace scoring."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Callable

from openminion_eval.memory_effectiveness.delegated_memory import (
    DelegatedMemoryEvalTrace,
    build_delegated_memory_scorecard_diff,
    build_delegated_memory_scorecard,
    load_delegated_memory_cases,
    load_delegated_memory_scorecard,
    write_delegated_memory_scorecard_diff,
    write_delegated_memory_scorecard,
)
from openminion_eval.memory_effectiveness.fixtures import (
    load_memory_effectiveness_cases,
)
from openminion_eval.memory_effectiveness.artifact_payloads import (
    json_objects,
    string_tuple,
)
from openminion_eval.memory_effectiveness.schemas import (
    MemoryEffectivenessTrace,
    MemoryTraceClaim,
    MemoryTraceMode,
    MemoryTraceRedactionStatus,
    MemoryTraceToolCall,
)
from openminion_eval.memory_effectiveness.scoring import (
    build_memory_scorecard,
    score_memory_case,
    write_memory_scorecard,
)


def add_memory_effectiveness_parser(subparsers: Any) -> None:
    memory_parser = subparsers.add_parser(
        "memory-effectiveness",
        help="score structured memory-effectiveness trace artifacts",
    )
    memory_subparsers = memory_parser.add_subparsers(
        dest="memory_command", required=True
    )
    score_parser = memory_subparsers.add_parser(
        "score",
        help="score a trace JSON artifact against packaged memory cases",
    )
    score_parser.add_argument("trace", type=Path, help="trace JSON file")
    score_parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="optional case fixture JSON; defaults to packaged cases",
    )
    score_parser.add_argument(
        "--suite-id",
        default="openminion-sophiagraph-memory-effectiveness",
        help="suite id for scorecard artifacts",
    )
    score_parser.add_argument(
        "--run-id",
        default="memory-effectiveness-local",
        help="run id for scorecard artifacts",
    )
    score_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write scorecard JSON artifact to PATH",
    )
    score_parser.set_defaults(func=memory_score_command)

    delegated_parser = memory_subparsers.add_parser(
        "delegated-score",
        help="score delegated-memory trace JSON artifacts",
    )
    delegated_parser.add_argument("trace", type=Path, help="delegated trace JSON file")
    delegated_parser.add_argument(
        "--cases",
        type=Path,
        default=None,
        help="optional delegated case fixture JSON; defaults to packaged cases",
    )
    delegated_parser.add_argument(
        "--suite-id",
        default="delegated-multi-agent-memory.v1",
        help="suite id for scorecard artifacts",
    )
    delegated_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write delegated scorecard JSON artifact to PATH",
    )
    delegated_parser.set_defaults(func=delegated_memory_score_command)

    delegated_diff_parser = memory_subparsers.add_parser(
        "delegated-diff",
        help="compare delegated-memory scorecard artifacts",
    )
    delegated_diff_parser.add_argument("previous", type=Path)
    delegated_diff_parser.add_argument("current", type=Path)
    delegated_diff_parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="write delegated-memory diff JSON artifact to PATH",
    )
    delegated_diff_parser.set_defaults(func=delegated_memory_diff_command)


def memory_score_command(args: argparse.Namespace) -> int:
    return _run_memory_command(lambda: _score_memory_trace(args))


def delegated_memory_score_command(args: argparse.Namespace) -> int:
    return _run_memory_command(lambda: _score_delegated_memory_trace(args))


def delegated_memory_diff_command(args: argparse.Namespace) -> int:
    return _run_memory_command(lambda: _diff_delegated_memory_scorecards(args))


def _run_memory_command(command: Callable[[], int]) -> int:
    try:
        return command()
    except (OSError, TypeError, ValueError) as exc:
        _write_error(f"memory-effectiveness error: {exc}")
        return 2


def _score_memory_trace(args: argparse.Namespace) -> int:
    cases = load_memory_effectiveness_cases(args.cases)
    traces = _load_memory_traces(args.trace)
    traces_by_case = {trace.case_id: trace for trace in traces}
    results = [
        score_memory_case(case, traces_by_case[case.case_id])
        for case in cases
        if case.case_id in traces_by_case
    ]
    unmatched_cases = tuple(
        case.case_id for case in cases if case.case_id not in traces_by_case
    )
    scorecard = build_memory_scorecard(
        suite_id=args.suite_id,
        run_id=args.run_id,
        case_results=results,
        metadata={"trace": str(args.trace), "unmatched_cases": unmatched_cases},
    )
    if args.out is not None:
        write_memory_scorecard(args.out, scorecard)
    _write_json(
        {
            "suite_id": scorecard.suite_id,
            "run_id": scorecard.run_id,
            "case_count": len(scorecard.cases),
            "unmatched_case_count": len(unmatched_cases),
            "overall_score": scorecard.overall_score,
            "critical_failure_count": len(scorecard.critical_failures),
            "artifact": None if args.out is None else str(args.out),
        }
    )
    return 1 if scorecard.critical_failures or unmatched_cases else 0


def _score_delegated_memory_trace(args: argparse.Namespace) -> int:
    cases = load_delegated_memory_cases(args.cases)
    traces = _load_delegated_memory_traces(args.trace)
    scorecard = build_delegated_memory_scorecard(
        cases,
        traces,
        suite_id=args.suite_id,
    )
    if args.out is not None:
        write_delegated_memory_scorecard(args.out, scorecard)
    _write_json(
        {
            "suite_id": scorecard.suite_id,
            "case_count": len(scorecard.results),
            "passed": scorecard.passed,
            "utility_recall": scorecard.utility_recall,
            "critical_failure_count": len(scorecard.critical_failures),
            "artifact": None if args.out is None else str(args.out),
        }
    )
    return 0 if scorecard.passed else 1


def _diff_delegated_memory_scorecards(args: argparse.Namespace) -> int:
    previous = load_delegated_memory_scorecard(args.previous)
    current = load_delegated_memory_scorecard(args.current)
    diff = build_delegated_memory_scorecard_diff(previous, current)
    payload = asdict(diff)
    if args.out is None:
        _write_json(payload)
    else:
        write_delegated_memory_scorecard_diff(args.out, diff)
    regressions = {"regressed", "missing_case"}
    current_failures = any(
        item.current_passed is False and item.category != "improved"
        for item in diff.entries
    )
    return 1 if regressions.intersection(diff.categories) or current_failures else 0


def _load_memory_traces(path: Path) -> tuple[MemoryEffectivenessTrace, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    items = _trace_items(payload)
    traces: list[MemoryEffectivenessTrace] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"trace item {index} must be an object")
        traces.append(_memory_trace_from_dict(item))
    return tuple(traces)


def _load_delegated_memory_traces(path: Path) -> tuple[DelegatedMemoryEvalTrace, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    traces: list[DelegatedMemoryEvalTrace] = []
    for index, item in enumerate(_trace_items(payload)):
        if not isinstance(item, dict):
            raise TypeError(f"trace item {index} must be an object")
        traces.append(_delegated_memory_trace_from_dict(item))
    return tuple(traces)


def _trace_items(payload: object) -> list[Any]:
    if isinstance(payload, dict) and "traces" in payload:
        items = payload["traces"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("trace artifact must be a list or contain a 'traces' list")
    if not isinstance(items, list):
        raise TypeError("trace artifact 'traces' value must be a list")
    return items


def _memory_trace_from_dict(data: dict[str, Any]) -> MemoryEffectivenessTrace:
    supporting_claims = data.get("supporting_claims", ())
    tool_calls = data.get("tool_calls", ())
    if not isinstance(supporting_claims, list | tuple):
        raise TypeError("supporting_claims must be a list")
    if not isinstance(tool_calls, list | tuple):
        raise TypeError("tool_calls must be a list")
    return MemoryEffectivenessTrace(
        case_id=str(data.get("case_id", "")),
        run_id=str(data.get("run_id", "")),
        memory_mode=_memory_trace_mode(data),
        saved_memory_ids=tuple(data.get("saved_memory_ids", ())),
        retrieved_memory_ids=tuple(data.get("retrieved_memory_ids", ())),
        used_memory_ids=tuple(data.get("used_memory_ids", ())),
        supporting_claims=tuple(
            MemoryTraceClaim(
                claim=str(item.get("claim", "")),
                memory_id=str(item.get("memory_id", "")),
            )
            for item in json_objects(supporting_claims, "supporting_claims")
        ),
        tool_calls=tuple(
            MemoryTraceToolCall(
                tool=str(item.get("tool", "")),
                arguments_ref=str(item.get("arguments_ref", "")),
                memory_ids=tuple(item.get("memory_ids", ())),
                operation=str(item.get("operation", "") or ""),
                memory_location=str(item.get("memory_location", "") or ""),
            )
            for item in json_objects(tool_calls, "tool_calls")
        ),
        diagnostics=tuple(data.get("diagnostics", ())),
        namespace=str(data.get("namespace", "")),
        timestamp=str(data.get("timestamp", "")),
        context_memory_ids=tuple(data.get("context_memory_ids", ())),
        cited_memory_ids=tuple(data.get("cited_memory_ids", ())),
        provider_id=str(data.get("provider_id", "") or ""),
        model_id=str(data.get("model_id", "") or ""),
        token_count=data.get("token_count"),
        cost_usd=data.get("cost_usd"),
        latency_ms=data.get("latency_ms"),
        entity_proposal_ids=tuple(data.get("entity_proposal_ids", ())),
        fact_proposal_ids=tuple(data.get("fact_proposal_ids", ())),
        lifecycle_event_ids=tuple(data.get("lifecycle_event_ids", ())),
        artifact_ids=tuple(data.get("artifact_ids", ())),
        citation_spans=tuple(data.get("citation_spans", ())),
        trajectory_steps=tuple(data.get("trajectory_steps", ())),
        graph_path_ids=tuple(data.get("graph_path_ids", ())),
        valid_time_refs=tuple(data.get("valid_time_refs", ())),
        transaction_time_refs=tuple(data.get("transaction_time_refs", ())),
        redaction_status=_redaction_status(data),
        private_trace_refs=tuple(data.get("private_trace_refs", ())),
    )


def _delegated_memory_trace_from_dict(data: dict[str, Any]) -> DelegatedMemoryEvalTrace:
    return DelegatedMemoryEvalTrace(
        case_id=str(data.get("case_id", "")),
        retrieved_memory_ids=string_tuple(data, "retrieved_memory_ids"),
        sibling_scratch_ids=string_tuple(data, "sibling_scratch_ids"),
        direct_id_bypass_ids=string_tuple(data, "direct_id_bypass_ids"),
        revoked_future_operation_ids=string_tuple(
            data,
            "revoked_future_operation_ids",
        ),
        forbidden_reshare_ids=string_tuple(data, "forbidden_reshare_ids"),
        accepted_poisoning_ids=string_tuple(data, "accepted_poisoning_ids"),
        provenance_failures=string_tuple(data, "provenance_failures"),
        forgetting_failures=string_tuple(data, "forgetting_failures"),
        prior_delivery_ids=string_tuple(data, "prior_delivery_ids"),
        latency_ms=float(data.get("latency_ms", 0.0)),
        token_count=int(data.get("token_count", 0)),
    )


def _memory_trace_mode(data: dict[str, Any]) -> MemoryTraceMode:
    value = data.get("memory_mode")
    if value in ("disabled", "enabled"):
        return value
    raise ValueError(f"invalid memory_mode: {value!r}")


def _redaction_status(data: dict[str, Any]) -> MemoryTraceRedactionStatus:
    value = data.get("redaction_status", "sanitized")
    if value in ("sanitized", "unredacted", "unknown"):
        return value
    raise ValueError(f"invalid redaction_status: {value!r}")


def _write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def _write_error(message: str) -> None:
    sys.stderr.write(f"{message}\n")
