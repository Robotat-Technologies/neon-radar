"""Companies House REST resources to C1 records (PHASE-1.md M1.8a step 5, contracts/C1-record.md).

`Mapper` takes the company profile, officer items and PSC items as the API returns them and
collects FtM `ValueEntity` records keyed by id, plus the counts the spike report needs. It
never maps `identity_verification_details` (Phase 2 decides); it only counts the fields seen.
"""

import hashlib
import html
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any

from followthemoney import ValueEntity, model

from neonradar_contracts.records import make_id

DATASET = "gb_companies_house"
PREFIX = "gbch"
NR_VERSION = "1.0"

# Companies House `jurisdiction` values that mean the United Kingdom (M1.8a step 5).
UK_JURISDICTIONS = frozenset(
    {"england-wales", "wales", "scotland", "northern-ireland", "united-kingdom", "england"}
)
# Corporate officer identification types that name a registered company; others are LegalEntity.
COMPANY_ID_TYPES = frozenset(
    {
        "uk-limited-company",
        "eea",
        "non-eea",
        "registered-overseas-entity-corporate-managing-officer",
    }
)
PSC_PERSON = frozenset(
    {"individual-person-with-significant-control", "individual-beneficial-owner"}
)
PSC_COMPANY = frozenset(
    {"corporate-entity-person-with-significant-control", "corporate-entity-beneficial-owner"}
)
# The API documentation spells the legal-person kind two ways; accept both (research note A2).
PSC_LEGAL = frozenset(
    {
        "legal-person-person-with-significant-control",
        "legal-person-with-significant-control",
        "legal-person-beneficial-owner",
    }
)
PSC_SUPER_SECURE = frozenset(
    {"super-secure-person-with-significant-control", "super-secure-beneficial-owner"}
)
BAND_RE = re.compile(r"(\d{2,3})-to-(\d{2,3})-percent")
MORE_THAN_RE = re.compile(r"more-than-(\d{2})-percent")
OWNERSHIP_PREFIXES = (
    "ownership-of-shares",
    "right-to-share-surplus-assets",
    "part-right-to-share-surplus-assets",
)
CONTROL_PREFIXES = (
    ("voting-rights", "voting"),
    ("right-to-appoint-and-remove", "appointment"),
    ("significant-influence-or-control", "influence"),
)
# Registered office fields in the order they make up `Address.full`. `care_of` is left out: it
# can name a person.
ADDRESS_PARTS = (
    "po_box",
    "premises",
    "address_line_1",
    "address_line_2",
    "locality",
    "region",
    "postal_code",
    "country",
)
# A natural officer's name in the officers list: "SURNAME, Forenames[, Title]" (research note A6).
SURNAME_FIRST_RE = re.compile(r"^[^a-z,]*[A-Z][^a-z,]*, \S")


@dataclass
class MappingStats:
    """Counts for the spike report: no names, no values, only field names and numbers."""

    appointments: int = 0
    corporate_appointments: int = 0
    natural_appointments: int = 0
    surname_first_names: int = 0
    psc_kinds: Counter[str] = field(default_factory=Counter)
    natures: Counter[str] = field(default_factory=Counter)
    skipped: Counter[str] = field(default_factory=Counter)
    dropped: Counter[str] = field(default_factory=Counter)
    identity_verification: Counter[str] = field(default_factory=Counter)
    unmapped_fields: Counter[str] = field(default_factory=Counter)


def normalise_company_number(raw: str) -> str:
    """Upper case, no spaces, all-digit numbers left-padded to 8 (`617987` -> `00617987`)."""
    number = raw.strip().upper().replace(" ", "")
    return number.zfill(8) if number.isdigit() else number


def company_id(number: str) -> str:
    return make_id(PREFIX, "co", number)


def _digest(*parts: str) -> str:
    joined = "|".join(parts).encode("utf-8")
    return hashlib.sha1(joined, usedforsecurity=False).hexdigest()[:20]


def edge_id(schema: str, *parts: str) -> str:
    """`<prefix>-<schema in lower case>-<first 20 hex of SHA-1 of the parts>` (PHASE-1.md 4.4)."""
    return f"{PREFIX}-{schema.lower()}-{_digest(*parts)}"


