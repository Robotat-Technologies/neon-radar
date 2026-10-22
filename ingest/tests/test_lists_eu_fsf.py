"""The EU Financial Sanctions Files loader (PHASE-2.md M2.6d). Synthetic fixture only: every
name, number, reference and URL in `fixtures/lists/eu_fsf/eu-fsf-1-1.xml` is invented."""

import dataclasses
import json
import logging
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
from neonradar_ingest.sources.lists import eu_fsf
from neonradar_ingest.sources.lists.common import sanction_id

FIXTURE = Path(__file__).parent / "fixtures" / "lists" / "eu_fsf" / "eu-fsf-1-1.xml"
PROFILE = "eu-lists"
INVENTED = "SYNTOKEN0001"  # an invented token: the loader must send it and never store it
runner = CliRunner()


class Server:
    """A mock transport that answers with `statuses` first, then the body, on a fake clock."""

    def __init__(self, body: bytes, statuses: tuple[int, ...] = ()) -> None:
        self.body, self.statuses = body, iter(statuses)
        self.requests: list[httpx.Request] = []
        self.now, self.sleeps = 0.0, list[float]()

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        status = next(self.statuses, 200)
        return httpx.Response(status, content=self.body if status == 200 else b"")

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds

    def client(self) -> HttpClient:
        """The loader's own client (timeout, retries, backoff) on the mock transport."""
        client = eu_fsf.make_client(httpx.MockTransport(self.handler), sleep=self.sleep)
        client.limiter = RateLimiter(1.0, clock=lambda: self.now, sleep=self.sleep)
        return client


def serve(monkeypatch: pytest.MonkeyPatch, body: bytes, *statuses: int) -> Server:
    server = Server(body, statuses)
    spec = dataclasses.replace(sources._SOURCES[eu_fsf.DATASET], client=server.client)
    monkeypatch.setitem(sources._SOURCES, eu_fsf.DATASET, spec)
    return server


def use_profile(data_env: Any, **options: bool) -> None:
    block = {"enabled": True, **options}
    data_env.write_profile(PROFILE, real_data=True, sources={eu_fsf.DATASET: block})
    data_env.allow_real(PROFILE)


def fetch_and_build(data_env: Any, monkeypatch: pytest.MonkeyPatch, *extra: str) -> Any:
    serve(monkeypatch, FIXTURE.read_bytes())
    fetched = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert fetched.exit_code == 0, fetched.output
    args = ["ingest", "build", "--profile", PROFILE, "--dataset", eu_fsf.DATASET, *extra]
    return runner.invoke(app, args)


def records_dir(data_env: Any) -> Path:
    return data_env.cache / "real" / "records" / PROFILE / eu_fsf.DATASET


def load_records(data_env: Any) -> dict[str, dict[str, Any]]:
    path = records_dir(data_env) / f"{eu_fsf.DATASET}.ftm.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return {record["id"]: record for record in map(json.loads, lines)}


def summary(data_env: Any) -> dict[str, Any]:
    folder = data_env.cache / "reports" / PROFILE
    builds = sorted(folder.glob("ingest-build-*.json"))
    built: dict[str, Any] = json.loads(builds[-1].read_text(encoding="utf-8"))
    return built["datasets"][eu_fsf.DATASET]  # type: ignore[no-any-return]


