"""The synthetic register of generator v1 (PHASE-3.md 7.2.6).

A world stands in for the register on synthetic profiles: companies with sectors, incorporation
dates, a few dissolved and a few filed as dormant; people; addresses, including registered agents'
and serviced offices' addresses that host many companies; ownership as Companies House bands, with
corporate groups (some with a foreign top company, some with no recorded owner); directors,
including professional directors with many appointments; family links; formation agents; and a few
synthetic list entries, two of them holding small stakes in ordinary companies; and a few
politically exposed people holding synthetic offices, with no links (exposure is planted only by
the overlay's scenarios, so the evaluation can count it). Addresses fall in `districts` postcode
districts, so businesses of one sector have local peers. It plants no scenario: worlds carry no
labels, and every pattern found in a world alone is background.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

import numpy as np

from neonradar_ingest.synth import records as rec
from neonradar_ingest.synth.ctx import NameSource, letter, name_key
from neonradar_ingest.synth.streams import stream

SECTORS = (
    ("services", 0.22),
    ("construction", 0.12),
    ("retail", 0.10),
    ("wholesale", 0.08),
    ("manufacturing", 0.07),
    ("hospitality", 0.06),
    ("restaurant", 0.05),
    ("real estate", 0.08),
    ("transport", 0.05),
    ("technology", 0.08),
    ("tourism", 0.02),
    ("car wash", 0.01),
    ("convenience store", 0.02),
    ("holding", 0.04),
)
PARENT_PLACES = ("gb", "gb", "gb", "ie", "nl", "lu", "je", "gg", "us", "de", "cy", "vg")


@dataclass(frozen=True, slots=True)
class WorldConfig:
    companies: int = 600
    people: int = 900
    today: date = date(2026, 7, 1)
    agent_every: int = 300
    professional_every: int = 200
    dissolved_share: float = 0.05
    dormant_share: float = 0.08
    corporate_owner_share: float = 0.15
    parent_owner_share: float = 0.85
    no_owner_share: float = 0.06
    listed: int = 6
    peps: int = 4
    districts: int = 30


class _W:
    def __init__(self, seed: int, names: NameSource) -> None:
        self.seed = seed
        self.names = names
        self.records: list[dict[str, Any]] = []
        self.used: set[str] = set()
        self.counts: dict[str, int] = {}

    def company_name(self, rid: str, jurisdiction: str, suffix: str = "") -> str:
        """A company name not used before, drawn from the record's own name stream."""
        rng = self.names_rng(rid)
        return str(
            self.unique(
                lambda: self.names.company(rng, jurisdiction).replace(" Ltd", suffix or " Ltd")
            )
        )

    def person_names(self, rid: str, locale: str) -> tuple[list[str], str]:
        rng = self.names_rng(rid)
        names, gender = self.unique(lambda: self.names.person(rng, locale))
        return list(names), str(gender)

    def names_rng(self, rid: str) -> np.random.Generator:
        """The stream names of record `rid` come from: separate from the structure's stream, so a
        different name source changes names only, never ids, links, amounts or dates."""
        return stream(self.seed, "world", "name", rid)

    def rid(self, kind: str) -> str:
        self.counts[kind] = self.counts.get(kind, 0) + 1
        return f"syn-w-{kind}-{self.counts[kind]:06d}"

    def unique(self, make: Any, attempts: int = 100) -> Any:
        """A name not used yet when one turns up within `attempts` draws, else a repeat (as
        `Ctx._unique`); only the name stream moves."""
        value = make()
        for _ in range(attempts):
            names = value[0] if isinstance(value, tuple) else [value]
            keys = [name_key(n) for n in names]
            if not any(k in self.used for k in keys):
                break
            value = make()
        names = value[0] if isinstance(value, tuple) else [value]
        self.used.update(name_key(n) for n in names)
        return value


