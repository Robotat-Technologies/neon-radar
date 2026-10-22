"""The ICIJ loader (PHASE-2.md M2.5 deliverables 1 and 3 to 6) on an in-memory zip.

Synthetic rows with ICIJ's published column layout (docs/data/spikes/icij.md 2): invented node
ids (ten digits starting with 99), invented names, `QQ` postcodes. The network is an
`httpx.MockTransport`; folders are the `data_env` temporary tree.
"""

import csv
import hashlib
import io
import json
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest
import yaml

from neonradar_contracts.records import Manifest, manifest_path, validate_files
from neonradar_ingest.data import layout, sources
from neonradar_ingest.data.build import build_dataset
from neonradar_ingest.data.download import fetch
from neonradar_ingest.data.profiles import load_profile
from neonradar_ingest.data.project import REPO_ROOT, load_project
from neonradar_ingest.data.sources import BuildContext, BuildError, BuildResult
from neonradar_ingest.http import HttpClient, HttpError, RateLimiter
from neonradar_ingest.sources.icij import full
from neonradar_ingest.sources.icij.archive import ARCHIVE_FILE, ARCHIVE_URL

HEADERS = {
    "nodes-entities.csv": "node_id,name,original_name,former_name,jurisdiction,"
    "jurisdiction_description,company_type,address,internal_id,incorporation_date,"
    "inactivation_date,struck_off_date,dorm_date,status,service_provider,ibcRUC,country_codes,"
    "countries,sourceID,valid_until,note",
    "nodes-officers.csv": "node_id,name,countries,country_codes,sourceID,valid_until,note",
    "nodes-intermediaries.csv": "node_id,name,status,internal_id,address,countries,"
    "country_codes,sourceID,valid_until,note",
    "nodes-others.csv": "node_id,name,type,incorporation_date,struck_off_date,closed_date,"
    "jurisdiction,jurisdiction_description,countries,country_codes,sourceID,valid_until,note",
    "nodes-addresses.csv": "node_id,address,name,countries,country_codes,sourceID,valid_until,note",
    "relationships.csv": "node_id_start,node_id_end,rel_type,link,status,start_date,end_date,"
    "sourceID",
}
NOTE = "SYNTHETIC NOTE THAT MUST NEVER BE LOADED"
SOURCE = "Synthetic Papers"
A1, A2 = "9910000001", "9910000002"
E1, E2, E3 = "9920000001", "9920000002", "9920000003"
O1, O2, O5 = "9930000001", "9930000002", "9930000005"
I1, X1 = "9940000001", "9950000001"
TRUST = ("settlor", "founder", "beneficiary of", "grantor", "protector of")
ROWS: dict[str, list[dict[str, str]]] = {
    "nodes-entities.csv": [
        {"node_id": E1, "name": "Synthetic Entity One Ltd", "original_name":
         "Synthetic Entity Four Corp", "former_name": "Synthetic Entity One Former Ltd",
         "jurisdiction": "XYZ",
         "jurisdiction_description": "British Virgin Islands", "company_type": "SYN TYPE",
         "address": "SYN ADDRESS TEXT", "internal_id": "SYN-1", "incorporation_date":
         "22-MAY-2006", "struck_off_date": "01-JAN-99", "closed_date": "02-FEB-2003",
         "status": "Defaulted", "ibcRUC": "SYN-IBC", "country_codes": "GBR;VGB",
         "sourceID": SOURCE, "valid_until": "SYN VALID", "note": NOTE},
        {"node_id": E2, "name": "Synthetic Entity Two S.A.", "original_name":
         "Synthetic Entity Two S.A.", "incorporation_date": "13/04/2010",
         "inactivation_date": "21-AUG-0200",
         "struck_off_date": "2011-03-04", "sourceID": SOURCE, "note": NOTE},
        {"node_id": E3, "name": "? ?"},  # junk name: skipped
    ],
    "nodes-officers.csv": [
        {"node_id": O1, "name": "Synthetic Officer Alpha", "country_codes": "GBR",
         "sourceID": SOURCE, "note": NOTE},
        {"node_id": O2, "name": "Synthetic Officer Beta", "sourceID": SOURCE},
        {"node_id": O5, "name": "Synthetic Nominee Officer Ltd"},
        {"node_id": I1, "name": "Synthetic Agent Services Ltd"},  # also an intermediary
    ],
    "nodes-intermediaries.csv": [
        {"node_id": I1, "name": "Synthetic Agent Services Ltd", "status": "ACTIVE", "country_codes":
         "VGB", "address": "SYN ADDRESS TEXT", "note": NOTE},
    ],
    "nodes-others.csv": [
        {"node_id": X1, "name": "Synthetic Foundation Gamma", "type": "SYN TYPE",
         "incorporation_date":
         "2001-02-03", "closed_date": "31-DEC-2010", "jurisdiction_description": "Anguilla",
         "country_codes": "AIA", "note": NOTE},
    ],
    "nodes-addresses.csv": [
        {"node_id": A1, "address": "1 Synthetic Row, Testford QQ1 1AA", "name": "SYN NAME",
         "country_codes": "GBR", "note": NOTE},
        {"node_id": A2, "address": "2 Example Lane, Testford QQ2 2BB", "country_codes": "GBR"},
    ],
}  # fmt: skip


