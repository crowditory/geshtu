# Claude Desktop setup

## 1. Get a token

Ask your admin to add you on the **Users** page in the Geshtu admin UI.
After they confirm, send them their **Connect** page link — that page
shows the token + a pre-filled JSON snippet you can copy directly.
Tokens look like `tk_eyJhbGciOiJIUzI1NiIs...`.

If you're running Geshtu yourself, your bootstrap output already gave
you a project-scoped token. That's the one you want here (not the
all-projects admin token).

## 2. Find your config file

| OS       | Path                                                              |
|----------|-------------------------------------------------------------------|
| macOS    | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows  | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux    | `~/.config/Claude/claude_desktop_config.json`                     |

## 3. Add the Geshtu MCP server

```json
{
  "mcpServers": {
    "geshtu-main": {
      "command": "npx",
      "args": ["-y", "@geshtu/mcp"],
      "env": {
        "GESHTU_TOKEN":   "tk_paste-your-token-here",
        "GESHTU_API_URL": "https://geshtu.example.com/api",
        "GESHTU_EMAIL":   "you@example.com",
        "GESHTU_PROJECT": "main"
      }
    }
  }
}
```

| Env | Required? | What it does |
|---|---|---|
| `GESHTU_TOKEN` | yes | Bearer issued by your admin (starts with `tk_`) |
| `GESHTU_API_URL` | yes (in production) | Base URL of memory-api, e.g. `https://geshtu.example.com/api`. Falls back to `http://api:8000` for in-docker setups. |
| `GESHTU_EMAIL` | recommended | Your email. The MCP server calls `/users/me` on startup and refuses if the token doesn't identify this user — catches "I pasted Bob's token by accident" mistakes. |
| `GESHTU_PROJECT` | recommended | Project slug to default into tools. Without it, the AI must pass `project` on every call; with it, just ask "what's new" and it works. |

> **Tip**: Pick a server name like `geshtu-main` (not just `geshtu`) so
> you can later add a second project as `geshtu-otherproj` without name
> collisions. Each entry under `mcpServers` is an independent connection.

For local development (`docker compose up` on your laptop without TLS):

```json
"GESHTU_API_URL": "http://localhost:8000"
```

You'll need to expose the api port — by default it's only on the docker
network. Add this to a `docker-compose.override.yml`:

```yaml
services:
  api:
    ports:
      - "127.0.0.1:8000:8000"
```

## 4. Restart Claude Desktop

Fully quit (not just close the window) and reopen. On launch the MCP
server prints a line to stderr that Claude Desktop shows in its log:

```
Geshtu MCP: connected as Alice <alice@example.com> (member) · project=main · api=https://...
```

If that line names someone you don't expect, fix the token before the
AI starts using it. You should now see six new tools — `geshtu_search`,
`geshtu_decisions`, `geshtu_digest`, `geshtu_log_decision`,
`geshtu_log_fact`, `geshtu_close_session`.

## 5. Add the team protocol to your project

Open Claude Desktop → Project → Project Instructions and paste the block
from [team-protocol.md](team-protocol.md). The Connect page in the admin
UI gives you the same block with your project slug already substituted —
fastest way is to copy from there.

## Verifying it works

Start a new conversation in your Geshtu-wired project and ask:

> What's new on this project since last week?

Claude should call `geshtu_digest` with `depth='quick'` and return a
markdown summary. If it instead says "I don't have access to project
history", check that:

- Tools are visible in the tool icon (top-right of input)
- The token isn't revoked (admin can verify on the **Tokens** page)
- `GESHTU_API_URL` reaches your server — `curl <url>/health` from a
  shell should return `{"status":"ok",...}`
- Stderr line says "connected as YOU" — if it says someone else, you
  pasted the wrong token
