# cli: neonradar_cli

- Purpose: the `neonradar` command (typer): `neonradar <group> <command>`, for example
  `neonradar graph load`. It depends on every other package and wires them together.
  Phase 1 starts with `neonradar --version`, `doctor`, `graph smoke`, `graph migrate`,
  `contracts validate-records`, `contracts export` and `check`, `docs typology-index`,
  `spike clean`, the spikes (`spike companies-house`, M1.8a; `spike gleif`, M1.8b;
  `spike icij`, M1.8c; `spike opensanctions`, M1.8d), `onboarding check|reset`
  (Assignment 1) and `gate check --phase 1` (`make gate-1`, M1.12).
- Owner: docs squad (nr-docs).
- Depends on: every contract, through the packages it calls.
- Commands: `uv run pytest cli/tests`, `uv run neonradar --help`, `uv run neonradar doctor`.
- Traps:
  - Keep logic in the packages; a command parses options, calls one function, prints.
  - Output through `typer.echo`; library code logs and never prints.
  - Spike commands (`neonradar spike <source>`) live in `spike.py`: fetch and map through
    `neonradar_ingest.sources.<source>`, write with `neonradar_ingest.spikes.write_output`
    (only into `data/cache/spikes/<source>/`), and finish with `report_output(path)`, which
    validates in strict mode and exits 1 on any issue. Import ingest code inside the command
    so `neonradar --help` stays fast. `spike clean` deletes files, so it only ever cleans
    `spikes.SPIKE_ROOT` (no folder option); its tests monkeypatch `SPIKE_ROOT` and
    `PROJECT_FILE` to tmp paths.
  - `doctor` exits 1 only on FAIL. Its tests replace `doctor.run` and `doctor.port_in_use`,
    so they never call Docker, uv or pkg-config for real.
  - `gate.py` (Gate 1, PHASE-1.md section 8): one `@gate_check` function per GC check returns
    `(Status, evidence)`; it only reads and never tags, approves or edits (OD-5). Every command
    goes through `Context.run`, so tests pass a fake runner and tmp folders and never call gh,
    Docker or the network; `make_context` decides whether gh and Docker are usable, and their
    checks report MANUAL with the reason when not (`--offline` skips both). GC-02 starts a
    throwaway Testcontainers Neo4j when Docker and the pinned GDS jar are there. Exit 1 on any
    FAIL unless `--report-only` (`make gate-1 GATE_ARGS=--report-only`).
