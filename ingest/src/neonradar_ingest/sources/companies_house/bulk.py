"""The Free Company Data Product: discovery, reading and the `index` step (PHASE-2.md M2.3a).

The monthly product (`companies`) is a set of zip parts `BasicCompanyData-<date>-partN_M.zip`
listed on `en_output.html`. Reading follows the quirks of research note bulk-sources-loading.md
2.2 to 2.4: header cells stripped and columns mapped by name, strict UTF-8 (a decoding error
stops the build with the part's name), empty rows and rows with the wrong field count skipped
and counted, HTML character references decoded only when complete, `dd/mm/yyyy` dates parsed
strictly. Messages name parts, columns and counts, never a value.
"""

import csv
import html
import io
import re
import sqlite3
import unicodedata
import zipfile
from collections import Counter
from collections.abc import Iterator, Sequence
from datetime import date
from pathlib import Path
from urllib.parse import urljoin, urlsplit

from neonradar_ingest.data.download import DownloadError
from neonradar_ingest.data.sources import BuildError, RemoteFile, SourceSpec, register_source
from neonradar_ingest.http import HttpClient, HttpError, redact
from neonradar_keys.postcodes import normalise_uk_postcode, postcode_parts

DATASET = "gb_companies_house"
PRODUCT = "companies"
PAGE_URL = "https://download.companieshouse.gov.uk/en_output.html"
HOST = "download.companieshouse.gov.uk"  # parts listed anywhere else are ignored
PART_RE = re.compile(r"BasicCompanyData-(\d{4}-\d{2}-\d{2})-part(\d+)_(\d+)\.zip\Z")
HREF_RE = re.compile(r"""href\s*=\s*["']([^"'#?]+)["']""", re.IGNORECASE)
REFERENCE_RE = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
DATE_RE = re.compile(r"(\d{2})/(\d{2})/(\d{4})\Z")
OUTWARD_RE = re.compile(r"[A-Z]{1,2}[0-9][A-Z0-9]?\Z")
SIC = tuple(f"SICCode.SicText_{n}" for n in range(1, 5))
PREVIOUS = tuple(f"PreviousName_{n}.CompanyName" for n in range(1, 11))
# The registered office fields in the order they make up `Address.full` (care-of left out).
ADDRESS = tuple(
    f"RegAddress.{name}"
    for name in ("POBox", "AddressLine1", "AddressLine2", "PostTown", "County", "PostCode",
                 "Country")
)  # fmt: skip
# The columns the loader reads (the M2.3a table); a part without one of them stops the build.
COLUMNS = (
    "CompanyName",
    "CompanyNumber",
    "CompanyCategory",
    "CompanyStatus",
    "CountryOfOrigin",
    "IncorporationDate",
    "DissolutionDate",
    "Accounts.AccountCategory",
    *SIC,
    *PREVIOUS,
    *ADDRESS,
)
INDEX_COLUMNS = ("CompanyNumber", "CompanyName", "RegAddress.PostCode", "CompanyCategory",
                 "CompanyStatus", "CountryOfOrigin")  # fmt: skip
BATCH = 10_000

Row = dict[str, str]


def discover(client: HttpClient) -> list[RemoteFile]:
    """The parts of the newest snapshot date for which all `M` parts are listed."""
    response = client.get(PAGE_URL)
    if response.is_error:
        raise HttpError(
            f"GET {redact(PAGE_URL)}: HTTP {response.status_code}", response.status_code
        )
    found: dict[str, dict[int, tuple[int, str]]] = {}
    for href in HREF_RE.findall(response.text):
        name = href.rsplit("/", 1)[-1]
        url = urljoin(PAGE_URL, href)
        where = urlsplit(url)
        if (match := PART_RE.fullmatch(name)) and (where.scheme, where.hostname) == ("https", HOST):
            when, part, of = match[1], int(match[2]), int(match[3])
            found.setdefault(when, {})[part] = (of, url)
    for when in sorted(found, reverse=True):
        parts = found[when]
        totals = {of for of, _ in parts.values()}
        if len(totals) == 1 and set(parts) == set(range(1, totals.pop() + 1)):
            return [
                RemoteFile(url.rsplit("/", 1)[-1], url, when, None, None, product=PRODUCT)
                for _, (_, url) in sorted(parts.items())
            ]
    raise DownloadError("discover: no snapshot with every part listed", "discover")


register_source(SourceSpec(DATASET, discover))


def part_number(path: Path) -> int:
    match = PART_RE.fullmatch(path.name)
    return int(match[2]) if match else 0


