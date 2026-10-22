"""The ICIJ Offshore Leaks loader (PHASE-2.md M2.5).

`SPEC` finds the current archive for `neonradar data fetch` (a HEAD request, conditional on
the last download's `ETag` and `Last-Modified`; the version is the `Last-Modified` date, else
the download date). `build` reads the six CSV members straight from the downloaded zip, never
extracting it, selects the profile's slice (`slice.py`), and writes one C1 record file with
its manifest and `icij_offshore_leaks-<yyyymmdd>-hints.csv`: ICIJ's own duplicate hints
between two kept non-address records, which the resolver reads as possible matches (not
confirmed) and which never merge anything by themselves. Relationships are read before node
records are written, so `registered_address` links become `addressEntity` on the right
record. The free-text `note` column and every other column the mapping does not name are never
read into records.
"""

import csv
import email.utils
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter
from collections.abc import Iterator
from datetime import UTC, date, datetime
from functools import cache
from pathlib import Path
from typing import IO, Any

import yaml
from followthemoney import Schema, ValueEntity, model

from neonradar_contracts.datasets import load_registry
from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data import layout
from neonradar_ingest.data.download import RECORD, stored_url
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.sources import (
    BuildContext,
    Builder,
    BuildError,
    BuildResult,
    RemoteFile,
    SourceSpec,
    register_builder,
    register_source,
)
from neonradar_ingest.http import HttpClient, HttpError, redact
from neonradar_ingest.sources.icij.archive import ARCHIVE_FILE, ARCHIVE_URL
from neonradar_ingest.sources.icij.mapping import ADDRESS_ROLES, node_id
from neonradar_ingest.sources.icij.slice import (
    NODE_FILES,
    RELATIONSHIPS,
    IcijSource,
    Row,
    Selection,
    ends,
    is_hint,
    postcode_districts,
    select,
)
from neonradar_keys.countries import country_code

DATASET = "icij_offshore_leaks"
PREFIX = "icij"
PRODUCT = "main"
NR_VERSION = "1.1"
NODE_URL = "https://offshoreleaks.icij.org/nodes/{}"
LINKS_FILE = Path(__file__).with_name("links.yaml")
DISCLAIMER = (
    "There are legitimate uses for offshore companies and trusts.",
    "We do not intend to suggest or imply that any individuals, companies or other entities"
    " included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted"
    " improperly. (ICIJ FAQ, as re-fetched for M1.8c on 21 October 2026)",
)
REQUIRED = {name: ("node_id", "name") for name in NODE_FILES} | {
    RELATIONSHIPS: ("node_id_start", "node_id_end", "rel_type", "link")
}
OPTIONAL = {
    "nodes-entities.csv": ("original_name", "former_name", "jurisdiction_description",
                           "country_codes", "incorporation_date", "inactivation_date",
                           "struck_off_date", "closed_date", "status", "sourceID"),
    "nodes-officers.csv": ("country_codes", "sourceID"),
    "nodes-intermediaries.csv": ("country_codes", "status", "sourceID"),
    "nodes-others.csv": ("jurisdiction_description", "country_codes", "incorporation_date",
                         "struck_off_date", "closed_date", "sourceID"),
    "nodes-addresses.csv": ("address", "country_codes", "sourceID"),
    RELATIONSHIPS: ("status", "start_date", "end_date", "sourceID"),
}  # fmt: skip
DISSOLUTION = {
    "entity": ("inactivation_date", "struck_off_date", "closed_date"),
    "other": ("struck_off_date", "closed_date"),
}
LINK_CLASSES = {
    "ownership": ("Ownership", False),
    "nominee_ownership": ("Ownership", True),
    "directorship": ("Directorship", False),
    "nominee_directorship": ("Directorship", True),
    "unknown_link": ("UnknownLink", False),
}
KNOWN_REL_TYPES = ("registered_address", "intermediary_of", "officer_of", "underlying",
                   "related_entity", "connected_to")  # fmt: skip
