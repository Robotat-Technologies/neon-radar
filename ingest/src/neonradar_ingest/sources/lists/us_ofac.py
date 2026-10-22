"""OFAC SDN List loader, advanced XML (PHASE-2.md M2.6b; sanctions-peps.md section 2).

OFAC publishes the SDN List as one advanced XML file (schema `sdn_advanced.xsd`, committed under
`ingest/tests/fixtures/lists/us_ofac_sdn/`). Every type, country, list and feature in it is an ID
into `ReferenceValueSets`, and `ProfileRelationships` and `SanctionsEntries` come after
`DistinctParties` (note 2.4), so the builder reads the file twice. Pass 1 keeps only the small
tables: reference values, locations, identity documents, sanctions entries, relationships and
the schema of each loadable profile. Pass 2 streams `DistinctParty` elements and writes one
record at a time, keeping no party. Individuals become `Person`, entities `Organization`, with
`topics: ["sanction"]`; each sanctions entry becomes a `Sanction`; each relationship between two
loaded parties a link record, never `Ownership` (OFAC's relation types give no share, note 2.8).
Vessels and aircraft are skipped and counted; every feature and document type the mapping does
not name is counted by its type name, never loaded and never logged with its value.
"""

import hashlib
from collections import Counter, defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import iterparse
from followthemoney import model

from neonradar_contracts.records import ID_RE
from neonradar_ingest.data.profiles import Profile, register_source_model
from neonradar_ingest.data.sources import (
    BuildContext,
    Builder,
    BuildError,
    BuildResult,
    SourceSpec,
    register_builder,
    register_source,
)
from neonradar_ingest.sources.lists import shared
from neonradar_ingest.sources.lists.common import (
    join_name,
    partial_date,
    period_dates,
    sanction_id,
    year_range,
)
from neonradar_ingest.spikes import entity_record
from neonradar_keys.countries import country_code
from neonradar_keys.ids import is_valid_lei, uk_company_number

DATASET = "us_ofac_sdn"
PREFIX = "ofac"
FILE_NAME = "SDN_ADVANCED.XML"
URL = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML"
DETAILS_URL = "https://sanctionssearch.ofac.treas.gov/Details.aspx?id={}"
AUTHORITY = "US Office of Foreign Assets Control"
COUNTRY = "us"
# Party type (subtype, or the party type when the subtype is "Unknown", note 2.9) to schema.
KINDS = {
    "individual": "Person",
    "entity": "Organization",
    "vessel": "Vessel",
    "aircraft": "Airplane",
}
SCHEMATA = ("Person", "Organization")
FATAL_RATES = ("person_birth_date", "sanction_program")  # zero means a broken parser
PERSON_PARTS = ("first name", "middle name", "patronymic", "matronymic", "last name")
PERSON_PROPS = ("firstName", "middleName", "fatherName", "motherName", "lastName")
NAME_PARTS = frozenset(
    {*PERSON_PARTS, "maiden name", "nickname", "entity name", "vessel name", "aircraft name"}
)
FEATURES = {
    "birthdate": "birthDate",
    "place of birth": "birthPlace",
    "nationality country": "nationality",
    "citizenship country": "citizenship",
    "gender": "gender",
    "location": "address",
    "organization established date": "incorporationDate",
}
GENDERS = {"male": "male", "female": "female"}
LOCATION_PARTS = ("ADDRESS1", "ADDRESS2", "ADDRESS3", "CITY", "STATE/PROVINCE", "REGION")
LOCATION_PARTS += ("POSTAL CODE",)
PASSPORTS = frozenset({"passport", "diplomatic passport"})
ID_NUMBERS = frozenset({"national id no.", "identification number", "cedula no."})
UK_IF_ISSUED_IN_GB = frozenset(
    {
        "company number", "registration number", "registration id", "business registration number",
        "commercial registry number", "certificate of incorporation number",
    }
)  # fmt: skip
LEI_TYPES = frozenset({"legal entity number", "le number"})
# Relation type to (schema, property of the From party, property of the To party), deliverable 8.
RELATIONS = {
    "owned or controlled by": ("Control", "controlled", "controller"),
    "owns, controls, or operates": ("Control", "controller", "controlled"),
    "property in the interest of": ("Control", "controlled", "controller"),
    "acting for or on behalf of": ("Representation", "agent", "client"),
    "leader or official of": ("Directorship", "director", "organization"),
    "principal executive officer": ("Directorship", "director", "organization"),
    "playing a significant role in": ("Membership", "member", "organization"),
    "associate of": ("Associate", "person", "associate"),
    "family member of": ("Family", "person", "relative"),
    "providing support to": ("UnknownLink", "subject", "object"),
}
UNKNOWN_LINK = ("UnknownLink", "subject", "object")
PERSONS_ONLY = frozenset({"Associate", "Family"})
TARGETED = {"Control": "controlled", "Directorship": "organization", "Membership": "organization"}
RATES = {
    "person_birth_date": ("Person", ("birthDate",)),
    "person_nationality": ("Person", ("nationality",)),
    "person_passport_or_id": ("Person", ("passportNumber", "idNumber")),
    "sanction_program": ("Sanction", ("program",)),
    "sanction_start_date": ("Sanction", ("startDate",)),
    "organization_registration_or_lei": ("Organization", ("registrationNumber", "leiCode")),
}
LAST_SECTIONS = frozenset({"ProfileRelationships", "SanctionsEntries", "SanctionsEntryLinks"})