def iter_part(path: Path, stats: Counter[str], columns: Sequence[str] = COLUMNS) -> Iterator[Row]:
    """The rows of one zip part as {column: raw value} for `columns`; skips are counted."""
    with zipfile.ZipFile(path) as archive:
        for member in archive.namelist():
            if member.endswith("/"):
                continue
            with archive.open(member) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8", errors="strict", newline="")
                try:
                    yield from _rows(csv.reader(text), path.name, stats, columns)
                except UnicodeDecodeError:
                    message = f"{path.name}: not valid UTF-8 (a mis-encoded release); stopped"
                    raise BuildError(message, "encoding", counts_only=True) from None


def _rows(reader: Iterator[list[str]], part: str, stats: Counter[str], columns: Sequence[str]
          ) -> Iterator[Row]:  # fmt: skip
    header = [cell.strip() for cell in next(reader, [])]
    if not header:
        raise BuildError(f"{part}: no header line", "header", counts_only=True)
    where = {name: i for i, name in reversed(list(enumerate(header)))}
    missing = [name for name in COLUMNS if name not in where]
    if missing:
        raise BuildError(f"{part}: column {missing[0]} is missing", "header", counts_only=True)
    stats["extra_columns"] = max(stats["extra_columns"], len(set(header) - set(COLUMNS)))
    width, wanted = len(header), [(name, where[name]) for name in columns]
    for row in reader:
        if not any(cell.strip() for cell in row):
            stats["empty_rows"] += 1
        elif len(row) != width:
            stats["bad_field_count_rows"] += 1
        else:
            stats["rows_read"] += 1
            yield {name: row[i] for name, i in wanted}


def text(value: str | None) -> str | None:
    """NFC, complete HTML references decoded (`A&B LIMITED` stays), spaces collapsed."""
    if not value:
        return None
    decoded = REFERENCE_RE.sub(lambda match: html.unescape(match.group(0)), value)
    cleaned = " ".join(unicodedata.normalize("NFC", decoded).split())
    return cleaned or None


def address_part(value: str | None) -> str | None:
    """A cleaned address field; only punctuation, digits or a bare outward postcode is missing."""
    cleaned = text(value)
    if cleaned is None or not any(c.isalpha() for c in cleaned):
        return None
    return None if OUTWARD_RE.fullmatch(cleaned.upper()) else cleaned


def iso_date(value: str, stats: Counter[str], what: str) -> str | None:
    """`dd/mm/yyyy` to ISO; anything else is dropped and counted under `what`."""
    value = value.strip()
    if not value:
        return None
    if match := DATE_RE.fullmatch(value):
        try:
            return date(int(match[3]), int(match[2]), int(match[1])).isoformat()
        except ValueError:
            pass
    stats[f"dates_dropped.{what}"] += 1
    return None


def district(postcode: str | None) -> str | None:
    """The outward code of a UK postcode (`neonradar_keys.postcodes`), else None."""
    normalised = normalise_uk_postcode(postcode) if postcode else None
    return postcode_parts(normalised).district if normalised else None


def build_index(parts: Sequence[Path], path: Path) -> dict[str, int]:
    """The `index` step: every company's number, name, district, category, status and origin."""
    stats: Counter[str] = Counter()
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("PRAGMA journal_mode=OFF")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute(
            "CREATE TABLE company(number TEXT PRIMARY KEY, name TEXT, district TEXT,"
            " category TEXT, status TEXT, origin TEXT)"
        )
        batch: list[tuple[str | None, ...]] = []
        for part in parts:
            for row in iter_part(part, stats, INDEX_COLUMNS):
                number = row["CompanyNumber"].strip()
                if not number:
                    stats["rows_without_number"] += 1
                    continue
                where = district(row["RegAddress.PostCode"])
                stats["rows_without_district"] += where is None
                batch.append((number, text(row["CompanyName"]), where,
                              text(row["CompanyCategory"]), text(row["CompanyStatus"]),
                              text(row["CountryOfOrigin"])))  # fmt: skip
                if len(batch) >= BATCH:
                    connection.executemany(
                        "INSERT OR IGNORE INTO company VALUES (?,?,?,?,?,?)", batch
                    )
                    batch.clear()
        connection.executemany("INSERT OR IGNORE INTO company VALUES (?,?,?,?,?,?)", batch)
        connection.execute("CREATE INDEX company_district ON company(district)")
        indexed = connection.execute("SELECT count(*) FROM company").fetchone()[0]
        connection.commit()
    except BaseException:
        connection.close()
        temporary.unlink(missing_ok=True)  # it holds the rows read so far
        raise
    connection.close()
    temporary.replace(path)
    counts = {"parts": len(parts), "companies_indexed": indexed}
    counts["duplicate_numbers"] = stats["rows_read"] - stats["rows_without_number"] - indexed
    return counts | dict(sorted(stats.items()))