MONTH_NAMES = ("jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec")
MONTHS = {name: number for number, name in enumerate(MONTH_NAMES, start=1)}
ICIJ_DATE = re.compile(r"(\d{1,2})-([A-Za-z]{3})-(\d{4}|\d{2})\Z")  # 22-MAY-2006, 22-MAY-06
ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})\Z")
QUESTION_MARKS = re.compile(r"[?\s]+\Z")
GENERATED_ON = re.compile(r"GENERATED_ON_(\d{4})(\d{2})(\d{2})\.txt\Z")
SUMMARY_VALUE = re.compile(r"[^a-z0-9 ._#:/()&,'-]+")
HINT_COUNTS = ("hints_written", "hints_repeated", "address_hints_dropped", "hints_outside_slice")
FIELD_LIMIT = 1 << 24
SKIP_DUPLICATE_NODE = "duplicate node rows"
SKIP_NO_ID = "rows without a node id or relationship type"
SKIP_OUTSIDE = "relationships with an end outside the slice"
SKIP_CAP = "relationships dropped with nodes over the cap"
SKIP_DUPLICATE_LINK = "duplicate relationship rows"


def clean(value: str | None) -> str:
    """NFC, stripped; empty when the value is only question marks (junk names)."""
    text = unicodedata.normalize("NFC", (value or "").strip())
    return "" if QUESTION_MARKS.match(text) else text


def usable(kind: str, row: Row) -> bool:
    """A row C1 can carry: a name (addresses: the address text)."""
    return bool(clean(row.get("address" if kind == "address" else "name")))


@cache
def link_table() -> dict[str, tuple[str, bool]]:
    """`links.yaml`: lower-case `officer_of` link -> (schema, nominee)."""
    data = yaml.safe_load(LINKS_FILE.read_text(encoding="utf-8"))
    table: dict[str, tuple[str, bool]] = {}
    for group, values in data.items():
        for value in values:
            if value != link_key(value):
                raise ValueError(f"links.yaml: {value!r} is not lower case with single spaces")
            if value in table:
                raise ValueError(f"links.yaml lists {value!r} twice")
            table[value] = LINK_CLASSES[group]
    return table


def link_key(link: str | None) -> str:
    return " ".join((link or "").lower().split())


def classify(rel_type: str, link: str | None) -> tuple[str, bool]:
    """(schema or "address", nominee) for a non-hint relationship row."""
    if rel_type == "registered_address":
        return "address", False
    if rel_type == "intermediary_of":
        return "Representation", False
    if rel_type == "officer_of":
        return link_table().get(link_key(link), ("UnknownLink", False))
    return "UnknownLink", False


def summary_value(text: str) -> str:
    """A vocabulary value as a `_by_value` summary key (M2.2): lower case, safe characters."""
    value = SUMMARY_VALUE.sub("_", text.lower())
    start = next((i for i, char in enumerate(value) if char.isalnum()), len(value))
    return value[start : start + 80] or "empty"


def address_role(link: str | None) -> str:
    """The Phase 1 rule: the first of registered, residential, business, service in the link."""
    key = link_key(link)
    return next((role for role in ADDRESS_ROLES if role in key), "unknown")


class Dates:
    """ICIJ dates to ISO: `%d-%b-%Y`, `%d-%b-%y` (19YY when YY is past this year's, else
    20YY) and ISO dates; the rest are dropped and counted. Years before 1000 are dropped."""

    def __init__(self, today: date) -> None:
        self.century_cut = today.year % 100
        self.counts: Counter[str] = Counter(parsed=0, two_digit_year=0, dropped=0)

    def parse(self, raw: str | None) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None
        found, iso = ICIJ_DATE.match(text), ISO_DATE.match(text)
        try:
            if found:
                day, month, year = int(found[1]), MONTHS.get(found[2].lower(), 0), found[3]
                number = int(year)
                if len(year) == 2:
                    number += 1900 if number > self.century_cut else 2000
                value = date(number, month, day)
            elif iso:
                value = date(int(iso[1]), int(iso[2]), int(iso[3]))
            else:
                value = None
        except ValueError:
            value = None
        if value is None or value.year < 1000:
            self.counts["dropped"] += 1
            return None
        self.counts["parsed"] += 1
        self.counts["two_digit_year"] += bool(found and len(found[3]) == 2)
        return value.isoformat()

    def first(self, row: Row, columns: tuple[str, ...]) -> str | None:
        """The first of `columns` that holds a date."""
        for column in columns:
            if value := self.parse(row.get(column)):
                return value
        return None


