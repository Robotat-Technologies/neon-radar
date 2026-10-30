"""The ingest package's settings: environment variables first, then the repository's `.env`.

The operator adds `CH_API_KEY` to `.env` (operator decision OD-14); `.env` also holds keys of
other packages, hence `extra="ignore"`. Read when a command runs, never at import time.
"""

from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class IngestSettings(BaseSettings):
    """`CH_API_KEY`: the Companies House API key; empty or absent means not available.

    `NR_REAL_DATA_MACHINE`: `approved` on a machine the data steward listed in
    docs/data/real-data-machines.md (PHASE-2.md 1.1); the real-data gate reads it (M2.2).

    `NR_EU_FSF_TOKEN`: the EU Financial Sanctions Files download token; empty or absent means
    the Commission's public token (PHASE-2.md M2.6d).
    """

    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env", env_file_encoding="utf-8", extra="ignore"
    )

    ch_api_key: SecretStr | None = None
    nr_real_data_machine: str = ""
    nr_eu_fsf_token: SecretStr | None = None
    nr_project_file: str = ""  # another project.yaml: tests and acceptance commands only (M2.2)
    compose_project_name: str = ""  # Docker Compose's own override; purge --graph checks it

    def companies_house_key(self) -> str | None:
        key = self.ch_api_key.get_secret_value().strip() if self.ch_api_key else ""
        return key or None
