<p align="center">
  <img src="https://www.openminion.com/brand/openminion-logo.png" alt="OpenMinion Eval logo" width="128" />
</p>

<h1 align="center">OpenMinion Eval</h1>

<p align="center">
  <strong>Standalone evaluation toolkit for agent quality, routing, tools, policy, and closure.</strong>
</p>

<p align="center">
  <a href="https://github.com/openminion/openminion-eval">GitHub</a>
  · <a href="#install">Install</a>
  · <a href="#what-ships-in-the-public-package">What Ships</a>
  · <a href="https://www.openminion.com">Website</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <img alt="Package version" src="https://img.shields.io/badge/package-0.0.1-3775A9">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3775A9">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-6B7280">
</p>

`openminion-eval` is the `v0.0.1` public preview of the standalone
non-memory evaluation package for OpenMinion.

Use it when you want repeatable agent-quality checks for routing, tools,
freshness, closure, policy, and skills without pulling in the full runtime.

## Trust and Brand Safety

- Official GitHub: `https://github.com/openminion/openminion-eval`
- Official website: `https://www.openminion.com`
- Official X account: `https://x.com/OpenMinion`

`openminion-eval` has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

## At a glance

- Current public line: `v0.0.1` preview
- Distribution name: `openminion-eval`
- Python import: `openminion_eval`
- Best fit when: you want standalone, repeatable, non-memory eval checks
  without depending on the full OpenMinion runtime
- Not the claim: memory eval harnesses and broader host-runtime validation
  flows still live in the repo, but they are not part of the published package

## What ships in the public package

The public package currently ships:

- generic eval runner, scorer, suite, interface, schema, config, and constant
  surfaces
- typed `EvalSubjectInterface` and `EvalRunContext` contracts for subjects
  under test
- suite run manifests, stable input hashing, JSON suite-result artifacts, and
  baseline diffs
- versioned JSON and JSONL dataset loaders with stable dataset hashing
- package CLI entrypoints for suite runs and baseline diffs
- opt-in parallel suite execution and partial rerun selection by previous
  failures, transcript name, and transcript tags
- the starter `EvalCase` registry under `openminion_eval.cases`
- canonical non-memory eval families for tools, freshness, routing, closure,
  policy, and skills
- shared support needed by those surfaces

## What stays repo-local

The repository still contains broader validation tooling that is not part of
the installable standalone wheel:

- `tests/eval/integration/` for memory eval and trace-flywheel work
- memory fixtures, baselines, and companion reports
- grounding eval and repo-local eval runners
- other validation assets that depend on host-runtime state rather than the
  standalone package alone

Why this split exists: the published wheel is meant to stay small, stable, and
safe to install into downstream projects. Memory harnesses and source-tree
validation flows remain available from source in this repository, but they are
not exposed as part of the installable `openminion_eval` package.

The `openminion_eval.config` module is intentionally minimal today. It remains
as a documented no-op compatibility surface; the public package does not
currently require runtime-loaded configuration.

## Install

Install from GitHub:

```bash
python3.11 -m pip install "openminion-eval @ git+https://github.com/openminion/openminion-eval.git"
```

Run a minimal public smoke:

```bash
python - <<'PY'
import openminion_eval
from openminion_eval import EVAL_INTERFACE_VERSION, EvalRunContext, EvalRunner
from openminion_eval import EvalCase, build_run_manifest, load_eval_dataset_jsonl
from openminion_eval import registered_cases
from openminion_eval.schemas import EvalTranscript
from openminion_eval.tools import ToolSelectionCase
from openminion_eval.freshness import FreshnessCase
from openminion_eval.routing import RoutingCase
from openminion_eval.closure import ClosureCase
from openminion_eval.policy import PolicyCase
from openminion_eval.skills import load_skill_quality_manifest

print(EVAL_INTERFACE_VERSION)
print(EvalRunner.__name__)
print(EvalRunContext.__name__)
print(EvalCase.__name__, len(registered_cases()))
print(
    build_run_manifest(
        [EvalTranscript(name="smoke", turns=[])],
        scorer_name="exact_match",
        threshold=0.8,
    ).scorer_name
)
print(
    ToolSelectionCase.__name__,
    FreshnessCase.__name__,
    RoutingCase.__name__,
    ClosureCase.__name__,
    PolicyCase.__name__,
)
print(load_skill_quality_manifest().__class__.__name__)
print(load_eval_dataset_jsonl.__name__)
PY
```

