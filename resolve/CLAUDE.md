# resolve: neonradar_resolve

- Purpose: entity resolution: features, deterministic rules D1 to D7, cannot-link rules X1 to
  X8, Splink 5 models, constrained clustering, the merge policy P1 to P6, decisions,
  labelling and the precision report. Empty until M2.10a (PHASE-2.md 7.1).
- Owner: graph and entity resolution squad (nr-graph).
- Depends on: contracts, graph (mapping tables only, never the database), keys, splink,
  duckdb, pyarrow. Never imports neonradar_ingest or neonradar_cli.
- Commands: `uv run pytest resolve/tests`.
- Traps:
  - Splink 5 only: `db_api.register(...)`, then `Linker(sdf, settings)`; no Splink 4 code.
  - An empty DuckDB list is not NULL; DuckDB memory and threads go on `duckdb.connect`.
  - Humans label (G10): never write, pre-fill or infer labels or decisions.
  - Rules in .claude/rules/er.md and .claude/rules/real-data.md.