@dataclass(frozen=True, slots=True)
class Place:
    """A `Location`: its address parts in the order of deliverable 5, and its country."""

    parts: tuple[str, ...]
    country: str | None  # the country's name in `CountryValues`
    iso2: str | None


@dataclass(frozen=True, slots=True)
class Document:
    kind: str  # the `IDRegDocType` value
    number: str | None
    issued_by: str | None  # ISO code of `IssuedBy-CountryID`
    fraudulent: bool


@dataclass(frozen=True, slots=True)
class Entry:
    id: str
    start: str | None  # the earliest `EntryEvent` date
    programs: tuple[str, ...]
    provisions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Relation:
    id: str
    source: str  # From-ProfileID
    target: str  # To-ProfileID
    kind: str  # the raw relation type
    former: bool


@dataclass(slots=True)
class Tables:
    """What pass 1 keeps: the small tables, never a party."""

    stamp: str | None = None
    values: dict[str, dict[str, tuple[str, dict[str, str]]]] = field(default_factory=dict)
    places: dict[str, Place] = field(default_factory=dict)
    documents: dict[str, list[Document]] = field(default_factory=lambda: defaultdict(list))
    entries: dict[str, list[Entry]] = field(default_factory=lambda: defaultdict(list))
    relations: list[Relation] = field(default_factory=list)
    parties: dict[str, tuple[str, str]] = field(default_factory=dict)  # profile: (id, schema)

    def value(self, table: str, ref: str | None) -> str | None:
        """The value of `ref` in the reference table `table` (for example "AliasType")."""
        row = self.values.get(table, {}).get(ref or "")
        return row[0] if row else None

    def attr(self, table: str, ref: str | None, name: str) -> str | None:
        row = self.values.get(table, {}).get(ref or "")
        return row[1].get(name) if row else None

    def country(self, ref: str | None) -> tuple[str | None, str | None]:
        """(name, ISO2) of a `CountryID`."""
        return self.value("Country", ref), self.attr("Country", ref, "ISO2")


