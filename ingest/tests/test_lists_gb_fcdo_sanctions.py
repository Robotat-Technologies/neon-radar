"""The UK Sanctions List loader (PHASE-2.md M2.6a). Synthetic fixture only: every name, number
and reference in `fixtures/lists/gb_fcdo_sanctions/uk-sanctions-list.xml` is invented."""

import dataclasses
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import sources
from neonradar_ingest.data.sources import BuildError
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.lists import gb_fcdo, shared
from neonradar_ingest.sources.lists.common import sanction_id

FIXTURES = Path(__file__).parent / "fixtures" / "lists" / "gb_fcdo_sanctions"
FIXTURE = FIXTURES / "uk-sanctions-list.xml"
XSD = FIXTURES / "SanctionsListSchema-4.33.3.xsd"
PROFILE = "uk-lists"
runner = CliRunner()


class Server:
    """A mock transport that serves one body and records every request."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return httpx.Response(200, content=self.body)

    def client(self) -> HttpClient:
        transport = httpx.MockTransport(self.handler)
        return HttpClient(
            "", follow_redirects=True, limiter=RateLimiter(100.0), transport=transport
        )


def serve(monkeypatch: pytest.MonkeyPatch, body: bytes) -> Server:
    server = Server(body)
    spec = dataclasses.replace(sources._SOURCES[gb_fcdo.DATASET], client=server.client)
    monkeypatch.setitem(sources._SOURCES, gb_fcdo.DATASET, spec)
    return server


def use_profile(data_env: Any, **options: bool) -> None:
    block = {"enabled": True, **options}
    data_env.write_profile(PROFILE, real_data=True, sources={gb_fcdo.DATASET: block})
    data_env.allow_real(PROFILE)


def fetch_and_build(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, *extra: str, body: bytes | None = None
) -> Any:
    serve(monkeypatch, FIXTURE.read_bytes() if body is None else body)
    fetched = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert fetched.exit_code == 0, fetched.output
    args = ["ingest", "build", "--profile", PROFILE, "--dataset", gb_fcdo.DATASET, *extra]
    return runner.invoke(app, args)


def records_dir(data_env: Any) -> Path:
    return data_env.cache / "real" / "records" / PROFILE / gb_fcdo.DATASET


def load_records(data_env: Any) -> dict[str, dict[str, Any]]:
    path = records_dir(data_env) / f"{gb_fcdo.DATASET}.ftm.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return {record["id"]: record for record in map(json.loads, lines)}


def summary(data_env: Any) -> dict[str, Any]:
    folder = data_env.cache / "reports" / PROFILE
    builds = sorted(folder.glob("ingest-build-*.json"))
    built: dict[str, Any] = json.loads(builds[-1].read_text(encoding="utf-8"))
    return built["datasets"][gb_fcdo.DATASET]  # type: ignore[no-any-return]


@pytest.fixture
def built(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    return load_records(data_env)


def props(record: dict[str, Any]) -> dict[str, list[str]]:
    return record["properties"]  # type: ignore[no-any-return]


def sanctions_of(records: dict[str, dict[str, Any]], party: str) -> list[dict[str, Any]]:
    found = [r for r in records.values() if r["schema"] == "Sanction"]
    return sorted((r for r in found if props(r)["entity"] == [party]), key=lambda r: r["id"])


def test_fixture_validates_against_the_committed_xsd() -> None:
    if not XSD.is_file():
        pytest.skip("the publisher's XSD is not committed (see the pull request)")
    import xmlschema

    schema = xmlschema.XMLSchema(str(XSD.resolve()), allow="sandbox")  # never fetches anything
    schema.validate(str(FIXTURE.resolve()))


def test_gate_refuses_a_list_left_out_of_access_sanctions_lists(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2.6 rule 2: the profile may run on this machine, but the list is not allowed."""
    data_env.write_project(
        real_data_profiles=["uk-tiny"],
        data_protection_filed=True,
        sanctions_lists=["us_ofac_sdn", "eu_fsf"],
    )
    monkeypatch.setenv("NR_REAL_DATA_MACHINE", "approved")
    server = serve(monkeypatch, FIXTURE.read_bytes())
    for command in (["data", "fetch"], ["ingest", "build"]):
        args = [*command, "--profile", "uk-tiny", "--dataset", gb_fcdo.DATASET]
        result = runner.invoke(app, args)
        assert result.exit_code == 3, result.output
        assert "gb_fcdo_sanctions is not in access.sanctions_lists" in result.output
    assert server.requests == []
    assert not (data_env.cache / "real").exists()


