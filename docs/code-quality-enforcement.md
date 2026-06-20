# OpenMinion Eval Code Quality Enforcement

Status: active
Last updated: 2026-06-20

Purpose: summarize the public contributor view of the active quality gates for
`openminion-eval`.

## What contributors should expect

OpenMinion Eval enforces code quality through three layers:

1. package-level boundaries and typed-surface rules,
2. automated lint, tests, and release-check validation,
3. focused standalone-vs-integration separation for new work.

## Required local validation

For normal contribution work, run:

```bash
make lint
make test
```

For broader release proof, also run:

```bash
python3.11 scripts/release_check.py
```

## What the gates protect

The active checks are designed to catch drift in areas such as:

1. standalone import-boundary regressions,
2. packaged asset omissions,
3. public-surface drift between docs and shipped code,
4. repo-local integration helpers leaking into the wheel,
5. deterministic eval-case and reporting regressions.

## Public validation expectations

1. Keep changes focused and reviewable.
2. Include exact validation commands and results in the PR description.
3. Do not treat repo-local test helpers as stable package API.
4. Do not mix unrelated cleanup into a feature PR.

## See also

1. [`engineering-patterns.md`](engineering-patterns.md)
2. [`getting-started.md`](getting-started.md)
3. [`testing-and-validation.md`](testing-and-validation.md)
