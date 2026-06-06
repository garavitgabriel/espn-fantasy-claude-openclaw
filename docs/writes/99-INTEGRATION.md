# Phase 3 — Integration & Release (run in `main` after WT-A/B/C merge)

Done by the driver in the main session once the three operation worktrees are merged.

1. **Merge order:** WT-A, WT-B, WT-C (any order — they own disjoint files). Rebase each on
   latest `master` before merge. Expect zero conflicts (separate module + test files).
2. **Full suite:** `uv run pytest` — all green, including each `tests/writes/test_*.py`.
3. **Smoke the registrars:** start `uv run espn-mcp` and confirm the 6 write tools appear; run
   `uv run espn --help` and confirm `add`, `drop`, `waiver`, `lineup`, `propose-trade`,
   `cancel-trade` are listed. With `ESPN_WRITE_ENABLED` unset, each must return the disabled
   message (no network).
4. **Docs:**
   - `CLAUDE.md`: add the 6 tools to the Tool ↔ CLI ↔ Formatter table; add `ESPN_WRITE_ENABLED`
     to the env-var table; add a "Writes & Safety" section.
   - `README.md`: mirror the table + env var; document the preview→confirm-token flow.
   - Keep `docs/WRITES.md` (owner live-verification procedure) authoritative for real moves.
5. **`server.py` instructions:** note that gated write tools exist and require explicit human
   confirmation; keep the read-first guidance.
6. **Owner live verification** (manual, real moves, `ESPN_WRITE_ENABLED=true`): per `docs/WRITES.md`
   — lineup toggle+revert; net-zero add-then-drop; propose+cancel; waiver only with a real claim.
   After confirming real payloads, snapshot them into the test suite to lock the contract.

## docs/WRITES.md (owner-only) must contain
- Big warning: these make REAL moves on the live league.
- How to enable: `export ESPN_WRITE_ENABLED=true` then restart the server/CLI.
- The two-step flow: run once for a preview + token, then re-run echoing the token.
- The 4 reversible verification recipes and how to undo each.
