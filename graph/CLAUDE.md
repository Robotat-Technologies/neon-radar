# graph: neonradar_graph

- Purpose: the Neo4j client and settings, schema migrations (`graph/schema/`, frozen at
  Gate 1), the C1 record loader and, in Phase 2, entity resolution.
- Owner: graph squad (nr-graph); `graph/schema/` also needs the tech lead.
- Depends on: C1 records (input) and C2 graph schema (output).
- Commands: `uv run pytest graph/tests`, `make test-int`, `make up`, `make smoke` and
  `uv run neonradar graph migrate`.
- Modules: `mapping` (C1 records to C2 loader rows, pure; the mapping data lives in
  `neonradar_contracts.graph`), `migrate` (the migration runner), `client`, `smoke`,
  `onboarding` (the Assignment 1 sandbox: `Onb*` labels only, never part of C2), `loader`
  (`neonradar graph load|stats|wipe`: C1 files to the graph; `load_files`, `load_records`,
  `plan_load` without a database, `wipe`, `stats`).
- Integration tests of every suite share one Neo4j per session (`tests/support/nr_test_neo4j.py`,
  a pytest plugin the root `conftest.py` registers once; fixtures `neo4j`, `empty_neo4j`,
  `graph_db`): a Testcontainers container with the GDS jar from `make plugins` copied in, or
  `NR_TEST_NEO4J_URI` (wiped; refused if it holds any node but `:SchemaMigration` unless
  `NR_TEST_ALLOW_WIPE=1`). Import `Neo4jTarget` and `pinned_gds` from it (or from
  `tests/conftest.py`), never the fixtures, or pytest starts a second database.
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
