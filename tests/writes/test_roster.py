"""WT-A tests — roster moves (add / drop / waiver). See docs/writes/wt-a-roster.md.

All network access is mocked at the requests.post boundary; no real ESPN call is ever
made and ESPN_WRITE_ENABLED is never set on the real environment (it is patched per-test).
"""

from types import SimpleNamespace
from unittest import TestCase, mock

import requests_mock

from espn_api.baseball import League
import mcp_server.config as cfg
from mcp_server.writes import _base, roster


WRITE_URL = (
    "https://lm-api-writes.fantasy.espn.com/apis/v3/games/flb/"
    "seasons/2026/segments/0/leagues/123/transactions/"
)
SWID = "{EFFBA4A3-C6FC-430F-A4ED-46A70E1CC95B}"
OK = {"id": "txn-1", "status": "EXECUTED"}


def _player(pid, name, position="OF", pro="CHC", lineup_slot="BE"):
    return SimpleNamespace(
        playerId=pid, name=name, position=position, proTeam=pro, lineupSlot=lineup_slot
    )


def _make_league():
    league = League(league_id=123, year=2026, espn_s2="s2", swid=SWID, fetch_league=False)
    league.scoringPeriodId = 74
    return league


class RosterToolTest(TestCase):
    def setUp(self):
        self.league = _make_league()
        # Plenty of capacity by default so the roster-full pre-warning stays quiet.
        self.league.espn_request.get_league = mock.Mock(
            return_value={"settings": {"rosterSettings": {"lineupSlotCounts": {"16": 30}}}}
        )
        self.team = SimpleNamespace(
            team_id=8,
            team_name="My Team",
            roster=[_player(i, f"P{i}", lineup_slot="BE") for i in range(3)],
        )
        self.fa = _player(42417, "Pete Crow-Armstrong", "OF", "CHC")
        self.mine = _player(999, "Jake Burger", "3B", "CHC")

        self._patch(roster, "get_league", return_value=self.league)
        self._patch(_base, "get_my_team_or_error", return_value=(self.team, None))
        self.m_fa = self._patch(_base, "resolve_free_agent", return_value=(self.fa, None))
        self.m_my = self._patch(_base, "resolve_my_player", return_value=(self.mine, None))
        # Writes enabled for most tests (real env stays untouched / off).
        self._patch(cfg, "ESPN_WRITE_ENABLED", new=True)

    def _patch(self, target, attr, **kw):
        p = mock.patch.object(target, attr, **kw)
        mocked = p.start()
        self.addCleanup(p.stop)
        return mocked

    # -- helpers --------------------------------------------------------------

    def _token_for(self, payload):
        return cfg.txn_token(payload)

    # -- payload correctness (execute path) -----------------------------------

    @requests_mock.Mocker()
    def test_add_only_payload(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        expected = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        out = roster.add_player("Pete Crow-Armstrong", confirm_token=self._token_for(expected))
        self.assertEqual(m.call_count, 1)
        body = m.last_request.json()
        self.assertEqual(body, expected)
        self.assertEqual(body["type"], "FREEAGENT")
        self.assertEqual(body["executionType"], "EXECUTE")
        self.assertEqual(body["memberId"], SWID)
        self.assertEqual(body["items"], [{"playerId": 42417, "type": "ADD", "toTeamId": 8}])
        self.assertTrue(m.last_request.url.endswith("/transactions/"))
        self.assertIn("lm-api-writes", m.last_request.url)
        self.assertIn("EXECUTED", out)

    @requests_mock.Mocker()
    def test_add_drop_payload(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        expected = self.league.add_drop_player(8, add_player_id=42417, drop_player_id=999, dry_run=True)
        out = roster.add_player(
            "Pete Crow-Armstrong", drop_player_name="Jake Burger",
            confirm_token=self._token_for(expected),
        )
        self.assertEqual(m.call_count, 1)
        self.assertEqual(m.last_request.json()["items"], [
            {"playerId": 42417, "type": "ADD", "toTeamId": 8},
            {"playerId": 999, "type": "DROP", "fromTeamId": 8},
        ])
        self.assertIn("EXECUTED", out)

    @requests_mock.Mocker()
    def test_drop_only_payload(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        expected = self.league.add_drop_player(8, add_player_id=None, drop_player_id=999, dry_run=True)
        out = roster.drop_player("Jake Burger", confirm_token=self._token_for(expected))
        self.assertEqual(m.call_count, 1)
        body = m.last_request.json()
        self.assertEqual(body["type"], "FREEAGENT")
        self.assertEqual(body["items"], [{"playerId": 999, "type": "DROP", "fromTeamId": 8}])
        self.assertIn("EXECUTED", out)

    @requests_mock.Mocker()
    def test_waiver_payload_has_null_bid(self, m):
        m.post(WRITE_URL, json={"id": "w1", "status": "PENDING"}, status_code=200)
        expected = self.league.waiver_claim(8, 42417, drop_player_id=None, bid_amount=None, dry_run=True)
        out = roster.waiver_claim("Pete Crow-Armstrong", confirm_token=self._token_for(expected))
        self.assertEqual(m.call_count, 1)
        body = m.last_request.json()
        self.assertEqual(body["type"], "WAIVER")
        self.assertIn("bidAmount", body)
        self.assertIsNone(body["bidAmount"])
        self.assertEqual(body["items"], [{"playerId": 42417, "type": "ADD", "toTeamId": 8}])
        # Waivers land PENDING — the result should say so.
        self.assertIn("PENDING", out)
        self.assertIn("Pending", out)

    @requests_mock.Mocker()
    def test_waiver_with_drop_payload(self, m):
        m.post(WRITE_URL, json={"id": "w2", "status": "PENDING"}, status_code=200)
        expected = self.league.waiver_claim(8, 42417, drop_player_id=999, bid_amount=None, dry_run=True)
        roster.waiver_claim(
            "Pete Crow-Armstrong", drop_player_name="Jake Burger",
            confirm_token=self._token_for(expected),
        )
        self.assertEqual(m.last_request.json()["items"], [
            {"playerId": 42417, "type": "ADD", "toTeamId": 8},
            {"playerId": 999, "type": "DROP", "fromTeamId": 8},
        ])

    # -- gate off -------------------------------------------------------------

    @requests_mock.Mocker()
    def test_gate_off_blocks_all(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        with mock.patch.object(cfg, "ESPN_WRITE_ENABLED", False):
            a = roster.add_player("Pete Crow-Armstrong", confirm_token="whatever")
            d = roster.drop_player("Jake Burger", confirm_token="whatever")
            w = roster.waiver_claim("Pete Crow-Armstrong", confirm_token="whatever")
        for out in (a, d, w):
            self.assertIn("DISABLED", out)
        self.assertEqual(m.call_count, 0)

    # -- preview / token gate -------------------------------------------------

    @requests_mock.Mocker()
    def test_no_token_returns_preview_with_token_no_post(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        expected = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        token = self._token_for(expected)
        out = roster.add_player("Pete Crow-Armstrong")
        self.assertIn("PREVIEW", out)
        self.assertIn(token, out)
        self.assertIn("ADD  Pete Crow-Armstrong", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_wrong_token_returns_preview_no_post(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        out = roster.add_player("Pete Crow-Armstrong", confirm_token="deadbeef")
        self.assertIn("PREVIEW", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_matching_token_posts_once_and_invalidates(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        expected = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        cfg._league_instance = "sentinel-not-none"
        roster.add_player("Pete Crow-Armstrong", confirm_token=self._token_for(expected))
        self.assertEqual(m.call_count, 1)
        # invalidate_league() reset the singleton so later reads refetch.
        self.assertIsNone(cfg._league_instance)

    # -- ESPN error mapping ---------------------------------------------------

    @requests_mock.Mocker()
    def test_409_maps_to_friendly_roster_full(self, m):
        m.post(WRITE_URL, text="roster full", status_code=409)
        expected = self.league.add_drop_player(8, add_player_id=42417, dry_run=True)
        out = roster.add_player("Pete Crow-Armstrong", confirm_token=self._token_for(expected))
        self.assertTrue(out.startswith("❌"))
        self.assertIn("roster full", out.lower())
        self.assertEqual(m.call_count, 1)

    # -- validation failures (no post) ----------------------------------------

    @requests_mock.Mocker()
    def test_add_non_free_agent_errors(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        self.m_fa.return_value = (None, "'X' is already rostered by Rivals — not a free agent.")
        out = roster.add_player("X", confirm_token="anything")
        self.assertIn("already rostered", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_drop_player_not_on_roster_errors(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        self.m_my.return_value = (None, "'Nobody' is not on your roster.")
        out = roster.drop_player("Nobody", confirm_token="anything")
        self.assertIn("not on your roster", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_add_drop_invalid_drop_errors(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        self.m_my.return_value = (None, "'Ghost' is not on your roster.")
        out = roster.add_player("Pete Crow-Armstrong", drop_player_name="Ghost", confirm_token="x")
        self.assertIn("not on your roster", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_my_team_unresolved_errors(self, m):
        m.post(WRITE_URL, json=OK, status_code=200)
        with mock.patch.object(_base, "get_my_team_or_error", return_value=(None, "no team")):
            out = roster.add_player("Pete Crow-Armstrong", confirm_token="x")
        self.assertIn("no team", out)
        self.assertEqual(m.call_count, 0)

    # -- roster-full pre-warning ----------------------------------------------

    def test_roster_full_warning_in_preview(self):
        # capacity 3, roster 3, no drop -> warn
        self.league.espn_request.get_league = mock.Mock(
            return_value={"settings": {"rosterSettings": {"lineupSlotCounts": {"16": 3}}}}
        )
        out = roster.add_player("Pete Crow-Armstrong")
        self.assertIn("Roster appears full", out)
        self.assertIn("409", out)

    def test_open_slot_no_warning(self):
        out = roster.add_player("Pete Crow-Armstrong")  # capacity 30 from setUp
        self.assertNotIn("Roster appears full", out)

    def test_add_with_drop_skips_full_warning(self):
        self.league.espn_request.get_league = mock.Mock(
            return_value={"settings": {"rosterSettings": {"lineupSlotCounts": {"16": 3}}}}
        )
        out = roster.add_player("Pete Crow-Armstrong", drop_player_name="Jake Burger")
        self.assertNotIn("Roster appears full", out)

    def test_roster_full_check_degrades_on_lookup_error(self):
        # A failing settings fetch must not raise or false-warn.
        self.league.espn_request.get_league = mock.Mock(side_effect=RuntimeError("boom"))
        out = roster.add_player("Pete Crow-Armstrong")
        self.assertIn("PREVIEW", out)
        self.assertNotIn("Roster appears full", out)


class RegistrarTest(TestCase):
    def test_register_tools_registers_three(self):
        captured = {}

        class FakeMCP:
            def tool(self):
                def deco(fn):
                    captured[fn.__name__] = fn
                    return fn
                return deco

        roster.register_tools(FakeMCP())
        self.assertEqual(set(captured), {"add_player", "drop_player", "waiver_claim"})

    def test_register_commands_registers_three(self):
        import typer

        app = typer.Typer()
        roster.register_commands(app)
        names = {c.callback.__name__ for c in app.registered_commands}
        self.assertEqual(names, {"add", "drop", "waiver"})
