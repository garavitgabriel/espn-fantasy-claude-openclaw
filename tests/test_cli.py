"""Tests for the Typer CLI — verify all commands load and render help."""

from unittest import TestCase
from typer.testing import CliRunner

from mcp_server.cli import app

runner = CliRunner()


class TestCLIHelp(TestCase):
    """Every command should render --help without crashing."""

    def _assert_help(self, args):
        result = runner.invoke(app, args + ["--help"])
        self.assertEqual(result.exit_code, 0, f"Failed for {args}: {result.output}")

    def test_root_help(self):
        self._assert_help([])

    def test_roster_help(self):
        self._assert_help(["roster"])

    def test_matchup_help(self):
        self._assert_help(["matchup"])

    def test_standings_help(self):
        self._assert_help(["standings"])

    def test_free_agents_help(self):
        self._assert_help(["free-agents"])

    def test_activity_help(self):
        self._assert_help(["activity"])

    def test_box_scores_help(self):
        self._assert_help(["box-scores"])

    def test_player_help(self):
        self._assert_help(["player"])

    def test_compare_help(self):
        self._assert_help(["compare"])

    def test_rosters_help(self):
        self._assert_help(["rosters"])

    def test_trade_help(self):
        self._assert_help(["trade"])

    def test_scoring_help(self):
        self._assert_help(["scoring"])

    def test_slots_help(self):
        self._assert_help(["slots"])

    def test_draft_help(self):
        self._assert_help(["draft"])

    def test_needs_help(self):
        self._assert_help(["needs"])

    def test_refresh_help(self):
        self._assert_help(["refresh"])

    def test_schedule_help(self):
        self._assert_help(["schedule"])

    def test_settings_help(self):
        self._assert_help(["settings"])

    def test_search_help(self):
        self._assert_help(["search"])

    def test_scoreboard_help(self):
        self._assert_help(["scoreboard"])

    def test_news_help(self):
        self._assert_help(["news"])

    def test_splits_help(self):
        self._assert_help(["splits"])

    def test_gamelog_help(self):
        self._assert_help(["gamelog"])

    def test_mlb_games_help(self):
        self._assert_help(["mlb-games"])

    def test_vs_team_help(self):
        self._assert_help(["vs-team"])

    def test_pro_schedule_help(self):
        self._assert_help(["pro-schedule"])

    def test_chat_help(self):
        self._assert_help(["chat"])

    def test_auth_help(self):
        self._assert_help(["auth"])

    def test_auth_token_help(self):
        self._assert_help(["auth", "token"])

    def test_auth_status_help(self):
        self._assert_help(["auth", "status"])

    def test_auth_logout_help(self):
        self._assert_help(["auth", "logout"])

    def test_auth_login_help(self):
        self._assert_help(["auth", "login"])

    def test_build_plugin_help(self):
        self._assert_help(["build-plugin"])

    def test_verify_auth_help(self):
        self._assert_help(["verify-auth"])

    def test_set_lineup_help(self):
        self._assert_help(["set-lineup"])

    def test_add_drop_help(self):
        self._assert_help(["add-drop"])

    def test_propose_trade_help(self):
        self._assert_help(["propose-trade"])

    def test_accept_trade_help(self):
        self._assert_help(["accept-trade"])
