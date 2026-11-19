# Windows development container

## Scope

D7 runs the synthetic NeonRadar demo on Windows using Docker Desktop
and a VS Code development container.

The Compose project is `neonradar-d7`, with separate Neo4j volumes.
Codespaces was not tested.

## Prerequisites

- Docker Desktop running with Linux containers.
- VS Code with the Dev Containers extension.
- Git and PowerShell.
- Internet access for the first image build and dependency downloads.

The tested laptop has 8 GB RAM. Neo4j uses a 1 GB heap, 512 MB
page cache and a 2500 MB container memory limit. Stop other local
NeonRadar stacks if resources are limited; retain their volumes.

## First-time setup

Run PowerShell from the repository root.

Create `.env` from `.env.example` only if it does not already exist.
Set a unique, long `NEO4J_PASSWORD` locally. Never commit or share it.

For this isolated stack, set the host connection in `.env` to:

```dotenv
NEO4J_URI=bolt://localhost:17687
```

VS Code invokes Compose without the explicit `--env-file` option.
Copy the environment file into the Compose directory:

```powershell
Copy-Item .env .devcontainer/.env
git check-ignore .env .devcontainer/.env
```

Both paths must be ignored. Repeat the copy after changing the password.
The Compose services receive only their explicitly configured settings.

Validate and build:

```powershell
docker compose --env-file .env -f .devcontainer/compose.dev.yaml config --quiet
docker compose --env-file .env -f .devcontainer/compose.dev.yaml build dev
```

Download the pinned GDS plugin and start the development services:

```powershell
docker compose --env-file .env -f .devcontainer/compose.dev.yaml run --rm --no-deps plugins
docker compose --env-file .env -f .devcontainer/compose.dev.yaml up -d --wait dev
```

GDS is checked against its pinned SHA-256 before installation.
The plugin service exiting with code 0 is expected.

Open the repository in VS Code and select
**Dev Containers: Reopen in Container**.

If reopening stalls after the services have started, use
**Dev Containers: Attach to Running Container**, select
`neonradar-d7-dev-1`, and open `/workspaces/neonradar`.

## Install dependencies

Run these commands inside the development container:

```bash
UV_HTTP_TIMEOUT=300 uv sync --locked --all-packages
npm ci --prefix ui --include=optional --prefer-offline --maxsockets=2 --fetch-retries=5 --fetch-timeout=300000 --no-audit --no-fund
```

The first installation can take a long time on a slow connection.
Keep the laptop awake. Preserve dependency caches and lockfiles.

## Load and run the synthetic demo

Inside the development container:

```bash
make demo-data
```

This migrates and wipes the selected database, loads `demo-mini`,
and runs detection. The synthetic-data guard must remain enabled.
Do not add `CONFIRM=yes` or target another database.

Start the API:

```bash
uv run neonradar api serve
```

In a second terminal, start the UI:

```bash
npm run --prefix ui dev
```

Keep both terminals running. In VS Code's **Ports** tab, open
the forwarded UI port `5174` in the browser.

The UI proxies `/api` to the API inside the container.
Use the forwarded address shown by VS Code.

## Ports

| Service | Container port | Windows access |
| --- | --- | --- |
| UI | 5174 | VS Code port forwarding |
| API | 8000 | VS Code port forwarding |
| Neo4j HTTP | 7474 | 127.0.0.1:17474 |
| Neo4j Bolt | 7687 | 127.0.0.1:17687 |

Inside the Compose network, Neo4j is `bolt://neo4j:7687`.

VS Code may forward a container port to a different local port.
In the final browser check, container port 5174 mapped to localhost:5175,
and API port 8000 mapped to localhost:8001.
Always use the Forwarded Address shown in VS Code's Ports tab.

## Observed problems and resolutions

| Problem | Resolution or tested workaround |
| --- | --- |
| Docker Linux engine pipe unavailable | Start Docker Desktop and wait for its engine before running Compose. |
| GDS download failed with HTTP/2 `PROTOCOL_ERROR` | Use HTTP/1.1 in `scripts/fetch_gds.sh`; retain SHA-256 verification. |
| Neo4j rejected settings named `PAGECACHE` or `PASSWORD` | Pass `NEO4J_AUTH` and supported Neo4j settings explicitly; do not import the whole `.env` into Neo4j. |
| Python package downloads timed out | Increase the download timeout. A resumable IPv4/HTTP1.1 download of the pinned `rigour` wheel was verified against `uv.lock` and supplied through `uv sync --find-links /tmp`. |
| PowerShell stripped quotes from inline Python | Pipe a PowerShell here-string to `docker exec -i ... python -`. |
| A multiline Bash command received an invalid path | Passing subprocess arguments through Python avoided the suspected line-ending issue. |
| npm downloads failed with `ECONNRESET` | Retry with optional dependencies included, cached downloads preferred and two concurrent connections. |
| Vite could not load the Linux Rolldown binding | Reinstall with `npm ci --include=optional`; do not delete the lockfile. |
| VS Code connection repeatedly stalled | Logs showed a failed server installation in the small `docker-desktop` root filesystem. Removing one identified stale installation directory freed space; attaching to the running container then succeeded. Reopen reliability remains to be verified. |
| Browser could not reach Vite | Binding Vite to `0.0.0.0` on fixed port `5174`, with port forwarding, worked. `strictPort` prevents silent port changes. |
| Editor rejected the TypeScript `lib` setting | Point `typescript.tsdk` to `ui/node_modules/typescript/lib` and select the workspace TypeScript version. |
| Editor could not load `vscode://schemas/mcp` | An editor schema warning remained; it did not prevent the demo or checks from running. |
| Two unit tests inherited `COMPOSE_PROJECT_NAME` | The dev service now receives explicit environment settings instead of importing the whole `.env`. After recreating dev, the variable was absent and plain `make check` passed. |

Do not reset Docker, prune volumes or remove database data to troubleshoot
the VS Code server installation.

## Validation recorded on 18–19 November 2026

- Development tools: Python 3.14.8, uv 0.13.4, Node 24.22.1,
  npm 11.19.1, GNU Make 4.4.1 and ICU 76.1.
- Python dependency installation completed; PyICU built successfully.
- UI dependency installation completed.
- Neo4j connectivity passed.
- Synthetic fixture: 454 records, 110 nodes and 370 relationships.
- No dangling references, rejected records or mapping issues.
- Detection produced three `circular_flow` alerts.
- The browser demo opened and the user confirmed it was working.
- After recreating the development container, `COMPOSE_PROJECT_NAME`
  was absent and plain `make check` exited with code 0:
  2090 Python tests, 503 contract tests, 40 Cypher statements,
  57 UI tests, lint, formatting and type checks passed.
- VS Code reopen reliability and automatic editor-setting selection
  still require verification.
- Final browser check after recreating dev passed: company search,
  entity graph, alert details and data sources.

## Stop and resume

Stop the API and Vite with Ctrl+C in their respective terminals.

To stop the development services while keeping database volumes,
run from Windows PowerShell:

```powershell
docker compose --env-file .env -f .devcontainer/compose.dev.yaml stop
```

To resume, start Docker Desktop, run `up -d --wait dev`, reconnect
VS Code, and start the API and UI again.

Do not rerun `make demo-data` merely to resume: it reloads the database.