def officer_id(item: dict[str, Any]) -> str | None:
    """The officer id from `links.officer.appointments` (`/officers/{officer_id}/appointments`)."""
    link = _obj(_obj(item, "links"), "officer").get("appointments")
    parts = str(link or "").strip("/").split("/")
    return parts[1] if len(parts) >= 3 and parts[0] == "officers" and parts[1] else None


def last_segment(link: Any) -> str | None:
    """The last path segment of a `links.self` value, for example a PSC or appointment id."""
    segment = str(link or "").rstrip("/").rsplit("/", 1)[-1]
    return segment or None


def birth_month(dob: Any) -> str | None:
    """`{month, year}` to `YYYY-MM` (or `YYYY`); the register never shows the day."""
    if not isinstance(dob, dict) or not isinstance(dob.get("year"), int):
        return None
    month = dob.get("month")
    return f"{dob['year']:04d}-{month:02d}" if isinstance(month, int) else f"{dob['year']:04d}"


def share_band(nature: str) -> tuple[float, float] | None:
    """`...-25-to-50-percent...` to (25, 50); `...-more-than-25-percent...` to (25, 100)."""
    if band := BAND_RE.search(nature):
        return float(band[1]), float(band[2])
    if more := MORE_THAN_RE.search(nature):
        return float(more[1]), 100.0
    return None


def classify_nature(nature: str) -> tuple[str, str | None]:
    """`("ownership", None)`, `("control", controlType)` or `("unmapped", None)`."""
    if nature.startswith(OWNERSHIP_PREFIXES) and share_band(nature) is not None:
        return "ownership", None
    for prefix, control_type in CONTROL_PREFIXES:
        if nature.startswith(prefix):
            return "control", control_type
    return "unmapped", None


def _obj(item: dict[str, Any], key: str) -> dict[str, Any]:
    value = item.get(key)
    return value if isinstance(value, dict) else {}


def _text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFC", html.unescape(value)).strip()
    return text or None


def _segments(value: Any) -> Iterator[str]:
    """Free-text lists such as `British,Irish` split into their parts."""
    text = _text(value)
    if text:
        yield from (part.strip() for part in text.split(",") if part.strip())


