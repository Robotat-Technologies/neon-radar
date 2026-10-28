"""fan_out_distribution scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 6).

Illicit `cash_out` (easy): one account pays 10 to 25 newly opened accounts of people similar or
round amounts within 1 to 2 days; most recipients withdraw 80 to 100 percent in cash or pass it on
within 1 to 4 days. Illicit `spread_out` (hard): amounts vary widely and only about half the
recipients move the money on, so some fall below a one-half rule. Look-alikes: a recurring
payroll (`payroll`), a one-off dividend to shareholders (`dividend`) and refunds after a cancelled
event (`event_refunds`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "fan_out_distribution"
ILLICIT = (("cash_out", "easy"), ("spread_out", "hard"))
LOOKALIKES = ("payroll", "dividend", "event_refunds")
SPAN_DAYS = 100
LEAD_DAYS = 70


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 30, 400)), "distributor_holder"
    )
    dist = s.label(s.account(holder, opened=opened_before(rng, start, 20, 300)), "distributor")
    branch = s.ctx.branches[int(rng.integers(len(s.ctx.branches)))]
    first = at(rng, start)
    n = int(rng.integers(10, 26))
    base = float(rng.choice([900.0, 950.0, 1000.0, 2000.0]))
    for _ in range(n):
        r = s.account(s.person(born=(1985, 2006)), opened=opened_before(rng, start, 5, 60))
        amount = base if variant == "cash_out" else uniform(rng, 300, 4500)
        moment = later(rng, first, 0, 40)
        s.label_payment(s.pay(dist, r, amount, moment, purpose="Payment"), "distribution")
        moves = rng.random() < (0.9 if variant == "cash_out" else 0.7)
        if moves:
            out = round(amount * float(rng.uniform(0.8, 1.0)), 2)
            s.label_payment(
                s.pay(r, branch, out, later(rng, moment, 20, 96), channel="cash_withdrawal"),
                "cash_out",
            )
    s.finish(
        variant, difficulty, {"recipients": n, "amount": base if variant == "cash_out" else None}
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 900, 8000)), "distributor_holder"
    )
    dist = s.label(s.account(holder, opened=opened_before(rng, start, 500, 5000)), "distributor")
    shop = s.account(
        s.company(incorporated=opened_before(rng, start, 900, 8000), sector="retail"),
        opened=opened_before(rng, start, 500, 5000),
    )
    n = int(rng.integers(10, 30))
    people = [s.account(s.person(), opened=opened_before(rng, start, 300, 6000)) for _ in range(n)]
    if kind == "payroll":
        salaries = [uniform(rng, 1500, 3500) for _ in range(n)]
        for month in range(3):
            day = start + timedelta(days=30 * month)
            for p, amount in zip(people, salaries, strict=True):
                moment = at(rng, day, 7, 9)
                s.label_payment(s.pay(dist, p, amount, moment, purpose="Salary"), "distribution")
                s.pay(
                    p,
                    shop,
                    round(amount * 0.15, 2),
                    later(rng, moment, 24, 200),
                    channel="card",
                    purpose="Groceries",
                )
    elif kind == "dividend":
        moment = at(rng, start)
        for p in people:
            s.label_payment(
                s.pay(
                    dist,
                    p,
                    float(rng.choice([500.0, 1000.0, 1500.0])),
                    later(rng, moment, 0, 6),
                    purpose="Dividend",
                ),
                "distribution",
            )
    else:  # event_refunds: the recipients had paid the organiser before
        moment = at(rng, start)
        for p in people:
            s.pay(
                p,
                dist,
                120.0,
                later(rng, moment - timedelta(days=40), 0, 240),
                channel="card",
                purpose="Ticket",
            )
            s.label_payment(
                s.pay(dist, p, 120.0, later(rng, moment, 0, 30), purpose="Refund"), "distribution"
            )
    s.finish(kind, "", {"recipients": n})
