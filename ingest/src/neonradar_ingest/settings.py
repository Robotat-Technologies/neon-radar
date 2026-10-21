"""The ingest package's settings: environment variables first, then the repository's `.env`.

The operator adds `CH_API_KEY` to `.env` (operator decision OD-14); `.env` also holds keys of
other packages, hence `extra="ignore"`. Read when a command runs, never at import time.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class IngestSettings(BaseSettings):
    """`CH_API_KEY`: the Companies House API key; empty or absent means not available."""

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    ch_api_key: SecretStr | None = None

    def companies_house_key(self) -> str | None:
        key = self.ch_api_key.get_secret_value().strip() if self.ch_api_key else ""
        return key or None
