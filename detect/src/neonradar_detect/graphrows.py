"""C1 records to a MemGraph with the C2 1.2.0 labels, types and properties (PHASE-3.md 7.1.2).

The oracle's own reading of C2 (PHASE-1.md 5.2 and the 1.1.0 and 1.2.0 changes), limited to the
labels, types and properties the detectors read (the table in 7.1.2). It does not call the
graph package's mapping, so that the oracle is an independent implementation: the loader's
mapping and this one are compared by every detector test in Neo4j mode, which loads the same
records with the project's loader, and by the world parity test (7.1.5). `test_graphrows.py` pins
the result. Records are taken as they are, one node per record: the oracle does no entity
resolution, so it is for synthetic data, where resolution is off.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from neonradar_detect.memgraph import MemGraph

LABELS = {
    "Person": ["Entity", "LegalEntity", "Person"],
    "Company": ["Entity", "LegalEntity", "Organization", "Company"],
    "Organization": ["Entity", "LegalEntity", "Organization"],
    "LegalEntity": ["Entity", "LegalEntity"],
    "Address": ["Entity", "Address"],
    "BankAccount": ["Entity", "Account"],
    "Position": ["Entity", "Position"],
}
FLAGS = {"sanction": "Sanctioned", "role.pep": "PEP", "role.rca": "RCA"}


def _one(props: dict[str, list[str]], key: str) -> str | None:
    vals = props.get(key) or []
    return vals[0] if vals else None


def from_records(records: list[dict[str, Any]]) -> MemGraph:
    g = MemGraph()
    by_id = {r["id"]: r for r in records}
    for r in sorted(records, key=lambda r: r["id"]):
        schema = r["schema"]
        if schema not in LABELS and schema != "Sanction":
            continue
        p = r["properties"]
        nr = r.get("nr") or {}
        synthetic = bool(nr.get("synthetic", False))
        topics = sorted(p.get("topics", []))
        if schema == "Sanction":
            g.add_node(
                r["id"],
                ["Sanction"],
                {
                    k: v
                    for k, v in {
                        "authority": _one(p, "authority"),
                        "program": _one(p, "program"),
                        "provisions": p.get("provisions") or None,
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                        "listing_date": _one(p, "listingDate"),
                        "datasets": r["datasets"],
                        "synthetic": synthetic,
                        "caption": _one(p, "authority") or r["id"],
                    }.items()
                    if v is not None
                },
            )
            continue
        labels = list(LABELS[schema])
        labels += [FLAGS[t] for t in topics if t in FLAGS]
        if synthetic:
            labels.append("Synthetic")
        names = p.get("name", []) or p.get("full", [])
        props: dict[str, Any] = {
            "schema": schema,
            "caption": (names[0] if names else (_one(p, "accountNumber") or r["id"])),
            "names": names,
            "topics": topics,
            "datasets": r["datasets"],
            "synthetic": synthetic,
            "referents": [r["id"]],
        }
        if schema == "BankAccount":
            props.update(
                account_number=_one(p, "accountNumber"),
                bank_name=_one(p, "bankName"),
                currency=_one(p, "currency"),
                opening_date=_one(p, "openingDate"),
                account_kind=nr.get("account_kind"),
            )
            props["caption"] = props["account_number"]
        if schema in ("Company", "Organization", "LegalEntity"):
            props.update(
                jurisdiction=_one(p, "jurisdiction"),
                registration_number=_one(p, "registrationNumber"),
                incorporation_date=_one(p, "incorporationDate"),
                dissolution_date=_one(p, "dissolutionDate"),
                status=_one(p, "status"),
                sector=_one(p, "sector"),
                accounts_category=nr.get("accounts_category"),
                psc_statements=nr.get("psc_statements"),
            )
        if schema == "Person":
            props.update(birth_date=_one(p, "birthDate"), nationalities=p.get("nationality", []))
        if schema == "Address":
            props.update(
                full=_one(p, "full"),
                country=_one(p, "country"),
                postal_code=_one(p, "postalCode"),
                city=_one(p, "city"),
            )
        if schema == "Position":
            props.update(country=_one(p, "country"))
        props["countries"] = sorted(
            set(p.get("country", []) + p.get("jurisdiction", []) + p.get("nationality", []))
        )
        g.add_node(r["id"], labels, {k: v for k, v in props.items() if v is not None})
    for r in sorted(records, key=lambda r: r["id"]):
        p = r["properties"]
        nr = r.get("nr") or {}
        base = {"datasets": r["datasets"], "synthetic": bool(nr.get("synthetic", False))}
        s = r["schema"]
        if s in ("Company", "Organization", "Person", "LegalEntity"):
            roles = nr.get("address_roles", {})
            for addr in p.get("addressEntity", []):
                g.add_rel(
                    f"{r['id']}|addr|{addr}",
                    "HAS_ADDRESS",
                    r["id"],
                    addr,
                    {**base, "role": roles.get(addr, "unknown")},
                )
        elif s == "Sanction":
            entity = _one(p, "entity") or ""
            g.add_rel(f"{entity}|sanction|{r['id']}", "SUBJECT_OF", entity, r["id"], base)
        elif s == "Payment":
            amount = float(_one(p, "amount") or 0)
            moment = datetime.strptime(_one(p, "date") or "", "%Y-%m-%dT%H:%M:%S").replace(
                tzinfo=UTC
            )
            g.add_rel(
                r["id"],
                "PAID",
                _one(p, "payerAccount") or "",
                _one(p, "beneficiaryAccount") or "",
                {
                    **base,
                    "amount": amount,
                    "currency": _one(p, "currency"),
                    "ts": moment,
                    "channel": nr.get("channel"),
                    "purpose": _one(p, "purpose"),
                },
            )
        elif s == "Ownership":
            owner, asset = _one(p, "owner") or "", _one(p, "asset") or ""
            if by_id.get(asset, {}).get("schema") == "BankAccount":
                g.add_rel(r["id"], "HOLDS_ACCOUNT", owner, asset, {**base, "role": _one(p, "role")})
            elif nr.get("consolidation"):
                g.add_rel(
                    r["id"],
                    "CONSOLIDATES",
                    owner,
                    asset,
                    {
                        **base,
                        "level": nr["consolidation"],
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                    },
                )
            else:
                g.add_rel(
                    r["id"],
                    "OWNS",
                    owner,
                    asset,
                    {
                        **base,
                        "share_pct_min": nr.get("share_pct_min"),
                        "share_pct_max": nr.get("share_pct_max"),
                        "share_min_exclusive": bool(nr.get("share_pct_min_exclusive", False)),
                        "share_max_exclusive": bool(nr.get("share_pct_max_exclusive", False)),
                        "is_nominee": bool(nr.get("is_nominee", False)),
                        "start_date": _one(p, "startDate"),
                        "end_date": _one(p, "endDate"),
                    },
                )
        elif s == "Control":
            g.add_rel(
                r["id"],
                "CONTROLS",
                _one(p, "controller") or "",
                _one(p, "controlled") or "",
                {
                    **base,
                    "control_type": _one(p, "controlType"),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                    "share_pct_min": nr.get("share_pct_min"),
                    "share_pct_max": nr.get("share_pct_max"),
                    "share_min_exclusive": bool(nr.get("share_pct_min_exclusive", False)),
                    "share_max_exclusive": bool(nr.get("share_pct_max_exclusive", False)),
                },
            )
        elif s == "Directorship":
            g.add_rel(
                r["id"],
                "DIRECTOR_OF",
                _one(p, "director") or "",
                _one(p, "organization") or "",
                {
                    **base,
                    "role": _one(p, "role"),
                    "is_nominee": bool(nr.get("is_nominee", False)),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                },
            )
        elif s == "Representation":
            g.add_rel(
                r["id"],
                "REPRESENTS",
                _one(p, "agent") or "",
                _one(p, "client") or "",
                {**base, "role": _one(p, "role")},
            )
        elif s == "Family":
            g.add_rel(
                r["id"],
                "FAMILY_OF",
                _one(p, "person") or "",
                _one(p, "relative") or "",
                {**base, "relationship": _one(p, "relationship")},
            )
        elif s == "Occupancy":
            g.add_rel(
                r["id"],
                "HOLDS_POSITION",
                _one(p, "holder") or "",
                _one(p, "post") or "",
                {
                    **base,
                    "status": _one(p, "status"),
                    "start_date": _one(p, "startDate"),
                    "end_date": _one(p, "endDate"),
                },
            )
        elif s == "Associate":
            g.add_rel(
                r["id"],
                "ASSOCIATE_OF",
                _one(p, "person") or "",
                _one(p, "associate") or "",
                {**base, "relationship": _one(p, "relationship")},
            )
    return g
