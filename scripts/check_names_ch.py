#!/usr/bin/env python3
"""Check the entity resolution benchmark's names on the Companies House search (OD-12).

A human runs it in a terminal, with `CH_API_KEY` in the environment or `.env`; it refuses to
query when stdin is not a terminal, so an agent cannot spend the key (OD-12). It prints match
flags per name index only, never a search result, and stores nothing, so its output can go into
a pull request as it is:

    uv run python scripts/check_names_ch.py --list   # index, kind, entity id, synthetic name
    uv run python scripts/check_names_ch.py          # index, company=, officer=, surname=, counts

Every distinct name (people: canonical given name and surname; organisations: name and legal
form) goes to the company search and the officer search, at the client's 2 requests per second.
A flag is 1 when a result's title has the same name key (companies: the name without its legal
form; officers: every token of the name among the title's tokens). The invented surnames of
listed and leaked people also go alone to the officer search: `surname=1` when an officer has
that surname, which makes it a real surname (`-` for other names). For a flagged name, add its
entity id to `REDRAW` in `ingest/src/neonradar_ingest/synth/erbench.py` (or a real surname to
`variants.NOT_INVENTED`), run `make fixtures` and check again.
"""

import argparse
import sys

from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house.client import CompaniesHouseClient
from neonradar_ingest.synth import ER_BENCH_SEED
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.erbench import SIZES, build
from neonradar_ingest.synth.names import fold


def bench_names(size: str, seed: int) -> list[tuple[str, str, str, str | None]]:
    """(kind, entity id, name, invented surname or None) for every distinct name, people first."""
    bench = build(size, seed)
    entries = [
        ("person", p.entity_id, f"{p.given.latin[0]} {p.surname.latin[0]}",
         p.surname.latin[0] if p.invented else None)
        for p in bench.people
    ]  # fmt: skip
    entries += [("org", o.entity_id, o.name, None) for o in bench.orgs]
    seen: set[str] = set()
    out = []
    for entry in entries:
        if fold(entry[2]) not in seen:
            seen.add(fold(entry[2]))
            out.append(entry)
    return out


def _titles(client: CompaniesHouseClient, path: str, name: str) -> list[str]:
    body = client.get_json(path, {"q": name, "items_per_page": 20}) or {}
    return [str(item.get("title", "")) for item in body.get("items") or []]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--size", choices=sorted(SIZES), default="small")
    parser.add_argument("--seed", type=int, default=ER_BENCH_SEED)
    parser.add_argument("--list", action="store_true", help="print the names, query nothing")
    args = parser.parse_args(argv)
    names = bench_names(args.size, args.seed)
    if args.list:
        for index, (kind, entity, name, _) in enumerate(names):
            print(f"{index:04d}\t{kind}\t{entity}\t{name}")
        return 0
    if not sys.stdin.isatty():
        print("check_names_ch: run it yourself in a terminal (OD-12)", file=sys.stderr)
        return 2
    key = IngestSettings().companies_house_key()
    if key is None:
        print("check_names_ch: CH_API_KEY is not set", file=sys.stderr)
        return 2
    flagged = 0
    with CompaniesHouseClient(key) as client:
        for index, (_, _, name, invented) in enumerate(names):
            company = any(
                name_key(t) == name_key(name) for t in _titles(client, "/search/companies", name)
            )
            tokens = set(fold(name).split())
            officer = any(
                tokens <= set(fold(t).split()) for t in _titles(client, "/search/officers", name)
            )
            surname = "-"
            if invented:
                titles = _titles(client, "/search/officers", invented)
                surname = str(int(any(fold(invented) in fold(t).split() for t in titles)))
            flagged += company or officer or surname == "1"
            flags = f"company={int(company)}\tofficer={int(officer)}\tsurname={surname}"
            print(f"{index:04d}\t{flags}", flush=True)
    print(f"{len(names)} names checked; {flagged} with a match; {client.requests} requests")
    return 1 if flagged else 0


if __name__ == "__main__":
    sys.exit(main())
