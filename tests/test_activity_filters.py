"""Tests for activity-filter + matchup-period-from-date helpers in tools.py."""

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import TestCase

from mcp_server.tools import _activity_matches, _matchup_period_for_date


def _league_stub(matchup_periods=None, start_ms=None, year=2026):
    raw_schedule = {}
    if start_ms is not None:
        raw_schedule["scoringPeriodStartDate"] = start_ms
    settings = SimpleNamespace(
        matchup_periods=matchup_periods or {},
        _raw_schedule_settings=raw_schedule,
    )
    return SimpleNamespace(settings=settings, year=year)


class TestMatchupPeriodForDate(TestCase):
    def test_maps_date_within_first_period(self):
        # Opening day 2026-04-01
        start_ms = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        league = _league_stub(
            matchup_periods={"1": [1, 2, 3, 4, 5, 6, 7], "2": [8, 9, 10, 11, 12, 13, 14]},
            start_ms=start_ms,
        )
        # Activity on 2026-04-03 = day 3 -> matchup period 1
        act_ms = int(datetime(2026, 4, 3, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(_matchup_period_for_date(league, act_ms), 1)

    def test_maps_to_second_period(self):
        start_ms = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        league = _league_stub(
            matchup_periods={"1": [1, 2, 3, 4, 5, 6, 7], "2": [8, 9, 10, 11, 12, 13, 14]},
            start_ms=start_ms,
        )
        act_ms = int(datetime(2026, 4, 10, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertEqual(_matchup_period_for_date(league, act_ms), 2)

    def test_out_of_range_returns_none(self):
        start_ms = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        league = _league_stub(
            matchup_periods={"1": [1, 2, 3, 4, 5, 6, 7]},
            start_ms=start_ms,
        )
        # Day 20 isn't in period 1
        act_ms = int(datetime(2026, 4, 20, tzinfo=timezone.utc).timestamp() * 1000)
        self.assertIsNone(_matchup_period_for_date(league, act_ms))

    def test_handles_missing_settings(self):
        league = _league_stub(matchup_periods=None, start_ms=None)
        self.assertIsNone(_matchup_period_for_date(league, 1774872000000))

    def test_ignores_non_numeric_date(self):
        league = _league_stub(matchup_periods={"1": [1]})
        self.assertIsNone(_matchup_period_for_date(league, "2026-04-01"))


class TestActivityMatches(TestCase):
    def _activity(self, team_id=1, action_type="FA ADDED", date_ms=None):
        team = SimpleNamespace(team_id=team_id, team_name=f"Team {team_id}")
        return SimpleNamespace(
            date=date_ms or int(datetime(2026, 4, 3, tzinfo=timezone.utc).timestamp() * 1000),
            actions=[(team, action_type, "Some Player")],
        )

    def test_no_filters_matches(self):
        act = self._activity()
        league = _league_stub()
        self.assertTrue(_activity_matches(act, None, 0, league))

    def test_team_filter_matches(self):
        team_filter = SimpleNamespace(team_id=1)
        act = self._activity(team_id=1)
        league = _league_stub()
        self.assertTrue(_activity_matches(act, team_filter, 0, league))

    def test_team_filter_rejects(self):
        team_filter = SimpleNamespace(team_id=2)
        act = self._activity(team_id=1)
        league = _league_stub()
        self.assertFalse(_activity_matches(act, team_filter, 0, league))

    def test_scoring_period_filter_matches(self):
        start_ms = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        league = _league_stub(
            matchup_periods={"1": [1, 2, 3, 4, 5, 6, 7]},
            start_ms=start_ms,
        )
        act = self._activity(
            date_ms=int(datetime(2026, 4, 3, tzinfo=timezone.utc).timestamp() * 1000),
        )
        self.assertTrue(_activity_matches(act, None, 1, league))
        self.assertFalse(_activity_matches(act, None, 2, league))

    def test_combined_filters(self):
        start_ms = int(datetime(2026, 4, 1, tzinfo=timezone.utc).timestamp() * 1000)
        league = _league_stub(
            matchup_periods={"1": [1, 2, 3, 4, 5, 6, 7]},
            start_ms=start_ms,
        )
        team_filter = SimpleNamespace(team_id=1)
        act = self._activity(
            team_id=1,
            date_ms=int(datetime(2026, 4, 3, tzinfo=timezone.utc).timestamp() * 1000),
        )
        self.assertTrue(_activity_matches(act, team_filter, 1, league))
        # Right period, wrong team
        self.assertFalse(
            _activity_matches(act, SimpleNamespace(team_id=99), 1, league)
        )
