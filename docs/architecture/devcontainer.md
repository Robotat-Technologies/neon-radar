# Devcontainer and GitHub Codespaces

The devcontainer gives everyone the same ready environment: Python 3.14 with uv 0.13, ICU for PyICU, Node.js 24, `gh` and Claude Code, running next to the same Neo4j 5.26 server that `make up` starts ([local stack](local-stack.md)). It lives in `.devcontainer/` and works with VS Code Dev Containers, the `devcontainer` command line and GitHub Codespaces.

## When to use it

- **Windows.** Use the devcontainer (or Codespaces) instead of installing the tools by hand; see [Windows](#windows) below.
- **A weak or crowded laptop**, or when PyICU does not build on your machine.
- **GitHub Codespaces**, when you cannot run Docker locally at all.

On macOS and Linux with the tools from `PHASE-1.md` 1.1 installed, the host setup (`make setup`, `make plugins`, `make up`) is faster.

## What you get

| Part | Value |
|---|---|
| `dev` container | Built from `.devcontainer/Dockerfile`: `ghcr.io/astral-sh/uv:0.13-python3.14-trixie` (Debian 13, Python 3.14, uv 0.13) plus `pkg-config`, `libicu-dev`, `build-essential`, `git`, `make`, `jq`. You work as the non-root user `dev` (uid 1000). |
| Features | Node.js 24 (`ghcr.io/devcontainers/features/node:2`), GitHub CLI (`github-cli:1`), Claude Code (`ghcr.io/anthropics/devcontainer-features/claude-code:1.0`) |
| Checkout | Your clone, mounted at `/workspaces/neonradar` |
| Python environment | `/home/dev/.venv`, inside the container and on `PATH`, so it never replaces your host's `.venv` (`UV_PROJECT_ENVIRONMENT`) |
| Neo4j | The `neo4j` service from `compose.yaml`, unchanged: same image, GDS jar, memory profile, ports and data volume |
| Environment | `NEO4J_URI=bolt://neo4j:7687`, `NR_TEST_NEO4J_URI=bolt://neo4j:7687`, `NEO4J_PASSWORD` (the value Compose gives Neo4j), `NR_DEVCONTAINER=1` |

There is no Docker inside the container. That is deliberate: `dev` reaches Neo4j over the Compose network, so nobody needs Docker-in-Docker (`docs/research/2026-10-16/stack.md` 7.1).

## Open it in VS Code

1. Start Docker Desktop (or Docker Engine) and install the VS Code "Dev Containers" extension.
2. Open your clone of the repository and run **Dev Containers: Reopen in Container**.
3. Before any container starts, `initializeCommand` runs on your computer: `bash scripts/ensure_env.sh && bash scripts/fetch_gds.sh`.
   - `ensure_env.sh` creates `.env` with a generated Neo4j password if there is none (Compose needs `NEO4J_PASSWORD`). It does nothing if `.env` exists, or if `NEO4J_PASSWORD` is already set in the environment.
   - `fetch_gds.sh` downloads the pinned GDS jar once (about 64 MB from github.com) into `data/cache/neo4j-plugins/` and checks its SHA-256. `compose.yaml` mounts that folder, and Neo4j cannot start without it.
4. Compose starts Neo4j, waits until it is healthy, then starts `dev`. Inside it, `postCreateCommand` runs `make setup` (Python packages, pre-commit hooks). The first build takes several minutes, mostly for compiling PyICU.
5. Check it in the VS Code terminal:

```bash
uv run neonradar doctor   # Docker and Compose show WARN: there is no Docker in here, by design
make smoke                # Neo4j 5.26.32 community, APOC 5.26.32, GDS 2.13.4
make check
```

Creating the container uses the network: base image, features (Node.js, `gh`, Claude Code), Python packages and the GDS jar. Once it exists, nothing in it phones home (G3).

From a terminal instead of VS Code, run these from the repository root (`initializeCommand` uses paths relative to it):

```bash
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . make check
```

`devcontainer build` on its own does not run `initializeCommand`, so in a fresh clone run `bash scripts/ensure_env.sh && bash scripts/fetch_gds.sh` first.

## GitHub Codespaces

- **Who pays.** The project uses `personal-quota` (`docs/build/project.yaml`, `access.codespaces`): each person's own free allowance. A personal GitHub Free account includes 120 core hours and 15 GB of storage a month (`stack.md` 7.2). `hostRequirements` asks for 4 cores and 8 GB, so Codespaces offers 4-core machines or larger: that is 30 hours a month. Stop your codespace when you are not using it.
- **Memory.** Use the small memory profile. In the codespace, set `NEO4J_HEAP=1G`, `NEO4J_PAGECACHE=512M` and `NEO4J_MEM_LIMIT=2500m` in `.env`, then run **Codespaces: Rebuild Container**.
- **Secrets.** Codespaces secrets become environment variables in the codespace, and environment variables win over `.env`. Put `CH_API_KEY` there rather than in `.env`. If `NEO4J_PASSWORD` reaches `initializeCommand` as well, `ensure_env.sh` creates no `.env` at all (not checked: whether Codespaces passes secrets to `initializeCommand`; if it does not, `.env` is created as usual).
- **Ports.** `forwardPorts` lists Neo4j Browser (`neo4j:7474`), Bolt (`neo4j:7687`), the API (8000) and the UI dev server (5173); open them from the Ports tab. Neo4j Browser through Codespaces port forwarding has not been checked yet.

## Claude Code inside the container

- The Claude Code CLI is installed, and VS Code adds the Claude Code extension. Run `claude` once and sign in. The login is kept in the Docker volume `neonradar-claude-config-<id>`, mounted at `/home/dev/.claude` (`CLAUDE_CONFIG_DIR`), so it survives a rebuild.
- Prefer Auto mode. `--dangerously-skip-permissions` is acceptable only inside this container and only as the non-root user `dev`; never use it on your own machine (`PHASE-1.md` 1.5).
- The read-only Neo4j MCP server in `.mcp.json` connects to `NEO4J_URI`, so inside the container it reaches the `neo4j` service with the `NEO4J_PASSWORD` from the environment.

## Limits

- **No Docker inside.** `make plugins`, `make up`, `make test-int` (Testcontainers), `make demo-mini` and `make e2e` run on the host, not in the container. Inside it, Neo4j is already running as the `neo4j` service. Run integration tests against it with `NR_TEST_NEO4J_URI` (preset) plus `NR_TEST_ALLOW_WIPE=1` when you accept that the tests wipe that database (M1.7b), and run the demo with `make demo-dev` (M1.9e), which needs no Docker. `neonradar doctor` reports the missing Docker and Compose as WARN.
- **One database per machine.** The devcontainer uses the same Compose project, `neonradar`, as `make up`: the same Neo4j container, the same data volume, and ports 7474 and 7687 on your computer's `127.0.0.1`. Stop any other Neo4j first. When VS Code closes the devcontainer it stops the Compose services, Neo4j included; `make up` on the host starts Neo4j again. Close the devcontainer before you run `make down`.
- **One checkout, two environments.** The Python environments are separate, but git hooks are shared: `make setup` points the pre-commit hook at the Python of whichever side ran it last. If you commit from the host as well, run `make setup` on the host again after creating the container. The other way round works: a hook installed on the host still runs inside the container, because the container's environment is on `PATH`.
- **Git worktrees.** Open the devcontainer from a normal clone. A linked worktree's `.git` file points at a path on the host that does not exist in the container, so git, and with it `make setup`, fail there.
- **`ui/node_modules` (from M1.9d).** `npm ci` inside the container would write Linux binaries into the checkout's `ui/node_modules`, which the host shares. M1.9d must give the container its own named volume for `ui/node_modules`.
- **Checked on** an Intel Mac (amd64) with Docker Desktop. Apple Silicon (arm64), Linux hosts whose user id is not 1000, Windows and Codespaces still need a person to confirm them (Gate 1 check GC-07).

## Windows

`initializeCommand` runs on your computer through `cmd.exe` and needs `bash` on `PATH`, plus `curl`, `sha256sum` and `openssl` (or `python3`) for the two scripts. Creating `.env` by hand is not enough, because the GDS jar must be fetched too.

- **Recommended:** install WSL 2 with Ubuntu, clone the repository inside WSL (for example `~/src/neon-radar`), open it with VS Code's WSL extension, then run **Dev Containers: Reopen in Container**. `initializeCommand` then runs in WSL, and the checkout sits on the Linux file system, which is also much faster for the mounted folder.
- **Or use GitHub Codespaces**, which needs nothing on your computer but a browser or VS Code.
- A clone on the Windows file system (`C:\...`) works only if the `bash` on `PATH` can run these scripts, for example WSL's `bash` with a distribution installed. This has not been checked. `.gitattributes` keeps shell scripts at LF line endings.

## When something goes wrong

| Symptom | What to do |
|---|---|
| `Set NEO4J_PASSWORD in .env` during build or start | On the host, run `bash scripts/ensure_env.sh`, or export `NEO4J_PASSWORD` |
| `bind source path does not exist: .../data/cache/neo4j-plugins` | On the host, run `bash scripts/fetch_gds.sh` (`initializeCommand` does it; `devcontainer build` alone does not) |
| `port is already allocated` for 7474 or 7687 | Another Neo4j is running: stop it, or run `make down` on the host |
| `dev` never starts because `neo4j` is unhealthy | Usually a password that differs from the one the database was created with: see [local-stack.md](local-stack.md) |
| `detected dubious ownership in repository` | The image trusts `/workspaces/neonradar` only; if you changed `workspaceFolder`, change the `safe.directory` line in the Dockerfile too |
| `ensure_env: this is a linked git worktree` | Use a normal clone (see Limits) |
