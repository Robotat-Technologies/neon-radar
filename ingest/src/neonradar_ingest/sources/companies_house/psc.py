"""The PSC snapshot: discovery, reading, the `psc-index` and `psc` steps (PHASE-2.md M2.3b).

The daily product (`psc`) is a set of zip parts `psc-snapshot-<date>_<N>of<M>.zip` listed on
`en_pscdata.html` (research note bulk-sources-loading.md 3.1). Each member holds one JSON
object per line, `{"company_number": ..., "data": {...}}`, read as bytes and parsed with
orjson; a line without `company_number` is a totals record, used as a completeness check
(note 3.2). Pass 1 (`psc-index`) writes `corporate_pscs.sqlite`; pass 2 (`psc`) writes the
PSC, `Ownership` and `Control` records of the slice companies. Unknown kinds and natures of
control are counted by value, never dropped silently. Only the fields in the M2.3b table are
read: a usual residential address and any day of birth never are, and the title is removed
from the front of an individual's `name`. Messages and counts name parts, kinds and
enumeration values, never a value from a record.
"""

import hashlib
import json
import re
import sqlite3
import zipfile
from collections import Counter
from collections.abc import Collection, Iterator, Mapping, Sequence
from pathlib import Path
from typing import Any

import orjson

from neonradar_contracts.records import Producer, Source, iter_records, make_id, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data.sources import RemoteFile
from neonradar_ingest.http import HttpClient
from neonradar_ingest.sources.companies_house import bulk, natures, records
from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_ingest.sources.companies_house.identification import (
    is_uk,
    resolve_corporate,
    uk_number,
)
from neonradar_keys.countries import country_code

PRODUCT = "psc"
PAGE_URL = "https://download.companieshouse.gov.uk/en_pscdata.html"
PART_RE = re.compile(r"psc-snapshot-(\d{4}-\d{2}-\d{2})_(\d+)of(\d+)\.zip\Z")
RECORD_FILE = "psc.ftm.jsonl"
TOTALS = "totals#persons-of-significant-control-snapshot"
TOTAL_COUNTS = ("persons_of_significant_control_count", "statements_count", "exemptions_count")
SCHEMAS = {
    "individual-person-with-significant-control": "Person",
    "individual-beneficial-owner": "Person",
    "corporate-entity-person-with-significant-control": "Company",
    "corporate-entity-beneficial-owner": "Company",
    "legal-person-person-with-significant-control": "Organization",
    "legal-person-with-significant-control": "Organization",
    "legal-person-beneficial-owner": "Organization",
}
SUPER_SECURE = ("super-secure-person-with-significant-control", "super-secure-beneficial-owner")
STATEMENT = "persons-with-significant-control-statement"
EXEMPTIONS = "exemptions"
KNOWN_KINDS = (*SCHEMAS, *SUPER_SECURE, STATEMENT, EXEMPTIONS)
OUTCOMES = ("resolved", "name_mismatch", "number_not_found", "no_number", "non_uk")
ADDRESS = (
    "po_box",
    "address_line_1",
    "address_line_2",
    "locality",
    "region",
    "postal_code",
    "country",
)
# Counters the summary always shows, also when zero (as M2.3a's `records.COUNTED`).
INDEX_COUNTED = ("ceased_skipped", "statements_ceased_skipped", "super_secure_ceased_skipped")
READ_COUNTED = ("lines_read", "lines_malformed", "totals_lines")
PSC_COUNTED = (
    "beneficial_owners_sanctioned",
    "ceased_skipped",
    "duplicate_pscs",
    "lines_not_psc",
    "lines_other_companies",
    "nationalities_unmapped",
    "natures_unknown",
    "psc_address_country_unmapped",
    "pscs_without_address_key",
    "pscs_without_id",
    "pscs_without_known_nature",
    "pscs_without_name",
    "titles_kept",
    "titles_removed",
    "with_identity_verification_details",
)
VALUE_RE = re.compile(r"[a-z0-9][a-z0-9 ._#:/()&,'-]{0,79}\Z")  # a `_by_value` key (M2.2)
BATCH = 10_000

