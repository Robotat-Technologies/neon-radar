"""The GLEIF Golden Copy loader (PHASE-2.md M2.4): discovery, reading, scope, records.

Every file is built in the test as a zip of a synthetic CSV in the publish's own format (the
dotted LEI-CDF 3.1 header of note 6.2 and the RR header of the 2019 fixture there), with
invented values only: `SYN0` LEIs with valid ISO 17442 check digits, `99` company numbers,
`QQ` postcodes, the invented authority `RA888888` and company names from the demo-mini
fixture. Nothing is committed as a file (2.9).
"""

import csv
import io
import json
import re
import zipfile
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_contracts.records import iter_records, validate_files
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.build import build_dataset
from neonradar_ingest.data.download import DownloadError
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.sources import BuildError, BuildResult
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_ingest.sources.gleif import golden_copy as gc
from neonradar_keys.addresses import address_key
from neonradar_keys.ids import is_valid_lei

VERSION = "20261021-1600"
PROFILE = "gl-test"


def lei(body: str) -> str:
    """An invented LEI: `SYN0`, the body padded to 18 characters, ISO 7064 check digits."""
    base = f"SYN0{body}".ljust(18, "0")
    digits = "".join(str(int(c, 36)) for c in base + "00")
    return f"{base}{98 - int(digits) % 97:02d}"


CHILD, SIBLING, OUTSIDE, ODD = lei("CHILD1"), lei("CHILD2"), lei("UKOUT1"), lei("UKODD1")
PARENT, ULTIMATE, INACTIVE_PARENT = lei("PARENT1"), lei("ULTIM1"), lei("PARENT2")
ANNULLED, DUPLICATE, FUND, GHOST = lei("ANNUL1"), lei("DUPL1"), lei("FUND1"), lei("GHOST1")
OTHER_A, OTHER_B = lei("OTHERA"), lei("OTHERB")
INVALID = CHILD[:-1] + str((int(CHILD[-1]) + 1) % 10)

OPTIONAL = [
    gc.CREATION,
    *(f"Entity.OtherEntityNames.OtherEntityName.{n}{x}" for n in (1, 2) for x in ("", ".xmllang")),
    "Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.1",
    *(f"Entity.{k}.{p}" for k in ("LegalAddress", "HeadquartersAddress")
      for p in ("AdditionalAddressLine.1", "Region", "PostalCode")),
]  # fmt: skip
LEI_HEADER = [*gc.LEI_COLUMNS[:5], *OPTIONAL, *gc.LEI_COLUMNS[5:]]
RR_HEADER = [
    gc.START, gc.START_TYPE, gc.END, gc.END_TYPE, gc.TYPE, gc.STATUS,
    "Registration.InitialRegistrationDate", "Registration.LastUpdateDate",
    "Registration.RegistrationStatus", "Registration.NextRenewalDate", "Registration.ManagingLOU",
    "Registration.ValidationSources", "Registration.ValidationDocuments",
    "Registration.ValidationReference",
    *(f"Relationship.Period.{n}.{p}" for n in range(1, 6)
      for p in ("startDate", "endDate", "periodType")),
    *(f"Relationship.Qualifiers.{n}.{p}" for n in range(1, 6)
      for p in ("QualifierDimension", "QualifierCategory")),
    *(f"Relationship.Qualifiers.{n}.{p}" for n in range(1, 6)
      for p in ("MeasurementMethod", "QuantifierAmount", "QuantifierUnits")),
]  # fmt: skip


def entity(
    code: str, name: str, number: str, authority: str = "RA000585", **values: str
) -> dict[str, str]:
    office = {"FirstAddressLine": "1 TEST STREET", "City": "TESTTOWN", "Country": "GB",
              "PostalCode": "QQ1 1AA"}  # fmt: skip
    row = {"LEI": code, "Entity.LegalName": name, "Entity.LegalName.xmllang": "en",
           "Entity.LegalJurisdiction": "GB", "Entity.EntityStatus": "ACTIVE",
           "Entity.EntityCategory": "GENERAL", "Entity.LegalForm.EntityLegalFormCode": "SYN1",
           gc.AUTHORITY: authority, gc.ENTITY_ID: number, gc.REGISTRATION: "ISSUED",
           **{f"Entity.{k}.{p}": v for k in ("LegalAddress", "HeadquartersAddress")
              for p, v in office.items()}}  # fmt: skip
    return row | values


