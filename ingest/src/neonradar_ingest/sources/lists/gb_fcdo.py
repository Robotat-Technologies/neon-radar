"""UK Sanctions List loader (PHASE-2.md M2.6a; sanctions-peps.md section 1).

The FCDO publishes one XML file (schema `SanctionsListSchema-4.33.3.xsd`, committed under
`ingest/tests/fixtures/lists/gb_fcdo_sanctions/`). One person or entity can have several
designations, one Unique ID per regime, so the builder groups designations into parties: by
OFSI Group ID, then by UN reference number, else one party per Unique ID (deliverable 4). Each
party becomes one `Person` or `Organization` with `topics: ["sanction"]`, and each designation
one `Sanction`. Ships are skipped and counted. Phone numbers, e-mail addresses, websites, other
information, crypto wallet addresses, parent companies and subsidiaries are never loaded;
statements of reasons, titles and positions only when the profile block asks for them.
"""

import html
import re
from collections import Counter, defaultdict
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, ParseError

from defusedxml import DefusedXmlException
from defusedxml.ElementTree import iterparse

from neonradar_contracts.records import ID_RE, make_id
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
    extract_leis,
    join_name,
    parse_dmy,
    sanction_id,
    split_values,
    uk_company_numbers,
)
from neonradar_ingest.spikes import entity_record
from neonradar_keys.countries import country_code
from neonradar_keys.ids import un_reference

DATASET = "gb_fcdo_sanctions"
PREFIX = "uksl"
FILE_NAME = "UK-Sanctions-List.xml"
URL = "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"
AUTHORITY = "UK Foreign, Commonwealth and Development Office"
COUNTRY = "gb"
SCHEMATA = {"Individual": "Person", "Entity": "Organization"}
SKIPPED_TYPES = {"Ship": "Vessel"}  # M2.6 rule 5: not a C1 schema
GENDERS = {"male": "male", "female": "female"}
FATAL_RATES = ("person_birth_date", "sanction_program")  # zero means a broken parser
# The children of Designation in XSD 4.33.3; any other one is counted (a format change).
KNOWN = frozenset(
    {
        "LastUpdated", "DateDesignated", "UniqueID", "OFSIGroupID", "UNReferenceNumber", "Names",
        "NonLatinNames", "Titles", "RegimeName", "IndividualEntityShip", "DesignationSource",
        "SanctionsImposed", "SanctionsImposedIndicators", "OtherInformation",
        "UKStatementofReasons", "Addresses", "PhoneNumbers", "Websites", "CryptoWalletAddresses",
        "EmailAddresses", "IndividualDetails", "EntityDetails", "ShipDetails",
    }
)  # fmt: skip
NUMBER_TOKEN = re.compile(r"[A-Za-z0-9]*\d[A-Za-z0-9]*")
MAX_ID = 120  # PHASE-1.md 4.4
MIN_NUMBER = 5  # shorter digit runs in a registration string are not counted as numbers
INDIVIDUAL = ("IndividualDetails", "Individual")
ENTITY = ("EntityDetails", "Entity")


@dataclass(slots=True)
class Name:
    parts: tuple[str | None, ...]  # Name1 to Name6 (Name6: surname or the entity's name)
    kind: str
    strength: str


@dataclass(slots=True)
class Designation:
    """The fields of one `Designation` element the loader may use (nothing else is kept)."""

    unique_id: str
    group_id: str | None
    un_ref: str | None
    kind: str
    regime: str | None = None
    imposed: str | None = None
    designated: str | None = None
    updated: str | None = None
    reasons: str | None = None
    names: list[Name] = field(default_factory=list)
    non_latin: list[str] = field(default_factory=list)
    titles: list[str] = field(default_factory=list)
    addresses: list[tuple[str, str | None]] = field(default_factory=list)
    dobs: list[str] = field(default_factory=list)
    passports: list[str] = field(default_factory=list)
    national_ids: list[str] = field(default_factory=list)
    nationalities: list[str] = field(default_factory=list)
    positions: list[str] = field(default_factory=list)
    genders: list[str] = field(default_factory=list)
    births: list[tuple[str | None, str | None]] = field(default_factory=list)
    registrations: list[str] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class Party:
    id: str
    source_ref: str
    form: str  # group, un_reference or unique_id
    members: tuple[Designation, ...]


