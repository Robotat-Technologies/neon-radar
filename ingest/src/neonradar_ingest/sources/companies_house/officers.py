"""The `officers` step: officers of the slice companies through the API (PHASE-2.md M2.3c).

The real-data gate comes first (`access.companies_house_key`, the profile, the data protection
documents, CI and Codespaces, the approved machine: exit 3), then the key (`CH_API_KEY`, read
through the settings object only), both before any request or file write. Then, for each
company of `slice.csv` that has a `Company` record, in the file's order (seeds, then parents
and children by level, then the district sample in hash order), the step pages through
`GET /company/{number}/officers?items_per_page=100&start_index=<k>`, advancing `k` by the
items returned until `total_results` (whether a gateway caps the page size is not known,
research note bulk-sources-loading.md 5). The Phase 1 client rules apply (`client.py`): basic
auth with the key, 2 requests per second (600 per 5 minutes), after a 429 a wait until
`X-Ratelimit-Reset` or 300 seconds; 429 and 5xx answers are retried three times with backoff,
then the fetch stops, keeps what it has and reports it (2.7 rule 4).

**Budget, cache and resume.** No request goes out once `request_budget` requests (retries
included) have gone out in this run. Every answer, reduced to the fields the records use
(`minimal`), is cached in
`officer_cache_dir()/<first 20 hex of sha1(company number)>/<start_index>.json` with the time
it was fetched and the query it answered, so folder names do not name the company numbers
directly; an entry younger than `cache_days` for the same query is a hit and costs no request.
After the budget runs out or the fetch stops, the remaining companies are read from the cache
only, so a re-run finishes what an earlier one left.

**Records.** One record per officer id (from `links.officer.appointments`) across all
companies, one `Directorship` per appointment, and one `Address` per distinct service address
key, shared with the company and PSC records. Only the fields in the M2.3c list are read:
never a usual residential address, a day of birth, the occupation, former names, contact or
identity verification details, or the care-of line. Messages, logs and the summary hold
counts, enumeration values and field names only.
"""

import hashlib
import json
import os
import time
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt, field_validator

from neonradar_contracts.records import Producer, Source, make_id, write_manifest
from neonradar_ingest import __version__
from neonradar_ingest.data import gate, layout
from neonradar_ingest.data.profiles import Profile
from neonradar_ingest.data.project import Project
from neonradar_ingest.data.sources import BuildError
from neonradar_ingest.http import HttpError, RateLimiter
from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house import bulk, psc, records
from neonradar_ingest.sources.companies_house import slice as slices
from neonradar_ingest.sources.companies_house.client import (
    BASE_URL,
    REQUESTS_PER_SECOND,
    CompaniesHouseClient,
)
from neonradar_ingest.sources.companies_house.identification import is_uk, uk_number
from neonradar_ingest.sources.companies_house.mapping import edge_id, last_segment, officer_id
from neonradar_keys.countries import country_code
from neonradar_keys.names import split_ch_name

STEP = "officers"
RECORD_FILE = "officers.ftm.jsonl"
PATH = "/company/{}/officers"
PAGE_SIZE = 100
DAY = 86_400.0
STOPPED = ("done", "budget", "http_error")
COMPANY_STATUSES = ("complete", "partial", "not_reached", "not_found")
NOMINEE = ("nominee-", "corporate-nominee-")
# The only item fields the step reads, so the only ones the cache keeps (`minimal`).
ITEM_FIELDS = ("name", "officer_role", "appointed_on", "resigned_on", "nationality",
               "country_of_residence", "person_number")  # fmt: skip
ADDRESS_FIELDS = ("premises", *psc.ADDRESS)  # never care_of
IDENTIFICATION_FIELDS = ("identification_type", "legal_authority", "legal_form", "place_registered",
                         "registration_number", "country_registered")  # fmt: skip