Line = tuple[str, dict[str, Any]]


def discover(client: HttpClient) -> list[RemoteFile]:
    """The parts of the newest PSC snapshot with every part listed (product `psc`)."""
    return bulk.discover_parts(client, PAGE_URL, PART_RE, PRODUCT)


def vocabulary(value: object) -> str:
    """An enumeration value as a `_by_value` key: lower case, or `unprintable` (M2.2)."""
    text = value.strip().lower() if isinstance(value, str) else ""
    return text if VALUE_RE.fullmatch(text) else "unprintable"


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _address(data: Mapping[str, Any]) -> dict[str, Any]:
    """The service or registered address (`principal_office_address` for some owners)."""
    return _dict(data.get("address")) or _dict(data.get("principal_office_address"))


def _identification(data: Mapping[str, Any]) -> dict[str, str | None]:
    return {k: v for k, v in _dict(data.get("identification")).items() if isinstance(v, str)}


def _natures(data: Mapping[str, Any]) -> list[str]:
    values = data.get("natures_of_control")
    return [v for v in values if isinstance(v, str)] if isinstance(values, list) else []


def psc_id(data: Mapping[str, Any]) -> str | None:
    """The last path segment of `data.links.self` (PHASE-2.md 4.4)."""
    link = _str(_dict(data.get("links")).get("self"))
    segment = link.rstrip("/").rsplit("/", 1)[-1].strip() if link else ""
    return segment or None


class Reader:
    """One pass over the parts: the data lines, with line counts and the totals check."""

    def __init__(self, parts: Sequence[Path]) -> None:
        self.parts = parts
        self.stats: Counter[str] = Counter(dict.fromkeys(READ_COUNTED, 0))
        self.totals: int | None = None

    def __iter__(self) -> Iterator[Line]:
        for part in self.parts:
            with zipfile.ZipFile(part) as archive:
                for member in archive.namelist():
                    if member.endswith("/"):
                        continue
                    with archive.open(member) as raw:
                        for line in raw:
                            if line.strip():
                                yield from self._line(line)

    def _line(self, line: bytes) -> Iterator[Line]:
        try:
            item = orjson.loads(line)
        except orjson.JSONDecodeError:
            item = None
        item = _dict(item)
        data, number = item.get("data"), item.get("company_number")
        if number is None and isinstance(data, dict) and data.get("kind") == TOTALS:
            self.stats["totals_lines"] += 1
            found = [data.get(key) for key in TOTAL_COUNTS]
            self.totals = (self.totals or 0) + sum(
                n for n in found if isinstance(n, int) and not isinstance(n, bool)
            )
            return
        self.stats["lines_read"] += 1
        if not isinstance(data, dict) or not isinstance(number, str) or not number.strip():
            self.stats["lines_malformed"] += 1
            return
        yield number.strip(), data

    @property
    def totals_check(self) -> str:
        """`passed` when the data lines read equal the totals' three counts, else `failed`;
        `absent` without a totals line (whether every part has one is unknown, note 3.2)."""
        if self.totals is None:
            return "absent"
        return "passed" if self.stats["lines_read"] == self.totals else "failed"


