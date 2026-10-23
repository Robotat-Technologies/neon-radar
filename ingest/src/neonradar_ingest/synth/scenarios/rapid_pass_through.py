"""rapid_pass_through scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 2).

Illicit `funnel` (easy): 3 to 8 payers send 25,000 to 200,000 in all within 1 to 4 days; within 2
to 36 hours of each arrival the account sends 90 to 98 percent on to 1 or 2 beneficiaries, one of
them abroad. Illicit `slow_funnel` (hard): dwell of 20 to 70 hours and 2 to 5 beneficiaries, so
part of it falls outside a 48-hour, 3-beneficiary rule. Look-alikes: a payroll bureau (one client
in, many employees out), a marketplace settlement account (many buyers in, one payout to the
merchant next day), an escrow account (holds for 20 to 40 days).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "rapid_pass_through"
ILLICIT = (("funnel", "easy"), ("slow_funnel", "hard"))
LOOKALIKES = ("payroll_bureau", "marketplace_settlement", "escrow")
SPAN_DAYS = 45
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    hub_holder = s.label(
        s.company(incorporated=opened_before(rng, start, 200, 2000), sector="trading"), "holder"
    )
    hub = s.label(
        s.account(hub_holder, opened=opened_before(rng, start, 100, 1500)), "pass_through_account"
    )
    n_in = int(rng.integers(3, 9))
    total = uniform(rng, 25000, 200000)
    shares = rng.dirichlet([2.0] * n_in)
    n_out = int(rng.integers(1, 3)) if variant == "funnel" else int(rng.integers(2, 6))
    dests = []
    for i in range(n_out):
        jurisdiction = foreign(rng) if i == 0 else "gb"
        dests.append(
            s.account(
                s.company(
                    incorporated=opened_before(rng, start, 300, 3000), jurisdiction=jurisdiction
                ),
                opened=opened_before(rng, start, 200, 3000),
            )
        )
    first = at(rng, start)
    lo, hi = (2, 36) if variant == "funnel" else (20, 70)
    for i in range(n_in):
        payer = s.account(
            s.company(incorporated=opened_before(rng, start, 300, 5000)),
            opened=opened_before(rng, start, 300, 4000),
        )
        moment = first if i == 0 else later(rng, first, 1, 72)
        amount = round(total * float(shares[i]), 2) or 1.0
        s.label_payment(s.pay(payer, hub, amount, moment, purpose="Consultancy"), "inflow")
        out = round(amount * float(rng.uniform(0.90, 0.98)), 2)
        dest = dests[i % n_out]
        s.label_payment(
            s.pay(hub, dest, out, later(rng, moment, lo, hi), purpose="Services"), "outflow"
        )
    camouflage(
        s,
        hub,
        utc(start.year, start.month, start.day) - timedelta(days=40),
        utc(start.year, start.month, start.day),
    )
    s.finish(
        variant,
        difficulty,
        {"inflows": n_in, "beneficiaries": n_out, "dwell_hours": [lo, hi], "total": total},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector="services"), "holder"
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 300, 3000)), "pass_through_account"
    )
    if kind == "payroll_bureau":
        client = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        n = int(rng.integers(12, 30))
        salaries = [uniform(rng, 1400, 3200) for _ in range(n)]
        s.label_payment(
            s.pay(client, acct, round(sum(salaries) * 1.01, 2), moment, purpose="Payroll funding"),
            "inflow",
        )
        for amount in salaries:
            emp = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            s.label_payment(
                s.pay(acct, emp, amount, later(rng, moment, 3, 20), purpose="Salary"), "outflow"
            )
    elif kind == "marketplace_settlement":
        merchant = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail"),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        received = 0.0
        for _ in range(int(rng.integers(8, 20))):
            buyer = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            amount = uniform(rng, 900, 4000)
            received += amount
            s.label_payment(
                s.pay(
                    buyer, acct, amount, later(rng, moment, 0, 40), channel="card", purpose="Order"
                ),
                "inflow",
            )
        s.label_payment(
            s.pay(
                acct,
                merchant,
                round(received * 0.97, 2),
                later(rng, moment, 44, 50),
                purpose="Settlement",
            ),
            "outflow",
        )
    else:  # escrow
        seller = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 300, 3000),
        )
        moment = at(rng, start)
        received = 0.0
        for _ in range(int(rng.integers(3, 6))):
            payer = s.account(s.person(), opened=opened_before(rng, start, 300, 4000))
            amount = uniform(rng, 8000, 15000)
            received += amount
            s.label_payment(
                s.pay(payer, acct, amount, later(rng, moment, 0, 72), purpose="Deposit"), "inflow"
            )
        s.label_payment(
            s.pay(
                acct,
                seller,
                round(received, 2),
                later(rng, moment, 20 * 24, 40 * 24),
                purpose="Completion",
            ),
            "outflow",
        )
    s.finish(kind, "", {})
