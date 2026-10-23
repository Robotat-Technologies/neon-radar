"""C1 record builders for generator v1 (PHASE-3.md 7.2.2).

Every builder returns one C1 record as a plain dict in `ValueEntity.to_dict()` shape: dataset
`nr_synthetic`, `nr.v` "1.1", `nr.synthetic` true and the `synthetic_kind` the record needs
(`registry` for companies, people, addresses and their links; `activity` for accounts, account
holdings and payments). Nothing here carries a label (C1 R9): roles in a scenario live only in the
label files.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

CHANNELS = ("wire", "card", "cash_deposit", "cash_withdrawal", "internal")
ADDRESS_ROLES = ("registered", "service", "residential", "business", "unknown")

Record = dict[str, Any]


def hashed_id(namespace: str, seed: int, key: str) -> str:
    """`syn-ov-<namespace>-<16 hex>`: an id that says nothing about the record's role."""
    digest = hashlib.sha256(f"{seed}|{namespace}|{key}".encode()).hexdigest()[:16]
    return f"syn-ov-{namespace}-{digest}"


def _nr(kind: str, **extra: Any) -> dict[str, Any]:
    return {"v": "1.1", "synthetic": True, "synthetic_kind": kind, **extra}


LIST_TOPICS = frozenset({"sanction", "role.pep", "role.rca"})


def _kind(topics: list[str] | None) -> str:
    """`list` for a synthetic list entry (a record with a flag topic), else `registry`."""
    return "list" if LIST_TOPICS & set(topics or []) else "registry"


def _record(rid: str, schema: str, props: dict[str, list[str]], nr: dict[str, Any]) -> Record:
    clean = {k: v for k, v in props.items() if v}
    return {
        "id": rid,
        "schema": schema,
        "datasets": ["nr_synthetic"],
        "properties": clean,
        "nr": nr,
    }


def money(amount: float | Decimal) -> str:
    """A C1 amount: a decimal string with two decimals, greater than zero (R7)."""
    value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if value <= 0:
        raise ValueError("payment amounts must be greater than zero")
    return f"{value:.2f}"


def ts(moment: datetime) -> str:
    """A C1 payment date: UTC, `YYYY-MM-DDTHH:MM:SS`, no offset (R5)."""
    offset = moment.utcoffset()
    if offset is not None and offset.total_seconds() != 0:
        raise ValueError("payment times must be UTC")
    return moment.strftime("%Y-%m-%dT%H:%M:%S")


def company(
    rid: str,
    name: str,
    *,
    jurisdiction: str,
    registration_number: str,
    incorporation_date: str,
    addresses: dict[str, str] | None = None,
    sector: str = "",
    status: str = "active",
    dissolution_date: str = "",
    topics: list[str] | None = None,
) -> Record:
    roles = addresses or {}
    props = {
        "name": [name],
        "jurisdiction": [jurisdiction],
        "registrationNumber": [registration_number],
        "incorporationDate": [incorporation_date],
        "dissolutionDate": [dissolution_date] if dissolution_date else [],
        "status": [status] if status else [],
        "sector": [sector] if sector else [],
        "addressEntity": sorted(roles),
        "topics": sorted(topics or []),
    }
    extra = {"address_roles": dict(sorted(roles.items()))} if roles else {}
    return _record(rid, "Company", props, _nr(_kind(topics), **extra))


def organization(rid: str, name: str, *, country: str, topics: list[str] | None = None) -> Record:
    props = {"name": [name], "country": [country], "topics": sorted(topics or [])}
    return _record(rid, "Organization", props, _nr(_kind(topics)))


def person(
    rid: str,
    names: list[str],
    *,
    birth_date: str,
    nationality: str,
    gender: str = "",
    addresses: dict[str, str] | None = None,
    topics: list[str] | None = None,
) -> Record:
    roles = addresses or {}
    props = {
        "name": names,
        "birthDate": [birth_date],
        "nationality": [nationality],
        "gender": [gender] if gender else [],
        "addressEntity": sorted(roles),
        "topics": sorted(topics or []),
    }
    extra = {"address_roles": dict(sorted(roles.items()))} if roles else {}
    return _record(rid, "Person", props, _nr(_kind(topics), **extra))


