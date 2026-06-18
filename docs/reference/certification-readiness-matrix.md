# OpenMinion Eval Certification Readiness Matrix

Status: alpha
Scope: public package proof matrix

## Purpose

Single map of the current public `openminion-eval` surface, the standalone
package proof for each lane, and the host-integration proof where one exists.

## Scope

The matrix below lists each shipped eval-package lane, the exact package test
target that proves the standalone surface works, and the exact host-facing
proof when the lane has one.

## Non-goals

This matrix does not cover:

1. hosted evaluation services,
2. live provider orchestration,
3. private memory-provider benchmarks as wheel-shipped API,
4. the OpenMinion application runtime.

## Success Criteria

Every row points to a passing package-local test, release smoke, or documented
host-facing proof that exercises public package imports.

## Matrix

| Lane | Standalone package proof | Host-facing proof |
| --- | --- | --- |
| Generic eval primitives | `tests/eval/test_eval.py`, `tests/eval/test_interfaces_contract.py` | `n/a` |
| Public import boundary | `tests/eval/test_family_imports.py`, `tests/eval/test_public_release_boundary.py` | `openminion/scripts/validate_openminion_eval_layout.py` |
| Eval families | `tests/eval/families/`, `tests/eval/test_family_missing_observation.py` | `n/a` |
| Certification reporting | `tests/eval/test_family_certification_reporting.py`, `tests/eval/test_family_certification_sequence.py` | `n/a` |
| Goal trajectory | `tests/eval/test_goal_trajectory.py` | `n/a` |
| Skill resources and reports | `tests/eval/test_skill_quality_eval.py`, `tests/eval/test_nl_named_skill_eval.py` | `n/a` |
| Starter case CLI | `tests/eval/test_starter_eval_cases.py`, `python -m openminion_eval.cases` release smoke | `n/a` |
| Package release contract | `tests/eval/test_package_structure.py`, `tests/eval/test_release_check.py`, `scripts/check_release_package.py` | `n/a` |

## Public surface proofs

1. root imports remain stable for `openminion_eval` and the documented
   non-memory eval families,
2. package docs and examples match the published public contract,
3. built artifacts install cleanly without depending on the OpenMinion application
   tree,
4. packaged skill resources remain present in the built wheel,
5. repo-local memory/integration tooling stays outside the public wheel.

## Package-local validation anchors

1. `tests/eval/test_package_structure.py`
2. `tests/eval/test_public_release_boundary.py`
3. `tests/eval/test_family_imports.py`
4. `tests/eval/test_interfaces_contract.py`
5. `tests/eval/families/`
6. `scripts/check_release_package.py`

## Run-the-suite commands

```bash
cd openminion-eval
make check
python3.11 scripts/release_check.py
```

```bash
cd openminion
.venv/bin/python3.11 -m ruff check .
make lint
```

## Boundary reminder

The public package owns the generic eval runner/scorer/suite/interfaces/schemas
surface, deterministic non-memory eval-family helpers, packaged skill-eval
resources, and the starter case CLI. Repo-local integration tooling under
`tests/eval/` remains source-only validation support rather than wheel-shipped
API.
