# Real-data handling

| | |
|---|---|
| Owner | Data steward (`people.data_steward` in `docs/build/project.yaml`) |
| Decision record | [ADR-0018](../decisions/0018-real-data-handling.md) (proposed) |
| Rules | `docs/build/PHASE-2.md` sections 2.1 (G2, G8 to G10) and 7.4 |
| Status | Drafted by the build agent in M2.0; the data steward edits and approves it |

From Phase 2 on, NeonRadar can load real records about real people: company officers, people with significant control, sanctioned persons and the names in the ICIJ Offshore Leaks Database. This page says where that data may live, who may see it, how long it stays, and how the project's tools keep it away from the AI agent that helps build the project. It is a practical project rule set, not legal advice: the data steward decides, and the legal analysis is in the research notes [bulk-sources-loading.md section 10](../research/2026-10-18/bulk-sources-loading.md#10-companies-house-data-and-data-protection-q9) and [sanctions-peps.md section 8](../research/2026-10-18/sanctions-peps.md#8-data-protection-analysis-not-legal-advice).

Much of this data is personal data under UK GDPR Article 4(1) [uk_gdpr], and the analysis in the research notes treats a sanctions designation as possibly criminal offence data under Article 10, following the ICO's guidance. Robotat is the controller for the real data its staff and interns load in this project; anyone else who runs NeonRadar on real data is the controller for their own copy (Article 4(7)) [uk_gdpr].

## The rules

These apply to every machine and every person, not only to the agent (PHASE-2.md 7.4).

1. **Before the first real run.** The data steward, with the project lead, files in `docs/data/dpia/` the documents PHASE-2.md 7.4 rule 1 lists: a legitimate interests assessment, a data protection impact assessment, the condition from Schedule 1 to the Data Protection Act 2018 that the processing relies on, with its appropriate policy document where that condition needs one, and the approach to UK GDPR Article 14 (information for people whose data was not obtained from them) [uk_gdpr], including the privacy information the project publishes. The research note `sanctions-peps.md` section 8 quotes the ICO on these documents. Only then does the data steward set `access.data_protection_filed: true`. Until then every real-profile command refuses to run (M2.2).
2. **Where.** Real data lives only under `data/cache/real/` and `data/cache/spikes/`, and in the separate Neo4j instance `neo4j-real` (Docker volume `neo4j-real-data`), on a machine listed in [real-data-machines.md](real-data-machines.md). DuckDB spill files of a real run go to `data/cache/real/duckdb-tmp/<run_id>/` and are deleted when the run ends. Never in GitHub Codespaces, CI, cloud sessions, shared drives, chat tools or email. The default Neo4j instance (`neo4j`) holds synthetic data only.
3. **How long.** `neonradar data purge --expired` (M2.2) deletes downloads, records, resolution runs, decisions and logs older than `access.real_data_days` (30 by default), label files older than `access.label_days` (30) and spike output older than `access.spike_cache_days` (7). Someone runs it; `neonradar doctor` warns when anything is older.
4. **What leaves the machine.** Only counts-only reports: counts, timings, rates, versions and settings, never a value from a record. No names, birth dates, addresses, identifiers or source record ids of real people in any pull request, issue, commit, screenshot, recording, slide or chat message. Real company numbers and LEIs of companies may appear in documentation where PHASE-2.md puts them (the `uk-tiny` seeds), never with a pattern or a flag next to them.
5. **Logs and errors.** Library code logs record ids and values only at DEBUG, and real-data commands never run at DEBUG in a session with the agent. On a real profile an error prints its class, the step, the dataset, the rule id and a run-local reference; the full traceback goes to `data/cache/real/logs/` and is purged with the rest (the redaction guard, M2.2).
6. **The agent** never reads real records (below).
7. **The local API and UI** connect to the default instance, so they show synthetic data. `neonradar api serve --real` (port 8001, M2.12) serves the real instance to a person at a terminal on an approved machine. Nobody takes screenshots of real data; the demo uses synthetic data only.
8. **Labels and review decisions** are personal data too. They stay in `data/cache/real/`, are purged as rule 3 says, and are never copied into the repository. Label files hold record ids and labels only; the data steward may extend `access.label_days` so that others can audit the published precision figure.
9. **Questions from the public.** Anyone who believes NeonRadar shows wrong data about them is pointed to the source register for corrections, and the project corrects its own code if the error is NeonRadar's. Anyone else who runs NeonRadar on real data is the controller for their own copy [uk_gdpr] ([ADR-0006](../decisions/0006-data-licensing.md)).
10. **If real data reaches the repository** or any other place in rule 4: stop, tell the data steward and the tech lead at once, and do not try to fix history yourself. An admin removes it, and the data steward records what happened in `docs/data/incidents.md` without repeating the data.

