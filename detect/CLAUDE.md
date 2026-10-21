# detect: neonradar_detect

- Purpose: the typology catalog (`detect/typologies/*.yaml`, read by `catalog.py`), headline
  rendering (`wording.py`), detectors (Cypher plus Python) and the alert writer.
- Owner: detect squad (nr-detect); typology definitions belong to typology researchers.
- Depends on: C2 graph schema (reads only C2 labels, types and properties) and C4 alerts;
  pyyaml (the catalog).
- Commands: `uv run pytest detect/tests`, `make test-int`,
  `uv run neonradar docs typology-index [--check]` (renders docs/typologies/README.md).
- Traps:
  - Patterns, not accusations: headlines use the wording templates (PHASE-1.md 7.1).
    scripts/check_wording.py lints every string literal in `wording.py` (docstrings excepted).
  - Typology files stay `status: draft`; only a typology researcher approves. After changing
    one, run `uv run neonradar docs typology-index` (CI checks the index with `--check`).
  - C4 `Alert` is strict (contracts/C4-alert.md): pass lists, not tuples; times as
    `strftime("%Y-%m-%dT%H:%M:%SZ")` (`datetime.isoformat()` gives `+00:00` and fails);
    numbers as int or float, never strings or bools; `query_sha256` = `query_sha256(cypher)`;
    `alert_id` = `compute_alert_id(...)`. Lint summary and steps with `find_forbidden(text,
    mask=[captions, account numbers])` before building the alert. No NaN or infinity in
    metrics or query parameters; one subject per entity id.
  - Data flags (C4 rules 1 to 7): an edge counts as the record that built it (interval id,
    entity of `a|addr|b`, Sanction of `a|sanction|b`); `synthetic_activity` is false if any
    is real, true if all are synthetic, false with no edges next to real entities; list every
    named id's dataset. Collect holders with `collect(DISTINCT holder)`. In case F (real
    holder, synthetic account) the holding Ownership is a `syn-` record, so it is synthetic.
  - Loading alerts: one `FLAGS` per alert and subject (`MERGE` on the pair, `SET` role); a
    re-run deletes `FLAGS` to entities that are no longer subjects.
  - A detector waits for its typology's approval; every query has a fixture test.
  - Bounded Cypher: at most 8 hops, LIMIT, a time window; GDS with `concurrency: 4`.
