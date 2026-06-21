# CI Recipes

Status: alpha
Last updated: 2026-06-21

Purpose: copyable, offline CI patterns for the standalone `openminion-eval`
package.

## Pytest-native recipe

Use package APIs directly when CI owns the subject under test. The executable
package-local version lives at `examples/test_pytest_recipe.py`.

## GitHub Actions shape

```yaml
name: eval
on: [push, pull_request]
jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: python -m pip install -e ".[dev]"
      - run: python -m pytest -q examples tests/eval/test_release_check.py
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: eval-artifacts
          path: artifacts/
```

## Exit-code policy

1. `openminion-eval run` exits `0` only when every transcript passes.
2. `openminion-eval diff` exits `1` for `new_fail`, `regressed`, or
   `missing_transcript`.
3. Pytest examples should assert thresholds directly and keep failure text
   deterministic.

## Deterministic mode

Set `OPENMINION_EVAL_DETERMINISTIC_REPORTS=1` when asserting exact family report
bytes. This replaces wall-clock timestamps with the deterministic report
timestamp.

## Artifact upload

Write suite results and trace artifacts to a relative path such as
`artifacts/eval/`. Do not include provider secrets, environment dumps, absolute
workspace paths, or host-local runtime state in public artifacts.
