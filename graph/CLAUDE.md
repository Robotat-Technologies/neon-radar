# graph: neonradar_graph

- Purpose: the Neo4j client and settings, schema migrations (`graph/schema/`, frozen at
  Gate 1), the C1 record loader and, in Phase 2, entity resolution.
- Owner: graph squad (nr-graph); `graph/schema/` also needs the tech lead.
- Depends on: C1 records (input) and C2 graph schema (output).
- Commands: `uv run pytest graph/tests`, `make test-int`, `make up`, `make smoke` and
  `uv run neonradar graph migrate`.
- Modules: `mapping` (C1 records to C2 loader rows, pure; the mapping data lives in
  `neonradar_contracts.graph`), `migrate` (the migration runner), `client`, `smoke`,
  `onboarding` (the Assignment 1 sandbox: `Onb*` labels only, never part of C2).
- Integration tests share one Neo4j (`tests/conftest.py`): a Testcontainers container with the
  GDS jar from `make plugins` copied in, or `NR_TEST_NEO4J_URI` (wiped; refused if it holds
  any node but `:SchemaMigration` unless `NR_TEST_ALLOW_WIPE=1`).
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
