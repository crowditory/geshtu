# How extraction works

When a message arrives at `POST /messages`:

1. The API saves it synchronously to `messages` and returns 200. **The
   user never waits on extraction.**
2. The API enqueues a Celery task (`geshtu.extract_message`) on Redis.
3. The worker pulls the job and runs the spec §5.1 pipeline:

```
       message text
            │
            ▼
    ┌────────────────┐
    │ skip filter    │  drop greetings, <40-char chatter
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ Claude Haiku   │  → strict JSON: {facts:[], decisions:[]}
    │ (extract.py)   │
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ BGE-M3 embed   │  local CPU, 1024-dim, free
    │ (embed.py)     │
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ for each fact: │
    │  cosine vs.    │
    │  active facts  │
    │   ≥0.92 → SUPERSEDE (set valid_until on old, link via superseded_by)
    │   0.75–0.92 → REFINE (insert + link via refines)
    │   <0.75 → ADD (pure insert)
    │ (dedup.py)     │
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ insert         │  decisions are NEVER deduped — context is unique
    │ decisions      │
    └───────┬────────┘
            ▼
    ┌────────────────┐
    │ access_log row │
    └────────────────┘
```

## Why Haiku for extraction

Extraction is the highest-volume LLM call in Geshtu — every substantive
message triggers one. Haiku 4.5 is the cheapest reasoning model that
emits structured JSON reliably. Roughly €0.001 per call at our prompt
size, or about €8–12/month for a 5-person team writing 500 messages/day.

## Why BGE-M3 for embeddings

Embeddings happen even more often than extraction (one per fact, one
per query). Calling a paid embedding API at that volume would dominate
the bill. BGE-M3 runs on CPU, takes ~80ms per fact, and is multilingual
out of the box. The model cache is ~2 GB and lives in a Docker volume
shared between API and worker.

## Why `valid_until` instead of overwriting

Memory should be **auditable**. If your team chose Postgres, then
later moved to ClickHouse, both moments are part of the team's history.
Geshtu marks the older fact's `valid_until = now()` and links the new
fact via `superseded_by` — the old claim isn't deleted, just out of the
active set. Future digests can still surface it ("the team moved from
Postgres to ClickHouse on Apr 12").

## What happens if Haiku is down

The API still returns 200. The Celery job retries with backoff (default
3 retries, 10s apart). After all retries fail, the message lives on in
`messages`; you can re-trigger extraction later by republishing the job.
You don't lose data and the user is never blocked.

## What happens if you change the embedding model

Don't, casually. Embedding spaces aren't compatible across models.
If you must (e.g. BGE-M3 → BGE-M3.5):

1. Add a column for the new dimension if it differs.
2. Backfill: re-embed all `facts` with the new model.
3. Cut over `EMBEDDING_MODEL` in `.env`.

A future migration will probably automate this; for v0.1, treat it as
a one-time operator task.
