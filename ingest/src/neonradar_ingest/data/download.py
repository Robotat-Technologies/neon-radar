"""Downloads with checksums, resumption and rotation (PHASE-2.md M2.2 deliverable 7).

`fetch(spec, client)` writes each file as `<name>.part` in
`layout.sources_dir(dataset, product, version)`, resumes it with an HTTP `Range` request when
the server sent `Accept-Ranges: bytes` (any reply but a 206 that continues the part exactly
restarts the file), renames it when complete, checks the size and SHA-256 when the spec gives
them, and records it in the version folder's `download.json`. URLs are stored without their
query string (the EU download token). After a cut connection it retries with backoff up to
three times, then stops that dataset and keeps the partial file for the next fetch (2.7); a
failed discovery stops only that dataset too. The two newest complete versions of each
dataset and product are kept; older ones are deleted after a successful download.
"""

import hashlib
import json
import shutil
import time
from collections import Counter
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

from neonradar_ingest.data import layout
from neonradar_ingest.data.sources import RemoteFile, SourceSpec
from neonradar_ingest.http import HttpClient, HttpError

GB = 1000**3
SPARE = 2 * GB  # free space left after a download: twice the file plus 2 GB, or 2 GB
CHUNK = 1 << 20
RETRIES = 3
KEEP = 2  # complete versions kept per dataset and product
RECORD = "download.json"
RESERVED_ENDINGS = (".part", ".part.json", ".tmp")  # partial files and atomic writes


class DownloadError(Exception):
    """A download that stopped; the message holds file names, sizes and counts only."""

    exit_code = 1
    counts_only = True

    def __init__(self, message: str, rule: str) -> None:
        super().__init__(message)
        self.rule = rule


def stored_url(url: str) -> str:
    """The URL without user info, query string or fragment: the form every file stores."""
    return str(httpx.URL(url).copy_with(userinfo=b"", query=None, fragment=None))


