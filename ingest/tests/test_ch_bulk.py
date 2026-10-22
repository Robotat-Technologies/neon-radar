"""The Free Company Data loader (PHASE-2.md M2.3a): discovery, reading, index and companies.

Every part is built in memory as a zip file with the product's literal header (research note
bulk-sources-loading.md 2.2) and invented values: `T` company numbers, which no Companies House
number has, `QQ` postcodes and test names. Nothing is committed as a file (2.9).
"""

import csv
import io
import json
import re
import sqlite3
import zipfile
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
from neonradar_ingest.data.sources import BuildError
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.companies_house import build as ch_build
from neonradar_ingest.sources.companies_house import bulk
from neonradar_ingest.sources.companies_house import records as records_module
from neonradar_keys.addresses import address_key

HEADER = (
    "CompanyName, CompanyNumber,RegAddress.CareOf,RegAddress.POBox,RegAddress.AddressLine1,"
    " RegAddress.AddressLine2,RegAddress.PostTown,RegAddress.County,RegAddress.Country,"
    "RegAddress.PostCode,CompanyCategory,CompanyStatus,CountryOfOrigin,DissolutionDate,"
    "IncorporationDate,Accounts.AccountRefDay,Accounts.AccountRefMonth,Accounts.NextDueDate,"
    "Accounts.LastMadeUpDate,Accounts.AccountCategory,Returns.NextDueDate,"
    "Returns.LastMadeUpDate,Mortgages.NumMortCharges,Mortgages.NumMortOutstanding,"
    "Mortgages.NumMortPartSatisfied,Mortgages.NumMortSatisfied,SICCode.SicText_1,"
    "SICCode.SicText_2,SICCode.SicText_3,SICCode.SicText_4,LimitedPartnerships.NumGenPartners,"
    "LimitedPartnerships.NumLimPartners,URI,PreviousName_1.CONDATE, PreviousName_1.CompanyName,"
    " PreviousName_2.CONDATE, PreviousName_2.CompanyName,PreviousName_3.CONDATE,"
    " PreviousName_3.CompanyName,PreviousName_4.CONDATE, PreviousName_4.CompanyName,"
    "PreviousName_5.CONDATE, PreviousName_5.CompanyName,PreviousName_6.CONDATE,"
    " PreviousName_6.CompanyName,PreviousName_7.CONDATE, PreviousName_7.CompanyName,"
    "PreviousName_8.CONDATE, PreviousName_8.CompanyName,PreviousName_9.CONDATE,"
    " PreviousName_9.CompanyName,PreviousName_10.CONDATE, PreviousName_10.CompanyName,"
    "ConfStmtNextDueDate, ConfStmtLastMadeUpDate"
)
COLUMNS = [cell.strip() for cell in HEADER.split(",")]
VERSION = "2026-10-01"
DATASET = bulk.DATASET


def company(number: str, postcode: str = "QQ1 1AA", **values: str) -> dict[str, str]:
    row = {"CompanyName": "TEST HOLDER LTD", "CompanyNumber": number,
           "RegAddress.AddressLine1": "1 TEST STREET", "RegAddress.PostTown": "TESTTOWN",
           "RegAddress.PostCode": postcode, "CompanyCategory": "Private Limited Company",
           "CompanyStatus": "Active", "CountryOfOrigin": "United Kingdom",
           "IncorporationDate": "11/06/2021", "Accounts.AccountCategory": "DORMANT",
           "SICCode.SicText_1": "70100 - Activities of head offices"}  # fmt: skip
    return row | values


def csv_bytes(rows: Sequence[dict[str, str] | list[str]], header: str = HEADER) -> bytes:
    out = io.StringIO()
    out.write(header + "\n")
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\n")
    for row in rows:
        writer.writerow(row if isinstance(row, list) else [row.get(c, "") for c in COLUMNS])
    return out.getvalue().encode("utf-8")


