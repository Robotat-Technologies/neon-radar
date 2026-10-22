"""EU Financial Sanctions Files loader (PHASE-2.md M2.6d; sanctions-peps.md section 4).

The Commission builds the consolidated list on request as XML 1.1, the format that keeps alias
strength (note 4.4). Each `sanctionEntity` is one party: `person` becomes a `Person`,
`enterprise` an `Organization`, any other subject type is skipped and counted. Each
`regulation` of the party becomes one `Sanction`. The download URL carries a token
(`NR_EU_FSF_TOKEN`, else the public one); every stored or logged URL leaves it out. Phone
numbers, e-mail addresses, websites (`contactInfo`) and documents marked false are never
loaded; remarks only as `Sanction:reason` with `keep_reasons`, titles and functions only with
`keep_positions`.
"""

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from xml.etree.ElementTree import Element, ParseError

import httpx
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import iterparse
from followthemoney.types import registry

from neonradar_contracts.records import ID_RE, make_id
from neonradar_ingest.data import gate
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
from neonradar_ingest.http import HttpClient, RateLimiter, Sleep
from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.lists import shared
from neonradar_ingest.sources.lists.common import parse_iso, partial_date, sanction_id, year_range
from neonradar_ingest.spikes import entity_record
from neonradar_keys.ids import uk_company_number, un_reference

DATASET = "eu_fsf"
PREFIX = "eufsf"
FILE_NAME = "xmlFullSanctionsList_1_1.xml"
URL = "https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content"
# The public token the Commission publishes with its links (note 4.1): base64 "token-2017".
PUBLIC_TOKEN = "dG9rZW4tMjAxNw"  # noqa: S105 (published, not a secret; .gitleaks.toml)
AUTHORITY = "European Union"
COUNTRY = "eu"
SCHEMATA = {"person": "Person", "enterprise": "Organization"}
GENDERS = {"M": "male", "F": "female"}
# The server builds the file on request: a long read timeout, five retries, backoff factor 3.
TIMEOUT = httpx.Timeout(60.0, connect=10.0, read=300.0)
RETRIES, BACKOFF = 5, 3.0
FATAL_RATES = ("person_birth_date", "sanction_program")  # zero means a broken parser
MAX_ID = 120  # PHASE-1.md 4.4
ADDRESS_PARTS = ("street", "poBox", "city", "zipCode", "region", "place")
BIRTH_PARTS = (
    "birthdate", "year", "monthOfYear", "dayOfMonth", "yearRangeFrom", "yearRangeTo", "circa",
    "city", "place", "countryIso2Code",
)  # fmt: skip


@dataclass(slots=True)
class Alias:
    whole: str
    first: str | None
    middle: str | None
    last: str | None
    language: str  # upper case; "" when the name has none
    strong: bool
    gender: str | None
    title: str | None
    function: str | None


@dataclass(slots=True)
class Regulation:
    key: str  # regulation@logicalId (the designation key of the Sanction id)
    programme: str | None
    number_title: str | None
    entry_into_force: str | None
    publication_date: str | None
    url: str | None


@dataclass(slots=True)
class Entry:
    """The fields of one `sanctionEntity` the loader may use (nothing else is kept)."""

    logical_id: str
    subject: str
    eu_ref: str | None = None
    un_ref: str | None = None
    designation_date: str | None = None
    remark: str | None = None
    regulations: list[Regulation] = field(default_factory=list)
    names: list[Alias] = field(default_factory=list)
    citizenships: list[str] = field(default_factory=list)
    births: list[dict[str, str]] = field(default_factory=list)
    documents: list[tuple[str, str | None, str]] = field(default_factory=list)  # code, country, no
    addresses: list[tuple[str, str | None]] = field(default_factory=list)


def token() -> str:
    """`NR_EU_FSF_TOKEN` from the environment or `.env`, else the public token."""
    secret = IngestSettings(_env_file=gate.ENV_FILE).nr_eu_fsf_token
    value = secret.get_secret_value().strip() if secret else ""
    return value or PUBLIC_TOKEN


def discover(client: HttpClient) -> list[RemoteFile]:
    """The one XML 1.1 file, its URL with the token (download.json stores it without)."""
    url = str(httpx.URL(URL, params={"token": token()}))
    return shared.discover_static(FILE_NAME, url)(client)


def make_client(
    transport: httpx.BaseTransport | None = None, sleep: Sleep = time.sleep
) -> HttpClient:
    """The list client (`shared.list_client`: no query string, so no token, in any log line or
    error) with the read timeout and retries the slow EU server needs."""
    client = HttpClient(
        "",
        follow_redirects=True,
        limiter=RateLimiter(1.0),
        retries=RETRIES,
        backoff=BACKOFF,
        sleep=sleep,
        log_query=False,
        transport=transport,
    )
    client.timeout = TIMEOUT
    return client


