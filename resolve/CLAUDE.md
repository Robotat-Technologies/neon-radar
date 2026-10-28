# resolve: neonradar_resolve

- Purpose: entity resolution (PHASE-2.md 7.1). M2.10a: records.py (C1 files, context, hints),
  policy.py (flag topics, kinds), features.py (members, feature tables), rules.py (D1 to D7),
  cluster.py and feature_schema.py (verbatim from the spec), run.py (run folder), bench.py
  (benchmark measures), config.py (resolve/config/er.yaml). M2.10b: models.py (verbatim
  except the person training sessions, OD-26), scoring.py (counts, training, pairs.parquet),
  calibrate.py (threshold sweep), resolve/models/*.settings.json (settings only, regenerated
  by a test's one-liner).
- Owner: graph and entity resolution squad (nr-graph).
- Depends on: contracts, graph (mapping tables only, never the database), keys, splink,
  duckdb, pyarrow, followthemoney. Never imports neonradar_ingest or neonradar_cli.
- Commands: `uv run pytest resolve/tests`, `uv run neonradar er run --profile demo`,
  `uv run neonradar er bench --size small` (the G2-05 gates), `er blocking --profile demo`,
  `er calibrate --size large` (writes docs/data/er/benchmark.md; never edits er.yaml).
- Traps:
  - Splink 5 only: `db_api.register(...)`, then `Linker(sdf, settings)`; no Splink 4 code.
  - An empty DuckDB list is not NULL; DuckDB memory and threads go on `duckdb.connect`.
  - Tests and the benchmark use one DuckDB thread; `run.guard_decisions` and
    `cluster.resolve` get one list object of probabilistic links.
  - Every Splink comparison level needs a fixed `label_for_charts`, never a literal value:
    labels go into `pairs.parquet`, `candidates.jsonl` and Splink's own warnings.
  - Build a Splink `Linker` only inside `scoring.splink_warnings()`: on a `splink` logger without
    handlers, Splink installs its own stderr handler, which bypasses the run's summary.
  - Person EM sessions (OD-26): postcode first, then the first linked organisation with the
    birth year. A session blocked on surname and birth year is full of near twins, and in
    the other order Splink's EM drove a birth level's m to exactly 0 and refused it.
  - Only `scoring.UNTRAINABLE` (exact classes, no DuckDB error in the chain) means a model
    cannot be trained; synthetic profiles skip the class, real profiles fail (OD-10).
  - Never read the entity from a record id: benchmark truth lives in labels/er_truth.csv.
  - Policy-blocked gate (OD-27): pass `RunResult.name_only` to `bench.measure` and
    `calibrate.sweep`; without it every policy-blocked pair counts in the gate (fail closed).
    It is empty on real-data runs. A new feature column counts as evidence until it is added
    to `features.NAME_COLUMNS` (a test pins `EVIDENCE_COLUMNS`); an empty gate fails.
  - Humans label (G10): never write, pre-fill or infer labels or decisions.
  - Rules in .claude/rules/er.md and .claude/rules/real-data.md.
