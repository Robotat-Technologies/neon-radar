"""Synthetic join: accounts and background payments for entities that already exist (M1.8e).

PHASE-1.md M1.8e deliverable 3 and ADR-0005 (rule 2, guardrail G1). Given any C1 records, for
example spike output in `data/cache/spikes/`:

- Holders are live registry organisations only: `Company` or `Organization` records from
  `gb_companies_house` or `gleif_lei` (or synthetic `nr_synthetic` records), with no
  `dissolutionDate`, a status that is empty or in LIVE, and an incorporation date before
  LATEST_FOUNDED. Everything else gets nothing: people, bare `LegalEntity` and `PublicBody`
  records, every other dataset (ICIJ records are leak-derived), and any other status.
- Each holder only receives payments from new synthetic "customer" companies and only pays new
  synthetic "supplier" companies. Customers never receive and suppliers never pay, so no input
  entity pays another and no cycle runs through an input entity's account.
- One `round_trip` scenario runs only among four new synthetic companies. Their background uses
  the purposes and amounts of demo-mini's EUR background, with the same customers and
  suppliers, never with an input entity.
- New ids use the namespace `syn-<kind>-j<seed>-`. Account numbers come from a block reserved
  for the seed (far above demo-mini's), skipping every number in the input. A generated name
  equal to an input name is rejected.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from followthemoney import model

from neonradar_ingest.synth.activity import (
    EUR_BACKGROUND,
    EUR_PURPOSES,
    Pay,
    amount,
    number_payments,
    office,
    open_accounts,
    prune,
    round_trip,
    scenario_label,
)  # fmt: skip
from neonradar_ingest.synth.companies import CompanyNames, name_key
from neonradar_ingest.synth.emit import Rec, Scenario, ordered
from neonradar_ingest.synth.registry import Registry, sid
from neonradar_ingest.synth.rng import between, pick, stream

DATASETS = ("gb_companies_house", "gleif_lei", "nr_synthetic")
LIVE = ("active", "open", "registered")  # Companies House and GLEIF (ACTIVE), case-folded
LATEST_FOUNDED = date(2025, 11, 30)  # accounts open by 15 December 2025, never before founding
POOL = {"customer": 4, "supplier": 4, "ring": 4}
NAME_PROPS = ("name", "alias", "previousName")
SCHEMATA = ("Company", "BankAccount", "Ownership", "Payment")  # all the join ever writes
AUDIT = ("labels", "other schemata", "payments between input-held accounts", "scenario",
         "topics", "two-way counterparties")  # fmt: skip


@dataclass
class JoinResult:
    records: list[dict[str, Any]]  # C1 records, written in this order
    scenarios: list[Scenario]
    counts: Counter[str] = field(default_factory=Counter)


def _founded(props: dict[str, Any]) -> date | None:
    value = (props.get("incorporationDate") or ["2012"])[0]
    try:
        parts = [int(p) for p in value[:10].split("-")] + [1, 1]
        return date(parts[0], parts[1], parts[2])
    except ValueError:
        return None


def _skip(record: dict[str, Any]) -> str | None:
    """Why a record gets no account (None: it is a holder). Anything unknown fails closed."""
    schema = model.get(str(record.get("schema")))
    if schema is None or not schema.is_a("LegalEntity"):
        return "not a legal entity"
    dataset = (record.get("datasets") or ["?"])[0]
    if dataset not in DATASETS:
        return f"dataset {dataset}"
    if schema.name not in ("Company", "Organization"):
        return f"schema {schema.name}"
    props = record.get("properties") or {}
    status = {str(s).casefold() for s in props.get("status") or []}
    if props.get("dissolutionDate") or not status <= set(LIVE):
        return "status not live"
    founded = _founded(props)
    return None if founded is not None and founded <= LATEST_FOUNDED else "incorporation date"


def synthetic_join(
    inputs: Iterable[dict[str, Any]], seed: int, max_holders: int = 200
) -> JoinResult:
    """Accounts and background payments for the input's live registry organisations, plus one
    scenario among new synthetic companies. Returns the new records only."""
    first_seen: dict[str, dict[str, Any]] = {}
    for record in inputs:  # a duplicate id keeps its first record, as C1 R4 does
        first_seen.setdefault(str(record.get("id")), record)
    unique = list(first_seen.values())
    counts: Counter[str] = Counter()
    holders = []
    for r in sorted(unique, key=lambda r: str(r.get("id"))):
        reason = _skip(r)
        if reason is None:
            holders.append(r)
        elif reason != "not a legal entity":
            counts[f"skipped: {reason}"] += 1
    counts["skipped: over --max-holders"] += max(0, len(holders) - max_holders)
    holders = holders[:max_holders]
    props = [r.get("properties") or {} for r in unique]
    taken = {name_key(v) for p in props for prop in NAME_PROPS for v in p.get(prop) or []}
    used = {v for p in props for v in p.get("accountNumber") or []}

    reg, rng, names = Registry(ns=f"j{seed}-"), stream(seed, "join"), CompanyNames(seed, taken)
    roles = [role for role, size in POOL.items() for _ in range(size)]
    pool: dict[str, list[str]] = {role: [] for role in POOL}
    for number, index in enumerate(rng.permutation(len(roles)), start=1):  # ids hide roles
        cid = sid("co", number, ns=reg.ns)
        name, _ = names.draw(number, "gb")
        new = {"name": [name], "jurisdiction": ["gb"], "registrationNumber": [f"SYNJ{number:05d}"]}
        reg.records.append(Rec(cid, "Company", "registry", new))
        reg.founded[cid] = date(2015, 1, 1)
        pool[roles[int(index)]].append(cid)
    currency: dict[str, str] = {}
    for r in holders:
        hid = str(r["id"])
        currency[hid] = "GBP" if "gb" in (r["properties"].get("jurisdiction") or []) else "EUR"
        reg.founded[hid] = _founded(r["properties"]) or LATEST_FOUNDED
    wanted = [(h, cur, "customer") for h, cur in currency.items()]
    wanted += [(c, cur, "customer") for role in POOL for c in pool[role] for cur in ("GBP", "EUR")]
    first = 1_000_000_000 + (seed % 8_999) * 1_000_000  # demo-mini numbers stay below 1,000
    while used & {f"NRSYN{n:010d}" for n in range(first, first + len(wanted))}:
        first += len(wanted)
    acct = open_accounts(reg, wanted, seed, first_number=first)
    clash = {str(r.get("id")) for r in unique} & {rec.id for rec in reg.records}
    if clash:
        raise ValueError(f"{len(clash)} new id(s) already exist in the input; use another seed")

    pays: list[Pay] = []
    for target, cur, n, kind in [
        *((h, cur, 6, "payments with input entities") for h, cur in currency.items()),
        *((c, "EUR", 6, "payments among synthetic companies") for c in pool["ring"]),
    ]:
        for i in range(n):  # receipts from customers, payments to suppliers, alternately
            mine = acct[target, cur]
            other = acct[pick(rng, pool["customer" if i % 2 == 0 else "supplier"]), cur]
            source, sink = (other, mine) if i % 2 == 0 else (mine, other)
            ref = f"Invoice INV-{between(rng, 10000, 99999)}"
            if target in currency:
                cents, purpose = amount(rng, 50_000, 900_000, 5_000_000), ref
            else:  # the scenario companies' background looks like the scenario (demo-mini)
                cents = amount(rng, *EUR_BACKGROUND, p_low=0.5)
                purpose = ref if i % 4 == 0 else EUR_PURPOSES[i % 4]
            pays.append(Pay(source, sink, cents, office(rng), "wire", purpose))
            counts[kind] += 1
    trip = round_trip(stream(seed, "scenario"), [acct[c, "EUR"] for c in pool["ring"]])
    pays = prune([*pays, *trip], [trip], trip)
    number_payments(pays, ns=reg.ns)
    reg.records.extend(p.to_rec() for p in pays)
    counts.update({
        "input records (unique ids)": len(unique), "holders": len(holders),
        "new synthetic companies": len(roles), "payments in the scenario": len(trip),
    })  # fmt: skip
    steps = list(zip(trip, ("outbound", "pass_through", "pass_through", "return"), strict=True))
    label = scenario_label(
        "scn-0001", "round_trip", False, steps,
        [("origin", trip[0].source), *(("intermediary", p.target) for p in trip[:3])],
    )  # fmt: skip
    return JoinResult([rec.to_dict() for rec in ordered(reg.records)], [label], counts)


def touches_input(result: JoinResult, input_ids: set[str]) -> Counter[str]:
    """G1 audit: everything in the new records or labels that should never refer to an input
    entity, by kind. All counts must be 0; holding an account and its background payments with
    one-way synthetic counterparties are the only allowed links."""
    found: Counter[str] = Counter(dict.fromkeys(AUDIT, 0))
    held = {
        r["properties"]["asset"][0]
        for r in result.records
        if r["schema"] == "Ownership" and r["properties"]["owner"][0] in input_ids
    }
    pays = [r["properties"] for r in result.records if r["schema"] == "Payment"]
    senders = {p["payerAccount"][0] for p in pays}
    receivers = {p["beneficiaryAccount"][0] for p in pays}
    for r in result.records:
        found["topics"] += bool(r["properties"].get("topics"))
        found["other schemata"] += r["schema"] not in SCHEMATA
    for p in pays:
        ends = {p["payerAccount"][0], p["beneficiaryAccount"][0]}
        found["payments between input-held accounts"] += ends <= held
        if ends & held:
            other = ends - held
            found["two-way counterparties"] += bool(other & senders & receivers)
    by_id = {r["id"]: r["properties"] for r in result.records}
    for sc in result.scenarios:
        found["labels"] += sum(rid in input_ids or rid in held for _, rid in sc.participants)
        for tx, _, _ in sc.steps:
            p = by_id[tx]
            parties = [
                p[k][0] for k in ("payer", "beneficiary", "payerAccount", "beneficiaryAccount")
            ]
            found["scenario"] += sum(e in input_ids or e in held for e in parties)
    return found