def write_part(folder: Path, n: int, m: int, data: bytes) -> Path:
    stem = f"BasicCompanyData-{VERSION}-part{n}_{m}"
    folder.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(folder / f"{stem}.zip", "w") as archive:
        archive.writestr(f"{stem}.csv", data)
    return folder / f"{stem}.zip"


def download(*parts: bytes) -> list[Path]:
    """The parts as a complete download of the `companies` product (as `data fetch` leaves it)."""
    folder = layout.sources_dir(DATASET, "companies", VERSION)
    paths = [write_part(folder, n, len(parts), data) for n, data in enumerate(parts, 1)]
    files = [{"name": p.name, "url": f"https://download.example/{p.name}", "product": "companies"}
             for p in paths]  # fmt: skip
    (folder / "download.json").write_text(json.dumps({"files": files, "complete": True}))
    return paths


def profile(env: Any, **companies: Any) -> None:
    block = {"seeds": [], "postcode_districts": ["QQ1"], "max_per_district": 100,
             "max_companies": 1000, "sample_seed": 7} | companies  # fmt: skip
    sources = {DATASET: {"enabled": True, "companies": block, "psc": {"enabled": False}}}
    env.write_profile("ch-test", real_data=True, sources=sources)


def strict(paths: list[Path]) -> int:
    return len(validate_files(paths, strict=True)[1])


def build(steps: tuple[str, ...] = (), keep_work: bool = False) -> Any:
    builder = sources.builder_for(DATASET)
    assert builder is not None
    return build_dataset(builder, load_profile("ch-test"), load_project(), strict,
                         run_id="build-1", steps=steps, keep_work=keep_work)  # fmt: skip


def records() -> dict[str, dict[str, Any]]:
    path = layout.records_dir("ch-test", DATASET) / "companies.ftm.jsonl"
    return {r["id"]: r for r in iter_records(path)}


def rows_of(tmp_path: Path, data: bytes) -> tuple[list[bulk.Row], Any]:
    from collections import Counter

    stats: Counter[str] = Counter()
    part = write_part(tmp_path / "parts", 1, 1, data)
    return list(bulk.iter_part(part, stats)), stats


def test_the_header_with_leading_spaces_is_mapped_by_name(tmp_path: Path) -> None:
    rows, stats = rows_of(tmp_path, csv_bytes([company("T0000001")]))
    assert rows[0]["CompanyNumber"] == "T0000001"
    assert rows[0]["PreviousName_10.CompanyName"] == ""
    assert stats["rows_read"] == 1
    assert stats["extra_columns"] == len(set(COLUMNS) - set(bulk.COLUMNS))


def test_a_missing_column_stops_the_build_with_its_name(tmp_path: Path) -> None:
    header = HEADER.replace("CountryOfOrigin,", "")
    with pytest.raises(BuildError, match="column CountryOfOrigin is missing") as stopped:
        rows_of(tmp_path, csv_bytes([], header=header))
    with pytest.raises(BuildError, match="no header line"):
        rows_of(tmp_path, b"")
    assert stopped.value.counts_only


def test_a_56_field_row_and_an_empty_row_are_skipped_and_counted(tmp_path: Path) -> None:
    good = company("T0000001")
    wide = [good.get(c, "") for c in COLUMNS] + ["99999 - Dormant Company"]
    data = csv_bytes([good, wide]) + b"\n" + csv_bytes([company("T0000002")])[len(HEADER) + 1 :]
    rows, stats = rows_of(tmp_path, data)
    assert [r["CompanyNumber"] for r in rows] == ["T0000001", "T0000002"]
    assert (stats["bad_field_count_rows"], stats["empty_rows"]) == (1, 1)


def test_a_mis_encoded_byte_stops_the_build_with_the_part_name(tmp_path: Path) -> None:
    data = csv_bytes([company("T0000001", CompanyName="TEST HOLDER LTD")])
    with pytest.raises(BuildError, match=r"part1_1\.zip: not valid UTF-8") as stopped:
        rows_of(tmp_path, data.replace(b"HOLDER", b"HOLD\xe9R"))
    assert stopped.value.rule == "encoding"