## How the guards work

Instructions alone are not enough, so the agent kit enforces rules 2, 4 and 6 with code that runs before each of the agent's tool calls. The guards load when a Claude Code session starts.

| Guard | Where | What it does |
|---|---|---|
| Permission rules | `.claude/settings.json` | Deny `Read` of `data/cache/real/**` and `data/cache/spikes/**`, and `Edit` anywhere under `data/cache/` (which covers the tools that write files). Each rule appears twice: relative to the current folder (`./data/...`, as PHASE-2.md wrote it) and anchored at the project root (`/data/...`), because Claude Code reads `./path` relative to the current folder. Claude Code also applies these deny rules to file commands it recognises in Bash (`cat`, `head`, `tail`, `sed`, `tee`) and to redirections. `WebFetch` of the hosts that serve list, register or leak data asks a person first. |
| Hook | `.claude/hooks/guard_real_data.py` | Runs before every `Bash`, `Read`, `Grep`, `Glob`, `WebFetch` and Neo4j MCP call. Details below. |
| Rules files | `.claude/rules/real-data.md`, `.claude/rules/er.md` | Load into the agent's context when it works on the folders they name. |
| Subagent | `.claude/agents/data-guardian.md` | Reviews a diff for real-data leaks, flag safety and label rules. |
| Separate instance | `compose.yaml` service `neo4j-real` | Real graphs never share a database with the tools the agent uses every day. |
| Redaction guard | `neonradar_cli.redact` (M2.2) | Real-profile errors print no values (rule 5). |
| Masked validation | `neonradar contracts validate-records` and the spike commands | For a record that is not synthetic, each issue shows the file, the line and the rule, with values, `nr` keys and long numbers replaced by `<value>` and no record id; a synthetic record's issue shows any real record id it quotes as `<record id>`. |
| Human-only commands | `neonradar er label`, `er review`, `api serve --real` | Refuse to run when stdin is not a terminal (M2.10c, M2.12). |

What the hook blocks (exit 2, with a reason):

- **Shell commands that touch real data.** A command line that names `data/cache/real` or `data/cache/spikes` (directly, through a glob, a relative or absolute path, another worktree, or by changing into the folder) may only run listing and housekeeping programs such as `ls`, `du`, `wc`, `stat`, `find` without actions, `mkdir` and `rm`; the read-only `git` subcommands without the flags that read files outside the index; and the project's own commands (`uv run neonradar ...`, `make ...`), which print counts only. Interpreters, `cat`, `head`, `jq`, `duckdb` and the like are blocked there. Nobody may change into `data/`, `data/cache/` or a real-data folder, and recursive readers (`grep -r`, `rg --no-ignore`, `tar`, `zip`, `rsync`, `cp -r`, `find -exec`) may not run over a folder that holds real data.
- **The real instance.** A command that names `neo4j-real`, the database `realdata`, the ports 7475, 7688 or 8001, `NR_NEO4J_REAL_*` or `NEO4J_REAL_PASSWORD` may only be `uv run neonradar`, `make`, or `docker compose up`, `start`, `stop`, `down` or `ps`. So `cypher-shell` against port 7688, a Python driver opened on it, `docker compose logs neo4j-real` and `docker volume rm` of its volume are blocked for the agent.
- **Human-only commands** (`er label`, `er review`, `api serve --real`) and the terminal wrappers `script`, `expect`, `unbuffer` and `faketty`.
- **Downloads of data.** `WebFetch`, `curl`, `wget` and similar tools may fetch documentation, schemas (`.xsd`) and API descriptions (swagger, OpenAPI), but not list, register or leak data files, nor pages about real people (for example a Companies House officer page).
- **Password leaks.** `docker compose config` without `--quiet` or a listing flag, and `docker inspect`, print the passwords in `.env`.
- **`Read`, `Grep` and `Glob`** with a path, glob or pattern that can reach the two folders. A repository-wide `Grep` is allowed: it skips the gitignored `data/cache/`.
- **The Neo4j MCP server** when `.mcp.json` names the real instance.

