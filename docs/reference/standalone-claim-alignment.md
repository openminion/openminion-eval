# Standalone Claim Alignment

Status: alpha
Scope: public package claims and current shipped surfaces

This note maps the public `openminion-eval` story to the package surfaces that
ship today. It keeps the standalone package description narrow, testable, and
useful for downstream consumers.

## Claim Inventory

| Public claim | Shipped package surface | Proof today | Alignment |
| --- | --- | --- | --- |
| `openminion-eval` is a standalone evaluation toolkit for agent quality checks. | `EvalRunner`, `EvalScorer`, `EvalSuite`, schemas, interfaces, scorer helpers. | `tests/eval/test_eval.py`, `tests/eval/test_interfaces_contract.py`, `scripts/check_release_package.py` | Keep. The generic eval primitives are package-owned and installable. |
| The package ships deterministic non-memory eval families. | Tools, freshness, routing, closure, policy, skills, goal-trajectory, and reporting helpers. | `tests/eval/families/`, `tests/eval/test_family_imports.py`, `docs/reference/eval-families.md` | Keep. These are explicit DTO/report builders over supplied observations. |
| The package includes a starter case runner. | `openminion_eval.cases`, top-level `EvalCase` exports, and `python -m openminion_eval.cases`. | `tests/eval/test_starter_eval_cases.py`, `docs/reference/eval-cases.md`, release smoke. | Keep, but describe it as a starter registry and CLI, not a complete live-agent harness. |
| The package can be released independently. | Wheel/sdist build, installed-wheel smoke, license/resource checks, public-boundary checks. | `scripts/check_release_package.py`, `RELEASING.md` | Keep. Release checks must stay package-local. |
| Memory-eval and provider-certification fixtures are part of the public package API. | Source-tree fixtures and tests exist, but memory harness modules are not wheel-shipped public imports. | `tests/eval/test_public_release_boundary.py`, release smoke import rejection. | Narrow. They are repo-local validation support, not public package API. |
| The package evaluates live model behavior end to end. | Structural scoring helpers and optional live-gated case mode exist. | `docs/reference/eval-cases.md` | Narrow. Hosts own provider execution; the package owns deterministic scoring/reporting surfaces. |

## Resulting Public Stance

The honest standalone story is:

1. a small installable evaluation library,
2. deterministic family scoring/reporting over explicit observations,
3. packaged skill-eval resources,
4. a starter case registry and Markdown report CLI,
5. release checks that prove the installed wheel exposes only the intended
   public surface.

It is not:

1. the full OpenMinion application runtime,
2. a hosted evaluation service,
3. a memory-provider benchmark package,
4. a live provider orchestration engine,
5. a freeform model-output judging system.
