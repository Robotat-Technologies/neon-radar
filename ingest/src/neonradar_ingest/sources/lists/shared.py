"""What every official list builder shares besides `common.py` (PHASE-2.md M2.6 rules 2 to 10).

`common.py` holds the pure parsing helpers (verbatim from the spec); this module holds the
builder plumbing: the profile block model, the newest complete download, the bounds and
fill-rate checks, the record writer and the namespace-agnostic XML helpers. Messages name
datasets, schemata, rules and counts only, never a value from the list.
"""

import json
import re
from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element

import yaml
from pydantic import BaseModel, ConfigDict, StrictBool

from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data import layout
from neonradar_ingest.data.sources import BuildError, RemoteFile
from neonradar_ingest.http import HttpClient, RateLimiter
from neonradar_ingest.sources.lists.common import check_bounds

BOUNDS_FILE = Path(__file__).with_name("bounds.yaml")
PRODUCT = "main"
RECORD_V = "1.1"  # Phase 2 loaders write nr.v "1.1" (PHASE-2.md 5.1)
# A list's own stamp as it may appear in a summary (dates, times, offsets, short ids).
STAMP = re.compile(r"[A-Za-z0-9][A-Za-z0-9 ._:/+-]{0,59}\Z")


class ListOptions(BaseModel):
    """The profile block of every official list (M2.6 rule 7, PHASE-2.md 7.8)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    keep_reasons: StrictBool = False  # statements of reasons, only into Sanction:reason
    keep_positions: StrictBool = False  # titles and positions (possible special category data)


class SizeError(BuildError):
    """A list outside its bounds or with a zero fill rate (M2.6 rule 10): exit code 4."""

    exit_code = 4


@dataclass(frozen=True, slots=True)
class Download:
    """The newest complete download of a list file, as `download.json` records it."""

    path: Path
    url: str  # without its query string (download.stored_url)
    version: str
    downloaded_at: str | None


def discover_static(name: str, url: str) -> Callable[[HttpClient], list[RemoteFile]]:
    """`SourceSpec.discover` for a list published at one fixed URL: no request is sent.

    The version is the UTC date of the fetch (M2.6 rule 4): a list file shows its own stamp
    only once downloaded, and the lists change several times a week.
    """

    def discover(client: HttpClient) -> list[RemoteFile]:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        return [RemoteFile(name=name, url=url, version=today, size=None, sha256=None)]

    return discover


def list_client() -> HttpClient:
    """`SourceSpec.client` for a list file: redirects followed, one request per second, and no
    query string in any log (M2.6 rule 4: the UN redirect is signed, the EU URL holds a token)."""
    return HttpClient("", follow_redirects=True, limiter=RateLimiter(1.0), log_query=False)


def latest_download(dataset: str, name: str) -> Download:
    """The file `name` of the newest complete version of `dataset`, else BuildError."""
    product_dir = layout.sources_dir(dataset, PRODUCT, "current").parent
    found: list[tuple[str, str, Download]] = []
    for folder in sorted(product_dir.iterdir()) if product_dir.is_dir() else []:
        try:
            record = json.loads((folder / "download.json").read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        if not isinstance(record, dict) or not record.get("complete"):
            continue
        for entry in record.get("files", []):
            if isinstance(entry, dict) and entry.get("name") == name and (folder / name).is_file():
                download = Download(
                    folder / name,
                    str(entry.get("url", "")),
                    str(entry.get("version", folder.name)),
                    entry.get("downloaded_at"),
                )
                found.append((str(record.get("completed_at", "")), folder.name, download))
    if not found:
        raise BuildError(
            f"{dataset}: no complete download of {name}; run neonradar data fetch first",
            "download",
            counts_only=True,
        )
    return max(found, key=lambda item: item[:2])[2]


@cache
def load_bounds() -> dict[str, dict[str, list[int]]]:
    data = yaml.safe_load(BOUNDS_FILE.read_text(encoding="utf-8"))
    return {str(slug): dict(ranges) for slug, ranges in data.items()}


def rate(part: int, whole: int) -> float:
    """A fill rate rounded to four places; 0.0 when there is nothing to fill."""
    return round(part / whole, 4) if whole else 0.0


def _filled(records: list[dict[str, Any]], schema: str, *names: str) -> tuple[int, int]:
    chosen = [r for r in records if r["schema"] == schema]
    return sum(any(r["properties"].get(n) for n in names) for r in chosen), len(chosen)


def fill_rates(records: list[dict[str, Any]]) -> dict[str, float]:
    """The shares of M2.6 rule 10, from the records as written."""
    pairs = {
        "person_birth_date": _filled(records, "Person", "birthDate"),
        "person_nationality": _filled(records, "Person", "nationality"),
        "person_passport_or_id": _filled(records, "Person", "passportNumber", "idNumber"),
        "sanction_program": _filled(records, "Sanction", "program"),
        "sanction_start_date": _filled(records, "Sanction", "startDate"),
        "organization_registration_or_lei": _filled(
            records, "Organization", "registrationNumber", "leiCode"
        ),
    }
    return {name: rate(*pair) for name, pair in pairs.items()}


def check_size(
    dataset: str, counts: Mapping[str, int], zero_rates: Iterable[str], *, accept_size: bool
) -> int:
    """Raise SizeError for a zero fill rate (always) or a count outside bounds.yaml (unless
    `accept_size`); return how many counts were outside their range."""
    problems = check_bounds(dataset, dict(counts), load_bounds())
    fatal = [] if accept_size else list(problems)
    if fatal:
        fatal.append("a human may pass --accept-size after reading the list's publication page")
    fatal += [
        f"{dataset}: the fill rate of {name} is zero; the parser is broken" for name in zero_rates
    ]
    if fatal:
        raise SizeError("; ".join(fatal), "size", counts_only=True)
    return len(problems)


def list_stamp(value: str | None) -> str:
    """The list's own stamp for the summary and the manifest notes, if it looks like one."""
    text = " ".join((value or "").split())
    if not text:
        return "missing"
    return text if STAMP.fullmatch(text) else "unrecognised"


