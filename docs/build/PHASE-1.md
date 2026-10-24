# NeonRadar build spec, Phase 1: Foundation and contracts

| | |
|---|---|
| File | `docs/build/PHASE-1.md` |
| Version | 1.0, 16 October 2026 |
| Phase window | Friday 16 October to Friday 23 October 2026 (Gate 1: schema frozen) |
| Built by | Claude Code (VS Code extension or CLI), one milestone per pull request |
| Reviewed and merged by | Humans only |
| Facts verified on | 16 October 2026 (section 3, with the full research notes in `docs/research/2026-10-16/`) |
| Next document | `docs/build/PHASE-2.md` (Ownership graph), written after Gate 1 |

This document is both a plan and a set of executable instructions. Humans read it to know what will be built and what they must decide or review. Claude Code reads it to build the project, milestone by milestone, without needing a new prompt for every step.

---

## 0. How to use this document

### 0.1 Who reads what

| Reader | Reads | Why |
|---|---|---|
| Operator (tech lead or project lead) | Sections 0, 1 and 8 in full, then the "Review focus" box of each milestone | Prepares access and decisions, starts each milestone, checks Gate 1 |
| Claude Code (the build agent) | Sections 0, 2, 3, 4 and 5 once per session, then only the active milestone in section 6, plus section 7 when a milestone points there | Executes milestones within the rules |
| Reviewers (mentors and interns) | The pull request, the milestone's "Review focus" box, and section 5 for any contract change | Decide whether the work is correct and understood |

### 0.2 How the build runs

```text
operator: /milestone M1.x  (or the explicit prompt in 1.7)
   |
   v
Claude Code: read spec -> plan -> branch -> build -> run acceptance commands
             -> independent review subagent -> update PROGRESS.md -> open PR -> STOP
   |
   v
humans: CI + review checklist + named reviewer -> request changes or approve -> MERGE
   |
   v
next milestone (or several in parallel, see 1.8)
```

Claude Code never merges. A human merges every pull request, and that merge is the only way work reaches `main`.

### 0.3 The six phases

| Phase | Name | Dates (2026) | Ends with | Main output |
|---|---|---|---|---|
| 1 | Foundation and contracts | Fri 16 Oct to Fri 23 Oct | Gate 1, Fri 23 Oct: schema frozen | Repository, tooling, CI, agent kit, four frozen contracts, data source spikes, a thin end-to-end walking skeleton |
| 2 | Ownership graph | Mon 26 Oct to Wed 4 Nov | Gate 2, Wed 4 Nov: graph loads end to end | Production loaders for Companies House, GLEIF, ICIJ and a sanctions source; entity resolution with a published precision figure |
| 3 | Transactions and detection | Mon 26 Oct to Fri 13 Nov | Gate 3, Fri 13 Nov: detections green | Synthetic transaction overlay attached to entities, 10 typology detections with fixtures, evaluation harness with precision and recall |
| 4 | API and investigation copilot | Mon 2 Nov to Fri 13 Nov | Part of Gate 3 | Complete API v1, a template-first local copilot that answers the 10 benchmark questions |
| 5 | Explorer UI | Mon 2 Nov to Tue 17 Nov | Gate 4, Tue 17 Nov: feature freeze | Vue explorer: search, network canvas, alert queue, explain panel |
| 6 | Hardening, documentation and launch | Mon 16 Nov to Fri 20 Nov | Gate 5, Fri 20 Nov: public launch | Documentation site, benchmark, demo video, launch post, every definition-of-done box ticked |

Phases 2 and 3 overlap on purpose: the contracts frozen in Phase 1 are what let the Ingestion, Graph and Detection squads work in parallel.

### 0.4 Phase 1 scope

In scope:

- Repository, governance files, labels, issue and pull request templates.
- The agent kit: `CLAUDE.md`, path-scoped rules, settings, hooks, skills, subagents and a read-only Neo4j MCP server, so every later AI session builds in the same style.
- Python workspace (uv), Node toolchain, `neonradar` command line, Makefile.
- Local stack: Neo4j 5.26 LTS Community with APOC and GDS in Docker Compose; devcontainer and Codespaces.
- CI, quality gates and repository protection.
- The four contracts, frozen at Gate 1: the record format (C1), the graph schema (C2), the API (C3) and the alert object (C4), with a contract test suite.
- Spikes that fetch a small slice of each data source end to end, and a spike that proves synthetic accounts can be attached to entities.
- A walking skeleton: synthetic fixture, graph load, one detection (circular flow), API, a bare UI that shows the alert and its evidence.
- Knowledge base seeds: standing disclaimer, wording rules, glossary, bibliography, 15 typology drafts, case notes, architecture decision records.
- Team kits: onboarding assignments 1 and 2, learning track scaffolding, contributor ledger.
- The Gate 1 check and a Phase 1 report.

Out of scope (later phases): production loaders and entity resolution (Phase 2), the full synthetic generator and the other nine detections (Phase 3), the copilot (Phase 4), the real explorer UI (Phase 5), the documentation site, benchmark and launch (Phase 6).

### 0.5 What changed from the project plan

Research on 16 October 2026 changed several assumptions in the project plan. Humans should know these before the build starts. Details and sources are in section 3 and in `docs/research/2026-10-16/`.

| # | Plan said | Phase 1 does | Why |
|---|---|---|---|
| 1 | Neo4j 5.x | Pins `neo4j:5.26.32-community` (5.26 is the LTS line) | Neo4j moved to calendar versions (newest 2026.09.0). 5.26 LTS is supported until June 2028, ships APOC Core and GDS 2.13 in the image, and is the Cypher dialect AI models know best. Revisit when the 2026 LTS ships (ADR-0002). |
| 2 | Python 3.11+ | Python 3.14 | 3.13 is now security-only; 3.15 (released 9 Oct) lacks wheels for duckdb and the GDS client; numpy and pandas dropped older versions. |
| 3 | OpenSanctions as a source | Loader stays, but use is gated by a licence decision | OpenSanctions data is CC BY-NC 4.0 and states "Any use inside a for-profit business requires a data license." Development uses synthetic fixtures; a 1,000-entity evaluation slice only after the operator records the decision (1.2). |
| 4 | ICIJ Offshore Leaks | Load from ICIJ directly | ICIJ data is ODbL plus CC BY-SA, commercial use allowed with citation. The OpenSanctions copy of ICIJ is CC BY-NC. |
| 5 | Companies House bulk data | Officers come from the REST API | No free bulk officers file exists. The API allows 600 requests per 5 minutes. New identity-verification fields appeared in 2025. |
| 6 | GLEIF as a source | GLEIF joins to Companies House deterministically | `registeredAt` RA000585, RA000586 or RA000587 plus `registeredAs` equal to the company number. API limit 60 requests per minute; GLEIF warns of outages 19 October to 4 November. |
| 7 | Splink, FollowTheMoney | Splink 5, FollowTheMoney 4.11 | Both changed their Python APIs in 2025 and 2026. AI-written code defaults to the old APIs, so `CLAUDE.md` lists the traps. |
| 8 | IBM AMLSim generator | Own seeded Python generator | AMLSim is unmaintained since 2022, needs Java 8 and an old Python, and cannot attach accounts to existing entities. |
| 9 | "UNODC estimates as much as 5% of GDP" | Cite correctly | UNODC (2011) attributes the 2 to 5 percent range to the IMF (1998) and gives its own estimate of about 2.7 percent of global GDP for 2009. |
| 10 | Sprint 0 is analysis only | Adds a thin walking skeleton | Contracts are proven by running code before they freeze. |
| 11 | Assignment 1 due Fri 16 Oct, Assignment 2 due Mon 19 Oct | Assignment 1 due Tue 20 Oct, Assignment 2 due Thu 22 Oct | The repository and the onboarding kit are built during the first days of this phase. |
| 12 | "A laundering chain can run through a genuine shell company structure from Companies House" | Synthetic accounts and background payments attach to real entities, but planted scenarios run only among synthetic entities (G1). Any exception needs an ADR and the safeguards in G1. | The plan's own definition of done says "No real person or company labelled suspicious anywhere in the repo, the demo or the screenshots"; personal data rules; the research recommendation in `synthetic-docs-mcp.md` part A. |
| 13 | Each intern writes one typology explainer (Assignment 2) | The agent drafts all 15 explainers; each intern checks one sentence by sentence against its sources, corrects it and opens the pull request under their own name | The build is AI-first with human review; checking a draft against the source still means reading the source. |
| 14 | Detection queries are written only after the typology researcher has written the definition | The walking skeleton's circular-flow detector is built against the draft definition in 5.4, and the researcher must approve it before Gate 1 (GC-10); every Phase 3 detector waits for its typology's approval | The contracts must be proven by running code before they freeze. |
| 15 | ADRs are "written by whoever made it" | The agent drafts each ADR from this spec with status `proposed`; the named deciders edit it until it says what they think and set it to `accepted` | Authorship and understanding stay with the deciders while the agent does the typing. |

---

## 1. Operator setup (humans, before the first prompt)

### 1.1 Accounts, tools and access

Do these on the machine that will run Claude Code. Tick each box before the kickoff prompt.

- [ ] **GitHub organisation and repository.** Create an empty private repository `<org>/neonradar` with default branch `main`. Keep it private until launch day.
- [ ] **GitHub teams.** Create one team per squad (`nr-ingest`, `nr-graph`, `nr-detect`, `nr-copilot`, `nr-ui`, `nr-docs`) and `nr-maintainers` (tech lead and mentors). Add people. Give each squad team the Write role on the repository and `nr-maintainers` the Maintain role: CODEOWNERS ignores teams that cannot write to the repository.
- [ ] **GitHub CLI.** Install `gh` and run `gh auth login` with scopes `repo`, `workflow` and `read:org`. Claude Code uses `gh` to open pull requests and create labels and issues. Repository settings that need admin rights (branch protection, secret scanning) are scripted but run by a human.
- [ ] **Claude Code.** Install the "Claude Code" extension in VS Code 1.94 or later (Extensions view, search "Claude Code", publisher Anthropic). Sign in with a paid Claude plan or a Claude Console account. Optional: install the standalone CLI if you also want `claude` in the integrated terminal.
- [ ] **Docker.** Docker Desktop (macOS, Windows) or Docker Engine (Linux) with Compose v2 or later. Give the Docker VM at least 8 GB of memory. On a 16 GB laptop the Docker Desktop default (half of RAM) is enough.
- [ ] **Local tools** (or use the devcontainer from M1.5 instead): `git` 2.40+, `make`, `jq`, `uv` 0.13+, Node.js 24 LTS, and ICU headers for PyICU (`apt install pkg-config libicu-dev build-essential` on Debian or Ubuntu; `brew install icu4c pkg-config` on macOS). Windows users should use the devcontainer.
- [ ] **Companies House API key.** Register at the Companies House developer hub, create a live application, create an API key. Put it only in `.env` as `CH_API_KEY=...` after M1.4 creates `.env.example`. Never paste it into a chat.
- [ ] **Optional: review agent in CI.** Install the Claude GitHub App on the repository and add a repository secret `ANTHROPIC_API_KEY` (Claude Console key) or `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`). Without it, CI still runs every deterministic check.

### 1.2 Decisions to record before the build