def generate(seed: int, cfg: WorldConfig, names: NameSource) -> list[dict[str, Any]]:
    w = _W(seed, names)
    rng = stream(seed, "world")
    today = cfg.today

    # addresses: a few agents' and serviced offices' addresses host many companies
    n_agents = max(2, cfg.companies // cfg.agent_every)
    hubs = []
    for i in range(n_agents + 1):
        a = _address(w, rng, cfg.districts)
        hubs.append((a, int(rng.integers(25, 150)) if i < n_agents else int(rng.integers(15, 40))))
    # companies
    sectors, weights = zip(*SECTORS, strict=True)
    p = np.array(weights) / sum(weights)
    companies: list[str] = []
    info: dict[str, dict[str, Any]] = {}
    hub_slots = [a for a, k in hubs for _ in range(k)]
    rng.shuffle(hub_slots)
    for i in range(cfg.companies):
        sector = sectors[int(rng.choice(len(sectors), p=p))]
        age = min(60 * 365, int(rng.exponential(9 * 365)))
        if rng.random() < 0.1:
            age = int(rng.integers(30, 365))
        inc = today - timedelta(days=age)
        address = hub_slots[i] if i < len(hub_slots) else _address(w, rng, cfg.districts)
        dissolved = rng.random() < cfg.dissolved_share and age > 400
        rid = w.rid("co")
        name = w.company_name(rid, "gb")
        record = rec.company(
            rid,
            name,
            jurisdiction="gb",
            registration_number=f"SY{6 + i // 100000}{i % 100000:05d}",
            incorporation_date=inc.isoformat(),
            addresses={address: "registered"},
            sector=sector,
            status="dissolved" if dissolved else "active",
            dissolution_date=(today - timedelta(days=int(rng.integers(10, 300)))).isoformat()
            if dissolved
            else "",
        )
        if rng.random() < cfg.dormant_share:
            record["nr"]["accounts_category"] = "DORMANT"
        w.records.append(record)
        companies.append(rid)
        info[rid] = {"incorporated": inc, "sector": sector}
    # people
    people = []
    for _ in range(cfg.people):
        r = rng.random()
        locale, nationality = (
            ("ar_SA", "sa") if r < 0.1 else (("ru_RU", "ru") if r < 0.2 else ("en_GB", "gb"))
        )
        pid = w.rid("p")
        spellings, gender = w.person_names(pid, locale)
        year = int(rng.integers(1945, 2001))
        w.records.append(
            rec.person(
                pid,
                spellings,
                birth_date=f"{year}-{int(rng.integers(1, 13)):02d}",
                nationality=nationality,
                gender=gender,
            )
        )
        people.append(pid)
    # ownership: people, corporate parents (some abroad), or nobody recorded
    parents: list[str] = []
    for idx, co in enumerate(companies):
        r = rng.random()
        start = info[co]["incorporated"].isoformat()
        if r < cfg.no_owner_share:
            continue
        if r < cfg.no_owner_share + cfg.corporate_owner_share and idx > 10:
            if parents and rng.random() < 0.5:
                parent = parents[int(rng.integers(len(parents)))]
            else:
                parent = _parent(w, rng, today, names, people, cfg.parent_owner_share)
                parents.append(parent)
            w.records.append(
                rec.ownership(w.rid("own"), parent, co, band="75-100", start_date=start)
            )
            continue
        if rng.random() < 0.7:
            w.records.append(
                rec.ownership(
                    w.rid("own"),
                    people[int(rng.integers(len(people)))],
                    co,
                    band="75-100",
                    start_date=start,
                )
            )
        else:
            for owner in rng.choice(len(people), size=2, replace=False):
                w.records.append(
                    rec.ownership(
                        w.rid("own"), people[int(owner)], co, band="25-50", start_date=start
                    )
                )
    # directors, and professional directors with many appointments
    pros = [
        people[int(i)]
        for i in rng.choice(
            len(people), size=max(2, cfg.companies // cfg.professional_every), replace=False
        )
    ]
    for co in companies:
        start = (info[co]["incorporated"] + timedelta(days=int(rng.integers(0, 30)))).isoformat()
        for _ in range(int(rng.integers(1, 4))):
            w.records.append(
                rec.directorship(
                    w.rid("dir"), people[int(rng.integers(len(people)))], co, start_date=start
                )
            )
    for pro in pros:
        for co in rng.choice(len(companies), size=int(rng.integers(10, 30)), replace=False):
            w.records.append(
                rec.directorship(
                    w.rid("dir"),
                    pro,
                    companies[int(co)],
                    start_date=(today - timedelta(days=int(rng.integers(30, 4000)))).isoformat(),
                )
            )
    # family links
    for _ in range(cfg.people // 20):
        a, b = rng.choice(len(people), size=2, replace=False)
        w.records.append(
            rec.family(
                w.rid("fam"),
                people[int(a)],
                people[int(b)],
                relationship=str(rng.choice(["spouse", "sibling", "child"])),
            )
        )
    # formation agents represent many of the companies at their address
    by_address: dict[str, list[str]] = {}
    for record in w.records:
        if record["schema"] == "Company":
            for a in record["properties"].get("addressEntity", []):
                by_address.setdefault(a, []).append(record["id"])
    for a, _ in hubs[:n_agents]:
        agent = w.rid("org")
        agent_name = w.company_name(agent, "gb", " Formations Ltd")
        w.records.append(rec.organization(agent, agent_name, country="gb"))
        for co in by_address.get(a, []):
            if rng.random() < 0.5:
                w.records.append(rec.representation(w.rid("rep"), agent, co))
    # synthetic list entries: most unconnected, two with small stakes in ordinary companies
    for i in range(cfg.listed):
        entity = w.rid("lst")
        w.records.append(
            rec.company(
                entity,
                w.company_name(entity, "ae"),
                jurisdiction="ae",
                registration_number=f"SL{i:06d}",
                incorporation_date="2010-01-01",
                topics=["sanction"],
            )
        )
        w.records.append(
            rec.sanction(
                w.rid("san"),
                entity,
                authority="Synthetic Authority A",
                program="Synthetic Programme 1",
                start_date="2022-03-01",
            )
        )
        if i < 2:
            target = companies[int(rng.integers(len(companies)))]
            w.records.append(
                rec.ownership(
                    w.rid("own"), entity, target, band=f"exact:{int(rng.integers(5, 20))}"
                )
            )
    for i in range(cfg.peps):
        pid = w.rid("p")
        names_rng = w.names_rng(pid)  # PEP personas carry invented surnames (2.9, 7.2.3)
        spellings, gender = w.unique(lambda r=names_rng: w.names.invented_person(r, "en_GB"))
        w.records.append(
            rec.person(
                pid,
                spellings,
                birth_date="1961-04",
                nationality="gb",
                gender=gender,
                topics=["role.pep"],
            )
        )
        post = w.rid("pos")
        w.records.append(rec.position(post, f"Synthetic Member of Assembly {i + 1}", country="zz"))
        w.records.append(rec.occupancy(w.rid("occ"), pid, post, start_date="2021-05-01"))
    return sorted(w.records, key=lambda r: r["id"])


def _address(w: _W, rng: np.random.Generator, districts: int) -> str:
    rid = w.rid("addr")
    district = int(rng.integers(1, districts + 1))
    town = w.names.town(stream(w.seed, "world", "town", str(district)))
    postcode = f"QQ{district} {int(rng.integers(1, 9))}{letter(rng)}{letter(rng)}"
    w.records.append(
        rec.address(
            rid,
            f"{int(rng.integers(1, 300))} {w.names.street(w.names_rng(rid))}, {town}, {postcode}",
            city=town,
            postal_code=postcode,
            country="gb",
        )
    )
    return rid


def _parent(
    w: _W,
    rng: np.random.Generator,
    today: date,
    names: NameSource,
    people: list[str],
    owner_share: float,
) -> str:
    place = PARENT_PLACES[int(rng.integers(len(PARENT_PLACES)))]
    rid = w.rid("co")
    w.records.append(
        rec.company(
            rid,
            w.company_name(rid, place),
            jurisdiction=place,
            registration_number=f"SH{w.counts['co']:06d}",
            incorporation_date=(today - timedelta(days=int(rng.integers(1500, 12000)))).isoformat(),
            sector="holding",
        )
    )
    if rng.random() < owner_share:
        w.records.append(
            rec.ownership(w.rid("own"), people[int(rng.integers(len(people)))], rid, band="75-100")
        )
    return rid
