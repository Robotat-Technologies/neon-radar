"""The OpenSanctions bulk loader (PHASE-2.md M2.7), offline, on synthetic FtM bodies only.

The export is the M1.8d fixture (`fixtures/opensanctions/entities.ftm.json`) extended with
`bulk-extra.ftm.json`: a sanctioned person who is also a PEP, a sanctioned company, an
associated company without topics, a `Vessel` and the relationships between them. The mock
transport answers `index.json` with a 307 like data.opensanctions.org; nothing touches the
network, and no row comes from OpenSanctions.
"""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.opensanctions.access import REFUSAL
from neonradar_ingest.sources.opensanctions.mapping import DATASET

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures" / "opensanctions"
EXPORT = b"".join(
    (FIXTURES / name).read_bytes() for name in ("entities.ftm.json", "bulk-extra.ftm.json")
)
HOST = "https://data.opensanctions.org"
PINNED = "data.opensanctions.org"
VERSION = "20261015185439-syn"


class Transport:
    """data.opensanctions.org in miniature: `latest` answers 307 to the versioned artifact."""

    def __init__(self, checksum: str | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.checksum = checksum or hashlib.sha1(EXPORT, usedforsecurity=False).hexdigest()
        self.entities_host = self.index_host = HOST
        self.entities_redirect: str | None = None  # a 307 for the entities.ftm.json request

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        path = request.url.path
        if self.entities_redirect and path.endswith("/entities.ftm.json"):
            return httpx.Response(307, headers={"Location": self.entities_redirect})
        if path.startswith("/datasets/latest/"):
            collection = path.split("/")[3]
            location = f"{self.index_host}/artifacts/{collection}/{VERSION}/index.json"
            return httpx.Response(307, headers={"Location": location})
        collection = path.split("/")[2]
        if path.endswith("/index.json"):
            entities = f"{self.entities_host}/artifacts/{collection}/{VERSION}/entities.ftm.json"
            resource = {"name": "entities.ftm.json", "url": entities, "size": len(EXPORT)}
            body = {"version": VERSION, "resources": [resource | {"checksum": self.checksum}]}
            return httpx.Response(200, json=body)
        return httpx.Response(200, content=EXPORT)

    def client(self) -> HttpClient:
        mock = httpx.MockTransport(self)
        return HttpClient(HOST, follow_redirects=True, limiter=RateLimiter(1000), transport=mock)


@pytest.fixture
def mock(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> Transport:
    transport = Transport()
    sources.load_plugins()  # registers the loader
    spec = replace(sources.source_spec(DATASET), client=transport.client)  # type: ignore[type-var]
    monkeypatch.setitem(sources._SOURCES, DATASET, spec)
    return transport


def setup(data_env: Any, *, access: str = "licensed", peps: bool = False, **block: Any) -> None:
    sources_block = {DATASET: {"enabled": True, **block}}
    data_env.write_profile("uk-test", real_data=True, sources=sources_block)
    data_env.allow_real("uk-test", opensanctions=access, pep_sources=[DATASET] if peps else [])


def run(*command: str) -> Any:
    return runner.invoke(app, [*command, "--profile", "uk-test", "--dataset", DATASET])


@pytest.mark.parametrize("access", ["licensed", "exempt"])
def test_fetch_follows_the_redirect_and_downloads_the_collection(
    data_env: Any, mock: Transport, access: str
) -> None:
    setup(data_env, access=access)
    assert run("data", "fetch").exit_code == 0
    artifact = f"/artifacts/sanctions/{VERSION}"  # `sanctions` is the default collection
    assert [request.url.path for request in mock.requests] == [
        "/datasets/latest/sanctions/index.json",
        f"{artifact}/index.json",
        f"{artifact}/index.json",
        f"{artifact}/entities.ftm.json",
    ]
    folder = layout.sources_dir(DATASET, "sanctions", VERSION)
    assert (folder / "entities.ftm.json").read_bytes() == EXPORT
    assert json.loads((folder / "download.json").read_text(encoding="utf-8"))["complete"]


def test_the_default_collection_downloads_only_that_collection(
    data_env: Any, mock: Transport
) -> None:
    setup(data_env, collection="default")
    assert run("data", "fetch").exit_code == 0
    paths = [request.url.path for request in mock.requests]
    assert paths[0] == "/datasets/latest/default/index.json"
    assert all("/default/" in path for path in paths)


@pytest.mark.parametrize("where", ["entities_host", "index_host"])
def test_a_file_outside_data_opensanctions_org_stops_the_collection(
    data_env: Any, mock: Transport, where: str
) -> None:
    setup(data_env)
    setattr(mock, where, "https://mirror.example.invalid")  # named by index.json, or a 307 to it
    result = run("data", "fetch")
    assert result.exit_code == 1, result.output
    assert "1 product(s) stopped" in result.output
    assert {request.url.host for request in mock.requests} == {PINNED}
    assert not layout.sources_dir(DATASET, "sanctions", VERSION).exists()
    report = sorted(layout.reports_dir("uk-test").glob("data-fetch-*.json"))[-1]
    summary = json.loads(report.read_text(encoding="utf-8"))["datasets"][DATASET]
    assert summary["status"] == "partial" and summary["products_stopped"] == 1
    assert summary["products"] == {"sanctions": {"status": "stopped", "rule": "host"}}


@pytest.mark.parametrize(
    "host", ["https://mirror.example.invalid", "http://data.opensanctions.org"]
)
def test_a_download_redirect_off_the_pinned_host_is_never_sent(
    data_env: Any, mock: Transport, host: str
) -> None:
    setup(data_env)
    mock.entities_redirect = f"{host}/artifacts/sanctions/{VERSION}/entities.ftm.json"
    result = run("data", "fetch")
    assert result.exit_code == 1 and "a request outside data.opensanctions.org" in result.output
    assert {(r.url.scheme, r.url.host) for r in mock.requests} == {("https", PINNED)}
    assert not (layout.sources_dir(DATASET, "sanctions", VERSION) / "entities.ftm.json").exists()


@pytest.mark.parametrize("access", ["none", "evaluation"])
@pytest.mark.parametrize("command", [("data", "fetch")])
def test_gate_refuses_without_licensed_or_exempt_access(
    data_env: Any, mock: Transport, access: str, command: tuple[str, str]
) -> None:
    setup(data_env, access=access)  # the profile and the machine are allowed
    result = run(*command)
    assert result.exit_code == 3, result.output
    assert REFUSAL in result.output and f"(it is {access})" in result.output
    assert mock.requests == []
    real = data_env.cache / "real"
    assert not [path for path in real.rglob("*") if path.is_file()] if real.exists() else True


def test_gate_in_the_loader_itself_sends_no_request(data_env: Any, mock: Transport) -> None:
    setup(data_env, access="none")
    profile = load_profile("uk-test")
    spec = sources.source_spec(DATASET)
    assert spec is not None and spec.products is not None
    with pytest.raises(RealDataRefused, match=r"needs access\.opensanctions licensed or exempt"):
        spec.products(profile)["sanctions"](mock.client())
    assert mock.requests == []