def _address(element: Element) -> tuple[str, str | None]:
    names = [f"AddressLine{n}" for n in range(1, 7)] + ["AddressPostalCode", "AddressCountry"]
    parts = [shared.text(element, name) for name in names]
    return ", ".join(part for part in parts if part), shared.text(element, "AddressCountry")


def _designation(element: Element, counts: Counter[str]) -> Designation | None:
    unique_id = shared.text(element, "UniqueID")
    if unique_id is None:
        counts["designations_without_unique_id"] += 1
        return None
    counts["unknown_elements"] += sum(shared.local(item.tag) not in KNOWN for item in element)
    t = shared.texts
    d = Designation(
        unique_id=unique_id,
        group_id=shared.text(element, "OFSIGroupID"),
        un_ref=un_reference(shared.text(element, "UNReferenceNumber")),
        kind=(shared.text(element, "IndividualEntityShip") or "").capitalize(),
        regime=shared.text(element, "RegimeName"),
        imposed=shared.text(element, "SanctionsImposed"),
        designated=shared.text(element, "DateDesignated"),
        updated=shared.text(element, "LastUpdated"),
        reasons=shared.text(element, "UKStatementofReasons"),
        non_latin=t(element, "NonLatinNames", "NonLatinName", "NameNonLatinScript"),
        titles=t(element, "Titles", "Title"),
        dobs=t(element, *INDIVIDUAL, "DOBs", "DOB"),
        passports=t(element, *INDIVIDUAL, "PassportDetails", "Passport", "PassportNumber"),
        national_ids=t(
            element,
            *INDIVIDUAL,
            "NationalIdentifierDetails",
            "NationalIdentifier",
            "NationalIdentifierNumber",
        ),
        nationalities=t(element, *INDIVIDUAL, "Nationalities", "Nationality"),
        positions=t(element, *INDIVIDUAL, "Positions", "Position"),
        genders=t(element, *INDIVIDUAL, "Genders", "Gender"),
        registrations=t(
            element, *ENTITY, "BusinessRegistrationNumbers", "BusinessRegistrationNumber"
        ),
    )
    for name in shared.children(shared.child(element, "Names"), "Name"):
        parts = tuple(shared.text(name, f"Name{n}") for n in range(1, 7))
        kind, strength = shared.text(name, "NameType"), shared.text(name, "AliasStrength")
        d.names.append(Name(parts, (kind or "").casefold(), (strength or "").casefold()))
    for address in shared.children(shared.child(element, "Addresses"), "Address"):
        d.addresses.append(_address(address))
    for individual in shared.children(shared.child(element, INDIVIDUAL[0]), INDIVIDUAL[1]):
        for location in shared.children(shared.child(individual, "BirthDetails"), "Location"):
            births = (shared.text(location, "TownOfBirth"), shared.text(location, "CountryOfBirth"))
            d.births.append(births)
    stubs = t(element, *ENTITY, "ParentCompanies", "ParentCompany")
    stubs += t(element, *ENTITY, "Subsidiaries", "Subsidiary")
    counts["stub_names_skipped"] += sum(len(split_values(value)) for value in stubs)
    counts["crypto_wallets_skipped"] += len(
        t(element, "CryptoWalletAddresses", "CryptoWalletAddress")
    )
    return d


