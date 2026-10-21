# 0007. Toolchain

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (tech lead)

## Context

NeonRadar has seven Python packages, one per squad (`contracts`, `ingest`, `graph`, `detect`, `copilot`, `api`, `cli`), and a Vue app in `ui/` (`docs/build/PHASE-1.md` section 4.2). Most of the code is written by AI agents and reviewed by people, so every machine and every session has to install, format, lint, type-check and test the same way, with one command each. The choices below were checked against package registries and release schedules on 16 October 2026 (`docs/research/2026-10-16/stack.md`).

The facts that shape the decision:

- **Python.** 3.15.0 came out on 9 October 2026, but `graphdatascience` and `neo4j-graphrag` require Python below 3.15, and `duckdb` (needed by Splink) has wheels only up to 3.14. Python 3.13 now gets security fixes only. Every compiled dependency checked has 3.14 wheels. numpy 2.5 has no 3.10 or 3.11 wheels, and pandas 3, pre-commit 4.7 and rapidfuzz need 3.11 or later, so the project plan's "3.11+" floor is out of date (`stack.md` 3.1).
- **Workspaces.** In a uv workspace all members share one `uv.lock` and one `requires-python`, and members depend on each other as editable workspace sources. uv's documentation says workspaces do not suit members with conflicting requirements; path dependencies are the alternative (`stack.md` 3.3).
- **Type checking.** mypy 2.4 runs strict with the pydantic plugin and installs as pure Python through uv. pyright and basedpyright are fast editor checkers. Astral's `ty` is still in beta (`stack.md` 3.2).
- **Hooks.** ruff-pre-commit v0.17.1 provides `ruff-check` and `ruff-format`, uv-pre-commit 0.13.1 provides `uv-lock`, and gitleaks v8.30.1 provides `gitleaks` (`stack.md` 3.4 and 7.4).
- **Older system Pythons.** Some files run with a system Python, not the project's 3.14: `scripts/*.py` on CI's Ubuntu `python3` (3.12) and `.claude/hooks/guard_git.py` on macOS's `python3` (3.9.6 on the operator's Mac). With a 3.14 target, ruff's formatter rewrites `except (A, B):` as `except A, B:`, which Python 3.13 and older reject (`PHASE-1.md` 3.2).
- **ICU.** followthemoney, rigour and normality need PyICU, which has no wheels on PyPI and builds from source against ICU headers (`stack.md` 3.5).
- **Frontend.** Node 20 reached end of life on 30 April 2026. Node 24 is an LTS line supported until 30 April 2028, and Node 26 becomes LTS on 28 October 2026. create-vue 3.24.0 needs Node `^22.18.0 || >=24.12.0` and pins `typescript ~6.0.0` and `vitest ^4.1.11`. `typescript@latest` is 7.x, which has no JavaScript API, so vue-tsc and typescript-eslint break with it (`stack.md` 5.1 and 5.3).

## Options considered

1. **Python version.**
   - 3.13: every library supports it, but it already gets security fixes only.
   - 3.14 (current patch 3.14.8): every dependency has wheels, and it gets bug fixes until October 2027.
   - 3.15: the newest release, but key libraries do not support it yet.
2. **Project layout.**
   - One uv workspace with one lock file: one install command, consistent versions across squads, and editable links between packages. The cost is one shared set of versions for everyone.
   - Separate projects joined by path dependencies: each squad could pin its own versions, but there would be seven lock files, and drift between them.
