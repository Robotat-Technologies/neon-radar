"""sanctions_exposure scenarios (PHASE-3.md 7.2.5; PHASE-1.md 7.2 entry 10).

A synthetic listed entity carries the `sanction` topic and a `Sanction` record from "Synthetic
Authority A"; a listed person has an invented surname in a script the name stream chooses and the
synthetic nationality `zz`. Illicit `majority_chain` (easy): it owns 75 percent or more of a company
directly, or through one or two companies it holds more than half of; every company in the chain is
an exposed organisation (the target is the core one). Illicit `split_or_control` (hard): two listed
owners hold more than 25 percent each (the aggregate rule's case), or a listed person holds a board
appointment right, significant influence, or a directorship without owning the company. Look-alikes:
a minority stake of 20 to 40 percent two links away (`minority_stake`; the middle company is exposed
too, and an alert on it is a look-alike hit) and a listed entity holding 3 to 15 percent of a
company others hold the rest of (`diffuse_holding`), both recorded as exact shares.
"""

from __future__ import annotations

from datetime import date

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import foreign, opened_before

TYPOLOGY = "sanctions_exposure"
ILLICIT = (("majority_chain", "easy"), ("split_or_control", "hard"))
LOOKALIKES = ("minority_stake", "diffuse_holding")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _listed(s: ScenarioCtx, start: date, person: bool) -> str:
    rng = s.rng("listed")
    if person:
        entity = s.person(locale="any", nationality="zz", topics=("sanction",))
    else:
        entity = s.company(
            incorporated=opened_before(rng, start, 1000, 6000),
            jurisdiction=foreign(rng),
            topics=("sanction",),
        )
    s.sanction(entity, start=opened_before(rng, start, 100, 1500))
    return s.label(entity, "listed_owner")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    target = s.label(s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity")
    if variant == "majority_chain":
        owner = _listed(s, start, rng.random() < 0.5)
        links = int(rng.integers(1, 4))
        for i in range(links - 1):
            mid = s.label(
                s.company(
                    incorporated=opened_before(rng, start, 200, 3000), jurisdiction=foreign(rng)
                ),
                "exposed_entity",
                core=False,
            )
            s.owns(
                owner,
                mid,
                band="75-100" if i == 0 else "50-75",
                start=opened_before(rng, start, 30, 900),
            )
            owner = mid
        s.owns(owner, target, band="75-100", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"links": links})
        return
    if rng.random() < 0.5:
        a, b = _listed(s, start, False), _listed(s, start, True)
        s.owns(a, target, band="25-50", start=opened_before(rng, start, 30, 900))
        s.owns(b, target, band="25-50", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"form": "two listed owners"})
        return
    person = _listed(s, start, True)
    r = rng.random()
    if r < 0.35:
        s.control(person, target, control_type="appointment")
        form = "appointment right"
    elif r < 0.7:
        s.control(person, target, control_type="influence")
        form = "significant influence"
    else:
        s.director(person, target, start=opened_before(rng, start, 30, 900))
        form = "director"
    s.finish(variant, difficulty, {"form": form})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    target = s.label(s.company(incorporated=opened_before(rng, start, 500, 6000)), "exposed_entity")
    listed = _listed(s, start, False)
    if kind == "minority_stake":
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 500, 6000)),
            "exposed_entity",
            core=False,
        )
        s.owns(
            listed,
            mid,
            band=f"exact:{int(rng.integers(20, 40))}",
            start=opened_before(rng, start, 100, 2000),
        )
        s.owns(
            mid,
            target,
            band=f"exact:{int(rng.integers(20, 40))}",
            start=opened_before(rng, start, 100, 2000),
        )
    else:
        s.owns(
            listed,
            target,
            band=f"exact:{int(rng.integers(3, 15))}",
            start=opened_before(rng, start, 100, 2000),
        )
        for _ in range(2):
            s.owns(s.person(), target, band="25-50", start=opened_before(rng, start, 100, 2000))
    s.finish(kind, "", {})