def _now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError, json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _write_json(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def _check_disk(folder: Path, remote: RemoteFile) -> None:
    need = SPARE if remote.size is None else 2 * remote.size + SPARE
    free = shutil.disk_usage(folder).free
    if free < need:
        raise DownloadError(
            f"{remote.name}: {free / GB:.1f} GB free, {need / GB:.1f} GB needed (twice the file"
            " plus 2 GB); free some space, for example with neonradar data purge --expired",
            "disk",
        )


def _complete(folder: Path, record: dict[str, Any], remote: RemoteFile) -> bool:
    entry = next((e for e in record.get("files", []) if e.get("name") == remote.name), None)
    path = folder / remote.name
    return entry is not None and path.is_file() and path.stat().st_size == entry.get("size")


def _encoded(response: httpx.Response) -> bool:
    return response.headers.get("Content-Encoding", "").strip().lower() not in ("", "identity")


def _continues(response: httpx.Response, offset: int, meta: dict[str, Any]) -> bool:
    """A 206 that continues the part exactly: same start, same file, no content encoding."""
    etag, stored = response.headers.get("ETag"), meta.get("etag")
    return (
        response.status_code == 206
        and response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")
        and not (etag and stored and etag != stored)
        and not _encoded(response)
    )


def _stream(
    client: HttpClient, remote: RemoteFile, part: Path, meta_path: Path, counts: Counter[str]
) -> dict[str, Any]:
    """One attempt: resume or restart `part`; return the response's validators.

    A Range request answered with anything but a 206 that continues the part exactly (a 200,
    a 416, a 206 from another offset or of another file, an encoded body) deletes the part and
    asks again without a range.
    """
    meta = _read_json(meta_path) if part.exists() else {}
    offset = part.stat().st_size if part.exists() else 0
    headers = {"Accept-Encoding": "identity"}  # the file as published: byte ranges stay exact
    if offset and meta.get("accept_ranges") == "bytes":
        headers["Range"] = f"bytes={offset}-"
        if meta.get("etag") or meta.get("last_modified"):
            headers["If-Range"] = meta.get("etag") or meta["last_modified"]
    restart = False
    with client.stream("GET", remote.url, headers=headers) as response:
        if "Range" in headers:
            restart = not _continues(response, offset, meta)
            mode = "ab"
        elif response.status_code == 200:
            mode = "wb"
            ranges = response.headers.get("Accept-Ranges", "").strip().lower()
            meta = {
                "accept_ranges": "none" if _encoded(response) else ranges,  # never resume those
                "etag": response.headers.get("ETag"),
                "last_modified": response.headers.get("Last-Modified"),
            }
            _write_json(meta_path, meta)
        else:
            raise DownloadError(f"{remote.name}: HTTP {response.status_code}", "http")
        if not restart:
            counts["files_resumed"] += mode == "ab"
            with part.open(mode) as handle:
                for chunk in response.iter_bytes():  # as received, so a cut keeps what arrived
                    handle.write(chunk)
    if restart:
        part.unlink(missing_ok=True)
        meta_path.unlink(missing_ok=True)
        counts["files_restarted"] += 1
        return _stream(client, remote, part, meta_path, counts)  # no part now: no Range
    return meta


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(CHUNK):
            digest.update(block)
    return digest.hexdigest()


def _download(
    client: HttpClient,
    folder: Path,
    remote: RemoteFile,
    counts: Counter[str],
    sleep: Callable[[float], None],
) -> dict[str, Any]:
    part, meta_path = folder / f"{remote.name}.part", folder / f"{remote.name}.part.json"
    started = time.monotonic()
    for attempt in range(RETRIES + 1):
        try:
            meta = _stream(client, remote, part, meta_path, counts)
            break
        except HttpError as exc:  # the client's own retries ran out; its message has the URL
            status = f"HTTP {exc.status}" if exc.status else "no response"
            raise DownloadError(f"{remote.name}: {status} after retries", "http") from None
        except httpx.TransportError:  # a cut connection: keep the part and resume it
            if attempt == RETRIES:
                raise DownloadError(
                    f"{remote.name}: the connection failed {RETRIES + 1} times; the partial file"
                    " is kept for the next fetch",
                    "network",
                ) from None
            counts["retries"] += 1
            sleep(min(2.0**attempt, 60.0))
    size, digest = part.stat().st_size, _sha256(part)
    problem = None
    if remote.size is not None and size != remote.size:
        problem = DownloadError(f"{remote.name}: {size} bytes, expected {remote.size}", "size")
    elif remote.sha256 and digest != remote.sha256.lower():
        problem = DownloadError(f"{remote.name}: the SHA-256 does not match", "sha256")
    if problem:
        part.unlink()
        meta_path.unlink(missing_ok=True)
        raise problem
    part.replace(folder / remote.name)
    meta_path.unlink(missing_ok=True)
    counts["files_downloaded"] += 1
    counts["bytes_downloaded"] += size
    return {
        "name": remote.name,
        "url": stored_url(remote.url),
        "version": remote.version,
        "product": remote.product,
        "size": size,
        "sha256": digest,
        "etag": meta.get("etag"),
        "last_modified": meta.get("last_modified"),
        "downloaded_at": _now(),
        "duration_s": round(time.monotonic() - started, 3),
    }


def _rotate(product_dir: Path) -> int:
    """Delete complete versions beyond the `KEEP` newest (by completion time); return how many."""
    complete = []
    for version in product_dir.iterdir():
        record = _read_json(version / RECORD) if version.is_dir() else {}
        if record.get("complete"):
            complete.append((str(record.get("completed_at", "")), version.name, version))
    complete.sort(reverse=True)
    for _, _, old in complete[KEEP:]:
        shutil.rmtree(old)
    return max(len(complete) - KEEP, 0)


def fetch(
    spec: SourceSpec, client: HttpClient, *, sleep: Callable[[float], None] = time.sleep
) -> dict[str, Any]:
    """Download the current version of every product of `spec`; return counts and versions."""
    counts: Counter[str] = Counter()
    groups: dict[tuple[str, str], list[RemoteFile]] = {}
    try:
        found = spec.discover(client)
    except HttpError as exc:  # stop this dataset only; the message would carry the URL
        status = f"HTTP {exc.status}" if exc.status else "no response"
        raise DownloadError(f"discover: {status} after retries", "http") from None
    for remote in found:
        layout.safe_name("file name", remote.name)
        if remote.name == RECORD or remote.name.endswith(RESERVED_ENDINGS):
            raise DownloadError(f"{remote.name}: a file name the data manager uses itself", "name")
        groups.setdefault((remote.product, remote.version), []).append(remote)
    products: dict[str, dict[str, Any]] = {}
    for (product, version), remotes in sorted(groups.items()):
        folder = layout.sources_dir(spec.dataset, product, version)
        folder.mkdir(parents=True, exist_ok=True)
        record = _read_json(folder / RECORD) or {"files": []}
        for remote in remotes:
            if _complete(folder, record, remote):
                counts["files_skipped"] += 1
                continue
            _check_disk(folder, remote)
            entry = _download(client, folder, remote, counts, sleep)
            record["files"] = [e for e in record["files"] if e.get("name") != remote.name]
            record["files"].append(entry)
            _write_json(folder / RECORD, record)
        if not record.get("complete"):
            record |= {"complete": True, "completed_at": _now()}
            _write_json(folder / RECORD, record)
        counts["versions_deleted"] += _rotate(folder.parent)
        products[product] = {"version": version, "files": len(remotes)}
    return {**{key: counts[key] for key in sorted(counts)}, "products": products}
