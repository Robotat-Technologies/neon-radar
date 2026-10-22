"""UN Security Council Consolidated List loader (PHASE-2.md M2.6c; sanctions-peps.md section 3).

The UN publishes one XML file ordered by reference number. Its URL answers with a redirect to a
signed storage URL valid for one hour, which is followed but never stored or logged (M2.6 rule
4: `shared.list_client`). Each `INDIVIDUAL` becomes one `Person` and each `ENTITY` one
`Organization` with `topics: ["sanction"]`, and each entry one `Sanction`. The value "na" means
"not available" and is treated as missing. Comments, notes, Interpol links, list types and sort
keys are never loaded; the comments only into `Sanction:reason` with `keep_reasons`, titles and
designations only with `keep_positions`. The UN gives no company registration numbers as fields,
and numbers in the comments are never read.

The UN website terms allow download "for the User's personal, non-commercial use" (note 3.5),
so the loader refuses to fetch or build, besides the gate's `access.sanctions_lists` check, until
the data steward has filed the UN's written permission in `docs/data/licences/un_sc_sanctions.md`.
"""

import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import iterparse

from neonradar_contracts.records import ID_RE
from neonradar_ingest.data.gate import RealDataRefused
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.project import REPO_ROOT
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
from neonradar_ingest.sources.lists import shared
from neonradar_ingest.sources.lists.common import (
    join_name,
    parse_iso,
    partial_date,
    sanction_id,
    split_values,
    year_range,
)
from neonradar_ingest.spikes import entity_record
from neonradar_keys.countries import country_code
from neonradar_keys.ids import un_reference

DATASET = "un_sc_sanctions"
PREFIX = "unsc"
FILE_NAME = "consolidated.xml"
URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"
AUTHORITY = "United Nations Security Council"
# Looked up per call, so tests can point it at a temporary file. Never created by an agent.
PERMISSION_FILE = REPO_ROOT / "docs" / "data" / "licences" / f"{DATASET}.md"
PERMISSION_RULE = "un_written_permission"
SCHEMATA = {"INDIVIDUAL": "Person", "ENTITY": "Organization"}
NOT_AVAILABLE = "na"
GENDERS = {"male": "male", "female": "female"}
PASSPORTS = frozenset({"passport", "numéro de passeport", "número de pasaporte"})
NATIONAL_IDS = frozenset(
    {
        "national identification number",
        "numéro d'identification nationale",
        "número de identificación nacional",
    }
)
FATAL_RATES = ("person_birth_date", "sanction_program")  # zero means a broken parser
# The children of INDIVIDUAL and ENTITY in note 3.3; any other one is counted (a format change).
KNOWN = frozenset(
    {
        "DATAID", "VERSIONNUM", "FIRST_NAME", "SECOND_NAME", "THIRD_NAME", "FOURTH_NAME",
        "UN_LIST_TYPE", "REFERENCE_NUMBER", "LISTED_ON", "GENDER", "NAME_ORIGINAL_SCRIPT",
        "COMMENTS1", "HAS_INTERPOL_LINK", "INTERPOL_LINK", "TITLE", "DESIGNATION",
        "NATIONALITY", "LIST_TYPE", "LAST_DAY_UPDATED", "INDIVIDUAL_ALIAS", "ENTITY_ALIAS",
        "INDIVIDUAL_ADDRESS", "ENTITY_ADDRESS", "INDIVIDUAL_DATE_OF_BIRTH",
        "INDIVIDUAL_PLACE_OF_BIRTH", "INDIVIDUAL_DOCUMENT", "SORT_KEY", "SORT_KEY_LAST_MOD",
    }
)  # fmt: skip
ADDRESS_PARTS = ("STREET", "CITY", "STATE_PROVINCE", "ZIP_CODE", "COUNTRY")


def require_permission() -> None:
    """Refuse (exit code 3) unless the UN's written permission is filed (PHASE-2.md 3.3)."""
    if not PERMISSION_FILE.is_file():
        raise RealDataRefused(
            PERMISSION_RULE,
            f"{DATASET} needs the UN's written permission, filed by the data steward in"
            f" docs/data/licences/{DATASET}.md (PHASE-2.md 3.3); without it the UK and EU lists"
            " carry the UN listings",
        )


