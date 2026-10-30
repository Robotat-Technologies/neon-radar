"""fan_in_collection scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 5).

Illicit `collector` (easy): 10 to 30 accounts of people, most of them years old (a fifth opened 10
to 60 days earlier: the senders are often victims, and recency belongs to the collector), each
pay 300 to 2,000 into one collection account within 2 to 6 days; the collector pays 80 to 95
percent on within 1 to 3 days or withdraws it in cash. Illicit `ring` (hard): 5 to 12 newly opened
accounts each receive from 2 to 4 people and pass the money to one or two hub accounts, also new,
which forward it. Look-alikes: a donation drive (`charity`), rent collection (`landlord`) and a
crowdfunding campaign that pays its beneficiary once (`crowdfunding`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import foreign, opened_before, uniform

TYPOLOGY = "fan_in_collection"
ILLICIT = (("collector", "easy"), ("ring", "hard"))
LOOKALIKES = ("charity", "landlord", "crowdfunding")
SPAN_DAYS = 100
LEAD_DAYS = 70


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    first = at(rng, start)
    branch = s.ctx.branches[0]
    if variant == "collector":
        collector_holder = s.label(s.person(born=(1985, 2005)), "collector_holder")
        collector = s.label(
            s.account(collector_holder, opened=opened_before(rng, start, 20, 90)), "collector"
        )
        n = int(rng.integers(10, 31))
        received = 0.0
        last = first
        for _ in range(n):
            new = rng.random() < 0.2
            sender = s.account(
                s.person(),
                opened=opened_before(rng, start, 10, 60)
                if new
                else opened_before(rng, start, 400, 4000),
            )
            amount = uniform(rng, 300, 2000)
            received += amount
            moment = later(rng, first, 0, float(rng.uniform(2, 6)) * 24)
            last = max(last, moment)
            s.label_payment(
                s.pay(sender, collector, amount, moment, purpose="Payment"), "contribution"
            )
        onward = round(received * float(rng.uniform(0.8, 0.95)), 2)
        if rng.random() < 0.5:
            s.label_payment(
                s.pay(
                    collector, branch, onward, later(rng, last, 24, 72), channel="cash_withdrawal"
                ),
                "cash_out",
            )
        else:
            dest = s.account(
                s.company(
                    incorporated=opened_before(rng, start, 100, 2000), jurisdiction=foreign(rng)
                ),
                opened=opened_before(rng, start, 100, 2000),
            )
            s.label_payment(
                s.pay(collector, dest, onward, later(rng, last, 24, 72), purpose="Goods"), "onward"
            )
        s.finish(variant, difficulty, {"senders": n})
        return
    hubs = [
        s.account(
            s.label(s.person(born=(1985, 2005)), "collector_holder"),
            opened=opened_before(rng, start, 5, 40),
        )
        for _ in range(int(rng.integers(1, 3)))
    ]
    for h in hubs:
        s.label(h, "collector")
    mules = int(rng.integers(5, 13))
    hub_in = {h: 0.0 for h in hubs}
    for m in range(mules):
        mule = s.account(s.person(born=(1990, 2006)), opened=opened_before(rng, start, 5, 45))
        got = 0.0
        for _ in range(int(rng.integers(2, 5))):
            victim = s.account(
                s.person(born=(1940, 1990)), opened=opened_before(rng, start, 1000, 9000)
            )
            amount = uniform(rng, 400, 2500)
            got += amount
            s.label_payment(
                s.pay(victim, mule, amount, later(rng, first, 0, 72), purpose="Transfer"),
                "victim_payment",
            )
        hub = hubs[m % len(hubs)]
        share = round(got * float(rng.uniform(0.85, 0.95)), 2)
        hub_in[hub] += share
        s.label_payment(
            s.pay(mule, hub, share, later(rng, first, 80, 120), purpose="Transfer"), "to_hub"
        )
    for hub in hubs:
        s.label_payment(
            s.pay(
                hub,
                branch,
                round(hub_in[hub] * 0.9, 2),
                later(rng, first, 130, 170),
                channel="cash_withdrawal",
            ),
            "cash_out",
        )
    s.finish(variant, difficulty, {"mules": mules, "hubs": len(hubs)})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    first = at(rng, start)
    sector = {"charity": "charity", "landlord": "real estate", "crowdfunding": "services"}[kind]
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector=sector),
        "collector_holder",
    )
    acct = s.label(s.account(holder, opened=opened_before(rng, start, 400, 4000)), "collector")
    if kind == "landlord":
        tenants = [
            s.account(s.person(), opened=opened_before(rng, start, 400, 5000))
            for _ in range(int(rng.integers(8, 20)))
        ]
        mortgage = s.account(
            s.organization(f"Synthetic Mortgages {s.scenario_id[-5:]} plc"),
            opened=opened_before(rng, start, 3000, 9000),
        )
        for month in range(3):
            day = start + timedelta(days=30 * month)
            for t in tenants:
                s.label_payment(s.pay(t, acct, 950.0, at(rng, day), purpose="Rent"), "contribution")
            s.label_payment(
                s.pay(acct, mortgage, 950.0 * len(tenants) * 0.7, at(rng, day + timedelta(days=2))),
                "onward",
            )
    else:
        n = int(rng.integers(25, 80))
        total = 0.0
        for _ in range(n):
            donor = s.account(s.person(), opened=opened_before(rng, start, 300, 6000))
            amount = uniform(rng, 10, 250)
            total += amount
            s.label_payment(
                s.pay(
                    donor,
                    acct,
                    amount,
                    later(rng, first, 0, 5 * 24),
                    channel="card",
                    purpose="Donation",
                ),
                "contribution",
            )
        if kind == "crowdfunding":
            beneficiary = s.account(s.person(), opened=opened_before(rng, start, 300, 6000))
            s.label_payment(
                s.pay(
                    acct,
                    beneficiary,
                    round(total * 0.95, 2),
                    later(rng, first, 6 * 24, 8 * 24),
                    purpose="Campaign payout",
                ),
                "onward",
            )
    s.finish(kind, "", {})
