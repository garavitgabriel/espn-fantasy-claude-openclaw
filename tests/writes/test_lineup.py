"""WT-B tests — set_lineup tool/command. See docs/writes/wt-b-lineup.md.

All network access is mocked at the requests.post boundary. No real ESPN calls,
and ESPN_WRITE_ENABLED is never set in the real environment — it is patched per test.
"""

import re
from contextlib import ExitStack
from unittest import TestCase, mock

import requests_mock

from espn_api.baseball import League
import mcp_server.config as cfg
from mcp_server.writes import _base
from mcp_server.writes import lineup


WRITE_URL = (
    "https://lm-api-writes.fantasy.espn.com/apis/v3/games/flb/"
    "seasons/2026/segments/0/leagues/123/transactions/"
)
SWID = "{EFFBA4A3-C6FC-430F-A4ED-46A70E1CC95B}"

# lineupSlotId reference: 0=C 4=SS 5=OF 12=UTIL 13=P 14=SP 15=RP 16=BE 17=IL
TOKEN_RE = re.compile(r'confirm_token=\\?"([0-9a-f]{8})\\?"')


class FakePlayer:
    def __init__(self, name, playerId, lineupSlotId, eligibleSlots, position="?"):
        self.name = name
        self.playerId = playerId
        self.lineupSlotId = lineupSlotId
        self.eligibleSlots = eligibleSlots
        self.position = position


class FakeTeam:
    def __init__(self, team_id, roster):
        self.team_id = team_id
        self.roster = roster
        self.team_name = "My Team"


def _make_league():
    """A real League with no network fetch (so set_lineup_moves builds real payloads)."""
    league = League(league_id=123, year=2026, espn_s2="s2", swid=SWID, fetch_league=False)
    league.scoringPeriodId = 74
    return league


class LineupTestBase(TestCase):
    def setUp(self):
        self.league = _make_league()
        # Mason Miller benched (16), eligible to pitch. Tarik Skubal starting (P=13).
        self.miller = FakePlayer("Mason Miller", 4307825, 16, ["RP", "P", "BE", "IL"], "RP")
        self.skubal = FakePlayer("Tarik Skubal", 42403, 13, ["SP", "P", "BE", "IL"], "SP")
        # A SS already starting (slot 4) and a SS-eligible bat on the bench wanting in.
        self.turner = FakePlayer("Trea Turner", 101, 4, ["SS", "UTIL", "BE"], "SS")
        self.witt = FakePlayer("Bobby Witt", 100, 16, ["SS", "UTIL", "BE"], "SS")
        self.team = FakeTeam(8, [self.miller, self.skubal, self.turner, self.witt])

    def _enabled_patches(self, write_enabled=True):
        return [
            mock.patch.object(cfg, "ESPN_WRITE_ENABLED", write_enabled),
            mock.patch.object(lineup, "get_league", return_value=self.league),
            mock.patch.object(_base, "get_league", return_value=self.league),
            mock.patch.object(_base, "resolve_my_team", return_value=(self.team, None)),
        ]

    def _call(self, *args, write_enabled=True, **kwargs):
        with ExitStack() as stack:
            for p in self._enabled_patches(write_enabled):
                stack.enter_context(p)
            return lineup.set_lineup(*args, **kwargs)

    def _preview_token(self, *args, **kwargs):
        out = self._call(*args, **kwargs)
        match = TOKEN_RE.search(out)
        self.assertIsNotNone(match, f"no token in preview:\n{out}")
        return match.group(1), out


# --- name → slot mapping -----------------------------------------------------

class SlotMappingTest(TestCase):
    def test_known_positions(self):
        self.assertEqual(lineup._slot_id("UTIL"), 12)
        self.assertEqual(lineup._slot_id("P"), 13)
        self.assertEqual(lineup._slot_id("BE"), 16)
        self.assertEqual(lineup._slot_id("SP"), 14)
        self.assertEqual(lineup._slot_id("RP"), 15)
        self.assertEqual(lineup._slot_id("C"), 0)
        self.assertEqual(lineup._slot_id("SS"), 4)
        self.assertEqual(lineup._slot_id("OF"), 5)

    def test_case_and_alias_insensitive(self):
        self.assertEqual(lineup._slot_id("util"), 12)
        self.assertEqual(lineup._slot_id(" p "), 13)
        self.assertEqual(lineup._slot_id("UT"), 12)  # POSITION_ALIASES: UT -> UTIL

    def test_combo_infield_aliases(self):
        # The spec advertises MI/CI; POSITION_MAP names them 2B/SS and 1B/3B.
        self.assertEqual(lineup._slot_id("MI"), 6)
        self.assertEqual(lineup._slot_id("ci"), 7)
        self.assertEqual(lineup._slot_id("IF"), 19)

    def test_unknown_slot_is_none(self):
        self.assertIsNone(lineup._slot_id("QB"))
        self.assertIsNone(lineup._slot_id(""))

    def test_slot_name_roundtrip(self):
        self.assertEqual(lineup._slot_name(13), "P")
        self.assertEqual(lineup._slot_name(16), "BE")