def link(
    start: str, end: str, kind: str = "IS_DIRECTLY_CONSOLIDATED_BY", **values: str
) -> dict[str, str]:
    row = {gc.START: start, gc.START_TYPE: "LEI", gc.END: end, gc.END_TYPE: "LEI",
           gc.TYPE: kind, gc.STATUS: "ACTIVE"}  # fmt: skip
    return row | values


LEI_ROWS = [
    entity(CHILD, "MYRTLE LEAT\nFORMATIONS LTD", "99000001", **{
        gc.CREATION: "2012-06-06T15:52:00+02:00",
        "Entity.OtherEntityNames.OtherEntityName.1": "TANSY STRAND SUPPLIES LTD",
        "Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.1":
            "MYRTLE LEAT FORMATIONS LIMITED",
        "Entity.HeadquartersAddress.PostalCode": "qq1  1aa"}),
    entity(SIBLING, "BRACKEN DALE FREIGHT LTD", "990 00002", "RA000587", **{
        gc.CREATION: "06/06/2012", "Entity.LegalForm.EntityLegalFormCode": "",
        "Entity.LegalForm.OtherLegalForm": "PRIVATE LIMITED COMPANY",
        "Entity.HeadquartersAddress.FirstAddressLine": "2 SAMPLE ROAD",
        "Entity.HeadquartersAddress.PostalCode": "QQ2 2BB"}),
    entity(OUTSIDE, "COPPER ACRE INTERIORS LTD", "99000009"),
    entity(ODD, "BASALT HOLM FOODS LTD", "XY123456", "RA000586"),
    entity(PARENT, "TANSY TARN VENTURES LIMITED", "123", "RA888888", **{
        "Entity.LegalJurisdiction": "US-DE", "Entity.LegalAddress.Country": "US",
        "Entity.LegalAddress.PostalCode": "00000", "Entity.HeadquartersAddress.Country": "US",
        "Entity.HeadquartersAddress.PostalCode": "00000"}),
    entity(ULTIMATE, "UMBER GARTH FOODS LTD", "99000003", "RA000587",
           **{"Entity.LegalJurisdiction": "GB-SCT"}),
    entity(INACTIVE_PARENT, "FENNEL WEALD FOODS LTD", "99000005"),
    entity(ANNULLED, "SORREL SIKE TRADING LTD", "99000004", **{gc.REGISTRATION: "ANNULLED"}),
    entity(DUPLICATE, "SORREL SIKE TRADING LTD", "99000006", **{gc.REGISTRATION: "DUPLICATE"}),
    entity(INVALID, "TEASEL QUAY TRADING LTD", "99000007"),
    entity(FUND, "KESTREL SCAR FINANCE LTD", "", "RA888888", **{"Entity.EntityCategory": "FUND"}),
    entity(OTHER_A, "LINNET WOLD FOODS LTD", "99000010"),
    entity(OTHER_B, "LARCH MERE SERVICES LTD", "99000011"),
]  # fmt: skip
RR_ROWS = [
    link(CHILD, PARENT, **{
        "Relationship.Period.1.periodType": "ACCOUNTING_PERIOD",
        "Relationship.Period.1.startDate": "2017-01-01T00:00:00Z",
        "Relationship.Period.2.periodType": "RELATIONSHIP_PERIOD",
        "Relationship.Period.2.startDate": "2018-01-01T00:00:00.000Z",
        "Relationship.Qualifiers.1.QuantifierAmount": "60"}),
    link(CHILD, ULTIMATE, "IS_ULTIMATELY_CONSOLIDATED_BY"),
    link(PARENT, ULTIMATE),  # two parents, both loaded: kept
    link(SIBLING, INACTIVE_PARENT, **{gc.STATUS: "INACTIVE"}),
    link(SIBLING, GHOST, "IS_ULTIMATELY_CONSOLIDATED_BY"),  # a parent missing from the file
    link(OUTSIDE, CHILD),  # a child outside the scope
    link(CHILD, PARENT, "IS_INTERNATIONAL_BRANCH_OF"),
    link(FUND, CHILD, "IS_FUND-MANAGED_BY"),
    link(OTHER_A, OTHER_B),
]  # fmt: skip