def _attr(element: Element, name: str) -> str | None:
    value = " ".join((element.get(name) or "").split())
    return value or None


def _alias(element: Element) -> Alias | None:
    whole = _attr(element, "wholeName")
    if whole is None:
        return None
    return Alias(
        whole=whole,
        first=_attr(element, "firstName"),
        middle=_attr(element, "middleName"),
        last=_attr(element, "lastName"),
        language=(_attr(element, "nameLanguage") or "").upper(),
        strong=(_attr(element, "strong") or "true").casefold() != "false",
        gender=_attr(element, "gender"),
        title=_attr(element, "title"),
        function=_attr(element, "function"),
    )


def _regulation(element: Element, position: int, counts: Counter[str]) -> Regulation:
    key = _attr(element, "logicalId")
    if key is None:
        counts["regulations_without_logical_id"] += 1
    return Regulation(
        key=key or f"n{position}",
        programme=_attr(element, "programme"),
        number_title=_attr(element, "numberTitle"),
        entry_into_force=_attr(element, "entryIntoForceDate"),
        publication_date=_attr(element, "publicationDate"),
        url=shared.text(element, "publicationUrl"),
    )


def _document(element: Element, counts: Counter[str]) -> tuple[str, str | None, str] | None:
    if (_attr(element, "knownFalse") or "").casefold() == "true":
        counts["false_documents_skipped"] += 1
        return None
    number = _attr(element, "number") or _attr(element, "latinNumber")
    if number is None:
        return None
    code = (_attr(element, "identificationTypeCode") or "").casefold()
    return code, _attr(element, "countryIso2Code"), "".join(number.split())


def _entry(element: Element, counts: Counter[str]) -> Entry | None:
    logical_id = _attr(element, "logicalId")
    if logical_id is None:
        counts["entities_without_logical_id"] += 1
        return None
    subject = shared.child(element, "subjectType")
    entry = Entry(
        logical_id=logical_id,
        subject=((_attr(subject, "code") if subject is not None else None) or "").casefold(),
        eu_ref=_attr(element, "euReferenceNumber"),
        un_ref=un_reference(_attr(element, "unitedNationId")),
        designation_date=_attr(element, "designationDate"),
        remark=shared.text(element, "remark"),
    )
    for position, item in enumerate(shared.children(element, "regulation")):
        entry.regulations.append(_regulation(item, position, counts))
    entry.names = [a for a in map(_alias, shared.children(element, "nameAlias")) if a]
    for item in shared.children(element, "citizenship"):
        code = _attr(item, "countryIso2Code")
        if code:
            entry.citizenships.append(code)
    for item in shared.children(element, "birthdate"):
        found = {name: value for name in BIRTH_PARTS if (value := _attr(item, name))}
        entry.births.append(found)
    for item in shared.children(element, "identification"):
        document = _document(item, counts)
        if document:
            entry.documents.append(document)
    for item in shared.children(element, "address"):
        parts = [_attr(item, name) for name in ADDRESS_PARTS]
        entry.addresses.append((", ".join(p for p in parts if p), _attr(item, "countryIso2Code")))
    return entry


def parse(path: Path) -> tuple[str | None, str | None, list[Entry], Counter[str]]:
    """The list's `generationDate` and `globalFileId`, its entries (one element at a time) and
    counts."""
    stamp: str | None = None
    file_id: str | None = None
    found: list[Entry] = []
    seen: set[str] = set()
    counts: Counter[str] = Counter()
    try:
        for event, element in iterparse(str(path), events=("start", "end")):
            name = shared.local(element.tag)
            if event == "start":
                if name == "export" and stamp is None:
                    stamp, file_id = (
                        _attr(element, "generationDate"),
                        _attr(element, "globalFileId"),
                    )
                continue
            if name != "sanctionEntity":
                continue
            counts["entities"] += 1
            entry = _entry(element, counts)
            element.clear()
            if entry is None:
                continue
            if entry.logical_id in seen:
                counts["duplicate_logical_ids"] += 1
                continue
            seen.add(entry.logical_id)
            found.append(entry)
    except (ParseError, DefusedXmlException) as exc:
        message = f"{DATASET}: {path.name} is not a well-formed list file ({type(exc).__name__})"
        raise BuildError(message, "xml", counts_only=True) from None
    return stamp, file_id, found, counts


