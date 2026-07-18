# OpenMinion Eval Source Tree Owner Map

Status: alpha

Purpose: explain the `openminion_eval` source-tree owners without treating deep
imports as blanket public promises.

## Public contract

The public alpha surface is documented in:

1. `README.md`
2. `API_COMPATIBILITY.md`
3. `docs/`

The preferred public entrypoint is `openminion_eval`, with stable import roots
for cases, tools, freshness, routing, closure, policy, skills,
goal-trajectory, reporting helpers, dataset/artifact helpers, family registry,
manual review artifacts, boundary artifact validators, memory-effectiveness
helpers, and memory/context scorecards.

## Source-tree owner map

1. `runner.py`, `scorer.py`, `suite.py`, `schemas.py`, and `interfaces.py`
   own the generic eval primitives, scorer contracts, suite summaries, and
   trace-row schemas.
2. `datasets.py` owns versioned JSON/JSONL dataset loading and stable dataset
   hashing.
3. `suite_artifacts.py` owns suite-result manifests, baseline diffs, and
   scorer trace JSONL output.
4. `manual.py` owns local manual-review queues and adjudication imports.
5. `boundary_artifacts.py` owns provider-free red-team/security and
   synthetic-golden artifact validation.
6. `family_registry.py` owns static metadata for built-in non-memory eval
   families.
7. `cases/` owns the starter `EvalCase` registry and Markdown case report CLI.
8. `tools/`, `freshness/`, `routing/`, `closure/`, and `policy/` own
   deterministic family case and report helpers.
9. `skills/` owns packaged skill-quality and named-skill manifests plus report
   builders.
10. `goal_trajectory/` owns objective-drift fixtures, metrics, runner, and
   aggregate reports.
11. `memory_effectiveness/` owns structured memory trace scoring, packaged
    benchmark samples, and memory-effectiveness scorecards.
12. `memory_context_scorecard/` owns deterministic memory/context scorecard
    fixtures, typed metric validation, report IO, and the matching CLI
    subcommand owner.
13. `reporting/` owns package-level certification signal helpers.
14. `cli.py` and `__main__.py` own the public package command line dispatcher.
15. `py.typed` marks the installed package as PEP 561 typed.
16. `config.py`, `constants.py`, `paths.py`, and `family_support.py` own shared
    package support used by the public surfaces above.
17. `integration_quarantine.py` owns installed support metadata for
    source-tree integration probes; it does not make those probes stable
    package APIs.

## Repo-local but not public API

1. `tests/eval/integration/` contains memory eval and trace-flywheel harnesses.
2. `tests/eval/grounding/` and `tests/eval/runners/` support source-tree
   validation workflows.
3. Memory and provider fixtures plus baselines are regression inputs, not
   wheel-shipped import surfaces.
4. Host planning docs stay outside the package-local public docs directory.
5. `scripts/validate_quality_patterns.py` and `scripts/baselines/` own the
   package-local structural quality ratchets used by `make validate-patterns`
   and `make check`.