# Counters the summary always shows, also when zero (as M2.3a's `records.COUNTED`).
COUNTED = (
    "appointments_duplicate",
    "appointments_without_officer_id",
    "appointments_without_role",
    "cache_hits",
    "cache_stale",
    "cache_unreadable",
    "corporate_uk_numbers_invalid",
    "lists_shorter_than_total",
    "nationalities_unmapped",
    "names_not_split",
    "officer_schema_conflicts",
    "officers_without_address_key",
    "officers_without_name",
    "pages_fetched",
    "person_number_conflicts",
    "person_numbers",
    "person_numbers_not_12_digits",
    "residence_unmapped",
    "slice_companies_without_record",
)


class OfficersBlock(BaseModel):
    """The `officers` block of a profile (PHASE-2.md 7.8, M2.3c deliverable 4)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: StrictBool
    request_budget: StrictInt = Field(default=20_000, ge=0)  # OD-22: 20,000 for uk-sample
    cache_days: StrictInt = Field(default=30, ge=0)
    appointments: StrictBool = False
    active_only: StrictBool = False

    @field_validator("appointments")
    @classmethod
    def _never_appointments(cls, value: bool) -> bool:
        if value:
            raise ValueError("appointments must be false: Phase 2 never calls the appointments API")
        return value


class KeyMissing(BuildError):
    """`CH_API_KEY` is not set: a refusal before any request (exit 2)."""

    exit_code = 2


@dataclass(frozen=True)
class Network:
    """What the step talks through; tests replace `NETWORK` with a mock transport and clocks."""

    transport: httpx.BaseTransport | None = None
    sleep: Callable[[float], None] = time.sleep
    clock: Callable[[], float] = time.time  # wall clock: cache age, X-Ratelimit-Reset
    monotonic: Callable[[], float] = time.monotonic  # the rate limiter and the duration


NETWORK = Network()


class BudgetExhausted(Exception):
    """The run's request budget is spent: the next request does not go out."""


class BudgetLimiter(RateLimiter):
    """Two requests per second, and none after the budget's last (retries count too)."""

    def __init__(self, per_second: float, budget: int, network: Network) -> None:
        super().__init__(per_second, clock=network.monotonic, sleep=network.sleep)
        self.budget, self.used = budget, 0

    def wait(self) -> None:
        if self.used >= self.budget:
            raise BudgetExhausted
        super().wait()
        self.used += 1


def api_key(project: Project, profile: Profile) -> str:
    """The gate (exit 3), then the key (exit 2 when missing): before any request or write."""
    gate.check_real_data(project, profile, bulk.DATASET, step=STEP)
    key = IngestSettings(_env_file=gate.ENV_FILE).companies_house_key()
    if key is None:
        message = (
            "CH_API_KEY is not set: the operator adds it to .env (OD-14); the officers step"
            " sent no request"
        )
        raise KeyMissing(message, "CH_API_KEY", counts_only=True)
    return key


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _pick(value: object, names: Sequence[str]) -> dict[str, Any]:
    return {name: item for name, item in _dict(value).items() if name in names}


