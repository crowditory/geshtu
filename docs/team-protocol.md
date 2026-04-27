# Team Memory Protocol — Geshtu

> Drop this into every project's system prompt or rules file. Replace
> `{{PROJECT_SLUG}}` with the project's slug.

```markdown
You have access to the team's shared memory via `geshtu_*` tools.
Project slug: {{PROJECT_SLUG}}.

## Before answering substantive questions
1. If the user references past work ("our plan", "we decided",
   "the architecture"), call `geshtu_search` with key terms.
2. If the user starts with a catch-up question ("what's new",
   "where are we"), call `geshtu_digest` with depth='quick' first.
3. Treat retrieved facts as ground truth. If the user contradicts
   them, ASK whether to update — don't silently overwrite.

## During the conversation
- When the user makes an explicit decision ("let's go with X"),
  call `geshtu_log_decision` BEFORE moving on, capturing
  both the decision and the rationale.
- When the user says "remember that..." or "note that...",
  call `geshtu_log_fact`.

## At session end (or every 20 substantive turns)
- Call `geshtu_close_session` with a brief markdown summary,
  open questions, and next actions.

## Citation rules
- When using a retrieved fact, cite briefly: "(per memory, Apr 12)".
- When facts and the current message conflict, surface the conflict.
- Never invent a fact or rationale not in memory or this conversation.
```

## Where to paste it

| Client          | Location                                       |
|-----------------|------------------------------------------------|
| Claude Desktop  | Project Instructions                           |
| Cursor          | `.cursor/rules` or project-level `CLAUDE.md`   |
| Windsurf        | `.windsurfrules`                               |
| Cline / others  | Per-project system prompt                      |

## Why this works

The protocol matches the four-table memory model 1:1:

- `geshtu_search` reads `facts` (hybrid SQL via Reciprocal Rank Fusion).
- `geshtu_digest` joins facts + decisions + summaries into a Sonnet-summarized window.
- `geshtu_log_fact` and `geshtu_log_decision` write to the corresponding tables.
- `geshtu_close_session` writes to `session_summaries`.

If your AI follows the protocol, every conversation contributes to the team's
memory and benefits from past contributions — without anyone managing it manually.
