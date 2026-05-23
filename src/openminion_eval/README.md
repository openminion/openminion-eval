# Eval Core

`openminion_eval` is the standalone Python package for the canonical OpenMinion
eval surface.

## Included

Top-level generic surfaces:

- `runner.py`, `scorer.py`, `suite.py`
- `schemas.py`, `interfaces.py`
- `config.py`, `constants.py`
- `family_support.py`, `reporting/`

Canonical non-memory families:

- `tools/`
- `freshness/`
- `routing/`
- `closure/`
- `policy/`
- `skills/`

Additional repo-local eval surfaces in this repository:

- `tests/eval/integration/` (memory eval + trace flywheel)
- memory fixtures and baselines
- memory quality and provider certification reports
- grounding eval
- eval runners and package-owned eval tests

## Monorepo posture

- external standalone code imports `openminion_eval`
- `openminion/src/openminion/eval/` is retired
- `openminion/tests/eval/` is retired
- `openminion` consumes eval only through the external package

## Public release contract

Public standalone promise today:

- generic eval primitives
- shared package-owned support needed by those primitives
- canonical non-memory families
- `config.py` as a documented no-op compatibility surface (the package does
  not currently load runtime config)

Repo-local integration/report tooling outside the published package:

- `tests/eval/integration/` (memory eval + trace flywheel)
- companion reports
- grounding eval
- eval baselines and runners
