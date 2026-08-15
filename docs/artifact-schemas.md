# Artifact Schemas

Status: alpha

`openminion-eval` writes deterministic JSON artifacts that downstream CI can
store, diff, and render. The package keeps these artifacts provider-free: they
contain explicit eval facts, not secrets, environment dumps, or host-local
paths.

For the full run, validate, render, compare, and upload loop, see
[`artifact-workflows.md`](artifact-workflows.md).

## Suite Result

Produced by:

```bash
openminion-eval run dataset.json --out artifacts/suite-result.json
```

Top-level shape:

```json
{
  "artifact_version": "1",
  "manifest": {
    "run_id": "2026-01-01T00:00:00Z",
    "package_version": "0.0.1",
    "scorer_name": "substring_match"
  },
  "result": {
    "suite_name": "dataset-name",
    "summaries": []
  }
}
```

Render with:

```bash
openminion-eval report suite artifacts/suite-result.json --out artifacts/suite-result.md
```

Schema:

```text
docs/schemas/suite-result.v1.schema.json
```

## Baseline Diff

Produced by:

```bash
openminion-eval diff artifacts/previous.json artifacts/current.json --out artifacts/diff.json
```

Top-level shape:

```json
{
  "version": "suite-diff.v1",
  "previous_suite_name": "previous",
  "current_suite_name": "current",
  "categories": {
    "unchanged_pass": 1
  },
  "entries": []
}
```

Render with:

```bash
openminion-eval report diff artifacts/previous.json artifacts/current.json --out artifacts/diff.md
openminion-eval report suite-diff artifacts/diff.json --out artifacts/diff.md
```

Schema:

```text
docs/schemas/suite-diff.v1.schema.json
```

## Dataset

Produced by:

```bash
openminion-eval dataset init --family routing --out artifacts/dataset.json
```

Top-level shape:

```json
{
  "dataset_version": "1",
  "name": "routing-starter",
  "cases": []
}
```

Validate and hash with:

```bash
openminion-eval dataset validate artifacts/dataset.json
openminion-eval dataset hash artifacts/dataset.json
```

## Memory-Effectiveness Scorecard

Produced by:

```bash
openminion-eval memory-effectiveness score examples/memory-effectiveness-trace.json --cases examples/memory-effectiveness-cases.json --out artifacts/memory-scorecard.json
```

Top-level shape:

```json
{
  "artifact_version": "1",
  "scorecard": {
    "suite_id": "openminion-sophiagraph-memory-effectiveness",
    "run_id": "memory-effectiveness-local",
    "overall_score": 1.0,
    "cases": []
  }
}
```

Render with:

```bash
openminion-eval report memory-scorecard artifacts/memory-scorecard.json --out artifacts/memory-scorecard.md
```

## Delegated-Memory Scorecard

Produced by:

```bash
openminion-eval memory-effectiveness delegated-score examples/delegated-memory-trace.json --out artifacts/delegated-memory-scorecard.json
```

Top-level shape:

```json
{
  "version": "delegated-memory-scorecard.v1",
  "suite_id": "delegated-multi-agent-memory.v1",
  "passed": true,
  "utility_recall": 1.0,
  "results": []
}
```

Render and compare with:

```bash
openminion-eval report delegated-memory artifacts/delegated-memory-scorecard.json --out artifacts/delegated-memory-scorecard.md
openminion-eval memory-effectiveness delegated-diff artifacts/previous-delegated.json artifacts/current-delegated.json --out artifacts/delegated-diff.json
openminion-eval report delegated-diff artifacts/delegated-diff.json --out artifacts/delegated-diff.md
```

The delegated diff artifact is versioned for upload and review:

```json
{
  "version": "delegated-memory-diff.v1",
  "previous_suite_id": "delegated-multi-agent-memory.v1",
  "current_suite_id": "delegated-multi-agent-memory.v1",
  "categories": {
    "unchanged_pass": 8
  },
  "entries": []
}
```

## Memory/Context Scorecard

Produced by:

```bash
openminion-eval memory-context-scorecard --out artifacts/memory-context-scorecard.json
openminion-eval memory-context-scorecard \
  --fixtures examples/memory-context-scorecard-cases.json \
  --out artifacts/memory-context-scorecard.json
```

Top-level shape:

```json
{
  "report_version": "memory-context-scorecard.v1",
  "run_id": "memory-context-scorecard-local",
  "summary": {
    "all_blocking_passed": false,
    "blocking_fail_count": 11
  },
  "metrics": []
}
```

Render with:

```bash
openminion-eval report memory-context artifacts/memory-context-scorecard.json --out artifacts/memory-context-scorecard.md
```

## Artifact Validation

Validate known artifacts before uploading them from CI:

```bash
openminion-eval artifact validate artifacts/suite-result.json
openminion-eval artifact validate artifacts/diff.json
openminion-eval artifact validate artifacts/memory-scorecard.json
openminion-eval artifact validate artifacts/delegated-memory-scorecard.json
openminion-eval artifact validate artifacts/delegated-diff.json
openminion-eval artifact validate artifacts/memory-context-scorecard.json
```

Summarize artifacts for logs or review:

```bash
openminion-eval artifact inspect artifacts/suite-result.json
openminion-eval report bundle artifacts/suite-result.json artifacts/diff.json --out artifacts/index.html
```

## Boundary And Manual Review Artifacts

Manual review and red-team boundary artifacts are versioned JSON contracts
exposed through Python helpers and the `manual` CLI commands. They are
documented in [`artifacts-and-manual-grading.md`](artifacts-and-manual-grading.md).

## Portability Rules

1. Use relative artifact paths in public docs and CI examples.
2. Do not store provider credentials, environment dumps, raw private traces, or
   machine-local absolute paths.
3. Keep raw provider evidence outside public artifacts and cite sanitized trace
   ids instead.
