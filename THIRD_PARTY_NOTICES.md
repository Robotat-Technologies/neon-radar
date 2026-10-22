# Third-party notices

NeonRadar is licensed under the Apache License 2.0 (`LICENSE`, `NOTICE`). It depends on third-party software and, from Phase 2, reuses third-party data and code. This file has one section per third-party work whose notice the project must carry or whose licence needs a decision, starting with the dependencies under licences other than permissive ones. The other packages the project installs are under permissive licences (MIT, BSD, ISC, Apache-2.0, 0BSD and similar); the pull request that adds a dependency lists its licence, which the package metadata states (`uv pip show <name>`, `npm view <name> license`). No Python or npm dependency under a GPL or AGPL licence is added (`CLAUDE.md`); the Neo4j Community Edition server (GPLv3, run from the official Docker image) and its Graph Data Science plugin (below) run as a separate database that each user's machine downloads.

The tech lead owns this file (`.github/CODEOWNERS`). Decisions about licences are recorded in `docs/build/operator-decisions.md` and made by people, never by the build agent.

M2.8 added the sections for `ar_symbols.json.gz` (built from rigour's MIT-licensed data, whose names come from Wikidata) and `nationalities.csv` (built from Open Government Licence inputs). M2.6 adds a section for code ported from MIT-licensed sanctions-list crawlers.

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

## Arabic name index (`keys/src/neonradar_keys/data/ar_symbols.json.gz`)

| | |
|---|---|
| What | An index from Arabic-script name forms, normalised with `neonradar_keys.arabic.ar_normalize`, to the Wikidata ids (QIDs) of the name groups they belong to; `neonradar_keys.symbols.arabic_symbols` reads it |
| Built from | `rust/data/names/person_names.txt` in rigour at tag `v2.5.0` (SHA-256 `be47a435969da3fa7311d8c682e462d6d20e6cf27cf90ad1473ce213c9a91c79`), the tag that matches the `rigour==2.5.*` pin |
| Licence | MIT License (rigour); the name data in rigour's file comes from Wikidata (CC0 1.0) |
| Copyright | Copyright (c) 2023-2025: OpenSanctions Datenbanken GmbH |
| Source | https://github.com/opensanctions/rigour |
| How it is made | `uv run python keys/scripts/build_ar_symbol_index.py --tag v2.5.0 --sha256 be47a435969da3fa7311d8c682e462d6d20e6cf27cf90ad1473ce213c9a91c79` downloads the file from `raw.githubusercontent.com/opensanctions/rigour`, checks its SHA-256 and writes 17,798 keys. The gzip header carries no timestamp, so a rebuild gives the same file (SHA-256 `7712414a8eb9b07cf7e2814ffd8d1460ae1c35a834a17a5ce39099f41f56f7e8`). It is rebuilt whenever the locked rigour version changes (`docs/build/PHASE-2.md` M2.8) |
| Where it goes | Committed in the repository and packaged in the `neonradar-keys` wheel. The project publishes no wheel yet; a published wheel or image that contains the file must also carry this notice |

The file holds name forms and Wikidata ids of name groups (for example محمد maps to `Q5837762`, the name group that rigour also gives Mohammed and Мухаммед), not records about people. rigour's licence:

```text
MIT License

Copyright (c) 2023-2025: OpenSanctions Datenbanken GmbH

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Nationalities table (`keys/src/neonradar_keys/data/nationalities.csv`)

| | |
|---|---|
| What | 236 nationality values (Companies House nationality values and FCDO citizen names) mapped to lower-case ISO 3166-1 alpha-2 codes; `neonradar_keys.countries.country_code` reads it |
| Derived from | The Companies House list of nationalities ("Nationalities and countries for company filings") and the citizen names of the FCDO Geographical Names Index |
| Licence | Open Government Licence v3.0 (both sources): https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ |
| Attribution | "Contains public sector information licensed under the Open Government Licence v3.0." |
| How it is made | `keys/scripts/build_nationalities.py` maps the two lists to codes with rigour (no fuzzy matching) and its own overrides (UK nations to `gb`, and values rigour maps wrongly or not at all). The two inputs are not in the repository; the committed file is the one in `docs/build/PHASE-2.md` M2.8, and the script is run again only when either list changes |
| Where it goes | Committed in the repository and packaged in the `neonradar-keys` wheel |

Contains public sector information licensed under the Open Government Licence v3.0.

## UK Sanctions List schema (`ingest/tests/fixtures/lists/gb_fcdo_sanctions/SanctionsListSchema-4.33.3.xsd`)

| | |
|---|---|
| What | The XML Schema of the UK Sanctions List, version 4.33.3; it describes the file's structure and holds no personal data |
| Source | https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd, linked from the publication page https://www.gov.uk/government/publications/the-uk-sanctions-list (downloaded on 22 October 2026, SHA-256 `bccc15735fac55c235855fcfb8017ed3b75369854c63c60f2bb81a6132f8426d`) |
| Terms | The notice at the top of the file: it may be copied, used and distributed "for the purpose of developing, testing, or implementing compatible systems", provided that no modifications are made to the schema structure or namespace identifiers, the notice is retained, the schema is not misrepresented as originating from another source, and it is not "used for commercial resale or as part of a paid service without prior consent". The GOV.UK page that links it carries the Open Government Licence v3.0 "except where otherwise stated" |
| How it is used | Test input only: `ingest/tests/test_lists_gb_fcdo_sanctions.py` validates the synthetic fixture against it, offline (`xmlschema`, `allow="sandbox"`). It is committed unchanged (`.gitattributes` keeps its bytes) and is not part of any package |
| Where it goes | Committed in the repository under `ingest/tests/fixtures/`; never shipped in a wheel or image. The data steward confirms in the M2.6a review that these terms suit the repository |
