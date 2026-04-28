# @geshtu/mcp

**MCP server for [Geshtu](https://github.com/crowditory/geshtu)** — self-hosted
shared memory for teams using LLMs.

This package exposes 6 MCP tools that proxy to a self-hosted Geshtu API:

- `geshtu_search` — hybrid (vector + keyword) search over your team's facts
- `geshtu_decisions` — list recent decisions with rationale
- `geshtu_digest` — async markdown digest of project activity
- `geshtu_log_decision` — record a decision + rationale
- `geshtu_log_fact` — record an explicit fact (with auto-dedup)
- `geshtu_close_session` — close a session with summary, open questions, next actions

The actual memory layer (Postgres + pgvector + extraction worker) lives
separately. **You self-host the server, this package is just the client adapter.**
See <https://github.com/crowditory/geshtu> for setup.

## Install

You don't install it directly — your MCP client (Claude Desktop, Cursor,
Windsurf, Cline, …) launches it via `npx -y @geshtu/mcp` per your config.

## Configure (Claude Desktop)

```json
{
  "mcpServers": {
    "geshtu": {
      "command": "npx",
      "args": ["-y", "@geshtu/mcp"],
      "env": {
        "GESHTU_TOKEN": "tk_...",
        "API_URL": "http://memory.example.com:8000"
      }
    }
  }
}
```

The token comes from your team's Geshtu admin (issued via the admin UI or
`docker compose exec api python -m geshtu.bootstrap`). For Cursor, Windsurf,
and other clients, see the per-client guides in the main repo.

## How it works

```
Claude Desktop ──stdio──▶ this package ──HTTP──▶ memory-api (your server)
                          (forwards token)        (validates JWT, runs query,
                                                   returns facts/decisions)
```

This package contains no business logic — JWT validation, embeddings, dedup,
search ranking all happen on the API side. That keeps the surface stable
even if internal endpoints change.

## Requirements

- Node.js 20+
- A running Geshtu deployment (`git clone && docker compose up`)
- A team token issued by your admin

## License

AGPL-3.0-only. See the [main repository](https://github.com/crowditory/geshtu)
for the full license text and trademark policy.
