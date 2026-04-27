# Governance

This document describes how Geshtu is governed: who decides what,
how decisions are made, and how that will evolve.

## Current model: BDFL with a public deadline

For the first **24 months** of the project, Geshtu operates under
a Benevolent Dictator For Life (BDFL) model.

- **BDFL:** Crowditory Ltd, represented by the project lead.
- **Final word** on architecture, roadmap, and merges rests with the BDFL.
- **No committee, no voting** during this period.

This is the model used by Linux (Linus), Python (Guido, historically),
and Vue (Evan You). It is the only structure that consistently works
for a solo-driven project in its first year.

At month 24 the model will be **publicly reviewed** in an issue:

- If the BDFL is still active: continue, optionally adding 1–2 maintainers.
- If the BDFL has stepped back: transition to a maintainer council of
  3–5 active long-term contributors.
- Either way, the outcome is documented in this file.

## What we accept into core

A pull request is merged into core only if it meets every one of these:

- Maps to one of the four memory layers — `messages`, `facts`,
  `decisions`, `session_summaries`.
- Does not add a new external runtime dependency without strong
  justification.
- Includes tests.
- Includes documentation updates for any user-visible change.
- Does not break the existing API surface, or includes a migration plan.

If a contribution is out of scope, it is not rejected as a judgment on
the contributor — it is simply pointed elsewhere. The standard reply:

> This is a great idea but does not fit the four-layer memory model.
> Consider publishing it as a separate plugin or extension; we will
> happily link to it from the README.

## The five-table rule

> Every memory operation in Geshtu maps to a query against one of
> four core tables: `messages`, `facts`, `decisions`, `session_summaries`.
> If a feature requires a fifth table, treat it as a signal to push back
> on the feature, not as a signal to add the table.

The simplicity is the product. New tables → new query patterns → new
test surface → compounding maintenance. Hold the line.

## Roadmap

The public roadmap lives at `github.com/crowditory/geshtu-roadmap`
(separate repo, GitHub Projects board) with three columns: **Now**,
**Next**, **Later**.

The roadmap is informational. It is updated when priorities change.

## RFC process

Major changes — anything that affects the MCP tool surface or the
database schema — require a Request For Comments (RFC):

1. Open an issue with `[RFC]` prefix in the title.
2. Post the proposal as a markdown comment on that issue.
3. Public comment period: **7 days** minimum.
4. The BDFL posts the final decision as a comment.
5. Accepted RFCs are archived in `/rfcs/` in the repository.

This is the pattern used by Rust and React. Lightweight, transparent,
proven at scale.

## Contributor ladder

Roles grow in response to demonstrated track record, not on a fixed
schedule. The expected pacing for the first 24 months:

- **Months 0–6:** the BDFL handles all PRs.
- **Months 6–12:** identify 2–3 regular contributors with consistent
  high-quality PRs.
- **Month 12:** invite them as **triagers** — can label and close
  issues; cannot merge to `main`.
- **Month 18:** promote one or more to **maintainer** — can merge
  non-architectural PRs after review.
- **Month 24:** review the BDFL model; formalize a maintainer council
  if appropriate.

Architectural decisions (schema changes, MCP surface changes, license
changes) remain with the BDFL throughout this period.

## Code of Conduct enforcement

The project follows the [Contributor Covenant 2.1](CODE_OF_CONDUCT.md).

For the first 24 months, enforcement is handled personally by the BDFL.
The standard escalation is a three-strike warning system, with public
acknowledgment for serious violations and repository bans for repeat
offenses. Reports go to **conduct@geshtu.io**.

## Decision-making outside the BDFL

Day-to-day decisions that do not affect architecture, schema, or the
MCP surface — for example, bug fixes, doc improvements, dependency
bumps within an existing major version — can be merged by any
maintainer once the contributor ladder has produced one.

When in doubt, ask in the relevant issue or PR thread.

## Changing this document

Changes to `GOVERNANCE.md` are themselves an RFC — they affect the
MCP surface only indirectly, but they affect everything else. Open an
issue, run the comment period, and merge with a clear changelog entry.
