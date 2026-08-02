# OpenMinion Eval Package Docs

Status: alpha

This directory holds the public package documentation for standalone
`openminion-eval`.

## Start Here

| If you want to... | Read |
| --- | --- |
| Install and run the package locally | [`getting-started.md`](getting-started.md) |
| Understand the eval-family contract | [`eval-families.md`](eval-families.md) |
| Author or run starter eval cases | [`eval-cases.md`](eval-cases.md) |
| Add reports to CI | [`ci-recipes.md`](ci-recipes.md) |
| Review manual grading and boundary artifacts | [`artifacts-and-manual-grading.md`](artifacts-and-manual-grading.md) |
| Check public claims and proof coverage | [`standalone-claim-alignment.md`](standalone-claim-alignment.md) and [`certification-readiness-matrix.md`](certification-readiness-matrix.md) |

## Memory And Context Evaluation

- [`memory-effectiveness.md`](memory-effectiveness.md): structured
  SophiaGraph/OpenMinion memory trace scoring, scorecards, paired-run deltas,
  and optional live evidence.
- [`memory-context-scorecard.md`](memory-context-scorecard.md): deterministic
  memory/context quality scorecards, paired ablation evidence, trace links, and
  blocking-vs-advisory metric policy.

## Contributor References

- [`engineering-patterns.md`](engineering-patterns.md)
- [`code-quality-enforcement.md`](code-quality-enforcement.md)
- [`cleanup-workflow.md`](cleanup-workflow.md)
- [`testing-and-validation.md`](testing-and-validation.md)
- `docs/assets/openminion-eval-logo.png`, the public README/social logo asset
  rather than an importable runtime API.

## Package-local code/docs boundaries

1. `README.md` is the public package contract and install surface.
2. `API_COMPATIBILITY.md` records the supported public import roots and
   top-level export policy.
3. The Source Tree Owner Map reference explains the source-tree owner map and
   public-vs-repo-local boundary.
4. `CHANGELOG.md` records package-facing release notes.
5. `CODE_QUALITY.md` summarizes the public contributor code-quality rules.
6. `RELEASING.md` records the package-local release and PyPI publish flow.
7. `scripts/release_check.py` is the canonical package release smoke entrypoint.
8. `python -m openminion_eval.cases` is the package-owned case report CLI.
9. `openminion-eval dataset`, `openminion-eval scorers`,
   `openminion-eval report`, and `openminion-eval integration` expose the
   package-owned dataset authoring, scorer discovery, report rendering, and
   optional integration-tier inspection surfaces.

## Repository-local but not wheel-shipped

1. `tests/eval/integration/` keeps broader integration fixtures and runners.
2. `tests/eval/grounding/` and `tests/eval/runners/` support repo-local eval
   workflows instead of the published package API.

## Public package stance

The `0.0.x` alpha contract is intentionally narrow: deterministic scoring and
reporting helpers, black-box subject adapters, packaged skill-eval resources,
a starter case CLI, and provider-free artifact validators, with release checks
that prove the installed wheel exposes only the documented public surface.