| Decision | Owner | Options | Where it goes |
|---|---|---|---|
| OpenSanctions route | Data steward and project lead | `none` (default: synthetic fixtures only); `evaluation` (a 1,000-entity stream for the spike, only after OpenSanctions confirms in writing); `licensed`; `exempt` (only if the organisation running NeonRadar itself qualifies for OpenSanctions' free programme: public-interest journalists, advocacy groups and nonprofits working on democratic governance or exposing corruption and financial crime, affiliated academics, or public institutions of Ukraine, Georgia and Moldova; never for a company team) | `access.opensanctions` in `project.yaml`; the request and OpenSanctions' written answer filed in `docs/data/licences/opensanctions.md` |
| Spike cache retention | Data steward | Days to keep spike output in `data/cache/spikes/` (default 7; it contains personal data from Companies House and ICIJ) | `access.spike_cache_days` in `project.yaml` |
| Named owners | Project lead | Tech lead, mentors, data steward, typology researchers, technical writer, demo producer, community manager, release manager for week 1 | `people` in `project.yaml` |
| Review agent in CI | Tech lead | `on` (needs the secret), `off` | `access.claude_review_action` |
| Codespaces | Project lead | `personal-quota` (each intern's free 120 core hours), `org-paid`, `off` | `access.codespaces` |
| Legal and communications heads-up | Project lead | Start the conversation now; sign-off needed before 20 Nov | Note in `docs/build/PROGRESS.md` |

### 1.3 Fill in `docs/build/project.yaml`

Claude Code reads this file for names, teams and access decisions. Leave `TODO` where unknown; Claude stops and asks when a milestone needs a value that is still `TODO`.

```yaml
# docs/build/project.yaml
# Filled in by the operator. Claude Code reads it; it never writes secrets here.
version: 1
project:
  name: NeonRadar
  repo: "<org>/neonradar"            # for example robotat/neonradar
  default_branch: main
  domain: neonradar.com
  description: "Open-source, local-first graph investigation for anti-money-laundering and anti-corruption work"
  security_contact: "TODO@example.com"
  conduct_contact: "TODO@example.com"
  licence: Apache-2.0
people:                               # GitHub handles, with the @
  project_lead: "@TODO"
  tech_lead: "@TODO"
  mentors: ["@TODO", "@TODO", "@TODO"]
  release_manager: "@TODO"            # rotates weekly; update this line each Monday
  data_steward: "@TODO"
  typology_researchers: ["@TODO"]
  technical_writer: "@TODO"
  demo_producer: "@TODO"
  community_manager: "@TODO"
  interns: ["@TODO", "@TODO"]         # every intern's GitHub handle (15 in the plan)
squads:                               # team slugs must exist in the org (section 1.1)
  ingest:  { team: "@<org>/nr-ingest",  dir: ingest,  mentor: "@TODO" }
  graph:   { team: "@<org>/nr-graph",   dir: graph,   mentor: "@TODO" }
  detect:  { team: "@<org>/nr-detect",  dir: detect,  mentor: "@TODO" }
  copilot: { team: "@<org>/nr-copilot", dir: copilot, mentor: "@TODO" }
  ui:      { team: "@<org>/nr-ui",      dir: ui,      mentor: "@TODO" }
  docs:    { team: "@<org>/nr-docs",    dir: docs,    mentor: "@TODO" }
maintainers_team: "@<org>/nr-maintainers"
access:
  companies_house_key: pending        # pending | available  (the key itself lives only in .env)
  opensanctions: none                 # none | evaluation | licensed | exempt  (see 1.2)
  spike_cache_days: 7                 # spike output holds personal data; delete it after this many days
  claude_review_action: off           # off | on
  codespaces: personal-quota          # personal-quota | org-paid | off
schedule:
  phase_1_start: 2026-10-16
  assignment_1_due: 2026-10-20
  assignment_2_due: 2026-10-22
  gate_1: 2026-10-23
  gate_2: 2026-11-04
  gate_3: 2026-11-13
  gate_4: 2026-11-17
  gate_5: 2026-11-20
```

### 1.4 Seed the repository

```bash
git clone git@github.com:<org>/neonradar.git && cd neonradar
mkdir -p docs/build docs/research/2026-10-16 docs/plan
# copy the kit files you received:
#   PHASE-1.md                      -> docs/build/PHASE-1.md
#   project.yaml (filled in)        -> docs/build/project.yaml
#   research/*.md                   -> docs/research/2026-10-16/
#   neonradar-project-plan.md       -> docs/plan/neonradar-project-plan.md
git add docs && git commit -m "docs(build): add phase 1 build spec and research notes"
git push -u origin main
code .
```

This seed commit is the only direct push to `main`. From M1.2 on, the `guard_git.py` hook stops Claude Code from pushing to `main`, and branch protection (M1.6) blocks everyone else where the GitHub plan allows it; on a private repository on the free plan, team discipline covers people until launch day (M1.6 explains).

### 1.5 Claude Code settings for this build

- **Permission mode.** Use Auto mode (the starting mode in recent Claude Code versions; a classifier reviews actions instead of prompting) together with the project's allow and deny rules from M1.2. Use Manual mode if you want to approve each command. Never use `--dangerously-skip-permissions` on your own machine; it is acceptable only inside the devcontainer, run as a non-root user.
- **One milestone per session.** Start each milestone in a fresh conversation (or run `/clear`), and name it with `/rename p1-m1-4` so it can be resumed.
- **Model.** Use your most capable model for M1.2, M1.7 and M1.9 and for every review; any current model is fine for the rest.
- **Plan first where marked.** Milestones marked "Plan first" start in plan mode (`/plan` in the VS Code prompt box, or Shift+Tab in the CLI). Read the plan, adjust it, then approve.
- **Evidence over claims.** Ask for the command output, not a summary, whenever something looks too easy.

### 1.6 The kickoff prompt (paste once, in a fresh session)

```text
You are the build agent for NeonRadar, Phase 1 (Foundation and contracts).

The build spec is docs/build/PHASE-1.md. Project facts (people, teams, access
decisions) are in docs/build/project.yaml. Verified research notes are in
docs/research/2026-10-16/.

Before doing anything else:
1. Read docs/build/PHASE-1.md sections 0, 2, 3, 4 and 5 in full, and read
   docs/build/project.yaml. Do not read all of section 6; read only the
   milestone you are executing.
2. Reply with five short bullets: the milestone order and dependencies, the
   rules you must never break, when you must stop and ask, how you prove a
   milestone is done, and what you do after opening a pull request.

Then execute milestone M1.1 exactly as section 6 describes, following the
milestone protocol in section 2.2. Stop when the pull request is open and
you have reported its URL and the verification evidence. Do not start
another milestone until I name it.
```

### 1.7 Milestone prompts and goal conditions

From M1.3 on, the `/milestone` skill (created in M1.2) carries the protocol, so the prompt is one line. For an unattended run, add a goal condition: Claude keeps working until the condition holds, and a separate evaluator checks it after every turn. The goal condition only works when Claude's own output can show it, so each condition names the evidence.

| Milestone | Prompt | Optional goal line (paste after the prompt has started) |
|---|---|---|
| M1.1 | Kickoff prompt (1.6) | `/goal M1.1 acceptance commands from PHASE-1.md were run in this session and passed, PROGRESS.md marks M1.1 pr-open with the PR URL, and the PR is open; stop after 40 turns` |
| M1.2 | `Execute milestone M1.2 from docs/build/PHASE-1.md following section 2.2.` | `/goal M1.2 acceptance commands passed in this session, the PR is open, and PROGRESS.md records it; stop after 40 turns` |
| M1.3 onward | `/milestone M1.3` (and so on) | `/goal <milestone id> acceptance commands passed in this session, CI on the PR is green (gh pr checks) or, before M1.6 is merged, the PR says "no CI yet", and PROGRESS.md records the PR URL; stop after 60 turns` |

When review comments arrive: `Address the review comments on PR #<n>. Reply to each comment with what you changed, re-run the milestone's acceptance commands, push, and stop.`

### 1.8 Parallel work and the merge rhythm

Milestones form a dependency graph. Milestones whose dependencies are all merged can run at the same time in separate worktrees (`claude --worktree m1-8a` in a terminal, or ask in the VS Code panel: "Run M1.8a, M1.8b and M1.8c in parallel using subagents with worktree isolation; each opens its own pull request").

```text
M1.1 bootstrap -> M1.2 agent kit -> M1.3 workspace
M1.3                        -> M1.4 local stack -> M1.5 devcontainer
M1.3                        -> M1.6 CI and protection
M1.3                        -> M1.7a record contract
M1.7a + M1.6                -> M1.7c alert contract
M1.7a + M1.4                -> M1.7b graph schema
M1.7b + M1.7c               -> M1.7d API contract
M1.7a (+ M1.4 for M1.8a)    -> M1.8a .. M1.8d spikes (parallel)
M1.7a + M1.6                -> M1.8e synthetic generator and join
M1.7b + M1.8e               -> M1.9a graph loader
M1.9a + M1.7c               -> M1.9b circular flow
M1.9b + M1.7d + M1.10a      -> M1.9c API endpoints
M1.7d                       -> M1.9d UI shell (parallel with M1.9a to M1.9c)
M1.9a .. M1.9d              -> M1.9e demo-mini and end-to-end test
M1.6                        -> M1.10a wording, glossary, bibliography -> M1.10c cases and reading list
M1.10a + M1.7c              -> M1.10b-1, M1.10b-2, M1.10b-3 typology drafts (parallel)
M1.4 + M1.6                 -> M1.11a onboarding and learning kit (Assignment 1)
M1.10b-1 .. M1.10b-3        -> M1.11b Assignment 2 kit
everything                  -> M1.12 Gate 1 check
```

The milestone headers in section 6 are the authority; this graph summarises them.

Suggested calendar:

| Day | Agent work (pull requests) | Human work |
|---|---|---|
| Fri 16 Oct | M1.1, M1.2, M1.3 | Section 1 setup; review and merge as they arrive |
| Mon 19 Oct | M1.4, M1.5, M1.6, M1.7a, M1.10a, M1.11a | Run the branch protection script; first contract review |
| Tue 20 Oct | M1.7b, M1.7c, M1.8a, M1.8b, M1.8c, M1.8e, M1.10b-1, M1.10b-2, M1.10b-3 | Assignment 1 due; typology researchers review the drafts |
| Wed 21 Oct | M1.7d, M1.8d, M1.9a, M1.9b, M1.10c, M1.11b | Assignment 2 starts; contract review round 2 |
| Thu 22 Oct | M1.9c, M1.9d, M1.9e, fixes from review | Assignment 2 due; teach-back 1; tech lead approves contracts |
| Fri 23 Oct | M1.12 | Freeze tag `contracts-v1.0.0`; Gate 1 decision; Friday demo |

Merge rule: merge in dependency order. When `main` has moved, bring the branch up to date by merging, never by rebasing (a rebased branch needs a force-push, which the guard hook blocks): `Merge origin/main into this branch, re-run the acceptance commands, push`. Every day from Monday to Thursday carries chains of two or three dependent merges, so the named reviewers (above all for M1.6, M1.7a, M1.7b, M1.7c, M1.8e, M1.9a and M1.9b) should keep time free for review on those days.

Parallel sessions on one machine share the one local Neo4j that `make up` starts. Run the milestones that load or wipe the local database (M1.4, M1.7b, M1.8e, M1.9a to M1.9e, M1.11a) one at a time per machine. Integration tests start their own Testcontainers database and are safe to run in parallel.

### 1.9 What humans do themselves

The agent writes code and drafts. These stay human, because the plan's learning track and accountability depend on them:

- Reviewing and merging every pull request, and defending or rejecting what the agent drafted.
- Approving the frozen contracts (tech lead) and creating the freeze tag.
- Approving typology definitions (typology researchers). The agent drafts; it never sets `status: approved`.
- Licence decisions and the OpenSanctions email (data steward).
- Learning logs, self-assessments, teach-backs and exit posts. The agent must not write these for anyone.
- Assignment 1 (each intern's first query and pull request) and Assignment 2 (each intern checks one agent-drafted typology explainer against its sources, corrects it and submits it under their own name). Interns may use AI help but submit their own work and must be able to explain every line.
- Editing and accepting ADRs. The agent drafts them as `proposed`; the named deciders make them say what they decided.
- Running repository admin scripts (branch protection, secret scanning) that need admin rights.
- Making the repository public on launch day.

---

## 2. Operating rules for the build agent

This section is the agent's constitution. M1.2 condenses it into `CLAUDE.md`, but this section wins if they ever disagree.

### 2.1 Mission guardrails (never break these)

| ID | Rule |
|---|---|
| G1 | **No real person or company is ever labelled suspicious.** Synthetic laundering scenarios run only among synthetic entities (ids starting `syn-`). Real registry entities may receive synthetic background activity only, never a scenario role. Any exception needs an ADR approved by the project lead and the data steward, and must watermark every such transaction and alert in the interface, keep them out of exports, screenshots and the public demo, and come with a revised real-data notice (7.1). |
| G2 | **The repository holds code and synthetic fixtures only.** Never commit bulk data, API responses about real people, real personal data, or any row derived from OpenSanctions. Spike outputs go to `data/cache/` (gitignored). |
| G3 | **Nothing phones home.** No telemetry, analytics or outbound calls at runtime by default. Only explicit loader and spike commands use the network. Tests never use the network (`@pytest.mark.network` tests are excluded from CI). |
| G4 | **AML facts carry citations.** Every factual AML statement in documentation cites a key from `docs/sources/bibliography.yaml`. The agent drafts typology definitions; only a typology researcher can set `status: approved`. |
| G5 | **Patterns, not accusations.** Text produced by the system or written in docs about entities describes structures and patterns. It never says an entity laundered money, committed a crime, is a launderer, criminal, fraudster or guilty. Wording rules are in 7.1. |
| G6 | **Secrets stay out.** API keys and passwords live in `.env` (gitignored) or GitHub secrets. Never print, log, commit or request them in chat. |
| G7 | **Licences decide what a loader may do.** Follow `contracts/datasets.yaml`. Never publish or commit a database that merges sources. OpenSanctions access follows `access.opensanctions` in `project.yaml`. |

### 2.2 Milestone protocol

Run these steps for every milestone or sub-milestone (M1.7a and so on).

1. **Sync and check dependencies.** `git fetch origin`. Read `docs/build/PROGRESS.md` as it is on `origin/main` (`git show origin/main:docs/build/PROGRESS.md`; for M1.1, which creates the file, check instead that the seed commit is on `origin/main`). If a dependency listed in the milestone header is not `merged`, stop and report which one; a row still marked `pr-open` counts as merged when `gh pr view <number> --json state` reports `MERGED`, and you note that in your pull request. (This works the same in a worktree, where `main` may be checked out elsewhere.)
2. **Read.** Read the whole milestone section and everything it links to. Read `docs/build/project.yaml`. If a value the milestone needs is `TODO`, stop and ask for it.
3. **Plan.** If the milestone is marked "Plan first" and the operator is in the session, present a plan (files, order, risks, how you will verify) and wait for approval. If the milestone was started with a `/goal` condition, write the plan into the pull request description draft and continue.
4. **Branch.** `git switch -c <branch named in the milestone header> origin/main`, then `uv sync --all-packages` once `pyproject.toml` exists (and `npm ci --prefix ui` once `ui/package-lock.json` exists).
5. **Build in small commits.** Conventional Commits (2.3). Add or update tests in the same commit as the code they test.
6. **Verify.** Run every command in the milestone's "Acceptance" list. Fix until all pass. Never weaken, skip or delete a test to make it pass; if a test is wrong, say so in the pull request and explain.
7. **Independent review.** Ask the `reviewer` subagent to review the branch diff against the milestone's acceptance list and section 2. For contract work also run `contract-guardian`; for documentation about AML also run `aml-claims-checker`. Fix every finding that affects correctness, the stated requirements or the guardrails. Record the rest in the pull request under "Not addressed".
8. **Record progress.** Update the milestone's row in `docs/build/PROGRESS.md` (2.8).
9. **Open the pull request** with the `/open-pr` skill (from M1.2 on) or `gh pr create`, using the template, the labels named in the milestone header, and a mention of the human owner.
10. **Wait for CI** with `gh pr checks <number> --watch` (up to 15 minutes). If CI fails, fix, push, and wait again. Before M1.6 is merged there is no CI: write "no CI yet" in the pull request and skip this step.
11. **Stop and report**: pull request URL, what changed, the acceptance commands with their results, deviations from this spec, open questions. Do not merge. Do not start another milestone.

When asked to address review comments: switch to the branch, make the changes, re-run the acceptance commands, push, reply to each comment with what changed, and stop. When the branch is behind `main`, run `git fetch origin && git merge origin/main`, resolve conflicts, re-run the acceptance commands and push normally. Never rebase a branch that is already pushed: that needs a force-push, which is blocked.

### 2.3 Branches, commits and pull requests

- **Branch names:** `p1/<milestone>-<slug>`, for example `p1/m1-4-local-stack`, `p1/m1-7a-record-contract`.
- **Commits:** Conventional Commits 1.0.0, `type(scope): summary`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `build`, `ci`, `chore`. Scopes: `repo`, `build`, `ci`, `contracts`, `ingest`, `graph`, `detect`, `copilot`, `api`, `cli`, `ui`, `docs`, `data`, `agent`.
- **Pull request title:** `type(scope): summary [M1.x]`.
- **Pull request body:** the template from M1.1 (summary, milestone, acceptance evidence, contract impact, data and licence impact, deviations, not addressed, human owner).
- **Labels:** always `agent` and `phase-1`; plus the squad label(s) and any label in the milestone header.
- **Size:** at most 400 changed lines of code, tests and configuration per pull request. Not counted: Markdown, typology YAML files, the bibliography, lock files, generated files, fixtures, examples and research notes (`.github/pr-size-exclude.txt` lists them); documentation is reviewed by reading, not by line count. Milestones whose header says `Size: exception` (verbatim content from this spec, or a scaffold) may exceed the limit; their pull requests carry the `size-exception` label, which turns the size check into a warning (locally: `make hygiene LABELS=size-exception`). Any other milestone that would exceed the limit is split into pull requests named `<milestone>-1`, `<milestone>-2` and so on, each with its own row in `PROGRESS.md`, and the first one says so.
- **Human owner:** every agent pull request names one human who is accountable for it (the squad mentor for squad work, the tech lead for repository and contract work).

### 2.4 Verification standard

"Done" means: every acceptance command passed in this session, CI is green on the pull request (before M1.6 is merged: "no CI yet", 2.2 step 10), and the pull request body shows the evidence (the commands and the meaningful lines of their output). Claims without output do not count.

### 2.5 Stop and ask

Stop, explain, and wait for a human when:

1. A value in `project.yaml` that the milestone needs is `TODO`.
2. Anything requires a secret, an account, a payment, an admin permission or a licence decision.
3. A fixture, test or document would contain data about a real person, or any OpenSanctions row.
4. A change would touch a frozen contract (after the tag `contracts-v1.0.0` exists).
5. The spec and reality disagree in a way that changes behaviour (for example a pinned version does not exist, or an API returns different fields). Small mechanical deviations can be fixed and recorded instead.
6. An AML definition, threshold or legal statement has no source in `docs/sources/bibliography.yaml` or `docs/research/`.
7. An acceptance command still fails after three focused attempts.
8. Work would require pushing to `main`, force-pushing, deleting branches or tags, changing repository visibility or settings, or merging.

### 2.6 Never

- Never merge a pull request, push to `main`, force-push in any form (including `--force-with-lease` and `+` refspecs), delete a remote branch, or change repository settings. The `guard_git.py` hook (M1.2) blocks these; never try to get around it.
- Never write learning logs, exit posts, self-assessments or assignment submissions for people.
- Never mark a typology `approved`, a contract `frozen`, or a licence decision `confirmed`.
- Never add `@neo4j-nvl/*` (proprietary), GPL-licensed Python or JavaScript dependencies (for example `unidecode`, `pyarabic`), or vendor the GPL-3.0 Neo4j MCP binary.
- Never disable a test, lint rule or type check to make CI pass without saying so in the pull request.
- Never invent an AML typology, regulation, threshold, function signature or API field. Check the sources; if absent, stop and ask.

### 2.7 When the spec seems wrong

Facts in this document were verified on 16 October 2026. Things change. When a command, version or API behaves differently:

1. Check the official source (allowed domains: `code.claude.com`, `docs.claude.com`, `neo4j.com`, `github.com`, `pypi.org`, `npmjs.com`, `gov.uk`, `company-information.service.gov.uk`, `gleif.org`, `opensanctions.org`, `followthemoney.tech`, `icij.org`, `fatf-gafi.org`).
2. If the difference is mechanical (a renamed flag, a newer patch version), adapt, and record it under "Deviations from spec" in the pull request and in the milestone's row of `PROGRESS.md`.
3. If it changes behaviour, a contract, a licence position or a guardrail, stop and ask (2.5).
4. For network failures in spikes: retry with backoff up to three times, then record the failure in the spike report and make the tests use fixtures.

### 2.8 Progress log format

`docs/build/PROGRESS.md` is created in M1.1 and updated by every milestone.

```markdown
# Build progress

| Milestone | Status | Branch | PR | Updated | Evidence | Notes and deviations |
|---|---|---|---|---|---|---|
| M1.1 | pr-open | p1/m1-1-bootstrap | #1 | 2026-10-16 | make check: pass | none |
```

Status values: `todo`, `in-progress`, `pr-open`, `changes-requested`, `merged`, `blocked`. Only humans set `merged` (or the agent sets it when it starts the next milestone and `gh pr view` shows the previous one merged). Each pull request edits only its own row; if `PROGRESS.md` conflicts after merging `main`, keep every row's newest values from both sides.

---

## 3. Verified technical baseline (16 October 2026)

Every version below was checked against PyPI, npm, the Docker official-images manifest, GitHub release tags or official documentation on 16 October 2026. The research notes in `docs/research/2026-10-16/` hold the sources, the reasoning and the alternatives.

### 3.1 Pinned versions

| Component | Pin | Notes |
|---|---|---|
| Neo4j | `neo4j:5.26.32-community` (exact tag) | 5.26 is the LTS line (supported until June 2028). Bundles APOC Core 5.26.32 and GDS 2.13.14. Cypher 5 only. |
| GDS (in Neo4j) | 2.13.x via `NEO4J_PLUGINS='["apoc", "graph-data-science"]'` | Community limits: 4 CPU cores, 3 catalogued models. All algorithms available. |
| Python | 3.14 (`requires-python = ">=3.14,<3.15"`) | 3.15 lacks wheels for duckdb and graphdatascience. |
| uv | 0.13.x, build backend `uv_build>=0.13.1,<0.14` | One workspace, one `uv.lock`. |
| neo4j (driver) | `>=6.4,<7` | `execute_read` and `execute_write`; `read_transaction` was removed in 6.0. |
| followthemoney | `>=4.11,<5` | Needs ICU headers to build PyICU. 4.x API: `ValueEntity` for records, `StatementEntity` for statements; `model.make_entity` returns an `EntityProxy` (see 3.2). |
| pydantic | `>=2.14,<3` | Contract models. |
| FastAPI | `>=0.143,<0.144` | Pin the minor (0.x). |
| typer | `>=0.27,<0.28` | The `neonradar` command line. |
| httpx | `>=0.28,<0.29` | Does not follow redirects unless `follow_redirects=True`. |
| pytest | `>=9.1,<10` | Markers: `contract`, `integration`, `network`, `e2e`. |
| testcontainers | `[neo4j]>=4.15,<5` | Import from `testcontainers.community.neo4j`. |
| ruff | `0.17.x` | Lint and format. pre-commit hook ids `ruff-check`, `ruff-format`. |
| mypy | `>=2.4,<3` | Strict mode with the pydantic plugin. |
| pre-commit | `>=4.7,<5` | Hooks also run in CI. |
| splink | `==5.0.*` (Phase 2) | Version 5 API, not 4. DuckDB backend. |
| rigour, normality | `rigour>=2.5,<3`, `normality>=3.1,<4` (Phase 2) | Name handling. `fingerprints` is unmaintained. |
| Faker | `>=40.43,<41` | MIT. Use with a denylist (7.1). Never use mimesis company names (they are real companies). |
| Node.js | 24 LTS (24.12 or later) | Node 20 is end of life. |
| vue | `^3.5.44` | 3.6 (Vapor) is still a release candidate; do not use Vapor mode. |
| vite | `^8.3.4` | Rolldown and Oxc based. |
| typescript | `~6.0.3` | Never `typescript@latest` (7.x has no JavaScript API and breaks vue-tsc and typescript-eslint). |
| vue-router, pinia | `^5.4.0`, `^4.1.0` | Match the create-vue 3.24 scaffold. |
| vitest | `^4.1.12` | Matches create-vue. |
| @playwright/test | `^1.64.1` | End-to-end smoke tests. |
| cytoscape | `^3.34.4` | MIT, zero dependencies. Layouts: `cytoscape-fcose ^2.2.0`, `cytoscape-dagre ^4.0.1`. |
| GitHub Actions | `actions/checkout@v7`, `actions/setup-node@v7`, `astral-sh/setup-uv@v10.3.0` (exact; no floating major), `github/codeql-action@v4` | Node 24 based majors. |
| Neo4j MCP (developer tool) | `uvx neo4j-mcp-server@1.6.0`, read-only, telemetry off | GPL-3.0: run as an external tool, never vendor it. Needs APOC. |
| Claude Code review action | `anthropics/claude-code-action@v1` | Optional; no secrets reach fork pull requests. |

### 3.2 Known traps for AI-written code

| Area | Trap | Do this instead |
|---|---|---|
| FollowTheMoney 4.x | `nomenklatura.entity.CompositeEntity` and old dataset classes are gone; `model.make_entity()` returns an `EntityProxy` whose `to_dict()` has no `datasets` key, so its records fail C1 rule R2 (verified with 4.11.0) | Build records with `ValueEntity(model["Company"], {"id": ..., "datasets": [slug]})`, then `.add(prop, value)`, then `{**entity.to_dict(), "nr": {...}}` |
| FollowTheMoney dates | Payment `date` values lose their timezone offset (verified: `...+00:00` becomes `...` without offset) | Write all timestamps in UTC without an offset; the graph loader converts them to Neo4j `datetime` in UTC |
| FollowTheMoney validation | `Schema.validate` does not catch a required property that is missing entirely | Check `schema.required` yourself (C1 validator) |
| FollowTheMoney edges | Not every interval schema is an edge (`Sanction` is not) | Use `schema.edge`, `schema.edge_source`, `schema.edge_target` |
| Splink 5 | v4 examples pass `db_api=` to `Linker` | `sdf = db_api.register(df)`, then `Linker(sdf, settings)` |
| graphdatascience 2.x | 1.x camelCase API is gone | Prefer `CALL gds.<algo>.stream(...)` in Cypher through the driver |
| Neo4j driver 6 | `session.read_transaction` removed | `session.execute_read(fn)` or `driver.execute_query(..., database_="neo4j")` |
| Neo4j Community | Existence, type and key constraints are Enterprise-only | Uniqueness constraints only; enforce required properties in pydantic and tests |
| Cypher | Training data mixes old syntax | Use the forward-compatible Cypher 5 subset (C2, "Cypher conventions") |
| testcontainers | `testcontainers.neo4j` is deprecated | `from testcontainers.community.neo4j import Neo4jContainer` |
| Neo4j image | `curl` is not installed | Health checks use `cypher-shell` or `wget` |
| OpenSanctions | Since 17 Aug 2026 `datasets/latest/...` answers with HTTP 307 | Follow redirects explicitly |
| TypeScript | `npm i typescript@latest` installs 7.x | Keep `~6.0.3` |
| Vite 8 | `esbuild` options are deprecated | Use defaults; no esbuild-specific config |
| Graph visualisation | `@neo4j-nvl/base` looks official | It is proprietary (Aura and Enterprise only); use Cytoscape.js |
| Faker `ar_SA` | Surname list includes real prominent families | Apply the denylist in 7.1; build company names from neutral word lists |
| Cypher batches | `CALL { } IN TRANSACTIONS` fails inside `driver.execute_query()` or `execute_write()`, which open a transaction | Send it with `session.run()` (auto-commit) |
| pytest | Test files with the same name in several `tests/` folders (for example seven `test_version.py`) fail collection with "import file mismatch" | `--import-mode=importlib` in `addopts`, and unique file names |
| pytest | `pytest -m integration` exits with code 5 when no test matches, which fails CI | Keep at least one integration test from M1.6 on (the Neo4j smoke test) |
| ruff with Python 3.14 target | Formats `except (A, B):` as `except A, B:`, which Python 3.13 and older reject | Scripts run by a system Python get an older per-file target version (M1.3) |
| pydantic-settings | Reading `.env` fails on keys the model does not define (the file also holds `NEO4J_HEAP` and others) | `env_file` plus `extra="ignore"`; real environment variables win over `.env` |
| GitHub required checks | Branch protection matches the check name, which is the job's `name:` when one is set | Give CI jobs no `name:`, so the job id (`python`, `integration`, `ui`, `hygiene`) is the check name |
| create-vue Playwright config | Starts `npm run preview` when `CI` is set, defines three browsers, runs headed outside CI and hard-codes the base URL | M1.9e rewrites `ui/playwright.config.ts` |

### 3.3 Data sources and licences (summary)

| Dataset slug | Source | Licence | Commercial use | Attribution | Phase 1 use |
|---|---|---|---|---|---|
| `gb_companies_house` | UK Companies House REST API | Register data is made available under the Companies Act 2006 and approvals under section 47 of the Copyright, Designs and Patents Act 1988, with no Companies House rules on reuse; Companies House's own material is under the Open Government Licence v3.0, which does not cover personal data, so whoever loads officers and PSCs becomes a UK GDPR controller | Yes | "Contains public sector information licensed under the Open Government Licence v3.0." plus "Source: Companies House" | Spike with one company number, output in cache only |
| `gleif_lei` | GLEIF API and Golden Copy | CC0 1.0; GLEIF's terms forbid using its logo or implying endorsement, with liquidated damages of CHF 100,000 per breach | Yes | Not required; courtesy line in 5.1 (`contracts/datasets.yaml`) | Spike with one LEI and its parents |
| `icij_offshore_leaks` | ICIJ Offshore Leaks Database (`full-oldb.LATEST.zip`) | ODbL 1.0 (database), CC BY-SA 3.0 (contents) | Yes, with citation. A publicly used derived database must be ODbL and offered in machine-readable form (clause 4.6); produced works such as screenshots and reports need a notice that the content came from the database under ODbL (clause 4.3); internal use is not public use | "Always cite the International Consortium of Investigative Journalists when using this data." plus the ODbL notices | Spike reading a slice, cache outside the repository |
| `opensanctions_default` | OpenSanctions bulk data | CC BY-NC 4.0; "Any use inside a for-profit business requires a data license." | Licence required | No official text; proposed wording in 5.1 (`contracts/datasets.yaml`), following CC BY-NC 4.0 section 3(a)(1) | Only if `access.opensanctions` is `evaluation`, `licensed` or `exempt` (1.2) |
| `nr_synthetic` | NeonRadar generator | Apache-2.0 (our own output) | Yes | None | Fixtures and the walking skeleton |

### 3.4 Where the evidence is

- `docs/research/2026-10-16/stack.md`: versions, tooling, CI, memory sizing.
- `docs/research/2026-10-16/neo4j.md`: Neo4j editions, Docker, GDS, constraints, Cypher 25 versus 5, bulk loading.
- `docs/research/2026-10-16/sources-ch-gleif.md`: Companies House and GLEIF endpoints, fields, enumerations, licences, spikes.
- `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md`: OpenSanctions licensing and formats, FollowTheMoney 4.x schema tables, ICIJ files and licence.
- `docs/research/2026-10-16/synthetic-docs-mcp.md`: synthetic generator design, Faker findings, docs tooling, Neo4j MCP, Claude Code GitHub Action.
- `docs/research/2026-10-16/aml-domain.md`: primary AML sources, typology definitions, terminology, disclaimers, cases.

---

## 4. Architecture and repository layout

### 4.1 Components and data flow

```text
  public sources (CH, GLEIF, ICIJ, sanctions)        synthetic generator (ingest/synth)
                 |                                              |
                 v                                              v
          ingest/ loaders  ------>  C1 records: *.ftm.jsonl + *.manifest.json  <------+
                                              |
                                              v
                         graph/ resolver (Phase 2) -> graph/ loader -> Neo4j (C2 schema)
                                                                         |        ^
                                                       detect/ runs -----+        | :Alert nodes
                                                       (writes C4 alerts) --------+
                                                                         |
                                                                         v
                                          copilot/ (Phase 4) -> api/ FastAPI (C3)
                                                                         |
                                                                         v
                                                                 ui/ Vue explorer
```

The arrows are the contracts. A squad can build its box against the contract and a fixture, without waiting for the box upstream.

### 4.2 Repository tree at the end of Phase 1

```text
neonradar/
  CLAUDE.md                     shared context for AI sessions (M1.2)
  README.md  LICENSE  NOTICE  SECURITY.md  CODE_OF_CONDUCT.md
  CONTRIBUTING.md  CONTRIBUTORS.md  DATA_SOURCES.md  CHANGELOG.md
  Makefile                      developer commands (M1.3)
  pyproject.toml  uv.lock  .python-version
  compose.yaml  .env.example    local stack (M1.4, extended in M1.9)
  .pre-commit-config.yaml  .editorconfig  .gitattributes  .gitignore  .worktreeinclude
  .mcp.json                     read-only Neo4j MCP for Claude Code (M1.2)
  .claude/
    settings.json  rules/  hooks/  skills/  agents/
  .github/
    workflows/  ISSUE_TEMPLATE/  pull_request_template.md  CODEOWNERS
    dependabot.yml  labels.yml  pr-size-exclude.txt
  .devcontainer/                devcontainer.json  Dockerfile  compose.dev.yaml (M1.5)
  contracts/                    C1 to C4: pydantic models, JSON Schemas, OpenAPI snapshot,
                                datasets.yaml, golden examples, contract docs (FROZEN at Gate 1)
  ingest/                       loaders, spikes, synthetic generator (squad: ingest)
  graph/                        schema migrations (graph/schema: FROZEN), loader, client (squad: graph)
  detect/                       typology catalog, detectors, alert writer (squad: detect)
  copilot/                      placeholder package until Phase 4 (squad: copilot)
  api/                          FastAPI app (squads: copilot for code, ui as consumer)
  cli/                          the `neonradar` command (squad: docs)
  ui/                           Vue 3 app (squad: ui)
  data/
    fixtures/                   synthetic fixtures only (committed)
    cache/  import/  runs/      gitignored working directories
  docs/
    build/                      PHASE-1.md, project.yaml, PROGRESS.md, reports/
    research/2026-10-16/        verified research notes
    plan/                       project plan (export)
    decisions/                  architecture decision records
    sources/bibliography.yaml   citation keys
    typologies/                 plain-language explainers
    learning/                   learning logs (humans), templates, reading list, cases
    team/                       assignments, roles, first-queries.md
    data/                       spike reports, licence notes
    architecture/               overview
  scripts/                      repository checks and admin helpers
```

Each Python directory (`contracts`, `ingest`, `graph`, `detect`, `copilot`, `api`, `cli`) is a uv workspace member with the layout `<dir>/pyproject.toml`, `<dir>/src/neonradar_<dir>/`, `<dir>/tests/`, and a short `<dir>/CLAUDE.md` with module notes.

### 4.3 Ownership map

| Path | Owner (CODEOWNERS) | Required reviewer for |
|---|---|---|
| `contracts/`, `graph/schema/` | tech lead and `nr-maintainers` | every change |
| `ingest/`, `data/fixtures/` | `nr-ingest` | loaders, generator, fixtures |
| `graph/` | `nr-graph` | loader, migrations, mapping |
| `detect/` | `nr-detect` | detectors, typology catalog |
| `copilot/`, `api/` | `nr-copilot` | API and copilot |
| `ui/` | `nr-ui` | frontend |
| `cli/`, `docs/`, root files, `.github/`, `.devcontainer/`, `Makefile` | `nr-docs` | developer experience and docs |
| `.claude/`, `CLAUDE.md`, `docs/build/` | tech lead | agent kit and build spec |
| `docs/build/PROGRESS.md` | no code owner (a CODEOWNERS line with the path and no owner) | nobody; every pull request updates it, and it must not pull the tech lead into every review |
| `DATA_SOURCES.md`, `docs/data/licences/` | data steward | licence statements |
| `contracts/datasets.yaml` | tech lead and data steward | licence fields of the frozen record contract |
| `docs/typologies/`, `detect/typologies/` | typology researchers | AML definitions |

CODEOWNERS applies the last matching line, so `scripts/generate_codeowners.py` writes the rows in this table's order, adjusted so that every specific path comes after the broader one that contains it (for example `docs/build/PROGRESS.md` after `docs/build/`, and `docs/typologies/` after `docs/`).

### 4.4 Naming conventions

| Thing | Convention | Example |
|---|---|---|
| Entity id (records and graph) | `<prefix>-<rest>`; prefix from `contracts/datasets.yaml`; rest uses `[A-Za-z0-9._:-]`; at most 120 characters | `gbch-co-01800000`, `gleif-549300OWFMSO9NYV4H90`, `icij-10000001`, `syn-co-0001` |
| Reserved prefixes | `syn` synthetic, `nr` canonical resolved entities (Phase 2) | |
| Edge entity ids | `<prefix>-<schema in lowercase>-<sha1 of parts, first 20 hex>` | `syn-ownership-3f2a9c...` |
| Dataset slugs | lowercase snake case | `gb_companies_house` |
| Record files | `<dataset>-<yyyymmdd>-<part>.ftm.jsonl` with a sibling `.manifest.json` | `nr_synthetic-20261023-demo-mini.ftm.jsonl` |
| Graph labels | PascalCase singular | `Company`, `Account` |
| Relationship types | UPPER_SNAKE_CASE verbs | `OWNS`, `DIRECTOR_OF`, `PAID` |
| Graph properties | snake_case (records keep FtM camelCase) | `registration_number` |
| Typology slugs | lowercase snake case | `circular_flow` |
| Python packages | `neonradar-<dir>`, import `neonradar_<dir>` | `neonradar_graph` |
| CLI | `neonradar <group> <command>` | `neonradar graph load` |
| ADR files | `docs/decisions/NNNN-kebab-title.md` | `0002-neo4j-5-26-lts.md` |

---

## 5. The four contracts (frozen at Gate 1)

The contracts are the agreements between squads. Everything else can move; these cannot, after Gate 1. They live in `contracts/` (a Python package with docs, JSON Schemas and examples) and `graph/schema/` (Cypher migrations).

### 5.0 Contract rules

- **Versions.** Each contract has a semantic version: C1 record `1.0.0`, C2 graph schema `1.0.0`, C3 API `1.0.0`, C4 alert `1.0.0`. `neonradar_contracts.versions` exports them. At Gate 1 the tech lead tags the repository `contracts-v1.0.0`.
- **Before the freeze** (until the tag exists): changes go through normal pull requests with the tech lead as required reviewer.
- **After the freeze**: a change needs a `contract-change` issue (template from M1.1) approved by the tech lead, then a pull request labelled `contract-change` that bumps the version, updates `contracts/CHANGELOG.md`, regenerates JSON Schemas and the OpenAPI snapshot, and, for C2, adds a new migration file (never edit an applied migration).
  - Patch (`1.0.x`): wording, examples, documentation; no shape change.
  - Minor (`1.x.0`): additive and optional (a new optional field, endpoint, dataset entry, relationship type).
  - Major (`2.0.0`): renaming, removing or changing meaning. Not allowed before 20 November without tech lead sign-off and a migration note.
- **Enforcement.** The `guard-contracts` hook (M1.2) blocks agent edits to `contracts/**` and `graph/schema/**` once the tag exists. CI (M1.6) fails a pull request that touches those paths without the `contract-change` label. `make contracts-check` fails on any drift between models, JSON Schemas and the OpenAPI snapshot.

### 5.1 C1: NeonRadar Record v1.0.0

**What it is.** The format every loader and the synthetic generator emit, and the only input the graph loader accepts. It is FollowTheMoney (FtM), so the files work with FtM tooling, plus a small, closed extension object `nr` for the few facts FtM cannot express.

**File format.**

- UTF-8, JSON Lines, one entity per line, file extension `.ftm.jsonl`.
- Each file has a sibling manifest `<same name>.manifest.json`.
- Each line is the output of `followthemoney` 4.11+ `ValueEntity.to_dict()`: keys `id` (required), `schema` (required), `properties` (required, property name to list of strings), `datasets` (required), and optionally `referents`, `caption`, `first_seen`, `last_seen`, `last_change`, `nr`. FtM keeps the unknown top-level key `nr` through `ValueEntity.from_dict()` and `to_dict()` (verified with 4.11.0).

**Allowed schemata in v1.** `Person`, `Company`, `Organization`, `LegalEntity`, `PublicBody`, `Address`, `BankAccount`, `Position`, `Ownership`, `Control`, `Directorship`, `Representation`, `Family`, `Associate`, `Membership`, `Employment`, `UnknownLink`, `Succession`, `Occupancy`, `Payment`, `Sanction`. Other schemata are rejected by the validator and counted in the manifest under `skipped`.

**Rules.** The validator `neonradar_contracts.records.validate_record()` enforces all of them; each rule has a failing golden example in the tests.

| Rule | Statement |
|---|---|
| R1 | `id` matches `^(?P<prefix>[a-z][a-z0-9]{1,15})-(?P<rest>[A-Za-z0-9._:-]{1,100})$`, and `prefix` equals the `id_prefix` of the record's dataset in `contracts/datasets.yaml`. |
| R2 | `datasets` contains exactly one slug, and that slug exists in `contracts/datasets.yaml`. |
| R3 | `followthemoney.model[schema].validate(record)` passes, and every property in `schema.required` is present and non-empty (FtM's own validator does not check missing required properties). |
| R4 | Entity-typed properties hold ids (strings). References may point to records in other files of the same load. The graph loader reports dangling references; in strict mode (fixtures, CI) any dangling reference fails the load. |
| R5 | `Payment.date` is a full UTC timestamp `YYYY-MM-DDTHH:MM:SS` without an offset. All other dates are ISO 8601 and may be partial (`1979`, `1979-08`). |
| R6 | Synthetic consistency: dataset `nr_synthetic` if and only if id prefix `syn` if and only if `nr.synthetic` is `true`. Synthetic records must carry `nr`. Non-synthetic records must not set `nr.synthetic`. |
| R7 | `Payment` records (synthetic only in v1) have `payer`, `beneficiary`, `payerAccount`, `beneficiaryAccount`, `amount` (decimal string, at most two decimals, greater than zero), `currency` (ISO 4217, upper case), `date` (R5), and `nr.channel`. |
| R8 | Every `BankAccount` is the `asset` of at least one `Ownership` whose `owner` is a `LegalEntity` in the same load (this becomes `HOLDS_ACCOUNT`). Synthetic account numbers use the form `NRSYN` plus 10 digits, and synthetic records never set `iban` or `bic`, so no synthetic account can collide with a real one. |
| R9 | No ground-truth labels anywhere in records, including `nr`: no typology, scenario, role-in-scenario or "illicit" field. Labels live in separate label files (Phase 3). |
| R10 | Strings are Unicode NFC. Names keep their original script. Machine transliterations are never written into records (Phase 2 computes matching keys at load time). |

**The `nr` extension object.** Closed set of keys. Unknown keys fail validation.

| Key | Type | Used on | Meaning |
|---|---|---|---|
| `v` | string, required when `nr` is present | all | Record contract version, `"1.0"` |
| `synthetic` | boolean | all | `true` for synthetic records (R6) |
| `synthetic_kind` | `"registry"` or `"activity"` | synthetic records | Synthetic companies and people versus synthetic accounts and payments |
| `channel` | `"wire"`, `"card"`, `"cash_deposit"`, `"cash_withdrawal"`, `"internal"` | `Payment` | How the money moved. Cash deposits are payments from the bank branch's `cash_ledger` account. |
| `account_kind` | `"customer"` or `"cash_ledger"` | `BankAccount` | `cash_ledger` accounts belong to a synthetic bank branch and model cash in and out |
| `address_roles` | object, Address id to `"registered"`, `"service"`, `"residential"`, `"business"`, `"unknown"` | any `LegalEntity` with `addressEntity` | Role of each linked address (FtM has no role on `addressEntity`) |
| `source_ref` | string | any | The source's native identifier (Companies House `officer_id`, ICIJ `node_id`) |
| `natures_of_control` | list of strings | `Ownership`, `Control` | Raw Companies House PSC values |
| `share_pct_min`, `share_pct_max` | numbers in [0, 100] | `Ownership` | Parsed share band, for example 25 and 50 for "more than 25% but not more than 50%" |
| `is_nominee` | boolean | `Directorship` | True for nominee roles (for example Companies House `nominee-director`) |
| `consolidation` | `"direct"` or `"ultimate"` | `Ownership` | GLEIF accounting consolidation parent; becomes `CONSOLIDATES`, not `OWNS` |

**Examples** (synthetic; also committed as `contracts/examples/c1/demo.ftm.jsonl`):

```json
{"id": "syn-co-0001", "schema": "Company", "datasets": ["nr_synthetic"], "properties": {"name": ["Falcon Ridge Trading Ltd"], "jurisdiction": ["gb"], "registrationNumber": ["SYN00001"], "incorporationDate": ["2019-04-02"], "addressEntity": ["syn-addr-0001"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "registry", "address_roles": {"syn-addr-0001": "registered"}}}
{"id": "syn-addr-0001", "schema": "Address", "datasets": ["nr_synthetic"], "properties": {"full": ["Unit 4, 12 Example Street, London, EX1 2MP"], "city": ["London"], "postalCode": ["EX1 2MP"], "country": ["gb"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "registry"}}
{"id": "syn-p-0001", "schema": "Person", "datasets": ["nr_synthetic"], "properties": {"name": ["Omar Haddad", "عمر حداد", "Омар Хаддад"], "birthDate": ["1979-08"], "nationality": ["jo"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "registry"}}
{"id": "syn-ownership-0001", "schema": "Ownership", "datasets": ["nr_synthetic"], "properties": {"owner": ["syn-p-0001"], "asset": ["syn-co-0001"], "percentage": ["25-50"], "role": ["ownership-of-shares-25-to-50-percent"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "registry", "natures_of_control": ["ownership-of-shares-25-to-50-percent"], "share_pct_min": 25.0, "share_pct_max": 50.0}}
{"id": "syn-acct-0001", "schema": "BankAccount", "datasets": ["nr_synthetic"], "properties": {"accountNumber": ["NRSYN0000000001"], "bankName": ["Synthetic Bank One"], "currency": ["EUR"], "openingDate": ["2020-01-15"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "activity", "account_kind": "customer"}}
{"id": "syn-ownership-0002", "schema": "Ownership", "datasets": ["nr_synthetic"], "properties": {"owner": ["syn-co-0001"], "asset": ["syn-acct-0001"], "role": ["account holder"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "activity"}}
{"id": "syn-payment-000001", "schema": "Payment", "datasets": ["nr_synthetic"], "properties": {"payer": ["syn-co-0001"], "beneficiary": ["syn-co-0002"], "payerAccount": ["syn-acct-0001"], "beneficiaryAccount": ["syn-acct-0002"], "amount": ["9500.00"], "currency": ["EUR"], "date": ["2026-03-14T10:22:05"]}, "nr": {"v": "1.0", "synthetic": true, "synthetic_kind": "activity", "channel": "wire"}}
```

(The last line references `syn-co-0002` and `syn-acct-0002`, which the full example file defines.)

**Manifest** (`*.manifest.json`, validated by `neonradar_contracts.records.Manifest`):

```json
{
  "manifest_version": "1.0",
  "record_contract": "1.0.0",
  "dataset": "nr_synthetic",
  "files": [{"path": "nr_synthetic-20261023-demo-mini.ftm.jsonl", "sha256": "<hex>", "records": 412}],
  "created_at": "2026-10-23T09:00:00Z",
  "producer": {"name": "neonradar_ingest.synth", "version": "0.1.0", "git_sha": "<sha>"},
  "source": {"urls": [], "retrieved_at": null, "source_version": null},
  "licence": {"id": "Apache-2.0", "attribution": null},
  "counts": {"by_schema": {"Company": 24, "Person": 30, "Payment": 260}, "skipped": {}},
  "dependencies": {"followthemoney": "4.11.0"},
  "synthetic": true,
  "seed": 20261023,
  "notes": []
}
```

**Dataset registry** (`contracts/datasets.yaml`). Adding a dataset after the freeze is a minor change (5.0).

```yaml
version: 1
reserved_prefixes: [nr]          # canonical resolved entities, Phase 2
datasets:
  - slug: gb_companies_house
    id_prefix: gbch
    title: UK Companies House public register
    publisher: Companies House
    url: https://developer.company-information.service.gov.uk/
    licence: { id: OGL-UK-3.0, url: "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" }
    attribution: "Contains public sector information licensed under the Open Government Licence v3.0. Source: Companies House."
    commercial_use: allowed
    redistribution: loaders-only     # project policy: the repository ships loaders, never data
    personal_data: true              # officers and PSCs; the user who loads them is a UK GDPR controller
    synthetic: false
    access: api-key
    status: spike
    notes: >-
      Register data is made available under the Companies Act 2006 and section 47 approvals of the
      Copyright, Designs and Patents Act 1988, with no Companies House rules on reuse; Companies
      House's own material is under OGL v3.0, which does not cover personal data.
  - slug: gleif_lei
    id_prefix: gleif
    title: GLEIF Global LEI Index
    publisher: Global Legal Entity Identifier Foundation
    url: https://www.gleif.org/
    licence: { id: CC0-1.0, url: "https://creativecommons.org/publicdomain/zero/1.0/" }
    attribution: "LEI data from the GLEIF Global LEI Index, available under CC0 1.0. NeonRadar is not affiliated with or endorsed by GLEIF."
    commercial_use: allowed
    redistribution: loaders-only
    personal_data: false
    synthetic: false
    access: none
    status: spike
    notes: >-
      No attribution required. GLEIF's terms forbid using its logo or implying endorsement, with
      liquidated damages of CHF 100,000 per breach.
  - slug: icij_offshore_leaks
    id_prefix: icij
    title: ICIJ Offshore Leaks Database
    publisher: International Consortium of Investigative Journalists
    url: https://offshoreleaks.icij.org/
    licence: { id: ODbL-1.0, url: "https://opendatacommons.org/licenses/odbl/1-0/", contents: CC-BY-SA-3.0 }
    attribution: "Always cite the International Consortium of Investigative Journalists when using this data."
    commercial_use: allowed
    redistribution: loaders-only     # a published derived database would have to be ODbL
    personal_data: true
    synthetic: false
    access: none
    status: spike
    notes: >-
      Produced works (screenshots, reports) carry a notice that the content came from the ICIJ
      Offshore Leaks Database under ODbL 1.0 (clause 4.3); a publicly used derived database must be
      ODbL and offered in machine-readable form (clause 4.6). Show ICIJ's disclaimer with the data.
      Never publish a database that merges ICIJ data with OpenSanctions data.
  - slug: opensanctions_default
    id_prefix: os
    title: OpenSanctions (default collection)
    publisher: OpenSanctions Datenbanken GmbH
    url: https://www.opensanctions.org/
    licence: { id: CC-BY-NC-4.0, url: "https://creativecommons.org/licenses/by-nc/4.0/" }
    attribution: "Contains data from OpenSanctions (https://www.opensanctions.org), (c) OpenSanctions Datenbanken GmbH, licensed under CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/), provided without warranty. Converted and filtered by NeonRadar."
    commercial_use: licence-required # "Any use inside a for-profit business requires a data license."
    redistribution: never
    personal_data: true              # includes crime-related topics: special care under data protection law
    synthetic: false
    access: licence-required
    status: blocked                  # becomes spike only when project.yaml access.opensanctions allows it
    notes: >-
      Free access exists only for public-interest journalists, advocacy groups and nonprofits working
      on democratic governance or exposing corruption and financial crime, affiliated academics, and
      public institutions of Ukraine, Georgia and Moldova. Every commercial user needs their own licence.
  - slug: nr_synthetic
    id_prefix: syn
    title: NeonRadar synthetic data
    publisher: NeonRadar
    url: https://neonradar.com/
    licence: { id: Apache-2.0, url: "https://www.apache.org/licenses/LICENSE-2.0" }
    attribution: null
    commercial_use: allowed
    redistribution: allowed
    personal_data: false
    synthetic: true
    access: none
    status: active
```

The OpenSanctions attribution line is NeonRadar's proposal (OpenSanctions publishes no official wording; the line follows CC BY-NC 4.0 section 3(a)(1)). The data steward approves every licence field in this file before the freeze (GC-17 in section 8).

### 5.2 C2: Graph schema v1.0.0

**Node labels.** Every node built from an FtM thing gets `:Entity` plus labels that mirror the FtM hierarchy, so `MATCH (x:LegalEntity)` finds people and organisations alike.

| FtM schema | Labels | Schema-specific properties (snake_case) |
|---|---|---|
| `Person` | `:Entity:LegalEntity:Person` | `birth_date`, `nationalities`, `gender` |
| `Company` | `:Entity:LegalEntity:Organization:Company` | `registration_number`, `jurisdiction`, `lei`, `status`, `legal_form`, `sector`, `incorporation_date`, `dissolution_date` |
| `Organization` | `:Entity:LegalEntity:Organization` | as Company where present |
| `PublicBody` | `:Entity:LegalEntity:Organization:PublicBody` | as Organization |
| `LegalEntity` | `:Entity:LegalEntity` | `registration_number`, `jurisdiction`, `lei`, `status`, `sector` |
| `Address` | `:Entity:Address` | `full`, `street`, `city`, `postal_code`, `region`, `country`, `address_key` (normalised key, Phase 2) |
| `BankAccount` | `:Entity:Account` | `account_number`, `bank_name`, `currency`, `account_type`, `account_kind`, `opening_date`, `closing_date` |
| `Position` | `:Entity:Position` | `country` |
| `Sanction` | `:Sanction` | `authority`, `program`, `program_id`, `listing_date`, `start_date`, `end_date`, `reason`, `country` |

Support nodes (not `:Entity`): `:SourceRecord` (entity resolution evidence, Phase 2), `:Alert` (C4), `:DetectionRun`, `:SchemaMigration`.

| Support label | Properties |
|---|---|
| `:Alert` | `alert_id` (unique), `typology`, `typology_version`, `priority`, `pattern_strength` (FLOAT), `headline`, `created_at` (UTC ISO string), `run_id`, `wording_class`, `involves_real_entities` (BOOLEAN), `synthetic_activity` (BOOLEAN), `payload` (STRING: the complete C4 alert as JSON) |
| `:DetectionRun` | `run_id` (unique), `started_at`, `finished_at` (UTC ISO strings), `typologies` (LIST<STRING>), `detectors` (STRING: JSON list of name and version), `alert_count` (INTEGER), `status` (`ok` or `failed`) |
| `:SchemaMigration` | `id`, `checksum`, `applied_at` |
| `:SourceRecord` | defined in Phase 2 |

The API reads alerts only from Neo4j: it filters on the scalar properties and parses `payload` for `AlertDetail`. The files in `data/runs/<run_id>/` are the run's audit copy, not an API source.

**Flag labels** on `:Entity` nodes, set by the loader: `:Synthetic` (dataset is synthetic), `:Sanctioned` (`topics` contains `sanction`), `:PEP` (`role.pep`), `:RCA` (`role.rca`). Flags come only from source data, never from detections.

**Common properties on every `:Entity` and `:Sanction` node.**

| Property | Type | Rule |
|---|---|---|
| `id` | STRING | Unique. The record id in Phase 1; the canonical id after entity resolution (Phase 2) |
| `schema` | STRING | FtM schema name |
| `caption` | STRING | FtM caption, else the first name |
| `names` | LIST<STRING> | Every value of `name`, `alias`, `previousName`, `abbreviation` (and `full` for addresses), in original scripts |
| `names_text` | STRING | `names` joined with `" \| "`, for the full-text index |
| `countries` | LIST<STRING> | Lower-case ISO codes from every country-typed property |
| `topics` | LIST<STRING> | FtM topics |
| `datasets` | LIST<STRING> | Dataset slugs |
| `referents` | LIST<STRING> | Record ids merged into this node (Phase 1: `[id]`) |
| `synthetic` | BOOLEAN | Equals the dataset's `synthetic` flag; mirrors the `:Synthetic` label |
| `first_seen`, `last_seen` | STRING | ISO datetimes when the source provides them |
| `source_url` | STRING | Optional |

Dates on entities and relationships are ISO 8601 strings and may be partial. Only transaction timestamps (`PAID.ts`) are Neo4j `DATETIME` values in UTC.

**Relationships.**

| Type | From | To | Built from | Specific properties |
|---|---|---|---|---|
| `OWNS` | `LegalEntity` | `LegalEntity` | `Ownership` whose asset is not a `BankAccount` and without `nr.consolidation` | `share_pct_min`, `share_pct_max` (FLOAT), `percentage_raw`, `ownership_type`, `role`, `natures_of_control`, `start_date`, `end_date`, `status` |
| `CONTROLS` | `LegalEntity` | `LegalEntity` | `Control` | `control_type`, `legal_basis`, `natures_of_control`, `start_date`, `end_date` |
| `CONSOLIDATES` | `Organization` (parent) | `Organization` (child) | `Ownership` with `nr.consolidation` | `level` (`direct` or `ultimate`), `start_date`, `end_date`, `status` |
| `DIRECTOR_OF` | `LegalEntity` | `Organization` | `Directorship` | `role`, `is_nominee`, `start_date`, `end_date` |
| `HOLDS_ACCOUNT` | `LegalEntity` | `Account` | `Ownership` whose asset is a `BankAccount` | `role`, `start_date`, `end_date` |
| `PAID` | `Account` | `Account` | `Payment` (payerAccount to beneficiaryAccount) | `amount` (FLOAT, major units), `currency`, `ts` (DATETIME, UTC), `channel`, `purpose` |
| `HAS_ADDRESS` | `LegalEntity` | `Address` | `addressEntity` property | `role` from `nr.address_roles`, default `unknown` |
| `REPRESENTS` | `LegalEntity` | `LegalEntity` | `Representation` (agent to client) | `role` (ICIJ intermediaries use `intermediary`) |
| `FAMILY_OF` | `Person` | `Person` | `Family` (person to relative) | `relationship` |
| `ASSOCIATE_OF` | `Person` | `Person` | `Associate` | `relationship` |
| `MEMBER_OF` | `LegalEntity` | `Organization` | `Membership` | `role`, `start_date`, `end_date` |
| `EMPLOYED_BY` | `Person` | `Organization` | `Employment` (employee to employer) | `role`, `start_date`, `end_date` |
| `LINKED_TO` | `Entity` | `Entity` | `UnknownLink` | `role` |
| `SUCCEEDED_BY` | `LegalEntity` | `LegalEntity` | `Succession` (predecessor to successor) | `date` |
| `HOLDS_POSITION` | `Person` | `Position` | `Occupancy` (holder to post) | `status`, `start_date`, `end_date` |
| `SUBJECT_OF` | `Entity` | `Sanction` | `Sanction.entity` | none |
| `RESOLVED_TO` | `SourceRecord` | `Entity` | Entity resolution (Phase 2) | `match_probability`, `method`, `resolver_version`, `decided_at` |
| `FLAGS` | `Alert` | `Entity` | Alert subjects | `role` |
| `PRODUCED` | `DetectionRun` | `Alert` | Detection runs | none |

Common relationship properties (all types except `RESOLVED_TO`, `FLAGS`, `PRODUCED`): `id` (STRING, unique per type: the FtM interval entity id, or `<entity id>|addr|<address id>` for `HAS_ADDRESS`, or `<entity id>|sanction|<sanction id>` for `SUBJECT_OF`), `datasets`, `synthetic`, `source_url` (optional).

**Migration `graph/schema/migrations/0001_init.cypher`** (Neo4j 5.26 Community, Cypher 5; one statement per line ending with `;`):

```cypher
// 0001_init: NeonRadar graph schema v1.0.0
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT sanction_id IF NOT EXISTS FOR (n:Sanction) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT source_record_id IF NOT EXISTS FOR (n:SourceRecord) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT alert_id IF NOT EXISTS FOR (n:Alert) REQUIRE n.alert_id IS UNIQUE;
CREATE CONSTRAINT detection_run_id IF NOT EXISTS FOR (n:DetectionRun) REQUIRE n.run_id IS UNIQUE;
CREATE CONSTRAINT schema_migration_id IF NOT EXISTS FOR (n:SchemaMigration) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT owns_id IF NOT EXISTS FOR ()-[r:OWNS]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT controls_id IF NOT EXISTS FOR ()-[r:CONTROLS]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT consolidates_id IF NOT EXISTS FOR ()-[r:CONSOLIDATES]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT director_of_id IF NOT EXISTS FOR ()-[r:DIRECTOR_OF]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT holds_account_id IF NOT EXISTS FOR ()-[r:HOLDS_ACCOUNT]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT paid_id IF NOT EXISTS FOR ()-[r:PAID]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT has_address_id IF NOT EXISTS FOR ()-[r:HAS_ADDRESS]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT represents_id IF NOT EXISTS FOR ()-[r:REPRESENTS]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT family_of_id IF NOT EXISTS FOR ()-[r:FAMILY_OF]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT associate_of_id IF NOT EXISTS FOR ()-[r:ASSOCIATE_OF]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT member_of_id IF NOT EXISTS FOR ()-[r:MEMBER_OF]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT employed_by_id IF NOT EXISTS FOR ()-[r:EMPLOYED_BY]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT linked_to_id IF NOT EXISTS FOR ()-[r:LINKED_TO]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT succeeded_by_id IF NOT EXISTS FOR ()-[r:SUCCEEDED_BY]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT holds_position_id IF NOT EXISTS FOR ()-[r:HOLDS_POSITION]-() REQUIRE r.id IS UNIQUE;
CREATE CONSTRAINT subject_of_id IF NOT EXISTS FOR ()-[r:SUBJECT_OF]-() REQUIRE r.id IS UNIQUE;
CREATE INDEX company_registration_number IF NOT EXISTS FOR (n:Company) ON (n.registration_number);
CREATE INDEX legal_entity_lei IF NOT EXISTS FOR (n:LegalEntity) ON (n.lei);
CREATE INDEX address_key IF NOT EXISTS FOR (n:Address) ON (n.address_key);
CREATE INDEX account_number IF NOT EXISTS FOR (n:Account) ON (n.account_number);
CREATE INDEX paid_ts IF NOT EXISTS FOR ()-[r:PAID]-() ON (r.ts);
CREATE INDEX alert_typology IF NOT EXISTS FOR (n:Alert) ON (n.typology);
CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (n:LegalEntity|Address) ON EACH [n.names_text] OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard-no-stop-words' } };
```

A uniqueness constraint creates its own backing index, so no separate index on `id` is needed. Community Edition has no existence, type or key constraints; the loader and the invariant tests enforce required properties instead.

**Migration runner** (`neonradar graph migrate`): applies `graph/schema/migrations/NNNN_*.cypher` in order, one statement per auto-commit transaction, then records `(:SchemaMigration {id, checksum, applied_at})`. Re-running is a no-op. If an applied migration's checksum changed, it stops with an error ("add a new migration; never edit an applied one").

**Loader rules** (`neonradar graph load`):

1. Validate every record (C1) first; nothing is written if validation fails in strict mode.
2. Load nodes before relationships, in batches of 5,000 rows with `UNWIND $rows AS row`, through `driver.execute_query(..., database_="neo4j")`.
3. Labels come only from the fixed mapping table above, written into the query text per schema; data values are never interpolated into Cypher. Flag labels use `FOREACH (_ IN CASE WHEN row.flag THEN [1] ELSE [] END | SET n:Flag)`.
4. Nodes: `MERGE (n:Entity {id: row.id})`, then set labels, then `SET n += row.props`.
5. Relationships: `MATCH` both endpoints by `id`, `MERGE` the relationship on its `id`, `SET r += row.props`. Count rows whose endpoints were not found and report them as dangling.
6. `PAID.ts`: the loader passes `<record date>Z` and the query sets `r.ts = datetime(row.ts)`.
7. Loading the same files twice leaves the graph unchanged (tested).

**Graph invariants** (integration tests, run against the demo-mini load):

| Invariant | Check |
|---|---|
| I1 | Every `:Entity` has non-null `id`, `schema`, `caption`, `datasets`, `synthetic`. |
| I2 | A node has the `:Synthetic` label if and only if `synthetic = true`. |
| I3 | Every `PAID` goes from an `:Account` to an `:Account`, has `amount > 0`, a three-letter `currency`, and a `DATETIME` `ts`. |
| I4 | Every `:Account` has at least one incoming `HOLDS_ACCOUNT`. |
| I5 | Every `OWNS` with share bounds has `0 <= share_pct_min <= share_pct_max <= 100`. |
| I6 | No `:Alert` with `wording_class = 'synthetic_scenario'` flags a node where `synthetic = false`. |

**Cypher conventions** (Neo4j 5.26, Cypher 5, written so that it still runs on Cypher 25 later):

- Always pass parameters; never build Cypher from data.
- Use the variable-scope subquery form `CALL (x) { ... }`, not an importing `WITH` inside `CALL`.
- Use `elementId()`, never `id()`.
- Variable-length traversals use quantified relationships or quantified path patterns, for example `(a:Account)-[t:PAID]->{2,6}(a)` or `((x)-[:OWNS]->(y)){1,6}`, not `[*1..6]`. Bound every traversal (at most 8 hops) and every result (`LIMIT`).
- Shortest paths use `SHORTEST 1` or `ANY SHORTEST` path selectors.
- Large writes use `CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS` in an auto-commit query, never `apoc.periodic.iterate`.
- No `SET n = r` with a node or relationship on the right side, no `indexProvider` options, no cross-entity property references inside one `MERGE`.
- GDS procedures run with `concurrency: 4` (the Community limit).
- Detection queries read only labels, relationship types and properties defined in C2.

### 5.3 C3: API v1.0.0

**Basics.** FastAPI, OpenAPI 3.1, base path `/api/v1`, JSON with snake_case fields, bound to `127.0.0.1` only. CORS allows `http://localhost:5173` in development. Errors use RFC 9457 problem details (`application/problem+json`: `type`, `title`, `status`, `detail`, `instance`). The OpenAPI document is committed at `contracts/openapi/v1.json`; a contract test fails when the running app's document differs. The UI generates TypeScript types from it (`openapi-typescript`) into `ui/src/api/schema.d.ts`.

**Endpoints.**

| Method and path | Response model | Phase 1 status | Parameters and limits |
|---|---|---|---|
| `GET /api/v1/health` | `HealthResponse` | implemented | none |
| `GET /api/v1/meta` | `MetaResponse` | implemented | none |
| `GET /api/v1/search` | `SearchResponse` | implemented | `q` (2 to 200 characters), `labels` (repeatable; `Person`, `Company`, `Organization`, `LegalEntity`, `Address`, `Account`), `limit` 1 to 50, default 20 |
| `GET /api/v1/entities/{entity_id}` | `EntityDetail` | implemented | accepts a canonical id or any id in `referents` |
| `GET /api/v1/entities/{entity_id}/network` | `Subgraph` | implemented | `depth` 1 to 3 (default 1), `rel_types` (repeatable), `max_nodes` 1 to 500 (default 200) |
| `GET /api/v1/entities/{entity_id}/ownership` | `OwnershipResponse` | 501 until Phase 2 | `direction` `up` or `down`, `max_hops` 1 to 8 (default 6), `min_share` 0 to 100 |
| `GET /api/v1/paths` | `PathsResponse` | 501 until Phase 2 | `from_id`, `to_id`, `max_hops` 1 to 6 (default 4), `rel_types` |
| `GET /api/v1/alerts` | `AlertPage` | implemented | `typology`, `priority`, `entity_id`, `run_id`, `limit` 1 to 200 (default 50), `cursor` (opaque) |
| `GET /api/v1/alerts/{alert_id}` | `AlertDetail` | implemented | none |
| `GET /api/v1/typologies` | `list[TypologySummary]` | implemented | none |
| `GET /api/v1/typologies/{slug}` | `TypologyDetail` | implemented | none |
| `POST /api/v1/copilot/ask` | `CopilotAnswer` | 501 until Phase 4 | body `CopilotRequest` |

**Models** (pydantic, in `contracts/src/neonradar_contracts/api.py`; field types abbreviated):

```text
NodeFlags        synthetic: bool, sanctioned: bool, pep: bool, rca: bool
GraphNode        id: str, labels: list[str], schema: str, caption: str, flags: NodeFlags,
                 properties: dict[str, JsonValue]
GraphEdge        id: str, type: str, source: str, target: str, properties: dict[str, JsonValue]
Subgraph         nodes: list[GraphNode], edges: list[GraphEdge], truncated: bool,
                 limits: {max_nodes: int, max_edges: int}
EntitySummary    id, schema, caption, labels, flags: NodeFlags, countries: list[str], datasets: list[str]
SearchHit        entity: EntitySummary, score: float, matched_name: str
SearchResponse   query: str, items: list[SearchHit], total_estimate: int
ProvenanceRecord dataset: str, record_id: str, retrieved_at: str | None, source_url: str | None
EntityDetail     entity: EntitySummary, names: list[str], properties: dict[str, JsonValue],
                 identifiers: dict[str, list[str]], provenance: list[ProvenanceRecord],
                 relationship_counts: dict[str, int], alerts: list[AlertSummary]
PathRef          node_ids: list[str], edge_ids: list[str],
                 effective_share_min: float | None, effective_share_max: float | None
OwnershipResponse root_id, direction, paths: list[PathRef], subgraph: Subgraph
PathsResponse    from_id, to_id, paths: list[PathRef], subgraph: Subgraph
AlertSummary     alert_id, typology, priority, pattern_strength, headline, created_at,
                 subject_ids: list[str], involves_real_entities: bool, synthetic_activity: bool
AlertPage        items: list[AlertSummary], next_cursor: str | None
AlertDetail      alert: Alert (C4), evidence: Subgraph
Citation         key, title, publisher, year, url
TypologySummary  slug, name, tier, status, summary, detector_available: bool
TypologyDetail   TypologySummary fields + definition_markdown, graph_pattern, citations: list[Citation],
                 parameters: dict[str, JsonValue], false_positives: list[str]
DatasetInfo      slug, title, licence_id, licence_url, attribution, synthetic, personal_data,
                 record_count: int | None, loaded_at: str | None
Disclaimers      standing: str, synthetic_demo: str, real_data: str
MetaResponse     app_version, contracts_version, schema_version, datasets: list[DatasetInfo],
                 disclaimers: Disclaimers,
                 counts: {nodes_by_label: dict[str, int], relationships_by_type: dict[str, int]}
HealthResponse   status: "ok" | "degraded", neo4j: {connected: bool, version: str | None, edition: str | None},
                 apoc_version: str | None, gds_version: str | None
CopilotRequest   question: str (1 to 500 characters), context_entity_ids: list[str] = []
CopilotAnswer    status: "answered" | "refused" | "unsupported", answer_text: str | None,
                 template_id: str | None, cypher: str | None, parameters: dict | None,
                 subgraph: Subgraph | None, refusal_reason: str | None
Problem          type, title, status, detail, instance
```

`Subgraph` maps one to one onto Cytoscape elements (`{data: {id, source, target, ...}}`), so the UI does no graph reshaping.

### 5.4 C4: Alert v1.0.0

**What it is.** The object every detector produces, the API serves and the copilot (Phase 4) explains. It is written to `data/runs/<run_id>/alerts.jsonl` and loaded into Neo4j as `:Alert` nodes linked with `FLAGS` to their subjects.

| Field | Type | Rule |
|---|---|---|
| `alert_id` | string | `alr-` plus the first 20 hex characters of SHA-1 over `typology`, `detector.version`, sorted `evidence.edge_ids` and sorted `evidence.node_ids`, joined with `\|`. Re-running the same detector on the same graph yields the same ids. |
| `contract_version` | string | `"1.0.0"` |
| `typology` | string | A slug from the typology catalog |
| `typology_version` | string | Version of the typology definition used |
| `detector` | object | `name` (module path), `version`, `query_sha256` |
| `run_id` | string | `run-<UTC yyyymmddThhmmss>-<4 hex>` |
| `created_at` | string | UTC ISO datetime |
| `priority` | `"high"`, `"medium"`, `"low"` | Queue ordering. Default rule: `pattern_strength` of at least 0.75 is high, at least 0.5 medium, else low; a typology may document its own rule |
| `pattern_strength` | number in [0, 1] | How closely the evidence matches the typology's graph pattern. Never called a risk or suspicion score. |
| `headline` | string, at most 140 characters | Rendered from the typology's wording template; passes the wording lint (7.1) |
| `wording_class` | `"structural_pattern"` or `"synthetic_scenario"` | `synthetic_scenario` when every evidence node, every subject and every holder (source of `HOLDS_ACCOUNT`) of an evidence account is synthetic; otherwise `structural_pattern`. So `synthetic_scenario` holds exactly when `data_flags.involves_real_entities` is false |
| `subjects` | list of `{entity_id, role, caption}` | Roles are typology-defined (`origin`, `origin_holder`, `collector`, `intermediary`, `owner`, ...) |
| `evidence` | object | `node_ids`, `edge_ids` (C2 ids), `query` (`cypher`, `parameters`) so the finding can be reproduced, optional `window` (`start`, `end`) |
| `metrics` | object | Typology-specific numbers documented in the typology file (for circular flow: `cycle_length`, `sent_amount` (first hop), `returned_amount` (last hop), `currency`, `duration_hours`, `duration_days` (hours divided by 24, rounded up), `return_ratio`) |
| `explanation` | object | `summary` (plain language), `steps` (ordered `{order, text, edge_ids}`, each text at most 280 characters), `typology_reference` (`slug`, `doc_path`, `citations`), `false_positive_notes` (from the typology file) |
| `data_flags` | object | `involves_real_entities` (true if any evidence node, subject or holder of an evidence account has `synthetic = false`), `synthetic_activity` (true if every evidence relationship is synthetic, so the UI can say that a pattern next to a real entity lies in generated background activity), `datasets` |
| `disclaimer_id` | string | `"standing-v1"`; the API adds the text from `MetaResponse.disclaimers` |

**Example** (synthetic, from the walking skeleton):

```json
{
  "alert_id": "alr-5d1c0a9e4b7f2c3d1e0a",
  "contract_version": "1.0.0",
  "typology": "circular_flow",
  "typology_version": "0.1.0",
  "detector": {"name": "neonradar_detect.detectors.circular_flow", "version": "0.1.0", "query_sha256": "<hex>"},
  "run_id": "run-20261021T101500-7f3a",
  "created_at": "2026-10-21T10:15:02Z",
  "priority": "high",
  "pattern_strength": 0.79,
  "headline": "Synthetic scenario: funds returned to the originating account through 4 transfers within 7 days",
  "wording_class": "synthetic_scenario",
  "subjects": [
    {"entity_id": "syn-acct-0007", "role": "origin", "caption": "NRSYN0000000007"},
    {"entity_id": "syn-co-0003", "role": "origin_holder", "caption": "Fenwhistle Holdings Ltd"}
  ],
  "evidence": {
    "node_ids": ["syn-acct-0007", "syn-acct-0012", "syn-acct-0015", "syn-acct-0021"],
    "edge_ids": ["syn-payment-000101", "syn-payment-000102", "syn-payment-000103", "syn-payment-000104"],
    "query": {"cypher": "MATCH p = (a:Account {id: $origin})-[t:PAID]->{2,6}(a) ...", "parameters": {"origin": "syn-acct-0007", "max_window_days": 14}},
    "window": {"start": "2026-03-02T09:00:00Z", "end": "2026-03-08T16:40:00Z"}
  },
  "metrics": {"cycle_length": 4, "sent_amount": 120000.0, "returned_amount": 115200.0, "currency": "EUR", "duration_hours": 151.7, "duration_days": 7, "return_ratio": 0.96},
  "explanation": {
    "summary": "EUR 120,000 left account NRSYN0000000007 and EUR 115,200 came back to it after passing through three other accounts in just over six days.",
    "steps": [
      {"order": 1, "text": "NRSYN0000000007 sent EUR 120,000 to NRSYN0000000012 on 2 March.", "edge_ids": ["syn-payment-000101"]}
    ],
    "typology_reference": {"slug": "circular_flow", "doc_path": "docs/typologies/circular-flow.md", "citations": ["fatf_egmont_tbml_indicators_2021", "fatf_egmont_concealment_2018", "ffiec_appendix_f", "fatf_pml_2018"]},
    "false_positive_notes": ["Refunds, loan drawdown and repayment, and intra-group cash pooling also form cycles."]
  },
  "data_flags": {"involves_real_entities": false, "synthetic_activity": true, "datasets": ["nr_synthetic"]},
  "disclaimer_id": "standing-v1"
}
```

(The example `alert_id` and hashes are placeholders; real values are computed. The example shows one of the four steps. `pattern_strength` 0.79 follows the M1.9b formula: 0.5 x 0.96 + 0.3 x (1 minus 151.7 / 336) + 0.2 x 0.75.)

**Typology catalog file** (`detect/typologies/<slug>.yaml`). Not a frozen contract, but the alert refers to it, so its shape is fixed here:

```yaml
slug: circular_flow
name: Round-tripping or circular flows
version: 0.1.0
status: draft                 # draft | approved | retired  (only a typology researcher sets approved)
tier: core                    # core | extended | explainer_only
owner: "@TODO"                # typology researcher
approved_by: null
summary: >
  Funds leave an account, pass through other accounts and return to the originator
  or to a party under the same control.
doc: docs/typologies/circular-flow.md
citations: [fatf_egmont_tbml_indicators_2021, fatf_egmont_concealment_2018, ffiec_appendix_f, fatf_pml_2018]
graph_pattern: >
  A directed cycle of PAID relationships starting and ending at the same Account
  (or at two Accounts held by the same LegalEntity), with time-ordered hops,
  near-equal amounts and a short total duration.
parameters:
  min_hops: { default: 2, min: 2, max: 8 }
  max_hops: { default: 6, min: 2, max: 8 }
  max_window_days: { default: 14, min: 1, max: 90 }
  min_return_ratio: { default: 0.8, min: 0.0, max: 1.0 }
metrics: [cycle_length, sent_amount, returned_amount, currency, duration_hours, duration_days, return_ratio]
wording:
  headline_structural: "Funds returned to the originating account through {cycle_length} transfers within {duration_days} days"
  headline_synthetic: "Synthetic scenario: funds returned to the originating account through {cycle_length} transfers within {duration_days} days"
false_positives:
  - Refunds and payment reversals
  - Loan drawdown followed by repayment
  - Intra-group cash pooling and treasury sweeps
synthetic_support: high       # high | medium | low | none
generator_scenario: round_trip
detector: neonradar_detect.detectors.circular_flow   # null until implemented
```

A typology without a detector yet (most of them in Phase 1, and every `explainer_only` one) sets `detector: null` and may leave `parameters: {}`, `metrics: []`, `wording: null` and `generator_scenario: null`. Once `detector` is set, `parameters`, `metrics` and both `wording` templates are required, and every placeholder in a template must be a listed metric. `citations` holds at least one key. `TypologyFile` (M1.7c) enforces these shape rules; `scripts/check_citations.py` (M1.10a) checks that each key exists in `docs/sources/bibliography.yaml`.

### 5.5 Contract test suite

Run with `make contracts-check` (pytest marker `contract` plus drift checks). It must pass on every pull request.

| Test file | Checks |
|---|---|
| `contracts/tests/test_records.py` | Golden examples validate; one failing example per rule R1 to R10; `nr` rejects unknown keys; manifest model round-trips |
| `contracts/tests/test_datasets.py` | Registry loads; prefixes unique; reserved prefixes unused; every dataset has licence, attribution policy and status |
| `contracts/tests/test_graph_mapping.py` | Every allowed FtM schema maps to labels or a relationship; mapping matches the migration file; label and type names follow 4.4 |
| `contracts/tests/test_alert.py` | Committed `contracts/schemas/alert.v1.json` equals `Alert.model_json_schema()`; `alert_id` is deterministic; example validates; an alert whose subjects or evidence-account holders include a non-synthetic entity must be `structural_pattern` with `involves_real_entities: true` |
| `contracts/tests/test_wording.py` | Every typology wording template passes the wording lint (7.1); every "Never write" phrase in 7.1 (copied into the test) matches a forbidden pattern; "matches the graph pattern of <name>" passes the lint for every typology that has a detector; the three disclaimer files exist and are non-empty (they are outside the lint because they discuss money laundering as a subject) |
| `api/tests/test_openapi_contract.py` | The running app's OpenAPI equals `contracts/openapi/v1.json` |
| `graph/tests/test_migrations.py` (integration) | Migrations apply on an empty database, re-apply as a no-op, refuse an edited migration |
| `graph/tests/test_invariants.py` (integration) | I1 to I6 hold after loading `data/fixtures/demo-mini/` |

**Freeze procedure (Gate 1, tech lead):** `make check && make contracts-check`, review `contracts/CHANGELOG.md`, then `git tag -a contracts-v1.0.0 -m "NeonRadar contracts v1.0.0, frozen at Gate 1"` and `git push origin contracts-v1.0.0`.

---

## 6. Milestones

Every milestone has the same parts: a header, the goal, the deliverables, step-by-step instructions, acceptance commands, and a "Review focus" box for the humans who review the pull request. Where this section gives the full content of a file, write it as given (adapting only `<org>` placeholders and values from `project.yaml`), and record any change you had to make under "Deviations from spec".

---

### M1.1 Repository bootstrap and governance

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; tech lead |
| Depends on | Seed commit (1.4) |
| Branch | `p1/m1-1-bootstrap` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | No |
| ADR | ADR-0001 (record architecture decisions) |

**Goal.** A repository a stranger could open today and understand: what NeonRadar is, what it is not, how to contribute, how to report a security issue, and how work is tracked.

**Deliverables.**

| Path | Content |
|---|---|
| `LICENSE` | Apache License 2.0, exact text from `gh api /licenses/apache-2.0 --jq .body` |
| `NOTICE` | `NeonRadar` and `Copyright 2026 the NeonRadar contributors` (the project lead may change the holder) |
| `README.md` | Stub: name and one-line description from `project.yaml`; status line "Pre-release. Under construction until 20 November 2026."; the standing disclaimer from 7.1, verbatim; "What it is" and "What it is not" (from the plan's mission and out-of-scope list); a "Limitations" section with the README limitations text from 7.1, verbatim; "Quickstart: coming in Phase 1"; licence; "How we build" paragraph saying AI drafts most code openly and humans review, own and merge every change |
| `CODE_OF_CONDUCT.md` | Contributor Covenant version 2.1 text with `project.conduct_contact` |
| `SECURITY.md` | Report privately through GitHub private vulnerability reporting or `project.security_contact`; supported versions: `main` until the first release; no bounty; response within 7 days |
| `CONTRIBUTING.md` | Draft: issue first, then branch and pull request; the template; review by a member of another squad; "the author must be able to explain every line, and 'the AI wrote it' is not an answer"; agent pull requests are labelled `agent` and name a human owner; Conventional Commits; the size rule from 2.3; bring a branch up to date by merging `main`, never by force-pushing; documentation, typology definitions, fixtures and licence notes are contributions like code; link to `docs/build/` |
| `CONTRIBUTORS.md` | Header and format only: `- Name (@handle): what they owned. N merged PRs.` (humans fill it in) |
| `DATA_SOURCES.md` | Draft table from 3.3, marked "Draft, owned by the data steward (`people.data_steward`)" |
| `CHANGELOG.md` | `# Changelog` with an `## Unreleased` section |
| `.gitignore` | Python, Node, editors; `.env`, `.env.*` except `.env.example`; `secrets/`; the data rules in exactly this order (git cannot re-include a file inside an excluded directory, so the order matters): `data/*`, `!data/fixtures/`, `!data/README.md`, `!data/import/`, `data/import/*`, `!data/import/.gitkeep`; `.claude/settings.local.json`; `CLAUDE.local.md`; `.claude/worktrees/`; `ui/node_modules/`, `ui/dist/`, `ui/test-results/`, `ui/playwright-report/` |
| `.gitattributes` | `* text=auto eol=lf`; `*.sh text eol=lf`; mark as generated: `uv.lock`, `ui/package-lock.json`, `ui/src/api/schema.d.ts`, `contracts/openapi/*.json`, `contracts/schemas/*.json`; mark as documentation: `docs/research/**` |
| `.editorconfig` | UTF-8, LF, final newline, 4 spaces for Python, 2 spaces for YAML, JSON, TypeScript, Vue, Markdown; tabs for `Makefile` |
| `.worktreeinclude` | `.env` (so Claude Code worktrees get the local environment file) |
| `.github/pull_request_template.md` | Full content below |
| `.github/ISSUE_TEMPLATE/` | Issue forms: `bug.yml`, `feature.yml`, `typology.yml` (slug, definition, graph pattern, sources with links, false positives), `data-source.yml` (source, licence, access, personal data, what it adds), `contract-change.yml` (contract, current version, proposed change, classification patch, minor or major, migration impact, who approved), `config.yml` (blank issues off, security link) |
| `.github/labels.yml` | The label set below |
| `.github/pr-size-exclude.txt` | One glob per line: `uv.lock`, `ui/package-lock.json`, `ui/src/api/schema.d.ts`, `contracts/openapi/**`, `contracts/schemas/**`, `contracts/examples/**`, `data/fixtures/**`, `**/tests/fixtures/**`, `docs/research/**`, `**/*.md`, `detect/typologies/*.yaml`, `docs/sources/bibliography.yaml`, `LICENSE`, `NOTICE` |
| `.github/CODEOWNERS` | Generated by `scripts/generate_codeowners.py` from `project.yaml` and the ownership map in 4.3 |
| `scripts/generate_codeowners.py` | Reads `docs/build/project.yaml`; writes `.github/CODEOWNERS`; `--check` exits 1 if the file is out of date. Uses PyYAML through `uv run --no-project --with pyyaml` |
| `scripts/sync_labels.py` | Creates or updates every label in `.github/labels.yml` with `gh label create <name> --color <hex> --description <text> --force`. Uses PyYAML through `uv run --no-project --with pyyaml` |
| `docs/build/PROGRESS.md` | The table from 2.8 with one row per milestone (M1.1 to M1.12, including every sub-milestone and the three pull requests M1.10b-1, M1.10b-2 and M1.10b-3) set to `todo`, and M1.1 set to `pr-open` at the end of this milestone |
| `docs/README.md` | Index of the `docs/` tree (4.2) |
| `docs/decisions/README.md`, `docs/decisions/_template.md` | ADR index and template: Title, Status (proposed, accepted, superseded), Date, Deciders, Context, Options considered, Decision, Consequences, Sources |
| `docs/decisions/0001-record-architecture-decisions.md` | Status `proposed` (the project lead and tech lead accept it in review): we record every non-obvious decision as an ADR owned by the people who made it; the agent may draft an ADR, always as `proposed`, and the named deciders edit it and set `accepted`; numbering is pre-assigned in 7.6 to avoid collisions between parallel pull requests |
| `data/README.md` | What may be committed (synthetic fixtures only) and what must not (everything else), with the guardrails G1 and G2 |
| `data/import/.gitkeep` | Keeps the Compose import mount directory present |

Pull request template (`.github/pull_request_template.md`):

```markdown
## Summary
<!-- What changed and why, in two to five sentences. -->

## Milestone
<!-- For example M1.4. Link the spec section. -->

## Human owner
<!-- @handle of the person accountable for this PR. Agent PRs must name one. -->

## Acceptance evidence
<!-- Each acceptance command and the meaningful lines of its output. -->

## Contract impact
- [ ] None
- [ ] Touches contracts/ or graph/schema/ (needs the contract-change label and tech lead approval)

## Data and licence impact
- [ ] No data files added
- [ ] Only synthetic fixtures added (ids start with syn-)
- [ ] Touches a loader, DATA_SOURCES.md or contracts/datasets.yaml (data steward review)

## AI involvement
- [ ] Drafted by an agent (label: agent)
- [ ] Human-written

## Deviations from spec

## Not addressed
<!-- Review findings deliberately left for later, with reasons. -->
```

Labels (`.github/labels.yml`, name, colour, description):

```yaml
- { name: agent, color: "7057ff", description: "Drafted by an AI agent; a named human owns it" }
- { name: phase-1, color: "0e8a16", description: "Phase 1: foundation and contracts" }
- { name: phase-2, color: "0e8a16", description: "Phase 2: ownership graph" }
- { name: phase-3, color: "0e8a16", description: "Phase 3: transactions and detection" }
- { name: phase-4, color: "0e8a16", description: "Phase 4: API and copilot" }
- { name: phase-5, color: "0e8a16", description: "Phase 5: explorer UI" }
- { name: phase-6, color: "0e8a16", description: "Phase 6: hardening, docs and launch" }
- { name: "squad:ingest", color: "1d76db", description: "Data ingestion squad" }
- { name: "squad:graph", color: "1d76db", description: "Graph and entity resolution squad" }
- { name: "squad:detect", color: "1d76db", description: "Typologies and detection squad" }
- { name: "squad:copilot", color: "1d76db", description: "Investigation copilot and API squad" }
- { name: "squad:ui", color: "1d76db", description: "Explorer UI squad" }
- { name: "squad:docs", color: "1d76db", description: "Docs, DX and launch squad" }
- { name: contract-change, color: "b60205", description: "Changes a frozen contract; tech lead approval required" }
- { name: needs-human-decision, color: "d93f0b", description: "Blocked on a decision only a human can make" }
- { name: blocked, color: "d93f0b", description: "Cannot proceed" }
- { name: typology, color: "5319e7", description: "AML typology definition or detection" }
- { name: data-source, color: "5319e7", description: "Data source, loader or licence" }
- { name: spike, color: "c5def5", description: "Time-boxed exploration" }
- { name: adr, color: "c5def5", description: "Architecture decision record" }
- { name: learning, color: "fbca04", description: "Learning track" }
- { name: "good first issue", color: "7057ff", description: "Good for newcomers" }
- { name: "help wanted", color: "008672", description: "Extra attention is needed" }
- { name: e2e, color: "c5def5", description: "Run the end-to-end demo test on this pull request" }
- { name: size-exception, color: "c5def5", description: "Milestone allowed to exceed the 400-line limit (see PHASE-1.md 2.3)" }
```

**Instructions.**

1. Create the branch. Write every file above. Fill names and contacts from `project.yaml`; where a value is `TODO`, leave a visible `TODO` and list it in the pull request (do not stop for contacts in this milestone).
2. Run `uv run --no-project --with pyyaml python scripts/generate_codeowners.py` to produce `.github/CODEOWNERS`, then run it again with `--check`.
3. Run `uv run --no-project --with pyyaml python scripts/sync_labels.py` so the labels exist before you open the pull request.
4. Open the pull request with labels `agent`, `phase-1`, `squad:docs`.

**Acceptance.**

```bash
grep -q "Apache License" LICENSE && grep -q "Version 2.0" LICENSE
uv run --no-project --with pyyaml python scripts/generate_codeowners.py --check
gh label list --limit 100 --json name --jq '.[].name' | grep -c -E '^(agent|phase-1|contract-change|squad:graph)$'   # prints 4
test -f docs/build/PROGRESS.md && grep -q "M1.12" docs/build/PROGRESS.md
git check-ignore -q .env && git check-ignore -q data/cache/x && ! git check-ignore -q data/fixtures/x
! git check-ignore -q data/import/.gitkeep && git check-ignore -q data/import/companies.csv
```

**Review focus (humans).** Does the README say plainly what NeonRadar is not? Are the disclaimer and the limitations text verbatim? Are the CODEOWNERS teams right, and do they have write access? Are the contacts real?

---

### M1.2 Agent kit

| | |
|---|---|
| Squad, human owner | Tech lead |
| Depends on | M1.1 |
| Branch | `p1/m1-2-agent-kit` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | Yes |
| Size | exception (verbatim kit from this spec) |
| ADR | ADR-0011 (AI-built workflow) |

**Goal.** Every later Claude Code session, for every person, starts from the same rules, commands and conventions, and the most dangerous mistakes are blocked by deterministic hooks rather than by instructions alone.

**Deliverables.** `CLAUDE.md`; `.claude/rules/*.md`; `.claude/settings.json`; `.claude/hooks/format-file.sh`, `guard-contracts.sh` and `guard_git.py`; six skills in `.claude/skills/`; three subagents in `.claude/agents/`; `.mcp.json`; `scripts/test_hooks.sh`; `docs/decisions/0011-ai-built-workflow.md`.

**`CLAUDE.md`** (keep under 200 lines; write exactly this, then fill `<org>`):

```markdown
# NeonRadar

Open-source, local-first graph investigation toolkit for anti-money-laundering and
anti-corruption work. Python 3.14 (uv workspace), Neo4j 5.26 LTS Community with APOC and
GDS, FastAPI, Vue 3. Licence Apache-2.0. The build spec for the current phase is
docs/build/PHASE-<n>.md; project facts are in docs/build/project.yaml.

## Non-negotiable rules
1. Never label a real person or company as suspicious. Synthetic laundering scenarios run
   only among synthetic entities (ids start with `syn-`). Real registry entities may only
   receive synthetic background activity. Exceptions need an approved ADR (PHASE-1.md G1).
2. Commit code and synthetic fixtures only. Never commit bulk data, real personal data,
   API responses about real people, or any row derived from OpenSanctions.
3. Nothing phones home. No telemetry, analytics or outbound calls at runtime. Only explicit
   loader and spike commands use the network. Tests never use the network.
4. Every AML fact in docs cites a key from docs/sources/bibliography.yaml. You may draft
   typology definitions; never set `status: approved`.
5. Describe patterns, never accusations. Never write that an entity laundered money or is
   a launderer, criminal, fraudster or guilty. Use the wording templates (PHASE-1.md 7.1).
6. Secrets live in .env or GitHub secrets. Never print, log, commit or ask for them.
7. contracts/** and graph/schema/** are frozen once tag contracts-v1.0.0 exists. Changes
   need an approved contract-change issue (/contract-change).
8. Humans merge. Never run gh pr merge, push to main, force-push, or change repo settings
   (.claude/hooks/guard_git.py blocks these). Update a branch with `git merge origin/main`.

## Commands
- `make setup`            install everything (uv sync, npm ci, pre-commit)
- `make check`            lint, types, unit tests, contract checks: run before every PR
- `make up` / `make down` start or stop Neo4j (Docker Compose); `make smoke` checks it
- `make test-int`         integration tests (Neo4j via Testcontainers)
- `make contracts`        regenerate JSON Schemas and the OpenAPI snapshot
- `make demo-mini`        load the synthetic demo, run detection, start API and UI
- `make hygiene`          the pull request checks CI runs (size, fixtures, wording)
- `uv run neonradar --help`  the project command line

## Layout
contracts/ (C1-C4, frozen) · ingest/ · graph/ (graph/schema frozen) · detect/ · copilot/ ·
api/ · cli/ · ui/ · data/fixtures/ (synthetic only) · docs/ · scripts/ · .claude/
Each Python package: <dir>/src/neonradar_<dir>/, tests in <dir>/tests/, notes in <dir>/CLAUDE.md.

## Workflow
- One milestone per branch and PR: `/milestone <id>` runs the protocol in PHASE-<n>.md 2.2.
- Branch `p<phase>/<milestone>-<slug>`; Conventional Commits `type(scope): summary`.
- PR <= 400 changed lines of code, tests and config (PHASE-<n>.md 2.3; split otherwise).
- Prove it: run the milestone's acceptance commands; paste the evidence into the PR.
- Before opening a PR, ask the `reviewer` subagent to review the diff.
- If the spec and reality disagree: small and mechanical, adapt and record it under
  "Deviations from spec"; anything that changes behaviour, stop and ask.

## Conventions
- Python: typed (mypy strict), pydantic v2 models, typer CLIs, pytest markers `contract`,
  `integration`, `network`, `e2e`. No print in library code; use logging.
- Cypher: Neo4j 5.26, Cypher 5, forward-compatible subset (PHASE-1.md 5.2): parameters
  only, `CALL (x) { }`, `elementId()`, quantified paths `-[:PAID]->{2,6}`, bounded hops
  and LIMIT, `CALL { } IN TRANSACTIONS` for big writes, no apoc.periodic.iterate.
- Graph properties snake_case; record (FtM) properties camelCase. Ids `<prefix>-<rest>`.
- Frontend: Vue 3.5 `<script setup lang="ts">`, TypeScript ~6.0.3 (never 7), Pinia, Vue
  Router, Cytoscape.js, CSS logical properties (RTL-ready).

## Known traps (verified 16 Oct 2026)
- followthemoney 4.x: build records with `ValueEntity(model[schema], {"id": ..., "datasets":
  [slug]})`; `model.make_entity` output has no `datasets`; CompositeEntity is gone; Payment
  dates lose their timezone, so write UTC without an offset.
- `CALL { } IN TRANSACTIONS` needs an auto-commit `session.run()`, not `execute_query`.
- pydantic-settings reading `.env`: `extra="ignore"`.
- Splink 5, not 4: `db_api.register(df)` then `Linker(sdf, settings)`.
- graphdatascience 2.x is snake_case only; prefer `CALL gds.*` through the driver.
- neo4j driver 6: `execute_read` / `execute_write`; `read_transaction` is gone.
- testcontainers: `from testcontainers.community.neo4j import Neo4jContainer`.
- Community Edition: uniqueness constraints only (no existence, type or key constraints).
- httpx needs `follow_redirects=True` (OpenSanctions answers 307).
- The Neo4j image has wget and cypher-shell, not curl.
- Never add @neo4j-nvl (proprietary) or GPL packages (unidecode, pyarabic).
- Faker ar_SA surnames include real prominent families: use the denylist.
```

**Path-scoped rules** (`.claude/rules/`). Each file starts with `paths:` frontmatter so it loads only when Claude works on matching files.

`.claude/rules/python.md`:

```markdown
---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---
# Python rules
- Python 3.14. Every public function and method has type hints; mypy strict must pass.
- Contract types come from `neonradar_contracts`; never redefine them locally.
- Read configuration from environment variables through one settings object per package
  (pydantic-settings), never at import time.
- Network code lives only in `neonradar_ingest` loaders and spikes; it uses httpx with
  timeouts, explicit `follow_redirects`, retries with backoff and a rate limiter.
- Tests: `tests/test_<module>.py`; integration tests marked `@pytest.mark.integration`;
  anything touching the internet marked `@pytest.mark.network` (never run in CI).
- No test may depend on the order of other tests or on data outside `data/fixtures/` and
  the package's own `tests/fixtures/`.
```

`.claude/rules/cypher.md`:

```markdown
---
paths:
  - "**/*.cypher"
  - "graph/**"
  - "detect/**"
---
# Cypher rules (Neo4j 5.26 Community, Cypher 5)
- Parameters only. Labels and relationship types come from the C2 mapping table, never
  from data.
- Use `CALL (x) { ... }`, `elementId()`, quantified relationships `-[:R]->{1,6}` or
  quantified path patterns; never `[*..]`, never `id()`.
- Bound every traversal (at most 8 hops), every result (LIMIT) and every time window.
- Large writes: `CALL (row) { ... } IN TRANSACTIONS OF 10000 ROWS` in auto-commit queries.
- Never `apoc.periodic.iterate`, `SET n = r`, `indexProvider`, or existence/type/key
  constraints (Enterprise only).
- GDS calls pass `concurrency: 4`. Prefer `CALL gds.<algo>.stream(...)` from Cypher.
- Detection queries read only C2 labels, types and properties.
- Every detection query has a fixture test with a known right answer.
```

`.claude/rules/frontend.md`:

```markdown
---
paths:
  - "ui/**"
---
# Frontend rules
- Vue 3.5 single-file components with `<script setup lang="ts">`; no Vapor mode.
- TypeScript pinned to ~6.0.3. Never install typescript@latest.
- API types are generated from contracts/openapi/v1.json into src/api/schema.d.ts; never
  hand-write API types.
- Graph rendering uses Cytoscape.js; never @neo4j-nvl.
- Use CSS logical properties (margin-inline-start, not margin-left) so Arabic RTL works later.
- The standing disclaimer is visible on every page that shows entities or alerts.
- No analytics, no external fonts or CDNs at runtime; everything is bundled.
```

`.claude/rules/data-and-fixtures.md`:

```markdown
---
paths:
  - "data/**"
  - "**/fixtures/**"
  - "ingest/**"
  - "contracts/examples/**"
---
# Data and fixture rules
- Committed fixtures are synthetic: every record id starts with `syn-`, dataset
  `nr_synthetic`, `nr.synthetic: true`.
- Never commit API responses, downloads or samples from real sources. Spike and loader
  output goes to data/cache/ (gitignored).
- Synthetic names: Faker (ar_SA, ru_RU, en_GB) through the denylist filter; company names
  from neutral word lists plus a legal form; no real brands or listed companies.
- Synthetic accounts: `NRSYN` plus 10 digits; never set iban or bic.
- Ground-truth labels never go into records or the graph; they go to separate label files.
- Respect each source's rate limit and licence (contracts/datasets.yaml).
```

`.claude/rules/aml-docs.md`:

```markdown
---
paths:
  - "docs/**"
  - "detect/typologies/**"
  - "README.md"
---
# Rules for AML documentation
- Every factual AML statement cites a key from docs/sources/bibliography.yaml.
- Use the terminology in docs/glossary.md: "beneficial owner" only for natural persons,
  STR for FATF contexts and SAR for US material, "nominee" (strawman and proxy are synonyms).
- 25 percent is an illustrative FATF example that became law in the EU and elsewhere; it is
  not a FATF requirement.
- Typology files you write have `status: draft`. Only a typology researcher approves.
- Real cases: name as wrongdoers only institutions that admitted facts and individuals who
  were convicted (give the court level and the date you checked). Victims, publishers,
  courts and authorities may be named in those roles. Describe everyone else by role, and
  say what is adjudicated and what is alleged.
- Keep the standing disclaimer wording exactly as in PHASE-1.md 7.1.
```

**`.claude/settings.json`:**

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(make *)",
      "Bash(uv run *)",
      "Bash(uv sync *)",
      "Bash(uv lock *)",
      "Bash(uv add *)",
      "Bash(uv remove *)",
      "Bash(uv tree *)",
      "Bash(uv python *)",
      "Bash(npm ci *)",
      "Bash(npm run *)",
      "Bash(npm install *)",
      "Bash(npx playwright *)",
      "Bash(npx vue-tsc *)",
      "Bash(docker compose *)",
      "Bash(git status *)",
      "Bash(git diff *)",
      "Bash(git log *)",
      "Bash(git show *)",
      "Bash(git add *)",
      "Bash(git commit *)",
      "Bash(git switch *)",
      "Bash(git checkout -b *)",
      "Bash(git fetch *)",
      "Bash(git pull --ff-only *)",
      "Bash(git merge origin/main)",
      "Bash(git merge --no-edit origin/main)",
      "Bash(git push -u origin p1/*)",
      "Bash(git push origin p1/*)",
      "Bash(gh pr create *)",
      "Bash(gh pr view *)",
      "Bash(gh pr checks *)",
      "Bash(gh pr diff *)",
      "Bash(gh pr comment *)",
      "Bash(gh pr edit *)",
      "Bash(gh issue create *)",
      "Bash(gh issue view *)",
      "Bash(gh issue list *)",
      "Bash(gh label *)",
      "Bash(gh run view *)",
      "Bash(gh run list *)",
      "Bash(jq *)",
      "Bash(python3 scripts/*)",
      "WebFetch(domain:code.claude.com)",
      "WebFetch(domain:neo4j.com)",
      "WebFetch(domain:pypi.org)",
      "WebFetch(domain:www.npmjs.com)",
      "WebFetch(domain:github.com)",
      "WebFetch(domain:developer.company-information.service.gov.uk)",
      "WebFetch(domain:www.gleif.org)",
      "WebFetch(domain:followthemoney.tech)",
      "WebFetch(domain:www.opensanctions.org)",
      "WebFetch(domain:offshoreleaks.icij.org)",
      "WebFetch(domain:www.fatf-gafi.org)"
    ],
    "ask": [
      "Bash(docker compose down -v*)",
      "Bash(docker volume rm *)",
      "Bash(gh api *)",
      "Bash(gh secret *)",
      "Bash(gh variable *)",
      "Bash(git reset *)",
      "Bash(git branch -D *)",
      "Bash(rm -rf *)"
    ],
    "deny": [
      "Read(./.env)",
      "Read(./.env.local)",
      "Read(./secrets/**)",
      "Edit(./.env)",
      "Bash(gh pr merge *)",
      "Bash(git push --force *)",
      "Bash(git push --force-with-lease*)",
      "Bash(git push -f *)",
      "Bash(git push origin main*)",
      "Bash(git push origin HEAD:main*)",
      "Bash(gh repo edit *)",
      "Bash(gh repo delete *)",
      "Bash(npm install typescript@latest*)",
      "Bash(npm i typescript@latest*)"
    ]
  },
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard-contracts.sh" }
        ]
      },
      {
        "matcher": "Bash",
        "hooks": [
          { "type": "command", "command": "python3 \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/guard_git.py" }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "\"$CLAUDE_PROJECT_DIR\"/.claude/hooks/format-file.sh" }
        ]
      }
    ]
  }
}
```

Rule order is deny, then ask, then allow; the first match wins. That is why `git push` to `p1/*` branches is allowed while pushes to `main` and force-pushes are denied, and why there is no broad `git push *` ask rule (it would override the allow rules). Permission rules match command text by pattern, so a command such as `git push origin p1/x:main` would slip past them; the `guard_git.py` hook below parses every Bash command and is the real control. From Phase 2 on, add `p2/*` push rules in that phase's first milestone (the hook already accepts any `p<phase>/` branch).

**`.claude/hooks/guard-contracts.sh`** (make it executable):

```bash
#!/usr/bin/env bash
# PreToolUse(Edit|Write): block edits to frozen contracts once tag contracts-v1.0.0 exists.
# Exit 2 blocks the tool call and shows the message to Claude. See CLAUDE.md rule 7.
set -uo pipefail
input="$(cat)"
file="$(printf '%s' "$input" | jq -r '.tool_input.file_path // empty')"
[ -z "$file" ] && exit 0
case "$file" in
  */contracts/*|*/graph/schema/*) ;;
  *) exit 0 ;;
esac
if ! git -C "${CLAUDE_PROJECT_DIR:-.}" rev-parse -q --verify "refs/tags/contracts-v1.0.0" >/dev/null 2>&1; then
  exit 0   # contracts are not frozen yet (Phase 1 authoring)
fi
if [ "${NR_ALLOW_CONTRACT_CHANGE:-}" = "1" ]; then
  exit 0   # the tech lead opened an approved contract-change session
fi
echo "Blocked: ${file} is a frozen contract (tag contracts-v1.0.0). Open a contract-change issue; the tech lead enables NR_ALLOW_CONTRACT_CHANGE=1 for the session after approval." >&2
exit 2
```

The patterns match `*/contracts/*` anywhere in the path, so the guard also works inside worktrees under `.claude/worktrees/`. For an approved change, the tech lead adds `{"env": {"NR_ALLOW_CONTRACT_CHANGE": "1"}}` to `.claude/settings.local.json` (gitignored) for that session only, then removes it.

**`.claude/hooks/format-file.sh`** (make it executable; it never blocks; it only formats, because lint fixes between two edits would delete an import the next edit is about to use; `ruff check --fix` runs at commit time through pre-commit):

```bash
#!/usr/bin/env bash
# PostToolUse(Edit|Write): format the file Claude just wrote. Always exits 0.
set -uo pipefail
file="$(jq -r '.tool_input.file_path // empty')"
[ -z "$file" ] || [ ! -f "$file" ] && exit 0
case "$file" in
  *.py)
    uv run --no-sync ruff format --quiet "$file" >/dev/null 2>&1
    ;;
  */ui/*.ts|*/ui/*.vue|*/ui/*.css|*/ui/*.json)
    ( cd "${CLAUDE_PROJECT_DIR:-.}/ui" && npx --no-install prettier --write "$file" >/dev/null 2>&1 )
    ;;
esac
exit 0
```

**`.claude/hooks/guard_git.py`** (standard library only, Python 3.9 or later, because it runs with the system `python3`; tested with the cases listed under `scripts/test_hooks.sh`):

```python
#!/usr/bin/env python3
"""PreToolUse(Bash) hook: keep git pushes on milestone branches and keep merges human.

Blocks (exit 2, reason on stderr): force pushes of any kind, pushes whose destination
is not a p<phase>/ branch (main, tags, HEAD on main, deletions), `gh pr merge`,
`gh api` calls that merge or move refs or change branch protection, and
`gh repo edit|delete|rename|archive`. Everything else passes (exit 0).
Standard library only; runs on Python 3.9 or later.
"""

import json
import re
import shlex
import subprocess
import sys

BRANCH_OK = re.compile(r"^p\d+/[A-Za-z0-9._/-]+$")
OPERATORS = {"&&", "||", ";", "|", "&", "\n"}
FORCE_FLAGS = {"-f", "--force", "--mirror", "--all", "--tags", "--delete", "-d", "--prune"}


def block(reason):
    sys.stderr.write("Blocked by .claude/hooks/guard_git.py: " + reason + "\n")
    sys.exit(2)


def split_commands(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    commands, current = [], []
    for token in lexer:
        if token in OPERATORS or set(token) <= set("&|;"):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def current_branch(cwd):
    try:
        out = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd or None,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return out.stdout.strip()
    except Exception:
        return ""


def check_push(args, cwd):
    positional = []
    for arg in args:
        if arg.startswith("--"):
            name = arg.split("=", 1)[0]
            if name in FORCE_FLAGS or name.startswith("--force"):
                block("force, delete, mirror, tag and all-branch pushes are blocked (" + arg + ")")
        elif arg.startswith("-") and len(arg) > 1:
            if arg in FORCE_FLAGS or "f" in arg[1:] or "d" in arg[1:]:
                block("force and delete pushes are not allowed (" + arg + ")")
        else:
            positional.append(arg)
    refspecs = positional[1:]
    if not refspecs:
        branch = current_branch(cwd)
        if not BRANCH_OK.match(branch):
            block("a plain push from branch '" + branch + "' would not go to a p<phase>/ branch")
        return
    for spec in refspecs:
        if spec.startswith("+"):
            block("forced refspec '" + spec + "' is not allowed")
        src, _, dst = spec.partition(":")
        if ":" not in spec:
            dst = src
        if src == "" or dst == "":
            block("deleting a remote branch is not allowed ('" + spec + "')")
        if dst == "HEAD":
            dst = current_branch(cwd)
        dst = dst[len("refs/heads/") :] if dst.startswith("refs/heads/") else dst
        if not BRANCH_OK.match(dst):
            block("push destination '" + dst + "' is not a p<phase>/ milestone branch")


def check_command(tokens, cwd):
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]
    if not tokens:
        return False
    if tokens[0] == "git":
        i = 1
        while i < len(tokens) and tokens[i].startswith("-"):
            i += 2 if tokens[i] in ("-C", "-c") else 1
        if i < len(tokens) and tokens[i] == "push":
            check_push(tokens[i + 1 :], cwd)
            return True
    elif tokens[0] == "gh" and len(tokens) > 1:
        rest = tokens[1:]
        if rest[:2] == ["pr", "merge"]:
            block("only humans merge pull requests")
        if rest[0] == "repo" and rest[1:2] in (["edit"], ["delete"], ["rename"], ["archive"]):
            block("repository settings are changed by humans")
        if rest[0] == "api":
            joined = " ".join(rest)
            if re.search(r"/merges?\b|/git/refs|/protection\b|/rulesets", joined):
                block("this gh api call merges, moves refs or changes protection; humans do that")
    return False


def parse(command):
    """Token lists per simple command, or None when the shell syntax is too complex."""
    try:
        commands = []
        for line in command.replace("\\\n", " ").splitlines():
            commands.extend(split_commands(line))
        return commands
    except ValueError:
        pass
    try:
        return split_commands(command)
    except ValueError:
        return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    command = (data.get("tool_input") or {}).get("command") or ""
    if "git" not in command and "gh" not in command:
        return 0
    raw_push = re.search(r"\bgit\b(\s+-\S+)*(\s+-[Cc]\s+\S+)*\s+push\b", command)
    if re.search(r"\bgh\s+pr\s+merge\b", command):
        block("only humans merge pull requests")
    commands = parse(command)
    if commands is None:
        if raw_push or re.search(r"\bgh\s+(api|repo)\b", command):
            block("could not parse a command that pushes or calls gh api or gh repo; simplify it")
        return 0
    seen_push = False
    for tokens in commands:
        if check_command(tokens, data.get("cwd")):
            seen_push = True
    if raw_push and not seen_push:
        block("could not verify this push; run git push as a simple command of its own")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**Skills** (`.claude/skills/<name>/SKILL.md`). Write these six.

`.claude/skills/milestone/SKILL.md`:

```markdown
---
name: milestone
description: Execute one NeonRadar build milestone (for example M1.4 or M2.3) end to end with the milestone protocol, open a pull request, and stop. Use when the user gives a milestone id.
argument-hint: "[milestone-id]"
disable-model-invocation: true
---
Execute milestone $ARGUMENTS.

Current state:
- Branch: !`git branch --show-current`
- Recent progress: !`tail -n 25 docs/build/PROGRESS.md 2>/dev/null || echo "PROGRESS.md missing"`

1. The spec is docs/build/PHASE-<n>.md where <n> is the number after "M". If you have not
   read its sections 0, 2, 3, 4 and 5 in this session, read them now. Then read only the
   section for $ARGUMENTS and whatever it links to.
2. Follow the milestone protocol in section 2.2 exactly: dependencies merged, plan (if the
   milestone says "Plan first"), branch, build, run every acceptance command, reviewer
   subagent, update PROGRESS.md, /open-pr, wait for CI, report, stop.
3. Never merge. Never start another milestone. If anything in section 2.5 applies, stop
   and ask.
```

`.claude/skills/open-pr/SKILL.md`:

```markdown
---
name: open-pr
description: Push the current branch and open a NeonRadar pull request with the template, labels and human owner, after checks pass. Use at the end of a milestone.
---
1. Confirm `make check` passed in this session (run it if not). Confirm the milestone's
   acceptance commands passed.
2. `git push -u origin <current branch>`.
3. Write the PR body from .github/pull_request_template.md: summary, milestone, human owner
   (from docs/build/project.yaml: the squad mentor, or the tech lead for repo and contract
   work), acceptance evidence (commands and key output lines), contract impact, data and
   licence impact, AI involvement (agent), deviations from spec, not addressed.
4. `gh pr create --base main --title "<type>(<scope>): <summary> [<milestone>]"
   --body-file <tmp file> --label agent --label phase-<n> --label <squad labels>`, plus
   `--label size-exception` only when the milestone header says `Size: exception`.
5. Print the PR URL. Do not merge.
```

`.claude/skills/adr/SKILL.md`:

```markdown
---
name: adr
description: Write an architecture decision record in docs/decisions using the project template and the pre-assigned number from the build spec. Use when a milestone asks for an ADR.
argument-hint: "[number] [title]"
---
Write ADR $ARGUMENTS.
- Use docs/decisions/_template.md. The number is pre-assigned in the phase spec (7.6 in
  PHASE-1.md); never pick a new number yourself.
- Context and options must cite evidence (docs/research/ files or official URLs).
- Status: always "proposed". The deciders named in the spec edit the ADR and set
  "accepted" themselves. Deciders are people, never yourself.
- Add the ADR to docs/decisions/README.md.
```

`.claude/skills/contract-change/SKILL.md`:

```markdown
---
name: contract-change
description: Prepare a change to a frozen NeonRadar contract (C1 record, C2 graph schema, C3 API, C4 alert) after tag contracts-v1.0.0. Use only when a contract-change issue exists.
argument-hint: "[issue-number]"
disable-model-invocation: true
---
1. Read issue #$ARGUMENTS. It must have the label contract-change and an approval comment
   from the tech lead. If not, stop.
2. Classify: patch, minor or major (PHASE-1.md 5.0). Major changes need written sign-off.
3. The guard hook blocks edits unless NR_ALLOW_CONTRACT_CHANGE=1 is set for this session.
   If edits are blocked, stop and ask the tech lead; never try to bypass the hook.
4. Change the models, bump the contract version, update contracts/CHANGELOG.md, run
   `make contracts` to regenerate JSON Schemas and OpenAPI, and for C2 add a NEW migration
   file. Update every consumer and test in the same PR.
5. Run `make check` and `make test-int`. Open the PR with the label contract-change.
```

`.claude/skills/typology-draft/SKILL.md`:

```markdown
---
name: typology-draft
description: Draft or update a NeonRadar typology definition file and its plain-language explainer from cited primary sources, always as status draft. Use for detect/typologies and docs/typologies work.
argument-hint: "[slug]"
---
Draft typology $ARGUMENTS.
- Sources: docs/research/2026-10-16/aml-domain.md section 2 and the bibliography keys in
  docs/sources/bibliography.yaml. Every factual sentence cites a key. If a claim has no
  source, leave it out and list it under "Open questions".
- Write detect/typologies/$ARGUMENTS.yaml in the shape of PHASE-1.md 5.4 with
  `status: draft`, `approved_by: null`.
- Write docs/typologies/<slug with hyphens>.md: what it is (plain language), how it looks
  in a graph, red flags from the sources, typical false positives, why synthetic data can or
  cannot show it, sources. No accusatory wording (7.1). Reading level: a new intern.
- Never set status approved.
```

`.claude/skills/spike-report/SKILL.md`:

```markdown
---
name: spike-report
description: Write a data source spike report in docs/data/spikes from the measured results of a spike run. Use at the end of an M1.8 spike.
argument-hint: "[source-slug]"
---
Write docs/data/spikes/$ARGUMENTS.md with these sections:
1. Command run, date, duration, network conditions.
2. What was fetched (endpoints or files, record counts by FtM schema). No personal data:
   counts, field names and coverage only.
3. Measured facts that confirm or correct docs/research/2026-10-16/ (sizes, headers, rate
   limit behaviour, redirects, encodings).
4. Mapping notes: source field to FtM property, and anything that does not map.
5. Licence and personal-data notes for the data steward.
6. Gotchas and recommendations for the Phase 2 loader.
7. Verdict: go, go with changes, or drop (the plan's day-2 spike rule).
```

**Subagents** (`.claude/agents/`).

`.claude/agents/reviewer.md`:

```markdown
---
name: reviewer
description: Independent pre-PR reviewer for NeonRadar. Use before opening any pull request to check the branch diff against the milestone acceptance list, the contracts and the repository rules. Read-only.
tools: Read, Grep, Glob, Bash
model: inherit
---
You review a NeonRadar branch before it becomes a pull request. You did not write it.
Never edit files; use Bash only for read-only commands (git diff, git log, ls, cat, grep,
uv run pytest --collect-only).

1. `git diff --stat main...HEAD` and `git diff main...HEAD`.
2. Read the milestone section named in your request (docs/build/PHASE-<n>.md) and section 2.
3. Check:
   - every acceptance item is met and there is evidence for it;
   - contracts (section 5) are respected; no frozen file changed without the label;
   - guardrails G1 to G7: no real-person data, no OpenSanctions rows, no network in tests,
     no secrets, no accusatory wording, citations present for AML facts;
   - tests are meaningful: they would fail if the code were wrong, and no test was
     weakened or deleted to pass;
   - Cypher follows the conventions in 5.2; Python is typed; no new GPL dependencies;
   - PR size within the limit (excluding generated files and fixtures).
4. Report only findings that affect correctness, the stated requirements or the rules, as:
   BLOCKING (file:line, why, suggested fix), SHOULD FIX, NOTES. If there are none, say so.
```

`.claude/agents/contract-guardian.md`:

```markdown
---
name: contract-guardian
description: Checks a NeonRadar diff for contract impact (C1 record, C2 graph schema, C3 API, C4 alert) and for drift between models, JSON Schemas, OpenAPI snapshot, migrations and consumers. Use for any change under contracts/, graph/, api/ or detect/.
tools: Read, Grep, Glob, Bash
model: inherit
---
Read-only. Compare the diff (`git diff main...HEAD`) with PHASE-1.md section 5.
Report: which contract and version is affected; whether the change is patch, minor or
major; whether JSON Schemas, contracts/openapi/v1.json, migrations and every consumer
(loader, detectors, API, UI types, fixtures, tests) were updated; whether `make
contracts-check` would pass (run it). Findings as BLOCKING, SHOULD FIX, NOTES.
```

`.claude/agents/aml-claims-checker.md`:

```markdown
---
name: aml-claims-checker
description: Checks NeonRadar documentation and typology files for uncited AML claims, wrong terminology, accusatory wording and unsafe naming of real people or companies. Use for changes under docs/, detect/typologies/ or README.md.
tools: Read, Grep, Glob
model: inherit
---
Read-only. For each changed documentation file:
- every factual AML statement cites a key that exists in docs/sources/bibliography.yaml;
- terminology matches docs/glossary.md;
- no accusatory wording about any entity (PHASE-1.md 7.1);
- real cases name as wrongdoers only institutions that admitted facts and individuals who
  were convicted; victims, publishers, courts and authorities may be named in those roles;
  everyone else is described by role; adjudicated facts are separated from allegations;
- typology files keep status draft unless a human approved them in the PR history.
Report findings as BLOCKING, SHOULD FIX, NOTES with file:line.
```

**`.mcp.json`** (project-scoped Neo4j MCP server, read-only; optional convenience for Claude to inspect the local graph):

```json
{
  "mcpServers": {
    "neo4j": {
      "type": "stdio",
      "command": "uvx",
      "args": ["neo4j-mcp-server@1.6.0"],
      "env": {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "${NEO4J_USER:-neo4j}",
        "NEO4J_MCP_PASSWORD": "${NEO4J_PASSWORD}",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true",
        "NEO4J_MCP_TELEMETRY": "false"
      }
    }
  }
}
```

The password comes from the environment of the process that runs Claude Code. Start VS Code from a terminal after `set -a; . ./.env; set +a`, or skip the MCP server. Claude Code asks for approval before using a project-scoped server for the first time. The server is GPL-3.0 and runs as a separate tool; never copy its binary into the repository.

**`scripts/test_hooks.sh`.** A self-test that pipes sample hook input into the hooks and prints PASS or FAIL per case, exiting non-zero on any failure:

- `guard-contracts.sh`: an edit to `ui/src/x.ts` and to `contracts/x.py` with no tag (both exit 0); in a temporary clone with a local tag `contracts-v1.0.0`, an edit to `contracts/x.py` (exit 2) and the same with `NR_ALLOW_CONTRACT_CHANGE=1` (exit 0).
- `guard_git.py`, run in a temporary repository on branch `p1/m1-4-local-stack` with `cwd` set in the input JSON. Exit 0: `git push -u origin p1/m1-4-local-stack`, `git push origin HEAD:p1/m1-4-local-stack`, `git push origin HEAD`, plain `git push`, `make check && git push -u origin p1/m1-4-local-stack`, `git -C . push origin p2/m2-1-loader`, `gh pr create --base main --title x`, `git status`, a heredoc commit (`git commit -m "$(cat <<'EOF'` with a multi-line message containing an apostrophe), a multi-line `gh pr comment 12 --body "..."` containing an apostrophe, `cat > notes.txt <<'EOF'` with a body line `it's a digit thing`, and a two-line command `uv run pytest -q` then `gh pr checks 7 --watch`. Exit 2: `git push origin main`, `git push origin p1/x:main`, `git push origin p1/x main`, `git push origin HEAD:refs/heads/main`, `git push origin +p1/x`, `git push --force-with-lease origin p1/x`, `git push -uf origin p1/x`, `git push origin --delete p1/x`, `git push origin :p1/x`, `git push --tags`, `FOO=1 git push origin main`, a two-line command whose second line is `git push origin main`, `bash -c 'git push origin main'`, `gh pr merge 12 --squash`, `gh api -X PUT repos/o/r/pulls/12/merge`, `gh repo edit --visibility public`; and on branch `main`, plain `git push` and `git push origin HEAD`.

**ADR-0011** (`docs/decisions/0011-ai-built-workflow.md`, status `proposed`; deciders: project lead and tech lead, who accept it in review): AI agents draft most code and documents; one milestone per pull request; humans review and merge; agent pull requests are labelled `agent` and name a human owner; the agent kit (this milestone) is the shared context; deterministic hooks and CI enforce what must never happen; the share of agent-drafted pull requests is measured and published at launch.

**Instructions.**

1. Plan first: list the files and how you will test the hooks without a real tag on the repository.
2. Write every file above. `chmod +x .claude/hooks/*.sh .claude/hooks/*.py scripts/test_hooks.sh`.
3. Do not create the tag `contracts-v1.0.0` on the real repository. Test the frozen case only in a temporary clone.
4. Claude Code reads hooks when a session starts, so in this session prove the hooks with `scripts/test_hooks.sh`; the operator check after merge confirms them in a fresh session. From then on, if a push you need is blocked, the push itself is wrong for this repository: fix the branch or the command, never the hook.

**Acceptance.**

```bash
bash scripts/test_hooks.sh                              # all PASS
python3 -c "import ast; ast.parse(open('.claude/hooks/guard_git.py').read(), feature_version=(3, 9))"
jq empty .claude/settings.json .mcp.json                 # valid JSON
test "$(wc -l < CLAUDE.md)" -lt 200
grep -l '^description:' .claude/skills/*/SKILL.md | wc -l    # prints 6
grep -l '^name:' .claude/agents/*.md | wc -l                 # prints 3
grep -L '^paths:' .claude/rules/*.md                          # prints nothing
```

Operator check after merge: open a new Claude Code session, type `/` and confirm `milestone`, `open-pr` and the other skills are listed; run `/hooks` and confirm the three hooks are active; ask "Which rules do you follow in this repository?" and check that the answer reflects `CLAUDE.md`; ask Claude to run `git push origin HEAD:main --dry-run` and confirm the hook blocks it.

**Review focus (humans).** Do the rules in `CLAUDE.md` match section 2? Would the hook and the deny rules really stop a merge, a force-push or a push to `main`? Does the guard hook block contract edits in the temporary-clone test?

---

### M1.3 Python workspace, tooling and the `neonradar` command

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; tech lead |
| Depends on | M1.2 |
| Branch | `p1/m1-3-workspace` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | No |
| ADR | ADR-0007 (toolchain) |

**Goal.** One command installs everything, one command checks everything, and every squad has its package skeleton.

**Deliverables.**

1. Root `pyproject.toml`: project `neonradar-workspace` (not published; `[tool.uv] package = false`), `requires-python = ">=3.14,<3.15"`, `dependencies = ["neonradar-cli"]` with `[tool.uv.sources] neonradar-cli = { workspace = true }` (so a plain `uv run` installs every member), `[tool.uv.workspace] members = ["contracts", "ingest", "graph", "detect", "copilot", "api", "cli"]`, dependency group `dev` with `ruff`, `mypy`, `pytest`, `pytest-cov`, `pre-commit`, `types-PyYAML`, `testcontainers[neo4j]`. Tool configuration:
   - ruff: `line-length = 100`, `target-version = "py314"`, rules `E`, `F`, `I`, `B`, `UP`, `SIM`, `RUF`, `S`; per-file ignores `S101` in tests and `S603`, `S607` in `scripts/` and `.claude/hooks/`; `per-file-target-version` `"scripts/*.py" = "py312"` and `".claude/hooks/*.py" = "py39"`, because those files run with a system Python (CI's Ubuntu `python3` is 3.12, macOS can be 3.9) and a 3.14 target lets the formatter write syntax older Pythons reject.
   - mypy: `strict = true`, `plugins = ["pydantic.mypy"]`, `files` set to the seven `src` directories.
   - pytest: markers `contract`, `integration`, `network`, `e2e`; `addopts = "-m 'not integration and not network and not e2e' --strict-markers --import-mode=importlib"`; `testpaths` the seven `tests` directories.
2. `.python-version` containing `3.14`.
3. Seven members, each with `pyproject.toml` (name `neonradar-<dir>`, version `0.1.0`, build backend `uv_build>=0.13.1,<0.14`), `src/neonradar_<dir>/__init__.py` with `__version__ = "0.1.0"`, `src/neonradar_<dir>/py.typed`, `tests/test_<dir>_version.py` (unique names across members), and a `CLAUDE.md` of at most 20 lines (purpose, owner squad, contracts it depends on, commands, traps). Member dependencies: `cli` depends on all other members (`[tool.uv.sources]` with `workspace = true`); `api`, `detect` and `graph` depend on `contracts`; `ingest` depends on `contracts`; `contracts` depends on `pydantic>=2.14,<3` from the start, because mypy loads the pydantic plugin.
4. `cli`: a typer application exposed as the `neonradar` script with `neonradar --version` and `neonradar doctor`. `doctor` checks and prints, one line each with OK, WARN or FAIL: Python version, uv version, Docker reachable, Compose version, `.env` present, ports 7474, 7687, 8000 and 5173 free or used by the NeonRadar stack, memory available to Docker (from `docker info`), ICU available (`pkg-config --exists icu-uc`). It exits 1 only on FAIL.
5. `Makefile` with these targets (recipes indented with a tab; targets that a later milestone fills print `available after M1.x` and exit 0):

| Target | Runs |
|---|---|
| `setup` | `uv sync --all-packages`, `uv run pre-commit install`, and `npm ci --prefix ui` when `ui/package.json` exists |
| `fmt` | `uv run ruff format .` and `uv run ruff check --fix .` |
| `lint` | `uv run ruff check .` and `uv run ruff format --check .` |
| `typecheck` | `uv run mypy` |
| `test` | `uv run pytest` |
| `test-int` | `uv run pytest -m integration` |
| `contracts`, `contracts-check` | filled by M1.7 |
| `check` | `lint typecheck test contracts-check`, plus the UI checks when `ui/package.json` exists |
| `hygiene` | filled by M1.6 |
| `up`, `down`, `reset`, `smoke`, `logs` | filled by M1.4 |
| `demo-mini`, `e2e` | filled by M1.9 |
| `gate-1` | filled by M1.12 |

6. `.pre-commit-config.yaml`:

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.17.1
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/astral-sh/uv-pre-commit
    rev: 0.13.1
    hooks:
      - id: uv-lock
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.30.1
    hooks:
      - id: gitleaks
```

7. `docs/decisions/0007-toolchain.md` (drafted as `proposed`; decider: tech lead): Python 3.14 with uv workspaces; Makefile as the developer entry point (works on macOS and Linux; Windows through the devcontainer); ruff, mypy strict, pytest, pre-commit; Node 24 with the create-vue 3.24 pins for the UI; reasons from `docs/research/2026-10-16/stack.md`.

**Acceptance.**

```bash
uv lock && uv sync --all-packages --locked
make check                              # lint, mypy, pytest all pass (contracts-check is a no-op until M1.7)
uv run neonradar --version              # prints 0.1.0
uv run neonradar doctor                 # prints one line per check; exits 0 unless a FAIL
uv run pre-commit run --all-files       # passes
```

**Review focus (humans).** Can a new intern run `make setup` and `make check` from a clean clone? Are the package boundaries the squads' directories?

---

### M1.4 Local stack: Neo4j in Docker Compose

| | |
|---|---|
| Squad, human owner | Graph and ER; graph squad mentor |
| Depends on | M1.3 |
| Branch | `p1/m1-4-local-stack` |
| Labels | `agent`, `phase-1`, `squad:graph` |
| Plan first | No |
| ADR | ADR-0002 (Neo4j 5.26 LTS) |

**Goal.** `make up` gives every developer the same healthy Neo4j with APOC and GDS, bound to localhost, with memory sized for their laptop and no outbound telemetry.

**Deliverables.**

1. `compose.yaml`:

```yaml
name: neonradar

services:
  neo4j:
    image: neo4j:5.26.32-community
    restart: unless-stopped
    ports:
      - "127.0.0.1:7474:7474"
      - "127.0.0.1:7687:7687"
    environment:
      NEO4J_AUTH: "neo4j/${NEO4J_PASSWORD:?Set NEO4J_PASSWORD in .env (at least 8 characters)}"
      NEO4J_PLUGINS: '["apoc", "graph-data-science"]'
      NEO4J_server_memory_heap_initial__size: "${NEO4J_HEAP:-2G}"
      NEO4J_server_memory_heap_max__size: "${NEO4J_HEAP:-2G}"
      NEO4J_server_memory_pagecache_size: "${NEO4J_PAGECACHE:-2G}"
      NEO4J_server_jvm_additional: "-XX:+ExitOnOutOfMemoryError"
      # Step 3 of the instructions adds the verified settings that switch off product analytics.
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - ./data/import:/import:ro
    mem_limit: "${NEO4J_MEM_LIMIT:-5g}"
    healthcheck:
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p \"$${NEO4J_AUTH#*/}\" 'RETURN 1' || exit 1"]
      interval: 5s
      timeout: 10s
      retries: 30
      start_period: 30s

