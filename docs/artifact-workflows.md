# Artifact Workflows

Status: alpha

`openminion-eval` artifacts are designed for a simple review loop:

1. run a deterministic scorer or report command,
2. validate the JSON artifact,
3. render a human-readable report,
4. compare against a previous artifact when a baseline exists,
5. upload only sanitized artifacts from CI.

The package owns artifact shape, validation, rendering, and diffing. Hosts own
provider execution, credential handling, raw transcripts, and any live
OpenMinion runtime setup.

## Recommended CI Loop

```bash
openminion-eval run dataset.json --out artifacts/current-suite.json
openminion-eval artifact validate artifacts/current-suite.json
openminion-eval report suite artifacts/current-suite.json --out artifacts/current-suite.md
```

When a previous result exists:

```bash
openminion-eval diff artifacts/previous-suite.json artifacts/current-suite.json --out artifacts/suite-diff.json
openminion-eval artifact validate artifacts/suite-diff.json
openminion-eval report suite-diff artifacts/suite-diff.json --out artifacts/suite-diff.md
```

For memory-effectiveness traces:

```bash
openminion-eval memory-effectiveness score examples/memory-effectiveness-trace.json --cases examples/memory-effectiveness-cases.json --out artifacts/memory-scorecard.json
openminion-eval artifact validate artifacts/memory-scorecard.json
openminion-eval report memory-scorecard artifacts/memory-scorecard.json --out artifacts/memory-scorecard.md
```

For delegated multi-agent memory traces:

```bash
openminion-eval memory-effectiveness delegated-score examples/delegated-memory-trace.json --out artifacts/delegated-memory-scorecard.json
openminion-eval artifact validate artifacts/delegated-memory-scorecard.json
openminion-eval report delegated-memory artifacts/delegated-memory-scorecard.json --out artifacts/delegated-memory-scorecard.md
```

## Upload Policy

Upload JSON artifacts, Markdown reports, and bundle indexes that contain typed
eval facts only. Do not upload provider credentials, environment dumps, raw
private transcripts, local database paths, or unredacted memory payloads.

Use relative paths in logs and docs. Keep raw provider evidence in a separate
host-owned location, then cite sanitized trace ids or artifact ids from
`openminion-eval` outputs.

## Release Smoke Expectations

`make release-check` builds the wheel and sdist, installs the wheel in a fresh
environment, and exercises the public artifact commands. When artifact features
change, update this workflow document, `artifact-schemas.md`, and the release
smoke together so the installed package proves the same surface documented for
users.