def csv_bytes(header: Sequence[str], rows: Sequence[dict[str, str]]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")
    writer.writerow(header)
    writer.writerows([row.get(column, "") for column in header] for row in rows)
    return out.getvalue().encode("utf-8")


def zipped(path: Path, data: bytes) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(path.name.removesuffix(".zip"), data)
    return path


def download(lei_header: Sequence[str] = LEI_HEADER, rr_header: Sequence[str] = RR_HEADER,
             lei_rows: Sequence[dict[str, str]] = LEI_ROWS) -> None:  # fmt: skip
    """The two files as a complete download of the `golden-copy` product."""
    folder = layout.sources_dir(gc.DATASET, gc.PRODUCT, VERSION)
    files = []
    for kind, data in (("lei2", csv_bytes(lei_header, lei_rows)),
                       ("rr", csv_bytes(rr_header, RR_ROWS))):  # fmt: skip
        name = f"{VERSION}-gleif-goldencopy-{kind}-golden-copy.csv.zip"
        zipped(folder / name, data)
        files.append({"name": name, "url": f"https://goldencopy.example/{name}"})
    (folder / "download.json").write_text(json.dumps({"files": files, "complete": True}))


def profile(env: Any, scope: str = "slice", numbers: Sequence[str] | None = ("99000001",
            "99000002", "99000004", "99000006", "99000007")) -> None:  # fmt: skip
    env.write_profile(PROFILE, real_data=True,
                      sources={gc.DATASET: {"enabled": True, "scope": scope}})  # fmt: skip
    if numbers is not None:
        path = layout.work_dir(PROFILE, "gb_companies_house") / "slice.csv"
        path.parent.mkdir(parents=True, exist_ok=True)
        slices.write(path, [slices.Member(n, "seed", 0, n) for n in numbers])


def build() -> BuildResult:
    builder = sources.builder_for(gc.DATASET)
    assert builder is not None

    def strict(paths: list[Path]) -> int:
        return len(validate_files(paths, strict=True)[1])

    return build_dataset(builder, load_profile(PROFILE), load_project(), strict, run_id="b-1")


def records() -> dict[str, dict[str, Any]]:
    path = layout.records_dir(PROFILE, gc.DATASET) / gc.RECORD_FILE
    return {r["id"]: r for r in iter_records(path)}


def test_the_lei_helper_gives_valid_check_digits() -> None:
    assert lei("000000000000AB") == "SYN0000000000000AB65"  # test_lists_common.py's SYN_LEI
    assert all(is_valid_lei(code) for code in (CHILD, PARENT, GHOST)) and not is_valid_lei(INVALID)


def test_discover_takes_the_two_csv_files_of_the_combined_publish() -> None:
    def entry(kind: str, cdf: str, stamp: str = "20261021-1600") -> dict[str, Any]:
        folder = "https://goldencopy.gleif.org/storage/golden-copy-files/2026/10/21/1"
        url = f"{folder}/{stamp}-gleif-goldencopy-{kind}-golden-copy.csv.zip"
        csv_file = {"type": kind, "format": "csv", "record_count": 3, "size": 1234, "url": url,
                    "delta_type": "GoldenCopy", "cdf_version": cdf}  # fmt: skip
        return {"type": kind, "publish_date": "2026-10-21 16:00:00",
                "full_file": {"csv": csv_file, "json": {}}, "delta_files": {}}  # fmt: skip

    def client(body: Any) -> HttpClient:
        def answer(request: httpx.Request) -> httpx.Response:
            assert str(request.url) == gc.PUBLISHES_URL
            return httpx.Response(200, json=body)

        return HttpClient("", follow_redirects=True, limiter=RateLimiter(1000.0),
                          transport=httpx.MockTransport(answer))  # fmt: skip

    data = {"publish_date": "2026-10-21 16:00:00", "lei2": entry("lei2", "LEI_3.1"),
            "rr": entry("rr", "RR_2.1"), "repex": entry("repex", "REPEX_2.1")}  # fmt: skip
    found = gc.discover(client({"data": data}))
    assert [(f.version, f.product, f.size, f.sha256) for f in found] == [
        (VERSION, "golden-copy", 1234, None)
    ] * 2
    assert [f.name for f in found] == [
        f"{VERSION}-gleif-goldencopy-lei2-golden-copy.csv.zip",
        f"{VERSION}-gleif-goldencopy-rr-golden-copy.csv.zip",
    ]
    for broken, message in (
        ({"rr": entry("rr", "RR_2.2")}, "not RR_2.1"),
        ({"rr": entry("rr", "RR_2.1", "20261020-1600")}, "not a Golden Copy CSV"),
        ({"lei2": {}}, "no lei2 CSV"),
        ({"publish_date": None}, "no publish_date"),
    ):
        with pytest.raises(DownloadError, match=message):
            gc.discover(client({"data": data | broken}))
    moved = entry("rr", "RR_2.1")
    moved["full_file"]["csv"]["url"] = moved["full_file"]["csv"]["url"].replace(
        "goldencopy.gleif.org", "goldencopy.example"
    )
    with pytest.raises(DownloadError, match="not a Golden Copy CSV"):
        gc.discover(client({"data": data | {"rr": moved}}))


def test_the_profile_block_is_validated(data_env: Any) -> None:
    profile(data_env, scope="everything", numbers=None)
    with pytest.raises(ValueError, match="scope"):
        load_profile(PROFILE)
    data_env.write_profile(PROFILE, real_data=True, sources={gc.DATASET: {"enabled": True,
                           "colour": "red"}})  # fmt: skip
    with pytest.raises(ValueError, match="colour"):
        load_profile(PROFILE)
    for name in ("uk-tiny", "uk-sample"):
        assert load_profile(name).options(gc.DATASET).scope == "slice"


def test_reading_maps_dotted_columns_and_keeps_line_breaks(tmp_path: Path) -> None:
    stats: Counter[str] = Counter()
    data = b"\xef\xbb\xbf" + csv_bytes(LEI_HEADER, LEI_ROWS[:1]) + b'"SHORT","ROW"\r\n'
    table = gc.Table(zipped(tmp_path / "lei.csv.zip", data), gc.LEI_COLUMNS, stats)
    rows = list(table.rows())
    assert table.header[0] == "LEI" and table.header == LEI_HEADER  # a byte order mark is dropped
    assert rows[0]["Entity.LegalName"] == "MYRTLE LEAT\nFORMATIONS LTD"
    assert gc.text(rows[0]["Entity.LegalName"]) == "MYRTLE LEAT FORMATIONS LTD"
    assert stats == {"rows_read": 1, "bad_field_count_rows": 1}
    for header, columns, missing in (
        ([c for c in LEI_HEADER if c != "Entity.LegalJurisdiction"], gc.LEI_COLUMNS,
         "Entity.LegalJurisdiction"),
        ([c for c in RR_HEADER if c != gc.STATUS], gc.RR_COLUMNS, gc.STATUS),
    ):  # fmt: skip
        broken = gc.Table(zipped(tmp_path / "x.csv.zip", csv_bytes(header, [])), columns, stats)
        with pytest.raises(BuildError, match=f"x.csv.zip: column {re.escape(missing)} is missing"):
            list(broken.rows())
    bad = gc.Table(zipped(tmp_path / "y.csv.zip", "LEI,\xe9".encode("latin-1")), (), stats)
    with pytest.raises(BuildError, match=r"y\.csv\.zip: not valid UTF-8") as stopped:
        list(bad.rows())
    assert stopped.value.counts_only


def test_dates_keep_the_written_date_and_bad_ones_are_counted() -> None:
    stats: Counter[str] = Counter()
    assert gc.iso_date("2012-06-06T15:52:00+02:00", stats, "x") == "2012-06-06"
    assert gc.iso_date("2012-06-06T23:30:00-05:00", stats, "x") == "2012-06-06"
    assert gc.iso_date("2018-01-01T00:00:00.000Z", stats, "x") == "2018-01-01"
    assert gc.iso_date("", stats, "x") is None
    for bad in ("06/06/2012", "2012-02-30", "2012"):
        assert gc.iso_date(bad, stats, "x") is None
    assert stats == {"dates_dropped.x": 3}


def test_the_slice_scope_keeps_slice_companies_and_their_parents(data_env: Any) -> None:
    profile(data_env)
    download()
    result = build()
    found = records()
    companies = {rid for rid, r in found.items() if r["schema"] == "Company"}
    assert companies == {f"gleif-{c}" for c in (CHILD, SIBLING, PARENT, ULTIMATE)}
    counts = result.counts
    assert counts["by_reason"] == {"slice": 2, "uk": 0, "all": 0, "parent": 2}
    assert counts["slice_companies"] == 5 and counts["slice_companies_with_lei"] == 2
    assert counts["registration_skipped"] == {"annulled": 1, "duplicate": 1}
    assert counts["invalid_leis"] == 1 and counts["parents_not_loaded"] == 1
    assert counts["uk_authority_leis"] == 8 and counts["scoped_leis"] == 2

    child = found[f"gleif-{CHILD}"]
    props = child["properties"]
    assert props["name"] == ["MYRTLE LEAT FORMATIONS LTD"]
    assert sorted(props["alias"]) == ["MYRTLE LEAT FORMATIONS LIMITED", "TANSY STRAND SUPPLIES LTD"]
    assert props["leiCode"] == [CHILD] and props["registrationNumber"] == ["99000001"]
    assert props["jurisdiction"] == ["gb"] and props["status"] == ["ACTIVE"]
    assert props["legalForm"] == ["SYN1"] and props["incorporationDate"] == ["2012-06-06"]
    assert props["sourceUrl"] == [f"https://search.gleif.org/#/record/{CHILD}"]
    assert child["nr"]["source_ref"] == CHILD
    # Legal and headquarters addresses with one key: one Address, role registered.
    (office,) = props["addressEntity"]
    assert child["nr"]["address_roles"] == {office: "registered"}
    full = found[office]["properties"]["full"][0]
    assert address_key(full) == "QQ1 1AA|1 TEST STREET TESTTOWN"
    assert office == gc.hashed_id("addr", address_key(full) or "")
    assert found[office]["properties"]["postalCode"] == ["QQ1 1AA"]

    sibling = found[f"gleif-{SIBLING}"]
    assert sibling["properties"]["registrationNumber"] == ["99000002"]  # normalised (RA000587)
    assert sibling["properties"]["legalForm"] == ["PRIVATE LIMITED COMPANY"]
    assert "incorporationDate" not in sibling["properties"]
    assert sorted(sibling["nr"]["address_roles"].values()) == ["business", "registered"]
    assert sibling["nr"]["address_roles"][office] == "registered"  # shared with the child
    parent = found[f"gleif-{PARENT}"]["properties"]
    assert parent["jurisdiction"] == ["us"] and parent["registrationNumber"] == ["123"]  # raw
    assert found[f"gleif-{ULTIMATE}"]["properties"]["jurisdiction"] == ["gb-sct"]
    assert counts["records"] == {"company": 4, "address": 3, "ownership": 3}
    assert counts["dates_dropped.creation"] == 1

    owns = {(r["properties"]["asset"][0], r["properties"]["owner"][0]): r
            for r in found.values() if r["schema"] == "Ownership"}  # fmt: skip
    assert {(a[6:], o[6:], r["nr"]["consolidation"]) for (a, o), r in owns.items()} == {
        (CHILD, PARENT, "direct"),
        (CHILD, ULTIMATE, "ultimate"),
        (PARENT, ULTIMATE, "direct"),
    }
    direct = owns[(f"gleif-{CHILD}", f"gleif-{PARENT}")]
    assert direct["id"] == gc.hashed_id("ownership", CHILD, PARENT, "IS_DIRECTLY_CONSOLIDATED_BY")
    assert direct["properties"]["startDate"] == ["2018-01-01"]  # the RELATIONSHIP_PERIOD
    assert not {"percentage", "sharesCount", "endDate"} & set(direct["properties"])
    assert set(direct["nr"]) == {"v", "consolidation"}
    assert counts["relationships"] == {"direct": 2, "ultimate": 1}
    assert counts["quantifiers_filled"] == 1
    assert counts["skipped_type_by_value"] == {
        "is_international_branch_of": 1,
        "is_fund-managed_by": 1,
    }
    assert counts["skipped_status_by_value"] == {"inactive": 1}
    assert counts["relationships_end_not_loaded"] == 2  # the missing parent, the outside child
    assert counts["relationships_outside_scope"] == 1
    assert counts["optional_columns_absent"] == dict.fromkeys(
        ("other_entity_names", "transliterated_other_entity_names", "entity_creation_date",
         "relationship_period", "quantifiers"), 0)  # fmt: skip
    assert result.lists == {"lei_headers": LEI_HEADER, "rr_headers": RR_HEADER}
    assert result.strings == {"version": VERSION, "scope": "slice"}
    manifest = json.loads((layout.records_dir(PROFILE, gc.DATASET) /
                           "golden-copy.manifest.json").read_text())  # fmt: skip
    assert manifest["source"]["source_version"] == VERSION


def test_the_uk_scope_and_a_header_without_optional_columns(data_env: Any) -> None:
    profile(data_env, scope="uk", numbers=None)
    long_name = "Entity.LegalAddress." + "X" * 80
    download([*gc.LEI_COLUMNS, long_name], list(gc.RR_COLUMNS))
    result = build()
    found = records()
    companies = {rid[6:] for rid, r in found.items() if r["schema"] == "Company"}
    assert companies == {
        CHILD,
        SIBLING,
        OUTSIDE,
        ODD,
        ULTIMATE,
        INACTIVE_PARENT,
        OTHER_A,
        OTHER_B,
        PARENT,
    }
    assert result.counts["by_reason"] == {"slice": 0, "uk": 8, "all": 0, "parent": 1}
    odd = found[f"gleif-{ODD}"]["properties"]
    assert odd["registrationNumber"] == ["XY123456"]  # not a Companies House form: kept raw
    assert result.counts["uk_numbers_not_ch_form"] == 1
    child = found[f"gleif-{CHILD}"]["properties"]
    assert "alias" not in child and "incorporationDate" not in child
    assert result.counts["optional_columns_absent"] == dict.fromkeys(
        ("other_entity_names", "transliterated_other_entity_names", "entity_creation_date",
         "relationship_period", "quantifiers"), 1)  # fmt: skip
    assert result.counts["relationships"] == {"direct": 4, "ultimate": 1}
    assert result.counts["headers_too_long"] == 1
    assert result.lists["lei_headers"] == list(gc.LEI_COLUMNS)


def test_a_missing_slice_or_download_names_what_to_run_first(data_env: Any) -> None:
    profile(data_env, numbers=None)
    download()
    with pytest.raises(BuildError, match="build gb_companies_house for this profile first") as e:
        build()
    assert e.value.exit_code == 2 and e.value.counts_only
    profile(data_env, scope="all", numbers=None)
    with pytest.raises(BuildError, match="no complete download") as e:
        (layout.sources_dir(gc.DATASET, gc.PRODUCT, VERSION) / "download.json").unlink()
        build()
    assert e.value.exit_code == 2


def test_ingest_build_writes_the_header_lists_and_counts_only(data_env: Any) -> None:
    from neonradar_cli.main import app

    profile(data_env)
    download()
    data_env.allow_real(PROFILE)
    command = ["ingest", "build", "--profile", PROFILE, "--dataset", gc.DATASET]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    summary = json.loads(next(layout.reports_dir(PROFILE).glob("ingest-build-*.json")).read_text())
    gleif = summary["datasets"][gc.DATASET]
    assert gleif["lei_headers"] == LEI_HEADER and gleif["rr_headers"] == RR_HEADER
    assert gleif["version"] == VERSION and gleif["scope"] == "slice"
    assert gleif["records"] == {"company": 4, "address": 3, "ownership": 3}
    for text in (json.dumps(summary), result.output):
        assert "SYN0" not in text and "MYRTLE" not in text and "QQ1" not in text
        assert "99000001" not in text
