"""dormant_reactivation scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 7).

The burst starts on the scenario's start day; the quiet gap lies before it. Illicit
`reactivated` (easy): a company account with a few small payments, then 200 to 300 quiet days,
then 6 to 15 payments in and out totalling 50,000 to 300,000 within 3 to 10 days, 5 to 30 days
after a new director was appointed. Illicit `dormant_company` (hard): the holder filed dormant
accounts; a quiet gap of 150 to 260 days ends in 4 to 10 payments totalling 15,000 to 60,000 over up
to 20 days, so some bursts fall below the thresholds. Illicit `capital_flip` (medium): a company
incorporated 20 to 80 days earlier receives two or three large payments totalling 80,000 to
400,000 and pays 85 to 100 percent of it on to two to four accounts within five days ("large sums
of capital funding quickly following incorporation", FATF and Egmont 2018 Annex E).
Look-alikes: a seasonal business back after its closed season at its usual level (`seasonal`), a
property sale paid into a long-quiet personal account (`property_sale`, which the detector does
flag: the shape is the same), a business that restarts at its earlier level under a new owner
(`restart`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "dormant_reactivation"
ILLICIT = (("reactivated", "easy"), ("dormant_company", "hard"), ("capital_flip", "medium"))
LOOKALIKES = ("seasonal", "property_sale", "restart")
SPAN_DAYS = 25
LEAD_DAYS = 420


def _counterparties(s: ScenarioCtx, start: date, n: int) -> list[str]:
    rng = s.rng("counterparties")
    return [
        s.account(
            s.company(incorporated=opened_before(rng, start, 200, 4000)),
            opened=opened_before(rng, start, 200, 3000),
        )
        for _ in range(n)
    ]


def _burst(s: ScenarioCtx, acct: str, start: date, n: int, total: float, days: float) -> None:
    """Payments in from some counterparties and out to others, alternately."""
    rng = s.rng("burst", acct)
    payers = _counterparties(s, start, max(2, n // 4))
    payees = _counterparties(s, start, max(2, n // 4))
    first = at(rng, start)
    amount = total / n
    for i in range(n):
        moment = first if i == 0 else later(rng, first, 0.5, days * 24)
        if i % 2 == 0:
            other = payers[(i // 2) % len(payers)]
            s.label_payment(
                s.pay(
                    other,
                    acct,
                    round(amount * float(rng.uniform(0.8, 1.2)), 2),
                    moment,
                    purpose="Services",
                ),
                "burst_in",
            )
        else:
            other = payees[(i // 2) % len(payees)]
            s.label_payment(
                s.pay(
                    acct,
                    other,
                    round(amount * float(rng.uniform(0.7, 1.0)), 2),
                    moment,
                    purpose="Services",
                ),
                "burst_out",
            )


def _early(s: ScenarioCtx, acct: str, before: date) -> None:
    rng = s.rng("early", acct)
    other = _counterparties(s, before, 1)[0]
    for _ in range(int(rng.integers(1, 4))):
        s.pay(
            other,
            acct,
            uniform(rng, 50, 600),
            at(rng, before - timedelta(days=int(rng.integers(0, 20)))),
            purpose="Invoice",
        )


def _usual(s: ScenarioCtx, acct: str, until: date, days: int, monthly: float) -> None:
    """Ordinary activity at `monthly` volume over the `days` before `until` (unlabelled)."""
    rng = s.rng("usual", acct)
    others = _counterparties(s, until, 3)
    n = max(4, days // 7)
    for i in range(n):
        day = until - timedelta(days=int(rng.integers(1, days)))
        amount = round(monthly * days / 30 / n * float(rng.uniform(0.6, 1.4)), 2)
        if i % 2 == 0:
            s.pay(others[i % 3], acct, amount, at(rng, day), purpose="Invoice")
        else:
            s.pay(acct, others[i % 3], round(amount * 0.9, 2), at(rng, day), purpose="Invoice")


def _capital_flip(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("flip")
    holder = s.label(
        s.company(incorporated=start - timedelta(days=int(rng.integers(20, 81)))), "holder"
    )
    acct = s.label(
        s.account(holder, opened=start - timedelta(days=int(rng.integers(5, 15)))),
        "reactivated_account",
    )
    funders = _counterparties(s, start, int(rng.integers(2, 4)))
    total = uniform(rng, 80000, 400000)
    first = at(rng, start)
    for i, f in enumerate(funders):
        s.label_payment(
            s.pay(
                f,
                acct,
                round(total / len(funders), 2),
                later(rng, first, 0, 24) if i else first,
                purpose="Capital",
            ),
            "burst_in",
        )
    dests = _counterparties(s, start, int(rng.integers(2, 5)))
    moved = total * float(rng.uniform(0.85, 1.0))
    for d in dests:
        s.label_payment(
            s.pay(
                acct,
                d,
                round(moved / len(dests), 2),
                later(rng, first, 26, 120),
                purpose="Transfer",
            ),
            "burst_out",
        )
    s.finish(variant, difficulty, {"capital": total, "moved_share": round(moved / total, 3)})


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    if variant == "capital_flip":
        _capital_flip(s, variant, difficulty, start)
        return
    rng = s.rng("illicit")
    category = "DORMANT" if variant == "dormant_company" else ""
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 900, 6000), accounts_category=category),
        "holder",
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 600, 3000)), "reactivated_account"
    )
    gap = int(rng.integers(200, 301)) if variant == "reactivated" else int(rng.integers(150, 261))
    _early(s, acct, start - timedelta(days=gap))
    if variant == "reactivated" or rng.random() < 0.5:
        director = s.label(s.person(), "new_director")
        s.director(director, holder, start=start - timedelta(days=int(rng.integers(5, 31))))
    if variant == "reactivated":
        n, total, days = (
            int(rng.integers(6, 16)),
            uniform(rng, 50000, 300000),
            float(rng.uniform(3, 10)),
        )
    else:
        n, total, days = (
            int(rng.integers(4, 11)),
            uniform(rng, 15000, 60000),
            float(rng.uniform(3, 20)),
        )
    _burst(s, acct, start, n, total, days)
    s.finish(
        variant,
        difficulty,
        {"gap_days": gap, "burst_payments": n, "burst_total": total, "burst_days": round(days, 1)},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    if kind == "property_sale":
        holder = s.label(s.person(born=(1940, 1975)), "holder")
        acct = s.label(
            s.account(holder, opened=opened_before(rng, start, 2000, 9000)), "reactivated_account"
        )
        _early(s, acct, start - timedelta(days=int(rng.integers(200, 320))))
        solicitor = _counterparties(s, start, 3)
        moment = at(rng, start)
        s.label_payment(
            s.pay(
                solicitor[0], acct, uniform(rng, 150000, 450000), moment, purpose="Completion funds"
            ),
            "burst_in",
        )
        for dest in solicitor[1:] * 3:
            s.label_payment(
                s.pay(
                    acct,
                    dest,
                    uniform(rng, 8000, 60000),
                    later(rng, moment, 2, 240),
                    purpose="Transfer",
                ),
                "burst_out",
            )
        s.finish(kind, "", {})
        return
    sector = "tourism" if kind == "seasonal" else "manufacturing"
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 1500, 8000), sector=sector), "holder"
    )
    acct = s.label(
        s.account(holder, opened=opened_before(rng, start, 900, 5000)), "reactivated_account"
    )
    gap = int(rng.integers(170, 200)) if kind == "seasonal" else int(rng.integers(200, 260))
    total = uniform(rng, 30000, 150000)
    # the business was as busy before the quiet period as it is after it
    _usual(
        s,
        acct,
        start - timedelta(days=gap),
        120 if kind == "seasonal" else 150,
        total * float(rng.uniform(0.8, 1.5)),
    )
    if kind == "restart":
        owner = s.company(incorporated=opened_before(rng, start, 1500, 8000))
        s.owns(
            owner, holder, band="75-100", start=start - timedelta(days=int(rng.integers(10, 40)))
        )
    _burst(s, acct, start, int(rng.integers(6, 14)), total, float(rng.uniform(5, 14)))
    s.finish(kind, "", {"gap_days": gap})
