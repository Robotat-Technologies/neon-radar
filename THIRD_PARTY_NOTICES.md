# Third-party notices

NeonRadar is licensed under the Apache License 2.0 (`LICENSE`, `NOTICE`). It depends on third-party software and, from Phase 2, reuses third-party data and code. This file has one section per third-party work whose notice the project must carry or whose licence needs a decision, starting with the dependencies under licences other than permissive ones. The other packages the project installs are under permissive licences (MIT, BSD, ISC, Apache-2.0, 0BSD and similar); the pull request that adds a dependency lists its licence, which the package metadata states (`uv pip show <name>`, `npm view <name> license`). No Python or npm dependency under a GPL or AGPL licence is added (`CLAUDE.md`); the Neo4j Community Edition server (GPLv3, run from the official Docker image) and its Graph Data Science plugin (below) run as a separate database that each user's machine downloads.

The tech lead owns this file (`.github/CODEOWNERS`). Decisions about licences are recorded in `docs/build/operator-decisions.md` and made by people, never by the build agent.

Later milestones add sections: M2.6 for code ported from MIT-licensed sanctions-list crawlers, and M2.8 for `ar_symbols.json.gz` (built from rigour's MIT-licensed data, whose names come from Wikidata) and `nationalities.csv` (built from Open Government Licence inputs).

## python-stdnum

| | |
|---|---|
| What | A Python library that parses and validates standard numbers and codes (for example LEIs, VAT numbers and IBANs) |
| Version | 2.2 (locked in `uv.lock`) |
| Licence | GNU Lesser General Public License, version 2.1 or later (LGPL-2.1-or-later) |
| Copyright | Arthur de Jong and contributors |
| Source | https://github.com/arthurdejong/python-stdnum/ and https://arthurdejong.org/python-stdnum/ |
| Why NeonRadar needs it | Required by FollowTheMoney (`neonradar-contracts`, `neonradar-ingest`, `neonradar-graph`) and by rigour (`neonradar-keys`); NeonRadar does not import it directly |
| How it is used | Unmodified, installed from PyPI by `uv sync` as a separate package; NeonRadar links to it only through Python imports |
| Decision | Accepted as an unmodified library installed from PyPI (`docs/build/PHASE-2.md` 0.5 item 14 and 1.2; operator decision OD-20, 22 October 2026) |

The repository ships no copy of python-stdnum. If NeonRadar ever publishes an image, an archive or another bundle that contains python-stdnum, that bundle must include the text of the LGPL version 2.1 and either the library's source code or a written offer to provide it, and must allow the recipient to replace the library with a modified version.

## Neo4j Graph Data Science

| | |
|---|---|
| What | The Graph Data Science library (GDS) for Neo4j, a database plugin (a Java jar) |
| Version | 2.13.4 (pinned with its SHA-256 in `scripts/fetch_gds.sh`) |
| Licence | Treated as the GNU General Public License, version 3 (GPLv3) |
| Copyright | Neo4j, Inc. |
| Source | https://github.com/neo4j/graph-data-science |
| Why NeonRadar needs it | Graph algorithms for detection (Phase 3); the local Neo4j instances load it as a plugin |
| How it is used | `make plugins` downloads the jar once, on the user's own machine, into the gitignored `data/cache/neo4j-plugins/`, and checks its SHA-256. Docker Compose mounts it read-only into the Neo4j containers (`compose.yaml`). CI downloads it the same way and caches it on GitHub. NeonRadar's Python code talks to it only through Cypher procedure calls (`CALL gds.*`) over the Neo4j driver |
| Decision | Treated as GPLv3; never committed to the repository and never redistributed by the project (operator decision OD-20, 22 October 2026; operator decision OD-13 for the pinned download) |

The repository holds no copy of the jar. If NeonRadar ever publishes an image or bundle that contains GDS, the GPLv3 terms apply to that distribution, and the decision must be revisited first.
