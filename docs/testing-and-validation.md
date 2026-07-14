# OpenMinion Eval Testing And Validation

Status: active
Last updated: 2026-06-20

Purpose: give package users and contributors one package-local reference for
the validation commands that prove `openminion-eval` installs and runs
correctly.

## Install baseline

OpenMinion Eval currently expects:

1. Python 3.11 or newer
2. a recent `pip` that supports editable installs

Recommended local setup from the package root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

## First-user smoke flow

From the package root:

```bash
python3.11 -m openminion_eval.cases
```

Expected outcome:

1. the command exits successfully,
2. it returns a Markdown report,
3. the output lists the packaged starter eval cases.

## Package validation gates

Run from the package root:

```bash
make check
```

## Focused regression tests

The public standalone surface is protected by targeted package tests under
`tests/eval/`.

Example focused run:

```bash
python3.11 -m pytest -q \
  tests/eval/test_public_release_boundary.py \
  tests/eval/test_starter_eval_cases.py
```

## Release smoke

For package-release validation, use:

```bash
make release-check
```

That target builds the artifacts, verifies packaged files, installs the wheel
into a clean target, and smoke-checks the documented public boundary.
