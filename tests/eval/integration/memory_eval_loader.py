"""YAML fixture loading for the memory eval harness."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from tests.eval.integration.memory_eval_types import (
    MemoryEvalGeneratedRecords,
    MemoryEvalGroundTruth,
    MemoryEvalScenario,
    MemoryEvalSeedCandidate,
    MemoryEvalSeedRecord,
    MemoryEvalSession,
    MemoryEvalSetup,
    MemoryEvalTurn,
)


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


__all__ = ["MemoryEvalFixtureLoader"]
