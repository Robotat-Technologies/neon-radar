"""shell_chain scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 8).

Illicit `layered` (easy): a person, or a company with no recorded owner, owns a chain of 3 to 5
companies in 2 to 4 jurisdictions; one link has a nominee owner or a chain company has a nominee
director, and a professional director with 12 to 25 other appointments sits on one of them.
Illicit `loop` (hard): three or four companies in two or more jurisdictions own each other in a
loop, or a chain of only two companies, which falls below a three-layer rule. Look-alikes: a lawful
group holding structure with ordinary directors (`group_holding`), and a fund vehicle whose
directors are professional directors (`fund_vehicle`).
"""

from __future__ import annotations

from datetime import date

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import FOREIGN, opened_before

TYPOLOGY = "shell_chain"
ILLICIT = (("layered", "easy"), ("loop", "hard"))
LOOKALIKES = ("group_holding", "fund_vehicle")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _jurisdictions(s: ScenarioCtx, n: int, distinct: int) -> list[str]:
    rng = s.rng("jurisdictions")
    pool = ["gb", *FOREIGN]
    picked = [pool[0]] + [
        pool[1 + int(i)] for i in rng.choice(len(pool) - 1, size=distinct - 1, replace=False)
    ]
    return [picked[i % distinct] for i in range(n)]


def _professional(s: ScenarioCtx, start: date, appointments: int) -> str:
    rng = s.rng("professional")
    pro = s.person(locale="en_GB", nationality="je")
    for _ in range(appointments):
        client = s.company(incorporated=opened_before(rng, start, 200, 4000), jurisdiction="je")
        s.director(pro, client, start=opened_before(rng, start, 30, 1500))
    return pro


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    if variant == "loop" and rng.random() < 0.4:
        # two layers only: present, but below the three-layer rule
        top = s.label(s.person(), "top_owner")
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 1500), jurisdiction="vg"), "layer"
        )
        leaf = s.label(s.company(incorporated=opened_before(rng, start, 50, 900)), "owned_company")
        s.owns(top, mid, band="75-100", start=opened_before(rng, start, 30, 900))
        s.owns(mid, leaf, band="75-100", start=opened_before(rng, start, 20, 800), nominee=True)
        s.finish(variant, difficulty, {"layers": 2})
        return
    if variant == "loop":
        n = int(rng.integers(3, 5))
        places = _jurisdictions(s, n, 2)
        companies = [
            s.company(incorporated=opened_before(rng, start, 100, 2000), jurisdiction=j)
            for j in places
        ]
        for i, c in enumerate(companies):
            s.label(c, "layer" if i else "owned_company")
            s.owns(
                c, companies[(i + 1) % n], band="50-75", start=opened_before(rng, start, 20, 900)
            )
        s.finish(variant, difficulty, {"layers": n, "loop": True})
        return
    n = int(rng.integers(3, 6))
    places = _jurisdictions(s, n, int(rng.integers(2, min(4, n) + 1)))
    if rng.random() < 0.5:
        top = s.label(s.person(nationality="cy"), "top_owner")
    else:
        top = s.label(
            s.company(incorporated=opened_before(rng, start, 500, 4000), jurisdiction="pa"),
            "top_owner",
        )
    companies = [
        s.company(incorporated=opened_before(rng, start, 60, 1500), jurisdiction=j)
        for j in reversed(places)
    ]
    owner = top
    nominee_at = int(rng.integers(n))
    for i, c in enumerate(companies):
        s.label(c, "owned_company" if i == n - 1 else "layer")
        s.owns(
            owner,
            c,
            band="75-100",
            start=opened_before(rng, start, 20, 900),
            nominee=(i == nominee_at and rng.random() < 0.5),
        )
        owner = c
    nominee = s.label(s.person(), "nominee")
    s.director(
        nominee, companies[nominee_at], start=opened_before(rng, start, 20, 900), nominee=True
    )
    pro = s.label(_professional(s, start, int(rng.integers(12, 26))), "professional_director")
    s.director(pro, companies[int(rng.integers(n))], start=opened_before(rng, start, 20, 900))
    s.finish(variant, difficulty, {"layers": n, "jurisdictions": len(set(places))})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    n = int(rng.integers(3, 5))
    places = ["gb", "ie", "gb", "nl"][:n]
    top = s.label(
        s.person()
        if kind == "group_holding"
        else s.company(incorporated=opened_before(rng, start, 2000, 8000), jurisdiction="lu"),
        "top_owner",
    )
    owner = top
    companies = []
    for i in range(n):
        c = s.label(
            s.company(incorporated=opened_before(rng, start, 400, 6000), jurisdiction=places[i]),
            "owned_company" if i == n - 1 else "layer",
        )
        s.owns(owner, c, band="75-100", start=opened_before(rng, start, 100, 3000))
        companies.append(c)
        owner = c
    if kind == "fund_vehicle":
        pro = s.label(_professional(s, start, int(rng.integers(15, 40))), "professional_director")
        s.director(pro, companies[0], start=opened_before(rng, start, 100, 2000))
    else:
        for c in companies:
            s.director(s.person(), c, start=opened_before(rng, start, 100, 2000))
    s.finish(kind, "", {"layers": n})
