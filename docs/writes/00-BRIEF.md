# ESPN Fantasy Baseball — WRITE Support: Master Brief

> Read this first. It is the shared contract every worktree codes against.
> Your specific task is in `wt-a-roster.md`, `wt-b-lineup.md`, or `wt-c-trades.md`.

## What we are building

The MCP/CLI/`espn_api` stack is read-only today. We are adding the ability to **mutate
a real, live ESPN fantasy baseball league**: set lineups, add/drop players, submit waiver
claims, and propose/cancel trades.

Every mutation is a single authenticated `POST` to **one** endpoint
(`lm-api-writes.fantasy.espn.com/.../transactions/`); only the JSON body changes. The
verified payload spec lives at
`…/reverse-api-engineer/projects/espn-fantasy/WRITE_API_REFERENCE.md` — treat it as ground
truth for body shapes. The approved overall plan is at
`~/.claude/plans/joyful-yawning-conway.md`.

**Because these hit a live league, safety is the #1 requirement.** The default posture is
read-only; writes are gated behind an env switch AND a payload-bound confirm token. Both are
implemented in the foundation — you do not reimplement them, you call them.

## Architecture (post-foundation)

The foundation introduces a plugin package so operation work never touches shared files:

```
mcp_server/
  writes/
    __init__.py     # register_write_tools(mcp) / register_write_commands(app) — iterate modules
    _base.py        # SHARED helpers: gate, token, resolution, write_flow(), base formatters
    roster.py       # WT-A  (add / drop / waiver)        <-- one worktree owns this file
    lineup.py       # WT-B  (set lineup)                  <-- one worktree owns this file
    trades.py       # WT-C  (propose / cancel trade)      <-- one worktree owns this file
  tools.py          # foundation adds ONE call: register_write_tools(mcp)
  cli/__init__.py   # foundation adds ONE call: register_write_commands(app)
tests/writes/
    test_foundation.py   # foundation
    test_roster.py       # WT-A
    test_lineup.py       # WT-B
    test_trades.py       # WT-C
```

**Conflict rule:** a worktree edits ONLY its own `writes/<module>.py` and `tests/writes/test_<module>.py`.
Never touch `_base.py`, `__init__.py`, `tools.py`, `cli/__init__.py`, `formatters.py`,
`league.py`, or another worktree's module. If you think you need to, stop and flag it — it
means the foundation contract is missing something.

## Foundation deliverables (built in `main` before any worktree starts)

1. **HTTP** (`espn_api/requests/constant.py`, `espn_requests.py`): write host constants,
   `LEAGUE_WRITE_ENDPOINT`, `ESPNRosterFull` exception, `league_post()`, `checkWriteStatus()`
   (separate from the read status handler — never retries a mutation).
2. **Library write methods** (`espn_api/baseball/league.py`, `player.py`): the 5 methods below,
   each with a `dry_run` flag, plus `player.lineupSlotId` (raw int).
3. **Safety primitives** (`mcp_server/auth.py`, `config.py`): `ESPN_WRITE_ENABLED` env switch,
   `writes_enabled()`, `require_writes_enabled()`, `invalidate_league()`, `txn_token()`.
4. **`writes/_base.py`**: the shared helper contract below (this is what you call).
5. **`writes/{roster,lineup,trades}.py` stubs**: each defines empty `register_tools(mcp)` and
   `register_commands(app)` so imports succeed before worktrees fill them in.
6. **Registrar hooks** wired into `tools.py` and `cli/__init__.py`.
7. **`tests/writes/test_foundation.py`**: mocked-HTTP tests for the library methods + safety.

## Library method contract (`espn_api/baseball/league.py`)

`dry_run=True` returns the exact payload dict (no network). `dry_run=False` POSTs and returns
ESPN's parsed JSON. The payload built in both modes is identical (single code path), so the
preview a user approves is byte-for-byte what executes.

```python
league.set_lineup_moves(team_id, moves, dry_run=False)
    # moves: list[tuple[playerId:int, fromLineupSlotId:int, toLineupSlotId:int]]; swap = 2 tuples
league.add_drop_player(team_id, add_player_id=None, drop_player_id=None, dry_run=False)   # type FREEAGENT
league.waiver_claim(team_id, add_player_id, drop_player_id=None, bid_amount=None, dry_run=False)  # type WAIVER
league.propose_trade(from_team_id, to_team_id, send_player_ids, receive_player_ids,
                     comment='', expiration_date=None, dry_run=False)                     # type TRADE_PROPOSAL
league.cancel_trade(team_id, related_transaction_id, dry_run=False)                       # CANCEL
```

`memberId`, `scoringPeriodId`, `isLeagueManager`, envelope `type`/`executionType`, and item
shapes are all handled inside these methods per the verified spec. You pass IDs; the method
builds the body.

## Shared helper contract (`mcp_server/writes/_base.py`)

