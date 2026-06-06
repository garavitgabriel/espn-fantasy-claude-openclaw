"""Credential management — persists ESPN cookies to ~/.espn-fantasy/config.json."""

import json
import os
from pathlib import Path

from pydantic import BaseModel

CONFIG_DIR = Path.home() / ".espn-fantasy"
CONFIG_FILE = CONFIG_DIR / "config.json"


class EspnConfig(BaseModel):
    espn_s2: str | None = None
    espn_swid: str | None = None
    league_id: int = 612122596
    year: int = 2026
    team_id: str | None = None
    team_name: str = "Gabriel"
    write_enabled: bool = False


class ConfigManager:
    """Load/save ESPN credentials from ~/.espn-fantasy/config.json.

    Environment variables always override the config file.
    """

    def __init__(self, path: Path = CONFIG_FILE):
        self._path = path

    def load(self) -> EspnConfig:
        """Load config from file, then apply env var overrides."""
        if self._path.exists():
            data = json.loads(self._path.read_text())
            config = EspnConfig(**data)
        else:
            config = EspnConfig()

        # Environment variables override file config
        if os.environ.get("ESPN_S2"):
            config.espn_s2 = os.environ["ESPN_S2"]
        if os.environ.get("ESPN_SWID"):
            config.espn_swid = os.environ["ESPN_SWID"]
        if os.environ.get("ESPN_LEAGUE_ID"):
            config.league_id = int(os.environ["ESPN_LEAGUE_ID"])
        if os.environ.get("ESPN_YEAR"):
            config.year = int(os.environ["ESPN_YEAR"])
        if os.environ.get("ESPN_TEAM_ID"):
            config.team_id = os.environ["ESPN_TEAM_ID"]
        if os.environ.get("ESPN_TEAM_NAME"):
            config.team_name = os.environ["ESPN_TEAM_NAME"]
        if os.environ.get("ESPN_WRITE_ENABLED"):
            config.write_enabled = os.environ["ESPN_WRITE_ENABLED"].strip().lower() in (
                "1", "true", "yes", "on",
            )

        return config

    def save(self, config: EspnConfig) -> None:
        """Save config to file."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(config.model_dump_json(indent=2) + "\n")

    def update(self, **kwargs) -> EspnConfig:
        """Update specific fields and save."""
        # Load from file only (not env overrides) to avoid persisting env values
        if self._path.exists():
            data = json.loads(self._path.read_text())
            config = EspnConfig(**data)
        else:
            config = EspnConfig()

        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)

        self.save(config)
        return config
