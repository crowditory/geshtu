# Geshtu

**Self-hosted shared memory for teams using LLMs.**
Connect Claude Desktop, Cursor, or Windsurf — your team gets persistent,
project-scoped memory and async digests across every chat.

> *Geshtu — Sumerian for "ear", "wisdom", and "memory". In Mesopotamian
> thought, the ear was the organ of memory: to listen well was to
> remember.*

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![MCP](https://img.shields.io/badge/MCP-compatible-green.svg)](https://modelcontextprotocol.io)
[![Postgres](https://img.shields.io/badge/Postgres-16-336791.svg)](https://www.postgresql.org/)

> **Open core promise.** Every feature documented in this repository stays
> in OSS forever under AGPL-3.0. New features may launch hosted-only and
> migrate to OSS later — but **never the reverse**.

---

## Why

Every chat with an LLM starts cold. You re-explain the project, the stack,
the decisions. With 5 teammates and 3 tools, your team spends an hour a day
reminding the AI of context it had yesterday.

Geshtu holds onto that context for the whole team. When a teammate
opens Claude on Tuesday and asks *"catch me up on the project since Friday"*,
they get a clean digest in 30 seconds, scoped to the project, cited back
to the source.

## What it does

- **Captures facts and decisions** from your conversations automatically
- **Tracks rationale**, not just outcomes — *why* you chose Postgres, not
  just *that* you did
- **Generates async digests** at three depths (`quick` / `standard` / `deep`)
- **Scopes everything per-project** so memory never leaks between products
- **Works in any MCP client** — Claude Desktop, Cursor, Windsurf, Cline...

## Quick start

```bash
git clone https://github.com/crowditory/geshtu
cd geshtu
cp .env.example .env
# edit .env — at minimum set ANTHROPIC_API_KEY, JWT_SECRET, POSTGRES_PASSWORD
docker compose up -d --build
docker compose exec api python -m geshtu.migrate
docker compose exec api python -m geshtu.bootstrap \
  --team "My Team" \
  --admin-email "me@example.com" \
  --admin-name "Me"
```

The `bootstrap` command prints a JWT token. Drop it into your Claude
Desktop config:

```json
{
  "mcpServers": {
    "geshtu": {
      "command": "npx",
      "args": ["-y", "@geshtu/mcp"],
      "env": {
        "GESHTU_TOKEN": "tk_...",
        "API_URL": "http://localhost:8000"
      }
    }
  }
}
```

Restart Claude. You now have six new tools and your team's memory layer is
wired in. See [docs/claude-desktop-setup.md](docs/claude-desktop-setup.md)
for screenshots and other clients.

## How it works

```
Your message ──▶ memory-api ──▶ saved to Postgres
                      │
                      └─▶ Celery worker:
                          - extracts facts + decisions via Claude Haiku
                          - embeds via BGE-M3 (local, no API)
                          - dedupes against existing memory
                          - supersedes outdated facts (temporal validity)

Your AI calls geshtu_search → hybrid search (vector + keyword via RRF)
                                  → returns relevant facts and decisions
```

Four layers of memory, each doing one thing well:

1. **Raw log** — every message, untouched. Source of truth.
2. **Facts** — extracted statements with embeddings and validity windows.
3. **Decisions** — explicit choices with their rationale and authorship.
4. **Session summaries** — what happened, where you stopped, what's open.

## The team protocol

For Geshtu to work reliably, your AI needs to know when to read
and write memory. Drop this into your project's system prompt or rules file:

```markdown
# Team Memory Protocol — Geshtu
You have access to the team's shared memory via `geshtu_*` tools.
Project slug: {{PROJECT_SLUG}}.

Before answering substantive questions:
- If the user references past work, call geshtu_search.
- If the user starts with a catch-up question, call geshtu_digest depth='quick'.
- Treat retrieved facts as ground truth. If contradicted, ASK — don't overwrite.

During the conversation:
- On explicit decisions, call geshtu_log_decision (with rationale).
- On "remember that...", call geshtu_log_fact.

At session end (or every 20 turns):
- Call geshtu_close_session with summary, open questions, next actions.

Citation rules:
- Cite retrieved facts briefly: "(per memory, Apr 12)".
- Surface conflicts. Never invent rationale.
```

Full protocol: [docs/team-protocol.md](docs/team-protocol.md).

## Stack

- PostgreSQL 16 + pgvector + pg_trgm
- Python / FastAPI / Celery
- Node.js MCP server (`@modelcontextprotocol/sdk`)
- Claude Haiku 4.5 (extraction) + Sonnet 4.6 (digests)
- BGE-M3 embeddings (local, CPU, 1024-dim)
- Streamlit admin (optional)
- Docker Compose deployment

Runs on a single Hetzner CPX21 (~€8/month) for teams up to ~15 people.

## What this is not

- Not a SaaS — self-host or fork.
- Not a RAG tool — we don't ingest your PDFs.
- Not a chat UI — memory lives invisibly inside Claude/Cursor/etc.
- Not multi-tenant — one deployment per team.

## Contributing

Issues, PRs, and ideas welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).
For security disclosures, see [SECURITY.md](SECURITY.md).

## License

AGPL-3.0. See [LICENSE](LICENSE).

For commercial license inquiries (use cases incompatible with AGPL):
licensing@geshtu.io.

## Disclosures

Geshtu is owned by Crowditory Ltd. Several products in our portfolio use
Geshtu internally, which informs feature priorities. We commit to keeping
Geshtu neutral — no portfolio-specific code in core, no preferential
integrations.
