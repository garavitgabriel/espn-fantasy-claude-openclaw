"""ESPN Fantasy Baseball memory MCP server.

Local-only (stdio) server backed by SQLite. Provides persistent
cross-session memory for the ESPN Fantasy Baseball plugin.
"""

import json

from mcp.server.fastmcp import FastMCP

import repos

mcp = FastMCP(
    name="espn-memory",
    instructions=(
        "Memory tools for the ESPN Fantasy Baseball plugin. "
        "Use these to persist and recall matchup results, roster moves, "
        "player watchlists, category trends, draft picks, and user preferences "
        "across sessions."
    ),
)


# ---------------------------------------------------------------------------
# Matchup History
# ---------------------------------------------------------------------------

@mcp.tool()
async def save_matchup_result(
    week: int,
    season: int,
    opponent_team: str,
    my_wins: int,
    my_losses: int,
    ties: int = 0,
    categories_won: str = "[]",
    categories_lost: str = "[]",
    notes: str = "",
) -> str:
    """Record a weekly matchup result with category breakdown.

    Args:
        week: Matchup week number
        season: Season year (e.g. 2026)
        opponent_team: Opponent team name
        my_wins: Number of categories won
        my_losses: Number of categories lost
        ties: Number of tied categories
        categories_won: JSON array of category names won (e.g. '["HR","RBI","SB"]')
        categories_lost: JSON array of category names lost (e.g. '["ERA","WHIP"]')
        notes: Optional notes about the matchup
    """
    won = json.loads(categories_won) if isinstance(categories_won, str) else categories_won
    lost = json.loads(categories_lost) if isinstance(categories_lost, str) else categories_lost
    return await repos.save_matchup(
        week, season, opponent_team, my_wins, my_losses, ties, won, lost, notes
    )


@mcp.tool()
async def get_matchup_history(
    season: int | None = None,
    opponent: str | None = None,
    week: int | None = None,
) -> str:
    """Query past matchup results. Filter by season, opponent, or week.

    Args:
        season: Filter by season year
        opponent: Filter by opponent team name (partial match)
        week: Filter by specific week number
    """
    results = await repos.get_matchups(season, opponent, week)
    if not results:
        return "No matchup history found."
    lines = []
    for m in results:
        cats_won = m.get("categories_won", [])
        cats_lost = m.get("categories_lost", [])
        line = (
            f"Week {m['week']} ({m['season']}): vs {m['opponent_team']} — "
            f"{m['my_wins']}-{m['my_losses']}-{m['ties']}"
        )
        if cats_won:
            line += f" | Won: {', '.join(cats_won)}"
        if cats_lost:
            line += f" | Lost: {', '.join(cats_lost)}"
        if m.get("notes"):
            line += f" | {m['notes']}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Roster Moves
# ---------------------------------------------------------------------------

@mcp.tool()
async def save_roster_move(
    season: int,
    action: str,
    player_name: str,
    position: str = "",
    notes: str = "",
) -> str:
    """Log a roster transaction (add, drop, or trade).

    Args:
        season: Season year
        action: Transaction type: ADD, DROP, TRADE_SEND, or TRADE_RECEIVE
        player_name: Player name
        position: Player position (e.g. SS, SP)
        notes: Optional context about why the move was made
    """
    return await repos.save_roster_move(season, action, player_name, position, notes)


@mcp.tool()
async def get_roster_moves(
    season: int | None = None,
    player: str | None = None,
    action: str | None = None,
    limit: int = 50,
) -> str:
    """Query roster transaction log. Filter by season, player, or action type.

    Args:
        season: Filter by season year
        player: Filter by player name (partial match)
        action: Filter by action type: ADD, DROP, TRADE_SEND, TRADE_RECEIVE
        limit: Max results to return (default 50)
    """
    moves = await repos.get_roster_moves(season, player, action, limit)
    if not moves:
        return "No roster moves found."
    lines = []
    for m in moves:
        line = f"{m['moved_at']}: {m['action']} {m['player_name']}"
        if m.get("position"):
            line += f" ({m['position']})"
        if m.get("notes"):
            line += f" — {m['notes']}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

@mcp.tool()
async def add_to_watchlist(
    player_name: str,
    position: str = "",
    reason: str = "",
) -> str:
    """Add a player to the watchlist for tracking.

    Args:
        player_name: Player name
        position: Player position
        reason: Why this player is being watched
    """
    return await repos.add_watchlist(player_name, position, reason)


@mcp.tool()
async def remove_from_watchlist(player_name: str) -> str:
    """Remove a player from the watchlist.

    Args:
        player_name: Player name (partial match)
    """
    return await repos.remove_watchlist(player_name)


@mcp.tool()
async def get_watchlist() -> str:
    """Get all players currently on the watchlist."""
    items = await repos.get_watchlist()
    if not items:
        return "Watchlist is empty."
    lines = []
    for w in items:
        line = f"- {w['player_name']}"
        if w.get("position"):
            line += f" ({w['position']})"
        if w.get("reason"):
            line += f" — {w['reason']}"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Category Trends
