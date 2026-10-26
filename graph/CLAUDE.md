# graph: neonradar_graph

- Purpose: the Neo4j client and settings, schema migrations (`graph/schema/`, frozen at
  Gate 1), the C1 record loader and, in Phase 2, entity resolution.
- Owner: graph squad (nr-graph); `graph/schema/` also needs the tech lead.
- Depends on: C1 records (input) and C2 graph schema (output).
- Commands: `uv run pytest graph/tests`, `make test-int`, `make up`, `make smoke`,
  `uv run neonradar graph migrate`, `graph load --profile demo --resolution latest` and
  `graph verify` (I1 to I14; `--real` on migrate, verify, stats and wipe runs the real-data gate).
- Modules: `mapping` (C1 records plus an optional resolution run to C2 loader rows, pure; the
  mapping data lives in `neonradar_contracts.graph`), `migrate` (the migration runner),
  `client`, `smoke`, `onboarding` (the Assignment 1 sandbox: `Onb*` labels only, never part of
  C2), `loader` (`neonradar graph load|stats|wipe`: `load(paths, resolution, replace,
  instance)`, `load_files`, `load_records`, `plan_load` without a database, `execute_plan`,
  `wipe`, `stats`), `resolution` (`ResolutionMap.load(run_dir)`: canonical.csv,
  candidates.jsonl, run.json), `instances` (`Instance.DEFAULT` and `Instance.REAL`, L17),
  `cypher` (reads `queries/*.cypher` and fills `{{rel_type}}`-style placeholders with C2 names,
  or with a value the file's `lint-values` header lists, such as `max_hops`; never with data),
  `verify` (`graph verify`), `wording` (the resolution and possible-match texts of PHASE-2.md
  7.2, verbatim; pure, no Splink, so the API and `er review` share them;
  `scripts/check_wording.py` scans it), `shapes` (C2 rows to C3 models with property allow-lists
  from `neonradar_contracts.graph`, and Phase 1's subgraph builder; moved from `neonradar_api`
  in M2.12), `ownership` (M2.12: `ownership()` and `paths()` of C3 1.1.0, `resolve_id`, the
  `read` helper with the 5-second timeout and READ routing; ADR-0019), `readonly` (M4.1:
  `run_read`, the one way Phase 4 code reads Neo4j: READ session, explicit transaction with a
  timeout and metadata naming the query, `max_rows + 1` fetched, never committed, summary
  checked, `ReadRefused`; ADR-0026; unit-tested on `tests/fakeneo4j.py`). Every new Cypher
  statement lives in `queries/`; the files PHASE-2.md M2.11 gives are verbatim except three
  (phase-2-reconciliation 2.9, J1, J2).
- Integration tests of every suite share one Neo4j per session (`tests/support/nr_test_neo4j.py`,
  a pytest plugin the root `conftest.py` registers once; fixtures `neo4j`, `empty_neo4j`,
  `graph_db`): a Testcontainers container with the GDS jar from `make plugins` copied in, or
  `NR_TEST_NEO4J_URI` (wiped; refused if it holds any node but `:SchemaMigration` unless
  `NR_TEST_ALLOW_WIPE=1`). Import `Neo4jTarget` and `pinned_gds` from it (or from
  `tests/conftest.py`), never the fixtures, or pytest starts a second database. The container
  runs under `compose.yaml`'s procedure allowlist and `db.memory.transaction.max` (M4.1).
- Settings: `neonradar_graph.client.Neo4jSettings` (env vars win over the root `.env`,
  `extra="ignore"`); every package's settings follow this pattern. `get_driver()`.
- Traps:
  - neo4j driver 6: `execute_read` / `execute_write`; `read_transaction` is gone.
  - `CALL { } IN TRANSACTIONS` needs an auto-commit `session.run()`.
  - Community Edition: uniqueness constraints only.
  - Never edit an applied migration; add a new one. One statement per line, ending in `;`,
    always `IF NOT EXISTS`.
  - Labels and types come from `neonradar_contracts.graph`, never from data.
  - testcontainers: `from testcontainers.community.neo4j import Neo4jContainer`.
  - Loader: strict by default (a C1 issue or MappingIssue refuses the load before anything is
    written; a dangling reference found while writing fails it); non-strict never maps a
    record that failed C1 and drops an account left without HOLDS_ACCOUNT (R8). It needs the
    migrated schema (`graph_db` fixture in tests).
  - Reload is an upsert: mapped properties a record dropped are removed (sent as null), flags
    follow the record both ways, and a relationship whose end or type changed moves (an
    Ownership between OWNS, CONSOLIDATES and HOLDS_ACCOUNT); one whose new end is missing is
    deleted and reported as dangling. Removed
    records, dropped `addressEntity` or `Sanction.entity` values (their HAS_ADDRESS and
    SUBJECT_OF stay) and old schema labels stay until `graph wipe --yes`. Invariants I1 to I5
    are guaranteed after wipe then load: wipe before loading a regenerated synthetic dataset.
  - One transaction per 5,000-row batch: a database error part-way leaves earlier batches
    committed; running the same load again completes it (idempotent).
  - Tests derive expected rows from `mapping` and the fixture files, never from hard-coded
    demo-mini names or counts (the fixture is regenerated).
  - L17: real records only into the real-data instance (database `realdata`), synthetic ones
    only into the default instance; checked on the records before connecting and again on the
    rows in `execute_plan`, keyed by the database name. Tests build non-synthetic look-alikes
    in code and load them only into a second container started with
    `NEO4J_initial_dbms_default__database=realdata` (`test_loader_resolution.py`). The one
    exception is detection case F (`detect/tests/test_circular_flow_neo4j.py`, reconciliation
    J7), which writes its look-alike holder itself and is skipped when `NR_TEST_NEO4J_URI` is
    set, so the look-alike only reaches a Testcontainers database.
  - Resolved loads (L8 to L16): single-record entities keep their record id; merged ones get
    `nr-<anchor>` plus one `:SourceRecord` and `RESOLVED_TO` per member. A load with a run first
    purges what it replaces (`--no-replace` skips it), so `written` is not 0 on a reload; the
    counts are (L16). Run `graph verify` after a load.
  - `PAID.ts` is a timezone-aware `datetime` in the row's props, never a string.
  - `followthemoney.ValueEntity.from_dict` pops keys from the dict it gets: pass a copy.
  - The neo4j driver imports PyArrow when it is installed; the graph package itself never
    imports the resolver, PyArrow, DuckDB or Splink (`graph`'s `dev` group has the resolver
    for the integration tests' runs, `tests/conftest.py` `demo_resolution`).