def address(rid: str, full: str, *, city: str, postal_code: str, country: str) -> Record:
    props = {"full": [full], "city": [city], "postalCode": [postal_code], "country": [country]}
    return _record(rid, "Address", props, _nr("registry"))


def account(
    rid: str,
    number: str,
    *,
    bank_name: str,
    currency: str,
    opening_date: str,
    kind: str = "customer",
) -> Record:
    if not (number.startswith("NRSYN") and len(number) == 15 and number[5:].isdigit()):
        raise ValueError("synthetic account numbers are NRSYN plus 10 digits (R8)")
    if kind not in ("customer", "cash_ledger"):
        raise ValueError("account_kind is customer or cash_ledger")
    props = {
        "accountNumber": [number],
        "bankName": [bank_name],
        "currency": [currency],
        "openingDate": [opening_date],
    }
    return _record(rid, "BankAccount", props, _nr("activity", account_kind=kind))


def holding(rid: str, owner: str, account_id: str) -> Record:
    props = {"owner": [owner], "asset": [account_id], "role": ["account holder"]}
    return _record(rid, "Ownership", props, _nr("activity"))


BANDS: dict[str, tuple[float, float, bool, bool, str]] = {
    # band: (min, max, min exclusive, max exclusive, Companies House nature of control)
    "25-50": (25.0, 50.0, True, False, "ownership-of-shares-25-to-50-percent"),
    "50-75": (50.0, 75.0, True, True, "ownership-of-shares-50-to-75-percent"),
    "75-100": (75.0, 100.0, False, False, "ownership-of-shares-75-to-100-percent"),
}


def ownership(
    rid: str, owner: str, asset: str, *, band: str, start_date: str = "", nominee: bool = False
) -> Record:
    """`band` is a Companies House band ("25-50", "50-75", "75-100") or an exact share such as
    "exact:12.5" (a registered shareholding outside the PSC bands, for synthetic look-alikes)."""
    if band.startswith("exact:"):
        value = float(band.split(":", 1)[1])
        if not 0 < value <= 100:
            raise ValueError("an exact share lies in (0, 100]")
        props = {
            "owner": [owner],
            "asset": [asset],
            "percentage": [f"{value:g}"],
            "role": ["shareholder"],
            "startDate": [start_date] if start_date else [],
        }
        nr_extra: dict[str, Any] = {"share_pct_min": value, "share_pct_max": value}
        if nominee:
            nr_extra["is_nominee"] = True
        return _record(rid, "Ownership", props, _nr("registry", **nr_extra))
    low, high, low_x, high_x, nature = BANDS[band]
    props = {
        "owner": [owner],
        "asset": [asset],
        "percentage": [band],
        "role": [nature],
        "startDate": [start_date] if start_date else [],
    }
    extra: dict[str, Any] = {
        "natures_of_control": [nature],
        "share_pct_min": low,
        "share_pct_max": high,
    }
    if low_x:
        extra["share_pct_min_exclusive"] = True
    if high_x:
        extra["share_pct_max_exclusive"] = True
    if nominee:
        extra["is_nominee"] = True
    return _record(rid, "Ownership", props, _nr("registry", **extra))


def directorship(
    rid: str,
    director: str,
    organization_id: str,
    *,
    role: str = "director",
    start_date: str,
    end_date: str = "",
    nominee: bool = False,
) -> Record:
    props = {
        "director": [director],
        "organization": [organization_id],
        "role": [role],
        "startDate": [start_date],
        "endDate": [end_date] if end_date else [],
    }
    extra = {"is_nominee": True} if nominee else {}
    return _record(rid, "Directorship", props, _nr("registry", **extra))