class IndexNames(Mapping[str, str]):
    """Company names in `companies.sqlite`, looked up one number at a time."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def __getitem__(self, number: str) -> str:
        row = self.connection.execute("SELECT name FROM company WHERE number = ?", (number,))
        found = row.fetchone()
        if found is None or not found[0]:
            raise KeyError(number)
        return str(found[0])

    def __iter__(self) -> Iterator[str]:
        return (str(n) for (n,) in self.connection.execute("SELECT number FROM company"))

    def __len__(self) -> int:
        return int(self.connection.execute("SELECT count(*) FROM company").fetchone()[0])


def _read_only(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path.absolute().as_uri() + "?mode=ro", uri=True)


def build_index(
    parts: Sequence[Path], path: Path, company_index: Path, include_ceased: bool, version: str
) -> tuple[dict[str, Any], str]:
    """The `psc-index` step (deliverable 6): counts and the totals check.

    Table `corporate_psc` gets every corporate and legal-person PSC (a ceased one only with
    `include_ceased`, as the `psc` step loads them) with its outcome and normalised number;
    table `statement` every statement value without `ceased_on`, super-secure kind and
    exemption key; table `meta` the snapshot `version`. Indexes are created before the inserts
    and temporary storage stays in memory, so SQLite never sorts values into a file outside
    the work folder.
    """
    reader = Reader(parts)
    stats = reader.stats
    stats.update(dict.fromkeys(INDEX_COUNTED, 0))
    names_of = ("kinds", "unknown_kinds", "unknown_natures", "countries")
    by: dict[str, Counter[str]] = {name: Counter() for name in names_of}
    outcomes: Counter[str] = Counter()
    temporary = path.with_name(path.name + ".tmp")
    temporary.unlink(missing_ok=True)
    index = _read_only(company_index)
    try:
        connection = sqlite3.connect(temporary)
    except BaseException:
        index.close()
        raise
    try:
        for pragma in ("journal_mode=OFF", "synchronous=OFF", "temp_store=MEMORY"):
            connection.execute(f"PRAGMA {pragma}")
        connection.execute("CREATE TABLE meta(key TEXT PRIMARY KEY, value TEXT)")
        connection.execute("INSERT INTO meta VALUES ('version', ?)", (version,))
        connection.execute(
            "CREATE TABLE corporate_psc(company_number TEXT, psc_id TEXT, outcome TEXT,"
            " number TEXT)"
        )
        connection.execute("CREATE TABLE statement(company_number TEXT, value TEXT)")
        connection.execute("CREATE INDEX corporate_psc_company ON corporate_psc(company_number)")
        connection.execute("CREATE INDEX corporate_psc_number ON corporate_psc(outcome, number)")
        names = IndexNames(index)
        pscs: list[tuple[str, str, str, str | None]] = []
        statements: list[tuple[str, str]] = []
        for number, data in reader:
            kind = _str(data.get("kind")) or ""
            if kind not in KNOWN_KINDS:
                by["unknown_kinds"][vocabulary(kind)] += 1
                continue
            by["kinds"][kind] += 1
            if kind in SCHEMAS:
                for value in _natures(data):
                    if natures.classify(value) is None:
                        by["unknown_natures"][vocabulary(value)] += 1
                if data.get("ceased_on") and not include_ceased:
                    stats["ceased_skipped"] += 1
                elif SCHEMAS[kind] != "Person":
                    address_country = _str(_address(data).get("country"))
                    name = bulk.text(_str(data.get("name"))) or ""
                    ident = _identification(data)
                    outcome, found = resolve_corporate(name, ident, address_country, names)
                    outcomes[outcome] += 1
                    if outcome == "non_uk":
                        code = country_code(ident.get("country_registered"))
                        by["countries"][code or ""] += 1
                    pscs.append((number, psc_id(data) or "", outcome, found))
            elif kind in SUPER_SECURE:
                if data.get("ceased") is True or data.get("ceased_on"):
                    stats["super_secure_ceased_skipped"] += 1
                else:
                    statements.append((number, kind))
            elif kind == STATEMENT:
                statement = _str(data.get("statement"))
                if data.get("ceased_on"):
                    stats["statements_ceased_skipped"] += 1
                elif statement:
                    statements.append((number, statement))
            else:
                statements.extend((number, key) for key in sorted(_dict(data.get(EXEMPTIONS))))
            if len(pscs) + len(statements) >= BATCH:
                _flush(connection, pscs, statements)
        _flush(connection, pscs, statements)
        stats["corporate_psc_rows"] = connection.execute(
            "SELECT count(*) FROM corporate_psc"
        ).fetchone()[0]
        stats["statement_rows"] = connection.execute("SELECT count(*) FROM statement").fetchone()[0]
        connection.commit()
        connection.close()
        temporary.replace(path)
    except BaseException:
        connection.close()
        temporary.unlink(missing_ok=True)  # it holds the rows read so far
        raise
    finally:
        index.close()
    unmapped = by["countries"].pop("", 0)
    counts: dict[str, Any] = {
        "parts": len(parts),
        **dict(sorted(stats.items())),
        "kinds_by_value": dict(sorted(by["kinds"].items())),
        "unknown_kinds_by_value": dict(sorted(by["unknown_kinds"].items())),
        "unknown_natures_by_value": dict(sorted(by["unknown_natures"].items())),
        "outcomes": {outcome: outcomes[outcome] for outcome in OUTCOMES},
        "non_uk_countries_by_value": dict(sorted(by["countries"].items())),
        "non_uk_country_unmapped": unmapped,
    }
    return counts, reader.totals_check


def _flush(
    connection: sqlite3.Connection,
    pscs: list[tuple[str, str, str, str | None]],
    statements: list[tuple[str, str]],
) -> None:
    connection.executemany("INSERT INTO corporate_psc VALUES (?,?,?,?)", pscs)
    connection.executemany("INSERT INTO statement VALUES (?,?)", statements)
    pscs.clear()
    statements.clear()


def expansion(
    psc_index: Path, company_index: Path, parent_depth: int, child_depth: int, seed: int
) -> slices.Expansion:
    """The slice step's expansion through `resolved` corporate PSCs (deliverable 7).

    A parent is the normalised number of a resolved corporate PSC of a company in the set (so
    it is in the index); a child is a company in the index whose resolved corporate PSC is.
    """

    def expand(base: Collection[str]) -> list[slices.Member]:
        connection = _read_only(psc_index)
        try:
            connection.execute("PRAGMA temp_store=MEMORY")
            connection.execute(
                "ATTACH DATABASE ? AS idx", (company_index.absolute().as_uri() + "?mode=ro",)
            )
            parents = (
                "SELECT number FROM corporate_psc WHERE outcome = 'resolved' AND company_number = ?"
            )
            children = (
                "SELECT p.company_number FROM corporate_psc p JOIN idx.company c"
                " ON c.number = p.company_number WHERE p.outcome = 'resolved' AND p.number = ?"
            )

            def parents_of(number: str) -> list[str]:
                return [str(n) for (n,) in connection.execute(parents, (number,))]

            def children_of(number: str) -> list[str]:
                return [str(n) for (n,) in connection.execute(children, (number,))]

            return slices.expand(base, parents_of, children_of, parent_depth, child_depth, seed)
        finally:
            connection.close()

    return expand


def birth_month(value: object) -> str | None:
    """`yyyy-mm` from `{month, year}`; a day, if one were given, is never read (note 3.3)."""
    month, year = _dict(value).get("month"), _dict(value).get("year")
    if isinstance(month, int) and isinstance(year, int) and 1 <= month <= 12 and year > 0:
        return f"{year:04d}-{month:02d}"
    return None


def interest_id(kind: str, psc_record: str, number: str, key: str) -> str:
    """`gbch-ownership-` or `gbch-control-` plus 20 hex of SHA-1 of the joined parts (4.4)."""
    digest = hashlib.sha1(f"{psc_record}|{number}|{key}".encode(), usedforsecurity=False)
    return f"{records.PREFIX}-{kind}-{digest.hexdigest()[:20]}"


class PscWriter(records.Writer):
    """The PSC records of the slice: one per PSC, one per interest, addresses shared by key."""

    def __init__(self, known_addresses: set[str]) -> None:
        super().__init__(None)
        self.stats = Counter(dict.fromkeys(PSC_COUNTED, 0))
        self.known_addresses = known_addresses

    def psc_address(self, address: Mapping[str, Any], role: str) -> dict[str, str]:
        """`{address id: role}`, or empty when the address gives no key (counted)."""
        part = {name: _str(address.get(name)) for name in ADDRESS}
        premises = _str(address.get("premises"))
        if premises:
            part["address_line_1"] = f"{premises} {part['address_line_1'] or ''}"
        cleaned = [bulk.address_part(part[name]) for name in ADDRESS]
        found = self.add_address(cleaned, default_country=None)  # no country is assumed
        if found is None:
            self.stats["pscs_without_address_key"] += 1
            return {}
        self.stats["psc_address_country_unmapped"] += country_code(cleaned[6]) is None
        return {found[1]: role}

    def psc(self, kind: str, data: Mapping[str, Any], segment: str) -> dict[str, Any] | None:
        """The PSC's `Person`, `Company` or `Organization` record (rules 3 and 5)."""
        schema, stats = SCHEMAS[kind], self.stats
        values: dict[str, Any] = {"name": bulk.text(_str(data.get("name")))}
        address, elements = _address(data), _dict(data.get("name_elements"))
        title = bulk.text(_str(elements.get("title")))
        name, size = values["name"], len(title or "")
        if (
            schema == "Person"
            and name
            and title
            and name[:size].casefold() == title.casefold()
            and name[size : size + 1] == " "
        ):
            values["name"] = bulk.text(name[size:])  # the title is not loaded
            stats["titles_removed"] += 1
        elif schema == "Person" and title:
            stats["titles_kept"] += 1  # `name` does not start with it: kept as given
        if values["name"] is None:
            stats["pscs_without_name"] += 1  # FtM needs a name (R3)
            return None
        if schema == "Person":
            demonyms = (_str(data.get("nationality")) or "").split(",")
            nationality = [country_code(d) for d in demonyms if d.strip()]
            stats["nationalities_unmapped"] += nationality.count(None)
            values |= {
                "firstName": bulk.text(_str(elements.get("forename"))),
                "middleName": bulk.text(_str(elements.get("middle_name"))),
                "lastName": bulk.text(_str(elements.get("surname"))),
                "birthDate": birth_month(data.get("date_of_birth")),
                "nationality": nationality,
                "country": country_code(_str(data.get("country_of_residence"))),
            }
        else:
            ident = _identification(data)
            values["legalForm"] = bulk.text(ident.get("legal_form"))
            if is_uk(ident, _str(address.get("country"))):
                number, values["jurisdiction"] = uk_number(ident.get("registration_number")), "gb"
            else:
                number = bulk.text(ident.get("registration_number"))
                values["jurisdiction"] = country_code(ident.get("country_registered"))
            if schema == "Company":
                values["registrationNumber"] = number
        if kind.endswith("beneficial-owner") and data.get("is_sanctioned") is True:
            values["topics"] = "sanction"  # stated by the register of overseas entities (3.7)
            stats["beneficial_owners_sanctioned"] += 1
        entity = self._entity(schema, make_id(records.PREFIX, "psc", segment), values)
        nr: dict[str, Any] = {"v": records.NR_VERSION, "source_ref": segment}
        if roles := self.psc_address(address, "service" if schema == "Person" else "registered"):
            entity.add("addressEntity", next(iter(roles)))
            nr["address_roles"] = roles
        return {**entity.to_dict(), "nr": nr}

    def interests(self, number: str, data: Mapping[str, Any], owner: str) -> list[dict[str, Any]]:
        """One `Ownership` or `Control` per interest of the PSC in the company (rule 4)."""
        found = [n for n in map(natures.classify, _natures(data)) if n is not None]
        company = make_id(records.PREFIX, "co", number)
        out = []
        for interest in natures.interests(found):
            ownership = interest.kind == "ownership"
            label = "ownership" if ownership else "control"
            band = interest.band
            values: dict[str, Any] = {
                ("owner" if ownership else "controller"): owner,
                ("asset" if ownership else "controlled"): company,
                ("ownershipType" if ownership else "controlType"): interest.type_label,
                "role": list(interest.values),
                "startDate": _str(data.get("notified_on")),
                "endDate": _str(data.get("ceased_on")),
            }
            nr: dict[str, Any] = {
                "v": records.NR_VERSION,
                "natures_of_control": list(interest.values),
            }
            if band is not None:
                if ownership:
                    values["percentage"] = band.percentage
                nr |= {"share_pct_min": float(band.pct_min), "share_pct_max": float(band.pct_max)}
                nr |= {"share_pct_min_exclusive": True} if band.min_exclusive else {}
                nr |= {"share_pct_max_exclusive": True} if band.max_exclusive else {}
            rid = interest_id(label, owner, number, interest.key)
            schema = "Ownership" if ownership else "Control"
            out.append({**self._entity(schema, rid, values).to_dict(), "nr": nr})
        return out


