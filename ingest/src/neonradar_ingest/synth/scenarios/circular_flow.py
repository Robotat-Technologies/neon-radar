"""circular_flow scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 4; M1.8e `round_trip`).

Illicit `round_trip` (easy): 30,000 to 400,000 leaves an account, passes through 2 to 5 other
companies (often abroad), each keeping 0.5 to 3 percent, and comes back to the same account within
2 to 12 days. Illicit `same_holder_return` (hard): the money comes back to another account of the
same holder, or the trip lasts 12 to 20 days. Look-alikes: a refund (`refund`), a short loan
drawdown and repayment (`loan`), and an intra-group cash pooling sweep and return (`cash_pool`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, foreign, opened_before, uniform

TYPOLOGY = "circular_flow"
ILLICIT = (("round_trip", "easy"), ("same_holder_return", "hard"))
LOOKALIKES = ("refund", "loan", "cash_pool")
SPAN_DAYS = 45
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    origin_holder = s.label(
        s.company(incorporated=opened_before(rng, start, 300, 5000)), "origin_holder"
    )
    origin = s.label(
        s.account(origin_holder, opened=opened_before(rng, start, 300, 4000)), "origin"
    )
    back = origin
    total_days = float(rng.uniform(2, 12))
    if variant == "same_holder_return":
        if rng.random() < 0.6:
            back = s.label(
                s.account(origin_holder, opened=opened_before(rng, start, 300, 4000)),
                "return_account",
            )
        else:
            total_days = float(rng.uniform(12, 20))
    hops = int(rng.integers(3, 7))
    intermediaries = []
    for _ in range(hops - 1):
        co = s.company(
            incorporated=opened_before(rng, start, 60, 1500),
            jurisdiction=foreign(rng) if rng.random() < 0.6 else "gb",
        )
        intermediaries.append(s.account(co, opened=opened_before(rng, start, 30, 900)))
    path = [origin, *intermediaries, back]
    amount = uniform(rng, 30000, 400000)
    moment = at(rng, start)
    gaps = rng.dirichlet([1.5] * hops) * total_days * 24
    for i in range(hops):
        if i > 0:
            moment = later(rng, moment, max(1.0, float(gaps[i]) * 0.9), max(1.5, float(gaps[i])))
        p = s.pay(
            path[i], path[i + 1], amount, moment, purpose="Investment" if i == 0 else "Services"
        )
        s.label_payment(p, "hop")
        amount = round(amount * float(rng.uniform(0.97, 0.995)), 2)
    camouflage(
        s,
        origin,
        utc(start.year, start.month, start.day) - timedelta(days=50),
        utc(start.year, start.month, start.day),
    )
    s.finish(
        variant,
        difficulty,
        {"hops": hops, "days": round(total_days, 1), "same_holder": back != origin},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    a_holder = s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail")
    a = s.label(s.account(a_holder, opened=opened_before(rng, start, 400, 4000)), "origin")
    s.label(a_holder, "origin_holder")
    moment = at(rng, start)
    if kind == "refund":
        b = s.account(
            s.company(incorporated=opened_before(rng, start, 800, 6000)),
            opened=opened_before(rng, start, 400, 4000),
        )
        amount = uniform(rng, 1000, 30000)
        s.label_payment(s.pay(a, b, amount, moment, purpose="Order 4471"), "hop")
        s.label_payment(
            s.pay(b, a, amount, later(rng, moment, 24, 240), purpose="Refund order 4471"), "hop"
        )
    elif kind == "loan":
        lender = s.account(
            s.organization(f"Synthetic Lending {s.scenario_id[-5:]} Ltd"),
            opened=opened_before(rng, start, 2000, 8000),
        )
        amount = uniform(rng, 5000, 80000)
        s.label_payment(s.pay(lender, a, amount, moment, purpose="Loan drawdown"), "hop")
        s.label_payment(
            s.pay(
                a,
                lender,
                round(amount * float(rng.uniform(1.0, 1.03)), 2),
                later(rng, moment, 5 * 24, 13 * 24),
                purpose="Loan repayment",
            ),
            "hop",
        )
    else:  # cash_pool
        parent = s.company(incorporated=opened_before(rng, start, 2000, 8000))
        s.owns(parent, a_holder, band="75-100", start=opened_before(rng, start, 900, 4000))
        pool = s.account(parent, opened=opened_before(rng, start, 400, 4000))
        amount = uniform(rng, 20000, 200000)
        s.label_payment(s.pay(a, pool, amount, moment, purpose="Cash pool sweep"), "hop")
        s.label_payment(
            s.pay(
                pool,
                a,
                round(amount * float(rng.uniform(0.95, 1.0)), 2),
                later(rng, moment, 16, 72),
                purpose="Cash pool return",
            ),
            "hop",
        )
    s.finish(kind, "", {})
