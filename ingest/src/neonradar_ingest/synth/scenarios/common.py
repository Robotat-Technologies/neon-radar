"""Helpers shared by the scenario modules (PHASE-3.md 7.2.5)."""

from __future__ import annotations

from datetime import date, datetime, timedelta

import numpy as np

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, business_days

FOREIGN = ("vg", "cy", "ae", "pa", "sc", "bz", "mt", "hk")


def lognormal(
    rng: np.random.Generator, median: float, sigma: float, low: float, high: float
) -> float:
    """A lognormal amount around `median`, kept inside [low, high], rounded to pennies."""
    value = float(median * np.exp(sigma * rng.standard_normal()))
    return round(min(high, max(low, value)), 2)


def uniform(rng: np.random.Generator, low: float, high: float) -> float:
    return round(float(rng.uniform(low, high)), 2)


def opened_before(rng: np.random.Generator, day: date, min_days: int, max_days: int) -> date:
    return day - timedelta(days=int(rng.integers(min_days, max_days + 1)))


def camouflage(
    s: ScenarioCtx, account: str, start: datetime, end: datetime, n: int = 4, median: float = 600.0
) -> None:
    """A few ordinary payments in and out of `account` with two counterparties the scenario owns,
    spread over [start, end), so a scenario account is not an account with nothing else on it.
    They carry no label: they are background as far as the evaluation knows."""
    rng = s.rng("camouflage", account)
    start, end = max(start, s.period.start), min(end, s.period.end)
    if end - start < timedelta(days=2):
        return
    people = [
        s.account(s.person(), opened=opened_before(rng, start.date(), 400, 3000)) for _ in range(2)
    ]
    days = business_days(start.date(), end.date())
    if not days:
        return
    for i in range(n):
        day = days[int(rng.integers(len(days)))]
        moment = at(rng, day)
        amount = lognormal(rng, median, 0.5, 20, 5000)
        other = people[i % 2]
        if i % 2 == 0:
            s.pay(other, account, amount, moment, channel="wire", purpose="Invoice")
        else:
            s.pay(account, other, amount, moment, channel="card", purpose="Purchase")


def foreign(rng: np.random.Generator) -> str:
    return FOREIGN[int(rng.integers(len(FOREIGN)))]
