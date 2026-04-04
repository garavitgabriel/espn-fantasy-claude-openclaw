# ESPN Fantasy Baseball — MCP Plugin for Claude

A Python toolkit for ESPN Fantasy Baseball built on [cwendt94/espn-api](https://github.com/cwendt94/espn-api). Includes an **MCP server** (16 tools + 5 resources), a **Typer CLI**, **8 skills**, a **memory system**, and a **Claude Code plugin** — all for H2H Categories league management.

Works with **Claude Code**, **Claude Desktop**, **Claude Cowork**, and **OpenClaw**.

## Quick Start

### Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- ESPN Fantasy Baseball account

### Setup

```bash
git clone https://github.com/garavitgabriel/espn-api.git
cd espn-api
uv sync
```

### Authenticate

**Option A — Browser login (easiest):**

```bash
uv sync --extra browser              # first time only
uv run playwright install chromium   # first time only
uv run espn auth login
```

A browser opens, you log in to ESPN, and cookies are captured automatically.

**Option B — Manual token:**

Get your cookies from ESPN Fantasy > DevTools > Application > Cookies, then:

```bash
uv run espn auth token <ESPN_S2> <ESPN_SWID>
```

**Option C — `.env` file:**

```bash
cp .env.example .env   # edit with your values
```

### Activate

| Platform | How |
|---|---|
| **Claude Code** | Open the project — auto-discovered via `.claude-plugin/` |
| **Claude Desktop** | Add to `claude_desktop_config.json` (see below) |
| **Claude Cowork** | `uv run espn build-plugin build --target claude --url <SSE_URL>`, upload zip |
| **OpenClaw** | `./install-openclaw.sh` (see [docs/openclaw-setup.md](docs/openclaw-setup.md)) |

<details>
<summary>Claude Desktop config</summary>

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

File location: `~/Library/Application Support/Claude/claude_desktop_config.json`
</details>

## CLI

```bash
uv run espn standings
uv run espn roster
uv run espn matchup --week 5
uv run espn free-agents --position SS --size 10
uv run espn player "Shohei Ohtani"
uv run espn compare "Shohei Ohtani" "Aaron Judge"
uv run espn trade --give "Player A" --receive "Player B"

# Draft day
uv run espn scoring
uv run espn slots
uv run espn draft
uv run espn needs

# Auth
uv run espn auth login                        # browser login
uv run espn auth token <ESPN_S2> <ESPN_SWID>  # manual token
uv run espn auth status
uv run espn auth logout

# Plugin bundle
uv run espn build-plugin build --target openclaw
uv run espn build-plugin build --target claude --url https://your-app.up.railway.app/sse

uv run espn --help
```

## MCP Tools (16)

<details>
<summary>Full tool reference</summary>

| Tool | Description |
|---|---|
| `get_my_roster` | Your team's full roster with stats and injury status |
| `get_team_roster` | Any team's roster by name |
| `get_matchup` | Current or specific week matchup with H2H category breakdown |
| `get_standings` | League standings sorted by rank |
| `get_free_agents` | Best available players, filterable by position |
| `get_recent_activity` | Recent adds, drops, and trades |
| `get_box_scores` | All matchup scores for a week |
| `get_player_info` | Detailed stats for any player |
| `compare_players` | Side-by-side player comparison |
| `get_league_rosters` | Overview of all teams' rosters |
| `analyze_trade` | Evaluate a trade by comparing give vs receive |
| `get_scoring_categories` | League's H2H categories with direction |
| `get_roster_slots` | Roster slot configuration |
| `get_draft_board` | Draft picks, auction prices, team budgets |
| `get_roster_needs` | Which positions you still need to fill |
| `refresh_data` | Pull latest data from ESPN |
</details>

## MCP Resources (5)

| Resource URI | Description |
|---|---|
| `espn://workflow/season-management` | Weekly season management playbook |
| `espn://workflow/draft-day` | Auction draft day playbook |
| `espn://info/league-settings` | H2H Categories format, scoring, roster config |
| `espn://skill/matchup-scout` | Matchup analysis workflow |
| `espn://skill/free-agent-finder` | Free agent search workflow |

## Skills (8)

| Skill | Description |
|---|---|
| `matchup-scout` | Analyze your H2H matchup and find advantages |
| `free-agent-finder` | Find the best available players for your needs |
| `trade-analyzer` | Evaluate trade proposals with category impact |
| `draft-assistant` | Auction draft guidance and budget strategy |
| `weekly-prep` | Full weekly preparation workflow |
| `category-strategist` | Optimize your category standings |
| `waiver-wire-scout` | Monitor league activity for opportunities |
| `season-outlook` | Big-picture season analysis and trends |

## Project Structure

```
espn-api/
├── .claude-plugin/        # Plugin manifest (auto-discovered by Claude Code)
├── .mcp.json              # MCP server registration (uv run)
├── skills/                # 8 agent-invoked skills
├── commands/              # 5 user-invoked slash commands
├── agents/                # fantasy-advisor agent
├── memory/                # SQLite memory MCP server (cross-session)
├── espn_api/              # Upstream ESPN Fantasy API library
├── mcp_server/            # MCP server + CLI
│   ├── server.py          # FastMCP server (16 tools + 5 resources)
│   ├── tools.py           # Tool definitions
│   ├── resources.py       # MCP resource definitions
│   ├── formatters.py      # Shared markdown table formatters
│   ├── config.py          # League connection & config
│   ├── auth.py            # ConfigManager + credential storage
│   └── cli/               # Typer CLI
│       ├── __init__.py    # 16 league commands
│       ├── auth.py        # token, status, logout
│       └── build_plugin.py # Plugin bundle builder
├── tests/                 # Test suite
├── pyproject.toml         # uv/hatchling package config
├── Dockerfile             # Production container
└── install-openclaw.sh    # OpenClaw one-command installer
```

## Transports

| Transport | Use Case | Default Port |
|---|---|---|
| `stdio` | Local — Claude Code, Desktop, IDE plugins (default) | N/A |
| `sse` | Remote — Railway, Cowork, any HTTP client | 8000 |
| `streamable-http` | Remote — newer MCP clients | 8000 |

```bash
# Local (default)
uv run espn-mcp

# Remote
MCP_TRANSPORT=sse uv run espn-mcp
```

## Deploy to Railway

The project includes a `Dockerfile` and `railway.json` for one-click deployment.

### 1. Create the service

1. Push to GitHub
2. Go to [railway.com](https://railway.com) > New Project > Deploy from GitHub Repo
3. Select your fork

### 2. Set environment variables

In the Railway dashboard, add these variables to your service:

| Variable | Value |
|---|---|
| `ESPN_S2` | Your ESPN `espn_s2` cookie |
| `ESPN_SWID` | Your ESPN `SWID` cookie (include `{}`curly braces) |
| `ESPN_LEAGUE_ID` | Your league ID (default: `612122596`) |
| `ESPN_YEAR` | Season year (default: `2026`) |
| `ESPN_TEAM_NAME` | Partial match for your team name |

> `MCP_TRANSPORT=sse` is already baked into the Dockerfile — no need to set it manually.

### 3. Deploy

Railway auto-builds from the Dockerfile. The `railway.json` configures:
- **Build**: Dockerfile (uv + Python 3.12, layer-cached deps)
- **Start command**: `/app/.venv/bin/python -m mcp_server.server` — uses the venv Python directly (required because Railway may override the Dockerfile CMD)
- **Healthcheck**: `GET /health` with a 60s retry window
- **Restart policy**: on failure, up to 3 retries

### 4. Connect

Once deployed, your endpoints are:

| Endpoint | URL |
|---|---|
| **SSE** | `https://your-app.up.railway.app/sse` |
| **Health** | `https://your-app.up.railway.app/health` |

Use the SSE URL in Claude Desktop, Cowork, or any MCP client:

```json
{
  "mcpServers": {
    "espn-baseball": {
      "type": "url",
      "url": "https://your-app.up.railway.app/sse"
    }
  }
}
```

> **Note**: The `startCommand` in `railway.json` is critical. Railway's Dockerfile builder may ignore the `CMD` instruction and use a dashboard-configured command instead. The explicit `startCommand` ensures the venv Python (with all dependencies) is always used.

## Development

```bash
uv sync --group dev
uv run pytest
uv run espn --help
uv run espn-mcp  # Start MCP server locally
```

## Upstream API

For documentation on the underlying `espn_api` library, see the [upstream wiki](https://github.com/cwendt94/espn-api/wiki).

## License

Based on [cwendt94/espn-api](https://github.com/cwendt94/espn-api). See upstream repository for license details.
