# Privacy Notice

Geshtu is **self-hosted software**. When your team installs it,
you are the data controller — Crowditory Ltd does not host your data,
does not have access to your database, and does not collect your
content.

This document explains where data goes when Geshtu runs, what
third parties are involved, and what the project upstream does and
does not collect.

## What Geshtu stores

On the box where you run it, Geshtu writes the following to its
own Postgres database:

- **Messages** logged by your team — raw conversation content,
  timestamps, the user who logged them, and the project the message
  belongs to.
- **Facts** extracted from those messages, with their embeddings and
  validity windows.
- **Decisions** logged explicitly by team members, with rationale.
- **Session summaries** generated when sessions are closed.
- **Users**, **teams**, and **projects** — minimal identity records
  needed for token-based auth.
- **Access logs** — who read what and when, for audit.

All of this lives in the Postgres instance you control. There is no
phone-home channel for content.

## Third parties involved when Geshtu runs

Geshtu makes outbound requests to a small, fixed list of
services. Operators should disclose these to their team.

### Anthropic (required)

Geshtu sends message content to the **Anthropic API** for two
purposes:

- **Extraction** — Claude Haiku 4.5 reads new messages and returns
  structured facts and decisions in JSON.
- **Digests** — Claude Sonnet 4.6 generates project digests on
  request.

Anthropic's data handling for API traffic is governed by their
[commercial terms](https://www.anthropic.com/legal/commercial-terms).
At time of writing, API inputs and outputs are not used to train
Anthropic models by default. Verify the current policy before
deploying.

The Anthropic API key is supplied by the operator via `.env`. There
is no Geshtu-controlled gateway in the path.

### Embedding model — local

Embeddings are produced **locally on CPU** via BGE-M3. **No embedding
API is called.** This is a deliberate design choice: the embedding
surface is the largest data flow in the system, and keeping it local
removes one third party entirely.

### No other third parties

Geshtu does not integrate with analytics platforms, error
trackers, ad networks, or CDNs as part of its runtime. If your
deployment topology adds any of those (for example, a reverse proxy
behind Cloudflare), that is your operational choice and falls under
your own privacy notice.

## Telemetry from the upstream project

Upstream Geshtu has a telemetry policy documented separately in
`TELEMETRY.md`. Summary:

- **Off by default** in v0.1 and for the foreseeable future.
- **Opt-in only**, via env var `GESHTU_TELEMETRY=on` or admin UI.
- When opted-in: an anonymous instance ID, version string, startup and
  healthcheck events. **No content. No query strings. No team data.**
- Aggregate counts may be published at `geshtu.io/stats`.
- Opt-out is instant by setting the env var to `off`.

If you do not opt in, no traffic from your deployment reaches the
upstream project — there is no analytics endpoint that the software
talks to silently.

## Data subject requests

Because Geshtu is self-hosted, requests under GDPR, CCPA, or
similar frameworks are handled by **the operating team**, not by the
upstream project. Geshtu provides the SQL surface needed to
fulfill them:

- **Access** — facts, decisions, and messages are queryable per user
  via the admin UI and direct SQL.
- **Deletion** — `DELETE FROM messages WHERE user_id = ?` cascades to
  derived facts and decisions via foreign keys; the admin UI exposes
  a per-user delete action.
- **Export** — JSON export per project is available via the API.

Operators are responsible for their own retention policies and for
disclosing them to their team.

## Data Processing Agreement (DPA)

For EU teams that need a DPA between **the operating organization and
its team members**, a template will be provided in `/legal/` once the
project is past initial bootstrap. This is a self-service template;
the upstream project is not a sub-processor in your deployment.

If you have a contractual relationship with Anthropic that requires a
DPA, that is between your organization and Anthropic directly.

## Sub-processors (when running upstream-hosted services)

Crowditory Ltd does not currently operate a hosted Geshtu
service. If and when one launches, the live sub-processor list will
be published at `geshtu.io/security/sub-processors` with
versioning and a change-notification policy. Until then, this section
is intentionally empty.

## Security

See [SECURITY.md](SECURITY.md) for vulnerability reporting and
operator hardening guidance.

## Contact

- Privacy questions about the upstream project: **privacy@geshtu.io**
- Privacy questions about your team's specific deployment: contact
  your team's operator. The upstream project cannot answer those —
  we do not have access to your data.