@dataclass(slots=True)
class Tally:
    """Counts of the records as they are written: per schema, and the fill rates (rule 10)."""

    by_schema: Counter[str] = field(default_factory=Counter)
    filled: Counter[str] = field(default_factory=Counter)

    def observe(self, records: Iterable[dict[str, Any]]) -> Iterator[dict[str, Any]]:
        for record in records:
            schema, props = record["schema"], record["properties"]
            self.by_schema[schema] += 1
            for name, (wanted, keys) in RATES.items():
                self.filled[name] += schema == wanted and any(props.get(k) for k in keys)
            yield record

    def rates(self) -> dict[str, float]:
        return {
            name: shared.rate(self.filled[name], self.by_schema[schema])
            for name, (schema, _keys) in RATES.items()
        }


def _vocabulary(name: str) -> str:
    """A type name as a `_by_value` summary key (lower case, at most 80 characters)."""
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789 ._#:/()&,'-")
    key = "".join(c if c in allowed else "_" for c in " ".join(name.casefold().split()))[:80]
    return key if key[:1].isalnum() else f"x{key}"[:80]


def _elements(path: Path) -> Iterator[tuple[str, Element]]:
    """(section, element) for every complete element two levels below the root (the rows of
    each section and the tables of `ReferenceValueSets`), and `DateOfIssue`. Each element is
    cleared and detached once used, so the tree never grows (deliverable 2). Tags are compared
    without their namespace (M2.6 rule 3)."""
    stack: list[Element] = []
    try:
        with path.open("rb") as handle:
            for event, element in iterparse(handle, events=("start", "end")):
                if event == "start":
                    stack.append(element)
                    continue
                stack.pop()
                section = shared.local(stack[1].tag) if len(stack) == 2 else ""
                if section and section != "DateOfIssue":
                    yield section, element
                elif len(stack) == 1 and shared.local(element.tag) == "DateOfIssue":
                    yield "DateOfIssue", element
                else:
                    continue
                element.clear()
                stack[-1].remove(element)
    except (ParseError, DefusedXmlException) as exc:
        message = f"{DATASET}: {path.name} is not a well-formed list file ({type(exc).__name__})"
        raise BuildError(message, "xml", counts_only=True) from None


def _int(element: Element | None, name: str) -> int | None:
    value = shared.text(element, name)
    return int(value) if value and value.isdigit() else None


def _point(element: Element | None) -> tuple[int | None, int | None, int | None]:
    return _int(element, "Year"), _int(element, "Month"), _int(element, "Day")


def _reference_values(element: Element, tables: Tables) -> None:
    table = shared.local(element.tag).removesuffix("Values")
    rows = tables.values.setdefault(table, {})
    for row in element:
        attrs = {key: value for key, value in row.attrib.items() if key != "ID"}
        rows[row.get("ID", "")] = (shared.text(row) or "", attrs)


def _not_primary(value: Element) -> bool:
    return value.get("Primary") != "true"


def _place(element: Element, tables: Tables, counts: Counter[str]) -> Place:
    parts: dict[str, list[str]] = defaultdict(list)
    for part in shared.children(element, "LocationPart"):
        kind = (tables.value("LocPartType", part.get("LocPartTypeID")) or "").upper()
        values = sorted(shared.children(part, "LocationPartValue"), key=_not_primary)
        value = shared.text(values[0], "Value") if values else None
        if value and kind in LOCATION_PARTS:
            parts[kind].append(value)
        elif value:
            counts["location_parts_not_loaded"] += 1
    country = shared.child(element, "LocationCountry")
    name, iso2 = tables.country(country.get("CountryID") if country is not None else None)
    ordered = tuple(value for kind in LOCATION_PARTS for value in parts.get(kind, ()))
    return Place(ordered, name, iso2)


def _country(name: str | None, iso2: str | None, counts: Counter[str]) -> str | None:
    """The ISO code of a country (ISO2 first, then the name); a value that does not map is
    counted, never guessed (M2.6 rule 6)."""
    code = country_code(iso2) or country_code(name)
    if (name or iso2) and code is None:
        counts["unmapped_countries"] += 1
    return code


