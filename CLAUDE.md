# CLAUDE.md

## Project Overview

This is a fork of [cwendt94/espn-api](https://github.com/cwendt94/espn-api) extended with an **MCP server**, **CLI**, and **Claude Code plugin** for ESPN Fantasy Baseball. The league is "El Rey" (league ID 612122596), an H2H Categories format.

Works with Claude Code, Claude Desktop, Claude Cowork, and OpenClaw.

## Quick Reference

```bash
uv sync                              # Install dependencies
uv run espn auth login               # Browser login (captures cookies)
uv run espn auth token <S2> <SWID>   # Manual credential entry
uv run espn standings                # CLI command
uv run espn-mcp                      # Start MCP server (stdio)
uv run pytest                        # Run tests
```

## Architecture

```
espn-api/
├── .claude-plugin/plugin.json   # Plugin manifest (auto-discovered)
├── .mcp.json                    # MCP registration (uv run espn-mcp)
├── settings.json                # Default agent: fantasy-advisor
├── skills/                      # 8 agent-invoked skills
├── commands/                    # 5 user-invoked slash commands
├── agents/                      # fantasy-advisor agent
├── memory/                      # SQLite memory MCP server (separate package)
├── espn_api/                    # Upstream library (don't modify)
├── mcp_server/                  # MCP server + CLI (main package)
│   ├── server.py                # FastMCP: 20 tools + 5 resources
│   ├── tools.py                 # Tool definitions → register_tools(mcp)
│   ├── resources.py             # Resource definitions → register_resources(mcp)
│   ├── formatters.py            # 14 fmt_* functions (shared by tools + CLI)
│   ├── config.py                # League singleton, credential loading
│   ├── auth.py                  # ConfigManager + EspnConfig (Pydantic)
│   └── cli/                     # Typer CLI
│       ├── __init__.py          # 20 league commands + main()
│       ├── auth.py              # token, status, logout
│       └── build_plugin.py      # Plugin bundle builder
├── pyproject.toml               # uv/hatchling config, entry points
└── Dockerfile                   # Production container
```

## Key Patterns

- **Formatters are the single source of truth for output.** Both `tools.py` and `cli/` call functions in `formatters.py`. Never duplicate formatting logic.
- **config.py owns the League instance.** Always use `get_league()` and `get_my_team()` — never instantiate League directly in tools or CLI.
- **MCP tools and CLI commands are 1:1.** Every MCP tool has a matching CLI subcommand. When adding a new capability, add it to both.
- **Credentials: env vars > config file > defaults.** `ConfigManager` loads from `~/.espn-fantasy/config.json`, then applies env var overrides. Users can set credentials via `espn auth login` (browser), `espn auth token` (manual), or `.env`.
- **The plugin wraps the MCP, never replaces it.** Skills orchestrate MCP tools via markdown instructions. The standalone MCP stays stateless.
- **Memory is optional and plugin-only.** The SQLite memory server runs locally via stdio. It does NOT affect the standalone MCP. Skills degrade gracefully without memory.

## Development

```bash
uv sync --group dev     # Install with dev deps
uv run pytest           # Run tests
uv run espn --help      # CLI help
uv run espn-mcp         # Start MCP server (stdio)
```

## Plugin Development

```bash
# Test the plugin locally (auto-discovered from repo root)
claude

# Available slash commands
/espn-fantasy:standings
/espn-fantasy:roster [team_name]
/espn-fantasy:matchup [week]
/espn-fantasy:scout [position]
/espn-fantasy:refresh
```

### Plugin ↔ Skill ↔ MCP Tool Mapping

| Plugin Skill | Type | MCP Tools Used |
|-------------|------|----------------|
| `matchup-scout` | Agent-invoked | `get_standings`, `get_matchup`, `get_team_roster`, `get_my_roster` + memory |
| `free-agent-finder` | Agent-invoked | `get_scoring_categories`, `get_my_roster`, `get_roster_needs`, `get_free_agents`, `get_player_info` + memory |
| `trade-analyzer` | Agent-invoked | `get_scoring_categories`, `analyze_trade`, `get_player_info`, `get_my_roster` + memory |
| `draft-assistant` | Agent-invoked | `get_scoring_categories`, `get_roster_slots`, `get_draft_board`, `get_roster_needs`, `get_free_agents`, `get_player_info` + memory |
| `weekly-prep` | Agent-invoked | `get_standings`, `get_matchup`, `get_my_roster`, `get_team_roster`, `get_free_agents` + memory |
| `category-strategist` | Agent-invoked | `get_standings`, `get_my_roster`, `get_scoring_categories`, `get_league_rosters` + memory |
| `waiver-wire-scout` | Agent-invoked | `get_recent_activity`, `get_my_roster`, `get_scoring_categories`, `get_player_info` + memory |
| `season-outlook` | Agent-invoked | `get_standings`, `get_my_roster`, `get_scoring_categories`, `get_box_scores` + memory |

### Memory MCP Server

The memory server (`memory/`) is a local SQLite-backed MCP server with 14 tools across 6 tables: `matchup_history`, `roster_moves`, `watchlist`, `category_trends`, `draft_picks`, `preferences`. DB stored at `~/.espn-fantasy/memory.db`.

### Adding a New Skill

1. Create `skills/<skill-name>/SKILL.md` with frontmatter (`name`, `description`) and step-by-step instructions referencing MCP tool names.
2. Skills reference ESPN tools as `get_*` and memory tools as `save_*`/`get_*` from the memory server.
3. Include conditional memory steps: "If memory tools are available, call X."
4. Update the skill mapping table above.

## Environment Variables

Set via `espn auth login` (browser), `espn auth token` (manual), or `.env` (gitignored). Stored in `~/.espn-fantasy/config.json`. Env vars always override the config file.

| Variable | Purpose |
|----------|---------|
| `ESPN_S2` | ESPN auth cookie |
| `ESPN_SWID` | ESPN auth SWID |
| `ESPN_LEAGUE_ID` | League ID (default: 612122596) |
| `ESPN_YEAR` | Season year (default: 2026) |
| `ESPN_TEAM_NAME` | Partial match for your team name (default: Gabriel) |

## MCP Resources

| URI | Description |
|-----|-------------|
| `espn://workflow/season-management` | Weekly season management playbook |
| `espn://workflow/draft-day` | Auction draft day playbook |
| `espn://info/league-settings` | H2H Categories format, scoring, roster config |
| `espn://skill/matchup-scout` | Matchup analysis workflow |
| `espn://skill/free-agent-finder` | Free agent search workflow |

## Tool ↔ CLI ↔ Formatter Mapping

| MCP Tool | CLI Command | Formatter |
|----------|-------------|-----------|
| `get_my_roster` | `roster` | `fmt_roster` |
| `get_team_roster` | `roster --team X` | `fmt_roster` |
| `get_matchup` | `matchup` | `fmt_box_score` |
| `get_standings` | `standings` | `fmt_standings` |
| `get_free_agents` | `free-agents` | `fmt_free_agents` |
| `get_recent_activity` | `activity` | `fmt_activity` |
| `get_box_scores` | `box-scores` | `fmt_box_score` |
| `get_player_info` | `player` | `fmt_player_detail` |
| `compare_players` | `compare` | `fmt_compare` |
| `get_league_rosters` | `rosters` | `fmt_league_rosters` |
| `analyze_trade` | `trade` | `fmt_trade_analysis` |
| `get_scoring_categories` | `scoring` | `fmt_scoring_categories` |
| `get_roster_slots` | `slots` | `fmt_roster_slots` |
| `get_draft_board` | `draft` | `fmt_draft_board` + `fmt_roster_needs` |
| `get_roster_needs` | `needs` | `fmt_roster_needs` |
| `get_schedule` | `schedule` | `fmt_schedule` |
| `get_league_settings` | `settings` | `fmt_league_settings` |
| `search_player` | `search` | `fmt_player_search` |
| `get_scoreboard` | `scoreboard` | *(none)* |
| `refresh_data` | `refresh` | *(none — returns status string)* |
| `get_probable_pitchers` | `probable-pitchers` | `fmt_probable_pitchers` |
| `get_sp_schedule` | `sp-schedule` | `fmt_sp_schedule` |
| `get_weekly_moves` | `weekly-moves` | `fmt_weekly_moves` |
| `get_batter_vs_team` (accepts `opponent_team`) | `vs-team --opponent` | `fmt_batter_vs_team` |
| `get_recent_activity` (accepts `team_name`, `scoring_period`) | `activity --team --period` | `fmt_activity` |

## Adding a New Tool

1. Add formatter function in `formatters.py` if new output formatting is needed.
2. Add MCP tool in `tools.py` inside `register_tools()`.
3. Add `@app.command()` in `cli/__init__.py`.
4. Update the tool mapping table above and in `README.md`.

## Agent Workflows

When the user asks about their fantasy baseball league, use the MCP tools in this order:

1. **Situational awareness first** — Start with `get_standings` and `get_my_roster` to understand the current state before making recommendations.
2. **Scouting** — Use `get_free_agents` (filter by position if the user has a gap) and `get_league_rosters` to find trade targets.
3. **Evaluation** — Use `compare_players` for head-to-head comparisons and `analyze_trade` before recommending any moves.
4. **Live games** — Use `get_matchup` during the season to check the current week's H2H category breakdown. Use `get_box_scores` for a league-wide view.
5. **Refresh** — Call `refresh_data` if the user says scores seem stale or asks for the latest.

The league uses **H2H Categories** (not points). Advice should focus on winning individual stat categories, not total points. When analyzing trades, consider category impact — not just point differential.

### Draft Day Workflow

The league uses **AUCTION** draft ($280 budget per team). When assisting during draft:

1. **Start with context** — Call `get_scoring_categories` + `get_roster_slots` to understand what categories matter and what positions need filling.
2. **Track the draft** — Call `refresh_data` then `get_draft_board` to see picks so far, prices paid, and remaining budgets per team. Spot teams running low on cash.
3. **Know what you need** — Call `get_roster_needs` to see which positions are still empty. Prioritize scarce positions (C, SS have only 1 slot each).
4. **Scout picks** — Use `get_free_agents` filtered by needed positions and `get_player_info` / `compare_players` to evaluate targets.
5. **Value by category** — Don't just rank by total points. The 14 categories are: AVG, HR, OPS, R, RBI, SB, B_SO (lower wins) | WHIP (lower wins), ERA (lower wins), K, W, L (lower wins), SV, HLD. Target players who help in categories you're weakest in.
6. **Budget strategy** — With $280 and ~20 active slots, average cost is ~$14/player. Stars go for $40-60+. Track opponent budgets to know when you can win players cheaply late.

## Building Plugin Bundles

```bash
# For Claude Cowork (requires deployed SSE URL)
uv run espn build-plugin build --target claude --url https://your-app.up.railway.app/sse

# For OpenClaw (local)
uv run espn build-plugin build --target openclaw

# Without memory server
uv run espn build-plugin build --target openclaw --no-memory
```

## Gotchas

- The `espn_api` baseball module uses H2H Categories scoring. Box scores have `home_stats`/`away_stats` dicts with per-category breakdowns — not simple point totals.
- `league.player_info()` can return a single Player or a list. Always handle both cases.
- `league.free_agents()` accepts `position` as a string (e.g., "SS"), not the numeric ESPN position ID.
- The `.mcp.json` uses `uv run` — requires [uv](https://docs.astral.sh/uv/) to be installed.
