"""Write-operation helpers shared by MCP tools and CLI.

These helpers enforce safe defaults before any live POST could happen.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Iterable

from .guardrails import (
    decision_for_payload,
    dry_run_enabled,
    ensure_budget_remaining,
    ensure_not_protected,
    ensure_position_legal,
    ensure_writes_enabled,
    get_protected_players,
)


APPROVAL_REQUIRED = "approval_required"
SIMULATED_SUCCESS = "simulated_success"


def verify_auth(league) -> dict:
    return league.verify_auth()


def set_lineup(league, team, assignments: list[dict], protected_players: Iterable[str] | None = None) -> dict:
    ensure_writes_enabled()
    protected = get_protected_players(team, protected_players)

    roster_by_id = {getattr(player, "playerId", None): player for player in getattr(team, "roster", [])}
    for assignment in assignments:
        player = roster_by_id.get(assignment.get("playerId"))
        if player is None:
            continue
        ensure_position_legal(player, assignment.get("toLineupSlotId"))
        if assignment.get("toLineupSlotId") == 16:  # BE
            ensure_not_protected(getattr(player, "name", "Unknown"), protected, "Bench move")

    payload = {
        "team_id": team.team_id,
        "scoring_period_id": getattr(league, "scoringPeriodId", None) or getattr(league, "current_week", None),
        "assignments": assignments,
    }
    decision = decision_for_payload("set_lineup", payload)
    if decision.dry_run:
        return {"status": SIMULATED_SUCCESS, "decision": asdict(decision)}

    response = league.set_lineup(team.team_id, payload["scoring_period_id"], assignments)
    return {"status": "executed", "response": response, "decision": asdict(decision)}


def add_drop(league, team, add_player, drop_player, remaining_moves: int | None, protected_players: Iterable[str] | None = None) -> dict:
    ensure_writes_enabled()
    ensure_budget_remaining(remaining_moves, requested_moves=1)
    protected = get_protected_players(team, protected_players)
    ensure_not_protected(getattr(drop_player, "name", "Unknown"), protected, "Drop")

    payload = {
        "team_id": team.team_id,
        "add_player_id": getattr(add_player, "playerId"),
        "drop_player_id": getattr(drop_player, "playerId"),
        "add_player_name": getattr(add_player, "name", None),
        "drop_player_name": getattr(drop_player, "name", None),
    }
    decision = decision_for_payload("add_drop", payload)
    if decision.dry_run:
        return {"status": SIMULATED_SUCCESS, "decision": asdict(decision)}

    response = league.add_drop_player(team.team_id, payload["add_player_id"], payload["drop_player_id"])
    return {"status": "executed", "response": response, "decision": asdict(decision)}


def propose_trade(league, team, trade_partner_team_id: int, give_player_ids: list[int], receive_player_ids: list[int]) -> dict:
    payload = {
        "team_id": team.team_id,
        "trade_partner_team_id": trade_partner_team_id,
        "give_player_ids": give_player_ids,
        "receive_player_ids": receive_player_ids,
    }
    decision = decision_for_payload("propose_trade", payload, requires_approval=True)
    return {
        "status": APPROVAL_REQUIRED,
        "decision": asdict(decision),
        "message": "Trade proposals always require human approval",
    }


def accept_trade(league, team, proposal_id: int) -> dict:
    payload = {
        "team_id": team.team_id,
        "proposal_id": proposal_id,
    }
    decision = decision_for_payload("accept_trade", payload, requires_approval=True)
    return {
        "status": APPROVAL_REQUIRED,
        "decision": asdict(decision),
        "message": "Trade acceptance always requires human approval",
    }
