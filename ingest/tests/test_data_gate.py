"""The real-data gate (PHASE-2.md M2.2 deliverable 5, acceptance).

For each of the five conditions, a project file and environment where only that condition
fails gives exit 3, its own message, no request on the mock transport and no file written.
Everything is synthetic: a test profile `uk-test`, a fake `us_ofac_sdn` source.
"""

import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import gate, sources
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.http import HttpClient, RateLimiter

runner = CliRunner()
BODY = b"<synthetic-list/>\n"
ALLOWED = {
    "real_data_profiles": ["uk-test"],
    "data_protection_filed": True,
    "sanctions_lists": ["us_ofac_sdn"],
}


class Transport:
    """A mock transport that records every request."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, content=BODY)

    def client(self) -> HttpClient:
        mock = httpx.MockTransport(self)
        return HttpClient("", follow_redirects=False, limiter=RateLimiter(1000), transport=mock)


@pytest.fixture
def transport(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> Transport:
    """A real test profile with one fake list source, on a machine where every check passes."""
    mock = Transport()

    def discover(client: HttpClient) -> list[sources.RemoteFile]:
        client.get("https://lists.example.test/index")
        return [
            sources.RemoteFile("list.xml", "https://lists.example.test/list.xml", "1", None, None)
        ]

    spec = sources.SourceSpec("us_ofac_sdn", discover, client=mock.client)
    monkeypatch.setitem(sources._SOURCES, "us_ofac_sdn", spec)
    data_env.write_profile(
        "uk-test",
        real_data=True,
        sources={"us_ofac_sdn": {"enabled": True}, "gb_companies_house": {"enabled": True}},
    )
    data_env.write_project(**ALLOWED)
    data_env.approve_machine()
    return mock


def files_under(folder: Path) -> list[Path]:
    return [p for p in folder.rglob("*") if p.is_file()] if folder.exists() else []


def fetch() -> Any:
    return runner.invoke(app, ["data", "fetch", "--profile", "uk-test", "--dataset", "us_ofac_sdn"])


def test_every_condition_passes_then_the_fetch_runs(data_env: Any, transport: Transport) -> None:
    result = fetch()
    assert result.exit_code == 0, result.output
    assert len(transport.requests) == 2
    assert (data_env.cache / "real/sources/us_ofac_sdn/main/1/list.xml").read_bytes() == BODY
    assert len(files_under(data_env.cache / "reports" / "uk-test")) == 1


def _no_list(env: Any, mp: pytest.MonkeyPatch) -> None:
    env.write_project(**(ALLOWED | {"sanctions_lists": ["gb_fcdo_sanctions"]}))


def _no_profile(env: Any, mp: pytest.MonkeyPatch) -> None:
    env.write_project(**(ALLOWED | {"real_data_profiles": ["uk-tiny"]}))


def _not_filed(env: Any, mp: pytest.MonkeyPatch) -> None:
    env.write_project(**(ALLOWED | {"data_protection_filed": False}))


def _ci(env: Any, mp: pytest.MonkeyPatch) -> None:
    mp.setenv("CI", "true")


def _codespaces(env: Any, mp: pytest.MonkeyPatch) -> None:
    mp.setenv("CODESPACES", "true")


def _unapproved(env: Any, mp: pytest.MonkeyPatch) -> None:
    env.approve_machine(False)


def _environment_wins(env: Any, mp: pytest.MonkeyPatch) -> None:
    mp.setenv("NR_REAL_DATA_MACHINE", "pending")  # .env says approved; the variable wins


Breaker = Callable[[Any, pytest.MonkeyPatch], None]


@pytest.mark.parametrize(
    ("breaker", "message"),
    [
        (_no_list, "rule access.sanctions_lists, err-"),
        (_no_profile, "uk-test is not in access.real_data_profiles"),
        (_not_filed, "access.data_protection_filed is false: the data steward files"),
        (_ci, "CI is set: real data never runs in CI or Codespaces"),
        (_codespaces, "CODESPACES is set: real data never runs in CI or Codespaces"),
        (_unapproved, "NR_REAL_DATA_MACHINE is not approved"),
        (_environment_wins, "NR_REAL_DATA_MACHINE is not approved"),
    ],
)
def test_each_condition_alone_refuses_with_exit_3_and_no_request(
    data_env: Any,
    transport: Transport,
    monkeypatch: pytest.MonkeyPatch,
    breaker: Breaker,
    message: str,
) -> None:
    breaker(data_env, monkeypatch)
    result = fetch()
    assert result.exit_code == 3, result.output
    assert message in result.output
    assert result.output.startswith("RealDataRefused, step gate, dataset -, rule ")
    assert transport.requests == []
    assert files_under(data_env.cache) == []  # no file written, not even a log


def test_the_dataset_rule_names_the_list(data_env: Any, transport: Transport) -> None:
    data_env.write_project(**(ALLOWED | {"sanctions_lists": ["gb_fcdo_sanctions"]}))
    assert "us_ofac_sdn is not in access.sanctions_lists" in fetch().output


def test_the_checks_run_in_order(
    data_env: Any, transport: Transport, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With everything wrong, each fix reveals the next condition, in the spec's order."""
    data_env.write_project(sanctions_lists=[])
    data_env.approve_machine(False)
    monkeypatch.setenv("CI", "true")
    profile = load_profile("uk-test")
    fixes: list[Callable[[], object]] = [
        lambda: data_env.write_project(sanctions_lists=["us_ofac_sdn"]),
        lambda: data_env.write_project(**(ALLOWED | {"data_protection_filed": False})),
        lambda: data_env.write_project(**ALLOWED),
        lambda: monkeypatch.delenv("CI"),
        data_env.approve_machine,
    ]
    rules = []
    for fix in fixes:
        with pytest.raises(gate.RealDataRefused) as refused:
            gate.check_real_data(load_project(), profile, "us_ofac_sdn")
        assert refused.value.exit_code == 3
        rules.append(refused.value.rule)
        fix()
    gate.check_real_data(load_project(), profile, "us_ofac_sdn")  # every condition now passes
    assert rules == [
        "access.sanctions_lists",
        "access.real_data_profiles",
        "access.data_protection_filed",
        "CI",
        "NR_REAL_DATA_MACHINE",
    ]