def _document(element: Element, tables: Tables) -> None:
    validity = tables.value("Validity", element.get("ValidityID")) or ""
    name, iso2 = tables.country(element.get("IssuedBy-CountryID"))
    tables.documents[element.get("IdentityID", "")].append(
        Document(
            kind=tables.value("IDRegDocType", element.get("IDRegDocTypeID")) or "",
            number=shared.text(element, "IDRegistrationNo"),
            issued_by=country_code(iso2) or country_code(name),
            fraudulent=validity.casefold() == "fraudulent",
        )
    )


def _entry(element: Element, tables: Tables) -> None:
    dates = [
        partial_date(*_point(shared.child(event, "Date")))
        for event in shared.children(element, "EntryEvent")
    ]
    programs: list[str] = []
    provisions: list[str] = []
    for measure in shared.children(element, "SanctionsMeasure"):
        kind = tables.value("SanctionsType", measure.get("SanctionsTypeID")) or ""
        comment = shared.text(measure, "Comment")
        if kind.casefold() == "program":
            programs += [comment] if comment else []
        elif kind:
            provisions.append(kind)
    tables.entries[element.get("ProfileID", "")].append(
        Entry(
            id=element.get("ID", ""),
            start=min((d for d in dates if d), default=None),
            programs=tuple(dict.fromkeys(programs)),
            provisions=tuple(dict.fromkeys(provisions)),
        )
    )


def _relation(element: Element, tables: Tables) -> None:
    tables.relations.append(
        Relation(
            id=element.get("ID", ""),
            source=element.get("From-ProfileID", ""),
            target=element.get("To-ProfileID", ""),
            kind=tables.value("RelationType", element.get("RelationTypeID")) or "",
            former=element.get("Former") == "true",
        )
    )


def party_kind(profile: Element, tables: Tables) -> str:
    """Person, Organization, Vessel or Airplane from the profile's `PartySubTypeID`, through
    its `PartyType` when the subtype is "Unknown" (deliverable 3); "" when neither maps."""
    subtype = profile.get("PartySubTypeID")
    name = tables.value("PartySubType", subtype) or ""
    if name.casefold() in ("", "unknown"):
        name = tables.value("PartyType", tables.attr("PartySubType", subtype, "PartyTypeID")) or ""
    return KINDS.get(name.casefold(), "")


def party_id(native: str) -> str:
    """`ofac-<FixedRef>`, or a hash when the native id breaks the C1 id alphabet (OD-11)."""
    candidate = f"{PREFIX}-{native}"
    if ID_RE.fullmatch(candidate) and len(candidate) <= 120:
        return candidate
    digest = hashlib.sha1(native.encode("utf-8"), usedforsecurity=False).hexdigest()[:20]
    return f"{PREFIX}-x{digest}"


def _has_name(profile: Element) -> bool:
    return any(
        shared.local(item.tag) == "NamePartValue" and shared.text(item) for item in profile.iter()
    )


def _classify(element: Element, tables: Tables) -> None:
    """Pass 1: remember the id and schema of each profile pass 2 will load (deliverable 8 needs
    them for the relationships)."""
    fixed_ref = element.get("FixedRef", "")
    profile = shared.child(element, "Profile")
    if profile is None or not fixed_ref:
        return
    kind = party_kind(profile, tables)
    if kind in SCHEMATA and _has_name(profile):
        tables.parties[profile.get("ID", "")] = (party_id(fixed_ref), kind)


def read_tables(path: Path, counts: Counter[str]) -> Tables:
    """Pass 1 (deliverable 2). The sections follow the XSD's order, so the reference values are
    known before any row that points into them."""
    tables = Tables()
    for section, element in _elements(path):
        if section == "DateOfIssue":
            tables.stamp = partial_date(*_point(element))
        elif section == "ReferenceValueSets":
            _reference_values(element, tables)
        elif section == "Locations":
            tables.places[element.get("ID", "")] = _place(element, tables, counts)
        elif section == "IDRegDocuments":
            _document(element, tables)
        elif section == "DistinctParties":
            counts["distinct_parties"] += 1
            _classify(element, tables)
        elif section == "ProfileRelationships":
            _relation(element, tables)
        elif section == "SanctionsEntries":
            _entry(element, tables)
    return tables


