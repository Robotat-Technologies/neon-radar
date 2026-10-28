"""mass_registration_address scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 9).

Illicit `factory` (easy): 25 to 60 companies registered at one address, most incorporated within
a month, two or three nominee directors shared across many of them, and payments between some of
them. Illicit `quiet_factory` (hard): 18 to 30 companies, spread over a year, one shared director,
no payments, so some fall below a 20-company rule. Look-alikes: a registered agent's address with
30 to 120 ordinary clients incorporated over many years (`registered_agent`) and a serviced office
(`serviced_office`).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "mass_registration_address"
ILLICIT = (("factory", "easy"), ("quiet_factory", "hard"))
LOOKALIKES = ("registered_agent", "serviced_office")
SPAN_DAYS = 30
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    address = s.label(s.address(), "registered_address")
    easy = variant == "factory"
    n = int(rng.integers(25, 61)) if easy else int(rng.integers(18, 31))
    spread = 30 if easy else 365
    companies = []
    for i in range(n):
        incorporated = start - timedelta(
            days=int(rng.integers(0, spread)) + (0 if easy or i % 3 else 400)
        )
        companies.append(s.label(s.company(incorporated=incorporated, address=address), "member"))
    directors = [
        s.label(s.person(), "shared_director")
        for _ in range(int(rng.integers(2, 4)) if easy else 1)
    ]
    for i, c in enumerate(companies):
        if rng.random() < (0.7 if easy else 0.3):
            s.director(
                directors[i % len(directors)],
                c,
                start=opened_before(rng, start, 0, 30),
                nominee=easy,
            )
    if easy:
        accounts = [
            s.account(c, opened=opened_before(rng, start, 0, 20))
            for c in companies[: max(4, n // 5)]
        ]
        moment = at(rng, start + timedelta(days=5))
        for a, b in pairwise(accounts):
            s.pay(a, b, uniform(rng, 20000, 150000), later(rng, moment, 1, 200), purpose="Services")
    s.finish(variant, difficulty, {"companies": n})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    address = s.label(s.address(), "registered_address")
    n = int(rng.integers(30, 121)) if kind == "registered_agent" else int(rng.integers(20, 41))
    for _ in range(n):
        c = s.company(
            incorporated=start - timedelta(days=int(rng.integers(30, 7000))), address=address
        )
        s.director(s.person(), c, start=opened_before(rng, start, 30, 3000))
    s.finish(kind, "", {"companies": n})
