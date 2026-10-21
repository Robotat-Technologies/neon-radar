"""Open ICIJ's bulk zip without downloading it, when the server allows (M1.8c steps 2 and 3).

`open_archive` sends a HEAD request first. With `Accept-Ranges: bytes`, `RangeReader` gives
`zipfile` a seekable view of the remote file: it reads the central directory from the tail
and streams each member with one open-ended range request. Every range request carries
`If-Range`, and every answer must be the asked-for range of the same file, so a file replaced
during the read fails instead of mixing two versions. Otherwise the archive is downloaded
once into the cache directory and reused with `If-None-Match` and `If-Modified-Since`.
"""

import io
import json
import logging
import zipfile
from collections.abc import Buffer, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import httpx

from neonradar_ingest.http import HttpClient, HttpError, redact

log = logging.getLogger(__name__)
ARCHIVE_URL = "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"
ARCHIVE_FILE = "full-oldb.LATEST.zip"  # the cached copy's name, never taken from the URL
CHUNK = 1 << 16
RESUMES = 5  # per archive read: HttpClient retries opening a request, not reading its body


class RangeNotSupportedError(HttpError):
    """The first range request was answered with something other than 206. An HttpError, not
    an OSError, which zipfile would turn into BadZipFile."""


class ArchiveChangedError(HttpError):
    """A range answer came from another version of the file, or for another range."""


@dataclass(frozen=True, slots=True)
class ArchiveInfo:
    """The HEAD response facts the spike report needs."""

    url: str
    size: int | None
    last_modified: str | None
    etag: str | None
    accept_ranges: str | None
    content_type: str | None


def _check(response: httpx.Response) -> None:
    if response.is_error:
        where = f"{response.request.method} {redact(response.request.url)}"
        raise HttpError(f"{where}: HTTP {response.status_code}", response.status_code)


def head(client: HttpClient, url: str) -> ArchiveInfo:
    response = client.head(url)
    _check(response)
    length = response.headers.get("Content-Length")
    return ArchiveInfo(
        url=str(response.url),
        size=int(length) if length and length.isdigit() else None,
        last_modified=response.headers.get("Last-Modified"),
        etag=response.headers.get("ETag"),
        accept_ranges=response.headers.get("Accept-Ranges"),
        content_type=response.headers.get("Content-Type"),
    )


