# OpenMinion Eval Package Docs

This package-local docs directory is reserved for standalone `openminion-eval`
documentation and public release references.

Package-local reusable docs:

- `docs/certification-readiness-matrix.md` records the current standalone and
  integration proof targets for the public package surface.
- `docs/assets/openminion-eval-logo.png` is the package-local README/social
  logo asset.

Package-local code/docs boundaries:

1. `README.md` is the public package contract and install surface.
2. `src/openminion_eval/README.md` explains the package-owned module layout and
   public-vs-repo-local boundary.
3. `scripts/release_check.py` is the canonical package release smoke entrypoint.

Repository-local but not wheel-shipped:

1. `tests/eval/integration/` keeps broader integration fixtures and runners.
2. `tests/eval/grounding/` and `tests/eval/runners/` support repo-local eval
   workflows instead of the published package API.