class Mapper:
    """Collects the C1 records of one company: profile, officers and PSCs."""

    def __init__(self) -> None:
        self.entities: dict[str, ValueEntity] = {}
        self.nr: dict[str, dict[str, Any]] = {}
        self.stats = MappingStats()
        self._seen: set[str] = set()  # appointments and PSCs already mapped (pages can overlap)

    def records(self) -> list[dict[str, Any]]:
        """Every record as a C1 dict, sorted by id."""
        return [
            {**self.entities[rid].to_dict(), "nr": self.nr[rid]} for rid in sorted(self.entities)
        ]

    def _entity(self, schema: str, rid: str, **nr: Any) -> ValueEntity:
        entity = self.entities.get(rid)
        if entity is None:
            entity = ValueEntity(model[schema], {"id": rid, "datasets": [DATASET]})
            self.entities[rid] = entity
            self.nr[rid] = {"v": NR_VERSION}
        self.nr[rid].update({key: value for key, value in nr.items() if value is not None})
        return entity

    def _put(self, entity: ValueEntity, prop: str, values: Any) -> None:
        """Add cleaned values; count the ones FtM cannot parse under `dropped`."""
        items = values if isinstance(values, list | tuple) else [values]
        for raw in items:
            text = _text(raw)
            if text is None:
                continue
            cleaned = entity.schema.properties[prop].type.clean(text)
            if cleaned is None:
                self.stats.dropped[f"{entity.schema.name}.{prop}"] += 1
            else:
                entity.add(prop, cleaned, cleaned=True)

    def _count_identity_verification(self, where: str, item: dict[str, Any]) -> None:
        details = item.get("identity_verification_details")
        if isinstance(details, dict):
            self.stats.identity_verification[f"{where}.identity_verification_details"] += 1
            for key in sorted(details):
                self.stats.identity_verification[f"{where}.{key}"] += 1

    def add_company(self, profile: dict[str, Any], number: str | None = None) -> str:
        """The company profile to a `Company` and its registered office to an `Address`.

        `number` is the number that was asked for, used if the profile has none.
        """
        raw = profile.get("company_number") or number
        if not raw:
            raise ValueError("the company profile has no company_number")
        number = normalise_company_number(str(raw))
        rid = company_id(number)
        company = self._entity("Company", rid, source_ref=number)
        self._put(company, "name", profile.get("company_name"))
        self._put(company, "registrationNumber", number)
        jurisdiction = profile.get("jurisdiction")
        if jurisdiction in UK_JURISDICTIONS:
            company.add("jurisdiction", "gb")
        elif jurisdiction:
            self.stats.unmapped_fields[f"company.jurisdiction={jurisdiction}"] += 1
        self._put(company, "status", profile.get("company_status"))
        self._put(company, "legalForm", profile.get("type"))
        self._put(company, "incorporationDate", profile.get("date_of_creation"))
        self._put(company, "dissolutionDate", profile.get("date_of_cessation"))
        for previous in profile.get("previous_company_names") or []:
            if isinstance(previous, dict):
                self._put(company, "previousName", previous.get("name"))
        address = self._address(profile.get("registered_office_address"))
        if address is not None:
            company.add("addressEntity", address)
            self.nr[rid].setdefault("address_roles", {})[address] = "registered"
        return rid

    def _address(self, raw: Any) -> str | None:
        """A registered office to an `Address` whose id hashes the full text, so equal
        addresses share one record."""
        if not isinstance(raw, dict):
            return None
        values = {key: _text(raw.get(key)) for key in ADDRESS_PARTS}
        full = ", ".join(value for value in values.values() if value)
        if not full:
            return None
        rid = f"{PREFIX}-addr-{_digest(full)}"
        address = self._entity("Address", rid)
        self._put(address, "full", full)
        street = " ".join(v for v in (values["premises"], values["address_line_1"]) if v)
        self._put(address, "street", street)
        self._put(address, "street2", values["address_line_2"])
        self._put(address, "city", values["locality"])
        self._put(address, "region", values["region"])
        self._put(address, "postalCode", values["postal_code"])
        self._put(address, "postOfficeBox", values["po_box"])
        self._put(address, "country", values["country"])
        return rid

    def add_officer(self, item: dict[str, Any], company: str, number: str) -> None:
        """One officers-list item to a Person, Company or LegalEntity plus a `Directorship`."""
        native = officer_id(item)
        role = _text(item.get("officer_role")) or ""
        if native is None or not role:
            self.stats.skipped["officer-without-id-or-role"] += 1
            return
        appointment = last_segment(_obj(item, "links").get("self")) or native
        link_id = edge_id("Directorship", number, appointment, role)
        if link_id in self._seen:
            return  # the same appointment on two overlapping pages: count and map it once
        self._seen.add(link_id)
        self.stats.appointments += 1
        self._count_identity_verification("officers", item)
        for key in ("person_number", "address", "occupation", "former_names", "appointed_before"):
            if item.get(key):
                self.stats.unmapped_fields[f"officers.{key}"] += 1
        rid = make_id(PREFIX, "off", native)
        if role.startswith("corporate-"):
            self.stats.corporate_appointments += 1
            ident = _obj(item, "identification")
            registered = ident.get("identification_type") in COMPANY_ID_TYPES
            officer = self._entity(
                "Company" if registered else "LegalEntity", rid, source_ref=native
            )
            self._put(officer, "name", item.get("name"))
            self._put(officer, "registrationNumber", ident.get("registration_number"))
            self._put(officer, "legalForm", ident.get("legal_form"))
        else:
            self.stats.natural_appointments += 1
            name = _text(item.get("name")) or ""
            if SURNAME_FIRST_RE.match(name):
                self.stats.surname_first_names += 1
            officer = self._entity("Person", rid, source_ref=native)
            self._put(officer, "name", name)
            self._put(officer, "birthDate", birth_month(item.get("date_of_birth")))
            self._put(officer, "nationality", list(_segments(item.get("nationality"))))
            self._put(officer, "country", list(_segments(item.get("country_of_residence"))))
        link = self._entity(
            "Directorship", link_id, source_ref=appointment, is_nominee="nominee-" in role
        )
        link.add("director", rid)
        link.add("organization", company)
        self._put(link, "role", role)
        self._put(link, "startDate", item.get("appointed_on"))
        self._put(link, "endDate", item.get("resigned_on"))

    def add_psc(self, item: dict[str, Any], company: str, number: str) -> None:
        """One PSC item to a Person, Company or LegalEntity, plus one `Ownership` or `Control`
        per nature of control. Super-secure and unknown kinds are skipped and counted."""
        kind = str(item.get("kind") or "unknown")
        native = last_segment(_obj(item, "links").get("self"))
        if native is not None:
            if f"psc|{native}" in self._seen:
                return  # the same PSC on two overlapping pages: count and map it once
            self._seen.add(f"psc|{native}")
        self.stats.psc_kinds[kind] += 1
        self._count_identity_verification("psc", item)
        if kind in PSC_SUPER_SECURE or kind not in PSC_PERSON | PSC_COMPANY | PSC_LEGAL:
            self.stats.skipped[f"psc:{kind}"] += 1
            return
        if native is None:
            self.stats.skipped["psc-without-id"] += 1
            return
        for key in ("address", "is_sanctioned", "principal_office_address"):
            if key in item:
                self.stats.unmapped_fields[f"psc.{key}"] += 1
        rid = make_id(PREFIX, "psc", native)
        if kind in PSC_PERSON:
            psc = self._entity("Person", rid, source_ref=native)
            elements = _obj(item, "name_elements")
            self._put(psc, "firstName", elements.get("forename"))
            self._put(psc, "middleName", elements.get("middle_name"))
            self._put(psc, "lastName", elements.get("surname"))
            self._put(psc, "title", elements.get("title"))
            self._put(psc, "birthDate", birth_month(item.get("date_of_birth")))
            self._put(psc, "nationality", list(_segments(item.get("nationality"))))
            self._put(psc, "country", list(_segments(item.get("country_of_residence"))))
        else:
            schema = "Company" if kind in PSC_COMPANY else "LegalEntity"
            psc = self._entity(schema, rid, source_ref=native)
            ident = _obj(item, "identification")
            self._put(psc, "registrationNumber", ident.get("registration_number"))
            self._put(psc, "legalForm", ident.get("legal_form"))
            self._put(psc, "jurisdiction", ident.get("country_registered"))
        self._put(psc, "name", item.get("name"))
        for nature in _natures(item.get("natures_of_control")):
            self._add_nature(nature, rid, company, number, native, item)

    def _add_nature(
        self, nature: str, psc: str, company: str, number: str, native: str, item: dict[str, Any]
    ) -> None:
        kind, control_type = classify_nature(nature)
        self.stats.natures[kind if control_type is None else f"control:{control_type}"] += 1
        if kind == "unmapped":
            self.stats.skipped[f"nature:{nature}"] += 1
            return
        rid = edge_id("Ownership" if kind == "ownership" else "Control", number, native, nature)
        if kind == "ownership":
            low, high = share_band(nature) or (0.0, 100.0)
            link = self._entity(
                "Ownership", rid, natures_of_control=[nature], share_pct_min=low, share_pct_max=high
            )
            link.add("owner", psc)
            link.add("asset", company)
            link.add("percentage", f"{low:g}-{high:g}")
        else:
            link = self._entity("Control", rid, natures_of_control=[nature])
            link.add("controller", psc)
            link.add("controlled", company)
            link.add("controlType", control_type)
        self._put(link, "role", nature)
        self._put(link, "startDate", item.get("notified_on"))
        self._put(link, "endDate", item.get("ceased_on"))


def _natures(values: Any) -> Iterable[str]:
    if isinstance(values, list):
        yield from (text for value in values if (text := _text(value)))
