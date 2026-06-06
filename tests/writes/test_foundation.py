"""Foundation tests for write support — HTTP layer, library methods, safety primitives.

All network access is mocked. No real ESPN calls are ever made.
"""

import re
from unittest import TestCase, mock

import requests_mock

from espn_api.baseball import League
from espn_api.requests.espn_requests import (
    EspnFantasyRequests,
    ESPNRosterFull,
    ESPNAccessDenied,
    ESPNUnknownError,
)
import mcp_server.config as cfg
from mcp_server.writes import _base


WRITE_URL = (
    "https://lm-api-writes.fantasy.espn.com/apis/v3/games/flb/"
    "seasons/2026/segments/0/leagues/123/transactions/"
)
SWID = "{EFFBA4A3-C6FC-430F-A4ED-46A70E1CC95B}"


def _make_league():
    """A League with no network fetch; scoringPeriodId set manually."""
    league = League(
        league_id=123, year=2026, espn_s2="s2", swid=SWID, fetch_league=False
    )
    league.scoringPeriodId = 74
    return league


# --- HTTP layer --------------------------------------------------------------

class HttpWriteLayerTest(TestCase):
    def setUp(self):
        self.req = EspnFantasyRequests(
            sport="mlb", year=2026, league_id=123,
            cookies={"espn_s2": "s2", "SWID": SWID},
        )

    def test_write_endpoint_uses_writes_host(self):
        self.assertIn("lm-api-writes.fantasy.espn.com", self.req.LEAGUE_WRITE_ENDPOINT)
        self.assertNotIn("lm-api-reads", self.req.LEAGUE_WRITE_ENDPOINT)
        self.assertTrue(self.req.LEAGUE_WRITE_ENDPOINT.endswith("/leagues/123"))

    @requests_mock.Mocker()
    def test_league_post_sends_headers_and_cookies(self, m):
        m.post(WRITE_URL, json={"id": "abc", "status": "EXECUTED"}, status_code=200)
        out = self.req.league_post({"hello": "world"})
        self.assertEqual(out["status"], "EXECUTED")
        last = m.last_request
        self.assertEqual(last.headers["x-fantasy-platform"], "espn-fantasy-web")
        self.assertEqual(last.headers["x-fantasy-source"], "kona")
        self.assertIn("application/json", last.headers["content-type"])
        self.assertEqual(last.json(), {"hello": "world"})

    @requests_mock.Mocker()
    def test_409_raises_roster_full(self, m):
        m.post(WRITE_URL, text="roster full", status_code=409)
        with self.assertRaises(ESPNRosterFull):
            self.req.league_post({"x": 1})

    @requests_mock.Mocker()
    def test_401_raises_access_denied_without_retry(self, m):
        m.post(WRITE_URL, text="nope", status_code=401)
        with self.assertRaises(ESPNAccessDenied):
            self.req.league_post({"x": 1})
        # Exactly one POST — a mutation must never be retried.
        self.assertEqual(m.call_count, 1)

    @requests_mock.Mocker()
    def test_500_raises_unknown(self, m):
        m.post(WRITE_URL, text="boom", status_code=500)
        with self.assertRaises(ESPNUnknownError):
            self.req.league_post({"x": 1})


# --- Library payload construction (dry_run) ----------------------------------

