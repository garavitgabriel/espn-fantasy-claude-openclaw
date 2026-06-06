"""WT-A — roster moves (add / drop / waiver). See docs/writes/wt-a-roster.md.

Three MCP tools (add_player / drop_player / waiver_claim) and three 1:1 CLI commands
(add / drop / waiver). Every mutation flows through the shared safety model in
``_base.write_flow`` (env gate + payload-bound confirm token + preview==execute +
cache invalidation + friendly ESPN error mapping) — this module never reimplements it.
"""

from . import _base
from ..config import get_league


# --- Small display helpers ---------------------------------------------------

def _describe(player) -> str:
    """A short human label for a player: 'Name (POS, TEAM)'."""
    name = getattr(player, "name", None) or "Unknown player"
    pos = getattr(player, "position", "") or ""
    pro = getattr(player, "proTeam", "")
    pro = "" if pro in (None, "") else str(pro)
    meta = ", ".join(part for part in (pos, pro) if part)
    return f"{name} ({meta})" if meta else name


def _roster_has_open_slot(league, team) -> bool:
    """Best-effort check for a free roster spot (used only for a 409 pre-warning).

    Capacity = sum of every lineup slot count except IL (slot 17); occupancy = rostered
    players not currently on IL. Any lookup failure returns True so we never block a move
    or raise a false 'roster full' alarm — ESPN's own 409 (mapped by write_flow) is the
    real safety net.
    """
    try:
        data = league.espn_request.get_league()
        counts = data["settings"].get("rosterSettings", {}).get("lineupSlotCounts", {})
        capacity = sum(int(c) for slot_id, c in counts.items() if int(slot_id) != 17)
        if capacity <= 0:
            return True
        rostered = sum(
            1 for p in getattr(team, "roster", []) if getattr(p, "lineupSlot", "") != "IL"
        )
        return rostered < capacity
    except Exception:
        return True


# --- Tool functions (module-level so the CLI commands reuse them 1:1) ---------

def add_player(player_name: str, drop_player_name: str = "", confirm_token: str = "") -> str:
    """Add a free agent to your roster (optionally dropping a player in the same move).

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; show the human the exact move and get explicit approval; only then
    re-call with the confirm_token from the preview. Never invent/reuse a token. Never
    preview and execute in the same turn without explicit human approval.

    Args:
        player_name: Free agent to add (ESPN player name).
        drop_player_name: Player on your roster to drop in the same transaction (optional).
        confirm_token: Echo the 8-hex token from the preview to execute.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()
    team, err = _base.get_my_team_or_error()
    if err:
        return err

    fa, err = _base.resolve_free_agent(league, player_name)
    if err:
        return err

    drop = None
    if drop_player_name:
        drop, err = _base.resolve_my_player(league, drop_player_name)
        if err:
            return err

    add_id = getattr(fa, "playerId", None)
    drop_id = getattr(drop, "playerId", None) if drop else None

    lines = [f"ADD  {_describe(fa)} — free agent"]
    title = "Add Player"
    if drop:
        lines.append(f"DROP {_describe(drop)} — from your roster")
        title = "Add + Drop"
    elif not _roster_has_open_slot(league, team):
        lines.append(
            "⚠️ Roster appears full and no drop specified — ESPN may reject (409). "
            "Add a drop with `drop_player_name` / `--drop`."
        )

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.add_drop_player(
            team.team_id, add_player_id=add_id, drop_player_id=drop_id, dry_run=True
        ),
        execute=lambda: league.add_drop_player(
            team.team_id, add_player_id=add_id, drop_player_id=drop_id, dry_run=False
        ),
        render_preview=lambda payload, token: _base.fmt_txn_preview(title, lines, payload, token),
        render_result=lambda resp, payload: _base.fmt_txn_result(title, resp),
    )


def drop_player(player_name: str, confirm_token: str = "") -> str:
    """Drop a player from your roster (no add).

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; show the human the exact move and get explicit approval; only then
    re-call with the confirm_token from the preview. Never invent/reuse a token. Never
    preview and execute in the same turn without explicit human approval.

    Args:
        player_name: Player on your roster to drop (ESPN player name).
        confirm_token: Echo the 8-hex token from the preview to execute.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()
    team, err = _base.get_my_team_or_error()
    if err:
        return err

    player, err = _base.resolve_my_player(league, player_name)
    if err:
        return err

    drop_id = getattr(player, "playerId", None)
    lines = [f"DROP {_describe(player)} — from your roster"]

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.add_drop_player(
            team.team_id, add_player_id=None, drop_player_id=drop_id, dry_run=True
        ),
        execute=lambda: league.add_drop_player(
            team.team_id, add_player_id=None, drop_player_id=drop_id, dry_run=False
        ),
        render_preview=lambda payload, token: _base.fmt_txn_preview("Drop Player", lines, payload, token),
        render_result=lambda resp, payload: _base.fmt_txn_result("Drop Player", resp),
    )