def rel(start: str, end: str, rel_type: str, link: str, **extra: str) -> dict[str, str]:
    return {"node_id_start": start, "node_id_end": end, "rel_type": rel_type, "link": link,
            "sourceID": SOURCE, **extra}  # fmt: skip


ROWS["relationships.csv"] = [
    rel(E1, A1, "registered_address", "registered address"),
    rel(O1, A1, "registered_address", "residential address"),
    rel(O1, A2, "registered_address", "mailing address"),
    rel(
        O2,
        E1,
        "officer_of",
        "Shareholder of",
        start_date="22-MAY-2006",
        end_date="13/04/2010",
        status="resigned",
    ),
    rel(
        O2,
        E1,
        "officer_of",
        "Shareholder of",
        start_date="22-MAY-2006",
        end_date="13/04/2010",
        status="resigned",
    ),  # an exact duplicate row
    rel(O2, E1, "officer_of", "Shareholder of", start_date="01-JUN-2012"),  # re-appointed
    rel(O5, E1, "officer_of", "nominee shareholder of"),
    rel(O5, E2, "officer_of", "nominee director of"),
    rel(O1, E1, "officer_of", "director of"),
    rel(O1, X1, "officer_of", "director of"),  # X1 is no Organization
    *(rel(O5, X1, "officer_of", link) for link in TRUST),
    rel(O2, E2, "officer_of", "synthetic custom role of"),
    rel(I1, E1, "intermediary_of", "registered agent of"),
    rel(I1, O2, "underlying", "underlying"),
    rel(E1, E2, "connected_to", "connected to"),
    rel(E1, E3, "officer_of", "director of"),  # E3 has no usable name
    rel(O1, O2, "same_name_as", "same name as"),
    rel(O1, O2, "same_name_as", "same name as"),  # repeated
    rel(E1, E2, "similar_company_as", "similar company as"),
    rel(A1, A2, "same_address_as", "same address as"),
    rel(E1, A1, "similar", "similar name and address as"),
    rel(E1, E3, "same_as", "same as"),  # E3 is outside
]


def zip_body(rows: dict[str, list[dict[str, str]]], drop: tuple[str, ...] = ()) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("GENERATED_ON_20990101.txt", "")
        for member, header in HEADERS.items():
            text = io.StringIO()
            columns = [c for c in header.split(",") if c not in drop]
            writer = csv.DictWriter(text, columns, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows.get(member, []))
            zf.writestr(member, text.getvalue())
    return buffer.getvalue()


def install(body: bytes, version: str = "2099-01-01") -> Path:
    folder = layout.sources_dir("icij_offshore_leaks", "main", version)
    folder.mkdir(parents=True)
    (folder / ARCHIVE_FILE).write_bytes(body)
    entry = {"name": ARCHIVE_FILE, "url": ARCHIVE_URL, "version": version, "size": len(body),
             "sha256": hashlib.sha256(body).hexdigest(), "etag": '"syn-1"',
             "last_modified": "Thu, 01 Jan 2099 00:00:00 GMT",
             "downloaded_at": "2099-01-01T00:00:00Z"}  # fmt: skip
    record = {"files": [entry], "complete": True, "completed_at": f"{version}T00:00:00Z"}
    (folder / "download.json").write_text(json.dumps(record), encoding="utf-8")
    return folder


