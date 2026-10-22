"""The PSC snapshot loader (PHASE-2.md M2.3b): discovery, both passes, the expansion, records.

Every snapshot part is built in memory as a zip file of JSON lines in the published format
(research note bulk-sources-loading.md 3.2) with invented values: `99` company numbers, `QQ`
postcodes, `SYN` PSC ids, surnames checked under OD-12 and company names from the demo-mini
fixture. Nothing is committed as a file (2.9).
"""

import csv
import io
import json
import re
import sqlite3
import zipfile
from pathlib import Path
from typing import Any

import httpx
import pytest
from typer.testing import CliRunner

from neonradar_contracts.records import iter_records, validate_files
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.build import build_dataset
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import load_project
from neonradar_ingest.data.sources import BuildError
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.companies_house import build as ch_build
from neonradar_ingest.sources.companies_house import bulk, psc
from neonradar_ingest.sources.companies_house import slice as slices

DATASET = bulk.DATASET
VERSION, SNAPSHOT = "2026-10-01", "2026-10-17"
OFFICE = {
    "premises": "1",
    "address_line_1": "Test Street",
    "locality": "Testtown",
    "postal_code": "QQ1 1AA",
    "country": "England",
}
NAMES = {
    "99000010": "BRACKEN DALE FREIGHT LTD",
    "99000020": "TANSY STRAND SUPPLIES LTD",
    "99000030": "LARCH MERE SERVICES LTD",
    "99000040": "HAZEL BRAE TEXTILES LTD",
    "99000050": "KESTREL SCAR FINANCE LTD",
    "99000060": "SORREL SIKE TRADING LTD",
    "OE000070": "UMBER GARTH FOODS LTD",
}


def companies_part(numbers: list[str]) -> bytes:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(bulk.COLUMNS)
    for number in numbers:
        row = {
            "CompanyName": NAMES[number],
            "CompanyNumber": number,
            "CompanyStatus": "Active",
            "RegAddress.AddressLine1": "1 TEST STREET",
            "RegAddress.PostTown": "TESTTOWN",
            "RegAddress.PostCode": "QQ1 1AA",
            "CompanyCategory": "Private Limited Company",
        }
        writer.writerow([row.get(column, "") for column in bulk.COLUMNS])
    return out.getvalue().encode()


def put(product: str, version: str, parts: dict[str, bytes], member: str) -> None:
    """The parts as a complete download of `product` (as `data fetch` leaves it)."""
    folder = layout.sources_dir(DATASET, product, version)
    folder.mkdir(parents=True, exist_ok=True)
    for name, data in parts.items():
        with zipfile.ZipFile(folder / name, "w") as archive:
            archive.writestr(name.replace(".zip", member), data)
    files = [{"name": n, "url": f"https://download.example/{n}", "product": product} for n in parts]
    (folder / "download.json").write_text(json.dumps({"files": files, "complete": True}))


def lines(*items: dict[str, Any]) -> bytes:
    return b"".join(json.dumps(item).encode() + b"\n" for item in items)


def totals(pscs: int, statements: int = 0, exemptions: int = 0) -> dict[str, Any]:
    return {
        "data": {
            "kind": psc.TOTALS,
            "persons_of_significant_control_count": pscs,
            "statements_count": statements,
            "exemptions_count": exemptions,
            "generated_at": "2026-10-17T03:00:00Z",
        }
    }


def line(number: str, kind: str, ident: str, **data: Any) -> dict[str, Any]:
    folder = {"individual": "individual", "corporate": "corporate-entity"}.get(kind[:10], "x")
    link = f"/company/{number}/persons-with-significant-control/{folder}/SYN{ident}"
    return {
        "company_number": number,
        "data": {
            "kind": kind,
            "etag": "0",
            "links": {"self": link},
            "notified_on": "2016-04-06",
            **data,
        },
    }


def person(number: str, ident: str, natures: list[str], **data: Any) -> dict[str, Any]:
    values = {
        "name": "Mr Zafer Velqasimi",
        "nationality": "British,Syrian",
        "name_elements": {"title": "Mr", "forename": "Zafer", "surname": "Velqasimi"},
        "date_of_birth": {"month": 3, "year": 1981},
        "country_of_residence": "England",
        "address": OFFICE,
        "natures_of_control": natures,
    }
    return line(number, "individual-person-with-significant-control", ident, **values | data)


