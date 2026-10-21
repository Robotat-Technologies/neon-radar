# Devcontainer and GitHub Codespaces

The devcontainer gives everyone the same ready environment: Python 3.14 with uv 0.13, ICU for PyICU, Node.js 24 and `gh`, running next to the same Neo4j 5.26 server that `make up` starts ([local stack](local-stack.md)). It lives in `.devcontainer/` and works with VS Code Dev Containers, the `devcontainer` command line and GitHub Codespaces.

## When to use it

- **Windows.** Use the devcontainer (or Codespaces) instead of installing the tools by hand; see [Windows](#windows) below.
- **A weak or crowded laptop**, or when PyICU does not build on your machine.
- **GitHub Codespaces**, when you cannot run Docker locally at all.

On macOS and Linux with the tools from `PHASE-1.md` 1.1 installed, the host setup (`make setup`, `make plugins`, `make up`) is faster.

## What you get

| Part | Value |
|---|---|
| `dev` container | Built from `.devcontainer/Dockerfile` on `ghcr.io/astral-sh/uv:0.13-python3.14-trixie` (Debian 13, Python 3.14, uv 0.13). You work as the non-root user `dev` (uid 1000). The container drops every Linux capability and cannot gain privileges (`cap_drop: [ALL]`, `no-new-privileges`). |
| Tools | Only what the spec names, from official sources, pinned: see [Tools and where they come from](#tools-and-where-they-come-from). No global npm packages, no `curl \| sh` installers, no VS Code extensions. |
| Checkout | Your clone, mounted read-write at `/workspaces/neonradar` |
| Python environment | `/home/dev/.venv`, inside the container and on `PATH`, so it never replaces your host's `.venv` (`UV_PROJECT_ENVIRONMENT`) |
| Neo4j | The `neo4j` service from `compose.yaml`, unchanged: same image, GDS jar, memory profile, ports and data volume |
| Neo4j password | The Compose secret `neo4j_password`, a file at `/run/secrets/neo4j_password`. The `neonradar` command reads it from there; it is never an environment variable in the container. |
| Environment | `NEO4J_URI=bolt://neo4j:7687`, `NR_TEST_NEO4J_URI=bolt://neo4j:7687`, `NR_DEVCONTAINER=1` |

There is no Docker inside the container. That is deliberate: `dev` reaches Neo4j over the Compose network, so nobody needs Docker-in-Docker (`docs/research/2026-10-16/stack.md` 7.1).

## Open it in VS Code

1. Start Docker Desktop (or Docker Engine) and install the VS Code "Dev Containers" extension.
2. Open your clone of the repository and run **Dev Containers: Reopen in Container**.
3. Before any container starts, `initializeCommand` runs on your computer: `bash scripts/ensure_env.sh && bash scripts/fetch_gds.sh`.
   - `ensure_env.sh` creates `.env` with a generated Neo4j password if there is none. It does nothing if `.env` exists, or if `NEO4J_PASSWORD` is already set in the environment.
   - `fetch_gds.sh` downloads the pinned GDS jar once (about 64 MB from github.com) into `data/cache/neo4j-plugins/` and checks its SHA-256. `compose.yaml` mounts that folder, and Neo4j cannot start without it.
4. Compose starts Neo4j, waits until it is healthy, then starts `dev`. Inside it, `postCreateCommand` runs `make setup` (Python packages, pre-commit hooks).
   - The first image build takes a few minutes: two image pulls, the Debian packages and the GitHub CLI.
   - The first `make setup` compiles PyICU, which takes about a minute.
5. Check it in the VS Code terminal:

```bash
uv run neonradar doctor   # Docker and Compose show WARN: there is no Docker in here, by design
make smoke                # Neo4j 5.26.32 community, APOC 5.26.32, GDS 2.13.4
make check
```

Creating the container downloads the two images, the Debian packages, the GitHub CLI, the Python packages and the GDS jar. NeonRadar itself makes no outbound calls (G3); the developer tools in the container connect to their own services as on any machine.

From a terminal instead of VS Code, run these from the repository root (`initializeCommand` uses paths relative to it):

```bash
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . make check
```

`devcontainer build` works without `.env`; `devcontainer up` runs `initializeCommand` first.

## GitHub Codespaces

- **Who pays.** The project uses `personal-quota` (`docs/build/project.yaml`, `access.codespaces`): each person's own free allowance. A personal GitHub Free account includes 120 core hours and 15 GB of storage a month (`stack.md` 7.2). `hostRequirements` asks for 4 cores and 8 GB, so Codespaces offers 4-core machines or larger: that is 30 hours a month. Stop your codespace when you are not using it.
- **Memory.** Use the small memory profile. In the codespace, set `NEO4J_HEAP=1G`, `NEO4J_PAGECACHE=512M` and `NEO4J_MEM_LIMIT=2500m` in `.env`, then run **Codespaces: Rebuild Container**.
- **Secrets.** Codespaces secrets become environment variables in the codespace, and environment variables win over `.env`. Put `CH_API_KEY` there rather than in `.env`. If `NEO4J_PASSWORD` reaches `initializeCommand` as well, `ensure_env.sh` creates no `.env` at all. This is not checked: whether Codespaces passes secrets to `initializeCommand`; if it does not, `.env` is created as usual.
- **Ports.** `forwardPorts` lists Neo4j Browser (`neo4j:7474`), Bolt (`neo4j:7687`), the API (8000) and the UI dev server (5173); open them from the Ports tab. Neo4j Browser through Codespaces port forwarding has not been checked yet.

## Tools and where they come from

The operator decided on 2026-10-22 to install only safe, well-known tools from official sources, pinned. Nothing else is installed.

| Tool | Source | Pinned by | Version (2026-10-22) |
|---|---|---|---|
| Debian 13, Python 3.14, uv | `ghcr.io/astral-sh/uv:0.13-python3.14-trixie`, the official uv image (built on the official `python:3.14-trixie`) | image digest in the Dockerfile | Python 3.14.8, uv 0.13.4 |
| `pkg-config`, `libicu-dev`, `build-essential`, `git`, `make`, `jq`, `ca-certificates` | Debian apt (`deb.debian.org`, trixie), as the spec's Dockerfile names them | the base image's Debian release | ICU 76.1, git 2.47.3 |
| Node.js 24, npm, npx, corepack | the official `node:24-trixie-slim` image: only these four are copied (no yarn) | image digest in the Dockerfile | Node 24.22.1, npm 11.19.1 |
| GitHub CLI (`gh`) | `ghcr.io/devcontainers/features/github-cli:1`, which installs GitHub's `.deb` from github.com/cli/cli releases | feature digest in `.devcontainer/devcontainer-lock.json` | feature 1.1.3, gh 2.102.1 |
| Python packages | PyPI, through `uv sync` | `uv.lock` | as locked |

Dependabot proposes updates for both images and the feature. The Python packages and the pre-commit hooks are the project's own (`uv.lock`, `.pre-commit-config.yaml`).

## Claude Code and the container

- **Claude Code is not installed in the container.** The spec names the Claude Code feature (`ghcr.io/anthropics/devcontainer-features/claude-code`), but that feature installs Claude Code with `npm install -g`, which the operator's rule excludes. Run Claude Code on your computer: it works on the same checkout. The login volume (`/home/dev/.claude`, `CLAUDE_CONFIG_DIR`) is kept, so a later decision can add Claude Code without other changes.
- **If you run an agent inside the container anyway:** prefer Auto mode. `--dangerously-skip-permissions` is acceptable only inside this container and only as the non-root user `dev`; never use it on your own machine (`PHASE-1.md` 1.5). Know what the container does not protect:
  - **The checkout is shared read-write with your computer.** A command can change `.git/hooks`, `.git/config`, the `Makefile`, `scripts/ensure_env.sh` or anything else that your computer later runs outside the container. Look at `git status` and `git diff` before you run `make` or commit on the host after such a session.
  - **Credentials are forwarded.** VS Code forwards your git credentials and SSH agent into the container, and a codespace has a `GITHUB_TOKEN`, so a command can push or call the GitHub API as you.
  - **The network is open.** Nothing restricts outbound connections from the container.
- **The Neo4j MCP server** in `.mcp.json` connects to `NEO4J_URI`, which inside the container is the `neo4j` service. It reads the password from `NEO4J_PASSWORD` in the agent's environment, which the container does not set. You would have to start the agent with `NEO4J_PASSWORD="$(cat /run/secrets/neo4j_password)"`; the password is then in that session's environment, so the rules in [Secrets and logs](#secrets-and-logs) apply to everything the session prints.

## Secrets and logs

The Neo4j password reaches Neo4j and the `dev` container only as the Compose secret `neo4j_password` (the file `/run/secrets/neo4j_password`):

- It is not in the resolved Compose configuration that `devcontainer up` and `build`, VS Code's Dev Containers log and the Codespaces creation log print.
- It is not in `docker inspect`, and not on a process command line (checked on 2026-10-21).

Treat those logs as sensitive all the same:

- **Older copies.** A checkout from before this change (pull request #19 before its review fixes) printed `NEO4J_AUTH: neo4j/…` and `NEO4J_PASSWORD: …` there.
- **Your own additions.** Any variable you add to a Compose file is printed in full.
- **Where the logs are.** VS Code shows its log with **Dev Containers: Show Container Log** and keeps it in its logs folder.

Rules:

- Never paste these logs into an issue, a pull request, a chat or an AI session without first replacing every password and key with `<redacted>`.
- In an AI agent session (Claude Code or another), do not run `env`, `printenv` or `cat` on `.env` or `/run/secrets/`; everything a command prints goes into the session.
- If a password leaked: change `NEO4J_PASSWORD` in `.env`, then run `make reset CONFIRM=yes` (this deletes the local database) and `make up`. The new password only takes effect when the database is created again. For an API key, revoke it with its provider and put the new one in `.env`.

## Limits

- **No Docker inside.** `make plugins`, `make up`, `make test-int` without `NR_TEST_NEO4J_URI`, `make demo-mini` and `make e2e` run on the host, not in the container. Inside it, Neo4j is already running as the `neo4j` service:
  - Integration tests run against it with `NR_TEST_NEO4J_URI` (preset) plus `NR_TEST_ALLOW_WIPE=1` once you accept that the tests wipe that database: `NR_TEST_ALLOW_WIPE=1 make test-int`.
  - The demo runs with `make demo-dev` (M1.9e), which needs no Docker.
  - `neonradar doctor` reports the missing Docker and Compose as WARN.
- **One database per machine.** The devcontainer uses the same Compose project, `neonradar`, as `make up`: the same Neo4j container, the same data volume, and ports 7474 and 7687 on your computer's `127.0.0.1`. Stop any other Neo4j first. When VS Code closes the devcontainer it stops the Compose services, Neo4j included; `make up` on the host starts Neo4j again. Close the devcontainer before you run `make down`.
- **One checkout, two environments.** The Python environments are separate, but git hooks are shared. Inside the container, `make setup` keeps a pre-commit hook that the host installed: it still works there, because the container's environment is on `PATH`. A clone that has no hook yet (a codespace, a fresh clone opened in the container) gets one that points at the container's Python. If you then also commit from the host, run `make setup` on the host once.
- **Git worktrees.** Open the devcontainer from a normal clone. A linked worktree's `.git` file points at a path on the host that does not exist in the container, so git, and with it `make setup`, fail there.
- **`ui/node_modules` (from M1.9d).** `npm ci` inside the container would write Linux binaries into the checkout's `ui/node_modules`, which the host shares. M1.9d must give the container its own named volume for `ui/node_modules`.
- **Checked on** 2026-10-21 on an Intel Mac (amd64) with Docker Desktop 29.7.2, Compose 5.4.0 and `@devcontainers/cli` 0.89.0, from a fresh clone. `make check`, `make smoke` and the integration tests passed inside the container. Not yet checked, and left for a person to confirm (Gate 1 check GC-07): Apple Silicon (arm64), Linux hosts whose user id is not 1000, Windows and Codespaces.

## Windows

`initializeCommand` runs on your computer through `cmd.exe` and needs `bash` on `PATH`, plus `curl`, `sha256sum` and `openssl` (or `python3`) for the two scripts. Creating `.env` by hand is not enough, because the GDS jar must be fetched too.

- **Recommended:** install WSL 2 with Ubuntu, clone the repository inside WSL (for example `~/src/neon-radar`), open it with VS Code's WSL extension, then run **Dev Containers: Reopen in Container**. `initializeCommand` then runs in WSL, and the checkout sits on the Linux file system, which is also much faster for the mounted folder.
- **Or use GitHub Codespaces**, which needs nothing on your computer but a browser or VS Code.
- A clone on the Windows file system (`C:\...`) works only if the `bash` on `PATH` can run these scripts, for example WSL's `bash` with a distribution installed. This has not been checked. `.gitattributes` keeps shell scripts at LF line endings.

## When something goes wrong

| Symptom | What to do |
|---|---|
| `environment variable "NEO4J_PASSWORD" required by secret ... is not set` | On the host, run `bash scripts/ensure_env.sh`, or export `NEO4J_PASSWORD` |
| `neonradar: NEO4J_PASSWORD is missing or shorter than 8 characters` in the Neo4j log | Set a password of at least 8 characters in `.env` |
| `bind source path does not exist: .../data/cache/neo4j-plugins` | On the host, run `bash scripts/fetch_gds.sh` (`initializeCommand` does it; `devcontainer build` alone does not) |
| `port is already allocated` for 7474 or 7687 | Another Neo4j is running: stop it, or run `make down` on the host |
| `dev` never starts because `neo4j` is unhealthy | Usually a password that differs from the one the database was created with: see [local-stack.md](local-stack.md) |
| `detected dubious ownership in repository` | The image trusts `/workspaces/neonradar` only; if you changed `workspaceFolder`, change the `safe.directory` line in the Dockerfile too |
| `ensure_env: this is a linked git worktree` | Use a normal clone (see Limits) |
