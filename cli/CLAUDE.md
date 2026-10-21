# cli: neonradar_cli

- Purpose: the `neonradar` command (typer): `neonradar <group> <command>`, for example
  `neonradar graph load`. It depends on every other package and wires them together.
  Phase 1 starts with `neonradar --version`, `neonradar doctor` and
  `neonradar contracts validate-records`.
- Owner: docs squad (nr-docs).
- Depends on: every contract, through the packages it calls.
- Commands: `uv run pytest cli/tests`, `uv run neonradar --help`, `uv run neonradar doctor`.
- Traps:
  - Keep logic in the packages; a command parses options, calls one function, prints.
  - Output through `typer.echo`; library code logs and never prints.
  - `doctor` exits 1 only on FAIL. Its tests replace `doctor.run` and `doctor.port_in_use`,
    so they never call Docker, uv or pkg-config for real.
