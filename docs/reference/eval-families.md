# Eval Families

Status: alpha
Scope: public non-memory eval-family contracts

`openminion-eval` ships deterministic helpers for package-owned evaluation
families. These helpers are intended for downstream projects that want stable
case DTOs, observations, reports, and score summaries without importing the
OpenMinion application runtime.

## Public Roots

- `openminion_eval.tools`
- `openminion_eval.freshness`
- `openminion_eval.routing`
- `openminion_eval.closure`
- `openminion_eval.policy`
- `openminion_eval.skills`
- `openminion_eval.goal_trajectory`
- `openminion_eval.reporting`

The top-level `openminion_eval` package re-exports the common case, report,
and builder symbols for these families.

## Family Surface

| Family | What it evaluates | Public shape |
| --- | --- | --- |
| Tool selection | Whether the selected tool is necessary and appropriate. | `ToolSelectionCase`, `ToolSelectionObservation`, `ToolSelectionReport` |
| Tool result usage | Whether tool output is used and unsupported output is rejected. | `ToolResultUsageCase`, `ToolResultUsageObservation`, `ToolResultUsageReport` |
| Freshness | Whether stale or missing recency evidence is handled correctly. | `FreshnessCase`, `FreshnessObservation`, `FreshnessReport` |
| Routing | Whether routing observations match expected routing behavior. | `RoutingCase`, `RoutingObservation`, `RoutingReport` |
| Closure | Whether the response satisfies closure criteria. | `ClosureCase`, `ClosureObservation`, `ClosureReport` |
| Policy | Whether policy gates and denials are reflected structurally. | `PolicyCase`, `PolicyObservation`, `PolicyReport` |
| Skills | Whether skill selection and skill-quality evidence can be summarized. | `SkillQuality*`, `NLNamedSkill*` report helpers |
| Goal trajectory | Whether objective-drift and trajectory signals can be replayed. | `GoalTrajectoryBenchmark`, `GoalTrajectoryReport`, `run_benchmark(...)` |
| Certification reporting | Whether family signals can update provider certification cells. | `FamilyCertificationSignal`, `apply_family_signals_to_certification_cells(...)` |

## Data Boundary

The public family helpers consume explicit case and observation payloads. They
do not:

1. call model providers,
2. run the OpenMinion agent runtime,
3. read private host application state,
4. infer freeform intent from raw chat logs.

Host applications may generate observations however they choose, then pass
those observations into these package helpers for deterministic scoring and
reporting.

## Resource Boundary

The wheel packages the skill-quality and named-skill manifest resources used by
the public skills helpers. Repo-local memory fixtures, provider baselines, and
integration runners are source-tree validation support only; they are not
importable package API.

## Proof

The family surface is guarded by:

1. `tests/eval/families/`
2. `tests/eval/test_family_imports.py`
3. `tests/eval/test_family_certification_reporting.py`
4. `tests/eval/test_public_release_boundary.py`
5. `scripts/check_release_package.py`
