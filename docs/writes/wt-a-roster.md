# WT-A — Roster Moves (add / drop / waiver)

> Prereq: read `00-BRIEF.md` first. You own **only** `mcp_server/writes/roster.py` and
> `tests/writes/test_roster.py`. Do not touch any other file.

## Scope

Implement 3 MCP tools + 3 1:1 CLI commands, all going through the shared `write_flow`:

| Tool | CLI | League method | Envelope type |
|---|---|---|---|
| `add_player(player_name, drop_player_name="", confirm_token="")` | `add <player> [--drop X] [--confirm-token T]` | `add_drop_player` | FREEAGENT |
| `drop_player(player_name, confirm_token="")` | `drop <player> [--confirm-token T]` | `add_drop_player` (drop-only) | FREEAGENT |
| `waiver_claim(player_name, drop_player_name="", confirm_token="")` | `waiver <player> [--drop X] [--confirm-token T]` | `waiver_claim` | WAIVER |

## Behavior per tool

**`add_player`**
1. `require_writes_enabled()` gate → return message if off.
2. `get_my_team_or_error()`.
3. `resolve_free_agent(league, player_name)` — must be a free agent / on waivers. Error if not.
4. If `drop_player_name`: `resolve_my_player(league, drop_player_name)` — must be on my roster.
5. **Roster-full pre-warning**: if no drop given and the roster has no open slot, include a clear
   warning line in the preview that ESPN will likely 409 unless a drop is added. (Still allow the
   user to proceed; `ESPNRosterFull` is mapped to a friendly message by `write_flow`.)
6. `write_flow(...)` with `add_player_id` = FA's `playerId`, `drop_player_id` = dropped player's
   `playerId` (or None). Title "Add Player" / "Add + Drop".

**`drop_player`**
1. Gate → my team → `resolve_my_player(league, player_name)` (must be on my roster).
2. `write_flow(...)` with `add_player_id=None, drop_player_id=<id>`. Title "Drop Player".

**`waiver_claim`**
1. Same resolution as `add_player` (add target is FA/waiver; optional drop from my roster).
2. `write_flow(...)` via `league.waiver_claim(team_id, add_player_id, drop_player_id, bid_amount=None)`.
   This league has **no FAAB** — pass `bid_amount=None` (payload `"bidAmount": null`). Title "Waiver Claim".
   Note in the result that waivers land **PENDING** (process later), not immediate.

## Preview lines (human-readable, above the JSON payload)

Build a short `lines` list for `fmt_txn_preview`, e.g.:
- `ADD  Pete Crow-Armstrong (OF, CHC) — free agent`
- `DROP Jake Burger (3B) — from your roster`
- (waiver) `Type: WAIVER (lands PENDING until waiver processing)`
- (roster full, no drop) `⚠️ Roster appears full and no drop specified — ESPN may reject (409). Add `--drop`.`

## Tests (`tests/writes/test_roster.py`, mocked HTTP only)

For each of add / add+drop / drop-only / waiver / waiver+drop:
- Assert payload via `dry_run=True`: correct `type`, `executionType: EXECUTE`, items
  (ADD has `toTeamId`=my team, DROP has `fromTeamId`=my team), `bidAmount: null` for waiver,
  `memberId` == SWID, host `lm-api-writes`, path ends `/transactions/`.
- Gate off → disabled message, `requests.post` never called.
- No token → preview string contains the 8-hex token; post never called.
- Correct token → exactly one post; `invalidate_league` effect (league singleton reset).
- 409 from ESPN → friendly `ESPNRosterFull` message (mock `requests.post` → 409).
- Validation failures: add a non-free-agent → error; drop a player not on my roster → error;
  in all failures, post never called.

Run: `uv run pytest tests/writes/test_roster.py` — must be green.

## Done criteria
- `roster.py` implements all 3 tools + 3 commands via shared helpers; no other file modified.
- All tests green. Report: tools added, edge cases covered, anything in the foundation contract
  that was missing or awkward.