def parse(path: Path) -> tuple[str | None, list[Designation], Counter[str]]:
    """The list's `DateGenerated`, its designations (one element at a time) and counts."""
    stamp: str | None = None
    found: list[Designation] = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    try:
        for _event, element in iterparse(str(path), events=("end",)):
            name = shared.local(element.tag)
            if name == "DateGenerated" and stamp is None:
                stamp = shared.text(element)
            elif name == "Designation":
                counts["designations"] += 1
                designation = _designation(element, counts)
                element.clear()
                if designation is None:
                    continue
                if designation.unique_id in seen:
                    counts["duplicate_unique_ids"] += 1
                    continue
                seen.add(designation.unique_id)
                found.append(designation)
    except (ParseError, DefusedXmlException) as exc:
        message = f"{DATASET}: {path.name} is not a well-formed list file ({type(exc).__name__})"
        raise BuildError(message, "xml", counts_only=True) from None
    return stamp, found, counts


# The id kinds of PHASE-2.md 4.4 and the `make_id` kind used when a native id breaks R1.
ID_FORMS = {"group": ("g", "g"), "un_reference": ("un-", "un"), "unique_id": ("", "uid")}


def party_id(form: str, native: str) -> str:
    """`uksl-g<group id>`, `uksl-un-<UN reference>` or `uksl-<Unique ID>` (PHASE-2.md 4.4); a
    native id outside the C1 id alphabet goes through `make_id` (C1-record.md, OD-11)."""
    marker, kind = ID_FORMS[form]
    candidate = f"{PREFIX}-{marker}{native}"
    if ID_RE.fullmatch(candidate) and len(candidate) <= MAX_ID:
        return candidate
    return make_id(PREFIX, kind, native)


def _party(form: str, native: str, members: Iterable[Designation]) -> Party:
    """A party, its designations ordered by Unique ID: the smallest gives the name."""
    ordered = tuple(sorted(members, key=lambda member: member.unique_id))
    marker = ID_FORMS[form][0]
    return Party(party_id(form, native), f"{marker}{native}", form, ordered)


def _single(designation: Designation) -> Party:
    return _party("unique_id", designation.unique_id, (designation,))


def _kinds(members: Iterable[Designation]) -> int:
    return len({member.kind for member in members})


def group(designations: list[Designation], counts: Counter[str]) -> list[Party]:
    """Parties in the order of deliverable 4: OFSI Group ID, then UN reference, else Unique ID.

    A group whose designations disagree on `IndividualEntityShip` is split into its Unique IDs,
    and a designation whose UN reference sits on two groups (or on a group of another type)
    joins none; each such case counts as a `group_conflict`. An ungrouped designation with a
    UN reference is `uksl-un-<reference>` even alone (PHASE-2.md 4.4), so its id stays the
    same when the UK adds a second designation for that listing.
    """
    parties: list[Party] = []
    by_group: dict[str, list[Designation]] = defaultdict(list)
    ungrouped: list[Designation] = []
    for designation in designations:
        if designation.group_id:
            by_group[designation.group_id].append(designation)
        else:
            ungrouped.append(designation)
    groups: dict[str, list[Designation]] = {}
    for gid, members in by_group.items():
        if _kinds(members) > 1:
            counts["group_conflicts"] += 1
            parties.extend(_single(member) for member in members)
        else:
            groups[gid] = members
    un_groups: dict[str, set[str]] = defaultdict(set)
    for gid, members in groups.items():
        for member in members:
            if member.un_ref:
                un_groups[member.un_ref].add(gid)
    remaining: list[Designation] = []
    for designation in ungrouped:
        targets = sorted(un_groups.get(designation.un_ref or "", ()))
        if not targets:
            remaining.append(designation)
        elif len(targets) == 1 and groups[targets[0]][0].kind == designation.kind:
            groups[targets[0]].append(designation)
            counts["joined_by_un_reference"] += 1
        else:
            counts["group_conflicts"] += 1
            parties.append(_single(designation))
    by_un: dict[str, list[Designation]] = defaultdict(list)
    for designation in remaining:
        if designation.un_ref:
            by_un[designation.un_ref].append(designation)
        else:
            parties.append(_single(designation))
    for ref, members in by_un.items():
        if _kinds(members) > 1:
            counts["group_conflicts"] += 1
            parties.extend(_single(member) for member in members)
        else:
            parties.append(_party("un_reference", ref, members))
    for gid, members in groups.items():
        parties.append(_party("group", gid, members))
    return sorted(parties, key=lambda party: party.id)


