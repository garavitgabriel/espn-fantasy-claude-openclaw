"""WT-C — trades (propose / cancel). See docs/writes/wt-c-trades.md.

Two MCP tools (propose_trade / cancel_trade) + two 1:1 CLI commands, all routed
through the shared safety flow in ``_base.write_flow`` (env gate + payload-bound
confirm token + preview==execute + cache invalidation + ESPN error mapping).

Trade item direction is the critical correctness point (WRITE_API_REFERENCE §5):
  give    -> {type: TRADE, fromTeamId: me,    toTeamId: other}
  receive -> {type: TRADE, fromTeamId: other, toTeamId: me}
The library ``League.propose_trade`` builds the items; we just pass send/receive ids.

Accept/reject are OUT OF SCOPE (payloads never captured) — not implemented.
"""

from . import _base
from ..config import get_league


def _split_names(raw):
    """Split a comma-separated player-name string into stripped, non-empty names."""
    return [part.strip() for part in (raw or "").split(",") if part.strip()]


def _player_label(player):
    """'Spencer Strider (SP)'-style label for preview lines."""
    name = getattr(player, "name", "?")
    position = getattr(player, "position", "") or ""
    return f"{name} ({position})" if position else name


def propose_trade(
    to_team: str,
    give_players: str,
    receive_players: str,
    comment: str = "",
    confirm_token: str = "",
) -> str:
    """Propose a trade to another team in your REAL live league.

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; show the human the exact players and direction and get explicit
    approval; only then re-call with the confirm_token from the preview. Never invent or
    reuse a token. Never preview and execute in the same turn without explicit human approval.

    Args:
        to_team: Name of the team you are proposing to (the counterparty).
        give_players: Comma-separated names of players YOU send (must be on your roster).
        receive_players: Comma-separated names of players you RECEIVE (must be on the
            other team's roster).
        comment: Optional note attached to the proposal.
        confirm_token: Leave empty for a preview; echo the previewed token to execute.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()

    my_team, err = _base.get_my_team_or_error()
    if err:
        return err

    other_team, err = _base.resolve_other_team(league, to_team)
    if err:
        return err

    give_names = _split_names(give_players)
    receive_names = _split_names(receive_players)
    if not give_names and not receive_names:
        return "A trade needs at least one player to give or receive."

    give = []
    for name in give_names:
        player, err = _base.resolve_my_player(league, name)
        if err:
            return err
        give.append(player)

    receive = []
    for name in receive_names:
        player, err = _base.resolve_team_player(other_team, name)
        if err:
            return err
        receive.append(player)

    from_team_id = my_team.team_id
    to_team_id = other_team.team_id
    send_ids = [p.playerId for p in give]
    receive_ids = [p.playerId for p in receive]
    other_name = getattr(other_team, "team_name", to_team)

    def _lines(payload):
        lines = []
        for player in give:
            lines.append(f"GIVE:    {_player_label(player)} → {other_name}")
        for player in receive:
            lines.append(f"RECEIVE: {_player_label(player)} ← {other_name}")
        expires = payload.get("expirationDate", "?")
        lines.append(f'Expires: {expires}   Comment: "{comment}"')
        return lines

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.propose_trade(
            from_team_id, to_team_id,
            send_player_ids=send_ids, receive_player_ids=receive_ids,
            comment=comment, dry_run=True,
        ),
        execute=lambda: league.propose_trade(
            from_team_id, to_team_id,
            send_player_ids=send_ids, receive_player_ids=receive_ids,
            comment=comment, dry_run=False,
        ),
        render_preview=lambda payload, token: _base.fmt_txn_preview(
            "Propose Trade", _lines(payload), payload, token,
        ),
        render_result=lambda resp, payload: _render_propose_result(resp),
    )


def _render_propose_result(response) -> str:
    """Surface PENDING status and the proposal id prominently (needed to cancel)."""
    base = _base.fmt_txn_result("Propose Trade", response)
    txn_id = response.get("id") if isinstance(response, dict) else None
    if txn_id:
        base += (
            f"\n\n**Proposal id:** `{txn_id}`\n"
            f"Cancel it with `cancel_trade(transaction_id=\"{txn_id}\")`."
        )
    return base


def cancel_trade(transaction_id: str, confirm_token: str = "") -> str:
    """Withdraw a pending trade proposal you created in your REAL live league.

    SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
    preview + token; confirm with a human; only then re-call with the previewed token.
    Never invent or reuse a token.

    Args:
        transaction_id: The proposal id (from a propose_trade result or get_recent_activity).
        confirm_token: Leave empty for a preview; echo the previewed token to execute.
    """
    gate = _base.require_writes_enabled()
    if gate:
        return gate

    league = get_league()

    my_team, err = _base.get_my_team_or_error()
    if err:
        return err

    transaction_id = (transaction_id or "").strip()
    if not transaction_id:
        return "A transaction id is required to cancel a trade proposal."

    team_id = my_team.team_id

    return _base.write_flow(
        confirm_token,
        build_payload=lambda: league.cancel_trade(
            team_id, related_transaction_id=transaction_id, dry_run=True,
        ),
        execute=lambda: league.cancel_trade(
            team_id, related_transaction_id=transaction_id, dry_run=False,
        ),
        render_preview=lambda payload, token: _base.fmt_txn_preview(
            "Cancel Trade",
            [f"Cancel pending proposal {transaction_id}"],
            payload, token,
        ),
        render_result=lambda resp, payload: _base.fmt_txn_result("Cancel Trade", resp),
    )


def register_tools(mcp):
    """Register propose_trade / cancel_trade tools."""
    mcp.tool()(propose_trade)
    mcp.tool()(cancel_trade)


def register_commands(app):
    """Register propose-trade / cancel-trade CLI commands."""
    import typer
    from ..cli import console

    @app.command(name="propose-trade")
    def propose_trade_cmd(
        to: str = typer.Option(..., "--to", help="Team you are proposing to."),
        give: str = typer.Option("", "--give", help="Comma-separated players you send."),
        receive: str = typer.Option("", "--receive", help="Comma-separated players you receive."),
        comment: str = typer.Option("", "--comment", help="Optional note on the proposal."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Echo the previewed token to execute."),
    ):
        """Propose a trade (preview first; re-run with --confirm-token to execute)."""
        console.print(propose_trade(to, give, receive, comment=comment, confirm_token=confirm_token))

    @app.command(name="cancel-trade")
    def cancel_trade_cmd(
        transaction_id: str = typer.Argument(..., help="Proposal id to withdraw."),
        confirm_token: str = typer.Option("", "--confirm-token", help="Echo the previewed token to execute."),
    ):
        """Cancel a pending trade proposal (preview first; re-run with --confirm-token)."""
        console.print(cancel_trade(transaction_id, confirm_token=confirm_token))
