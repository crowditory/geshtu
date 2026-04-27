# REST API reference

The MCP server proxies these endpoints; you can also call them directly
(e.g. from CI, a script, or a custom integration). All endpoints require
`Authorization: Bearer <token>` except `/health`.

## Health

`GET /health` → `{status, version, db}`

## Projects

| Method | Path             | Auth   |
|--------|------------------|--------|
| GET    | `/projects`      | user   |
| POST   | `/projects`      | admin  |
| GET    | `/projects/{slug}` | user |

POST body:
```json
{ "slug": "playserv-core", "name": "PlayServ Core", "description": "..." }
```

## Sessions

| Method | Path                          | Auth |
|--------|-------------------------------|------|
| POST   | `/sessions`                   | user |
| GET    | `/sessions/{id}`              | user |
| POST   | `/sessions/{id}/close`        | user |

POST `/sessions` body:
```json
{ "project": "playserv-core", "title": "kickoff", "llm_model": "claude-sonnet-4-6" }
```

POST `/sessions/{id}/close` body (provide either summary_md or set auto_summarize=true):
```json
{ "summary_md": "...", "open_questions": [], "next_actions": [], "auto_summarize": false }
```

## Messages

`POST /messages`
```json
{ "session_id": "uuid", "role": "user|assistant|system|tool", "content": "...", "extract": true }
```

The API saves synchronously and returns 200 BEFORE extraction runs (spec invariant).

## Search

`GET /search?project=<slug>&q=<text>&k=10&include_decisions=true`

## Decisions

| Method | Path           |
|--------|----------------|
| GET    | `/decisions`   |
| POST   | `/decisions`   |

GET params: `project`, `limit`, `since`.
POST body: `{ project, decision, rationale, source_session_id?, source_message_id? }`.

## Facts

`POST /facts`
```json
{ "project": "playserv-core", "statement": "Postgres 16 is the primary DB", "entity": "Postgres", "attribute": "version" }
```

Returns `{ id, status, superseded_id?, refines_id? }`.

## Digest

`GET /digest?project=<slug>&depth=quick|standard|deep&since=<ISO>&use_cache=true`

## Users (admin)

| Method | Path                              |
|--------|-----------------------------------|
| GET    | `/users`                          |
| POST   | `/users`                          |
| GET    | `/users/me`                       |
| GET    | `/users/{id}/tokens`              |
| POST   | `/users/{id}/tokens`              |
| POST   | `/users/tokens/{token_id}/revoke` |
