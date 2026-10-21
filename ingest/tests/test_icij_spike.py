"""ICIJ spike, offline: a zip built in memory from synthetic rows (tests/fixtures/icij)."""

import io
import json
import re
import zipfile
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest

from neonradar_contracts.records import Manifest, manifest_path, validate_batch, validate_files
from neonradar_contracts.records import validate_record as check
from neonradar_ingest.http import HttpClient, HttpError, RateLimiter
from neonradar_ingest.sources.icij import mapping
from neonradar_ingest.sources.icij.archive import (
    ArchiveChangedError,
    RangeNotSupportedError,
    RangeReader,
    head,
    open_archive,
)
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


class BreakingStream(httpx.SyncByteStream):
    """A response body that breaks off halfway, like a dropped connection."""

    def __init__(self, data: bytes) -> None:
        self.data = data

    def __iter__(self) -> Iterator[bytes]:
        yield self.data[: len(self.data) // 2]
        raise httpx.ReadError("synthetic connection drop")


def server(
    body: bytes,
    ranges: str = "bytes",
    seen: list[httpx.Request] | None = None,
    breaks: int = 0,
    changes_after: int | None = None,
    shift: int = 0,
) -> HttpClient:
    """A mock archive host. `ranges`: "bytes" (206 answers), "none" (not advertised) or
    "refused" (advertised, but every range request gets 200). The first `breaks` range
    bodies break off halfway. After `changes_after` range answers the file is replaced (new
    ETag); `shift` makes every 206 start that many bytes early. A conditional GET with the
    right ETag gets 304."""
    etag, served = '"synthetic-1"', [0]

    def handle(request: httpx.Request) -> httpx.Response:
        if seen is not None:
            seen.append(request)
        headers = {"Content-Length": str(len(body)), "ETag": etag,
                   "Last-Modified": "Fri, 01 Jan 2099 00:00:00 GMT",
                   "Accept-Ranges": "none" if ranges == "none" else "bytes"}  # fmt: skip
        if request.method == "HEAD":
            return httpx.Response(200, headers=headers)
        if request.headers.get("If-None-Match") == etag:
            return httpx.Response(304, headers={"ETag": etag})
        match = re.fullmatch(r"bytes=(\d+)-", request.headers.get("Range", ""))
        if ranges == "bytes" and match:
            served[0] += 1
            start = max(0, int(match.group(1)) - shift)
            changed = changes_after is not None and served[0] > changes_after
            part = {"Content-Range": f"bytes {start}-{len(body) - 1}/{len(body)}",
                    "ETag": '"synthetic-2"' if changed else etag}  # fmt: skip
            if served[0] <= breaks:
                return httpx.Response(206, headers=part, stream=BreakingStream(body[start:]))
            return httpx.Response(206, headers=part, content=body[start:])
        return httpx.Response(200, content=body, headers=headers)

    transport = httpx.MockTransport(handle)
    limiter = RateLimiter(1000.0)
    return HttpClient("https://archive.test", follow_redirects=True, limiter=limiter,
                      transport=transport)  # fmt: skip


def test_slice_maps_to_the_expected_records_and_validates_strictly() -> None:
    piece = read_slice(zipfile.ZipFile(io.BytesIO(build_zip())), rows=3)
    records = piece.mapper.records()
    assert records == json.loads(EXPECTED.read_text(encoding="utf-8"))
    jurisdictions = {r["id"]: r["properties"].get("jurisdiction") for r in records}
    assert jurisdictions["icij-node-9900000001"] == ["ai"]  # ANG with "Anguilla", not Angola
    assert jurisdictions["icij-node-9900000002"] == ["pa"]  # the code when no description
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
        result = run_spike(client, url=URL, rows=3, out_root=tmp_path)
    assert result.mode == "range"
    gets = [r for r in seen if r.method == "GET"]
    assert all(r.headers["If-Range"] == '"synthetic-1"' and "Range" in r.headers for r in gets)
    assert result.output.parent == tmp_path / "icij"
    assert sorted(p.name for p in result.output.parent.iterdir()) == [
        result.output.name,
        manifest_path(result.output).name,
    ]  # no archive copy, no download folder
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


def test_a_broken_range_body_resumes_from_the_same_byte(
    caplog: pytest.LogCaptureFixture, tmp_path: Path
) -> None:
    seen: list[httpx.Request] = []
    with server(build_zip(), seen=seen, breaks=3) as client:
        zf, _, mode, reader = open_archive(client, URL, tmp_path)
        records = read_slice(zf, rows=3).mapper.records()
    assert mode == "range" and reader is not None
    assert records == json.loads(EXPECTED.read_text(encoding="utf-8"))
    assert reader.requests == len([r for r in seen if r.method == "GET"])
    assert caplog.text.count("resuming") == 3


def test_a_body_that_keeps_breaking_raises_http_error(tmp_path: Path) -> None:
    with server(build_zip(), breaks=99) as client, pytest.raises(HttpError, match="broke off"):
        open_archive(client, URL, tmp_path)


@pytest.mark.parametrize(
    ("options", "match"),
    [({"changes_after": 2}, "ETag"), ({"shift": 7}, "Content-Range")],
    ids=["file-replaced", "wrong-range"],
)
def test_an_answer_from_another_file_or_range_fails(
    tmp_path: Path, options: dict[str, int], match: str
) -> None:
    with server(build_zip(), **options) as client, pytest.raises(ArchiveChangedError, match=match):
        zf, *_ = open_archive(client, URL, tmp_path)
        read_slice(zf, rows=3)


def test_a_200_answer_to_a_range_request_is_never_read() -> None:
    body = build_zip()
    with server(body, ranges="refused") as client:
        reader = RangeReader(client, head(client, URL))
        with pytest.raises(RangeNotSupportedError, match="answered 200"):
            reader.read(10)
    assert (reader.requests, reader.bytes_received) == (1, 0)


def test_missing_columns_fail_with_their_names() -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(build_zip())) as source, zipfile.ZipFile(buffer, "w") as zf:
        for name in source.namelist():
            text = source.read(name).decode("utf-8")
            zf.writestr(name, text.replace(",link,", ",role,", 1))
    with pytest.raises(ValueError, match=r"relationships\.csv lacks the column\(s\) link"):
        read_slice(zipfile.ZipFile(buffer), rows=3)


@pytest.mark.parametrize("ranges", ["none", "refused"])
def test_without_ranges_downloads_once_then_revalidates(tmp_path: Path, ranges: str) -> None:
    body, seen = build_zip(), list[httpx.Request]()
    with server(body, ranges=ranges, seen=seen) as client:
        zf, _, mode, reader = open_archive(client, URL, tmp_path)
        assert (mode, reader, zf.namelist()[0]) == ("download", None, "GENERATED_ON_20990101.txt")
        cached = tmp_path / "full-oldb.LATEST.zip"
        assert cached.read_bytes() == body
        headers = json.loads((tmp_path / "full-oldb.LATEST.zip.headers.json").read_text())
        assert headers == {"If-None-Match": '"synthetic-1"',
                           "If-Modified-Since": "Fri, 01 Jan 2099 00:00:00 GMT"}  # fmt: skip
        seen.clear()
        zf2, _, mode2, _ = open_archive(client, URL, tmp_path)
    assert mode2 == "download" and zf2.namelist() == zf.namelist()
    assert seen[-1].headers["If-None-Match"] == '"synthetic-1"'  # answered 304: file reused
