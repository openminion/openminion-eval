# OpenMinion Eval Code Quality and Hygiene

This is the public contributor version of the project's code-quality rules.

The short version:

1. keep eval contracts typed and machine-checkable,
2. keep the standalone boundary explicit,
3. keep ownership clear,
4. keep comments minimal,
5. and prove the change with validation.

## 1. Prefer one truthful owner

Keep each concern in the package area that actually owns it.

Use the nearest clear owner:

1. eval schemas and typed records in `schemas.py` and `interfaces.py`
2. scoring logic in `scorer.py`
3. case execution and reporting in `runner.py`, `suite.py`, and `reporting/`
4. packaged skill-eval resources under `src/openminion_eval/skills/`

Avoid:

1. duplicate helpers,
2. repeated magic literals,
3. public-surface logic leaking into repo-local integration helpers.

## 2. Keep the standalone boundary explicit

`openminion-eval` must stay importable without the surrounding monorepo.

Rules:

1. do not import `openminion.*` inside `src/openminion_eval/`
2. keep host-integration logic under repo-local tests or runners
3. do not turn integration fixtures into accidental public API promises

## 3. Prefer machine-checkable outputs

This package is an evaluation toolkit. Its core outputs should stay structured
enough for callers to inspect programmatically.

Prefer:

1. typed records,
2. explicit fields,
3. deterministic scoring/reporting outputs.

Avoid:

1. prose-heavy summaries when typed facts are enough,
2. implicit result shaping that hides important eval details.

## 4. Keep names and layout honest

Names should match what the code actually owns.

Rules:

1. keep public roots intentional,
2. do not create generic junk-drawer files like `utils.py`,
3. make compatibility surfaces explicit when they exist.

## 5. Keep changes focused

Good practice:

1. one clear purpose per PR,
2. update tests near the change,
3. avoid unrelated refactors in the same patch.

## 6. Validate before calling work done

Before closing work, run the package gates from `openminion-eval/`:

```bash
make check
```

`make check` runs formatting, Ruff, structural quality ratchets, and the
standalone public package tests. The ratchets guard current debt for
file/function size, duplicate private helpers, path and filename drift, broad
exception handlers, bare `# type: ignore`, and hidden sibling-package imports.

If your change affects packaging or public release shape, also run:

```bash
make release-check
```

## 7. When in doubt, choose clarity over cleverness

The package prefers:

1. explicit standalone boundaries over convenience imports,
2. small truthful surfaces over broad magical ones,
3. maintainable structure over short-term shortcuts.

For a broad cleanup, simplification, or maintainability pass, follow
[docs/cleanup-workflow.md](docs/cleanup-workflow.md) so the coverage claim is
backed by a fresh inventory, explicit per-file dispositions, and current
validation.
