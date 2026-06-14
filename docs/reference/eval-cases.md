# Eval Cases

Status: `alpha`
Scope: package-local `EvalCase` registry and CLI contract

`openminion_eval.cases` owns the lightweight case roster used by `make eval`
and `python -m openminion_eval.cases`. The current registry ships five starter
cases across coding, research, recovery, multi-tool, and memory recall.

## Public Surface

Stable imports:

- `openminion_eval.EvalCase`
- `openminion_eval.EvalCaseResult`
- `openminion_eval.GradeMode`
- `openminion_eval.GradeOutcome`
- `openminion_eval.grade_case`
- `openminion_eval.registered_cases`
- `openminion_eval.cases`

The top-level exports are provided for common consumer use. The
`openminion_eval.cases` import root remains available for CLI and registry
helpers.

## Grade Modes

- `structural`: inspects local traces, files, or package-visible evidence
  without making a model call.
- `live`: reserved for opt-in agent runs and gated by
  `OPENMINION_EVAL_LIVE=1`.
- `manual`: records an ungraded result for human review.

`SKIPPED` and `UNGRADED` are non-failing outcomes for the CLI. `FAIL` is the
only outcome that produces a non-zero exit code.

## CLI

Run the starter roster from a source checkout:

```bash
make eval
```

Run the installed package module directly:

```bash
python -m openminion_eval.cases
```

Filter by category:

```bash
python -m openminion_eval.cases --category coding
```

Write a Markdown report:

```bash
python -m openminion_eval.cases --out report.md
```

Structural cases that depend on OpenMinion runtime evidence resolve anchors
from `OPENMINION_REPO_ROOT` when set, then from the nearest checkout-like
parent, and finally from the current working directory. Missing anchors produce
`SKIPPED`, not `FAIL`, because the evidence packet is environment-dependent.

## Adding Cases

New package-owned cases should:

1. use a stable `case_id`,
2. choose one category and one grade mode,
3. keep grading structural unless live execution is deliberately required,
4. return either `GradeOutcome` or `(GradeOutcome, detail)` from `grade_fn`,
5. add focused tests for result normalization and CLI/report behavior,
6. update this reference when the public case roster or mode contract changes.

Repository-local integration harnesses may keep broader runtime probes under
`tests/eval/integration/`; those probes are not part of the wheel-shipped
public case registry unless they are explicitly promoted here.
