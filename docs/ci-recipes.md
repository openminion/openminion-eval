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

For human review, render JSON artifacts before upload:

```bash
openminion-eval artifact validate artifacts/eval/suite-result.json
openminion-eval artifact validate artifacts/eval/diff.json
openminion-eval artifact validate artifacts/eval/memory-scorecard.json
openminion-eval artifact validate artifacts/eval/delegated-memory-scorecard.json
openminion-eval artifact validate artifacts/eval/delegated-diff.json
openminion-eval artifact validate artifacts/eval/memory-context-scorecard.json
openminion-eval report suite artifacts/eval/suite-result.json --out artifacts/eval/suite-result.md
openminion-eval report suite-diff artifacts/eval/diff.json --out artifacts/eval/diff.md
openminion-eval report memory-scorecard artifacts/eval/memory-scorecard.json --out artifacts/eval/memory-scorecard.md
openminion-eval report delegated-memory artifacts/eval/delegated-memory-scorecard.json --out artifacts/eval/delegated-memory-scorecard.md
openminion-eval report delegated-diff artifacts/eval/delegated-diff.json --out artifacts/eval/delegated-diff.md
openminion-eval report memory-context artifacts/eval/memory-context-scorecard.json --out artifacts/eval/memory-context-scorecard.md
openminion-eval report bundle artifacts/eval/suite-result.json artifacts/eval/diff.json artifacts/eval/memory-context-scorecard.json --out artifacts/eval/index.html
```

For a minimal offline memory/context CI case, start from
`examples/memory-context-scorecard-cases.json` and write outputs under a
relative artifact directory:

```bash
openminion-eval memory-context-scorecard \
  --fixtures examples/memory-context-scorecard-cases.json \
  --out artifacts/eval/memory-context-scorecard.json
openminion-eval artifact validate artifacts/eval/memory-context-scorecard.json
openminion-eval report memory-context artifacts/eval/memory-context-scorecard.json --out artifacts/eval/memory-context-scorecard.md
```