def companies_house() -> dict[str, Any]:
    text = (REPO_ROOT / "ingest" / "profiles" / "uk-sample.yaml").read_text(encoding="utf-8")
    block: dict[str, Any] = yaml.safe_load(text)["sources"]["gb_companies_house"]
    block["companies"]["postcode_districts"] = ["QQ1"]
    return block


def profile(data_env: Any, mode: str = "full", **block: Any) -> Any:
    icij = {"enabled": True, "mode": mode, "max_nodes": 100, "sample_seed": 7, **block}
    sources = {"gb_companies_house": companies_house(), "icij_offshore_leaks": icij}
    data_env.write_profile("icij-test", real_data=True, sources=sources)
    return load_profile("icij-test")


def run(data_env: Any, mode: str = "full", **block: Any) -> tuple[BuildResult, Path]:
    out = data_env.root / "out"
    out.mkdir(exist_ok=True)
    context = BuildContext(load_project(), "build-test", out, data_env.root / "work")
    result = full.build(profile(data_env, mode, **block), context, today=date(2026, 10, 22))
    return result, out


def records(out: Path) -> dict[str, dict[str, Any]]:
    lines = (out / "icij_offshore_leaks-20261022-records.ftm.jsonl").read_text(encoding="utf-8")
    return {r["id"]: r for r in map(json.loads, lines.splitlines())}


def hints(out: Path) -> list[list[str]]:
    text = (out / "icij_offshore_leaks-20261022-hints.csv").read_text(encoding="utf-8")
    return list(csv.reader(text.splitlines()))


def rid(node: str) -> str:
    return f"icij-node-{node}"


def links(found: dict[str, dict[str, Any]], schema: str) -> list[dict[str, Any]]:
    return [r for r in found.values() if r["schema"] == schema]


def test_nodes_map_to_the_c1_table_and_note_is_never_read(data_env: Any) -> None:
    install(zip_body(ROWS))
    result, out = run(data_env)
    found = records(out)
    assert NOTE not in (out / "icij_offshore_leaks-20261022-records.ftm.jsonl").read_text()
    assert "SYN" not in json.dumps(found)  # type, address text, ibcRUC, internal_id, valid_until
    e1 = found[rid(E1)]
    assert (e1["schema"], e1["datasets"]) == ("Company", ["icij_offshore_leaks"])
    assert e1["properties"] == {
        "name": ["Synthetic Entity One Ltd"],
        "alias": ["Synthetic Entity Four Corp"],
        "previousName": ["Synthetic Entity One Former Ltd"],
        "jurisdiction": ["vg"],  # from the description, never the code column
        "country": ["gb", "vg"],
        "incorporationDate": ["2006-05-22"],
        "dissolutionDate": ["1999-01-01"],  # struck_off_date first: inactivation_date is empty
        "status": ["Defaulted"],
        "publisher": [SOURCE],
        "sourceUrl": [f"https://offshoreleaks.icij.org/nodes/{E1}"],
        "icijId": [E1],
        "addressEntity": [rid(A1)],
    }
    assert e1["nr"] == {"v": "1.1", "source_ref": E1, "address_roles": {rid(A1): "registered"}}
    e2 = found[rid(E2)]["properties"]
    assert "alias" not in e2 and "incorporationDate" not in e2  # same name; slash date dropped
    assert e2["dissolutionDate"] == ["2011-03-04"]  # 0200 dropped, then the ISO struck-off date
    x1 = found[rid(X1)]
    assert x1["schema"] == "LegalEntity"
    assert {k: x1["properties"][k] for k in ("jurisdiction", "country", "incorporationDate",
            "dissolutionDate")} == {"jurisdiction": ["ai"], "country": ["ai"],
            "incorporationDate": ["2001-02-03"], "dissolutionDate": ["2010-12-31"]}  # fmt: skip
    o1 = found[rid(O1)]
    assert (o1["schema"], o1["properties"]["country"]) == ("LegalEntity", ["gb"])
    assert o1["nr"]["address_roles"] == {rid(A1): "residential", rid(A2): "unknown"}
    i1 = found[rid(I1)]  # officer and intermediary rows merged into one record
    assert (i1["schema"], i1["properties"]["status"]) == ("LegalEntity", ["ACTIVE"])
    a1 = found[rid(A1)]
    assert a1["schema"] == "Address" and a1["nr"] == {"v": "1.1", "source_ref": A1}
    assert a1["properties"]["full"] == ["1 Synthetic Row, Testford QQ1 1AA"]
    assert a1["properties"]["country"] == ["gb"] and "icijId" not in a1["properties"]
    assert rid(E3) not in found  # a junk name leaves no name: skipped
    counts = result.counts
    assert counts["records_by_schema"] == {"address": 2, "company": 2, "directorship": 2,
        "legalentity": 5, "ownership": 3, "representation": 1, "unknownlink": 9}  # fmt: skip
    assert counts["skipped"]["nodes_without_a_usable_name"] == 1
    assert counts["nodes_merged_across_files"] == 1
    assert counts["dates"] == {"parsed": 7, "two_digit_year": 1, "dropped": 3}


