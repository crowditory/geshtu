# MCP tool reference

Geshtu exposes exactly six tools. Each maps to one or two REST endpoints
on the API. The MCP server is a thin proxy — all logic lives in `api/`.

## `geshtu_search`

Hybrid search over a project's facts (and active decisions, opt-out via
`include_decisions=false`).

| param   | type           | required | default |
|---------|----------------|----------|---------|
| project | string (slug)  | yes      | —       |
| query   | string         | yes      | —       |
| k       | int (1–50)     | no       | 10      |

Returns `{ facts: [...], decisions: [...] }`. Each item has a `score`
(RRF-fused). Use BEFORE answering questions about past work.

REST: `GET /search?project=…&q=…&k=…`

## `geshtu_decisions`

List recent decisions chronologically.

| param   | type     | required | default |
|---------|----------|----------|---------|
| project | string   | yes      | —       |
| limit   | int      | no       | 10      |
| since   | ISO date | no       | —       |

REST: `GET /decisions?project=…&limit=…&since=…`

## `geshtu_digest`

On-demand markdown summary at three depths.

| param   | type                              | required | default     |
|---------|-----------------------------------|----------|-------------|
| project | string                            | yes      | —           |
| depth   | `quick` \| `standard` \| `deep`   | no       | `standard`  |
| since   | ISO date                          | no       | —           |

Quick ≈ 300 words / Standard ≈ 800 / Deep ≈ 2500. Cached for 1 hour per
`(project, depth, since)` triple.

REST: `GET /digest?project=…&depth=…&since=…`

## `geshtu_log_decision`

Record a decision + rationale. Rationale is required by design.

| param      | type   | required |
|------------|--------|----------|
| project    | string | yes      |
| decision   | string | yes      |
| rationale  | string | yes      |

REST: `POST /decisions` with body `{project, decision, rationale}`.

## `geshtu_log_fact`

Record a fact explicitly (auto-extraction also records implicit facts).
Subject to dedup: cosine ≥ 0.92 supersedes; 0.75–0.92 refines; below
inserts.

| param      | type   | required |
|------------|--------|----------|
| project    | string | yes      |
| statement  | string | yes      |
| entity     | string | no       |
| attribute  | string | no       |

Returns `{ id, status: 'logged' | 'updated' | 'duplicate', superseded_id?, refines_id? }`.

REST: `POST /facts`.

## `geshtu_close_session`

Close a session with a summary, open questions, next actions.

| param           | type       | required | default     |
|-----------------|------------|----------|-------------|
| session_id      | uuid       | yes      | —           |
| summary         | string     | no       | auto-generated via Sonnet |
| open_questions  | string[]   | no       | []          |
| next_actions    | string[]   | no       | []          |

REST: `POST /sessions/{id}/close`.
