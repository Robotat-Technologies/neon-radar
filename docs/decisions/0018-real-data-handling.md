# 0018. Real-data handling

- **Status:** proposed
- **Date:** 2026-10-22
- **Deciders:** @robotat-com (data steward)

## Context

Phase 2 is the first phase that loads real personal data at scale: Companies House officers and people with significant control, sanctioned persons from the UK, US and EU lists, and the names in the ICIJ Offshore Leaks Database (`docs/build/PHASE-2.md` 0.4 and 3.3). Most of it is personal data under UK GDPR Article 4(1) [uk_gdpr], and the research notes, following the ICO's guidance, treat a sanctions designation as possibly criminal offence data under Article 10. Robotat is the controller for the real data its staff and interns load in this project, and anyone else who runs NeonRadar on real data is the controller for their own copy (Article 4(7)) [uk_gdpr] (PHASE-2.md 3.3 and 7.4; the analysis in `docs/research/2026-10-18/bulk-sources-loading.md` section 10 and `sanctions-peps.md` section 8, which is not legal advice).

The project is built with an AI agent (Claude Code, [ADR-0011](0011-ai-built-workflow.md)) that reads files, runs shell commands, fetches web pages and queries the local Neo4j database. Anything the agent reads enters its context, and from there can reach chat transcripts, pull requests or commits. Guardrail G9 says the agent never reads real records; G2 keeps real data out of the repository; G10 keeps labelling with people (PHASE-2.md 2.1). Instructions in `CLAUDE.md` are necessary but not sufficient: a rule an agent can forget on a busy afternoon needs a control that does not depend on its memory.

The operator chose a synthetic-only start: `access.real_data_profiles: []` and `access.data_protection_filed: false` until the data protection documents are filed (operator decision OD-22). The controls below must exist before the first real profile runs, so they are built now (M2.0, M2.2, M2.10c, M2.11, M2.12).

## Options considered

1. **Rules in `CLAUDE.md` only.** Cheap, but nothing stops a mistaken `cat`, a repository-wide search or a `curl` of a list file; the first slip already puts real records into a transcript.
2. **Permission rules only** (`Read` denied on the real-data folders). Stops the `Read` tool, but not shell commands, absolute paths, other worktrees, `Grep` and `Glob` patterns, web fetches or database queries.
3. **Permission rules, a hook over every tool that can read, and a separate database instance for real data** (chosen). The hook understands shell command lines, paths, globs and URLs; the separate instance keeps real graphs away from the tools the agent uses every day.
4. **Real data only on machines where no agent runs.** The strongest control, but it doubles every workflow and still needs the same rules for the people on those machines; it stays open as a stricter choice for the data steward.

## Decision

We will handle real data by the rules in PHASE-2.md 7.4, written out for everyone in [`docs/data/real-data-handling.md`](../data/real-data-handling.md): the documents filed before the first real run, real data only under `data/cache/real/` and `data/cache/spikes/` and in the real-data instance on approved machines ([`docs/data/real-data-machines.md`](../data/real-data-machines.md)), retention by `access.real_data_days` and `access.label_days`, counts-only output, redacted errors, labels and decisions kept local, corrections pointed to the source register, and the incident procedure.

We will enforce them for the agent with these controls:

