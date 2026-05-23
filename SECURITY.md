# Security Policy

## Reporting a vulnerability

Please do not open a public issue with exploit details.

Instead:

1. contact the project maintainers privately through the security reporting
   channel used for OpenMinion, or
2. if that channel is unavailable, open a minimal private coordination thread
   without exploit details and request a secure handoff path.

## Scope

This package's security posture follows the same general rules as OpenMinion:

1. report vulnerabilities privately first,
2. do not publish proof-of-exploit details before maintainers have had time to
   assess and respond,
3. include affected version, reproduction steps, and impact summary when
   possible.

## Dependency note

`openminion-eval` still has repository-owned integration/report tooling such as
`tests/eval/integration/` (memory eval + trace flywheel). Security reports should
mention whether the issue affects:

1. the public standalone non-memory contract, or
2. integration/report tooling outside the current standalone public promise.
