"""WT-C tests — propose / cancel trade tools (mocked HTTP only).

No real ESPN calls are ever made. We mock at the ``requests.post`` boundary
(``requests_mock``) and assert the exact JSON body matches WRITE_API_REFERENCE §5,
paying special attention to trade item direction:
  give    -> {type: TRADE, fromTeamId: me,    toTeamId: other}
  receive -> {type: TRADE, fromTeamId: other, toTeamId: me}
"""

import contextlib
import datetime
import re
from types import SimpleNamespace
from unittest import TestCase, mock

import requests_mock

from espn_api.baseball import League
import espn_api.baseball.league as leaguemod
import mcp_server.config as cfg
from mcp_server.writes import _base
from mcp_server.writes import trades


WRITE_URL = (
    "https://lm-api-writes.fantasy.espn.com/apis/v3/games/flb/"
    "seasons/2026/segments/0/leagues/123/transactions/"
)
SWID = "{EFFBA4A3-C6FC-430F-A4ED-46A70E1CC95B}"

MY_TEAM_ID = 8
OTHER_TEAM_ID = 11

TOKEN_RE = re.compile(r'confirm_token="([0-9a-f]{8})"')
EXPIRATION_RE = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.000Z$"


def _player(name, player_id, position=""):
    return SimpleNamespace(name=name, playerId=player_id, position=position)


def _team(team_id, team_name, roster):
    return SimpleNamespace(team_id=team_id, team_name=team_name, roster=roster, owners=[])


def _make_league():
    """Real League (no network) with two fake teams + rosters."""
    league = League(
        league_id=123, year=2026, espn_s2="s2", swid=SWID, fetch_league=False
    )
    league.scoringPeriodId = 74
    my_team = _team(MY_TEAM_ID, "My Team", [
        _player("Spencer Strider", 42488, "SP"),
        _player("Mike Trout", 30836, "OF"),
    ])
    other_team = _team(OTHER_TEAM_ID, "Other Team", [
        _player("Bobby Witt Jr.", 4872587, "SS"),
        _player("Gunnar Henderson", 4801649, "SS"),
    ])
    league.teams = [my_team, other_team]
    return league


class _FrozenDateTime(datetime.datetime):
    """datetime subclass with a fixed now() so expirationDate is deterministic."""

    @classmethod
    def now(cls, tz=None):
        return datetime.datetime(2026, 6, 6, 17, 24, 52, tzinfo=tz or datetime.timezone.utc)


_FROZEN_DATETIME_NS = SimpleNamespace(
    datetime=_FrozenDateTime,
    timedelta=datetime.timedelta,
    timezone=datetime.timezone,
)
# 2026-06-06 17:24:52 + 2 days
EXPECTED_EXPIRATION = "2026-06-08T17:24:52.000Z"


class _TradeTestBase(TestCase):
    def setUp(self):
        self.league = _make_league()

    @contextlib.contextmanager
    def _ctx(self, *, enabled=True, freeze_clock=False):
        """Patch the env gate, my-team id, league lookups, and invalidate spy."""
        with contextlib.ExitStack() as stack:
            stack.enter_context(mock.patch.object(cfg, "ESPN_WRITE_ENABLED", enabled))
            stack.enter_context(mock.patch.object(cfg, "ESPN_TEAM_ID", MY_TEAM_ID))
            stack.enter_context(mock.patch.object(cfg, "ESPN_TEAM_NAME", ""))
            stack.enter_context(mock.patch.object(trades, "get_league", return_value=self.league))
            stack.enter_context(mock.patch.object(_base, "get_league", return_value=self.league))
            self.invalidate = stack.enter_context(
                mock.patch.object(_base, "invalidate_league")
            )
            if freeze_clock:
                stack.enter_context(mock.patch.object(leaguemod, "datetime", _FROZEN_DATETIME_NS))
            yield


# --- propose_trade: payload correctness -------------------------------------

