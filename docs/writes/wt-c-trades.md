# WT-C — Trades (propose / cancel)

> Prereq: read `00-BRIEF.md` first. You own **only** `mcp_server/writes/trades.py` and
> `tests/writes/test_trades.py`. Do not touch any other file.
> **Accept / reject are OUT OF SCOPE** (payloads were never captured — do not implement them).

## Scope

Two MCP tools + two 1:1 CLI commands, via the shared `write_flow`.

| Tool | CLI | League method | Envelope |
|---|---|---|---|
| `propose_trade(to_team, give_players, receive_players, comment="", confirm_token="")` | `propose-trade --to T --give "A,B" --receive "C" [--comment ...] [--confirm-token T]` | `propose_trade` | type TRADE_PROPOSAL, EXECUTE |
| `cancel_trade(transaction_id, confirm_token="")` | `cancel-trade <transaction_id> [--confirm-token T]` | `cancel_trade` | type TRADE_PROPOSAL, CANCEL |

`give_players` / `receive_players` are comma-separated player names at the tool boundary; split
and strip them.

## Behavior — `propose_trade`

1. `require_writes_enabled()` gate.
2. `get_my_team_or_error()` → this is `from_team_id` (the proposing team).
3. `resolve_other_team(league, to_team)` → the counterparty (`to_team_id`).
4. For each give name: `resolve_my_player(league, name)` — must be on MY roster → collect playerIds.
5. For each receive name: `resolve_team_player(other_team, name)` — must be on the OTHER team's
   roster → collect playerIds.
6. `write_flow(...)` → `league.propose_trade(from_team_id, to_team_id, send_player_ids=<give ids>,
   receive_player_ids=<receive ids>, comment=comment, dry_run=…)`.
   - The method builds items per the spec: each given player `{type:TRADE, fromTeamId:me, toTeamId:other}`,
     each received player `{type:TRADE, fromTeamId:other, toTeamId:me}`, plus `expirationDate`
     (~2 days out, ISO `…T…:….000Z`) and `comment`.
   - Returns PENDING + a proposal `id`. Title "Propose Trade". `render_result` must surface the
     returned proposal `id` prominently (the user needs it to cancel).

## Behavior — `cancel_trade`

1. Gate → `get_my_team_or_error()` (CANCEL still carries `teamId`).
2. `transaction_id` is the proposal id (from a `propose_trade` result or `get_recent_activity`).
   No roster validation.
3. `write_flow(...)` → `league.cancel_trade(team.team_id, related_transaction_id=transaction_id, dry_run=…)`.
   Builds CANCEL envelope with empty items + `relatedTransactionId`. Returns CANCELED. Title "Cancel Trade".

## Preview lines

- `GIVE:    Spencer Strider (SP) → <Other Team>`
- `RECEIVE: Bobby Witt Jr. (SS) ← <Other Team>`
- `Expires: 2026-06-08T…Z   Comment: "<...>"`
- cancel: `Cancel pending proposal <transaction_id>`

## Risks (must handle exactly per spec)

- **Item direction** is the critical correctness point: give = `fromTeamId:me,toTeamId:other`;
  receive = `fromTeamId:other,toTeamId:me`. Verify this precisely in tests against
  `WRITE_API_REFERENCE.md` §5. Only single-leg was captured live, so your payload tests are the
  guardrail until the owner runs the propose+cancel live test.
- **`expirationDate`** format = `%Y-%m-%dT%H:%M:%S.000Z`. The library method defaults it; assert
  the format in tests (regex), not an exact timestamp (time is non-deterministic — see below).

## Tests (`tests/writes/test_trades.py`, mocked HTTP only)

- Propose payload: `type: TRADE_PROPOSAL`, `executionType: EXECUTE`, one TRADE item per give/receive
  with correct mirrored `fromTeamId`/`toTeamId`, `comment` present, `expirationDate` matches the ISO
  regex, `memberId` == SWID, host `lm-api-writes`.
- Multi-player proposal (2-for-1) builds the right number/direction of items.
- Cancel payload: `executionType: CANCEL`, empty `items`, correct `relatedTransactionId`.
- `render_result` extracts and shows the proposal `id` from a mocked PENDING response.
- Gate off → disabled message, no post. No token → preview with token, no post. Correct token →
  exactly one post + cache invalidated. Validation failures (give player not on my roster, receive
  player not on other team, unknown team) → error string, no post.
- **Determinism note:** the foundation may make `expiration_date` injectable for tests (pass an
  explicit value) so the payload token is stable; if so, use that in token-match tests.

Run: `uv run pytest tests/writes/test_trades.py` — must be green.

## Done criteria
- `trades.py` implements both tools + both commands via shared helpers; no other file modified.
  Accept/reject NOT added. All tests green. Report item-direction handling and any foundation gaps.
