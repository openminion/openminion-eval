# Memory Context Scorecard

The memory/context scorecard is a deterministic local gate for context and
memory quality changes. It answers a narrow question: did the memory or context
input change behavior in a controlled fixture, and did the report preserve the
evidence needed for review?

## Report Version

Current report version: `memory-context-scorecard.v1`.

The report contains:

1. `report_version`
2. `generated_at`
3. `run_id`
4. `fixture_ids`
5. `metrics`
6. `summary`
7. `metadata`

Each metric records its name, status, numeric value, threshold, blocking flag,
evidence references, optional context/provenance trace IDs, and optional paired
ablation fields.

## Metric Policy

Metrics are either blocking or advisory.

Blocking metrics must use one of these statuses:

1. `pass`
2. `warn`
3. `fail`

Advisory metrics use `advisory` and cannot be treated as release blockers by
the local deterministic gate.

`block_usefulness` and `memory_influence` are causal claims. A blocking passing
claim for either metric requires:

1. a disabled outcome,
2. an enabled outcome,
3. a typed task oracle,
4. a non-zero score delta.

Trace presence alone is only evidence linkage. It never proves usefulness or
influence.

Provider-backed or otherwise nondeterministic blocking metrics require variance
evidence. Without variance evidence they must remain advisory.

## Threshold Changes

Threshold changes are behavior changes. A threshold update must include:

1. the old threshold,
2. the new threshold,
3. the fixture IDs affected,
4. an explanation of why the change is stricter, looser, or equivalent,
5. a rollback note naming the prior threshold.

For rollback, restore the previous threshold values and regenerate the report
with the same fixture set and run ID. Deterministic local fixtures should
produce byte-stable output when the same timestamp mode and output path are
used.

## Local Command

Run the packaged fixture set:

```bash
cd openminion-eval
OPENMINION_EVAL_DETERMINISTIC_REPORTS=1 \
  PYTHONPATH=src .venv/bin/python3.11 -m openminion_eval \
  memory-context-scorecard --run-id local-check
```

The default output path is:

```text
.openminion-eval/generated/memory-context-scorecard/<run-id>.json
```

Use `--fixtures` to run a specific deterministic fixture file and `--out` to
choose an explicit artifact path.