volumes:
  neo4j_data:
  neo4j_logs:
```

2. `.env.example`:

```bash
# Copy to .env and fill in. .env is gitignored. Never commit it.
NEO4J_PASSWORD=change-me-to-something-long
# Memory profile "standard" (16 GB laptop). For "small" (8 GB laptop) use:
#   NEO4J_HEAP=1G  NEO4J_PAGECACHE=512M  NEO4J_MEM_LIMIT=2500m
NEO4J_HEAP=2G
NEO4J_PAGECACHE=2G
NEO4J_MEM_LIMIT=5g
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
# Companies House API key: only for the companies-house spike and loader
CH_API_KEY=
```

3. `graph/src/neonradar_graph/client.py`: a pydantic-settings model (`NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` default `neo4j`) with `env_file` set to the repository root's `.env` and `extra="ignore"` (the file also holds other keys); real environment variables win over `.env`, so the devcontainer's `NEO4J_URI=bolt://neo4j:7687` is kept. Every later settings object in the project follows this pattern. `get_driver()` returns a `neo4j` 6.x driver; `wait_until_ready(timeout_s=120)` calls `verify_connectivity()` with backoff. Dependencies of `graph`: `neo4j>=6.4,<7`, `pydantic-settings>=2.16,<3`.
4. CLI: `neonradar graph smoke` prints the Neo4j version and edition (`CALL dbms.components()`), `RETURN apoc.version()` and `RETURN gds.version()`, and exits 1 if any is missing.
5. Makefile targets: `up` (`docker compose up -d --wait neo4j`), `down`, `reset` (refuses unless `CONFIRM=yes`, then `docker compose down -v`), `smoke` (`uv run neonradar graph smoke`), `logs`.
6. `docs/architecture/local-stack.md`: the two memory profiles; Docker Desktop memory settings; how to open Neo4j Browser at http://localhost:7474; the GDS Community limits (4 cores, 3 models); how to reset.
7. `scripts/ensure_env.sh`: if `.env` is missing, copy `.env.example` to `.env` and replace the `NEO4J_PASSWORD` value with 32 random hexadecimal characters (`openssl rand -hex 16`, or Python's `secrets` module as a fallback); never print the password; do nothing if `.env` exists. `make setup` and `make up` call it.
8. `docs/decisions/0002-neo4j-5-26-lts.md` (drafted as `proposed`; decider: tech lead): options were the 2026.09 calendar release (Cypher 25, newer features, moves monthly) and 5.26.32 LTS (support until June 2028, APOC and GDS bundled, Cypher 5 well known to AI models); decision 5.26.32 with the forward-compatible Cypher subset; revisit when the 2026 LTS is released and GDS, APOC, the driver and neo4j-graphrag support it. Cite `docs/research/2026-10-16/neo4j.md` and `stack.md`.

**Instructions.**

1. Write the files, run `bash scripts/ensure_env.sh` (it creates `.env` with a generated password, which you must not print), then `make up` and `make smoke`.
2. Check whether GDS was installed from the jar inside the image or downloaded: `docker compose logs neo4j | grep -i -E "graph-data-science|graphdatascience.ninja"`. Expected for 5.26.32: installed from the bundled jar. If the logs show a download, add a named volume `neo4j_plugins:/plugins`, add a `make reset-plugins` target, document both, and record it as a deviation.
3. Telemetry: look up, in the Neo4j 5.26 Operations Manual configuration settings, the settings that control product analytics and outbound connections from the server and from Neo4j Browser (candidates to verify: `client.allow_telemetry` and `browser.allow_outgoing_connections`). Set each verified setting to `false` through its `NEO4J_` environment variable (dots become `_`, underscores become `__`). Neo4j validates configuration strictly, so a wrong name stops the container; that is the test. Record what you set, with the documentation URL, in the ADR.
4. Test the small profile once: set the small values, `make down && make up && make smoke`, then restore.

**Acceptance.**

```bash
make up                                   # returns 0 within 3 minutes
make smoke                                # prints Neo4j 5.26.32 community, APOC 5.26.x, GDS 2.13.x
docker compose port neo4j 7687            # prints 127.0.0.1:7687
docker inspect --format '{{.State.Health.Status}}' "$(docker compose ps -q neo4j)"   # healthy
make down && make up && make smoke        # data and plugins survive a restart
make check
```

**Review focus (humans).** Run `make up` and `make smoke` on your own laptop (one macOS and one Linux machine before Gate 1). Are the ports bound to localhost only? Which telemetry settings were found and set, and is the source linked?

---

### M1.5 Devcontainer and Codespaces

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; tech lead |
| Depends on | M1.4 |
| Branch | `p1/m1-5-devcontainer` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | No |
| ADR | none |

**Goal.** Nobody loses a day to their laptop. Windows users and weak machines get a ready environment with Python 3.14, ICU, Node 24, `gh`, Claude Code and Neo4j.

**Deliverables.**

1. `.devcontainer/Dockerfile`:

```dockerfile
FROM ghcr.io/astral-sh/uv:python3.14-trixie
RUN apt-get update \
 && apt-get install -y --no-install-recommends pkg-config libicu-dev build-essential git make jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --shell /bin/bash --uid 1000 dev \
 && mkdir -p /home/dev/.claude \
 && chown dev:dev /home/dev/.claude
USER dev
WORKDIR /workspaces/neonradar
```

The `.claude` folder is created in the image so that the named volume mounted there (below) starts out owned by `dev`; otherwise Claude Code could not save its login.

2. `.devcontainer/compose.dev.yaml`:

```yaml
# Used together with ../compose.yaml. With several Compose files, relative paths resolve
# from the folder of the first file (the repository root), not from this folder.
services:
  dev:
    build:
      context: .
      dockerfile: .devcontainer/Dockerfile
    command: sleep infinity
    volumes:
      - .:/workspaces/neonradar:cached
    environment:
      NEO4J_URI: bolt://neo4j:7687
      NR_TEST_NEO4J_URI: bolt://neo4j:7687
    depends_on:
      neo4j:
        condition: service_healthy
```

3. `.devcontainer/devcontainer.json`:

```json
{
  "name": "neonradar",
  "dockerComposeFile": ["../compose.yaml", "compose.dev.yaml"],
  "service": "dev",
  "runServices": ["dev", "neo4j"],
  "workspaceFolder": "/workspaces/neonradar",
  "remoteUser": "dev",
  "features": {
    "ghcr.io/devcontainers/features/node:2": { "version": "24" },
    "ghcr.io/devcontainers/features/github-cli:1": {},
    "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}
  },
  "mounts": [
    "source=neonradar-claude-config-${devcontainerId},target=/home/dev/.claude,type=volume"
  ],
  "containerEnv": {
    "CLAUDE_CONFIG_DIR": "/home/dev/.claude"
  },
  "hostRequirements": { "cpus": 4, "memory": "8gb" },
  "forwardPorts": ["neo4j:7474", "neo4j:7687", 8000, 5173],
  "initializeCommand": "bash scripts/ensure_env.sh",
  "postCreateCommand": "make setup"
}
```

Compose needs `.env` (for `NEO4J_PASSWORD`) before the containers start, so `initializeCommand` runs on the host first. `scripts/ensure_env.sh` copies `.env.example` to `.env` with a random 32-character password if `.env` does not exist, and does nothing otherwise. It needs bash on the host (macOS, Linux and Codespaces have it); Windows users without bash create `.env` by hand once, as `docs/architecture/devcontainer.md` explains.

4. `docs/architecture/devcontainer.md`: when to use it; VS Code "Dev Containers: Reopen in Container"; Codespaces quota (personal free tier: 120 core hours a month, which is 30 hours on a 4-core machine); use the small memory profile in Codespaces; Claude Code inside the container (sign in once; the volume keeps you signed in); `--dangerously-skip-permissions` only inside the container and only as the non-root `dev` user, and Auto mode is preferred. Limits to state plainly: the container has no Docker, so `make up`, Testcontainers-based integration tests, `make demo-mini` and `make e2e` run on the host, not inside it. Inside the container, Neo4j is already running as the `neo4j` service; run integration tests against it with `NR_TEST_NEO4J_URI` (preset) plus `NR_TEST_ALLOW_WIPE=1` when you accept that the tests wipe that database, and run the demo with `make demo-dev` (M1.9e), which needs no Docker.

**Acceptance.**

```bash
npx --yes @devcontainers/cli build --workspace-folder .
npx --yes @devcontainers/cli up --workspace-folder .
npx --yes @devcontainers/cli exec --workspace-folder . make check
npx --yes @devcontainers/cli exec --workspace-folder . uv run neonradar graph smoke
```

**Review focus (humans).** One Windows user and one Codespaces user open the project and run `make check` before Gate 1.

---

### M1.6 CI, quality gates and repository protection

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; release manager |
| Depends on | M1.3 |
| Branch | `p1/m1-6-ci` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | Yes |
| Size | exception (verbatim workflows from this spec) |
| ADR | none |

**Goal.** Every pull request is checked the same way, mechanically, before a human spends attention on it; `main` cannot be changed except by a reviewed, green pull request.

**Deliverables.**

1. `.github/workflows/ci.yml`. The jobs have no `name:` on purpose: GitHub reports each job under its id, and those ids are the required checks the protection script sets.

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
  workflow_dispatch:
permissions:
  contents: read
concurrency:
  group: ci-${{ github.ref }}
  cancel-in-progress: true

jobs:
  python:
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v7
      - name: ICU headers for PyICU
        run: sudo apt-get update && sudo apt-get install -y --no-install-recommends pkg-config libicu-dev
      - uses: astral-sh/setup-uv@v10.3.0
        with:
          enable-cache: true
      - run: uv python install 3.14
      - run: uv sync --all-packages --locked
      - run: uv run pre-commit run --all-files
      - run: make lint typecheck test contracts-check

  integration:
    runs-on: ubuntu-24.04
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v7
      - name: ICU headers for PyICU
        run: sudo apt-get update && sudo apt-get install -y --no-install-recommends pkg-config libicu-dev
      - uses: astral-sh/setup-uv@v10.3.0
        with:
          enable-cache: true
      - run: uv python install 3.14
      - run: uv sync --all-packages --locked
      - run: uv run pytest -m integration
        env:
          NR_NEO4J_IMAGE: neo4j:5.26.32-community

  ui:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-node@v7
        if: ${{ hashFiles('ui/package.json') != '' }}
        with:
          node-version: 24
          cache: npm
          cache-dependency-path: ui/package-lock.json
      - if: ${{ hashFiles('ui/package.json') != '' }}
        run: npm ci --prefix ui
      - if: ${{ hashFiles('ui/package.json') != '' }}
        run: npm run --prefix ui lint && npm run --prefix ui type-check && npm run --prefix ui test:unit -- --run && npm run --prefix ui build
```

2. `.github/workflows/pr-hygiene.yml`, a separate workflow so that it re-runs when a title or a label changes (a re-run job would otherwise keep the labels it started with):

```yaml
name: pr-hygiene
on:
  pull_request:
    types: [opened, edited, synchronize, reopened, labeled, unlabeled]
permissions:
  contents: read
concurrency:
  group: pr-hygiene-${{ github.event.pull_request.number }}
  cancel-in-progress: true

jobs:
  hygiene:
    runs-on: ubuntu-24.04
    timeout-minutes: 10
    env:
      PR_TITLE: ${{ github.event.pull_request.title }}
      PR_LABELS: ${{ toJson(github.event.pull_request.labels.*.name) }}
      BASE_REF: origin/${{ github.base_ref }}
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 0
      - name: Conventional title
        run: python3 scripts/check_pr_title.py "$PR_TITLE"
      - name: Size limit
        run: python3 scripts/check_pr_size.py --base "$BASE_REF" --labels "$PR_LABELS"
      - name: Frozen contract paths
        run: python3 scripts/check_contract_paths.py --base "$BASE_REF" --labels "$PR_LABELS"
      - name: Synthetic fixtures only
        run: python3 scripts/check_fixtures.py
      - name: Wording lint
        run: python3 scripts/check_wording.py
```

3. Hygiene scripts in `scripts/`, Python standard library only (they run on the runner's system Python 3.12; the per-file ruff target from M1.3 keeps their syntax compatible), each with `--help`, each exiting 1 with a clear message on failure, each with a unit test in `scripts/tests/`. Add `scripts/tests` to pytest's `testpaths` and `pythonpath = ["scripts"]`.
   - `check_pr_title.py`: matches `^(feat|fix|docs|test|refactor|build|ci|chore)(\([a-z0-9-]+\))?!?: .+$`.
   - `check_pr_size.py`: sums added plus deleted lines from `git diff --numstat <base>...HEAD`, excluding paths that match a glob in `.github/pr-size-exclude.txt` (`fnmatch` semantics, where `*` also matches `/`, and a leading `**/` also matches the top level); above 400 it fails, or only warns when `--labels` contains `size-exception`.
   - `check_contract_paths.py`: fails if the diff touches `contracts/` or `graph/schema/`, the tag `contracts-v1.0.0` exists, and the labels do not include `contract-change`.
   - `check_fixtures.py`: every `*.ftm.jsonl` under `data/fixtures/`, `contracts/examples/` and any `tests/fixtures/` has ids starting `syn-`, dataset `nr_synthetic` and `nr.synthetic: true`, except the files under `contracts/examples/c1/invalid/`, which break exactly one rule on purpose; every CSV fixture starts with the comment line `# synthetic: true`, or, for CSV files meant for Neo4j `LOAD CSV` (which cannot skip comment lines), has `synthetic` as its first header column with the value `true` on every row; no file under `data/` other than fixtures, `README.md` and `.gitkeep` files is tracked.
   - `check_wording.py`: scans the entity-facing text templates (the `wording` fields of `detect/typologies/*.yaml` and string literals in `detect/src/**/wording.py`) for the forbidden patterns listed in `contracts/wording/forbidden-terms.txt` (7.1); prints file, line and term. The disclaimers and general documentation are out of scope (they discuss money laundering as a subject). Until M1.7c creates the terms file, the script exits 0 with a notice.
4. `graph/tests/test_neo4j_smoke.py`, marked `integration`, so the integration job has a real test from the start (`pytest -m integration` exits with code 5 when nothing matches): start `Neo4jContainer` from `testcontainers.community.neo4j` with the image in `NR_NEO4J_IMAGE` (default `neo4j:5.26.32-community`) and `NEO4J_PLUGINS='["apoc", "graph-data-science"]'`, then assert that `RETURN 1`, `RETURN apoc.version()` and `RETURN gds.version()` answer. M1.7b moves it onto the shared fixture.
5. Makefile target `hygiene` running the same scripts locally against `origin/main` with `uv run --no-project python`. Labels come from `LABELS=` (comma-separated) when given, else from `gh pr view --json labels` when a pull request exists for the branch, else none; milestones with `Size: exception` run `make hygiene LABELS=size-exception` before their pull request exists.
6. `.github/workflows/claude-review.yml` (runs only when the repository variable `CLAUDE_REVIEW` is `on`, never on drafts or forks):

```yaml
name: claude-review
on:
  pull_request:
    types: [opened, synchronize, ready_for_review, reopened]
jobs:
  review:
    if: ${{ vars.CLAUDE_REVIEW == 'on' && github.event.pull_request.draft == false && github.event.pull_request.head.repo.full_name == github.repository }}
    runs-on: ubuntu-24.04
    timeout-minutes: 20
    concurrency:
      group: claude-review-${{ github.event.pull_request.number }}
      cancel-in-progress: true
    permissions:
      contents: read
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v7
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          # or: claude_code_oauth_token: ${{ secrets.CLAUDE_CODE_OAUTH_TOKEN }}
          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}
            You are the NeonRadar pre-review agent. Read CLAUDE.md and section 2 of the
            current docs/build/PHASE-<n>.md. Review only for: acceptance evidence present in
            the PR body; contract impact declared and correct; synthetic-only fixtures; no
            secrets; no accusatory wording; citations for AML claims; tests that would fail if
            the code were wrong; Cypher conventions. Skip style preferences.
            Post one top-level summary with `gh pr comment` and inline comments only for
            BLOCKING issues. Do not approve or request changes; humans do that.
          claude_args: |
            --max-turns 30
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)"
```

7. `.github/dependabot.yml`:

```yaml
version: 2
updates:
  - package-ecosystem: uv
    directory: "/"
    schedule: { interval: weekly }
    groups:
      python-minor-patch: { update-types: [minor, patch] }
  - package-ecosystem: npm
    directory: "/ui"
    schedule: { interval: weekly }
    ignore:
      - dependency-name: typescript
        update-types: [version-update:semver-major]
  - package-ecosystem: github-actions
    directory: "/"
    schedule: { interval: weekly }
  - package-ecosystem: pre-commit
    directory: "/"
    schedule: { interval: weekly }
  - package-ecosystem: docker-compose
    directory: "/"
    schedule: { interval: weekly }
    ignore:
      - dependency-name: neo4j     # upgrade by hand (LTS line and GDS pairing)
```

8. `scripts/setup_repo_protection.sh` (a human with admin rights runs it; Claude Code never does): requires a pull request for `main`, one approving review, code owner review, the status checks `python`, `integration`, `ui` and `hygiene` (the job ids), dismisses stale approvals, blocks force pushes and deletion; enables private vulnerability reporting, secret scanning with push protection, and CodeQL default setup, each through `gh api`. It prints what it changed and what it could not change.
9. `docs/build/ci.md`: what every check does, how to run it locally (`make check`, `make hygiene`), and the plan limitation below.

Plan limitation to state in `ci.md` and in the pull request: on a GitHub Free organisation, branch protection, rulesets and required code-owner reviews are not available for private repositories, and secret scanning push protection and CodeQL are free only for public repositories. If the repository stays private on a free plan until launch, the `guard_git.py` hook, the deny rules in `.claude/settings.json`, CODEOWNERS review requests, CI and team discipline are the controls until 20 November, and the script is run again on launch day after the repository becomes public.

**Acceptance.**

```bash
uv run pytest scripts/tests -q                 # hygiene script tests pass
make hygiene LABELS=size-exception            # passes; the size check only warns (this milestone is a size exception)
uv run --no-project --with pyyaml python -c "import sys, yaml; [yaml.safe_load(open(f)) for f in sys.argv[1:]]" \
  .github/workflows/ci.yml .github/workflows/pr-hygiene.yml .github/workflows/claude-review.yml .github/dependabot.yml
uv run pytest -m integration graph/tests/test_neo4j_smoke.py   # needs Docker
gh pr checks <this PR> --watch                 # python, integration, ui, hygiene all green
```

The operator then runs `bash scripts/setup_repo_protection.sh` and pastes its output into the pull request.

**Review focus (humans).** Do the required checks match the job ids? Does the size check exclude only documentation, generated files and fixtures? What did the protection script report as unavailable on your plan?

---

### M1.7 Contracts v1 (four sub-milestones)

The contracts are written as code plus documentation, proven by tests, and frozen at Gate 1. Each sub-milestone is its own pull request with the tech lead as required reviewer. Read section 5 in full before starting any of them.

#### M1.7a Record contract (C1) and dataset registry

| | |
|---|---|
| Squad, human owner | Tech lead (Ingestion and Graph squads review; the data steward must approve `contracts/datasets.yaml`) |
| Depends on | M1.3 |
| Branch | `p1/m1-7a-record-contract` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `squad:graph` |
| Plan first | Yes |
| ADR | ADR-0003 (FollowTheMoney as the record format) |

**Deliverables.**

1. `contracts/pyproject.toml` dependencies: add `followthemoney>=4.11,<5` and `pyyaml` to the `pydantic>=2.14,<3` that M1.3 added.
2. `contracts/src/neonradar_contracts/versions.py`: `RECORD = "1.0.0"`, `GRAPH_SCHEMA = "1.0.0"`, `API = "1.0.0"`, `ALERT = "1.0.0"`, `CONTRACTS = "1.0.0"`.
3. `contracts/src/neonradar_contracts/datasets.py`: `Dataset` model and `load_registry()` (cached), reading `contracts/datasets.yaml` (5.1, verbatim).
4. `contracts/src/neonradar_contracts/records.py`:
   - `NrExtension` (pydantic, `extra="forbid"`, the keys in 5.1);
   - `RecordIssue(rule: str, record_id: str | None, message: str)`;
   - `validate_record(data: dict) -> list[RecordIssue]` implementing R1 to R10 (R4 and R8 need the whole batch, so they are checked by `validate_batch`);
   - `validate_batch(records: Iterable[dict], strict: bool) -> list[RecordIssue]` (dangling references and account holders);
   - `iter_records(path) -> Iterator[dict]` (streams a `.ftm.jsonl` file, reports line numbers);
   - `Manifest` model (5.1) with `write_manifest()` computing SHA-256 and counts.
5. CLI: `neonradar contracts validate-records PATH... [--strict]` printing counts by schema and every issue as `RULE id: message`; exit 1 on any issue.
6. `contracts/examples/c1/demo.ftm.jsonl` and its manifest: the seven example lines from 5.1 plus the records they reference (`syn-co-0002` with its own account `syn-acct-0002` and holder ownership), so the file validates in strict mode.
7. `contracts/examples/c1/invalid/`: one file per rule, named `r1-bad-id.ftm.jsonl` to `r10-not-nfc.ftm.jsonl`, each failing with exactly its rule.
8. `contracts/C1-record.md`: section 5.1 as a standalone document, plus "how to write a loader that emits C1": create each entity with `ValueEntity(model[schema], {"id": <id per 4.4>, "datasets": [<slug>]})` (not `model.make_entity`, whose output has no `datasets`), add values with `.add(prop, value)`, write `json.dumps({**entity.to_dict(), "nr": {...}}, ensure_ascii=False)` one per line, then write the manifest.
9. `contracts/CHANGELOG.md`: `## 1.0.0 (unreleased)` listing C1.
10. Tests in `contracts/tests/test_records.py` and `test_datasets.py` (5.5), marked `contract`.
11. Makefile: `contracts-check` runs `uv run pytest -m contract` (extended by M1.7c and M1.7d).
12. `docs/decisions/0003-followthemoney-record-format.md` (drafted as `proposed`; decider: tech lead): FtM is the native format of OpenSanctions and the format of FtM tooling, it models ownership, control, directorship, payments and accounts already, and it keeps loaders independent from Neo4j; the `nr` extension covers the few gaps (channel, account kind, address roles, parsed share bands, consolidation); cite `sources-opensanctions-ftm-icij.md` part B.

**Acceptance.**

```bash
uv run neonradar contracts validate-records contracts/examples/c1/demo.ftm.jsonl --strict   # OK, 0 issues
for f in contracts/examples/c1/invalid/*.ftm.jsonl; do
  uv run neonradar contracts validate-records "$f" --strict && echo "SHOULD HAVE FAILED: $f"
done                                                    # prints nothing
make contracts-check && make check
```

**Review focus (humans).** Read three of the invalid examples: would a loader author understand from the message what to fix? Is anything in `nr` a disguised label (R9)? Data steward: are the licence, attribution, commercial-use and redistribution fields in `contracts/datasets.yaml` right? Approve them explicitly in the review, because they freeze at Gate 1 (GC-17). Also search the Companies House register for the example company names (Falcon Ridge Trading Ltd, the second example company, and Fenwhistle Holdings Ltd from 5.4, which replaced the name OD-12 forbids) and ask for a rename if any exists.

#### M1.7b Graph schema (C2) and migrations

| | |
|---|---|
| Squad, human owner | Tech lead (Graph and Detection squads review) |
| Depends on | M1.7a, M1.4 |
| Branch | `p1/m1-7b-graph-schema` |
| Labels | `agent`, `phase-1`, `squad:graph` |
| Plan first | Yes |
| ADR | ADR-0004 (graph schema v1) |

**Deliverables.**

1. `graph/schema/migrations/0001_init.cypher`, verbatim from 5.2.
2. `contracts/src/neonradar_contracts/graph.py`: the C2 mapping as data, not code: for each allowed FtM schema either `NodeMapping(labels=[...], properties={ftm_prop: graph_prop})` or `RelationshipMapping(type, source_prop, target_prop, properties, condition)`; plus `FLAG_LABELS`, `NODE_LABELS`, `RELATIONSHIP_TYPES`, and the special cases (Ownership to `HOLDS_ACCOUNT` when the asset is a `BankAccount`, to `CONSOLIDATES` when `nr.consolidation` is set, else `OWNS`; `addressEntity` to `HAS_ADDRESS`; `Sanction.entity` to `SUBJECT_OF`).
3. `graph/src/neonradar_graph/mapping.py`: pure functions `to_node_rows(records)` and `to_relationship_rows(records)` producing the parameter rows the loader will send (snake_case properties, `names`, `names_text`, `countries`, flags, ids per 5.2), with no database access.
4. `graph/src/neonradar_graph/migrate.py` and the CLI `neonradar graph migrate` (runner rules in 5.2).
5. `contracts/C2-graph-schema.md`: section 5.2 as a standalone document plus a Mermaid diagram of labels and relationship types (GitHub renders Mermaid).
6. Tests: `contracts/tests/test_graph_mapping.py` (contract); `graph/tests/test_mapping.py` (unit: every schema in the allowlist, the three Ownership cases, address roles, share bands, flags); `graph/tests/test_migrations.py` (integration, Testcontainers with `NR_NEO4J_IMAGE`, default `neo4j:5.26.32-community`): apply on an empty database, re-apply is a no-op, an edited migration is refused.
7. `graph/tests/conftest.py`: a session-scoped Neo4j fixture. If `NR_TEST_NEO4J_URI` is set, use that running database (faster locally, wiped before use only if it contains no `:Entity` nodes or `NR_TEST_ALLOW_WIPE=1`); otherwise start a Testcontainers Neo4j with APOC and GDS. Move M1.6's smoke test onto this fixture.
8. `docs/decisions/0004-graph-schema-v1.md` (drafted as `proposed`; decider: tech lead): labels mirror the FtM hierarchy; transactions are relationships between accounts (fast traversal and cycle queries; one `id` for evidence); flags only from source data; identity-first loading in Phase 1, resolve-then-merge with `:SourceRecord` evidence in Phase 2 so merges stay explainable and reversible; uniqueness constraints only because Community lacks the rest.

**Acceptance.**

```bash
make up
uv run neonradar graph migrate            # applies 0001_init
uv run neonradar graph migrate            # "nothing to apply"
docker compose exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "SHOW CONSTRAINTS YIELD name RETURN count(*) AS n"     # n = 22
uv run pytest -m integration graph/tests/test_migrations.py
make contracts-check && make check
```

(`NEO4J_PASSWORD` must be exported in the shell for the `cypher-shell` line: `set -a; . ./.env; set +a`.)

**Review focus (humans).** Graph squad: can you write the ownership-chain query from these tables alone? Detection squad: is every property a detector needs present, typed and indexed where it matters (`PAID.ts`, `Address.address_key`)?

#### M1.7c Alert contract (C4) and wording

| | |
|---|---|
| Squad, human owner | Tech lead (Detection and Copilot squads and a typology researcher review) |
| Depends on | M1.7a, M1.6 |
| Branch | `p1/m1-7c-alert-contract` |
| Labels | `agent`, `phase-1`, `squad:detect` |
| Plan first | No |
| ADR | ADR-0009 (alert object and wording) |

**Deliverables.**

1. `contracts/src/neonradar_contracts/alert.py`: `Alert` and its sub-models exactly as 5.4; `compute_alert_id(typology, detector_version, node_ids, edge_ids) -> str`; validators for the rules in the field table (headline length, `wording_class` is `synthetic_scenario` exactly when `data_flags.involves_real_entities` is false, `pattern_strength` range). Detectors compute `involves_real_entities` from evidence nodes, subjects and the holders of evidence accounts (5.4); add a helper for that in `neonradar_detect` in M1.9b.
2. `contracts/schemas/alert.v1.json`: generated by `neonradar contracts export` from `Alert.model_json_schema()`.
3. `contracts/examples/c4/circular_flow.json`: the example in 5.4 with real computed `alert_id` and hashes.
4. `contracts/wording/`: `standing-v1.txt`, `synthetic-demo-v1.txt`, `real-data-v1.txt` (texts from 7.1, verbatim) and `forbidden-terms.txt` (the patterns from 7.1, one regular expression per line, case-insensitive).
5. `detect/src/neonradar_detect/catalog.py`: `TypologyFile` pydantic model of the catalog shape and the rules under it in 5.4, `load_catalog()` reading `detect/typologies/*.yaml` (an empty folder gives an empty catalog), with a check that `status` is not `approved` unless `approved_by` is set. Plus the CLI `neonradar docs typology-index [--check]`, which renders `docs/typologies/README.md` (slug, name, tier, status, owner, whether a detector exists) from the catalog; `--check` fails when the file is out of date. M1.10b uses it.
6. `detect/src/neonradar_detect/wording.py`: `render_headline(typology: TypologyFile, wording_class, metrics) -> str` choosing `headline_structural` or `headline_synthetic`, formatting the metrics, and refusing output that matches a forbidden pattern.
7. CLI: `neonradar contracts export` (writes `contracts/schemas/*.json`; M1.7d adds the OpenAPI snapshot) and `neonradar contracts check` (exports to a temporary directory and fails on any difference). Makefile: `contracts` runs export; `contracts-check` runs `pytest -m contract` and `neonradar contracts check`.
8. `contracts/C4-alert.md`: section 5.4 plus the wording rules from 7.1.
9. Tests: `contracts/tests/test_alert.py`, `contracts/tests/test_wording.py` (5.5).
10. `docs/decisions/0009-alert-object-and-wording.md` (drafted as `proposed`; deciders: tech lead and typology researchers): alerts carry reproducible evidence (ids plus the query) so findings are checked rather than trusted; deterministic ids; `pattern_strength` rather than any risk or suspicion score; two wording classes and a lint, because a reference project for anti-corruption work must never accuse anyone by accident.

**Acceptance.**

```bash
make contracts && git diff --exit-code contracts/schemas/     # export is stable
uv run pytest -m contract contracts/tests/test_alert.py contracts/tests/test_wording.py
make contracts-check && make check && make hygiene
```

**Review focus (humans).** Read the three disclaimer texts and the forbidden list. Would any headline template the Detection squad might need be impossible under these rules?

#### M1.7d API contract (C3)

| | |
|---|---|
| Squad, human owner | Tech lead (Copilot and UI squads review) |
| Depends on | M1.7b, M1.7c |
| Branch | `p1/m1-7d-api-contract` |
| Labels | `agent`, `phase-1`, `squad:copilot`, `squad:ui` |
| Plan first | Yes |
| ADR | ADR-0008 (API gateway and OpenAPI snapshot) |

**Deliverables.**

1. `contracts/src/neonradar_contracts/api.py`: every model in 5.3.
2. `api/pyproject.toml` dependencies: `fastapi>=0.143,<0.144`, `uvicorn`, `neonradar-contracts`, `neonradar-graph`, `pydantic-settings`.
3. `api/src/neonradar_api/main.py`: `create_app()` with every route in 5.3 declared with its response model, status codes and parameter limits; problem-details error handling; CORS for `http://localhost:5173`; `GET /api/v1/health` implemented (Neo4j connectivity, versions); every other route returns `501` with a problem body naming the milestone that implements it (M1.9c, Phase 2 or Phase 4).
4. CLI: `neonradar api serve [--port 8000]` running uvicorn on `127.0.0.1`.
5. `neonradar contracts export` also writes `contracts/openapi/v1.json` (sorted keys, two-space indentation, stable output).
6. `contracts/C3-api.md`: section 5.3 plus how the UI generates its types.
7. Tests: `api/tests/test_openapi_contract.py` (contract: the app's OpenAPI equals the snapshot); `api/tests/test_routes.py` (unit: every route exists, parameter limits enforced with 422, 501 bodies are problem details).
8. `docs/decisions/0008-api-gateway.md` (drafted as `proposed`; decider: tech lead): one FastAPI service is the only way the UI and the copilot reach the graph; the OpenAPI snapshot is the contract; read-only queries only; bound to localhost.

**Acceptance.**

```bash
make contracts && git diff --exit-code contracts/        # stable
uv run neonradar api serve & sleep 3
curl -s http://127.0.0.1:8000/api/v1/health | jq -e '.status'
curl -s -o /dev/null -w '%{http_code}\n' -X POST http://127.0.0.1:8000/api/v1/copilot/ask \
  -H 'content-type: application/json' -d '{"question": "who owns syn-co-0001?"}'   # 501
kill %1
make contracts-check && make check
```

**Review focus (humans).** UI squad: does `Subgraph` give you everything Cytoscape needs? Copilot squad: does `CopilotAnswer` let the answer always carry its evidence subgraph and a refusal reason?

---

### M1.8 Data source spikes (five sub-milestones, run in parallel)

The plan's rule: every source is fetched end to end before any squad commits to it, and a source that fails its spike is dropped that day. Each spike is time-boxed to one session.

**Common rules for every spike.**

- Code: `ingest/src/neonradar_ingest/sources/<source>/` (client, mapping to C1) and the CLI `neonradar spike <source> ...`.
- Shared HTTP client `ingest/src/neonradar_ingest/http.py` (written by whichever spike lands first; the others reuse it): httpx with connect timeout 10 s and read timeout 60 s, explicit `follow_redirects`, User-Agent `NeonRadar/<version> (+https://neonradar.com)`, retries with exponential backoff on 429 and 5xx honouring `Retry-After`, a per-source rate limiter, and logging that never prints keys or authorization headers.
- Output: C1 records plus manifest in `data/cache/spikes/<source>/` (gitignored), validated with `neonradar contracts validate-records`. Never write spike output anywhere else. The output holds personal data: delete it after `access.spike_cache_days` (`neonradar spike clean` removes expired output; the spike report keeps only counts).
- Tests: unit tests with `httpx.MockTransport` and synthetic response bodies shaped like the documented responses (no real data in the repository); assert on the mapped records in code or against `*.expected.json` files, never committed `.ftm.jsonl` files with non-synthetic ids (the fixture check rejects them); one `@pytest.mark.network` test that runs the real spike (excluded from CI; run it manually and paste the output into the pull request).
- Report: `/spike-report <source>` writes `docs/data/spikes/<source>.md`. Counts and field names only; no personal data.
- Update the source's row in `DATA_SOURCES.md` and its `status` in `contracts/datasets.yaml` if the verdict changes it. Request review from the data steward.
- Research notes to read first: `docs/research/2026-10-16/sources-ch-gleif.md` (CH and GLEIF), `sources-opensanctions-ftm-icij.md` (OpenSanctions, FtM, ICIJ), `synthetic-docs-mcp.md` part A (synthetic).

#### M1.8a Companies House

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M1.7a, M1.4 |
| Branch | `p1/m1-8a-spike-companies-house` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `data-source`, `spike` |
| Plan first | No |
| Needs | `CH_API_KEY` in `.env` (`access.companies_house_key: available`); otherwise build everything with mocks and stop before the network run |

**Do.**

1. Command: `neonradar spike companies-house --company <number> [--max-pages 5]`. Default company for the spike: `01800000` (British Telecommunications, a large non-financial company whose LEI record names a GLEIF parent, so M1.8b can test the join and the parent mapping on the same entity; checked against the GLEIF API on 16 October 2026). The spike is a technical fetch test: its report contains counts and field names only and says nothing about the company.
2. Authentication: the key as the HTTP basic auth username with an empty password. Base URL `https://api.company-information.service.gov.uk`.
3. Rate limit: 600 requests per 5 minutes. Client-side limiter at 2 requests per second. On 429, wait until the window resets (use `X-Ratelimit-Reset` if present, else 300 seconds) and record it.
4. Fetch `/company/{n}`, `/company/{n}/officers` (paginate with `items_per_page` and `start_index`), `/company/{n}/persons-with-significant-control`.
5. Map to C1 (ids per 4.4, prefix `gbch`):
   - company to `Company` `gbch-co-<number>`: `name`, `registrationNumber`, `jurisdiction` (from Companies House `jurisdiction`: `england-wales`, `wales`, `scotland`, `northern-ireland`, `united-kingdom` and `england` map to `gb`), `status`, `legalForm` (from `type`), `incorporationDate`, `dissolutionDate`, `previousName`; registered office to `Address` with `nr.address_roles` `registered`;
   - officers: natural persons to `Person`, `corporate-*` roles to `Company` or `LegalEntity`, id `gbch-off-<officer id from links.officer.appointments>`; `birthDate` as `YYYY-MM` from month and year; `nationality`, `country` from `country_of_residence`; a `Directorship` per appointment with `role` (raw `officer_role`), `startDate`, `endDate`, `nr.is_nominee` for `nominee-*` roles; `nr.source_ref` the officer id;
   - PSCs: individual to `Person`, corporate and legal-person kinds to `Company` or `LegalEntity`; super-secure kinds skipped and counted; share and surplus-asset bands (`ownership-of-shares-25-to-50-percent` and the like) to `Ownership` with `percentage` "25-50", `nr.share_pct_min` 25, `nr.share_pct_max` 50; voting rights, right to appoint and significant influence to `Control` with `controlType` `voting`, `appointment` or `influence`; the raw values always in `nr.natures_of_control`; `-as-trust` and `-as-firm` suffixes kept in `role`; accept both spellings of the legal-person kind (the API documentation is inconsistent).
6. Record the identity-verification fields you see (`identity_verification_details`) in the report, but do not map them yet (Phase 2 decides).
7. Report verdict and the facts that matter for Phase 2: officer pages per company, time per company at the rate limit, how often names appear as `SURNAME, Forenames`, and the share of officers that are corporate.

**Acceptance.** Unit tests pass; `neonradar spike companies-house --company 01800000` (network, operator's key) prints counts and writes a manifest; `neonradar contracts validate-records data/cache/spikes/companies_house/*.ftm.jsonl --strict` reports 0 issues; the report exists; `make check`.

#### M1.8b GLEIF

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor |
| Depends on | M1.7a |
| Branch | `p1/m1-8b-spike-gleif` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `data-source`, `spike` |
| Plan first | No |
| Needs | Nothing (no key). GLEIF warns of brief interruptions between 19 October and 4 November 2026: if the API is down, finish with mocks and say so. |

**Do.**

1. Command: `neonradar spike gleif --lei 549300OWFMSO9NYV4H90 [--ch-number 01800000]`. Expected (checked on 16 October 2026): the record is BRITISH TELECOMMUNICATIONS LIMITED, `registeredAs` 01800000 at `RA000585`; its direct and ultimate parent are both BT GROUP PLC (`213800LRO7NS5CYQMN21`, registered as 04190816), whose own parent fields are reporting exceptions.
2. API base `https://api.gleif.org/api/v1`, no key, at most 60 requests per minute (limiter at 1 per second), `page[size]` at most 200.
3. Fetch the LEI record, its direct and ultimate parent (`/lei-records/{lei}/direct-parent`, `/ultimate-parent`, and the `*-relationship` and `*-reporting-exception` links; branch on which link is present), and a count of direct children.
4. The deterministic join: `/lei-records?filter[entity.registeredAs]=<ch number>&filter[entity.registeredAt]=RA000585,RA000586,RA000587`. Normalise the company number as in the research note (upper case, no spaces, digits zero-padded to 8).
5. Map to C1 (prefix `gleif`): `Company` `gleif-<LEI>` with `leiCode`, `name` (legal name), `alias` (other names and transliterated names), `jurisdiction`, `registrationNumber` (`registeredAs`), `status`; legal and headquarters addresses to `Address` with roles `registered` and `business`; parent relationships to `Ownership` (owner the parent, asset the child) with `nr.consolidation` `direct` or `ultimate`; reporting exceptions recorded in the manifest `notes`.
6. Report: whether `registeredAs` matched the Companies House number for the spike company; record counts; observed rate-limit and paging behaviour; the GB coverage figures from the research note, confirmed or corrected.

**Acceptance.** Unit tests (mocked) pass; the network run prints the record, each parent or reporting exception with its reason, and the join result; validation reports 0 issues; report exists; `make check`.

#### M1.8c ICIJ Offshore Leaks

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M1.7a |
| Branch | `p1/m1-8c-spike-icij` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `data-source`, `spike` |
| Plan first | No |

**Do.**

1. Command: `neonradar spike icij [--rows 1000] [--cache-dir ~/.cache/neonradar/icij]`.
2. `HEAD https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip` (follow redirects). Log `Content-Length`, `Last-Modified`, `ETag`, `Accept-Ranges`.
3. If the server supports byte ranges, read the zip's central directory and the first rows of each CSV member through a seekable HTTP range reader (sketch in the research note C.6), without downloading the whole archive. Otherwise download once into the cache directory (outside the repository), reuse it with `If-None-Match` and `If-Modified-Since`, and read members straight from the zip without extracting.
4. Read the first `--rows` rows of `relationships.csv`, `nodes-entities.csv`, `nodes-officers.csv`, `nodes-intermediaries.csv`, `nodes-addresses.csv`, `nodes-others.csv` (UTF-8). Count `(rel_type, lower(link))` pairs and distinct `sourceID` values.
5. Map a slice to C1 (prefix `icij`, ids `icij-<node_id>`): entities to `Company`; officers and others to `LegalEntity` (many officers are not people); intermediaries to `LegalEntity` plus `Representation` with `role` `intermediary`; `registered_address` to `Address` plus `addressEntity` with role `registered`; `officer_of` links classified with a lookup table into `Ownership` (shareholder, beneficiary, owner, beneficial owner), `Directorship` (director, secretary, nominee, signatory and similar) or `UnknownLink`; `same_*` and `similar*` links are not loaded (count them as resolution hints for Phase 2). Dates with format `%d-%b-%Y`. Names consisting only of question marks become empty.
6. Report: archive size and date, range support, files and headers actually found, the top 30 link values with counts, the classification table, and ICIJ's disclaimer verbatim. Re-fetch it from the FAQ (`https://offshoreleaks.icij.org/pages/faq`) before quoting: the two research notes differ in one word ("individuals" in `sources-opensanctions-ftm-icij.md` C.3, "persons" in `aml-domain.md` section 4).

**Acceptance.** Unit tests (mocked zip built in memory from synthetic rows) pass; the network run prints the header facts and counts; validation reports 0 issues; report exists; `make check`.

#### M1.8d OpenSanctions (gated by the licence decision)

| | |
|---|---|
| Squad, human owner | Ingestion; data steward |
| Depends on | M1.7a |
| Branch | `p1/m1-8d-spike-opensanctions` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `data-source`, `spike`, `needs-human-decision` (if blocked) |
| Plan first | No |

**Do.**

1. Read `access.opensanctions` in `project.yaml`. `evaluation` is valid only when `docs/data/licences/opensanctions.md` holds OpenSanctions' written confirmation; otherwise stop and ask (2.5).
2. Always: implement the parser against a synthetic FtM fixture shaped like `entities.ftm.json` (including `target`, `topics`, `referents`, a `Sanction` entity, an `Occupancy` and `Position` for a PEP, a `Family` link, and one schema unknown to FtM 4.11 that must be skipped with a count). Map `topics` to the flag labels in C2. Tests run offline.
3. Command: `neonradar spike opensanctions [--collection sanctions] [--rows 1000]`. It refuses with exit code 3 and the message "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md" unless `access.opensanctions` is `evaluation`, `licensed` or `exempt`.
4. If allowed: fetch `https://data.opensanctions.org/datasets/latest/<collection>/index.json` (follow redirects; the latest paths answer 307 since 17 August 2026) and log `version` and the resource checksum; stream the first `--rows` lines of `entities.ftm.json`; parse each with `followthemoney.ValueEntity.from_dict`; count schemata and topics. Write nothing to disk unless the access is `licensed` (then only to the cache).
5. Report: the licence position verbatim from the research note, the access decision and who made it, and (if run) the counts. If blocked, the report's verdict is "blocked on licence decision" with the options for Phase 2: obtain a licence or evaluation agreement, or evaluate official government sanctions lists as an alternative source (their licences to be verified in Phase 2).

**Acceptance.** Unit tests pass offline; with `access.opensanctions: none` the command exits 3 with the message; report exists; `make check`.

#### M1.8e Synthetic registry, activity and the join

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (the data steward reviews the names policy and ADR-0005) |
| Depends on | M1.7a, M1.6 |
| Branch | `p1/m1-8e-synthetic-join` |
| Labels | `agent`, `phase-1`, `squad:ingest`, `spike` |
| Plan first | Yes |
| ADR | ADR-0005 (synthetic data policy) |

**Goal.** Prove the project's central idea on a small scale: synthetic accounts and payments attached to entities that already exist in the graph, with a laundering-like scenario that touches only synthetic entities, reproducibly.

**Deliverables.**

1. `ingest/src/neonradar_ingest/synth/` (generator v0; Phase 3 builds the full one). Add `faker>=40.43,<41` and `numpy` to `ingest/pyproject.toml`. Records and label files must be byte-identical for the same seed; only the manifest's `created_at` may differ.
   - `rng.py`: one root seed, `numpy.random.SeedSequence` spawning an independent stream per component; iterate entities in sorted id order.
   - `names.py`: Faker 40.43+ person names for `ar_SA`, `ru_RU` and `en_GB` with explicit gender; strip honorifics (for example the Arabic "الدكتور"); filter every generated name against `denylist.txt`; optional extra script variants of the same person (Arabic, Cyrillic and Latin spellings carried as several `name` values).
   - `denylist.txt`: start with the real prominent family names found in Faker's `ar_SA` list (Al Saud, Bin Laden, Olayan, Kanoo, in Arabic and Latin spellings); reviewers extend it.
   - `companies.py`: company names composed from neutral word lists plus a legal form per jurisdiction (`Ltd`, `LLP`; `ООО`, `АО`; an Arabic form such as `ذ.م.م`); reject any name equal to a registry name already in the input records. For the committed demo-mini fixture, also check every generated company name against the Companies House search API (`/search/companies?q=`) when `CH_API_KEY` is available and reject exact matches after normalisation (case, punctuation, legal-form suffix); without a key, list the names in the pull request for the data steward to check. The demo notice says none of these companies exists, so this check must hold.
   - `registry.py`: the demo-mini synthetic registry (below).
   - `activity.py`: accounts for given entities (`NRSYN` plus 10 digits, never `iban` or `bic`); background activity at realistic volume (payroll fan-out, supplier payments, customer receipts, benign refunds and one loan drawdown and repayment, business-hour timestamps in UTC); and one `round_trip` scenario (4 hops, about 2 percent fee per hop, 1 to 2 days between hops) placed only among synthetic entities.
   - Labels go to separate CSV files: `labels/transactions.csv` (`tx_id, scenario_id, typology, step, role, is_illicit`) and `labels/scenarios.csv` (`scenario_id, typology, variant, is_lookalike, start_ts, end_ts, participants`), each starting with `# synthetic: true`.
2. Command `neonradar synth demo-mini --seed 20261023 --out data/fixtures/demo-mini/` producing `nr_synthetic-20261023-demo-mini.ftm.jsonl`, its manifest and the label files. Commit them (synthetic). Target size: 24 companies (mostly `gb`, a few `vg`, `cy` and `ae`), 30 people (a third with names in two or three scripts), 12 addresses (one shared by 8 companies), one formation agent representing 6 companies, a three-level ownership chain ending at a person, one synthetic person with topic `role.pep` and one synthetic company with topic `sanction` (to exercise flags), 2 synthetic bank branches with `cash_ledger` accounts, about 40 customer accounts, about 250 background payments, the `round_trip` scenario and the benign loan look-alike. About 450 records in total.
3. Command `neonradar spike synthetic-join --entities <records.ftm.jsonl> --seed <n>`: reads any C1 entity file (for example the Companies House spike output in `data/cache/`), adds accounts and background payments for those entities, and adds the scenario only among new synthetic entities. Output to `data/cache/spikes/synthetic_join/`.
4. Tests: same seed gives byte-identical output (compare SHA-256); no generated name contains a denylisted name; every `Payment` validates (R7) and every account has a holder (R8); no scenario transaction touches an entity whose id does not start with `syn-` (G1); labels never appear in records (R9).
5. `docs/decisions/0005-synthetic-data-policy.md` (drafted as `proposed`; deciders: tech lead and data steward): own seeded generator rather than AMLSim (unmaintained since 2022, Java 8 and an old Python, cannot attach to existing entities, lacks structuring and dormancy); real entities receive only background activity; scenarios among synthetic entities in the `syn` namespace; labels outside the graph; Faker with a denylist; no `mimesis` company names (they are real listed companies); external benchmarks (AMLworld, SAML-D) only as optional user downloads. Cite `synthetic-docs-mcp.md` part A.

**Acceptance.**

```bash
uv run neonradar synth demo-mini --seed 20261023 --out /tmp/a && uv run neonradar synth demo-mini --seed 20261023 --out /tmp/b
diff /tmp/a/*.ftm.jsonl /tmp/b/*.ftm.jsonl && diff -r /tmp/a/labels /tmp/b/labels && echo deterministic
uv run neonradar contracts validate-records data/fixtures/demo-mini/*.ftm.jsonl --strict
uv run neonradar spike synthetic-join --entities contracts/examples/c1/demo.ftm.jsonl --seed 7
make check && make hygiene
```

**Review focus (humans).** Read 20 generated names: any real public figures or companies? Is the scenario's money trail plausible enough for a demo? Does anything in the records give the scenario away (R9)?

---

### M1.9 Walking skeleton (five sub-milestones)

**Goal.** By Gate 1 the whole path works once, thinly, on synthetic data: fixture to graph to one detection to API to a UI that shows the alert with its evidence. Contracts are frozen only after running code has used them.

#### M1.9a Graph loader

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor |
| Depends on | M1.7b, M1.8e |
| Branch | `p1/m1-9a-graph-loader` |
| Labels | `agent`, `phase-1`, `squad:graph` |
| Plan first | No |

**Deliverables.**

1. `graph/src/neonradar_graph/loader.py` implementing the loader rules in 5.2 on top of `mapping.py` (M1.7b), returning a `LoadReport` (counts by label and relationship type, dangling references, skipped records, duration).
2. CLI `neonradar graph load PATH... [--strict/--no-strict]` (a directory loads every `*.ftm.jsonl` directly inside it; label CSVs are ignored), `neonradar graph stats` (counts through `CALL apoc.meta.stats()`), and `neonradar graph wipe --yes`, which refuses without `--yes` and deletes every node except `:SchemaMigration` with `MATCH (n) WHERE NOT n:SchemaMigration CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS`. `CALL { } IN TRANSACTIONS` only runs in an auto-commit transaction, so send it with `session.run()`; `driver.execute_query()` and `execute_write()` wrap queries in a transaction and fail with this statement.
3. Integration tests `graph/tests/test_loader.py` (idempotency: loading twice changes no count; dangling references counted; strict mode refuses invalid input and writes nothing) and `graph/tests/test_invariants.py` (I1 to I5 on demo-mini; I6 joins in M1.9b once alerts exist).

**Acceptance.**

```bash
make up && uv run neonradar graph migrate
uv run neonradar graph load data/fixtures/demo-mini/ --strict     # counts, 0 dangling, under 30 s
uv run neonradar graph load data/fixtures/demo-mini/ --strict     # identical counts
uv run neonradar graph stats
uv run pytest -m integration graph/tests/
make check
```

**Review focus (humans).** Open Neo4j Browser, run `MATCH p=(:Person)-[:OWNS]->{1,3}(:Company) RETURN p LIMIT 25`. Does the picture match the fixture's story?

#### M1.9b Detection runner and the circular-flow detector

| | |
|---|---|
| Squad, human owner | Typologies and Detection; detect mentor |
| Depends on | M1.7c, M1.9a |
| Branch | `p1/m1-9b-circular-flow` |
| Labels | `agent`, `phase-1`, `squad:detect`, `typology` |
| Plan first | Yes |

**Deliverables.**

1. `detect/typologies/circular_flow.yaml`: M1.10b-1 creates it from 5.4 with `detector: null`; this milestone sets `detector: neonradar_detect.detectors.circular_flow` and leaves `status` alone. If the file does not exist yet, create it verbatim from 5.4 with `status: draft`.
2. `detect/src/neonradar_detect/queries/circular_flow.cypher` and `detectors/circular_flow.py`. Query requirements:
   - pattern `MATCH p = (a:Account)-[t:PAID]->{2,6}(a)` (Phase 1 covers cycles that return to the same account; the variant the typology file also names, a return to another account of the same holder, is Phase 3 work) with the bounds taken from the catalog parameters (quantifier bounds cannot be query parameters in Cypher, so build one query per allowed length range from a fixed template, never from user input);
   - hops strictly time-ordered: `all(i IN range(0, size(t) - 2) WHERE t[i].ts < t[i + 1].ts)` (this also means each cycle is found once, from the account where it starts);
   - intermediate accounts distinct (a simple cycle);
   - total duration within `max_window_days` (compare `duration.inSeconds(t[0].ts, t[-1].ts).seconds`);
   - return ratio `t[-1].amount / t[0].amount` at least `min_return_ratio`;
   - `LIMIT` on results.
3. `pattern_strength` = 0.5 x return ratio + 0.3 x (1 minus duration over window) + 0.2 x min(1, (cycle length minus 1) / 4), clipped to [0, 1]. Document the formula in the detector's docstring and in `docs/typologies/circular-flow.md` as a heuristic for ordering the queue, not a risk score.
4. `detect/src/neonradar_detect/runner.py` and CLI `neonradar detect run [--typology <slug>] [--run-id <id>]` and `neonradar detect list`: runs detectors, builds C4 alerts (subjects: the origin account and its holders; `wording_class`, `involves_real_entities` and `synthetic_activity` computed by one helper from the evidence nodes, the subjects and the holders of every evidence account, as 5.4 defines them; explanation steps from the payments, one step per hop, text like "NRSYN0000000007 sent EUR 120,000 to NRSYN0000000012 on 2 March."), checks the headline, the explanation summary and every step against the forbidden patterns (7.1) with entity captions and account numbers masked out first (names are source data, not NeonRadar's wording) and fails the run on a match, writes `data/runs/<run_id>/alerts.jsonl` and `run.json`, and loads `:DetectionRun`, `:Alert`, `FLAGS`, `PRODUCED` idempotently (MERGE on ids).
5. Fixture with a known right answer, `detect/tests/fixtures/circular_flow/cases.ftm.jsonl` (synthetic, handcrafted, 20 to 40 records) and `expected.json`:
   - case A: 4-hop cycle, time-ordered, 6 days, return ratio 0.96: must be found;
   - case B: 3-hop cycle within limits: must be found;
   - case C: same shape as A but one hop earlier than the previous one: must not be found;
   - case D: cycle lasting 40 days: must not be found;
   - case E: return ratio 0.3: must not be found.
   - case F, built in the test code rather than committed (fixtures must stay synthetic): case A's cycle where the origin account's holder is a non-synthetic `Company` record `gbch-co-T0000001` named "Test Holder Ltd" in dataset `gb_companies_house`; the alert must be found with `wording_class: structural_pattern`, `involves_real_entities: true` and `synthetic_activity: true`, and its headline must use `headline_structural`.
6. Tests: integration test that loads the fixture, runs the detector and asserts the found set of edge-id lists equals `expected.json` exactly; alerts validate against C4; ids are stable across runs; for cases A and B `wording_class` is `synthetic_scenario`; on demo-mini, the labelled `round_trip` scenario's transactions (from `labels/transactions.csv`) appear together in one alert. Other alerts on demo-mini are allowed (the benign loan look-alike may form a two-hop cycle; that is the false positive the typology file documents). Add invariant I6 to `graph/tests/test_invariants.py`.

**Acceptance.**

```bash
uv run pytest -m integration detect/tests/
uv run neonradar detect run --typology circular_flow        # prints run id and alert count
uv run neonradar detect run --typology circular_flow        # same alert ids
make check && make hygiene
```

**Review focus (humans).** Typology researcher: does the query encode the definition, or only the shape? Mentor: are cases C, D and E really excluded for the right reason?

#### M1.9c API: Phase 1 endpoints

| | |
|---|---|
| Squad, human owner | Investigation Copilot (API); copilot mentor |
| Depends on | M1.7d, M1.9b, M1.10a |
| Branch | `p1/m1-9c-api` |
| Labels | `agent`, `phase-1`, `squad:copilot` |
| Plan first | No |

**Deliverables.** Implement every route marked "implemented" in 5.3 (health, meta, search, entity detail, network, alerts list and detail, typologies list and detail); the others stay 501. Add `neonradar-detect` to the API's dependencies (for `load_catalog()`). Notes:

- Search: `CALL db.index.fulltext.queryNodes('entity_names', $q, {limit: $limit}) YIELD node, score`; escape Lucene special characters in user input; filter by labels after the call. The full-text index covers `LegalEntity` and `Address` only, so when `labels` asks for `Account`, also match `Account.account_number` exactly (the `account_number` index).
- Files the API reads (`contracts/datasets.yaml`, `contracts/wording/`, `detect/typologies/`, `docs/typologies/`, and `docs/sources/bibliography.yaml` for the `Citation` titles and links) are found from one setting, `NR_REPO_ROOT` (default: the nearest parent directory of the working directory whose `pyproject.toml` has a `[tool.uv.workspace]` table). M1.9e's image sets it.
- Network: one fixed query per depth (1, 2, 3) selected in code; cap nodes at `max_nodes` and set `truncated`.
- Meta: datasets from `contracts/datasets.yaml` (including `licence_url`), each with `record_count` set to the number of nodes whose `datasets` contain its slug (0 when nothing from it is loaded), counts from `apoc.meta.stats()`, disclaimers from `contracts/wording/`.
- Alerts: read only from Neo4j (`:Alert` properties for filters, `payload` for detail; 5.2).
- Typologies: from `load_catalog()`, with the explainer Markdown from `docs/typologies/` when present.
- Every query read-only, parameterised, executed with `routing_=RoutingControl.READ`.
- Integration tests with FastAPI's test client against a Testcontainers Neo4j loaded with demo-mini and one detection run; every response validates against its model; unknown ids give a 404 problem.

**Acceptance.**

```bash
uv run pytest -m integration api/tests/
make contracts-check                     # the OpenAPI snapshot did not change
make check
```

**Review focus (humans).** Try a few searches in the browser at `http://127.0.0.1:8000/docs`. Are responses free of anything the contract did not promise?

#### M1.9d UI shell

| | |
|---|---|
| Squad, human owner | Explorer UI; UI mentor |
| Depends on | M1.7d (can start in parallel with M1.9c using the OpenAPI snapshot) |
| Branch | `p1/m1-9d-ui-shell` |
| Labels | `agent`, `phase-1`, `squad:ui` |
| Plan first | Yes |
| Size | exception (create-vue scaffold) |

**Deliverables.**

1. `ui/` scaffolded non-interactively with create-vue 3.24 (TypeScript, Router, Pinia, Vitest, Playwright, ESLint, Prettier; check `npm create vue@3.24.0 -- --help` for the exact flags), then pinned per 3.1: `typescript ~6.0.3`, `vue ^3.5.44`, `vite ^8.3.4`, `vitest ^4.1.12`; add `cytoscape ^3.34.4`, `cytoscape-fcose ^2.2.0`, and `openapi-typescript` (exact current version) as a dev dependency. Commit `ui/package-lock.json`.
2. Scripts: `gen:api` (`openapi-typescript ../contracts/openapi/v1.json -o src/api/schema.d.ts`), `lint`, `type-check`, `test:unit`, `build`, `test:e2e`. The scaffold's `lint` script may apply fixes (`--fix`); change it so `lint` only checks and fails on errors (CI relies on that), and add `lint:fix` for local use. Exclude the generated `src/api/schema.d.ts` from ESLint and Prettier, so the committed file stays exactly what `gen:api` writes. CI's `ui` job now runs.
3. Vite dev server proxy `/api` to `http://127.0.0.1:8000`.
4. Pages: Search (`/`), Entity (`/entities/:id`, network canvas with the fcose layout), Alerts (`/alerts`), Alert (`/alerts/:id`, evidence subgraph, explanation steps, typology reference with citations, metrics). Notices from `GET /meta` on every page: the standing disclaimer always, plus the synthetic demo notice when every loaded dataset (those with `record_count` above 0) is synthetic, otherwise the real data notice. The registry always lists the real sources, so never decide from the list alone. A "Synthetic" badge on synthetic nodes and alerts; next to a real entity, an alert with `synthetic_activity: true` says the pattern lies in generated background activity. Source-data flags appear as text badges in the 7.1 vocabulary, naming the dataset ("listed in <dataset> as sanctioned", "as a politically exposed person", "as a relative or close associate of a politically exposed person"); no other source topics are shown in Phase 1.
5. Pure functions with unit tests: `toCytoscapeElements(subgraph)`; the API client (mocked fetch); the notice logic (only synthetic datasets loaded shows the synthetic notice; any loaded real dataset shows the real data notice; registered but unloaded real datasets change nothing).
6. CSS: plain CSS variables, logical properties only, no external fonts or CDNs, works at 1280 px and at 390 px width. The NeonRadar visual identity arrives in Phase 5.

**Acceptance.**

```bash
npm ci --prefix ui && npm run --prefix ui gen:api && git diff --exit-code ui/src/api/schema.d.ts
npm run --prefix ui lint && npm run --prefix ui type-check && npm run --prefix ui test:unit -- --run && npm run --prefix ui build
make check
```

**Review focus (humans).** Is the disclaimer impossible to miss? Does any screen say more than the data supports?

#### M1.9e One command for the demo, and the end-to-end test

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; tech lead |
| Depends on | M1.9a to M1.9d |
| Branch | `p1/m1-9e-demo-mini` |
| Labels | `agent`, `phase-1`, `squad:docs`, `e2e` |
| Plan first | No |

**Deliverables.**

1. `.dockerignore` at the repository root: `.git`, `.env`, `.env.*`, `secrets/`, `data/cache/`, `data/runs/`, `.venv/`, `**/__pycache__/`, `ui/node_modules/`, `ui/dist/`, `.claude/worktrees/`. The `.env` file must never enter an image.
2. `api/Dockerfile`, built with the repository root as context: from `ghcr.io/astral-sh/uv:python3.14-trixie`; install `pkg-config libicu-dev build-essential` (PyICU builds from source); copy the repository; `uv sync --locked --no-dev --package neonradar-api` (workspace members stay editable, so files under `contracts/` and `detect/` resolve as in development); `ENV NR_REPO_ROOT=/app`; non-root user; `CMD` running `uvicorn neonradar_api.main:create_app --factory --host 0.0.0.0 --port 8000` through `uv run --no-sync`. Inside the container the API listens on all interfaces; Compose publishes it on `127.0.0.1` only.
3. `ui/Dockerfile`, built with the repository root as context (`context: .`, `dockerfile: ui/Dockerfile`, so the root `.dockerignore` keeps a host's `ui/node_modules` out of the image): Node 24 build stage copying `ui/` and running `npm ci` and `npm run build`, then an nginx stable Alpine image pinned to an exact tag you record; `ui/nginx.conf` serves the build with history fallback to `index.html` and proxies `/api/` to `http://api:8000`.
4. `compose.yaml`: services `api` and `ui` under the profile `app`, so `make up` still starts only Neo4j. `api`: build context `.` with `api/Dockerfile`, environment `NEO4J_URI=bolt://neo4j:7687`, `NEO4J_USER=neo4j`, `NEO4J_PASSWORD=${NEO4J_PASSWORD}`; port `127.0.0.1:8000:8000`; depends on a healthy `neo4j`; health check calling `/api/v1/health` with Python's `urllib` (do not rely on curl). `ui`: port `127.0.0.1:8080:80`; depends on a healthy `api`.
5. Makefile `demo-dev`, for the devcontainer and Codespaces where there is no Docker: against the running `NEO4J_URI`, migrate, refuse non-synthetic data as below, load demo-mini, run detection, then start `neonradar api serve` and the Vite dev server (`npm run --prefix ui dev`), and print the URLs (UI `http://localhost:5173`). `make e2e E2E_BASE_URL=http://localhost:5173` works against it. Makefile `demo-mini`: `scripts/ensure_env.sh`; `docker compose up -d --wait neo4j`; `neonradar graph migrate`; refuse to continue if the graph holds any `:Entity` with `synthetic = false` (unless `CONFIRM=yes`, which wipes first); load `data/fixtures/demo-mini/`; run detection; `docker compose --profile app up -d --build --wait`; print the URLs (UI `http://localhost:8080`, API docs `http://localhost:8000/docs`, Neo4j Browser `http://localhost:7474`) and the total time.
6. `ui/playwright.config.ts` rewritten for this project: no `webServer` block (the stack is already running), `baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8080'`, `headless: true`, Chromium only. `ui/e2e/demo-mini.spec.ts`: the standing disclaimer and the synthetic demo notice are visible; searching for the first word of the first `Company` name in `data/fixtures/demo-mini/*.ftm.jsonl` (the test reads the fixture, so it survives a regenerated fixture) finds that company; the alerts page lists at least one alert whose headline starts with "Synthetic scenario"; the alert page shows explanation steps and an evidence graph canvas; an entity page shows its network. Makefile `e2e` runs it.
7. CI: a separate workflow `.github/workflows/e2e.yml` (not a required check) triggered by pushes to `main`, `workflow_dispatch`, and `pull_request` with types `opened`, `synchronize`, `reopened` and `labeled`; its job runs only when `github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'e2e')`. Steps: checkout, ICU headers, `astral-sh/setup-uv@v10.3.0`, Python 3.14, `uv sync --all-packages --locked`, `actions/setup-node@v7` with Node 24, `npm ci --prefix ui`, `npx --prefix ui playwright install --with-deps chromium`, `make demo-mini`, `make e2e`; upload the Playwright report as an artifact when the job fails. Timeout 30 minutes.
8. `docs/quickstart.md` (Phase 1 edition): requirements, `make demo-mini`, what you see, how to stop and reset, memory and port troubleshooting.

**Acceptance.**

```bash
make demo-mini        # ends by printing three URLs and the elapsed time (target: under 5 minutes on a 16 GB laptop, first run included)
make e2e              # all Playwright tests pass
make check
```

**Review focus (humans).** Two people who did not build it run `make demo-mini` from a clean clone, one on macOS and one on Linux, and report the time and anything confusing.

---

### M1.10 Knowledge base seeds (three sub-milestones)

The agent drafts; humans verify. Everything here cites `docs/sources/bibliography.yaml`. Read `docs/research/2026-10-16/aml-domain.md` first.

#### M1.10a Wording, glossary, bibliography and the licensing ADR

| | |
|---|---|
| Squad, human owner | Docs; technical writer (data steward reviews ADR-0006) |
| Depends on | M1.6 |
| Branch | `p1/m1-10a-wording-glossary` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | No |
| ADR | ADR-0006 (data licensing) |

**Deliverables.**

1. `docs/sources/bibliography.yaml` with every entry in 7.3, in this shape (one entry per source; `extra_urls`, `note` optional):

   ```yaml
   version: 1
   entries:
     - key: fatf_pml_2018
       title: Professional Money Laundering
       publisher: FATF
       year: 2018
       url: https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf
       extra_urls: []
       verified: 2026-10-16
       note: Professional launderers, mule networks, proxy networks of shell company accounts.
   ```

2. `docs/sources/README.md`: how to cite. In Markdown, cite with the key in square brackets, for example `[fatf_pml_2018]`, one key per bracket; a document that cites ends with a `## Sources` section listing each key it used with title, publisher, year and link. In typology YAML files, keys go in `citations`.
3. `scripts/check_citations.py` (run as `uv run python scripts/check_citations.py docs/ detect/typologies/ README.md`; it needs PyYAML, which the workspace provides): in Markdown, outside fenced code blocks and inline code, every match of `\[([a-z][a-z0-9]*(?:_[a-z0-9]+)+)\](?![(\[])` must be a bibliography key (this pattern skips links, task boxes and ordinary bracketed words); in `detect/typologies/*.yaml`, every `citations` entry must be a key; it skips `docs/research/` and `docs/plan/` (source material kept as delivered); it prints unknown keys with file and line and exits 1 if any. Unit test in `scripts/tests/`. Add it to `make hygiene` and as a step in CI's `python` job (the `hygiene` job is standard library only).
4. `docs/glossary.md` from 7.4.
5. `docs/wording.md`: the three disclaimers, the README limitations text, the vocabulary and the forbidden patterns from 7.1, with the reasons.
6. `docs/decisions/0006-data-licensing.md` (status `proposed`; the data steward changes it to `accepted` when approving the pull request; deciders: data steward and project lead): the loaders-only rule; the licence table from 3.3; the OpenSanctions position, its free-access groups and the recorded `access.opensanctions` decision; the ODbL obligations for ICIJ data (notice on produced works, share-alike and a machine-readable offer for a publicly used derived database); never publish a database merging sources; personal data: Companies House officers and PSCs, ICIJ officers and OpenSanctions persons are personal data, OpenSanctions crime-related topics need particular care, whoever loads them is a controller under UK or EU data protection law, and spike output is deleted after `access.spike_cache_days`.
7. `DATA_SOURCES.md`: final draft with attribution texts and the notes above.

**Acceptance.** `uv run python scripts/check_citations.py docs/` passes; the `aml-claims-checker` subagent reports no BLOCKING findings; `make hygiene` and `make check` pass.

#### M1.10b Typology catalog drafts (three pull requests of five)

| | |
|---|---|
| Squad, human owner | Typologies and Detection; typology researchers |
| Depends on | M1.10a, M1.7c |
| Branches | `p1/m1-10b1-typologies`, `p1/m1-10b2-typologies`, `p1/m1-10b3-typologies` |
| Labels | `agent`, `phase-1`, `squad:detect`, `typology` |
| Plan first | No |

**Batches.**

| Pull request | Typologies |
|---|---|
| M1.10b-1 | `circular_flow` (YAML from 5.4 with `detector: null`, unless M1.9b already created it, plus the explainer), `structuring`, `rapid_pass_through`, `layering_chain`, `fan_in_collection` |
| M1.10b-2 | `fan_out_distribution`, `dormant_reactivation`, `shell_chain`, `formation_agent_cluster`, `mass_registration_address` |
| M1.10b-3 | `recycled_directors`, `sanctions_exposure`, `pep_exposure`, `cash_commingling`, `trade_based_ml` |

**Deliverables per typology.** Run `/typology-draft <slug>` to produce `detect/typologies/<slug>.yaml` (shape 5.4, `status: draft`, `owner` the first handle in `people.typology_researchers` unless the project lead assigned another, tier, citations and synthetic support from 7.2, `detector: null` and the empty fields the 5.4 note allows) and `docs/typologies/<slug-with-hyphens>.md` (plain-language explainer: what it is, how it looks in the graph, red flags from the sources, typical false positives, whether synthetic data can show it, sources). Start from the research note `aml-domain.md` section 2, which has a verified entry for every core typology; for the split typologies (`formation_agent_cluster`, `recycled_directors`, `pep_exposure`, `mass_registration_address`) use its entries (g), (h) and (i).

Batch 1 also creates `docs/typologies/_explainer-template.md`. Every batch regenerates the catalog index `docs/typologies/README.md` with `neonradar docs typology-index` (from M1.7c) instead of editing it by hand; when a parallel batch merged first, merge `main` into the branch and regenerate.

**Acceptance.** `uv run python -c "from neonradar_detect.catalog import load_catalog; c = load_catalog(); print(len(c))"` prints the running total; no file changed in this pull request has `status: approved`; `uv run neonradar docs typology-index --check` passes; `scripts/check_citations.py` passes; `aml-claims-checker` reports no BLOCKING findings; `make check`.

**After merge (humans).** Assignment 2 (M1.11b) has one person check and correct each draft against its sources. Typology researchers then review those corrections and set `status: approved` and `approved_by` when satisfied. Gate 1 needs all 15 drafts merged and `circular_flow` approved (its detector already exists). Phase 3 implements a detector only after its typology is approved, so aim to approve every `core` typology by Wednesday 28 October.

#### M1.10c Cases, reading list, architecture overview, proposed ADRs

| | |
|---|---|
| Squad, human owner | Docs; technical writer |
| Depends on | M1.10a |
| Branch | `p1/m1-10c-cases-reading` |
| Labels | `agent`, `phase-1`, `squad:docs`, `learning` |
| Plan first | No |
| ADR | ADR-0010 (proposed), ADR-0012 (proposed) |

**Deliverables.**

1. `docs/learning/cases/README.md` and one note per case in 7.5, each with a Mermaid diagram that uses roles, not names, the adjudicated-versus-alleged section, and sources.
2. `docs/learning/reading-list.md`: the plan's reading list by sprint (7.5 end). Link only to official pages you can open; otherwise give the title without a link and mark it "link to be added".
3. `docs/architecture/overview.md`: section 4 plus links to the four contract documents.
4. `docs/decisions/0010-copilot-local-template-first.md` (proposed; for Phase 4): offline only (Ollama), a library of parameterised question templates first, free text-to-Cypher only behind read-only checks, refusal rather than guessing, every answer returns its evidence subgraph.
5. `docs/decisions/0012-docs-site.md` (proposed; for Phase 6): VitePress (Vue-native, local search, GitHub Pages workflow; native right-to-left is merged but not yet released) versus Astro Starlight (full right-to-left and Arabic search today); Material for MkDocs is in maintenance mode. Cite `synthetic-docs-mcp.md` part B.

**Acceptance.** `scripts/check_citations.py` passes; `aml-claims-checker` reports no BLOCKING findings; Mermaid blocks render in GitHub's preview (operator check); `make check`.

---

### M1.11 Team kits (two sub-milestones)

#### M1.11a Onboarding and learning kit (Assignment 1)

| | |
|---|---|
| Squad, human owner | Docs; community manager |
| Depends on | M1.4, M1.6 |
| Branch | `p1/m1-11a-onboarding` |
| Labels | `agent`, `phase-1`, `squad:docs`, `learning` |
| Plan first | No |

**Deliverables.**

1. `data/fixtures/onboarding/companies-20.csv`: synthetic, made for `LOAD CSV`, so it carries the synthetic marker as its first column (M1.6 fixture rule) instead of a comment line. Header `synthetic,company_id,company_name,jurisdiction,incorporated_on,director_id,director_name,registered_address,parent_company_id`; 20 rows, each starting with `true`, with ids like `onb-co-01` and `onb-p-01`, invented names from neutral word lists, and a design that makes two-hop questions interesting (shared directors, one shared address, a parent chain of three).
2. `docs/team/assignment-1.md` (due `schedule.assignment_1_due`): copy the CSV into `data/import/` (mounted read-only into Neo4j at `/import`); in Neo4j Browser at `http://localhost:7474`, load it with `LOAD CSV WITH HEADERS FROM 'file:///companies-20.csv' AS row` into the labels `OnbCompany`, `OnbPerson`, `OnbAddress` with relationships `DIRECTS`, `REGISTERED_AT`, `PARENT_OF` (these onboarding labels are deliberately separate from the real schema); write one query that traverses at least two hops; add it under your handle in `docs/team/first-queries.md`; open a pull request; be ready to explain every line. AI help is allowed; the pull request and the explanation are yours.
3. `docs/team/first-queries.md`: the format (one `## @handle` section per person, holding exactly one fenced `cypher` block and two or three lines on what the query finds and why it needs two hops) and one example section, `## @example`.
4. `neonradar onboarding check`: loads the CSV with a reference loader into the `Onb*` labels (idempotent), runs every query in `first-queries.md` read-only with a 10-second timeout, and prints per handle: ran, rows returned, or the error. `neonradar onboarding reset` removes the `Onb*` nodes. Makefile `onboarding-check`.
5. `docs/learning/README.md` (why logs exist; three to five lines a week; honest confusion is the most valuable content), `docs/learning/_template.md`, `docs/learning/skills-self-assessment.md` (the eight skills from the plan, scores 1 to 5 at start and end), `docs/learning/teach-back.md` (the plan asks for six recorded sessions of thirty minutes with everyone presenting at least once: Thursdays 22 Oct, 29 Oct, 5 Nov, 12 Nov and 19 Nov, plus one more the project lead schedules, or the 15 Oct session if it took place; a rota table with two or three presenters per session for the community manager to fill; recording and "good ones become documentation").
6. `docs/team/roles.md`: squads, cross-cutting roles and names from `project.yaml`.
7. Optional, with the operator's approval: one issue per handle in `people.interns`, "Assignment 1: @handle", assigned to that person, created with `gh issue create`.

**Acceptance.** `make up && make onboarding-check` runs the example query; `make check`; `make hygiene` (the CSV passes the fixture check).

#### M1.11b Assignment 2 kit

| | |
|---|---|
| Squad, human owner | Typologies and Detection; typology researchers |
| Depends on | M1.10b-1, M1.10b-2, M1.10b-3 |
| Branch | `p1/m1-11b-assignment-2` |
| Labels | `agent`, `phase-1`, `squad:detect`, `learning` |
| Plan first | No |

**Deliverables.** `docs/team/assignment-2.md` (due `schedule.assignment_2_due`): a table of the 15 typologies in 7.2 with an empty assignee column (the project lead fills it, one person per typology); the task, which is to read the primary sources cited for that typology, check the agent's draft explainer sentence by sentence against them, fix what is wrong, add what is missing with citations, and open a pull request under their own name; a review checklist for the typology researchers (every claim traced to a cited page, terminology from the glossary, no accusatory wording, false positives realistic); and the rule that typology status changes only through a researcher's approval. Optional (operator approval): one issue per assignee.

**Acceptance.** Links resolve to existing files; `make check`.

---

### M1.12 Gate 1 check and the Phase 1 report

| | |
|---|---|
| Squad, human owner | Release manager; tech lead decides Gate 1 |
| Depends on | Everything else in Phase 1 |
| Branch | `p1/m1-12-gate-1` |
| Labels | `agent`, `phase-1`, `squad:docs` |
| Plan first | No |

**Deliverables.**

1. `cli/src/neonradar_cli/gate.py` and `neonradar gate check --phase 1`: one line per check in section 8 (`GC-01` to `GC-17`) with PASS, FAIL or MANUAL and the evidence (file, count, command). Checks that need Docker or `gh` report MANUAL with the reason when those are unavailable. It never creates tags, approves anything or edits other people's files. Makefile `gate-1`. Unit tests for the checks that only read files.
2. `docs/build/reports/phase-1.md`: what was built (milestones and pull requests), metrics (merged pull requests; share labelled `agent`, from `gh pr list --state merged --json labels`; median CI duration; `make demo-mini` time), deviations collected from `PROGRESS.md`, risks still open, decisions needed for Phase 2 (sanctions source and licence, officer fetching strategy under the Companies House rate limit, entity resolution thresholds, whether to bulk-load with `neo4j-admin import`), and the inputs the Phase 2 spec needs.

**Acceptance.** `make gate-1` runs and every non-MANUAL check passes or is explained in the report; `make check`.

---

## 7. Knowledge base reference

Milestones M1.1, M1.7c, M1.8e, M1.9, M1.10 and M1.11 point here. Texts marked **verbatim** are copied exactly. Everything else is source material: before a statement goes into project documentation, the agent checks it against the cited source (the research note `docs/research/2026-10-16/aml-domain.md` quotes most of them with page or section references), and a human approves it.

### 7.1 Wording

**Standing disclaimer** (verbatim; `contracts/wording/standing-v1.txt`). Shown near the top of the README, on every UI page that shows entities or alerts, and served by `GET /api/v1/meta`.

```text
NeonRadar is an educational, open-source tool that finds structural patterns in synthetic or public data. A pattern match is not evidence of money laundering, corruption or any other wrongdoing. There are legitimate reasons for almost every structure shown here, including holding companies, shared registered agents, professional directors, payment intermediaries and cash businesses. Where public data is used, many people and entities share the same or similar names, and source registers contain errors. Nothing here suggests or implies that any identifiable person or entity has broken the law. NeonRadar is not a certified compliance system and does not make anyone compliant with anything. If you find an error in NeonRadar, tell us and we will correct it; errors in source data can only be corrected by the source, and we will tell you where to report them.
```

**Synthetic demo notice** (verbatim; `contracts/wording/synthetic-demo-v1.txt`). Shown when every loaded dataset is synthetic, and in every screenshot and recording of the demo.

```text
Synthetic data. Every company, person, address, account and payment in this demonstration was generated by NeonRadar, and none of them exists. Patterns that resemble money laundering were planted on purpose to show how such structures look in a graph, next to ordinary activity that only looks similar. Detection results on synthetic data say nothing about how NeonRadar would perform on real data.
```

**Real data notice** (verbatim; `contracts/wording/real-data-v1.txt`). Shown whenever any loaded dataset has `synthetic: false`.

```text
This view includes records from public sources (company registers, the GLEIF index, the ICIJ Offshore Leaks Database, which is built from leaked files, and, where licensed, sanctions and PEP lists), listed with their licences on the Data sources page. Records about real people and companies are shown as their source published them and may be out of date. NeonRadar adds no allegations: any payment activity shown next to a real entity is synthetic background activity, and a pattern that touches a real entity is a structural observation only. Names can match the wrong person or company, so confirm identities with addresses, dates or official identifiers before drawing any conclusion. These records can include personal data, and whoever loads them is responsible for handling it lawfully.
```

**README limitations text** (verbatim; the "Limitations" section of `README.md`, M1.1). It carries the three statements the plan requires in the README.

```text
Synthetic transactions are not real money laundering: every planted scenario is invented, and so is every payment in the demo. Detection rates measured on synthetic data say nothing about how NeonRadar would perform on real data. NeonRadar is not a certified compliance system and makes no one compliant with any law or regulation.
```

The disclaimers follow the pattern public graph tools use: legitimate uses exist, inclusion or a pattern match does not imply wrongdoing, and identity and data errors are possible and corrections are welcome ([icij_faq], [opensanctions_glossary], [opencorporates_terms], [openownership_register_terms]; quotes in `aml-domain.md` section 4, to be re-fetched before quoting).

**Vocabulary for entity-facing text** (alert headlines, summaries and steps, UI labels, and from Phase 4 the copilot's answers):

| Write | Never write |
|---|---|
| "structural pattern present", "matches the graph pattern of <typology name>" | "money laundering", "suspicious activity" |
| "funds returned to the originating account", "transfers", "payments" | "laundered funds", "dirty money" |
| "listed in <dataset> as sanctioned", "as a politically exposed person", "as a relative or close associate of a politically exposed person" (flags come from source data; no other source topics are shown next to entities) | "sanctioned criminal", "corrupt official" |
| "shares a registered address with 14 other companies" | "shell company", "front company" (about a specific entity) |
| "pattern strength" | "risk score", "suspicion score", "likelihood of laundering" |
| "synthetic scenario" (only when the alert's `wording_class` is `synthetic_scenario`: every evidence node, subject and evidence-account holder is synthetic, 5.4) | "laundering case", "the launderer" |
| "linked to", "holds an account that received" | "accomplice", "mule", "fraudster" |

Explainers may use domain terms such as "shell company chains", because they describe a pattern, not an entity. The display name of any typology that has a detector must pass the lint, because alert and UI text say "matches the graph pattern of <name>".

**Forbidden patterns** (verbatim; `contracts/wording/forbidden-terms.txt`; one regular expression per line, matched case-insensitively; lines starting with `#` are comments):

```text
# NeonRadar wording lint v1: entity-facing templates must not match any line below
\blaunder\w*
\blaundromat\w*
\bcriminal\w*
\bcrimes?\b
\bguilty\b
\bfraud\w*
\bsuspic\w*
\bsuspect\w*
\billicit\w*
\billegal\w*
\bdirty\s+money\b
\bcorrupt\w*
\bbrib\w*
\bterroris\w*
\bmules?\b
\bshell\s+compan\w*
\bfront\s+compan\w*
\bconceal\w*
\bevad\w*
\bevasion\b
\brisk[\s-]+scor\w*
\baccomplice\w*
\bwrongdo\w*
```

The lint applies to NeonRadar's own entity-facing wording: typology `wording` templates, string literals in `detect/src/**/wording.py`, rendered alert text (headline, summary and steps, with entity captions and account numbers masked out), and from Phase 4 the copilot's answer templates. It does not apply to the disclaimers, typology names and explainers, the glossary, case notes or other documentation, which discuss money laundering as a subject and follow the documentation rules below. Phase 5 adds Arabic equivalents when the UI is translated.

**Documentation rules** (also in `.claude/rules/aml-docs.md`):

1. Every factual AML statement cites a key from 7.3. Quote sources in quotation marks with the key; otherwise paraphrase and cite.
2. Use the terms in 7.4. "Beneficial owner" means a natural person only.
3. Real cases name as wrongdoers only institutions that admitted facts and individuals who were convicted (give the court level). Victims, publishers, courts and authorities may be named in those roles. Everyone else is described by role. Separate what was adjudicated from what is alleged, and give the date the status was checked.
4. Never call a real, named company a shell, front or mule account. Describe the structure instead.
5. A red flag or indicator is a reason to look closer, not evidence. FFIEC Appendix F says its red flags "are not all-inclusive" and warns that a red flag alone does not prove criminal activity ([ffiec_appendix_f]).

**Synthetic name denylist seed** (verbatim; `ingest/src/neonradar_ingest/synth/denylist.txt`). Faker's `ar_SA` surname list contains real, prominent family names; synthetic people must never carry them. One entry per line; the generator compares after Unicode NFC normalisation and case folding, and rejects a generated full name that contains any entry. Reviewers add any other name they recognise as a prominent real person or family.

```text
# Real prominent family names found in Faker's ar_SA data (research note synthetic-docs-mcp.md, part A)
آل سعود
Al Saud
بن لادن
Bin Laden
Binladin
العليان
Olayan
كانو
Kanoo
```

In synthetic-join mode (M1.8e) the generator also rejects any generated person or company name equal, after the same normalisation, to a name already present in the input records. Company names come from neutral word lists plus a legal form; never from `mimesis`, whose company lists are real listed companies.

### 7.2 Typology catalog

Fifteen typologies: ten `core` (Phase 3 builds a detector and a labelled synthetic scenario for each), four `extended` (detectors if Phase 3 has capacity), one `explainer_only`. The research entries are the lettered subsections of `aml-domain.md` section 2.

| # | Slug | Name | Tier | Research entry | Synthetic support | Detector |
|---|---|---|---|---|---|---|
| 1 | `structuring` | Structuring (smurfing) below reporting thresholds | core | (a) | high | Phase 3 |
| 2 | `rapid_pass_through` | Rapid pass-through (funnel or transit accounts) | core | (b) | high | Phase 3 |
| 3 | `layering_chain` | Layering through chains of transfers | core | (c) | high | Phase 3 |
| 4 | `circular_flow` | Round-tripping or circular flows | core | (d) | high | Phase 1 (M1.9b) |
| 5 | `fan_in_collection` | Fan-in to a collection account | core | (e) | high | Phase 3 |
| 6 | `fan_out_distribution` | Fan-out distribution from one account | core | (f) | high | Phase 3 |
| 7 | `dormant_reactivation` | Dormant account reactivation followed by high velocity | core | (j) | high | Phase 3 |
| 8 | `shell_chain` | Layered company ownership with nominee directors | core | (g) | medium | Phase 3 |
| 9 | `mass_registration_address` | Mass registration addresses | core | (h) | high | Phase 3 |
| 10 | `sanctions_exposure` | Sanctions exposure through indirect ownership or control | core | (i) | high | Phase 3 |
| 11 | `formation_agent_cluster` | Companies clustered around one formation agent | extended | (g) | medium | Phase 3 if capacity |
| 12 | `recycled_directors` | Recycled and professional directors | extended | (h) | high | Phase 3 if capacity |
| 13 | `pep_exposure` | Exposure to politically exposed persons through ownership, control, family or associates | extended | (i) | high | Phase 3 if capacity |
| 14 | `cash_commingling` | Cash-intensive business commingling | extended | (l) | medium | Phase 3 if capacity |
| 15 | `trade_based_ml` | Trade-based money laundering (over- and under-invoicing) | explainer_only | (k) | low | none |

Per typology: the `citations` to start from, the graph pattern in C2 terms, and the benign look-alikes that the explainer must describe and the Phase 3 generator must produce. Parameter values are starting points for the typology researcher, not facts from the sources.

1. **`structuring`.** Citations: `cfr_31_1010_314`, `ffiec_appendix_g`, `ffiec_appendix_f`, `fatf_pml_2018`, `fincen_fin_2014_a005`, `fincen_fin_2025_a003`, `europol_efecta_2023`. Pattern: many `PAID` edges with `channel = 'cash_deposit'` (from `cash_ledger` accounts) into one customer `Account`, or into several accounts with the same holder, within a short window, each amount just below a threshold parameter (default 10,000 with a 10 percent band, after the US reporting threshold described in FIN-2014-A005), often through several branches, with a daily total above the threshold. Look-alikes: cash businesses banking daily takings, deposit caps set by insurers or cash-in-transit contracts, fixed weekly savings.
2. **`rapid_pass_through`.** Citations: `fincen_fin_2014_a005`, `fatf_egmont_tbml_indicators_2021`, `fatf_cyber_fraud_2023`, `ffiec_appendix_f`, `fatf_egmont_concealment_2018`. Pattern: an `Account` whose inbound `PAID` total within a window leaves again through outbound `PAID` within hours or a few days (dwell-time parameter), keeping a small residual; inbound from several unrelated accounts, outbound to few beneficiaries. Look-alikes: payment service providers, payroll bureaus, escrow and client accounts, marketplace settlement and treasury sweep accounts.
3. **`layering_chain`.** Citations: `fatf_faq`, `fatf_pml_2018`, `fatf_egmont_concealment_2018`, `fincen_fin_2006_g014`, `europol_efecta_2023`, `wolfsberg_payment_transparency_2023`. Pattern: a time-ordered path of three or more `PAID` hops through accounts held by different `LegalEntity` nodes, with short dwell times, amounts shrinking slightly at each hop or split and merged again, and intermediate holders with little other activity, often sharing a registered address, an agent or a director. Look-alikes: intra-group treasury flows, multi-tier supply chains, correspondent banking hops.
4. **`circular_flow`.** Citations: `fatf_egmont_tbml_indicators_2021`, `fatf_egmont_concealment_2018`, `ffiec_appendix_f`, `fatf_pml_2018`. Pattern and parameters: 5.4 and M1.9b. Look-alikes: refunds and reversals, loan drawdown and repayment, foreign exchange hedging legs, intra-group cash pooling.
5. **`fan_in_collection`.** Citations: `fatf_cyber_fraud_2023`, `fincen_fin_2025_a003`, `fincen_fin_2014_a005`, `ffiec_appendix_f`, `fatf_pml_2018`, `europol_money_muling`, `egmont_best_cases_2024`. Pattern: one `Account` receiving `PAID` from many person-held accounts that had no earlier relationship with it or with each other, within a short window, often from recently opened accounts (`opening_date`), followed by onward transfers or cash withdrawals. A ring variant uses GDS weakly connected components or Louvain over recent `PAID` edges. Look-alikes: charities and donation drives, crowdfunding, landlords, clubs, small online sellers, school fee accounts.
6. **`fan_out_distribution`.** Citations: `fincen_fin_2006_g014`, `ffiec_appendix_f`, `fatf_pml_2018`, `fatf_cyber_fraud_2023`. Pattern: one `Account` sending `PAID` to many accounts in a short window, with similar or round amounts, to recipients without earlier relationship, followed by cash withdrawals or a second layer of transfers. Look-alikes: payroll runs, supplier batches, dividend, benefit and insurance payouts, refunds after a cancelled event.
7. **`dormant_reactivation`.** Citations: `ffiec_appendix_f`, `fatf_egmont_concealment_2018`, `fatf_cyber_fraud_2023`, `fatf_tcsp_2010`. Pattern: an `Account` with no `PAID` edges for a long gap (parameter, default 180 days) followed within days by a burst of inbound and outbound volume, often soon after a new `DIRECTOR_OF` or `OWNS` relationship on the holder (start dates); the company variant is a newly incorporated or long-dormant company that suddenly moves large sums. Look-alikes: seasonal businesses, account holders returning from abroad, inheritances and property sales, genuine restarts and acquisitions.
8. **`shell_chain`.** Citations: `fatf_egmont_concealment_2018`, `fatf_bo_legal_persons_2023`, `fatf_tcsp_2010`, `fatf_corporate_vehicles_2006`, `star_puppet_masters_2011`, `fincen_fin_2006_g014`, `europol_shadow_money_2021`. Pattern: an `OWNS` chain of two or more company layers, often across jurisdictions, ending at a person, at a company with no recorded owner, or looping back; nominee directorships (`DIRECTOR_OF.is_nominee`) or directors with many appointments; companies in the chain that move money but show no payroll or supplier pattern. Look-alikes: lawful holding structures, special purpose vehicles, funds with corporate directors, joint ventures, start-ups not yet trading.
9. **`mass_registration_address`.** Citations: `fatf_egmont_concealment_2018`, `fatf_egmont_tbml_indicators_2021`, `fincen_fin_2006_g014`, `fatf_tcsp_2010`. Pattern: an `Address` with many incoming `HAS_ADDRESS {role: 'registered'}` edges (parameter); stronger when companies at that address pay each other. Look-alikes: registered agents and corporate service firms, serviced offices, law and accounting firms, and clusters created by address normalisation errors. The generator must include legitimate mass-registration addresses at realistic frequency.
10. **`sanctions_exposure`.** Citations: `ofac_50_percent_2014`, `fatf_glossary`, `fatf_bo_legal_persons_2023`, `fatf_pf_sanctions_evasion_2025`, `fatf_egmont_concealment_2018`. Pattern: `OWNS` paths (at most 6 hops) from `:Sanctioned` nodes to the subject. Report each sanctioned owner's effective share (the sum over its paths of the product of shares along each path, computed for both share bounds to give a range) as a teaching metric, not as the OFAC test. The OFAC rule aggregates all blocked owners, and an entity owned 50 percent or more by blocked persons is itself treated as blocked, so its holdings count in full rather than being multiplied down ([ofac_50_percent_2014]); an OFAC-style flag must pass blocked status down the chain from owner to owned entity, toward the subject. It is a United States rule, used as an illustration. The typology researcher confirms both readings against the examples in the guidance. `CONTROLS` and `DIRECTOR_OF` links create exposure without ownership. Look-alikes: name-matching errors, minority stakes, delisted parties, diffuse shareholding, lawful state-owned counterparties.
11. **`formation_agent_cluster`.** Citations: `fatf_tcsp_2010`, `fatf_egmont_concealment_2018`, `fatf_corporate_vehicles_2006`, `star_puppet_masters_2011`. Pattern: one agent with `REPRESENTS` edges to many companies, or one formation agent's registered address, with incorporation dates in bursts and shared nominee directors or secretaries, plus payments among those companies. Look-alikes: company formation is a lawful business, and most companies an agent forms are ordinary.
12. **`recycled_directors`.** Citations: `fatf_egmont_concealment_2018`, `fincen_fin_2006_g014`, `europol_shadow_money_2021`. Pattern: a director with many `DIRECTOR_OF` edges (parameter), appointments that start and end in bursts, relatives of a controller (`FAMILY_OF`) as directors, and payments between companies that share the director. Look-alikes: professional directors in fund jurisdictions, corporate secretaries, directors across one corporate group.
13. **`pep_exposure`.** Citations: `fatf_peps_2013`, `fatf_glossary`, `fatf_recommendations_2026`, `fatf_egmont_concealment_2018`. Pattern: paths of at most 4 hops from a `:PEP` or `:RCA` person through `FAMILY_OF`, `ASSOCIATE_OF`, `OWNS`, `CONTROLS` or `DIRECTOR_OF` to the subject. PEP measures are preventive; being a PEP is not wrongdoing. Look-alikes: homonyms, people long out of office, ordinary family relationships.
14. **`cash_commingling`.** Citations: `ffiec_cash_intensive`, `europol_efecta_2023`, `egmont_100_cases`, `fatf_pml_2018`, `fatf_cash_transport_2015`, `ffiec_appendix_f`. Pattern: a company account whose `cash_deposit` volume is far above peers with the same `sector`, deposited on days unrelated to trading, with outflows to owners or related parties rather than to suppliers and payroll. Needs sector benchmarks; the generator documents its calibration assumptions. Look-alikes: genuinely busy or growing cash businesses, seasonal peaks, a new branch.
15. **`trade_based_ml`.** Citations: `fatf_egmont_tbml_2020`, `fatf_egmont_tbml_indicators_2021`, `fincen_fin_2014_a005`, `fincen_fin_2025_a003`, `fatf_pml_2018`. Pattern: price, quantity and quality misrepresentation can only be seen with invoices, shipments and price benchmarks, which C2 does not model; payment-only proxies (third-party payments, circular routing, round amounts) are weak. Explainer only: it teaches why payment data alone cannot detect this typology.

### 7.3 Bibliography

`docs/sources/bibliography.yaml` starts with these entries (checked on 15 or 16 October 2026 as `aml-domain.md` describes; where a row says a source was verified only indirectly, or a title still needs confirming, write that in the entry's `note`). Keys are lowercase snake case with at least one underscore; dated sources end with the year.

| Key | Title | Publisher | Year | URL |
|---|---|---|---|---|
| `fatf_recommendations_2026` | International Standards on Combating Money Laundering and the Financing of Terrorism and Proliferation: The FATF Recommendations (updated June 2026) | FATF | 2026 | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Fatf-recommendations.html |
| `fatf_glossary` | FATF Glossary (web version of the General Glossary) | FATF | living | https://www.fatf-gafi.org/glossary/ |
| `fatf_faq` | Frequently asked questions: How is money laundered? | FATF | living | https://www.fatf-gafi.org/en/pages/frequently-asked-questions.html |
| `fatf_bo_legal_persons_2023` | Guidance on Beneficial Ownership of Legal Persons | FATF | 2023 | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Legal-Persons.html |
| `fatf_bo_legal_arrangements_2024` | Guidance on Beneficial Ownership and Transparency of Legal Arrangements | FATF | 2024 | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Guidance-Beneficial-Ownership-Transparency-Legal-Arrangements.html |
| `fatf_egmont_concealment_2018` | Concealment of Beneficial Ownership (Annex E: indicators, extra URL) | FATF and Egmont Group | 2018 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/Concealment-beneficial-ownership.html ; https://egmontgroup.org/wp-content/uploads/2021/10/FATF-Egmont-Concealment-beneficial-ownership-annex-E.pdf |
| `fatf_pml_2018` | Professional Money Laundering | FATF | 2018 | https://www.fatf-gafi.org/content/dam/fatf-gafi/reports/Professional-Money-Laundering.pdf.coredownload.pdf |
| `fatf_tcsp_2010` | Money Laundering Using Trust and Company Service Providers | FATF | 2010 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/Moneylaunderingusingtrustandcompanyserviceproviders.html |
| `fatf_corporate_vehicles_2006` | The Misuse of Corporate Vehicles, Including Trust and Company Service Providers (existence verified; quote only after a manual download) | FATF | 2006 | https://fatf-gafi.org/content/dam/fatf-gafi/reports/Misuse%20of%20Corporate%20Vehicles%20including%20Trusts%20and%20Company%20Services%20Providers.pdf.coredownload.inline.pdf |
| `fatf_egmont_tbml_2020` | Trade-Based Money Laundering: Trends and Developments | FATF and Egmont Group | 2020 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-trends-and-developments.html |
| `fatf_egmont_tbml_indicators_2021` | Trade-Based Money Laundering: Risk Indicators | FATF and Egmont Group | 2021 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/Trade-based-money-laundering-indicators.html |
| `fatf_transparency_bo_2014` | Guidance on Transparency and Beneficial Ownership (verified through the FSB index, extra URL) | FATF | 2014 | http://www.fatf-gafi.org/media/fatf/documents/reports/Guidance-transparency-beneficial-ownership.pdf ; https://www.fsb.org/2014/10/guidance-on-transparency-and-beneficial-ownership/ |
| `fatf_bo_best_practices_2019` | Best Practices on Beneficial Ownership for Legal Persons (verified through the FSB index, extra URL) | FATF | 2019 | http://www.fatf-gafi.org/publications/methodsandtrends/documents/best-practices-beneficial-ownership-legal-persons.html ; https://www.fsb.org/2019/10/best-practices-on-beneficial-ownership-for-legal-persons/ |
| `fatf_peps_2013` | FATF Guidance: Politically Exposed Persons (Recommendations 12 and 22) | FATF | 2013 | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/Peps-r12-r22.html |
| `fatf_cyber_fraud_2023` | Illicit Financial Flows from Cyber-Enabled Fraud | FATF, INTERPOL and Egmont Group | 2023 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/illicit-financial-flows-cyber-enabled-fraud.html |
| `fatf_cyber_fraud_2026` | Cyber-Enabled Fraud - Digitalisation and ML/TF/PF Risks | FATF | 2026 | https://www.fatf-gafi.org/content/fatf-gafi/en/publications/Methodsandtrends/cyber-enabled-fraud-digitalisation-ml-tf-pf-risks.html |
| `fatf_pf_sanctions_evasion_2025` | Complex Proliferation Financing and Sanctions Evasion Schemes | FATF | 2025 | https://www.fatf-gafi.org/en/publications/Financingofproliferation/complex-proliferation-financing-sanction-evasion-schemes.html |
| `fatf_va_update_2026` | Seventh Targeted Update on Implementation of the FATF Standards on Virtual Assets/VASPs | FATF | 2026 | https://www.fatf-gafi.org/en/publications/Fatfrecommendations/targeted-updated-virtualassets-vasps-2026.html |
| `fatf_cash_transport_2015` | Money Laundering Through the Physical Transportation of Cash (with MENAFATF; year from the FATF catalogue) | FATF and MENAFATF | 2015 | https://www.fatf-gafi.org/en/publications/Methodsandtrends/Ml-through-physical-transportation-of-cash.html |
| `egmont_100_cases` | FIUs in Action: 100 Cases from the Egmont Group (no date printed; about 2000) | Egmont Group | 2000 | https://fincen.gov/sites/default/files/shared/fiuinaction.pdf |
| `egmont_best_cases_2024` | Best Egmont Cases: Financial Analysis Cases 2021-2023 | Egmont Group | 2024 | https://egmontgroup.org/wp-content/uploads/2024/09/EGMONT_2021-2023-BECA-III_FINAL.pdf |
| `egmont_fiu` | Financial Intelligence Units | Egmont Group | living | https://egmontgroup.org/about/financial-intelligence-unit |
| `europol_efecta_2023` | European Financial and Economic Crime Threat Assessment 2023: The Other Side of the Coin | Europol | 2023 | https://www.europol.europa.eu/cms/sites/default/files/documents/The%20Other%20Side%20of%20the%20Coin%20-%20Analysis%20of%20Financial%20and%20Economic%20Crime%20(EN).pdf |
| `europol_shadow_money_2021` | Shadow Money - The International Networks of Illicit Finance | Europol | 2021 | https://www.europol.europa.eu/cms/sites/default/files/documents/Shadow%20money%20%E2%80%93%20the%20international%20networks%20of%20illicit%20finance_PUBLIC_0.pdf |
| `europol_money_muling` | Money Muling (public awareness and prevention guide) | Europol | living | https://europol.europa.eu/operations-services-and-innovation/public-awareness-and-prevention-guides/money-muling |
| `wolfsberg_payment_transparency_2023` | Wolfsberg Group Payment Transparency Standards 2023 | Wolfsberg Group | 2023 | https://wolfsberg-group.org/news/50 |
| `wolfsberg_correspondent_2022` | Financial Crime Principles for Correspondent Banking | Wolfsberg Group | 2022 | https://wolfsberg-group.org/resources/203/91 |
| `unodc_iff_2011` | Estimating illicit financial flows resulting from drug trafficking and other transnational organized crimes | UNODC | 2011 | https://unodc.org/lpomex/es/publicaciones/documentos/crimen/Illicit_financial_flows_2011_web.html |
| `fincen_fin_2014_a005` | FinCEN Advisory FIN-2014-A005: Update on U.S. Currency Restrictions in Mexico: Funnel Accounts and TBML | FinCEN | 2014 | https://www.fincen.gov/resources/advisories/fincen-advisory-fin-2014-a005 |
| `fincen_fin_2006_g014` | FinCEN Guidance FIN-2006-G014: Potential Money Laundering Risks Related to Shell Companies | FinCEN | 2006 | https://www.fincen.gov/resources/statutes-regulations/guidance/potential-money-laundering-risks-related-shell-companies |
| `fincen_fin_2025_a003` | FinCEN Advisory FIN-2025-A003: Use of Chinese Money Laundering Networks by Mexico-Based Transnational Criminal Organizations | FinCEN | 2025 | https://www.fincen.gov/system/files/2025-08/FinCEN-Advisory-CMLN-508.pdf |
| `star_puppet_masters_2011` | The Puppet Masters: How the Corrupt Use Legal Structures to Hide Stolen Assets and What to Do About It | StAR (World Bank and UNODC) | 2011 | https://star.worldbank.org/sites/star/files/puppetmastersv1.pdf |
| `ffiec_appendix_f` | BSA/AML Examination Manual, Appendix F: Money Laundering and Terrorist Financing Red Flags | FFIEC | living | https://bsaaml.ffiec.gov/manual/Appendices/07 |
| `ffiec_appendix_g` | BSA/AML Examination Manual, Appendix G: Structuring | FFIEC | living | https://bsaaml.ffiec.gov/manual/Appendices/08 |
| `ffiec_cash_intensive` | BSA/AML Examination Manual: Cash-Intensive Businesses | FFIEC | living | https://bsaaml.ffiec.gov/manual/RisksAssociatedWithMoneyLaunderingAndTerroristFinancing/26 |
| `cfr_31_1010_314` | 31 CFR 1010.314: Structured transactions (Legal Information Institute copy) | US Code of Federal Regulations | living | https://www.law.cornell.edu/cfr/text/31/1010.314 |
| `ofac_50_percent_2014` | Revised Guidance on Entities Owned by Persons Whose Property and Interests in Property Are Blocked | OFAC, US Treasury | 2014 | https://ofac.treasury.gov/media/6186/download |
| `openownership_thresholds` | Beneficial ownership in law: Definitions and thresholds (thresholds) | Open Ownership | living | https://www.openownership.org/en/publications/beneficial-ownership-in-law-definitions-and-thresholds/thresholds/ |
| `eba_qa_2022_6622` | Single Rulebook Q&A 2022_6622 (reproduces Directive (EU) 2015/849, Article 3(6)) | European Banking Authority | 2022 | https://www.eba.europa.eu/single-rule-book-qa/qna/view/publicId/2022_6622 |
| `icij_faq` | Offshore Leaks Database: frequently asked questions | ICIJ | living | https://offshoreleaks.icij.org/pages/faq |
| `opensanctions_glossary` | OpenSanctions glossary | OpenSanctions | living | https://www.opensanctions.org/docs/glossary |
| `opencorporates_terms` | OpenCorporates terms of use | OpenCorporates | living | https://opencorporates.com/terms-of-use-2/ |
| `openownership_register_terms` | Open Ownership Register terms and conditions (archived page: the register closed on 29 November 2024) | Open Ownership | 2024 | https://register.openownership.org/terms-and-conditions |
| `danske_bruun_hjejle_2018` | Report on the Non-Resident Portfolio at Danske Bank's Estonian branch (press release; the report PDF is the extra URL) | Bruun & Hjejle for Danske Bank | 2018 | https://danskebank.com/news-and-insights/news-archive/press-releases/2018/pr19092018 ; https://danskebank.com/-/media/danske-bank-com/file-cloud/2018/9/report-on-the-non-resident-portfolio-at-danske-banks-estonian-branch.pdf |
| `doj_danske_2022` | Danske Bank Pleads Guilty to Fraud on U.S. Banks in Multi-Billion Dollar Scheme to Access the U.S. Financial System (title from the page address; confirm when opening) | US Department of Justice | 2022 | https://www.justice.gov/opa/pr/danske-bank-pleads-guilty-fraud-us-banks-multi-billion-dollar-scheme-access-us-financial |
| `occrp_azerbaijani_laundromat_2017` | The Azerbaijani Laundromat (project page; "The Core Companies" is the extra URL) | OCCRP | 2017 | https://www.occrp.org/en/project/the-azerbaijani-laundromat ; https://occrp.org/en/project/the-azerbaijani-laundromat/the-core-companies |
| `occrp_pace_bribery_2021` | Italian Court Sentences Former Council of Europe MP for Bribery | OCCRP | 2021 | https://www.occrp.org/en/news/italian-court-sentences-former-council-of-europe-mp-for-bribery |
| `doj_1mdb_2016` | United States Seeks to Recover More Than $1 Billion Obtained from Corruption Involving Malaysian Sovereign Wealth Fund | US Department of Justice | 2016 | https://www.justice.gov/opa/pr/united-states-seeks-recover-more-1-billion-obtained-corruption-involving-malaysian-sovereign |
| `doj_1mdb_complaint_2025` | Verified complaint for forfeiture in rem, C.D. Cal. 2:25-cv-00474 | US Department of Justice | 2025 | https://www.justice.gov/opa/media/1385611/dl |
| `doj_goldman_2020` | Goldman Sachs Charged in Foreign Bribery Case and Agrees to Pay Over $2.9 Billion | US Department of Justice | 2020 | https://www.justice.gov/archives/opa/pr/goldman-sachs-charged-foreign-bribery-case-and-agrees-pay-over-29-billion |
| `doj_ng_sentencing_2023` | Former Goldman Sachs Investment Banker Sentenced for $2.7B Bribery and Money Laundering Scheme (title and year from the page address and public record; confirm when opening) | US Department of Justice | 2023 | https://www.justice.gov/opa/pr/former-goldman-sachs-investment-banker-sentenced-27b-bribery-and-money-laundering-scheme |
| `doj_1mdb_settlement_2019` | U.S. Reaches Settlement to Recover More Than $700 Million in Assets Allegedly Traceable to Corruption Involving Malaysian Sovereign Wealth Fund (title from the page address; confirm when opening) | US Department of Justice | 2019 | https://www.justice.gov/usao-cdca/pr/us-reaches-settlement-recover-more-700-million-assets-allegedly-traceable-corruption |

In `bibliography.yaml`, the first URL of a row is `url` and any URL after the semicolon goes in `extra_urls`; "living" becomes `year: null` with a note. Before writing an entry, open its URL once; most of these domains are outside the WebFetch allow list in `.claude/settings.json`, so expect approval prompts. Set `verified` to the date you opened it. If a URL no longer resolves, keep the entry, set `note` to what happened and stop to ask (2.5).

Scale statement for the README and any slide (replaces the plan's wording): UNODC estimated that about USD 1.6 trillion, or 2.7 percent of global GDP, was laundered in 2009, and attributes the often-quoted range of 2 to 5 percent to the IMF in 1998 ([unodc_iff_2011]).

### 7.4 Glossary

`docs/glossary.md` starts from this table. Definitions are paraphrases unless quoted; check each against its source before publishing.

| Term | Definition for NeonRadar documentation | Sources |
|---|---|---|
| Placement, layering, integration | Three descriptive stages: placement introduces proceeds into the financial system, layering moves them to distance them from their source, integration returns them to the legitimate economy. Schemes often skip or repeat stages. | `fatf_faq`, `europol_efecta_2023` |
| Beneficial owner | The natural person or persons who ultimately own or control a customer, or on whose behalf a transaction is conducted, including those who exercise ultimate effective control over a legal person or arrangement. Only natural persons; a company that owns a company is a legal or intermediate owner. | `fatf_glossary` |
| Legal owner, intermediate owner | Project terms for companies and arrangements in an ownership chain between the subject and its beneficial owners. | project |
| Control | Ownership is one route to control; control can also come from voting rights, appointment rights, agreements, family ties or influence, at any percentage. | `fatf_bo_legal_persons_2023`, `star_puppet_masters_2011` |
| 25 percent threshold | An illustrative FATF example that became a legal threshold in the EU and elsewhere; it is not a FATF requirement, several countries use lower thresholds, and control can exist at any percentage. (The example is in the Interpretive Note to Recommendation 10, verified from the 2012 text; confirm it in the June 2026 edition before quoting.) | `fatf_recommendations_2026`, `openownership_thresholds`, `eba_qa_2022_6622` |
| Politically exposed person (PEP) | A person who is or has been entrusted with a prominent public function by a country (foreign or domestic PEP) or by an international organisation; not middle-ranking or junior officials. | `fatf_glossary`, `fatf_peps_2013` |
| RCA | Industry shorthand for relatives and close associates of PEPs, whom Recommendation 12 also covers (FATF speaks of family members and close associates; confirm the exact wording in the June 2026 edition before quoting it). | `fatf_recommendations_2026`, `fatf_peps_2013` |
| Nominee | A person who formally holds shares or a directorship for someone else (the nominator) whose identity is not disclosed; informal nominees include relatives and associates. "Strawman" and "proxy" are synonyms some sources use. | `fatf_egmont_concealment_2018`, `europol_shadow_money_2021` |
| Shell company | An incorporated company with no independent operations, significant assets or ongoing business activities. It describes a structure; never call a real, named company a shell. | `fatf_egmont_concealment_2018`, `fincen_fin_2006_g014` |
| Shelf company | An incorporated company with inactive shareholders, directors and secretary, left dormant and later sold with its incorporation date. | `fatf_egmont_concealment_2018` |
| Front company | A fully functioning company with the characteristics of a legitimate business, used to launder funds. | `fatf_egmont_concealment_2018` |
| Trust and company service provider (TCSP) | A person or business that, for third parties, forms legal persons, acts as or arranges directors or secretaries, provides a registered office or address, acts as or arranges trustees, or acts as or arranges nominee shareholders. | `fatf_glossary` |
| DNFBP | Designated non-financial businesses and professions: casinos, real estate agents, dealers in precious metals and stones, lawyers, notaries, other independent legal professionals and accountants, and TCSPs. | `fatf_glossary` |
| STR and SAR | Suspicious transaction report (the FATF term, Recommendation 20) and suspicious activity report (the US term). Treated as equivalent; use STR for FATF and non-US contexts and SAR for US material. | `fatf_recommendations_2026`, `ffiec_appendix_f` |
| Financial intelligence unit (FIU) | The national centre that receives and analyses STRs and other relevant information and disseminates the results. | `fatf_recommendations_2026`, `egmont_fiu` |
| Structuring, smurfing | Splitting cash transactions into amounts below a reporting threshold to avoid reports; smurfing is the same done by teams of people. | `cfr_31_1010_314`, `ffiec_appendix_g`, `fincen_fin_2025_a003` |
| Money mule | A person who receives money from a third party into their account and transfers it on, wittingly or unwittingly. | `europol_money_muling`, `fatf_pml_2018` |
| Funnel account | An account in one area that receives many cash deposits, often below the reporting threshold, withdrawn in another area soon after. | `fincen_fin_2014_a005` |
| Pass-through or transit account | An account that receives and forwards funds quickly and keeps little balance. | `fatf_egmont_tbml_indicators_2021` |
| Mass registration address | An address listed against many companies, usually the address of a TCSP that manages them. | `fatf_egmont_concealment_2018` |
| Round-tripping | Payments routed in a circle so that funds return to their origin. | `fatf_egmont_tbml_indicators_2021` |
| Trade-based money laundering (TBML) | Disguising proceeds and moving value through trade transactions, for example by misrepresenting price, quantity or quality. | `fatf_egmont_tbml_2020` |
| Correspondent banking | Banking services that one bank (the correspondent) provides to another (the respondent). | `fatf_glossary`, `wolfsberg_correspondent_2022` |
| Red flag, indicator | A feature that sources list as a reason to look closer; not evidence on its own. | `ffiec_appendix_f` |
| Structural pattern | NeonRadar's term for a graph shape that matches a typology's pattern. It describes data, not conduct. | project |
| Pattern strength | A number from 0 to 1 for how closely evidence matches a typology's pattern; used to order the queue; never a risk or suspicion score. | project (C4) |
| Synthetic scenario | A pattern planted by the generator among synthetic entities only. | project (G1) |
| Look-alike | Benign synthetic activity with the same shape as a typology (a refund cycle, a payroll fan-out), generated so that precision can be measured honestly. | project |
| Flag | A label from source data (`:Sanctioned`, `:PEP`, `:RCA`); never set by a detection. | project (C2) |
| Alert, evidence subgraph | A C4 object produced by a detector, with the node and edge ids and the query that reproduce it. | project (C4) |

### 7.5 Real cases and reading list

**Case notes** (M1.10c writes `docs/learning/cases/`). For each case: a summary, a Mermaid diagram that uses roles rather than names, the typologies it illustrates, "adjudicated" and "alleged" sections, and sources. Re-check the status of every court outcome before publishing and write the date checked.

1. **Danske Bank, Estonian branch, non-resident portfolio (2007 to 2015).**
   - May name: Danske Bank. In December 2022 it pleaded guilty in the United States to conspiracy to commit bank fraud, admitting that its Estonian branch processed about USD 160 billion through US banks for non-resident customers while misrepresenting its anti-money-laundering controls to its US correspondent banks, and agreed to forfeit about USD 2 billion ([doj_danske_2022]).
   - Context: the bank's own investigation describes about 10,000 non-resident customers (about 15,000 counting every customer with a cross-border characteristic) and about EUR 200 billion of payments in 2007 to 2015, and states that its findings do not allow a conclusion that money laundering or other crime occurred ([danske_bruun_hjejle_2018]).
   - Describe by role: customers, introducing agents, intermediaries, former employees. Individual liability is unresolved in the sources checked.
   - Diagram roles: one branch holding many customer accounts; customer companies (many UK limited partnerships and LLPs, and companies from the British Virgin Islands); introducing agents; inbound transfers from banks in other countries; US correspondent banks clearing the dollar payments. Typology: `rapid_pass_through` (pass-through to beneficiaries in other countries through correspondent banks).
2. **The Azerbaijani Laundromat (2012 to 2014).**
   - Reported by OCCRP and Berlingske in September 2017: about EUR 2.5 billion moved in more than 16,000 transactions over two years through four UK-registered companies (two Scottish limited partnerships and two English LLPs), all with accounts at Danske Bank's Estonian branch ([occrp_azerbaijani_laundromat_2017]).
   - Adjudicated: a former member of the Parliamentary Assembly of the Council of Europe was convicted of bribery at first instance by a Milan court in January 2021, with payments that OCCRP reports were routed through British and offshore companies ([occrp_pace_bribery_2021]); describe him by role and as "convicted at first instance", because the appeal status was not verified.
   - Documented by the bank's own investigation (not a court finding): 75 of its customers were linked by media reports to the scheme, and two thirds of them were UK LPs or LLPs ([danske_bruun_hjejle_2018]).
   - Alleged: the source and purpose of the funds, the involvement of any official, and the knowledge of any recipient. Name none of the companies, senders or recipients.
   - Diagram roles: four UK partnerships registered at formation-agent addresses; nominee directors; their accounts at one bank branch; a few state-linked senders; dense transfers among the four; fan-out to several hundred recipients. Typologies: `shell_chain`, `mass_registration_address`, `rapid_pass_through`, `fan_out_distribution`.
3. **1MDB (2009 to 2015).**
   - Alleged in US civil forfeiture complaints: more than USD 4.5 billion misappropriated from 1Malaysia Development Berhad and laundered through accounts in several countries into real estate, art and other assets ([doj_1mdb_complaint_2025]; the first complaints were announced in 2016, [doj_1mdb_2016]). These are allegations until a court rules, although many assets were forfeited by settlement ([doj_1mdb_settlement_2019]).
   - May name: 1MDB, as the fund the money was taken from; Goldman Sachs, whose Malaysian subsidiary pleaded guilty and whose parent entered a deferred prosecution agreement in October 2020 for conspiracy to violate the US Foreign Corrupt Practices Act, paying more than USD 2.9 billion ([doj_goldman_2020]); Roger Ng, a former Goldman managing director convicted by a jury in April 2022 and sentenced to 10 years ([doj_ng_sentencing_2023]); Tim Leissner, a former Goldman partner who pleaded guilty in 2018 ([doj_goldman_2020]).
   - Describe by role: the financier charged in the United States in 2018, who remains a fugitive and is presumed innocent; every official; the companies named in the complaints. Malaysian court outcomes for former officials: verify the current status before writing anything beyond "role".
   - Diagram roles: the fund; three bond issuances; three companies that received diverted funds (one with a name chosen to resemble a genuine Abu Dhabi entity), each with an account in Switzerland or Singapore; onward fan-out to assets; the charged financier controlling those companies; the convicted bankers attached to the bond issuances. Typologies: `layering_chain`, `fan_out_distribution`, `shell_chain`, `pep_exposure`.

Not used: the Troika Laundromat, because nothing in it has been adjudicated in the sources checked; it may appear later only as an anonymised structural illustration.

**Reading list by sprint** (from the plan; M1.10c writes `docs/learning/reading-list.md`). The right-hand column says where to start; the agent opens and verifies the exact page before linking it.

| Sprint (phases) | Everyone reads | The relevant squad also reads | Where to start |
|---|---|---|---|
| 0 (Phase 1) | Neo4j graph data modelling guide; one FATF typology report; FollowTheMoney documentation | Companies House and OpenSanctions API documentation | neo4j.com documentation; `fatf_egmont_concealment_2018` or `fatf_pml_2018`; followthemoney.tech; developer.company-information.service.gov.uk; opensanctions.org/docs |
| 1 (Phase 2) | Cypher query tuning basics; how indexes and constraints work in Neo4j | Splink documentation and the Fellegi-Sunter record linkage model | Neo4j Cypher Manual; the Splink documentation site |
| 2 (Phases 3 and 4) | Graph Data Science overview: community detection, centrality, weakly connected components | Text-to-Cypher and GraphRAG patterns, and their failure modes | Neo4j GDS manual; Neo4j GraphRAG for Python documentation |
| 3 (Phases 5 and 6) | What makes an open-source project usable by strangers | Technical writing for READMEs; Vue 3 Composition API | opensource.guide; vuejs.org guide |

### 7.6 Architecture decision records

Numbers are pre-assigned so that parallel pull requests never collide. The agent drafts each ADR from the decision recorded in this spec; the named deciders read it, edit it until it says what they think, and approve it. An ADR's "Deciders" line names people, never the agent.

| Number | Title | Written in | Status at Gate 1 (set by the deciders) | Deciders |
|---|---|---|---|---|
| 0001 | Record architecture decisions | M1.1 | accepted | project lead, tech lead |
| 0002 | Neo4j 5.26 LTS | M1.4 | accepted | tech lead |
| 0003 | FollowTheMoney as the record format | M1.7a | accepted | tech lead |
| 0004 | Graph schema v1 | M1.7b | accepted | tech lead |
| 0005 | Synthetic data policy | M1.8e | accepted | tech lead, data steward |
| 0006 | Data licensing | M1.10a | accepted | data steward, project lead |
| 0007 | Toolchain | M1.3 | accepted | tech lead |
| 0008 | API gateway and OpenAPI snapshot | M1.7d | accepted | tech lead |
| 0009 | Alert object and wording | M1.7c | accepted | tech lead, typology researchers |
| 0010 | Copilot: local and template first | M1.10c | proposed (decided in Phase 4) | tech lead, copilot mentor |
| 0011 | AI-built workflow | M1.2 | accepted | project lead, tech lead |
| 0012 | Documentation site | M1.10c | proposed (decided in Phase 6) | technical writer, tech lead |

Numbers from 0013 are assigned by later phase specs. The plan's definition of done needs ADRs for the schema (0004), the entity resolution approach (Phase 2) and the detection design (Phase 3), and at least eight in total.

---

## 8. Gate 1: schema frozen (Friday 23 October)

The tech lead decides Gate 1 with the release manager. `make gate-1` (M1.12) gathers the evidence; checks it cannot verify are marked MANUAL and a named human confirms them in the Phase 1 report.

| ID | Check | Evidence | Blocks the freeze |
|---|---|---|---|
| GC-01 | Contract suite green on `main` | `make contracts-check`; `contracts/CHANGELOG.md` has a complete 1.0.0 entry for C1 to C4 | yes |
| GC-02 | Graph schema applies cleanly | `neonradar graph migrate` on an empty test database yields 22 constraints and the 7 indexes in `0001_init.cypher` | yes |
| GC-03 | Walking skeleton runs end to end | latest `e2e` workflow run on `main` succeeded, or a local `make demo-mini && make e2e` | yes |
| GC-04 | CI green on `main` | latest `ci` workflow run on `main` succeeded | yes |
| GC-05 | Repository basics | governance files from M1.1 exist; `generate_codeowners.py --check` passes; labels exist | no |
| GC-06 | Protection in place, or the plan limitation recorded | `gh api repos/<repo>/branches/main/protection` answers, or `docs/build/ci.md` records the limitation and the interim controls | no (MANUAL) |
| GC-07 | Devcontainer works | evidence in the M1.5 pull request; one Windows or Codespaces user confirmed | no (MANUAL) |
| GC-08 | Every source fetched end to end in a spike | `docs/data/spikes/` has reports for Companies House, GLEIF, ICIJ and OpenSanctions, each with a verdict; "blocked on licence decision" is an acceptable OpenSanctions verdict | no |
| GC-09 | Synthetic join proven | demo-mini validates in strict mode and regenerates byte-identically; the synthetic-join command's output is in the M1.8e pull request | no |
| GC-10 | Knowledge base seeded | bibliography loads; `check_citations.py` passes; 15 typology files and explainers exist; `circular_flow` is approved | no |
| GC-11 | Every intern has a merged pull request | each handle in `people.interns` authored at least one merged pull request (`gh pr list --state merged --author <handle>`) | no |
| GC-12 | Learning logs started | `docs/learning/<handle>.md` exists with at least one entry for each intern | no |
| GC-13 | Assignment 2 under way | an open or merged pull request for each typology in the Assignment 2 table | no (MANUAL) |
| GC-14 | ADRs as in 7.6 | status lines of ADRs 0001 to 0012 match the table; every accepted ADR was accepted by its deciders (the commit that set `accepted` is theirs) | no |
| GC-15 | Legal and communications conversation started | note in `docs/build/PROGRESS.md` | no (MANUAL) |
| GC-16 | Phase 1 report written | `docs/build/reports/phase-1.md` exists with metrics, deviations, risks and Phase 2 inputs | no |
| GC-17 | Data steward approved the licence fields | link to the data steward's approving review of `contracts/datasets.yaml` (M1.7a, or a later pull request that changed it) and of `DATA_SOURCES.md` | yes (MANUAL) |

**Freeze.** When GC-01 to GC-04 and GC-17 pass, the tech lead reviews `contracts/CHANGELOG.md` and creates the tag (5.5). From that moment the guard hook and the CI label check enforce the freeze.

**Outcomes.**

- **Pass**: every check passes. Tag created; the Phase 2 spec is written from the Phase 1 report.
- **Pass with exceptions**: blocking checks pass and some others fail. Tag created; each failed check gets an owner and a date in the Phase 1 report.
- **Fail**: a blocking check fails. No tag. Fix and re-run. If the gate slips past Friday, the project lead applies the next cut on the plan's kill list the same day (the first cut is UI polish).

---

## 9. Risks for Phase 1

| # | Risk | Likelihood | Impact | Response in this spec | Owner |
|---|---|---|---|---|---|
| R1 | OpenSanctions licence blocks the planned sanctions source | high | medium | Loader gated by `access.opensanctions`; synthetic fixtures; Phase 2 chooses between a licence, an evaluation agreement or official government lists (M1.8d) | data steward |
| R2 | GLEIF API interruptions from 19 October to 4 November | medium | low | Mocked tests; network run whenever the API answers; Golden Copy files as the Phase 2 fallback (M1.8b) | ingest mentor |
| R3 | Companies House key not ready | medium | low | Build with mocks and stop before the network run; register on day 1 (1.1) | tech lead |
| R4 | PyICU fails to build on laptops | medium | medium | ICU headers in 1.1; `neonradar doctor` checks ICU; devcontainer (M1.5) | docs squad |
| R5 | Review capacity: about 30 agent pull requests in one week | high | high | 400-line limit; reviewer subagent and the optional CI review agent; cross-squad review; named owners; the calendar in 1.8 | project lead |
| R6 | Contracts change after the freeze | medium | high | Walking skeleton before the freeze; guard hook; CI label check; change process in 5.0 | tech lead |
| R7 | Plausible but wrong AI output: Cypher that encodes the wrong traversal, invented GDS signatures, confident AML errors | high | high | Fixtures with known answers; human approval of typologies; citations and the claims checker; "explain every line" review rule | mentors, typology researchers |
| R8 | Private repository on GitHub Free has no branch protection | medium | medium | Deny rules, CI, CODEOWNERS review requests and team discipline; consider a paid plan for five weeks; run the protection script again at launch (M1.6) | project lead |
| R9 | Not enough memory for Docker on 8 GB laptops | medium | medium | Small memory profile; Codespaces; demo-mini is small (M1.4, M1.5) | docs squad |
| R10 | Synthetic names collide with real people or companies | medium | high | Denylist; neutral company word lists; Companies House name search for the committed demo companies; collision check against loaded names; reviewers read samples (7.1, M1.7a, M1.8e) | data steward |
| R11 | Personal data from spikes reaches the repository | low | high | Spike output only in `data/cache/`; fixture check; gitleaks; reports with counts only (G2, M1.8) | data steward |
| R12 | Interns learn little because the agent does the typing | medium | high | Assignments 1 and 2; review duty; deciders edit their ADRs; learning logs, teach-backs and exit posts are human-only (1.9) | community manager |
| R13 | Version drift during the build | medium | low | Exact pins in 3.1; Dependabot ignores majors for Neo4j and TypeScript; ADR-0002 revisit | tech lead |
| R14 | GDS plugin downloaded at start instead of bundled, which breaks offline use | low | medium | M1.4 checks the logs; plugin volume fallback | graph mentor |

---

## 10. Appendix

### 10.1 Document history

| Version | Date | Change |
|---|---|---|
| 1.0 | 16 October 2026 | First version: Phase 1 build spec, verified baseline, contracts, milestones, knowledge base, Gate 1 |

Record later changes here, with a matching note in `docs/build/PROGRESS.md`.

### 10.2 Build terms

| Term | Meaning here |
|---|---|
| Acceptance commands | The commands at the end of a milestone; all must pass in the session before the pull request opens |
| ADR | Architecture decision record in `docs/decisions/` (7.6) |
| Agent pull request | A pull request drafted by Claude Code, labelled `agent`, with a named human owner |
| Auto mode | Claude Code permission mode in which a classifier reviews actions instead of prompting for each one |
| CODEOWNERS | GitHub file that requests reviews from the owning team for each path |
| Contract | One of C1 to C4 (section 5), frozen at Gate 1 |
| Devcontainer | A container definition that gives everyone the same development environment (M1.5) |
| Fixture | Small synthetic data committed for tests and demos |
| Gate | A dated checkpoint with explicit criteria (section 8) |
| Golden example | A committed example file that must validate (or fail with one named rule) |
| Hook | A script Claude Code runs before or after a tool call; `guard-contracts.sh` can block an edit |
| MCP server | A tool server Claude Code can call; here a read-only Neo4j server for inspecting the local graph |
| Milestone | One unit of work in section 6, built on one branch and delivered as one pull request |
| Operator | The human who prepares access and starts milestones (tech lead or project lead) |
| Plan first | Milestones where Claude Code proposes a plan and waits for approval before building |
| `PROGRESS.md` | The build log in `docs/build/` (2.8) |
| Skill | A reusable instruction set in `.claude/skills/`, started with a slash command such as `/milestone` |
| Spike | A time-boxed fetch of a small slice of a data source, end to end, to find problems early |
| Subagent | A separate Claude instance with its own instructions, used here for independent review |
| Walking skeleton | The thinnest version of the whole system that runs end to end (M1.9) |
| Worktree | A second working copy of the repository on its own branch, so milestones can run in parallel |

### 10.3 Files delivered with this spec

| File | Goes to |
|---|---|
| `PHASE-1.md` (this document) | `docs/build/PHASE-1.md` |
| `project.yaml` (template from 1.3) | `docs/build/project.yaml`, after the operator fills it in |
| `research/README.md` and six research notes | `docs/research/2026-10-16/` |
| `neonradar-project-plan.md` (export of the project plan) | `docs/plan/neonradar-project-plan.md` |
| `README.md` (the kit's four steps) | stays in the kit |