Package-local example:

```bash
PYTHONPATH=src python3.11 examples/basic_usage.py
```

Starter case report:

```bash
python -m openminion_eval.cases --category coding
```

Generic suite run:

```bash
openminion-eval run eval-dataset.jsonl --out suite-result.json
python -m openminion_eval diff baseline.json suite-result.json
```

Use the CLI when you want a small package-only proof path. Use source-tree
integration tests when you need host-runtime or memory-eval behavior.

Exit-code policy:

- `openminion-eval run` exits `0` when every transcript passes and `1` when
  any transcript fails.
- `openminion-eval diff` exits `1` for `new_fail`, `regressed`, or
  `missing_transcript` categories, and `0` otherwise.

Versioned dataset input:

```json
{
  "dataset_version": "1",
  "name": "smoke",
  "cases": [
    {
      "id": "hello",
      "name": "hello",
      "turns": [{"user": "hello", "expected": "hi"}],
      "tags": ["smoke"]
    }
  ]
}
```

JSONL uses the same case object per line and preserves file order.

Partial rerun selection:

```python
from openminion_eval import EvalSuite, select_transcripts

selected = select_transcripts(
    transcripts,
    previous_result=previous_result,
    failed_only=True,
    include_tags=["routing"],
)
result = EvalSuite(subject=subject).run(selected, max_workers=4)
```

Boundary check:

```bash
python - <<'PY'
import importlib

try:
    importlib.import_module("openminion_eval.memory_eval")
except ModuleNotFoundError as exc:
    print(exc.name)
else:
    raise SystemExit("openminion_eval.memory_eval should not ship in the public wheel")
PY
```

## Docs and release

- `docs/README.md` summarizes the package-local docs contract.
- `docs/eval-families.md` records the public non-memory eval-family
  contracts.
- `docs/certification-readiness-matrix.md` records standalone and
  host-integration proof coverage for the public package surface.
- `docs/eval-cases.md` records the starter `EvalCase` registry,
  grade modes, CLI, and extension rules.
- `docs/ci-recipes.md` gives pytest-native CI examples and artifact upload
  guidance.
- `docs/artifacts-and-manual-grading.md` documents scorer traces, manual
  grading JSON, and integration quarantine.
- `docs/standalone-claim-alignment.md` maps public claims to shipped
  package surfaces and proof.
- `API_COMPATIBILITY.md` records the supported public import roots and
  top-level export policy.
- `RELEASING.md` records the package-local release and PyPI publish flow.
- `docs/source-tree-owner-map.md` explains the module layout and
  public boundary.
- `scripts/release_check.py` is the canonical release smoke entrypoint.

## Surface classification

- `public_library_api`: top-level primitives, compatibility helpers,
  starter `EvalCase` registry, `openminion_eval.cases` CLI, canonical
  non-memory eval families, and package-owned support.
- `repo_local_integration_tooling`: memory eval, trace-flywheel work,
  provider certification, fixtures, baselines, and integration tests.
- `repo_local_tooling`: `conftest.py`, repo-local runners, grounding helpers,
  and dev/test helpers that rely on host runtime artifacts.

## License and brand-use boundary

- Source code license: `MIT`
- Brand/trademark grant: `none`

The software license grants rights to use, modify, and redistribute the code.
It does **not** grant rights to use the OpenMinion or OpenMinion Eval names,
logos, branding, website identity, or social identity except for truthful
attribution. Forks, clones, and derivative distributions must not present
themselves as the official OpenMinion Eval package or imply affiliation,
endorsement, or maintenance by OpenMinion contributors unless that is actually
true.
