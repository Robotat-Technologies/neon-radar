# Development container

## Purpose and requirements

Use this environment to develop NeonRadar on Windows with a Linux
toolchain, or in GitHub Codespaces. It reuses the root `compose.yaml`
for Neo4j and adds only a development service.

Local requirements:

- Docker Desktop with WSL 2 and Linux containers.
- VS Code with the Dev Containers extension.
- Git for Windows with Git Bash.
- 4 CPU cores, 8 GB RAM and space for images and dependencies.
- Internet access for initial setup.

Python, uv, Node.js 24, GitHub CLI and Claude Code are included.
`make setup` installs project dependencies and Git hooks automatically.

## Prepare Windows

Run commands from the repository root in PowerShell.
Ensure `bash` resolves to Git Bash rather than the Windows WSL relay:

```powershell
$env:Path = "C:\Program Files\Git\bin;" + $env:Path
bash --version
bash scripts/ensure_env.sh
```

Adjust the Git installation path if needed. The initialize command also
runs `scripts/ensure_env.sh`; it preserves an existing root `.env`.

Without Bash, create `.env` from `.env.example` manually once and set
a unique, long `NEO4J_PASSWORD`. Install Git Bash before using the
configured initialize command. Never overwrite an existing `.env`,
commit it, or copy it into `.devcontainer`.

For an 8 GB machine, set these values in the root `.env`:

```dotenv
NEO4J_HEAP=1G
NEO4J_PAGECACHE=512M
NEO4J_MEM_LIMIT=2500m
```

For a linked Git worktree, also run these commands in the same
PowerShell session before starting the container:

```powershell
$env:NR_DEV_GIT_COMMON_DIR = (git rev-parse --path-format=absolute --git-common-dir).Trim()
$worktreeGitDir = (git rev-parse --path-format=absolute --git-dir).Trim()
$env:NR_DEV_GIT_DIR = "/workspaces/neonradar-git/worktrees/" + (Split-Path $worktreeGitDir -Leaf)
```

This exposes the shared Git metadata to Linux without changing the
host worktree's `.git` file. Normal clones use the default paths.

Download the pinned GDS plugin before starting Neo4j:

```powershell
bash scripts/fetch_gds.sh
```

The script verifies the download against its pinned SHA-256.
Validate the combined Compose configuration:

```powershell
docker compose --env-file .env -f compose.yaml -f .devcontainer/compose.dev.yaml config --quiet
```

## Open the environment

Close all existing VS Code windows first so the new process inherits
Git Bash and any worktree variables from the prepared session.
Launch VS Code from the prepared PowerShell session:

```powershell
code .
```

Select **Dev Containers: Reopen in Container**. The workspace inside
the container is `/workspaces/neonradar`. Wait for `make setup` to finish.

Alternatively, start it from the host:

```powershell
npx --yes @devcontainers/cli build --workspace-folder .
npx --yes @devcontainers/cli up --workspace-folder .
```

To connect to an already running environment, select
**Dev Containers: Attach to Running Container**, choose its `dev`
container and open `/workspaces/neonradar`.

Initial downloads can be slow. Preserve build and package caches.

## Codespaces

Codespaces has not been validated; the verification recorded in the
pull request covers Windows only.

Create a Codespace using the repository's development-container
configuration and a machine meeting the declared requirements.
Windows Git Bash and linked-worktree instructions do not apply to
a normal Codespaces checkout.

Codespaces usage consumes the account's compute and storage allowance.
Check the account's current quota and pricing before leaving it running.
Keep forwarded ports private and stop the Codespace when finished.

The `.claude` volume persists configuration across container recreation
within the environment; it is not a backup across deleted Codespaces.

## Run the synthetic demo

Run inside the container:

```bash
uv run neonradar graph smoke
make demo-data
```

`make demo-data` migrates and wipes the selected database, loads the
synthetic fixture and runs detection. Target only the intended synthetic
development database. Keep the guard enabled; do not add `CONFIRM=yes`.

Start the API:

```bash
uv run neonradar api serve
```

In another container terminal, start Vite:

```bash
npm run --prefix ui dev -- --host 0.0.0.0
```

This host override applies only to this container process.
Do not change the shared `ui/vite.config.ts`.

Open port 5173 through VS Code's **Ports** tab.
Vite proxies API requests to the API in the same container.
Use the displayed forwarded address if the local port differs.

| Service | Container endpoint | Access |
| --- | --- | --- |
| UI | 5173 | VS Code forwarding |
| API | 127.0.0.1:8000 | Vite proxy or VS Code forwarding |
| Neo4j HTTP | neo4j:7474 | Forwarding or configured Compose host port |
| Neo4j Bolt | neo4j:7687 | Compose network or configured host port |

`make demo-dev` also loads synthetic data and starts both servers,
using Vite's default host setting. Use the separate commands above
when an explicit container host override is needed.

## Claude Code

Run `claude --version` to verify installation, then `claude` and follow
its authentication prompts. Do not put credentials in project files.

Configuration is stored in the mounted `/home/dev/.claude` volume.
Prefer Auto mode. Restrict any permission-skipping mode to trusted
work inside the non-root development container.

## Verification

Run the acceptance commands from the host repository root:

```powershell
npx --yes @devcontainers/cli build --workspace-folder .
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . make check
npx --yes @devcontainers/cli exec --workspace-folder . uv run neonradar graph smoke
```

Check company search, an entity graph, alert details and data sources
in the browser. Put command outputs, versions and validation results
in the pull request description.

No Docker daemon is installed inside the development container.
Run Docker-dependent targets such as `make up`, `make demo-mini`
and Testcontainers integration tests from a suitable host environment.

`NR_TEST_NEO4J_URI` targets the Compose database. Enable `ALLOW_WIPE=1`
only for tests against a disposable synthetic database.

## Troubleshooting

| Problem | Action |
| --- | --- |
| Docker engine unavailable | Start Docker Desktop and wait for its Linux engine. |
| Bash fails through the WSL relay | Put Git Bash first in PATH and launch VS Code from that session. |
| Git rejects a Windows worktree path | Set the worktree variables before creating the container. |
| Node download interrupted | The image uses HTTP/1.1 and retries binary downloads. Restore connectivity before retrying. |
| Python downloads time out | Setup increases the HTTP timeout and limits concurrent downloads; retain the cache when retrying. |
| npm reports `ECONNRESET` | Restore connectivity and retry; reduce concurrent connections on slow networks. |
| Linux Rolldown binding missing | Run `npm ci --prefix ui --include=optional` inside the container; preserve the lockfile. |
| Claude native binary missing | Check optional-package downloads and postinstall output. The image includes optional dependencies and permits Claude's installation script. |
| UI inaccessible | Keep Vite running with the container-only host override and forward 5173. |
| Wrong TypeScript editor version | Select the workspace version in `ui/node_modules/typescript/lib`. |
| Insufficient disk space | Check the drive holding Docker's disk image. Use Docker Desktop settings to relocate it; preserve database volumes. |

## Stop and resume

Stop the API and Vite with Ctrl+C. From the host, stop services without
removing volumes:

```powershell
docker compose --env-file .env -f compose.yaml -f .devcontainer/compose.dev.yaml stop dev neo4j
```

To resume, start Docker Desktop, prepare the host session as above,
and reopen the container or run the CLI `up` command. Start the API
and UI again. Do not rerun `make demo-data` merely to resume: it wipes
and reloads the selected database.