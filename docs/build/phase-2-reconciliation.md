# Phase 2 reconciliation

| | |
|---|---|
| File | `docs/build/phase-2-reconciliation.md` (PHASE-2.md M2.0 deliverable 1) |
| Reconciled against | `main` at `f3b55c9` (22 October 2026, after #31, #32, #35, #38, #41 and #42 merged), plus the open Phase 1 pull requests, read but not relied on |
| Written by | The M2.0 build agent; the tech lead owns it |
| Gate 1 | **Not passed** (operator decision OD-18: Phase 2 starts before Gate 1). No tag `contracts-v1.0.0`, no `docs/build/reports/phase-1.md` |

PHASE-2.md was written on 18 October, before Gate 1. This file lists every place found where it and what Phase 1 built differ, and what happens about each (PHASE-2.md 0.6). **Mechanical** differences (a name, a path, an id form) follow Phase 1 or the measured fact, and are noted here. **Behavioural** ones (they would change behaviour, a contract or a guardrail) are questions for the tech lead or the data steward; the milestone named in the row waits for the answer, M2.0 does not. Items that depend on an open Phase 1 pull request are marked **pending #n**.

Line numbers refer to `docs/build/PHASE-2.md`. Code paths under `ingest/src/neonradar_ingest/sources/` are shortened to `sources/`.

## 1. The Phase 1 inputs (PHASE-2.md 0.6)

| PHASE-2.md expects | On `main` | Consequence |
|---|---|---|
| Tag `contracts-v1.0.0`, `make contracts-check` green | No tag. `make contracts-check` is green. Without the tag, `.claude/hooks/guard-contracts.sh` and `scripts/check_contract_paths.py` do not enforce the freeze yet | M2.0 does not touch `contracts/**` or `graph/schema/**`. M2.1a to M2.1c wait for the tag, which the operator creates (OD-5, OD-18) |
| `docs/build/reports/phase-1.md` | **Missing.** The Gate 1 check (`neonradar gate check --phase 1`, M1.12-1, #32) is merged; the report follows Gate 1 (M1.12-2) | This reconciliation uses `docs/build/PROGRESS.md`, the spike reports and the code instead. Re-check it against the report when that merges |
| Spike reports for Companies House, GLEIF, ICIJ and OpenSanctions | All four in `docs/data/spikes/`. Companies House: verdict "pending network run" (no `CH_API_KEY` yet). OpenSanctions: blocked on the licence (OD-19) | See rows D6 and D7 |
| Walking skeleton: `make demo-mini`, `make e2e`, loader, migration runner, API, detection runner (M1.9) | On `main`: the migration runner, the demo-mini fixture (M1.8e, #27 and #41), the loader (`graph load`, `stats`, `wipe`; M1.9a, #31), the detection runner and circular-flow detector (M1.9b, #38) and the UI shell (M1.9d, #35). Open: the API endpoints (M1.9c, **#44**) and `make demo-mini` and `make e2e` (M1.9e, **#43**), which still print "available after M1.9" | See section 4 |
| C1 validator, dataset registry, fixture check (M1.6, M1.7a) | Present (`neonradar_contracts.records`, `contracts/datasets.yaml`, `scripts/check_fixtures.py`) | None |
| Deviations in `PROGRESS.md` | Many rows of merged pull requests still say `pr-open` (each row was written before its merge) | Milestone dependencies are checked with `gh pr view <n> --json state`, as 2.2 step 1 allows |

## 2. Differences and decisions

Class: **D** decided, **M** mechanical (noted, no question), **Q** question for the person named, **P** pending an open pull request.

### 2.1 The agent kit, the stack and the repository (this milestone)

| # | PHASE-2.md says | Phase 1 has | Class | Decision |
|---|---|---|---|---|
| A1 | The `scripts/test_hooks.sh` line sets `failed=1` (M2.0 item 4) | `failed` is a counter of failed cases, printed at the end | M | The line reports through the script's own `report` function, so the count stays right and the script still exits non-zero on a failure |
| A2 | CI's `ui` job "already has Node 24" (M2.0 item 11) | `.github/workflows/ci.yml` set Node up only when `ui/package.json` existed (it does since #35) | M | Node is set up unconditionally, with both lock files as the cache key, and the Cypher lint runs before the UI steps |
| A3 | `neo4j-real` with `NEO4J_AUTH=neo4j/${NEO4J_REAL_PASSWORD}` and the same image, plugins, memory and healthcheck as `neo4j` (M2.0 item 5) | `neo4j` guards its password with `${NEO4J_PASSWORD:?...}` | M | Written `${NEO4J_REAL_PASSWORD:-}`: Compose interpolates every service, profile or not, so a `:?` guard would stop `make up` on every machine without a real password (checked with Compose 5.4.0). `make up-real` refuses instead when the password is missing, checks the GDS jar and starts with `--pull never`, like `make up`. `restart: "no"`, and no logs or import mounts: only the `/data` volume the spec names |
| A4 | Same as A3 | **P #19** (M1.5) moves the default instance's password into a Compose secret | P | Whichever of #19 and M2.0 merges second gives `neo4j-real` the same form (a `neo4j_real_password` secret) |
| A5 | The hook checks `.mcp.json` for the real instance by its text (ports, names) | `main` has a literal `bolt://localhost:7687`. **P #19** changes it to `${NEO4J_URI:-bolt://localhost:7687}`, which the hook cannot see through | Q tech lead | Keep the URI literal in `.mcp.json`, or have the hook also check `NEO4J_URI`. Backstop meanwhile: the MCP database is `neo4j`, which the real instance does not have |
| A6 | Templates declare `// lint-values: ...` and write `{{name}}`; convert the circular-flow template in this pull request (M2.0 item 11) | `detect/src/neonradar_detect/queries/circular_flow.cypher` (M1.9b, #38) wrote `->{MIN_HOPS,MAX_HOPS}(`, which the lint reports as an error ("Invalid input 'MIN_HOPS'") | M | Converted in this pull request: header `// lint-values: min_hops=2 max_hops=2,6,8` (bounds the catalog allows), quantifier `->{{{min_hops}},{{max_hops}}}(`; `detectors/circular_flow.py` replaces that quantifier as before, and its test checks that no placeholder is left. The rendered query is unchanged apart from its comments, so its `query_sha256` changes |
| A7 | `validate-records` prints `<file>:<line>: <rule id>: <message>`; for records that are not synthetic it masks quoted values and leaves out the record id (M2.0 item 12) | Prints `RULE id: message` with no file or line; `records.validate_files` keeps no positions | M | The wrapper `cli/src/neonradar_cli/masking.py` numbers the lines itself and calls the frozen `validate_record` and `validate_batch` unchanged. A synthetic record's issue reads `<file>:<line>: RULE <record id>: <message>` (Phase 1's text with its place in front); every other record's reads `<file>:<line>: RULE: <masked message>`. Stricter than the spec: a record counts as synthetic only when its dataset is synthetic **and** its id starts `syn-`, and the spike commands' own validation output goes through the same wrapper, because spike output is real data (G9) |
| A8 | The two agent edits quote PHASE-1.md M1.2 wording | `reviewer.md` wraps the guardrail line over two lines; otherwise the merged text is the PHASE-1.md text | M | Same edits applied to the merged text |
| A9 | "CODEOWNERS regenerated with the rows in 4.3" | `scripts/generate_codeowners.py` holds the ownership map in code | M | The 4.3 rows are added to the script's map, then `.github/CODEOWNERS` is regenerated |
| A10 | Phase 2 dates in 1.3 (`phase_2_start` 26 October, freeze 29 October, labelling 2 November) | `project.yaml` shifted Phase 1 by three working days (`gate_1` 28 October) | M | The 1.3 dates are written as given; all dates are informational (OD-1) |
| A11 | `neonradar data purge --graph` stops `neo4j-real` and deletes its volume (4.5) | New in Phase 2 | M | Note for M2.2: `neo4j-real` keeps its logs inside the container, not on a volume, so the purge also removes the container (`docker compose --profile real rm -sf neo4j-real`) before it deletes the volume. Docker names the volume `neonradar_neo4j-real-data` (the Compose project name `neonradar`, then the volume key) |
| A12 | Rule from now on: every Cypher statement that new or changed code runs lives in a `.cypher` file | Phase 1 runs several statements from Python strings (section 3) | M | They move into files when a later milestone touches that code, not in M2.0 |
| A13 | Deny `Read(./data/cache/real/**)`, `Read(./data/cache/spikes/**)`, `Edit(./data/cache/**)` and `Write(./data/cache/**)` (M2.0 item 2) | Claude Code's permissions documentation (code.claude.com/docs/en/permissions, read 22 October 2026): `./path` and `path` are relative to the current directory, `/path` to the settings source (the primary working directory for project settings), `//path` is absolute. Path rules for `Write` are accepted but never consulted, with a warning at startup; `Edit` rules cover every tool that writes files, and a `Read` deny also blocks writes to the same path | M (2.7: the spec seems wrong, small and mechanical); Q tech lead | The spec's four entries stay as written. `Read(/data/cache/real/**)`, `Read(/data/cache/spikes/**)` and `Edit(/data/cache/**)` are added, so the rules hold wherever the session's current folder is. Question: drop the no-op `Write(./data/cache/**)`, which only causes the startup warning |

### 2.2 Record ids (PHASE-2.md 4.4)

PHASE-2.md 4.4 says a form a Phase 1 spike already chose stays, and `contracts/C1-record.md` is the authority for ids (OD-17): loaders build ids with `make_id(prefix, kind, native)`, which gives `<prefix>-<kind>-<native>`, or `<prefix>-<kind>-<first 20 hex of SHA-1(native)>`. A native id of parts joined with `|` always takes the hash branch, so every hashed id of 4.4 equals `make_id` over its joined parts.

| # | PHASE-2.md says | Phase 1 has | Class | Decision |
|---|---|---|---|---|
| B1 | GLEIF entity `gleif-<LEI>` (631, M2.4 at 3326) | `gleif-lei-<LEI>` (`sources/gleif/mapping.py`, `entity_id`) | M | Follow Phase 1; M2.4 reuses `entity_id()` |
| B2 | ICIJ node `icij-<node_id>`, called the Phase 1 form (634) | `icij-node-<node_id>` (`sources/icij/mapping.py`, `node_id`) | M | Follow Phase 1; M2.5 reuses `node_id()` |
| B3 | OpenSanctions entity `os-<id>`, called the Phase 1 form (643) | `os-ent-<id>` for every schema (`sources/opensanctions/mapping.py`, `record_id`) | M | Follow Phase 1; M2.7 reuses `record_id()` |
| B4 | Address ids hash `address_key` (625, 633); directorship ids hash officer id, company number, role, `appointed_on` (630); GLEIF relationship ids hash child, parent, relationship type (632) | Spike forms differ: Companies House addresses hash the full text; GLEIF addresses are `gleif-addr-<LEI>-legal` and `-hq`; directorships hash company number, appointment id and role; GLEIF ownership hashes child, parent and `direct` or `ultimate` | M | Follow the spec in the production loaders (M2.3a, M2.3c, M2.4). Spike output is never loaded into a graph, so nothing migrates; the address key is what removes duplicate addresses |
| B5 | ICIJ relationship id hashes start, end, `rel_type`, `link` (635, M2.5) | The spike hashes all eight relationship columns, including status, dates and source, and skips exact duplicates | Q tech lead (M2.5) | With the four-part key, rows that differ only in dates or status (a resignation and a re-appointment; the spike measured many `resigned` and `appointed` rows) get one id and fail C1 R4 as duplicates. Recommendation: keep the eight-column key |
| B6 | Sanctions and Parliament ids `uksl-g<group id>`, `uksl-<unique id>`, `ofac-<uid>`, `unsc-<ref>`, `eufsf-<logicalId>`, `ukparl-<member id>` (636 to 642) | `C1-record.md` says every loader id comes from `make_id`, which always has a kind segment. These forms pass R1 but have no kind. (`uksl-un-<ref>`, the `ukparl-pos-` and `-occupancy-` ids, the hashed relationship ids and `common.sanction_id` already fit) | Q tech lead (M2.1a, M2.6a) | Either add kinds (for example `uksl-grp-`, `ofac-party-`), which also changes the verbatim tests of M2.6 and M2.10a that use these forms, or record in C1 1.1.0 that list loaders may use these forms. Nothing is built yet, so nothing migrates |
| B7 | Company numbers normalised as in 7.1.2 (D1), prefix checked (624) | The spikes pad only all-digit numbers and keep prefixed ones as given | M | M2.3 and M2.4 use `neonradar_keys.ids` (M2.8) |

### 2.3 Mapping

| # | PHASE-2.md says | Phase 1 has | Class | Decision |
|---|---|---|---|---|
| C1 | `-as-trust` and `-as-firm` natures become `Control` of type `trust-or-firm`, keeping their band; voting rights keep their band on `Control`; exclusive bound flags; one record per interest (M2.3b) | Every banded share or surplus-asset nature becomes an `Ownership` (trust and firm only in `role`); voting, appointment and influence become `Control` with no band, because C1 1.0 allows the share keys only on `Ownership` (`sources/companies_house/mapping.py`, `classify_nature`) | D | **Decided change** (M2.0 item 1): M2.3b changes the Phase 1 spike's PSC mapping (PHASE-1.md M1.8a) as the spec says. `neonradar spike companies-house` keeps its C1 1.0 mapping |
| C2 | Legal-person PSCs become `Organization` (2534) | `LegalEntity` | M | Follow the spec in M2.3b |
| C3 | PSC and officer service addresses become `Address` records (2532, 3296) | Not loaded: the spike report says "minimised on purpose: no service addresses" | Q data steward (M2.3b, M2.3c) | The spec is explicit, but it reverses a Phase 1 data-minimisation choice; the data steward confirms in the M2.3b review |
| C4 | A PSC with `is_sanctioned: true` gets the topic `sanction` (2539) | Counted only; the spike report calls it a data steward decision under G1 | Q data steward and tech lead (M2.3b) | Confirm before M2.3b: the flag would then come from the register itself, which G8 allows |
| C5 | Ceased PSCs skipped unless `include_ceased`; super-secure kinds and statements to `nr.psc_statements`; a corporate officer is a `Company` when `identification.registration_number` is present; GLEIF legal form, incorporation date, ANNULLED and DUPLICATE records skipped | Ceased PSCs loaded with an end date; super-secure kinds skipped; corporate officers by identification type, raw numbers; raw `registeredAs` | M | Follow the spec (M2.3b, M2.3c, M2.4) |
| C6 | GLEIF other and transliterated names all become `alias` (3332) | Type-aware: a previous legal name goes to `previousName`, and GLEIF's automatic ASCII transliterations are not written, because C1 R10 keeps records as the source wrote them (M1.8b) | Q tech lead (M2.4) | The spec text would load machine transliterations, against C1 R10 (OD-17: the contract wins). Recommendation: keep reading each name's type, as Phase 1 does |
| C7 | `gleif_lei` holds no personal data (3.3) | The GLEIF spike report asks whether `SOLE_PROPRIETOR` records, whose name can be a person's name, are personal data | Q data steward (M2.4) | Decide before the M2.4 real-data run |
| C8 | Every ICIJ `registered_address` link gets the address role `registered` (3385) | The role comes from the link's words (registered, residential, business, service, else unknown); the spike measured many residential and mailing links | Q tech lead (M2.5) | A measured fact contradicts the spec, and `HAS_ADDRESS.role` is C2. Recommendation: keep the Phase 1 rule, and decide whether "mailing" maps to `service` |
| C9 | ICIJ trust and foundation roles become `UnknownLink`; a nominee shareholder becomes `Ownership` with `nr.is_nominee` (3390) | Beneficiary becomes `Ownership`, protector `Directorship`, nominee shareholder `Ownership` without the flag | M | Follow the spec (the spike report asked for this review) |
| C10 | ICIJ `note` never loaded; no address text, `ibcRUC`, `company_type`, `type` or `valid_until` (3375 to 3383) | The spike loads `note` and `valid_until` as notes, `ibcRUC` as a registration number, the two types as legal form, and the address text | M | Follow the spec (data minimisation) |
| C11 | D5 example: one ICIJ `node_id` in two node files gives two records (8136) | Ids do not depend on the file, so the second is an R4 duplicate; the spike keeps the first and counts the rest | Q tech lead (M2.10a) | Either merge them in the loader and drop the ICIJ example from D5, or give each file its own kind so D5 merges them |
| C12 | No rule for ICIJ links whose ends do not fit the property's range | The spike turns them into `UnknownLink`, which strict R4 needs | M | M2.5 keeps it |
| C13 | M2.7 keeps every C1 schema | The OpenSanctions spike did not check how `BankAccount` records meet R8 | M | M2.7 skips and counts a `BankAccount` without an `Ownership` holder in the load |

### 2.4 Headers, formats and measured facts

| # | PHASE-2.md says | Phase 1 measured | Class | Decision |
|---|---|---|---|---|
| D1 | Only two ICIJ header rows are confirmed; entities use `closed_date` (3367, 3375) | All six headers measured (`docs/data/spikes/icij.md` section 2); `nodes-entities.csv` has no `closed_date` and no `type` | M | M2.5 records the six headers as confirmed and counts `closed_date` as absent on entities |
| D2 | ICIJ dates use `%d-%b-%Y` or `%d-%b-%y` (3383) | ISO dates are common too, plus slash and dot forms and years below 1000 that FtM accepts and then rejects | M | M2.5 also accepts ISO and validates every cleaned date, as the spike does |
| D3 | Junk names are those the Phase 1 report lists | The report lists names made only of `?` | M | Use that rule |
| D4 | ICIJ download version from `Last-Modified`; archive size unverified (3367, 7.8) | Measured: 71,935,075-byte archive, members 626,079,368 bytes; the manifest's `source_version` is the archive's `GENERATED_ON_<date>` marker | M | Download version as the spec says; `source_version` from the marker; the measured size goes into the profile notes |
| D5 | Officer lists do not cap at 100 (3.5) | A comment in `sources/companies_house/client.py` and the spike report still call 100 the ceiling; the code pages by items returned | M | Correct the wording when M2.3c touches the client |
| D6 | Spike reports with measured fields and verdicts (0.6) | Companies House: verdict pending a network run; `person_number`, the officer links and the rate-limit headers are checked against documentation and mocks only | P operator | The operator runs the M1.8a network commands once `CH_API_KEY` exists (`access.companies_house_key: pending`), before the M2.3c real-data run |
| D7 | M2.7 runs only under `licensed` or `exempt` (4105) | The Phase 1 gate's `may_write()` is true only for `licensed` | M | M2.7 writes its own rule and reuses only the refusal message |
| D8 | No Phase 2 dataset needs `status: blocked` (902) | `opensanctions_default` is `blocked` | Q tech lead (M2.1a) | Low priority: under OD-19 nothing runs either way |
| D9 | New source modules (`bulk.py`, `psc.py`, `officers.py`, `slice.py`, `golden_copy.py`, `full.py` and others) | Spike modules `client.py`, `mapping.py`, `spike.py`, `archive.py`, `access.py`; no name clashes | M | Reuse the spike helpers: the Companies House client (paging, rate-limit wait), officer and PSC id helpers, GLEIF `entity_id`, ICIJ `node_id` and the conditional archive download, OpenSanctions `record_id` and `read_index` |

### 2.5 Contracts, graph and API

| # | PHASE-2.md says | Phase 1 has | Class | Decision |
|---|---|---|---|---|
| E1 | The network endpoint returns `POSSIBLY_SAME_AS`, and `/paths` accepts it when asked (970, 1052) | C3's `RelationshipType` (`contracts/src/neonradar_contracts/api.py`) lists 16 types without it, and `GraphEdge.type` and the `rel_types` parameter use it | Q tech lead (M2.1c) | Add `POSSIBLY_SAME_AS` to `RelationshipType` in M2.1c; the C3 issue text in 5.0 does not mention it. Otherwise network responses fail validation and `rel_types=POSSIBLY_SAME_AS` is a 422 |
| E2 | Invariant I11: `:PEP` exactly when `role.pep` is in `topics` (exact match), likewise `:RCA` (M2.11) | `graph/src/neonradar_graph/mapping.py` sets `:PEP` and `:RCA` also for sub-topics (`role.pep.*`), `:Sanctioned` only for the exact topic (M1.7b decision, tech lead sign-off at Gate 1) | Q tech lead (M2.11) | Write I11 to match sub-topics for PEP and RCA, or it reports false violations |
| E3 | M2.1a bumps `RECORD` to 1.1.0 and leaves demo-mini alone (2267) | `write_manifest` writes `versions.RECORD`, and `ingest/tests/test_synth_determinism.py` compares the committed demo-mini manifest with a fresh one | M | M2.1a regenerates the demo-mini fixture (`make fixtures`) |
| E4 | `upsert_relationships.cypher`: `MATCH` on `:Entity` and the target label, returns `count(r)` (7724) | `graph/src/neonradar_graph/loader.py` (M1.9a) checks the C2 from and to labels, replaces a relationship whose end moved, and returns dangling rows | Q tech lead (M2.11) | Recommendation: keep Phase 1's label check, move-on-change and dangling rows in the new template |
| E5 | `PAID.ts` is a timezone-aware `datetime` (7665) | The loader passes a string ending in `Z`, turned into a `DATETIME` by `datetime(row.ts)` | M | Follow the spec; still stored as `DATETIME` |
| E6 | `to_node_rows(records, resolution)`; `load(paths, resolution, replace, instance)` (7661 to 7667) | `to_node_rows(records)` returns a `MappingResult`; the loader has `load_files(driver, paths, *, strict, database, batch_size)` | M | Extend the Phase 1 functions; keep `strict` and `MappingResult` |
| E7 | `Instance.DEFAULT` reads the `NEO4J_*` settings (7659) | `Neo4jSettings` in `graph/src/neonradar_graph/client.py` (prefix `NEO4J_`, database `neo4j` by default); `.env.example` has no `NEO4J_DATABASE` | M | Wrap `Neo4jSettings` |
| E8 | Ownership queries run with a 5-second timeout; "Phase 1's subgraph builder" (5.3, M2.12) | API reads go through `GraphConnection.read` with no timeout; no subgraph builder on `main` yet (M1.9c, **#44**) | M, P #44 | Add a timeout to `read`; M2.12 waits for M1.9c |
| E9 | `WHERE $min_share = 0` (1045) | `min_share` is optional and defaults to null | M | Pass `min_share or 0` |
| E10 | M2.1c tests that the meta endpoint serves `real-data-v2.txt` (2336) | `GET /api/v1/meta` returns 501 naming M1.9c on `main` | P #44 | M2.1c waits for M1.9c or defers that test |
| E11 | Real data stays under `data/cache/real/` (4.5, G9) | The detection runner (M1.9b) writes alert audit copies (ids and captions) to `data/runs/<run_id>/` | Q tech lead (Phase 3) | Decide where a run against the real instance writes before Phase 3 detects on real data |
| E12 | `NR_PROJECT_FILE` points the data manager at a test project file (2374) | `neonradar_ingest.spikes.PROJECT_FILE` is fixed | M | M2.2 routes `cache_days` through `load_project()` |

## 3. Cypher that Phase 1 runs from Python strings

From now on every Cypher statement that new or changed code runs lives in a `.cypher` file, so `make cypher-lint` checks it (M2.0 item 11). These move into files when a later milestone touches the code, not in M2.0.

| Where | Statements | Purpose |
|---|---|---|
| `graph/src/neonradar_graph/smoke.py` | `COMPONENTS`, `APOC_VERSION`, `GDS_VERSION` | Neo4j, APOC and GDS versions (`api/src/neonradar_api/health.py` repeats them) |
| `graph/src/neonradar_graph/migrate.py` | `APPLIED`, `RECORD`, `AWAIT_INDEXES` | Applied migrations, the `:SchemaMigration` record, waiting for indexes |
| `graph/src/neonradar_graph/onboarding.py` | `LOAD_NODES`, `LOAD_PARENTS`, `COUNT_NODES`, `RESET` | Assignment 1 (`neonradar onboarding check` also runs the queries in `docs/team/first-queries.md`) |
| `graph/src/neonradar_graph/loader.py` | `APPLIED`, `WIPE`, `STATS`, `node_query()`, `relationship_query()` | Pending-migration check, `graph wipe`, `apoc.meta.stats`, node and relationship upserts built per schema and type |
| `graph/tests/test_invariants.py` | I1 to I6 | Test strings; M2.11's `verify.py` reuses them |
| `detect/src/neonradar_detect/runner.py` | `MERGE_RUN`, `PRUNE_RUN`, `MERGE_ALERTS` | Detection runs and alerts |

The `.cypher` files on `main` are `graph/schema/migrations/0001_init.cypher` and the circular-flow template; `make cypher-lint` checks 32 statements (29 plus the template's three lint variants) with 0 problems. The API queries of M1.9c (**#44**) must be `.cypher` files that pass the lint once M2.0 is merged.

## 4. Open Phase 1 items that block Phase 2 milestones

| Phase 2 milestone | Waits for |
|---|---|
| M2.1a, M2.1b, M2.1c | The tag `contracts-v1.0.0` (operator, OD-5) and the approved contract-change issues (5.0) |
| M2.1c | M1.9c (**#44**: `/meta`, E10); question E1 |
| M2.3c (real-data run) | `CH_API_KEY` and the Companies House network spike run (D6) |
| M2.4, M2.5, M2.6a, M2.10a | Questions C6 and C7, C8 and B5, B6, C11 |
| M2.11 | Questions E2 and E4 (the loader and the detection runner it builds on are merged) |
| M2.12 | M1.9c (**#44**: subgraph builder, entity id lookup, network endpoint) |
| M2.13 | M1.9c (**#44**: `/network` and `/search` in the query benchmark) and M1.9e (**#43**: `make demo-mini`, `make e2e`, the end-to-end workflow) |
| M2.16 | M1.9e (**#43**) for the Gate 2 checks that run the demo, and the Phase 1 report (M1.12-2) |
| M2.0 (this milestone) | Built before Gate 1 under OD-18. **P #19** (M1.5) touches `compose.yaml` and `.mcp.json` (A4, A5) |
| M2.2, M2.3a, M2.3b, M2.6b to M2.6e, M2.7, M2.8, M2.9, M2.10b, M2.10c, M2.14, M2.15 | No open Phase 1 pull request (they still wait for their Phase 2 dependencies, 1.8) |

## 5. Questions, by person

**Tech lead:** A5 (`.mcp.json` and the hook, with #19), A13 (the no-op `Write` deny rule), B5 (ICIJ relationship id key), B6 (list and Parliament id forms against `make_id`), C6 (GLEIF name types and C1 R10), C8 (ICIJ address roles), C11 (D5 and repeated ICIJ node ids), D8 (`opensanctions_default` status), E1 (`POSSIBLY_SAME_AS` in C3), E2 (I11 and sub-topics), E4 (relationship upsert template), E11 (where detection runs on real data write).

**Data steward:** C3 (service addresses), C4 (`is_sanctioned` as a topic, with the tech lead), C7 (GLEIF sole proprietors).

Each question blocks only the milestone named in its row.
