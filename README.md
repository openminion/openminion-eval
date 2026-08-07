<p align="center">
  <img src="https://www.openminion.com/brand/openminion-logo.png" alt="OpenMinion Eval logo" width="128" />
</p>

<h1 align="center">OpenMinion Eval</h1>

<p align="center">
  <strong>Deterministic evaluation toolkit for agent behavior, tools, routing, policy, memory, and closure.</strong>
</p>

<p align="center">
  <a href="https://github.com/openminion/openminion-eval">GitHub</a>
  · <a href="docs/README.md">Docs</a>
  · <a href="https://www.openminion.com">Website</a>
  · <a href="https://x.com/OpenMinion">X</a>
</p>

<p align="center">
  <img alt="Package version" src="https://img.shields.io/badge/package-0.0.1-3775A9">
  <img alt="Python" src="https://img.shields.io/badge/python-3.11%2B-3775A9">
  <a href="LICENSE"><img alt="License" src="https://img.shields.io/badge/license-MIT-blue"></a>
  <img alt="Status" src="https://img.shields.io/badge/status-alpha-6B7280">
</p>

`openminion-eval` `v0.0.1` is the source-only alpha of a standalone evaluation
package. It provides repeatable datasets, runners, scorers, artifacts, reports,
and evaluation families without importing the OpenMinion application runtime.

## Read This First

