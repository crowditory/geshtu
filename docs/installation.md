# Installation

Geshtu is one Docker Compose file. Five minutes to a working server.

## Prerequisites

- Docker 24+ and Docker Compose v2
- ~4 GB free RAM (BGE-M3 takes ~2 GB during embedding)
- An Anthropic API key from <https://console.anthropic.com>

That's it. No Kubernetes. No vector DB. No managed services.

## Step 1 — Clone and configure

```bash
git clone https://github.com/crowditory/geshtu
cd geshtu
cp .env.example .env
```

Edit `.env` and set at minimum:

- `POSTGRES_PASSWORD` — any strong random string
- `JWT_SECRET` — `openssl rand -hex 32`
- `ANTHROPIC_API_KEY` — your key

## Step 2 — Start the stack

```bash
docker compose up -d --build
```

The first build takes ~5 minutes (mostly downloading PyTorch and BGE-M3
on first worker startup). Subsequent restarts are seconds.

Check it's up:

```bash
docker compose ps
docker compose exec api curl -fsS http://localhost:8000/health
```

## Step 3 — Apply migrations

```bash
docker compose exec api python -m geshtu.migrate
```

Idempotent: safe to re-run.

## Step 4 — Bootstrap your team

```bash
docker compose exec api python -m geshtu.bootstrap \
  --team "My Team" \
  --admin-email "me@example.com" \
  --admin-name "Me" \
  --project-slug "main" \
  --project-name "Main"
```

`--project-slug` and `--project-name` are optional but recommended on first
run: bootstrap creates the project and issues a **project-scoped token** in
addition to the admin token, so you skip the "create your first project"
step in the UI. Output looks like:

```
Admin token — full access, all projects (save it; shown only once):
   tk_eyJhbGc…

Project-scoped token for 'main' — recommended for daily use; paste this
into your MCP client:
   tk_eyJhbGc…
```

Save **both** tokens (in 1Password / Bitwarden / your secret store of
choice). The admin one logs you into the UI and lets you add teammates;
the project-scoped one is what you drop into your own Claude Desktop
config — narrower blast radius if it leaks.

## Step 5 — Open the admin

For local development without TLS: visit <http://localhost:8501>.
For production with Caddy: visit `https://<your-hostname>/`.

Paste the admin token to log in. The sidebar's **Connect** tab gives you:

1. A button to issue more tokens (per-user, optionally per-project)
2. Pre-filled JSON config for Claude Desktop / Cursor / Windsurf —
   includes your real API URL, project slug, and email
3. The team protocol block to paste into your project's system prompt

From the **Users** tab you add teammates one at a time; for each, the UI
issues a token and shows it once. Send them the **Connect** page link
plus their token; they paste both into their MCP client.

## Token model — what's worth knowing

Geshtu tokens come in two flavors:

| Flavor | When | Risk if leaked |
|---|---|---|
| **All-projects** (no scope) | Admins only — for managing users, projects, settings | Compromises the entire team's memory |
| **Project-scoped** | Members; admins also use these for daily work | Compromises only that project — other projects unreachable from this token |

Issue project-scoped tokens by default. Keep the admin all-projects token
in a secret manager and use it only for admin tasks via the UI.

The schema-level enforcement lives on `access_tokens.project_id`: when
set, `resolve_project()` returns 403 for any request that targets a
different project, and `/projects` filters to only the scoped one.

## Step 6 — TLS (production)

```bash
cp Caddyfile.example Caddyfile
# edit PUBLIC_HOSTNAME in .env, point your DNS at the server
docker compose --profile tls up -d
```

Caddy auto-provisions Let's Encrypt certs.

## Backup

Two volumes hold all state:

- `pgdata` — Postgres
- `redisdata` — Redis (only the queue; ephemeral)

```bash
docker compose exec postgres pg_dump -U geshtu geshtu > backup-$(date +%F).sql
```

Restore:

```bash
cat backup-2026-04-27.sql | docker compose exec -T postgres psql -U geshtu geshtu
```

## Troubleshooting

| Symptom                                       | Likely cause                          | Fix                          |
|-----------------------------------------------|---------------------------------------|------------------------------|
| Worker crashes on first message               | BGE-M3 still downloading              | wait ~3 min, watch `docker compose logs worker` |
| `/search` slow                                | HNSW index not built yet              | first 1000 facts; speeds up after |
| `ANTHROPIC_API_KEY` errors in API logs        | Wrong key or rate-limit               | verify in Anthropic console  |
| Tokens rejected after `docker compose down`   | `JWT_SECRET` mismatch on restart      | preserve `.env`               |
| Admin UI says "Token rejected"                | Token revoked or expired              | issue a new one via CLI      |
