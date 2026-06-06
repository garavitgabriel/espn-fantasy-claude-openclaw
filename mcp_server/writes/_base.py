"""Shared helpers for write/mutation operations.

Operation modules (roster.py, lineup.py, trades.py) build on these. The safety model
(env gate + payload-bound confirm token + preview==execute + cache invalidation) is
centralized in ``write_flow`` so it cannot drift across modules.

See docs/writes/00-BRIEF.md for the contract.
"""

import json
import re

from ..config import (
    get_league,
    resolve_my_team,
    resolve_team,
    require_writes_enabled,
    invalidate_league,
    txn_token,
)
from espn_api.requests.espn_requests import (
    ESPNRosterFull,
    ESPNAccessDenied,
    ESPNInvalidLeague,
    ESPNUnknownError,
)

# Re-export so operation modules import everything write-related from one place.
__all__ = [
    "require_writes_enabled",
    "get_my_team_or_error",
    "resolve_my_player",
    "resolve_free_agent",
    "resolve_other_team",
    "resolve_team_player",
    "write_flow",
    "fmt_txn_preview",
    "fmt_txn_result",
]


def _norm(value) -> str:
    """Normalize a name for case/punctuation/spacing-insensitive matching."""
    return " ".join(re.sub(r"[^a-z0-9]+", " ", str(value or "").casefold()).split())


def _find_in_roster(roster, name):
    """Find a player on a roster by name (exact, then partial). Returns player or None."""
    target = _norm(name)
    if not target:
        return None
    exact = [p for p in roster if _norm(getattr(p, "name", "")) == target]
    if exact:
        return exact[0]
    partial = [p for p in roster if target in _norm(getattr(p, "name", ""))]
    return partial[0] if partial else None


def _resolve_league_player(league, name):
    """Resolve a player league-wide by name. Returns (player, error_msg)."""
    result = league.player_info(name=name)
    if result is None:
        import difflib
        names = list(getattr(league, "player_map", {}).keys())
        close = difflib.get_close_matches(name, names, n=3, cutoff=0.6)
        if close:
            suggestions = ", ".join(f'"{n}"' for n in close)
            return None, f"Player '{name}' not found. Did you mean: {suggestions}?"
        return None, f"Player '{name}' not found. Try the exact ESPN name."
    if isinstance(result, list):
        return (result[0] if result else None), None
    return result, None


# --- Resolution helpers (each returns (obj, error_message)) ------------------

def get_my_team_or_error():
    """Resolve the configured 'my team'. Returns (team, error_msg)."""
    league = get_league()
    return resolve_my_team(league)


def resolve_my_player(league, name):
    """Resolve a player that must be on MY roster. Returns (player, error_msg)."""
    team, err = resolve_my_team(league)
    if err:
        return None, err
    player = _find_in_roster(getattr(team, "roster", []), name)
    if player is None:
        return None, f"'{name}' is not on your roster."
    return player, None


def resolve_free_agent(league, name):
    """Resolve a player that must be a free agent / on waivers (not on any roster).

    Returns (player, error_msg).
    """
    player, err = _resolve_league_player(league, name)
    if err:
        return None, err
    pid = getattr(player, "playerId", None)
    for team in getattr(league, "teams", []):
        for rostered in getattr(team, "roster", []):
            if getattr(rostered, "playerId", None) == pid:
                return None, (
                    f"'{getattr(player, 'name', name)}' is already rostered by "
                    f"{getattr(team, 'team_name', 'another team')} — not a free agent."
                )
    return player, None


def resolve_other_team(league, name):
    """Resolve a counterparty team by name. Returns (team, error_msg)."""
    team = resolve_team(league, name)
    if team is None:
        from ..config import describe_available_teams
        return None, f"Team '{name}' not found. Available teams: {describe_available_teams(league)}"
    return team, None


def resolve_team_player(team, name):
    """Resolve a player that must be on the given team's roster. Returns (player, error_msg)."""
    player = _find_in_roster(getattr(team, "roster", []), name)
    if player is None:
        return None, f"'{name}' is not on {getattr(team, 'team_name', 'that team')}'s roster."
    return player, None


# --- The write flow ----------------------------------------------------------

def write_flow(confirm_token, *, build_payload, execute, render_preview, render_result):
    """Enforce the full safety model for one write.

    1. Refuse if writes are disabled.
    2. Build the exact payload (dry run) and derive its token.
    3. Without a matching token, return a preview (no execution).
    4. With a matching token, execute, invalidate the cache, and render the result.
    Friendly-maps ESPN write errors.
    """
    gate = require_writes_enabled()
    if gate:
        return gate

    payload = build_payload()
    token = txn_token(payload)

    if (confirm_token or "").strip() != token:
        return render_preview(payload, token)

    try:
        response = execute()
    except ESPNRosterFull as e:
        return f"❌ ESPN rejected the move (roster full / illegal): {e}"
    except ESPNAccessDenied as e:
        return f"❌ ESPN denied the write (auth): {e}"
    except (ESPNInvalidLeague, ESPNUnknownError) as e:
        return f"❌ ESPN write failed: {e}"
    except Exception as e:  # pragma: no cover - defensive
        return f"❌ Write failed: {e}"

    invalidate_league()
    return render_result(response, payload)


# --- Base formatters ---------------------------------------------------------

def fmt_txn_preview(title: str, lines, payload: dict, token: str) -> str:
    """Render a preview: human-readable summary + the literal payload + the confirm token."""
    out = [f"## ⚠️ {title} — PREVIEW (NOT YET EXECUTED)", ""]
    out += [f"- {line}" for line in (lines or [])]
    out += [
        "",
        "**Exact request body that will be sent:**",
        "```json",
        json.dumps(payload, indent=2),
        "```",
        "",
        f"To execute this exact move, re-call with `confirm_token=\"{token}\"`.",
        "Show this preview to a human and get explicit approval first. "
        "The token is bound to this exact payload — if anything changes it will not match.",
    ]
    return "\n".join(out)


def fmt_txn_result(title: str, response) -> str:
    """Render the result of an executed transaction (status + ids)."""
    status = "UNKNOWN"
    txn_id = None
    if isinstance(response, dict):
        status = response.get("status") or status
        txn_id = response.get("id")
    out = [f"## ✅ {title} — {status}", ""]
    if txn_id:
        out.append(f"- Transaction id: `{txn_id}`")
    if status == "PENDING":
        out.append("- Pending: this will be processed later (waiver run / counterparty action).")
    elif status == "EXECUTED":
        out.append("- Executed: the change is live on your roster.")
    elif status == "CANCELED":
        out.append("- Canceled.")
    return "\n".join(out)
