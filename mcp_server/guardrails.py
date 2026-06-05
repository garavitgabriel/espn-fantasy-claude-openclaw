"""Central write guardrails for ESPN MCP write actions.

Safe-by-default:
- WRITES_ENABLED=false blocks all write execution paths server-wide.
- DRY_RUN=true returns simulated success and logs the intended payload.
- Protected players cannot be benched or dropped without human approval.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

from espn_api.baseball.constant import POSITION_MAP, normalize_position_label


class GuardrailError(Exception):
    """Base class for write safety failures."""


class WritesDisabledError(GuardrailError):
    pass


class BudgetExceededError(GuardrailError):
    pass


class ProtectedPlayerError(GuardrailError):
    pass


class IllegalPositionError(GuardrailError):
    pass


@dataclass
class GuardrailDecision:
    allowed: bool
    dry_run: bool
    reason: str
    requires_approval: bool = False
    payload: dict | None = None


DEFAULT_PROTECTED_COUNT = 5
DEFAULT_DRY_RUN = True
DEFAULT_WRITES_ENABLED = False
DEFAULT_LOG_PATH = Path("write_actions.jsonl")


def env_flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def writes_enabled() -> bool:
    return env_flag("WRITES_ENABLED", DEFAULT_WRITES_ENABLED)


def dry_run_enabled() -> bool:
    return env_flag("DRY_RUN", DEFAULT_DRY_RUN)


def write_log_path() -> Path:
    raw = os.environ.get("WRITE_LOG_PATH", str(DEFAULT_LOG_PATH))
    return Path(raw)


def get_protected_players(team=None, configured: Sequence[str] | None = None) -> list[str]:
    if configured:
        return [str(name).strip() for name in configured if str(name).strip()]
    if team is None:
        return []

    roster = list(getattr(team, "roster", []) or [])
    ranked = sorted(
        roster,
        key=lambda player: getattr(player, "total_points", 0) or 0,
        reverse=True,
    )
    return [getattr(player, "name", "") for player in ranked[:DEFAULT_PROTECTED_COUNT] if getattr(player, "name", "")]


def ensure_writes_enabled() -> None:
    if not writes_enabled():
        raise WritesDisabledError("Writes are disabled by WRITES_ENABLED=false")


def ensure_budget_remaining(remaining_moves: int | None, requested_moves: int = 1) -> None:
    if remaining_moves is None:
        return
    if requested_moves > remaining_moves:
        raise BudgetExceededError(
            f"Move budget exceeded: requested {requested_moves}, remaining {remaining_moves}"
        )


def ensure_not_protected(player_name: str, protected_players: Iterable[str], action: str) -> None:
    protected = {name.casefold() for name in protected_players}
    if player_name.casefold() in protected:
        raise ProtectedPlayerError(
            f"{action} requires approval because '{player_name}' is protected"
        )


def ensure_position_legal(player, to_slot: int) -> None:
    slot_label = POSITION_MAP.get(to_slot)
    if not slot_label:
        raise IllegalPositionError(f"Unknown lineup slot id: {to_slot}")

    normalized_slot = normalize_position_label(slot_label)
    eligible = {
        normalize_position_label(pos)
        for pos in (getattr(player, "eligibleSlots", None) or [])
        if normalize_position_label(pos)
    }
    eligible.add(normalize_position_label(getattr(player, "position", None)))

    if normalized_slot not in eligible and normalized_slot not in {"BE", "IL"}:
        raise IllegalPositionError(
            f"Illegal position move: {getattr(player, 'name', 'Unknown')} cannot move to {slot_label}"
        )


def log_dry_run(action: str, payload: dict, response: dict | None = None) -> Path:
    path = write_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "payload": payload,
        "response": response or {"status": "simulated_success"},
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, sort_keys=True) + "\n")
    return path


def decision_for_payload(action: str, payload: dict, *, requires_approval: bool = False) -> GuardrailDecision:
    if dry_run_enabled():
        log_dry_run(action, payload)
        return GuardrailDecision(
            allowed=True,
            dry_run=True,
            reason="DRY_RUN=true — simulated success, payload logged locally",
            requires_approval=requires_approval,
            payload=payload,
        )
    return GuardrailDecision(
        allowed=True,
        dry_run=False,
        reason="Write allowed",
        requires_approval=requires_approval,
        payload=payload,
    )
