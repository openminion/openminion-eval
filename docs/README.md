# OpenMinion Eval Package Docs

Status: alpha

This directory holds the public package documentation for standalone
`openminion-eval`.

## Package-local references

- [`getting-started.md`](getting-started.md) gives the
  package-local bootstrap and execution summary for contributors and automation.
- [`engineering-patterns.md`](engineering-patterns.md)
  summarizes the package-local engineering and boundary rules for contributors.
- [`code-quality-enforcement.md`](code-quality-enforcement.md)
  summarizes the active public quality gates and validation posture.
- [`testing-and-validation.md`](testing-and-validation.md)
  records the package-local install, smoke, test, lint, and release-check
  flow.
- [`eval-families.md`](eval-families.md) records the
  package-owned non-memory eval-family contracts.
- [`eval-cases.md`](eval-cases.md) records the starter
  `EvalCase` registry, grade modes, CLI behavior, and extension rules.
- [`ci-recipes.md`](ci-recipes.md) gives pytest-native and CI examples for
  package users.
- [`artifacts-and-manual-grading.md`](artifacts-and-manual-grading.md)
  documents scorer traces, manual review queues, adjudication imports, and
  integration quarantine.
- [`standalone-claim-alignment.md`](standalone-claim-alignment.md)
  maps public standalone claims to shipped package surfaces and proof.
- [`certification-readiness-matrix.md`](certification-readiness-matrix.md)
  records the current standalone and host-integration proof targets for the
  public package surface.
- `docs/assets/openminion-eval-logo.png` is the package-local README/social
  logo asset. It is a public repo asset, not an importable runtime API.

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

## Repository-local but not wheel-shipped

1. `tests/eval/integration/` keeps broader integration fixtures and runners.
2. `tests/eval/grounding/` and `tests/eval/runners/` support repo-local eval
   workflows instead of the published package API.

## Public package stance

The `0.0.x` alpha contract is intentionally narrow: deterministic scoring and
reporting helpers, packaged skill-eval resources, a starter case CLI, and
release checks that prove the installed wheel exposes only the documented
public surface.
