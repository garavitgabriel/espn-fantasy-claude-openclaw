# CLAUDE.md

## Project Overview

This is a fork of [cwendt94/espn-api](https://github.com/cwendt94/espn-api) extended with an **MCP server** and **CLI** for ESPN Fantasy Baseball. The league is "El Rey" (league ID 612122596), an H2H Categories format.

## Architecture

- **espn_api/** — Upstream library. Avoid modifying unless fixing upstream bugs.
- **mcp_server/** — Our code. All new features go here.
  - `config.py` — Loads `.env`, creates the League singleton, resolves the user's team by `ESPN_TEAM_NAME`. Validates credentials on first use.
  - `formatters.py` — Pure functions that turn espn_api objects into markdown tables. Shared by both MCP tools and CLI. Contains 14 `fmt_*` functions.
  - `tools.py` — 16 MCP tool definitions registered on the FastMCP server. Thin wrappers: fetch data via `config.py`, format via `formatters.py`.
  - `cli.py` — Argparse CLI with 16 subcommands. Same logic as tools.py but invoked from the terminal.
  - `server.py` — FastMCP server entry point (stdio transport).
  - `__main__.py` — Allows `python -m mcp_server` to start the server.

## Key Patterns

- **Formatters are the single source of truth for output.** Both `tools.py` and `cli.py` call functions in `formatters.py`. Never duplicate formatting logic.
- **config.py owns the League instance.** Always use `get_league()` and `get_my_team()` — never instantiate League directly in tools or CLI.
- **MCP tools and CLI commands are 1:1.** Every MCP tool has a matching CLI subcommand. When adding a new capability, add it to both.

## Development

```bash
# Activate the venv (required — dependencies are here)
source venv/bin/activate

# Run CLI
python -m mcp_server.cli standings

# Run MCP server directly (for testing)
python -m mcp_server.server

# Run tests
pytest
```

## Environment Variables

Stored in `.env` (gitignored). Required:

| Variable | Purpose |
|----------|---------|
| `ESPN_S2` | ESPN auth cookie |
| `ESPN_SWID` | ESPN auth SWID |
| `ESPN_LEAGUE_ID` | League ID (default: 612122596) |
| `ESPN_YEAR` | Season year (default: 2026) |
| `ESPN_TEAM_NAME` | Partial match for your team name (default: Gabriel) |

## Tool ↔ CLI ↔ Formatter Mapping

| MCP Tool | CLI Command | Formatter |
|----------|-------------|-----------|
| `get_my_roster` | `roster` | `fmt_roster` |
| `get_team_roster` | `team-roster` | `fmt_roster` |
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
| `refresh_data` | `refresh` | *(none — returns status string)* |

## Adding a New Tool

1. Add formatter function in `formatters.py` if new output formatting is needed.
2. Add MCP tool in `tools.py` inside `register_tools()`.
3. Add CLI subcommand in `cli.py` — new `cmd_*` function + argparse subparser + dispatch entry.
4. Update the CLI commands table in `README.md`.

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

## Gotchas

- The `espn_api` baseball module uses H2H Categories scoring. Box scores have `home_stats`/`away_stats` dicts with per-category breakdowns — not simple point totals.
- `league.player_info()` can return a single Player or a list. Always handle both cases.
- `league.free_agents()` accepts `position` as a string (e.g., "SS"), not the numeric ESPN position ID.
- The `.mcp.json` uses an absolute path to the venv Python. If the venv moves, update it.