def write_records(
    out_dir: Path,
    dataset: str,
    module: str,
    records: Iterable[Mapping[str, Any]],
    download: Download,
    *,
    skipped: Mapping[str, int],
    notes: Iterable[str],
) -> Path:
    """Write `<out_dir>/<dataset>.ftm.jsonl` and its manifest; return the record file."""
    path = out_dir / f"{dataset}.ftm.jsonl"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.writelines(json.dumps(record, ensure_ascii=False) + "\n" for record in records)
    source = Source(
        urls=[download.url] if download.url else [],
        retrieved_at=download.downloaded_at,
        source_version=download.version,
    )
    producer = Producer(name=f"neonradar_ingest.sources.lists.{module}", version=__version__)
    write_manifest(
        path,
        dataset=dataset,
        producer=producer,
        source=source,
        skipped={key: count for key, count in sorted(skipped.items()) if count},
        notes=list(notes),
    )
    return path


def local(tag: object) -> str:
    """An element's tag without its namespace (M2.6 rule 3: OFAC changed its namespace)."""
    return tag.rsplit("}", 1)[-1] if isinstance(tag, str) else ""


def children(element: Element | None, name: str) -> Iterator[Element]:
    """Direct children called `name`, whatever their namespace."""
    if element is not None:
        yield from (child for child in element if local(child.tag) == name)


def child(element: Element | None, name: str) -> Element | None:
    return next(children(element, name), None)


def text(element: Element | None, name: str | None = None) -> str | None:
    """The stripped text of `element` (or of its first child `name`); None when empty."""
    target = child(element, name) if name is not None else element
    value = target.text if target is not None else None
    value = " ".join(value.split()) if value else ""
    return value or None


def texts(element: Element | None, *path: str) -> list[str]:
    """The non-empty texts at `path` below `element` (each step a child name)."""
    found = [element] if element is not None else []
    for name in path:
        found = [item for parent in found for item in children(parent, name)]
    return [value for value in (text(item) for item in found) if value]
