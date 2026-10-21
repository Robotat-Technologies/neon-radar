"""Downloads (PHASE-2.md M2.2 deliverable 7): resume, checksums, skip, disk space, rotation.

The network is `httpx.MockTransport` with synthetic bodies; folders are a temporary tree.
"""

import hashlib
import json
import shutil
from collections.abc import Callable, Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest

from neonradar_ingest.data import download, layout
from neonradar_ingest.data.download import DownloadError, fetch
from neonradar_ingest.data.sources import RemoteFile, SourceSpec
from neonradar_ingest.http import HttpClient, RateLimiter

BODY = bytes(range(256)) * 40  # 10,240 synthetic bytes
URL = "https://files.example.test/list.xml?token=SYNTHETIC-SECRET"
Handler = Callable[[httpx.Request], httpx.Response]


class Cut(httpx.SyncByteStream):
    """A body that stops after `at` bytes, as a cut connection does."""

    def __init__(self, data: bytes, at: int) -> None:
        self.data, self.at = data, at

    def __iter__(self) -> Iterator[bytes]:
        yield self.data[: self.at]
        raise httpx.ReadError("connection reset")


class Server:
    """Answers with `replies` in turn and records each request."""

    def __init__(self, *replies: Handler) -> None:
        self.replies, self.requests = list(replies), []  # type: list[Handler], list[httpx.Request]

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.replies.pop(0)(request)

    def client(self) -> HttpClient:
        return HttpClient(
            "",
            follow_redirects=False,
            limiter=RateLimiter(1000),
            sleep=lambda _: None,
            transport=httpx.MockTransport(self),
        )


def spec(*files: RemoteFile, dataset: str = "us_ofac_sdn") -> SourceSpec:
    return SourceSpec(dataset, lambda client: list(files))


def remote(**changes: Any) -> RemoteFile:
    values = {"name": "list.xml", "url": URL, "version": "2026-10-18", "size": None}
    return RemoteFile(**(values | {"sha256": None} | changes))


def full(headers: dict[str, str] | None = None) -> Handler:
    return lambda request: httpx.Response(200, content=BODY, headers=headers or {})


def cut(at: int, headers: dict[str, str]) -> Handler:
    return lambda request: httpx.Response(200, stream=Cut(BODY, at), headers=headers)


def folder() -> Path:
    return layout.sources_dir("us_ofac_sdn", "main", "2026-10-18")


def no_sleep(seconds: float) -> None:
    pass


def test_a_download_lands_with_its_record(data_env: Any) -> None:
    digest = hashlib.sha256(BODY).hexdigest()
    server = Server(full({"ETag": '"v1"', "Last-Modified": "Sun, 18 Oct 2026 08:00:00 GMT"}))
    counts = fetch(spec(remote(size=len(BODY), sha256=digest.upper())), server.client())
    assert (folder() / "list.xml").read_bytes() == BODY
    assert sorted(p.name for p in folder().iterdir()) == ["download.json", "list.xml"]
    record = json.loads((folder() / "download.json").read_text(encoding="utf-8"))
    entry = record["files"][0]
    assert (record["complete"], entry["sha256"], entry["size"], entry["etag"]) == (
        True, digest, len(BODY), '"v1"',
    )  # fmt: skip
    assert entry["url"] == "https://files.example.test/list.xml"
    assert {"downloaded_at", "duration_s", "last_modified", "version", "product"} <= set(entry)
    assert counts["files_downloaded"] == 1
    assert counts["products"] == {"main": {"version": "2026-10-18", "files": 1}}


def test_query_strings_are_never_written(data_env: Any) -> None:
    counts = fetch(spec(remote()), Server(full()).client())
    for path in data_env.cache.rglob("*"):
        if path.is_file():
            text = path.read_bytes()
            assert b"SYNTHETIC-SECRET" not in text and b"token" not in text
    assert "SYNTHETIC-SECRET" not in json.dumps(counts)
    assert download.stored_url("https://u:p@x.test/a.zip?t=1#f") == "https://x.test/a.zip"


def test_resume_after_a_cut_connection_with_206(data_env: Any) -> None:
    ranges = {"Accept-Ranges": "bytes", "ETag": '"v1"'}

    def rest(request: httpx.Request) -> httpx.Response:
        assert request.headers["Range"] == "bytes=4000-"
        assert request.headers["If-Range"] == '"v1"'
        return httpx.Response(206, content=BODY[4000:])

    server = Server(cut(4000, ranges), rest)
    counts = fetch(spec(remote(size=len(BODY))), server.client(), sleep=no_sleep)
    assert (folder() / "list.xml").read_bytes() == BODY
    assert (counts["files_resumed"], counts["retries"], len(server.requests)) == (1, 1, 2)
    assert not list(folder().glob("*.part*"))


