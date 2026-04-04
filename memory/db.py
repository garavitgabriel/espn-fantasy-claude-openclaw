"""SQLite database management for ESPN Fantasy Baseball memory."""

import os
import json
from pathlib import Path

import aiosqlite

_DB_PATH: str | None = None


def _resolve_db_path() -> str:
    """Resolve the database file path from env or default."""
    raw = os.environ.get("MEMORY_DB_PATH", "~/.espn-fantasy/memory.db")
    return str(Path(raw).expanduser())


def get_db_path() -> str:
    global _DB_PATH
    if _DB_PATH is None:
        _DB_PATH = _resolve_db_path()
    return _DB_PATH


SCHEMA_VERSION = 1

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS matchup_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,
    opponent_team TEXT NOT NULL,
    my_wins INTEGER NOT NULL DEFAULT 0,
    my_losses INTEGER NOT NULL DEFAULT 0,
    ties INTEGER NOT NULL DEFAULT 0,
    categories_won TEXT,
    categories_lost TEXT,
    notes TEXT,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(week, season)
);

CREATE TABLE IF NOT EXISTS roster_moves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    action TEXT NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT,
    notes TEXT,
    moved_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_name TEXT NOT NULL UNIQUE,
    position TEXT,
    reason TEXT,
    added_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS category_trends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    week INTEGER NOT NULL,
    category TEXT NOT NULL,
    strength TEXT NOT NULL,
    value REAL,
    recorded_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(season, week, category)
);

CREATE TABLE IF NOT EXISTS draft_picks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    season INTEGER NOT NULL,
    player_name TEXT NOT NULL,
    position TEXT,
    bid_amount REAL,
    round INTEGER,
    pick INTEGER,
    keeper INTEGER NOT NULL DEFAULT 0,
    drafted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS preferences (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


async def get_connection() -> aiosqlite.Connection:
    """Open a connection and ensure schema is applied."""
    db_path = get_db_path()
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row

    # Check if schema needs to be applied
    try:
        cursor = await conn.execute(
            "SELECT MAX(version) as v FROM schema_version"
        )
        row = await cursor.fetchone()
        current = row[0] if row and row[0] else 0
    except aiosqlite.OperationalError:
        current = 0

    if current < SCHEMA_VERSION:
        await conn.executescript(SCHEMA_SQL)
        await conn.execute(
            "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        await conn.commit()

    return conn
