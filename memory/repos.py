"""Repository functions for each memory domain."""

import json

import aiosqlite

from db import get_connection


# ---------------------------------------------------------------------------
# Matchup History
# ---------------------------------------------------------------------------

async def save_matchup(
    week: int,
    season: int,
    opponent_team: str,
    my_wins: int,
    my_losses: int,
    ties: int = 0,
    categories_won: list[str] | None = None,
    categories_lost: list[str] | None = None,
    notes: str = "",
) -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT OR REPLACE INTO matchup_history
               (week, season, opponent_team, my_wins, my_losses, ties,
                categories_won, categories_lost, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                week, season, opponent_team, my_wins, my_losses, ties,
                json.dumps(categories_won or []),
                json.dumps(categories_lost or []),
                notes,
            ),
        )
        await conn.commit()
        return f"Saved matchup: Week {week} vs {opponent_team} ({my_wins}-{my_losses}-{ties})"
    finally:
        await conn.close()


async def get_matchups(
    season: int | None = None,
    opponent: str | None = None,
    week: int | None = None,
) -> list[dict]:
    conn = await get_connection()
    try:
        query = "SELECT * FROM matchup_history WHERE 1=1"
        params: list = []
        if season is not None:
            query += " AND season = ?"
            params.append(season)
        if opponent is not None:
            query += " AND opponent_team LIKE ?"
            params.append(f"%{opponent}%")
        if week is not None:
            query += " AND week = ?"
            params.append(week)
        query += " ORDER BY season DESC, week DESC"

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Roster Moves
# ---------------------------------------------------------------------------

async def save_roster_move(
    season: int,
    action: str,
    player_name: str,
    position: str = "",
    notes: str = "",
) -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO roster_moves (season, action, player_name, position, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (season, action.upper(), player_name, position, notes),
        )
        await conn.commit()
        return f"Logged roster move: {action.upper()} {player_name}"
    finally:
        await conn.close()


async def get_roster_moves(
    season: int | None = None,
    player: str | None = None,
    action: str | None = None,
    limit: int = 50,
) -> list[dict]:
    conn = await get_connection()
    try:
        query = "SELECT * FROM roster_moves WHERE 1=1"
        params: list = []
        if season is not None:
            query += " AND season = ?"
            params.append(season)
        if player is not None:
            query += " AND player_name LIKE ?"
            params.append(f"%{player}%")
        if action is not None:
            query += " AND action = ?"
            params.append(action.upper())
        query += " ORDER BY moved_at DESC LIMIT ?"
        params.append(limit)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Watchlist
# ---------------------------------------------------------------------------

async def add_watchlist(player_name: str, position: str = "", reason: str = "") -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT OR REPLACE INTO watchlist (player_name, position, reason)
               VALUES (?, ?, ?)""",
            (player_name, position, reason),
        )
        await conn.commit()
        return f"Added {player_name} to watchlist"
    finally:
        await conn.close()


async def remove_watchlist(player_name: str) -> str:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "DELETE FROM watchlist WHERE player_name LIKE ?",
            (f"%{player_name}%",),
        )
        await conn.commit()
        if cursor.rowcount > 0:
            return f"Removed {player_name} from watchlist"
        return f"{player_name} not found on watchlist"
    finally:
        await conn.close()


async def get_watchlist() -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM watchlist ORDER BY added_at DESC"
        )
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Category Trends
# ---------------------------------------------------------------------------

async def save_category_trend(
    season: int,
    week: int,
    category: str,
    strength: str,
    value: float | None = None,
) -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT OR REPLACE INTO category_trends
               (season, week, category, strength, value)
               VALUES (?, ?, ?, ?, ?)""",
            (season, week, category, strength.upper(), value),
        )
        await conn.commit()
        return f"Saved trend: {category} = {strength.upper()} (week {week})"
    finally:
        await conn.close()


async def get_category_trends(
    season: int | None = None,
    category: str | None = None,
    last_n_weeks: int | None = None,
) -> list[dict]:
    conn = await get_connection()
    try:
        query = "SELECT * FROM category_trends WHERE 1=1"
        params: list = []
        if season is not None:
            query += " AND season = ?"
            params.append(season)
        if category is not None:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY season DESC, week DESC"
        if last_n_weeks is not None:
            query += " LIMIT ?"
            params.append(last_n_weeks)

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Draft Picks
# ---------------------------------------------------------------------------

async def save_draft_pick(
    season: int,
    player_name: str,
    position: str = "",
    bid_amount: float | None = None,
    round_num: int | None = None,
    pick: int | None = None,
    keeper: bool = False,
) -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO draft_picks
               (season, player_name, position, bid_amount, round, pick, keeper)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (season, player_name, position, bid_amount, round_num, pick, int(keeper)),
        )
        await conn.commit()
        price = f" for ${bid_amount}" if bid_amount is not None else ""
        return f"Saved draft pick: {player_name}{price}"
    finally:
        await conn.close()


async def get_draft_picks(season: int | None = None) -> list[dict]:
    conn = await get_connection()
    try:
        query = "SELECT * FROM draft_picks"
        params: list = []
        if season is not None:
            query += " WHERE season = ?"
            params.append(season)
        query += " ORDER BY drafted_at ASC"

        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Preferences
# ---------------------------------------------------------------------------

async def set_preference(key: str, value: str) -> str:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT OR REPLACE INTO preferences (key, value, updated_at)
               VALUES (?, ?, datetime('now'))""",
            (key, value),
        )
        await conn.commit()
        return f"Preference set: {key} = {value}"
    finally:
        await conn.close()


async def get_preferences() -> dict[str, str]:
    conn = await get_connection()
    try:
        cursor = await conn.execute("SELECT key, value FROM preferences")
        rows = await cursor.fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Full Context (aggregated snapshot)
# ---------------------------------------------------------------------------

async def get_full_context(season: int | None = None) -> dict:
    """Return a combined snapshot of all memory for quick skill loading."""
    matchups = await get_matchups(season=season)
    moves = await get_roster_moves(season=season, limit=20)
    watchlist_items = await get_watchlist()
    trends = await get_category_trends(season=season, last_n_weeks=28)
    prefs = await get_preferences()

    return {
        "matchup_history": matchups,
        "recent_roster_moves": moves,
        "watchlist": watchlist_items,
        "category_trends": trends,
        "preferences": prefs,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_dict(row: aiosqlite.Row) -> dict:
    d = dict(row)
    # Parse JSON fields
    for key in ("categories_won", "categories_lost"):
        if key in d and isinstance(d[key], str):
            try:
                d[key] = json.loads(d[key])
            except (json.JSONDecodeError, TypeError):
                pass
    return d