def test_without_a_dataset_condition_1_is_skipped(data_env: Any, transport: Transport) -> None:
    data_env.write_project(**(ALLOWED | {"sanctions_lists": []}))
    gate.check_real_data(load_project(), load_profile("uk-test"))


def test_other_access_rules(data_env: Any) -> None:
    project, tiny = load_project(), load_profile("uk-tiny")
    expected = {
        ("gb_parliament_members", None): "gb_parliament_members is not in access.pep_sources",
        ("opensanctions_default", None): "opensanctions_default needs access.opensanctions",
        ("gb_companies_house", "officers"): "the officers API needs access.companies_house_key",
    }
    for (dataset, step), message in expected.items():
        with pytest.raises(gate.RealDataRefused, match=message):
            gate.check_real_data(project, tiny, dataset, step=step)


def test_a_synthetic_profile_passes_without_checks(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CI", "true")
    gate.check_real_data(load_project(), load_profile("demo"), "us_ofac_sdn")


def test_the_real_instance_gate_refuses_while_no_profile_is_allowed(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(gate.RealDataRefused, match=r"access\.real_data_profiles is empty"):
        gate.check_real_instance(load_project())
    data_env.write_project(**ALLOWED)
    data_env.approve_machine()
    gate.check_real_instance(load_project())
    monkeypatch.setenv("CODESPACES", "1")
    with pytest.raises(gate.RealDataRefused, match="CODESPACES is set"):
        gate.check_real_instance(load_project())


def test_the_machine_setting_reads_the_environment_then_dot_env(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    assert not gate.machine_approved()  # no .env yet
    monkeypatch.setenv("NR_REAL_DATA_MACHINE", "approved")
    assert gate.machine_approved()
    monkeypatch.delenv("NR_REAL_DATA_MACHINE")
    data_env.approve_machine()
    assert gate.machine_approved()
    assert os.environ.get("NR_REAL_DATA_MACHINE") is None