# ---------------------------------------------------------------------------

@mcp.tool()
async def save_category_trend(
    season: int,
    week: int,
    category: str,
    strength: str,
    value: float | None = None,
) -> str:
    """Record a category strength assessment for a given week.

    Args:
        season: Season year
        week: Week number
        category: Stat category name (e.g. HR, ERA, WHIP, SB)
        strength: Assessment: STRONG, AVERAGE, or WEAK
        value: Optional numeric value for the category
    """
    return await repos.save_category_trend(season, week, category, strength, value)


@mcp.tool()
async def get_category_trends(
    season: int | None = None,
    category: str | None = None,
    last_n_weeks: int | None = None,
) -> str:
    """Query category strength trends over time.

    Args:
        season: Filter by season year
        category: Filter by specific category name
        last_n_weeks: Limit to most recent N weeks of data
    """
    trends = await repos.get_category_trends(season, category, last_n_weeks)
    if not trends:
        return "No category trends recorded."
    lines = []
    for t in trends:
        line = f"Week {t['week']} ({t['season']}): {t['category']} = {t['strength']}"
        if t.get("value") is not None:
            line += f" ({t['value']})"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Draft Picks
# ---------------------------------------------------------------------------

@mcp.tool()
async def save_draft_pick(
    season: int,
    player_name: str,
    position: str = "",
    bid_amount: float | None = None,
    round_num: int | None = None,
    pick: int | None = None,
    keeper: bool = False,
) -> str:
    """Record a draft pick with auction price.

    Args:
        season: Season year
        player_name: Player drafted
        position: Player position
        bid_amount: Auction bid amount in dollars
        round_num: Draft round (for snake drafts)
        pick: Pick number within round
        keeper: Whether this was a keeper pick
    """
    return await repos.save_draft_pick(
        season, player_name, position, bid_amount, round_num, pick, keeper
    )


@mcp.tool()
async def get_draft_picks(season: int | None = None) -> str:
    """Query draft pick history.

    Args:
        season: Filter by season year
    """
    picks = await repos.get_draft_picks(season)
    if not picks:
        return "No draft picks recorded."
    lines = []
    for p in picks:
        line = f"{p['player_name']}"
        if p.get("position"):
            line += f" ({p['position']})"
        if p.get("bid_amount") is not None:
            line += f" — ${p['bid_amount']}"
        if p.get("keeper"):
            line += " [KEEPER]"
        lines.append(line)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

@mcp.tool()
async def set_preference(key: str, value: str) -> str:
    """Set a user preference (e.g. punt categories, favorite positions).

    Args:
        key: Preference key (e.g. 'punt_categories', 'draft_strategy', 'favorite_positions')
        value: Preference value (use JSON for complex values)
    """
    return await repos.set_preference(key, value)


@mcp.tool()
async def get_preferences() -> str:
    """Get all saved user preferences."""
    prefs = await repos.get_preferences()
    if not prefs:
        return "No preferences saved."
    lines = [f"- {k}: {v}" for k, v in prefs.items()]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Full Context
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_full_context(season: int | None = None) -> str:
    """Get a combined snapshot of all memory: matchup history, recent roster moves,
    watchlist, category trends, and preferences. Call this at the start of a session
    to load prior context.

    Args:
        season: Filter matchups, moves, and trends by season year
    """
    ctx = await repos.get_full_context(season)

    sections = []

    if ctx["matchup_history"]:
        section = "## Matchup History\n"
        for m in ctx["matchup_history"][:10]:
            section += (
                f"- Week {m['week']} vs {m['opponent_team']}: "
                f"{m['my_wins']}-{m['my_losses']}-{m['ties']}\n"
            )
        sections.append(section)

    if ctx["recent_roster_moves"]:
        section = "## Recent Roster Moves\n"
        for m in ctx["recent_roster_moves"][:10]:
            section += f"- {m['action']} {m['player_name']}"
            if m.get("position"):
                section += f" ({m['position']})"
            section += f" — {m['moved_at']}\n"
        sections.append(section)

    if ctx["watchlist"]:
        section = "## Watchlist\n"
        for w in ctx["watchlist"]:
            section += f"- {w['player_name']}"
            if w.get("reason"):
                section += f" — {w['reason']}"
            section += "\n"
        sections.append(section)

    if ctx["category_trends"]:
        section = "## Category Trends (Recent)\n"
        # Group by most recent week
        seen_cats: set[str] = set()
        for t in ctx["category_trends"]:
            if t["category"] not in seen_cats:
                section += f"- {t['category']}: {t['strength']}"
                if t.get("value") is not None:
                    section += f" ({t['value']})"
                section += f" (week {t['week']})\n"
                seen_cats.add(t["category"])
        sections.append(section)

    if ctx["preferences"]:
        section = "## Preferences\n"
        for k, v in ctx["preferences"].items():
            section += f"- {k}: {v}\n"
        sections.append(section)

    if not sections:
        return "No memory data yet. This is a fresh session — memory will build up as you use the tools."

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run(transport="stdio")