def test_relationships_map_to_their_classes(data_env: Any) -> None:
    install(zip_body(ROWS))
    result, out = run(data_env)
    found = records(out)
    owners = links(found, "Ownership")
    assert len(owners) == 3  # the exact duplicate is skipped; the re-appointment is kept
    resigned = next(r for r in owners if r["properties"].get("endDate") is None
                    and r["properties"].get("status") == ["resigned"])  # fmt: skip
    assert resigned["properties"] == {"owner": [rid(O2)], "asset": [rid(E1)],
        "role": ["Shareholder of"], "status": ["resigned"], "publisher": [SOURCE],
        "startDate": ["2006-05-22"]}  # fmt: skip
    assert resigned["id"].startswith("icij-ownership-") and len(resigned["id"]) == 35
    nominee = next(r for r in owners if r["properties"]["role"] == ["nominee shareholder of"])
    assert nominee["nr"] == {"v": "1.1", "is_nominee": True}
    directors = {r["properties"]["role"][0]: r for r in links(found, "Directorship")}
    assert directors["nominee director of"]["nr"] == {"v": "1.1", "is_nominee": True}
    assert "nr" not in directors["director of"]
    agent = links(found, "Representation")[0]["properties"]
    assert (agent["agent"], agent["client"], agent["role"]) == (
        [rid(I1)],
        [rid(E1)],
        ["intermediary"],
    )
    unknown = {r["properties"]["role"][0] for r in links(found, "UnknownLink")}
    assert unknown == {*TRUST, "director of", "synthetic custom role of", "underlying",
                       "connected_to"}  # fmt: skip
    assert result.counts["unknown_links_by_value"] == {"synthetic custom role of": 1}
    assert result.counts["links_by_class"] == {"address": 3, "directorship": 2, "nominee": 2,
        "ownership": 3, "representation": 1, "unknownlink": 9}  # fmt: skip
    skipped = result.counts["skipped"]
    assert skipped["duplicate_relationship_rows"] == 1
    assert skipped["relationships_with_an_end_outside_the_slice"] == 1  # E1 -> E3


def test_hints_are_written_never_loaded_and_address_hints_dropped(data_env: Any) -> None:
    install(zip_body(ROWS))
    result, out = run(data_env)
    assert hints(out) == [
        ["record_a", "record_b", "hint"],
        [rid(O1), rid(O2), "same_name_as"],
        [rid(E1), rid(E2), "similar_company_as"],
    ]
    assert not any("same" in r["id"] or "similar" in r["id"] for r in records(out).values())
    counts = result.counts
    assert (counts["hints_written"], counts["hints_repeated"]) == (2, 1)
    assert (counts["address_hints_dropped"], counts["hints_outside_slice"]) == (2, 1)


