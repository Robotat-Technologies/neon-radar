"""The OFAC SDN List loader (PHASE-2.md M2.6b). Synthetic fixture only: every name, number and
reference value in `fixtures/lists/us_ofac_sdn/sdn_advanced.xml` is invented."""

import dataclasses
import json
import re
import tracemalloc
from collections import Counter
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
from neonradar_ingest.sources.lists import shared, us_ofac
from neonradar_ingest.sources.lists.common import sanction_id

FIXTURES = Path(__file__).parent / "fixtures" / "lists" / "us_ofac_sdn"
FIXTURE = FIXTURES / "sdn_advanced.xml"
XSD = FIXTURES / "sdn_advanced.xsd"
LEGACY_NS = "http://www.un.org/sanctions/1.0"
SLS_NS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML"
PROFILE = "us-lists"
KEY = re.compile(
    r'<xsd:key name="(\w+)">\s*<xsd:selector xpath="\.//un:(\w+)"/>\s*<xsd:field xpath="@(\w+)"/>'
)
KEYREF = re.compile(
    r'<xsd:keyref name="\w+" refer="(\w+)">\s*<xsd:selector xpath="[^"]+"/>\s*'
    r'<xsd:field xpath="@([\w-]+)"/>\s*</xsd:keyref>\s*'
)
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
    spec = dataclasses.replace(sources._SOURCES[us_ofac.DATASET], client=server.client)
    monkeypatch.setitem(sources._SOURCES, us_ofac.DATASET, spec)
    return server


def fetch_and_build(
    data_env: Any, monkeypatch: pytest.MonkeyPatch, *extra: str, body: bytes | None = None
) -> Any:
    block = {"enabled": True, "keep_reasons": False, "keep_positions": False}
    data_env.write_profile(PROFILE, real_data=True, sources={us_ofac.DATASET: block})
    data_env.allow_real(PROFILE)
    serve(monkeypatch, FIXTURE.read_bytes() if body is None else body)
    fetched = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert fetched.exit_code == 0, fetched.output
    args = ["ingest", "build", "--profile", PROFILE, "--dataset", us_ofac.DATASET, *extra]
    return runner.invoke(app, args)


def records_dir(data_env: Any) -> Path:
    path: Path = data_env.cache / "real" / "records" / PROFILE / us_ofac.DATASET
    return path


def summary(data_env: Any) -> dict[str, Any]:
    builds = sorted((data_env.cache / "reports" / PROFILE).glob("ingest-build-*.json"))
    built: dict[str, Any] = json.loads(builds[-1].read_text(encoding="utf-8"))
    return built["datasets"][us_ofac.DATASET]  # type: ignore[no-any-return]


@pytest.fixture
def built(data_env: Any, monkeypatch: pytest.MonkeyPatch) -> dict[str, dict[str, Any]]:
    result = fetch_and_build(data_env, monkeypatch, "--accept-size")
    assert result.exit_code == 0, result.output
    path = records_dir(data_env) / f"{us_ofac.DATASET}.ftm.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines()
    return {record["id"]: record for record in map(json.loads, lines)}


def props(record: dict[str, Any]) -> dict[str, list[str]]:
    return record["properties"]  # type: ignore[no-any-return]


def parse(path: Path) -> tuple[us_ofac.Tables, list[dict[str, Any]], Counter[str]]:
    counts: Counter[str] = Counter()
    tables = us_ofac.read_tables(path, counts)
    skipped = us_ofac.Skipped()
    records = list(us_ofac.party_records(path, tables, counts, skipped))
    return tables, records + list(us_ofac.relationship_records(tables, counts)), counts


def _broken_keyrefs(path: Path, text: str) -> dict[str, set[str | None]]:
    """The XSD's keyrefs that `path` breaks: attribute name to the ids that point nowhere."""
    from defusedxml.ElementTree import parse as parse_xml

    keys = {name: (tag, field) for name, tag, field in KEY.findall(text)}
    root = parse_xml(path).getroot()
    assert root is not None
    elements = list(root.iter())
    broken = {}
    for refer, attribute in KEYREF.findall(text):
        tag, field = keys[refer]
        known = {e.get(field) for e in elements if e.tag.rsplit("}", 1)[-1] == tag}
        used = {e.get(attribute) for e in elements if attribute in e.attrib}
        if used - known:
            broken[attribute] = used - known
    return broken


