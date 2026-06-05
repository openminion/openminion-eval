# OpenMinion Eval Certification Readiness Matrix

Status: alpha

This matrix records the package-local proof points expected before treating the
standalone `openminion-eval` surface as release-ready.

## Public surface proofs

1. root imports remain stable for `openminion_eval` and the documented
   non-memory eval families,
2. package docs and examples match the published public contract,
3. built artifacts install cleanly without depending on the OpenMinion runtime
   tree,
4. packaged skill resources remain present in the built wheel,
5. repo-local memory/integration tooling stays outside the public wheel.

## Package-local validation anchors

1. `tests/eval/test_package_structure.py`
2. `tests/eval/test_public_release_boundary.py`
3. `tests/eval/test_family_imports.py`
4. `tests/eval/test_interfaces_contract.py`
5. `scripts/check_release_package.py`

## Boundary reminder

The public package owns the generic eval runner/scorer/suite/interfaces/schemas
surface and the canonical non-memory eval families. Repo-local integration
tooling under `tests/eval/` remains source-only validation support rather than
wheel-shipped API.
