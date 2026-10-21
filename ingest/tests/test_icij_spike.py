"""ICIJ spike, offline: a zip built in memory from synthetic rows (tests/fixtures/icij)."""

import io
import json
import re
import zipfile
from collections.abc import Callable
from pathlib import Path

import httpx
import pytest

from neonradar_contracts.records import Manifest, manifest_path, validate_batch, validate_files
from neonradar_contracts.records import validate_record as check
from neonradar_ingest.sources.icij import mapping
from neonradar_ingest.sources.icij.archive import open_archive
from neonradar_ingest.sources.icij.spike import read_slice, run_spike, summary_lines

FIXTURES = Path(__file__).parent / "fixtures" / "icij"
EXPECTED = FIXTURES / "slice.expected.json"
URL = "https://archive.test/offshoreleaks/csv/full-oldb.LATEST.zip"
NAMES = ("Synthetic Entity One Ltd", "Synthetic Officer Alpha", "Sample Lane")


def build_zip() -> bytes:
    """The fixture CSVs without their `# synthetic: true` line, as ICIJ ships them."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("GENERATED_ON_20990101.txt", "")
        for path in sorted(FIXTURES.glob("*.csv")):
            zf.writestr(path.name, path.read_text(encoding="utf-8").split("\n", 1)[1])
    return buffer.getvalue()


def server(
    body: bytes, ranges: bool = True, seen: list[httpx.Request] | None = None
) -> httpx.Client:
    """A mock host for the archive: HEAD, range GETs (206) and conditional GETs (304)."""
    etag = '"synthetic-1"'

    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        headers = {"Content-Length": str(len(body)), "ETag": etag,
                   "Last-Modified": "Fri, 01 Jan 2099 00:00:00 GMT"}  # fmt: skip
        if ranges:
            headers["Accept-Ranges"] = "bytes"
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304, headers={"ETag": etag})
        match = re.fullmatch(r"bytes=(\d+)-", request.headers.get("Range", ""))
        if ranges and match:
            start = int(match.group(1))
            return httpx.Response(206, content=body[start:], headers={"ETag": etag})
        return httpx.Response(200, content=body, headers={**headers, "Accept-Ranges": "none"})

    return httpx.Client(transport=httpx.MockTransport(handle))


def test_slice_maps_to_the_expected_records_and_validates_strictly() -> None:
    piece = read_slice(zipfile.ZipFile(io.BytesIO(build_zip())), rows=3)
    records = piece.mapper.records()
    assert records == json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert [issue for record in records for issue in check(record)] == []
    assert validate_batch(records, strict=True) == []


def test_slice_counts_files_links_and_skips() -> None:
    piece = read_slice(zipfile.ZipFile(io.BytesIO(build_zip())), rows=3)
    assert piece.generated_on == "20990101"
    entities, relationships = piece.files["nodes-entities.csv"], piece.files["relationships.csv"]
    assert (entities.rows, entities.complete) == (3, False)
    assert (relationships.rows, relationships.complete, relationships.source_ids[""]) == (
        19,
        True,
        3,
    )
    assert piece.files["nodes-officers.csv"].header[:2] == ["node_id", "name"]
    assert piece.links[("officer_of", "shareholder of")] == 3
    assert piece.mapper.skipped == {
        mapping.SKIP_DUPLICATE: 1,
        mapping.SKIP_HINT: 1,
        mapping.SKIP_NO_NAME: 2,
        mapping.SKIP_OUTSIDE: 3,
    }
    assert piece.mapper.dates == {"seen": 11, "kept": 8}
    assert piece.mapper.date_misses == {"99-AAA-9999": 2, "99/99/9999": 1}


@pytest.mark.parametrize(
    ("rel_type", "link", "expected"),
    [
        ("officer_of", "Shareholder of", "Ownership"),
        ("officer_of", "nominee shareholder of", "Ownership"),
        ("officer_of", "Ultimate Beneficial Owner", "Ownership"),
        ("officer_of", "Nominee Director of", "Directorship"),
        ("officer_of", "Authorised Person / Signatory of", "Directorship"),
        ("officer_of", "auditor of", "UnknownLink"),
        ("intermediary_of", "intermediary of", "Representation"),
        ("registered_address", "registered address", "address"),
        ("same_as", "same name and registration date as", None),
        ("similar", "similar name and address as", None),
        ("probably_same_officer_as", "probably same officer as", None),
        ("underlying", "underlying", "UnknownLink"),
    ],
)
def test_classify_link(rel_type: str, link: str, expected: str | None) -> None:
    assert mapping.classify_link(rel_type, link) == expected


def test_question_mark_names_become_empty() -> None:
    assert mapping.clean(" ??? ") == ""
    assert mapping.clean("A?B") == "A?B"


def test_run_spike_reads_ranges_and_writes_a_valid_load(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    with server(build_zip(), seen=seen) as client:
        result = run_spike(client, url=URL, rows=3, out_dir=tmp_path / "out", cache_dir=tmp_path)
    assert result.mode == "range"
    assert all("Range" in r.headers for r in seen if r.method == "GET")
    assert not (tmp_path / "full-oldb.LATEST.zip").exists()
    counts, issues = validate_files([result.output], strict=True)
    assert issues == []
    assert counts.total() == 16
    manifest = Manifest.model_validate_json(manifest_path(result.output).read_text())
    assert manifest.dataset == "icij_offshore_leaks"
    assert manifest.source.source_version == "20990101"
    assert manifest.counts.skipped[mapping.SKIP_OUTSIDE] == 3
    text = "\n".join(summary_lines(result))
    assert "Accept-Ranges bytes" in text
    assert "officer_of | shareholder of -> Ownership" in text
    assert not any(name in text for name in NAMES)


@pytest.mark.parametrize(
    "make_client",
    [
        lambda body: server(body, ranges=False),
        lambda body: server_refusing_ranges(body),
    ],
    ids=["no-ranges", "ranges-refused"],
)
def test_without_ranges_downloads_once_then_revalidates(
    tmp_path: Path, make_client: Callable[[bytes], httpx.Client]
) -> None:
    body = build_zip()
    with make_client(body) as client:
        zf, _, mode, reader = open_archive(client, URL, tmp_path)
        assert (mode, reader, zf.namelist()[0]) == ("download", None, "GENERATED_ON_20990101.txt")
        cached = tmp_path / "full-oldb.LATEST.zip"
        assert cached.read_bytes() == body
        headers = json.loads((tmp_path / "full-oldb.LATEST.zip.headers.json").read_text())
        assert headers["If-None-Match"] == '"synthetic-1"'
        cached.write_bytes(body)  # a 304 must reuse this file, not rewrite it
        zf2, _, mode2, _ = open_archive(client, URL, tmp_path)
        assert mode2 == "download" and zf2.namelist() == zf.namelist()


def server_refusing_ranges(body: bytes) -> httpx.Client:
    """Advertises byte ranges but answers every range request with 200 and the whole body."""

    def handle(request: httpx.Request) -> httpx.Response:
        headers = {
            "Content-Length": str(len(body)),
            "Accept-Ranges": "bytes",
            "ETag": '"synthetic-1"',
        }
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        if request.headers.get("If-None-Match") == '"synthetic-1"':
            return httpx.Response(304)
        return httpx.Response(200, content=body, headers=headers)

    return httpx.Client(transport=httpx.MockTransport(handle))
