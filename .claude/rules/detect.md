---
paths:
  - "detect/**"
  - "eval/**"
  - "cli/src/neonradar_cli/evaluate.py"
---

# Detection rules (PHASE-3.md 2.1, 2.10, 7.1, 7.5, 7.6)

- Verbatim files come from `docs/build/PHASE-3-CODE.md` with `scripts/spec_extract.py`; never
  retype one, and never edit a verbatim test, `eval/baselines/ci.json` or `eval/freeze.json`
  to make a check pass. A failing verbatim test is a stop-and-ask case. A mechanical deviation
  goes into `docs/build/phase-3-deviations.json`; an accepted change goes into the code book
  with `spec_extract update` in the same pull request (2.10).
- Detectors see the graph only through the `Source` protocol (`source.py`). Every Cypher
  statement lives in `detect/src/neonradar_detect/queries/<method>.cypher`, is bounded,
  parameterised, ordered by C2 ids before any `LIMIT`, and passes `make cypher-lint`.
- A change to a query file or to `neo4jsource.py` needs the same change in `memsource.py`
  (the oracle), and `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration"`.
- R-REAL (G12) is applied by the runner on every instance: never emit a payment-based alert
  that involves a non-synthetic entity, or any alert that names a non-synthetic person (a
  `:LegalEntity` that is not an `:Organization`) as a subject or in its evidence.
- Registry relationships count only while current: no end date, or one after the end of the
  window (`LinkRow.current`).
- Alert text describes the shape and its numbers; it never names the conduct a typology is
  named after. `wording.render` lints every text it renders and raises on a match (7.5.2).
- GDS: `stream` only, concurrency 4, projections dropped in `finally`; no `graphdatascience`.
- Evaluation: the agent never runs `neonradar eval run --split test`, never chooses holdout
  seeds and never opens a holdout world (G11). Development figures are called development
  figures.
- A detector change that moves a count in `eval/baselines/ci.json` is an accepted change, not
  a fix to make a check pass: it needs a typology researcher's approval, updates the file and
  its code book block (`spec_extract update`) in the same pull request, for the typologies the
  milestone names only, and explains each change; after the freeze it also needs
  `freeze-change` (M3.11).