@dataclass(slots=True)
class Names:
    name: list[str] = field(default_factory=list)
    alias: list[str] = field(default_factory=list)
    previous: list[str] = field(default_factory=list)
    weak: list[str] = field(default_factory=list)


def _is_latin(tables: Tables, script: str | None) -> bool:
    code = (tables.attr("Script", script, "ScriptCode") or "").casefold()
    return code == "latn" or (tables.value("Script", script) or "").casefold() == "latin"


def _documented_name(
    documented: Element, groups: dict[str, str], tables: Tables, counts: Counter[str]
) -> tuple[dict[str, list[str]], list[str], bool]:
    """The typed parts of one `DocumentedName`, all its values in order, and whether it is
    written in Latin script."""
    parts: dict[str, list[str]] = defaultdict(list)
    values: list[str] = []
    script: str | None = None
    for part in shared.children(documented, "DocumentedNamePart"):
        value_element = shared.child(part, "NamePartValue")
        value = shared.text(value_element)
        if value_element is None or not value:
            continue
        kind = groups.get(value_element.get("NamePartGroupID", ""), "")
        counts["unknown_name_part_types"] += kind not in NAME_PARTS
        parts[kind].append(value)
        values.append(value)
        script = script or value_element.get("ScriptID")
    return parts, values, _is_latin(tables, script)


def _names(
    identity: Element,
    person: bool,
    tables: Tables,
    names: Names,
    props: dict[str, list[str]],
    counts: Counter[str],
) -> None:
    """Deliverable 4: one name per `DocumentedName`, placed by the alias's type and flags."""
    groups = {
        group.get("ID", ""): (
            tables.value("NamePartType", group.get("NamePartTypeID")) or ""
        ).casefold()
        for group in identity.iter()
        if shared.local(group.tag) == "NamePartGroup"
    }
    for alias in shared.children(identity, "Alias"):
        alias_type = (tables.value("AliasType", alias.get("AliasTypeID")) or "").casefold()
        primary, low = alias.get("Primary") == "true", alias.get("LowQuality") == "true"
        for documented in shared.children(alias, "DocumentedName"):
            parts, values, latin = _documented_name(documented, groups, tables, counts)
            maiden: str | None = None
            nicknames: list[str] = []
            if person:
                full = join_name(v for kind in PERSON_PARTS for v in parts.get(kind, ()))
                if parts.get("maiden name"):
                    given = [*parts.get("first name", ()), *parts.get("middle name", ())]
                    maiden = join_name([*given, *parts["maiden name"]])
                nicknames = list(parts.get("nickname", ()))
            else:
                full = join_name(parts.get("entity name", ()))
            if full is None and maiden is None and not nicknames:
                full = join_name(values)  # untyped parts: keep the name rather than lose it
            if full is None:
                pass
            elif primary and latin and not low and not names.name:
                names.name.append(full)
                if person:
                    for kind, prop in zip(PERSON_PARTS, PERSON_PROPS, strict=True):
                        props[prop] += parts.get(kind, [])
            elif low:
                names.weak.append(full)
            elif alias_type == "f.k.a.":
                names.previous.append(full)
            else:
                names.alias.append(full)
            if maiden:
                (names.weak if low else names.alias).append(maiden)
            names.weak += nicknames


def _place_names(names: Names, props: dict[str, list[str]], counts: Counter[str]) -> None:
    if not names.name:
        counts["parties_without_primary_name"] += 1
        names.name = (names.alias or names.previous or names.weak)[:1]
    taken = set(names.name)
    props["name"] = names.name
    props["alias"] = [a for a in dict.fromkeys(names.alias) if a not in taken]
    taken.update(props["alias"])
    props["previousName"] = [p for p in dict.fromkeys(names.previous) if p not in taken]
    taken.update(props["previousName"])
    props["weakAlias"] = [w for w in dict.fromkeys(names.weak) if w not in taken]


