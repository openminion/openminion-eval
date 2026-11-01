# OpenMinion Eval Engineering Patterns

Status: active
Last updated: 2026-11-01

Purpose: give public contributors one package-local summary of the engineering
patterns that shape `openminion-eval` changes.

## Core rule

Prefer explicit, typed, machine-checkable eval contracts over prose-heavy or
implicit behavior.

## Main package split

Use this source-tree ladder when deciding where code belongs:

1. `runner.py`, `suite.py`, `suite_selection.py`, and `suite_artifacts.py` own
   generic case execution, selection, manifests, baseline diffs, and trace
   artifacts.
2. `scorer.py`, `family_support.py`, `schemas.py`, and `interfaces.py` own
   typed scoring and family-level contracts.
3. `cases/`, `tools/`, `freshness/`, `routing/`, `closure/`, `policy/`,
   `skills/`, and `goal_trajectory/` own deterministic family fixtures,
   metrics, and reports.
4. `runtime_reliability/`, `memory_effectiveness/`, and
   `memory_context_scorecard/` own their structured benchmark contracts and
   packaged sample resources.
5. `reports.py` and `reporting/` own human-readable rendering and package-level
   certification signals; they consume structured results rather than becoming
   alternate scoring owners.
6. `subject_adapters.py` owns black-box command, HTTP, and replay subjects.
7. `tests/eval/integration/` owns repo-local host integration coverage and is
   not part of the standalone runtime contract.

## Shared-owner rules

1. Shared constants should live in package owners rather than being repeated
   inline.
2. Public roots should stay small and intentional; not every import path is a
   stable promise.
3. Repo-local integration helpers must not leak into the standalone package
   surface.
4. Keep built-in family registration static and reviewable; do not discover
   arbitrary host code or import sibling source trees at package runtime.

## Runtime-boundary rules

1. Keep outputs deterministic and typed.
2. Prefer structured eval facts over prose summaries when callers need
   machine-readable results.
3. Do not import `openminion.*` into `src/openminion_eval/`.
4. Keep the public wheel standalone; host-framework integration belongs in
   tests or sibling repos.

## Evaluation truth and evidence

1. Scorers consume explicit subject facts and return typed metrics, reasons,
   and trace rows. Do not infer success from prose summaries.
2. Keep scoring deterministic for identical cases, subject outputs, and
   configuration. Record dataset versions and stable hashes when results need
   comparison over time.
3. Preserve sample provenance. Packaged starter cases and synthetic benchmark
   samples demonstrate the scorer contract; they are not live-provider or
   production-quality claims.
4. Separate execution failure, unavailable evidence, invalid subject output,
   and a valid low score. Do not collapse those outcomes into one numeric
   fallback.
5. Baseline diffs compare compatible suite identities and scorer contracts;
   reject mismatched artifacts instead of producing a misleading delta.

## Subject and artifact boundaries

1. Subject adapters execute only the explicit command, HTTP, or replay contract
   supplied by the caller. They do not gain OpenMinion internals or credentials
   through implicit workspace discovery.
2. Keep manual review, boundary artifacts, scorer traces, and suite manifests
   distinct so human adjudication cannot silently rewrite raw subject evidence.
3. Store generated reports and integration artifacts outside the source tree
   and sanitize public outputs.
4. An installed-wheel smoke proves the packaged standalone surface. Repo-local
   integration, live-provider, and host-runtime claims require their own named
   probes and evidence.

## Cleanup and refactor rules

1. Preserve public-boundary clarity over broad rewrites.
2. Keep eval-family changes paired with matching tests.
3. Keep public docs portable and package-local.

## Use with

Read this doc together with:

1. [`code-quality-enforcement.md`](code-quality-enforcement.md)
2. [`getting-started.md`](getting-started.md)
3. [`testing-and-validation.md`](testing-and-validation.md)
4. [`source-tree-owner-map.md`](source-tree-owner-map.md)
