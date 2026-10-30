"""The two Neo4j instances (C2 loader rule L17, PHASE-2.md M2.11 deliverable 2).

`Instance.DEFAULT` is Phase 1's database (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`,
`NEO4J_DATABASE`, default `neo4j`): synthetic data only, the one the API on port 8000, the UI,
the end-to-end tests and the Neo4j MCP server use. `Instance.REAL` is the Compose service
`neo4j-real` (`NR_NEO4J_REAL_URI`, default `bolt://127.0.0.1:7688`, the same user,
`NEO4J_REAL_PASSWORD`), whose only database is `realdata`. Every query names the database of
its instance, so a query sent to the other instance fails ("database does not exist") before
anything is written, and the default instance may never be configured with the name
`realdata`. `check_records` refuses (exit 2) a load whose records do not all belong to the
instance, before any connection; its messages hold counts only.
"""

from collections import Counter
from collections.abc import Iterable, Mapping
from enum import StrEnum
from typing import Any, Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from neonradar_contracts.datasets import load_registry
from neonradar_graph.client import ENV_FILE, Neo4jSettings

REAL_DATABASE = "realdata"
REAL_URI = "bolt://127.0.0.1:7688"
Kind = Literal["synthetic", "real", "unknown"]


class InstanceRefused(Exception):
    """A load or a setting that would put records into the wrong instance; nothing is written."""

    exit_code = 2
    counts_only = True  # counts and setting names only, never a record value or id


class _DatabaseSetting(BaseSettings):
    """`NEO4J_DATABASE` alone, so the database is known without a password."""

    model_config = SettingsConfigDict(
        env_prefix="NEO4J_", env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore"
    )

    database: str = "neo4j"


class RealNeo4jSettings(BaseSettings):
    """`NR_NEO4J_REAL_URI`, `NEO4J_USER` and `NEO4J_REAL_PASSWORD` (env vars win over `.env`)."""

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    nr_neo4j_real_uri: str = REAL_URI
    neo4j_user: str = "neo4j"
    neo4j_real_password: SecretStr


def _default_database(name: str) -> str:
    if name == REAL_DATABASE:
        raise InstanceRefused(
            f"NEO4J_DATABASE is {REAL_DATABASE}, the real-data instance's database: the default"
            " instance holds synthetic data only (C2 L17)"
        )
    return name


class Instance(StrEnum):
    DEFAULT = "default"
    REAL = "real"

    @property
    def database(self) -> str:
        """The database every query to this instance names."""
        if self is Instance.REAL:
            return REAL_DATABASE
        return _default_database(_DatabaseSetting().database)

    def settings(self) -> Neo4jSettings:
        """Connection settings; raises pydantic's ValidationError when the password is unset."""
        if self is Instance.DEFAULT:
            settings = Neo4jSettings()
            _default_database(settings.database)
            return settings
        real = RealNeo4jSettings()
        return Neo4jSettings(
            uri=real.nr_neo4j_real_uri,
            user=real.neo4j_user,
            password=real.neo4j_real_password,
            database=REAL_DATABASE,
        )


def for_database(database: str) -> Instance:
    """The instance that holds `database`: only the real-data instance has `realdata`."""
    return Instance.REAL if database == REAL_DATABASE else Instance.DEFAULT


def record_kind(record: Mapping[str, Any]) -> Kind:
    """`synthetic` or `real` when every dataset the record names is registered as such."""
    datasets = record.get("datasets")
    if not isinstance(datasets, list) or not datasets:
        return "unknown"
    registry = load_registry()
    flags = set()
    for slug in datasets:
        entry = registry.get(slug) if isinstance(slug, str) else None
        if entry is None:
            return "unknown"
        flags.add(entry.synthetic)
    return "unknown" if len(flags) != 1 else "synthetic" if flags.pop() else "real"


def check_records(
    records: Iterable[Mapping[str, Any]], instance: Instance, manifests: Iterable[bool] = ()
) -> None:
    """L17: refuse (InstanceRefused, exit 2) unless every record and every manifest's `synthetic`
    flag belongs to `instance`. A record of no known dataset is refused by both instances, so a
    load that mixes synthetic and real records is refused whichever instance it names."""
    kinds: Counter[Kind] = Counter(record_kind(record) for record in records)
    kinds.update("synthetic" if synthetic else "real" for synthetic in manifests)
    wanted: Kind = "real" if instance is Instance.REAL else "synthetic"
    others = sum(count for kind, count in kinds.items() if kind != wanted)
    if not others:
        return
    if instance is Instance.DEFAULT:
        raise InstanceRefused(
            f"{others} record(s) or manifest(s) are not synthetic: the default instance holds"
            " synthetic data only, and a load never mixes the two (C2 L17); nothing was written"
        )
    raise InstanceRefused(
        f"{others} record(s) or manifest(s) are synthetic or of no known dataset: the real-data"
        " instance holds real records only, and a load never mixes the two (C2 L17); nothing"
        " was written"
    )
