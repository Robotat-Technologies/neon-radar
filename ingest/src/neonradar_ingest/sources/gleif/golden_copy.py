"""The GLEIF Golden Copy loader, dataset `gleif_lei` (PHASE-2.md M2.4).

Discovery reads the combined `publishes/latest` endpoint (`lei2/latest` once served an older
publish, research note bulk-sources-loading.md 6.1) and takes the full CSV files of type `lei2`
(LEI-CDF 3.1) and `rr` (RR-CDF 2.1); the version is the publish date and time, `20261021-1600`.
The builder streams each zip member through `csv.DictReader` (quoted fields may hold line
breaks, note 6.2), never extracting it: a first pass over the LEI file finds the LEIs in scope,
a pass over the RR file adds their direct and ultimate consolidating parents, a second pass over
the LEI file writes `Company` and `Address` records, and a last pass over the RR file writes the
consolidation relationships as `Ownership` with `nr.consolidation`, which C2 maps to
`CONSOLIDATES`, never to `OWNS`: Level 2 data is accounting consolidation, not ownership
(note 6.3), so no share is ever set. Messages name files, columns and counts, never a value.
"""

import csv
import hashlib
import io
import json
import re
import unicodedata
import zipfile
from collections import Counter
from collections.abc import Iterator, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Literal, TextIO
from urllib.parse import urlsplit

from followthemoney import ValueEntity, model, registry
from pydantic import BaseModel, ConfigDict, StrictBool

from neonradar_contracts.records import Producer, Source, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data import layout
from neonradar_ingest.data.download import RECORD, DownloadError
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
from neonradar_ingest.http import HttpClient
from neonradar_ingest.sources.companies_house import bulk as ch_bulk
from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_ingest.sources.companies_house.build import SLICE, SLICE_META, StepInputMissing
from neonradar_ingest.sources.gleif.mapping import NAME_PROPERTY, entity_id
from neonradar_keys.addresses import address_key
from neonradar_keys.countries import country_code
from neonradar_keys.ids import is_valid_lei, uk_company_number
from neonradar_keys.postcodes import normalise_uk_postcode

