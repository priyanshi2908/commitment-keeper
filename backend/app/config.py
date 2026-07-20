"""Configuration loading for the Commitment Keeper backend."""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import List

from dotenv import load_dotenv

load_dotenv()

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPOSITORY_ROOT = BACKEND_ROOT.parent

DEFAULT_SCHEMA_PATH = str(
    REPOSITORY_ROOT / "hermes-skill" / "schemas" / "commitment.schema.json"
)
DEFAULT_DB_PATH = str(REPOSITORY_ROOT / "data" / "commitments.db")


class Settings:
    def __init__(self) -> None:
        self.host: str = os.getenv("HOST", "127.0.0.1")
        self.port: int = int(os.getenv("PORT", "8000"))
        self.debug: bool = os.getenv("DEBUG", "0") == "1"

        self.hermes_command: str = os.getenv("HERMES_COMMAND", "hermes")
        self.hermes_timeout_seconds: float = float(
            os.getenv("HERMES_TIMEOUT_SECONDS", "60")
        )
        self.hermes_skill_name: str = os.getenv("HERMES_SKILL_NAME", "commitment-keeper")

        self.schema_path: str = os.getenv("COMMITMENT_SCHEMA_PATH") or DEFAULT_SCHEMA_PATH
        self.db_path: str = os.getenv("COMMITMENTS_DB_PATH") or DEFAULT_DB_PATH

        self.allowed_origins: List[str] = [
            o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
            if o.strip()
        ]

        # Slack (used in Block 3)
        self.slack_bot_token: str = os.getenv("SLACK_BOT_TOKEN", "")
        self.slack_app_token: str = os.getenv("SLACK_APP_TOKEN", "")
        self.slack_allowed_channels: List[str] = [
            c.strip() for c in os.getenv("SLACK_ALLOWED_CHANNELS", "").split(",") if c.strip()
        ]
        self.slack_authenticated_user: str = os.getenv("SLACK_AUTHENTICATED_USER", "Priyanshi")
        self.backend_base_url: str = os.getenv("BACKEND_BASE_URL", f"http://{self.host}:{self.port}")


@lru_cache
def get_settings() -> Settings:
    return Settings()
