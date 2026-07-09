# Releasing `openminion-eval`

Status: `alpha`
Scope: package-local release contract for the standalone `openminion-eval`
distribution

`openminion-eval` is published under MIT. This document keeps the package-local
release path explicit so publishing does not depend on host application
context.

## Release Contract

A publishable release must satisfy all of the following:

1. `pyproject.toml` and the installed package version agree.
2. `LICENSE` and `NOTICE` are present and included in built artifacts.
3. `README.md` describes install, public release boundary, examples, and
   package-local docs/script expectations for external consumers.
4. `API_COMPATIBILITY.md` names the stable import roots and deprecation policy.
5. `docs/` remains the canonical package-local docs root.
6. `docs/source-tree-owner-map.md` continues to document the package
   owner map and repo-local integration boundary.
7. The starter `EvalCase` registry and `openminion_eval.cases` CLI are covered
   by package tests and release smoke.
8. Package tests pass from the package root.
9. Both wheel and sdist build successfully.
10. A clean install smoke passes from a fresh target directory using the built
   wheel.
11. The package still ships only the intended standalone non-memory surface.

## Version Bump

Update the package metadata version in:

- `pyproject.toml`

If the release changes the external consumer contract, also update:

- `README.md`
- `API_COMPATIBILITY.md`
- `docs/README.md`
- `docs/`

## Build and Validation

Preferred deterministic release check:

```bash
python3.11 scripts/release_check.py
```

The script builds wheel+sdist, installs the wheel into a clean target,
verifies packaged assets, and smoke-checks the public boundary.

Manual equivalent:

```bash
rm -rf build dist src/*.egg-info
python3.11 -m pytest -q tests/eval \
  --ignore=tests/eval/integration \
  --ignore=tests/eval/test_eval_adjacent_owner_dispositions.py \
  --ignore=tests/eval/test_memory_eval.py \
  --ignore=tests/eval/test_trace_flywheel.py
python3.11 -m build
python3.11 -m pip install --no-deps --target wheel-install/openminion-eval dist/openminion_eval-*.whl
```

## Publish Sequence

`openminion-eval` follows the same repo-family release path as the other public
package repos:

1. prepare and validate an RC branch,
2. push an RC tag such as `v0.0.2rc1` to publish to TestPyPI,
3. install and smoke-test the RC artifact from TestPyPI,
4. prepare and validate the final non-RC branch,
5. dispatch the `Release` workflow from that final branch with
   `target=testpypi`,
6. install and smoke-test the final TestPyPI artifact,
7. push the final non-RC tag such as `v0.0.2` to publish to PyPI,
8. create the GitHub Release using the bare version title, such as `0.0.2`.

Manual `twine upload` remains fallback-only. Do not treat it as the canonical
flow when trusted publishing is available.

## GitHub Actions Trusted Publishing

The canonical release workflow for this package is
`.github/workflows/release.yml`.

Trusted publishing must be configured for:

1. TestPyPI environment: `testpypi`
2. PyPI environment: `pypi`

## Notes

1. `openminion-eval` is package-local and standalone; the host application
   consumes it as an external dependency.
2. Repo-local integration helpers may remain in this repository without being
   part of the wheel-shipped public contract.
3. Generated caches and `*.egg-info` directories are build artifacts and should
   not be kept as source-of-truth package content.
