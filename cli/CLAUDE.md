# cli: neonradar_cli

- Purpose: the `neonradar` command (typer): `neonradar <group> <command>`, for example
  `neonradar graph load`. It depends on every other package and wires them together.
  Phase 1 starts with `neonradar --version`, `doctor`, `graph smoke`, `graph migrate`,
  `contracts validate-records`, `contracts export` and `check` (JSON Schemas and the OpenAPI
  snapshot), `api serve` (127.0.0.1 only), `docs typology-index`, `graph load|stats|wipe`
  (M1.9a; `load` is strict by default, `wipe` needs `--yes`), `spike clean`, the spikes
  (`spike companies-house`, M1.8a; `spike gleif`, M1.8b; `spike icij`, M1.8c;
  `spike opensanctions`, M1.8d; `spike synthetic-join`, M1.8e), `synth demo-mini` and
  `synth check-names` (M1.8e), `onboarding check|reset` (Assignment 1), `detect run|list`
  (M1.9b) and `gate check --phase 1` (`make gate-1`, M1.12).
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
    `PROJECT_FILE` to tmp paths. `spike synthetic-join` reads other C1 files, so it
    validates input plus output together and prints counts and rule codes only, never an
    input name or id (its records reference input entities that may be real).
  - Phase 2 data commands (M2.2): `data profiles|fetch|status|purge` (`data.py`) and
    `ingest build` (`ingest.py`). A command that touches a profile runs inside
    `redact.guard(profile, command)`, runs the gate first and reports through `summary.emit`
    (counts only; it refuses record-like values). Errors carry `exit_code` (2 refusal, 3 gate,
    4 cap) and `counts_only` when their message is safe to print on a real profile. Human-only
    commands call `tty.require_terminal` inside the guard. `purge --graph` is
    `real_graph.wipe()`; tests replace `real_graph._run` and never call Docker.
  - `er run|show-config|bench` (`er.py`, M2.10a): `er run` gates a real profile, resolves
    into `resolution_dir`, spills DuckDB into `retention.spill_dir` and writes `LATEST` last.
  - `er sample|label|review|precision` (`er_labelling.py`, M2.10c): `--run <id>|latest`; a
    real profile runs the gate, then refuses while people.er_labellers or
    er_senior_reviewers still hold @TODO (OD-22), and `--adjudicate` and `er precision` refuse
    while people.tech_lead or squads.graph.mentor is not a handle. `er label` and `er review`
    are human-only: `require_terminal` first, no default answer; agents never run them (G10).
    They refuse when the record files differ from the run's inputs (`records.unchanged`).
  - `graph load [PATH...] [--profile NAME] [--resolution RUN_DIR|latest] [--no-replace]`,
    `graph verify` and `--real` on migrate, verify, stats and wipe (`graph.py`, M2.11): the
    instance comes from the profile, else from the paths and then the manifests (C2 L17; a
    path under the real roots is decided from its name, before its folder is listed); the
    real-data one runs the gate before connecting, inside `redact.guard`, takes only a run
    folder of its profile's resolution folder (G8), and prints counts only (a load through
    `summary.emit`). Tests replace `loader.load`, `get_driver` and `wait_until_ready`.
  - `doctor` exits 1 only on FAIL. Its tests replace `doctor.run` and `doctor.port_in_use`,
    so they never call Docker, uv or pkg-config for real.
  - `contracts export` and `check` import the API app lazily to render `openapi/v1.json`;
    `api serve` imports uvicorn inside the command, so `neonradar --help` stays fast.
  - `api serve --real` (M2.12) is human-only: inside `redact.guard`, `require_terminal` first,
    then the real-data gate without a profile, then the app on `Instance.REAL` at 127.0.0.1 on
    `REAL_PORT`. Agents never run it; its test closes stdin and checks nothing else ran. It
    serves `problems.Contained(create_app(..., report=...))` with `access_log=False` and log
    level warning (G9): a request line holds ids and names; `redact.report` keeps tracebacks
    in data/cache/real/logs. `--port` with `--real` exits 2.
  - `gate.py` (Gate 1, PHASE-1.md section 8): one `@gate_check` function per GC check returns
    `(Status, evidence)`; it only reads and never tags, approves or edits (OD-5). Every command
    goes through `Context.run`, so tests pass a fake runner and tmp folders and never call gh,
    Docker or the network; `make_context` decides whether gh and Docker are usable, and their
    checks report MANUAL with the reason when not (`--offline` skips both and sets
    `UV_OFFLINE=1` for `make contracts-check`). GC-02 runs the migration test in a throwaway
    Testcontainers Neo4j (it removes `NR_TEST_NEO4J_URI` and `NR_TEST_ALLOW_WIPE`) when Docker
    and the pinned GDS jar are there. A command that times out is killed with its whole process
    group. Exit 1 on any FAIL unless `--report-only` (`make gate-1 GATE_ARGS=--report-only`).
