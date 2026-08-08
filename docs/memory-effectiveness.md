# Memory-Effectiveness Trace Scoring

Status: alpha

`openminion-eval` can score structured memory-effectiveness traces for
OpenMinion runs that use SophiaGraph-backed persistent memory.

This is a deterministic package surface. It does not run OpenMinion, call an
LLM provider, create memories, or inspect assistant prose. It scores typed trace
artifacts supplied by a subject adapter or test fixture.

## What It Measures

The scorecard separates four components:

- `save`: required memory ids were written or observed as saved
- `retrieval`: required memory ids appeared in retrieval traces
- `usage`: required memory ids supported claims or tool/action traces
- `longitudinal`: later runs adopted corrections or retained approved memory

Critical failures block a clean pass even when aggregate score is high. The
default critical gates cover wrong namespace, private or stale memory use, and
hallucinated memory ids.

## Run Locally

Score a structured trace artifact:

```bash
openminion-eval memory-effectiveness score memory-trace.json --out memory-scorecard.json
```

Use a custom fixture file:

```bash
openminion-eval memory-effectiveness score memory-trace.json --cases cases.json --out memory-scorecard.json
```

Render the scorecard for review:

```bash
openminion-eval report memory-scorecard memory-scorecard.json --out memory-scorecard.md
```

The command prints a compact JSON summary to stdout. A successful clean
scorecard exits `0`. A valid scorecard with critical failures or unmatched
cases exits `1`. Malformed input exits `2`, writes a concise error to stderr,
and does not print a scorecard summary.

Typical stdout:

```json
{
  "artifact": "memory-scorecard.json",
  "case_count": 1,
  "critical_failure_count": 0,
  "overall_score": 1.0,
  "run_id": "memory-effectiveness-local",
  "suite_id": "openminion-sophiagraph-memory-effectiveness",
  "unmatched_case_count": 0
}
```

The package also exposes Python helpers:

```python
from openminion_eval import (
    build_memory_scorecard,
    compare_memory_scorecards,
    default_memory_effectiveness_cases_path,
    load_memory_effectiveness_cases,
    score_memory_case,
)
```

`default_memory_effectiveness_cases_path()` returns the packaged default fixture
resource for callers that want to inspect the shipped cases directly.

## Trace Shape

Trace JSON can be either a list of traces or an object with a `traces` list.
Each trace should name the saved, retrieved, and used memory ids explicitly:

```json
{
  "traces": [
    {
      "case_id": "repo-convention-positive",
      "run_id": "enabled",
      "memory_mode": "enabled",
      "saved_memory_ids": ["mem-release-check"],
      "retrieved_memory_ids": ["mem-release-check"],
      "used_memory_ids": ["mem-release-check"],
      "redaction_status": "sanitized",
      "supporting_claims": [
        {
          "claim": "This repo runs make check before release.",
          "memory_id": "mem-release-check"
        }
      ],
      "tool_calls": [
        {
          "tool": "shell",
          "arguments_ref": "sha256:release-check",
          "memory_ids": ["mem-release-check"]
        }
      ],
      "namespace": "agent:openminion/project:sophiagraph"
    }
  ]
}
```

The scorer uses the structured ids only. It does not parse final answer text.
When a live trace contains private raw references, mark the trace
`redaction_status` explicitly and keep raw artifacts outside the public
scorecard.

## Benchmark Adapter Samples

The package includes small packaged sample manifests for LoCoMo,
LongMemEval, and BEAM-shaped memory-effectiveness cases:

```python
from openminion_eval import (
    default_memory_benchmark_manifest_path,
    load_packaged_memory_benchmark_sample,
)

sample = load_packaged_memory_benchmark_sample("locomo")
manifest = default_memory_benchmark_manifest_path("locomo")
print(sample.source.source_revision)
print(sample.cases[0].case_id)
print(manifest.name)
```

