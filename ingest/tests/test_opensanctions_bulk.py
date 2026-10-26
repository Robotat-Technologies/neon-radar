"""The OpenSanctions bulk loader (PHASE-2.md M2.7), offline, on synthetic FtM bodies only.

The export is the M1.8d fixture (`fixtures/opensanctions/entities.ftm.json`) extended with
`bulk-extra.ftm.json`: a sanctioned person who is also a PEP, a sanctioned company, an
associated company without topics, a `Vessel` and the relationships between them, and lines
that strict C1 would reject: a directorship of a person, an ownership without an asset, an
account no ownership holds (and a sanction on it), and a held account whose bank is a person.
The mock transport answers `index.json` with a 307 like data.opensanctions.org; nothing
touches the network, and no row comes from OpenSanctions.
"""

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import httpx
import pytest
from followthemoney import registry
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_contracts.records import ALLOWED_SCHEMATA
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.sources import BuildContext
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.opensanctions import bulk
from neonradar_ingest.sources.opensanctions.access import REFUSAL
from neonradar_ingest.sources.opensanctions.mapping import DATASET, record_id

runner = CliRunner()
FIXTURES = Path(__file__).parent / "fixtures" / "opensanctions"
EXPORT = b"".join(
    (FIXTURES / name).read_bytes() for name in ("entities.ftm.json", "bulk-extra.ftm.json")
)
HOST = "https://data.opensanctions.org"
PINNED = "data.opensanctions.org"
VERSION = "20261015185439-syn"
SOURCE = {json.loads(line)["id"]: json.loads(line) for line in EXPORT.splitlines()}


class Transport:
    """data.opensanctions.org in miniature: `latest` answers 307 to the versioned artifact."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.export = EXPORT
        self.checksum: str | None = None  # None: the export's SHA-1; "": index.json names none
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
            sha1 = hashlib.sha1(self.export, usedforsecurity=False).hexdigest()
            checksum = sha1 if self.checksum is None else self.checksum
            resource = {"name": "entities.ftm.json", "url": entities, "size": len(self.export)}
            resource |= {"checksum": checksum} if checksum else {}
            return httpx.Response(200, json={"version": VERSION, "resources": [resource]})
        return httpx.Response(200, content=self.export)

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
    "host",
    [
        "https://mirror.example.invalid",
        "http://data.opensanctions.org",
        "https://data.opensanctions.org:8443",
    ],
)
def test_a_download_redirect_off_the_pinned_host_is_never_sent(
    data_env: Any, mock: Transport, host: str
) -> None:
    setup(data_env)
    mock.entities_redirect = f"{host}/artifacts/sanctions/{VERSION}/entities.ftm.json"
    result = run("data", "fetch")
    assert result.exit_code == 1 and "a request outside data.opensanctions.org" in result.output
    sent = {(r.url.scheme, r.url.host, r.url.port) for r in mock.requests}
    assert sent == {("https", PINNED, None)}
    assert not (layout.sources_dir(DATASET, "sanctions", VERSION) / "entities.ftm.json").exists()


@pytest.mark.parametrize("access", ["none", "evaluation"])
@pytest.mark.parametrize("command", [("data", "fetch"), ("ingest", "build")])
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


def fetch_and_build() -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Records by OpenSanctions id (from `nr.source_ref`) and the build summary's counts."""
    for command in (("data", "fetch"), ("ingest", "build")):
        result = run(*command)
        assert result.exit_code == 0, result.output
    folder = layout.records_dir("uk-test", DATASET)
    records = [json.loads(line) for path in folder.glob("*.ftm.jsonl") for line in path.open()]
    reports = sorted(layout.reports_dir("uk-test").glob("ingest-build-*.json"))
    summary = json.loads(reports[-1].read_text(encoding="utf-8"))["datasets"][DATASET]
    return {record["nr"]["source_ref"]: record for record in records}, summary


def topics(record: dict[str, Any]) -> list[str]:
    return list(record["properties"].get("topics", []))


def test_ids_references_and_schemata(data_env: Any, mock: Transport) -> None:
    setup(data_env, peps=True)
    mock.export = EXPORT + b'{"id": "syn-x", "schema": "Person:syn-leak", "properties": {}}\n'
    by_source, summary = fetch_and_build()
    for record in by_source.values():
        assert record["id"] == record_id(record["nr"]["source_ref"])
        assert record["datasets"] == [DATASET]
    assert by_source["syn-os-ownership-02"]["properties"] == {
        "owner": [record_id("NK-synCompanyZeta")],
        "asset": [record_id("syn-os-company-eta")],
        "percentage": ["100"],
    }
    # Vessel and Identification are not C1 schemata; the ownership of the vessel loses its end.
    assert "syn-os-vessel-theta" not in by_source and "syn-os-ident-01" not in by_source
    # A schema FollowTheMoney does not know (SynthFutureSchema, Person:syn-leak) is not shown.
    assert summary["skipped_by_schema"] == {"identification": 1, "unknown": 2, "vessel": 1}
    records = layout.records_dir("uk-test", DATASET)
    written = [*layout.reports_dir("uk-test").glob("*.json"), *records.iterdir()]  # manifest too
    assert not any("syn-leak" in path.read_text(encoding="utf-8") for path in written)
    assert summary["relationships_dropped"] == {"directorship": 1, "ownership": 1, "sanction": 1}
    assert summary["pep_relationships_dropped"] == {}
    assert summary["records"] == len(by_source) == 20
    # `ingest build` passed strict C1: what would fail it is skipped, dropped or removed, counted.
    gone = {"syn-os-directorship-02", "syn-os-ownership-04", "syn-os-account-01"}
    assert not (gone | {"syn-os-sanction-03"}) & set(by_source)  # the sanction on account-01
    assert summary["c1_records_skipped"] == {"bankaccount": 1, "ownership": 1}
    assert summary["c1_issues"] == {"r3": 1, "r8": 1}  # no asset; account-01 has no holder
    assert by_source["syn-os-account-02"]["properties"] == {"accountNumber": ["NRSYN0000000002"]}
    assert summary["references_removed"] == {"bankaccount:bank": 1}  # a person, not a bank


