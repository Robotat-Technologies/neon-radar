# detect: neonradar_detect

- Purpose: the typology catalog (`detect/typologies/*.yaml`, read by `catalog.py`), detectors
  (`detectors/<slug>.py`) over candidate steps (`source.py`: `neo4jsource.py` runs
  `queries/<step>.cypher`, `memsource.py` is the in-memory oracle over `graphrows.py`), R-REAL
  (`policy.py`), alert building (`alerts.py`), wording and its run-time lint (`wording.py`,
  `wording_lint.py`), the runner (`runner.py`) and runs (`runs.py`: run folder, the L19 store
  in `store/*.cypher`, verify-alert; `neonradar detect run|list|verify-alert`).
- Owner: detect squad (nr-detect); typology definitions belong to typology researchers.
- Depends on: C2 graph schema (reads only C2 labels, types and properties) and C4 alerts;
  pyyaml (the catalog); the neo4j driver. Detectors never import `neonradar_ingest`.
- Commands: `uv run pytest detect/tests`, `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests
  -m "not integration"` (every detector test on Neo4j), `uv run pytest -m integration
  detect/tests/`, `uv run neonradar detect run [--profile P] [--typology S]... [--engine
  neo4j|memory] [--window START END] [--keep-previous]`, `neonradar detect verify-alert --run
  latest`, `uv run neonradar docs typology-index [--check]`.
- Traps:
  - Verbatim files come from `docs/build/PHASE-3-CODE.md` (`scripts/spec_extract.py`); a
    mechanical change goes into `docs/build/phase-3-deviations.json`. `wording.py` (Phase 1's
    `render_headline`, R1) and `alerts.py` (`"window": null`, A2) carry recorded deviations.
  - A change to a query file or to `neo4jsource.py` needs the same change in `memsource.py`
    and both test modes. `queries/` holds exactly the 33 detection files; the store's
    statements live in `store/`.
  - Detectors never read names (reconciliation D1): no row type has a name field; only
    `node_info` returns captions, for the wording after the policy (`test_no_name_reads.py`).
  - Patterns, not accusations: every text is rendered from the typology file and linted by
    `wording_lint.violations` with captions masked as whole tokens; a `WordingError` names the
    typology, the part and the pattern, never the text. scripts/check_wording.py lints the
    string literals of `wording.py`.
  - `catalog.load()` (the frozen `Typology` view) refuses a detector typology without
    `shape_name`, a format spec, a stray brace, and a shape name or template that fails
    `wording_lint.violations`; `TypologyFile` still accepts the C4 document's Phase 1 example.
    A file's `detector` must be `neonradar_detect.detectors.<slug>`; nothing (`detect list`
    included) imports another module path read from a file.
  - Typology files stay `status: draft`; only a typology researcher approves. After changing
    one, run `uv run neonradar docs typology-index` (CI checks the index with `--check`).
  - C4 `Alert` is strict: `detect run` validates every alert before writing, then checks that
    both ends of every plain-id evidence edge are evidence nodes (`runs.check_edge_ends`; the
    model checks composite ids only).
    `detector.query_sha256` is the SHA-256 of `queries/evidence.cypher` (A1); the hashes of a
    detector's own `QUERIES` go into `run.json` only. A real entity with no evidence
    relationship needs `synthetic_activity: false` (C4 rule 6), which `policy.data_flags`
    does not give yet: an edge-less finding about a real entity fails validation (M3.4/M3.5).
  - R-REAL runs in the runner on every instance; never decide it in a detector.
  - Detector queries run as `session.run(neo4j.Query(text, timeout))`, never in
    `execute_read`. GDS: stream only, concurrency 4, drop projections in `finally`.
  - L19: a Neo4j run deletes every `:Alert` and `:DetectionRun` before it loads (unless
    `--keep-previous`); a failed run records its failed `:DetectionRun` and deletes nothing
    (OD-10); `--engine memory` writes the run folder only. Real profiles are refused until M3.4.
  - Integration tests use the shared Neo4j fixtures (`neo4j`, `graph_db`) of
    graph/tests/support/nr_test_neo4j.py; `neo4j_mode.py` loads records into that database
    (no second container). `worlds.py` generates the small parity world at run time.