# --- payload correctness -----------------------------------------------------

class SingleMovePayloadTest(LineupTestBase):
    @requests_mock.Mocker()
    def test_single_move_payload(self, m):
        m.post(WRITE_URL, json={"id": "t1", "status": "EXECUTED"}, status_code=200)
        token, _ = self._preview_token("Mason Miller", "RP")  # BE(16) -> RP(15), empty

        with mock.patch.object(_base, "invalidate_league") as inval:
            out = self._call("Mason Miller", "RP", confirm_token=token)

        self.assertEqual(m.call_count, 1)
        inval.assert_called_once()
        self.assertIn("lm-api-writes.fantasy.espn.com", m.last_request.url)
        body = m.last_request.json()
        self.assertEqual(body["type"], "ROSTER")
        self.assertEqual(body["memberId"], SWID)
        self.assertEqual(body["items"], [{
            "playerId": 4307825, "type": "LINEUP",
            "fromLineupSlotId": 16, "toLineupSlotId": 15,
        }])
        # Lineup items carry no team ids.
        self.assertNotIn("toTeamId", body["items"][0])
        self.assertNotIn("fromTeamId", body["items"][0])
        self.assertIn("EXECUTED", out)


class SwapPayloadTest(LineupTestBase):
    @requests_mock.Mocker()
    def test_swap_payload_mirrors_slots(self, m):
        m.post(WRITE_URL, json={"id": "t2", "status": "EXECUTED"}, status_code=200)
        # Miller BE(16) -> P(13); Skubal P(13) -> BE(16)
        token, preview = self._preview_token("Mason Miller", "P", swap_with="Tarik Skubal")
        # Preview shows both legs with names + ids.
        self.assertIn("Mason Miller", preview)
        self.assertIn("Tarik Skubal", preview)

        out = self._call("Mason Miller", "P", swap_with="Tarik Skubal", confirm_token=token)

        self.assertEqual(m.call_count, 1)
        items = m.last_request.json()["items"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0], {
            "playerId": 4307825, "type": "LINEUP",
            "fromLineupSlotId": 16, "toLineupSlotId": 13,
        })
        self.assertEqual(items[1], {
            "playerId": 42403, "type": "LINEUP",
            "fromLineupSlotId": 13, "toLineupSlotId": 16,
        })
        self.assertIn("EXECUTED", out)


# --- validation (no post) ----------------------------------------------------

class ValidationTest(LineupTestBase):
    @requests_mock.Mocker()
    def test_ineligible_slot_rejected(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        out = self._call("Bobby Witt", "P")  # Witt has no P eligibility
        self.assertIn("not eligible", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_occupied_slot_rejected_without_swap(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        out = self._call("Bobby Witt", "SS")  # SS(4) occupied by Trea Turner
        self.assertIn("occupied", out.lower())
        self.assertIn("swap-with", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_bench_target_not_blocked_by_occupancy(self, m):
        # Bench (16) is multi-capacity: moving an eligible starter there is allowed
        # even though other players already sit on BE.
        m.post(WRITE_URL, json={"id": "t3", "status": "EXECUTED"}, status_code=200)
        token, _ = self._preview_token("Tarik Skubal", "BE")  # P(13) -> BE(16)
        out = self._call("Tarik Skubal", "BE", confirm_token=token)
        self.assertEqual(m.call_count, 1)
        self.assertIn("EXECUTED", out)

    @requests_mock.Mocker()
    def test_swap_partner_eligibility_validated(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        # Skubal P(13) -> BE(16); the swap partner must take P(13). Witt (SS, no P
        # eligibility) cannot, so the whole swap is rejected before any post.
        out = self._call("Tarik Skubal", "BE", swap_with="Bobby Witt")
        self.assertIn("Bobby Witt", out)
        self.assertIn("not eligible", out)
        self.assertEqual(m.call_count, 0)


# --- safety gate + token flow ------------------------------------------------

class SafetyFlowTest(LineupTestBase):
    @requests_mock.Mocker()
    def test_gate_off_blocks(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        out = self._call("Mason Miller", "RP", write_enabled=False)
        self.assertIn("DISABLED", out)
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_no_token_returns_preview_no_post(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        out = self._call("Mason Miller", "RP")
        self.assertIn("PREVIEW", out)
        self.assertRegex(out, r'confirm_token=\\?"[0-9a-f]{8}\\?"')
        self.assertEqual(m.call_count, 0)

    @requests_mock.Mocker()
    def test_wrong_token_returns_preview_no_post(self, m):
        m.post(WRITE_URL, json={}, status_code=200)
        out = self._call("Mason Miller", "RP", confirm_token="deadbeef")
        self.assertIn("PREVIEW", out)
        self.assertEqual(m.call_count, 0)
