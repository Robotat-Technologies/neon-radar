# Local stack: Neo4j in Docker Compose

`make up` starts one Neo4j 5.26 LTS Community server with APOC and Graph Data Science (GDS), bound to `127.0.0.1`, with memory sized for your laptop and no analytics or usage reports. It works offline once the image and the GDS jar are present: `make plugins` is the only step that uses the network. Why this version and these settings: [ADR-0002](../decisions/0002-neo4j-5-26-lts.md).

## First start

```bash
make setup      # Python packages, pre-commit hooks, and .env with a generated Neo4j password
make plugins    # once, with network: pulls the Neo4j image and the pinned GDS jar (about 64 MB)
make up         # starts Neo4j and waits until it is healthy; never downloads anything
make smoke      # prints the Neo4j, APOC and GDS versions
```

`make smoke` should print:

```text
OK    Neo4j  5.26.32 community
OK    APOC   5.26.32
OK    GDS    2.13.4
```

`neonradar doctor` checks Docker, Compose, `.env`, the ports and the memory Docker has.

## What runs

| Thing | Value |
|---|---|
| Image | `neo4j:5.26.32-community` |
| Ports | `127.0.0.1:7474` (Browser, HTTP) and `127.0.0.1:7687` (Bolt); nothing listens on other interfaces |
| Data | Docker volumes `neonradar_neo4j_data` and `neonradar_neo4j_logs` |
| Import folder | `data/import/`, mounted read-only at `/import` |
| APOC Core | installed from the image |
| GDS | `data/cache/neo4j-plugins/neo4j-graph-data-science-2.13.4.jar`, written by `make plugins` and checked against its SHA-256 by `make up` |
| Settings | `.env` (created from `.env.example` by `scripts/ensure_env.sh`; never commit it) |

The Community image has no GDS jar, and letting it install GDS would mean a download on every start. `scripts/fetch_gds.sh` pins the version and the SHA-256. To move to another GDS version, change both in that script and the jar name in `compose.yaml`, in a reviewed pull request. If the image or the jar is missing, or the jar is damaged, `make up` stops and tells you to run `make plugins`; it never pulls or downloads anything itself.

## Memory profiles

Pick one in `.env`. The Neo4j container may never use more than `NEO4J_MEM_LIMIT`.

| Profile | Laptop | `NEO4J_HEAP` | `NEO4J_PAGECACHE` | `NEO4J_MEM_LIMIT` | Measured on 2026-10-21 (empty database) |
|---|---|---|---|---|---|
| standard | 16 GB | `2G` | `2G` | `5g` | 2.75 GiB of 5 GiB |
| small | 8 GB | `1G` | `512M` | `2500m` | 1.70 GiB of 2.44 GiB |

After changing the profile, run `make down && make up`. With the small profile, use the small synthetic dataset and run GDS with `concurrency: 2`.

**Docker Desktop (macOS and Windows).** The Docker VM gets half of your computer's memory by default (`docs/research/2026-10-16/stack.md` 8.3), and everything Docker runs shares it. Check the amount in Docker Desktop under Settings, Resources, Memory. The standard profile needs at least 6 GB there if other containers also run; otherwise use the small profile. `neonradar doctor` shows what Docker has.

## Neo4j Browser

Open http://localhost:7474, connect to `neo4j://localhost:7687` as user `neo4j` with the `NEO4J_PASSWORD` from your `.env`. The server sends no product analytics (`client.allow_telemetry=false`) and no usage reports (`dbms.usage_report.enabled=false`). Browser's own outgoing connections (`browser.allow_outgoing_connections`) can be switched off only in Enterprise Edition.

## GDS Community limits

All algorithms are available, but an algorithm uses at most 4 CPU cores and the model catalog holds at most 3 models. Pass `concurrency: 4` (or less) in every GDS call and prefer `CALL gds.<algorithm>.stream(...)` from Cypher.

## Stop, reset and passwords

- `make down` stops Neo4j and keeps the data. `make up` starts it again with the same data and plugins.
- `make logs` follows the server log.
- `make reset CONFIRM=yes` deletes the database and logs volumes. The next `make up` starts empty.
- The password in `.env` takes effect only when the database is first created. If you change `NEO4J_PASSWORD` later, run `make reset CONFIRM=yes`, then `make up`.
- All checkouts on one machine (the main checkout and every git worktree) share the same Compose project, `neonradar`, and so the same database. Give them the same `.env`: worktrees that Claude Code creates copy it (`.worktreeinclude`), and in any other worktree `bash scripts/ensure_env.sh` (run by `make setup`, `make plugins` and `make up`) links `.env` to the main checkout's. It stops with a message if the main checkout has no `.env` yet.
- To fetch the GDS jar again, delete `data/cache/neo4j-plugins/` and run `make plugins`.
- Worktrees that Claude Code creates also copy the GDS jar (`.worktreeinclude`); in a worktree you create yourself, run `make plugins` or copy `data/cache/neo4j-plugins/`.

## When something goes wrong

| Symptom | What to do |
|---|---|
| `make up` says the GDS jar or the Neo4j image is missing | `make plugins` (it needs the network once) |
| `Set NEO4J_PASSWORD in .env` and there is no `.env` | run `bash scripts/ensure_env.sh` (in a git worktree, run it in the main checkout first; the worktree then links to that `.env`) |
| `.env` exists but has no password (`ensure_env: .env has no NEO4J_PASSWORD`) | delete `.env`, run `bash scripts/ensure_env.sh`, then `make reset CONFIRM=yes` if a database already exists with another password |
| `make down`, `make logs` or `make reset` fail with `Set NEO4J_PASSWORD in .env` | Compose needs the variable even to stop: `NEO4J_PASSWORD=unused make down` (likewise for `logs` and `reset`), then fix `.env` as above |
| `container neonradar-neo4j-1 is unhealthy` | `make logs`. A password changed after the first start shows up as failed health checks: see above |
| Port 7474 or 7687 already in use | `neonradar doctor` shows it; stop the other program or the other Neo4j |
| Neo4j restarts with `OutOfMemoryError` | use a bigger profile, or give Docker more memory |