def party_id(native: str) -> str:
    """`eufsf-<logicalId>` (PHASE-2.md 4.4); a logical id outside the C1 id alphabet goes
    through `make_id` (`eufsf-lid-...`, C1-record.md, OD-11)."""
    candidate = f"{PREFIX}-{native}"
    if ID_RE.fullmatch(candidate) and len(candidate) <= MAX_ID:
        return candidate
    return make_id(PREFIX, "lid", native)


def _country(value: str | None, counts: Counter[str]) -> str | None:
    """A lower-cased ISO code that FollowTheMoney's country type accepts; others are counted."""
    if not value:
        return None
    code = value.strip().lower()
    if registry.country.clean_text(code) is None:
        counts["unmapped_countries"] += 1
        return None
    return code


def _birth_dates(birth: dict[str, str], counts: Counter[str]) -> list[str]:
    """`@birthdate`, else the year, month and day, else a range of at most 20 years; `circa`
    keeps the year only."""
    dates: list[str] = []
    full = parse_iso(birth.get("birthdate"))
    if full:
        dates = [full]
    elif "year" in birth:
        part = partial_date(birth["year"], birth.get("monthOfYear"), birth.get("dayOfMonth"))
        dates = [part] if part else []
    elif "yearRangeFrom" in birth or "yearRangeTo" in birth:
        ends = [birth[key] for key in ("yearRangeFrom", "yearRangeTo") if key in birth]
        years = [year for year in (partial_date(end) for end in ends) if year]
        counts["unparseable_dates"] += len(years) < len(ends)  # an end that is not a year
        dates = year_range(years[0], years[1]) if len(years) == 2 else years
        counts["wide_year_ranges"] += len(years) == 2 and not dates
        return dates
    has_date = any(key in birth for key in ("birthdate", "year"))
    if has_date and not dates:
        counts["unparseable_dates"] += 1
    if birth.get("circa", "").casefold() == "true":
        dates = list(dict.fromkeys(value[:4] for value in dates))
    return dates


def _names(entry: Entry, person: bool, props: dict[str, list[str]], counts: Counter[str]) -> None:
    """Weak names to `weakAlias`; of the strong ones, the first without a language or in
    English is `name` (and gives the name parts of a person), the rest `alias`. Without one,
    the first strong name in another language; a weak name never becomes the name."""
    strong = [a for a in entry.names if a.strong]
    chosen = next((a for a in strong if a.language in ("", "EN")), None)
    if chosen is None:
        if not strong:
            return
        counts["parties_without_primary_name"] += 1
        chosen = strong[0]
    props["name"] = [chosen.whole]
    if person:
        props["firstName"].append(chosen.first or "")
        props["middleName"].append(chosen.middle or "")
        props["lastName"].append(chosen.last or "")
    props["alias"] = [a.whole for a in strong if a is not chosen and a.whole != chosen.whole]
    taken = {chosen.whole, *props["alias"]}
    props["weakAlias"] = [a.whole for a in entry.names if not a.strong and a.whole not in taken]
    counts["weak_aliases"] += len(set(props["weakAlias"]))


def _person(entry: Entry, props: dict[str, list[str]], counts: Counter[str], keep: bool) -> None:
    for alias in entry.names:
        if alias.gender:
            value = GENDERS.get(alias.gender.upper())
            counts["unknown_genders"] += value is None
            props["gender"].append(value or "")
        if keep:
            props["title"].append(alias.title or "")
            props["position"].append(alias.function or "")
    props["nationality"] += [_country(code, counts) or "" for code in entry.citizenships]
    for birth in entry.births:
        props["birthDate"] += _birth_dates(birth, counts)
        props["birthPlace"].append(birth.get("city") or birth.get("place") or "")
        props["birthCountry"].append(_country(birth.get("countryIso2Code"), counts) or "")
    for code, _country_code, number in entry.documents:
        if code == "passport":
            props["passportNumber"].append(number)
        elif code == "id":
            props["idNumber"].append(number)
        else:
            counts["identifications_not_loaded"] += 1


def _organization(entry: Entry, props: dict[str, list[str]], counts: Counter[str]) -> None:
    """Only a GB `regnumber` in a Companies House form is kept (it feeds rule D1)."""
    counts["organization_citizenships_not_loaded"] += len(entry.citizenships)
    for code, country, number in entry.documents:
        if code != "regnumber":
            counts["identifications_not_loaded"] += 1
            continue
        kept = uk_company_number(number) if (country or "").upper() == "GB" else None
        if kept is None:
            counts["registration_numbers_not_loaded"] += 1
            continue
        props["registrationNumber"].append(kept)
        props["jurisdiction"].append("gb")


