# Testing

The repo is set up so that **CI is the default test path**. You don't need to
install Postgres, Redis, torch, or BGE-M3 locally. Push your branch and the
suite runs in GitHub Actions in ~2 minutes.

If you want a faster inner loop, the optional local-Docker section below
gets you the same coverage in ~30 seconds.

## CI: GitHub Actions

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every
push and PR:

- Postgres + pgvector and Redis as service containers (no setup, no secrets).
- Python deps (skipping torch / sentence-transformers — extraction tests
  mock those at the function boundary).
- `python -m geshtu.migrate` against the ephemeral Postgres.
- `pytest` with the `not golden` filter.
- `ruff check api/geshtu`.
- `tsc --noEmit` against the MCP server.

That's it for normal development. Open a PR, watch the green checkmark.

### Optional: GitHub repo secret

| Secret | When | Required? |
|---|---|---|
| `ANTHROPIC_API_KEY` | Only for the `golden` extraction test | **Optional** |

Set it once at <https://github.com/crowditory/geshtu/settings/secrets/actions>
if you want to run the golden test on `workflow_dispatch`. PRs from forks
don't get secrets — that's by design.

### Running golden manually

The "golden set" is 5 hand-curated extraction examples that hit the real
Anthropic API. Cost: ~5 × €0.001 = €0.005 per run. To trigger it:

1. Repo → Actions → "CI" workflow → **Run workflow**
2. Set `run_golden` to `true`
3. Run

Requires `ANTHROPIC_API_KEY` to be present in repo secrets.

## Local development (optional)

If you want tests faster than a CI round-trip, run the same Docker stack on
your laptop. **Docker Desktop on Windows / macOS** or **Docker Engine on
Linux** is the only prerequisite.

```bash
# one-time setup
cp .env.example .env
# edit .env — at minimum ANTHROPIC_API_KEY (placeholder is fine for non-golden tests)

# bring up Postgres + Redis (and optionally the API)
docker compose up -d postgres redis

# apply migrations
docker compose run --rm api python -m geshtu.migrate

# run the suite — bind-mount your local source so edits take effect immediately
docker compose run --rm \
    -v "$PWD/api:/app" -w /app \
    api sh -c "pip install -q pytest pytest-asyncio respx && pytest -q -k 'not golden'"
```

After the first run the postgres/redis containers stay healthy in the
background; subsequent test invocations are fast.

To wipe state between runs:

```bash
docker compose down -v
```

## Test taxonomy

| File | What it covers | Needs DB | Notes |
|---|---|---|---|
| `test_extract_parser.py` | Pure JSON parser | no | Always runs |
| `test_health_route.py` | `/health` via TestClient | no | Always runs |
| `test_auth.py` | JWT issue/verify, revocation | yes | |
| `test_dedup.py` | UPDATE / REFINE / ADD thresholds | yes | Synthetic vectors |
| `test_routes.py` | Auth + projects + sessions + messages + decisions + tokens, end-to-end via TestClient | yes | |
| `test_extraction_pipeline.py` | Worker pipeline with mocked Anthropic + embed | yes | Uses `respx` |
| `test_migrations.py` | Idempotent migration application | yes | |
| `test_extract_golden.py` | Real Anthropic extraction quality | yes + key | Gated by `RUN_GOLDEN=1` |
| `test_routes.py::test_log_fact_returns_status` | Real BGE-M3 embedding | yes + 2 GB RAM | Gated by `RUN_BGE=1` |

DB-touching tests **skip** (rather than fail) when no Postgres is reachable,
so the unit-level subset works even if you run pytest without Docker.

## Adding new tests

The fixtures in `tests/conftest.py` give you `db` (a session) and `have_db`
(a flag the DB-needing tests skip on). Helpers `_make_user` and
`_make_project` from `test_routes.py` build an authed TestClient setup.

For mocking external APIs, prefer `respx` — it intercepts at the httpx
layer, so the Anthropic SDK's own client behaves normally during the test.
For things that load heavy dependencies (BGE-M3, real Sonnet), gate the
test behind an env var (`RUN_GOLDEN=1`, `RUN_BGE=1`, etc.) and add it to
the table above.

Default-on tests must run in <30 seconds without external API calls.