def _full_name(parts: tuple[str | None, ...], person: bool) -> str | None:
    """Person: Name1 to Name6 in order (Name6 is the surname); entity: Name6, else the join."""
    if not person and parts[5]:
        return parts[5]
    return join_name(parts)


def _strong(name: Name, full: str, counts: Counter[str]) -> bool:
    """`AliasStrength`: good quality to alias, low quality to weakAlias; empty: two or more
    words to alias. An unknown strength is counted and treated as weak (never a match alone)."""
    if name.strength.startswith("good quality"):
        return True
    if name.strength.startswith("low quality"):
        return False
    if name.strength:
        counts["unknown_alias_strengths"] += 1
        return False
    return len(full.split()) >= 2


def _country(value: str | None, counts: Counter[str]) -> str | None:
    code = country_code(value)
    if value and code is None:
        counts["unmapped_countries"] += 1
    return code


def _date(value: str | None, counts: Counter[str]) -> str | None:
    parsed = parse_dmy(value)
    if value and parsed is None:
        counts["unparseable_dates"] += 1
    return parsed


def _names(party: Party, person: bool, props: dict[str, list[str]], counts: Counter[str]) -> None:
    primary: list[str] = []
    aliases: list[str] = []
    weak: list[str] = []
    for designation in party.members:
        for name in designation.names:
            full = _full_name(name.parts, person)
            if full is None:
                counts["empty_names"] += 1
            elif name.kind == "primary name":
                if not primary and person:
                    props["firstName"].append(name.parts[0] or "")
                    props["lastName"].append(name.parts[5] or "")
                (aliases if primary else primary).append(full)
            elif name.kind == "primary name variation":
                aliases.append(full)
            elif name.kind == "alias":
                (aliases if _strong(name, full, counts) else weak).append(full)
            else:
                counts["unknown_name_types"] += 1
        aliases.extend(designation.non_latin)
    if not primary:  # a strong alias may stand in; a weak alias never becomes the name
        counts["parties_without_primary_name"] += 1
        primary = aliases[:1]
    taken = set(primary)
    props["name"] = primary
    props["alias"] = [a for a in dict.fromkeys(aliases) if a not in taken]
    taken.update(props["alias"])
    props["weakAlias"] = [w for w in dict.fromkeys(weak) if w not in taken]


def _person(d: Designation, props: dict[str, list[str]], counts: Counter[str]) -> None:
    props["birthDate"] += [v for v in (_date(x, counts) for x in d.dobs) if v]
    props["nationality"] += [v for v in (_country(x, counts) for x in d.nationalities) if v]
    for town, country in d.births:
        props["birthPlace"].append(town or "")
        props["birthCountry"].append(_country(country, counts) or "")
    for gender in d.genders:
        value = GENDERS.get(gender.casefold())
        counts["unknown_genders"] += value is None
        props["gender"].append(value or "")
    props["passportNumber"] += ["".join(x.split()) for x in d.passports]
    props["idNumber"] += ["".join(x.split()) for x in d.national_ids]


def _organization(d: Designation, props: dict[str, list[str]], counts: Counter[str]) -> None:
    for value in d.registrations:
        numbers, leis = uk_company_numbers(value), extract_leis(value)
        props["registrationNumber"] += numbers
        props["leiCode"] += leis
        if numbers:
            props["jurisdiction"].append(COUNTRY)
        kept = set(numbers) | set(leis)
        others = [
            token
            for token in NUMBER_TOKEN.findall(value)
            if len(token) >= MIN_NUMBER and token.upper() not in kept
        ]
        counts["registration_numbers_not_loaded"] += len(others)