class PayloadConstructionTest(TestCase):
    def setUp(self):
        self.league = _make_league()

    def test_envelope_common_fields(self):
        p = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        self.assertEqual(p["isLeagueManager"], False)
        self.assertEqual(p["teamId"], 8)
        self.assertEqual(p["memberId"], SWID)
        self.assertEqual(p["scoringPeriodId"], 74)
        self.assertEqual(p["executionType"], "EXECUTE")

    def test_add_only(self):
        p = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        self.assertEqual(p["type"], "FREEAGENT")
        self.assertEqual(p["items"], [{"playerId": 42417, "type": "ADD", "toTeamId": 8}])

    def test_add_drop(self):
        p = self.league.add_drop_player(8, add_player_id=42417, drop_player_id=999, dry_run=True)
        self.assertEqual(p["items"], [
            {"playerId": 42417, "type": "ADD", "toTeamId": 8},
            {"playerId": 999, "type": "DROP", "fromTeamId": 8},
        ])

    def test_drop_only(self):
        p = self.league.add_drop_player(8, drop_player_id=999, dry_run=True)
        self.assertEqual(p["items"], [{"playerId": 999, "type": "DROP", "fromTeamId": 8}])

    def test_waiver_has_null_bid(self):
        p = self.league.waiver_claim(8, add_player_id=32367, drop_player_id=42457, dry_run=True)
        self.assertEqual(p["type"], "WAIVER")
        self.assertIsNone(p["bidAmount"])
        self.assertEqual(p["items"][0], {"playerId": 32367, "type": "ADD", "toTeamId": 8})
        self.assertEqual(p["items"][1], {"playerId": 42457, "type": "DROP", "fromTeamId": 8})

    def test_lineup_single_move(self):
        p = self.league.set_lineup_moves(8, [(4307825, 16, 13)], dry_run=True)
        self.assertEqual(p["type"], "ROSTER")
        self.assertEqual(p["items"], [{
            "playerId": 4307825, "type": "LINEUP",
            "fromLineupSlotId": 16, "toLineupSlotId": 13,
        }])
        # Lineup items carry no team ids.
        self.assertNotIn("toTeamId", p["items"][0])
        self.assertNotIn("fromTeamId", p["items"][0])

    def test_lineup_swap(self):
        p = self.league.set_lineup_moves(8, [(42457, 16, 12), (42470, 12, 16)], dry_run=True)
        self.assertEqual(len(p["items"]), 2)

    def test_propose_trade_directions(self):
        p = self.league.propose_trade(
            8, 11, send_player_ids=[42488], receive_player_ids=[4872587],
            comment="hi", dry_run=True,
        )
        self.assertEqual(p["type"], "TRADE_PROPOSAL")
        self.assertEqual(p["comment"], "hi")
        # send: leaves my team (8 -> 11); receive: comes to me (11 -> 8)
        self.assertEqual(p["items"][0], {"playerId": 42488, "type": "TRADE", "fromTeamId": 8, "toTeamId": 11})
        self.assertEqual(p["items"][1], {"playerId": 4872587, "type": "TRADE", "fromTeamId": 11, "toTeamId": 8})
        self.assertRegex(p["expirationDate"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z$")

    def test_cancel_trade(self):
        p = self.league.cancel_trade(8, related_transaction_id="uuid-123", dry_run=True)
        self.assertEqual(p["executionType"], "CANCEL")
        self.assertEqual(p["items"], [])
        self.assertEqual(p["relatedTransactionId"], "uuid-123")

    @requests_mock.Mocker()
    def test_execute_posts_to_writes_host(self, m):
        m.post(WRITE_URL, json={"id": "t1", "status": "EXECUTED"}, status_code=200)
        out = self.league.add_drop_player(8, add_player_id=42417, dry_run=False)
        self.assertEqual(out["status"], "EXECUTED")
        self.assertEqual(m.last_request.json()["items"][0]["playerId"], 42417)


# --- Safety primitives -------------------------------------------------------

class SafetyPrimitivesTest(TestCase):
    def test_token_is_deterministic_and_payload_bound(self):
        a = cfg.txn_token({"x": 1, "y": 2})
        b = cfg.txn_token({"y": 2, "x": 1})  # key order independent
        self.assertEqual(a, b)
        self.assertNotEqual(a, cfg.txn_token({"x": 1, "y": 3}))
        self.assertEqual(len(a), 8)

    def test_require_writes_enabled_message_when_off(self):
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", False):
            self.assertIsNotNone(cfg.require_writes_enabled())

    def test_require_writes_enabled_none_when_on(self):
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", True):
            self.assertIsNone(cfg.require_writes_enabled())


# --- write_flow --------------------------------------------------------------

class WriteFlowTest(TestCase):
    def _run(self, confirm_token):
        executed = {"called": False}

        def execute():
            executed["called"] = True
            return {"id": "t9", "status": "EXECUTED"}

        out = _base.write_flow(
            confirm_token,
            build_payload=lambda: {"type": "FREEAGENT", "teamId": 8},
            execute=execute,
            render_preview=lambda payload, token: f"PREVIEW:{token}",
            render_result=lambda resp, payload: f"RESULT:{resp['status']}",
        )
        return out, executed["called"]

    def test_gate_off_blocks(self):
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", False):
            out, called = self._run("anything")
        self.assertIn("DISABLED", out)
        self.assertFalse(called)

    def test_no_token_returns_preview_no_execute(self):
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", True):
            out, called = self._run("")
        self.assertTrue(out.startswith("PREVIEW:"))
        self.assertFalse(called)

    def test_wrong_token_returns_preview_no_execute(self):
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", True):
            out, called = self._run("deadbeef")
        self.assertTrue(out.startswith("PREVIEW:"))
        self.assertFalse(called)

    def test_matching_token_executes_and_invalidates(self):
        token = cfg.txn_token({"type": "FREEAGENT", "teamId": 8})
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", True), \
             mock.patch.object(_base, "invalidate_league") as inval:
            out, called = self._run(token)
        self.assertEqual(out, "RESULT:EXECUTED")
        self.assertTrue(called)
        inval.assert_called_once()

    def test_espn_error_mapped_friendly(self):
        token = cfg.txn_token({"type": "FREEAGENT", "teamId": 8})

        def execute():
            raise ESPNRosterFull("roster full")

        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", True), \
             mock.patch.object(_base, "invalidate_league"):
            out = _base.write_flow(
                token,
                build_payload=lambda: {"type": "FREEAGENT", "teamId": 8},
                execute=execute,
                render_preview=lambda p, t: "PREVIEW",
                render_result=lambda r, p: "RESULT",
            )
        self.assertIn("roster full", out)
        self.assertTrue(out.startswith("❌"))