The hook stops accidents, not a determined person. The permission rules, `CLAUDE.md` and the people who run the project remain responsible. Its 171 test cases are in `scripts/tests/test_guard_real_data.py`; `bash scripts/test_hooks.sh` runs them, and CI runs that script on every pull request.

Known limits, stated plainly:

- **The hook matches command text.** A path assembled while the command runs, from a shell variable, a command substitution, an encoded or concatenated string, or a file a program reads its paths from, is not caught. Neither is a program that opens files itself (a Python or Node script, for example) when its command line does not name the folder.
- **Only the project's MCP configuration is checked.** The hook reads `.mcp.json` in the repository. An MCP server configured at user or local scope (`~/.claude.json`, `claude mcp add` without `--scope project`) is not checked, so nobody configures a Neo4j MCP server there that points at the real instance.
- **The `ask` rules need a person to be asked.** In auto or bypass permission modes nobody is asked, so a `WebFetch` of the data hosts relies on the hook alone.
- **The permission rules have their own gaps.** Claude Code applies `Read` and `Edit` deny rules to its file tools and to the file commands it recognises in Bash. They do not apply to a command that reads files without naming them, or to a program that opens files itself; that is why the hook exists. A `Write(...)` path rule is accepted but never consulted (Claude Code checks `Edit` rules for writes), so the spec's `Write(./data/cache/**)` entry does nothing beyond a warning at startup.

**Test before the first real-data run.** Before the first real profile is added to `access.real_data_profiles`, the data steward, a person rather than the agent, tests the guards in a fresh Claude Code session with their own attempts to get round them. These come on top of the operator check in PHASE-2.md M2.0. The data steward records each attempt and its result, with no real data in the record, in the pull request that enables the first real profile.

## The real-data instance

| | Default instance | Real-data instance |
|---|---|---|
| Compose service | `neo4j` | `neo4j-real` (Compose profile `real`) |
| Ports (localhost only) | 7474 (browser), 7687 (Bolt) | 7475 (browser), 7688 (Bolt) |
| Database | `neo4j` | `realdata` (its only database) |
| Volume | `neo4j_data` | `neo4j-real-data` |
| Holds | synthetic data only | real profiles only (C2 rule L17, M2.11) |
| Used by | the API on port 8000, the UI, tests, the Neo4j MCP server, the agent | `neonradar` real-profile commands and `api serve --real` (port 8001, humans only) |

Because the real instance's only database is `realdata`, a query or a load sent to the wrong instance fails: the database does not exist there. Both instances run the same image, plugins, memory settings and migrations.

On an approved machine:

1. Set `NEO4J_REAL_PASSWORD` (at least 8 characters) and `NR_REAL_DATA_MACHINE=approved` in `.env`. `NR_NEO4J_REAL_URI` keeps its default, `bolt://127.0.0.1:7688`. On every other machine, leave the password and `NR_REAL_DATA_MACHINE` empty.
2. `make plugins` once (the image and the pinned GDS jar, shared with the default instance).
3. `make up-real` starts it and waits until it is healthy. `make down-real` stops it and keeps its data. A plain `docker compose up` or `make up` never starts it, and Docker does not restart it after a reboot.
4. Before the first real load: `uv run neonradar graph migrate --real` (M2.11).

`uv run neonradar doctor` warns while the instance is running.

## Purging

- `uv run neonradar data purge --expired` deletes what is older than the retention settings (rule 3) (M2.2).
- `uv run neonradar data purge --all-real --graph --yes` deletes all real data on the machine, including the real instance's volume: a volume-level wipe, so Neo4j's transaction logs and store files go with it, where deleted nodes would otherwise linger (M2.2).
- `uv run neonradar doctor` warns about real files older than the retention settings and about DuckDB spill folders that a crashed run left behind. It reads file ages and counts only.
- The data steward confirms in the Phase 2 report that the purge ran on every approved machine (PHASE-2.md 1.9).

Phase 1's `make reset` (`docker compose down -v`) may also remove the real volume, depending on the Compose version. That loses only data the operator can load again.
