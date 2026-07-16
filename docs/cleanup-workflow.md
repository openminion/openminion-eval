# OpenMinion Eval Cleanup Workflow

Use this workflow for package cleanup, simplification, and maintainability work
without weakening deterministic evaluation contracts.

## Choose the right scope

1. Use a post-authoring pass for the files changed by one feature.
2. Use a bounded sweep for one package area or an explicit file set.
3. Use a broad sweep only when every claimed source, test, or script file will
   receive an explicit review disposition.
4. Keep test cleanup separate when it changes fixtures, harnesses, or scoring
   proof.

Small local cleanup does not need a tracker. Broad cleanup needs a fresh
inventory and a ledger kept outside the committed package surface.

## Freeze the inventory

Before editing:

1. inspect the current worktree and preserve unrelated changes,
2. list current tracked files with `git ls-files`,
3. split source, tests, scripts, and docs when several trees are in scope,
4. record the exact file count and do not add silent scope later.

## Record every disposition

Use one ledger row per claimed file:

`path | area | before LOC | after LOC | disposition | rationale | validation`

Use `trim`, `keep`, `defer-owned:<issue>`, or
`defer-later:<reason>`. Close only when every inventory row has a disposition
and the remaining count is zero.

## Preserve evaluation truth

Simplify duplicate scaffolding, pass-through wrappers, repeated fixture
loading, and unnecessary commentary. Do not silently change score meaning,
grading policy, trace evidence, provider certification, or integration
quarantine behavior. A pre-existing focused-test failure is baseline or
contract drift, not a successful cleanup result.

## Validate

Use focused compilation, Ruff, and pytest while editing. Close the standalone
package slice with:

```bash
make check
```

Run `make test-all` when broader integration-owned tests are in scope and
`make release-check` when packaging or public imports change. Refresh the
inventory if the worktree moves during validation.
