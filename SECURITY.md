# Security Policy

Thank you for taking the time to look at Geshtu's security
posture. This document describes how to report vulnerabilities, what
to expect from us in return, and which versions we maintain.

## Supported versions

Geshtu is pre-1.0. We support the **latest minor release** on the
`main` branch. Older releases do not receive security backports.

| Version  | Supported          |
| -------- | ------------------ |
| `main`   | yes                |
| `0.x.y`  | latest minor only  |
| `< 0.1`  | no                 |

When 1.0 ships, this table will be updated to a multi-release support
matrix.

## Reporting a vulnerability

Please **do not** open a public GitHub issue for security reports.

Email: **security@geshtu.io**

Optionally encrypt with our PGP key (published at
`geshtu.io/.well-known/pgp-key.asc` once available).

Useful information to include:

- A description of the issue and the impact you believe it has.
- Steps to reproduce, or a proof-of-concept.
- The Geshtu version, deployment topology, and any relevant
  configuration.
- Whether the issue is already public anywhere.

Reports in any language are welcome; we respond in English.

## Our response commitments

- **Acknowledgment within 24 hours** of receiving the report.
- **A fix or documented workaround within 7 days** for the reported
  issue, or a written explanation of why more time is needed.
- **No public disclosure for 30 days** unless we mutually agree to
  shorten that window.
- A public security advisory via the GitHub Security tab, with a CVE
  assigned where applicable.

If we do not respond within 24 hours, please follow up — email can be
unreliable.

## Coordinated disclosure

We follow standard coordinated disclosure:

1. You report privately.
2. We acknowledge, investigate, and prepare a fix.
3. We agree on a disclosure date with you.
4. We release the fix and publish an advisory crediting you (unless
   you prefer to remain anonymous).

If a vulnerability is being actively exploited in the wild, we may
shorten the disclosure window in agreement with the reporter.

## Hall of fame

Researchers who report serious vulnerabilities are credited in
`SECURITY_THANKS.md` (with their consent). Once the project crosses
1K stars we may add a small bug bounty funded via Open Collective —
this will be announced separately.

## Out of scope

The following are **not** considered vulnerabilities for the purposes
of this policy:

- Issues caused by user-modified deployments that diverge from the
  documented `docker-compose.yml` topology.
- Issues that require an attacker to already hold a valid admin token
  for the team.
- Denial-of-service via resource exhaustion on a single-team,
  self-hosted box. Geshtu is not designed to withstand that
  threat model — operators are expected to control who can reach the
  API and MCP endpoints.
- Best-practice findings without a concrete exploit path (for example,
  "you should add header X").

If you are unsure whether something is in scope, send the report
anyway — we would rather review and decline than miss a real issue.

## Hardening guidance for operators

Geshtu ships secure-by-default for a single-team self-hosted
deployment, but operators are responsible for the perimeter:

- Place the API and MCP server behind Caddy or another reverse proxy
  that terminates TLS.
- Do not expose Postgres or Redis to the public internet.
- Rotate teammate JWT tokens at least once per year, and immediately
  on personnel changes.
- Restrict the `admin` Streamlit UI to a private network or
  IP-allowlisted route.
- Keep the Anthropic API key in `.env`, never in version control.

A more detailed deployment guide lives in `/docs/deploy/`.

## Contact

- Security reports: **security@geshtu.io**
- General questions about this policy: open a discussion in the
  repository.