class RangeReader(io.RawIOBase):
    """A read-only, seekable view of the remote file that `info` describes. Reads continue one
    streamed `Range: bytes=<pos>-` response; a seek elsewhere closes it, and the next read
    opens another. A body that breaks off is resumed from the same byte, at most RESUMES
    times per archive read."""

    def __init__(self, client: HttpClient, info: ArchiveInfo) -> None:
        super().__init__()
        if not info.size:
            raise ValueError("a range read needs the archive size from the HEAD answer")
        self._client, self._info, self._size = client, info, info.size
        self._pos = 0
        self._stream_pos = -1
        self._response: httpx.Response | None = None
        self._chunks: Iterator[bytes] = iter(())
        self._buffer = b""
        self.requests = 0
        self.resumes = 0
        self.bytes_received = 0

    def readable(self) -> bool:
        return True

    def seekable(self) -> bool:
        return True

    def tell(self) -> int:
        return self._pos

    def seek(self, offset: int, whence: int = io.SEEK_SET) -> int:
        base = {io.SEEK_SET: 0, io.SEEK_CUR: self._pos, io.SEEK_END: self._size}[whence]
        self._pos = max(0, base + offset)
        return self._pos

    def readinto(self, buffer: Buffer) -> int:
        view = memoryview(buffer).cast("B")
        wanted = min(len(view), self._size - self._pos)
        if wanted <= 0:
            return 0
        if self._stream_pos != self._pos:
            self._open(self._pos)
        filled = 0
        while filled < wanted:  # fill completely: zipfile treats a short read as truncation
            if not self._buffer:
                self._buffer = self._next_chunk(self._pos + filled)
                self.bytes_received += len(self._buffer)
            take = self._buffer[: wanted - filled]
            view[filled : filled + len(take)] = take
            self._buffer = self._buffer[len(take) :]
            filled += len(take)
        self._pos += filled
        self._stream_pos = self._pos
        return filled

    def _next_chunk(self, at: int) -> bytes:
        while True:
            try:
                chunk = next(self._chunks, b"")
            except httpx.TransportError as exc:
                if self.resumes == RESUMES:
                    where = f"GET {redact(self._info.url)}"
                    raise HttpError(f"{where}: body broke off at byte {at}: {exc}") from exc
                self.resumes += 1
                log.warning("range body broke at byte %d (%s); resuming", at, type(exc).__name__)
                self._open(at)
                continue
            if not chunk:
                raise OSError(f"range response ended early at byte {at}")
            return chunk

    def _open(self, start: int) -> None:
        self._close_stream()
        info = self._info
        headers = {"Range": f"bytes={start}-", "Accept-Encoding": "identity"}
        if info.etag or info.last_modified:
            headers["If-Range"] = info.etag or info.last_modified or ""
        request = self._client.build_request("GET", info.url, headers=headers)
        response = self._client.send(request, stream=True)
        self.requests += 1
        expected = f"bytes {start}-{self._size - 1}/{self._size}"
        etag = response.headers.get("ETag")
        problem = None
        if response.status_code != httpx.codes.PARTIAL_CONTENT:
            problem = f"answered {response.status_code}"
        elif response.headers.get("Content-Range") != expected:
            problem = f"Content-Range {response.headers.get('Content-Range')!r}, not {expected!r}"
        elif etag and info.etag and etag != info.etag:
            problem = f"ETag {etag} after {info.etag}"
        if problem is None:
            self._response, self._chunks = response, response.iter_bytes(CHUNK)
            self._stream_pos = start
            return
        response.close()  # a 200 would be the whole archive: never read it here
        where = f"GET {redact(info.url)} for {headers['Range']}"
        if self.requests == 1 and response.status_code != httpx.codes.PARTIAL_CONTENT:
            raise RangeNotSupportedError(f"{where}: {problem}", response.status_code)
        message = f"{where}: {problem}; the archive changed during the read; run again"
        raise ArchiveChangedError(message, response.status_code)

    def _close_stream(self) -> None:
        if self._response is not None:
            self._response.close()
        self._response, self._chunks, self._buffer, self._stream_pos = None, iter(()), b"", -1

    def close(self) -> None:
        self._close_stream()
        super().close()


def download(client: HttpClient, url: str, cache_dir: Path) -> Path:
    """Download the archive into `cache_dir` once; later calls send conditional headers."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / ARCHIVE_FILE
    meta = target.with_name(target.name + ".headers.json")
    headers: dict[str, str] = {}
    if target.exists() and meta.exists():
        saved = json.loads(meta.read_text(encoding="utf-8"))
        headers = {k: v for k, v in saved.items() if k in ("If-None-Match", "If-Modified-Since")}
    with client.stream("GET", url, headers=headers) as response:
        if response.status_code == httpx.codes.NOT_MODIFIED:
            log.info("archive not modified; reusing %s", target)
            return target
        _check(response)
        partial = target.with_name(target.name + ".part")
        with partial.open("wb") as handle:
            for chunk in response.iter_bytes(1 << 20):
                handle.write(chunk)
        partial.replace(target)
        validators = {"If-None-Match": response.headers.get("ETag"),
                      "If-Modified-Since": response.headers.get("Last-Modified")}  # fmt: skip
        meta.write_text(json.dumps({k: v for k, v in validators.items() if v}), encoding="utf-8")
    return target


Mode = Literal["range", "download"]


def open_archive(
    client: HttpClient, url: str, cache_dir: Path
) -> tuple[zipfile.ZipFile, ArchiveInfo, Mode, RangeReader | None]:
    """HEAD, then the zip over range requests if possible, else from a cached download."""
    info = head(client, url)
    if info.accept_ranges == "bytes" and info.size:
        reader = RangeReader(client, info)
        try:
            return zipfile.ZipFile(reader), info, "range", reader
        except RangeNotSupportedError as exc:
            log.warning("byte ranges advertised but refused (%s); downloading instead", exc)
            reader.close()
    return zipfile.ZipFile(download(client, info.url, cache_dir)), info, "download", None
