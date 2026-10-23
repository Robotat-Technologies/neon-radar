"""cash_commingling scenarios (PHASE-3.md 7.2.5; `typology-detection-definitions.md` 14).

Each scenario creates its own neighbourhood: five to eight ordinary businesses of one cash sector
in one postcode district (their own peer group, so the scenario works on any base), and the
business the scenario is about. Peers bank their takings on two to five days a week, Monday to
Saturday. Illicit `front_business` (easy): the business banks four to eight times its peers' cash,
some of it on Sundays, and pays most of it on to its owner and the owner's relative. Illicit
`blended_business` (hard): three to four times the peers, no Sunday deposits, about a third paid
on to the owner. Look-alikes: a busy business banking one and a half to two and a half times its
peers' cash and paying suppliers (`busy_business`) and a business that opened a second site half
way through and banks more from then on (`new_site`), both paying suppliers rather than people.
The business's cash deposits and its payments to related people are labelled; the peers are
context participants.
"""

from __future__ import annotations

from datetime import date, timedelta

from neonradar_ingest.synth.ctx import ScenarioCtx
from neonradar_ingest.synth.dates import at
from neonradar_ingest.synth.scenarios.common import lognormal, opened_before

TYPOLOGY = "cash_commingling"
ILLICIT = (("front_business", "easy"), ("blended_business", "hard"))
LOOKALIKES = ("busy_business", "new_site")
SPAN_DAYS = 120
LEAD_DAYS = 0
SECTORS = ("restaurant", "convenience store", "car wash", "hospitality")


def _area(s: ScenarioCtx) -> tuple[str, str]:
    """A postcode district of the scenario's own, and its sector."""
    rng = s.rng("area")
    return f"QQ{int(rng.integers(100, 990))}", str(rng.choice(SECTORS))


def _business(s: ScenarioCtx, district: str, sector: str, start: date) -> tuple[str, str]:
    rng = s.rng("business", str(len(s.created)))
    address = s.address(district=district)
    company = s.company(
        incorporated=opened_before(rng, start, 400, 6000), sector=sector, address=address
    )
    return company, s.account(company, opened=opened_before(rng, start, 200, 3000))


def _bank(
    s: ScenarioCtx,
    account: str,
    start: date,
    days: int,
    weekly: float,
    *,
    sundays: bool,
    label: bool,
    boost_from: date | None = None,
    boost: float = 1.0,
) -> list[str]:
    rng = s.rng("bank", account)
    per_week = int(rng.integers(2, 6))
    out = []
    for d in range(days):
        day = start + timedelta(days=d)
        if day.weekday() == 6 and not sundays:
            continue
        if rng.random() >= per_week / (7 if sundays else 6):
            continue
        amount = lognormal(
            rng,
            weekly / per_week * (boost if boost_from and day >= boost_from else 1.0),
            0.35,
            50,
            9500,
        )
        branch = s.ctx.branches[int(rng.integers(len(s.ctx.branches)))]
        p = s.pay(
            branch, account, amount, at(rng, day, 9, 17), channel="cash_deposit", purpose="Takings"
        )
        if label:
            s.label_payment(p, "deposit")
        out.append(p)
    return out


def _peers(
    s: ScenarioCtx, district: str, sector: str, start: date, days: int, weekly: float
) -> None:
    rng = s.rng("peers")
    for _ in range(int(rng.integers(5, 9))):
        company, account = _business(s, district, sector, start)
        s.label(company, "peer", core=False)
        _bank(
            s,
            account,
            start,
            days,
            weekly * float(rng.uniform(0.75, 1.3)),
            sundays=False,
            label=False,
        )


def _pay_on(
    s: ScenarioCtx,
    account: str,
    to: list[str],
    total: float,
    start: date,
    days: int,
    *,
    label: bool,
) -> None:
    rng = s.rng("onward", account)
    months = max(1, days // 30)
    for m in range(months):
        moment = at(rng, start + timedelta(days=30 * m + 27), 10, 15)
        for i, dst in enumerate(to):
            p = s.pay(
                account,
                dst,
                round(total / months / len(to) * (1.1 if i == 0 else 0.9), 2),
                moment,
                purpose="Transfer",
            )
            if label:
                s.label_payment(p, "related_party")


def illicit(s: ScenarioCtx, variant: str, difficulty: str, start: date) -> None:
    rng = s.rng("illicit")
    district, sector = _area(s)
    days = SPAN_DAYS
    weekly = float(rng.uniform(1500, 4000))
    _peers(s, district, sector, start, days, weekly)
    company, account = _business(s, district, sector, start)
    s.label(company, "business")
    s.label(account, "receiving_account")
    easy = variant == "front_business"
    ratio = float(rng.uniform(4, 8)) if easy else float(rng.uniform(3.2, 4))
    deposits = _bank(s, account, start, days, weekly * ratio, sundays=easy, label=True)
    owner = s.label(s.person(), "owner", core=False)
    s.owns(owner, company, band="75-100", start=opened_before(rng, start, 300, 3000))
    s.director(owner, company, start=opened_before(rng, start, 300, 3000))
    relative = s.label(s.person(), "relative", core=False)
    s.family(owner, relative, "spouse")
    targets = [
        s.account(owner, opened=opened_before(rng, start, 300, 3000)),
        s.account(relative, opened=opened_before(rng, start, 300, 3000)),
    ]
    banked = sum(float(s.ctx.record(p)["properties"]["amount"][0]) for p in deposits)
    _pay_on(s, account, targets, banked * (0.7 if easy else 0.33), start, days, label=True)
    s.finish(
        variant,
        difficulty,
        {"district": district, "sector": sector, "ratio": round(ratio, 2)},
        {"peer_ratio_at_least": 3.0},
    )


def lookalike(s: ScenarioCtx, kind: str, start: date) -> None:
    rng = s.rng("lookalike")
    district, sector = _area(s)
    days = SPAN_DAYS
    weekly = float(rng.uniform(1500, 4000))
    _peers(s, district, sector, start, days, weekly)
    company, account = _business(s, district, sector, start)
    s.label(company, "business")
    s.label(account, "receiving_account")
    if kind == "busy_business":
        deposits = _bank(
            s,
            account,
            start,
            days,
            weekly * float(rng.uniform(1.5, 2.5)),
            sundays=False,
            label=True,
        )
    else:
        deposits = _bank(
            s,
            account,
            start,
            days,
            weekly * 1.3,
            sundays=False,
            label=True,
            boost_from=start + timedelta(days=days // 2),
            boost=2.0,
        )
    supplier = s.company(incorporated=opened_before(rng, start, 1000, 6000), sector="wholesale")
    supplier_account = s.account(supplier, opened=opened_before(rng, start, 500, 4000))
    banked = sum(float(s.ctx.record(p)["properties"]["amount"][0]) for p in deposits)
    _pay_on(s, account, [supplier_account], banked * 0.6, start, days, label=False)
    s.finish(kind, "", {"district": district, "sector": sector})
