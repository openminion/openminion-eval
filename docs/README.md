# OpenMinion Eval Package Docs

Status: alpha

This directory holds the public package documentation for standalone
`openminion-eval`.

## Package-local references

- [`eval-families.md`](eval-families.md) records the
  package-owned non-memory eval-family contracts.
- [`eval-cases.md`](eval-cases.md) records the starter
  `EvalCase` registry, grade modes, CLI behavior, and extension rules.
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
4. `RELEASING.md` records the package-local release and PyPI publish flow.
5. `scripts/release_check.py` is the canonical package release smoke entrypoint.
6. `python -m openminion_eval.cases` is the package-owned case report CLI.

## Repository-local but not wheel-shipped

1. `tests/eval/integration/` keeps broader integration fixtures and runners.
2. `tests/eval/grounding/` and `tests/eval/runners/` support repo-local eval
   workflows instead of the published package API.

## Public package stance

The `0.1.x` alpha contract is intentionally narrow: deterministic scoring and
reporting helpers, packaged skill-eval resources, a starter case CLI, and
release checks that prove the installed wheel exposes only the documented
public surface.
