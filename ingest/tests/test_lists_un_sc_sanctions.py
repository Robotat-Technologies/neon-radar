"""The UN Security Council Consolidated List loader (PHASE-2.md M2.6c). Synthetic fixture only:
every name, number and reference in `fixtures/lists/un_sc_sanctions/consolidated.xml` is
invented (the `ZZ` regime does not exist)."""

import dataclasses
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_cli.main import app
from neonradar_ingest.data import sources
from neonradar_ingest.data.project import REPO_ROOT
from neonradar_ingest.data.sources import BuildError
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.lists import shared, un_sc
from neonradar_ingest.sources.lists.common import sanction_id

FIXTURE = Path(__file__).parent / "fixtures" / "lists" / "un_sc_sanctions" / "consolidated.xml"
PROFILE = "un-lists"
LISTS = ["gb_fcdo_sanctions", "us_ofac_sdn", "un_sc_sanctions", "eu_fsf"]
# The signed storage URL the UN redirects to (note 3.1), with an invented host and signature.
SIGNED = (
    "https://files.example.invalid/legacy/EN/consolidatedLegacyByPRN.xml"
    "?sv=2099-01-01&se=2099-01-01T01%3A00%3A00Z&sr=b&sp=r&sig=SYNTHETICSIGNATURE"
)
P1, P2, ORG = "unsc-ZZI.001", "unsc-ZZI.002", "unsc-ZZE.001"
runner = CliRunner()


class Server:
    """A mock transport: the list URL redirects to the signed URL, which serves the body."""

    def __init__(self, body: bytes) -> None:
        self.body = body
        self.requests: list[httpx.Request] = []

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if str(request.url) == un_sc.URL:
            return httpx.Response(302, headers={"Location": SIGNED})
        return httpx.Response(200, content=self.body)

    def client(self) -> HttpClient:
        transport = httpx.MockTransport(self.handler)
        limiter = RateLimiter(100.0)
        return HttpClient(
            "", follow_redirects=True, limiter=limiter, transport=transport, log_query=False
        )


def serve(monkeypatch: pytest.MonkeyPatch, body: bytes) -> Server:
    server = Server(body)
    spec = dataclasses.replace(sources._SOURCES[un_sc.DATASET], client=server.client)
    monkeypatch.setitem(sources._SOURCES, un_sc.DATASET, spec)
    return server


