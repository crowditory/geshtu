# Digests, three depths

A **digest** is an on-demand markdown summary of project activity since
some point in time. Three depths trade detail against length and cost.

| Depth      | Target length | Use case                                     | Sonnet tokens |
|------------|---------------|----------------------------------------------|---------------|
| `quick`    | ~300 words    | Catch-up after a weekend                     | low           |
| `standard` | ~800 words    | Tuesday morning re-orientation               | medium        |
| `deep`     | ~2500 words   | Returning after a vacation / writing a recap | high          |

## Inputs

For window `[since, now]`:

- All facts created in the window
- All decisions made in the window
- All session summaries closed in the window

These are concatenated into a structured payload and handed to **Claude
Sonnet 4.6** (digests are read by humans, quality matters more than
speed/cost).

## Output

Markdown. Quick and standard always have the same four sections:

- **Changed** — what evolved (facts that were superseded, refined)
- **Decided** — explicit choices the team made
- **Open Questions** — collected from session summaries
- **Next** — collected from session summaries' next-actions

Deep is narrative: it groups related decisions, surfaces dropped
threads, and attributes work to people.

## Caching

Each digest is keyed by `(project, depth, since)` and cached for 1 hour
(`DIGEST_CACHE_TTL_SECONDS`). Identical requests in the cache window
return the saved markdown without re-calling Sonnet. Pass
`use_cache=false` to force regeneration.

## Costs

For a 5-person team running ~10 digests/day:

- Quick: ~€0.005 each
- Standard: ~€0.012 each
- Deep: ~€0.04 each

Roughly €3–5/month. Caching covers the most common pattern (everyone
on the team asks "what's new" Monday morning, only the first call hits
Sonnet).