def test_no_relationship_end_can_be_a_relationship() -> None:
    """Pass 2 relies on it: dropping a relationship never leaves another one without an end."""
    ends = {name: bulk._ends(name) for name in sorted(ALLOWED_SCHEMATA) if bulk._ends(name)}
    for name, props in ends.items():
        for prop in props:
            assert not [other for other in ends if bulk._in_range(name, prop, other)], prop


def test_with_the_pep_decision_topics_are_kept_exactly(data_env: Any, mock: Transport) -> None:
    setup(data_env, peps=True)
    by_source, summary = fetch_and_build()
    for source_id, record in by_source.items():
        assert topics(record) == SOURCE[source_id]["properties"].get("topics", [])
    assert {"NK-synPersonAlpha", "syn-os-position_01", "syn-os-occupancy-01"} <= set(by_source)
    assert summary["pep_data"] == "kept"
    for key in ("pep_role_topics_removed", "pep_only_entities_skipped", "pep_linked_entities_kept"):
        assert summary[key] == {}


def test_without_the_pep_decision_pep_data_is_removed(data_env: Any, mock: Transport) -> None:
    setup(data_env)
    by_source, summary = fetch_and_build()
    assert topics(by_source["NK-synPersonEpsilon"]) == ["sanction", "gov.national"]
    assert topics(by_source["syn-os-person-iota"]) == ["debarment"]  # held by a skipped Occupancy
    skipped = {"NK-synPersonAlpha", "NK-synPersonBeta", "syn-os-position_01"}
    skipped |= {"syn-os-occupancy-01", "syn-os-family-01", "syn-os-directorship-01"}
    assert not skipped & set(by_source)
    # Never had a flag topic: they stay; the associated company loses the dangling reference.
    assert {"syn-os-address-01", "syn-os-company-eta", "syn-os-ownership-02"} <= set(by_source)
    assert "parent" not in by_source["syn-os-company-eta"]["properties"]
    assert not any(t.startswith("role.") for r in by_source.values() for t in topics(r))
    assert summary["pep_data"] == "removed"
    assert summary["pep_role_topics_removed"] == {"role.pep": 2}
    assert summary["pep_schemata_skipped"] == {"occupancy": 2, "position": 1}
    assert summary["pep_only_entities_skipped"] == {"person": 2}
    dropped = {"directorship": 2, "family": 1, "ownership": 1, "sanction": 1}
    assert summary["relationships_dropped"] == dropped
    assert summary["pep_relationships_dropped"] == {"directorship": 1, "family": 1}
    removed = {"bankaccount:bank": 1, "company:parent": 1}  # none from a dropped one
    assert summary["references_removed"] == removed
    assert summary["pep_linked_entities_kept"] == {"address": 1}  # Alpha's; Iota has a flag
    assert summary["flags"] == {"sanctioned": 3}  # Gamma, Epsilon, Zeta; sanction.linked sets none


def test_the_flag_rule_knows_every_followthemoney_topic() -> None:
    """Fails when FollowTheMoney's topics change, so that a human classifies the new ones (7.1.1)
    before the PEP rule uses them (as M2.10a's policy test does, until the loader shares it)."""
    names = sorted(registry.topic.names)
    digest = hashlib.sha256(" ".join(names).encode()).hexdigest()[:16]
    assert (len(names), len(bulk.flag_topics(names)), digest) == (75, 52, "06d4a4abc245c49d")


@pytest.mark.parametrize(("checksum", "message"), [("0" * 40, "SHA-1"), ("", "no checksum")])
def test_a_checksum_that_is_missing_or_does_not_match_stops_the_build(
    data_env: Any, mock: Transport, checksum: str, message: str
) -> None:
    setup(data_env)
    mock.checksum = checksum
    assert run("data", "fetch").exit_code == 0
    result = run("ingest", "build")
    assert result.exit_code == 1 and message in result.output
    assert not layout.records_dir("uk-test", DATASET).exists()


def test_gate_in_the_builder_itself(data_env: Any, mock: Transport, tmp_path: Path) -> None:
    setup(data_env)
    assert run("data", "fetch").exit_code == 0  # the download is there
    data_env.allow_real("uk-test", opensanctions="none", pep_sources=[])
    context = BuildContext(load_project(), "build-1", tmp_path / "out", tmp_path / "work")
    with pytest.raises(RealDataRefused, match=r"needs access\.opensanctions licensed or exempt"):
        bulk.build(load_profile("uk-test"), context)
    assert not (tmp_path / "out").exists() and not (tmp_path / "work").exists()