DATASET = "gleif_lei"
PRODUCT = "golden-copy"
PREFIX = "gleif"
NR_VERSION = "1.1"
PUBLISHES_URL = "https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest"
HOST = "goldencopy.gleif.org"
CDF = {"lei2": "LEI_3.1", "rr": "RR_2.1"}  # file type: the CDF version the mapping is for
FILE_RE = re.compile(r"(\d{8}-\d{4})-gleif-goldencopy-(lei2|rr)-golden-copy\.csv\.zip\Z")
PUBLISH_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2})")
ISO_RE = re.compile(r"\s*(\d{4})-(\d{2})-(\d{2})(?:T[\d:.]+)?(?:Z|[+-]\d{2}:?\d{2})?\s*\Z")
VOCAB_RE = re.compile(r"[a-z][a-z_-]{0,47}\Z")  # no digits: never an LEI or a number
HEADER_RE = re.compile(r"[A-Za-z0-9 ._:/+()#,'&-]{1,80}\Z")  # what a summary list may hold
UK_AUTHORITIES = ("RA000585", "RA000586", "RA000587")  # Companies House: E&W, NI, Scotland
AUTHORITY = "Entity.RegistrationAuthority.RegistrationAuthorityID"
ENTITY_ID = "Entity.RegistrationAuthority.RegistrationAuthorityEntityID"
REGISTRATION = "Registration.RegistrationStatus"
CREATION = "Entity.EntityCreationDate"
SKIPPED_REGISTRATIONS = ("ANNULLED", "DUPLICATE")
LEI_COLUMNS = (  # the enforced set of note 6.2
    "LEI", "Entity.LegalName", "Entity.LegalName.xmllang", "Entity.LegalJurisdiction",
    "Entity.EntityStatus", "Entity.EntityCategory", "Entity.LegalForm.EntityLegalFormCode",
    "Entity.LegalForm.OtherLegalForm", AUTHORITY,
    "Entity.RegistrationAuthority.OtherRegistrationAuthorityID", ENTITY_ID, REGISTRATION,
    "Registration.InitialRegistrationDate", "Registration.LastUpdateDate",
    "Entity.LegalAddress.FirstAddressLine", "Entity.LegalAddress.City",
    "Entity.LegalAddress.Country", "Entity.HeadquartersAddress.FirstAddressLine",
    "Entity.HeadquartersAddress.City", "Entity.HeadquartersAddress.Country",
)  # fmt: skip
START, END = "Relationship.StartNode.NodeID", "Relationship.EndNode.NodeID"
START_TYPE, END_TYPE = "Relationship.StartNode.NodeIDType", "Relationship.EndNode.NodeIDType"
TYPE, STATUS = "Relationship.RelationshipType", "Relationship.RelationshipStatus"
RR_COLUMNS = (START, START_TYPE, END, TYPE, STATUS)
# Other names by their `.type` column through the spike's NAME_PROPERTY (reconciliation C6:
# a previous legal name is `previousName`, an automatic transliteration is never written, C1
# R10). Without a `.type` column an other name is an alias and a transliterated one is skipped.
ALIAS_GROUPS = {
    "other_entity_names": "Entity.OtherEntityNames.OtherEntityName.{}",
    "transliterated_other_entity_names":
        "Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.{}",
}  # fmt: skip
PERIOD_RE = re.compile(r"Relationship\.Period\.(\d+)\.periodType\Z")
QUANTIFIER_RE = re.compile(
    r"Relationship\..+\.(MeasurementMethod|QuantifierAmount|QuantifierUnits)\Z"
)
CONSOLIDATION = {
    "IS_DIRECTLY_CONSOLIDATED_BY": "direct",
    "IS_ULTIMATELY_CONSOLIDATED_BY": "ultimate",
}
# Address parts in the order that makes up `Address.full` (and its key, M2.3a deliverable 7).
# Region (an ISO 3166-2 code) is kept as `region` but left out of the key, as are the house
# number fields and MailRouting, which can hold a person's name.
ADDRESS_PARTS = ("FirstAddressLine", "AdditionalAddressLine.1", "AdditionalAddressLine.2",
                 "AdditionalAddressLine.3", "City", "PostalCode", "Country")  # fmt: skip
ROLES = {"LegalAddress": "registered", "HeadquartersAddress": "business"}
SOURCE_URL = "https://search.gleif.org/#/record/{}"
RECORD_FILE = "golden-copy.ftm.jsonl"

Row = dict[str, str]


# --- discovery (`neonradar data fetch`) ------------------------------------------------------


def publish_version(value: object) -> str:
    """`2026-10-21 16:00:00` to `20261021-1600`; DownloadError for anything else."""
    match = PUBLISH_RE.match(value) if isinstance(value, str) else None
    if not match:
        raise DownloadError("discover: the publish has no publish_date", "discover")
    return "{}{}{}-{}{}".format(*match.groups())


def discover(client: HttpClient) -> list[RemoteFile]:
    """The full `lei2` and `rr` CSV files of the latest combined publish (one version)."""
    body = client.get_json(PUBLISHES_URL)
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        raise DownloadError("discover: the publish has no data object", "discover")
    version = publish_version(data.get("publish_date"))
    files = []
    for kind, cdf in CDF.items():
        section = data.get(kind)
        section = section if isinstance(section, dict) else {}
        full = section.get("full_file")
        entry = full.get("csv") if isinstance(full, dict) else None
        if not isinstance(entry, dict):
            raise DownloadError(f"discover: the publish lists no {kind} CSV file", "discover")
        if publish_version(section.get("publish_date")) != version:
            raise DownloadError(f"discover: the {kind} file is from another publish", "discover")
        if entry.get("cdf_version") != cdf:
            raise DownloadError(f"discover: the {kind} file is not {cdf}; stopped", "format")
        url = str(entry.get("url", ""))
        name = url.rsplit("/", 1)[-1]
        match = FILE_RE.fullmatch(name)
        where = urlsplit(url)
        if (where.scheme, where.hostname) != ("https", HOST) or not match or match[1] != version:
            raise DownloadError(f"discover: the {kind} URL is not a Golden Copy CSV", "discover")
        size = entry.get("size")
        size = size if isinstance(size, int) and not isinstance(size, bool) else None
        files.append(RemoteFile(name, url, version, size, None, product=PRODUCT))
    return files


