"""Fixture-driven memory evaluation harness for OpenMinion."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from importlib import import_module
import json
from pathlib import Path
import tempfile
import time
from types import SimpleNamespace
import uuid
from typing import Any, Callable

import yaml

from openminion.modules.memory.runtime.gc import run_gc
from openminion.modules.memory.models import MemoryCandidate, MemoryRecord
from openminion.modules.memory.service import MemoryService
from openminion.modules.memory.storage.store import SQLiteMemoryStore

from openminion_eval.scorer import MemoryEvalScorer
from openminion.base.common.time import utc_now_iso as _utc_now_iso


def _record_text(record: MemoryRecord) -> str:
    title = str(getattr(record, "title", "") or "").strip()
    content = getattr(record, "content", "")
    if isinstance(content, dict):
        payload = " ".join(str(value) for value in content.values())
    else:
        payload = str(content or "")
    return " ".join(chunk for chunk in (title, payload) if chunk).strip()


def _normalize_label(value: str) -> str:
    return " ".join(str(value or "").lower().split())


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, int(len(ordered) * 0.95) - 1)
    return float(ordered[index])


def _default_adapter_factory(
    service: MemoryService,
    engine_config: "MemoryEvalEngineConfig",
) -> Any:
    gateway_module = import_module("openminion.services.agent.memory.gateway_adapter")
    gateway_cls = getattr(gateway_module, "MemoryServiceGatewayAdapter")
    return gateway_cls(
        service,
        agent_id=engine_config.agent_id,
        project_id=engine_config.project_id,
        memory_config=engine_config.memory_config,
        **engine_config.adapter_kwargs,
    )


@dataclass(frozen=True)
class MemoryEvalSeedRecord:
    scope: str
    type: str
    content: dict[str, Any] | str
    ref: str | None = None
    key: str | None = None
    title: str | None = None
    confidence: float = 1.0
    source: str = "validated"
    meta: dict[str, Any] = field(default_factory=dict)
    superseded_by: str | None = None
    supersession_reason: str | None = None
    last_hit_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MemoryEvalSeedCandidate:
    session_id: str
    proposed_scope: str
    type: str
    content: dict[str, Any] | str
    candidate_id: str | None = None
    title: str | None = None
    key: str | None = None
    status: str = "proposed"
    confidence: float = 0.5
    source: str = "agent_inferred"
    meta: dict[str, Any] = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


@dataclass(frozen=True)
class MemoryEvalGeneratedRecords:
    scope: str
    type: str
    count: int
    content_prefix: str = "generated record"
    title_prefix: str = "Generated Record"
    confidence: float = 0.8


@dataclass(frozen=True)
class MemoryEvalSetup:
    records: list[MemoryEvalSeedRecord] = field(default_factory=list)
    candidates: list[MemoryEvalSeedCandidate] = field(default_factory=list)
    generated_records: list[MemoryEvalGeneratedRecords] = field(default_factory=list)


@dataclass(frozen=True)
class MemoryEvalTurn:
    user: str
    assistant: str | None = None


@dataclass(frozen=True)
class MemoryEvalSession:
    id: str
    turns: list[MemoryEvalTurn]


@dataclass(frozen=True)
class MemoryEvalGroundTruth:
    must_recall: list[str] = field(default_factory=list)
    must_not_surface: list[str] = field(default_factory=list)
    relevance_labels: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class MemoryEvalScenario:
    version: str
    scenario_id: str
    description: str
    eval_dimensions: list[str]
    requires_features: list[str] = field(default_factory=list)
    setup: MemoryEvalSetup = field(default_factory=MemoryEvalSetup)
    sessions: list[MemoryEvalSession] = field(default_factory=list)
    ground_truth: MemoryEvalGroundTruth = field(default_factory=MemoryEvalGroundTruth)


@dataclass(frozen=True)
class MemoryEvalEngineConfig:
    name: str = "default"
    agent_id: str = "eval-agent"
    project_id: str | None = None
    memory_config: Any | None = None
    adapter_kwargs: dict[str, Any] = field(default_factory=dict)
    adapter_factory: Callable[[MemoryService, "MemoryEvalEngineConfig"], Any] | None = (
        None
    )
    session_context_factory: Callable[[Path], Any] | None = None
    vector_adapter_factory: Callable[[MemoryEvalScenario], Any] | None = None


@dataclass(frozen=True)
class MemoryEvalScenarioResult:
    scenario_id: str
    dimensions: list[str]
    metrics: dict[str, float | int | bool]
    query_count: int


@dataclass(frozen=True)
class MemoryEvalReport:
    engine_name: str
    generated_at: str
    scenario_results: list[MemoryEvalScenarioResult]

    def to_snapshot(self, *, commit: str) -> dict[str, Any]:
        grouped: dict[str, dict[str, Any]] = {}
        for result in self.scenario_results:
            for metric_name, value in result.metrics.items():
                dimension = metric_name.split(".", 1)[0]
                bucket = grouped.setdefault(
                    dimension,
                    {"scenarios": [], "scores": {}},
                )
                if result.scenario_id not in bucket["scenarios"]:
                    bucket["scenarios"].append(result.scenario_id)
                scenario_scores = bucket["scores"].setdefault(result.scenario_id, {})
                scenario_scores[metric_name] = value
        return {
            "timestamp": self.generated_at,
            "commit": commit,
            "engine_name": self.engine_name,
            "dimensions": grouped,
        }


@dataclass(frozen=True)
class MemoryEvalComparisonEntry:
    scenario_id: str
    metric_name: str
    before: float | int | bool
    after: float | int | bool
    status: str


@dataclass(frozen=True)
class MemoryEvalComparison:
    entries: list[MemoryEvalComparisonEntry]


class MemoryEvalFixtureLoader:
    """Load typed memory eval scenarios from YAML fixtures."""

    def load(self, path: str | Path) -> MemoryEvalScenario:
        fixture_path = Path(path)
        payload = yaml.safe_load(fixture_path.read_text(encoding="utf-8")) or {}
        if not isinstance(payload, dict):
            raise ValueError(f"fixture must be a mapping: {fixture_path}")

        version = str(payload.get("version", "") or "")
        if version != "1":
            raise ValueError(
                f"unsupported fixture version in {fixture_path}: {version}"
            )

        scenario_id = str(payload.get("scenario_id", "") or "").strip()
        if not scenario_id:
            raise ValueError(f"scenario_id is required: {fixture_path}")

        description = str(payload.get("description", "") or "").strip()
        dimensions = self._string_list(
            payload.get("eval_dimensions"), "eval_dimensions"
        )
        requires_features = self._string_list(
            payload.get("requires_features"),
            "requires_features",
            required=False,
        )

        setup_payload = payload.get("setup") or {}
        if not isinstance(setup_payload, dict):
            raise ValueError(f"setup must be a mapping: {fixture_path}")

        records = [
            self._seed_record_from_payload(item, fixture_path)
            for item in (setup_payload.get("records") or [])
        ]
        candidates = [
            self._seed_candidate_from_payload(item, fixture_path)
            for item in (setup_payload.get("candidates") or [])
        ]
        generated_records = [
            self._generated_record_from_payload(item, fixture_path)
            for item in (setup_payload.get("generated_records") or [])
        ]

        sessions_payload = payload.get("sessions") or []
        sessions: list[MemoryEvalSession] = []
        for index, session_payload in enumerate(sessions_payload):
            if not isinstance(session_payload, dict):
                raise ValueError(
                    f"sessions[{index}] must be a mapping in {fixture_path}"
                )
            session_id = str(session_payload.get("id", "") or "").strip()
            if not session_id:
                raise ValueError(f"sessions[{index}].id is required in {fixture_path}")
            turns_payload = session_payload.get("turns") or []
            turns: list[MemoryEvalTurn] = []
            for turn_index, turn_payload in enumerate(turns_payload):
                if not isinstance(turn_payload, dict):
                    raise ValueError(
                        f"sessions[{index}].turns[{turn_index}] must be a mapping"
                    )
                user = str(turn_payload.get("user", "") or "")
                if not user.strip():
                    raise ValueError(
                        f"sessions[{index}].turns[{turn_index}].user is required"
                    )
                assistant_raw = turn_payload.get("assistant")
                assistant = None if assistant_raw is None else str(assistant_raw)
                turns.append(MemoryEvalTurn(user=user, assistant=assistant))
            sessions.append(MemoryEvalSession(id=session_id, turns=turns))

        ground_truth_payload = payload.get("ground_truth") or {}
        if not isinstance(ground_truth_payload, dict):
            raise ValueError(f"ground_truth must be a mapping: {fixture_path}")
        relevance_labels = ground_truth_payload.get("relevance_labels") or {}
        if not isinstance(relevance_labels, dict):
            raise ValueError(f"relevance_labels must be a mapping: {fixture_path}")

        return MemoryEvalScenario(
            version=version,
            scenario_id=scenario_id,
            description=description,
            eval_dimensions=dimensions,
            requires_features=requires_features,
            setup=MemoryEvalSetup(
                records=records,
                candidates=candidates,
                generated_records=generated_records,
            ),
            sessions=sessions,
            ground_truth=MemoryEvalGroundTruth(
                must_recall=self._string_list(
                    ground_truth_payload.get("must_recall"),
                    "ground_truth.must_recall",
                    required=False,
                ),
                must_not_surface=self._string_list(
                    ground_truth_payload.get("must_not_surface"),
                    "ground_truth.must_not_surface",
                    required=False,
                ),
                relevance_labels={
                    str(key): str(value) for key, value in relevance_labels.items()
                },
            ),
        )

    def load_directory(self, directory: str | Path) -> list[MemoryEvalScenario]:
        fixture_dir = Path(directory)
        return [self.load(path) for path in sorted(fixture_dir.glob("*.yaml"))]

    def _seed_record_from_payload(
        self,
        payload: Any,
        fixture_path: Path,
    ) -> MemoryEvalSeedRecord:
        if not isinstance(payload, dict):
            raise ValueError(f"record entry must be a mapping in {fixture_path}")
        scope = str(payload.get("scope", "") or "").strip()
        record_type = str(payload.get("type", "") or "").strip()
        if not scope or not record_type:
            raise ValueError(f"record scope/type required in {fixture_path}")
        content = payload.get("content", "")
        if not isinstance(content, (str, dict)):
            raise ValueError(
                f"record content must be string or mapping in {fixture_path}"
            )
        return MemoryEvalSeedRecord(
            scope=scope,
            type=record_type,
            content=content,
            ref=self._optional_string(payload.get("ref")),
            key=self._optional_string(payload.get("key")),
            title=self._optional_string(payload.get("title")),
            confidence=float(payload.get("confidence", 1.0)),
            source=str(payload.get("source", "validated") or "validated"),
            meta=dict(payload.get("meta", {}) or {}),
            superseded_by=self._optional_string(payload.get("superseded_by")),
            supersession_reason=self._optional_string(
                payload.get("supersession_reason")
            ),
            last_hit_at=self._optional_string(payload.get("last_hit_at")),
            created_at=self._optional_string(payload.get("created_at")),
            updated_at=self._optional_string(payload.get("updated_at")),
        )

    def _generated_record_from_payload(
        self,
        payload: Any,
        fixture_path: Path,
    ) -> MemoryEvalGeneratedRecords:
        if not isinstance(payload, dict):
            raise ValueError(
                f"generated_records entry must be a mapping in {fixture_path}"
            )
        scope = str(payload.get("scope", "") or "").strip()
        record_type = str(payload.get("type", "") or "").strip()
        count = int(payload.get("count", 0) or 0)
        if not scope or not record_type or count <= 0:
            raise ValueError(
                f"generated record scope/type/count required in {fixture_path}"
            )
        return MemoryEvalGeneratedRecords(
            scope=scope,
            type=record_type,
            count=count,
            content_prefix=str(payload.get("content_prefix", "generated record")),
            title_prefix=str(payload.get("title_prefix", "Generated Record")),
            confidence=float(payload.get("confidence", 0.8)),
        )

    def _seed_candidate_from_payload(
        self,
        payload: Any,
        fixture_path: Path,
    ) -> MemoryEvalSeedCandidate:
        if not isinstance(payload, dict):
            raise ValueError(f"candidate entry must be a mapping in {fixture_path}")
        session_id = str(payload.get("session_id", "") or "").strip()
        proposed_scope = str(payload.get("proposed_scope", "") or "").strip()
        candidate_type = str(payload.get("type", "") or "").strip()
        if not session_id or not proposed_scope or not candidate_type:
            raise ValueError(
                f"candidate session_id/proposed_scope/type required in {fixture_path}"
            )
        content = payload.get("content", "")
        if not isinstance(content, (str, dict)):
            raise ValueError(
                f"candidate content must be string or mapping in {fixture_path}"
            )
        return MemoryEvalSeedCandidate(
            session_id=session_id,
            proposed_scope=proposed_scope,
            type=candidate_type,
            content=content,
            candidate_id=self._optional_string(payload.get("candidate_id")),
            title=self._optional_string(payload.get("title")),
            key=self._optional_string(payload.get("key")),
            status=str(payload.get("status", "proposed") or "proposed"),
            confidence=float(payload.get("confidence", 0.5)),
            source=str(payload.get("source", "agent_inferred") or "agent_inferred"),
            meta=dict(payload.get("meta", {}) or {}),
            created_at=self._optional_string(payload.get("created_at")),
            updated_at=self._optional_string(payload.get("updated_at")),
        )

    def _string_list(
        self,
        value: Any,
        label: str,
        *,
        required: bool = True,
    ) -> list[str]:
        if value in (None, ""):
            if required:
                raise ValueError(f"{label} is required")
            return []
        if not isinstance(value, list):
            raise ValueError(f"{label} must be a list")
        return [str(item) for item in value]

    def _optional_string(self, value: Any) -> str | None:
        normalized = str(value).strip() if value is not None else ""
        return normalized or None


class MemoryEvalHarness:
    """Run fixture-driven memory evaluations against the standard memory surface."""

    def __init__(self, loader: MemoryEvalFixtureLoader | None = None) -> None:
        self._loader = loader or MemoryEvalFixtureLoader()

    @property
    def loader(self) -> MemoryEvalFixtureLoader:
        return self._loader

    def run(
        self,
        scenarios: list[MemoryEvalScenario],
        *,
        engine_config: MemoryEvalEngineConfig | None = None,
    ) -> MemoryEvalReport:
        config = engine_config or MemoryEvalEngineConfig()
        results = [self._run_scenario(scenario, config) for scenario in scenarios]
        return MemoryEvalReport(
            engine_name=config.name,
            generated_at=_utc_now_iso(),
            scenario_results=results,
        )

    def compare(
        self,
        report_a: MemoryEvalReport,
        report_b: MemoryEvalReport,
    ) -> MemoryEvalComparison:
        lower_is_better = {
            "stale_memory_suppression.leak_count",
            "contradiction_leak.leak_count",
            "contradiction_leak.contradiction_leak_rate",
            "capsule_precision.capsule_noise_rate",
            "latency_regression.capsule_build_p95_ms",
            "latency_regression.retrieval_p95_ms",
            "latency_regression.search_p95_ms",
        }
        entries: list[MemoryEvalComparisonEntry] = []
        before_map = {item.scenario_id: item for item in report_a.scenario_results}
        after_map = {item.scenario_id: item for item in report_b.scenario_results}
        for scenario_id in sorted(before_map):
            before_result = before_map[scenario_id]
            after_result = after_map.get(scenario_id)
            if after_result is None:
                continue
            for metric_name, before_value in before_result.metrics.items():
                if metric_name not in after_result.metrics:
                    continue
                after_value = after_result.metrics[metric_name]
                status = "unchanged"
                if isinstance(before_value, bool) or isinstance(after_value, bool):
                    if bool(after_value) and not bool(before_value):
                        status = "improved"
                    elif bool(before_value) and not bool(after_value):
                        status = "regressed"
                elif metric_name in lower_is_better:
                    if float(after_value) < float(before_value):
                        status = "improved"
                    elif float(after_value) > float(before_value):
                        status = "regressed"
                else:
                    if float(after_value) > float(before_value):
                        status = "improved"
                    elif float(after_value) < float(before_value):
                        status = "regressed"
                entries.append(
                    MemoryEvalComparisonEntry(
                        scenario_id=scenario_id,
                        metric_name=metric_name,
                        before=before_value,
                        after=after_value,
                        status=status,
                    )
                )
        return MemoryEvalComparison(entries=entries)

    def write_snapshot(
        self,
        path: str | Path,
        scenarios: list[MemoryEvalScenario],
        *,
        engine_config: MemoryEvalEngineConfig | None = None,
        commit: str = "workspace",
    ) -> dict[str, Any]:
        report = self.run(scenarios, engine_config=engine_config)
        payload = report.to_snapshot(commit=commit)
        Path(path).write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return payload

    def _run_scenario(
        self,
        scenario: MemoryEvalScenario,
        engine_config: MemoryEvalEngineConfig,
    ) -> MemoryEvalScenarioResult:
        with tempfile.TemporaryDirectory(prefix="memory-eval-") as temp_dir:
            temp_root = Path(temp_dir)
            db_path = temp_root / "memory-eval.sqlite3"
            store = SQLiteMemoryStore(db_path)
            vector_adapter = (
                engine_config.vector_adapter_factory(scenario)
                if engine_config.vector_adapter_factory is not None
                else None
            )
            service = MemoryService(store=store, vector_adapter=vector_adapter)
            effective_engine_config = engine_config
            required_features = {
                str(item).strip().lower() for item in scenario.requires_features
            }
            if (
                engine_config.session_context_factory is not None
                and "session_handoff" in required_features
            ):
                session_context = engine_config.session_context_factory(temp_root)
                effective_engine_config = replace(
                    engine_config,
                    adapter_kwargs={
                        **engine_config.adapter_kwargs,
                        "session_context": session_context,
                    },
                )
            adapter_factory = engine_config.adapter_factory or _default_adapter_factory
            adapter = adapter_factory(service, effective_engine_config)
            self._seed_setup(store=store, service=service, scenario=scenario)
            if "reflection" in required_features:
                runner = getattr(adapter, "_maybe_run_reflection", None)
                if callable(runner):
                    runner()
            queries = self._apply_sessions(adapter=adapter, scenario=scenario)
            metrics: dict[str, float | int | bool] = {}
            if "cross_session_recall" in scenario.eval_dimensions:
                metrics.update(
                    self._score_recall(
                        adapter=adapter,
                        service=service,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            if "paraphrase_retrieval" in scenario.eval_dimensions:
                metrics.update(
                    self._score_paraphrase(
                        adapter=adapter,
                        service=service,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            if "stale_memory_suppression" in scenario.eval_dimensions:
                metrics.update(
                    self._score_stale_suppression(
                        adapter=adapter,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            if "contradiction_leak" in scenario.eval_dimensions:
                metrics.update(
                    self._score_contradiction_leak(
                        adapter=adapter,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            if "capsule_precision" in scenario.eval_dimensions:
                metrics.update(
                    self._score_capsule_precision(
                        adapter=adapter,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            if "latency_regression" in scenario.eval_dimensions:
                metrics.update(
                    self._score_latency(
                        adapter=adapter,
                        service=service,
                        scenario=scenario,
                        queries=queries,
                    )
                )
            return MemoryEvalScenarioResult(
                scenario_id=scenario.scenario_id,
                dimensions=list(scenario.eval_dimensions),
                metrics=metrics,
                query_count=len(queries),
            )

    def _seed_setup(
        self,
        *,
        store: SQLiteMemoryStore,
        service: MemoryService,
        scenario: MemoryEvalScenario,
    ) -> None:
        ref_map: dict[str, str] = {}
        for record in scenario.setup.records:
            if record.key:
                stored = service.upsert_record(
                    scope=record.scope,
                    record_type=record.type,
                    key=record.key,
                    record_patch={
                        "title": record.title,
                        "content": record.content,
                        "confidence": record.confidence,
                        "source": record.source,
                        "meta": dict(record.meta),
                    },
                )
            else:
                now = _utc_now_iso()
                stored = MemoryRecord(
                    id=f"mem_{uuid.uuid4().hex[:12]}",
                    scope=record.scope,
                    type=record.type,  # type: ignore[arg-type]
                    key=record.key,
                    title=record.title,
                    content=record.content,
                    source=record.source,  # type: ignore[arg-type]
                    confidence=float(record.confidence),
                    meta=dict(record.meta),
                    last_hit_at=record.last_hit_at,
                    supersession_reason=record.supersession_reason,
                    created_at=record.created_at or now,
                    updated_at=record.updated_at or now,
                )
                store.put(stored)
            if record.ref:
                ref_map[record.ref] = stored.id

        for record in scenario.setup.records:
            if not record.ref or not record.superseded_by:
                continue
            old_id = ref_map.get(record.ref)
            new_id = ref_map.get(record.superseded_by)
            if old_id and new_id:
                service.supersede_by_contradiction(
                    old_id,
                    new_id,
                    reason=record.supersession_reason or "",
                )

        for generated in scenario.setup.generated_records:
            for index in range(generated.count):
                now = _utc_now_iso()
                store.put(
                    MemoryRecord(
                        id=f"mem_{uuid.uuid4().hex[:12]}",
                        scope=generated.scope,
                        type=generated.type,  # type: ignore[arg-type]
                        title=f"{generated.title_prefix} {index}",
                        content=(
                            f"{generated.content_prefix} number {index} "
                            f"contains unique payload {index}"
                        ),
                        source="validated",
                        confidence=float(generated.confidence),
                        created_at=now,
                        updated_at=now,
                    )
                )
        for candidate in scenario.setup.candidates:
            now = _utc_now_iso()
            service.candidate_put(
                MemoryCandidate(
                    candidate_id=candidate.candidate_id
                    or f"cand_{uuid.uuid4().hex[:12]}",
                    session_id=candidate.session_id,
                    proposed_scope=candidate.proposed_scope,  # type: ignore[arg-type]
                    type=candidate.type,  # type: ignore[arg-type]
                    title=candidate.title,
                    key=candidate.key,
                    content=candidate.content,
                    source=candidate.source,  # type: ignore[arg-type]
                    confidence=float(candidate.confidence),
                    status=candidate.status,  # type: ignore[arg-type]
                    meta=dict(candidate.meta),
                    created_at=candidate.created_at or now,
                    updated_at=candidate.updated_at or now,
                )
            )
        if "gc" in {item.strip().lower() for item in scenario.requires_features}:
            # MREF-02 (2026-04-29): `run_gc` now reads typed
            # `summary_compression_*` / `summary_delete_age_days` fields
            # directly. The eval harness's small-budget context wants a
            # 100-char compressed-summary cap, but it must now supply the
            # typed field name (`summary_compression_max_chars`) instead
            # of overloading `session_summary_max_chars`. All retention
            # fields the GC pipeline reads must be present on this
            # synthetic object — this is the eval-harness analogue of
            # the "test fixtures must construct full retention" rule
            # named in `docs/specs/memory-retention-explicit-fields-spec.md`.
            run_gc(
                store,
                retention_config=SimpleNamespace(
                    confidence_decay_interval_days=7,
                    confidence_decay_rate=0.05,
                    min_confidence_eviction=0.3,
                    disuse_threshold_days=30,
                    disuse_decay_multiplier=2.0,
                    session_summary_max_chars=500,
                    summary_compression_max_chars=100,
                    summary_compression_age_days=14,
                    summary_delete_age_days=90,
                    max_records_per_scope=500,
                ),
            )

    def _apply_sessions(
        self,
        *,
        adapter: Any,
        scenario: MemoryEvalScenario,
    ) -> list[tuple[str, str]]:
        queries: list[tuple[str, str]] = []
        session_context = getattr(adapter, "_session_context", None)
        session_store = getattr(session_context, "_sessions", None)
        agent_id = str(getattr(adapter, "_agent_id", "eval-agent") or "eval-agent")
        for session in scenario.sessions:
            has_recorded_turn = False
            for turn_index, turn in enumerate(session.turns):
                if turn.assistant is None:
                    queries.append((session.id, turn.user))
                    continue
                if session_store is not None:
                    session_store.resolve_session(
                        agent_id=agent_id,
                        channel="eval",
                        target=session.id,
                        session_id=session.id,
                    )
                    session_store.append_message(
                        session_id=session.id,
                        role="inbound",
                        body=turn.user,
                    )
                    session_store.append_message(
                        session_id=session.id,
                        role="outbound",
                        body=turn.assistant,
                    )
                adapter.record_turn(
                    session_id=session.id,
                    run_id=f"{scenario.scenario_id}:{session.id}:run:{turn_index}",
                    request_id=f"{scenario.scenario_id}:{session.id}:req:{turn_index}",
                    channel="eval",
                    target="user",
                    user_message=turn.user,
                    assistant_message=turn.assistant,
                )
                has_recorded_turn = True
            if (
                has_recorded_turn
                and session_context is not None
                and hasattr(session_context, "on_session_close")
            ):
                session_context.on_session_close(session_id=session.id)
        if not queries and scenario.sessions:
            last_session = scenario.sessions[-1]
            if last_session.turns:
                queries.append((last_session.id, last_session.turns[-1].user))
        return queries

    def _score_recall(
        self,
        *,
        adapter: Any,
        service: MemoryService,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float]:
        recalls: list[float] = []
        precisions: list[float] = []
        for session_id, query in queries:
            records = self._retrieve_records(
                service=service,
                adapter=adapter,
                session_id=session_id,
                query=query,
                limit=5,
            )
            texts = [_record_text(record) for record in records]
            recalls.append(
                MemoryEvalScorer.recall_at_k(
                    texts,
                    scenario.ground_truth.must_recall,
                    5,
                )
            )
            precisions.append(
                MemoryEvalScorer.precision_at_k(
                    texts,
                    scenario.ground_truth.must_recall,
                    5,
                )
            )
        return {
            "cross_session_recall.recall_at_5": (
                sum(recalls) / len(recalls) if recalls else 0.0
            ),
            "cross_session_recall.precision_at_5": (
                sum(precisions) / len(precisions) if precisions else 0.0
            ),
        }

    def _score_paraphrase(
        self,
        *,
        adapter: Any,
        service: MemoryService,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float]:
        recalls: list[float] = []
        for session_id, query in queries:
            records = self._retrieve_records(
                service=service,
                adapter=adapter,
                session_id=session_id,
                query=query,
                limit=5,
            )
            text = "\n".join(_record_text(record) for record in records)
            recalls.append(
                MemoryEvalScorer.substring_recall(
                    text,
                    scenario.ground_truth.must_recall,
                )
            )
        return {
            "paraphrase_retrieval.paraphrase_recall_at_5": (
                sum(recalls) / len(recalls) if recalls else 0.0
            )
        }

    def _score_stale_suppression(
        self,
        *,
        adapter: Any,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float | int]:
        capsule_texts = [
            adapter.build_context(session_id=session_id, user_message=query)
            for session_id, query in queries
        ]
        normalized_capsules = [text.lower() for text in capsule_texts]
        denied = scenario.ground_truth.must_not_surface
        total_checks = max(1, len(normalized_capsules) * max(1, len(denied)))
        leak_count = 0
        for item in denied:
            normalized = _normalize_label(item)
            for capsule_text in normalized_capsules:
                if normalized and normalized in capsule_text:
                    leak_count += 1
        suppression_rate = 1.0 - (float(leak_count) / float(total_checks))
        return {
            "stale_memory_suppression.suppression_rate": suppression_rate,
            "stale_memory_suppression.leak_count": leak_count,
        }

    def _score_contradiction_leak(
        self,
        *,
        adapter: Any,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float | int]:
        capsule_texts = [
            adapter.build_context(session_id=session_id, user_message=query)
            for session_id, query in queries
        ]
        leak_count = sum(
            MemoryEvalScorer.contradiction_leak_count(
                text,
                scenario.ground_truth.must_not_surface,
            )
            for text in capsule_texts
        )
        total_checks = max(
            1,
            len(capsule_texts) * max(1, len(scenario.ground_truth.must_not_surface)),
        )
        correct_resolutions = 0
        for text in capsule_texts:
            required_score = MemoryEvalScorer.substring_recall(
                text,
                scenario.ground_truth.must_recall,
            )
            if (
                required_score >= 1.0
                and MemoryEvalScorer.contradiction_leak_count(
                    text,
                    scenario.ground_truth.must_not_surface,
                )
                == 0
            ):
                correct_resolutions += 1
        return {
            "contradiction_leak.contradiction_leak_rate": float(leak_count)
            / float(total_checks),
            "contradiction_leak.correct_resolution_rate": float(correct_resolutions)
            / float(max(1, len(capsule_texts))),
            "contradiction_leak.leak_count": leak_count,
        }

    def _score_capsule_precision(
        self,
        *,
        adapter: Any,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float]:
        if not scenario.ground_truth.relevance_labels:
            return {
                "capsule_precision.capsule_precision": 0.0,
                "capsule_precision.capsule_noise_rate": 0.0,
            }
        precisions: list[float] = []
        noise_rates: list[float] = []
        for session_id, query in queries:
            capsule_text = adapter.build_context(
                session_id=session_id,
                user_message=query,
            )
            precision, noise_rate = MemoryEvalScorer.capsule_precision(
                capsule_text,
                scenario.ground_truth.relevance_labels,
            )
            precisions.append(precision)
            noise_rates.append(noise_rate)
        return {
            "capsule_precision.capsule_precision": (
                sum(precisions) / len(precisions) if precisions else 0.0
            ),
            "capsule_precision.capsule_noise_rate": (
                sum(noise_rates) / len(noise_rates) if noise_rates else 0.0
            ),
        }

    def _score_latency(
        self,
        *,
        adapter: Any,
        service: MemoryService,
        scenario: MemoryEvalScenario,
        queries: list[tuple[str, str]],
    ) -> dict[str, float | bool]:
        if not queries:
            queries = [("latency-eval", "what does memory know?")]
        session_id, query = queries[0]
        capsule_samples: list[float] = []
        retrieval_samples: list[float] = []
        search_samples: list[float] = []
        scopes = self._scopes_for_session(adapter=adapter, session_id=session_id)
        for _ in range(50):
            start = time.perf_counter()
            adapter.build_context(session_id=session_id, user_message=query)
            capsule_samples.append((time.perf_counter() - start) * 1000.0)

            start = time.perf_counter()
            adapter.build_retrieval_context(session_id=session_id, user_message=query)
            retrieval_samples.append((time.perf_counter() - start) * 1000.0)

            start = time.perf_counter()
            service.search_all(query, scopes=scopes, limit=8)
            search_samples.append((time.perf_counter() - start) * 1000.0)

        capsule_p95 = _p95(capsule_samples)
        retrieval_p95 = _p95(retrieval_samples)
        search_p95 = _p95(search_samples)
        return {
            "latency_regression.capsule_build_p95_ms": capsule_p95,
            "latency_regression.retrieval_p95_ms": retrieval_p95,
            "latency_regression.search_p95_ms": search_p95,
            "latency_regression.capsule_within_bound": MemoryEvalScorer.latency_gate(
                capsule_p95,
                200.0,
            ),
            "latency_regression.retrieval_within_bound": MemoryEvalScorer.latency_gate(
                retrieval_p95,
                300.0,
            ),
            "latency_regression.search_within_bound": MemoryEvalScorer.latency_gate(
                search_p95,
                100.0,
            ),
        }

    def _retrieve_records(
        self,
        *,
        service: MemoryService,
        adapter: Any,
        session_id: str,
        query: str,
        limit: int,
    ) -> list[MemoryRecord]:
        scopes = self._scopes_for_session(adapter=adapter, session_id=session_id)
        return service.search_semantic(query=query, scopes=scopes, limit=limit)

    def _scopes_for_session(
        self,
        *,
        adapter: Any,
        session_id: str,
    ) -> list[str]:
        long_term_scopes = list(adapter._long_term_scopes())  # noqa: SLF001
        return [f"session:{session_id}", *long_term_scopes]


__all__ = [
    "MemoryEvalComparison",
    "MemoryEvalComparisonEntry",
    "MemoryEvalEngineConfig",
    "MemoryEvalFixtureLoader",
    "MemoryEvalGeneratedRecords",
    "MemoryEvalGroundTruth",
    "MemoryEvalHarness",
    "MemoryEvalReport",
    "MemoryEvalScenario",
    "MemoryEvalScenarioResult",
    "MemoryEvalSeedRecord",
    "MemoryEvalSession",
    "MemoryEvalSetup",
    "MemoryEvalTurn",
]
