# OpenMinion Eval Code Quality Enforcement

Status: active
Last updated: 2026-06-20

Purpose: summarize the public contributor view of the active quality gates for
`openminion-eval`.

## What contributors should expect

OpenMinion Eval enforces code quality through four layers:

1. package-level boundaries and typed-surface rules,
2. automated lint, tests, and release-check validation,
3. structural quality ratchets for source shape and package boundaries,
4. focused standalone-vs-integration separation for new work.

## Required local validation

For normal contribution work, run:

```bash
make check
```

For the structural ratchets alone, run:

```bash
make validate-patterns
```

For broader release proof, also run:

```bash
make release-check
```

## What the gates protect

The active checks are designed to catch drift in areas such as:

1. standalone import-boundary regressions,
2. packaged asset omissions,
3. public-surface drift between docs and shipped code,
4. repo-local integration helpers leaking into the wheel,
5. deterministic eval-case and reporting regressions.
6. new oversized files/functions, duplicate helpers, broad exceptions, path
   drift, bare type-ignore pragmas, and hidden sibling imports.

## Public validation expectations

1. Keep changes focused and reviewable.
2. Include exact validation commands and results in the PR description.
3. Do not treat repo-local test helpers as stable package API.
4. Do not mix unrelated cleanup into a feature PR.

## See also

1. [`engineering-patterns.md`](engineering-patterns.md)
2. [`getting-started.md`](getting-started.md)
3. [`testing-and-validation.md`](testing-and-validation.md)