def _record(schema: str, record_id: str, props: dict[str, list[str]], ref: str) -> dict[str, Any]:
    values = {key: list(dict.fromkeys(v for v in items if v)) for key, items in props.items()}
    record = entity_record(schema, record_id, DATASET, values)
    record["nr"] = {"v": shared.RECORD_V, "source_ref": ref}
    return record


def party_records(
    party: Party, options: shared.ListOptions, counts: Counter[str]
) -> list[dict[str, Any]]:
    """The party's `Person` or `Organization` record, then one `Sanction` per designation."""
    schema = SCHEMATA[party.members[0].kind]
    person = schema == "Person"
    props: dict[str, list[str]] = defaultdict(list)
    props["topics"] = ["sanction"]
    _names(party, person, props, counts)
    if not props["name"]:
        counts["no_strong_name"] += 1
        return []
    for d in party.members:
        if person:
            _person(d, props, counts)
            if options.keep_positions:
                props["title"] += d.titles
                props["position"] += [p for value in d.positions for p in split_values(value)]
        else:
            _organization(d, props, counts)
        for address, country in d.addresses:
            props["address"].append(address)
            props["country"].append(_country(country, counts) or "")
    records = [_record(schema, party.id, props, party.source_ref)]
    for d in party.members:
        sanction: dict[str, list[str]] = {
            "entity": [party.id],
            "authority": [AUTHORITY],
            "country": [COUNTRY],
            "authorityId": [d.unique_id],
            "unscId": [d.un_ref or ""],
            "program": [d.regime or ""],
            "startDate": [_date(d.designated, counts) or ""],
            "modifiedAt": [_date(d.updated, counts) or ""],
            "provisions": split_values(d.imposed),
        }
        if options.keep_reasons and d.reasons:
            sanction["reason"] = [html.unescape(d.reasons)]
        sid = sanction_id(PREFIX, party.id, d.unique_id)
        records.append(_record("Sanction", sid, sanction, d.unique_id))
    return records


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: shared.ListOptions = profile.options(DATASET)
    download = shared.latest_download(DATASET, FILE_NAME)
    raw_stamp, designations, counts = parse(download.path)
    kept: list[Designation] = []
    for designation in designations:
        if designation.kind in SCHEMATA:
            kept.append(designation)
        elif designation.kind in SKIPPED_TYPES:
            counts[f"skipped_{SKIPPED_TYPES[designation.kind].lower()}"] += 1
        else:
            counts["unknown_designation_types"] += 1
    parties = group(kept, counts)
    records = [record for party in parties for record in party_records(party, options, counts)]
    by_schema = Counter(str(record["schema"]) for record in records)
    rates = shared.fill_rates(records)
    zero = [name for name in FATAL_RATES if rates[name] == 0]
    outside = shared.check_size(DATASET, by_schema, zero, accept_size=context.accept_size)
    stamp = shared.list_stamp(raw_stamp)
    forms = Counter(party.form for party in parties)
    skipped = {
        "Vessel": counts["skipped_vessel"],
        "CryptoWallet": counts["crypto_wallets_skipped"],
        "stub_names": counts["stub_names_skipped"],
    }
    notes = [f"list_generated: {stamp}", f"designations: {counts['designations']}"]
    shared.write_records(
        context.out_dir, DATASET, "gb_fcdo", records, download, skipped=skipped, notes=notes
    )
    return BuildResult(
        counts={
            **{key: counts[key] for key in sorted(counts)},
            "records": {name.lower(): count for name, count in sorted(by_schema.items())},
            "parties": {form: forms[form] for form in ("group", "un_reference", "unique_id")},
            "fill_rates": rates,
            "bounds_outside_accepted": outside,
        },
        strings={"list_generated": stamp},
    )


register_source_model(DATASET, shared.ListOptions)
register_source(SourceSpec(DATASET, shared.discover_static(FILE_NAME, URL)))
register_builder(Builder(DATASET, build, string_keys=("list_generated",)))
