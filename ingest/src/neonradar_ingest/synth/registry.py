"""The demo-mini synthetic registry (PHASE-1.md M1.8e deliverable 2).

24 companies (18 `gb`, 2 each `vg`, `cy`, `ae`), 2 bank branches, 30 people (10 with names in
two or three scripts), 12 addresses (one the registered office of 8 companies), a formation
agent representing 6 companies, a nominee director on 4 of them, a three-level ownership
chain ending at a person (who has topic `role.pep`) and one company with topic `sanction`.
Roles are fixed positions in a seeded shuffle, so records never carry them (R9). The PEP, the
nominee director and the sanctioned company are seeded draws across name origins and
jurisdictions, and none of them is a party to a planted scenario or look-alike.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from itertools import pairwise
from typing import Any

from neonradar_contracts.records import SYNTHETIC_PREFIX, make_id
from neonradar_ingest.synth import words
from neonradar_ingest.synth.companies import CompanyNames, street
from neonradar_ingest.synth.emit import Rec
from neonradar_ingest.synth.names import Origin, PersonNames
from neonradar_ingest.synth.rng import between, chance, pick, stream

COUNTRIES = ("gb", "vg", "cy", "ae")
PLAN = ("gb",) * 18 + ("vg",) * 2 + ("cy",) * 2 + ("ae",) * 2
PEOPLE: tuple[tuple[Origin, int], ...] = (
    (("ar", 3),) * 3 + (("ar", 2),) * 3 + (("ru", 2),) * 4
    + (("en", 1),) * 9 + (("ar", 1),) * 6 + (("ru", 1),) * 5
)  # fmt: skip
BANDS = {"25-50": (25.0, 50.0), "50-75": (50.0, 75.0), "75-100": (75.0, 100.0)}


def sid(kind: str, number: int, width: int = 4) -> str:
    """A synthetic record id such as `syn-co-0001`."""
    return make_id(SYNTHETIC_PREFIX, kind, f"{number:0{width}d}")


@dataclass
class Registry:
    records: list[Rec] = field(default_factory=list)
    names: dict[str, str] = field(default_factory=dict)  # record id -> primary name
    jurisdiction: dict[str, str] = field(default_factory=dict)
    founded: dict[str, date] = field(default_factory=dict)
    persons: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)
    roles: dict[str, list[str]] = field(default_factory=dict)
    ownerships: int = 0
    attempts: dict[str, int] = field(default_factory=dict)  # record id -> name draw used
    origin: dict[str, str] = field(default_factory=dict)  # person id -> en, ar or ru

    def own(self, owner: str, asset: str, start: date, band: str | None = None) -> None:
        """An Ownership: a share band between legal entities, or an account holding."""
        self.ownerships += 1
        props = {"owner": [owner], "asset": [asset], "startDate": [start.isoformat()]}
        if band is None:
            props["role"] = ["account holder"]
            self.records.append(
                Rec(sid("ownership", self.ownerships), "Ownership", "activity", props)
            )
            return
        nature = f"ownership-of-shares-{band.replace('-', '-to-')}-percent"
        props |= {"percentage": [band], "role": [nature]}
        low, high = BANDS[band]
        nr = {"natures_of_control": [nature], "share_pct_min": low, "share_pct_max": high}
        self.records.append(
            Rec(sid("ownership", self.ownerships), "Ownership", "registry", props, nr)
        )


def build_registry(seed: int, redraw: Mapping[str, int] | None = None) -> Registry:
    """The registry; `redraw` maps a record id to the first name draw to use (OD-12)."""
    rng, redraw = stream(seed, "registry"), redraw or {}
    reg = Registry()
    plan = [PLAN[int(i)] for i in rng.permutation(len(PLAN))]
    ids = [sid("co", n) for n in range(1, len(plan) + 1)]
    gb, vg, cy, ae = ([c for c, j in zip(ids, plan, strict=True) if j == k] for k in COUNTRIES)
    reg.roles = {
        "agent": [gb[0]], "agent_clients": gb[1:7], "nominee_served": gb[1:5],
        "chain": [vg[0], cy[0], gb[8]], "round_trip": [gb[9], ae[0], vg[1], cy[1]],
        "lender": [gb[10]], "borrower": [gb[11]], "employers": [gb[12], gb[13], gb[9]],
        "retail": gb[14:18], "eur_second": [gb[9], gb[12], gb[14]],
    }  # fmt: skip
    # Flags never sit on a scenario or look-alike party, and their place is a seeded draw, so
    # no jurisdiction or name origin always carries them (M1.8e review).
    planted_roles = ("round_trip", "lender", "borrower", "retail")
    planted = {c for role in planted_roles for c in reg.roles[role]}
    free = [c for c in ids if c not in planted]
    country = pick(rng, sorted({plan[ids.index(c)] for c in free}))
    reg.roles["sanctioned"] = [pick(rng, [c for c in free if plan[ids.index(c)] == country])]

    addresses: dict[str, str] = {}  # company or branch id -> address id
    groups = [gb[:8], gb[8:10], gb[10:12], gb[12:14], gb[14:16], gb[16:17], gb[17:], vg, cy, ae]
    for number, group in enumerate([*groups, ["branch-1"], ["branch-2"]], start=1):
        country = "gb" if group[0].startswith("branch") else plan[ids.index(group[0])]
        unit = None
        if number == 1:  # the formation agent's office, registered office of 8 companies
            unit = f"Suite {between(rng, 2, 9)}"
        elif country == "ae":
            unit = f"Office {between(rng, 101, 940)}"
        line, city = f"{between(rng, 2, 180)} {street(rng)}", pick(rng, words.CITIES[country])
        aid = sid("addr", number)
        full = ", ".join(part for part in (unit, line, city) if part)
        props = {"full": [full], "street": [line], "city": [city], "country": [country]}
        reg.records.append(Rec(aid, "Address", "registry", props))
        addresses |= dict.fromkeys(group, aid)
        reg.names[aid] = line

    company_names = CompanyNames(seed)
    special = {gb[0]: words.AGENT_ACTIVITY, gb[10]: words.LENDER_ACTIVITY}
    for number, (cid, country) in enumerate(zip(ids, plan, strict=True), start=1):
        name, reg.attempts[cid] = company_names.draw(
            number, country, special.get(cid), redraw.get(cid, 0)
        )
        start = date(2005, 3, 1) if cid == gb[0] else date(2008, 1, 1)
        founded = start + timedelta(days=between(rng, 0, 900 if cid == gb[0] else 5800))
        aid = addresses[cid]
        props = {
            "name": [name], "jurisdiction": [country], "registrationNumber": [f"SYN{number:05d}"],
            "incorporationDate": [founded.isoformat()], "addressEntity": [aid],
        }  # fmt: skip
        if cid in reg.roles["sanctioned"]:
            props["topics"] = ["sanction"]
        nr = {"address_roles": {aid: "registered"}}
        reg.records.append(Rec(cid, "Company", "registry", props, nr))
        reg.names[cid], reg.jurisdiction[cid], reg.founded[cid] = name, country, founded

    for number, bank in enumerate(words.BANKS[:2], start=1):
        bid, aid = sid("org", number), addresses[f"branch-{number}"]
        name = f"{bank}, {reg.names[aid].split(' ', 1)[1]} branch"
        props = {"name": [name], "jurisdiction": ["gb"], "addressEntity": [aid]}
        nr = {"address_roles": {aid: "business"}}
        reg.records.append(Rec(bid, "Organization", "registry", props, nr))
        reg.names[bid], reg.jurisdiction[bid], reg.founded[bid] = name, "gb", date(2001, 6, 1)
        reg.branches.append(bid)

    person_names = PersonNames(seed)
    people: dict[str, Rec] = {}
    for number, index in enumerate(rng.permutation(len(PEOPLE)), start=1):
        origin, scripts = PEOPLE[int(index)]
        pid = sid("p", number)
        person = person_names.draw(number, origin, scripts, redraw.get(pid, 0))
        reg.attempts[pid] = person.attempt
        props = {
            "name": list(person.names), "gender": [person.gender],
            "birthDate": [person.birth], "nationality": [person.nationality],
        }  # fmt: skip
        people[pid] = Rec(pid, "Person", "registry", props)
        reg.names[pid], reg.origin[pid] = person.names[0], origin
        reg.persons.append(pid)
    reg.records.extend(people.values())

    # The PEP and the nominee director come from two different name origins, drawn by seed.
    origins = [str(o) for o in rng.permutation(sorted(set(reg.origin.values())))]
    top = pick(rng, [p for p in reg.persons if reg.origin[p] == origins[0]])
    reg.roles["pep"] = [top]
    people[top].props["topics"] = ["role.pep"]  # PEP exposure through the chain, typology (i)
    chain = [top, *reg.roles["chain"]]
    for owner, asset in pairwise(chain):
        start = max(reg.founded.get(owner, reg.founded[asset]), reg.founded[asset])
        reg.own(owner, asset, start, "75-100")
    owners: dict[str, list[str]] = {}
    others = [p for p in reg.persons if p != top]
    for cid in ids:
        if cid in reg.roles["chain"]:
            continue
        two = chance(rng, 0.3)
        pool = others if cid in planted else reg.persons  # the PEP owns no planted party
        picked = [str(p) for p in rng.choice(pool, 2 if two else 1, replace=False)]
        owners[cid] = picked
        for owner, band in zip(picked, ("50-75", "25-50") if two else ("75-100",), strict=True):
            reg.own(owner, cid, reg.founded[cid], band)

    served = reg.roles["nominee_served"]
    nominee = pick(rng, [p for p in others if reg.origin[p] == origins[1]
                         and not any(p in owners[c] for c in served)])  # fmt: skip
    for number, cid in enumerate(ids, start=1):
        extra: dict[str, Any] = {}
        if cid in served:
            director, role, extra = nominee, "nominee-director", {"is_nominee": True}
        else:
            mine = owners.get(cid, [])
            pool = others if cid in planted else reg.persons
            director = mine[0] if mine and chance(rng, 0.6) else pick(rng, pool)
            role = "director"
        props = {
            "director": [director], "organization": [cid], "role": [role],
            "startDate": [reg.founded[cid].isoformat()],
        }  # fmt: skip
        reg.records.append(
            Rec(sid("directorship", number), "Directorship", "registry", props, extra)
        )
    for number, client in enumerate(reg.roles["agent_clients"], start=1):
        props = {
            "agent": [gb[0]], "client": [client], "role": ["company formation agent"],
            "startDate": [reg.founded[client].isoformat()],
        }  # fmt: skip
        reg.records.append(Rec(sid("representation", number), "Representation", "registry", props))
    return reg