def corporate(
    number: str,
    ident: str,
    name: str,
    identification: dict[str, str],
    natures: list[str] | None = None,
    **data: Any,
) -> dict[str, Any]:
    values = {
        "name": name,
        "identification": identification,
        "address": OFFICE,
        "natures_of_control": natures or ["ownership-of-shares-75-to-100-percent"],
    }
    kind = data.pop("kind", "corporate-entity-person-with-significant-control")
    return line(number, kind, ident, **values | data)


def uk(number: str) -> dict[str, str]:
    return {
        "country_registered": "England",
        "place_registered": "Companies House",
        "legal_authority": "Companies Act 2006",
        "legal_form": "Private Limited Company",
        "registration_number": number,
    }


def profile(env: Any, seeds: list[str], max_companies: int = 100, **block: Any) -> None:
    companies = {
        "seeds": seeds,
        "postcode_districts": [],
        "max_per_district": 0,
        "max_companies": max_companies,
        "sample_seed": 7,
    }
    psc_block = {"enabled": True, "parent_depth": 2, "child_depth": 1} | block
    sources_ = {DATASET: {"enabled": True, "companies": companies, "psc": psc_block}}
    env.write_profile("ch-test", real_data=True, sources=sources_)


def download(pscs: list[bytes]) -> None:
    put(
        "companies",
        VERSION,
        {f"BasicCompanyData-{VERSION}-part1_1.zip": companies_part(list(NAMES))},
        ".csv",
    )
    parts = {f"psc-snapshot-{SNAPSHOT}_{n}of{len(pscs)}.zip": d for n, d in enumerate(pscs, 1)}
    put("psc", SNAPSHOT, parts, ".txt")


def strict(paths: list[Path]) -> int:
    return len(validate_files(paths, strict=True)[1])


def build(steps: tuple[str, ...] = (), keep_work: bool = False) -> Any:
    builder = sources.builder_for(DATASET)
    assert builder is not None
    return build_dataset(
        builder,
        load_profile("ch-test"),
        load_project(),
        strict,
        run_id="build-1",
        steps=steps,
        keep_work=keep_work,
    )


def records() -> dict[str, dict[str, Any]]:
    folder = layout.records_dir("ch-test", DATASET)
    return {r["id"]: r for p in sorted(folder.glob("*.ftm.jsonl")) for r in iter_records(p)}


def links(found: dict[str, dict[str, Any]], owner: str) -> dict[str, dict[str, Any]]:
    """The `Ownership` and `Control` records of one PSC record, by `Interest.key` order."""
    return {
        r["id"]: r
        for r in found.values()
        if owner in r["properties"].get("owner", []) + r["properties"].get("controller", [])
    }


def table(name: str, sql: str) -> list[tuple[Any, ...]]:
    connection = sqlite3.connect(layout.work_dir("ch-test", DATASET) / name)
    try:
        return sorted(connection.execute(sql).fetchall())
    finally:
        connection.close()


