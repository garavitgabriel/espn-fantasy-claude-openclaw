# OpenClaw Setup Guide

## Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (auto-installed by the script if missing)
- ESPN Fantasy Baseball account with league access

## Quick Install (Local)

```bash
git clone https://github.com/garavitgabriel/espn-api.git
cd espn-api
./install-openclaw.sh
```

The script will:
1. Install `uv` if needed
2. Install Python dependencies
3. Register the MCP server with OpenClaw
4. Copy skills to your OpenClaw workspace

## Remote Install (Railway SSE)

If the MCP server is deployed on Railway or another host:

```bash
openclaw mcp set espn-baseball '{"type": "url", "url": "https://your-app.up.railway.app/sse"}'
```

Or build a plugin bundle:

```bash
uv run espn build-plugin build --target openclaw --url https://your-app.up.railway.app/sse
openclaw plugins install ~/Desktop/espn-fantasy-openclaw-plugin.zip
```

## Authentication

ESPN requires cookies for API access. Get them from your browser:

1. Log in to [ESPN Fantasy](https://fantasy.espn.com)
2. Open DevTools > Application > Cookies
3. Copy the values of `espn_s2` and `SWID`

Then set them:

```bash
# If installed locally:
uv run espn auth token <ESPN_S2> <ESPN_SWID>

# On headless servers, use environment variables:
export ESPN_S2="your_espn_s2_cookie"
export ESPN_SWID="{your_swid}"
```

Verify with:

```bash
uv run espn auth status
```

## Tool Naming in OpenClaw

When using ESPN tools through OpenClaw, the tool names are prefixed:

| MCP Tool | OpenClaw Name |
|---|---|
| `get_my_roster` | `mcp__espn-baseball__get_my_roster` |
| `get_standings` | `mcp__espn-baseball__get_standings` |
| `get_matchup` | `mcp__espn-baseball__get_matchup` |

You don't need to use these names directly — just ask naturally:
> "Show my fantasy baseball standings"

## Troubleshooting

**"uv: command not found"**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

**"Missing ESPN credentials"**
```bash
uv run espn auth token <ESPN_S2> <ESPN_SWID>
```

**"Could not register MCP server"**
Add manually to your OpenClaw config (`~/.openclaw/openclaw.json`):
```json
{
  "mcpServers": {
    "espn-baseball": {
      "command": "uv",
      "args": ["run", "--project", "/path/to/espn-api", "espn-mcp"]
    }
  }
}
```
