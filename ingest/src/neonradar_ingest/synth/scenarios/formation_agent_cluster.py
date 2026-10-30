"""formation_agent_cluster scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 11).

Illicit `agent_factory` (easy): one agent represents 12 to 30 companies incorporated within three
weeks, most registered at the agent's own address, with two or three nominee directors shared
across them and payments between a few of them. Illicit `spread_agent` (hard): 12 to 18 companies
incorporated over 20 to 40 days, with two directors shared across about half of them, so some
bursts fall below ten companies within 30 days. Look-alikes: a busy lawful formation
agent with 40 to 80 clients formed over years, each with its own directors (`busy_agent`), and a
corporate group of 10 to 14 companies formed in one week by an agent, owned by one holding company
and sharing the group's two directors (`group_formation`, which the detector does flag: the shape
is the same).
"""

from __future__ import annotations

from datetime import date, timedelta
from itertools import pairwise

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at, later
from neonradar_ingest.synth.scenarios.common import opened_before, uniform

TYPOLOGY = "formation_agent_cluster"
ILLICIT = (("agent_factory", "easy"), ("spread_agent", "hard"))
LOOKALIKES = ("busy_agent", "group_formation")
SPAN_DAYS = 45
LEAD_DAYS = 0


def _agent(s: ScenarioCtx, start: date) -> tuple[str, str]:
    rng = s.rng("agent")
    office = s.address()
    agent = s.company(
        incorporated=opened_before(rng, start, 1500, 8000), sector="services", address=office
    )
    return s.label(agent, "agent"), office


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    agent, office = _agent(s, start)
    easy = variant == "agent_factory"
    n = int(rng.integers(12, 31)) if easy else int(rng.integers(12, 19))
    spread = 21 if easy else int(rng.integers(20, 41))
    clients = []
    for _ in range(n):
        at_office = rng.random() < (0.8 if easy else 0.4)
        client = s.company(
            incorporated=start - timedelta(days=int(rng.integers(0, spread + 1))),
            address=office if at_office else s.address(),
        )
        s.label(client, "client")
        s.represents(agent, client)
        clients.append(client)
    officers = [
        s.label(s.person(), "shared_officer") for _ in range(int(rng.integers(2, 4)) if easy else 2)
    ]
    share = 0.8 if easy else 0.5
    for i, client in enumerate(clients):
        if rng.random() < share:
            s.director(
                officers[i % len(officers)],
                client,
                start=opened_before(rng, start, 0, 10),
                nominee=easy,
            )
        else:
            s.director(s.person(), client, start=opened_before(rng, start, 0, 10))
    if easy:
        accounts = [s.account(c, opened=opened_before(rng, start, 0, 10)) for c in clients[:4]]
        moment = at(rng, start + timedelta(days=10))
        for a, b in pairwise(accounts):
            s.pay(
                a, b, uniform(rng, 15000, 90000), later(rng, moment, 1, 240), purpose="Consultancy"
            )
    s.finish(
        variant,
        difficulty,
        {"clients": n, "spread_days": spread, "shared_officers": len(officers)},
        {"incorporated_in_burst": n if easy else None},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    agent, office = _agent(s, start)
    if kind == "busy_agent":
        n = int(rng.integers(40, 81))
        for _ in range(n):
            client = s.company(
                incorporated=start - timedelta(days=int(rng.integers(30, 4000))),
                address=office if rng.random() < 0.5 else s.address(),
            )
            s.represents(agent, client)
            s.director(s.person(), client, start=opened_before(rng, start, 30, 3000))
        s.finish(kind, "", {"clients": n})
        return
    n = int(rng.integers(10, 15))
    holding = s.label(
        s.company(incorporated=opened_before(rng, start, 400, 4000), sector="holding"), "client"
    )
    s.owns(s.person(), holding, band="75-100")  # a group with a person at the top
    directors = [s.label(s.person(), "shared_officer") for _ in range(2)]
    s.represents(agent, holding)
    for _ in range(n):
        sub = s.label(
            s.company(incorporated=start - timedelta(days=int(rng.integers(0, 7))), address=office),
            "client",
        )
        s.represents(agent, sub)
        s.owns(holding, sub, band="75-100", start=start)
        for d in directors:
            s.director(d, sub, start=start)
    s.finish(kind, "", {"subsidiaries": n})
