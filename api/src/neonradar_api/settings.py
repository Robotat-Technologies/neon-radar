"""The API's settings (`NR_` environment variables only, read when the app starts).

- `NR_REPO_ROOT`: the repository the typology routes read (`neonradar_api.files`).

The host names the API answers are fixed in `neonradar_api.hardening.ALLOWED_HOSTS` (PHASE-4.md
M4.1), not configurable: any other `Host` header gets a 400 before a route runs, so a page whose
domain is rebound to 127.0.0.1 (DNS rebinding) cannot read the API.

The settings come from the environment, never from the repository's `.env`: `NR_REPO_ROOT`
locates the repository, so it cannot come from a file inside it.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class ApiSettings(BaseSettings):
    """`NR_REPO_ROOT`."""

    model_config = SettingsConfigDict(env_prefix="NR_", extra="ignore")

    repo_root: Path | None = None