def test_district_linked_slice_drops_relationships_with_their_ends(data_env: Any) -> None:
    install(zip_body(ROWS))
    result, out = run(data_env, "district-linked", max_nodes=3)
    found = records(out)
    # Level 0: A1 (QQ1); level 1: E1 and O1; level 2 (O2, O5, I1) does not fit under the cap.
    nodes = {k for k, r in found.items() if r["schema"] in ("Address", "Company", "LegalEntity")}
    assert nodes == {rid(A1), rid(E1), rid(O1)}
    assert result.counts["nodes_by_level"] == {"level_0": 1, "level_1": 2, "level_2": 3}
    assert result.counts["nodes_dropped_by_cap"] == 3
    assert result.counts["skipped"]["relationships_dropped_with_nodes_over_the_cap"] == 6
    assert found[rid(O1)]["nr"]["address_roles"] == {rid(A1): "residential"}  # A2 not kept
    assert [r["properties"]["role"] for r in links(found, "Directorship")] == [["director of"]]
    assert result.strings["mode"] == "district-linked"


def test_the_build_validates_in_strict_mode_with_its_manifest(data_env: Any) -> None:
    install(zip_body(ROWS))
    builder = sources.builder_for("icij_offshore_leaks")
    assert builder is not None

    def strict(paths: list[Path]) -> int:
        return len(validate_files(paths, strict=True)[1])

    project, chosen = load_project(), profile(data_env)
    build_dataset(builder, chosen, project, strict, run_id="build-1")
    folder = layout.records_dir(chosen, "icij_offshore_leaks")
    record_file = next(folder.glob("*.ftm.jsonl"))
    counts, issues = validate_files([record_file], strict=True)
    assert issues == [] and counts.total() == 24
    manifest = Manifest.model_validate_json(manifest_path(record_file).read_text())
    assert (manifest.record_contract, manifest.licence.id) == ("1.1.0", "ODbL-1.0")
    assert manifest.source.source_version == "2099-01-01"
    assert manifest.source.urls == [ARCHIVE_URL]
    assert "There are legitimate uses for offshore companies and trusts." in manifest.notes
    assert manifest.counts.skipped["nodes without a usable name"] == 1


def test_headers_are_matched_by_name_required_ones_stop_the_build(data_env: Any) -> None:
    install(zip_body(ROWS, drop=("closed_date", "status")))
    result, _ = run(data_env)
    assert "nodes-entities.csv:closed_date" in result.lists["columns_absent"]
    assert "relationships.csv:status" in result.lists["columns_absent"]
    assert result.counts["columns_extra"]["nodes-entities.csv"] == 10
    for column in ("name", "link"):
        layout_dir = layout.sources_dir("icij_offshore_leaks", "main", "2099-01-01")
        for path in layout_dir.iterdir():
            path.unlink()
        layout_dir.rmdir()
        install(zip_body(ROWS, drop=(column,)))
        with pytest.raises(BuildError, match=f"has no column {column}") as stopped:
            run(data_env)
        assert stopped.value.counts_only


def test_a_build_without_a_download_stops(data_env: Any) -> None:
    with pytest.raises(BuildError, match="no complete download"):
        run(data_env)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("22-MAY-2006", "2006-05-22"), ("22-may-06", "2006-05-22"), ("22-MAY-26", "2026-05-22"),
     ("22-MAY-27", "1927-05-22"), ("2001-02-03", "2001-02-03"), ("21-AUG-0200", None),
     ("31-FEB-2010", None), ("13/04/2010", None), ("*", None), ("", None)],
)  # fmt: skip
def test_dates(raw: str, expected: str | None) -> None:
    assert full.Dates(date(2026, 10, 22)).parse(raw) == expected


def test_junk_names_and_summary_values() -> None:
    assert [full.clean(v) for v in ("???", " ? ? ", "A?", None)] == ["", "", "A?", ""]
    assert full.summary_value("Mailing Address; Residential") == "mailing address_ residential"
    assert full.summary_value(";;") == "empty"