register_source(SourceSpec(DATASET, discover))


# --- reading ---------------------------------------------------------------------------------


@dataclass(slots=True)
class Table:
    """One zipped CSV file of the publish, read row by row as {column: value}."""

    path: Path
    enforced: Sequence[str]
    stats: Counter[str]
    header: list[str] = field(default_factory=list)

    def rows(self) -> Iterator[Row]:
        name = self.path.name
        with zipfile.ZipFile(self.path) as archive:
            members = [m for m in archive.namelist() if not m.endswith("/")]
            if len(members) != 1:
                raise BuildError(f"{name}: {len(members)} files inside, expected one CSV",
                                 "format", counts_only=True)  # fmt: skip
            with archive.open(members[0]) as raw:
                text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="strict", newline="")
                reader = csv.DictReader(text)
                try:
                    self.header = [cell.strip() for cell in reader.fieldnames or []]
                    missing = [column for column in self.enforced if column not in self.header]
                    if missing:
                        raise BuildError(f"{name}: column {missing[0]} is missing", "header",
                                         counts_only=True)  # fmt: skip
                    reader.fieldnames = self.header
                    for row in reader:
                        if None in row or None in row.values():
                            self.stats["bad_field_count_rows"] += 1
                            continue
                        self.stats["rows_read"] += 1
                        yield row
                except UnicodeDecodeError:
                    raise BuildError(f"{name}: not valid UTF-8; stopped", "encoding",
                                     counts_only=True) from None  # fmt: skip
                except csv.Error:
                    raise BuildError(f"{name}: not readable as CSV near line {reader.line_num}",
                                     "format", counts_only=True) from None  # fmt: skip


def text(value: str | None) -> str | None:
    """NFC with white space (line breaks included) collapsed; None when empty."""
    cleaned = " ".join(unicodedata.normalize("NFC", value).split()) if value else ""
    return cleaned or None


def iso_date(value: str | None, stats: Counter[str], what: str) -> str | None:
    """The date of an ISO date or date and time with an offset (`2012-06-06T15:52:00+02:00`
    gives `2012-06-06`, as `lists.common.parse_iso` does); anything else is counted."""
    if not value or not value.strip():
        return None
    if match := ISO_RE.fullmatch(value):
        try:
            return date(int(match[1]), int(match[2]), int(match[3])).isoformat()
        except ValueError:
            pass
    stats[f"dates_dropped.{what}"] += 1
    return None


def vocab(value: str) -> str:
    """An enumeration value as a summary key (`_by_value`); anything unexpected is `other`."""
    key = value.strip().lower()
    return key if VOCAB_RE.fullmatch(key) else "other"


def hashed_id(kind: str, *parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode(), usedforsecurity=False).hexdigest()[:20]
    return f"{PREFIX}-{kind}-{digest}"


def loadable(row: Row) -> str | None:
    """The row's LEI when it may load: a valid LEI whose registration is not annulled or a
    duplicate."""
    lei = row["LEI"].strip().upper()
    if not is_valid_lei(lei) or row[REGISTRATION].strip().upper() in SKIPPED_REGISTRATIONS:
        return None
    return lei


# --- the profile block and the scope ---------------------------------------------------------


