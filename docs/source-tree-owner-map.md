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
goal-trajectory, and reporting helpers.

## Source-tree owner map

1. `runner.py`, `scorer.py`, `suite.py`, `schemas.py`, and `interfaces.py`
   own the generic eval primitives.
2. `cases/` owns the starter `EvalCase` registry and Markdown case report CLI.
3. `tools/`, `freshness/`, `routing/`, `closure/`, and `policy/` own
   deterministic family case and report helpers.
4. `skills/` owns packaged skill-quality and named-skill manifests plus report
   builders.
5. `goal_trajectory/` owns objective-drift fixtures, metrics, runner, and
   aggregate reports.
6. `reporting/` owns package-level certification signal helpers.
7. `config.py`, `constants.py`, `paths.py`, and `family_support.py` own shared
   package support used by the public surfaces above.

## Repo-local but not public API

1. `tests/eval/integration/` contains memory eval and trace-flywheel harnesses.
2. `tests/eval/grounding/` and `tests/eval/runners/` support source-tree
   validation workflows.
3. Memory and provider fixtures plus baselines are regression inputs, not
   wheel-shipped import surfaces.
4. Host planning docs stay outside the package-local public docs directory.
