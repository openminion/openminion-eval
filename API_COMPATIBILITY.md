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
- `openminion_eval.memory_effectiveness`
- `openminion_eval.memory_context_scorecard`
- `openminion_eval.goal_trajectory`
- `openminion_eval.reporting`
- `openminion_eval.suite_artifacts`
- `openminion_eval.datasets`
- `openminion_eval.reports`
- `openminion_eval.subject_adapters`
- `openminion_eval.boundary_artifacts`
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
- `openminion_eval.EvalScorerInfo`
- `openminion_eval.EvalScorerSpec`
- `openminion_eval.EvalSubjectInterface`
- `openminion_eval.CliSubject`
- `openminion_eval.HttpSubject`
- `openminion_eval.ReplaySubject`
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
- dataset authoring helpers: `build_eval_dataset_template(...)` and
  `write_eval_dataset_template(...)`
- subject adapter helpers: `load_replay_subject(...)` and
  `parse_http_headers(...)`
- human-readable report helpers:
  `render_suite_result_markdown(...)`, `render_suite_result_html(...)`,
  `render_baseline_diff_markdown(...)`, and `render_baseline_diff_html(...)`
- boundary artifact helpers:
  `load_red_team_security_artifact(...)`,
  `write_red_team_security_artifact(...)`,
  `load_synthetic_golden_artifact(...)`, and
  `write_synthetic_golden_artifact(...)`
- boundary artifact schemas: `RedTeamSecurityArtifact`,
  `RedTeamSecurityFixture`, `RedTeamSecurityResult`,
  `SyntheticGoldenArtifact`, `SyntheticGolden`, and
  `SyntheticGoldenProvenance`
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
- memory-effectiveness exports such as `MemoryEffectivenessCase`,
  `MemoryExpectation`, `MemoryEffectivenessTrace`, `MemoryTraceClaim`,
  `MemoryTraceToolCall`, `score_memory_case(...)`,
  `build_memory_scorecard(...)`, `compare_memory_scorecards(...)`,
  `load_memory_effectiveness_cases(...)`,
  `default_memory_effectiveness_cases_path(...)`, and
  `write_memory_scorecard(...)`
- benchmark adapter exports for memory-effectiveness samples:
  `BENCHMARK_ADAPTER_VERSION`, `MemoryBenchmarkSource`,
  `default_memory_benchmark_manifest_path(...)`,
  `load_memory_benchmark_cases(...)`,
  `load_packaged_memory_benchmark_sample(...)`, and
  `hash_benchmark_manifest_cases(...)`
- memory/context scorecard exports such as
  `MEMORY_CONTEXT_SCORECARD_VERSION`, `MemoryContextScorecardV1`,
  `ScorecardCaseFixture`, `ScorecardMetricFixture`,
  `load_memory_context_scorecard_fixtures(...)`,
  `default_memory_context_scorecard_cases_path(...)`,
  `build_memory_context_scorecard(...)`,
  `write_memory_context_scorecard(...)`, and
  `load_memory_context_scorecard(...)`
- certification helpers such as `FamilyCertificationSignal` and
  `apply_family_signals_to_certification_cells(...)`
- type/version contract: `openminion_eval.__version__` and packaged
  `openminion_eval/py.typed`
- scorer trace helpers: `build_case_traces(...)` and
  `write_case_traces_jsonl(...)`
- threshold-aware scorer metadata: `EvalScorer.score(...)` and
  `EvalScorer.score_results(...)` may record `scorer_reason` and
  `scorer_threshold` for trace consumers.
- manual grading helpers: `build_manual_review_queue(...)`,
  `load_manual_adjudications(...)`, and `apply_manual_adjudications(...)`
- static family registry helpers: `list_builtin_families(...)` and
  `get_builtin_family(...)`
- integration quarantine metadata helpers:
  `build_integration_quarantine_map(...)`, `integration_probe_tiers(...)`, and
  `IntegrationProbeDisposition`

## Integration quarantine and promotion checklist

`tests/eval/integration/` contains source-only probes. The installed
quarantine helper may describe them, but the probes themselves are not stable
public API and must not be promoted into package workflows unless a future lane
proves all of the following:

1. fixture shape is stable and package-owned,
2. host-owned runtime adapters are removed or replaced with public package
   contracts,
3. installed-wheel tests prove the import works outside the source tree,
4. public-release-boundary tests cover the promoted surface,
5. docs describe the new public workflow or import root.

## Trace and manual artifacts

Scorer trace artifacts and manual review/adjudication artifacts are local JSON
or JSONL files. They must use relative paths and must not include provider
secrets, environment dumps, host runtime paths, or OpenMinion runtime-owned
objects.

Red-team/security and synthetic-golden boundary artifacts are also local JSON
files. The package validates artifact shape and provenance, but it does not
generate prompts, call providers, create synthetic datasets, or run model
judges. Those workflows remain host-owned.

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
15. boundary artifact validation, provenance failures, and no-provider-core
    checks.
16. memory/context scorecard fixture loading, typed metric validation,
    installed-wheel resource inclusion, and CLI exit policy.
17. black-box subject adapters for CLI, HTTP, and JSONL replay targets.
18. dataset validate/hash/init CLI behavior.
19. scorer registry listing and human-readable suite/diff reports.
20. integration quarantine tiers and requirement metadata.

## Non-goals

This policy does not promise:

1. the repo-local integration fixtures under `tests/eval/integration/`,
2. source-tree memory-harness internals or memory provider baselines as
   wheel-shipped API,
3. compatibility for undocumented import paths,
4. runtime-loaded configuration beyond the current documented no-op
   compatibility surface.
