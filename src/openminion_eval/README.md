# OpenMinion Eval Package Layout

`openminion_eval` is the standalone evaluation package for deterministic agent
quality checks.

## Public Contract

The public alpha surface is documented in:

1. `README.md`
2. `API_COMPATIBILITY.md`
3. `docs/`

The preferred public entrypoint is `openminion_eval`, with stable import roots
for cases, tools, freshness, routing, closure, policy, skills,
memory-effectiveness trace scoring, goal-trajectory, reporting helpers,
dataset/artifact helpers, family registry, manual review artifacts, and
boundary artifact validators.

## Source-Tree Owner Map

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
   deterministic family case/report helpers.
9. `skills/` owns packaged skill-quality and named-skill manifests plus
   report builders.
10. `memory_effectiveness/` owns provider-free SophiaGraph/OpenMinion memory
   trace DTOs, packaged deterministic cases, scorecards, and paired-run
   comparison helpers.
11. `goal_trajectory/` owns objective-drift fixtures, metrics, runner, and
   aggregate reports.
12. `reporting/` owns package-level certification signal helpers.
13. `cli.py` and `__main__.py` own the public package command line.
14. `py.typed` marks the installed package as PEP 561 typed.
15. `config.py`, `constants.py`, `paths.py`, and `family_support.py` own shared
    package support used by the public surfaces above.
16. `integration_quarantine.py` owns installed support metadata for
    source-tree integration probes; it does not make those probes stable
    package APIs.

## Repo-Local But Not Public API

1. `tests/eval/integration/` contains memory eval and trace-flywheel harnesses.
2. `tests/eval/grounding/` and `tests/eval/runners/` support source-tree
   validation workflows.
3. Memory and provider fixtures plus baselines are regression inputs, not
   wheel-shipped import surfaces.
4. Host planning docs stay outside the package-local public docs directory.
