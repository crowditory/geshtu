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

## Users

Self-service (any authenticated user, including members):

| Method | Path                  | What |
|--------|-----------------------|------|
| GET    | `/users/me`           | Current user (issued via the bearer) |
| GET    | `/users/me/tokens`    | List your own tokens (revoked + active) |
| POST   | `/users/me/tokens`    | Issue a fresh token for yourself, optionally project-scoped |

`POST /users/me/tokens` body:

```json
{ "label": "alice's laptop", "project": "main" }
```

Both fields optional. Omit `project` for an all-projects token (admins
only — members get 403 if they try). If your current token is itself
project-scoped, the new token inherits that scope.

Admin-only:

| Method | Path                              | What |
|--------|-----------------------------------|------|
| GET    | `/users`                          | List all users |
| POST   | `/users`                          | Create a new user (returns initial token, shown once) |
| GET    | `/users/{id}/tokens`              | List tokens for any user |
| POST   | `/users/{id}/tokens`              | Issue a token for any user (with optional project scope) |
| POST   | `/users/tokens/{token_id}/revoke` | Revoke a specific token |

`POST /users/{id}/tokens` body is the same as `POST /users/me/tokens`.
The response includes `project_id` and `project_slug` so the caller can
confirm the scope was applied.

## Token scope — what to know

`access_tokens.project_id` is nullable:

- `NULL` → all-projects token. Authenticates as the user across the
  entire team. Use sparingly — leak compromises everything.
- Set to a project ID → calls that reference any other project return
  403, and `GET /projects` filters down to just the scoped one.

The scope is enforced in `routes/common.py::resolve_project()`, which
every route that takes a `project` argument flows through. Routes that
take a `session_id` or `message_id` look up the project indirectly via
`assert_project_in_scope()`.
