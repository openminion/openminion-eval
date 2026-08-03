"""CLI support for memory-effectiveness trace scoring."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from openminion_eval.memory_effectiveness.fixtures import (
    load_memory_effectiveness_cases,
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


def memory_score_command(args: argparse.Namespace) -> int:
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


def _load_memory_traces(path: Path) -> tuple[MemoryEffectivenessTrace, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict) and "traces" in payload:
        items = payload["traces"]
    elif isinstance(payload, list):
        items = payload
    else:
        raise ValueError("trace artifact must be a list or contain a 'traces' list")
    if not isinstance(items, list):
        raise TypeError("trace artifact 'traces' value must be a list")
    traces: list[MemoryEffectivenessTrace] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"trace item {index} must be an object")
        traces.append(_memory_trace_from_dict(item))
    return tuple(traces)


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
            for item in _json_objects(supporting_claims, "supporting_claims")
        ),
        tool_calls=tuple(
            MemoryTraceToolCall(
                tool=str(item.get("tool", "")),
                arguments_ref=str(item.get("arguments_ref", "")),
                memory_ids=tuple(item.get("memory_ids", ())),
                operation=str(item.get("operation", "") or ""),
                memory_location=str(item.get("memory_location", "") or ""),
            )
            for item in _json_objects(tool_calls, "tool_calls")
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


def _json_objects(items: list | tuple, label: str) -> tuple[dict[str, Any], ...]:
    objects: list[dict[str, Any]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise TypeError(f"{label} item {index} must be an object")
        objects.append(item)
    return tuple(objects)


def _write_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))
