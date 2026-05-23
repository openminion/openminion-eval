# Support

## What is supported today

Current public standalone support is limited to:

1. the generic eval primitives,
2. package-owned support required by those primitives,
3. canonical non-memory families under `openminion_eval`.

## Not yet covered by the standalone public support promise

The following surfaces are repository-owned integration/report tooling rather
than supported standalone public API:

1. `tests/eval/integration/` (memory eval + trace flywheel)
2. memory fixtures and baselines
3. companion reports
4. grounding eval
5. eval baselines and runners

## Getting help

For usage questions or bug reports:

1. include the package version,
2. include the exact import path or command you ran,
3. state whether the issue affects the public standalone surface or an
   integration/report surface,
4. include traceback or reproduction steps when available.

If the issue only reproduces with `openminion` present, call that out
explicitly; that usually means the problem is on an integration-owned path
rather than the standalone non-memory contract.