```python
# Gate (call FIRST in every tool/command)
require_writes_enabled() -> str | None      # returns the "writes disabled" message, or None if enabled

# Resolution (return (obj, error_message); on failure obj is None and you return the message)
get_my_team_or_error()                  -> tuple[team|None, str|None]
resolve_my_player(league, name)         -> tuple[player|None, str|None]   # must be on MY roster
resolve_free_agent(league, name)        -> tuple[player|None, str|None]   # must be FA / on waivers
resolve_other_team(league, name)        -> tuple[team|None, str|None]
resolve_team_player(team, name)         -> tuple[player|None, str|None]   # on that team's roster

# THE write flow — enforces gate + preview/token + execute + cache invalidation + ESPN error mapping
write_flow(confirm_token, *, build_payload, execute, render_preview, render_result) -> str
    # build_payload() -> dict     : call the league method with dry_run=True
    # execute()       -> dict     : call the SAME league method with dry_run=False (only runs if token matches)
    # render_preview(payload, token) -> str
    # render_result(response, payload) -> str
    # Behavior: token = txn_token(payload); if confirm_token != token -> return render_preview(...)
    #           else run execute(), invalidate_league(), return render_result(...).
    #           ESPNRosterFull / ESPNAccessDenied / ESPNUnknownError -> friendly error string.

# Base formatters (use directly or wrap)
fmt_txn_preview(title: str, lines: list[str], payload: dict, token: str) -> str
fmt_txn_result(title: str, response: dict) -> str    # reads status EXECUTED/PENDING/CANCELED, extracts trade id
```

### Canonical operation module shape (every worktree follows this)

```python
# mcp_server/writes/<module>.py
from . import _base
from .. import formatters          # only if you add op-specific formatting; base formatters live in _base
from ..config import get_league

def register_tools(mcp):
    @mcp.tool()
    def add_player(player_name: str, drop_player_name: str = "", confirm_token: str = "") -> str:
        """<one-liner>.

        SAFETY: modifies your REAL live league. Call WITHOUT confirm_token first to get a
        preview + token; show the human the exact move and get explicit approval; only then
        re-call with the confirm_token from the preview. Never invent/reuse a token. Never
        preview and execute in the same turn without explicit human approval.
        Args: ...
        """
        gate = _base.require_writes_enabled()
        if gate: return gate
        league = get_league()
        team, err = _base.get_my_team_or_error()
        if err: return err
        # ... resolve + validate players/slots/teams; return an error string on any failure ...
        return _base.write_flow(
            confirm_token,
            build_payload=lambda: league.add_drop_player(team.team_id, add_player_id=..., drop_player_id=..., dry_run=True),
            execute=lambda:       league.add_drop_player(team.team_id, add_player_id=..., drop_player_id=..., dry_run=False),
            render_preview=lambda payload, token: _base.fmt_txn_preview("Add Player", [...lines...], payload, token),
            render_result=lambda resp, payload:   _base.fmt_txn_result("Add Player", resp),
        )

def register_commands(app):
    import typer
    from ..cli import console     # shared Typer console
    @app.command()
    def add(player: str = typer.Argument(...), drop: str = typer.Option("", "--drop", "-d"),
            confirm_token: str = typer.Option("", "--confirm-token")):
        """Add a free agent (preview first; re-run with --confirm-token to execute)."""
        console.print(add_player(player, drop_player_name=drop, confirm_token=confirm_token))
```

CLI commands reuse the tool functions where practical so logic lives once. Keep tool ↔ CLI 1:1.

## Safety model (enforced by the foundation — do not weaken it)

1. **Env kill-switch**: nothing executes unless `ESPN_WRITE_ENABLED=true`. With it off, tools
   still exist (discoverable) but return the disabled message. `require_writes_enabled()` first.
2. **Payload-bound confirm token**: first call (no/empty `confirm_token`) returns a preview that
   renders the literal JSON payload + an 8-hex token derived from that payload. Execution only
   happens when the caller echoes the exact token. If anything changed (player resolved
   differently, scoring period rolled over), the token differs → forced re-preview.
3. **Preview == execute**: guaranteed by building the payload via `dry_run=True` and executing
   the identical call with `dry_run=False`.
4. **Cache invalidation** after a successful write (`invalidate_league()`), so later reads reflect it.

## Testing rules (ALL worktrees)

- **No real API calls, ever, in tests.** Mock at the `requests.post` boundary (repo already uses
  `requests_mock`; see `tests/espn_requests/`). Assert the exact JSON body matches the spec.
- Cover, per operation: payload correctness (envelope `type`/`executionType`, item shapes,
  ADD `toTeamId` / DROP `fromTeamId`, lineup `from/toLineupSlotId`, `bidAmount: null`,
  trade `expirationDate`/`comment`, cancel `relatedTransactionId`); gate-off → no post +
  disabled message; no-token → preview contains token + no post; matching token → exactly one
  post + cache invalidated; bad token / failed validation → error string + no post.
- `uv run pytest tests/writes/test_<yourmodule>.py` must pass before you report done.
- Do **not** run the live-verification procedure (that is owner-only, real moves, gated).

## Risks to respect (from the spec)

- **Trade direction** (`fromTeamId`/`toTeamId` per item) is logically built but only single-leg
  was captured — WT-C must build send/receive exactly as documented and lean on payload tests;
  real confirmation is the owner's propose+cancel live test.
- **`expirationDate` format** assumed `…T…:….000Z` — WT-C: match the spec doc.
- **Trade accept/reject** were NOT captured — OUT OF SCOPE. Do not implement from guesswork.
- **409** = roster full / illegal move — surfaced via `ESPNRosterFull`; WT-A pre-warns when
  roster is full and no drop is given.
```
