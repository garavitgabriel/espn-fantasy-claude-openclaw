"""Tests for mcp_server/formatters.py — all formatter functions."""

from types import SimpleNamespace
from unittest import TestCase

from mcp_server.formatters import (
    _fmt_owned,
    _fmt_started,
    _fmt_stat_value,
    fmt_player,
    fmt_roster,
    fmt_standings,
    fmt_free_agents,
    fmt_box_score,
    fmt_activity,
    fmt_player_detail,
    fmt_compare,
    fmt_trade_analysis,
    fmt_league_rosters,
    fmt_scoring_categories,
    fmt_roster_slots,
    fmt_roster_needs,
    fmt_player_search,
    fmt_player_news,
    fmt_player_splits,
    fmt_player_gamelog,
    fmt_mlb_games,
    fmt_batter_vs_team,
    fmt_league_chat,
)


def _make_player(**kwargs):
    defaults = dict(
        name="Test Player",
        position="SS",
        lineupSlot="SS",
        proTeam="NYY",
        injuryStatus="ACTIVE",
        percent_owned=85.5,
        percent_started=42.0,
        total_points=120.5,
        projected_total_points=95.0,
        eligibleSlots=["SS", "2B", "UTIL", "BE", "IL"],
        acquisitionType="FA",
        stats={0: {
            "points": 120.5,
            "breakdown": {"HR": 15, "AVG": 0.285, "RBI": 45},
            "projected_points": 95.0,
            "projected_breakdown": {"HR": 20, "AVG": 0.270, "RBI": 60},
        }},
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def _make_team(**kwargs):
    defaults = dict(
        team_name="Test Team",
        team_id=1,
        wins=10,
        losses=5,
        ties=0,
        roster=[_make_player(), _make_player(name="Player 2", lineupSlot="BE")],
    )
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestHelpers(TestCase):
    def test_fmt_owned_positive(self):
        self.assertEqual(_fmt_owned(85.5), "85.5%")

    def test_fmt_owned_negative(self):
        self.assertEqual(_fmt_owned(-1), "—")

    def test_fmt_owned_none(self):
        self.assertEqual(_fmt_owned(None), "—")

    def test_fmt_started_positive(self):
        self.assertEqual(_fmt_started(42.0), "42.0%")

    def test_fmt_started_negative(self):
        self.assertEqual(_fmt_started(-1), "—")

    def test_fmt_stat_value_float_small(self):
        self.assertEqual(_fmt_stat_value(0.285), "0.285")

    def test_fmt_stat_value_float_large(self):
        self.assertEqual(_fmt_stat_value(15.0), "15.0")

    def test_fmt_stat_value_int(self):
        self.assertEqual(_fmt_stat_value(42), "42")


class TestFmtPlayer(TestCase):
    def test_basic(self):
        p = _make_player()
        result = fmt_player(p)
        self.assertIn("Test Player", result)
        self.assertIn("SS", result)
        self.assertIn("NYY", result)

    def test_injured(self):
        p = _make_player(injuryStatus="OUT")
        result = fmt_player(p)
        self.assertIn("(OUT)", result)

    def test_active_no_injury_tag(self):
        p = _make_player(injuryStatus="ACTIVE")
        result = fmt_player(p)
        self.assertNotIn("(ACTIVE)", result)


class TestFmtRoster(TestCase):
    def test_groups_starters_and_bench(self):
        team = _make_team()
        result = fmt_roster(team)
        self.assertIn("**Starters**", result)
        self.assertIn("**Bench**", result)
        self.assertIn("Test Team", result)
        self.assertIn("10-5-0", result)


class TestFmtStandings(TestCase):
    def test_basic(self):
        teams = [_make_team(team_name="Team A"), _make_team(team_name="Team B")]
        result = fmt_standings(teams)
        self.assertIn("Team A", result)
        self.assertIn("Team B", result)
        self.assertIn("| 1 |", result)
        self.assertIn("| 2 |", result)


class TestFmtFreeAgents(TestCase):
    def test_basic(self):
        players = [_make_player(), _make_player(name="FA Player")]
        result = fmt_free_agents(players)
        self.assertIn("Test Player", result)
        self.assertIn("FA Player", result)
        self.assertIn("%Start", result)


class TestFmtBoxScore(TestCase):
    def test_h2h_category(self):
        bs = SimpleNamespace(
            home_team=SimpleNamespace(team_name="Home Team"),
            away_team=SimpleNamespace(team_name="Away Team"),
            home_stats={"HR": {"value": 10, "result": "WIN"}, "AVG": {"value": 0.285, "result": "LOSS"}},
            away_stats={"HR": {"value": 8, "result": "LOSS"}, "AVG": {"value": 0.310, "result": "WIN"}},
            home_wins=1,
            away_wins=1,
            home_ties=0,
        )
        result = fmt_box_score(bs)
        self.assertIn("Home Team", result)
        self.assertIn("Away Team", result)
        self.assertIn("HR", result)

    def test_no_stats_fallback(self):
        bs = SimpleNamespace(
            home_team=SimpleNamespace(team_name="Home"),
            away_team=SimpleNamespace(team_name="Away"),
            home_score=100,
            away_score=95,
        )
        result = fmt_box_score(bs)
        self.assertIn("Home", result)
        self.assertIn("Away", result)

    def test_none_stats(self):
        bs = SimpleNamespace(
            home_team=SimpleNamespace(team_name="Home"),
            away_team=SimpleNamespace(team_name="Away"),
            home_stats=None,
            home_score=50,
            away_score=60,
        )
        result = fmt_box_score(bs)
        self.assertIn("Home", result)


class TestFmtActivity(TestCase):
    def test_basic(self):
        act = SimpleNamespace(
            date="2026-04-01",
            actions=[(SimpleNamespace(team_name="My Team"), "ADD", "Player X")],
        )
        result = fmt_activity([act])
        self.assertIn("ADD", result)
        self.assertIn("Player X", result)
        self.assertIn("My Team", result)

    def test_none_team(self):
        act = SimpleNamespace(
            date="2026-04-01",
            actions=[(None, "DROP", "Player Y")],
        )
        result = fmt_activity([act])
        self.assertIn("DROP", result)
        self.assertIn("Player Y", result)


class TestFmtPlayerDetail(TestCase):
    def test_includes_projections(self):
        p = _make_player()
        result = fmt_player_detail(p)
        self.assertIn("Projected Points", result)
        self.assertIn("Projected Stats", result)
        self.assertIn("Eligible slots", result)
        self.assertIn("SS, 2B", result)

    def test_includes_acquisition_type(self):
        p = _make_player()
        result = fmt_player_detail(p)
        self.assertIn("Acquired via", result)


class TestFmtCompare(TestCase):
    def test_basic(self):
        p1 = _make_player(name="Player A")
        p2 = _make_player(name="Player B", total_points=100)
        result = fmt_compare(p1, p2)
        self.assertIn("Player A", result)
        self.assertIn("Player B", result)
        self.assertIn("Projected Points", result)
        self.assertIn("% Started", result)


class TestFmtTradeAnalysis(TestCase):
    def test_category_impact(self):
        give = [_make_player(name="Give Player")]
        recv = [_make_player(name="Recv Player", total_points=150)]
        result = fmt_trade_analysis(give, recv)
        self.assertIn("Category Impact", result)
        self.assertIn("HR", result)
        self.assertIn("Points differential", result)
        self.assertIn("Projected differential", result)


class TestFmtPlayerSearch(TestCase):
    def test_results(self):
        players = [_make_player(name="Shohei Ohtani")]
        result = fmt_player_search(players, "ohtani")
        self.assertIn("Shohei Ohtani", result)
        self.assertIn("1 matches", result)

    def test_no_results(self):
        result = fmt_player_search([], "nobody")
        self.assertIn("No players found", result)


class TestFmtPlayerNews(TestCase):
    def test_with_rotowire_and_news(self):
        data = {
            "rotowire": {"blurb": "Expected back Tuesday from IL stint."},
            "nextGame": {"event": {"name": "NYY @ BOS", "date": "2026-04-05T00:00Z"}},
            "news": {"items": [
                {"headline": "Ohtani hits 3 HRs", "published": "2026-04-04", "description": "Big night."},
            ]},
        }
        result = fmt_player_news(data, "Shohei Ohtani")
        self.assertIn("Expected back Tuesday", result)
        self.assertIn("NYY @ BOS", result)
        self.assertIn("Ohtani hits 3 HRs", result)

    def test_empty(self):
        result = fmt_player_news({}, "Nobody")
        self.assertIn("News", result)


class TestFmtPlayerSplits(TestCase):
    def test_basic(self):
        data = {
            "splitCategories": [{
                "displayName": "vs Left/Right",
                "splits": [
                    {"displayName": "vs LHP", "stats": [0.320, 15, 45], "abbreviations": ["AVG", "HR", "RBI"]},
                    {"displayName": "vs RHP", "stats": [0.260, 10, 30], "abbreviations": ["AVG", "HR", "RBI"]},
                ],
            }],
        }
        result = fmt_player_splits(data, "Test")
        self.assertIn("vs Left/Right", result)
        self.assertIn("vs LHP", result)
        self.assertIn("vs RHP", result)

    def test_empty(self):
        result = fmt_player_splits({"splitCategories": []}, "Test")
        self.assertIn("No split data", result)


class TestFmtMlbGames(TestCase):
    def test_basic(self):
        data = {"events": [
            {"summary": "NYY @ BOS", "status": {"type": {"shortDetail": "7:05 PM ET"}}, "lastPlay": None},
        ]}
        result = fmt_mlb_games(data, "20260404")
        self.assertIn("NYY @ BOS", result)
        self.assertIn("2026-04-04", result)

    def test_empty(self):
        result = fmt_mlb_games({"events": []}, "20260404")
        self.assertIn("No MLB games", result)


class TestFmtBatterVsTeam(TestCase):
    def test_basic(self):
        data = {
            "statistics": [{
                "labels": ["AB", "H", "HR", "AVG"],
                "splits": [
                    {"displayName": "vs NYY", "stats": [50, 15, 3, ".300"]},
                    {"displayName": "vs BOS", "stats": [40, 10, 1, ".250"]},
                ],
            }],
        }
        result = fmt_batter_vs_team(data, "Test Player")
        self.assertIn("vs NYY", result)
        self.assertIn("vs BOS", result)

    def test_empty(self):
        result = fmt_batter_vs_team({"statistics": []}, "Test")
        self.assertIn("No batter vs team data", result)


class TestFmtLeagueChat(TestCase):
    def test_basic(self):
        data = {"topics": [
            {"author": "Gabriel", "date": 1712188800000, "messages": [{"message": "Trade anyone?"}], "totalMessageCount": 3},
        ]}
        result = fmt_league_chat(data)
        self.assertIn("Gabriel", result)
        self.assertIn("Trade anyone?", result)

    def test_empty(self):
        result = fmt_league_chat({"topics": []})
        self.assertIn("No league messages", result)