1. Read [At a Glance](#at-a-glance) to distinguish the standalone package
   contract from repo-local integration probes.
2. Follow [Install](#install) and [Quick Start](#quick-start) for one
   deterministic exact-match suite.
3. Read [Evaluation Families](#evaluation-families) to choose a package-owned
   scoring surface.
4. Use the [package docs](docs/README.md) for datasets, artifacts, CI,
   certification, and memory scorecards.
5. Read [Development](#development) before changing the package.

## Trust and Brand Safety

- Official GitHub: <https://github.com/openminion/openminion-eval>
- Official website: <https://www.openminion.com>
- Official X account: <https://x.com/OpenMinion>

OpenMinion Eval has no official token, coin, NFT, airdrop, staking program,
treasury product, or investment offering. Any claim otherwise is unauthorized
and should be treated as a scam.

## At a Glance

| | |
| --- | --- |
| Package | `openminion-eval` |
| Import root | `openminion_eval` |
| Current line | `v0.0.1` source-only alpha |
| Python | 3.11+ |
| Best fit | Repeatable package-level evaluation without the full agent runtime |
| Main artifacts | Versioned datasets, suite results, case traces, reports, and baseline diffs |
| Not the claim | A live agent runtime, model judge, memory engine, or hosted evaluation service |

## Common Commands

```bash
openminion-eval dataset validate eval-dataset.jsonl
openminion-eval run eval-dataset.jsonl --out suite-result.json
openminion-eval report suite suite-result.json --out suite-report.md
openminion-eval diff baseline.json suite-result.json
```

## Install

The package is currently installed from the official repository:

```bash
python3.11 -m pip install \
  "openminion-eval @ git+https://github.com/openminion/openminion-eval.git"
```

For a source checkout:

```bash
python3.11 -m pip install -e ".[dev]"
```

## Quick Start

Run a minimal deterministic suite:

```python
from openminion_eval import EvalRunner, EvalSuite
from openminion_eval.schemas import EvalTranscript

transcript = EvalTranscript(
    name="hello-world",
    turns=[{"user": "ping", "expected": "pong"}],
    tags=["quickstart"],
)
suite = EvalSuite(
    runner=EvalRunner(agent_executor=lambda _user_input: "pong"),
    threshold=1.0,
)
result = suite.run([transcript], scorer_name="exact_match")

print(result.total_transcripts)
print(result.failed_transcripts)
```

Run the complete package example:

```bash
python3.11 examples/basic_usage.py
```

Create a starter dataset and render a report:

```bash
openminion-eval dataset init --family routing --out routing-starter.json
openminion-eval run routing-starter.json --out routing-result.json
openminion-eval report suite routing-result.json --out routing-report.md
```

## What OpenMinion Eval Provides

- versioned JSON and JSONL dataset contracts with stable hashing
- runner, scorer, suite, subject, schema, and configuration interfaces
- CLI, HTTP, and replay subject adapters
- deterministic run manifests, suite results, case traces, and baseline diffs
- Markdown and HTML report rendering
- manual-review queues and adjudication artifacts
- red-team and synthetic-golden boundary artifact validation
- built-in agent-behavior and memory-oriented evaluation families
- partial reruns and opt-in parallel suite execution
- integration quarantine metadata for distinguishing proof tiers

## What OpenMinion Eval Does Not Provide

- OpenMinion runtime execution or SophiaGraph storage
- provider calls, prompt generation, or model-judge execution
- automatic synthetic dataset generation
- a hosted evaluation service or dashboard
- a guarantee that repo-local integration probes ship in the wheel
- semantic interpretation of free-form assistant prose for memory scoring

The package scores explicit inputs and structured traces. Host applications own
provider execution, data generation, live runtime setup, and model judging.

## Evaluation Families

| Family | What it checks |
| --- | --- |
| Tools | Tool selection and use of tool results |
| Freshness | Whether an answer uses current supplied evidence |
| Routing | Whether work reaches the intended route or owner |
| Closure | Whether the run reaches a valid terminal outcome |
| Policy | Whether explicit policy expectations are satisfied |
| Skills | Skill selection and rubric-based skill quality |
| Goal trajectory | Drift and progress across multi-step work |
| Memory effectiveness | Saved, retrieved, used, and cited memory traces |
| Memory context | Ablation, usefulness, influence, and governance gates |
| Delegated memory | Shared-recall utility plus isolation, revocation, provenance, and re-sharing gates |

See [`docs/eval-families.md`](docs/eval-families.md),
[`docs/memory-effectiveness.md`](docs/memory-effectiveness.md), and
[`docs/memory-context-scorecard.md`](docs/memory-context-scorecard.md) for
contracts and artifact shapes.

## Public Package vs Repo-local Proof

The installable package owns deterministic evaluation contracts and portable
artifacts. `tests/eval/integration/` and other source-tree probes may depend on
host runtime state and are not automatically public wheel APIs.

Use the package CLI for a small standalone proof. Use explicitly labeled
integration tests when validating OpenMinion, SophiaGraph, providers, or other
live host behavior. Do not present one proof tier as evidence for another.

## Development

```bash
make dev-install
make hooks-install
make check
```

Use `make test-all` only when you intentionally want the broader repo-local
integration suite. Use `make release-check` before publishing or changing the
documented public surface.

## Docs and Release

- [`docs/README.md`](docs/README.md): package documentation map
- [`docs/getting-started.md`](docs/getting-started.md): contributor bootstrap
- [`docs/eval-cases.md`](docs/eval-cases.md): starter case registry
- [`docs/eval-families.md`](docs/eval-families.md): built-in family contracts
- [`docs/artifacts-and-manual-grading.md`](docs/artifacts-and-manual-grading.md):
  traces and human review
- [`docs/ci-recipes.md`](docs/ci-recipes.md): CI integration examples
- [`docs/certification-readiness-matrix.md`](docs/certification-readiness-matrix.md):
  package and integration proof
- [`docs/source-tree-owner-map.md`](docs/source-tree-owner-map.md): code owners
  and package layout
- [`docs/standalone-claim-alignment.md`](docs/standalone-claim-alignment.md):
  standalone-package claim boundaries and validation
- [`API_COMPATIBILITY.md`](API_COMPATIBILITY.md): supported public imports
- [`RELEASING.md`](RELEASING.md): release and publish flow
- [`scripts/release_check.py`](scripts/release_check.py): package release smoke
  validation

## License and Brand-use Boundary

- Source code license: MIT
- Brand/trademark grant: none

The license grants rights to use, modify, and redistribute the code. It does
not grant rights to present a fork, clone, token, website, or social account as
the official OpenMinion Eval or OpenMinion project or imply affiliation or
endorsement.