def test_fetch_downloads_the_static_file_with_the_date_as_version(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    server = serve(monkeypatch, FIXTURE.read_bytes())
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 0, result.output
    assert [str(r.url) for r in server.requests] == [gb_fcdo.URL]
    assert server.requests[0].headers["User-Agent"].startswith("NeonRadar/")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    folder = data_env.cache / "real" / "sources" / gb_fcdo.DATASET / "main" / today
    record = json.loads((folder / "download.json").read_text(encoding="utf-8"))
    assert record["complete"] is True
    assert [(f["name"], f["url"]) for f in record["files"]] == [(gb_fcdo.FILE_NAME, gb_fcdo.URL)]


def test_build_needs_a_download(data_env: Any) -> None:
    use_profile(data_env)
    args = ["ingest", "build", "--profile", PROFILE, "--accept-size"]
    result = runner.invoke(app, args)
    assert result.exit_code == 1
    assert "no complete download of UK-Sanctions-List.xml" in result.output


def test_grouping(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    parties = sorted(r["id"] for r in built.values() if r["schema"] != "Sanction")
    assert parties == [
        "uksl-SYN0006",  # alone: no group id, no UN reference
        "uksl-SYN0007",  # group 9002 disagrees on IndividualEntityShip: split
        "uksl-SYN0008",
        "uksl-SYN0011",  # its UN reference sits on two groups: joins neither
        "uksl-SYN0012",
        "uksl-g9001",
        "uksl-g9003",
        "uksl-g9004",
        "uksl-g9005",  # SYN0014 plus SYN0003, joined through its UN reference
        "uksl-un-ZZI.002",  # SYN0004 and SYN0005 share a UN reference
    ]
    grouped = {props(s)["authorityId"][0] for s in sanctions_of(built, "uksl-g9001")}
    assert grouped == {"SYN0001", "SYN0002"}  # one party, two sanctions
    joined = {props(s)["authorityId"][0] for s in sanctions_of(built, "uksl-g9005")}
    assert joined == {"SYN0003", "SYN0014"}
    shared_un = sanctions_of(built, "uksl-un-ZZI.002")
    assert {props(s)["authorityId"][0] for s in shared_un} == {"SYN0004", "SYN0005"}
    assert {props(s)["unscId"][0] for s in shared_un} == {"ZZI.002"}
    assert built["uksl-g9001"]["nr"] == {"v": "1.1", "source_ref": "g9001"}
    assert built["uksl-un-ZZI.002"]["nr"]["source_ref"] == "un-ZZI.002"
    assert built["uksl-SYN0006"]["nr"]["source_ref"] == "SYN0006"
    assert (built["uksl-SYN0007"]["schema"], built["uksl-SYN0008"]["schema"]) == (
        "Person",
        "Organization",
    )
    counts = summary(data_env)
    assert counts["parties"] == {"group": 4, "un_reference": 1, "unique_id": 5}
    assert (counts["group_conflicts"], counts["joined_by_un_reference"]) == (2, 1)
    assert counts["designations"] == 14


def test_person_mapping(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    person = built["uksl-g9001"]
    assert person["schema"] == "Person"
    assert person["datasets"] == ["gb_fcdo_sanctions"]
    p = props(person)
    assert p["topics"] == ["sanction"]
    assert p["name"] == ["Ivo KESTRANE"]
    assert (p["firstName"], p["lastName"]) == (["Ivo"], ["KESTRANE"])
    # Variation, good quality, empty strength with two words, non-Latin script.
    assert sorted(p["alias"]) == sorted(
        ["Iwo KESTRAN", "Ivo Marek KESTRANNE", "Ivo KESTREN", "Иво Кестране"]
    )
    assert sorted(p["weakAlias"]) == ["Ivko", "Kesto"]  # low quality; empty with one word
    assert sorted(p["birthDate"]) == ["1968", "1968-05", "1968-11-02"]  # placeholders
    assert p["nationality"] == ["cy"]
    assert (p["birthPlace"], p["birthCountry"]) == (["Tarnbury"], ["cy"])
    assert p["gender"] == ["male"]
    assert (p["passportNumber"], p["idNumber"]) == (["SYNP000101"], ["SYNN000101"])
    assert p["address"] == ["1 Sedge Lane, Limassol, QQ1 1QQ, Cyprus"]
    assert p["country"] == ["cy"]
    assert "title" not in p and "position" not in p  # keep_positions is off by default
    assert props(built["uksl-un-ZZI.002"])["gender"] == ["female"]
    counts = summary(data_env)
    assert counts["unmapped_countries"] == 1  # "Atlantis" is counted, never guessed
    assert counts["unparseable_dates"] == 1  # "circa 1970"


def test_sanction_mapping(built: dict[str, dict[str, Any]]) -> None:
    first = built[sanction_id("uksl", "uksl-g9001", "SYN0001")]
    assert first["nr"] == {"v": "1.1", "source_ref": "SYN0001"}
    assert props(first) == {
        "entity": ["uksl-g9001"],
        "authority": ["UK Foreign, Commonwealth and Development Office"],
        "country": ["gb"],
        "authorityId": ["SYN0001"],
        "program": ["Synthetic Regime Alpha"],
        "startDate": ["2022-03-15"],
        "modifiedAt": ["2025"],  # dd/mm/2025
        "provisions": ["Asset freeze", "Travel ban"],
    }
    second = props(built[sanction_id("uksl", "uksl-g9001", "SYN0002")])
    assert (second["startDate"], second["modifiedAt"]) == (["2023-04"], ["2025"])
    assert second["program"] == ["Synthetic Regime Beta"]
    joined = props(built[sanction_id("uksl", "uksl-g9005", "SYN0003")])
    assert joined["unscId"] == ["ZZI.004"]  # "zzi.004." normalised
    alone = props(built[sanction_id("uksl", "uksl-SYN0006", "SYN0006")])
    assert alone["startDate"] == ["2021-02"]  # 31/02 is not a day: year and month


def test_organization_registration_numbers(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    p = props(built["uksl-SYN0012"])
    assert p["name"] == ["Teasel Quay Trading Ltd"]
    assert (p["alias"], p["weakAlias"]) == (["Teasel Quay Trading Limited"], ["TQT"])
    # Only the labelled UK number and the LEI; the unlabelled, the Cyprus and the SY number
    # are counted, not loaded.
    assert p["registrationNumber"] == ["99000112"]
    assert p["jurisdiction"] == ["gb"]
    assert p["leiCode"] == ["SYN0000000000000AB65"]
    assert p["country"] == ["gb"]
    assert "registrationNumber" not in props(built["uksl-SYN0008"])
    counts = summary(data_env)
    assert counts["registration_numbers_not_loaded"] == 3
    assert counts["stub_names_skipped"] == 3  # one parent company, two subsidiaries


def test_ships_and_never_loaded_fields(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    text = (records_dir(data_env) / f"{gb_fcdo.DATASET}.ftm.jsonl").read_text(encoding="utf-8")
    for value in (
        "LINNET WOLD",  # the ship
        "SYNIMO0001",
        "nobody@example.invalid",  # e-mail
        "example.invalid",  # website
        "+00 0000",  # phone
        "SYNWALLET0001",  # crypto wallet
        "Synthetic other information",
        "Synthetic statement",  # reasons: keep_reasons is off
        "Synthetic additional information",
        "Synthetic identity card",
        "Umber Garth",  # subsidiary, parent: never stubs
        "Tansy Strand",
        "Copper Acre",
        "Limited company",  # type of entity
        "Dr",
    ):
        assert value not in text, value
    counts = summary(data_env)
    assert (counts["skipped_vessel"], counts["crypto_wallets_skipped"]) == (1, 1)
    manifest = json.loads(
        (records_dir(data_env) / f"{gb_fcdo.DATASET}.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts"]["skipped"] == {"CryptoWallet": 1, "Vessel": 1, "stub_names": 3}
    assert manifest["counts"]["by_schema"] == {"Organization": 2, "Person": 8, "Sanction": 13}
    assert manifest["source"]["urls"] == [gb_fcdo.URL]
    assert manifest["record_contract"] == "1.1.0"
    assert "list_generated: 2026-10-20T09:00:00" in manifest["notes"]


def test_keep_reasons_and_positions(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    use_profile(data_env, keep_reasons=True, keep_positions=True)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    records = load_records(data_env)
    p = props(records["uksl-g9001"])
    assert p["title"] == ["Dr"]
    assert p["position"] == ["Synthetic director", "Synthetic adviser"]
    reason = props(records[sanction_id("uksl", "uksl-g9001", "SYN0001")])["reason"]
    assert reason == ["Synthetic statement & reasons for a test"]  # HTML entity decoded
    assert "reason" not in props(records[sanction_id("uksl", "uksl-g9001", "SYN0002")])


def test_profile_block_model() -> None:
    options = shared.ListOptions(enabled=True)
    assert (options.keep_reasons, options.keep_positions) == (False, False)
    with pytest.raises(ValueError, match="keep_notes"):
        shared.ListOptions.model_validate({"enabled": True, "keep_notes": True})
    with pytest.raises(ValueError):
        shared.ListOptions.model_validate({"enabled": True, "keep_reasons": "yes"})


def test_summary_counts_and_rates(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    counts = summary(data_env)
    assert counts["status"] == "ok"
    assert counts["list_generated"] == "2026-10-20T09:00:00"
    assert counts["records"] == {"organization": 2, "person": 8, "sanction": 13}
    assert counts["fill_rates"] == {
        "person_birth_date": 0.875,
        "person_nationality": 0.25,
        "person_passport_or_id": 0.25,
        "sanction_program": 1.0,
        "sanction_start_date": 1.0,
        "organization_registration_or_lei": 0.5,
    }
    assert counts["bounds_outside_accepted"] == 2
    assert counts["unknown_elements"] == 0


def test_bounds_fail_with_exit_4_unless_accepted(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch)
    assert result.exit_code == 4, result.output
    assert (
        "unexpected size for gb_fcdo_sanctions: Organization 2, expected 900 to 3000; "
        "the format may have changed" in result.output
    )
    assert "Person 8, expected 3000 to 7200" in result.output
    assert not records_dir(data_env).exists()  # nothing replaced
    accepted = runner.invoke(
        app,
        ["ingest", "build", "--profile", PROFILE, "--dataset", gb_fcdo.DATASET, "--accept-size"],
    )
    assert accepted.exit_code == 0, accepted.output


def test_zero_fill_rate_fails_even_with_accept_size(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    body = re.sub(r"\s*<DOBs>.*?</DOBs>", "", FIXTURE.read_text(encoding="utf-8"), flags=re.S)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size", body=body.encode())
    assert result.exit_code == 4, result.output
    assert "the fill rate of person_birth_date is zero; the parser is broken" in result.output
    assert not records_dir(data_env).exists()


def test_parse_ignores_namespaces_and_refuses_bad_xml(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    namespaced = tmp_path / "namespaced.xml"
    namespaced.write_text(
        text.replace("<Designations ", '<Designations xmlns="urn:example:synthetic" '),
        encoding="utf-8",
    )
    stamp, designations, _ = gb_fcdo.parse(namespaced)
    assert (stamp, len(designations)) == ("2026-10-20T09:00:00", 14)
    broken = tmp_path / "broken.xml"
    broken.write_text("<Designations><Designation>", encoding="utf-8")
    with pytest.raises(BuildError, match="not a well-formed list file"):
        gb_fcdo.parse(broken)
    entities = tmp_path / "entities.xml"
    entities.write_text(
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><Designations>&a;</Designations>',
        encoding="utf-8",
    )
    with pytest.raises(BuildError, match="EntitiesForbidden"):
        gb_fcdo.parse(entities)


def _designation(uid: str, kind: str, group: str | None, un: str | None) -> gb_fcdo.Designation:
    return gb_fcdo.Designation(unique_id=uid, group_id=group, un_ref=un, kind=kind)


def test_group_conflicts_without_a_file() -> None:
    from collections import Counter

    counts: Counter[str] = Counter()
    parties = gb_fcdo.group(
        [
            _designation("SYNA001", "Individual", "1", "ZZI.010"),
            _designation("SYNA002", "Entity", None, "ZZI.010"),  # another type: not joined
            _designation("SYNA003", "Individual", None, "ZZI.011"),
            _designation("SYNA004", "Entity", None, "ZZI.011"),  # share a reference, disagree
        ],
        counts,
    )
    assert [(p.id, p.form) for p in parties] == [
        ("uksl-SYNA002", "unique_id"),
        ("uksl-SYNA003", "unique_id"),
        ("uksl-SYNA004", "unique_id"),
        ("uksl-g1", "group"),
    ]
    assert counts["group_conflicts"] == 2
    assert gb_fcdo.party_id("SYN 0001") == gb_fcdo.party_id("SYN 0001")
    assert re.fullmatch(r"uksl-x[0-9a-f]{20}", gb_fcdo.party_id("SYN 0001"))
