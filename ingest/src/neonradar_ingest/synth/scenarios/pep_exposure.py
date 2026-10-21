"""pep_exposure scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 13).

A synthetic politically exposed person carries the `role.pep` topic and holds a synthetic public
office (`Position` with an `Occupancy`) in a synthetic country (`zz`) or, for some, in `gb`. The
PEP, the relatives and the associates have invented surnames.
Illicit `family_vehicle` (easy): the PEP is in office and a spouse, child or parent owns 75 percent
or more of a company, which owns a second company (both exposed; the first is the core one).
Illicit `associate_vehicle` (hard): a business partner of the PEP (ASSOCIATE_OF) holds more than
half of a company through two intermediate companies, three links in all. Look-alikes: a PEP who
left office 18 to 36 months ago and whose spouse owns a company (`former_pep`: family measures end
with the office, MLR 2017 reg 35(11)) and a cousin of a PEP in office who owns a company
(`distant_relative`: cousins are outside the family members the regulations name).
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.scenarios.common import foreign, opened_before

TYPOLOGY = "pep_exposure"
ILLICIT = (("family_vehicle", "easy"), ("associate_vehicle", "hard"))
LOOKALIKES = ("former_pep", "distant_relative")
SPAN_DAYS = 1
LEAD_DAYS = 0


def _pep(s: ScenarioCtx, start: date, *, left_months: int = 0) -> str:
    rng = s.rng("pep")
    pep = s.label(s.person(locale="any", born=(1950, 1980), topics=("role.pep",)), "pep")
    country = "gb" if rng.random() < 0.3 else "zz"
    post = s.position(
        f"Synthetic Minister of Department {int(rng.integers(1, 40))}", country=country
    )
    began = opened_before(rng, start, 400, 3000)
    ended = start - timedelta(days=30 * left_months) if left_months else None
    s.occupancy(pep, post, start=began, end=ended)
    return pep


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    pep = _pep(s, start)
    if variant == "family_vehicle":
        relation = str(rng.choice(["spouse", "child", "parent"]))
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, relation)
        first = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity"
        )
        second = s.label(
            s.company(incorporated=opened_before(rng, start, 100, 3000)),
            "exposed_entity",
            core=False,
        )
        s.owns(relative, first, band="75-100", start=opened_before(rng, start, 30, 900))
        s.owns(first, second, band="50-75", start=opened_before(rng, start, 30, 900))
        s.finish(variant, difficulty, {"relationship": relation})
        return
    partner = s.label(s.person(invented=True), "associate")
    s.associate(pep, partner, "business partner")
    owner = partner
    for i in range(2):
        mid = s.label(
            s.company(incorporated=opened_before(rng, start, 200, 4000), jurisdiction=foreign(rng)),
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
    target = s.label(s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity")
    s.owns(owner, target, band="50-75", start=opened_before(rng, start, 30, 900))
    s.finish(variant, difficulty, {"links": 3})


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    if kind == "former_pep":
        pep = _pep(s, start, left_months=int(rng.integers(18, 37)))
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, "spouse")
    else:
        pep = _pep(s, start)
        relative = s.label(s.person(invented=True), "relative")
        s.family(pep, relative, "cousin")
    company = s.label(
        s.company(incorporated=opened_before(rng, start, 100, 3000)), "exposed_entity"
    )
    s.owns(relative, company, band="75-100", start=opened_before(rng, start, 30, 900))
    s.finish(kind, "", {})
