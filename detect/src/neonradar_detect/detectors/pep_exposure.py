"""pep_exposure 0.1.0: an organisation that a politically exposed person, a family member of one
or a close associate owns, controls or directs, directly or through up to three companies
(PHASE-1.md 7.2 extended entry; `typology-detection-definitions.md` section 13; PHASE-3.md
7.3.13).

Registry evidence only, and only relationships that still hold at the end of the window (no end
date, or a later one). The people it starts from:

- every :PEP person in scope: in office (a HOLDS_POSITION with no end date, or one ending on or
  after the end of the window), out of office for at most `after_office_months` (MLR 2017 reg
  35(9): "at least 12 months"), or with no recorded position (then `office_dates_unknown`, since
  missing end dates make former PEPs look current);
- while the PEP is in office (or the dates are unknown), the family members one FAMILY_OF hop
  away whose relationship to the PEP is in `family_relationships` (reg 35(12)(b) and FCA FG25/3:
  spouse or civil partner, children and their spouses or civil partners, parents, siblings). FtM
  names the relative from the person's side ("e.g. 'mother', where `relative` is the mother of
  `person`"), so a link whose relative is the PEP is turned round first: a PEP recorded as
  someone's mother makes that someone the PEP's child, and a PEP recorded as someone's son-in-law
  makes that someone a parent-in-law, who is not in the list;
- while the PEP is in office, the people one ASSOCIATE_OF hop away whose relationship is in
  `associate_relationships`, or who hold OWNS or CONTROLS into a legal entity the PEP also holds
  into: reg 35(12)(c) counts "joint beneficial ownership of a legal entity" or "any other close
  business relations". Reg 35(11): the firm "is no longer required to apply" the measures to
  family members and associates once the PEP leaves office;
- every :RCA person as the source data gives it, with the office of the PEPs it is linked to by
  FAMILY_OF or ASSOCIATE_OF (none linked: unknown), and no start when every linked PEP has left
  office (reg 35(11)).

From each of them, up to `ownership_control_hops` OWNS, CONTROLS or DIRECTOR_OF relationships
lead to organisations; every organisation reached is a finding, with the PEP, the family or
associate link and the paths in its evidence. Being a PEP "does not prejudge a link to criminal
activities" (FATF 2013, Annex 1): the alert says only which records connect the organisation to a
public function. Every finding names people in its evidence, so on a real profile R-REAL (c)
withholds it (PHASE-3.md 7.1.4).

pattern_strength = 0.35 * relation (PEP 1, family 0.7, associate or RCA 0.6) + 0.3 * proximity
(1 - (hops - 1) / ownership_control_hops) + 0.2 * first link (a majority holding or appointment
right 1, other ownership or control 0.7, a directorship 0.5) + 0.15 * office (in office 1, unknown
0.8, former 0.5), less 0.1 when every position of the PEP is in `domestic_countries` (reg 35(3A):
a domestic PEP starts from a lower risk).
"""

from __future__ import annotations

from collections import defaultdict, deque
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date

from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "pep_exposure"
VERSION = "0.1.0"
QUERIES = ("entities.cypher", "flagged_ids.cypher", "links_from.cypher", "links_into.cypher")
FAMILY = (
    "spouse",
    "civil partner",
    "husband",
    "wife",
    "child",
    "son",
    "daughter",
    "child's spouse",
    "child's civil partner",
    "son-in-law",
    "daughter-in-law",
    "parent",
    "father",
    "mother",
    "sibling",
    "brother",
    "sister",
)
# What the person is to the PEP when the PEP is the `relative` of a FAMILY_OF: the relationship
# names the PEP from the person's side, so it is turned round. In-laws turn into parents-in-law.
REVERSE = {
    "spouse": "spouse",
    "civil partner": "civil partner",
    "husband": "wife",
    "wife": "husband",
    "child": "parent",
    "son": "parent",
    "daughter": "parent",
    "parent": "child",
    "father": "child",
    "mother": "child",
    "sibling": "sibling",
    "brother": "sibling",
    "sister": "sibling",
    "child's spouse": "parent-in-law",
    "child's civil partner": "parent-in-law",
    "son-in-law": "parent-in-law",
    "daughter-in-law": "parent-in-law",
}
ASSOCIATES = ("business partner", "business associate", "co-owner", "joint owner")
RELATION_SCORE = {"pep": 1.0, "family": 0.7, "associate": 0.6, "rca": 0.6}
OFFICE_SCORE = {"in office": 1.0, "unknown": 0.8, "former": 0.5}


@dataclass(frozen=True, slots=True)
class Params:
    family_relationships: tuple[str, ...] = FAMILY
    associate_relationships: tuple[str, ...] = ASSOCIATES
    associate_hops: int = 1
    ownership_control_hops: int = 3
    after_office_months: int = 12
    domestic_countries: tuple[str, ...] = ("gb",)
    max_paths: int = 1_000
    max_steps: int = 12