LINKS = [
    ("shareholder of", "Ownership", False), ("Ultimate Beneficial Owner", "Ownership", False),
    ("beneficial owner", "Ownership", False), ("owner of", "Ownership", False),
    ("partner of", "Ownership", False), ("nominee shareholder", "Ownership", True),
    ("nominee shareholder of", "Ownership", True), ("director of", "Directorship", False),
    ("secretary of", "Directorship", False), ("president", "Directorship", False),
    ("treasurer", "Directorship", False), ("is signatory for", "Directorship", False),
    ("power of attorney of", "Directorship", False), ("nominee director of", "Directorship", True),
    ("settlor", "UnknownLink", False), ("founder", "UnknownLink", False),
    ("beneficiary of", "UnknownLink", False), ("grantor", "UnknownLink", False),
    ("protector of", "UnknownLink", False), ("trustee of trust of", "UnknownLink", False),
    ("auditor of", "UnknownLink", False), ("records & registers of", "UnknownLink", False),
    ("an unknown synthetic role", "UnknownLink", False),
]  # fmt: skip


def test_every_link_value_maps_to_its_schema() -> None:
    for link, schema, nominee in LINKS:
        assert full.classify("officer_of", f"  {link} ") == (schema, nominee), link
    assert full.classify("intermediary_of", "registered agent of") == ("Representation", False)
    assert full.classify("registered_address", "registered office") == ("address", False)
    assert full.classify("underlying", "") == ("UnknownLink", False)


def client(handler: Any) -> HttpClient:
    transport = httpx.MockTransport(handler)
    return HttpClient("", follow_redirects=True, limiter=RateLimiter(1000), transport=transport)


def test_discover_takes_the_version_from_last_modified_and_asks_conditionally(
    data_env: Any,
) -> None:
    seen: list[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.headers.get("If-None-Match") == '"syn-1"':
            return httpx.Response(304)
        headers = {"Last-Modified": "Wed, 09 Sep 2099 10:55:34 GMT", "Content-Length": "7"}
        return httpx.Response(200, headers=headers)

    assert full.discover(client(answer))[0].version == "2099-09-09"
    assert seen[0].method == "HEAD" and "If-None-Match" not in seen[0].headers
    install(zip_body(ROWS))
    again = full.discover(client(answer))
    assert (again[0].version, again[0].name) == ("2099-01-01", ARCHIVE_FILE)
    assert seen[1].headers["If-Modified-Since"] == "Thu, 01 Jan 2099 00:00:00 GMT"
    spec = sources.source_spec("icij_offshore_leaks")
    assert spec is not None and fetch(spec, client(answer))["files_skipped"] == 1
    with pytest.raises(HttpError, match="HTTP 404"):
        full.discover(client(lambda request: httpx.Response(404)))


def test_unreadable_members_stop_the_build_without_quoting_a_value(data_env: Any) -> None:
    body = io.BytesIO()
    with (
        zipfile.ZipFile(io.BytesIO(zip_body(ROWS))) as source,
        zipfile.ZipFile(body, "w") as target,
    ):
        for name in source.namelist():
            data = source.read(name)
            if name == "nodes-officers.csv":
                data += b"9930000009,Synthetic \xff Officer\n"  # not UTF-8
            if name != "nodes-others.csv":
                target.writestr(name, data)
    install(body.getvalue())
    with pytest.raises(BuildError) as stopped:
        run(data_env)
    assert stopped.value.counts_only and "Synthetic" not in str(stopped.value)
    assert str(stopped.value) in (
        "nodes-officers.csv is not a readable UTF-8 CSV file (UnicodeDecodeError)",
        "the archive has no nodes-others.csv",
    )


def test_committed_profiles_never_use_full_mode() -> None:
    for path in (REPO_ROOT / "ingest" / "profiles").glob("*.yaml"):
        block = yaml.safe_load(path.read_text(encoding="utf-8"))["sources"].get(
            "icij_offshore_leaks", {}
        )
        assert block.get("mode") != "full", path.name


def test_the_link_table_is_lower_case_and_each_value_appears_once() -> None:
    table = full.link_table()
    assert all(value == full.link_key(value) for value in table)
    assert table["person of significant control"] == ("UnknownLink", False)
