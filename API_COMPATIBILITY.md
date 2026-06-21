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
- `openminion_eval.cli`
- `openminion_eval.cases`
- `openminion_eval.tools`
- `openminion_eval.freshness`
- `openminion_eval.routing`
- `openminion_eval.closure`
- `openminion_eval.policy`
- `openminion_eval.skills`
- `openminion_eval.goal_trajectory`
- `openminion_eval.reporting`
- `openminion_eval.suite_artifacts`
- `openminion_eval.datasets`
- `openminion_eval.family_registry`
- `openminion_eval.manual`

The top-level `openminion_eval` package is the preferred entrypoint for common
usage.

## Stable top-level exports

The following top-level exports are part of the current public contract:

- `openminion_eval.EVAL_INTERFACE_VERSION`
- `openminion_eval.EvalRunner`
- `openminion_eval.EvalRunContext`
- `openminion_eval.EvalScorer`
- `openminion_eval.EvalSubjectInterface`
- `openminion_eval.EvalSuite`
- `openminion_eval.EvalResult`
- `openminion_eval.EvalRunManifest`
- `openminion_eval.EvalSummary`
- `openminion_eval.EvalSuiteResult`
- `openminion_eval.EvalTranscript`
- suite artifact helpers: `build_run_manifest(...)`,
  `hash_transcripts(...)`, `write_suite_result(...)`,
  `load_suite_result(...)`, and `compare_suite_results(...)`
- dataset loader helpers: `load_eval_dataset(...)`,
  `load_eval_dataset_json(...)`, `load_eval_dataset_jsonl(...)`, and
  `hash_eval_dataset(...)`
- CLI entrypoints: `openminion-eval` and `python -m openminion_eval`
- suite selection helper: `select_transcripts(...)`
- compatibility validators such as `ensure_eval_subject_compatibility(...)`
- canonical case/report builders for `tools`, `freshness`, `routing`,
  `closure`, `policy`, and `skills`
- starter case registry exports: `EvalCase`, `EvalCaseResult`, `GradeMode`,
  `GradeOutcome`, `grade_case(...)`, and `registered_cases(...)`
- goal trajectory exports such as `GoalTrajectoryBenchmark`,
  `GoalTrajectoryReport`, `GoalDriftSignalKind`, `run_benchmark(...)`, and
  `aggregate_reports(...)`
- certification helpers such as `FamilyCertificationSignal` and
  `apply_family_signals_to_certification_cells(...)`
- type/version contract: `openminion_eval.__version__` and packaged
  `openminion_eval/py.typed`
- scorer trace helpers: `build_case_traces(...)` and
  `write_case_traces_jsonl(...)`
- manual grading helpers: `build_manual_review_queue(...)`,
  `load_manual_adjudications(...)`, and `apply_manual_adjudications(...)`
- static family registry helpers: `list_builtin_families(...)` and
  `get_builtin_family(...)`

## Integration quarantine and promotion checklist

`tests/eval/integration/` contains source-only probes. They are not public API
and must not be imported from `src/openminion_eval` unless a future promotion
lane proves all of the following:

1. fixture shape is stable and package-owned,
2. host-owned runtime adapters are removed or replaced with public package
   contracts,
3. installed-wheel tests prove the import works outside the source tree,
4. public-release-boundary tests cover the promoted surface,
5. docs describe the new public import root.

## Trace and manual artifacts

Scorer trace artifacts and manual review/adjudication artifacts are local JSON
or JSONL files. They must use relative paths and must not include provider
secrets, environment dumps, host runtime paths, or OpenMinion runtime-owned
objects.

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
10. `openminion_eval.cases` CLI/report behavior,
11. reference docs for eval families, eval cases, standalone claims, and
    certification readiness,
12. parallel suite execution ordering and partial-rerun selection filters.
13. versioned dataset loader validation for JSON and JSONL inputs.
14. CLI help, suite-run artifact output, and baseline-diff exit policy.

## Non-goals

This policy does not promise:

1. the repo-local integration fixtures under `tests/eval/integration/`,
2. memory-eval internals or memory provider baselines as wheel-shipped API,
3. compatibility for undocumented import paths,
4. runtime-loaded configuration beyond the current documented no-op
   compatibility surface.
