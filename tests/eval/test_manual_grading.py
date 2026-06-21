from __future__ import annotations

import json

import pytest

from openminion_eval import (
    EvalCase,
    EvalCaseResult,
    GradeMode,
    GradeOutcome,
    apply_manual_adjudications,
    build_manual_review_queue,
    load_manual_adjudications,
    write_manual_review_queue,
)


def test_manual_review_queue_is_optional_for_non_manual_cases(tmp_path) -> None:
    queue = build_manual_review_queue(
        (
            EvalCase(
                case_id="manual",
                category="quality",
                description="Needs human judgment",
                prompt="Review this output",
                grade_mode=GradeMode.MANUAL,
                tags=("review",),
            ),
            EvalCase(
                case_id="structural",
                category="quality",
                description="Structural",
                prompt="Run this check",
                grade_mode=GradeMode.STRUCTURAL,
            ),
        )
    )

    assert [item.case_id for item in queue.items] == ["manual"]
    output = write_manual_review_queue(tmp_path / "queue.json", queue)
    payload = json.loads(output.read_text())
    assert payload["artifact_version"] == "1"
    assert payload["items"][0]["tags"] == ["review"]


def test_manual_adjudication_import_updates_results(tmp_path) -> None:
    artifact = tmp_path / "adjudication.json"
    artifact.write_text(
        json.dumps(
            {
                "artifact_version": "1",
                "adjudications": [
                    {
                        "case_id": "manual",
                        "outcome": "pass",
                        "detail": "reviewed by human",
                    }
                ],
            }
        )
    )
    adjudications = load_manual_adjudications(artifact)

    updated = apply_manual_adjudications(
        (
            EvalCaseResult(
                case_id="manual",
                category="quality",
                grade_mode=GradeMode.MANUAL,
                outcome=GradeOutcome.UNGRADED,
            ),
        ),
        adjudications,
    )

    assert updated[0].outcome is GradeOutcome.PASS
    assert updated[0].detail == "reviewed by human"


def test_manual_adjudication_rejects_malformed_import(tmp_path) -> None:
    artifact = tmp_path / "bad.json"
    artifact.write_text(json.dumps({"artifact_version": "1", "adjudications": [{}]}))

    with pytest.raises(ValueError, match="requires case_id"):
        load_manual_adjudications(artifact)
