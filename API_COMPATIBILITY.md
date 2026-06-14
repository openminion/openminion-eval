# openminion-eval API Compatibility Policy

Owner: `openminion-eval`
Status: `alpha`
Scope: stable import-root and versioning policy for external
`openminion-eval` consumers

## Purpose

Define what external consumers can rely on when they build against the
standalone `openminion-eval` package.

## Stable import roots

External consumers should treat these import roots as the supported public API:

- `openminion_eval`
- `openminion_eval.cases`
- `openminion_eval.tools`
- `openminion_eval.freshness`
- `openminion_eval.routing`
- `openminion_eval.closure`
- `openminion_eval.policy`
- `openminion_eval.skills`
- `openminion_eval.goal_trajectory`
- `openminion_eval.reporting`

The top-level `openminion_eval` package is the preferred entrypoint for common
usage.

## Stable top-level exports

The following top-level exports are part of the current public contract:

- `openminion_eval.EVAL_INTERFACE_VERSION`
- `openminion_eval.EvalRunner`
- `openminion_eval.EvalScorer`
- `openminion_eval.EvalSuite`
- `openminion_eval.EvalResult`
- `openminion_eval.EvalSummary`
- `openminion_eval.EvalTranscript`
- canonical case/report builders for `tools`, `freshness`, `routing`,
  `closure`, `policy`, and `skills`
- starter case registry exports: `EvalCase`, `EvalCaseResult`, `GradeMode`,
  `GradeOutcome`, `grade_case(...)`, and `registered_cases(...)`
- goal trajectory exports such as `GoalTrajectoryBenchmark`,
  `GoalTrajectoryReport`, `GoalDriftSignalKind`, `run_benchmark(...)`, and
  `aggregate_reports(...)`
- certification helpers such as `FamilyCertificationSignal` and
  `apply_family_signals_to_certification_cells(...)`

## Versioning posture

`openminion-eval` is currently `0.x` software.

That means:

1. additive API changes are preferred,
2. breaking changes are still possible,
3. breaking changes must be called out in release notes and package docs,
4. stable import roots should not be moved casually even during `0.x`.

## Deprecation policy

When a public symbol or import path needs to change:

1. prefer an additive replacement first,
2. document the new path in `README.md`,
3. keep the old path available for at least one `0.x` release when practical,
4. remove only after the deprecation is documented in release notes.

If a safety or correctness issue requires immediate removal, the release notes
must say so explicitly.

## Compatibility tests

Public-contract confidence should be enforced by tests that cover:

1. import-root availability,
2. public top-level export availability,
3. version agreement between `pyproject.toml` and the installed package,
4. package independence from the OpenMinion runtime tree,
5. public release boundary checks for non-memory standalone surfaces,
6. release/install smoke for built artifacts,
7. packaged skill/resource availability,
8. goal trajectory export and report behavior,
9. package-local docs, examples, and release-smoke entrypoints,
10. `openminion_eval.cases` CLI/report behavior.

## Non-goals

This policy does not promise:

1. the repo-local integration fixtures under `tests/eval/integration/`,
2. memory-eval internals or memory provider baselines as wheel-shipped API,
3. compatibility for undocumented import paths,
4. runtime-loaded configuration beyond the current documented no-op
   compatibility surface.
