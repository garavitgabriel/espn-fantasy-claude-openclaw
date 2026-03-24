"""League connection and environment configuration.

Loads ESPN credentials from .env, creates a cached League singleton,
and resolves the user's team from ESPN_TEAM_ID / ESPN_TEAM_NAME.
"""

import os
import re
import sys
from typing import Iterable, List, Optional, Tuple

# Add the project root to sys.path so espn_api can be imported
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _project_root)

# Load .env from project root when python-dotenv is available.
try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - exercised indirectly in lean envs
    load_dotenv = None

if load_dotenv is not None:
    load_dotenv(os.path.join(_project_root, ".env"))

from espn_api.baseball import League

ESPN_S2 = os.environ.get("ESPN_S2", "")
ESPN_SWID = os.environ.get("ESPN_SWID", "")
ESPN_LEAGUE_ID = int(os.environ.get("ESPN_LEAGUE_ID", "612122596"))
ESPN_YEAR = int(os.environ.get("ESPN_YEAR", "2026"))
ESPN_TEAM_ID = os.environ.get("ESPN_TEAM_ID", "").strip()
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


def _normalize_team_text(value: object) -> str:
    """Normalize names for resilient case/punctuation/spacing-insensitive matching."""
    if value is None:
        return ""
    normalized = re.sub(r"[^a-z0-9]+", " ", str(value).casefold())
    return " ".join(normalized.split())


def _coerce_team_id(value: object) -> Optional[int]:
    """Return an integer team id when configured, otherwise None."""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _owner_name_candidates(team) -> Iterable[str]:
    """Yield owner names from ESPN member records in comparable forms."""
    for owner in getattr(team, "owners", []) or []:
        if not isinstance(owner, dict):
            continue

        first_name = owner.get("firstName", "")
        last_name = owner.get("lastName", "")
        full_name = " ".join(part for part in (first_name, last_name) if part).strip()

        for candidate in (
            first_name,
            last_name,
            full_name,
            owner.get("displayName", ""),
            owner.get("fullName", ""),
        ):
            if candidate:
                yield str(candidate)


def _team_owner_labels(team) -> List[str]:
    """Return readable owner labels for display/debug output."""
    labels = []
    seen = set()
    for owner in getattr(team, "owners", []) or []:
        if not isinstance(owner, dict):
            continue
        first_name = owner.get("firstName", "")
        last_name = owner.get("lastName", "")
        full_name = " ".join(part for part in (first_name, last_name) if part).strip()
        candidate = full_name or owner.get("fullName", "") or owner.get("displayName", "") or first_name or last_name
        normalized = _normalize_team_text(candidate)
        if normalized and normalized not in seen:
            seen.add(normalized)
            labels.append(str(candidate).strip())
    return labels


def describe_available_teams(league: League) -> str:
    """Describe teams with ids and owner names for troubleshooting."""
    descriptions = []
    for team in getattr(league, "teams", []):
        owners = ", ".join(_team_owner_labels(team)) or "unknown owner"
        descriptions.append(f"{team.team_name} [id={team.team_id}; owners={owners}]")
    return "; ".join(descriptions)


def resolve_team(league: League, team_name: str):
    """Resolve an arbitrary team name using normalized exact-first, then partial matching."""
    target = _normalize_team_text(team_name)
    if not target:
        return None

    exact_matches = []
    partial_matches = []
    for team in league.teams:
        normalized_name = _normalize_team_text(getattr(team, "team_name", ""))
        if normalized_name == target:
            exact_matches.append(team)
        elif target in normalized_name:
            partial_matches.append(team)

    if exact_matches:
        return exact_matches[0]
    if len(partial_matches) == 1:
        return partial_matches[0]
    if partial_matches:
        return partial_matches[0]
    return None


def resolve_my_team(league: League) -> Tuple[object, Optional[str]]:
    """Resolve the configured team using team id, team name, then owner names."""
    configured_team_id = _coerce_team_id(ESPN_TEAM_ID)
    if ESPN_TEAM_ID and configured_team_id is None:
        return None, (
            f"Could not resolve your team: ESPN_TEAM_ID='{ESPN_TEAM_ID}' is not a valid integer. "
            f"Available teams: {describe_available_teams(league)}"
        )

    if configured_team_id is not None:
        for team in league.teams:
            if getattr(team, "team_id", None) == configured_team_id:
                return team, None
        return None, (
            f"Could not resolve your team: no team matched ESPN_TEAM_ID={configured_team_id}. "
            f"Available teams: {describe_available_teams(league)}"
        )

    target_name = _normalize_team_text(ESPN_TEAM_NAME)
    if not target_name:
        return None, (
            "Could not resolve your team: set ESPN_TEAM_ID or ESPN_TEAM_NAME. "
            f"Available teams: {describe_available_teams(league)}"
        )

    exact_name_matches = []
    partial_name_matches = []
    exact_owner_matches = []
    partial_owner_matches = []

    for team in league.teams:
        normalized_name = _normalize_team_text(getattr(team, "team_name", ""))
        if normalized_name == target_name:
            exact_name_matches.append(team)
            continue
        if target_name in normalized_name:
            partial_name_matches.append(team)

        normalized_owners = [_normalize_team_text(name) for name in _owner_name_candidates(team)]
        if any(owner == target_name for owner in normalized_owners):
            exact_owner_matches.append(team)
        elif any(target_name in owner for owner in normalized_owners):
            partial_owner_matches.append(team)

    for matches in (
        exact_name_matches,
        partial_name_matches,
        exact_owner_matches,
        partial_owner_matches,
    ):
        if matches:
            return matches[0], None

    return None, (
        "Could not resolve your team from ESPN_TEAM_ID or ESPN_TEAM_NAME. "
        f"Current ESPN_TEAM_NAME='{ESPN_TEAM_NAME}'. "
        f"Available teams: {describe_available_teams(league)}"
    )


def get_my_team(league: League):
    team, _ = resolve_my_team(league)
    return team


def get_my_team_error(league: League) -> str:
    """Return the shared failure message for my-team resolution."""
    _, error = resolve_my_team(league)
    return error or "Could not resolve your team."
