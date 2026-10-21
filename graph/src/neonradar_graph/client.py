"""Neo4j connection settings and driver (PHASE-1.md M1.4).

Settings come from environment variables and the repository's `.env`; real environment
variables win, so the devcontainer's `NEO4J_URI=bolt://neo4j:7687` is kept. Every settings
object in the project follows this pattern. Where Compose provides secrets (the devcontainer),
the password can also come from the file `/run/secrets/neo4j_password`, after the other two.
"""

import logging
import time
from collections.abc import Callable
from pathlib import Path

from neo4j import Driver, GraphDatabase
from neo4j.exceptions import AuthError, DriverError, Neo4jError
from pydantic import SecretStr
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SecretsSettingsSource,
    SettingsConfigDict,
)

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = REPO_ROOT / ".env"
SECRETS_DIR = Path("/run/secrets")  # Compose secrets; the devcontainer has neo4j_password here


class Neo4jSettings(BaseSettings):
    """`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` and `NEO4J_DATABASE`."""

    # `.env` also holds NEO4J_HEAP, CH_API_KEY and others, hence extra="ignore".
    model_config = SettingsConfigDict(
        env_prefix="NEO4J_", env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    uri: str = "bolt://localhost:7687"
    user: str = "neo4j"
    password: SecretStr
    database: str = "neo4j"

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Arguments, then environment, then `.env`, then Compose secrets if the folder exists.

        The folder is checked when the settings are read, not at import, so hosts without
        `/run/secrets` behave exactly as before.
        """
        sources: tuple[PydanticBaseSettingsSource, ...] = (
            init_settings,
            env_settings,
            dotenv_settings,
        )
        if SECRETS_DIR.is_dir():
            sources += (SecretsSettingsSource(settings_cls, secrets_dir=SECRETS_DIR),)
        return sources


def get_driver(settings: Neo4jSettings | None = None) -> Driver:
    """A neo4j 6.x driver for the configured database; close it after use.

    Driver telemetry is off (guardrail G3), and a connection attempt gives up after 10 s.
    """
    settings = settings or Neo4jSettings()
    return GraphDatabase.driver(
        settings.uri,
        auth=(settings.user, settings.password.get_secret_value()),
        telemetry_disabled=True,
        connection_timeout=10.0,
    )


def wait_until_ready(
    driver: Driver,
    timeout_s: float = 120,
    *,
    sleep: Callable[[float], None] = time.sleep,
    clock: Callable[[], float] = time.monotonic,
) -> None:
    """Call `verify_connectivity()` with exponential backoff until it succeeds.

    Raises TimeoutError after `timeout_s` seconds; a wrong password fails at once.
    """
    deadline = clock() + timeout_s
    delay = 0.5
    attempt = 0
    while True:
        attempt += 1
        try:
            driver.verify_connectivity()
            return
        except AuthError:
            raise
        except (DriverError, Neo4jError) as error:
            remaining = deadline - clock()
            if remaining <= 0:
                message = f"Neo4j is not reachable after {timeout_s:g} s ({attempt} attempts)"
                raise TimeoutError(f"{message}: {error}") from error
            logger.info("Neo4j is not ready (attempt %d): %s", attempt, error)
            sleep(min(delay, remaining))
            delay = min(delay * 2, 10.0)