def representation(rid: str, agent: str, client: str, *, role: str = "formation agent") -> Record:
    props = {"agent": [agent], "client": [client], "role": [role]}
    return _record(rid, "Representation", props, _nr("registry"))


def family(rid: str, person_id: str, relative: str, *, relationship: str) -> Record:
    props = {"person": [person_id], "relative": [relative], "relationship": [relationship]}
    return _record(rid, "Family", props, _nr("registry"))


def associate(rid: str, person_id: str, other: str, *, relationship: str) -> Record:
    props = {"person": [person_id], "associate": [other], "relationship": [relationship]}
    return _record(rid, "Associate", props, _nr("registry"))


def sanction(rid: str, entity: str, *, authority: str, program: str, start_date: str) -> Record:
    props = {
        "entity": [entity],
        "authority": [authority],
        "program": [program],
        "startDate": [start_date],
        "provisions": ["Asset freeze"],
    }
    return _record(rid, "Sanction", props, _nr("list"))


def control(
    rid: str, controller: str, controlled: str, *, control_type: str, band: str = ""
) -> Record:
    """A PSC `Control`: `control_type` voting, appointment or influence (C2 `control_type`); a
    voting band carries the four share keys as on `Ownership` (PHASE-2.md 4.5)."""
    if control_type not in ("voting", "appointment", "influence"):
        raise ValueError(f"unknown control type {control_type}")
    if (control_type == "voting") != bool(band):
        raise ValueError("a voting control needs a band, and only a voting control has one")
    nature = {
        "appointment": "right-to-appoint-and-remove-directors",
        "influence": "significant-influence-or-control",
    }.get(control_type, f"voting-rights-{band.replace('-', '-to-')}-percent")
    props = {
        "controller": [controller],
        "controlled": [controlled],
        "controlType": [control_type],
        "role": [nature],
    }
    extra: dict[str, Any] = {"natures_of_control": [nature]}
    if band:
        low, high, low_x, high_x, _ = BANDS[band]
        extra.update(share_pct_min=low, share_pct_max=high)
        if low_x:
            extra["share_pct_min_exclusive"] = True
        if high_x:
            extra["share_pct_max_exclusive"] = True
    return _record(rid, "Control", props, _nr("registry", **extra))


def consolidation(rid: str, parent: str, child: str, *, level: str = "direct") -> Record:
    """A GLEIF-style accounting consolidation (C2 `CONSOLIDATES`)."""
    props = {"owner": [parent], "asset": [child], "role": ["consolidation"]}
    return _record(rid, "Ownership", props, _nr("registry", consolidation=level))


def position(rid: str, name: str, *, country: str) -> Record:
    return _record(rid, "Position", {"name": [name], "country": [country]}, _nr("registry"))


def occupancy(rid: str, holder: str, post: str, *, start_date: str, end_date: str = "") -> Record:
    props = {
        "holder": [holder],
        "post": [post],
        "startDate": [start_date],
        "endDate": [end_date] if end_date else [],
        "status": ["current" if not end_date else "ended"],
    }
    return _record(rid, "Occupancy", props, _nr("registry"))


def payment(
    rid: str,
    *,
    payer: str,
    beneficiary: str,
    payer_account: str,
    beneficiary_account: str,
    amount: float | Decimal,
    currency: str,
    moment: datetime,
    channel: str,
    purpose: str = "",
) -> Record:
    if channel not in CHANNELS:
        raise ValueError(f"unknown channel {channel}")
    if payer_account == beneficiary_account:
        raise ValueError("a payment needs two different accounts")
    props = {
        "payer": [payer],
        "beneficiary": [beneficiary],
        "payerAccount": [payer_account],
        "beneficiaryAccount": [beneficiary_account],
        "amount": [money(amount)],
        "currency": [currency],
        "date": [ts(moment)],
        "purpose": [purpose] if purpose else [],
    }
    return _record(rid, "Payment", props, _nr("activity", channel=channel))
