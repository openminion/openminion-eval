# Artifacts And Manual Grading

Status: alpha
Last updated: 2026-06-21

Purpose: document package-owned JSON artifacts for scorer traces, manual
review, and integration-probe quarantine.

## Scorer traces

`build_case_traces()` converts an `EvalSuiteResult` into one row per evaluated
turn. `write_case_traces_jsonl()` writes those rows as input-order-preserving
JSONL. Suite runs record scorer reason and threshold with the same threshold
used by the summary pass/fail decision. Trace artifacts must not include host
runtime paths, tokens, or environment dumps.

## Manual review queue

Manual cases stay local and JSON-backed:

```python
from openminion_eval import build_manual_review_queue, registered_cases

queue = build_manual_review_queue(registered_cases())
```

Only `GradeMode.MANUAL` cases enter the queue. Starter structural cases remain
unchanged.

## Adjudication import

Reviewer decisions use a local JSON artifact:

```json
{
  "artifact_version": "1",
  "adjudications": [
    {"case_id": "manual-demo", "outcome": "pass", "detail": "reviewed"}
  ]
}
```

`load_manual_adjudications()` validates the artifact, and
`apply_manual_adjudications()` updates matching `EvalCaseResult` rows.
Malformed imports fail deterministically.

## Integration quarantine

Files under `tests/eval/integration/` are source-only probes. The installed
quarantine helper may describe them, but the probes themselves are not stable
package APIs and are not promoted into package workflows without the checklist
in `API_COMPATIBILITY.md`.