def test_fixture_validates_against_the_committed_xsd(tmp_path: Path) -> None:
    if not XSD.is_file():
        pytest.skip("the publisher's XSD is not committed (see the pull request)")
    import xmlschema

    text = XSD.read_text(encoding="utf-8")
    keyrefs = KEYREF.findall(text)
    key_names = {name for name, _tag, _field in KEY.findall(text)}
    assert len(keyrefs) == 48 and {refer for refer, _ in keyrefs} <= key_names
    # Everything but the keyrefs through xmlschema (sandboxed: never fetches anything). Their
    # `.//un:*` selectors take xmlschema 15 s on this small file, so they are checked below.
    base = str(FIXTURES.resolve())
    schema = xmlschema.XMLSchema(KEYREF.sub("", text), base_url=base, allow="sandbox")
    schema.validate(str(FIXTURE.resolve()))
    assert _broken_keyrefs(FIXTURE, text) == {}
    # The keyref check fails on a reference that points nowhere.
    broken = tmp_path / "broken.xml"
    fixture = FIXTURE.read_text(encoding="utf-8")
    broken.write_text(
        fixture.replace('<LocationCountry CountryID="3"', '<LocationCountry CountryID="77"'),
        encoding="utf-8",
    )
    assert _broken_keyrefs(broken, text) == {"CountryID": {"77"}}


