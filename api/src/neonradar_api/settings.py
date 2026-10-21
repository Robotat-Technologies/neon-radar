"""The API's settings (`NR_` environment variables only, read when the app starts).

- `NR_REPO_ROOT`: the repository the typology routes read (`neonradar_api.files`).
- `NR_ALLOWED_HOSTS`: the `Host` header values the API answers, as a JSON list. The default
  covers the browser and the UI's proxies on this machine (`localhost`, `127.0.0.1`; Vite and
  nginx pass the browser's host on) and the Compose service name `api`. Any other host gets a
  400 before a route runs, so a page whose domain is rebound to 127.0.0.1 (DNS rebinding)
  cannot read the API.

The settings come from the environment, never from the repository's `.env`: `NR_REPO_ROOT`
locates the repository, so it cannot come from a file inside it.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_ALLOWED_HOSTS = ("localhost", "127.0.0.1", "api")


class ApiSettings(BaseSettings):
    """`NR_REPO_ROOT` and `NR_ALLOWED_HOSTS`."""

    model_config = SettingsConfigDict(env_prefix="NR_", extra="ignore")

    repo_root: Path | None = None
    allowed_hosts: list[str] = list(DEFAULT_ALLOWED_HOSTS)
