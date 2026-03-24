import sys
import types
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

sys.modules.setdefault("requests", types.SimpleNamespace(get=None))

import mcp_server.config as config


def make_team(team_id, team_name, owners=None):
    return SimpleNamespace(team_id=team_id, team_name=team_name, owners=owners or [])


def make_league(*teams):
    return SimpleNamespace(teams=list(teams))


class TeamResolutionTest(TestCase):
    def test_resolve_my_team_prefers_team_id(self):
        league = make_league(
            make_team(1, "Gabriel's Bombers"),
            make_team(7, "Actual Target"),
        )

        with patch.object(config, "ESPN_TEAM_ID", "7"), patch.object(config, "ESPN_TEAM_NAME", "Gabriel"):
            team, error = config.resolve_my_team(league)

        self.assertEqual(team.team_id, 7)
        self.assertIsNone(error)

    def test_resolve_my_team_matches_normalized_exact_name_before_partial(self):
        league = make_league(
            make_team(1, "The Judge"),
            make_team(2, "Judge"),
        )

        with patch.object(config, "ESPN_TEAM_ID", ""), patch.object(config, "ESPN_TEAM_NAME", " judge!! "):
            team, error = config.resolve_my_team(league)

        self.assertEqual(team.team_id, 2)
        self.assertIsNone(error)

    def test_resolve_my_team_falls_back_to_partial_name(self):
        league = make_league(
            make_team(1, "Gabriel's Bombers"),
            make_team(2, "Other Club"),
        )

        with patch.object(config, "ESPN_TEAM_ID", ""), patch.object(config, "ESPN_TEAM_NAME", "gabriel"):
            team, error = config.resolve_my_team(league)

        self.assertEqual(team.team_id, 1)
        self.assertIsNone(error)

    def test_resolve_my_team_can_match_owner_name(self):
        league = make_league(
            make_team(
                3,
                "Bomb Squad",
                owners=[
                    {
                        "firstName": "Gabriel",
                        "lastName": "Robles",
                        "displayName": "Gabe R.",
                    }
                ],
            ),
            make_team(4, "Other Club"),
        )

        with patch.object(config, "ESPN_TEAM_ID", ""), patch.object(config, "ESPN_TEAM_NAME", "gabriel robles"):
            team, error = config.resolve_my_team(league)

        self.assertEqual(team.team_id, 3)
        self.assertIsNone(error)

    def test_resolve_team_uses_normalized_exact_before_partial(self):
        league = make_league(
            make_team(1, "The Judge"),
            make_team(2, "Judge"),
        )

        team = config.resolve_team(league, "judge")

        self.assertEqual(team.team_id, 2)

    def test_get_my_team_error_reports_invalid_team_id_and_available_teams(self):
        league = make_league(
            make_team(1, "Bombers", owners=[{"displayName": "Gabriel"}]),
            make_team(2, "Aces", owners=[{"firstName": "Ana", "lastName": "Lopez"}]),
        )

        with patch.object(config, "ESPN_TEAM_ID", "abc"), patch.object(config, "ESPN_TEAM_NAME", "Gabriel"):
            error = config.get_my_team_error(league)

        self.assertIn("ESPN_TEAM_ID='abc' is not a valid integer", error)
        self.assertIn("Bombers [id=1; owners=Gabriel]", error)
        self.assertIn("Aces [id=2; owners=Ana Lopez]", error)

    def test_get_my_team_error_reports_missing_match(self):
        league = make_league(
            make_team(1, "Bombers", owners=[{"displayName": "Gabriel"}]),
            make_team(2, "Aces", owners=[{"displayName": "Ana"}]),
        )

        with patch.object(config, "ESPN_TEAM_ID", ""), patch.object(config, "ESPN_TEAM_NAME", "No Match"):
            error = config.get_my_team_error(league)

        self.assertIn("Could not resolve your team from ESPN_TEAM_ID or ESPN_TEAM_NAME.", error)
        self.assertIn("Current ESPN_TEAM_NAME='No Match'.", error)
        self.assertIn("Bombers [id=1; owners=Gabriel]", error)
