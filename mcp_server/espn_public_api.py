"""ESPN public player API client — no auth needed.

Uses site.web.api.espn.com for player profiles, splits, game logs, and news.
Uses site.api.espn.com for MLB game scores.
These are public ESPN APIs, separate from the fantasy league API.
"""

import httpx

PLAYER_BASE = "https://site.web.api.espn.com/apis/common/v3/sports/baseball/mlb/athletes"
GAMES_BASE = "https://site.api.espn.com/apis/fantasy/v2/games/flb/games"
SEARCH_BASE = "https://site.web.api.espn.com/apis/search/v2"

DEFAULT_PARAMS = {"contentorigin": "espn", "lang": "en", "region": "us"}

_client = None


def _get_client() -> httpx.Client:
    global _client
    if _client is None:
        _client = httpx.Client(timeout=15.0)
    return _client


def get_player_overview(athlete_id: int) -> dict:
    """Get player overview: stats, news, next game, rotowire blurb, awards."""
    resp = _get_client().get(
        f"{PLAYER_BASE}/{athlete_id}/overview",
        params=DEFAULT_PARAMS,
    )
    resp.raise_for_status()
    return resp.json()


def get_player_splits(athlete_id: int, season: int | None = None) -> dict:
    """Get player splits: vs LHP/RHP, home/away, by month, by count, etc."""
    params = {**DEFAULT_PARAMS}
    if season:
        params["season"] = str(season)
    resp = _get_client().get(
        f"{PLAYER_BASE}/{athlete_id}/splits",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def get_player_gamelog(athlete_id: int, season: int | None = None, category: str | None = None) -> dict:
    """Get player game log: game-by-game stats."""
    params = {**DEFAULT_PARAMS}
    if season:
        params["season"] = str(season)
    if category:
        params["category"] = category  # "batting" or "pitching"
    resp = _get_client().get(
        f"{PLAYER_BASE}/{athlete_id}/gamelog",
        params=params,
    )
    resp.raise_for_status()
    return resp.json()


def get_mlb_games(date: str) -> dict:
    """Get MLB games for a specific date. Date format: YYYYMMDD."""
    resp = _get_client().get(
        GAMES_BASE,
        params={"dates": date, "pbpOnly": "true", "useMap": "true", "lang": "en", "region": "us"},
    )
    resp.raise_for_status()
    return resp.json()


def search_espn(query: str, limit: int = 10) -> dict:
    """Search ESPN for players, teams, articles."""
    resp = _get_client().get(
        SEARCH_BASE,
        params={"query": query, "type": "player", "limit": str(limit), "page": "1"},
    )
    resp.raise_for_status()
    return resp.json()


def resolve_athlete_id(league, player_name: str) -> int | None:
    """Resolve a fantasy player name to an ESPN public athlete ID.

    Strategy: search ESPN's public API for the player name, then match
    against the fantasy player_map to confirm identity.
    """
    try:
        data = search_espn(player_name, limit=5)
        results = data.get("results", [])
        for result_group in results:
            items = result_group.get("contents", [])
            for item in items:
                # Player search results have an 'id' field
                athlete_id = item.get("id")
                if athlete_id:
                    return int(athlete_id)
    except Exception:
        pass

    # Fallback: try the fantasy playerId directly (sometimes they match)
    fantasy_id = league.player_map.get(player_name)
    if isinstance(fantasy_id, int):
        return fantasy_id

    return None
