# graph: neonradar_graph

- Purpose: the Neo4j client and settings, schema migrations (`graph/schema/`, frozen at
  Gate 1), the C1 record loader and, in Phase 2, entity resolution.
- Owner: graph squad (nr-graph); `graph/schema/` also needs the tech lead.
- Depends on: C1 records (input) and C2 graph schema (output).
- Commands: `uv run pytest graph/tests`, `make test-int`, `make up` and `make smoke`.
- Traps:
  - neo4j driver 6: `execute_read` / `execute_write`; `read_transaction` is gone.
  - `CALL { } IN TRANSACTIONS` needs an auto-commit `session.run()`.
  - Community Edition: uniqueness constraints only.
  - Never edit an applied migration; add a new one.
  - testcontainers: `from testcontainers.community.neo4j import Neo4jContainer`.
