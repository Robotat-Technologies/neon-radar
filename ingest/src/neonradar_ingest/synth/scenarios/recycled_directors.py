"""recycled_directors scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 12).

Illicit `strawman` (easy): one person is appointed director of 12 to 20 unrelated new companies,
eight or more within a month, resigns from some within three months, and a few of the companies pay
each other. Illicit `slow_strawman` (hard): 8 to 13 unrelated companies over four to eight months
and no payments, so the counts sit near the thresholds ("small numbers can matter": ten nominees,
25 companies in FATF PML Box 10). Look-alikes: a professional director of 12 to 25 fund companies
in fund jurisdictions with long tenures (`fund_director`, which the detector flags: the shape is
the same) and the director of a group's 12 to 20 subsidiaries (`group_director`, one group).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "recycled_directors"
ILLICIT = (("strawman", "easy"), ("slow_strawman", "hard"))
LOOKALIKES = ("fund_director", "group_director")
SPAN_DAYS = 240
LEAD_DAYS = 0


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    director = s.label(s.person(), "director")
    easy = variant == "strawman"
    n = int(rng.integers(12, 21)) if easy else int(rng.integers(8, 14))
    companies = []
    for i in range(n):
        offset = (
            int(rng.integers(0, 30))
            if easy and i < 8
            else int(rng.integers(0, 120 if easy else 240))
        )
        appointed = start + timedelta(days=offset)
        company = s.label(
            s.company(incorporated=appointed - timedelta(days=int(rng.integers(0, 5)))),
            "company",
            core=False,
        )
        resigned = (
            appointed + timedelta(days=int(rng.integers(30, 90)))
            if easy and rng.random() < 0.3
            else None
        )
        s.director(director, company, start=appointed, end=resigned)
        companies.append(company)
    if easy:
        accounts = [s.account(c, opened=start) for c in companies[:4]]
        moment = at(rng, start + timedelta(days=35))
        for a, b in pairwise(accounts):
            s.pay(a, b, uniform(rng, 10000, 60000), later(rng, moment, 1, 300), purpose="Services")
    s.finish(variant, difficulty, {"companies": n})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    director = s.label(s.person(), "director")
    if kind == "fund_director":
        for _ in range(int(rng.integers(12, 26))):
            fund = s.company(
                incorporated=opened_before(rng, start, 400, 5000),
                jurisdiction=str(rng.choice(["je", "gg", "ky", "lu"])),
                sector="fund",
            )
            s.director(director, fund, start=opened_before(rng, start, 200, 3000))
        s.finish(kind, "", {})
        return
    parent = s.company(incorporated=opened_before(rng, start, 2000, 8000), sector="holding")
    s.owns(s.person(), parent, band="75-100")  # a group with a person at the top
    s.director(director, parent, start=opened_before(rng, start, 500, 3000))
    for _ in range(int(rng.integers(12, 21))):
        sub = s.company(incorporated=opened_before(rng, start, 100, 3000))
        s.owns(parent, sub, band="75-100")
        s.director(director, sub, start=opened_before(rng, start, 50, 2000))
    s.finish(kind, "", {})