def written(path: Path) -> tuple[set[str], set[str]]:
    """The `Company` and `Address` record ids of the `companies` step's file."""
    companies: set[str] = set()
    addresses: set[str] = set()
    for record in iter_records(path):
        if record.get("schema") == "Company":
            companies.add(str(record.get("id")))
        elif record.get("schema") == "Address":
            addresses.add(str(record.get("id")))
    return companies, addresses


def write_pscs(
    parts: Sequence[Path],
    slice_csv: Path,
    companies_file: Path,
    out_dir: Path,
    *,
    include_ceased: bool,
    version: str,
    urls: Sequence[str],
) -> tuple[dict[str, Any], str]:
    """The `psc` step (deliverable 8): records of the slice companies; counts, totals check.

    Only companies with a record in `companies_file` get PSCs, so every link resolves; their
    addresses already in that file are linked, not written again.
    """
    company_ids, address_ids = written(companies_file)
    numbers = {
        number
        for number, _, _ in slices.read(slice_csv)
        if make_id(records.PREFIX, "co", number) in company_ids
    }
    writer, reader = PscWriter(address_ids), Reader(parts)
    stats, loaded = writer.stats, Counter[str]()
    seen: set[str] = set()
    path = out_dir / RECORD_FILE
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for number, data in reader:
            kind = _str(data.get("kind")) or ""
            if number not in numbers:
                stats["lines_other_companies"] += 1
                continue
            if kind not in SCHEMAS:  # statements are in the index, unknown kinds counted there
                stats["lines_not_psc"] += 1
                continue
            if data.get("ceased_on") and not include_ceased:
                stats["ceased_skipped"] += 1
                continue
            segment = psc_id(data)
            if segment is None or segment in seen:
                stats["pscs_without_id" if segment is None else "duplicate_pscs"] += 1
                continue
            owner = make_id(records.PREFIX, "psc", segment)
            interests = writer.interests(number, data, owner)
            unknown = sum(natures.classify(value) is None for value in _natures(data))
            if not interests:
                stats["pscs_without_known_nature"] += 1  # no link to load: no record either
                stats["natures_unknown"] += unknown
                continue
            record = writer.psc(kind, data, segment)
            if record is None:
                continue  # without a name (counted)
            stats["natures_unknown"] += unknown
            # Counted, never read: identity verification details (as the M1.8a mapping does).
            stats["with_identity_verification_details"] += "identity_verification_details" in data
            seen.add(segment)
            loaded[kind] += 1
            for item in (record, *interests):
                handle.write(json.dumps(item, ensure_ascii=False) + "\n")
        for key in sorted(writer.addresses):
            handle.write(json.dumps(writer.addresses[key], ensure_ascii=False) + "\n")
    producer = Producer(name="neonradar_ingest.sources.companies_house", version=__version__)
    write_manifest(
        path,
        dataset=bulk.DATASET,
        producer=producer,
        source=Source(urls=list(urls), source_version=version),
    )
    schemas = Counter(record["schema"].lower() for record in iter_records(path))
    counts: dict[str, Any] = {
        "parts": len(parts),
        "slice_companies": len(numbers),
        "records": dict(sorted(schemas.items())),
        "loaded_by_kind_by_value": dict(sorted(loaded.items())),
        **dict(sorted({**reader.stats, **stats}.items())),
    }
    return counts, reader.totals_check
