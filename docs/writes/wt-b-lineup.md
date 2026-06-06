# WT-B — Set Lineup (activate / bench / swap)

> Prereq: read `00-BRIEF.md` first. You own **only** `mcp_server/writes/lineup.py` and
> `tests/writes/test_lineup.py`. Do not touch any other file.

## Scope

One MCP tool + one 1:1 CLI command, via the shared `write_flow`, using `league.set_lineup_moves`.

| Tool | CLI | League method | Envelope type |
|---|---|---|---|
| `set_lineup(player_name, to_slot, swap_with="", confirm_token="")` | `lineup <player> <to_slot> [--swap-with X] [--confirm-token T]` | `set_lineup_moves` | ROSTER |

`to_slot` and `swap_with` are at the tool boundary expressed as **position names** (e.g. `UTIL`,
`P`, `BE`, `SP`, `RP`, `C`, `OF`, …). Convert names → numeric `lineupSlotId` using the two-way
`POSITION_MAP` in `espn_api/baseball/constant.py`.

## Slot id reference (from the verified spec)

`0=C 1=1B 2=2B 3=3B 4=SS 5=OF 6=MI 7=CI 8=LF 9=CF 10=RF 11=DH 12=UTIL 13=P 14=SP 15=RP 16=BE 17=IL`
(Confirmed in capture: 12=UTIL, 13=P, 16=BE.)

## Behavior

1. `require_writes_enabled()` gate.
2. `get_my_team_or_error()`.
3. `resolve_my_player(league, player_name)` — must be on my roster. Read its current slot from
   the raw `player.lineupSlotId` (added by the foundation) → this is `fromLineupSlotId`.
4. Map `to_slot` name → `toLineupSlotId`. Validate the target is in `player.eligibleSlots`
   (the eligible-slots check uses the position-name list; map appropriately). Error if ineligible.
5. **Single move vs swap:**
   - No `swap_with`: build one LINEUP item `(playerId, fromSlotId, toSlotId)`.
     - If the target slot is already occupied by another starter, reject with a clear message
       telling the user to use `--swap-with` (moving into an occupied slot is illegal). Detect by
       scanning `team.roster` for a player whose current `lineupSlotId == toLineupSlotId`.
   - With `swap_with`: `resolve_my_player(league, swap_with)`; build **two** LINEUP items —
     the named player → `to_slot`, and the swap partner → the named player's original slot.
     Validate each player is eligible for the slot it is moving into.
6. `write_flow(...)` → `league.set_lineup_moves(team.team_id, moves, dry_run=…)`.
   `moves` is a list of `(playerId, fromSlotId, toSlotId)` tuples (1 for a move, 2 for a swap).
   Title "Set Lineup".

LINEUP items have **no** `fromTeamId/toTeamId`. Lineup transactions return EXECUTED immediately.

## Preview lines

- `Mason Miller (RP) : BE (16) → P (13)`
- swap: also `Tarik Skubal (SP) : P (13) → BE (16)`
- Show both the position name and numeric id so the user can audit.

## Tests (`tests/writes/test_lineup.py`, mocked HTTP only)

- Single move payload: `type: ROSTER`, one item with correct `from/toLineupSlotId`, no team ids,
  `memberId` == SWID, host `lm-api-writes`.
- Swap payload: two LINEUP items with mirrored slots.
- Name→slot mapping correctness for several positions (UTIL/P/BE/SP/RP at minimum).
- Eligibility rejection: move a player to a slot not in `eligibleSlots` → error, no post.
- Occupied-slot rejection without `--swap-with` → error, no post.
- Gate off → disabled message, no post.
- No token → preview with token, no post. Correct token → exactly one post + cache invalidated.

Use fixtures with a fake `league`/`team`/`player` exposing `team_id`, `roster`, `playerId`,
`lineupSlotId`, `eligibleSlots`. Run: `uv run pytest tests/writes/test_lineup.py` — must be green.

## Done criteria
- `lineup.py` implements the tool + command + slot mapping + swap/occupancy logic via shared
  helpers; no other file modified. All tests green. Report mapping edge cases and any gaps in the
  foundation contract (esp. whether `player.lineupSlotId` and `eligibleSlots` were sufficient).