@pytest.fixture
def built(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    return load_records(data_env)


def props(record: dict[str, Any]) -> dict[str, list[str]]:
    return record["properties"]  # type: ignore[no-any-return]


def sanction(records: dict[str, dict[str, Any]], party: str, key: str) -> dict[str, list[str]]:
    return props(records[sanction_id("eufsf", party, key)])


def test_gate_refuses_a_list_left_out_of_access_sanctions_lists(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2.6 rule 2: the profile may run on this machine, but the list is not allowed."""
    data_env.write_project(
        real_data_profiles=["uk-tiny"],
        data_protection_filed=True,
        sanctions_lists=["gb_fcdo_sanctions", "us_ofac_sdn"],
    )
    monkeypatch.setenv("NR_REAL_DATA_MACHINE", "approved")
    server = serve(monkeypatch, FIXTURE.read_bytes())
    for command in (["data", "fetch"], ["ingest", "build"]):
        args = [*command, "--profile", "uk-tiny", "--dataset", eu_fsf.DATASET]
        result = runner.invoke(app, args)
        assert result.exit_code == 3, result.output
        assert "eu_fsf is not in access.sanctions_lists" in result.output
    assert server.requests == []
    assert not (data_env.cache / "real").exists()


def test_the_token_is_sent_but_never_stored_or_logged(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    monkeypatch.setenv("NR_EU_FSF_TOKEN", INVENTED)
    use_profile(data_env)
    server = serve(monkeypatch, FIXTURE.read_bytes())
    fetched = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert fetched.exit_code == 0, fetched.output
    args = ["ingest", "build", "--profile", PROFILE, "--dataset", eu_fsf.DATASET, "--accept-size"]
    built = runner.invoke(app, args)
    assert built.exit_code == 0, built.output
    assert [str(r.url) for r in server.requests] == [f"{eu_fsf.URL}?token={INVENTED}"]
    assert server.requests[0].headers["User-Agent"].startswith("NeonRadar/")
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    folder = data_env.cache / "real" / "sources" / eu_fsf.DATASET / "main" / today
    record = json.loads((folder / "download.json").read_text(encoding="utf-8"))
    assert [(f["name"], f["url"]) for f in record["files"]] == [(eu_fsf.FILE_NAME, eu_fsf.URL)]
    manifest = records_dir(data_env) / f"{eu_fsf.DATASET}.manifest.json"
    assert json.loads(manifest.read_text(encoding="utf-8"))["source"]["urls"] == [eu_fsf.URL]
    written = [p for p in data_env.cache.rglob("*") if p.is_file() and p.name != eu_fsf.FILE_NAME]
    assert {p.name for p in written} >= {"download.json", manifest.name}
    assert any(p.parent.name == PROFILE and "ingest-build" in p.name for p in written)
    for path in written:  # download.json, the manifests, the summaries, the records
        assert INVENTED not in path.read_text(encoding="utf-8", errors="replace"), path.name
    assert "token=REDACTED" in caplog.text  # httpx logged the request, without the token
    assert INVENTED not in caplog.text + fetched.output + built.output


def test_the_token_comes_from_env_file_else_the_public_token(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("NR_EU_FSF_TOKEN", raising=False)
    use_profile(data_env)
    assert eu_fsf.token() == eu_fsf.PUBLIC_TOKEN
    with data_env.env_file.open("a", encoding="utf-8") as handle:
        handle.write("NR_EU_FSF_TOKEN=SYNTOKEN0002\n")
    assert eu_fsf.token() == "SYNTOKEN0002"
    monkeypatch.setenv("NR_EU_FSF_TOKEN", " ")  # empty: the public token
    assert eu_fsf.token() == eu_fsf.PUBLIC_TOKEN


def test_retries_on_500_with_backoff_factor_3_and_a_long_read_timeout(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    server = serve(monkeypatch, FIXTURE.read_bytes(), 500, 500, 500)
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 0, result.output
    assert (len(server.requests), server.sleeps) == (4, [3.0, 6.0, 12.0])
    timeout = {"connect": 10.0, "read": 300.0, "write": 60.0, "pool": 60.0}
    assert server.requests[0].extensions["timeout"] == timeout
    server = serve(monkeypatch, FIXTURE.read_bytes(), *[500] * 6)
    monkeypatch.setenv("NR_EU_FSF_TOKEN", INVENTED)
    for path in (data_env.cache / "real" / "sources").rglob("download.json"):
        path.unlink()  # as if nothing had been downloaded yet
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 1, result.output
    assert "eu_fsf: stopped: xmlFullSanctionsList_1_1.xml: HTTP 500 after retries" in result.output
    assert (len(server.requests), server.sleeps) == (6, [3.0, 6.0, 12.0, 24.0, 48.0])
    assert INVENTED not in result.output


def test_person_mapping(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    person = built["eufsf-990001"]
    assert (person["schema"], person["datasets"]) == ("Person", ["eu_fsf"])
    assert person["nr"] == {"v": "1.1", "source_ref": "990001"}
    p = props(person)
    assert p["topics"] == ["sanction"]
    # The French name comes first, but `name` is the first strong one without a language.
    assert p["name"] == ["Zafir Yazan Qandelouni"]
    assert (p["firstName"], p["middleName"], p["lastName"]) == (
        ["Zafir"],
        ["Yazan"],
        ["Qandelouni"],
    )
    assert sorted(p["alias"]) == sorted(["Zafer QANDELOUNI", "Зафир Канделуни", "ظافر قنديلوني"])
    assert p["weakAlias"] == ["Zafo"]  # strong="false"
    assert p["gender"] == ["male"]
    assert p["nationality"] == ["cy"]  # "00" is counted, never guessed
    assert (p["birthDate"], p["birthPlace"], p["birthCountry"]) == (
        ["1961-04-12"],
        ["Tarnbury"],
        ["cy"],
    )
    assert p["passportNumber"] == ["SYNP000201"]  # spaces removed; the false one skipped
    assert p["idNumber"] == ["SYNN000201"]  # from latinNumber
    assert p["address"] == ["1 Sedge Lane, Limassol, QQ1 1QQ, Synthetic Region"]
    assert p["country"] == ["cy"]
    assert "title" not in p and "position" not in p  # keep_positions is off by default
    second = props(built["eufsf-990002"])
    assert (second["name"], second["weakAlias"]) == (["Rakan Velqasimi"], ["Raqan"])
    assert (second["gender"], second["nationality"]) == (["female"], ["gb"])
    assert second["birthDate"] == ["1975"]  # circa: the year only
    third = props(built["eufsf-990003"])
    assert (third["name"], third["alias"]) == (["Nadim Ulvarasi"], ["Nadim Ulvarazi"])
    # A 1958 to 1960 range gives each year, a 41-year range nothing, a year and month both.
    assert sorted(third["birthDate"]) == ["1957-05", "1958", "1959", "1960"]
    assert third["birthPlace"] == ["Synthetic Place"]  # from @place when @city is empty
    assert "gender" not in third and "passportNumber" not in third
    counts = summary(data_env)
    assert counts["parties_without_primary_name"] == 1  # only German and French names
    assert (counts["unmapped_countries"], counts["unknown_genders"]) == (1, 1)
    assert (counts["wide_year_ranges"], counts["unparseable_dates"]) == (1, 1)
    assert (counts["false_documents_skipped"], counts["weak_aliases"]) == (1, 3)


def test_sanction_mapping(built: dict[str, dict[str, Any]]) -> None:
    first = built[sanction_id("eufsf", "eufsf-990001", "991001")]
    assert first["nr"] == {"v": "1.1", "source_ref": "991001"}
    assert props(first) == {
        "entity": ["eufsf-990001"],
        "authority": ["European Union"],
        "country": ["eu"],
        "authorityId": ["EU.99001.11"],
        "program": ["SYNA"],
        "programId": ["9901/2022 (OJ L 901)"],
        "startDate": ["2022-03-15"],  # designationDate, earlier than the entry into force
        "listingDate": ["2022-03-15"],
        "sourceUrl": ["https://example.invalid/oj/zz-9901-2022"],
    }
    second = sanction(built, "eufsf-990001", "991002")  # the same person, a second regulation
    assert (second["program"], second["startDate"]) == (["SYNB"], ["2021-06-30"])
    assert second["listingDate"] == ["2021-07-01"]
    no_ref = sanction(built, "eufsf-990002", "991003")
    assert no_ref["authorityId"] == ["990002"]  # no euReferenceNumber: the logical id
    assert no_ref["unscId"] == ["ZZI.001"]
    assert no_ref["startDate"] == ["2023-05-11"]  # no designationDate: the entry into force
    assert sanction(built, "eufsf-990005", "991006")["unscId"] == ["ZZE.002"]
    assert "reason" not in first["properties"]  # keep_reasons is off by default


def test_organization_mapping(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    org = built["eufsf-990004"]
    assert org["schema"] == "Organization"
    p = props(org)
    assert p["name"] == ["Lichen Heath Logistics Ltd"]
    assert (p["alias"], p["weakAlias"]) == (["Lichen Heath Logistics Limited"], ["LHL"])
    # Only the GB regnumber in a Companies House form; the SY and the Cyprus number dropped.
    assert (p["registrationNumber"], p["jurisdiction"]) == (["99000123"], ["gb"])
    assert p["address"] == ["2 Teasel Row, PO Box 0, London, QQ2 2QQ"]
    assert p["country"] == ["gb"]
    other = props(built["eufsf-990005"])
    assert "registrationNumber" not in other and "nationality" not in other
    counts = summary(data_env)
    assert counts["registration_numbers_not_loaded"] == 2
    assert counts["identifications_not_loaded"] == 2  # two trade licences
    assert counts["organization_citizenships_not_loaded"] == 1


def test_skipped_subject_types_and_never_loaded_fields(
    built: dict[str, dict[str, Any]], data_env: Any
) -> None:
    text = (records_dir(data_env) / f"{eu_fsf.DATASET}.ftm.jsonl").read_text(encoding="utf-8")
    for value in (
        "LINNET WOLD",  # subject type vessel: skipped
        "990006",
        "+00 0000",  # phone
        "+00 1111",  # fax
        "nobody@example.invalid",  # e-mail
        "www.example.invalid",  # website
        "SYNP000202",  # a passport marked false
        "Synthetic remark",  # keep_reasons is off
        "Synthetic name remark",
        "Synthetic document remark",
        "Synthetic title",  # keep_positions is off
        "Synthetic function",
        "SY000123",
        "SY000401",
        "SY000402",
        "SY000301",
        "UNKNOWN",
    ):
        assert value not in text, value
    manifest = json.loads(
        (records_dir(data_env) / f"{eu_fsf.DATASET}.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts"]["skipped"] == {"known_false_documents": 1, "other_subject_types": 1}
    assert manifest["counts"]["by_schema"] == {"Organization": 2, "Person": 3, "Sanction": 6}
    assert manifest["record_contract"] == "1.1.0"
    notes = manifest["notes"]
    assert "list_generated: 2026-10-20T10:20:00.000+02:00" in notes
    assert "global_file_id: 990999" in notes
    assert summary(data_env)["skipped_subject_types"] == 1


def test_keep_reasons_and_positions(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    use_profile(data_env, keep_reasons=True, keep_positions=True)
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    records = load_records(data_env)
    p = props(records["eufsf-990001"])
    assert p["title"] == ["Synthetic title"]
    assert sorted(p["position"]) == ["Synthetic function one", "Synthetic function two"]
    for key in ("991001", "991002"):  # the entity remark, on each of its sanctions
        assert sanction(records, "eufsf-990001", key)["reason"] == ["Synthetic remark for a test."]
    assert "reason" not in sanction(records, "eufsf-990002", "991003")
    text = (records_dir(data_env) / f"{eu_fsf.DATASET}.ftm.jsonl").read_text(encoding="utf-8")
    assert "Synthetic name remark" not in text and "Synthetic document remark" not in text


def test_summary_counts_and_rates(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    counts = summary(data_env)
    assert counts["status"] == "ok"
    assert (counts["list_generated"], counts["global_file_id"]) == (
        "2026-10-20T10:20:00.000+02:00",
        "990999",
    )
    assert counts["records"] == {"organization": 2, "person": 3, "sanction": 6}
    assert counts["entities"] == 6
    assert counts["fill_rates"] == {
        "person_birth_date": 1.0,
        "person_nationality": 0.6667,
        "person_passport_or_id": 0.3333,
        "sanction_program": 1.0,
        "sanction_start_date": 1.0,
        "sanction_unsc_id": 0.3333,  # the note saw it empty in every record it read
        "organization_registration_or_lei": 0.5,
    }
    assert counts["bounds_outside_accepted"] == 2


def test_bounds_fail_with_exit_4_unless_accepted(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    use_profile(data_env)
    result = fetch_and_build(data_env, monkeypatch)
    assert result.exit_code == 4, result.output
    assert "unexpected size for eu_fsf: Organization 2, expected 970 to 2300" in result.output
    assert "Person 3, expected 3400 to 8000" in result.output
    assert not records_dir(data_env).exists()


def test_profile_block_rejects_unknown_keys(data_env: Any) -> None:
    data_env.write_profile(
        PROFILE, real_data=True, sources={eu_fsf.DATASET: {"enabled": True, "keep_notes": True}}
    )
    data_env.allow_real(PROFILE)
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code != 0
    assert "keep_notes" in result.output


def test_parse_ignores_namespaces_and_refuses_bad_xml(tmp_path: Path) -> None:
    plain = tmp_path / "plain.xml"
    text = FIXTURE.read_text(encoding="utf-8")
    plain.write_text(re.sub(r' xmlns="[^"]+"', "", text, count=1), encoding="utf-8")
    for path in (FIXTURE, plain):
        stamp, file_id, entries, counts = eu_fsf.parse(path)
        assert (stamp, file_id, len(entries)) == ("2026-10-20T10:20:00.000+02:00", "990999", 6)
        assert counts["entities"] == 6
    broken = tmp_path / "broken.xml"
    broken.write_text("<export><sanctionEntity>", encoding="utf-8")
    with pytest.raises(BuildError, match="not a well-formed list file"):
        eu_fsf.parse(broken)
    entities = tmp_path / "entities.xml"
    entities.write_text(
        '<?xml version="1.0"?><!DOCTYPE d [<!ENTITY a "aaaa">]><export>&a;</export>',
        encoding="utf-8",
    )
    with pytest.raises(BuildError, match="EntitiesForbidden"):
        eu_fsf.parse(entities)
    duplicate = tmp_path / "duplicate.xml"
    entity = '<sanctionEntity logicalId="990001"><subjectType code="person"/></sanctionEntity>'
    duplicate.write_text(f"<export>{entity}{entity}<sanctionEntity/></export>", encoding="utf-8")
    _, _, entries, counts = eu_fsf.parse(duplicate)
    assert len(entries) == 1
    assert (counts["duplicate_logical_ids"], counts["entities_without_logical_id"]) == (1, 1)
