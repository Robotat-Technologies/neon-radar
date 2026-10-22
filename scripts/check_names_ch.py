#!/usr/bin/env python3
"""Check the entity resolution benchmark's names on the Companies House search (OD-12).

A human runs it in a terminal, with `CH_API_KEY` in the environment or `.env`; it refuses to
query when stdin is not a terminal, so an agent cannot spend the key. It prints match flags per
query index only, never a search result, and stores nothing, so its output can go into a pull
request as it is:

    uv run python scripts/check_names_ch.py --list   # index, class, styles, exposure, kind,
                                                     # entity id, synthetic text
    uv run python scripts/check_names_ch.py          # index, company=, officer=, then counts

Queries (`kind`):
- `name`: every entity's canonical name (people: given name and surname; organisations: name
  and legal form), on the company search and the officer search.
- `spelling`: for list and leak entities, their near twins and the people linked to them
  (officers and PSCs of any of these organisations, and near twins of any of these people),
  every other Latin given name and surname pair, alias and organisation name their records
  show (variants and typos), on both searches.
- `surname`: every distinct Latin surname those people's records show, alone on the officer
  search (`officer=1` when an officer has that surname).

A flag is 1 when a result's title has the same name key (companies: the name without its legal
form, "&" read as "and"; officers: every token of the query among the title's tokens).

Action rule:
- `company` must be 0 for every organisation.
- Every flag must be 0 for list and leak entities and the people linked to them (`exposure`
  other than `registry`): for a flag, add the entity id to `REDRAW` in
  `ingest/src/neonradar_ingest/synth/erbench.py` (or the surname to `variants.NOT_INVENTED`),
  run `make fixtures` and check again.
- Officer matches of registry-only people on common names are expected (Faker names); a public
  figure's name goes to `ingest/src/neonradar_ingest/synth/denylist.txt`.
The exit code is 1 when the rule is broken.
"""

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import dataclass

from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house.client import CompaniesHouseClient
from neonradar_ingest.synth import ER_BENCH_SEED
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.erbench import SIZES, Bench, build, exposed_orgs
from neonradar_ingest.synth.names import fold

OTHER_SCRIPT = re.compile("[\u0400-\u04ff\u0600-\u06ff]")  # Cyrillic, Arabic


@dataclass(frozen=True, slots=True)
class Query:
    cls: str  # person or org
    styles: str  # the entity's record styles
    exposure: str  # list, leak, linked, twin (the near twin of one of these), registry
    kind: str  # name, spelling or surname
    entity: str  # the id REDRAW reads: a near twin's original
    text: str


def _exposures(bench: Bench) -> tuple[dict[str, str], dict[str, str]]:
    exposure, styles = {}, defaultdict(set)
    for _, entity, _, style, _ in bench.truth:
        styles[entity].add(style)
    for person in bench.people:
        parts = [part for part, on in (("list", person.authorities), ("leak", person.leaked),
                                       ("linked", person.linked)) if on]  # fmt: skip
        exposure[person.entity_id] = "+".join(parts) or ("twin" if person.invented else "registry")
    exposed = exposed_orgs(bench.orgs)
    for org in bench.orgs:
        parts = [part for part, on in (("list", org.listed), ("leak", org.leaked)) if on]
        twin = "twin" if org.number in exposed else "registry"  # the near twin of one
        exposure[org.entity_id] = "+".join(parts) or twin
    return exposure, {entity: ",".join(sorted(s)) for entity, s in styles.items()}