@dataclass(frozen=True, slots=True)
class Start:
    person: str
    relation: str  # pep | family | associate | rca
    pep: str  # the PEP behind it ("" for an RCA given as such)
    link: LinkRow | None  # the family or associate link
    office: str  # in office | former | unknown


def _months_before(day: date, months: int) -> date:
    y, m = divmod(day.year * 12 + day.month - 1 - months, 12)
    return date(y, m + 1, min(day.day, 28))


def office(positions: list[LinkRow], as_of: date, months: int) -> str | None:
    """`in office`, `former` (left within `months`), `unknown` (no position), or None (left
    earlier, out of scope)."""
    if not positions:
        return "unknown"
    ends = []
    for x in positions:
        if not x.end_date or x.end_date >= as_of.isoformat():
            return "in office"
        ends.append(x.end_date)
    return "former" if max(ends) >= _months_before(as_of, months).isoformat() else None


def _normal(relationship: str) -> str:
    return " ".join(relationship.casefold().replace("_", " ").split())


def relation_to_pep(link: LinkRow, pep: str) -> str:
    """What the other person of a FAMILY_OF is to `pep`, in the normal form of `_normal`."""
    word = _normal(link.role)
    return word if link.source == pep else REVERSE.get(word, "")


def _holdings(source: Source, ids: list[str], as_of: str) -> dict[str, set[str]]:
    """The legal entities each id holds into through a current OWNS or CONTROLS."""
    return {
        i: {x.target for x in links if x.current(as_of)}
        for i, links in source.links_from(ids, ("OWNS", "CONTROLS")).items()
    }


def starts(source: Source, p: Params, as_of: date) -> tuple[list[Start], dict[str, list[LinkRow]]]:
    day = as_of.isoformat()
    peps = source.flagged_ids("PEP")
    positions = source.links_from(peps, ("HOLDS_POSITION",))
    family_set = {_normal(x) for x in p.family_relationships}
    associate_set = {_normal(x) for x in p.associate_relationships}
    kinds = ("FAMILY_OF", "ASSOCIATE_OF") if p.associate_hops >= 1 else ("FAMILY_OF",)
    outgoing = source.links_from(peps, kinds)
    incoming = source.links_into(peps, kinds)
    status_of = {pep: office(positions.get(pep, []), as_of, p.after_office_months) for pep in peps}
    links_of = {
        pep: sorted(
            (x for x in outgoing.get(pep, []) + incoming.get(pep, []) if x.current(day)),
            key=lambda x: x.rel_id,
        )
        for pep in peps
    }
    associates = sorted(
        {
            x.target if x.source == pep else x.source
            for pep in peps
            for x in links_of[pep]
            if x.rel_type == "ASSOCIATE_OF"
        }
    )
    held = _holdings(source, sorted(set(peps) | set(associates)), day)
    out: list[Start] = []
    for pep in peps:
        status = status_of[pep]
        if status is None:
            continue
        out.append(Start(pep, "pep", pep, None, status))
        if status == "former":
            continue  # reg 35(11): family and associates only while the PEP holds office
        for x in links_of[pep]:
            other = x.target if x.source == pep else x.source
            if x.rel_type == "ASSOCIATE_OF":
                joint = held.get(other, set()) & held.get(pep, set())
                if _normal(x.role) in associate_set or joint:
                    out.append(Start(other, "associate", pep, x, status))
            elif relation_to_pep(x, pep) in family_set:
                out.append(Start(other, "family", pep, x, status))
    rcas = source.flagged_ids("RCA")
    rca_links = {
        k: [x for x in v if x.current(day)]
        for k, v in source.links_from(rcas, ("FAMILY_OF", "ASSOCIATE_OF")).items()
    }
    for k, v in source.links_into(rcas, ("FAMILY_OF", "ASSOCIATE_OF")).items():
        rca_links.setdefault(k, []).extend(x for x in v if x.current(day))
    for rca in rcas:
        linked = sorted(
            {x.target if x.source == rca else x.source for x in rca_links.get(rca, [])} & set(peps)
        )
        statuses = {status_of[pep] for pep in linked}
        if not linked:
            out.append(Start(rca, "rca", "", None, "unknown"))
        elif "in office" in statuses:
            out.append(Start(rca, "rca", "", None, "in office"))
        elif "unknown" in statuses:
            out.append(Start(rca, "rca", "", None, "unknown"))
        # every linked PEP has left office: reg 35(11), no start
    return out, positions