class ProposeTradePayloadTest(_TradeTestBase):
    def _execute(self, m, **kwargs):
        """Run preview to get the token, then confirm to POST. Returns the result string."""
        m.post(WRITE_URL, json={"id": "prop-1", "status": "PENDING"}, status_code=200)
        with self._ctx(freeze_clock=True):
            preview = trades.propose_trade(confirm_token="", **kwargs)
            token = TOKEN_RE.search(preview).group(1)
            self.assertEqual(m.call_count, 0)  # preview never posts
            result = trades.propose_trade(confirm_token=token, **kwargs)
        return result

    @requests_mock.Mocker()
    def test_single_for_single_payload(self, m):
        self._execute(
            m, to_team="Other Team",
            give_players="Spencer Strider", receive_players="Bobby Witt Jr.",
            comment="fair deal",
        )
        self.assertEqual(m.call_count, 1)
        body = m.last_request.json()
        self.assertEqual(body["type"], "TRADE_PROPOSAL")
        self.assertEqual(body["executionType"], "EXECUTE")
        self.assertEqual(body["teamId"], MY_TEAM_ID)
        self.assertEqual(body["memberId"], SWID)
        self.assertEqual(body["scoringPeriodId"], 74)
        self.assertEqual(body["comment"], "fair deal")
        self.assertRegex(body["expirationDate"], EXPIRATION_RE)
        # Direction is the critical correctness point (§5).
        self.assertEqual(body["items"], [
            {"playerId": 42488, "type": "TRADE",
             "fromTeamId": MY_TEAM_ID, "toTeamId": OTHER_TEAM_ID},      # give: me -> other
            {"playerId": 4872587, "type": "TRADE",
             "fromTeamId": OTHER_TEAM_ID, "toTeamId": MY_TEAM_ID},      # receive: other -> me
        ])

    @requests_mock.Mocker()
    def test_writes_host_used(self, m):
        self._execute(
            m, to_team="Other Team",
            give_players="Spencer Strider", receive_players="Bobby Witt Jr.",
        )
        self.assertIn("lm-api-writes.fantasy.espn.com", m.last_request.url)

    @requests_mock.Mocker()
    def test_two_for_one_directions(self, m):
        self._execute(
            m, to_team="Other Team",
            give_players="Spencer Strider, Mike Trout",
            receive_players="Bobby Witt Jr.",
        )
        items = m.last_request.json()["items"]
        self.assertEqual(len(items), 3)
        # Two give items (me -> other), then one receive (other -> me), in order.
        self.assertEqual(
            [(i["playerId"], i["fromTeamId"], i["toTeamId"]) for i in items],
            [
                (42488, MY_TEAM_ID, OTHER_TEAM_ID),
                (30836, MY_TEAM_ID, OTHER_TEAM_ID),
                (4872587, OTHER_TEAM_ID, MY_TEAM_ID),
            ],
        )
        self.assertTrue(all(i["type"] == "TRADE" for i in items))

    @requests_mock.Mocker()
    def test_expiration_format(self, m):
        self._execute(
            m, to_team="Other Team",
            give_players="Spencer Strider", receive_players="Bobby Witt Jr.",
        )
        self.assertEqual(m.last_request.json()["expirationDate"], EXPECTED_EXPIRATION)


# --- propose_trade: flow / result -------------------------------------------