class GleifSource(BaseModel):
    """The `gleif_lei` block of a profile (PHASE-2.md 7.8); `all` exists for tests only."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    scope: Literal["slice", "uk", "all"] = "slice"


register_source_model(DATASET, GleifSource)


def in_scope(
    lei_file: Table, scope: str, numbers: set[str], counts: Counter[str]
) -> dict[str, str]:
    """First pass: {LEI: scope reason} for the LEIs the scope keeps; skips are counted here."""
    found: dict[str, str] = {}
    matched: set[str] = set()
    for row in lei_file.rows():
        lei = loadable(row)
        if lei is None:
            if is_valid_lei(row["LEI"].strip()):
                counts[f"registration_skipped.{vocab(row[REGISTRATION])}"] += 1
            else:
                counts["invalid_leis"] += 1
            continue
        uk = row[AUTHORITY].strip().upper() in UK_AUTHORITIES
        counts["uk_authority_leis"] += uk
        number = uk_company_number(row[ENTITY_ID]) if uk and scope == "slice" else None
        if scope == "all" or (uk and scope == "uk"):
            found.setdefault(lei, scope)
        elif number is not None and number in numbers:
            found.setdefault(lei, "slice")
            matched.add(number)
    counts["slice_companies_with_lei"] = len(matched)
    return found


def consolidation(row: Row) -> tuple[str, str, str] | None:
    """(child, parent, `direct` or `ultimate`) for an active consolidation between two LEIs."""
    level = CONSOLIDATION.get(row[TYPE].strip())
    if level is None or row[STATUS].strip().upper() != "ACTIVE":
        return None
    if {row[START_TYPE].strip().upper(), row.get(END_TYPE, "LEI").strip().upper()} != {"LEI"}:
        return None
    return row[START].strip().upper(), row[END].strip().upper(), level


def add_parents(rr_file: Table, wanted: dict[str, str]) -> None:
    """The RR pass between the two LEI passes: direct and ultimate parents of the scoped LEIs."""
    children = set(wanted)
    for row in rr_file.rows():
        if (link := consolidation(row)) and link[0] in children:
            wanted.setdefault(link[1], "parent")


# --- records ---------------------------------------------------------------------------------


class Writer:
    """Builds the records; `Address` records are shared by key across the dataset."""

    def __init__(self, header: Sequence[str], counts: Counter[str]) -> None:
        self.counts = counts
        self.addresses: dict[str, dict[str, Any]] = {}
        self.names = [(pattern.format(n), group) for group, pattern in ALIAS_GROUPS.items()
                      for n in range(1, 6) if pattern.format(n) in header]  # fmt: skip
        self.typed = {column for column, _ in self.names if f"{column}.type" in header}

    def other_names(self, row: Row) -> dict[str, list[str | None]]:
        """`alias` and `previousName` from the other names, by each name's `.type`."""
        found: dict[str, list[str | None]] = {"alias": [], "previousName": []}
        for column, group in self.names:
            name = text(row[column])
            if name is None:
                continue
            if column in self.typed:
                kind = row[f"{column}.type"].strip()
                prop = NAME_PROPERTY.get(kind)
            else:
                kind, prop = "no type", None if group != "other_entity_names" else "alias"
            if prop is None:
                self.counts[f"names_skipped.{vocab(kind.replace(' ', '_'))}"] += 1
            else:
                found[prop].append(name)
        return found

    def entity(self, schema: str, rid: str, values: dict[str, Any]) -> ValueEntity:
        entity = ValueEntity(model[schema], {"id": rid, "datasets": [DATASET]})
        for prop, raw in values.items():
            for value in raw if isinstance(raw, list) else [raw]:
                if not value:
                    continue
                cleaned = entity.schema.properties[prop].type.clean(value)
                if cleaned is None:
                    self.counts[f"values_dropped.{schema.lower()}.{prop.lower()}"] += 1
                else:
                    entity.add(prop, cleaned, cleaned=True)
        return entity

    def address(self, row: Row, kind: str) -> str | None:
        """The `Address` id of the legal or headquarters address, or None (no key)."""
        part = {name: text(row.get(f"Entity.{kind}.{name}")) for name in ADDRESS_PARTS}
        country = country_code(part["Country"])
        raw_postcode = part["PostalCode"]
        postcode = normalise_uk_postcode(raw_postcode) if raw_postcode and country == "gb" else None
        parts = [part[name] for name in ADDRESS_PARTS[:5]] + [
            postcode or raw_postcode,
            part["Country"],
        ]
        # FtM cleans `full`, and the graph loader recomputes the key from it (C2 L15, M2.3a).
        full = registry.address.clean(", ".join(p for p in parts if p))
        key = address_key(full) if full else None
        if key is None:
            return None
        rid = hashed_id("addr", key)
        if key not in self.addresses:
            values = {
                "full": full,
                "street": part["FirstAddressLine"],
                "street2": part["AdditionalAddressLine.1"],
                "city": part["City"],
                "region": text(row.get(f"Entity.{kind}.Region")),
                "postalCode": postcode or raw_postcode,
                "country": country,
            }
            entity = self.entity("Address", rid, values)
            self.addresses[key] = {**entity.to_dict(), "nr": {"v": NR_VERSION}}
        return rid

    def company(self, lei: str, row: Row) -> dict[str, Any]:
        number = raw = text(row[ENTITY_ID])
        if raw and row[AUTHORITY].strip().upper() in UK_AUTHORITIES:
            number = uk_company_number(raw)
            if number is None:
                self.counts["uk_numbers_not_ch_form"] += 1
                number = raw
        values: dict[str, Any] = {
            "name": text(row["Entity.LegalName"]),
            "leiCode": lei,
            **self.other_names(row),
            "jurisdiction": text(row["Entity.LegalJurisdiction"]),
            "registrationNumber": number,
            "status": text(row["Entity.EntityStatus"]),
            "legalForm": text(row["Entity.LegalForm.EntityLegalFormCode"])
            or text(row["Entity.LegalForm.OtherLegalForm"]),
            "incorporationDate": iso_date(row.get(CREATION), self.counts, "creation"),
            "sourceUrl": SOURCE_URL.format(lei),
        }
        entity = self.entity("Company", entity_id(lei), values)
        nr: dict[str, Any] = {"v": NR_VERSION, "source_ref": lei}
        roles: dict[str, str] = {}
        for kind, role in ROLES.items():
            if (address := self.address(row, kind)) and address not in roles:
                roles[address] = role
        if roles:
            entity.add("addressEntity", list(roles))
            nr["address_roles"] = roles
        else:
            self.counts["companies_without_address_key"] += 1
        return {**entity.to_dict(), "nr": nr}

    def ownership(self, row: Row, child: str, parent: str, level: str, periods: Sequence[str]
                  ) -> dict[str, Any]:  # fmt: skip
        values: dict[str, Any] = {"owner": entity_id(parent), "asset": entity_id(child)}
        for n in periods:
            if row[f"Relationship.Period.{n}.periodType"].strip() == "RELATIONSHIP_PERIOD":
                start, end = (
                    f"Relationship.Period.{n}.{edge}" for edge in ("startDate", "endDate")
                )
                values["startDate"] = iso_date(row.get(start), self.counts, "relationship")
                values["endDate"] = iso_date(row.get(end), self.counts, "relationship")
                break
        rid = hashed_id("ownership", child, parent, row[TYPE].strip())
        entity = self.entity("Ownership", rid, values)
        return {**entity.to_dict(), "nr": {"v": NR_VERSION, "consolidation": level}}


