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

## Comment and docstring review

This rule applies to every contributor and coding agent, including tests and
scripts. Let clear names, types and direct control flow explain ordinary steps.
Review every added or changed comment and docstring in the final diff; remove
obvious restatements, decorative banners and duplicated walkthroughs. Keep one
concise explanation at the owner when a constraint is not obvious.

Preserve public API and model-facing descriptions, required notices/directives,
and useful safety, compatibility and regression-oracle rationale. Keep short
factual module explainers; move longer design/history narratives to docs.
Passing automated checks does not replace this review, and there is no comment
quota. Check current source and existing reports before filing cleanup debt;
keep unrelated cleanup out of a feature PR.

## Minimum usable code

These rules apply to maintainers, external contributors and coding agents, in
new work and cleanup of merged code. Start with actual callers, supported inputs
and concrete failure paths. Use the existing owner and a direct implementation;
add a helper or abstraction only when current callers need it.

Do not add speculative frameworks, unused modes or extension points,
pass-through wrappers, duplicate validation, silent defaults, blanket exception
handling, or retries that hide failures. Validate at the boundary that owns the
contract instead of repeatedly normalizing internal values. A retry needs a
specific transient failure, a bound and safe repeat behavior. Preserve necessary
trust-boundary checks, permissions, compatibility, persistence/replay and cleanup.

Preserve typed evaluation contracts, reproducible scoring and evidence
provenance. Keep host-runtime integration outside the standalone package core.

## Review and cleanup evidence

Review the complete final diff and every new delta for simplicity and the
[comment and docstring rules](#comment-and-docstring-review). Record the exact
reviewed head, checked callers, supported failure cases, findings and disposition
in the PR or linked review evidence. Passing automated checks does not replace
this review. Block approval or merge while a substantiated finding remains;
request the smaller existing-owner change when it satisfies the same contract.
Validate the current integration with the target branch and require all required
hosted checks on the exact head before merging. Never relax a gate to land cleanup.

For merged work, first verify that the code still exists on the current
development branch. Reuse existing findings and respect active ownership; record
obsolete findings without reopening old PRs, duplicating issues or taking over
another contributor's branch. Do not label all historical code clean from a
partial review.

A broad cleanup starts with a fresh file inventory at a recorded revision. Keep
source, tests and scripts separate, give each claimed file a trim, keep or explicit
defer disposition, and work in bounded tranches. Record callers, rationale,
validation and remaining work after each tranche; deferred files remain open.
Refresh evidence if the tree changes during validation. Record before/after LOC
for source cleanup and retain a simplification only when it reduces code and
improves readability while preserving the contract. Review the changed files
again after authoring; this is not proof of a package-wide sweep.

Preserve test assertions and negative controls. Do not introduce skips, expected
failures, extra waits or retries to conceal a regression. Preserve script output,
exit behavior and operator clarity. Run the repository's documented gates and
report local, hosted, installed-package and live-system evidence separately.
