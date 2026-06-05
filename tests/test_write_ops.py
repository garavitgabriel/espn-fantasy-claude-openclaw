from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from unittest import TestCase, mock

from mcp_server import write_ops
from mcp_server.guardrails import (
    BudgetExceededError,
    IllegalPositionError,
    ProtectedPlayerError,
    WritesDisabledError,
    dry_run_enabled,
)


class TestWriteOps(TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        patcher = mock.patch.dict(
            os.environ,
            {
                "WRITES_ENABLED": "true",
                "DRY_RUN": "true",
                "WRITE_LOG_PATH": f"{self.tmpdir.name}/writes.jsonl",
            },
            clear=False,
        )
        patcher.start()
        self.addCleanup(patcher.stop)

        self.team = SimpleNamespace(
            team_id=7,
            roster=[
                SimpleNamespace(playerId=1, name="Core Star", total_points=99, eligibleSlots=["OF"], position="OF"),
                SimpleNamespace(playerId=2, name="Bench Bat", total_points=10, eligibleSlots=["1B"], position="1B"),
            ],
        )
        self.league = SimpleNamespace(
            scoringPeriodId=88,
            set_lineup=mock.Mock(return_value={"ok": True, "kind": "lineup"}),
            add_drop_player=mock.Mock(return_value={"ok": True, "kind": "add_drop"}),
            verify_auth=mock.Mock(return_value={"ok": True}),
        )

    def test_verify_auth_passthrough(self):
        result = write_ops.verify_auth(self.league)
        self.assertEqual(result, {"ok": True})
        self.league.verify_auth.assert_called_once_with()

    def test_set_lineup_dry_run_simulated_success(self):
        result = write_ops.set_lineup(
            self.league,
            self.team,
            [{"playerId": 2, "type": "LINEUP", "fromLineupSlotId": 16, "toLineupSlotId": 1}],
        )
        self.assertEqual(result["status"], "simulated_success")
        self.assertTrue(result["decision"]["dry_run"])
        self.league.set_lineup.assert_not_called()

    def test_set_lineup_illegal_position_blocked(self):
        with self.assertRaises(IllegalPositionError):
            write_ops.set_lineup(
                self.league,
                self.team,
                [{"playerId": 2, "type": "LINEUP", "fromLineupSlotId": 16, "toLineupSlotId": 14}],
            )

    def test_set_lineup_protected_bench_blocked(self):
        with self.assertRaises(ProtectedPlayerError):
            write_ops.set_lineup(
                self.league,
                self.team,
                [{"playerId": 1, "type": "LINEUP", "fromLineupSlotId": 5, "toLineupSlotId": 16}],
                protected_players=["Core Star"],
            )

    def test_add_drop_budget_exceeded(self):
        add_player = SimpleNamespace(playerId=55, name="New Guy")
        drop_player = SimpleNamespace(playerId=2, name="Bench Bat")
        with self.assertRaises(BudgetExceededError):
            write_ops.add_drop(self.league, self.team, add_player, drop_player, remaining_moves=0)

    def test_add_drop_protected_drop_blocked(self):
        add_player = SimpleNamespace(playerId=55, name="New Guy")
        drop_player = SimpleNamespace(playerId=1, name="Core Star")
        with self.assertRaises(ProtectedPlayerError):
            write_ops.add_drop(
                self.league,
                self.team,
                add_player,
                drop_player,
                remaining_moves=1,
                protected_players=["Core Star"],
            )

    def test_add_drop_dry_run_simulated_success(self):
        add_player = SimpleNamespace(playerId=55, name="New Guy")
        drop_player = SimpleNamespace(playerId=2, name="Bench Bat")
        result = write_ops.add_drop(
            self.league,
            self.team,
            add_player,
            drop_player,
            remaining_moves=1,
            protected_players=["Core Star"],
        )
        self.assertEqual(result["status"], "simulated_success")
        self.league.add_drop_player.assert_not_called()

    def test_trade_actions_require_approval(self):
        proposal = write_ops.propose_trade(self.league, self.team, 3, [1], [2])
        acceptance = write_ops.accept_trade(self.league, self.team, 999)
        self.assertEqual(proposal["status"], "approval_required")
        self.assertEqual(acceptance["status"], "approval_required")
        self.assertTrue(proposal["decision"]["requires_approval"])
        self.assertTrue(acceptance["decision"]["requires_approval"])

    def test_writes_disabled_blocks_execution(self):
        with mock.patch.dict(os.environ, {"WRITES_ENABLED": "false"}, clear=False):
            add_player = SimpleNamespace(playerId=55, name="New Guy")
            drop_player = SimpleNamespace(playerId=2, name="Bench Bat")
            with self.assertRaises(WritesDisabledError):
                write_ops.add_drop(self.league, self.team, add_player, drop_player, remaining_moves=1)

    def test_dry_run_default_is_true(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(dry_run_enabled())