def discover(client: HttpClient) -> list[RemoteFile]:
    """The one list file; the permission is checked before any request."""
    require_permission()
    return shared.discover_static(FILE_NAME, URL)(client)


@dataclass(slots=True)
class Entry:
    """The fields of one `INDIVIDUAL` or `ENTITY` the loader may use (nothing else is kept)."""

    kind: str
    reference: str
    data_id: str | None = None
    names: tuple[str | None, ...] = ()  # FIRST_NAME to FOURTH_NAME
    original: str | None = None
    list_type: str | None = None
    listed_on: str | None = None
    updated: list[str] = field(default_factory=list)
    comments: str | None = None
    gender: str | None = None
    titles: list[str] = field(default_factory=list)
    designations: list[str] = field(default_factory=list)
    nationalities: list[str] = field(default_factory=list)
    aliases: list[tuple[str, str]] = field(default_factory=list)  # (quality, ALIAS_NAME)
    addresses: list[tuple[str, str | None]] = field(default_factory=list)
    dobs: list[dict[str, str | None]] = field(default_factory=list)
    places: list[tuple[str | None, str | None]] = field(default_factory=list)
    documents: list[tuple[str | None, str | None]] = field(default_factory=list)


def value(element: Element | None, name: str | None = None) -> str | None:
    """`shared.text`, with "na" (not available, note 3.3) as missing."""
    found = shared.text(element, name)
    return None if found is None or found.casefold() == NOT_AVAILABLE else found


def values(element: Element | None, *path: str) -> list[str]:
    return [v for v in shared.texts(element, *path) if v.casefold() != NOT_AVAILABLE]


def _entry(element: Element, kind: str, counts: Counter[str]) -> Entry | None:
    reference = un_reference(value(element, "REFERENCE_NUMBER"))
    if reference is None:
        counts["entries_without_reference"] += 1
        return None
    counts["unknown_elements"] += sum(shared.local(item.tag) not in KNOWN for item in element)
    e = Entry(
        kind=kind,
        reference=reference,
        data_id=value(element, "DATAID"),
        names=tuple(value(element, f"{n}_NAME") for n in ("FIRST", "SECOND", "THIRD", "FOURTH")),
        original=value(element, "NAME_ORIGINAL_SCRIPT"),
        list_type=value(element, "UN_LIST_TYPE"),
        listed_on=value(element, "LISTED_ON"),
        updated=values(element, "LAST_DAY_UPDATED", "VALUE"),
        comments=value(element, "COMMENTS1"),
        gender=value(element, "GENDER"),
        titles=values(element, "TITLE", "VALUE"),
        designations=values(element, "DESIGNATION", "VALUE"),
        nationalities=values(element, "NATIONALITY", "VALUE"),
    )
    for alias in shared.children(element, f"{kind}_ALIAS"):
        quality = (value(alias, "QUALITY") or "").casefold()
        e.aliases += [(quality, name) for name in split_values(value(alias, "ALIAS_NAME"), ";")]
    for address in shared.children(element, f"{kind}_ADDRESS"):
        parts = [value(address, name) for name in ADDRESS_PARTS]
        if any(parts):
            e.addresses.append((", ".join(p for p in parts if p), value(address, "COUNTRY")))
    for dob in shared.children(element, "INDIVIDUAL_DATE_OF_BIRTH"):
        names = ("TYPE_OF_DATE", "DATE", "YEAR", "FROM_YEAR", "TO_YEAR")
        e.dobs.append({name: value(dob, name) for name in names})
    for place in shared.children(element, "INDIVIDUAL_PLACE_OF_BIRTH"):
        town = [part for part in (value(place, "CITY"), value(place, "STATE_PROVINCE")) if part]
        e.places.append((", ".join(town) or None, value(place, "COUNTRY")))
    for document in shared.children(element, "INDIVIDUAL_DOCUMENT"):
        e.documents.append((value(document, "TYPE_OF_DOCUMENT"), value(document, "NUMBER")))
    return e


