"""Synthetic accounts and payments (PHASE-1.md M1.8e deliverable 1, `activity.py`).

Background activity comes first, at a realistic volume: payroll fan-out, supplier invoices,
card purchases, cash deposits and withdrawals, refunds, one loan drawdown and repayment, and
cross-border payments in EUR. One `round_trip` scenario (4 hops, about 2 percent fee per hop,
1 to 2 days apart) runs only among synthetic entities. Every timestamp is a weekday between
08:00 and 18:00 UTC, the scenario's included, and every purpose the scenario uses also
appears in the background, so nothing in the records gives it away (R9).

The generator then removes background payments that close a cycle the circular-flow
detector would report with the default parameters (`cycles.py`), so the labels list every such
cycle: the scenario and two benign look-alikes (the loan, one full refund). It removes
one-off payments before periodic ones (salaries). The PEP holds no account, and the
sanctioned company never pays or is paid by a round-trip account, so flags stay apart from
planted patterns.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta

import numpy as np

from neonradar_ingest.synth import words
from neonradar_ingest.synth.cycles import Hop, find_cycles
from neonradar_ingest.synth.emit import Rec, Scenario
from neonradar_ingest.synth.registry import Registry, sid
from neonradar_ingest.synth.rng import between, chance, pick, stream

FIRST_DAY, LAST_DAY = date(2026, 1, 5), date(2026, 4, 2)  # Good Friday is 3 April 2026
BUSINESS_DAYS = tuple(
    day
    for day in (FIRST_DAY + timedelta(days=n) for n in range((LAST_DAY - FIRST_DAY).days + 1))
    if day.weekday() < 5
)
OPEN, CLOSE = 8 * 3600, 18 * 3600 - 1
PAYDAYS = ((date(2026, 1, 30), "January"), (date(2026, 2, 27), "February"),
           (date(2026, 3, 31), "March"))  # fmt: skip
EUR_PURPOSES = ("Invoice", "Commission", "Service fee", "Shareholder loan")
TYPOLOGY = "circular_flow"


@dataclass(frozen=True, slots=True)
class Account:
    id: str
    holder: str
    currency: str
    number: str
    kind: str  # customer | cash_ledger


@dataclass(slots=True)
class Pay:
    source: Account
    target: Account
    cents: int
    ts: datetime
    channel: str
    purpose: str
    id: str = ""

    def to_rec(self) -> Rec:
        props = {
            "payer": [self.source.holder], "beneficiary": [self.target.holder],
            "payerAccount": [self.source.id], "beneficiaryAccount": [self.target.id],
            "amount": [f"{self.cents // 100}.{self.cents % 100:02d}"],
            "currency": [self.source.currency], "date": [stamp(self.ts)],
            "purpose": [self.purpose],
        }  # fmt: skip
        return Rec(self.id, "Payment", "activity", props, {"channel": self.channel})


def stamp(ts: datetime) -> str:
    """UTC `YYYY-MM-DDTHH:MM:SS` without an offset or Z (C1 R5)."""
    return ts.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S")


def at(day: date, second: int) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(seconds=second)


def office(rng: np.random.Generator, day: date | None = None) -> datetime:
    """A random weekday time between 08:00 and 18:00 UTC (on `day` if given)."""
    return at(day or pick(rng, BUSINESS_DAYS), between(rng, OPEN, CLOSE))


def later_day(rng: np.random.Generator, day: date, low: int, high: int) -> date | None:
    """A business day `low` to `high` calendar days after `day`, inside the window."""
    options = [d for d in BUSINESS_DAYS if low <= (d - day).days <= high]
    return pick(rng, options) if options else None


def amount(rng: np.random.Generator, low: int, mid: int, high: int, p_low: float = 0.75) -> int:
    """Cents: mostly in [low, mid], sometimes in [mid, high] (integer draws only)."""
    return between(rng, low, mid) if chance(rng, p_low) else between(rng, mid, high)


def open_accounts(
    reg: Registry, holders: Iterable[tuple[str, str, str]], seed: int, first_number: int = 1
) -> dict[tuple[str, str], Account]:
    """Accounts for (holder, currency, kind), numbered in holder order from `first_number`
    (ids in `reg.ns`), each with its holder Ownership."""
    rng = stream(seed, "accounts")
    accounts: dict[tuple[str, str], Account] = {}
    for number, (holder, currency, kind) in enumerate(sorted(holders), start=first_number):
        aid = sid("acct", number, ns=reg.ns)
        account = Account(aid, holder, currency, f"NRSYN{number:010d}", kind)
        accounts[holder, currency] = account
        if kind == "cash_ledger":
            bank = words.BANKS[reg.branches.index(holder)]
        else:
            bank = words.BANKS[2] if currency == "EUR" else pick(rng, words.BANKS[:2])
        founded = reg.founded.get(holder, date(2012, 1, 1))
        opened = min(founded + timedelta(days=between(rng, 20, 900)), date(2025, 12, 15))
        props = {
            "accountNumber": [account.number], "bankName": [bank], "currency": [currency],
            "openingDate": [opened.isoformat()],
        }  # fmt: skip
        reg.records.append(Rec(aid, "BankAccount", "activity", props, {"account_kind": kind}))
        reg.own(holder, aid, opened)
    return accounts


def round_trip(rng: np.random.Generator, ring: list[Account]) -> list[Pay]:
    """Funds leave ring[0], pass ring[1..3] and come back: a fee of 1.5 to 2.5 percent per hop,
    each hop one or two calendar days after the previous one, Monday to Friday, office hours."""
    day = pick(rng, [d for d in BUSINESS_DAYS[10:-10] if d.weekday() == 0])
    gaps = pick(rng, ((1, 1, 1), (2, 1, 1), (1, 2, 1), (1, 1, 2)))  # ends by Friday
    cents = between(rng, 4_000_000, 11_000_000)  # inside the background EUR range, not its top
    purposes = (f"Invoice INV-{between(rng, 10000, 99999)}", *EUR_PURPOSES[1:])
    hops = []
    for hop in range(4):
        hops.append(Pay(ring[hop], ring[(hop + 1) % 4], cents, office(rng, day), "wire",
                        purposes[hop]))  # fmt: skip
        if hop < 3:
            day += timedelta(days=gaps[hop])
            cents = cents * (10_000 - between(rng, 150, 250)) // 10_000
    return hops


def _order(pay: Pay) -> tuple[datetime, str, str, int, str]:
    return (pay.ts, pay.source.id, pay.target.id, pay.cents, pay.purpose)


def prune(pays: list[Pay], planted: list[list[Pay]], keep: list[Pay]) -> list[Pay]:
    """Drop background payments that close a detectable cycle that was not planted.

    Keys come from the payments' sorted order, never from memory addresses, so the same input
    always loses the same payments.
    """
    pays = sorted(pays, key=_order)
    kept = {id(p) for p in keep}
    while True:
        keys = {id(p): f"{index:06d}" for index, p in enumerate(pays)}
        hops = [Hop(keys[id(p)], p.source.id, p.target.id, int(p.ts.timestamp()), p.cents)
                for p in pays]  # fmt: skip
        wanted = {tuple(keys[id(p)] for p in cycle) for cycle in planted}
        found = find_cycles(hops)
        extra = [cycle for cycle in found if cycle not in wanted]
        if not extra:
            if wanted - set(found):
                raise RuntimeError("a planted cycle is not detectable; check its timing")
            return pays
        by_key = {keys[id(p)]: p for p in pays}
        removable = [by_key[k] for k in extra[0] if id(by_key[k]) not in kept]
        if not removable:
            raise RuntimeError("an unplanned cycle consists of planted payments only")
        one_off = [p for p in removable if not p.purpose.startswith("Salary")]
        victim = max(one_off or removable, key=_order)
        pays = [p for p in pays if p is not victim]


def number_payments(pays: list[Pay], ns: str = "") -> None:
    """Ids in time order, so planted payments are spread among the background."""
    pays.sort(key=_order)
    for number, pay in enumerate(pays, start=1):
        pay.id = sid("payment", number, width=6, ns=ns)


def scenario_label(
    scenario_id: str, variant: str, lookalike: bool, steps: list[tuple[Pay, str]],
    participants: list[tuple[str, Account]],
) -> Scenario:  # fmt: skip
    roles: list[tuple[str, str]] = []
    for role, account in participants:
        roles += [(role, account.id), (f"{role}_holder", account.holder)]
    return Scenario(
        scenario_id, TYPOLOGY, variant, lookalike, not lookalike,
        tuple((p.id, role, stamp(p.ts)) for p, role in steps), tuple(roles),
    )  # fmt: skip


def demo_activity(reg: Registry, seed: int) -> list[Scenario]:
    """Accounts and payments for the demo-mini registry; appends the records to `reg`."""
    rng, scen_rng = stream(seed, "background"), stream(seed, "scenario")
    roles = reg.roles
    gb = [c for c, j in reg.jurisdiction.items() if j == "gb" and c not in reg.branches]
    offshore = [c for c, j in reg.jurisdiction.items() if j != "gb"]
    people = [p for p in reg.persons if p not in roles["pep"]]
    customers = [str(p) for p in rng.permutation(people)[:13]]
    holders = [(c, "GBP", "customer") for c in gb] + [(c, "EUR", "customer") for c in offshore]
    holders += [(c, "EUR", "customer") for c in roles["eur_second"]]
    holders += [(p, "GBP", "customer") for p in customers]
    holders += [(b, "GBP", "cash_ledger") for b in reg.branches]
    acct = open_accounts(reg, holders, seed)
    gbp = {c: acct[c, "GBP"] for c in gb}
    eur = sorted((a for a in acct.values() if a.currency == "EUR"), key=lambda a: a.id)
    ledgers = [acct[b, "GBP"] for b in reg.branches]

    pays: list[Pay] = []
    for index, employer in enumerate(roles["employers"]):
        for person in customers[index * 4 : index * 4 + 4]:
            salary = between(rng, 210_000, 480_000)
            for day, month in PAYDAYS:
                when = at(day, between(rng, 9 * 3600, 11 * 3600))
                pays.append(Pay(gbp[employer], acct[person, "GBP"], salary, when, "wire",
                                f"Salary {month} 2026"))  # fmt: skip
    cards = []
    for _ in range(66):
        buyer, shop = acct[pick(rng, customers), "GBP"], gbp[pick(rng, roles["retail"])]
        cards.append(Pay(buyer, shop, between(rng, 800, 18_000), office(rng), "card",
                         "Card purchase"))  # fmt: skip
    pays += cards
    for _ in range(86):
        payer, payee = (gbp[str(c)] for c in rng.choice(gb, 2, replace=False))
        cents = amount(rng, 45_000, 900_000, 4_800_000)
        pays.append(Pay(payer, payee, cents, office(rng), "wire",
                        f"Invoice INV-{between(rng, 10000, 99999)}"))  # fmt: skip
    ring_ids = {acct[c, "EUR"].id for c in roles["round_trip"]}
    for index in range(24):
        while True:
            payer, payee = (eur[int(i)] for i in rng.choice(len(eur), 2, replace=False))
            pair = {payer.holder, payee.holder}
            if not (pair & set(roles["sanctioned"]) and {payer.id, payee.id} & ring_ids):
                break
        purpose = EUR_PURPOSES[index % 4]
        if purpose == "Invoice":
            purpose = f"Invoice INV-{between(rng, 10000, 99999)}"
        cents = amount(rng, 500_000, 3_000_000, 18_000_000, p_low=0.5)
        pays.append(Pay(payer, payee, cents, office(rng), "wire", purpose))
    for _ in range(16):
        shop = gbp[pick(rng, roles["retail"])]
        pays.append(Pay(pick(rng, ledgers), shop, between(rng, 30_000, 480_000), office(rng),
                        "cash_deposit", "Cash deposit"))  # fmt: skip
    for _ in range(10):
        pays.append(Pay(acct[pick(rng, customers), "GBP"], pick(rng, ledgers),
                        between(rng, 2, 30) * 2_000, office(rng), "cash_withdrawal",
                        "Cash withdrawal"))  # fmt: skip

    refunds: list[tuple[Pay, Pay]] = []
    for index in rng.permutation(len(cards)):
        purchase = cards[int(index)]
        refund_day = later_day(rng, purchase.ts.date(), 1, 6)
        if refund_day is None:
            continue
        full = len(refunds) == 3
        cents = purchase.cents if full else purchase.cents * between(rng, 40, 70) // 100
        refunds.append((purchase, Pay(purchase.target, purchase.source, cents,
                                      office(rng, refund_day), "card", "Refund")))  # fmt: skip
        if full:
            break
    pays += [refund for _, refund in refunds]

    lender, borrower = gbp[roles["lender"][0]], gbp[roles["borrower"][0]]
    draw_day = pick(scen_rng, [d for d in BUSINESS_DAYS if d + timedelta(days=13) <= LAST_DAY])
    repay_day = later_day(scen_rng, draw_day, 10, 13) or draw_day + timedelta(days=11)
    principal = between(scen_rng, 25, 60) * 100_000
    loan = [
        Pay(lender, borrower, principal, office(scen_rng, draw_day), "wire", "Loan drawdown"),
        Pay(borrower, lender, principal * (10_000 + between(scen_rng, 30, 80)) // 10_000,
            office(scen_rng, repay_day), "wire", "Loan repayment"),
    ]  # fmt: skip
    ring = [acct[c, "EUR"] for c in roles["round_trip"]]
    trip = round_trip(scen_rng, ring)
    pays += loan + trip

    planted = [trip, loan, list(refunds[-1])]
    keep = [p for pair in refunds for p in pair] + loan + trip
    pays = prune(pays, planted, keep)
    number_payments(pays)
    reg.records.extend(p.to_rec() for p in pays)
    purchase, refund = refunds[-1]
    return [
        scenario_label("scn-0001", "round_trip", False,
                       list(zip(trip, ("outbound", "pass_through", "pass_through", "return"),
                                strict=True)),
                       [("origin", ring[0]), *(("intermediary", a) for a in ring[1:])]),
        scenario_label("scn-0002", "loan_drawdown_repayment", True,
                       list(zip(loan, ("drawdown", "repayment"), strict=True)),
                       [("lender", lender), ("borrower", borrower)]),
        scenario_label("scn-0003", "refund", True,
                       [(purchase, "purchase"), (refund, "refund")],
                       [("customer", purchase.source), ("merchant", purchase.target)]),
    ]  # fmt: skip