# --- the builder -----------------------------------------------------------------------------


def golden_copy_download() -> tuple[str, dict[str, Path], list[str]]:
    """The newest complete download: version, {`lei2` and `rr`: zip path}, stored URLs."""
    product = layout.sources_dir(DATASET, PRODUCT, "latest").parent
    for folder in sorted(product.iterdir(), reverse=True) if product.is_dir() else []:
        try:
            record = json.loads((folder / RECORD).read_text(encoding="utf-8"))
        except FileNotFoundError, ValueError:
            continue
        if not isinstance(record, dict) or not record.get("complete"):
            continue
        found: dict[str, dict[str, Any]] = {}
        for entry in record.get("files", []):
            if match := FILE_RE.fullmatch(str(entry.get("name"))):
                found[match[2]] = entry
        if set(found) == set(CDF):
            paths = {kind: folder / str(found[kind]["name"]) for kind in CDF}
            return folder.name, paths, [str(found[kind].get("url", "")) for kind in CDF]
    raise StepInputMissing(
        f"{DATASET}: no complete download of the {PRODUCT} product; run"
        f" neonradar data fetch --profile <profile> --dataset {DATASET} first",
        "input",
        counts_only=True,
    )


def read_slice(profile: Profile) -> tuple[set[str], dict[str, str]]:
    """The company numbers of the profile's Companies House `slice.csv`, and the snapshot
    version and SHA-256 its `slice.json` records; exit 2 when either is missing, or when the
    file is not the one `slice.json` describes."""
    work = layout.work_dir(profile, ch_bulk.DATASET)
    path, meta_path = work / SLICE, work / SLICE_META
    if not path.is_file() or not meta_path.is_file():
        missing = SLICE if not path.is_file() else SLICE_META
        message = f"{DATASET}: {missing} is missing; build {ch_bulk.DATASET} for this profile first"
        raise StepInputMissing(message, "input", counts_only=True)
    meta = slices.read_meta(meta_path)
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    if meta.get("slice_sha256") != sha256:
        message = f"{DATASET}: {SLICE} differs from {SLICE_META}; build {ch_bulk.DATASET} again"
        raise StepInputMissing(message, "slice", counts_only=True)
    strings = {"slice_version": str(meta.get("version")), "slice_sha256": sha256}
    return {number for number, _, _ in slices.read(path)}, strings