class Archive:
    """The CSV members of the zip, read by header name; header facts counted on first read."""

    def __init__(self, zf: zipfile.ZipFile) -> None:
        self.zf = zf
        # The default 131,072-character field limit would stop the build on one long `note`
        # (read by the parser, never loaded); the limit is process-wide.
        csv.field_size_limit(max(csv.field_size_limit(), FIELD_LIMIT))
        self.absent: list[str] = []
        self.extra: dict[str, int] = {}

    def source_version(self) -> str | None:
        """The `GENERATED_ON_<yyyymmdd>.txt` marker's date, ISO."""
        for name in self.zf.namelist():
            if found := GENERATED_ON.match(name):
                return f"{found[1]}-{found[2]}-{found[3]}"
        return None

    def _header(self, member: str, header: list[str]) -> None:
        missing = [column for column in REQUIRED[member] if column not in header]
        if missing:
            raise BuildError(f"{member} has no column {missing[0]}", "header", counts_only=True)
        if member not in self.extra:
            self.absent += [f"{member}:{c}" for c in OPTIONAL[member] if c not in header]
            known = {*REQUIRED[member], *OPTIONAL[member]}
            self.extra[member] = sum(1 for column in header if column not in known)

    def rows(self, member: str) -> Iterator[Row]:
        try:
            info = self.zf.getinfo(member)
        except KeyError:
            raise BuildError(f"the archive has no {member}", "archive", counts_only=True) from None
        with self.zf.open(info) as raw, io.TextIOWrapper(raw, encoding="utf-8", newline="") as text:
            reader = csv.DictReader(text)
            try:
                header = [name.replace("\ufeff", "").strip() for name in reader.fieldnames or []]
                reader.fieldnames = header
                self._header(member, header)
                yield from reader
            except (UnicodeDecodeError, csv.Error) as exc:  # their messages can quote a value
                message = f"{member} is not a readable UTF-8 CSV file ({type(exc).__name__})"
                raise BuildError(message, "archive", counts_only=True) from None


