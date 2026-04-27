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
  --admin-name "Me"
```

This prints a one-time admin token. **Save it.** You'll use it to log into
the admin UI and to wire your own Claude Desktop.

## Step 5 — Open the admin

Visit <http://localhost:8501> and paste the admin token to log in.

From there:

1. Create a project (e.g. `playserv-core`).
2. Add a teammate — copy the displayed token, send it to them via secure channel.
3. They paste the token into their Claude Desktop config (see
   [claude-desktop-setup.md](claude-desktop-setup.md)).

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
