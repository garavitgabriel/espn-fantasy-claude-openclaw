# ESPN Fantasy Baseball API + MCP Server + CLI

A Python toolkit for ESPN Fantasy Baseball built on top of [cwendt94/espn-api](https://github.com/cwendt94/espn-api). Includes the upstream library, an **MCP server** for AI-assisted league management via Claude Code, and a **CLI** for quick terminal queries.

## What's Included

| Layer | Description |
|-------|-------------|
| **espn_api/** | Upstream ESPN Fantasy API library (Football, Basketball, Hockey, Baseball) |
| **mcp_server/** | MCP server exposing 16 baseball tools to Claude Code |
| **mcp_server/cli.py** | Standalone CLI mirroring the same 16 tools |

## Quick Start

### 1. Clone & install

```bash
git clone https://github.com/YOUR_USER/espn-api
cd espn-api
python -m venv venv
source venv/bin/activate
pip install -r requirementsV2.txt
pip install mcp python-dotenv
```

### 2. Configure credentials

Copy the example env file and fill in your ESPN credentials:

```bash
cp .env.example .env
```

```env
ESPN_S2=your_espn_s2_cookie
ESPN_SWID={your_swid}
ESPN_LEAGUE_ID=612122596
ESPN_YEAR=2026
ESPN_TEAM_ID=
ESPN_TEAM_NAME=Gabriel
```

`ESPN_TEAM_ID` is the highest-priority resolver for tools that operate on "my team" and is the most reliable option. If `ESPN_TEAM_ID` is unset, the server falls back to `ESPN_TEAM_NAME` using normalized matching in this order: exact team-name match, partial team-name match, exact owner-name match, then partial owner-name match.

To find your `ESPN_S2` and `ESPN_SWID` cookies, log in to ESPN Fantasy, open browser DevTools > Application > Cookies, and copy the values.

### 3. Use the CLI

```bash
source venv/bin/activate

python -m mcp_server.cli standings
python -m mcp_server.cli roster
python -m mcp_server.cli matchup
python -m mcp_server.cli free-agents --position SS --size 10
python -m mcp_server.cli player "Shohei Ohtani"
python -m mcp_server.cli compare "Shohei Ohtani" "Aaron Judge"
python -m mcp_server.cli trade --give "Player A" --receive "Player B"

# Draft day tools
python -m mcp_server.cli scoring
python -m mcp_server.cli slots
python -m mcp_server.cli draft
python -m mcp_server.cli needs

python -m mcp_server.cli --help
```

### 4. Use with Claude Code (MCP)

The `.mcp.json` at the project root registers the server. Claude Code picks it up automatically when you open the project. All 16 tools become available as natural-language actions in conversation.

To run the MCP server manually:

```bash
python -m mcp_server.server
# or equivalently:
python -m mcp_server
```

## CLI Commands

| Command | Args | Description |
|---------|------|-------------|
| `roster` | — | Show my team's roster |
| `team-roster` | `TEAM_NAME` | Show any team's roster (normalized exact match first, then partial) |
| `matchup` | `--week N` | My current matchup (category breakdown) |
| `standings` | — | League standings by rank |
| `free-agents` | `--position POS --size N` | Best available free agents |
| `activity` | `--size N` | Recent league transactions |
| `box-scores` | `--week N` | All matchup box scores |
| `player` | `NAME` | Detailed player stats |
| `compare` | `PLAYER1 PLAYER2` | Side-by-side player comparison |
| `rosters` | — | Overview of all league rosters |
| `trade` | `--give "A,B" --receive "C,D"` | Evaluate a potential trade |
| `scoring` | — | Show league's H2H scoring categories |
| `slots` | — | Show roster slot configuration |
| `draft` | — | Show draft board, auction prices & budgets |
| `needs` | — | Show my unfilled roster positions |
| `refresh` | — | Pull latest data from ESPN |

## Project Structure

```
espn-api/
├── espn_api/              # Upstream ESPN Fantasy API library
│   ├── baseball/          # Baseball-specific models & league logic
│   ├── football/          # Football API
│   ├── basketball/        # Basketball API
│   ├── hockey/            # Hockey API
│   └── base_league.py     # Shared base class
├── mcp_server/            # Our MCP server + CLI layer
│   ├── __main__.py        # Allows `python -m mcp_server` to start the server
│   ├── server.py          # FastMCP server entry point (stdio/sse/streamable-http)
│   ├── tools.py           # 16 MCP tool definitions
│   ├── formatters.py      # Shared markdown table formatters
│   ├── config.py          # League connection & env config
│   └── cli.py             # Argparse CLI (same 16 commands)
├── tests/                 # Upstream test suite
├── .env                   # ESPN credentials (gitignored)
├── .mcp.json              # Claude Code MCP server registration
├── railway.json           # Railway deployment config
├── Procfile               # Railway process definition
├── requirements-deploy.txt # Deployment dependencies
└── README.md
```

## MCP Server Tools

The MCP server exposes these tools to Claude Code:

- **get_my_roster** — Your team's full roster with stats and injury status
- **get_team_roster** — Any team's roster by name
- **get_matchup** — Current or specific week matchup with H2H category breakdown
- **get_standings** — League standings sorted by rank
- **get_free_agents** — Best available players, filterable by position
- **get_recent_activity** — Recent adds, drops, and trades
- **get_box_scores** — All matchup scores for a week
- **get_player_info** — Detailed stats for any player
- **compare_players** — Side-by-side player comparison
- **get_league_rosters** — Overview of all teams' rosters
- **analyze_trade** — Evaluate a trade by comparing give vs receive
- **get_scoring_categories** — League's H2H categories with direction (higher/lower wins)
- **get_roster_slots** — Roster slot configuration (positions and counts)
- **get_draft_board** — Draft picks, auction prices, team budgets, and roster needs
- **get_roster_needs** — Which positions you still need to fill
- **refresh_data** — Pull latest data from ESPN

## Transports

The server supports three MCP transports, controlled by the `MCP_TRANSPORT` environment variable:

| Transport | Use Case | Default Port |
|-----------|----------|--------------|
| `stdio` | Local — Claude Code, IDE plugins (default) | N/A |
| `sse` | Remote — Railway, any HTTP client | 8000 |
| `streamable-http` | Remote — newer MCP clients | 8000 |

```bash
# Local (default)
python -m mcp_server.server

# Remote / deployed
MCP_TRANSPORT=sse python -m mcp_server.server
```

## Deploy to Railway

Railway runs the server as a persistent process with SSE transport so any remote MCP client can connect over HTTPS.

### 1. Create a GitHub repo and push

```bash
git remote add origin https://github.com/YOUR_USER/espn-baseball-mcp.git
git push -u origin master
```

### 2. Deploy on Railway

1. Go to [railway.com](https://railway.com) and create a new project
2. Select **"Deploy from GitHub Repo"** and pick your repo
3. Railway auto-detects Python via `requirements-deploy.txt`
4. Add environment variables in the Railway dashboard:

```
ESPN_S2=your_espn_s2_cookie
ESPN_SWID={your_swid}
ESPN_LEAGUE_ID=612122596
ESPN_YEAR=2026
ESPN_TEAM_ID=
ESPN_TEAM_NAME=Gabriel
MCP_TRANSPORT=sse
```

5. Railway assigns a public URL like `https://espn-baseball-mcp-production.up.railway.app`

### 3. Connect from any MCP client

Once deployed, the SSE endpoint is at:

```
https://your-app.up.railway.app/sse
```

## Using with Other MCP Clients

### Local (stdio) — Claude Code, Cursor, Windsurf

For local use, the client spawns the server as a subprocess. Add to your MCP config:

```json
{
  "mcpServers": {
    "espn-baseball": {
      "command": "/path/to/espn-api/venv/bin/python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/path/to/espn-api"
    }
  }
}
```

Config file locations:
- **Claude Code:** `.mcp.json` in the project root (already included)
- **Claude Desktop:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Cursor / Windsurf:** Check your IDE's MCP documentation for the config path

### Remote (SSE) — Deployed server

For a deployed Railway instance, point your client at the SSE URL:

```json
{
  "mcpServers": {
    "espn-baseball": {
      "url": "https://your-app.up.railway.app/sse"
    }
  }
}
```

### Programmatic (Python)

**Local (stdio):**

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="/path/to/espn-api/venv/bin/python",
    args=["-m", "mcp_server.server"],
    cwd="/path/to/espn-api",
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool("get_standings", {})
        print(result)
```

**Remote (SSE):**

```python
from mcp import ClientSession
from mcp.client.sse import sse_client

async with sse_client("https://your-app.up.railway.app/sse") as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        tools = await session.list_tools()
        result = await session.call_tool("get_standings", {})
        print(result)
```

## Upstream ESPN API

For documentation on the underlying `espn_api` library (all sports), see the [upstream wiki](https://github.com/cwendt94/espn-api/wiki).

```python
from espn_api.baseball import League

league = League(league_id=612122596, year=2026, espn_s2="...", swid="...")
print(league.standings())
```

## Running Tests

```bash
pytest
```

## License

Based on [cwendt94/espn-api](https://github.com/cwendt94/espn-api). See upstream repository for license details.
