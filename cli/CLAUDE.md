# cli: neonradar_cli

- Purpose: the `neonradar` command (typer): `neonradar <group> <command>`, for example
  `neonradar graph load`. It depends on every other package and wires them together.
  Phase 1 starts with `neonradar --version`, `neonradar doctor`, `neonradar graph smoke`,
  `neonradar graph migrate`, `neonradar contracts validate-records`, `neonradar contracts export`
  and `check`, `neonradar docs typology-index`, `neonradar spike clean` and the spikes
  (`neonradar spike gleif`, M1.8b; `neonradar spike opensanctions`, M1.8d).
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
