# FAQ

### Is this a SaaS?

No. Geshtu is self-hosted only — `git clone && docker compose up`.
A hosted version may appear later as a convenience, but every feature
in the spec stays in OSS forever (see [LICENSE_PHILOSOPHY.md](../LICENSE_PHILOSOPHY.md)).

### Why not Mem0 / Zep / Letta?

Those are designed around **one user's relationship with one AI**.
Geshtu is designed around **one team's relationship with one project**.
Different unit of analysis → different schema → different tradeoffs.
See the comparison table in the README.

### Why AGPL?

To prevent hyperscalers from re-hosting Geshtu as a competing service
without contributing back. Cal.com, n8n, Plausible, Mastodon all use
AGPL for the same reason. Internal use is fine; sharing modifications
is required only if you offer Geshtu *as a service* to third parties.

### Will you re-license to BSL or anything else?

We've reserved the right (CLA grants Crowditory the ability) but
**old AGPL versions stay AGPL forever** — the community keeps what they
already have.

### What data leaves my server?

By default: only outbound calls to `api.anthropic.com` for extraction
(Haiku) and digests (Sonnet). Embeddings are local. Nothing else.

If you turn on `GESHTU_TELEMETRY=on`, an anonymous startup ping with
just the version and platform is sent to `telemetry.geshtu.io`. No
content. Off by default.

### Can I use a different LLM provider?

Not in v0.1. The code paths are abstract enough to swap in another
provider, but the prompt + JSON parsing are tuned for Claude. PRs
welcome if you have time.

### Can I use a different embedding model?

Yes — set `EMBEDDING_MODEL` to any sentence-transformers-compatible
model and `EMBEDDING_DIM` to its output size, then re-embed your data.
See [how-extraction-works.md](concepts/how-extraction-works.md#what-happens-if-you-change-the-embedding-model).

### How do I back up data?

```bash
docker compose exec postgres pg_dump -U geshtu geshtu > backup.sql
```

That's the whole memory layer. Redis is just a queue, nothing to back up.

### Does it work offline?

Embeddings: yes, fully. Extraction and digests need Anthropic — those
calls go out. If Anthropic is unreachable, the API still saves messages;
extraction retries when the network returns.

### How does scope/multi-tenancy work?

Geshtu is single-team by design. The `team` table has exactly one row.
You scope memory by **project**, and every API call requires a project
slug. If you need multiple isolated teams, run multiple Compose stacks
on different ports — that's the supported pattern in v0.1.

### What if the AI hallucinates a fact and writes it to memory?

That's why the team protocol says: *"Treat retrieved facts as ground
truth. If the user contradicts them, ASK whether to update — don't
silently overwrite."* The admin UI exposes every fact and decision,
filterable by author and date — review what's getting captured during
the first week.