@pytest.fixture(autouse=True)
def permitted(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A stand-in for the data steward's permission file (the real one does not exist)."""
    path = tmp_path / "licences" / "un_sc_sanctions.md"
    path.parent.mkdir()
    path.write_text("Synthetic stand-in for a test.\n", encoding="utf-8")
    monkeypatch.setattr(un_sc, "PERMISSION_FILE", path)
    return path


def use_profile(data_env: Any, **options: bool) -> None:
    block = {"enabled": True, **options}
    data_env.write_profile(PROFILE, real_data=True, sources={un_sc.DATASET: block})
    data_env.allow_real(PROFILE, sanctions_lists=LISTS)


def fetch_and_build(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, *extra: str, body: bytes | None = None
) -> Any:
    serve(monkeypatch, FIXTURE.read_bytes() if body is None else body)
    fetched = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert fetched.exit_code == 0, fetched.output
    args = ["ingest", "build", "--profile", PROFILE, "--dataset", un_sc.DATASET, *extra]
    return runner.invoke(app, args)


def records_dir(data_env: Any) -> Path:
    cache: Path = data_env.cache
    return cache / "real" / "records" / PROFILE / un_sc.DATASET


def load_records(data_env: Any) -> dict[str, dict[str, Any]]:
    path = records_dir(data_env) / f"{un_sc.DATASET}.ftm.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return {record["id"]: record for record in map(json.loads, lines)}


def summary(data_env: Any) -> dict[str, Any]:
    builds = sorted((data_env.cache / "reports" / PROFILE).glob("ingest-build-*.json"))
    built: dict[str, Any] = json.loads(builds[-1].read_text(encoding="utf-8"))
    return built["datasets"][un_sc.DATASET]  # type: ignore[no-any-return]


@pytest.fixture
def built(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    return load_records(data_env)


def props(record: dict[str, Any]) -> dict[str, list[str]]:
    return record["properties"]  # type: ignore[no-any-return]


def test_gate_refuses_a_list_left_out_of_access_sanctions_lists(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2.6 rule 2: the profile may run on this machine, but the list is not allowed (OD-22)."""
    data_env.write_project(real_data_profiles=["uk-tiny"], data_protection_filed=True)
    monkeypatch.setenv("NR_REAL_DATA_MACHINE", "approved")
    server = serve(monkeypatch, FIXTURE.read_bytes())
    for command in (["data", "fetch"], ["ingest", "build"]):
        args = [*command, "--profile", "uk-tiny", "--dataset", un_sc.DATASET]
        result = runner.invoke(app, args)
        assert result.exit_code == 3, result.output
        assert "un_sc_sanctions is not in access.sanctions_lists" in result.output
    assert server.requests == []
    assert not (data_env.cache / "real").exists()


def test_permission_gate_refuses_without_the_written_permission(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, permitted: Path
) -> None:
    """Even when access.sanctions_lists names the list, no request and no build without the
    UN's written permission in docs/data/licences/un_sc_sanctions.md (PHASE-2.md 3.3)."""
    assert not (REPO_ROOT / "docs" / "data" / "licences" / "un_sc_sanctions.md").exists()
    use_profile(data_env)
    server = serve(monkeypatch, FIXTURE.read_bytes())
    assert runner.invoke(app, ["data", "fetch", "--profile", PROFILE]).exit_code == 0
    permitted.unlink()
    requests = len(server.requests)
    for command in (["data", "fetch"], ["ingest", "build", "--accept-size"]):
        result = runner.invoke(app, [*command, "--profile", PROFILE])
        assert result.exit_code == 3, result.output
        assert "rule un_written_permission" in result.output
        assert "un_sc_sanctions needs the UN's written permission" in result.output
        assert "docs/data/licences/un_sc_sanctions.md" in result.output
    assert len(server.requests) == requests  # nothing sent after the permission went
    assert not records_dir(data_env).exists()


def test_fetch_follows_the_redirect_and_never_keeps_its_query(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    assert sources._SOURCES[un_sc.DATASET].client is shared.list_client  # as registered
    with shared.list_client() as client:
        assert (client.follow_redirects, client.log_query) == (True, False)
    caplog.set_level(logging.DEBUG)
    use_profile(data_env)
    server = serve(monkeypatch, FIXTURE.read_bytes())  # the same settings on a mock transport
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 0, result.output
    assert [str(r.url) for r in server.requests] == [un_sc.URL, SIGNED]
    assert server.requests[0].headers["User-Agent"].startswith("NeonRadar/")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    folder = data_env.cache / "real" / "sources" / un_sc.DATASET / "main" / today
    record = json.loads((folder / "download.json").read_text(encoding="utf-8"))
    assert [(f["name"], f["url"]) for f in record["files"]] == [(un_sc.FILE_NAME, un_sc.URL)]
    assert (folder / un_sc.FILE_NAME).read_bytes() == FIXTURE.read_bytes()
    assert "files.example.invalid/legacy/EN/consolidatedLegacyByPRN.xml" in caplog.text
    for secret in ("SYNTHETICSIGNATURE", "sig=", "se=", "sv=2099"):
        assert secret not in caplog.text + result.output, secret
        for path in data_env.cache.rglob("*.json"):
            assert secret not in path.read_text(encoding="utf-8"), path.name


def test_first_person(built: dict[str, dict[str, Any]]) -> None:
    person = built[P1]
    assert (person["schema"], person["datasets"]) == ("Person", ["un_sc_sanctions"])
    assert person["nr"] == {"v": "1.1", "source_ref": "ZZI.001"}
    p = props(person)
    assert p["topics"] == ["sanction"]
    assert p["name"] == ["Yazan Zafer Velqasimi"]  # FOURTH_NAME "na" is missing
    assert (p["firstName"], p["lastName"]) == (["Yazan"], ["Velqasimi"])
    # Good quality split on "; ", empty quality with two words, the original script.
    assert sorted(p["alias"]) == sorted(
        ["Yazan Zafir Velqasimi", "Yazan Velqasimy", "Yazen Velqasimi", "يزن ظافر فلقاسمي"]
    )
    assert sorted(p["weakAlias"]) == ["Velqasimi", "Yazan Z. Velqasimi"]  # low; empty, one word
    # EXACT, EXACT with an offset, APPROXIMATELY and a BETWEEN range of three years.
    assert sorted(p["birthDate"]) == ["1970", "1971-06-04", "1972-02-09", "1975", "1976", "1977"]
    assert p["nationality"] == ["cy"]  # "Possibly Cyprus" is counted, not guessed
    assert (p["birthPlace"], p["birthCountry"]) == (["Tarnbury, Marram Province"], ["cy"])
    assert p["gender"] == ["male"]
    assert sorted(p["passportNumber"]) == ["SYNP000101", "SYNP000102"]  # English and French
    assert p["idNumber"] == ["SYNN000101"]
    assert (p["address"], p["country"]) == (["4 Sedge Row, Limassol, QQ4 4QQ, Cyprus"], ["cy"])
    assert "title" not in p and "position" not in p  # keep_positions is off by default


def test_second_person_not_available_values_and_wide_ranges(
    built: dict[str, dict[str, Any]],
) -> None:
    person = built[P2]  # REFERENCE_NUMBER "zzi.002." normalised
    assert person["nr"]["source_ref"] == "ZZI.002"
    p = props(person)
    assert (p["name"], p["firstName"], p["lastName"]) == (
        ["Rakan Zubeirono"],
        ["Rakan"],
        ["Zubeirono"],
    )
    assert sorted(p["alias"]) == ["Raqan Zubeirono", "Ракан Зубейроно"]
    # BETWEEN 1940 and 1980 is wider than 20 years and "early 1960s" does not parse; "na" is
    # never a country (it would be Namibia) nor a gender.
    for name in ("weakAlias", "birthDate", "nationality", "gender", "birthPlace", "birthCountry"):
        assert name not in p, name
    assert (p["passportNumber"], p["idNumber"]) == (["SYNP000201"], ["SYNN000201"])
    assert (p["address"], p["country"]) == (["Nicosia, Cyprus"], ["cy"])


def test_organization_and_never_loaded_fields(
    built: dict[str, dict[str, Any]], data_env: Any
) -> None:
    p = props(built[ORG])
    assert built[ORG]["schema"] == "Organization"
    assert p["name"] == ["Copper Acre Interiors Ltd"]
    assert p["alias"] == ["Copper Acre Interiors Limited"]
    assert sorted(p["weakAlias"]) == ["CAI", "Copper Acre Trading"]  # Low; unknown "a.k.a."
    assert p["country"] == ["gb"]
    for name in ("registrationNumber", "leiCode", "jurisdiction"):
        assert name not in p, name
    text = (records_dir(data_env) / f"{un_sc.DATASET}.ftm.jsonl").read_text(encoding="utf-8")
    for never in (
        "Synthetic comments",  # COMMENTS1: keep_reasons is off
        "Synthetic reasons",
        "SY000101",
        "99000301",  # a number in the comments is never a registration number
        "example.invalid",  # Interpol link
        "UN List",
        "Synthetic address note",
        "Synthetic date note",
        "Synthetic document note",
        "SYND000101",  # a driving licence is counted, not loaded
        "Synthetic title",
        "Synthetic position",
    ):
        assert never not in text, never


def test_sanctions(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    first = built[sanction_id("unsc", P1, "ZZI.001")]
    assert first["nr"] == {"v": "1.1", "source_ref": "ZZI.001"}
    assert props(first) == {
        "entity": [P1],
        "authority": ["United Nations Security Council"],
        "authorityId": ["990001"],
        "unscId": ["ZZI.001"],
        "program": ["Synthetic ZZ regime"],
        "startDate": ["2021-03-15"],
        "listingDate": ["2021-03-15"],
        "modifiedAt": ["2024-11-20"],  # the latest LAST_DAY_UPDATED
    }
    second = props(built[sanction_id("unsc", P2, "ZZI.002")])
    assert (second["startDate"], second["listingDate"]) == (["2022-07-01"], ["2022-07-01"])
    assert "modifiedAt" not in second  # an empty LAST_DAY_UPDATED
    entity = props(built[sanction_id("unsc", ORG, "ZZE.001")])
    assert (entity["unscId"], entity["modifiedAt"]) == (["ZZE.001"], ["2025-08-30"])
    manifest = json.loads(
        (records_dir(data_env) / f"{un_sc.DATASET}.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts"]["by_schema"] == {"Organization": 1, "Person": 2, "Sanction": 3}
    assert manifest["source"]["urls"] == [un_sc.URL]
    assert "list_generated: 2026-10-20T08:30:00.123Z" in manifest["notes"]


def test_keep_reasons_and_positions(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    use_profile(data_env, keep_reasons=True, keep_positions=True)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    records = load_records(data_env)
    p = props(records[P1])
    assert p["title"] == ["Synthetic title"]
    assert p["position"] == ["Synthetic position one", "Synthetic position two"]
    reason = props(records[sanction_id("unsc", P1, "ZZI.001")])["reason"]
    assert reason == ["Synthetic comments for a test. UK Company Number SY000101."]
    assert "reason" not in props(records[sanction_id("unsc", P2, "ZZI.002")])  # "na"
    assert "registrationNumber" not in props(records[ORG])  # reasons never give numbers


def test_summary_counts_and_rates(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    counts = summary(data_env)
    assert counts["status"] == "ok"
    assert counts["list_generated"] == "2026-10-20T08:30:00.123Z"
    assert counts["records"] == {"organization": 1, "person": 2, "sanction": 3}
    assert counts["fill_rates"] == {
        "person_birth_date": 0.5,
        "person_nationality": 0.5,
        "person_passport_or_id": 1.0,
        "sanction_program": 1.0,
        "sanction_start_date": 1.0,
        "organization_registration_or_lei": 0.0,
    }
    assert counts["entries"] == 3
    assert counts["unmapped_countries"] == 2  # "Possibly Cyprus", "Atlantis"
    assert counts["unparseable_dates"] == 1  # "early 1960s"
    assert counts["wide_birth_year_ranges"] == 1
    assert counts["documents_not_loaded"] == 1
    assert counts["unknown_alias_qualities"] == 1
    assert counts["unknown_elements"] == 0
    assert counts["bounds_outside_accepted"] == 2


def test_bounds_fail_with_exit_4_unless_accepted(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch)
    assert result.exit_code == 4, result.output
    assert "unexpected size for un_sc_sanctions: Organization 1, expected 180 to 420" in (
        result.output
    )
    assert not records_dir(data_env).exists()


def test_profile_block_rejects_unknown_keys(data_env: Any) -> None:
    data_env.write_profile(
        PROFILE, real_data=True, sources={un_sc.DATASET: {"enabled": True, "keep_notes": True}}
    )
    data_env.allow_real(PROFILE, sanctions_lists=LISTS)
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 2, result.output
    assert "keep_notes" in result.output


def test_parse_skips_duplicates_and_entries_without_reference(tmp_path: Path) -> None:
    path = tmp_path / "list.xml"
    path.write_text(
        '<CONSOLIDATED_LIST dateGenerated="2026-10-20T08:30:00Z"><INDIVIDUALS>'
        "<INDIVIDUAL><FIRST_NAME>Nadim</FIRST_NAME><REFERENCE_NUMBER>ZZi.010</REFERENCE_NUMBER>"
        "<EXTRA_FIELD>x</EXTRA_FIELD></INDIVIDUAL>"
        "<INDIVIDUAL><FIRST_NAME>Nadim</FIRST_NAME><REFERENCE_NUMBER>ZZI.010 </REFERENCE_NUMBER>"
        "</INDIVIDUAL>"
        "<INDIVIDUAL><FIRST_NAME>Rakan</FIRST_NAME><REFERENCE_NUMBER>na</REFERENCE_NUMBER>"
        "</INDIVIDUAL></INDIVIDUALS></CONSOLIDATED_LIST>",
        encoding="utf-8",
    )
    stamp, entries, counts = un_sc.parse(path)
    assert (stamp, [e.reference for e in entries]) == ("2026-10-20T08:30:00Z", ["ZZI.010"])
    assert (counts["entries"], counts["duplicate_references"]) == (3, 1)
    assert (counts["entries_without_reference"], counts["unknown_elements"]) == (1, 1)
    options = shared.ListOptions(enabled=True)
    records = un_sc.entry_records(entries[0], options, counts)
    assert props(records[0])["name"] == ["Nadim"]
    assert "lastName" not in props(records[0])  # one name part: no last name


def test_parse_refuses_bad_xml(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<CONSOLIDATED_LIST><INDIVIDUALS>", encoding="utf-8")
    with pytest.raises(BuildError, match="not a well-formed list file"):
        un_sc.parse(broken)
    entities = tmp_path / "entities.xml"
    entities.write_text(
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><CONSOLIDATED_LIST>&a;'
        "</CONSOLIDATED_LIST>",
        encoding="utf-8",
    )
    with pytest.raises(BuildError, match="EntitiesForbidden"):
        un_sc.parse(entities)
