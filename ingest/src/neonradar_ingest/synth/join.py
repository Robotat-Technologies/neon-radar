"""Synthetic join: accounts and background payments for entities that already exist (M1.8e).

PHASE-1.md M1.8e deliverable 3 and ADR-0005 (rule 2, guardrail G1). Given any C1 records, for
example spike output in `data/cache/spikes/`:

- Only organisations (`Company`, `Organization`, `PublicBody`) that are not dissolved get an
  account. People and bare `LegalEntity` records never do (ICIJ officers are often people).
- Each holder only receives payments from new synthetic "customer" companies and only pays new
  synthetic "supplier" companies. Customers never receive and suppliers never pay, so no input
  entity pays another and no cycle runs through an input entity's account.
- One `round_trip` scenario runs only among four new synthetic companies. They have background
  activity with the same customers and suppliers, never with an input entity.
- New ids sit in the namespace `syn-<kind>-j<seed>-NNNN` and new account numbers start above
  every `NRSYN` number in the input. A generated name equal to an input name is rejected.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from followthemoney import model

from neonradar_ingest.synth.activity import (
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

POOL = {"customer": 4, "supplier": 4, "ring": 4}
NAME_PROPS = ("name", "alias", "previousName")
ENDED = ("dissolved", "inactive", "closed", "struck off")
SCHEMATA = ("Company", "BankAccount", "Ownership", "Payment")  # all the join ever writes


@dataclass
class JoinResult:
    records: list[dict[str, Any]]  # C1 records, written in this order
    scenarios: list[Scenario]
    counts: Counter[str] = field(default_factory=Counter)


def _holder(record: dict[str, Any], counts: Counter[str]) -> bool:
    schema = model.get(str(record.get("schema")))
    props = record.get("properties") or {}
    if schema is None or not schema.is_a("LegalEntity"):
        return False
    if not schema.is_a("Organization"):
        counts[f"skipped {schema.name}"] += 1  # people and bare legal entities
        return False
    status = " ".join(props.get("status") or []).casefold()
    if props.get("dissolutionDate") or any(word in status for word in ENDED):
        counts["skipped dissolved"] += 1
        return False
    return True


def _founded(record: dict[str, Any]) -> date:
    value = ((record.get("properties") or {}).get("incorporationDate") or ["2012"])[0]
    parts = [int(p) for p in value[:10].split("-")] + [1, 1]
    return date(parts[0], parts[1], parts[2])


def synthetic_join(
    inputs: Iterable[dict[str, Any]], seed: int, max_holders: int = 200
) -> JoinResult:
    """Accounts and background payments for the input organisations, plus one scenario among
    new synthetic companies. Returns the new records only; the input is never changed."""
    inputs = list(inputs)
    counts: Counter[str] = Counter()
    holders = sorted((r for r in inputs if _holder(r, counts)), key=lambda r: str(r["id"]))
    holders = holders[:max_holders]
    props = [r.get("properties") or {} for r in inputs]
    taken = {name_key(v) for p in props for prop in NAME_PROPS for v in p.get(prop) or []}
    numbers = [int(v[5:]) for p in props for v in p.get("accountNumber") or []
               if v.startswith("NRSYN") and v[5:].isdigit()]  # fmt: skip

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
        reg.founded[hid] = _founded(r)
    wanted = [(h, cur, "customer") for h, cur in currency.items()]
    wanted += [(c, cur, "customer") for role in POOL for c in pool[role] for cur in ("GBP", "EUR")]
    acct = open_accounts(reg, wanted, seed, first_number=max(numbers, default=0) + 1)
    clash = {str(r.get("id")) for r in inputs} & {rec.id for rec in reg.records}
    if clash:
        raise ValueError(f"{len(clash)} new id(s) already exist in the input; use another seed")

    pays: list[Pay] = []
    for target, cur, n, kind in [
        *((h, cur, 6, "payments with input entities") for h, cur in currency.items()),
        *((c, "EUR", 4, "payments among synthetic companies") for c in pool["ring"]),
    ]:
        for i in range(n):  # receipts from customers, payments to suppliers, alternately
            mine = acct[target, cur]
            other = acct[pick(rng, pool["customer" if i % 2 == 0 else "supplier"]), cur]
            source, sink = (other, mine) if i % 2 == 0 else (mine, other)
            cents = amount(rng, 50_000, 900_000, 5_000_000)
            ref = f"Invoice INV-{between(rng, 10000, 99999)}"
            pays.append(Pay(source, sink, cents, office(rng), "wire", ref))
            counts[kind] += 1
    trip = round_trip(stream(seed, "scenario"), [acct[c, "EUR"] for c in pool["ring"]])
    pays = prune([*pays, *trip], [trip], trip)
    number_payments(pays, ns=reg.ns)
    reg.records.extend(p.to_rec() for p in pays)
    counts.update({
        "holders": len(holders), "accounts held by input entities": len(currency),
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
    entity, by kind. All counts must be 0; holding an account and its background payments are
    the only allowed links."""
    found: Counter[str] = Counter()
    held = {
        r["properties"]["asset"][0]
        for r in result.records
        if r["schema"] == "Ownership" and r["properties"]["owner"][0] in input_ids
    }
    by_id = {r["id"]: r for r in result.records}
    for r in result.records:
        found["topics"] += bool(r["properties"].get("topics"))
        found["other schemata"] += r["schema"] not in SCHEMATA
        if r["schema"] == "Payment":
            ends = {r["properties"]["payerAccount"][0], r["properties"]["beneficiaryAccount"][0]}
            found["payments between input-held accounts"] += ends <= held
    for sc in result.scenarios:
        found["labels"] += sum(rid in input_ids or rid in held for _, rid in sc.participants)
        for tx, _, _ in sc.steps:
            p = by_id[tx]["properties"]
            parties = [
                p[k][0] for k in ("payer", "beneficiary", "payerAccount", "beneficiaryAccount")
            ]
            found["scenario"] += sum(e in input_ids or e in held for e in parties)
    return found
