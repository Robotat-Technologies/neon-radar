# resolve: neonradar_resolve

- Purpose: entity resolution (PHASE-2.md 7.1). M2.10a: records.py (C1 files, context, hints),
  policy.py (flag topics, kinds), features.py (members, feature tables), rules.py (D1 to D7),
  cluster.py and feature_schema.py (verbatim from the spec), run.py (run folder), bench.py
  (benchmark measures), config.py (resolve/config/er.yaml). M2.10b adds the Splink models.
- Owner: graph and entity resolution squad (nr-graph).
- Depends on: contracts, graph (mapping tables only, never the database), keys, splink,
  duckdb, pyarrow, followthemoney. Never imports neonradar_ingest or neonradar_cli.
- Commands: `uv run pytest resolve/tests`, `uv run neonradar er run --profile demo`,
  `uv run neonradar er bench --size small`.
- Traps:
  - Splink 5 only: `db_api.register(...)`, then `Linker(sdf, settings)`; no Splink 4 code.
  - An empty DuckDB list is not NULL; DuckDB memory and threads go on `duckdb.connect`.
  - Never read the entity from a record id: benchmark truth lives in labels/er_truth.csv.
  - Humans label (G10): never write, pre-fill or infer labels or decisions.
  - Rules in .claude/rules/er.md and .claude/rules/real-data.md.