class ProposeTradeFlowTest(_TradeTestBase):
    @requests_mock.Mocker()
    def test_gate_off_returns_disabled_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx(enabled=False):
            out = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", confirm_token="",
            )
        self.assertIn("DISABLED", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_no_token_previews_with_token_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx(freeze_clock=True):
            out = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", comment="hi", confirm_token="",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("PREVIEW", out)
        self.assertRegex(out, TOKEN_RE)
        # Preview lines show direction with the other team's name.
        self.assertIn("GIVE:    Spencer Strider (SP) → Other Team", out)
        self.assertIn("RECEIVE: Bobby Witt Jr. (SS) ← Other Team", out)

    @requests_mock.Mocker()
    def test_wrong_token_previews_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx(freeze_clock=True):
            out = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", confirm_token="deadbeef",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("PREVIEW", out)

    @requests_mock.Mocker()
    def test_matching_token_executes_invalidates_and_shows_id(self, m):
        m.post(WRITE_URL, json={"id": "prop-xyz", "status": "PENDING"}, status_code=200)
        with self._ctx(freeze_clock=True):
            preview = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", confirm_token="",
            )
            token = TOKEN_RE.search(preview).group(1)
            out = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", confirm_token=token,
            )
            self.invalidate.assert_called_once()
        self.assertEqual(m.call_count, 1)
        self.assertIn("PENDING", out)
        self.assertIn("prop-xyz", out)  # proposal id surfaced for cancellation

    @requests_mock.Mocker()
    def test_unknown_team_errors_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx():
            out = trades.propose_trade(
                to_team="No Such Team", give_players="Spencer Strider",
                receive_players="Bobby Witt Jr.", confirm_token="",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("not found", out)

    @requests_mock.Mocker()
    def test_give_player_not_on_my_roster_errors_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx():
            out = trades.propose_trade(
                to_team="Other Team", give_players="Bobby Witt Jr.",  # on OTHER roster
                receive_players="Gunnar Henderson", confirm_token="",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("not on your roster", out)

    @requests_mock.Mocker()
    def test_receive_player_not_on_other_roster_errors_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx():
            out = trades.propose_trade(
                to_team="Other Team", give_players="Spencer Strider",
                receive_players="Mike Trout",  # on MY roster, not other's
                confirm_token="",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("Other Team", out)
        self.assertIn("not on", out)

    @requests_mock.Mocker()
    def test_empty_trade_errors_no_post(self, m):
        m.post(WRITE_URL, json={"id": "x", "status": "PENDING"})
        with self._ctx():
            out = trades.propose_trade(
                to_team="Other Team", give_players="", receive_players="",
                confirm_token="",
            )
        self.assertEqual(m.call_count, 0)
        self.assertIn("at least one player", out)


# --- cancel_trade ------------------------------------------------------------

class CancelTradeTest(_TradeTestBase):
    @requests_mock.Mocker()
    def test_cancel_payload(self, m):
        m.post(WRITE_URL, json={"id": "prop-1", "status": "CANCELED"}, status_code=200)
        with self._ctx():
            preview = trades.cancel_trade(transaction_id="uuid-123", confirm_token="")
            token = TOKEN_RE.search(preview).group(1)
            self.assertEqual(m.call_count, 0)
            out = trades.cancel_trade(transaction_id="uuid-123", confirm_token=token)
            self.invalidate.assert_called_once()
        self.assertEqual(m.call_count, 1)
        body = m.last_request.json()
        self.assertEqual(body["type"], "TRADE_PROPOSAL")
        self.assertEqual(body["executionType"], "CANCEL")
        self.assertEqual(body["items"], [])
        self.assertEqual(body["relatedTransactionId"], "uuid-123")
        self.assertEqual(body["teamId"], MY_TEAM_ID)
        self.assertIn("CANCELED", out)

    @requests_mock.Mocker()
    def test_cancel_gate_off_no_post(self, m):
        m.post(WRITE_URL, json={"status": "CANCELED"})
        with self._ctx(enabled=False):
            out = trades.cancel_trade(transaction_id="uuid-123", confirm_token="")
        self.assertEqual(m.call_count, 0)
        self.assertIn("DISABLED", out)

    @requests_mock.Mocker()
    def test_cancel_no_token_previews_no_post(self, m):
        m.post(WRITE_URL, json={"status": "CANCELED"})
        with self._ctx():
            out = trades.cancel_trade(transaction_id="uuid-123", confirm_token="")
        self.assertEqual(m.call_count, 0)
        self.assertIn("PREVIEW", out)
        self.assertIn("Cancel pending proposal uuid-123", out)

    @requests_mock.Mocker()
    def test_cancel_missing_id_errors_no_post(self, m):
        m.post(WRITE_URL, json={"status": "CANCELED"})
        with self._ctx():
            out = trades.cancel_trade(transaction_id="  ", confirm_token="")
        self.assertEqual(m.call_count, 0)
        self.assertIn("transaction id is required", out)


# --- tool / command registration --------------------------------------------

class RegistrationTest(TestCase):
    def test_register_tools_registers_both(self):
        registered = []

        class FakeMCP:
            def tool(self):
                def deco(fn):
                    registered.append(fn.__name__)
                    return fn
                return deco

        trades.register_tools(FakeMCP())
        self.assertEqual(set(registered), {"propose_trade", "cancel_trade"})

    def test_register_commands_registers_both(self):
        names = []

        class FakeApp:
            def command(self, name=None):
                names.append(name)
                def deco(fn):
                    return fn
                return deco

        trades.register_commands(FakeApp())
        self.assertEqual(set(names), {"propose-trade", "cancel-trade"})
