"""layering_chain scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 3).

Illicit `chain` (easy): 50,000 to 500,000 passes through 3 to 6 accounts of different companies,
each keeping 0.5 to 3 percent and passing the rest on within 2 to 48 hours; two or more of the
intermediate companies share a registered address or a director. Illicit `split_chain` (hard): the
same, but one hop is split into two payments that merge again, or one dwell lasts 60 to 100 hours.
Look-alikes: a supply chain in which each tier adds a margin (`supply_chain`), and treasury sweeps
between companies of one group (`group_treasury`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "layering_chain"
ILLICIT = (("chain", "easy"), ("split_chain", "hard"))
LOOKALIKES = ("supply_chain", "group_treasury")
SPAN_DAYS = 30
LEAD_DAYS = 0


def _companies(s: ScenarioCtx, start: date, n: int, shared: bool) -> list[str]:
    rng = s.rng("companies")
    address = s.address() if shared else ""
    director = s.person() if shared else ""
    out = []
    for i in range(n):
        jurisdiction = foreign(rng) if rng.random() < 0.4 else "gb"
        co = s.company(
            incorporated=opened_before(rng, start, 60, 900),
            jurisdiction=jurisdiction,
            address=address if shared and i % 2 == 1 else "",
        )
        if shared and i % 2 == 0 and 0 < i < n - 1:
            s.director(director, co, start=opened_before(rng, start, 30, 600))
        out.append(co)
    return out


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    hops = int(rng.integers(3, 7))
    holders = _companies(s, start, hops + 1, True)
    accounts = [s.account(h, opened=opened_before(rng, start, 30, 700)) for h in holders]
    for h in holders[1:-1]:
        s.label(h, "intermediary_holder")
    s.label(accounts[0], "origin")
    s.label(accounts[-1], "destination")
    amount = uniform(rng, 50000, 500000)
    moment = at(rng, start)
    split_at = int(rng.integers(1, hops)) if variant == "split_chain" and rng.random() < 0.5 else -1
    slow_at = int(rng.integers(1, hops)) if variant == "split_chain" and split_at < 0 else -1
    for i in range(hops):
        dwell = (60, 100) if i == slow_at else (2, 48)
        if i > 0:
            moment = later(rng, moment, *dwell)
        if i == split_at:
            part = round(amount * float(rng.uniform(0.35, 0.65)), 2)
            for piece in (part, round(amount - part, 2)):
                s.label_payment(
                    s.pay(
                        accounts[i],
                        accounts[i + 1],
                        piece,
                        later(rng, moment, 0.1, 3),
                        purpose="Services",
                    ),
                    "hop",
                )
        else:
            s.label_payment(
                s.pay(accounts[i], accounts[i + 1], amount, moment, purpose="Services"), "hop"
            )
        amount = round(amount * float(rng.uniform(0.97, 0.995)), 2)
    for a in accounts[1:-1]:
        camouflage(
            s,
            a,
            utc(start.year, start.month, start.day) - timedelta(days=45),
            utc(start.year, start.month, start.day),
            n=2,
        )
    s.finish(variant, difficulty, {"hops": hops, "split_at": split_at, "slow_at": slow_at})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    tiers = int(rng.integers(3, 6))
    if kind == "group_treasury":
        parent = s.company(incorporated=opened_before(rng, start, 2000, 8000))
        holders = [parent] + [
            s.company(incorporated=opened_before(rng, start, 1000, 6000)) for _ in range(tiers)
        ]
        for child in holders[1:]:
            s.owns(parent, child, band="75-100", start=opened_before(rng, start, 900, 4000))
    else:
        holders = [
            s.company(incorporated=opened_before(rng, start, 1000, 8000), sector=sec)
            for sec in ["retail"] + ["wholesale"] * (tiers - 1) + ["manufacturing"]
        ]
    accounts = [s.account(h, opened=opened_before(rng, start, 400, 4000)) for h in holders]
    s.label(accounts[0], "origin")
    s.label(accounts[-1], "destination")
    amount = uniform(rng, 40000, 300000)
    moment = at(rng, start)
    for i in range(len(accounts) - 1):
        if i > 0:
            moment = later(rng, moment, 4, 60)
        s.label_payment(
            s.pay(accounts[i], accounts[i + 1], amount, moment, purpose="Invoice"), "hop"
        )
        if kind == "supply_chain":
            amount = round(
                amount * float(rng.uniform(0.80, 0.92)), 2
            )  # the upstream supplier is paid less
        else:
            amount = round(amount * float(rng.uniform(0.98, 1.0)), 2)
    s.finish(kind, "", {"tiers": tiers})