3. **Quality tools.** ruff for lint and format, mypy strict as the type gate, pytest with markers, and pre-commit for the same checks before every commit. Alternatives for the type gate: pyright or basedpyright, which the research recommends as optional editor checkers next to mypy, or ty, which is still in beta.
4. **Developer entry point.**
   - A Makefile: the GNU Make that ships with macOS (3.81 on the operator's Mac) and the one on Linux both run it. Windows has no `make`, so Windows users work in the devcontainer.
   - Only the raw `uv`, `npm` and `docker compose` commands, documented in the README: nothing to install, but long commands, and every person and agent types them a little differently.
5. **Frontend runtime.**
   - Node 24 with the create-vue 3.24 pins: what the official scaffold supports today.
   - Node 26: it becomes LTS only on 28 October 2026, and the create-vue pins were checked against Node 24.

## Decision

We will use:

- **Python 3.14** for the whole workspace: `requires-python = ">=3.14,<3.15"` and `.python-version` set to `3.14`.
- **One uv workspace.** The root `pyproject.toml` (`neonradar-workspace`, not published) lists the seven members. It depends on `neonradar-cli`, and `neonradar-cli` depends on every other member, so a plain `uv run` installs them all. There is one `uv.lock`, and the build backend is `uv_build>=0.13.1,<0.14`.
- **These quality tools.**
  - ruff: line length 100, target py314, rules `E F I B UP SIM RUF S`. `scripts/*.py` gets a py312 target and `.claude/hooks/*.py` a py39 target, so ruff never writes syntax their system Python rejects.
  - mypy: strict, with the pydantic plugin, over the seven `src` directories.
  - pytest: markers `contract`, `integration`, `network` and `e2e`. The default run excludes integration, network and e2e tests and uses `--import-mode=importlib`.
  - pre-commit: ruff-check, ruff-format, uv-lock and gitleaks.
- **A Makefile as the developer entry point.**
  - `make setup` installs everything, and `make check` runs what every pull request needs.
  - Targets that later milestones fill in print which milestone fills them and succeed.
  - Windows users use the devcontainer (M1.5).
- **Node 24 LTS** for the UI, with the create-vue 3.24 pins from `PHASE-1.md` 3.1: `typescript ~6.0.3`, never 7.x.

## Consequences

- **One way to work.** One command installs everything and one command checks it, the same on every machine and in CI (M1.6). The lock file makes every install identical.
- **Shared versions.** All squads share one set of dependency versions, and a squad that needs a conflicting version must raise it with the others. Members cannot be split out without moving to path dependencies.
- **Unfamiliar syntax in package code.** With the 3.14 target, ruff writes `except A, B:` (PEP 758) in package code. This is valid on 3.14 but looks unusual to readers who know older Python.
- **Scripts keep older targets.** A new script that runs on a system Python goes in `scripts/` or `.claude/hooks/`, so it gets the older target. `guard_git.py` stays outside mypy's file list: it runs on Python 3.9 and has no type annotations, which strict mode would require (51 errors if checked).
- **ICU on every machine.** Each contributor needs ICU headers before followthemoney arrives in M1.7a. `neonradar doctor` (M1.3-2) checks for them, and the devcontainer and CI install them.
- **No Markdown formatting.** ruff 0.17's default file list includes Markdown, which would rewrite code blocks in the research notes and the specs. The ruff settings exclude `*.md`: documentation is reviewed by reading, and some of its code blocks show wrong code on purpose.
- **Revisit.** Move to Python 3.15 once `duckdb`, `graphdatascience` and `neo4j-graphrag` support it. Review the Node line after Node 26 becomes LTS. Revisit ty when it leaves beta.

## Sources

- `docs/research/2026-10-16/stack.md`: sections 3.1 (which Python to pin), 3.2 (tool versions), 3.3 (uv workspaces), 3.4 (lint, format and hooks), 3.5 (PyICU), 5.1 to 5.3 (frontend versions and the TypeScript 7 trap), 7.4 (gitleaks) and the pinned versions table.
- `docs/build/PHASE-1.md`: sections 3.1 (pinned versions), 3.2 (known traps: ruff with a 3.14 target, the pytest import mode) and milestone M1.3.
- Checked on 2026-10-21 in this repository, with ruff 0.17.1, uv 0.13.4 and mypy 2.4.0:
  - `ruff check --show-settings` lists `*.md` in ruff's default `include`;
  - a probe file showed that the per-file target versions keep `except (A, B):` in `scripts/` and `.claude/hooks/` and rewrite it in package code;
  - `bash scripts/test_hooks.sh` still passes 172 of 172 with these settings.
