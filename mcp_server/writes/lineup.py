"""WT-B — set lineup (activate / bench / swap). See docs/writes/wt-b-lineup.md.

One MCP tool + one 1:1 CLI command, both routed through the shared ``write_flow``
safety model and ``league.set_lineup_moves``. Position names at the tool boundary
(UTIL, P, BE, SP, ...) are converted to numeric ``lineupSlotId`` via the two-way
``POSITION_MAP``; the raw ``player.lineupSlotId`` supplies the from-slot.
"""

from . import _base
from ..config import get_league
from espn_api.baseball.constant import POSITION_MAP, normalize_position_label

# Bench (16) and IL (17) hold multiple players, so the "slot already occupied"
# rule does not apply to them — a player can always be moved to the bench/IL.
MULTI_CAPACITY_SLOTS = {16, 17}

# The combo infield/middle-infield slots are named '2B/SS' (6) and '1B/3B' (7) in
# POSITION_MAP, but the spec's tool vocabulary uses the conventional 'MI'/'CI'
# labels. Bridge them here (lineup.py owns its name boundary) so the names we
# advertise in errors are the names we actually accept.
_SLOT_NAME_ALIASES = {"MI": 6, "CI": 7}


def _slot_id(name):
    """Position name (e.g. 'UTIL', 'p', 'BE', 'MI') -> numeric lineupSlotId, or None."""
    normalized = normalize_position_label(name)
    if not normalized:
        return None
    if normalized in _SLOT_NAME_ALIASES:
        return _SLOT_NAME_ALIASES[normalized]
    slot = POSITION_MAP.get(normalized)
    return slot if isinstance(slot, int) else None


def _slot_name(slot_id):
    """Numeric lineupSlotId -> position name (falls back to the id itself)."""
    return POSITION_MAP.get(slot_id, slot_id)


def _move_line(player, from_id, to_id):
    """One auditable preview line: 'Name (POS) : FROM (id) → TO (id)'."""
    return (
        f"{getattr(player, 'name', '?')} ({getattr(player, 'position', '?')}) : "
        f"{_slot_name(from_id)} ({from_id}) → {_slot_name(to_id)} ({to_id})"
    )


def _eligible(player, slot_id):
    """True if the player can occupy the slot (eligibleSlots is a name list)."""
    return _slot_name(slot_id) in (getattr(player, "eligibleSlots", []) or [])


def _build_moves(league, team, player_name, to_slot, swap_with):
    """Resolve players + slots and build the LINEUP move tuples.

    Returns (moves, lines, error). On any validation failure moves/lines are None
    and error is a human-readable string; the caller returns it without posting.
    ``moves`` is a list of (playerId, fromLineupSlotId, toLineupSlotId) tuples —
    one for a plain move, two for a swap.
    """
    player, err = _base.resolve_my_player(league, player_name)
    if err:
        return None, None, err

    to_slot_id = _slot_id(to_slot)
    if to_slot_id is None:
        return None, None, (
            f"Unknown slot '{to_slot}'. Valid slots: "
            "C, 1B, 2B, 3B, SS, OF, MI, CI, LF, CF, RF, DH, UTIL, P, SP, RP, BE, IL."
        )

    from_slot_id = player.lineupSlotId
    to_name = _slot_name(to_slot_id)

    if from_slot_id == to_slot_id:
        return None, None, f"{player.name} is already in {to_name} ({to_slot_id})."

    if not _eligible(player, to_slot_id):
        eligible = ", ".join(getattr(player, "eligibleSlots", []) or []) or "none"
        return None, None, (
            f"{player.name} is not eligible for {to_name} ({to_slot_id}). "
            f"Eligible slots: {eligible}."
        )

    moves = [(player.playerId, from_slot_id, to_slot_id)]
    lines = [_move_line(player, from_slot_id, to_slot_id)]

    if swap_with:
        partner, err = _base.resolve_my_player(league, swap_with)
        if err:
            return None, None, err
        if partner.playerId == player.playerId:
            return None, None, "Cannot swap a player with themselves."

        partner_from = partner.lineupSlotId
        partner_to = from_slot_id  # the swap partner takes the named player's original slot
        if not _eligible(partner, partner_to):
            eligible = ", ".join(getattr(partner, "eligibleSlots", []) or []) or "none"
            return None, None, (
                f"{partner.name} is not eligible for {_slot_name(partner_to)} "
                f"({partner_to}). Eligible slots: {eligible}."
            )
        moves.append((partner.playerId, partner_from, partner_to))
        lines.append(_move_line(partner, partner_from, partner_to))
        return moves, lines, None

    # Single move: moving into an occupied starter slot is illegal — require a swap.
    if to_slot_id not in MULTI_CAPACITY_SLOTS:
        occupant = next(
            (
                p
                for p in getattr(team, "roster", []) or []
                if getattr(p, "lineupSlotId", None) == to_slot_id
                and getattr(p, "playerId", None) != player.playerId
            ),
            None,
        )
        if occupant is not None:
            return None, None, (
                f"Slot {to_name} ({to_slot_id}) is already occupied by {occupant.name}. "
                f'Use --swap-with "{occupant.name}" to swap them.'
            )

    return moves, lines, None


def set_lineup(player_name: str, to_slot: str, swap_with: str = "", confirm_token: str = "") -> str:
    """Move a player on YOUR roster to a different lineup slot (activate, bench, or swap).

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; show the human the exact move and get explicit approval; only then
    re-call with the confirm_token from the preview. Never invent/reuse a token. Never
    preview and execute in the same turn without explicit human approval.

    Args:
        player_name: Player on your roster to move.
        to_slot: Destination slot as a position name (UTIL, P, BE, SP, RP, C, OF, ...).
        swap_with: Optional player on your roster to move into the named player's old slot.
        confirm_token: Echo the token from the preview to execute. Empty = preview only.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()
    team, err = _base.get_my_team_or_error()
    if err:
        return err

    moves, lines, err = _build_moves(league, team, player_name, to_slot, swap_with)
    if err:
        return err

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.set_lineup_moves(team.team_id, moves, dry_run=True),
        execute=lambda: league.set_lineup_moves(team.team_id, moves, dry_run=False),
        render_preview=lambda payload, token: _base.fmt_txn_preview("Set Lineup", lines, payload, token),
        render_result=lambda resp, payload: _base.fmt_txn_result("Set Lineup", resp),
    )


def register_tools(mcp):
    """Register the set_lineup tool (the module-level function is the tool body)."""
    mcp.tool()(set_lineup)
    return set_lineup


def register_commands(app):
    """Register the lineup CLI command (reuses set_lineup so logic lives once)."""
    import typer
    from ..cli import console

    @app.command()
    def lineup(
        player: str = typer.Argument(..., help="Player on your roster to move."),
        to_slot: str = typer.Argument(..., help="Destination slot name (UTIL, P, BE, SP, RP, ...)."),
        swap_with: str = typer.Option("", "--swap-with", help="Player to move into the old slot."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Echo preview token to execute."),
    ):
        """Set a lineup slot (preview first; re-run with --confirm-token to execute)."""
        console.print(set_lineup(player, to_slot, swap_with=swap_with, confirm_token=confirm_token))

    return lineup
