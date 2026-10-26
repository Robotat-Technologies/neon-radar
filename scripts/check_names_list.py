#!/usr/bin/env python3
"""Check a list of fixed synthetic names on the Companies House search (OD-12).

The companion of `check_names_ch.py` for names written by hand into tests, fixtures and docs: it
sends each name of a list to the same company and officer searches and applies the same match
rules. A human runs it in a terminal, with `CH_API_KEY` in the environment or `.env`; it refuses
to query when stdin is not a terminal, so an agent cannot spend the key. It prints match flags
per index only, never a name or a search result, and stores nothing, so its output can go into
a pull request as it is:

    uv run python scripts/check_names_list.py FILE --list   # index, kind, name, source
    uv run python scripts/check_names_list.py FILE          # index, company=, officer=, counts

FILE is UTF-8 text with one name per line. Blank lines and lines starting with `#` are skipped,
and a trailing ` # comment` (where the name comes from) is kept only for `--list`. An optional
tab-separated second column gives the kind: `company`, `person` or `place`; without it a name
that ends in a legal form is a company and any other name a person. A name repeated (same
`fold`) is checked once.

Every name goes to the company search and the officer search. A flag is 1 when a result's title
has the same name key as the name (`check_names_ch.py`: companies, the name without its legal
form, "&" read as "and"; officers, every token of the name among the title's tokens). Names in
Cyrillic or Arabic script are not sent (`skipped=script`): the search is Latin-script, so the
list gives their Latin spelling on a line of its own.

Action rule:
- Every flag must be 0 for a company or person name: rename a name with a flag, add the real
  name to `ingest/src/neonradar_ingest/synth/denylist.txt` when it is a public figure's, and
  check the new name again.
- A flag on a place means a company or officer shares the place's name; check that the place
  itself is invented. Places never break the rule.
The exit code is 1 when the rule is broken, 2 when the run did not start or a search failed (the
message gives the HTTP status only, never the query).
"""

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
from check_names_ch import OTHER_SCRIPT, Query, _flags

from neonradar_ingest.http import HttpError
from neonradar_ingest.settings import IngestSettings
from neonradar_ingest.sources.companies_house.client import CompaniesHouseClient
from neonradar_ingest.synth.companies import name_key
from neonradar_ingest.synth.names import fold

KINDS = ("company", "person", "place")
COMMENT = re.compile(r"\s+#.*$")


class ListError(ValueError):
    """A line of the list that cannot be read; the message names the line number, never text."""


@dataclass(frozen=True, slots=True)
class Name:
    text: str
    kind: str  # company, person or place
    source: str  # the trailing comment: where the name comes from


def default_kind(text: str) -> str:
    """`company` when the name ends (or starts) with a legal form, otherwise `person`."""
    return "company" if name_key(text) != fold(text) else "person"


def read_names(path: Path) -> list[Name]:
    """The list's names in file order, each distinct `fold` once."""
    names: list[Name] = []
    seen: set[str] = set()
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip() or line.strip().startswith("#"):
            continue
        source = ""
        if comment := COMMENT.search(line):
            source = comment.group(0).strip().removeprefix("#").strip()
            line = line[: comment.start()]
        text, _, kind = line.partition("\t")
        text, kind = text.strip(), kind.strip()
        if not text:
            raise ListError(f"line {number}: no name before the tab")
        kind = kind or default_kind(text)
        if kind not in KINDS:
            raise ListError(f"line {number}: the kind is not one of {', '.join(KINDS)}")
        if fold(text) not in seen:
            seen.add(fold(text))
            names.append(Name(text, kind, source))
    return names


def check(names: list[Name], client: CompaniesHouseClient) -> int:
    """Search every name, print its flags by index and the counts; 1 when the rule is broken."""
    broken = places = skipped = 0
    for index, name in enumerate(names):
        if OTHER_SCRIPT.search(name.text):
            skipped += 1
            print(f"{index:04d}\tskipped=script", flush=True)
            continue
        query = Query(name.kind, "", "fixed", "name", "", name.text)
        company, officer = _flags(client, query)
        if company or officer:
            if name.kind == "place":
                places += 1
            else:
                broken += 1
        print(f"{index:04d}\tcompany={int(bool(company))}\tofficer={int(officer)}", flush=True)
    print(f"{len(names)} names; {broken} company or person names match (rename them, OD-12);"
          f" {places} places match (check that the place is invented); {skipped} not in Latin"
          f" script (not sent); {client.requests} requests")  # fmt: skip
    return 1 if broken else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("file", type=Path, help="UTF-8 text, one name per line")
    parser.add_argument(
        "--list", action="store_true", help="print the numbered names, send nothing"
    )
    args = parser.parse_args(argv)
    try:
        names = read_names(args.file)
    except (OSError, UnicodeDecodeError, ListError) as error:
        print(f"check_names_list: {error}", file=sys.stderr)
        return 2
    if args.list:
        for index, name in enumerate(names):
            print(f"{index:04d}\t{name.kind}\t{name.text}\t{name.source}")
        return 0
    if sys.stdin is None or not sys.stdin.isatty():
        print("check_names_list: run it yourself in a terminal (OD-12)", file=sys.stderr)
        return 2
    key = IngestSettings().companies_house_key()
    if key is None:
        print("check_names_list: CH_API_KEY is not set", file=sys.stderr)
        return 2
    with CompaniesHouseClient(key) as client:
        try:
            return check(names, client)
        except (HttpError, httpx.HTTPError) as error:  # its message holds the query: not shown
            status = getattr(error, "status", None) or "no response"
            print(f"check_names_list: a search failed (HTTP {status}); the indexes above were"
                  " checked, nothing after them", file=sys.stderr)  # fmt: skip
            return 2


if __name__ == "__main__":
    sys.exit(main())
