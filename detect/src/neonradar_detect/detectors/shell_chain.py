"""shell_chain 0.2.0: ownership of a company layered through other companies, with the concealment
indicators of FATF and Egmont 2018 Annex E (PHASE-1.md 7.2 entry 8, corrected by
`typology-detection-definitions.md` section 8; PHASE-3.md 7.3.8).

Registry evidence only, so the detector also runs on real profiles (R-REAL allows registry
patterns about organisations whose evidence names no person). Only relationships that still hold
at the end of the window count (no end date, or a later one): a resigned director or a sold
holding is history, not structure. Candidates are the maximal OWNS paths from a top owner (a node
no OWNS points to) down to a leaf company (one that owns no organisation), and the OWNS cycles.
The paths to a leaf qualify when they pass through at least `min_company_layers` organisations,
the leaf included, and the leaf's paths show at least `min_indicators` of:

- `nominee`: `is_nominee` on an OWNS relationship of a path or on a directorship of a path company;
- `professional_director`: a director of a path company with at least `professional_appointments`
  current appointments ("mass" nominees, Annex E);
- `unknown_owner`: a top owner that is an organisation with no recorded owner or controller, or a
  path company whose PSC statements say no registrable person was found or identified;
- `loop`: the ownership returns to itself (the cycle variant);
- `mass_registration_address`: a path company registered at an address shared by at least
  `mass_address_companies` active organisations (Companies House default addresses excepted);
- `po_box`: a path company whose registered address is a PO box ("Only a post-box address").

A loop needs no other indicator. `min_indicators` is 2 because each indicator alone is common in
lawful groups (a foreign parent with no owner on the UK register, a professional director in a
fund jurisdiction): on the development worlds one indicator flagged most corporate groups
(PHASE-3.md 7.6.5), and a red flag on its own is not evidence (FFIEC, quoted in
`typology-detection-definitions.md` 16.1). Jurisdictions are a
strength factor, not a condition ("different jurisdictions", with no number). One finding per
leaf company (or per loop), with every qualifying path in its evidence.

pattern_strength = 0.15 * min(1, (layers - 1) / 3) + 0.15 * min(1, (jurisdictions - 1) / 2)
+ 0.2 * nominee + 0.15 * professional director + 0.15 * (unknown owner or loop)
+ 0.1 * mass registration address + 0.1 * PO box.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from neonradar_detect.detectors.mass_registration_address import (
    DEFAULT_ADDRESS_POSTCODES,
    PO_BOX,
    normalise_postcode,
)
from neonradar_detect.model import Finding, Subject, clip01
from neonradar_detect.rows import EntityRow, LinkRow, OwnershipPath
from neonradar_detect.source import DetectorOutput, Source, Window

SLUG = "shell_chain"
VERSION = "0.2.0"
QUERIES = (
    "appointment_counts.cypher",
    "entities.cypher",
    "links_from.cypher",
    "links_into.cypher",
    "ownership_cycles.cypher",
    "ownership_paths.cypher",
)
# PSC statement values (Companies House spelling, prefixes) that leave the owner unknown
UNKNOWN_OWNER_STATEMENTS = (
    "no-individual-or-entity-with-signficant-control",
    "psc-exists-but-not-identified",
    "psc-details-not-confirmed",
    "steps-to-find-psc-not-yet-completed",
    "psc-contacted-but-no-response",
    "restrictions-notice-issued-to-psc",
)
INACTIVE = frozenset({"dissolved", "converted-closed", "removed", "closed"})
INDICATORS = (
    "nominee",
    "professional_director",
    "unknown_owner",
    "loop",
    "mass_registration_address",
    "po_box",
)
INDICATOR_TEXT = {
    "nominee": "a nominee recorded",
    "professional_director": "a director of many companies",
    "unknown_owner": "no recorded top owner",
    "loop": "ownership that returns to itself",
    "mass_registration_address": "a widely shared address",
    "po_box": "a PO box address",
}


@dataclass(frozen=True, slots=True)
class Params:
    min_company_layers: int = 2
    min_indicators: int = 2
    professional_appointments: int = 10
    mass_address_companies: int = 25
    max_hops: int = 6
    max_paths: int = 200_000


@dataclass(slots=True)
class Context:
    entities: dict[str, EntityRow]
    directors: dict[str, list[LinkRow]]
    appointments: dict[str, int]
    owned_by: dict[str, list[LinkRow]]
    registered: dict[str, list[LinkRow]]  # organisation -> its registered HAS_ADDRESS links
    crowded: set[str]  # addresses with at least mass_address_companies active organisations
    boxes: set[str]  # PO box addresses


def _active(e: EntityRow) -> bool:
    return not e.dissolution_date and e.status.casefold() not in INACTIVE


def _current(links: dict[str, list[LinkRow]], as_of: str) -> dict[str, list[LinkRow]]:
    return {k: [x for x in v if x.current(as_of)] for k, v in links.items()}


def run(source: Source, p: Params, window: Window) -> DetectorOutput:
    as_of = window.end.date().isoformat()
    paths = source.ownership_paths(p.max_hops, p.max_paths, as_of)
    cycles = source.ownership_cycles(p.max_hops, p.max_paths, as_of)
    ids = sorted({n for x in [*paths, *cycles] for n in x.nodes})
    entities = source.entities(ids)
    orgs = [i for i in ids if "Organization" in entities[i].labels]
    directors = _current(source.links_into(orgs, ("DIRECTOR_OF",)), as_of)
    appointments = source.appointment_counts(
        sorted({d.source for links in directors.values() for d in links}), as_of
    )
    owned_by = _current(source.links_into(ids, ("OWNS", "CONTROLS")), as_of)
    registered = {
        o: [x for x in links if x.role == "registered"]
        for o, links in source.links_from(orgs, ("HAS_ADDRESS",)).items()
    }
    addresses = sorted({x.target for links in registered.values() for x in links})
    address_rows = source.entities(addresses)
    excluded = {normalise_postcode(x) for x in DEFAULT_ADDRESS_POSTCODES}
    at_address = source.links_into(addresses, ("HAS_ADDRESS",))
    members = sorted(
        {x.source for links in at_address.values() for x in links if x.role == "registered"}
    )
    member_rows = source.entities(members)
    crowded = set()
    for a in addresses:
        if normalise_postcode(address_rows[a].postal_code) in excluded:
            continue
        active = {
            x.source
            for x in at_address.get(a, [])
            if x.role == "registered"
            and "Organization" in member_rows[x.source].labels
            and _active(member_rows[x.source])
        }
        if len(active) >= p.mass_address_companies:
            crowded.add(a)
    boxes = {a for a in addresses if PO_BOX.search(address_rows[a].full)}
    ctx = Context(entities, directors, appointments, owned_by, registered, crowded, boxes)
    by_leaf: dict[str, list[OwnershipPath]] = defaultdict(list)
    for path in paths:
        by_leaf[path.nodes[-1]].append(path)
    findings = []
    for leaf in sorted(by_leaf):
        f = _evaluate(leaf, by_leaf[leaf], False, ctx, p)
        if f is not None:
            findings.append(f)
    for cycle in cycles:
        f = _evaluate(cycle.nodes[0], [cycle], True, ctx, p)
        if f is not None:
            findings.append(f)
    return DetectorOutput(
        findings, {"paths": len(paths), "cycles": len(cycles), "crowded_addresses": len(crowded)}
    )


def _layers(path: OwnershipPath, entities: dict[str, EntityRow]) -> int:
    return len([n for n in dict.fromkeys(path.nodes) if "Organization" in entities[n].labels])


def _evaluate(
    anchor: str, paths: list[OwnershipPath], loop: bool, ctx: Context, p: Params
) -> Finding | None:
    e = ctx.entities
    kept = [x for x in paths if _layers(x, e) >= p.min_company_layers]
    if not kept:
        return None
    nodes = sorted({n for x in kept for n in x.nodes})
    orgs = [n for n in nodes if "Organization" in e[n].labels]
    links = sorted(
        {link.rel_id: link for x in kept for link in x.links}.values(), key=lambda x: x.rel_id
    )
    nominee_links = [x for x in links if x.is_nominee]
    nominee_dirs = [d for n in orgs for d in ctx.directors.get(n, []) if d.is_nominee]
    pro_dirs = [
        d
        for n in orgs
        for d in ctx.directors.get(n, [])
        if ctx.appointments.get(d.source, 0) >= p.professional_appointments
    ]
    tops = sorted({x.nodes[0] for x in kept}) if not loop else []
    ownerless = [t for t in tops if "Organization" in e[t].labels and not ctx.owned_by.get(t)]
    statements = [
        n for n in orgs if any(s.startswith(UNKNOWN_OWNER_STATEMENTS) for s in e[n].psc_statements)
    ]
    crowded_links = [x for n in orgs for x in ctx.registered.get(n, []) if x.target in ctx.crowded]
    box_links = [x for n in orgs for x in ctx.registered.get(n, []) if x.target in ctx.boxes]
    present = {
        "nominee": bool(nominee_links or nominee_dirs),
        "professional_director": bool(pro_dirs),
        "unknown_owner": bool(ownerless or statements),
        "loop": loop,
        "mass_registration_address": bool(crowded_links),
        "po_box": bool(box_links),
    }
    if not loop and sum(present.values()) < p.min_indicators:
        return None
    layers = max(_layers(x, e) for x in kept)
    jurisdictions = sorted({e[n].jurisdiction for n in orgs if e[n].jurisdiction})
    strength = clip01(
        0.15 * min(1.0, (layers - 1) / 3)
        + 0.15 * min(1.0, (len(jurisdictions) - 1) / 2)
        + 0.2 * present["nominee"]
        + 0.15 * present["professional_director"]
        + 0.15 * (present["unknown_owner"] or loop)
        + 0.1 * present["mass_registration_address"]
        + 0.1 * present["po_box"]
    )
    if loop:
        top_kind = "loop"
    elif ownerless:
        top_kind = "company without a recorded owner"
    elif any("Person" in e[t].labels for t in tops):
        top_kind = "person"
    elif any("Organization" not in e[t].labels for t in tops):
        top_kind = "legal entity of unstated kind"
    else:
        top_kind = "company"
    director_links = sorted(
        {d.rel_id: d for d in [*nominee_dirs, *pro_dirs]}.values(), key=lambda d: d.rel_id
    )
    address_links = sorted(
        {x.rel_id: x for x in [*crowded_links, *box_links]}.values(), key=lambda x: x.rel_id
    )
    metrics = {
        "company_layers": layers,
        "jurisdictions": len(jurisdictions),
        "jurisdiction_list": ", ".join(jurisdictions),
        "indicators": ", ".join(k for k in INDICATORS if present[k]),
        "indicator_text": " and ".join(
            [INDICATOR_TEXT[k] for k in INDICATORS if present[k] and k != "loop"][:2]
        )
        or INDICATOR_TEXT["loop"],
        "nominee_links": len(nominee_links) + len(nominee_dirs),
        "professional_directors": len({d.source for d in pro_dirs}),
        "unknown_owner_statements": len(statements),
        "top_kind": top_kind,
        "paths": len(kept),
    }
    path_steps = tuple(tuple(link.rel_id for link in x.links) for x in kept)
    extra_steps = tuple((d.rel_id,) for d in director_links) + tuple(
        (x.rel_id,) for x in address_links
    )
    extra_nodes = {d.source for d in director_links} | {x.target for x in address_links}
    return Finding(
        typology=SLUG,
        variant="loop" if loop else "chain",
        anchor=anchor,
        node_ids=tuple(sorted(set(nodes) | extra_nodes)),
        edge_ids=tuple(
            sorted(
                {x.rel_id for x in links}
                | {d.rel_id for d in director_links}
                | {x.rel_id for x in address_links}
            )
        ),
        subjects=(Subject(anchor, "owned_company"),),
        metrics=metrics,
        pattern_strength=strength,
        steps=path_steps + extra_steps,
        window=None,
        activity=False,
    )