def waiver_claim(player_name: str, drop_player_name: str = "", confirm_token: str = "") -> str:
    """Submit a waiver claim for a player (optionally dropping a player if it processes).

    Waiver claims land PENDING and are processed at the next waiver run — they are NOT
    immediate. This league has no FAAB, so no bid amount is sent.

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; show the human the exact move and get explicit approval; only then
    re-call with the confirm_token from the preview. Never invent/reuse a token. Never
    preview and execute in the same turn without explicit human approval.

    Args:
        player_name: Player to claim off waivers / free agency (ESPN player name).
        drop_player_name: Player on your roster to drop if the claim processes (optional).
        confirm_token: Echo the 8-hex token from the preview to execute.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()
    team, err = _base.get_my_team_or_error()
    if err:
        return err

    fa, err = _base.resolve_free_agent(league, player_name)
    if err:
        return err

    drop = None
    if drop_player_name:
        drop, err = _base.resolve_my_player(league, drop_player_name)
        if err:
            return err

    add_id = getattr(fa, "playerId", None)
    drop_id = getattr(drop, "playerId", None) if drop else None

    lines = [f"ADD  {_describe(fa)} — via waivers"]
    if drop:
        lines.append(f"DROP {_describe(drop)} — from your roster")
    lines.append("Type: WAIVER (lands PENDING until waiver processing)")

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.waiver_claim(
            team.team_id, add_id, drop_player_id=drop_id, bid_amount=None, dry_run=True
        ),
        execute=lambda: league.waiver_claim(
            team.team_id, add_id, drop_player_id=drop_id, bid_amount=None, dry_run=False
        ),
        render_preview=lambda payload, token: _base.fmt_txn_preview("Waiver Claim", lines, payload, token),
        render_result=lambda resp, payload: _base.fmt_txn_result("Waiver Claim", resp),
    )


# --- Registrars --------------------------------------------------------------

def register_tools(mcp):
    """Register add_player / drop_player / waiver_claim tools."""
    mcp.tool()(add_player)
    mcp.tool()(drop_player)
    mcp.tool()(waiver_claim)


def register_commands(app):
    """Register add / drop / waiver CLI commands (1:1 with the tools)."""
    import typer
    from ..cli import console

    @app.command()
    def add(
        player: str = typer.Argument(..., help="Free agent to add (ESPN player name)."),
        drop: str = typer.Option("", "--drop", "-d", help="Player to drop in the same move."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Token from the preview to execute."),
    ):
        """Add a free agent (preview first; re-run with --confirm-token to execute)."""
        console.print(add_player(player, drop_player_name=drop, confirm_token=confirm_token))

    @app.command()
    def drop(
        player: str = typer.Argument(..., help="Player on your roster to drop."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Token from the preview to execute."),
    ):
        """Drop a player from your roster (preview first; re-run with --confirm-token)."""
        console.print(drop_player(player, confirm_token=confirm_token))

    @app.command()
    def waiver(
        player: str = typer.Argument(..., help="Player to claim off waivers."),
        drop: str = typer.Option("", "--drop", "-d", help="Player to drop if the claim processes."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Token from the preview to execute."),
    ):
        """Submit a waiver claim (preview first; re-run with --confirm-token to execute)."""
        console.print(waiver_claim(player, drop_player_name=drop, confirm_token=confirm_token))
