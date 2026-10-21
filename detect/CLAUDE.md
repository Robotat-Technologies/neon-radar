# detect: neonradar_detect

- Purpose: the typology catalog (`detect/typologies/*.yaml`, read by `catalog.py`), headline
  rendering (`wording.py`), detectors (Cypher plus Python) and the alert writer.
- Owner: detect squad (nr-detect); typology definitions belong to typology researchers.
- Depends on: C2 graph schema (reads only C2 labels, types and properties) and C4 alerts.
- Commands: `uv run pytest detect/tests`, `make test-int`,
  `uv run neonradar docs typology-index [--check]` (renders docs/typologies/README.md).
- Traps:
  - Patterns, not accusations: headlines use the wording templates (PHASE-1.md 7.1).
    scripts/check_wording.py lints every string literal in `wording.py` (docstrings excepted).
  - Typology files stay `status: draft`; only a typology researcher approves.
  - A detector waits for its typology's approval; every query has a fixture test.
  - Bounded Cypher: at most 8 hops, LIMIT, a time window; GDS with `concurrency: 4`.