def write_relationships(
    rr_file: Table, writer: Writer, loaded: set[str], handle: TextIO, counts: Counter[str]
) -> dict[str, int]:
    """The last RR pass: consolidations between two loaded records; the rest counted."""
    relationships = {"direct": 0, "ultimate": 0}
    seen: set[str] = set()
    periods: list[str] | None = None
    for row in rr_file.rows():
        if periods is None:  # the header is known once the first row is read
            periods = sorted({m[1] for c in rr_file.header if (m := PERIOD_RE.fullmatch(c))})
        start, end = row[START].strip().upper(), row[END].strip().upper()
        if start not in loaded and end not in loaded:
            counts["relationships_outside_scope"] += 1
            continue
        link = consolidation(row)
        if row[TYPE].strip() not in CONSOLIDATION:
            counts[f"skipped_type.{vocab(row[TYPE])}"] += 1  # branches and funds among them
        elif row[STATUS].strip().upper() != "ACTIVE":
            counts[f"skipped_status.{vocab(row[STATUS])}"] += 1
        elif link is None:
            counts["relationships_not_lei"] += 1
        elif start not in loaded or end not in loaded:
            counts["relationships_end_not_loaded"] += 1
        else:
            record = writer.ownership(row, start, end, link[2], periods)
            if record["id"] in seen:
                counts["duplicate_relationships"] += 1
                continue
            seen.add(record["id"])
            relationships[link[2]] += 1
            quantified = any(row[c].strip() for c in rr_file.header if QUANTIFIER_RE.fullmatch(c))
            counts["quantifiers_filled"] += quantified  # counted, never loaded (note 6.3)
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return relationships


def header_list(header: Sequence[str], counts: Counter[str]) -> list[str]:
    """Column names for the summary; a name over 80 characters is counted, not written (and
    so is one with a character a summary string may not hold)."""
    kept = [name for name in header if HEADER_RE.fullmatch(name)]
    counts["headers_too_long"] += sum(len(name) > 80 for name in header)
    counts["headers_unlisted"] += len(header) - len(kept) - sum(len(n) > 80 for n in header)
    return kept