def test_a_reply_other_than_206_restarts_the_file(data_env: Any) -> None:
    server = Server(cut(4000, {"Accept-Ranges": "bytes"}), full())
    counts = fetch(spec(remote(size=len(BODY))), server.client(), sleep=no_sleep)
    assert server.requests[1].headers["Range"] == "bytes=4000-"
    assert (folder() / "list.xml").read_bytes() == BODY
    assert counts.get("files_resumed", 0) == 0


def test_without_accept_ranges_the_file_restarts_without_a_range(data_env: Any) -> None:
    server = Server(cut(4000, {}), full())
    fetch(spec(remote()), server.client(), sleep=no_sleep)
    assert "Range" not in server.requests[1].headers
    assert (folder() / "list.xml").read_bytes() == BODY


def test_a_connection_that_keeps_failing_keeps_the_partial_file(data_env: Any) -> None:
    server = Server(*[cut(1000, {"Accept-Ranges": "bytes"})] * 4)
    with pytest.raises(DownloadError, match="failed 4 times") as failed:
        fetch(spec(remote()), server.client(), sleep=no_sleep)
    assert failed.value.rule == "network"
    assert (folder() / "list.xml.part").stat().st_size == 1000
    assert not (folder() / "list.xml").exists()


@pytest.mark.parametrize(
    ("change", "rule"), [({"sha256": "0" * 64}, "sha256"), ({"size": len(BODY) + 1}, "size")]
)
def test_a_checksum_or_size_failure_keeps_nothing(
    data_env: Any, change: dict[str, Any], rule: str
) -> None:
    with pytest.raises(DownloadError) as failed:
        fetch(spec(remote(**change)), Server(full()).client())
    assert failed.value.rule == rule
    assert sorted(p.name for p in folder().iterdir()) == []


def test_an_http_error_stops_the_dataset(data_env: Any) -> None:
    server = Server(lambda request: httpx.Response(404))
    with pytest.raises(DownloadError, match=r"list\.xml: HTTP 404"):
        fetch(spec(remote()), server.client())
    server = Server(*[lambda request: httpx.Response(503)] * 4)
    with pytest.raises(DownloadError, match="HTTP 503 after retries"):
        fetch(spec(remote()), server.client())


def test_a_complete_version_is_skipped(data_env: Any) -> None:
    fetch(spec(remote()), Server(full()).client())
    server = Server()  # any request would fail: no replies left
    counts = fetch(spec(remote()), server.client())
    assert (server.requests, counts["files_skipped"]) == ([], 1)


def test_too_little_disk_space_refuses_before_any_request(
    data_env: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    usage = shutil.disk_usage(data_env.root)
    monkeypatch.setattr(shutil, "disk_usage", lambda path: usage._replace(free=3 * 10**9))
    server = Server(full())
    with pytest.raises(DownloadError, match=r"3\.0 GB free, 4\.0 GB needed") as refused:
        fetch(spec(remote(size=10**9)), server.client())  # twice the size plus 2 GB
    assert (refused.value.rule, server.requests) == ("disk", [])
    fetch(spec(remote()), server.client())  # unknown size: 2 GB is enough


def test_rotation_keeps_two_versions_per_product(data_env: Any) -> None:
    """Three daily PSC versions never delete the one monthly companies version."""
    companies = remote(name="companies.zip", version="2026-10-01", product="companies")
    fetch(spec(companies, dataset="gb_companies_house"), Server(full()).client())
    for day in ("2026-10-16", "2026-10-17", "2026-10-18"):
        psc = remote(name="psc.zip", version=day, product="psc")
        counts = fetch(spec(psc, dataset="gb_companies_house"), Server(full()).client())
    root = data_env.cache / "real/sources/gb_companies_house"
    assert sorted(p.name for p in (root / "psc").iterdir()) == ["2026-10-17", "2026-10-18"]
    assert [p.name for p in (root / "companies").iterdir()] == ["2026-10-01"]
    assert counts["versions_deleted"] == 1


def test_file_names_must_be_plain(data_env: Any) -> None:
    with pytest.raises(ValueError, match="file name"):
        fetch(spec(remote(name="../escape.xml")), Server(full()).client())