These samples are adapters, not redistributed benchmark datasets. Full
benchmark corpora stay with their upstream owners. Each imported manifest must
declare `source_url`, `source_revision`, `source_license`, `fixture_version`,
and a `fixture_hash` over the case payloads so downstream evidence can cite the
exact source snapshot used.

## Paired Runs

For memory-effectiveness evidence, run the same case twice:

- `memory_mode="disabled"` baseline with no retrieved or used ids
- `memory_mode="enabled"` run with SophiaGraph-backed trace ids

Use `compare_memory_scorecards(...)` to compute the enabled-minus-disabled
delta. Disabled-baseline memory misses lower the baseline score; enabled-run
critical failures block improvement.

## Optional Live Evidence

Live provider runs can be useful release evidence, but they do not replace the
deterministic trace scorer.

Recommended live flow:

1. run the deterministic fixture scorer and confirm it passes,
2. run a small OpenMinion scenario that teaches a repo convention,
3. persist through SophiaGraph,
4. run a later turn with memory enabled,
5. export the structured trace artifact,
6. score that trace with `openminion-eval memory-effectiveness score`.

Live evidence must still be grounded in structured saved, retrieved, cited, and
tool/action memory ids.

## Delegated Multi-Agent Memory

The package includes eight named delegated-memory cases spanning bounded shared
recall, sibling scratch isolation, private direct-ID attacks, graph and
federation boundaries, reviewed child learning, revocation/retry, nested
delegation, and MCP/A2A audience mismatch. These cases are packaged JSON
fixtures and deterministic scorers; they do not add a runtime dependency on
Sophiagraph or require provider access.

```python
from openminion_eval import (
    DelegatedMemoryEvalTrace,
    build_delegated_memory_scorecard,
    load_delegated_memory_cases,
    write_delegated_memory_scorecard,
)

cases = load_delegated_memory_cases()
traces = tuple(
    DelegatedMemoryEvalTrace(
        case_id=case.case_id,
        retrieved_memory_ids=case.required_recall_ids,
    )
    for case in cases
)
scorecard = build_delegated_memory_scorecard(cases, traces)
write_delegated_memory_scorecard("delegated-memory-scorecard.json", scorecard)
```

Scoring is deterministic over typed IDs and counters. Unauthorized disclosure,
sibling scratch leakage, direct-ID bypass, post-revocation operations,
forbidden re-sharing, poisoning acceptance, invalid provenance, or failed
forgetting is a critical failure even when useful recall is perfect. Context
delivered before revocation is recorded separately and is not misreported as a
future-operation failure.

The same scorer is available from the CLI:

```bash
openminion-eval memory-effectiveness delegated-score delegated-trace.json --out delegated-memory-scorecard.json
```

Render or compare delegated-memory artifacts:

```bash
openminion-eval report delegated-memory delegated-memory-scorecard.json --out delegated-memory-scorecard.md
openminion-eval memory-effectiveness delegated-diff previous-delegated.json current-delegated.json --out delegated-diff.json
```

Delegated trace JSON accepts either a list or an object with a `traces` list:

```json
{
  "traces": [
    {
      "case_id": "bounded-project-recall",
      "retrieved_memory_ids": ["project-approved"],
      "sibling_scratch_ids": [],
      "direct_id_bypass_ids": [],
      "revoked_future_operation_ids": [],
      "forbidden_reshare_ids": [],
      "accepted_poisoning_ids": [],
      "provenance_failures": [],
      "forgetting_failures": [],
      "latency_ms": 3.5,
      "token_count": 42
    }
  ]
}
```

`write_delegated_memory_scorecard(...)` and
`load_delegated_memory_scorecard(...)` persist the deterministic scorecard JSON
used by release checks and downstream CI jobs.

Runnable example traces live under `examples/`:

```bash
openminion-eval memory-effectiveness score examples/memory-effectiveness-trace.json --cases examples/memory-effectiveness-cases.json --out artifacts/memory-scorecard.json
openminion-eval memory-effectiveness delegated-score examples/delegated-memory-trace.json --out artifacts/delegated-memory-scorecard.json
```
