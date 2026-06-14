# OpenMinion Eval Package Docs

This package-local docs directory is reserved for standalone `openminion-eval`
documentation and public release references.

Package-local reference docs:

- `docs/reference/certification-readiness-matrix.md` records the current
  standalone and integration proof targets for the public package surface.
- `docs/reference/eval-cases.md` records the package-owned starter case
  registry, grade modes, CLI behavior, and extension rules.
- `docs/assets/openminion-eval-logo.png` is the package-local README/social
  logo asset. It is a public repo asset, not an importable runtime API.

Package-local code/docs boundaries:

1. `README.md` is the public package contract and install surface.
2. `API_COMPATIBILITY.md` records the supported public import roots and
   top-level export policy.
3. `src/openminion_eval/README.md` explains the package-owned module layout and
   public-vs-repo-local boundary.
4. `RELEASING.md` records the package-local release and PyPI publish flow.
5. `scripts/release_check.py` is the canonical package release smoke entrypoint.
6. `python -m openminion_eval.cases` is the package-owned case report CLI.

Repository-local but not wheel-shipped:

1. `tests/eval/integration/` keeps broader integration fixtures and runners.
2. `tests/eval/grounding/` and `tests/eval/runners/` support repo-local eval
   workflows instead of the published package API.
