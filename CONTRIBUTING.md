# Contributing to openminion-eval

Thanks for contributing. This document is self-contained: everything you
need to set up, test, and submit a change lives in this repository.

## Read first

Before substantial code changes, read:

1. [README.md](./README.md)
2. [API_COMPATIBILITY.md](./API_COMPATIBILITY.md)
3. [docs/README.md](./docs/README.md)
4. [docs/source-tree-owner-map.md](./docs/source-tree-owner-map.md)
5. [docs/getting-started.md](./docs/getting-started.md)
6. [docs/engineering-patterns.md](./docs/engineering-patterns.md)
7. [docs/code-quality-enforcement.md](./docs/code-quality-enforcement.md)
8. [docs/testing-and-validation.md](./docs/testing-and-validation.md)
9. [RELEASING.md](./RELEASING.md) when the work affects packaging or release
   behavior

## Repository layout

```
openminion-eval/
├── src/openminion_eval/        # public package shipped on PyPI
│   ├── tools/  freshness/  routing/  closure/  policy/  skills/
│   ├── runner.py  scorer.py  suite.py
│   ├── schemas.py  interfaces.py  config.py  constants.py
│   └── reporting/  family_support.py
├── tests/                       # all tests
│   └── eval/
│       ├── integration/         # repo-local integration tooling
│       │                        # (memory eval + trace flywheel; NOT
│       │                        # shipped in the public wheel)
│       └── runners/             # CLI runner scripts
├── pyproject.toml
└── conftest.py                  # pytest bootstrap; sys.path setup
```

The public wheel is everything under `src/openminion_eval/`. Anything
under `tests/` (including `tests/eval/integration/`) is repo-local and
stays out of the published package.

## Setup

Requires Python 3.11+.

```bash
# 1. Clone and enter the repo
git clone https://github.com/openminion/openminion-eval.git openminion-eval
cd openminion-eval

# 2. Create and activate a virtualenv
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install in editable mode with dev extras
pip install -e ".[dev]"

# 4. Install local hooks, including commit-message enforcement
make hooks-install
```

## Running tests

```bash
# Full test suite (public + repo-local integration)
python -m pytest -q tests/

# Public-surface tests only (skip integration that needs the monorepo)
python -m pytest -q tests/ --ignore=tests/eval/integration \
  --deselect tests/eval/test_memory_eval.py \
  --deselect tests/eval/test_trace_flywheel.py

# Public boundary smoke
python -m pytest -q tests/eval/test_public_release_boundary.py
```

The repo-local integration tests under `tests/eval/test_memory_eval.py`
and `tests/eval/test_trace_flywheel.py` require the surrounding
`openminion` monorepo to be present as a sibling checkout; standalone
contributors can skip them.

## Running lint

```bash
python -m ruff check .
```

## Style and conventions

1. Follow existing style. The codebase uses standard Python conventions:
   `from __future__ import annotations`, type hints throughout, dataclasses
   for typed records, no implicit globals.
2. Keep changes focused. One PR = one logical change.
3. Prefer typed-fact APIs over prose-summary outputs (rationale: this is
   an evaluation toolkit — outputs need to be machine-checkable).
4. Add or update tests for any behavior change. Tests live under `tests/`
   mirroring the `src/openminion_eval/` layout.
5. Do not introduce imports from `openminion.*` (the monorepo) into
   `src/openminion_eval/`. The public package must remain importable
   without the monorepo present. Imports from `openminion.*` are only
   allowed under `tests/eval/integration/` and `tests/eval/runners/`.
6. Don't add CI-only conveniences (path tweaks, sys.path injection) to
   `src/`. If a script needs them, put them in the script itself or in
   `conftest.py`.

Commit message guidance:

1. Use commit messages in the form `<type>: <summary>` or
   `<type>(<scope>): <summary>`.
2. Approved current types are `feat`, `fix`, `docs`, `refactor`, `test`,
   `chore`, `style`, and `build`.
3. In `openminion-eval`, scope is optional but recommended when it improves
   owner clarity, for example `routing`, `policy`, `reporting`, `skills`,
   `tools`, `freshness`, `docs`, or `release`.
4. Keep the summary specific to the landed change and avoid vague messages like
   `update`.
5. Prefer the most specific truthful type; do not use `chore` when `docs`,
   `test`, `refactor`, or `build` is more accurate.
6. Do not use local shorthand or planning labels as normal commit types.

The same policy runs locally through `make hooks-install` and again in GitHub
Actions on pull requests plus `dev`/`main` pushes.

## Submitting a pull request

1. Fork and create a branch from `main`.
2. Make your change; add or update tests; run `pytest -q tests/` and
   `ruff check .` locally.
3. Open a PR with a clear summary. In the description, include:
   - what changed and why,
   - the exact commands you ran for validation,
   - whether the change affects the public standalone surface
     (`src/openminion_eval/`) or only repo-local integration tooling.
4. Keep PRs small and reviewable.
5. Don't bundle unrelated refactors. If you find adjacent cleanup
   opportunities, open a separate PR.

## Legal basics

1. You keep ownership of your contributions.
2. By submitting a contribution, you license it under the project license (MIT).
3. Only submit code or content you have the right to contribute.
4. Do not add third-party code or assets unless their license is
   compatible and clearly documented.
5. Project names and logos are not granted for endorsement use.
6. `openminion-eval` is provided on an "as is" basis under the project
   license; there are no guarantees about performance, reliability,
   availability, cost outcomes, or malfunction-related consequences.
7. If you configure third-party providers or paid infrastructure while
   developing or testing, you are responsible for any resulting charges.
8. See [LICENSE](./LICENSE) for the full legal terms.

## Code of conduct

By participating, you agree to follow [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md).