def _first_link_score(link: LinkRow) -> float:
    if link.rel_type == "DIRECTOR_OF":
        return 0.5
    if link.rel_type == "CONTROLS" and link.control_type == "appointment":
        return 1.0
    low = link.share_min if link.share_min is not None else 0.0
    if low > 50 or (low == 50 and link.share_min_exclusive):
        return 1.0
    return 0.7


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date()
    people, positions = starts(source, p, as_of)
    links: dict[str, LinkRow] = {}
    frontier = sorted({s.person for s in people})
    seen = set(frontier)
    day = as_of.isoformat()
    for _ in range(p.ownership_control_hops):
        if not frontier:
            break
        nxt = set()
        for rows in source.links_from(frontier, ("OWNS", "CONTROLS", "DIRECTOR_OF")).values():
            for x in rows:
                if not x.current(day):
                    continue
                links[x.rel_id] = x
                if x.target not in seen:
                    seen.add(x.target)
                    nxt.add(x.target)
        frontier = sorted(nxt)
    out_links: dict[str, list[LinkRow]] = defaultdict(list)
    for x in sorted(links.values(), key=lambda x: x.rel_id):
        out_links[x.source].append(x)
    position_ids = sorted({x.target for rows in positions.values() for x in rows})
    entities = source.entities(sorted(seen | set(position_ids) | {s.pep for s in people if s.pep}))
    reached: dict[str, list[tuple[Start, list[LinkRow]]]] = defaultdict(list)
    for s in people:
        for target, path in _paths(s.person, out_links, p.ownership_control_hops, p.max_paths):
            if "Organization" in entities[target].labels:
                reached[target].append((s, path))
    findings = []
    for target in sorted(reached):
        if "PEP" in entities[target].labels:
            continue
        findings.append(_finding(target, reached[target], positions, entities, p))
    return DetectorOutput(findings, {"starts": len(people), "links": len(links)})


def _paths(
    start: str, out_links: dict[str, list[LinkRow]], max_hops: int, limit: int
) -> Iterator[tuple[str, list[LinkRow]]]:
    """Simple paths from `start` of 1 to `max_hops` relationships, breadth first."""
    found = 0
    queue: deque[tuple[str, list[LinkRow], frozenset[str]]] = deque(
        [(start, [], frozenset({start}))]
    )
    while queue:
        node, path, visited = queue.popleft()
        for x in out_links.get(node, []):
            if x.target in visited:
                continue
            grown = [*path, x]
            yield x.target, grown
            found += 1
            if found >= limit:
                return
            if len(grown) < max_hops:
                queue.append((x.target, grown, visited | {x.target}))


def _finding(
    target: str,
    found: list[tuple[Start, list[LinkRow]]],
    positions: dict[str, list[LinkRow]],
    entities: dict[str, EntityRow],
    p: Params,
) -> Finding:
    def score(item: tuple[Start, list[LinkRow]]) -> tuple[float, int, str]:
        s, path = item
        return (-RELATION_SCORE[s.relation], len(path), s.person)

    ordered = sorted(found, key=lambda item: (score(item), tuple(x.rel_id for x in item[1])))
    best, best_path = ordered[0]
    hops = len(best_path)
    domestic = False
    if best.pep:
        countries = {c for x in positions.get(best.pep, []) for c in entities[x.target].countries}
        domestic = bool(countries) and countries <= set(p.domestic_countries)
    strength = clip01(
        0.35 * RELATION_SCORE[best.relation]
        + 0.3 * (1 - (hops - 1) / p.ownership_control_hops)
        + 0.2 * _first_link_score(best_path[0])
        + 0.15 * OFFICE_SCORE[best.office]
        - (0.1 if domestic else 0.0)
    )
    shown = ordered[: p.max_steps]
    edges: set[str] = set()
    nodes: set[str] = {target}
    steps: list[tuple[str, ...]] = []
    for s, path in shown:
        step = tuple(x.rel_id for x in path)
        if s.link is not None:
            step = (s.link.rel_id, *step)
        steps.append(step)
        edges.update(step)
        nodes.update({s.person, *(x.target for x in path)})
        if s.pep:
            nodes.add(s.pep)
    peps = sorted({s.pep for s, _ in found if s.pep})
    metrics = {
        "relation": best.relation,
        "office": best.office,
        "office_dates_unknown": best.office == "unknown",
        "domestic": domestic,
        "shortest_path": min(len(path) for _, path in found),
        "paths": len(found),
        "peps": len(peps),
        "first_link": best_path[0].rel_type,
        "family_relationship": relation_to_pep(best.link, best.pep)
        if best.link is not None and best.relation == "family"
        else "",
    }
    return Finding(
        typology=SLUG,
        variant=best.relation,
        anchor=target,
        node_ids=tuple(sorted(nodes)),
        edge_ids=tuple(sorted(edges)),
        subjects=(Subject(target, "exposed_entity"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=tuple(steps),
        window=None,
        activity=False,
    )