class Mapper:
    """Writes the records of one selection: relationships first, then nodes."""

    def __init__(self, selection: Selection, today: date) -> None:
        self.selection = selection
        self.selected = selection.selected
        self.dates = Dates(today)
        self.skipped: Counter[str] = Counter(selection.skipped)
        self.schemas: Counter[str] = Counter()
        self.links: Counter[str] = Counter()
        self.unknown_links: Counter[str] = Counter()
        self.unknown_rel_types: Counter[str] = Counter()
        self.hints: Counter[str] = Counter(dict.fromkeys(HINT_COUNTS, 0))
        self.merged = 0  # ids in more than one node file, written as one record
        self.addresses: dict[str, dict[str, str]] = {}  # node id -> {address record id: role}
        self.edge_ids: set[str] = set()

    def schema(self, node: str) -> str:
        kinds = self.selection.kinds[node]
        if "entity" in kinds:
            return "Company"
        return "Address" if kinds == ("address",) else "LegalEntity"

    def write(self, out: IO[str], entity: ValueEntity, nr: dict[str, Any] | None) -> None:
        data = entity.to_dict()
        if nr:
            data["nr"] = nr
        out.write(json.dumps(data, ensure_ascii=False) + "\n")
        self.schemas[entity.schema.name] += 1

    def relationships(self, rows: Iterator[Row], out: IO[str], hints: Any) -> None:
        kept = self.selection.kept
        seen_hints: set[tuple[str, str, str]] = set()
        for row in rows:
            start, end, rel = ends(row)
            if not (start and end and rel):
                self.skipped[SKIP_NO_ID] += 1
            elif is_hint(rel):
                self.hint(start, end, rel, hints, seen_hints)
            elif start not in kept or end not in kept:
                both = start in self.selected and end in self.selected
                self.skipped[SKIP_CAP if both else SKIP_OUTSIDE] += 1
            else:
                self.relationship(row, start, end, rel, out)

    def hint(self, start: str, end: str, rel: str, hints: Any, seen: set[Any]) -> None:
        kept, kinds = self.selection.kept, self.selection.kinds
        if rel == "same_address_as" or (
            start in kept and end in kept and "address" in kinds[start] + kinds[end]
        ):
            self.hints["address_hints_dropped"] += 1
        elif start not in kept or end not in kept or start == end:
            self.hints["hints_outside_slice"] += 1
        elif (key := (*sorted((node_id(start), node_id(end))), rel)) in seen:
            self.hints["hints_repeated"] += 1
        else:
            seen.add(key)
            hints.writerow(key)
            self.hints["hints_written"] += 1

    def relationship(self, row: Row, start: str, end: str, rel: str, out: IO[str]) -> None:
        kind, nominee = classify(rel, row.get("link"))
        source, target = model[self.schema(start)], model[self.schema(end)]
        if kind == "address" and target.is_a("Address") and not source.is_a("Address"):
            roles = self.addresses.setdefault(start, {})
            roles.setdefault(node_id(end), address_role(row.get("link")))
            self.links["address"] += 1
            return
        kind = fit(kind if kind != "address" else "UnknownLink", source, target)
        parts = "|".join(
            row.get(c) or "" for c in (*REQUIRED[RELATIONSHIPS], *OPTIONAL[RELATIONSHIPS])
        )
        digest = hashlib.sha1(parts.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
        rid = f"{PREFIX}-{kind.lower()}-{digest}"
        if rid in self.edge_ids:
            self.skipped[SKIP_DUPLICATE_LINK] += 1
            return
        self.edge_ids.add(rid)
        if rel == "officer_of" and link_key(row.get("link")) not in link_table():
            self.unknown_links[summary_value(link_key(row.get("link")))] += 1
        elif rel not in KNOWN_REL_TYPES:
            self.unknown_rel_types[summary_value(rel)] += 1
        link = ValueEntity(model[kind], {"id": rid, "datasets": [DATASET]})
        link.add(link.schema.edge_source or "", node_id(start))
        link.add(link.schema.edge_target or "", node_id(end))
        raw_link = clean(row.get("link"))
        if kind == "Representation":
            link.add("role", "intermediary")
        elif kind == "UnknownLink" and rel != "officer_of":
            link.add("role", rel)
        else:
            link.add("role", raw_link or rel)
        link.add("status", clean(row.get("status")))
        link.add("publisher", clean(row.get("sourceID")))
        link.add("startDate", self.dates.parse(row.get("start_date")))
        link.add("endDate", self.dates.parse(row.get("end_date")))
        self.links[kind.lower()] += 1
        nominee = nominee and kind in ("Ownership", "Directorship")
        self.links["nominee"] += nominee
        self.write(out, link, {"v": NR_VERSION, "is_nominee": True} if nominee else None)

    def nodes(self, archive: Archive, out: IO[str]) -> None:
        kinds, done = self.selection.kinds, set[tuple[str, str]]()
        pending: dict[str, list[tuple[str, Row]]] = {}  # ids in more than one node file
        for member, kind in NODE_FILES.items():
            for row in archive.rows(member):
                node = (row.get("node_id") or "").strip()
                if kind not in kinds.get(node, ()) or not usable(kind, row):
                    continue
                if (node, kind) in done:
                    self.skipped[SKIP_DUPLICATE_NODE] += 1
                    continue
                done.add((node, kind))
                if len(kinds[node]) == 1:
                    self.node(node, [(kind, row)], out)
                else:
                    pending.setdefault(node, []).append((kind, dict(row)))
        for node, parts in pending.items():
            self.node(node, parts, out)
        self.merged += len(pending)

    def node(self, node: str, parts: list[tuple[str, Row]], out: IO[str]) -> None:
        entity = ValueEntity(model[self.schema(node)], {"id": node_id(node), "datasets": [DATASET]})
        for kind, row in parts:
            for prop, value in self.properties(kind, row):
                if value:
                    entity.add(prop, value)
        entity.add("sourceUrl", NODE_URL.format(node))
        nr: dict[str, Any] = {"v": NR_VERSION, "source_ref": node}
        if not entity.schema.is_a("Address"):
            entity.add("icijId", node)
            if roles := self.addresses.get(node):
                entity.add("addressEntity", list(roles))
                nr["address_roles"] = roles
        self.write(out, entity, nr)

    def properties(self, kind: str, row: Row) -> Iterator[tuple[str, str | None]]:
        name = clean(row.get("name"))
        if kind == "address":
            yield "full", clean(row.get("address"))
        else:
            yield "name", name
        yield "publisher", clean(row.get("sourceID"))
        for code in (row.get("country_codes") or "").split(";"):
            yield "country", country_code(code)
        if kind == "entity":
            yield "previousName", clean(row.get("former_name"))
            original = clean(row.get("original_name"))
            yield "alias", original if original.casefold() != name.casefold() else None
        if kind in ("entity", "other"):
            yield "jurisdiction", country_code(clean(row.get("jurisdiction_description")))
            yield "incorporationDate", self.dates.parse(row.get("incorporation_date"))
            yield "dissolutionDate", self.dates.first(row, DISSOLUTION[kind])
        if kind in ("entity", "intermediary"):
            yield "status", clean(row.get("status"))


def fit(kind: str, source: Schema, target: Schema) -> str:
    """`kind`, or UnknownLink when the ends do not fit its FtM ranges (C1 R4: an Ownership
    asset may be any LegalEntity)."""
    schema = model[kind]
    start = schema.properties[schema.edge_source or ""].range
    end = schema.properties[schema.edge_target or ""].range
    fits_end = target.is_a(end) or (kind == "Ownership" and target.is_a("LegalEntity"))
    return kind if source.is_a(start) and fits_end else "UnknownLink"


def latest_download() -> tuple[Path, dict[str, Any], dict[str, Any]] | None:
    """(folder, download.json, the archive's entry) of the newest complete download."""
    product = layout.sources_dir(DATASET, PRODUCT, "latest").parent
    best: tuple[str, Path, dict[str, Any], dict[str, Any]] | None = None
    for folder in sorted(product.iterdir()) if product.is_dir() else []:
        try:
            record = json.loads((folder / RECORD).read_text(encoding="utf-8"))
        except OSError, ValueError:
            continue
        entry = next((e for e in record.get("files", []) if e.get("name") == ARCHIVE_FILE), None)
        if record.get("complete") and entry and (folder / ARCHIVE_FILE).is_file():
            stamp = str(record.get("completed_at", ""))
            if best is None or stamp > best[0]:
                best = (stamp, folder, record, entry)
    return best[1:] if best else None


def discover(client: HttpClient) -> list[RemoteFile]:
    """The archive's current version: a HEAD request, conditional on the last download."""
    latest = latest_download()
    headers = {}
    if latest and latest[2].get("etag"):
        headers["If-None-Match"] = latest[2]["etag"]
    if latest and latest[2].get("last_modified"):
        headers["If-Modified-Since"] = latest[2]["last_modified"]
    headers["Accept-Encoding"] = "identity"  # the size `fetch` checks is the file's own
    response = client.head(ARCHIVE_URL, headers=headers)
    if response.status_code == 304 and latest:  # not modified: `fetch` skips the file
        entry = latest[2]
        return [RemoteFile(ARCHIVE_FILE, ARCHIVE_URL, entry["version"], entry.get("size"), None)]
    if response.is_error:
        message = f"HEAD {redact(ARCHIVE_URL)}: HTTP {response.status_code}"
        raise HttpError(message, response.status_code)
    try:
        modified = email.utils.parsedate_to_datetime(response.headers["Last-Modified"])
        version = modified.astimezone(UTC).date().isoformat()
    except KeyError, TypeError, ValueError:
        version = datetime.now(UTC).date().isoformat()
    length = response.headers.get("Content-Length", "")
    size = int(length) if length.isdigit() else None
    return [RemoteFile(ARCHIVE_FILE, ARCHIVE_URL, version, size, None)]


def build(profile: Profile, context: BuildContext, *, today: date | None = None) -> BuildResult:
    options: IcijSource = profile.options(DATASET)
    found = latest_download()
    if found is None:
        message = f"{DATASET}: no complete download; run neonradar data fetch first"
        raise BuildError(message, "download", counts_only=True)
    folder, _, entry = found
    today = today or datetime.now(UTC).date()
    stem = context.out_dir / f"{DATASET}-{today:%Y%m%d}"
    records = stem.with_name(stem.name + "-records.ftm.jsonl")
    with zipfile.ZipFile(folder / ARCHIVE_FILE) as zf:
        archive = Archive(zf)
        selection = select(archive.rows, usable, options, postcode_districts(profile.sources))
        mapper = Mapper(selection, today)
        with (
            records.open("w", encoding="utf-8", newline="\n") as out,
            stem.with_name(stem.name + "-hints.csv").open("w", encoding="utf-8", newline="") as h,
        ):
            hints = csv.writer(h, lineterminator="\n")
            hints.writerow(("record_a", "record_b", "hint"))
            mapper.relationships(archive.rows(RELATIONSHIPS), out, hints)
            mapper.nodes(archive, out)
        version = archive.source_version()
    registered = load_registry().get(DATASET)
    contents = registered.licence.contents if registered else None
    write_manifest(
        records,
        dataset=DATASET,
        producer=Producer(name="neonradar_ingest.sources.icij.full", version=__version__),
        source=Source(
            urls=[stored_url(str(entry.get("url") or ARCHIVE_URL))],
            retrieved_at=entry.get("downloaded_at"),
            source_version=version or str(entry.get("version")),
        ),
        skipped=dict(mapper.skipped),
        notes=[
            *DISCLAIMER,
            f"Contents licence {contents} (ICIJ FAQ); the database licence is in licence.",
            f"Slice mode {options.mode}; hints in {stem.name}-hints.csv.",
        ],
    )
    counts: dict[str, Any] = {
        **selection.counts(),
        "records_by_schema": {k.lower(): v for k, v in sorted(mapper.schemas.items())},
        "links_by_class": dict(sorted(mapper.links.items())),
        **{key: mapper.hints[key] for key in HINT_COUNTS},
        "nodes_merged_across_files": mapper.merged,
        "unknown_links_by_value": dict(mapper.unknown_links.most_common()),
        "unknown_rel_types_by_value": dict(mapper.unknown_rel_types.most_common()),
        "dates": dict(sorted(mapper.dates.counts.items())),
        "skipped": {re.sub(r"[^a-z0-9]+", "_", k): v for k, v in sorted(mapper.skipped.items())},
        "columns_extra": dict(sorted(archive.extra.items())),
    }
    strings = {"mode": options.mode, "version": str(entry.get("version")),
               "source_version": version or ""}  # fmt: skip
    return BuildResult(counts, strings, {"columns_absent": archive.absent})


register_source_model(DATASET, IcijSource)
register_source(SourceSpec(DATASET, discover))
register_builder(
    Builder(DATASET, build, string_keys=("mode", "source_version"), list_keys=("columns_absent",))
)