def queries(bench: Bench) -> list[Query]:
    """Every distinct query, people first, then organisations."""
    exposure, styles = _exposures(bench)
    people = {p.number: p for p in bench.people}
    orgs = {o.number: o for o in bench.orgs}
    by_entity: dict[str, list[str]] = defaultdict(list)
    for record_id, entity, *_ in bench.truth:
        by_entity[entity].append(record_id)
    props = {rec.id: rec.props for rec in bench.records}
    out: list[Query] = []
    seen: set[tuple[str, str]] = set()

    def add(cls: str, entity: str, owner: str, kind: str, text: str) -> None:
        if not OTHER_SCRIPT.search(text) and (kind, fold(text)) not in seen:
            seen.add((kind, fold(text)))
            out.append(Query(cls, styles[entity], exposure[entity], kind, owner, text))

    for p in bench.people:
        owner = people[p.twin_of or p.number].entity_id
        add("person", p.entity_id, owner, "name", f"{p.given.latin[0]} {p.surname.latin[0]}")
    for p in bench.people:
        if exposure[p.entity_id] == "registry":
            continue
        owner = people[p.twin_of or p.number].entity_id
        for record_id in sorted(by_entity[p.entity_id]):
            shown = bench.shown[record_id]
            add("person", p.entity_id, owner, "spelling", f"{shown.given} {shown.surname}")
            for alias in props[record_id].get("alias", []):
                add("person", p.entity_id, owner, "spelling", alias)
            add("person", p.entity_id, owner, "surname", shown.surname)
    for o in bench.orgs:
        add("org", o.entity_id, orgs[o.twin_of or o.number].entity_id, "name", o.name)
    for o in bench.orgs:
        if exposure[o.entity_id] == "registry":
            continue
        owner = orgs[o.twin_of or o.number].entity_id
        for record_id in sorted(by_entity[o.entity_id]):
            for text in (*props[record_id].get("name", []), *props[record_id].get("alias", [])):
                add("org", o.entity_id, owner, "spelling", text)
    return out


def _company_key(name: str) -> str:
    """`name_key` with "&" written as "and", so both spellings of a name meet."""
    return name_key(name.replace("&", " and "))


def _titles(client: CompaniesHouseClient, path: str, text: str) -> list[str]:
    body = client.get_json(path, {"q": text, "items_per_page": 20}) or {}
    return [str(item.get("title", "")) for item in body.get("items") or []]


def _flags(client: CompaniesHouseClient, query: Query) -> tuple[bool | None, bool]:
    """(company match or None when not searched, officer match)."""
    tokens = set(fold(query.text).split())
    officers = _titles(client, "/search/officers", query.text)
    officer = any(tokens <= set(fold(title).split()) for title in officers)
    if query.kind == "surname":
        return None, officer
    companies = _titles(client, "/search/companies", query.text)
    return any(_company_key(t) == _company_key(query.text) for t in companies), officer


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--size", choices=sorted(SIZES), default="small")
    parser.add_argument("--seed", type=int, default=ER_BENCH_SEED)
    parser.add_argument("--list", action="store_true", help="print the queries, send nothing")
    args = parser.parse_args(argv)
    items = queries(build(args.size, args.seed))
    if args.list:
        for index, q in enumerate(items):
            print(f"{index:04d}\t{q.cls}\t{q.styles}\t{q.exposure}\t{q.kind}\t{q.entity}\t{q.text}")
        return 0
    if sys.stdin is None or not sys.stdin.isatty():
        print("check_names_ch: run it yourself in a terminal (OD-12)", file=sys.stderr)
        return 2
    key = IngestSettings().companies_house_key()
    if key is None:
        print("check_names_ch: CH_API_KEY is not set", file=sys.stderr)
        return 2
    broken = expected = 0
    with CompaniesHouseClient(key) as client:
        for index, query in enumerate(items):
            company, officer = _flags(client, query)
            exposed = query.exposure != "registry"
            if (query.cls == "org" and company) or (exposed and (company or officer)):
                broken += 1
            elif company or officer:
                expected += 1
            shown = "-" if company is None else str(int(company))
            print(f"{index:04d}\tcompany={shown}\tofficer={int(officer)}", flush=True)
    print(f"{len(items)} queries; {broken} break the action rule; {expected} registry-only"
          f" matches (expected for common names); {client.requests} requests")  # fmt: skip
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
