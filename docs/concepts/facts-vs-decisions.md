# Facts vs Decisions

Two of Geshtu's four memory tables. They look similar at a glance and the
distinction is intentional. Mixing them defeats the design.

## Facts

A **fact** is a stable claim about an entity. Examples:

- "Postgres 16 is the primary database."
- "The support email is help@playserv.io."
- "The mobile release window is Tuesdays."

Facts have:

- A statement (the claim itself)
- An optional entity + attribute (e.g. `Postgres` / `version`)
- A 1024-dim embedding (BGE-M3, local)
- A validity window (`valid_from`, `valid_until`)
- A `superseded_by` link if a newer fact replaces this one

Facts are **deduped** on write. If you log "Postgres 16 is the database"
and later "We use Postgres 16", the second one supersedes the first
(cosine ≥ 0.92) — the team's memory contains one fact, with a clean
history.

## Decisions

A **decision** is a choice your team made, with the rationale.

- "Decision: monthly billing only. Rationale: annual is too inflexible
  for early customers."
- "Decision: hire frontend before backend. Rationale: design debt is
  growing faster than infra debt."

Decisions have:

- The decision text
- A **required** rationale (this is the whole point — Geshtu rejects
  decisions without one)
- Authorship (`decided_by`)
- Status: `active`, `reversed`, `superseded`
- A reverse link via `reversed_by` when a later decision overrides

Decisions are **never deduped**. Two similarly-worded decisions a month
apart are likely two distinct moments in your team's evolution; we keep
both.

## When in doubt

Ask: "Could this be wrong tomorrow without anyone making a decision?"

- **Yes** → it's a fact. (Customer's email, current pricing, last-known-good build.)
- **No, it would take a deliberate choice to change** → it's a decision.
  (We chose Postgres. We picked monthly billing.)

## Why two types

The single mistake competing memory systems make is collapsing these.
You lose:

- The ability to ask "what did we decide and why" (decisions are buried)
- The ability to invalidate stale facts without rewriting history
- The audit trail showing who chose what when

Two tables, two queries. Simple.