def _either(element: Element | None, name: str, other: str) -> Element | None:
    found = shared.child(element, name)
    return found if found is not None else shared.child(element, other)


def _period(period: Element, counts: Counter[str]) -> list[str]:
    """Deliverable 5: `Start/From` and `End/To` through `period_dates`; years only when either
    boundary is marked approximate."""
    start, end = shared.child(period, "Start"), shared.child(period, "End")
    first = _point(_either(start, "From", "To"))
    last = _point(_either(end, "To", "From"))
    if start is None:
        first = last
    if end is None:
        last = first
    approximate = any(b is not None and b.get("Approximate") == "true" for b in (start, end))
    dates = year_range(first[0], last[0]) if approximate else period_dates(first, last)
    counts["unparseable_dates"] += not dates
    return dates


def _detail(version: Element, tables: Tables) -> list[str]:
    found = []
    for detail in shared.children(version, "VersionDetail"):
        reference = detail.get("DetailReferenceID")
        value = tables.value("DetailReference", reference) if reference else shared.text(detail)
        found += [value] if value else []
    return found


def _locations(version: Element, tables: Tables) -> list[Place]:
    found = (
        tables.places.get(item.get("LocationID", ""))
        for item in shared.children(version, "VersionLocation")
    )
    return [place for place in found if place is not None]


def _feature(
    feature: Element,
    schema: str,
    tables: Tables,
    props: dict[str, list[str]],
    counts: Counter[str],
    skipped_types: Counter[str],
) -> None:
    kind = tables.value("FeatureType", feature.get("FeatureTypeID")) or "unknown"
    prop = FEATURES.get(kind.casefold())
    if prop is None or model[schema].get(prop) is None:
        skipped_types[_vocabulary(kind)] += 1
        counts["crypto_wallets_skipped"] += kind.casefold().startswith("digital currency address")
        return
    for version in shared.children(feature, "FeatureVersion"):
        if prop in ("birthDate", "incorporationDate"):
            for period in shared.children(version, "DatePeriod"):
                props[prop] += _period(period, counts)
        elif prop == "address":
            for place in _locations(version, tables):
                if place.parts:
                    props["address"].append(", ".join([*place.parts, place.country or ""]))
                props["country"].append(_country(place.country, place.iso2, counts) or "")
        elif prop in ("nationality", "citizenship"):
            places = _locations(version, tables)
            pairs = [(p.country, p.iso2) for p in places] or [
                (v, None) for v in _detail(version, tables)
            ]
            props[prop] += [_country(name, iso2, counts) or "" for name, iso2 in pairs]
        elif prop == "gender":
            for value in _detail(version, tables):
                gender = GENDERS.get(value.casefold())
                counts["unknown_genders"] += gender is None
                props["gender"].append(gender or "")
        else:
            props[prop] += _detail(version, tables)


def _documents(
    documents: Iterable[Document],
    schema: str,
    props: dict[str, list[str]],
    counts: Counter[str],
    skipped_types: Counter[str],
) -> None:
    """Deliverable 6. A number from a typed field goes through `uk_company_number`, which accepts
    only Companies House forms (M2.6 rule 6)."""
    has = model[schema].get
    for doc in documents:
        kind = doc.kind.casefold()
        if doc.fraudulent:
            counts["fraudulent_documents_skipped"] += 1
        elif not doc.number:
            counts["documents_without_number"] += 1
        elif kind in PASSPORTS and has("passportNumber"):
            props["passportNumber"].append("".join(doc.number.split()))
        elif kind in ID_NUMBERS and has("idNumber"):
            props["idNumber"].append("".join(doc.number.split()))
        elif kind == "uk company number" or (kind in UK_IF_ISSUED_IN_GB and doc.issued_by == "gb"):
            number = uk_company_number(doc.number)
            if number and has("registrationNumber"):
                props["registrationNumber"].append(number)
                props["jurisdiction"].append("gb")
            else:
                counts["uk_company_numbers_rejected"] += 1
        elif kind in LEI_TYPES:
            lei = "".join(doc.number.split()).upper()
            if is_valid_lei(lei) and has("leiCode"):
                props["leiCode"].append(lei)
            else:
                counts["leis_rejected"] += 1
        else:
            skipped_types[_vocabulary(doc.kind)] += 1


