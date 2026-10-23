"""structuring scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 1).

Illicit `single_account` (easy): 4 to 8 cash deposits of 9,100 to 9,980 into one account within 1
to 4 days, at 2 to 4 branches. Illicit `multi_account` (hard): 4 to 9 deposits of 8,600 to 9,990
spread over 2 or 3 accounts of one holder within 2 to 7 days, so some fall outside a 10 percent
band or a 4-day window. Look-alikes: a cash business banking its takings (`daily_takings`), a
business whose insurer caps each deposit at 9,500 (`deposit_cap`), a person saving 9,500 a week
(`weekly_savings`).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, business_days, later, utc
from neonradar_ingest.synth.scenarios.common import camouflage, lognormal, opened_before, uniform

TYPOLOGY = "structuring"
ILLICIT = (("single_account", "easy"), ("multi_account", "hard"))
LOOKALIKES = ("daily_takings", "deposit_cap", "weekly_savings")
SPAN_DAYS = 40
LEAD_DAYS = 0


def _holder(s: ScenarioCtx, start: date, person: bool) -> str:
    if person:
        return s.person()
    return s.company(incorporated=opened_before(s.rng("inc"), start, 400, 4000), sector="wholesale")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    holder = s.label(_holder(s, start, rng.random() < 0.5), "holder")
    n_accounts = 1 if variant == "single_account" else int(rng.integers(2, 4))
    accounts = [
        s.label(s.account(holder, opened=opened_before(rng, start, 200, 3000)), "receiving_account")
        for _ in range(n_accounts)
    ]
    branches = s.ctx.branches
    n = int(rng.integers(4, 9)) if variant == "single_account" else int(rng.integers(4, 10))
    span = int(rng.integers(1, 5)) if variant == "single_account" else int(rng.integers(2, 8))
    low, high = (9100, 9980) if variant == "single_account" else (8600, 9990)
    first = at(rng, start, 9, 12)
    for i in range(n):
        moment = first if i == 0 else later(rng, first, 0.2, span * 24)
        branch = branches[int(rng.integers(min(len(branches), 4)))]
        account = accounts[i % n_accounts]
        p = s.pay(
            branch,
            account,
            uniform(rng, low, high),
            moment,
            channel="cash_deposit",
            purpose="Cash deposit",
        )
        s.label_payment(p, "deposit")
    for a in accounts:
        camouflage(
            s,
            a,
            utc(start.year, start.month, start.day) - timedelta(days=60),
            utc(start.year, start.month, start.day),
        )
    s.finish(
        variant,
        difficulty,
        {"deposits": n, "span_days": span, "accounts": n_accounts, "amount_range": [low, high]},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    branches = s.ctx.branches
    if kind == "weekly_savings":
        holder = s.label(s.person(), "holder")
        account = s.label(
            s.account(holder, opened=opened_before(rng, start, 300, 3000)), "receiving_account"
        )
        for week in range(5):
            day = start + timedelta(days=7 * week)
            p = s.pay(
                branches[0],
                account,
                9500.0,
                at(rng, day),
                channel="cash_deposit",
                purpose="Savings",
            )
            s.label_payment(p, "deposit")
        s.finish(kind, "", {"weeks": 5})
        return
    holder = s.label(
        s.company(incorporated=opened_before(rng, start, 800, 6000), sector="retail"), "holder"
    )
    account = s.label(
        s.account(holder, opened=opened_before(rng, start, 300, 3000)), "receiving_account"
    )
    days = business_days(start, start + timedelta(days=30))
    step = 0
    for i, day in enumerate(days):
        if kind == "deposit_cap" and i % 2 == 1:
            continue
        amount = (
            lognormal(rng, 4200, 0.6, 300, 18000)
            if kind == "daily_takings"
            else uniform(rng, 9000, 9500)
        )
        step += 1
        p = s.pay(
            branches[step % min(2, len(branches))],
            account,
            amount,
            at(rng, day, 16, 18),
            channel="cash_deposit",
            purpose="Takings",
        )
        s.label_payment(p, "deposit")
    s.finish(kind, "", {"days": len(days)})
