"""Tests for mcp_server/auth.py — ConfigManager and EspnConfig."""

import json
import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from mcp_server.auth import ConfigManager, EspnConfig


class TestEspnConfig(TestCase):
    def test_defaults(self):
        config = EspnConfig()
        self.assertIsNone(config.espn_s2)
        self.assertIsNone(config.espn_swid)
        self.assertEqual(config.league_id, 612122596)
        self.assertEqual(config.year, 2026)
        self.assertEqual(config.team_name, "Gabriel")

    def test_custom_values(self):
        config = EspnConfig(espn_s2="abc", espn_swid="{123}", league_id=999)
        self.assertEqual(config.espn_s2, "abc")
        self.assertEqual(config.espn_swid, "{123}")
        self.assertEqual(config.league_id, 999)


class TestConfigManager(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.config_path = Path(self.tmp) / "config.json"
        self.manager = ConfigManager(path=self.config_path)
        # Clear real ESPN env vars so they don't pollute tests
        self._env_backup = {}
        for key in ("ESPN_S2", "ESPN_SWID", "ESPN_LEAGUE_ID", "ESPN_YEAR", "ESPN_TEAM_ID", "ESPN_TEAM_NAME"):
            if key in os.environ:
                self._env_backup[key] = os.environ.pop(key)

    def tearDown(self):
        os.environ.update(self._env_backup)

    def test_load_no_file(self):
        config = self.manager.load()
        self.assertIsNone(config.espn_s2)
        self.assertEqual(config.league_id, 612122596)

    def test_save_and_load(self):
        config = EspnConfig(espn_s2="test_s2", espn_swid="{test_swid}")
        self.manager.save(config)
        self.assertTrue(self.config_path.exists())

        loaded = self.manager.load()
        self.assertEqual(loaded.espn_s2, "test_s2")
        self.assertEqual(loaded.espn_swid, "{test_swid}")

    def test_update(self):
        self.manager.update(espn_s2="first")
        config = self.manager.load()
        self.assertEqual(config.espn_s2, "first")

        self.manager.update(espn_s2="second", team_name="NewTeam")
        config = self.manager.load()
        self.assertEqual(config.espn_s2, "second")
        self.assertEqual(config.team_name, "NewTeam")

    @patch.dict(os.environ, {"ESPN_S2": "env_s2", "ESPN_SWID": "{env_swid}"})
    def test_env_vars_override_file(self):
        self.manager.update(espn_s2="file_s2", espn_swid="{file_swid}")
        config = self.manager.load()
        # Env vars should win
        self.assertEqual(config.espn_s2, "env_s2")
        self.assertEqual(config.espn_swid, "{env_swid}")

    @patch.dict(os.environ, {"ESPN_LEAGUE_ID": "999999"})
    def test_env_league_id_override(self):
        config = self.manager.load()
        self.assertEqual(config.league_id, 999999)

    def test_update_does_not_persist_env_values(self):
        """update() should only save file values, not env overrides."""
        with patch.dict(os.environ, {"ESPN_S2": "env_only"}):
            self.manager.update(team_name="Test")

        # Read file directly — should NOT have env_only
        data = json.loads(self.config_path.read_text())
        self.assertIsNone(data.get("espn_s2"))
        self.assertEqual(data["team_name"], "Test")