def absent_columns(lei_header: Sequence[str], rr_header: Sequence[str]) -> dict[str, int]:
    """1 for each optional column group the files lack (note 6.2: unverified until read)."""
    absent = {name: int(not any(pattern.format(n) in lei_header for n in range(1, 6)))
              for name, pattern in ALIAS_GROUPS.items()}  # fmt: skip
    absent |= {f"{name}_type": int(not any(f"{pattern.format(n)}.type" in lei_header
               for n in range(1, 6))) for name, pattern in ALIAS_GROUPS.items()}  # fmt: skip
    absent["entity_creation_date"] = int(CREATION not in lei_header)
    absent["relationship_period"] = int(not any(PERIOD_RE.fullmatch(c) for c in rr_header))
    absent["quantifiers"] = int(not any(QUANTIFIER_RE.fullmatch(c) for c in rr_header))
    return absent


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: GleifSource = profile.options(DATASET)
    numbers, strings = read_slice(profile) if options.scope == "slice" else (set(), {})
    version, paths, urls = golden_copy_download()
    counts: Counter[str] = Counter()
    lei_stats, rr_stats = Counter[str](), Counter[str]()
    lei_file = Table(paths["lei2"], LEI_COLUMNS, lei_stats)
    rr_file = Table(paths["rr"], RR_COLUMNS, rr_stats)
    wanted = in_scope(lei_file, options.scope, numbers, counts)
    counts["scoped_leis"] = len(wanted)
    add_parents(Table(paths["rr"], RR_COLUMNS, Counter()), wanted)  # rr_stats counts one pass
    writer = Writer(lei_file.header, counts)
    by_reason: Counter[str] = Counter()
    categories: Counter[str] = Counter()
    written: set[str] = set()
    out = context.out_dir / RECORD_FILE
    with out.open("w", encoding="utf-8", newline="\n") as handle:
        for row in Table(paths["lei2"], LEI_COLUMNS, Counter()).rows():  # the second pass
            lei = loadable(row)
            if lei is None or lei not in wanted:
                continue
            if lei in written:
                counts["duplicate_leis"] += 1
                continue
            if text(row["Entity.LegalName"]) is None:
                counts["rows_without_name"] += 1  # a Company needs a name (C1 R3)
                continue
            written.add(lei)
            by_reason[wanted[lei]] += 1
            categories[vocab(row["Entity.EntityCategory"] or "none")] += 1
            handle.write(json.dumps(writer.company(lei, row), ensure_ascii=False) + "\n")
        relationships = write_relationships(rr_file, writer, written, handle, counts)
        for key in sorted(writer.addresses):
            handle.write(json.dumps(writer.addresses[key], ensure_ascii=False) + "\n")
    producer = Producer(name="neonradar_ingest.sources.gleif", version=__version__)
    note = "Level 2 relationships are accounting consolidation (nr.consolidation), not ownership"
    write_manifest(out, dataset=DATASET, producer=producer, notes=[note],
                   source=Source(urls=urls, source_version=version))  # fmt: skip
    published = datetime.strptime(version, "%Y%m%d-%H%M").replace(tzinfo=UTC)
    summary: dict[str, Any] = {
        "publish_age_hours": int((datetime.now(UTC) - published).total_seconds() // 3600),
        "slice_companies": len(numbers),
        "records": {
            "company": len(written),
            "address": len(writer.addresses),
            "ownership": sum(relationships.values()),
        },
        "by_reason": {reason: by_reason[reason] for reason in ("slice", "uk", "all", "parent")},
        "relationships": relationships,
        "parents_not_loaded": sum(
            why == "parent" and lei not in written for lei, why in wanted.items()
        ),
        "entity_category_by_value": dict(categories),
        "optional_columns_absent": absent_columns(lei_file.header, rr_file.header),
        "lei_file": dict(sorted(lei_stats.items())),
        "rr_file": dict(sorted(rr_stats.items())),
    }
    lists = {"lei_headers": header_list(lei_file.header, counts),
             "rr_headers": header_list(rr_file.header, counts)}  # fmt: skip
    groups = {"registration_skipped": "registration_skipped",
              "names_skipped": "names_skipped_by_value", "skipped_type": "skipped_type_by_value",
              "skipped_status": "skipped_status_by_value"}  # fmt: skip
    whole_file = ("invalid_leis", "registration_skipped", "uk_authority_leis")
    for key, value in counts.items():
        group, _, name = key.partition(".")
        where = summary["lei_file"] if group in whole_file else summary  # whole-file counts
        if group in groups and name:
            where.setdefault(groups[group], {})[name] = value
        else:
            where[key] = value
    strings |= {"version": version, "scope": options.scope}
    return BuildResult(counts=dict(sorted(summary.items())), lists=lists, strings=strings)


register_builder(
    Builder(
        DATASET,
        build,
        string_keys=("scope", "slice_version", "slice_sha256"),
        list_keys=("lei_headers", "rr_headers"),
    )
)