def test_only_complete_html_references_are_decoded() -> None:
    assert bulk.text("TEST&#032;HOLDER&#039;S &AMP; CO LTD") == "TEST HOLDER'S & CO LTD"
    assert bulk.text("TEST &#x1F4A9; LTD") == "TEST \U0001f4a9 LTD"
    assert bulk.text("TEST A&B LTD") == "TEST A&B LTD"
    assert bulk.text("A&B; &#39") == "A&B; &#39"  # `&B;` is not a reference; `&#39` is cut


def test_dates_are_strict_day_first_and_bad_ones_are_counted() -> None:
    from collections import Counter

    stats: Counter[str] = Counter()
    assert bulk.iso_date("11/06/2021", stats, "x") == "2021-06-11"
    assert bulk.iso_date("", stats, "x") is None
    for bad in ("31/02/2021", "2021-06-11", "1/6/2021", "11/06/21"):
        assert bulk.iso_date(bad, stats, "x") is None
    assert stats == {"dates_dropped.x": 4}


def test_punctuation_digits_and_bare_outward_codes_are_missing_address_fields() -> None:
    assert [bulk.address_part(v) for v in ("-", "12", " ., ", "QQ1", "qq12", "")] == [None] * 6
    assert bulk.address_part(" 1  TEST STREET ") == "1 TEST STREET"
    assert bulk.district("qq1 1aa") == "QQ1" and bulk.district("QQ1") is None


