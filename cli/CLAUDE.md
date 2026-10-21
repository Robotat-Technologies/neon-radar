# cli: neonradar_cli

- Purpose: the `neonradar` command (typer): `neonradar <group> <command>`, for example
  `neonradar graph load`. It depends on every other package and wires them together.
  Phase 1 starts with `neonradar --version`, `doctor`, `graph smoke`, `graph migrate`,
  `contracts validate-records`, `contracts export` and `check`, `docs typology-index`,
  `spike clean`, the spikes (`spike companies-house`, M1.8a; `spike gleif`, M1.8b;
  `spike icij`, M1.8c; `spike opensanctions`, M1.8d) and `onboarding check|reset`
  (Assignment 1).
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
  - Inside the devcontainer (`NR_DEVCONTAINER=1`, or `doctor --devcontainer`) a missing
    Docker or Compose is a WARN: the container has no Docker by design (M1.5).