- **Permission rules** in `.claude/settings.json`: `Read` of `data/cache/real/**` and `data/cache/spikes/**` denied, `Edit` (which covers writes) under `data/cache/` denied, each both relative to the current folder and anchored at the project root, and `WebFetch` of the hosts that serve list, register or leak data set to ask a person first.
- **The hook** `.claude/hooks/guard_real_data.py`, run before every `Bash`, `Read`, `Grep`, `Glob`, `WebFetch` and Neo4j MCP call. It blocks shell command lines that would read from the real-data folders (directly, through globs, absolute paths, other worktrees or a changed folder), recursive readers over them, git flags that read files outside the index, commands that address the real instance other than `uv run neonradar`, `make` and `docker compose up`, `start`, `stop`, `down` or `ps`, downloads of list, register and leak data files and of pages about real people, `docker compose config` and `docker inspect` (which print passwords), `Read`, `Grep` and `Glob` on the real-data folders, the Neo4j MCP server pointed at the real instance, the human-only commands and the wrappers that fake a terminal. Its 171 test cases run in CI.
- **A separate real-data instance**: the Compose service `neo4j-real` (profile `real`, ports 7475 and 7688 on localhost, volume `neo4j-real-data`, and one database named `realdata`, so a query sent to the wrong instance fails). Real profiles load only there (C2 rule L17, M2.11). The tools the agent uses every day (the default instance, the API on port 8000, the UI, the end-to-end tests and the Neo4j MCP server) never reach it.
- **The redaction guard** for real-profile commands (M2.2): an error prints its class, the step, the dataset, the rule id and a run-local reference; the traceback stays in `data/cache/real/logs/`. `neonradar contracts validate-records` masks values and record ids of records that are not synthetic (M2.0).
- **The terminal rule**: `neonradar er label`, `er review` and `api serve --real` refuse to run when stdin is not a terminal (M2.10c, M2.12), so only a person at a keyboard labels, reviews or browses real data (G10).
- **Counts-only summaries**: every real-profile command prints counts, timings, rates, versions and settings, and writes the same summary to `data/cache/reports/<profile>/`, the only place under `data/cache/` the agent reads for a real profile.
- **The data-guardian subagent** (`.claude/agents/data-guardian.md`), which reviews any change under `ingest/`, `keys/`, `resolve/`, `graph/`, `api/`, `cli/`, `data/` or `docs/data/` for real-data leaks, flag safety and label rules.
- **Retention and purge**: `neonradar data purge --expired` and `--all-real --graph --yes` (M2.2); `--graph` deletes the real instance's Docker volume, a volume-level wipe that also removes Neo4j's transaction logs and store files, where deleted nodes would otherwise linger. `neonradar doctor` warns about expired real data, leftover DuckDB spill folders and a running real instance.
- **Incident handling**: if real data reaches the repository or any other place it must not go, whoever sees it stops and tells the data steward and the tech lead at once; an admin removes it; the data steward records what happened in `docs/data/incidents.md` without repeating the data.

## Consequences

- The agent can work freely with synthetic data: the default instance, the API, the UI, the MCP server, `data/cache/synthetic/` and the counts-only reports. Failures on real data are reproduced on the demo profile or the entity resolution benchmark.
- People on approved machines run every real-data command and paste only counts into pull requests (PHASE-2.md 2.2 step 6a). That is slower than letting the agent look, on purpose.
- Two Neo4j instances can run side by side on one machine; together they need twice the memory, so the real instance runs only while someone works with it, and Docker does not restart it after a reboot.
- The hook and the permission rules load when a Claude Code session starts, so a change to them takes effect in the next session; the operator check in PHASE-2.md M2.0 confirms them after the merge.
- **The honest limit.** The hook stops accidents, not a determined person, and has known limits:
  - It matches command text, so paths assembled while a command runs (shell variables, command substitution, encoded strings, programs that open files themselves) are not caught.
  - It checks only the project's `.mcp.json`; MCP servers configured at user or local scope are not checked.
  - In auto or bypass permission modes nobody is asked, so the `ask` rules for the data hosts rely on the hook alone.

  Beyond the hook, a person can paste real data into a chat, and a machine can be lost. The permission rules, `CLAUDE.md`, the approved-machine list, the data protection documents and the people who run the project remain responsible.
- **A person tests the guards first.** Before the first real-data run, the data steward tests the hook and the permission rules in a fresh session with their own attempts to get round them, and records the attempts and the results, with no real data, in the pull request that enables the first real profile.
- Follow-up: M2.2 (data manager, real-profile gate, redaction guard, purge), M2.10c (labelling and review commands), M2.11 (loader routing to `neo4j-real`, `graph migrate --real`), M2.12 (`api serve --real`). The data steward files the documents in `docs/data/dpia/` and lists approved machines before `access.real_data_profiles` changes.

## Sources

- `docs/build/PHASE-2.md` sections 2.1 (G2, G8 to G10), 3.3, 4.1, 4.5, 7.4 and M2.0.
- `docs/research/2026-10-18/bulk-sources-loading.md` section 10 and `docs/research/2026-10-18/sanctions-peps.md` section 8 (data protection analysis, not legal advice).
- UK GDPR Articles 4, 10 and 14 [uk_gdpr].
- [ADR-0006](0006-data-licensing.md) (data licensing) and [ADR-0011](0011-ai-built-workflow.md) (AI-built workflow).
- `docs/build/operator-decisions.md` OD-14 (agents never read `.env`), OD-20 and OD-22.