def test_discover_takes_the_newest_snapshot_with_every_part() -> None:
    names = [
        "BasicCompanyData-2026-10-01-part1_2.zip",
        "BasicCompanyData-2026-10-01-part2_2.zip",
        "BasicCompanyData-2026-11-01-part1_3.zip",
        "BasicCompanyDataAsOneFile-2026-10-01.zip",
    ]
    elsewhere = [  # a complete newer set, but not on the download host over https: ignored
        "https://elsewhere.example/BasicCompanyData-2026-12-01-part1_1.zip",
        "http://download.companieshouse.gov.uk/BasicCompanyData-2026-12-01-part1_1.zip",
    ]
    page = "".join(f'<a href="{name}">{name}</a>' for name in names + elsewhere)

    def answer(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == bulk.PAGE_URL
        return httpx.Response(200, text=page)

    client = HttpClient("", follow_redirects=True, limiter=RateLimiter(1000.0),
                        transport=httpx.MockTransport(answer))  # fmt: skip
    found = bulk.discover(client)
    assert [(f.name, f.version, f.product, f.size, f.sha256) for f in found] == [
        (names[0], "2026-10-01", "companies", None, None),
        (names[1], "2026-10-01", "companies", None, None),
    ]
    assert found[0].url == "https://download.companieshouse.gov.uk/" + names[0]
    empty = HttpClient(
        "",
        follow_redirects=True,
        limiter=RateLimiter(1000.0),
        transport=httpx.MockTransport(lambda r: httpx.Response(200, text=names[2])),
    )
    with pytest.raises(DownloadError, match="no snapshot"):
        bulk.discover(empty)


def test_the_profile_block_is_validated(data_env: Any) -> None:
    profile(data_env, colour="red")
    with pytest.raises(ValueError, match="colour"):
        load_profile("ch-test")
    profile(data_env, seeds=["1800000"])
    with pytest.raises(ValueError, match="8-character"):
        load_profile("ch-test")
    for name in ("uk-tiny", "uk-sample"):
        assert load_profile(name).options(DATASET).companies is not None


def test_a_step_without_its_input_names_the_step_to_run_first(data_env: Any) -> None:
    profile(data_env)
    with pytest.raises(BuildError, match="data fetch") as stopped:
        build(("index",))
    assert stopped.value.exit_code == 2
    download(csv_bytes([company("T0000001")]))
    with pytest.raises(BuildError, match="run --step index first"):
        build(("slice",))
    with pytest.raises(BuildError, match="run --step slice first"):
        build(("companies",))


def test_a_full_build_keeps_slice_csv_and_deletes_the_indexes(data_env: Any) -> None:
    profile(data_env)
    download(csv_bytes([company("T0000001")]))
    work = layout.work_dir("ch-test", DATASET)
    work.mkdir(parents=True)
    statement_table(work / ch_build.PSC_INDEX, [])
    build(("index", "slice"))
    assert (work / ch_build.INDEX).is_file()  # the companies step has not run yet
    result = build(keep_work=True)
    assert (work / ch_build.INDEX).is_file() and (work / ch_build.PSC_INDEX).is_file()
    assert result.strings["version"] == VERSION
    build()
    assert sorted(p.name for p in work.iterdir()) == ["slice.csv"]


def statement_table(path: Path, rows: list[tuple[str, str]]) -> None:
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE statement(company_number TEXT, value TEXT)")
    connection.executemany("INSERT INTO statement VALUES (?, ?)", rows)
    connection.commit()
    connection.close()


def test_company_and_address_records(data_env: Any) -> None:
    profile(data_env, seeds=["FCT00001", "SFT00001", "NFT00001", "OET00001"])
    shared = {"RegAddress.AddressLine1": "1 Test St.", "RegAddress.PostTown": "TESTTOWN"}
    download(
        csv_bytes([
            company("T0000001", CompanyName="TEST&#032;HOLDER LTD", **shared,
                    **{"PreviousName_1.CompanyName": "OLD &AMP; TEST LTD",
                       "SICCode.SicText_2": "None Supplied", "DissolutionDate": "31/02/2020"}),
            company("T0000002", "qq1  1aa", CompanyName="TEST A&B LTD", **shared,
                    **{"RegAddress.Country": "UNITED KINGDOM", "RegAddress.AddressLine2": "."}),
            company("FCT00001", "", CountryOfOrigin="FRANCE",
                    **{"RegAddress.AddressLine1": "-", "RegAddress.PostTown": ""}),
            company("SFT00001", CountryOfOrigin="GERMANY"),
            company("NFT00001", CountryOfOrigin="IRELAND"),
        ]),
        csv_bytes([company("OET00001", CountryOfOrigin="NOT A COUNTRY")]),
    )  # fmt: skip
    work = layout.work_dir("ch-test", DATASET)
    work.mkdir(parents=True)
    statement_table(work / ch_build.PSC_INDEX, [("T0000001", "psc-exists-but-not-identified"),
                    ("T0000001", "no-individual-or-entity-with-signficant-control"),
                    ("T0000009", "psc-details-not-confirmed")])  # fmt: skip
    result = build()
    found = records()
    first = found["gbch-co-T0000001"]
    assert first["properties"]["name"] == ["TEST HOLDER LTD"]
    assert first["properties"]["previousName"] == ["OLD & TEST LTD"]
    assert first["properties"]["sector"] == ["70100"]
    assert first["properties"]["incorporationDate"] == ["2021-06-11"]
    assert "dissolutionDate" not in first["properties"]
    assert first["properties"]["sourceUrl"] == [
        "https://find-and-update.company-information.service.gov.uk/company/T0000001"
    ]
    assert first["nr"]["accounts_category"] == "DORMANT"
    assert first["nr"]["psc_statements"] == [
        "no-individual-or-entity-with-signficant-control",
        "psc-exists-but-not-identified",
    ]
    assert found["gbch-co-T0000002"]["properties"]["name"] == ["TEST A&B LTD"]
    # One Address for the two offices with the same key; its full text gives that key back.
    addresses = [r for r in found.values() if r["schema"] == "Address"]
    office = first["properties"]["addressEntity"]
    assert found["gbch-co-T0000002"]["properties"]["addressEntity"] == office
    assert first["nr"]["address_roles"] == {office[0]: "registered"}
    shared_office = found[office[0]]["properties"]
    assert address_key(shared_office["full"][0]) == "QQ1 1AA|1 TEST STREET TESTTOWN"
    assert office[0] == records_module.address_id(address_key(shared_office["full"][0]) or "")
    assert shared_office["postalCode"] == ["QQ1 1AA"] and shared_office["country"] == ["gb"]
    assert len(addresses) == 1  # the FC office has no key: no street line, no postcode
    jurisdictions = {rid: r["properties"].get("jurisdiction") for rid, r in found.items()}
    assert jurisdictions["gbch-co-T0000001"] == ["gb"]
    assert jurisdictions["gbch-co-FCT00001"] == ["fr"]
    assert jurisdictions["gbch-co-SFT00001"] == ["de"]
    assert jurisdictions["gbch-co-NFT00001"] == ["ie"]
    assert jurisdictions["gbch-co-OET00001"] is None
    assert "addressEntity" not in found["gbch-co-FCT00001"]["properties"]
    counts = result.counts["companies"]
    assert counts["records"] == {"company": 6, "address": 1}
    assert counts["overseas_origin_unmapped"] == 1
    assert counts["companies_without_address_key"] == 1
    assert counts["sic_without_code"] == 1
    assert counts["dates_dropped.dissolution"] == 1
    assert counts["top10_address_share"] == round(5 / 6, 4)
    assert result.strings["statements"] == "present"


def test_without_the_psc_index_statements_are_absent(data_env: Any) -> None:
    profile(data_env)
    download(csv_bytes([company("T0000001")]))
    result = build()
    assert result.strings["statements"] == "absent"
    assert "psc_statements" not in records()["gbch-co-T0000001"]["nr"]
    manifest = json.loads((layout.records_dir("ch-test", DATASET) /
                           "companies.manifest.json").read_text())  # fmt: skip
    assert manifest["source"]["source_version"] == VERSION


def test_top10_address_share_counts_the_ten_most_common_offices(data_env: Any) -> None:
    profile(data_env)
    rows = [company(f"T{n:07d}", **{"RegAddress.AddressLine1": f"{n % 12} TEST STREET"})
            for n in range(1, 25)]  # fmt: skip
    download(csv_bytes(rows))
    counts = build().counts["companies"]
    assert counts["records"]["address"] == 12
    assert counts["top10_address_share"] == round(20 / 24, 4)


def test_ingest_build_emits_a_counts_only_summary(data_env: Any) -> None:
    from neonradar_cli.main import app

    profile(data_env, seeds=["T0000003"])
    download(csv_bytes([company("T0000001"), company("T0000002", "QQ2 1AA")]))
    data_env.allow_real("ch-test")
    command = ["ingest", "build", "--profile", "ch-test", "--dataset", DATASET]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    summary = json.loads(
        next(layout.reports_dir("ch-test").glob("ingest-build-*.json")).read_text()
    )
    ch = summary["datasets"][DATASET]
    assert ch["slice"]["by_reason"] == {"seed": 1, "district": 1, "parent": 0, "child": 0}
    assert ch["slice"]["seeds_missing_from_index"] == 1 and len(ch["slice_sha256"]) == 64
    assert ch["companies"]["records"] == {"company": 1, "address": 1}
    for text in (json.dumps(summary), result.output):
        assert "TEST" not in text and "QQ" not in text
        assert not re.search(r"(?<![0-9])T000000[1-3]", text)


def test_a_failed_real_build_prints_the_rule_and_the_part_only(data_env: Any) -> None:
    from neonradar_cli.main import app

    profile(data_env)
    data = csv_bytes([company("T0000001", CompanyName="TEST HOLDER LTD")])
    download(data.replace(b"HOLDER", b"HOLD\xe9R"))
    data_env.allow_real("ch-test")
    command = ["ingest", "build", "--profile", "ch-test", "--dataset", DATASET]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 1
    assert "rule encoding" in result.output and "part1_1.zip: not valid UTF-8" in result.output
    assert "TEST" not in result.output and "T0000001" not in result.output