def minimal(body: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """An answer with only the fields the step reads: no usual residential address, day of
    birth, occupation, former names, name elements, contact or identity verification details
    or care-of line ever reaches the cache. Items stay in place, so paging is unchanged."""
    if body is None:
        return None
    raw = body.get("items")
    items = []
    for item in raw if isinstance(raw, list) else []:
        kept = _pick(item, ITEM_FIELDS)
        if birth := _pick(_dict(item).get("date_of_birth"), ("month", "year")):
            kept["date_of_birth"] = birth
        for name, fields in (
            ("address", ADDRESS_FIELDS),
            ("identification", IDENTIFICATION_FIELDS),
        ):
            if part := _pick(_dict(item).get(name), fields):
                kept[name] = part
        corporate = (_str(_dict(item).get("officer_role")) or "").startswith("corporate-")
        if corporate and (country := _pick(kept.pop("address", None), ("country",))):
            kept["address"] = country  # a corporate officer's address: its country, for `is_uk`
        links = _dict(_dict(item).get("links"))
        # `links.self` holds the company number: only its last segment, the appointment id
        if appointment := last_segment(links.get("self")):
            kept["appointment_id"] = appointment
        if officer := _pick(links.get("officer"), ("appointments",)):
            kept["links"] = {"officer": officer}
        items.append(kept)
    return {"items": items, "total_results": body.get("total_results")}


class Cache:
    """Answers by company and start index; a hit is fresh (`cache_days`) and for one query."""

    def __init__(self, days: int, active_only: bool, network: Network, stats: Counter[str]):
        self.root, self.days, self.active_only = layout.officer_cache_dir(), days, active_only
        self.clock, self.stats = network.clock, stats

    def query(self, start: int) -> dict[str, Any]:
        query: dict[str, Any] = {"items_per_page": PAGE_SIZE, "start_index": start}
        return query | ({"filter": "active"} if self.active_only else {})

    def path(self, number: str, start: int) -> Path:
        folder = hashlib.sha1(number.encode(), usedforsecurity=False).hexdigest()[:20]
        return self.root / folder / f"{start}.json"

    def get(self, number: str, start: int) -> tuple[dict[str, Any] | None] | None:
        """`(body,)` for a hit (body None: the API answered 404), None for a miss."""
        try:
            entry = json.loads(self.path(number, start).read_text(encoding="utf-8"))
        except FileNotFoundError:
            return None
        except OSError, ValueError:
            self.stats["cache_unreadable"] += 1
            return None
        entry = _dict(entry)
        fetched, body = entry.get("fetched_at"), entry.get("body")
        if entry.get("query") != self.query(start) or not isinstance(fetched, int | float):
            self.stats["cache_stale"] += 1
            return None
        if not 0 <= self.clock() - fetched <= self.days * DAY or not isinstance(body, dict | None):
            self.stats["cache_stale"] += 1
            return None
        return (body,)

    def put(self, number: str, start: int, body: dict[str, Any] | None) -> None:
        """Write atomically, so an interrupted run never leaves half an entry."""
        path = self.path(number, start)
        path.parent.mkdir(parents=True, exist_ok=True)
        entry = {"fetched_at": self.clock(), "query": self.query(start), "body": body}
        temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
        temporary.write_text(json.dumps(entry, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)


class Fetcher:
    """Pages of each company from the cache or the API, within the budget."""

    def __init__(self, client: CompaniesHouseClient, cache: Cache, stats: Counter[str]):
        self.client, self.cache, self.stats = client, cache, stats
        self.stopped_by, self.error_status = "done", 0

    def company(self, number: str) -> tuple[str, list[dict[str, Any]]]:
        """The company's status and the officer items in hand."""
        start, items = 0, list[dict[str, Any]]()
        while True:
            hit = self.cache.get(number, start)
            if hit is not None:
                self.stats["cache_hits"] += 1
                body = hit[0]
            elif self.stopped_by != "done":
                break  # after the budget or an error: the cache only
            else:
                try:
                    body = minimal(
                        self.client.get_json(PATH.format(number), self.cache.query(start))
                    )
                except BudgetExhausted:
                    self.stopped_by = "budget"
                    break
                except (HttpError, ValueError) as exc:  # ValueError: a body that is not JSON
                    self.stopped_by = "http_error"
                    self.error_status = getattr(exc, "status", None) or 0
                    break
                self.cache.put(number, start, body)
                self.stats["pages_fetched"] += 1
            if body is None:
                return "not_found", items
            raw = body.get("items")
            page = raw if isinstance(raw, list) else []
            items.extend(item for item in page if isinstance(item, dict))
            start += len(page)
            total = body.get("total_results")
            if not page or not isinstance(total, int) or start >= total:
                self.stats["lists_shorter_than_total"] += isinstance(total, int) and start < total
                return "complete", items
        return ("partial" if start else "not_reached"), items


class OfficerWriter(records.Writer):
    """One record per officer id, one `Directorship` per appointment, shared addresses."""

    def __init__(self, known_addresses: set[str], stats: Counter[str]) -> None:
        super().__init__(None)
        self.stats, self.known_addresses = stats, known_addresses
        self.officers: dict[str, tuple[str, dict[str, list[Any]], dict[str, Any]]] = {}
        self.links: dict[str, dict[str, Any]] = {}
        self.roles: Counter[str] = Counter()

    def service_address(self, address: Mapping[str, Any]) -> str | None:
        """The `Address` id of a service address (never its care-of line), else None."""
        part = {name: _str(address.get(name)) for name in psc.ADDRESS}
        if premises := _str(address.get("premises")):
            part["address_line_1"] = f"{premises} {part['address_line_1'] or ''}"
        found = self.add_address([bulk.address_part(part[n]) for n in psc.ADDRESS], None)
        self.stats["officers_without_address_key"] += found is None
        return None if found is None else found[1]

    def person(self, item: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
        stats, name = self.stats, bulk.text(_str(item.get("name")))
        split = split_ch_name(name) if name else None
        stats["names_not_split"] += split is None
        demonyms = (_str(item.get("nationality")) or "").split(",")
        nationality = [country_code(d) for d in demonyms if d.strip()]
        stats["nationalities_unmapped"] += nationality.count(None)
        residence = bulk.text(_str(item.get("country_of_residence")))
        country = country_code(residence)
        stats["residence_unmapped"] += residence is not None and country is None
        values = {
            "name": name,
            "firstName": split[0] if split else None,
            "lastName": split[1] if split else None,
            "birthDate": psc.birth_month(item.get("date_of_birth")),  # never the day
            "nationality": nationality,
            "country": country,
        }
        nr: dict[str, Any] = {}
        number = _str(item.get("person_number"))
        if number:  # unchanged; rule D3 (the resolver) uses its first 8 characters
            nr["ch_person_number"] = number
            stats["person_numbers"] += 1
            stats["person_numbers_not_12_digits"] += not (len(number) == 12 and number.isdigit())
        if address := self.service_address(_dict(item.get("address"))):
            values["addressEntity"] = address
            nr["address_roles"] = {address: "service"}
        return values, nr

    def corporate(self, item: Mapping[str, Any]) -> tuple[str, dict[str, Any]]:
        """`Company` with a registration number, else `LegalEntity` (M2.3b rule 5)."""
        ident = {k: v for k, v in _dict(item.get("identification")).items() if isinstance(v, str)}
        raw = bulk.text(ident.get("registration_number"))
        values: dict[str, Any] = {
            "name": bulk.text(_str(item.get("name"))),
            "legalForm": bulk.text(ident.get("legal_form")),
        }
        if is_uk(ident, _str(_dict(item.get("address")).get("country"))):
            number, values["jurisdiction"] = uk_number(raw), "gb"
            self.stats["corporate_uk_numbers_invalid"] += raw is not None and number is None
        else:
            number, values["jurisdiction"] = raw, country_code(ident.get("country_registered"))
        if raw:
            values["registrationNumber"] = number
        return ("Company" if raw else "LegalEntity"), values

    def appointment(self, number: str, item: Mapping[str, Any]) -> None:
        stats = self.stats
        native, role = officer_id(dict(item)), bulk.text(_str(item.get("officer_role")))
        if native is None or role is None:
            stats["appointments_without_officer_id" if native is None else
                  "appointments_without_role"] += 1  # fmt: skip
            return
        if bulk.text(_str(item.get("name"))) is None:
            stats["officers_without_name"] += 1  # FtM needs a name (R3): no record, no link
            return
        rid = make_id(records.PREFIX, "off", native)
        if role.startswith("corporate-"):
            schema, values = self.corporate(item)
            nr: dict[str, Any] = {}
        else:
            schema = "Person"
            values, nr = self.person(item)
        self._merge(rid, schema, native, values, nr)
        appointed = _str(item.get("appointed_on"))
        link = edge_id("Directorship", native, number, role, appointed or "")
        if link in self.links:
            stats["appointments_duplicate"] += 1
            return
        self.roles[psc.vocabulary(role)] += 1
        link_values = {
            "director": rid,
            "organization": make_id(records.PREFIX, "co", number),
            "role": role,
            "startDate": appointed,
            "endDate": _str(item.get("resigned_on")),
        }
        link_nr: dict[str, Any] = {"v": records.NR_VERSION, "is_nominee": role.startswith(NOMINEE)}
        if appointment := _str(item.get("appointment_id")):
            link_nr["source_ref"] = appointment
        entity = self._entity("Directorship", link, link_values)
        self.links[link] = {**entity.to_dict(), "nr": link_nr}

    def _merge(
        self, rid: str, schema: str, native: str, values: dict[str, Any], nr: dict[str, Any]
    ) -> None:
        """One record per officer id: later appointments add values, never replace them."""
        if rid not in self.officers:
            self.officers[rid] = (schema, {}, {"v": records.NR_VERSION, "source_ref": native})
        known, merged, known_nr = self.officers[rid]
        if known != schema:
            self.stats["officer_schema_conflicts"] += 1
            return
        for prop, raw in values.items():
            for value in raw if isinstance(raw, list) else [raw]:
                if value and value not in merged.setdefault(prop, []):
                    merged[prop].append(value)
        if (pn := nr.get("ch_person_number")) and known_nr.setdefault("ch_person_number", pn) != pn:
            self.stats["person_number_conflicts"] += 1
        known_nr.setdefault("address_roles", {}).update(nr.get("address_roles", {}))

    def lines(self) -> list[dict[str, Any]]:
        out = []
        for rid in sorted(self.officers):
            schema, values, nr = self.officers[rid]
            nr = {k: v for k, v in nr.items() if v}
            out.append({**self._entity(schema, rid, values).to_dict(), "nr": nr})
        out.extend(self.links[link] for link in sorted(self.links))
        out.extend(self.addresses[key] for key in sorted(self.addresses))
        return out


def write_officers(
    key: str,
    block: OfficersBlock,
    slice_csv: Path,
    carried: Sequence[Path],
    out_dir: Path,
) -> tuple[dict[str, Any], str]:
    """The `officers` step: records and manifest in `out_dir`; counts and `stopped_by`.

    `carried` are this build's company (first) and PSC record files: officers are fetched
    only for slice companies with a `Company` record, and their addresses are linked, not
    written again.
    """
    network = NETWORK
    company_ids, address_ids = psc.written(carried[0])
    for path in carried[1:]:
        address_ids |= psc.written(path)[1]
    stats: Counter[str] = Counter(dict.fromkeys(COUNTED, 0))
    numbers = []
    for number, _, _ in slices.read(slice_csv):
        if make_id(records.PREFIX, "co", number) in company_ids:
            numbers.append(number)
        else:
            stats["slice_companies_without_record"] += 1
    began = network.monotonic()
    limiter = BudgetLimiter(REQUESTS_PER_SECOND, block.request_budget, network)
    status: Counter[str] = Counter(dict.fromkeys(COMPANY_STATUSES, 0))
    writer = OfficerWriter(address_ids, stats)
    with CompaniesHouseClient(
        key,
        transport=network.transport,
        limiter=limiter,
        sleep=network.sleep,
        clock=network.clock,
        hide_paths=True,
        follow_redirects=False,  # a redirect hop would pass the limiter and the budget
    ) as client:
        fetcher = Fetcher(client, Cache(block.cache_days, block.active_only, network, stats), stats)
        for number in numbers:
            found, items = fetcher.company(number)
            status[found] += 1
            for item in items:
                writer.appointment(number, item)
    path = out_dir / RECORD_FILE
    lines = writer.lines()
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.writelines(json.dumps(line, ensure_ascii=False) + "\n" for line in lines)
    producer = Producer(name="neonradar_ingest.sources.companies_house", version=__version__)
    source = Source(
        urls=[f"{BASE_URL}{PATH.format('{company_number}')}"],
        source_version=datetime.now(UTC).date().isoformat(),  # the API has no version: the date
    )
    write_manifest(path, dataset=bulk.DATASET, producer=producer, source=source)
    counts: dict[str, Any] = {
        "request_budget": block.request_budget,
        "requests": client.requests,
        "retries": client.retried,
        "rate_limit_waits": len(client.log.rate_limit_waits),
        "http_error_status": fetcher.error_status,
        "seconds": round(network.monotonic() - began, 1),
        "slice_companies": len(numbers),
        "companies": dict(status),
        "records": dict(sorted(Counter(line["schema"].lower() for line in lines).items())),
        "roles_by_value": dict(sorted(writer.roles.items())),
        **dict(sorted(stats.items())),
    }
    return counts, fetcher.stopped_by
