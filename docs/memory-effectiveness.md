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

The package also exposes Python helpers:

```python
from openminion_eval import (
    build_memory_scorecard,
    compare_memory_scorecards,
    load_memory_effectiveness_cases,
    score_memory_case,
)
```

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