def _record(schema: str, record_id: str, props: dict[str, list[str]], ref: str) -> dict[str, Any]:
    values = {key: list(dict.fromkeys(v for v in items if v)) for key, items in props.items()}
    record = entity_record(schema, record_id, DATASET, values)
    record["nr"] = {"v": shared.RECORD_V, "source_ref": ref}
    return record


def _start(entry: Entry, regulation: Regulation, counts: Counter[str]) -> str | None:
    """The earlier of the entity's designation date and the regulation's entry into force."""
    dates = []
    for value in (entry.designation_date, regulation.entry_into_force):
        parsed = parse_iso(value)
        counts["unparseable_dates"] += bool(value) and parsed is None
        dates += [parsed] if parsed else []
    return min(dates) if dates else None


def party_records(
    entry: Entry, options: shared.ListOptions, counts: Counter[str]
) -> list[dict[str, Any]]:
    """The party's `Person` or `Organization` record, then one `Sanction` per regulation."""
    schema = SCHEMATA[entry.subject]
    pid = party_id(entry.logical_id)
    props: dict[str, list[str]] = defaultdict(list)
    props["topics"] = ["sanction"]
    _names(entry, schema == "Person", props, counts)
    if not props["name"]:
        counts["no_strong_name"] += 1
        return []
    if schema == "Person":
        _person(entry, props, counts, options.keep_positions)
    else:
        _organization(entry, props, counts)
    for address, country in entry.addresses:
        props["address"].append(address)
        props["country"].append(_country(country, counts) or "")
    records = [_record(schema, pid, props, entry.logical_id)]
    counts["entities_without_regulation"] += not entry.regulations
    for regulation in entry.regulations:
        sanction: dict[str, list[str]] = {
            "entity": [pid],
            "authority": [AUTHORITY],
            "country": [COUNTRY],
            "authorityId": [entry.eu_ref or entry.logical_id],
            "unscId": [entry.un_ref or ""],
            "program": [regulation.programme or ""],
            "programId": [regulation.number_title or ""],
            "startDate": [_start(entry, regulation, counts) or ""],
            "listingDate": [parse_iso(regulation.publication_date) or ""],
            "sourceUrl": [regulation.url or ""],
        }
        if options.keep_reasons and entry.remark:
            sanction["reason"] = [entry.remark]
        sid = sanction_id(PREFIX, pid, regulation.key)
        records.append(_record("Sanction", sid, sanction, regulation.key))
    return records


def fill_rates(records: list[dict[str, Any]]) -> dict[str, float]:
    """The shares of M2.6 rule 10, plus `unscId` (empty in every record the note read)."""
    sanctions = [r for r in records if r["schema"] == "Sanction"]
    with_unsc = sum(bool(r["properties"].get("unscId")) for r in sanctions)
    return {
        **shared.fill_rates(records),
        "sanction_unsc_id": shared.rate(with_unsc, len(sanctions)),
    }


def build(profile: Profile, context: BuildContext) -> BuildResult:
    options: shared.ListOptions = profile.options(DATASET)
    download = shared.latest_download(DATASET, FILE_NAME)
    raw_stamp, raw_file_id, entries, counts = parse(download.path)
    records: list[dict[str, Any]] = []
    for entry in entries:
        if entry.subject in SCHEMATA:
            records += party_records(entry, options, counts)
        else:
            counts["skipped_subject_types"] += 1
    by_schema = Counter(str(record["schema"]) for record in records)
    rates = fill_rates(records)
    zero = [name for name in FATAL_RATES if rates[name] == 0]
    outside = shared.check_size(DATASET, by_schema, zero, accept_size=context.accept_size)
    stamp, file_id = shared.list_stamp(raw_stamp), shared.list_stamp(raw_file_id)
    skipped = {
        "other_subject_types": counts["skipped_subject_types"],
        "known_false_documents": counts["false_documents_skipped"],
    }
    notes = [
        f"list_generated: {stamp}",
        f"global_file_id: {file_id}",
        f"entities: {counts['entities']}",
    ]
    shared.write_records(
        context.out_dir, DATASET, "eu_fsf", records, download, skipped=skipped, notes=notes
    )
    return BuildResult(
        counts={
            **{key: counts[key] for key in sorted(counts)},
            "records": {name.lower(): count for name, count in sorted(by_schema.items())},
            "fill_rates": rates,
            "bounds_outside_accepted": outside,
        },
        strings={"list_generated": stamp, "global_file_id": file_id},
    )


register_source_model(DATASET, shared.ListOptions)
register_source(SourceSpec(DATASET, discover, make_client))
register_builder(Builder(DATASET, build, string_keys=("list_generated", "global_file_id")))