def _record(schema: str, record_id: str, props: dict[str, list[str]], ref: str) -> dict[str, Any]:
    values = {key: list(dict.fromkeys(v for v in items if v)) for key, items in props.items()}
    record = entity_record(schema, record_id, DATASET, values)
    record["nr"] = {"v": shared.RECORD_V, "source_ref": ref}
    return record


@dataclass(slots=True)
class Skipped:
    """Types counted, not loaded (summary keys ending in `_by_value`)."""

    features: Counter[str] = field(default_factory=Counter)
    documents: Counter[str] = field(default_factory=Counter)


def _party(
    element: Element, tables: Tables, counts: Counter[str], skipped: Skipped
) -> Iterator[dict[str, Any]]:
    profiles = list(shared.children(element, "Profile"))
    if len(profiles) > 1:
        counts["extra_profiles"] += len(profiles) - 1
    if not profiles:
        counts["parties_without_profile"] += 1
        return
    profile, fixed_ref = profiles[0], element.get("FixedRef", "")
    kind = party_kind(profile, tables)
    if kind not in SCHEMATA:
        counts[f"skipped_{kind.lower()}" if kind else "unknown_party_types"] += 1
        return
    loaded = tables.parties.get(profile.get("ID", ""))
    if loaded is None:
        counts["parties_without_name"] += 1
        return
    record_id, schema = loaded
    props: dict[str, list[str]] = defaultdict(list)
    props["topics"] = ["sanction"]
    names = Names()
    identities = list(shared.children(profile, "Identity"))
    for identity in identities:
        _names(identity, schema == "Person", tables, names, props, counts)
    _place_names(names, props, counts)
    for feature in shared.children(profile, "Feature"):
        _feature(feature, schema, tables, props, counts, skipped.features)
    for identity in identities:
        found = tables.documents.get(identity.get("ID", ""), [])
        _documents(found, schema, props, counts, skipped.documents)
    url = DETAILS_URL.format(fixed_ref)
    props["sourceUrl"] = [url]
    yield _record(schema, record_id, props, fixed_ref)
    for entry in tables.entries.get(profile.get("ID", ""), []):
        sanction: dict[str, list[str]] = {
            "entity": [record_id],
            "authority": [AUTHORITY],
            "country": [COUNTRY],
            "authorityId": [fixed_ref],
            "program": list(entry.programs),
            "provisions": list(entry.provisions),
            "startDate": [entry.start or ""],
            "sourceUrl": [url],
        }
        yield _record("Sanction", sanction_id(PREFIX, record_id, entry.id), sanction, entry.id)


def party_records(
    path: Path, tables: Tables, counts: Counter[str], skipped: Skipped
) -> Iterator[dict[str, Any]]:
    """Pass 2 (deliverable 2): one `DistinctParty` at a time; nothing is kept between them."""
    for section, element in _elements(path):
        if section == "DistinctParties":
            yield from _party(element, tables, counts, skipped)
        elif section in LAST_SECTIONS:
            return


