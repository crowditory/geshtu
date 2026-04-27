# Claude Desktop setup

## 1. Get a token

Ask your admin to add you in the Geshtu admin UI. They'll send you a token
that looks like:

```
tk_eyJhbGciOiJIUzI1NiIs...
```

## 2. Find your config file

| OS       | Path                                                              |
|----------|-------------------------------------------------------------------|
| macOS    | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows  | `%APPDATA%\Claude\claude_desktop_config.json`                     |
| Linux    | `~/.config/Claude/claude_desktop_config.json`                     |

## 3. Add the Geshtu MCP server

If your team self-hosts Geshtu at `http://memory.example.com:3000`:

```json
{
  "mcpServers": {
    "geshtu": {
      "command": "npx",
      "args": ["-y", "@geshtu/mcp"],
      "env": {
        "GESHTU_TOKEN": "tk_paste-your-token-here",
        "API_URL": "http://memory.example.com:8000"
      }
    }
  }
}
```

For local development (`docker compose up` on your laptop), `API_URL` is
`http://localhost:8000`.

## 4. Restart Claude Desktop

Fully quit (not just close the window) and reopen. You should now see six
new tools available — `geshtu_search`, `geshtu_decisions`, `geshtu_digest`,
`geshtu_log_decision`, `geshtu_log_fact`, `geshtu_close_session`.

## 5. Add the team protocol to your project

Open Claude Desktop → Project → Project Instructions and paste the block
from [team-protocol.md](team-protocol.md), replacing `{{PROJECT_SLUG}}`
with your project's slug.

## Verifying it works

Start a new conversation in your Geshtu-wired project and ask:

> What's new on this project since last week?

Claude should call `geshtu_digest` with `depth='quick'` and return a
markdown summary. If it instead says "I don't have access to project
history", check that:

- Tools are visible in the tool icon (top-right of input)
- The token isn't revoked (admin can verify)
- `API_URL` reaches your server (try `curl $API_URL/health` from your laptop)
