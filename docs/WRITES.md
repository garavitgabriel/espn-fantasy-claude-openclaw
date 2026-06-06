# Writes — Enabling & Live Verification (owner only)

> ⚠️ **These commands change your REAL ESPN fantasy league in real time.** There is no
> sandbox. Read this whole file before running anything with `ESPN_WRITE_ENABLED=true`.

Write support is **off by default** — the MCP and CLI are read-only until you opt in.
Two layers protect the league:

1. **Env kill-switch** — nothing executes unless `ESPN_WRITE_ENABLED=true`.
2. **Confirm token** — every write previews first and returns an 8-hex token bound to the
   exact request body. Execution happens only when you echo that token back. If anything
   changed since the preview, the token won't match and you'll get a fresh preview.

## Enabling writes

```bash
export ESPN_WRITE_ENABLED=true     # then restart the MCP server / new CLI shell
```

Unset it (or set `false`) to return to read-only. In Claude Desktop / Cowork, add
`ESPN_WRITE_ENABLED=true` to the MCP server's `env` block and restart.

## The two-step flow (every write)

**CLI** — run once with no `--confirm-token` to see the preview + token, then re-run with it:

```bash
espn drop "Some Player"                       # prints preview + a token like a1b2c3d4
espn drop "Some Player" --confirm-token a1b2c3d4   # executes
```

**MCP (Claude)** — the tool returns a preview; Claude must show you the exact move and the
literal JSON body, get your explicit approval, then call again with `confirm_token`. Claude
is instructed never to invent/reuse a token or preview-and-execute in the same turn without
your approval.

## Owner live-verification recipes (reversible / net-zero)

Run these once to confirm the real ESPN payloads are accepted. Each is reversible. Do them
one at a time and check your ESPN app between steps.

### 1. Lineup toggle + revert (fully reversible, zero roster change)
```bash
espn lineup "<a bench hitter>" UTIL            # preview → note token
espn lineup "<a bench hitter>" UTIL --confirm-token <token>   # EXECUTED
# then move them back:
espn lineup "<same player>" BE --confirm-token <token-from-new-preview>
```
Expect `status: EXECUTED`. Confirm the slot changed, then changed back, in the ESPN app.

### 2. Net-zero add + drop (costs one acquisition)
```bash
espn add "<a low-owned free agent>"            # preview → token; EXECUTE
# then immediately drop the same player to restore your roster:
espn drop "<same player>"                       # preview → token; EXECUTE
```
Expect `status: EXECUTED` on both. Roster returns to its original shape (one acquisition is
spent against your weekly limit — cosmetic).

### 3. Trade propose + cancel (no roster change)
```bash
espn propose-trade --to "<friendly team>" --give "<your player>" --receive "<their player>"
#   preview → token; EXECUTE → returns status PENDING + a proposal id
espn cancel-trade <proposal-id>                 # preview → token; EXECUTE → CANCELED
```
Confirms trade item direction (give vs receive) and the cancel path. Cancel before the other
team accepts. **Do this with a co-owner who won't accept**, or be ready to cancel instantly.

### 4. Waiver (only with a real intended claim)
Waivers land **PENDING** and process at the next waiver run — not immediately reversible the
way the others are. Only run `espn waiver "<player>"` when you actually want the claim, or
when you've confirmed you can cancel a pending waiver first.

## After verifying

Once you've confirmed the real payloads are accepted, snapshot the confirmed request bodies
into the test suite (`tests/writes/`) so the contract is locked against regressions. Then
decide whether to leave `ESPN_WRITE_ENABLED` on or keep it off between sessions.

## Reference
- Verified payload spec: `docs/writes/00-BRIEF.md` (and the upstream `WRITE_API_REFERENCE.md`).
- Library methods: `espn_api/baseball/league.py` (`add_drop_player`, `waiver_claim`,
  `set_lineup_moves`, `propose_trade`, `cancel_trade`).
- Safety flow: `mcp_server/writes/_base.py` (`write_flow`), `mcp_server/config.py`
  (`require_writes_enabled`, `txn_token`, `invalidate_league`).
