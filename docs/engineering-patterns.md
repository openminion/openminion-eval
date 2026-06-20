# OpenMinion Eval Engineering Patterns

Status: active
Last updated: 2026-06-20

Purpose: give public contributors one package-local summary of the engineering
patterns that shape `openminion-eval` changes.

## Core rule

Prefer explicit, typed, machine-checkable eval contracts over prose-heavy or
implicit behavior.

## Main package split

Use this source-tree ladder when deciding where code belongs:

1. `runner.py`, `suite.py`, and `reporting/` own case execution and packaged
   output shapes.
2. `scorer.py`, `family_support.py`, and `schemas.py` own typed scoring and
   family-level data contracts.
3. `skills/` owns packaged eval resources and catalogs that ship with the
   wheel.
4. `tests/eval/integration/` owns repo-local host integration coverage and is
   not part of the standalone runtime contract.

## Shared-owner rules

1. Shared constants should live in package owners rather than being repeated
   inline.
2. Public roots should stay small and intentional; not every import path is a
   stable promise.
3. Repo-local integration helpers must not leak into the standalone package
   surface.

## Runtime-boundary rules

1. Keep outputs deterministic and typed.
2. Prefer structured eval facts over prose summaries when callers need
   machine-readable results.
3. Do not import `openminion.*` into `src/openminion_eval/`.
4. Keep the public wheel standalone; host-framework integration belongs in
   tests or sibling repos.

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
