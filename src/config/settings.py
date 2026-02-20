"""Environment-backed runtime settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _PROJECT_ROOT / ".env"


def _parse_optional_int(name: str, raw_value: str | None) -> Optional[int]:
    """Parse optional integer env values used for OpenAI max_tokens overrides."""
    if raw_value is None:
        return None
    value = raw_value.strip()
    if value == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer when set") from exc


def _load_env_file(path: Path) -> None:
    """Populate process env vars from .env when present."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Settings:
    OPENAI_API_KEY: str = ""
    OAUTH_URL: str = ""
    CLIENT_ID: str = ""
    CLIENT_SECRET: str = ""
    AZURE_BASE_URL: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    AGENT_MODEL: str = ""
    AGENT_MODEL_OAUTH: str = ""
    AGENT_MAX_TOKENS: Optional[int] = None
    AGENT_MAX_TOKENS_OAUTH: Optional[int] = None

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
            OAUTH_URL=os.getenv("OAUTH_URL", ""),
            CLIENT_ID=os.getenv("CLIENT_ID", ""),
            CLIENT_SECRET=os.getenv("CLIENT_SECRET", ""),
            AZURE_BASE_URL=os.getenv("AZURE_BASE_URL", ""),
            OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o"),
            AGENT_MODEL=os.getenv("AGENT_MODEL", ""),
            AGENT_MODEL_OAUTH=os.getenv("AGENT_MODEL_OAUTH", ""),
            AGENT_MAX_TOKENS=_parse_optional_int(
                "AGENT_MAX_TOKENS", os.getenv("AGENT_MAX_TOKENS")
            ),
            AGENT_MAX_TOKENS_OAUTH=_parse_optional_int(
                "AGENT_MAX_TOKENS_OAUTH", os.getenv("AGENT_MAX_TOKENS_OAUTH")
            ),
        )


@lru_cache
def get_settings() -> Settings:
    _load_env_file(_ENV_FILE)
    return Settings.from_env()