def parse(path: Path) -> tuple[str | None, list[Entry], Counter[str]]:
    """The list's `dateGenerated`, its entries (one element at a time) and counts."""
    stamp: str | None = None
    found: list[Entry] = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    try:
        for event, element in iterparse(str(path), events=("start", "end")):
            name = shared.local(element.tag)
            if event == "start":
                if name == "CONSOLIDATED_LIST" and stamp is None:
                    stamp = element.get("dateGenerated")
                continue
            if name not in SCHEMATA:
                continue
            counts["entries"] += 1
            entry = _entry(element, name, counts)
            element.clear()
            if entry is None:
                continue
            if entry.reference in seen:
                counts["duplicate_references"] += 1
                continue
            seen.add(entry.reference)
            found.append(entry)
    except (ParseError, DefusedXmlException) as exc:
        message = f"{DATASET}: {path.name} is not a well-formed list file ({type(exc).__name__})"
        raise BuildError(message, "xml", counts_only=True) from None
    return stamp, found, counts


def party_id(reference: str) -> str:
    """`unsc-<reference>`, or a hash when the reference breaks the C1 id alphabet (OD-11)."""
    candidate = f"{PREFIX}-{reference}"
    if ID_RE.fullmatch(candidate) and len(candidate) <= 120:
        return candidate
    digest = hashlib.sha1(reference.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
    return f"{PREFIX}-x{digest}"


def _country(text: str | None, counts: Counter[str]) -> str | None:
    code = country_code(text)
    if text and code is None:
        counts["unmapped_countries"] += 1
    return code


def _iso(text: str | None, counts: Counter[str]) -> str | None:
    parsed = parse_iso(text)
    if text and parsed is None:
        counts["unparseable_dates"] += 1
    return parsed


def _birth_dates(entry: Entry, counts: Counter[str]) -> list[str]:
    """EXACT: the date (else its year); APPROXIMATELY: the year; BETWEEN: `year_range`."""
    found: list[str] = []
    for dob in entry.dobs:
        kind = (dob["TYPE_OF_DATE"] or "").upper()
        if kind == "EXACT":
            date = _iso(dob["DATE"], counts) if dob["DATE"] else partial_date(dob["YEAR"])
            found += [date] if date else []
        elif kind == "APPROXIMATELY":
            year = partial_date(dob["YEAR"])
            counts["unparseable_dates"] += bool(dob["YEAR"]) and year is None
            found += [year] if year else []
        elif kind == "BETWEEN":
            years = year_range(dob["FROM_YEAR"], dob["TO_YEAR"])
            counts["wide_birth_year_ranges"] += not years and bool(dob["FROM_YEAR"])
            found += years
        else:
            counts["unknown_date_types"] += 1
    return found


def _names(entry: Entry, person: bool, props: dict[str, list[str]], counts: Counter[str]) -> None:
    """Person: the four names joined, `firstName` the first, `lastName` the last of the others;
    Organization: FIRST_NAME. QUALITY Good to alias, Low to weakAlias, empty: two or more words
    to alias; any other quality is counted and treated as weak (never a match alone)."""
    first = entry.names[0] if entry.names else None
    full = join_name(entry.names) if person else first
    if full is None:
        return
    props["name"] = [full]
    if person:
        rest = [part for part in entry.names[1:] if part]
        props["firstName"] = [first or ""]
        props["lastName"] = rest[-1:]
    aliases, weak = [entry.original or ""], []
    for quality, alias in entry.aliases:
        if quality == "good" or (not quality and len(alias.split()) >= 2):
            aliases.append(alias)
        else:
            counts["unknown_alias_qualities"] += quality not in ("", "low")
            weak.append(alias)
    props["alias"] = [a for a in dict.fromkeys(aliases) if a and a != full]
    taken = {full, *props["alias"]}
    props["weakAlias"] = [w for w in dict.fromkeys(weak) if w not in taken]


def _person(entry: Entry, props: dict[str, list[str]], counts: Counter[str]) -> None:
    props["birthDate"] = _birth_dates(entry, counts)
    props["nationality"] = [c for c in (_country(n, counts) for n in entry.nationalities) if c]
    for town, country in entry.places:
        props["birthPlace"].append(town or "")
        props["birthCountry"].append(_country(country, counts) or "")
    if entry.gender:
        gender = GENDERS.get(entry.gender.casefold())
        counts["unknown_genders"] += gender is None
        props["gender"] = [gender or ""]
    for kind, number in entry.documents:
        folded = (kind or "").casefold()
        target = "passportNumber" if folded in PASSPORTS else None
        target = "idNumber" if folded in NATIONAL_IDS else target
        if target is None or number is None:
            counts["documents_not_loaded"] += 1
        else:
            props[target].append("".join(number.split()))


def _record(schema: str, record_id: str, props: dict[str, list[str]], ref: str) -> dict[str, Any]:
    cleaned = {key: list(dict.fromkeys(v for v in items if v)) for key, items in props.items()}
    record = entity_record(schema, record_id, DATASET, cleaned)
    record["nr"] = {"v": shared.RECORD_V, "source_ref": ref}
    return record


def entry_records(
    entry: Entry, options: shared.ListOptions, counts: Counter[str]
) -> list[dict[str, Any]]:
    """The entry's `Person` or `Organization` record, then its `Sanction`."""
    schema = SCHEMATA[entry.kind]
    person = schema == "Person"
    props: dict[str, list[str]] = defaultdict(list)
    props["topics"] = ["sanction"]
    _names(entry, person, props, counts)
    if not props["name"]:
        counts["entries_without_name"] += 1
        return []
    if person:
        _person(entry, props, counts)
        if options.keep_positions:
            props["title"], props["position"] = entry.titles, entry.designations
    for address, country in entry.addresses:
        props["address"].append(address)
        props["country"].append(_country(country, counts) or "")
    pid = party_id(entry.reference)
    listed = _iso(entry.listed_on, counts)
    updated = [date for date in (_iso(day, counts) for day in entry.updated) if date]
    sanction: dict[str, list[str]] = {
        "entity": [pid],
        "authority": [AUTHORITY],
        "authorityId": [entry.data_id or ""],
        "unscId": [entry.reference],
        "program": [entry.list_type or ""],
        "startDate": [listed or ""],
        "listingDate": [listed or ""],
        "modifiedAt": [max(updated)] if updated else [],
    }
    if options.keep_reasons and entry.comments:
        sanction["reason"] = [entry.comments]
    sid = sanction_id(PREFIX, pid, entry.reference)
    return [
        _record(schema, pid, props, entry.reference),
        _record("Sanction", sid, sanction, entry.reference),
    ]


def build(profile: Profile, context: BuildContext) -> BuildResult:
    require_permission()
    options: shared.ListOptions = profile.options(DATASET)
    download = shared.latest_download(DATASET, FILE_NAME)
    raw_stamp, entries, counts = parse(download.path)
    records = [record for entry in entries for record in entry_records(entry, options, counts)]
    by_schema = Counter(str(record["schema"]) for record in records)
    rates = shared.fill_rates(records)
    zero = [name for name in FATAL_RATES if rates[name] == 0]
    outside = shared.check_size(DATASET, by_schema, zero, accept_size=context.accept_size)
    stamp = shared.list_stamp(raw_stamp)
    notes = [f"list_generated: {stamp}", f"entries: {counts['entries']}"]
    shared.write_records(
        context.out_dir, DATASET, "un_sc", records, download, skipped={}, notes=notes
    )
    return BuildResult(
        counts={
            **{key: counts[key] for key in sorted(counts)},
            "records": {name.lower(): count for name, count in sorted(by_schema.items())},
            "fill_rates": rates,
            "bounds_outside_accepted": outside,
        },
        strings={"list_generated": stamp},
    )


register_source_model(DATASET, shared.ListOptions)
register_source(SourceSpec(DATASET, discover, client=shared.list_client))
register_builder(Builder(DATASET, build, string_keys=("list_generated",)))
