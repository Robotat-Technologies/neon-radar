import os
from pathlib import Path
from typing import Any, cast

import pytest
from neo4j import Driver
from neo4j.exceptions import AuthError, ServiceUnavailable
from pydantic import SecretStr

from neonradar_graph import client
from neonradar_graph.client import Neo4jSettings, get_driver, wait_until_ready


@pytest.fixture(autouse=True)
def no_neo4j_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    for name in [key for key in os.environ if key.startswith("NEO4J_")]:
        monkeypatch.delenv(name)
    monkeypatch.setattr(client, "SECRETS_DIR", tmp_path / "no-secrets")


def write_secret(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "neo4j_password").write_text(value, encoding="utf-8")
    monkeypatch.setattr(client, "SECRETS_DIR", secrets)


def write_env(tmp_path: Path, text: str) -> Path:
    path = tmp_path / ".env"
    path.write_text(text, encoding="utf-8")
    return path


def test_env_file_is_the_repository_root_env() -> None:
    assert Path(__file__).resolve().parents[2] / ".env" == client.ENV_FILE


def test_reads_env_file_ignores_other_keys_and_has_defaults(tmp_path: Path) -> None:
    env = write_env(tmp_path, "NEO4J_PASSWORD=from-file-secret\nNEO4J_HEAP=1G\nCH_API_KEY=\n")
    settings = Neo4jSettings(_env_file=env)
    assert settings.password.get_secret_value() == "from-file-secret"
    assert (settings.uri, settings.user, settings.database) == (
        "bolt://localhost:7687",
        "neo4j",
        "neo4j",
    )
    assert "from-file-secret" not in repr(settings)


def test_environment_variables_win_over_env_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = write_env(tmp_path, "NEO4J_PASSWORD=file\nNEO4J_URI=bolt://localhost:7687\n")
    monkeypatch.setenv("NEO4J_URI", "bolt://neo4j:7687")
    settings = Neo4jSettings(_env_file=env)
    assert settings.uri == "bolt://neo4j:7687"


def test_password_is_required(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="password"):
        Neo4jSettings(_env_file=write_env(tmp_path, ""))


def test_reads_the_password_from_a_compose_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_secret(tmp_path, monkeypatch, "from-secret-file")
    settings = Neo4jSettings(_env_file=tmp_path / "missing.env")
    assert settings.password.get_secret_value() == "from-secret-file"


def test_environment_and_env_file_win_over_the_compose_secret(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    write_secret(tmp_path, monkeypatch, "from-secret-file")
    env = write_env(tmp_path, "NEO4J_PASSWORD=from-env-file\n")
    assert Neo4jSettings(_env_file=env).password.get_secret_value() == "from-env-file"
    monkeypatch.setenv("NEO4J_PASSWORD", "from-environment")
    assert Neo4jSettings(_env_file=env).password.get_secret_value() == "from-environment"


def test_get_driver_uses_the_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    calls: list[tuple[Any, ...]] = []
    monkeypatch.setattr(client.GraphDatabase, "driver", lambda *a, **kw: calls.append((a, kw)))
    settings = Neo4jSettings(
        _env_file=tmp_path / "missing.env", uri="bolt://h:1", user="u", password=SecretStr("p")
    )
    get_driver(settings)
    get_driver(settings, max_transaction_retry_time=3.0)
    options = {"auth": ("u", "p"), "telemetry_disabled": True, "connection_timeout": 10.0}
    assert calls == [
        (("bolt://h:1",), {**options, "max_transaction_retry_time": 30.0}),
        (("bolt://h:1",), {**options, "max_transaction_retry_time": 3.0}),
    ]


class FlakyDriver:
    def __init__(self, errors: list[Exception]) -> None:
        self.errors = errors
        self.calls = 0

    def verify_connectivity(self) -> None:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def __call__(self) -> float:
        return self.now


def test_wait_until_ready_backs_off_until_connected() -> None:
    driver, clock = FlakyDriver([ServiceUnavailable("down")] * 3), FakeClock()
    wait_until_ready(cast(Driver, driver), 120, sleep=clock.sleep, clock=clock)
    assert driver.calls == 4
    assert clock.sleeps == [0.5, 1.0, 2.0]


def test_wait_until_ready_times_out() -> None:
    driver, clock = FlakyDriver([ServiceUnavailable("down")] * 100), FakeClock()
    with pytest.raises(TimeoutError, match="not reachable after 5 s"):
        wait_until_ready(cast(Driver, driver), 5, sleep=clock.sleep, clock=clock)
    assert sum(clock.sleeps) == 5


def test_wait_until_ready_does_not_retry_a_wrong_password() -> None:
    driver, clock = FlakyDriver([AuthError("unauthorized")]), FakeClock()
    with pytest.raises(AuthError):
        wait_until_ready(cast(Driver, driver), 120, sleep=clock.sleep, clock=clock)
    assert driver.calls == 1