def test_discover_takes_the_newest_psc_snapshot_with_every_part() -> None:
    names = [f"psc-snapshot-2026-10-17_{n}of2.zip" for n in (1, 2)]
    names += ["psc-snapshot-2026-10-18_1of2.zip", "persons-with-significant-control-snapshot.zip"]
    page = "".join(f'<a href="{name}">{name}</a>' for name in names)

    def answer(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == psc.PAGE_URL
        return httpx.Response(200, text=page)

    client = HttpClient(
        "",
        follow_redirects=True,
        limiter=RateLimiter(1000.0),
        transport=httpx.MockTransport(answer),
    )
    found = psc.discover(client)
    assert [(f.name, f.version, f.product) for f in found] == [
        (names[0], "2026-10-17", "psc"),
        (names[1], "2026-10-17", "psc"),
    ]
    spec = sources.source_spec(DATASET)
    assert spec is not None and spec.discover is ch_build.discover


def test_every_kind_statements_and_the_statement_table(data_env: Any) -> None:
    profile(data_env, ["99000010", "OE000070"], parent_depth=0, child_depth=0)
    oe_address = {
        "principal_office_address": {
            "address_line_1": "1 Rue d'Essai",
            "locality": "Testville",
            "country": "France",
        }
    }
    download(
        [
            lines(
                person("99000010", "P1", ["ownership-of-shares-25-to-50-percent"]),
                line(
                    "OE000070",
                    "individual-beneficial-owner",
                    "P2",
                    name="Yazan Ulvarazi",
                    name_elements={"forename": "Yazan", "surname": "Ulvarazi"},
                    nationality="French",
                    natures_of_control=[
                        "voting-rights-more-than-25-percent-registered-overseas-entity"
                    ],
                    is_sanctioned=True,
                    address=OFFICE,
                ),
                corporate("99000010", "C1", "TANSY STRAND SUPPLIES LIMITED", uk("99000020")),
                corporate(
                    "OE000070",
                    "C2",
                    "LINNET WOLD FOODS SARL",
                    {
                        "country_registered": "France",
                        "legal_form": "Sarl",
                        "registration_number": "FR-99-0001",
                    },
                    ["ownership-of-shares-more-than-25-percent-registered-overseas-entity"],
                    kind="corporate-entity-beneficial-owner",
                    is_sanctioned=False,
                    address=None,
                    **oe_address,
                ),
                line(
                    "99000010",
                    "legal-person-person-with-significant-control",
                    "L1",
                    name="SYNTHETIC AUTHORITY A",
                    identification={"legal_authority": "Test Act", "legal_form": "Public Body"},
                    address=OFFICE,
                    natures_of_control=["significant-influence-or-control"],
                ),
                line(
                    "99000010",
                    "legal-person-with-significant-control",
                    "L2",
                    name="SYNTHETIC BODY B",
                    natures_of_control=["right-to-appoint-and-remove-directors"],
                ),
                line(
                    "OE000070",
                    "legal-person-beneficial-owner",
                    "L3",
                    name="SYNTHETIC BODY C",
                    natures_of_control=[
                        "significant-influence-or-control-registered-overseas-entity"
                    ],
                ),
                line("99000010", "super-secure-person-with-significant-control", "S1"),
                line("99000020", "super-secure-beneficial-owner", "S2", ceased=True),
                line(
                    "99000010",
                    "persons-with-significant-control-statement",
                    "T1",
                    statement="psc-details-not-confirmed",
                ),
                line(
                    "99000010",
                    "persons-with-significant-control-statement",
                    "T2",
                    statement="no-individual-or-entity-with-signficant-control",
                    ceased_on="2020-01-01",
                ),
                line(
                    "OE000070",
                    "exemptions",
                    "E1",
                    exemptions={
                        "psc_exempt_as_trading_on_regulated_market": {
                            "exemption_type": "x",
                            "items": [],
                        },
                        "disclosure_transparency_rules_chapter_five_applies": {"items": []},
                    },
                ),
            )
        ]
    )
    result = build()
    found = records()
    schemas = {rid: found[rid]["schema"] for rid in found if rid.startswith("gbch-psc-")}
    assert schemas == {
        "gbch-psc-SYNP1": "Person",
        "gbch-psc-SYNP2": "Person",
        "gbch-psc-SYNC1": "Company",
        "gbch-psc-SYNC2": "Company",
        "gbch-psc-SYNL1": "Organization",
        "gbch-psc-SYNL2": "Organization",
        "gbch-psc-SYNL3": "Organization",
    }
    zafer = found["gbch-psc-SYNP1"]
    assert zafer["properties"] | {"addressEntity": []} == {
        "name": ["Mr Zafer Velqasimi"],
        "firstName": ["Zafer"],
        "lastName": ["Velqasimi"],
        "birthDate": ["1981-03"],
        "nationality": ["gb", "sy"],
        "country": ["gb"],
        "addressEntity": [],
    }
    office = zafer["properties"]["addressEntity"][0]
    assert zafer["nr"] == {"v": "1.1", "source_ref": "SYNP1", "address_roles": {office: "service"}}
    # The PSC's office has the key of the companies' registered office: one Address record.
    assert found["gbch-co-99000010"]["properties"]["addressEntity"] == [office]
    assert sum(r["schema"] == "Address" for r in found.values()) == 2
    company = found["gbch-psc-SYNC1"]["properties"]
    assert company["registrationNumber"] == ["99000020"] and company["jurisdiction"] == ["gb"]
    assert company["legalForm"] == ["Private Limited Company"]
    foreign = found["gbch-psc-SYNC2"]
    assert foreign["properties"]["registrationNumber"] == ["FR-99-0001"]
    assert foreign["properties"]["jurisdiction"] == ["fr"]
    assert list(foreign["nr"]["address_roles"].values()) == ["registered"]
    assert found["gbch-psc-SYNP2"]["properties"]["topics"] == ["sanction"]  # is_sanctioned
    assert "topics" not in foreign["properties"]  # is_sanctioned false
    assert "topics" not in zafer["properties"]
    assert found["gbch-psc-SYNL1"]["properties"]["legalForm"] == ["Public Body"]
    assert found["gbch-co-99000010"]["nr"]["psc_statements"] == [
        "psc-details-not-confirmed",
        "super-secure-person-with-significant-control",
    ]
    assert found["gbch-co-OE000070"]["nr"]["psc_statements"] == [
        "disclosure_transparency_rules_chapter_five_applies",
        "psc_exempt_as_trading_on_regulated_market",
    ]
    index = result.counts["psc-index"]
    assert index["kinds_by_value"]["super-secure-beneficial-owner"] == 1
    assert len(index["kinds_by_value"]) == len(psc.KNOWN_KINDS) == 11
    assert (index["statements_ceased_skipped"], index["super_secure_ceased_skipped"]) == (1, 1)
    assert index["statement_rows"] == 4 and index["corporate_psc_rows"] == 5
    counts = result.counts["psc"]
    assert counts["records"] == {
        "address": 1,
        "company": 2,
        "control": 4,
        "organization": 3,
        "ownership": 3,
        "person": 2,
    }
    assert counts["beneficial_owners_sanctioned"] == 1 and counts["lines_not_psc"] == 4
    assert result.strings["snapshot_date"] == SNAPSHOT


def test_the_five_outcomes_and_the_non_uk_countries(data_env: Any) -> None:
    profile(data_env, ["99000010"])
    download(
        [
            lines(
                corporate("99000010", "A", "Tansy Strand Supplies Ltd", uk("9900 0020")),
                corporate("99000010", "B", "HARBOUR TEST FOODS LTD", uk("99000030")),
                corporate("99000010", "C", "TANSY STRAND SUPPLIES LTD", uk("99000999")),
                corporate("99000010", "D", "TANSY STRAND SUPPLIES LTD", uk("N/A")),
                corporate(
                    "99000010", "E", "TANSY STRAND SUPPLIES SARL", {"country_registered": "France"}
                ),
                corporate(
                    "99000010", "F", "TANSY STRAND SUPPLIES SA", {"country_registered": "Atlantis"}
                ),
            )
        ]
    )
    counts = build(("index", "psc-index"), keep_work=True).counts["psc-index"]
    assert counts["outcomes"] == {
        "resolved": 1,
        "name_mismatch": 1,
        "number_not_found": 1,
        "no_number": 1,
        "non_uk": 2,
    }
    assert counts["non_uk_countries_by_value"] == {"fr": 1}
    assert counts["non_uk_country_unmapped"] == 1
    assert table(ch_build.PSC_INDEX, "SELECT psc_id, outcome, number FROM corporate_psc") == [
        ("SYNA", "resolved", "99000020"),
        ("SYNB", "name_mismatch", "99000030"),
        ("SYNC", "number_not_found", "99000999"),
        ("SYND", "no_number", None),
        ("SYNE", "non_uk", None),
        ("SYNF", "non_uk", None),
    ]


def test_expansion_two_levels_up_and_one_down_and_the_cap(data_env: Any) -> None:
    # 99000010 (seed) <- 99000020 <- 99000030 <- 99000040: parents at levels 1 and 2 only.
    # 99000050 is owned by 99000020 (child, level 1); 99000060 by 99000050 (level 2: not added).
    # A name mismatch is never followed.
    def owns(child: str, parent: str, ident: str, name: str = "") -> dict[str, Any]:
        return corporate(child, ident, name or NAMES[parent], uk(parent))

    download(
        [
            lines(
                owns("99000010", "99000020", "A"),
                owns("99000020", "99000030", "B"),
                owns("99000030", "99000040", "C"),
                owns("99000050", "99000020", "D"),
                owns("99000060", "99000050", "E"),
                owns("99000010", "OE000070", "F", "OTHER NAME LTD"),
            )
        ]
    )
    profile(data_env, ["99000010"])
    counts = build(("index", "psc-index", "slice"), keep_work=True).counts["slice"]
    work = layout.work_dir("ch-test", DATASET)
    assert slices.read(work / ch_build.SLICE) == [
        ("99000010", "seed", 0),
        ("99000020", "parent", 1),
        ("99000030", "parent", 2),
        ("99000050", "child", 1),
    ]
    assert counts["expansion_before_cap"] == {"parent": 2, "child": 1}
    profile(data_env, ["99000010"], child_depth=0)
    build(("slice",), keep_work=True)
    assert [n for n, _, _ in slices.read(work / ch_build.SLICE)] == [
        "99000010",
        "99000020",
        "99000030",
    ]
    profile(data_env, ["99000010"], max_companies=3)
    counts = build(("slice",), keep_work=True).counts["slice"]
    assert counts["cap_removed"] == 1  # the deepest level goes first
    assert [r for _, r, _ in slices.read(work / ch_build.SLICE)] == ["seed", "parent", "child"]


def test_bands_interests_and_record_ids(data_env: Any) -> None:
    profile(data_env, ["99000010", "OE000070"], parent_depth=0, child_depth=0)
    download(
        [
            lines(
                person(
                    "99000010",
                    "P1",
                    [
                        "ownership-of-shares-25-to-50-percent",
                        "ownership-of-shares-75-to-100-percent",
                    ],
                ),
                person(
                    "99000010",
                    "P2",
                    [
                        "ownership-of-shares-25-to-50-percent",
                        "ownership-of-shares-50-to-75-percent-as-trust",
                        "voting-rights-50-to-75-percent",
                    ],
                    name="Rakan Zubeirono",
                    name_elements={"forename": "Rakan", "surname": "Zubeirono"},
                ),
                person(
                    "99000010",
                    "P3",
                    [
                        "right-to-share-surplus-assets-75-to-100-percent"
                        "-limited-liability-partnership"
                    ],
                    name="Nadim Qandelouni",
                ),
                person(
                    "OE000070",
                    "P4",
                    [
                        "ownership-of-shares-more-than-25-percent-as-trust"
                        "-registered-overseas-entity"
                    ],
                    name="Zafir Velqasimi",
                ),
            )
        ]
    )
    build()
    found = records()

    one = links(found, "gbch-psc-SYNP1")
    assert len(one) == 1  # two ownership values of one interest: one band
    [shares] = one.values()
    assert shares["id"] == psc.interest_id("ownership", "gbch-psc-SYNP1", "99000010", "shares")
    assert shares["properties"]["percentage"] == ["25-100"]
    assert shares["properties"]["ownershipType"] == ["shares"]
    assert shares["properties"]["startDate"] == ["2016-04-06"]
    assert shares["nr"] == {
        "v": "1.1",
        "share_pct_min": 25.0,
        "share_pct_max": 100.0,
        "share_pct_min_exclusive": True,
        "natures_of_control": [
            "ownership-of-shares-25-to-50-percent",
            "ownership-of-shares-75-to-100-percent",
        ],
    }
    two = {
        r["properties"].get("ownershipType", r["properties"].get("controlType"))[0]: r
        for r in links(found, "gbch-psc-SYNP2").values()
    }
    assert set(two) == {"shares", "trust-or-firm", "voting"}  # direct and trust's holding apart
    assert two["shares"]["schema"] == "Ownership" and two["shares"]["nr"]["share_pct_max"] == 50.0
    trust = two["trust-or-firm"]
    assert trust["schema"] == "Control"
    assert trust["id"] == psc.interest_id(
        "control", "gbch-psc-SYNP2", "99000010", "trust-or-firm-shares-trust"
    )
    assert trust["properties"]["controlled"] == ["gbch-co-99000010"]
    voting = two["voting"]["nr"]
    assert (voting["share_pct_min"], voting["share_pct_max"]) == (50.0, 75.0)
    assert voting["share_pct_min_exclusive"] is voting["share_pct_max_exclusive"] is True
    assert "percentage" not in two["voting"]["properties"]
    [surplus] = links(found, "gbch-psc-SYNP3").values()
    assert surplus["properties"]["ownershipType"] == ["surplus assets"]
    assert surplus["nr"]["share_pct_min"] == 75.0 and "share_pct_min_exclusive" not in surplus["nr"]
    [trustee] = links(found, "gbch-psc-SYNP4").values()
    assert trustee["properties"]["ownershipType"] == ["shares (as trustee)"]
    assert trustee["id"] == psc.interest_id(
        "ownership", "gbch-psc-SYNP4", "OE000070", "shares-as-trust"
    )
    assert (trustee["nr"]["share_pct_min"], trustee["nr"]["share_pct_max"]) == (25.0, 100.0)


def test_totals_unknown_values_ceased_pscs_and_other_companies(data_env: Any) -> None:
    profile(data_env, ["99000010"])
    ceased = person("99000010", "P2", ["voting-rights-25-to-50-percent"], ceased_on="2021-05-01")
    part1 = lines(
        person(
            "99000010",
            "P1",
            ["ownership-of-shares-10-to-25-percent", "voting-rights-75-to-100-percent"],
        ),
        ceased,
        line("99000010", "some-new-kind", "X1"),
    )
    part2 = lines(
        person("99000050", "P3", ["voting-rights-25-to-50-percent"]),
        person("99000010", "P4", ["ownership-of-shares-10-to-25-percent"]),
        totals(5),
    )
    download([part1, part2])
    result = build()
    assert result.strings["totals_check"] == "passed"
    index = result.counts["psc-index"]
    assert index["unknown_kinds_by_value"] == {"some-new-kind": 1}
    assert index["unknown_natures_by_value"] == {"ownership-of-shares-10-to-25-percent": 2}
    assert (index["lines_read"], index["totals_lines"]) == (5, 1)
    counts = result.counts["psc"]
    assert counts["ceased_skipped"] == 1 and counts["lines_other_companies"] == 1
    assert counts["natures_unknown"] == 2 and counts["pscs_without_known_nature"] == 1
    assert "gbch-psc-SYNP2" not in records() and "gbch-psc-SYNP4" not in records()
    profile(data_env, ["99000010"], include_ceased=True)
    download([part1 + lines(totals(9)), part2])
    result = build()
    assert result.strings["totals_check"] == "failed"
    [link] = links(records(), "gbch-psc-SYNP2").values()
    assert link["properties"]["endDate"] == ["2021-05-01"]
    download([part1])
    assert build().strings["totals_check"] == "absent"


def test_steps_inputs_work_files_and_the_psc_block(data_env: Any) -> None:
    profile(data_env, ["99000010"], colour="red")
    with pytest.raises(ValueError, match="colour"):
        load_profile("ch-test")
    profile(data_env, ["99000010"])
    download([lines(person("99000010", "P1", ["voting-rights-25-to-50-percent"]))])
    with pytest.raises(BuildError, match="run --step index first"):
        build(("psc-index",))
    build(("index",))
    with pytest.raises(BuildError, match="run --step psc-index first"):
        build(("slice",))
    build(("psc-index", "slice"))
    with pytest.raises(BuildError, match="run --step companies first"):
        build(("psc",))
    build(("companies",), keep_work=True)
    result = build(("psc",))  # keeps the company records its links point to
    assert {"gbch-co-99000010", "gbch-psc-SYNP1"} <= set(records())
    assert result.counts["psc"]["slice_companies"] == 1
    work = layout.work_dir("ch-test", DATASET)
    assert sorted(p.name for p in work.iterdir()) == ["slice.csv"]
    for name in ("uk-tiny", "uk-sample"):
        block = load_profile(name).options(DATASET).psc
        assert block is not None and block.enabled and block.parent_depth == 4


def test_unmapped_personal_fields_never_reach_records_index_or_summary(data_env: Any) -> None:
    from neonradar_cli.main import app

    profile(data_env, ["99000010"])
    sentinel = {
        "usual_residential_address": {"premises": "SENTINELHOME", "postal_code": "QQ9 9ZZ"},
        "date_of_birth": {"day": 17, "month": 3, "year": 1981},
        "name_elements": {"title": "SENTINELTITLE", "forename": "Zafer", "surname": "Velqasimi"},
    }
    download(
        [lines(person("99000010", "P1", ["voting-rights-25-to-50-percent"], **sentinel), totals(1))]
    )
    data_env.allow_real("ch-test")
    command = ["ingest", "build", "--profile", "ch-test", "--dataset", DATASET, "--keep-work"]
    result = CliRunner().invoke(app, command)
    assert result.exit_code == 0, result.output
    summary = next(layout.reports_dir("ch-test").glob("ingest-build-*.json")).read_text()
    work = layout.work_dir("ch-test", DATASET)
    folder = layout.records_dir("ch-test", DATASET)
    texts = [summary, result.output, *(p.read_text() for p in folder.iterdir())]
    texts += [p.read_bytes().decode("latin-1") for p in work.iterdir()]
    for text in texts:
        assert "SENTINEL" not in text and "QQ9" not in text and "1981-03-17" not in text
    for text in (summary, result.output):
        assert not re.search(r"Velqasimi|Zafer|SYNP1|99000010|BRACKEN", text)
    ch = json.loads(summary)["datasets"][DATASET]
    assert (ch["totals_check"], ch["snapshot_date"]) == ("passed", SNAPSHOT)
    assert records()["gbch-psc-SYNP1"]["properties"]["birthDate"] == ["1981-03"]
