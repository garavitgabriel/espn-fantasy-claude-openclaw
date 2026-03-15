"""League connection and environment configuration.

Loads ESPN credentials from .env, creates a cached League singleton,
and resolves the user's team by ESPN_TEAM_NAME partial match.
"""

import os
import sys

# Add the project root to sys.path so espn_api can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(os.path.join(_project_root, ".env"))

from espn_api.baseball import League

ESPN_S2 = os.environ.get("ESPN_S2", "")
ESPN_SWID = os.environ.get("ESPN_SWID", "")
ESPN_LEAGUE_ID = int(os.environ.get("ESPN_LEAGUE_ID", "612122596"))
ESPN_YEAR = int(os.environ.get("ESPN_YEAR", "2026"))
ESPN_TEAM_NAME = os.environ.get("ESPN_TEAM_NAME", "Gabriel")

_league_instance = None


def _check_credentials():
    """Raise early with a helpful message if ESPN credentials are missing."""
    missing = []
    if not ESPN_S2:
        missing.append("ESPN_S2")
    if not ESPN_SWID:
        missing.append("ESPN_SWID")
    if missing:
        raise SystemExit(
            f"Missing ESPN credentials: {', '.join(missing)}. "
            f"Set them in .env or as environment variables. See .env.example."
        )


def get_league() -> League:
    global _league_instance
    if _league_instance is None:
        _check_credentials()
        _league_instance = League(
            league_id=ESPN_LEAGUE_ID,
            year=ESPN_YEAR,
            espn_s2=ESPN_S2,
            swid=ESPN_SWID,
        )
    return _league_instance


def get_my_team(league: League):
    name_lower = ESPN_TEAM_NAME.lower()
    for team in league.teams:
        if name_lower in team.team_name.lower():
            return team
    return None
