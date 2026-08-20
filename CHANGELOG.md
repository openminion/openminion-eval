# OpenMinion Eval Changelog

Status: active
Last updated: 2026-06-20

This file tracks package-facing release notes for `openminion-eval`.

## Unreleased

### Added

- Added a provider-free runtime-reliability family, complete built-in family
  discovery, benchmark-manifest scoring, portable report bundles, and schemas
  for the public dataset, memory, manual-review, and boundary artifacts.
- Added package-local public contributor references for testing, engineering
  patterns, agent bootstrap, and code-quality enforcement.

### Changed

- Separated executor and scorer failures in suite evidence, tightened dataset
  and suite-artifact validation, and completed manual-result round trips.
- Polished the public package docs surface so standalone consumers can follow
  package-local docs without monorepo-only context.

### Notes

- The project remains in alpha. Until the next tagged package release, changes
  may land ahead of a published semantic-versioned changelog entry.