def relationship_records(tables: Tables, counts: Counter[str]) -> Iterator[dict[str, Any]]:
    """Deliverable 8: links between two loaded parties of the list; never `Ownership`."""
    seen: set[str] = set()
    for relation in tables.relations:
        source, target = tables.parties.get(relation.source), tables.parties.get(relation.target)
        if source is None or target is None:
            counts["relationships_to_skipped_parties"] += 1
            continue
        (a, a_schema), (b, b_schema) = source, target
        known = RELATIONS.get(relation.kind.casefold())
        counts["unknown_relation_types"] += known is None
        schema, a_prop, b_prop = known or UNKNOWN_LINK
        persons = a_schema == b_schema == "Person"
        if schema in PERSONS_ONLY and not persons:
            schema, a_prop, b_prop = UNKNOWN_LINK
        elif schema in TARGETED and persons:
            schema, a_prop, b_prop = UNKNOWN_LINK
        elif schema in TARGETED:
            target_schema = a_schema if a_prop == TARGETED[schema] else b_schema
            if target_schema == "Person":  # note 2.9: a link in a reversed direction
                a_prop, b_prop = b_prop, a_prop
                counts["relationships_flipped"] += 1
        key = f"{a}|{b}|{relation.kind}".encode()
        digest = hashlib.sha1(key, usedforsecurity=False).hexdigest()[:20]
        record_id = f"{PREFIX}-{schema.lower()}-{digest}"
        if record_id in seen:
            counts["duplicate_relationships"] += 1
            continue
        seen.add(record_id)
        props: dict[str, list[str]] = {a_prop: [a], b_prop: [b]}
        if schema in PERSONS_ONLY:
            props["relationship"] = [relation.kind + (" (former)" if relation.former else "")]
        else:
            props["role"] = [relation.kind]
            props["status"] = ["former"] if relation.former else []
        yield _record(schema, record_id, props, relation.id)


def build(profile: Profile, context: BuildContext) -> BuildResult:
    # The block is validated (enabled, keep_reasons, keep_positions); OFAC gives no statement
    # of reasons, and titles stay among the counted feature types (M2.6 rule 7).
    profile.options(DATASET)
    download = shared.latest_download(DATASET, FILE_NAME)
    counts: Counter[str] = Counter()
    tables = read_tables(download.path, counts)
    skipped, tally = Skipped(), Tally()
    manifest_skipped: dict[str, int] = {}

    def records() -> Iterator[dict[str, Any]]:
        yield from party_records(download.path, tables, counts, skipped)
        yield from relationship_records(tables, counts)
        # write_records reads `skipped` after it has written the last record.
        manifest_skipped.update(
            Vessel=counts["skipped_vessel"],
            Airplane=counts["skipped_airplane"],
            CryptoWallet=counts["crypto_wallets_skipped"],
            relationships=counts["relationships_to_skipped_parties"],
        )

    stamp = shared.list_stamp(tables.stamp)
    notes = [f"list_generated: {stamp}", f"distinct_parties: {counts['distinct_parties']}"]
    shared.write_records(
        context.out_dir,
        DATASET,
        "us_ofac",
        tally.observe(records()),
        download,
        skipped=manifest_skipped,
        notes=notes,
    )
    rates = tally.rates()
    zero = [name for name in FATAL_RATES if rates[name] == 0]
    outside = shared.check_size(DATASET, tally.by_schema, zero, accept_size=context.accept_size)
    return BuildResult(
        counts={
            **{key: counts[key] for key in sorted(counts)},
            "records": {name.lower(): n for name, n in sorted(tally.by_schema.items())},
            "feature_types_not_loaded_by_value": dict(sorted(skipped.features.items())),
            "document_types_not_loaded_by_value": dict(sorted(skipped.documents.items())),
            "fill_rates": rates,
            "bounds_outside_accepted": outside,
        },
        strings={"list_generated": stamp},
    )


register_source_model(DATASET, shared.ListOptions)
register_source(SourceSpec(DATASET, shared.discover_static(FILE_NAME, URL)))
register_builder(Builder(DATASET, build, string_keys=("list_generated",)))