def test_gate_refuses_a_list_left_out_of_access_sanctions_lists(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """M2.6 rule 2: the profile may run on this machine, but the list is not allowed."""
    data_env.write_project(
        real_data_profiles=["uk-tiny"],
        data_protection_filed=True,
        sanctions_lists=["gb_fcdo_sanctions", "eu_fsf"],
    )
    monkeypatch.setenv("NR_REAL_DATA_MACHINE", "approved")
    server = serve(monkeypatch, FIXTURE.read_bytes())
    for command in (["data", "fetch"], ["ingest", "build"]):
        args = [*command, "--profile", "uk-tiny", "--dataset", us_ofac.DATASET]
        result = runner.invoke(app, args)
        assert result.exit_code == 3, result.output
        assert "us_ofac_sdn is not in access.sanctions_lists" in result.output
    assert server.requests == []
    assert not (data_env.cache / "real").exists()


def test_fetch_sends_a_user_agent_and_dates_the_version(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_env.write_profile(PROFILE, real_data=True, sources={us_ofac.DATASET: {"enabled": True}})
    data_env.allow_real(PROFILE)
    server = serve(monkeypatch, FIXTURE.read_bytes())
    result = runner.invoke(app, ["data", "fetch", "--profile", PROFILE])
    assert result.exit_code == 0, result.output
    assert [str(r.url) for r in server.requests] == [us_ofac.URL]
    assert server.requests[0].headers["User-Agent"].startswith("NeonRadar/")  # OFAC needs one
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    folder = data_env.cache / "real" / "sources" / us_ofac.DATASET / "main" / today
    record = json.loads((folder / "download.json").read_text(encoding="utf-8"))
    assert [(f["name"], f["url"]) for f in record["files"]] == [(us_ofac.FILE_NAME, us_ofac.URL)]


def test_reference_value_lookups() -> None:
    counts: Counter[str] = Counter()
    tables = us_ofac.read_tables(FIXTURE, counts)
    assert tables.stamp == "2026-10-20"
    assert tables.value("AliasType", "2") == "F.K.A."
    assert tables.value("FeatureType", "7") == "Organization Established Date"
    assert tables.attr("PartySubType", "3", "PartyTypeID") == "3"
    assert tables.country("1") == ("United Kingdom", "GB")
    assert tables.value("FeatureType", "99") is None
    assert tables.places["101"] == us_ofac.Place(
        ("1 Sedge Lane", "Limassol", "QQ1 1QQ"), "Cyprus", "CY"
    )  # primary value chosen, parts ordered, the "Unknown" part counted
    assert counts["location_parts_not_loaded"] == 1
    assert [d.kind for d in tables.documents["2001"]][:2] == ["Passport", "Passport"]
    assert tables.documents["2001"][1].fraudulent
    assert tables.entries["990001"][0] == us_ofac.Entry(
        "8001", "2019-05-01", ("SYN-ALPHA", "SYN-BETA"), ("Block",)
    )
    assert len(tables.relations) == 15
    # Subtype "Unknown" falls back to the party type; vessels and aircraft are not loadable.
    assert tables.parties["990001"] == ("ofac-990001", "Person")
    assert tables.parties["990011"] == ("ofac-990011", "Organization")
    assert "990021" not in tables.parties and "990022" not in tables.parties


def test_person_names_in_two_scripts_and_a_weak_alias(built: dict[str, dict[str, Any]]) -> None:
    p = props(built["ofac-990001"])
    assert built["ofac-990001"]["schema"] == "Person"
    assert built["ofac-990001"]["nr"] == {"v": "1.1", "source_ref": "990001"}
    assert p["topics"] == ["sanction"]
    assert p["name"] == ["Zafir Rakan QANDELOUNI"]  # the primary alias in Latin script
    assert (p["firstName"], p["middleName"], p["lastName"]) == (
        ["Zafir"],
        ["Rakan"],
        ["QANDELOUNI"],
    )
    assert sorted(p["alias"]) == sorted(["ظافر قنديلوني", "Zafer QANDELOUNI"])
    assert p["weakAlias"] == ["Zafir"]  # LowQuality="true"
    assert p["sourceUrl"] == ["https://sanctionssearch.ofac.treas.gov/Details.aspx?id=990001"]


def test_maiden_name_nickname_and_name_parts(built: dict[str, dict[str, Any]]) -> None:
    p = props(built["ofac-990002"])
    assert p["name"] == ["Yazan Zafer Raqan ULVARAZI"]  # first, patronymic, matronymic, last
    assert (p["firstName"], p["fatherName"], p["motherName"], p["lastName"]) == (
        ["Yazan"],
        ["Zafer"],
        ["Raqan"],
        ["ULVARAZI"],
    )
    assert sorted(p["alias"]) == ["Yazan ULVARASI", "Yazan ZUBEIRONO"]  # N.K.A.; maiden name
    assert p["previousName"] == ["Yazan ULVARAZY"]  # F.K.A.
    assert p["weakAlias"] == ["Nadim"]  # the nickname


def test_birth_dates(built: dict[str, dict[str, Any]]) -> None:
    assert props(built["ofac-990001"])["birthDate"] == ["1979-08-14", "1980"]  # date; whole year
    assert props(built["ofac-990002"])["birthDate"] == ["1965", "1966"]  # a two-year range
    # Approximate: the years of the range, and the year of an approximate exact date.
    assert props(built["ofac-990003"])["birthDate"] == ["1970", "1971", "1972", "1975"]
    assert props(built["ofac-990011"])["incorporationDate"] == ["2015-03"]  # a whole month
    assert "birthDate" not in props(built["ofac-990004"])


def test_person_features_and_documents(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    p = props(built["ofac-990001"])
    assert (p["birthPlace"], p["nationality"], p["citizenship"]) == (["Limassol"], ["cy"], ["gb"])
    assert p["gender"] == ["male"]
    assert p["address"] == ["1 Sedge Lane, Limassol, QQ1 1QQ, Cyprus"]
    assert p["country"] == ["cy"]
    assert p["passportNumber"] == ["SYNP000101"]  # the fraudulent SYNP000102 is skipped
    assert p["idNumber"] == ["SYNN000101"]  # spaces removed
    q = props(built["ofac-990002"])
    assert (q["gender"], q["passportNumber"]) == (["female"], ["SYNP000201"])  # diplomatic
    assert q["idNumber"] == ["SYNC000201", "SYNI000201"]  # cedula, identification number
    assert "nationality" not in q  # "Atlantis" is counted, never guessed
    # A company number and an established date on a person: counted, never loaded.
    r = props(built["ofac-990004"])
    assert not {"registrationNumber", "jurisdiction", "leiCode", "incorporationDate"} & set(r)
    counts = summary(data_env)
    assert (counts["unmapped_countries"], counts["fraudulent_documents_skipped"]) == (1, 1)
    assert counts["registration_numbers_on_persons"] == 1


def test_organization_numbers(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    o = props(built["ofac-990011"])
    assert built["ofac-990011"]["schema"] == "Organization"
    # UK Company Number, and a Company Number issued in the UK; the Cyprus one is counted.
    assert o["registrationNumber"] == ["99000111", "99000112"]
    assert (o["jurisdiction"], o["leiCode"]) == (["gb"], ["SYN0000000000000OF24"])
    assert o["address"] == [
        "2 Marram Row, Unit 3, Leeds, Sorrel Shire, North, QQ2 2QQ, United Kingdom"
    ]
    assert o["alias"] == ["Sorrel Sike Trading Limited"]
    t = props(built["ofac-990012"])
    assert t["registrationNumber"] == ["99000122"]  # the SY "UK Company Number" is refused
    assert t["leiCode"] == ["SYN0000000000000OG21"]  # the LEI with bad check digits is refused
    assert t["weakAlias"] == ["TQT"]
    counts = summary(data_env)
    assert (counts["uk_company_numbers_rejected"], counts["leis_rejected"]) == (1, 1)


def test_skipped_parties_and_values_never_loaded(
    built: dict[str, dict[str, Any]], data_env: Any
) -> None:
    text = (records_dir(data_env) / f"{us_ofac.DATASET}.ftm.jsonl").read_text(encoding="utf-8")
    for value in (
        "LINNET WOLD",  # vessel
        "BASALT HOLM",  # aircraft
        "nobody@example.invalid",
        "www.example.invalid",
        "SYNWALLET0001",
        "Synthetic title",
        "SYNT000101",  # tax id: counted by type
        "SYNP000102",  # fraudulent
        "SY000113",  # registration number issued in Cyprus
        "99000141",  # a company number on a person
        "Synthetic location note",
        "Lemesos",  # not the primary location part value
    ):
        assert value not in text, value
    counts = summary(data_env)
    assert (counts["skipped_vessel"], counts["skipped_airplane"]) == (1, 1)
    assert counts["crypto_wallets_skipped"] == 1
    # Fewer than 10 of each type: folded into the _rare count (the summary guard).
    assert counts["feature_types_not_loaded_by_value_rare"] == 6
    assert counts["document_types_not_loaded_by_value_rare"] == 2


def test_type_names_counted_by_value() -> None:
    counts: Counter[str] = Counter()
    tables = us_ofac.read_tables(FIXTURE, counts)
    skipped = us_ofac.Skipped()
    list(us_ofac.party_records(FIXTURE, tables, counts, skipped))
    assert skipped.features == {
        "email address": 1,
        "website": 1,
        "digital currency address - xbt": 1,
        "title": 1,  # titles are not loaded, whatever keep_positions says
        "nationality country": 1,  # on an Organization
        "organization established date": 1,  # on a Person
    }
    assert skipped.documents == {"tax id no.": 1, "registration number": 1}
    assert us_ofac._vocabulary("Russian State Number (OGRNIP) — X") == (
        "russian state number (ogrnip) _ x"
    )


def test_sanctions(built: dict[str, dict[str, Any]]) -> None:
    first = built[sanction_id("ofac", "ofac-990001", "8001")]
    assert first["nr"] == {"v": "1.1", "source_ref": "8001"}
    assert props(first) == {
        "entity": ["ofac-990001"],
        "authority": ["US Office of Foreign Assets Control"],
        "country": ["us"],
        "authorityId": ["990001"],  # the FixedRef (SDN UID)
        "program": ["SYN-ALPHA", "SYN-BETA"],
        "provisions": ["Block"],
        "startDate": ["2019-05-01"],  # the earliest entry event
        "sourceUrl": ["https://sanctionssearch.ofac.treas.gov/Details.aspx?id=990001"],
    }
    second = props(built[sanction_id("ofac", "ofac-990001", "8002")])
    assert (second["program"], second["provisions"]) == (["SYN-BETA"], ["Synthetic restriction"])
    assert "program" not in props(built[sanction_id("ofac", "ofac-990014", "8014")])
    assert sum(r["schema"] == "Sanction" for r in built.values()) == 9  # none for skipped types


def test_relationships(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    links = {
        r["nr"]["source_ref"]: (r["schema"], props(r))
        for r in built.values()
        if r["schema"] not in ("Person", "Organization", "Sanction")
    }
    # Relation type id: (schema, From property, From party, To property, To party, label).
    expected = {
        "9001": ("Control", "controlled", "12", "controller", "11", "Owned or Controlled By"),
        "9002": ("Control", "controller", "01", "controlled", "11", "Owns, controls, or operates"),
        "9003": ("Control", "controlled", "13", "controller", "02", "Property in the interest of"),
        "9004": ("Representation", "agent", "03", "client", "11", "Acting for or on behalf of"),
        "9005": ("Directorship", "director", "01", "organization", "12", "Leader or official of"),
        # From an entity to a person: the ends are swapped (note 2.9).
        "9006": ("Directorship", "organization", "14", "director", "04",
                 "Principal Executive Officer"),
        "9007": ("Membership", "member", "02", "organization", "13",
                 "playing a significant role in"),
        # 9015 repeats 9008's ends and type but is current: the current one is kept.
        "9015": ("Associate", "person", "01", "associate", "03", "Associate Of"),
        "9009": ("Family", "person", "02", "relative", "04", "Family member of"),
        "9010": ("UnknownLink", "subject", "03", "object", "14", "Associate Of"),  # not two persons
        "9011": ("UnknownLink", "subject", "14", "object", "11", "Providing support to"),
        "9012": ("UnknownLink", "subject", "03", "object", "04", "Owned or Controlled By"),
        "9014": ("UnknownLink", "subject", "13", "object", "14", "Synthetic other link"),
    }  # fmt: skip
    assert set(links) == set(expected)  # 9013 points to the vessel: skipped
    for ref, (schema, a_prop, a, b_prop, b, label) in expected.items():
        found, p = links[ref]
        assert (found, p[a_prop], p[b_prop]) == (schema, [f"ofac-9900{a}"], [f"ofac-9900{b}"]), ref
        assert p.get("role", p.get("relationship")) == [label], ref
        assert p.get("status") == (["former"] if ref == "9003" else None), ref
    assert not any(r["schema"] == "Ownership" for r in built.values())  # no share from OFAC
    assert any(re.fullmatch(r"ofac-control-[0-9a-f]{20}", key) for key in built)
    counts = summary(data_env)
    assert (counts["relationships_flipped"], counts["relationships_to_skipped_parties"]) == (1, 1)
    assert (counts["unknown_relation_types"], counts["duplicate_relationships"]) == (1, 1)


def test_parsing_ignores_the_namespace(tmp_path: Path) -> None:
    """Note 2.4: the legacy XSD namespace, the SLS one, and none at all read the same."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert LEGACY_NS in text
    results = []
    for name, namespace in (("legacy", LEGACY_NS), ("sls", SLS_NS), ("none", None)):
        path = tmp_path / f"{name}.xml"
        replaced = text.replace(
            f' xmlns="{LEGACY_NS}"', "" if namespace is None else f' xmlns="{namespace}"'
        )
        path.write_text(replaced, encoding="utf-8")
        tables, records, _ = parse(path)
        results.append((tables.stamp, records))
    assert results[0] == results[1] == results[2]
    assert len(results[0][1]) == 30


def test_bad_xml_is_refused(tmp_path: Path) -> None:
    broken = tmp_path / "broken.xml"
    broken.write_text("<Sanctions><DistinctParties>", encoding="utf-8")
    with pytest.raises(BuildError, match="not a well-formed list file"):
        us_ofac.read_tables(broken, Counter())
    entities = tmp_path / "entities.xml"
    entities.write_text(
        '<?xml version="1.0"?><!DOCTYPE s [<!ENTITY a "aaaa">]><Sanctions>&a;</Sanctions>',
        encoding="utf-8",
    )
    with pytest.raises(BuildError, match="EntitiesForbidden"):
        us_ofac.read_tables(entities, Counter())


PARTY = (
    '<DistinctParty FixedRef="99{i:04d}"><Profile ID="99{i:04d}" PartySubTypeID="1">'
    '<Identity ID="{i}" FixedRef="99{i:04d}" Primary="true" False="false">'
    '<Alias FixedRef="99{i:04d}" AliasTypeID="4" Primary="true" LowQuality="false">'
    '<DocumentedName ID="{i}" FixedRef="99{i:04d}" DocNameStatusID="1"><DocumentedNamePart>'
    '<NamePartValue NamePartGroupID="{i}" ScriptID="1" ScriptStatusID="1" Acronym="false">'
    "Nadim ULVARAZI {i}</NamePartValue></DocumentedNamePart></DocumentedName></Alias>"
    '<NamePartGroups><MasterNamePartGroup><NamePartGroup ID="{i}" NamePartTypeID="2"/>'
    "</MasterNamePartGroup></NamePartGroups></Identity></Profile></DistinctParty>"
)
ENTRY = (
    '<SanctionsEntry ID="{i}" ProfileID="99{i:04d}" ListID="1"><EntryEvent ID="{i}" '
    'EntryEventTypeID="1"><Date CalendarTypeID="1"><Year>2024</Year><Month>1</Month>'
    '<Day>1</Day></Date></EntryEvent><SanctionsMeasure ID="{i}" SanctionsTypeID="1">'
    "<Comment>SYN-ALPHA</Comment></SanctionsMeasure></SanctionsEntry>"
)


def _generated(tmp_path: Path, n: int) -> Path:
    text = FIXTURE.read_text(encoding="utf-8")
    head = text[: text.index("<DistinctParties>")]
    parties = "".join(PARTY.format(i=i) for i in range(1, n + 1))
    entries = "".join(ENTRY.format(i=i) for i in range(1, n + 1))
    path = tmp_path / f"generated-{n}.xml"
    path.write_text(
        f"{head}<DistinctParties>{parties}</DistinctParties><ProfileRelationships/>"
        f"<SanctionsEntries>{entries}</SanctionsEntries><SanctionsEntryLinks/></Sanctions>",
        encoding="utf-8",
    )
    return path


def _pass_two_peak(path: Path) -> tuple[int, int]:
    counts: Counter[str] = Counter()
    tables = us_ofac.read_tables(path, counts)
    tracemalloc.start()
    try:
        written = sum(1 for _ in us_ofac.party_records(path, tables, counts, us_ofac.Skipped()))
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    return written, peak


def test_pass_two_keeps_no_parties(tmp_path: Path) -> None:
    """Deliverable 2: ten times the parties must not double the peak memory of pass 2."""
    small, large = (
        _pass_two_peak(_generated(tmp_path, 200)),
        _pass_two_peak(_generated(tmp_path, 2000)),
    )
    assert (small[0], large[0]) == (400, 4000)  # a Person and a Sanction per party
    assert large[1] < 2 * small[1], (small, large)


def test_summary_counts_rates_and_manifest(built: dict[str, dict[str, Any]], data_env: Any) -> None:
    counts = summary(data_env)
    assert counts["status"] == "ok"
    assert counts["list_generated"] == "2026-10-20"
    assert counts["records"] == {
        "associate": 1, "control": 3, "directorship": 2, "family": 1, "membership": 1,
        "organization": 4, "person": 4, "representation": 1, "sanction": 9, "unknownlink": 4,
    }  # fmt: skip
    assert counts["fill_rates"] == {
        "person_birth_date": 0.75,
        "person_nationality": 0.25,
        "person_passport_or_id": 0.5,
        "sanction_program": 0.8889,
        "sanction_start_date": 1.0,
        "organization_registration_or_lei": 0.5,
    }
    assert counts["bounds_outside_accepted"] == 2
    manifest = json.loads(
        (records_dir(data_env) / f"{us_ofac.DATASET}.manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["counts"]["skipped"] == {
        "Airplane": 1, "CryptoWallet": 1, "Vessel": 1, "relationships": 1,
    }  # fmt: skip
    assert manifest["source"]["urls"] == [us_ofac.URL]
    assert "list_generated: 2026-10-20" in manifest["notes"]


def test_bounds_fail_with_exit_4_unless_accepted(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = fetch_and_build(data_env, monkeypatch)
    assert result.exit_code == 4, result.output
    assert (
        "unexpected size for us_ofac_sdn: Organization 4, expected 6000 to 14000" in result.output
    )
    assert "Person 4, expected 5000 to 11000" in result.output
    assert not records_dir(data_env).exists()  # nothing replaced
    accepted = runner.invoke(
        app,
        ["ingest", "build", "--profile", PROFILE, "--dataset", us_ofac.DATASET, "--accept-size"],
    )
    assert accepted.exit_code == 0, accepted.output


def test_zero_fill_rate_fails_even_with_accept_size(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = re.sub(
        r'<Feature ID="\d+" FeatureTypeID="1">.*?</Feature>',
        "",
        FIXTURE.read_text(encoding="utf-8"),
        flags=re.S,
    )
    result = fetch_and_build(data_env, monkeypatch, "--accept-size", body=body.encode())
    assert result.exit_code == 4, result.output
    assert "the fill rate of person_birth_date is zero; the parser is broken" in result.output
    assert not records_dir(data_env).exists()


def test_a_weak_alias_never_becomes_the_name(tmp_path: Path) -> None:
    """A party whose only name is weak is skipped and counted, with its relationships."""
    text = FIXTURE.read_text(encoding="utf-8")
    alias = '<Alias FixedRef="990004" AliasTypeID="4" Primary="true" LowQuality="false">'
    path = tmp_path / "weak.xml"
    path.write_text(text.replace(alias, alias.replace('"false"', '"true"')), encoding="utf-8")
    tables, records, counts = parse(path)
    assert "990004" not in tables.parties
    assert not any("ofac-990004" in json.dumps(record) for record in records)
    assert (counts["no_strong_name"], counts["relationships_to_skipped_parties"]) == (1, 4)
    assert us_ofac.party_id("990004") == "ofac-990004"
    assert re.fullmatch(r"ofac-uid-[0-9a-f]{20}", us_ofac.party_id("SYN 0001"))  # make_id


def test_the_client_logs_no_query_string() -> None:
    """M2.6 rule 4: the shared list client, which keeps every query string out of the logs."""
    assert sources._SOURCES[us_ofac.DATASET].client is shared.list_client
    with shared.list_client() as client:
        assert client.log_query is False


def test_address_without_a_country_and_an_impossible_month(tmp_path: Path) -> None:
    text = FIXTURE.read_text(encoding="utf-8")
    country = '<Location ID="105">\n      <LocationCountry CountryID="1" CountryRelevanceID="1"/>'
    birth = "<Year>1979</Year><Month>8</Month><Day>14</Day>"
    assert country in text and text.count(birth) == 4
    path = tmp_path / "edited.xml"
    edited = text.replace(country, '<Location ID="105">')
    # Start 1979-13-01, end 1979-13-31: period_dates would look up month 13 and raise.
    edited = edited.replace(birth, "<Year>1979</Year><Month>13</Month><Day>1</Day>", 2)
    edited = edited.replace(birth, "<Year>1979</Year><Month>13</Month><Day>31</Day>")
    path.write_text(edited, encoding="utf-8")
    _, records, counts = parse(path)
    found = {record["id"]: record for record in records}
    address = props(found["ofac-990011"])["address"]
    assert address == ["2 Marram Row, Unit 3, Leeds, Sorrel Shire, North, QQ2 2QQ"]  # no ", "
    assert props(found["ofac-990001"])["birthDate"] == ["1980"]  # month 13: counted, not raised
    assert counts["unparseable_dates"] == 1


def test_streamed_fill_rates_match_the_shared_ones() -> None:
    _, records, _ = parse(FIXTURE)
    tally = us_ofac.Tally()
    assert list(tally.observe(records)) == records
    assert tally.rates() == shared.fill_rates(records)
