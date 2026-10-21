# NeonRadar build spec, Phase 2: Ownership graph

| | |
|---|---|
| File | `docs/build/PHASE-2.md` |
| Version | 1.0, 18 October 2026 |
| Phase window | Monday 26 October to Wednesday 4 November 2026 (Gate 2: graph loads end to end) |
| Built by | Claude Code (VS Code extension or CLI), one milestone per pull request |
| Reviewed and merged by | Humans only |
| Facts verified on | 18 October 2026 (section 3, with the full research notes in `docs/research/2026-10-18/`) |
| Starts from | Gate 1 passed, tag `contracts-v1.0.0`, `docs/build/reports/phase-1.md` merged |
| Runs alongside | `docs/build/PHASE-3.md` (Transactions and detection), which also starts on 26 October |

This document is both a plan and a set of executable instructions, in the same format as `docs/build/PHASE-1.md`. Humans read it to know what will be built, what they must decide, and what they must do themselves (above all the labelling that produces the published entity resolution figure). Claude Code reads it to build the ownership graph milestone by milestone.

Phase 2 is the first phase that touches real personal data at scale: company officers, people with significant control, sanctioned persons and the names in the ICIJ Offshore Leaks Database. Three new guardrails (G8 to G10 in section 2.1), a separate local database for real data (4.1) and the real-data rules in section 7.4 exist for that reason. Read them before anything else.

---

## 0. How to use this document

### 0.1 Who reads what

| Reader | Reads | Why |
|---|---|---|
| Operator (tech lead or project lead) | Sections 0, 1 and 8 in full, then the "Review focus" box of each milestone | Prepares access and decisions, opens the contract-change issues, runs the real-data profiles on an approved machine, checks Gate 2 |
| Claude Code (the build agent) | Sections 0, 2, 3, 4 and 5 once per session, then only the active milestone in section 6, plus section 7 when a milestone points there | Executes milestones within the rules |
| Reviewers (mentors and interns) | The pull request, the milestone's "Review focus" box, section 5 for contract changes and section 7.1 for anything that touches matching | Decide whether the work is correct and understood |
| Data steward | Sections 1.1, 1.2, 2.1 (G2, G7, G8, G9), 3.3, 5.1, 7.4 and 7.7, and every pull request labelled `data-source` or `real-data-run` | Files Robotat's data protection documents; approves licence fields, real-data machines, retention and the merge policy |
| Labellers (named interns and mentors) | `docs/er/labelling-guide.md` (M2.14) and `docs/team/assignment-3.md` | Produce the human labels behind the published precision figure |

### 0.2 How the build runs

```text
operator: /milestone M2.x  (or the explicit prompt in 1.7)
   |
   v
Claude Code: read spec -> plan -> branch -> build -> run acceptance commands (synthetic data)
             -> independent review subagent -> update PROGRESS.md -> open PR -> STOP
   |
   v
humans: CI + review checklist + named reviewer -> request changes or approve -> MERGE
   |
   +--> for milestones marked "Real-data run": the operator runs the listed command on an
        approved machine and pastes the counts-only output into the pull request
   |
   v
next milestone (or several in parallel, see 1.8)
```

Claude Code never merges, never labels entity pairs and never reads real records. Every acceptance command in this document runs on synthetic data unless it is explicitly marked as a real-data run, and every real-data command prints counts, timings and rates only.

### 0.3 The six phases

| Phase | Name | Dates (2026) | Ends with | Main output |
|---|---|---|---|---|
| 1 | Foundation and contracts | Fri 16 Oct to Fri 23 Oct | Gate 1, Fri 23 Oct: schema frozen | Repository, tooling, CI, agent kit, four frozen contracts, data source spikes, a thin end-to-end walking skeleton |
| **2** | **Ownership graph (this document)** | **Mon 26 Oct to Wed 4 Nov** | **Gate 2, Wed 4 Nov: graph loads end to end** | **Production loaders for Companies House, GLEIF, ICIJ and official sanctions lists; entity resolution with a published precision figure; ownership, paths and resolution endpoints** |
| 3 | Transactions and detection | Mon 26 Oct to Fri 13 Nov | Gate 3, Fri 13 Nov: detections green | Synthetic transaction overlay attached to entities, 10 typology detections with fixtures, evaluation harness with precision and recall |
| 4 | API and investigation copilot | Mon 2 Nov to Fri 13 Nov | Part of Gate 3 | Complete API v1, a template-first local copilot that answers the 10 benchmark questions |
| 5 | Explorer UI | Mon 2 Nov to Tue 17 Nov | Gate 4, Tue 17 Nov: feature freeze | Vue explorer: search, network canvas, alert queue, explain panel |
| 6 | Hardening, documentation and launch | Mon 16 Nov to Fri 20 Nov | Gate 5, Fri 20 Nov: public launch | Documentation site, benchmark, demo video, launch post, every definition-of-done box ticked |

Phase 3 builds against the same contracts in parallel. Its synthetic overlay attaches accounts to entities by their record ids (for example `gbch-co-01800000`); the resolution-aware loader in M2.11 maps those ids to canonical entities, so the two phases never wait for each other's data.

### 0.4 Phase 2 scope

In scope:

- Phase 2 handover: reconcile this spec with what Phase 1 actually built, and update the agent kit (push rules for `p2/` branches, real-data guards, a separate Neo4j instance for real data, a Cypher linter in CI, new rules and traps).
- Contract changes to version 1.1.0, all additive: C1 (four official sanctions datasets, the UK Parliament dataset, five new `nr` keys and three extended ones), C2 (source records, possible matches, search keys, two company properties, open or closed share bounds on `OWNS` and `CONTROLS`, migration `0002`, invariants I7 to I14), C3 (a resolution endpoint; the ownership and paths endpoints become real). C4 stays 1.0.0.
- A data manager: named profiles, downloads with checksums and resumption, a gate that every real-profile command passes first, a status view, retention and purge.
- Production loaders: Companies House (bulk company data, the PSC snapshot, officers through the API within a request budget), the GLEIF Golden Copy, the ICIJ Offshore Leaks Database (a slice or in full), the UK, US and EU sanctions lists, and the UN list once the UN gives written permission; optionally UK Parliament members as a PEP source; OpenSanctions only where `access.opensanctions` allows it.
- A matching keys library for names in Latin, Arabic and Cyrillic scripts, organisation names, addresses, postcodes, nationalities and identifiers.
- A synthetic entity resolution benchmark with ground truth.
- The resolver: deterministic identifier rules, Splink 5 models for people and organisations, constrained clustering with cannot-link rules, the merge policy for listed and leaked records, possible matches, human decisions, a labelling tool and a precision report with a Wilson interval.
- A resolution-aware graph loader with canonical entities and source records, new graph invariants, and real data loaded only into a separate local database.
- API endpoints for ownership chains with effective share ranges, paths between entities, and the resolution evidence behind an entity.
- One command per profile (`make load PROFILE=...`), with measured load and query times.
- The published entity resolution precision figure, from pairs that people label (Assignment 3).
- ADRs 0013 to 0019, entity resolution documentation, real-data handling documentation, the Gate 2 check and the Phase 2 report.

Out of scope (later phases or not at all): the synthetic transaction overlay and every detector (Phase 3); the copilot (Phase 4); explorer UI changes (Phase 5; the Phase 1 shell keeps working against the new API); the documentation site and launch (Phase 6); the Companies House streaming API and daily updates; filing history and accounts data; crawling officer appointments beyond the request budget; OpenCorporates; any public hosting of real data.

### 0.5 Decisions this spec makes

These change the project plan or a Phase 1 assumption. Humans should know them before the build starts. Evidence is in section 3 and `docs/research/2026-10-18/`.

| # | Plan or Phase 1 said | Phase 2 does | Why |
|---|---|---|---|
| 1 | "Ownership graph loads from two or more sources" | Five source families under named profiles. The default real profile, `uk-sample`, is a bounded slice of the register (at most 50,000 companies plus their ownership chains), not the whole register | The scale target (500,000 nodes and 2 million relationships on a 16 GB laptop) has to leave room for Phase 3's transactions; data minimisation for personal data |
| 2 | Sanctions and PEP data from OpenSanctions | The UK, US and EU official lists are the default sanctions source. The UN list loader is built, but runs only with the UN's written permission. The UK and EU lists also carry the UN listings: the UK list gives their UN reference numbers, but the EU field for them was empty in every record the research read, so by default the UN reference rule (D4) may link little or nothing, and UK and EU entries for one listing are compared by the probabilistic model under P6 (7.1.4). PEP flags come from UK Parliament data (M2.6e, optional: current members, and former members for `access.pep_former_months` after they leave office) or from OpenSanctions where `access.opensanctions` allows it, otherwise only from synthetic data (decisions in 1.2) | OpenSanctions needs a data licence inside a company (Phase 1, M1.8d); the UN website terms allow "personal, non-commercial use" and no licence for the list was found; the UK, US and EU terms allow reuse (section 3.3) |
| 3 | "Entity resolution so one person appearing in four sources becomes one node" | Yes, with a merge policy: a listed record (sanctions or PEP) merges with an unlisted record or with a record listed for a different reason, and an ICIJ record with a record from another source, only on a deterministic identifier whose two records share an exact name key, or on a recorded human decision that a second reviewer (or a senior reviewer) confirmed. Otherwise the two stay separate nodes joined by an unconfirmed `POSSIBLY_SAME_AS` link, and flags never cross it. Records that a cannot-link rule separates (different birth dates, company numbers or LEIs, two entries of one list, a reviewer's "different") are not even linked | A false sanctions or leak match on a real person is the most harmful error this project can make (G1, G8); ICIJ warns that "many people and entities have the same or similar names" |
| 4 | "Fix on Splink with one agreed configuration. Accept roughly 80% precision and publish the number honestly" | Deterministic identifier rules first, then Splink 5. Thresholds are chosen on the synthetic benchmark and frozen before any evaluation pair is labelled; the evaluation run ignores earlier review decisions. Precision is measured on 400 human-labelled real pairs (at least 250) and published with a Wilson 95 percent interval, whatever it turns out to be | An honest number needs a frozen configuration and an untouched evaluation sample (G10); 400 labels bound the interval to about 5 points either way |
| 5 | Officers from the REST API (Phase 1) | Officers fetched per company within a request budget (default 20,000 requests, about three hours), cached and resumable; the first 8 characters of `person_number` link officer records whose names also agree (D3) | Companies House publishes no bulk officer file (products 195, 198 and 216 are available only on request, with unpublished terms); the API allows 600 requests per 5 minutes |
| 6 | "Whether to bulk-load with `neo4j-admin import`" (Phase 1 report) | Not in Phase 2. The online Python loader stays the only loading path; M2.13 measures it against the 10-minute target | The loader is idempotent and works in the devcontainer and CI; Community's offline import needs a stopped server and an empty database |
| 7 | Resolver inside `graph/` (Phase 1, 4.1) | Two new workspace members, both owned by the Graph and ER squad: `keys/` (pure matching-key functions used by the loaders, the resolver and the graph loader) and `resolve/` (the resolver) | Keeps Splink, DuckDB and PyArrow out of the API image, and keeps one implementation of every key |
| 8 | GLEIF through its API | The GLEIF Golden Copy files are the production source; the API is for spot checks only | Complete and fast. GLEIF announced service interruptions for 19 October to 4 November without naming the services, so whether Golden Copy downloads are affected is unconfirmed: M2.4 fetches a copy as soon as it merges and keeps it (R16) |
| 9 | ICIJ Offshore Leaks in full | For `uk-sample`, a slice tied to the profile's own postcode districts (`district-linked`, M2.5) by default; `gb-linked` (UK-linked nodes up to a cap) is an option the data steward chooses (1.2, ADR-0013); `full` is for local experiments only (M2.5) | The full database (about 2 million nodes and 3.3 million relationships) alone exceeds the scale target, and leak nodes unrelated to the sampled companies only add possible matches: data minimisation applies to them as to the register slice |
| 10 | C2: "`:SourceRecord` defined in Phase 2" | Defined (5.2). Source records exist only for entities merged from two or more records; a single-record entity keeps its record id as its node id | Halves the node count and keeps Phase 1 ids stable |
| 11 | Guardrails G1 to G7 | Adds G8 (no inferred flags), G9 (real data stays local, and the agent never reads it) and G10 (humans label, and labels stay honest) | Phase 2 is the first phase with real personal data at scale |
| 12 | Sprint 1 learning: Splink and the Fellegi-Sunter model | Assignment 3: every intern labels pairs for the precision figure and explains five hard decisions at the teach-back | The plan's learning track; the labels are real work that the agent must not do |
| 13 | Phase 1 stored a share band as two numbers, and its research note followed the API's long descriptions ("more than 75%") | The statute's bands: `(25, 50]`, `(50, 75)` and `[75, 100]`, carried as open or closed bounds from the PSC loader through the graph to the API, for shares (`Ownership`, `OWNS`) and for voting rights (`Control`, `CONTROLS`) (5.1 to 5.3) | "More than 50% but less than 75%" and "75% or more" are the legal words; a 50 percent test (OFAC) or a more-than-50 test of shares or voting rights (OFSI) depends on them |
| 14 | Dependency licences were not reviewed in Phase 1 | `python-stdnum` (LGPL-2.1-or-later), which rigour and FollowTheMoney require, is accepted as an unmodified library installed from PyPI, if the tech lead and the project lead agree (1.2). The project ships no copy of it; a published image or bundle that ever contains it must include the LGPL-2.1 text and its source, or a written offer of the source | Without it NeonRadar cannot use rigour or FollowTheMoney, and Phase 1 already depends on FollowTheMoney |

### 0.6 What Phase 2 needs from Phase 1

This spec was written on 18 October, before Gate 1. M2.0 reconciles it with what Phase 1 actually delivered. It expects:

- Tag `contracts-v1.0.0` on `main`, and `make contracts-check` green.
- `docs/build/reports/phase-1.md`, with the deviations from `PROGRESS.md` and the decisions needed for Phase 2.
- Spike reports in `docs/data/spikes/` for Companies House, GLEIF, ICIJ and OpenSanctions, with measured headers, field names and verdicts.
- The walking skeleton: `make demo-mini` and `make e2e` passing; the loader, migration runner, API and detection runner from M1.9.
- The C1 validator, the dataset registry and the fixture check from M1.6 and M1.7a.

Where the Phase 1 code or a spike report contradicts this document (a different header name, a different id scheme, a renamed function), M2.0 records it in `docs/build/phase-2-reconciliation.md`, and the measured fact wins for mechanical details. Anything that changes behaviour, a contract or a guardrail goes to the tech lead (2.5).

---

## 1. Operator setup (humans, before the first prompt)

Phase 1's section 1 still applies (accounts, tools, Claude Code settings). This section lists only what Phase 2 adds.

### 1.1 Accounts, tools and access

Tick each box before the Phase 2 kickoff prompt.

- [ ] **Gate 1 passed.** The tag `contracts-v1.0.0` exists on `origin`, and `docs/build/reports/phase-1.md` is merged.
- [ ] **Companies House API key** in `.env` as `CH_API_KEY` on every machine that runs a real-data profile, and `access.companies_house_key: available` in `project.yaml`.
- [ ] **Data protection documents.** Robotat is a controller whenever its staff and interns run a real profile. Before the first one runs, the data steward (with the project lead) files in `docs/data/dpia/`: a legitimate interests assessment; a data protection impact assessment; the DPA 2018 Schedule 1 condition relied on for criminal offence data (a designation may itself be such data, 3.3) with its appropriate policy document; and the Article 14 approach (the Article 14(5)(e) disproportionate-effort exemption with the Article 14(7) safeguards, including privacy information made available publicly). Only then do they set `access.data_protection_filed: true`; until then every real profile refuses to run (M2.2).
- [ ] **Approved real-data machines.** Every machine that will load `uk-tiny` or `uk-sample` has full-disk encryption switched on (FileVault on macOS, BitLocker on Windows, LUKS on Linux) and a screen lock, and the data steward lists it in `docs/data/real-data-machines.md` (owner handle, a nickname for the machine, the date checked; no serial numbers). Its owner then sets `NR_REAL_DATA_MACHINE=approved` in that machine's `.env`. GitHub Codespaces, CI runners and cloud sessions never load real data.
- [ ] **Separate database for real data.** On each approved machine, `.env` holds `NEO4J_REAL_PASSWORD` (and `NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688`, the default). Real profiles load only into the `neo4j-real` instance, never into the default database that the API, the UI, the tests and the agent use (4.1). Before the first real load, run `make up-real` (M2.0) and then `uv run neonradar graph migrate --real` (M2.11: a load into the real instance stops with exit 2 while a migration is pending there).
- [ ] **Disk space** on those machines: `uk-tiny` needs about 10 GB free and `uk-sample` about 25 GB (the downloads are shared between profiles; section 7.8 has the breakdown).
- [ ] **Memory.** `uk-sample` needs the standard memory profile (a 16 GB laptop with 8 GB for Docker). 8 GB laptops use the `demo` and `uk-tiny` profiles.
- [ ] **Time for the officer fetch.** The first `uk-sample` run fetches officers for up to 20,000 companies at the Companies House rate limit, which takes about three hours. Start it on Friday 30 October (the command is in the 1.8 calendar) so labelling can begin on Monday 2 November.
- [ ] **Labellers** (in `project.yaml` after M2.0 merges). Every intern (each labels at least 20 pairs in Assignment 3, G2-13) and every mentor who labels is named in `people.er_labellers`, at least four people in all, each with two hours booked on Monday 2 or Tuesday 3 November, on an approved machine, because labelling shows real records.
- [ ] **Senior reviewers** (in `project.yaml` after M2.0 merges). At least one person (the tech lead or the graph mentor) is named in `people.er_senior_reviewers`. A review decision that would merge a listed or leaked record with another record takes effect only when two reviewers agree or a senior reviewer made it (7.1).
- [ ] **OpenSanctions.** If the licence position changed since Phase 1, update `access.opensanctions` and file the evidence in `docs/data/licences/opensanctions.md`.
- [ ] **UN list (optional).** To load the UN Security Council list directly, the data steward asks `sc-sanctionslists@un.org` for written permission to use it inside Robotat and files the answer in `docs/data/licences/un_sc_sanctions.md` before adding `un_sc_sanctions` to `access.sanctions_lists` (3.3). Without it, the UK and EU lists still carry the UN listings.

### 1.2 Decisions to record before the build

| Decision | Owner | Options | Where it goes |
|---|---|---|---|
| Controller duties | Data steward and project lead | File the documents listed in 1.1 (legitimate interests assessment, DPIA, Schedule 1 condition with its appropriate policy document, Article 14 approach). No default: real profiles stay off until they are filed | `docs/data/dpia/`, then `access.data_protection_filed: true` |
| Which real-data profiles may run | Data steward and project lead | `[]` (synthetic only, the default); `[uk-tiny]`; `[uk-tiny, uk-sample]` | `access.real_data_profiles` |
| Real-data retention | Data steward | Days to keep real downloads, records, resolution runs, logs and decisions (default 30; the Phase 2 report confirms the purge, including the wipe of the real database) | `access.real_data_days` |
| Label retention | Data steward | Days to keep label files, which hold record ids and labels only (default 30); a longer period lets others audit the published figure | `access.label_days` |
| Sanctions lists | Data steward | Any subset of `gb_fcdo_sanctions`, `us_ofac_sdn`, `eu_fsf` and `un_sc_sanctions`, after reading the reuse terms quoted in 3.3. Default: the first three; `un_sc_sanctions` only with the UN's written permission (1.1) | `access.sanctions_lists` |
| PEP sources | Data steward and project lead | Any subset of `gb_parliament_members` (UK Parliament members and ministers, Open Parliament Licence; M2.6e) and `opensanctions_default` (only when `access.opensanctions` is `licensed` or `exempt`). Default `[]`: PEP flags only in synthetic data | `access.pep_sources` |
| Former PEPs | Data steward and project lead | Months a former member of either House keeps the PEP flag after leaving office. Default 12: MLR 2017 regulation 35(9) asks firms to keep enhanced measures for at least 12 months after a person leaves office. Former members outside the period are not loaded (M2.6e) | `access.pep_former_months` |
| The `uk-sample` slice | Data steward and tech lead | The default postcode districts in `ingest/profiles/uk-sample.yaml` (M2.2), or another neutral slice. Never choose a slice because its companies look unusual | Review of the M2.2 pull request |
| ICIJ slice for `uk-sample` | Data steward | `district-linked` (the default: leak nodes tied to the profile's own postcode districts, M2.5) or `gb-linked` (UK-linked nodes up to a cap), with the reason in ADR-0013 | `ingest/profiles/uk-sample.yaml` and ADR-0013 |
| Officer request budget | Tech lead | Default 20,000 requests for `uk-sample` | `ingest/profiles/uk-sample.yaml` |
| Matching thresholds | Tech lead and graph mentor | The values M2.10b calibrates on the synthetic benchmark | ADR-0014 and `resolve/config/er.yaml`, frozen on Thursday 29 October |
| The Companies House person number rule (D3) | Tech lead | Link officer records on the first 8 characters of `person_number` when their names also agree (the default), or use the number for blocking only | ADR-0014 |
| Merge policy | Data steward, project lead and tech lead | The policy in 7.1.4 as written, or stricter | ADR-0015 |
| Labellers | Project lead and graph mentor | Every intern, and each mentor who labels | `people.er_labellers` |
| Senior reviewers | Tech lead and graph mentor | Who may confirm alone a `same` decision that would merge a listed or leaked record with another record; anyone else needs a second reviewer who agrees | `people.er_senior_reviewers` |
| LGPL library dependency | Tech lead and project lead | Accept `python-stdnum` (LGPL-2.1-or-later), required by rigour and FollowTheMoney, as an unmodified library installed from PyPI (default), or stop and replace both libraries (not possible within Phase 2) | `THIRD_PARTY_NOTICES.md` (M2.0) and the M2.0 pull request review |

### 1.3 Additions to `docs/build/project.yaml`

M2.0 merges these keys into the existing mappings with the defaults shown. The operator edits the values; Claude Code stops when a milestone needs a value that is still `TODO`. The `people.er_*` handles are needed only by `er` commands on a real profile (M2.10c on `uk-sample`, M2.15): synthetic milestones (M2.10a, M2.10c on `demo`) run with the `@TODO` defaults and do not stop for them.

```yaml
# Phase 2 additions to docs/build/project.yaml
people:
  er_labellers: ["@TODO", "@TODO", "@TODO", "@TODO"]   # every intern, plus mentors who label
  er_senior_reviewers: ["@TODO"]        # may confirm alone a same decision that crosses P1 or P2 (7.1)
access:
  real_data_profiles: []                # [] | [uk-tiny] | [uk-tiny, uk-sample]
  real_data_days: 30                    # purge real data older than this
  label_days: 30                        # keep label files (record ids and labels only) this long
  data_protection_filed: false          # true once the documents in 1.1 are filed in docs/data/dpia/
  real_data_machines_doc: docs/data/real-data-machines.md
  sanctions_lists: [gb_fcdo_sanctions, us_ofac_sdn, eu_fsf]   # add un_sc_sanctions only with UN permission
  pep_sources: []                       # any of gb_parliament_members, opensanctions_default
  pep_former_months: 12                 # former members keep role.pep this long after leaving office
schedule:
  phase_2_start: 2026-10-26
  er_threshold_freeze: 2026-10-29
  labelling_start: 2026-11-02
```

Phase 1's `access.spike_cache_days` (7) keeps governing `data/cache/spikes/`. `access.real_data_days` governs the rest of `data/cache/real/`, except the label files, which `access.label_days` governs.

### 1.4 Seed the Phase 2 documents

From Phase 2 on, `main` changes only through reviewed pull requests, including this one.

```bash
git fetch origin && git switch -c p2/spec-seed origin/main
mkdir -p docs/research/2026-10-18
# copy the kit files you received:
#   PHASE-2.md          -> docs/build/PHASE-2.md
#   research/*.md       -> docs/research/2026-10-18/
git add docs && git commit -m "docs(build): add phase 2 build spec and research notes"
git push -u origin p2/spec-seed
gh pr create --base main --title "docs(build): add phase 2 build spec [M2.0 seed]" \
  --body "Phase 2 build spec and research notes, as delivered." --label phase-2
```

A human reviews and merges it. M2.0 starts from `main` with the spec in place.

### 1.5 Claude Code settings for this build

Everything in PHASE-1.md 1.5 applies (Auto mode with the project rules, one milestone per session, plan first where marked, evidence over claims). Phase 2 adds:

- **Real data and the agent.** From M2.0 on, the project's permission rules and the `guard_real_data.py` hook stop Claude Code from reading `data/cache/real/` and `data/cache/spikes/` (with Read, Grep, Glob or shell commands), from fetching list, register or leak data files with WebFetch, curl or wget, from reaching the separate real-data database (`neo4j-real`) other than through `neonradar` commands that print counts, and from running the human-only commands (`er label`, `er review`, `api serve --real`). Real profiles load only into `neo4j-real`; the default database, the API on port 8000, the UI, the Neo4j MCP server and every test hold synthetic data only, so the agent can use them freely. Real-data commands print counts only. When something fails on real data, the agent reproduces it on synthetic data; a human looks at real values.
- **Real-data runs.** A milestone marked "Real-data run" lists one command for a human to run on an approved machine (or for the agent to run in a session on that machine, if the operator says so in the session). Every real-profile command first checks, before any request, the dataset's access rule, the profile, `access.data_protection_filed`, that it is not running in CI or Codespaces, and `NR_REAL_DATA_MACHINE=approved` (M2.2). The pull request carries the counts-only output.
- **Contract-change sessions.** For M2.1a, M2.1b and M2.1c the tech lead first approves the matching issue (texts in 5.0), then adds `{"env": {"NR_ALLOW_CONTRACT_CHANGE": "1"}}` to `.claude/settings.local.json` (gitignored), starts a fresh session (hooks and settings are read when a session starts), and removes the setting once the pull request is open.

### 1.6 The Phase 2 kickoff prompt (paste once, in a fresh session)

```text
You are the build agent for NeonRadar, Phase 2 (Ownership graph).

The build spec is docs/build/PHASE-2.md. Phase 1's spec, docs/build/PHASE-1.md, still
defines the frozen contracts in its section 5 and the knowledge base rules in its
section 7; PHASE-2.md section 5 lists the Phase 2 changes to them. Project facts are in
docs/build/project.yaml. Verified research notes are in docs/research/2026-10-18/
(Phase 2) and docs/research/2026-10-16/ (Phase 1).

Before doing anything else:
1. Read docs/build/PHASE-2.md sections 0, 2, 3, 4 and 5 in full, and read
   docs/build/project.yaml. Read only the milestone you are executing from section 6.
2. Reply with six short bullets: the milestone order and dependencies, the rules you must
   never break (including G8 to G10), what you may and may not do with real data, when
   you must stop and ask, how you prove a milestone is done, and what you do after
   opening a pull request.

Then execute milestone M2.0 exactly as section 6 describes, following the milestone
protocol in section 2.2. Stop when the pull request is open and you have reported its URL
and the verification evidence. Do not start another milestone until I name it.
```

### 1.7 Milestone prompts and goal conditions

After M2.0 is merged, the `/milestone` skill reads `docs/build/PHASE-2.md` for any `M2.x` id, so the prompt is one line.

| Milestone | Prompt | Optional goal line (paste after the prompt has started) |
|---|---|---|
| M2.0 | Kickoff prompt (1.6) | `/goal M2.0 acceptance commands from PHASE-2.md were run in this session and passed, PROGRESS.md marks M2.0 pr-open with the PR URL, and the PR is open; stop after 40 turns` |
| M2.1a to M2.1c | `/milestone M2.1a` (in a contract-change session, 1.5) | `/goal <id> acceptance commands passed in this session, the PR is labelled contract-change, CI is green (gh pr checks), and PROGRESS.md records the PR URL; stop after 60 turns` |
| Other milestones | `/milestone M2.3a` (and so on) | `/goal <id> acceptance commands passed in this session, CI on the PR is green (gh pr checks), and PROGRESS.md records the PR URL; stop after 60 turns` |

When review comments arrive: `Address the review comments on PR #<n>. Reply to each comment with what you changed, re-run the milestone's acceptance commands, push, and stop.`

### 1.8 Parallel work and the merge rhythm

```text
seed PR (humans)                           -> M2.0 handover and agent kit
M2.0                                       -> M2.1a C1 1.1.0 -> M2.1b C2 1.1.0 -> M2.1c C3 1.1.0
M2.0                                       -> M2.2 data manager and profiles
M2.0                                       -> M2.8 matching keys
M2.1a                                      -> M2.9 synthetic ER benchmark
M2.1a + M2.2 + M2.8                        -> M2.3a Companies House companies and slice
M2.3a                                      -> M2.3b PSC snapshot -> M2.3c officers
M2.3a                                      -> M2.4 GLEIF Golden Copy
M2.1a + M2.2 + M2.8                        -> M2.5 ICIJ Offshore Leaks
M2.1a + M2.2 + M2.8                        -> M2.6a UK list and shared list module
M2.6a                                      -> M2.6b OFAC, M2.6c UN, M2.6d EU (parallel)
M2.6a + M2.6b + M2.6c + M2.6d              -> M2.6e Parliament PEPs (optional)
M2.1a + M2.2                               -> M2.7 OpenSanctions (only if access.opensanctions allows)
M2.2 + M2.8 + M2.9                         -> M2.10a resolver core -> M2.10b Splink models -> M2.10c decisions, labelling, precision
M2.1b + M2.10a                             -> M2.11 resolution-aware loader
M2.1c + M2.10c + M2.11                     -> M2.12 API: ownership, paths, resolution
M2.3c + M2.4 + M2.5 + M2.6a..d + M2.10c + M2.11 + M2.12 -> M2.13 one command per profile, load benchmark (M2.6e, M2.7 if they ran)
M2.10b                                     -> M2.14 ER documentation and the Assignment 3 kit
M2.13 + M2.14                              -> M2.15 published precision (humans label)
everything                                 -> M2.16 Gate 2 check and Phase 2 report
```

The milestone headers in section 6 are the authority; this graph summarises them.

Suggested calendar:

| Day | Agent work (pull requests) | Human work |
|---|---|---|
| Fri 23 Oct (after Gate 1) | none | Seed pull request (1.4); open the three contract-change issues (5.0); data steward lists approved machines, records the 1.2 decisions and starts the data protection documents (1.1) |
| Mon 26 Oct | M2.0, M2.1a, M2.2, M2.8 | Approve the contract-change issues; review M2.0 first, because every later session depends on its guards |
| Tue 27 Oct | M2.1b, M2.9, M2.3a, M2.5, M2.6a | Contract review; data steward reviews the new dataset entries |
| Wed 28 Oct | M2.1c, M2.3b, M2.4, M2.6b, M2.6c, M2.7, M2.10a | Tech lead tags `contracts-v1.1.0` after M2.1c merges; a `uk-tiny` dry run of the loaders that have merged (once the data protection documents are filed) |
| Thu 29 Oct | M2.3c, M2.6d, M2.10b, M2.11 | Teach-back on entity resolution; tech lead and graph mentor approve the thresholds and write the evaluation sample seed into ADR-0014: the freeze |
| Fri 30 Oct | M2.10c, then M2.12; M2.14, M2.6e (optional) | On an approved machine: `uv run neonradar data fetch --profile uk-sample && uv run neonradar ingest build --profile uk-sample --dataset gb_companies_house` (the downloads and the three-hour officer crawl; `make load` arrives with M2.13) |
| Mon 2 Nov | M2.13 | `uv run neonradar load --profile uk-sample --skip-fetch` (reuses Friday's downloads and officer cache; a new fetch would change the slice) and the evaluation run, `uv run neonradar er run --profile uk-sample --no-decisions` (7.3); labelling session 1 |
| Tue 3 Nov | M2.15, fixes | Labelling session 2; review the precision report |
| Wed 4 Nov | M2.16 | Gate 2 decision |

Merge rule (unchanged from Phase 1): merge in dependency order; bring a branch up to date with `git merge origin/main`, never by rebasing. The tight days are Tuesday to Thursday, when the loaders, the resolver and the loader change land together; the ingest and graph mentors should keep review time free then.

Parallel sessions on one machine share the default local Neo4j, which holds synthetic data only. Real profiles load only into the separate `neo4j-real` instance (M2.0, M2.11), where a real-data load replaces all real data, so run real-data loads one at a time per machine. Integration tests start their own Testcontainers database and are safe in parallel.

### 1.9 What humans do themselves

Everything in PHASE-1.md 1.9 still applies. Phase 2 adds:

- **Data protection.** The data steward, with the project lead, files the documents listed in 1.1 in `docs/data/dpia/` before any real profile runs, and only then sets `access.data_protection_filed: true`.
- **Contract changes.** The tech lead approves each contract-change issue, enables `NR_ALLOW_CONTRACT_CHANGE` for that session only, reviews the pull request and creates the tag `contracts-v1.1.0`.
- **Real-data runs.** A named human runs (or explicitly lets the agent run, in a session on an approved machine) every command marked "Real-data run", and checks that the output pasted into the pull request holds counts only.
- **Labelling.** Only the people in `people.er_labellers` label entity pairs, and no AI tool labels or pre-labels them (G10). Disagreements in the overlap sample are adjudicated by a person who did not set the thresholds (the project lead by default), without seeing either label (7.3). The agent builds the tool, the guide and the report.
- **Reviewing possible matches.** Deciding that two records are or are not the same real entity (`neonradar er review`) is human work, recorded with the reviewer's handle. A `same` decision that would merge a listed or leaked record with another record takes effect only when a second reviewer also records `same`, or when a senior reviewer (`people.er_senior_reviewers`) made it (7.1).
- **Approvals.** Thresholds (ADR-0014: tech lead and graph mentor), the merge policy (ADR-0015: data steward, project lead and tech lead), the real-data handling rules (ADR-0018: data steward), the data protection documents (data steward and project lead), and the licence fields of every new dataset (data steward).
- **Purging.** The data steward confirms in the Phase 2 report that real data older than `access.real_data_days` (label files: `access.label_days`) was purged on every approved machine, and that `neonradar data purge --graph` wiped the real database's volume when its data expired.
- **Source permissions.** The data steward writes to the UN for permission before `un_sc_sanctions` is enabled, decides `access.pep_sources` and `access.pep_former_months`, and keeps the evidence for every licence decision in `docs/data/licences/`. The tech lead and the project lead confirm the LGPL dependency decision (1.2).

---

## 2. Operating rules for the build agent

This section is the agent's constitution for Phase 2. It repeats the Phase 1 rules that still hold, so that a session needs only this document, and adds what real data requires. M2.0 updates `CLAUDE.md` to match; this section wins if they ever disagree.

### 2.1 Mission guardrails (never break these)

| ID | Rule |
|---|---|
| G1 | **No real person or company is ever labelled suspicious.** Synthetic laundering scenarios run only among synthetic entities (ids starting `syn-`). Real registry entities may receive synthetic background activity only, never a scenario role. Any exception needs an ADR approved by the project lead and the data steward (PHASE-1.md G1). |
| G2 | **The repository holds code and synthetic fixtures only.** Never commit bulk data, API responses about real people, real personal data, any row derived from OpenSanctions, or any artefact of a real-data run except the counts-only reports this spec names. |
| G3 | **Nothing phones home.** No telemetry, analytics or outbound calls at runtime by default. Only `neonradar data fetch`, the officer and Parliament API fetches (M2.3c, M2.6e), the spike commands and the one-off build script of M2.8 (which reads rigour's name data from `raw.githubusercontent.com/opensanctions/rigour` at the pinned tag) use the network. Tests never use the network: what they need, including the publishers' XSDs, is committed (2.9). |
| G4 | **AML facts carry citations.** Every factual AML statement in documentation cites a key from `docs/sources/bibliography.yaml`. Only a typology researcher sets a typology to `approved`. |
| G5 | **Patterns, not accusations.** System text describes structures and patterns. It never says an entity laundered money, committed a crime, is a launderer, criminal, fraudster or guilty (PHASE-1.md 7.1, plus 7.2 here for possible matches). |
| G6 | **Secrets stay out.** API keys and passwords live in `.env` or GitHub secrets. Never print, log, commit or request them in chat. |
| G7 | **Licences decide what a loader may do.** Follow `contracts/datasets.yaml` and `access.*` in `project.yaml`. Never publish or commit a database that merges sources. |
| G8 | **No inferred flags.** Flags (`:Sanctioned`, `:PEP`, `:RCA`) and topics on a node come only from that node's own source records. A probabilistic match never adds a flag. A listed record (one with a flag topic, 7.1.1) merges with an unlisted record or with a record listed for a different reason, and an ICIJ record with a record from another dataset, only through a deterministic identifier rule whose two records also share an exact name key, or through a recorded human decision that a second reviewer or a senior reviewer confirmed (7.1). Otherwise the two stay separate nodes joined by an unconfirmed `POSSIBLY_SAME_AS` link, which every text describes as "not confirmed" (7.2); records that a cannot-link rule separates are not linked at all. |
| G9 | **Real data stays local, and the agent never reads it.** Downloads, records, resolution runs, labels, decisions, logs and DuckDB spill files about real entities live only under `data/cache/real/` (and Phase 1 spike output under `data/cache/spikes/`), and real graphs only in the separate `neo4j-real` database, on a machine the data steward approved; they are purged after `access.real_data_days` (label files after `access.label_days`). They never appear in tests, fixtures, commits, pull request text, issues, chat, logs above DEBUG, screenshots or the public demo. The agent never opens, prints, greps or queries real records: not with Read, Grep or Glob, not with shell tools, not by fetching a list, register or leak data file with WebFetch or a shell tool such as curl or wget (documentation and schemas only), and never against `neo4j-real` except through `neonradar` commands that print counts. The default database, the Neo4j MCP server, the API on port 8000 and the UI hold synthetic data only. Real-data commands print counts, timings and rates only; on a real profile an error prints its class, the step, the dataset and the rule, never a value or a person's record id. |
| G10 | **Humans label, and labels stay honest.** Only the people in `people.er_labellers` (every intern, and the mentors who label) label pairs. The agent never writes, edits, pre-fills or infers labels or decisions, and never tunes thresholds, rules or models on the evaluation sample. Thresholds freeze before the evaluation sample is drawn, the evaluation run ignores earlier review decisions, and the published precision figure is what was measured, with its interval and its "unsure" count (7.3). |

### 2.2 Milestone protocol

Run these steps for every milestone or sub-milestone. They are Phase 1's steps with Phase 2 names, plus step 6a.

1. **Sync and check dependencies.** `git fetch origin`. Read `docs/build/PROGRESS.md` as it is on `origin/main` (`git show origin/main:docs/build/PROGRESS.md`). If a dependency in the milestone header is not `merged`, stop and report which one; a row still marked `pr-open` counts as merged when `gh pr view <number> --json state` reports `MERGED`, and you say so in your pull request.
2. **Read.** Read the whole milestone section, the parent section of a sub-milestone (M2.1, M2.3, M2.6 and M2.10 hold shared rules and build steps), everything they link to, and `docs/build/project.yaml`. If a value the milestone needs is `TODO`, stop and ask for it.
3. **Plan.** If the milestone is marked "Plan first" and the operator is in the session, present a plan (files, order, risks, how you will verify) and wait for approval. If the milestone was started with a `/goal` condition, write the plan into the pull request description draft and continue.
4. **Branch.** `git switch -c <branch named in the milestone header> origin/main`, then `uv sync --all-packages` and `npm ci --prefix ui`.
5. **Build in small commits.** Conventional Commits (2.3). Tests go in the same commit as the code they test.
6. **Verify.** Run every command in the milestone's "Acceptance" list. They run on synthetic data. Fix until all pass. Never weaken, skip or delete a test to make it pass; if a test is wrong, say so in the pull request.
   - 6a. **Real-data run** (only where the milestone has one). Do not run it yourself unless the operator said in this session that this machine is approved, the profile is in `access.real_data_profiles` and `access.data_protection_filed` is true. Otherwise write the exact command into the pull request under "Real-data run (operator)" and continue. The output that goes into the pull request is counts only.
7. **Independent review.** Ask the `reviewer` subagent to review the branch diff against the milestone's acceptance list and section 2. For contract work also run `contract-guardian`; for documentation about AML also run `aml-claims-checker`; for anything that touches matching, flags or real data also run `data-guardian` (created in M2.0). Fix every finding that affects correctness, the stated requirements or the guardrails. Record the rest under "Not addressed".
8. **Record progress.** Update the milestone's row in `docs/build/PROGRESS.md` (2.8).
9. **Open the pull request** with `/open-pr`, using the template, the labels named in the milestone header and a mention of the human owner.
10. **Wait for CI** with `gh pr checks <number> --watch` (up to 15 minutes). If CI fails, fix, push and wait again.
11. **Stop and report**: pull request URL, what changed, the acceptance commands with their results, any real-data run still to do, deviations from this spec, open questions. Do not merge. Do not start another milestone.

When asked to address review comments: switch to the branch, make the changes, re-run the acceptance commands, push, reply to each comment with what changed, and stop. When the branch is behind `main`, `git fetch origin && git merge origin/main`, resolve conflicts, re-run the acceptance commands and push normally. Never rebase a pushed branch.

### 2.3 Branches, commits and pull requests

- **Branch names:** `p2/<milestone>-<slug>`, for example `p2/m2-3a-ch-companies`, `p2/m2-10b-splink-models`.
- **Commits:** Conventional Commits 1.0.0, `type(scope): summary`. Types as in Phase 1. Scopes: Phase 1's list plus `resolve` and `er`.
- **Pull request title:** `type(scope): summary [M2.x]`.
- **Pull request body:** the Phase 1 template, plus two sections when they apply: "Real-data run (operator)" with the command and its counts-only output, and "Matching impact" (rules, thresholds, policy or features changed, and the benchmark numbers before and after).
- **Labels:** always `agent` and `phase-2`; the squad label(s); `contract-change` for M2.1a to M2.1c; `data-source` for loaders; `er` for resolver work; `real-data-run` when the milestone has a real-data run. M2.0 creates the new labels.
- **Size:** at most 400 changed lines of code, tests and configuration, counted as in Phase 1 (`.github/pr-size-exclude.txt`). A milestone whose header has the row `| Size | exception (<reason>) |` may exceed it: `/open-pr` adds the `size-exception` label for that header form only. Any other milestone that would exceed the limit is split into `<id>-1`, `<id>-2` and so on, merged in that order, each with its own `PROGRESS.md` row; every part passes `make check`, the last part runs the whole acceptance list, and a milestone that depends on `<id>` waits until every part is `merged`.
- **Human owner:** every agent pull request names one accountable human: the squad mentor for squad work, the tech lead for contract and agent-kit work, the data steward for data-handling documents.

### 2.4 Verification standard

"Done" means: every acceptance command passed in this session, CI is green on the pull request, the pull request body shows the evidence (the commands and the meaningful lines of their output), and, where the milestone has a real-data run, either its counts-only output is in the pull request or the pull request says who will run it and the milestone row in `PROGRESS.md` says `pr-open (real-data run pending)`. Claims without output do not count.

### 2.5 Stop and ask

Stop, explain, and wait for a human when:

1. A value in `project.yaml` that the milestone needs is `TODO`.
2. Anything requires a secret, an account, a payment, an admin permission or a licence decision.
3. A fixture, test, log line, report or document would contain data about a real person or company, any value from a real record, or any OpenSanctions row.
4. A change would touch `contracts/**` or `graph/schema/**` outside an approved contract-change session (M2.1a to M2.1c).
5. The spec and reality disagree in a way that changes behaviour (for example a file format, a header, an enumeration or an API field differs from section 3 or a research note). Small mechanical deviations can be fixed and recorded instead.
6. An AML definition, threshold or legal statement has no source in `docs/sources/bibliography.yaml` or `docs/research/`.
7. An acceptance command still fails after three focused attempts.
8. Work would require pushing to `main`, force-pushing, deleting branches or tags, changing repository settings, or merging.
9. A real-data command would run on a machine that is not approved, for a profile not in `access.real_data_profiles`, before `access.data_protection_filed` is true, or in CI, Codespaces or a cloud session; or a command would load real records into the default Neo4j database.
10. Anything would change the merge policy (7.1.4), a deterministic rule (7.1.2), a cannot-link rule (7.1.3) or a threshold after ADR-0014 is accepted (the freeze on Thursday 29 October).
11. You are asked to change thresholds, rules or features after looking at evaluation labels, or to drop, re-draw or re-weight labelled pairs.
12. A loader would set a flag or a topic that its source does not state.

### 2.6 Never

- Never merge a pull request, push to `main`, force-push in any form, delete a remote branch, or change repository settings. The `guard_git.py` hook blocks these; never try to get around it.
- Never write learning logs, exit posts, self-assessments, assignment submissions, labels or review decisions for people.
- Never mark a typology `approved`, a contract `frozen`, an ADR `accepted` or a licence decision `confirmed`.
- Never read, print, grep, sample or query real records (G9), and never paste a real name, birth date, address or identifier into a pull request, an issue, a commit message or the chat. Use synthetic examples.
- Never fetch a list, register or leak data file with WebFetch, curl or wget; fetch documentation and schemas only (G9).
- Never run a human-only command (`neonradar er label`, `neonradar er review`, `neonradar api serve --real`), and never wrap a command in `script`, `expect`, `unbuffer` or `faketty` to make it look as if a terminal were attached.
- Never add `@neo4j-nvl/*`, GPL-licensed dependencies (for example `unidecode`, `pyarabic`), or vendor the GPL-3.0 Neo4j MCP binary.
- Never disable a test, lint rule, type check, hook or permission rule to make something pass without saying so in the pull request.
- Never invent an AML typology, regulation, threshold, file format, header, enumeration value, function signature or API field. Check the sources; if absent, stop and ask.
- Never write that an entity "is sanctioned", "is a PEP" or "is the same as" another unless the flag or the merge comes from the entity's own source records or an accepted rule (G8).

### 2.7 When the spec seems wrong

Facts in this document were verified on 18 October 2026. When a command, version, file format or API behaves differently:

1. Check the official source. Allowed domains: Phase 1's list (`code.claude.com`, `docs.claude.com`, `neo4j.com`, `github.com`, `pypi.org`, `npmjs.com`, `gov.uk`, `company-information.service.gov.uk`, `gleif.org`, `opensanctions.org`, `followthemoney.tech`, `icij.org`, `fatf-gafi.org`) plus `legislation.gov.uk`, `ico.org.uk`, `treasury.gov`, `ofac.treasury.gov`, `sanctionslistservice.ofac.treas.gov`, `un.org`, `europa.eu`, `parliament.uk`, `creativecommons.org`, `moj-analytical-services.github.io` (Splink documentation), `duckdb.org` and `raw.githubusercontent.com/opensanctions/rigour` (rigour's data files, for the M2.8 build script only). Reading documentation, a schema or an API description there (an XSD, a swagger file) is allowed. Downloading list, register or leak data is a real-data run (G9), never a WebFetch: M2.0 sets WebFetch to ask before it reaches the hosts that serve such files, and the hook blocks data URLs on them.
2. If the difference is mechanical (a renamed flag, a newer patch version, a header with different spacing), adapt, and record it under "Deviations from spec" in the pull request and in the milestone's row of `PROGRESS.md`.
3. If it changes behaviour, a contract, a licence position, the merge policy or a guardrail, stop and ask (2.5).
4. For network failures in `data fetch` or the officer fetch: retry with backoff up to three times, then stop that dataset, keep what was downloaded, and report it. Tests always use synthetic inputs.

### 2.8 Progress log format

`docs/build/PROGRESS.md` keeps its Phase 1 format. M2.0 appends one row per Phase 2 milestone with status `todo`. Status values gain one note form: `pr-open (real-data run pending)` until the operator's counts-only output is in the pull request. Each pull request edits only its own row.

### 2.9 Fixtures and test data

- Tests use synthetic inputs only and never use the network.
- Hand-written fixtures in a source's own format (a small UK Sanctions List XML file, an OFAC advanced XML file, PSC snapshot lines, a Free Company Data CSV) are allowed under `<package>/tests/fixtures/`, as long as every value in them is invented: invented names, `SY` company numbers, `QQ` postcodes, `SYN0` LEIs, the `ZZ` regime and `SYNP` passport numbers (M2.6, M2.9). Committed C1 fixtures under `data/fixtures/` keep Phase 1's rule that every id starts with `syn-`.
- The publishers' schemas (XSDs) and API descriptions are committed next to the fixtures that use them, so a test that validates against a schema reads the committed copy.
- A record that must look real to a test (an id such as `gbch-co-T0000001`, a name such as "Test Holder Ltd") is built in the test code at run time, never committed as a file.

---

## 3. Verified technical baseline (18 October 2026)

PHASE-1.md section 3 still applies. This section adds what Phase 2 needs and corrects what changed. Every version was checked against PyPI, npm or the official documentation on 18 October 2026, and the code facts were checked by running code. The four research notes in `docs/research/2026-10-18/` hold the sources and the reasoning: `er-splink.md` (Splink 5, DuckDB, evaluation), `names-addresses.md` (name, address and country keys), `sanctions-peps.md` (official lists, PEP sources, matching guidance) and `bulk-sources-loading.md` (Companies House and GLEIF bulk files, ICIJ, Neo4j loading, data protection).

### 3.1 Pinned versions (additions)

| Component | Pin | Notes |
|---|---|---|
| splink | `==5.0.*` (5.0.0, 28 September 2026) | Version 5 API only. An unreleased change on master (merged 12 October) will shift trained u values, so any lock bump of splink, duckdb or pyarrow is a model change: re-run `er bench` and say so in the pull request |
| duckdb | `==1.5.*` (1.5.6) | MIT, cp314 wheels. `2.0.0.dev` pre-releases exist on PyPI; never resolve with pre-releases allowed |
| pyarrow | `>=26,<27` (26.0.0) | Splink needs at least 18. Ships no type information: M2.0 adds the mypy override |
| sqlglot | `>=30.18,<31` | Splink's SQL dependency, pure Python |
| rigour | `==2.5.*` | The Arabic name index in `neonradar_keys` is built from rigour's data at the installed version's tag (M2.8), and a test fails when the installed rigour differs from the index's tag, so a lock bump cannot drift silently: rebuild the index and bump `RULES_VERSION`. rigour 2.5.0 imports `typing_extensions` without declaring it, so `keys` declares `typing-extensions>=4.12` itself (M2.8). Requires `python-stdnum` (LGPL-2.1-or-later, used unmodified from PyPI; decision 14 in 0.5): a published image or bundle that contains it must include the LGPL-2.1 text and its source or a written offer |
| normality | `==3.1.*` | Requires PyICU, which builds against ICU headers (PHASE-1.md 1.1); `pyicu-wheels` 2.15.2 is a documented fallback through a uv override (`names-addresses.md` 1) |
| anyascii | `==0.3.*` (0.3.3) | ISC. Cyrillic and Arabic folding for keys |
| typing-extensions | `>=4.12` | rigour 2.5.0 imports it without declaring it, so `keys` declares it (M2.8) |
| orjson | `==3.13.*` | PSC snapshot parsing (M2.3b) |
| defusedxml | `==0.7.*`, with `types-defusedxml` in the dev group | Every XML parser (M2.6); ruff `S314` rejects the standard library ones. Works on Python 3.14.6 (checked) |
| xmlschema | `==4.3.*` (dev group) | Validates list fixtures against the publishers' XSDs (M2.6) |
| `@neo4j-cypher/language-support` | `2.0.0-next.39` (exact) | Offline Cypher 5 lint (M2.0) |
| neo4j driver | unchanged (`>=6.4,<7`; 6.4.1 current) | `neo4j-rust-ext==6.4.1.0` is a faster drop-in ("3x to 10x" in the driver manual); optional, M2.13 may try it |

### 3.2 Known traps for AI-written code (additions)

| Area | Trap | Do this instead |
|---|---|---|
| Splink 5 | Training data mixes v3 and v4 names (`exact_match`, `DateComparison`, `compare_two_records`, `find_matches_to_new_records`, `as_record_dict`, `bf_` columns, salting, `db_api=` on `Linker`) | Register inputs with `db_api.register(table, dataset_display_name=...)`, pass the result to `Linker`; read results with `as_record_list()` or `as_pyarrow_table()`; weights are `mw_` (log2). The upgrade notes and `/splink/llms.txt` describe version 5 (`er-splink.md` 5) |
| Splink 5 | `NameComparison` always adds term-frequency adjustment; `configure(term_frequency_adjustments=False)` does not remove it | Build name comparisons from `comparison_level_library` levels (M2.10b) |
| Splink 5 | Null levels test `IS NULL`, and an empty DuckDB list is not NULL, so an empty array counts as disagreement | Write every empty list as NULL in the feature tables (7.1.5) |
| Splink 5 | `DateOfBirthComparison` misfiles `YYYY-MM` strings (Levenshtein puts 1980-05 and 1990-05 one edit apart) | Custom birth levels on arrays of dates, months and years (7.1.5) |
| Splink 5 | `DuckDBAPI` has no memory or thread arguments | Configure them on the `duckdb.connect(..., config=...)` connection |
| Splink 5 | Clustering is connected components with no cannot-link rules | NeonRadar's own `cluster.py` (7.1.6) |
| Splink 5 | `estimate_u_using_random_sampling` warns at its default `max_pairs` of 1e6; with more than one DuckDB thread, EM m values differ at the 1e-15 level between runs | Set `max_pairs` from `er.yaml`; one thread in tests and the benchmark; round probabilities to 9 decimals before ordering |
| Splink 5 | The saved model JSON carries a random `linker_uid`; the HTML dashboards fetch web fonts and `chart.save()` loads Vega from a CDN | Set `linker_uid` in `SettingsCreator`; no dashboards on real data |
| rigour 2.5 | `from rigour.text import text_scripts` fails | `from rigour.text.scripts import text_scripts` |
| rigour and normality | rigour does not unify Arabic alef, ta marbuta, alef maqsura or hamza carriers; `normality.ascii_text` turns modifier-letter apostrophes into "?"; fuzzy territory lookups give confident wrong countries | Use `neonradar_keys` (M2.8), never the libraries directly for keys |
| Official lists | OFAC answers 403 without a User-Agent; OFAC's XML namespace changed in 2024; the UN XML URL redirects to a signed address valid for one hour; the EU file is generated on request and answers HTTP 500 in bursts | Shared client with User-Agent; namespace-agnostic tags; never store a redirect target; long timeouts and retries (M2.6) |
| UK Sanctions List | The OFSI Consolidated List closed on 28 January 2026; one person can have several Unique IDs, and people designated since then get no OFSI Group ID; dates contain literal `dd/mm` placeholders and are day first | Load the UK Sanctions List only; group designations by OFSI Group ID, then by UN reference number, else keep one record per Unique ID for the resolver to compare (M2.6a; X6 in 7.1.3); `common.parse_dmy` |
| Companies House bulk | 14 header cells start with a space; rows with 56 fields and empty rows occur; names contain HTML character references | Strip header cells, map by name, skip and count bad rows, decode only complete references (M2.3a) |
| PSC snapshot | The last line is a totals record without `company_number`; DuckDB's JSON auto-detection fails on it | Parse with orjson line by line and use the totals as a completeness check (M2.3b) |
| PSC bands | The API's long descriptions ("more than 75%") contradict the statute | Bands `(25, 50]`, `(50, 75)`, `[75, 100]`, `(25, 100]` with open and closed bounds (5.1, M2.3b) |
| Officers API | `person_number` is on `/company/{n}/officers` items, not on `/officers/{id}/appointments` items | Fetch the company officer lists (M2.3c) |
| GLEIF | `lei2/latest` served an older publish than the combined `publishes/latest`; Level 2 relationships are accounting consolidation | Use the combined endpoint; map to `CONSOLIDATES`, never to `OWNS` (M2.4) |
| DuckDB | Core DuckDB cannot read zip files; the `zipfs` extension downloads from the internet when installed | Read zip members with Python's `zipfile` (all loaders do) |
| DuckDB | Spill files in `temp_directory` hold the values being processed, so during a real run they can hold real names and birth dates, and a crashed run leaves them behind | `temp_directory` is `duckdb_tmp_dir(profile, run_id)` from `layout.py` (under `data/cache/real/` for a real profile), deleted in a `finally` block; `doctor` warns about leftovers and the purge removes them (M2.2, M2.10b) |
| Neo4j 5.26 | `ON ERROR RETRY` exists only from 2025.03; `CALL { } IN TRANSACTIONS` runs only in implicit transactions; `neo4j-admin database import` on Community needs a stopped server and an empty database | `session.run()` for batched deletes (L9); the online loader (decision 6 in 0.5) |
| Cypher | `null` sorts after every value in ascending order, so `ORDER BY x DESC` puts nulls first (possible matches without a probability, for example) | `ORDER BY x IS NULL, x DESC` (M2.12) |

### 3.3 Data sources and licences (Phase 2)

| Dataset slug | Source | Licence and terms | Commercial use | Personal data | Phase 2 use |
|---|---|---|---|---|---|
| `gb_companies_house` | Free Company Data Product (monthly), PSC snapshot (daily), officers API (the officer bulk products 195, 198 and 216 exist only on request, with unpublished terms) | As PHASE-1.md 3.3. The bulk pages say the files are "provided free of charge and will not be supported" | Yes | Yes: reusers "become controllers" (Companies House personal information charter) | Production loader with slices (M2.3) |
| `gleif_lei` | GLEIF Golden Copy (LEI-CDF 3.1 and RR-CDF 2.1 CSV) | CC0 1.0; no endorsement may be implied | Yes | No | Production loader (M2.4) |
| `icij_offshore_leaks` | ICIJ Offshore Leaks Database | As PHASE-1.md 3.3 (ODbL 1.0 and CC BY-SA 3.0) | Yes, with citation and the ODbL duties | Yes | Production loader; for `uk-sample` a slice tied to the profile's postcode districts by default (`district-linked`, M2.5) |
| `gb_fcdo_sanctions` | UK Sanctions List (FCDO), the only UK list since 28 January 2026 | OGL v3.0, which "does not cover: personal data in the Information" and gives no right to suggest official status | Yes | Yes | M2.6a |
| `us_ofac_sdn` | OFAC SDN List, advanced XML | CC0 1.0 in OFAC's data catalogue (`data.json`, rights "No restrictions on public access"); the data.gov record adds "This data is in the public domain and may be used without restriction." | Yes | Yes | M2.6b |
| `un_sc_sanctions` | UN Security Council Consolidated List | UN website terms: download "for the User's personal, non-commercial use"; no licence for the list found | Unclear: only with written permission | Yes | Loader built (M2.6c); runs only with permission |
| `eu_fsf` | EU Financial Sanctions Files, XML 1.1 | Commission reuse policy, Decision 2011/833/EU ("for commercial or non-commercial purposes", with acknowledgement). CC BY 4.0 is the Commission's default licence since 2019, but no licence statement attached to the files themselves was found, so the registry records the Decision (5.1) | Yes, with attribution | Yes | M2.6d |
| `gb_parliament_members` | UK Parliament Members API | Open Parliament Licence v3.0; personal data and photographs are outside it | Yes, with attribution | Yes | Optional PEP source (M2.6e) |
| `opensanctions_default` | OpenSanctions | As PHASE-1.md 3.3 | Licence required | Yes | Only where `access.opensanctions` allows it (M2.7) |
| `nr_synthetic` | NeonRadar generator | Apache-2.0 | Yes | No | Fixtures, the ER benchmark (M2.9) |

**Identifiers behind the deterministic rules.**

| Rule | Facts |
|---|---|
| D1 | Companies House numbers are 8 characters: digits, or a prefix and 6 digits; the prefixes are in `neonradar_keys.ids.CH_PREFIXES` (`bulk-sources-loading.md` 2.6; `SY` is not one of them, so the synthetic numbers cannot collide). A number with any other prefix is not a UK company number. Registry fields of corporate PSCs and officers are free text that "isn't guaranteed to be correct", about a quarter of UK-looking numbers lack their leading zeros, and some are foreign (`bulk-sources-loading.md` 3.4), hence the UK test and the name check (M2.3b, 7.1.2). A number in a sanctions entry's free text counts only when a company-number label and a UK register stand next to it (M2.6a) |
| D2 | LEIs carry ISO 17442 check digits (`is_valid_lei`) |
| D3 | `person_number` is a string; community examples are 12 digits, which posts read as an 8-digit person part and a 4-digit counter, and one party has been seen under several numbers; Companies House has not confirmed either (`bulk-sources-loading.md` 5). So D3 uses the first 8 characters, also requires the two records' names to agree (the name check), and a different number is never evidence against a match |
| D4 | The UN reference is `UNReferenceNumber` on the UK list, `sanctionEntity@unitedNationId` on the EU list (empty in every record the research read, so its fill rate is reported) and `REFERENCE_NUMBER` on the UN list. OFAC data carries none (`sanctions-peps.md` 6). With the UN list off (the default), D4 may therefore link little or nothing: the UK loader already groups designations that share a UN reference (M2.6a), and UK and EU entries for one listing are compared by the probabilistic model under P6 (7.1.4). With the UN list enabled, D4 links UK and UN entries |

**Data protection** (analysis from the research notes, not legal advice; the data steward owns the conclusions in ADR-0018, `docs/data/real-data-handling.md` and `docs/data/dpia/`): every list and register above with personal data makes whoever loads it a controller, Robotat included whenever its staff and interns run a real profile, so the documents in 1.1 come before the first real run; UK GDPR Article 14 applies to data not obtained from the person (since 5 February 2026 the disproportionate-effort exemption is Article 14(5)(e), and Article 14(7) then requires appropriate measures "including by making the information available publicly"); a designation may itself be criminal offence data (Article 10, DPA 2018 section 10(5)); dropping free-text reasons (off by default, M2.6 rule 7) reduces this but does not remove the need for a Schedule 1 condition; NeonRadar ships code, not data, and each deploying organisation needs its own lawful basis.

### 3.4 Formulas

**Wilson score interval** (Wilson 1927; NIST/SEMATECH e-Handbook 7.2.4.1), for `k` correct out of `n` labels, `p = k/n`, `z = 1.959964` at 95 percent:

```text
centre     = (p + z^2 / (2n)) / (1 + z^2 / n)
half-width = (z / (1 + z^2 / n)) * sqrt( p(1 - p)/n + z^2 / (4 n^2) )
interval   = [centre - half-width, centre + half-width]
             the lower bound is exactly 0 when k = 0, the upper bound exactly 1 when k = n;
             n = 0 is an error
```

Worked example: 180 of 200, `p = 0.900`, centre 0.8925, half-width 0.0419, interval [0.8506, 0.9343] (`er-splink.md` 9). `stats.py` (M2.10c) implements it and its tests check this example. With `u` labels marked `unsure`, the same formula applied to `k` out of `n + u` gives the precision if every unsure pair were wrong, which the report gives as a bound (7.3).

**Cohen's kappa** (Cohen 1960) for two labellers over the same pairs: `kappa = (p_o - p_e) / (1 - p_e)`, where `p_o` is the share of pairs with equal labels and `p_e` the sum over the labels (`same`, `different`, `unsure`) of the product of the two labellers' shares for that label.

**Fellegi-Sunter match weight** (Fellegi and Sunter 1969, as Splink computes it): for a pair, `weight = log2(lambda / (1 - lambda)) + sum over comparisons of log2(m / u)` at the level the pair reaches, where `lambda` is `probability_two_random_records_match`, `m` the probability of that level among true matches and `u` among non-matches; `probability = 2^weight / (1 + 2^weight)`.

**Effective share along an ownership path** (5.3): the products of the lower and of the upper bounds of the bands on the path; a product's bound is open if any factor's bound is open, because for positive numbers a product reaches its bound only when every factor reaches its own. Example: `(25, 50]` times `[75, 100]` is `(18.75, 50]`. It is a NeonRadar calculation for teaching, not a figure any register records: the PSC register may already record an indirect holding in full, and sanctions ownership tests do not multiply shares down a chain (OFAC passes blocked status from entity to entity, FAQ 401; the UK and EU guidance read gives no chain example, `sanctions-peps.md` 2.8), so it is never presented as the result of such a test (7.2).

### 3.5 Corrections to Phase 1

| Phase 1 said | Correct | Source |
|---|---|---|
| Use the long `natures_of_control` descriptions (`sources-ch-gleif.md` A2) | The statute matches the short descriptions: `50-to-75` excludes 75 and `75-to-100` includes it | `bulk-sources-loading.md` 4.2 and 12 |
| Free Company Data field names from the PDF (`CountryofOrigin`, `AccountingRefDay`) | The file's literal headers are `CountryOfOrigin`, `Accounts.AccountRefDay` and so on, 14 of them with a leading space | `bulk-sources-loading.md` 2.2 |
| The PSC totals line and overseas entity beneficial owners were unverified | Both confirmed by community evidence | `bulk-sources-loading.md` 3.2, 3.7 |
| Officer lists cap at 100 items | Not in today's service code; officer appointments cap at 50 | `bulk-sources-loading.md` 5 |
| `driver.execute_query` can run `CALL { } IN TRANSACTIONS` (`neo4j.md` 6) | It cannot; use `session.run()` (PHASE-1.md 3.2 already says so) | `bulk-sources-loading.md` 8.1 |

---

## 4. Architecture and repository layout

### 4.1 Components and data flow

```text
 ingest/profiles/<profile>.yaml        which sources, which slice, which steps
            |
            v
 neonradar data fetch    (ingest)  ->  data/cache/real/sources/<dataset>/<product>/<version>/
            |                          downloads + download.json (synthetic profiles skip this step)
            v
 neonradar ingest build  (ingest)  ->  C1 records: data/cache/<real|synthetic>/records/<profile>/<dataset>/
            |                          *.ftm.jsonl + *.manifest.json (+ *-hints.csv from ICIJ)
            v
 neonradar er run        (resolve) ->  resolution run: data/cache/<real|synthetic>/resolution/<profile>/<run_id>/
            |                          canonical.csv, candidates.jsonl, conflicts.jsonl, run.json, models
            v
 neonradar graph load    (graph)   ->  Neo4j, C2 1.1.0: canonical entities, :SourceRecord, RESOLVED_TO,
   --resolution <run>                  POSSIBLY_SAME_AS; relationships re-pointed to canonical ids
            |                          synthetic profiles: the default instance (neo4j, port 7687)
            |                          real profiles: only the separate instance (neo4j-real, port 7688)
            v
 neonradar graph verify  (graph)   ->  invariants I1 to I14 (--real: on neo4j-real, counts only)
            |
            +--> detect/ (Phase 3) reads the same graph; its overlay references record ids
            +--> api/ (C3 1.1.0): ownership, paths, resolution  ->  ui/ (Phase 5), copilot/ (Phase 4)
```

`make load PROFILE=<name>` runs six steps in order (fetch, build, resolve, migrate, load, verify), records the time of each, and prints a counts-only summary (M2.13).

**Two databases.** The default Neo4j instance (`neo4j`, ports 7474 and 7687 on localhost) only ever holds synthetic data. Real profiles load only into a second instance, `neo4j-real` (Compose profile `real`, ports 7475 and 7688 on localhost, its own volume `neo4j-real-data`, and one database named `realdata`, so a query or load sent to the wrong instance fails because the database does not exist), which M2.0 adds; the loader refuses real records on the default instance and refuses a load that mixes synthetic and real records (M2.11). The API on port 8000, the UI, `make e2e`, `make demo-mini` and the Neo4j MCP server use the default instance, so the agent can query them freely. `neonradar api serve --real` (humans only, port 8001, M2.12) serves the real one, and the agent never reaches it (G9).

The matching keys (`neonradar_keys`) are pure functions shared by three packages: the loaders use them for address record ids, the resolver for its features, and the graph loader for `address_key` and the Latin search names. Nothing in `keys/` does I/O.

### 4.2 Repository changes at the end of Phase 2

```text
neonradar/
  keys/                         NEW workspace member: neonradar_keys (names, orgs, addresses,
                                postcodes, countries, identifiers); pure functions (squad: graph)
  resolve/                      NEW workspace member: neonradar_resolve (features, rules, Splink models,
                                constrained clustering, policy, decisions, labelling, precision)
    config/er.yaml              thresholds, caps, training and DuckDB settings (frozen at the ER freeze, 29 Oct)
    models/                     committed Splink settings (no trained parameters from real data)
  ingest/
    profiles/                   demo.yaml, uk-tiny.yaml, uk-sample.yaml (NEW)
    src/neonradar_ingest/data/  data manager: layout, profiles, downloads, status, retention, purge (NEW)
    src/neonradar_ingest/sources/companies_house/   bulk.py, psc.py, officers.py, slice.py (NEW)
    src/neonradar_ingest/sources/gleif/             golden_copy.py (NEW)
    src/neonradar_ingest/sources/icij/              full.py, slice.py (NEW)
    src/neonradar_ingest/sources/lists/             common.py, bounds.yaml, gb_fcdo.py, us_ofac.py,
                                                    un_sc.py, eu_fsf.py (NEW)
    src/neonradar_ingest/sources/parliament/        members.py (NEW, optional M2.6e)
    src/neonradar_ingest/synth/erbench.py           synthetic ER benchmark generator (NEW)
  graph/
    schema/migrations/0002_resolution.cypher        (NEW, through M2.1b)
    src/neonradar_graph/loader.py, mapping.py      resolution-aware, routes real loads to neo4j-real (M2.11)
    src/neonradar_graph/verify.py                  invariants I1 to I14 (NEW)
    src/neonradar_graph/ownership.py               ownership and path queries (NEW, M2.12)
  cli/src/neonradar_cli/        data, er, synth and load commands; summary.py (counts-only summaries),
                                tty.py (human-only commands), redact.py (error redaction on real
                                profiles) (NEW)
  data/fixtures/er-bench/       synthetic benchmark records and ground truth (NEW, committed)
  docs/
    er/                         README.md (method and policy), labelling-guide.md (NEW)
    data/er/                    benchmark.md, precision-<date>.md: counts and rates only (NEW)
    data/benchmarks/            load and query timings: counts only (NEW)
    data/dpia/                  Robotat's data protection documents (data steward, 1.1) (NEW)
    data/real-data-handling.md, data/real-data-machines.md, data/profiles.md (NEW)
    build/PHASE-2.md, build/phase-2-reconciliation.md, build/reports/phase-2.md
    research/2026-10-18/        Phase 2 research notes
    team/assignment-3.md        labelling assignment (NEW)
  scripts/cypher-lint/          Cypher linter for CI (NEW, M2.0)
  compose.yaml                  adds the neo4j-real service under the Compose profile real (M2.0)
  THIRD_PARTY_NOTICES.md        notices for dependencies and reused code (NEW, M2.0)
  .claude/hooks/guard_real_data.py, .claude/agents/data-guardian.md, .claude/rules/real-data.md,
  .claude/rules/er.md           (NEW, M2.0)
```

Both new members follow the Phase 1 layout (`<dir>/pyproject.toml`, `<dir>/src/neonradar_<dir>/`, `<dir>/tests/`, `<dir>/CLAUDE.md` of at most 20 lines).

**Dependencies.** `keys` depends on `rigour`, `normality`, `anyascii` and `typing-extensions` only (rigour 2.5.0 imports `typing_extensions` without declaring it, M2.8). `ingest`, `graph` and `resolve` depend on `keys`. `resolve` depends on `contracts`, `graph` (for the mapping tables, not the database) and `keys`, plus `splink`, `duckdb` and `pyarrow`, and never imports `neonradar_ingest` or `neonradar_cli`. `graph` never imports `neonradar_ingest`, `neonradar_resolve` or `pyarrow`. `cli` depends on every member and is where the pieces meet: it resolves profiles, folders and summaries (from `ingest`), passes the record folders to `neonradar_resolve.run.run(record_dirs, run_dir, config)` and a run folder to the graph loader (`ResolutionMap.load(run_dir)`, M2.11), and wipes the real database for `neonradar data purge --graph`. So the packages form no cycle at run time; only `graph`'s `dev` dependency group lists `resolve`, for one integration-test fixture (M2.11). `api` depends on `graph` but not on `resolve`, and the graph loader reads `RESOLVED_TO` features from `canonical.csv`, not from Parquet, so the API image stays free of Splink, DuckDB and PyArrow.

### 4.3 Ownership map additions

| Path | Owner (CODEOWNERS) | Required reviewer for |
|---|---|---|
| `keys/`, `resolve/` | `nr-graph` | matching keys, resolver |
| `resolve/config/er.yaml` | `nr-graph` and the tech lead | thresholds, caps, training and DuckDB settings |
| `ingest/profiles/` | `nr-ingest` and the data steward | which real data a profile loads |
| `docs/er/`, `docs/data/er/` | `nr-graph` | method, policy, published figures |
| `docs/data/real-data-handling.md`, `docs/data/real-data-machines.md`, `docs/data/dpia/` | data steward | real-data rules, approved machines, data protection documents |
| `data/fixtures/er-bench/` | `nr-graph` | benchmark fixture |
| `.claude/hooks/guard_real_data.py`, `.claude/agents/data-guardian.md`, `.claude/rules/real-data.md`, `.claude/rules/er.md` | tech lead | agent kit |
| `THIRD_PARTY_NOTICES.md` | tech lead | dependency and reused-code notices |

`scripts/generate_codeowners.py` keeps its ordering rule: a specific path comes after the broader one that contains it (`resolve/config/er.yaml` after `resolve/`).

### 4.4 Naming conventions added in Phase 2

**Record ids.** Every id follows PHASE-1.md 4.4 (`<prefix>-<rest>`, at most 120 characters). Where a Phase 1 spike already chose an id form, it stays; M2.0 records any difference.

| Source | Record | Id | Example or note |
|---|---|---|---|
| Companies House bulk data | company | `gbch-co-<company number>` | `gbch-co-01800000` (company number normalised as in 7.1.2, D1) |
| Companies House (any) | address | `gbch-addr-<first 20 hex of sha1(address_key)>` | one record per distinct address key in the dataset |
| PSC snapshot | person, corporate or legal-person PSC, beneficial owner | `gbch-psc-<psc id>` | psc id: the last path segment of `data.links.self` |
| PSC snapshot | ownership band | `gbch-ownership-<first 20 hex of sha1 of psc record id, company number, interest key>` | edge id form from PHASE-1.md 4.4; one record per interest of a PSC in a company; interest keys (`natures.Interest.key`, M2.3b): `shares`, `surplus-assets`, `shares-as-trust` (an overseas entity's beneficial owner who is a trustee) |
| PSC snapshot | control | `gbch-control-<first 20 hex of sha1 of psc record id, company number, interest key>` | interest keys `voting`, `appointment`, `influence`, `nominee`, the overseas trustee forms such as `voting-as-trust`, and `trust-or-firm-<right>-<capacity>` (for example `trust-or-firm-shares-trust`; M2.3b) |
| Officers API | officer | `gbch-off-<officer id>` | officer id from `links.officer.appointments` (Phase 1 form) |
| Officers API | directorship | `gbch-directorship-<first 20 hex of sha1 of officer id, company number, role, appointed_on>` | |
| GLEIF Golden Copy | legal entity | `gleif-<LEI>` | `gleif-549300OWFMSO9NYV4H90` |
| GLEIF Golden Copy | relationship | `gleif-ownership-<first 20 hex of sha1 of child LEI, parent LEI, relationship type>` | accounting consolidation, `nr.consolidation` (M2.4) |
| GLEIF Golden Copy | address | `gleif-addr-<first 20 hex of sha1(address_key)>` | as for Companies House addresses |
| ICIJ | node | `icij-<node_id>` | Phase 1 form |
| ICIJ | relationship | `icij-<schema in lower case>-<first 20 hex of sha1 of start, end, rel_type, link>` | |
| UK Sanctions List | designated person or entity | `uksl-g<OFSI group id>`; without a Group ID `uksl-un-<UN reference number>`; otherwise `uksl-<unique id>` | designations grouped by OFSI Group ID, then by UN reference number (people designated since 28 January 2026 get no Group ID); a record of the last two forms may be one of several designations of one person under different regimes, so X6 does not keep it apart from other UK records (M2.6a, 7.1.3) |
| OFAC SDN | party | `ofac-<uid>` | the SDN UID (`DistinctParty@FixedRef`) |
| OFAC SDN | relationship | `ofac-<schema in lower case>-<first 20 hex of sha1 of from, to, relation type>` | M2.6b |
| UN Consolidated List | entry | `unsc-<reference number>` | the UN reference number, normalised with `un_reference` |
| EU FSF | sanctioned entity | `eufsf-<logicalId>` | |
| any sanctions list | sanction | `<prefix>-sanction-<first 20 hex of sha1 of party id, "\|", designation key>` | one `Sanction` per designation: the UK unique id, the OFAC sanctions entry id, the UN reference number, the EU regulation `logicalId` (`common.sanction_id`) |
| UK Parliament | member, post, occupancy | `ukparl-<member id>`, `ukparl-pos-commons`, `ukparl-pos-lords`, `ukparl-pos-gov-<post id>`, `ukparl-occupancy-<first 20 hex of sha1 of member id, post id, start date>` | M2.6e |
| OpenSanctions (gated) | entity | `os-<OpenSanctions id>` | Phase 1 form |
| canonical, merged | entity | `nr-<anchor record id>` | `nr-gbch-co-01800000`; the anchor rule is in 7.1.6 |

Every hashed id hashes its parts joined with `|` (UTF-8) and keeps the first 20 hex characters of the SHA-1, as `common.sanction_id` does.

An entity built from one record keeps that record's id as its node id. Only an entity merged from two or more records gets an `nr-` id. The API accepts either id (PHASE-1.md C3, "accepts a canonical id or any id in `referents`").

**Other names.**

| Thing | Convention | Example |
|---|---|---|
| Profile | lower-case words joined by hyphens | `uk-sample` |
| Resolution run id | `er-<UTC yyyymmddThhmmss>-<4 hex>` | `er-20261102T091500-3b7e` |
| Download product | one name per separately published file set of a dataset: `companies` (monthly Free Company Data) and `psc` (daily snapshot) for `gb_companies_house`, `golden-copy` for `gleif_lei`, `main` for every other dataset | `sources/gb_companies_house/psc/2026-10-18/` |
| Download version | the source's own version, else the download date | `2026-10-01` (Companies House bulk), a GLEIF publish timestamp |
| Rule ids | `D1` to `D7` deterministic, `X1` to `X8` cannot-link, `P1` to `P6` policy (7.1) | |
| Human handle in labels and decisions | the GitHub handle with `@` | `@example` |

### 4.5 Data directories

Everything under `data/cache/` is gitignored. Real and synthetic outputs live in separate trees so that the agent can inspect synthetic runs freely while the guards in M2.0 keep it out of real data.

```text
data/cache/
  real/                                   REAL DATA: the agent never reads anything here (G9)
    sources/<dataset>/<product>/<version>/  downloads and download.json, shared by every real profile;
                                          the two newest complete versions are kept per dataset and product
    api/gb_companies_house/officers/      cached officer API responses
    api/gb_parliament_members/            cached Members API responses (M2.6e)
    records/<profile>/<dataset>/          C1 records and manifests
    resolution/<profile>/<run_id>/        resolution runs
    resolution/<profile>/LATEST           id of the newest complete run (er run writes it last)
    labels/<profile>/<run_id>/            sample.jsonl, <handle>.jsonl (human labels; access.label_days)
    work/<profile>/<dataset>/             a build's intermediate files: indexes (deleted after a successful
                                          build unless --keep-work) and slice.csv (kept until the next
                                          slice step replaces it)
    duckdb-tmp/<run_id>/                  DuckDB spill files of a real run (deleted when the run ends)
    logs/                                 full tracebacks of failed real-profile commands (redaction guard)
    decisions.jsonl                       human same / different decisions
  synthetic/
    records/<profile>/<dataset>/          synthetic profile outputs (for example demo)
    resolution/<profile>/<run_id>/        (and resolution/<profile>/LATEST)
    labels/<profile>/<run_id>/            labels on synthetic runs (tests, the labelling tool's demo)
    er-bench-<size>/                      the generated ER benchmark (M2.9, M2.10a)
    duckdb-tmp/<run_id>/
    decisions.jsonl
  reports/<profile>/                      counts-only summaries of every command (the agent may read these)
  spikes/                                 Phase 1 spike output (real data; same rule as real/)
```

`neonradar_ingest.data.layout` names every path: `sources_dir(dataset, product, version)`, `records_dir(profile, dataset)`, `resolution_dir(profile, run_id)`, `latest_run(profile)`, `labels_dir(profile, run_id)`, `decisions_file(profile)`, `duckdb_tmp_dir(profile, run_id)`, `logs_dir()`, `work_dir(profile, dataset)`, `reports_dir(profile)`, `officer_cache_dir()`, `parliament_cache_dir()` and `bench_dir(size)`; `resolution_dir`, `latest_run`, `labels_dir`, `duckdb_tmp_dir` and `decisions_file` also accept the synthetic pseudo-profiles `er-bench-small` and `er-bench-large`. A synthetic profile never opens a path under `data/cache/real/`. Retention: `access.real_data_days` governs `real/`, except the label files (`access.label_days`); Phase 1's `access.spike_cache_days` governs `spikes/`.

The real Neo4j instance keeps its data in the Docker volume `neo4j-real-data`, outside `data/cache/`. `neonradar data purge --graph` stops `neo4j-real` and deletes that volume: a volume-level wipe, which also removes Neo4j's transaction logs and store files, where deleted nodes would otherwise linger. Phase 1's `make reset` (`docker compose down -v`) may also remove that volume, depending on the Compose version; that loses only data the operator can load again.

Every Phase 2 command that touches real data writes its summary (counts, timings, rates, versions, thresholds; never a value from a record) to `data/cache/reports/<profile>/<command>-<UTC timestamp>.json` and prints the same summary. That folder is the only place under `data/cache/` the agent reads for a real profile. Manifests and `download.json` files also hold no person data (M2.2 enforces it, and URLs are stored without their query strings), but they stay inside `real/`, so the agent sees their content only through the summaries.

---

## 5. Contract changes in Phase 2 (version 1.1.0)

The four contracts are defined in PHASE-1.md section 5 and in `contracts/C1-record.md` to `contracts/C4-alert.md`. This section lists only what Phase 2 changes. Every change is additive (a minor version under PHASE-1.md 5.0): no field is renamed or removed and no meaning changes, so everything that was valid under 1.0.0 stays valid.

| Contract | Version after Phase 2 | Milestone | What changes |
|---|---|---|---|
| C1 record | 1.1.0 | M2.1a | Four sanctions datasets and the UK Parliament dataset; two optional dataset fields (`kind`, `anchor_priority`); five new `nr` keys (`ch_person_number`, `psc_statements`, `accounts_category`, `share_pct_min_exclusive`, `share_pct_max_exclusive`) and three wider ones (`synthetic_kind` gains `list` and `leak`, `is_nominee` may sit on `Ownership`, the share band keys may sit on `Control`); `nr.v` may be `"1.1"` |
| C2 graph schema | 1.1.0 | M2.1b | `:SourceRecord` defined; `RESOLVED_TO` properties extended; new relationship `POSSIBLY_SAME_AS`; new entity and company properties; open or closed share bounds and a nominee flag on `OWNS`; voting-rights bands on `CONTROLS`; migration `0002_resolution.cypher`; loader rules L8 to L17; invariants I7 to I14 |
| C3 API | 1.1.0 | M2.1c | New endpoint `GET /api/v1/entities/{entity_id}/resolution`; `PathRef` says whether each effective share bound is open or closed; `PossibleMatch.rule`; exact semantics and every response declared for the ownership, paths and resolution endpoints (implemented in M2.12); the Phase 2 wording-lint patterns and an updated real data notice |
| C4 alert | 1.0.0 (unchanged) | none | Evidence ids are canonical node ids (already true: C2 ids) |

`neonradar_contracts.versions` becomes `RECORD = "1.1.0"`, `GRAPH_SCHEMA = "1.1.0"`, `API = "1.1.0"`, `ALERT = "1.0.0"`, `CONTRACTS = "1.1.0"`.

### 5.0 The change procedure for Phase 2

The freeze tag `contracts-v1.0.0` stays where it is, so the guard hook and the CI label check (PHASE-1.md 5.0) keep protecting `contracts/**` and `graph/schema/**`. For each of the three changes:

1. The operator opens a `contract-change` issue with the text below (on Friday 23 October, after Gate 1, or first thing on Monday 26 October).
2. The tech lead approves it in a comment ("Approved for M2.1a"). The data steward also approves the C1 issue, because it adds licence fields, and the C3 issue, because it changes the real data notice.
3. The tech lead adds `{"env": {"NR_ALLOW_CONTRACT_CHANGE": "1"}}` to `.claude/settings.local.json` and starts a fresh Claude Code session.
4. `/milestone M2.1a` (or `b`, `c`) follows the `/contract-change` skill: bump the version, update `contracts/CHANGELOG.md`, regenerate the JSON Schemas and the OpenAPI snapshot (`make contracts`), add the new migration for C2, update every consumer and test in the same pull request, label it `contract-change`.
5. After the pull request is open, the tech lead removes the setting.
6. When M2.1a, M2.1b and M2.1c are all merged, the tech lead runs `make check && make contracts-check` on `main` and creates the tag: `git tag -a contracts-v1.1.0 -m "NeonRadar contracts v1.1.0 (Phase 2)" && git push origin contracts-v1.1.0`.

Issue texts (copy them as they are):

```markdown
Title: Contract change: C1 record 1.1.0 (sanctions and PEP datasets, dataset kinds, nr keys)

Classification: minor (additive and optional). Milestone: M2.1a, PHASE-2.md 5.1.
Change:
- contracts/datasets.yaml: add gb_fcdo_sanctions, us_ofac_sdn, un_sc_sanctions, eu_fsf and
  gb_parliament_members with licence fields from PHASE-2.md 5.1; add optional fields `kind`
  and `anchor_priority` to every dataset; commercial_use may be "permission-required";
  status becomes active for gb_companies_house, gleif_lei and icij_offshore_leaks.
- nr extension: add ch_person_number (string), psc_statements (list of strings),
  accounts_category (string), share_pct_min_exclusive and share_pct_max_exclusive (booleans);
  synthetic_kind also accepts "list" and "leak"; is_nominee is also allowed on Ownership;
  share_pct_min, share_pct_max and the two exclusive flags are also allowed on Control;
  nr.v may be "1.0" or "1.1".
- Manifest: record_contract may be "1.0.0" or "1.1.0".
Consumers: ingest loaders (new), graph mapping (new company, OWNS and CONTROLS properties),
synthetic generators (M1.8e, M2.9), resolver (new).
Compatibility: every 1.0 record and manifest stays valid.
Approvals needed: tech lead (contract), data steward (licence fields).
```

```markdown
Title: Contract change: C2 graph schema 1.1.0 (entity resolution)

Classification: minor (additive). Milestone: M2.1b, PHASE-2.md 5.2.
Change: define :SourceRecord; extend RESOLVED_TO; add POSSIBLY_SAME_AS; add entity
properties cluster_size, resolution, names_latin, names_latin_text; add company properties
psc_statements, accounts_category; add OWNS properties share_min_exclusive,
share_max_exclusive and is_nominee (false when absent); add CONTROLS properties
share_pct_min, share_pct_max, share_min_exclusive and share_max_exclusive; new migration
0002_resolution.cypher (one constraint, two indexes, the entity_names full-text index rebuilt
over names_text and names_latin_text); loader rules L8 to L17 (L17: real data goes to a
separate Neo4j instance); invariants I7 to I14.
Consumers: graph loader and mapping, API search (same index name), detectors (no change
needed), UI (new relationship type in subgraphs).
Compatibility: Phase 1 loads without a resolution run behave exactly as before.
Approval needed: tech lead.
```

```markdown
Title: Contract change: C3 API 1.1.0 (resolution endpoint; ownership and paths semantics)

Classification: minor (additive). Milestone: M2.1c, PHASE-2.md 5.3.
Change: add GET /api/v1/entities/{entity_id}/resolution with ResolutionMember,
PossibleMatch (with rule) and ResolutionResponse; add effective_share_min_exclusive and
effective_share_max_exclusive to PathRef; fix the semantics of /ownership and /paths
(effective shares, ordering, limits, default relationship types, timeout); declare every
response the three routes return (200, 404, 422, 503); append the PHASE-2.md 7.2 patterns to
contracts/wording/forbidden-terms.txt; add contracts/wording/real-data-v2.txt and serve it as
the real data notice; regenerate contracts/openapi/v1.json and ui/src/api/schema.d.ts.
Consumers: API (M2.12 implements), UI (Phase 5), copilot (Phase 4).
Compatibility: no existing field changes; the new fields are nullable; real-data-v1.txt
stays in place.
Approvals needed: tech lead (contract), data steward (notice text).
```

### 5.1 C1: NeonRadar Record 1.1.0

**New datasets** in `contracts/datasets.yaml` (verbatim; the data steward approves each licence field in the M2.1a review, and removes any list from `access.sanctions_lists` or `access.pep_sources` whose terms they do not accept; the quotations come from `sanctions-peps.md`, checked on 18 October 2026):

```yaml
# Appended to datasets: in contracts/datasets.yaml (C1 1.1.0)
  - slug: gb_fcdo_sanctions
    id_prefix: uksl
    kind: list
    anchor_priority: 3
    title: UK Sanctions List
    publisher: Foreign, Commonwealth and Development Office (FCDO)
    url: https://www.gov.uk/government/publications/the-uk-sanctions-list
    licence: { id: OGL-UK-3.0, url: "https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/" }
    attribution: "Contains public sector information licensed under the Open Government Licence v3.0. Source: UK Sanctions List, Foreign, Commonwealth and Development Office. Converted to FollowTheMoney records by NeonRadar."
    commercial_use: allowed
    redistribution: loaders-only
    personal_data: true
    synthetic: false
    access: none
    status: active                   # runs only when access.sanctions_lists includes it (1.2)
    notes: >-
      The only UK sanctions list since 28 January 2026 ("The OFSI Consolidated List has closed.").
      OGL v3.0 does not cover "personal data in the Information": whoever loads the list is a
      controller under UK GDPR. No endorsement by the FCDO is implied. One person can have
      several Unique IDs, one per regime; the loader groups them by OFSI Group ID, which
      designations made since 28 January 2026 do not have (M2.6a).
  - slug: us_ofac_sdn
    id_prefix: ofac
    kind: list
    anchor_priority: 6
    title: OFAC Specially Designated Nationals and Blocked Persons List
    publisher: US Department of the Treasury, Office of Foreign Assets Control
    url: https://ofac.treasury.gov/sanctions-list-service
    licence: { id: CC0-1.0, url: "https://creativecommons.org/publicdomain/zero/1.0/" }
    attribution: "Source: US Department of the Treasury, Office of Foreign Assets Control, Specially Designated Nationals and Blocked Persons List (public domain). NeonRadar is not affiliated with OFAC. Converted to FollowTheMoney records by NeonRadar."
    commercial_use: allowed
    redistribution: loaders-only
    personal_data: true
    synthetic: false
    access: none
    status: active                   # runs only when access.sanctions_lists includes it (1.2)
    notes: >-
      OFAC's data catalogue (data.json) marks the list files CC0 1.0 with the rights statement
      "No restrictions on public access"; the data.gov record for the SDN files says "This data
      is in the public domain and may be used without restriction." Public-domain status does not
      remove data protection duties: whoever loads the list is a controller under UK GDPR.
      Requests need a User-Agent header. OFAC does not confirm matches; NeonRadar output is not a
      screening result.
  - slug: un_sc_sanctions
    id_prefix: unsc
    kind: list
    anchor_priority: 4
    title: United Nations Security Council Consolidated List
    publisher: United Nations Security Council
    url: https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list
    licence: { id: LicenseRef-UN-Terms-of-Use, url: "https://www.un.org/en/about-us/terms-of-use" }
    attribution: "Source: United Nations Security Council Consolidated List. Converted to FollowTheMoney records by NeonRadar."
    commercial_use: permission-required
    redistribution: loaders-only
    personal_data: true
    synthetic: false
    access: none
    status: active                   # runs only when access.sanctions_lists includes it, which needs the UN's written permission (1.1)
    notes: >-
      The UN website terms allow download "for the User's personal, non-commercial use", and no
      licence for the list was found. Load it only with written permission from
      sc-sanctionslists@un.org, filed in docs/data/licences/un_sc_sanctions.md. The loader is
      built and tested on synthetic data and runs only when access.sanctions_lists includes this
      dataset, so the status needs no contract change when permission arrives. Whoever loads the
      list is a controller under UK GDPR. The UK list carries UN listings with their UN reference
      numbers.
  - slug: eu_fsf
    id_prefix: eufsf
    kind: list
    anchor_priority: 5
    title: EU Financial Sanctions Files (consolidated list)
    publisher: European Commission
    url: https://webgate.ec.europa.eu/fsd/fsf/public/rss
    licence: { id: LicenseRef-EC-Reuse-Decision-2011-833, url: "https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32011D0833" }
    attribution: "Source: European Commission, Financial Sanctions Files, reused under the Commission's reuse policy (Decision 2011/833/EU). Only the information published in the Official Journal of the EU is deemed authentic. Converted to FollowTheMoney records by NeonRadar."
    commercial_use: allowed
    redistribution: loaders-only
    personal_data: true
    synthetic: false
    access: none
    status: active                   # runs only when access.sanctions_lists includes it (1.2)
    notes: >-
      Decision 2011/833/EU allows reuse "for commercial or non-commercial purposes", with
      acknowledgement of the source and without distorting the meaning. The Commission's default
      licence for its own content since 2019 is CC BY 4.0 ("reuse is allowed, provided
      appropriate credit is given and changes are indicated"), but no licence statement attached
      to the FSF files themselves was found. Whoever loads the list is a controller under UK GDPR.
      The public download token can be revoked, so it is configurable (NR_EU_FSF_TOKEN), and
      stored URLs never include it.
  - slug: gb_parliament_members
    id_prefix: ukparl
    kind: list
    anchor_priority: 7
    title: UK Parliament members and ministers
    publisher: UK Parliament
    url: https://members-api.parliament.uk/
    licence: { id: LicenseRef-Open-Parliament-Licence-3.0, url: "https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/" }
    attribution: "Contains Parliamentary information licensed under the Open Parliament Licence v3.0. Converted to FollowTheMoney records by NeonRadar."
    commercial_use: allowed
    redistribution: loaders-only
    personal_data: true
    synthetic: false
    access: none
    status: active                   # runs only when access.pep_sources includes it (M2.6e)
    notes: >-
      Current members of either House are politically exposed persons under MLR 2017 regulation
      35(14)(b); regulation 35(9) asks firms to keep enhanced measures for at least 12 months after
      a person leaves office, so the loader keeps former members only for
      access.pep_former_months (M2.6e). The Open Parliament Licence does not cover personal data:
      whoever loads it is a controller under UK GDPR. No endorsement by Parliament is implied.
      Photographs are outside the licence and are not loaded.
```

**New optional dataset fields** (on every entry; M2.1a adds them to the five existing entries too). `commercial_use` also accepts `permission-required` (the UN list). M2.1a also changes `status` from `spike` to `active` on `gb_companies_house`, `gleif_lei` and `icij_offshore_leaks`, whose production loaders arrive in this phase. Whether a source runs is decided by `access.*` in `project.yaml` and the profile (M2.2), never by `status`: Phase 1 uses `blocked` for a dataset whose status must change through a contract change before it may run, which no Phase 2 dataset needs.

| Field | Values | Meaning |
|---|---|---|
| `kind` | `registry`, `list`, `leak`, `synthetic` | `gb_companies_house` and `gleif_lei` are `registry`; the four sanctions lists, `gb_parliament_members` and `opensanctions_default` are `list`; `icij_offshore_leaks` is `leak` (policy P2 reads it); `nr_synthetic` is `synthetic` |
| `anchor_priority` | integer, 1 is first | The anchor order of 7.1.6: `gb_companies_house` 1, `gleif_lei` 2, `gb_fcdo_sanctions` 3, `un_sc_sanctions` 4, `eu_fsf` 5, `us_ofac_sdn` 6, `gb_parliament_members` 7, `opensanctions_default` 8, `icij_offshore_leaks` 9, `nr_synthetic` 10 |

**New `nr` keys** (the extension stays a closed set; unknown keys still fail):

| Key | Type | Used on | Meaning |
|---|---|---|---|
| `ch_person_number` | string | `Person` and `LegalEntity` records from the Companies House officers API | The officer resource's `person_number`, unchanged (D3 uses its first 8 characters) |
| `psc_statements` | list of strings | `Company` | Raw PSC statement values, exemption keys and super-secure kinds from the PSC snapshot, sorted, unchanged (including the source's own spelling, for example `no-individual-or-entity-with-signficant-control`) |
| `accounts_category` | string | `Company` | The raw accounts category from the Free Company Data Product (for example `DORMANT`) |
| `share_pct_min_exclusive` | boolean | `Ownership`, `Control` | `true` when the lower bound `share_pct_min` is excluded ("more than 25%"); absent means included |
| `share_pct_max_exclusive` | boolean | `Ownership`, `Control` | `true` when the upper bound `share_pct_max` is excluded ("less than 75%"); absent means included |

**Wider `nr` keys** (Phase 1 keys that accept more; every 1.0 use stays valid):

| Key | Change | Used on | Meaning of the addition |
|---|---|---|---|
| `synthetic_kind` | also `"list"` and `"leak"` | synthetic records | A synthetic record in the style of an official list entry, or of a leak record (the ER benchmark, M2.9). The resolver treats such a record like a record of a `list` or `leak` dataset (7.1.1), so the benchmark exercises policies P1, P2 and P6 |
| `is_nominee` | also on `Ownership` | `Directorship`, `Ownership` | On `Ownership`: the source names the owner as a nominee shareholder (ICIJ, M2.5) |
| `share_pct_min`, `share_pct_max` | also on `Control` | `Ownership`, `Control` | On `Control`: the voting-rights band (`voting-rights-25-to-50-percent` and the like, M2.3b); with the two exclusive flags above |

The statutory Companies House bands are `(25, 50]`, `(50, 75)` and `[75, 100]`, and `(25, 100]` for overseas entities ("more than 25% but not more than 50%", "more than 50% but less than 75%", "75% or more"; `bulk-sources-loading.md` 4.2, which corrects the Phase 1 note). M2.3b sets the bounds and the two flags from the band, on `Ownership` for shares and surplus assets and on `Control` for voting rights; the synthetic generators (M1.8e, updated in M2.9, and M2.9's benchmark) set them the same way; other sources leave the flags absent.

**Version fields.** `nr.v` accepts `"1.0"` and `"1.1"`; Phase 2 loaders write `"1.1"`. The manifest's `record_contract` accepts `"1.0.0"` and `"1.1.0"`; Phase 2 loaders write `"1.1.0"`. Rules R1 to R10 are unchanged.

**Examples** (synthetic; committed as `contracts/examples/c1/demo-1.1.ftm.jsonl`, which must validate in strict mode together with the records it references):

```json
{"id": "syn-co-0101", "schema": "Company", "datasets": ["nr_synthetic"], "properties": {"name": ["Quarry Lane Instruments Ltd"], "jurisdiction": ["gb"], "registrationNumber": ["SY000101"], "incorporationDate": ["2021-06-11"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "registry", "psc_statements": ["no-individual-or-entity-with-signficant-control"], "accounts_category": "DORMANT"}}
{"id": "syn-off-0101", "schema": "Person", "datasets": ["nr_synthetic"], "properties": {"name": ["MARLOWE, Petra Anne"], "firstName": ["Petra"], "middleName": ["Anne"], "lastName": ["Marlowe"], "birthDate": ["1981-03"], "nationality": ["gb"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "registry", "source_ref": "SYNOFF0101", "ch_person_number": "SYN00101A0001"}}
{"id": "syn-ownership-0101", "schema": "Ownership", "datasets": ["nr_synthetic"], "properties": {"owner": ["syn-off-0101"], "asset": ["syn-co-0101"], "percentage": ["25-50"], "role": ["ownership-of-shares-25-to-50-percent"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "registry", "natures_of_control": ["ownership-of-shares-25-to-50-percent"], "share_pct_min": 25.0, "share_pct_max": 50.0, "share_pct_min_exclusive": true}}
{"id": "syn-control-0101", "schema": "Control", "datasets": ["nr_synthetic"], "properties": {"controller": ["syn-off-0101"], "controlled": ["syn-co-0101"], "controlType": ["voting"], "role": ["voting-rights-50-to-75-percent"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "registry", "natures_of_control": ["voting-rights-50-to-75-percent"], "share_pct_min": 50.0, "share_pct_max": 75.0, "share_pct_min_exclusive": true, "share_pct_max_exclusive": true}}
{"id": "syn-lst-0101", "schema": "Person", "datasets": ["nr_synthetic"], "properties": {"name": ["Ivo Kestrane"], "alias": ["Iwo Kestran"], "birthDate": ["1968-11-02"], "nationality": ["zz"], "topics": ["sanction"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "list"}}
{"id": "syn-lst-sanction-0101", "schema": "Sanction", "datasets": ["nr_synthetic"], "properties": {"entity": ["syn-lst-0101"], "authority": ["Synthetic Authority A"], "authorityId": ["SYA-0101"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "list"}}
{"id": "syn-lk-0101", "schema": "LegalEntity", "datasets": ["nr_synthetic"], "properties": {"name": ["QUILLAN BRASKE"], "country": ["zz"]}, "nr": {"v": "1.1", "synthetic": true, "synthetic_kind": "leak"}}
```

(`SY` plus six digits is the synthetic company number form used by the benchmark: it has the shape of a UK company number, `SY` is not a Companies House prefix (`bulk-sources-loading.md` 2.6), and `neonradar_keys` accepts it only for synthetic records, M2.8. `Kestrane` and `Braske` are invented surnames, as M2.9 requires for list-style and leak-style people.)

**Tests** (`contracts/tests/test_records.py`, `test_datasets.py`): the new examples validate; `nr` with a 1.1 key validates under both `v` values; `synthetic_kind` `list` and `leak` validate, and an unknown kind still fails; `is_nominee` on `Ownership` and the share keys on `Control` validate; an unknown key still fails; the registry has unique prefixes, every entry has a `kind` from the list, anchor priorities are unique; `nr_synthetic` keeps `kind: synthetic`; every attribution of a `list` dataset added in 1.1.0 ends with "Converted to FollowTheMoney records by NeonRadar.".

### 5.2 C2: Graph schema 1.1.0

**`:SourceRecord`** (one node per member of an entity merged from two or more records; never for single-record entities):

| Property | Type | Rule |
|---|---|---|
| `id` | STRING | the record id (unique, constraint from 0001) |
| `dataset`, `schema`, `caption` | STRING | from the record |
| `names` | LIST<STRING> | the record's names, original scripts |
| `topics` | LIST<STRING> | the record's own topics (invariant I11 recomputes flags from these) |
| `canonical_id` | STRING | the id of the entity it resolved to (indexed) |
| `synthetic` | BOOLEAN | the dataset's flag |
| `retrieved_at`, `source_url` | STRING | when the source provides them |
| `run_id` | STRING | the resolution run |

**`RESOLVED_TO`** (from `:SourceRecord` to `:Entity`; Phase 1 defined `match_probability`, `method`, `resolver_version`, `decided_at`): `method` takes the values `anchor`, `deterministic`, `probabilistic`, `human`; `match_probability` is 1.0 for `anchor`, `deterministic` and `human`; adds `rule` (STRING, D rule or null), `run_id` (STRING) and `features` (STRING: the `features` column of `canonical.csv`, a JSON object of comparison name to level label for the link through which the record joined; probabilistic links only, else null). The loader reads everything from `canonical.csv` (7.1.8) and never needs `pairs.parquet`.

**`POSSIBLY_SAME_AS`** (new relationship type):

| From | To | Built from | Properties |
|---|---|---|---|
| `LegalEntity` | `LegalEntity` | a line of `candidates.jsonl` whose two records are of class `person`, `org` or `legal_entity` (L14); stored from the node with the smaller id to the node with the larger id, read as undirected | `id` (`<a>\|psa\|<b>`), `match_probability` (FLOAT, or null for `deterministic` and `source_hint` possible matches), `match_weight` (FLOAT or null), `method` (`probabilistic`, `deterministic`, `source_hint`), `rule` (STRING or null: the D rule of a `deterministic` possible match, for example `D1` when two records share a UK company number but their names differ), `reasons` (LIST<STRING>), `features` (STRING, JSON), `run_id`, `resolver_version`, `datasets` (LIST<STRING>, the union of both nodes' datasets), `synthetic` (BOOLEAN) |

It carries no other meaning. Detectors (Phase 3) never traverse it; the API's network endpoint returns it like any other relationship, and the UI draws it as unconfirmed. Queries that sort possible matches put null probabilities last (`ORDER BY p.match_probability IS NULL, p.match_probability DESC`).

**New node properties.**

| Label | Property | Type | Rule |
|---|---|---|---|
| `:Entity` (all) | `cluster_size` | INTEGER | number of source records (1 for single-record entities) |
| `:Entity` (all) | `resolution` | STRING | `identity`, `deterministic`, `probabilistic`, `human` or `mixed` |
| `:Entity` (all) | `names_latin` | LIST<STRING> | Latin-script forms of `names` from `neonradar_keys.names.latin_forms` (search aid; never shown as a name) |
| `:Entity` (all) | `names_latin_text` | STRING | `names_latin` joined with `" \| "` (full-text index) |
| `:Company` | `psc_statements` | LIST<STRING> | from `nr.psc_statements` |
| `:Company` | `accounts_category` | STRING | from `nr.accounts_category` |

**New relationship properties.**

| Type | Property | Type | Rule |
|---|---|---|---|
| `OWNS` | `share_min_exclusive`, `share_max_exclusive` | BOOLEAN | from `nr.share_pct_min_exclusive` and `nr.share_pct_max_exclusive`; `false` when absent |
| `OWNS` | `is_nominee` | BOOLEAN | from `nr.is_nominee` on the `Ownership`; `false` when absent |
| `CONTROLS` | `share_pct_min`, `share_pct_max` | FLOAT | from `nr.share_pct_min` and `nr.share_pct_max` on the `Control` (the voting-rights band); null when absent |
| `CONTROLS` | `share_min_exclusive`, `share_max_exclusive` | BOOLEAN | from the two exclusive flags on the `Control`; `false` when absent |

PHASE-1.md invariant I5 is unchanged; I14 checks the `CONTROLS` bounds the same way. The ownership endpoint still traverses only `OWNS` (5.3): a voting-rights band is control, not a share.

`Address.address_key`, declared in 1.0.0, is now always set by the loader (`neonradar_keys.addresses.address_key`).

**Migration `graph/schema/migrations/0002_resolution.cypher`** (verbatim; one statement per line):

```cypher
// 0002_resolution: NeonRadar graph schema v1.1.0 (entity resolution)
CREATE CONSTRAINT possibly_same_as_id IF NOT EXISTS FOR ()-[r:POSSIBLY_SAME_AS]-() REQUIRE r.id IS UNIQUE;
CREATE INDEX source_record_canonical_id IF NOT EXISTS FOR (n:SourceRecord) ON (n.canonical_id);
CREATE INDEX source_record_dataset IF NOT EXISTS FOR (n:SourceRecord) ON (n.dataset);
DROP INDEX entity_names IF EXISTS;
CREATE FULLTEXT INDEX entity_names IF NOT EXISTS FOR (n:LegalEntity|Address) ON EACH [n.names_text, n.names_latin_text] OPTIONS { indexConfig: { `fulltext.analyzer`: 'standard-no-stop-words' } };
```

After 0001 and 0002: 23 constraints, and 9 indexes that are neither constraint-backed nor token lookups (`SHOW INDEXES YIELD type, owningConstraint WHERE owningConstraint IS NULL AND type <> 'LOOKUP' RETURN count(*)`). The full-text index keeps its name, so the API's search query does not change. Both Neo4j instances (L17) get the same migrations.

**Loader rules added** (numbered after PHASE-1.md 5.2 rules 1 to 7):

- L8. `neonradar graph load PATH... --resolution RUN_DIR` reads `canonical.csv` into a map from record id to canonical id. Without `--resolution`, every record is its own entity, exactly as in Phase 1.
- L9. A load with a resolution run first removes what that run replaces, in batches with `CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS` sent through `session.run()`: on the real-data instance (L17), every `:Entity`, `:Sanction` and `:SourceRecord` with their relationships; on the default instance, every synthetic `:Entity` and `:SourceRecord` whose `id` or `referents` include a record id of this load (the nodes an earlier resolution of the same records left behind, so I13 holds after a re-run); on both, every `:Alert` and `:DetectionRun` (detections are re-run after a load). `--no-replace` skips this for additive loads (for example Phase 3's overlay against an already loaded resolution).
- L10. Member records are grouped by canonical id and merged into one node row with the rules in 7.1.6; labels come from the merged schema and flags from the merged topics.
- L11. For every entity with two or more members, one `:SourceRecord` per member and one `RESOLVED_TO` from it to the entity, with properties from `canonical.csv` (`method`, `rule`, `match_probability`, `features`).
- L12. Every entity reference in a relationship record is re-pointed through the map. A relationship whose two ends land on the same node is not loaded and is counted as `self_loops_dropped`.
- L13. A reference that is neither a loaded entity id nor in the map is looked up in the database as `(:SourceRecord {id: $ref})-[:RESOLVED_TO]->(e)` before it counts as dangling. This is what lets Phase 3's overlay, which references record ids, load against a resolved graph.
- L14. One `POSSIBLY_SAME_AS` per line of `candidates.jsonl`. A line whose records are not of class `person`, `org` or `legal_entity` in `canonical.csv` stops the load (exit 1): an address never has a possible match (7.1).
- L15. `names_latin`, `names_latin_text` and `Address.address_key` are computed at load time with `neonradar_keys`; records are never changed (C1 R10).
- L16. Loading the same records with the same resolution run twice leaves every count unchanged (tested).
- L17. Real data lives in its own Neo4j instance: the Compose service `neo4j-real` (profile `real`, bolt on `127.0.0.1:7688`, its own volume `neo4j-real-data`), reached through `NR_NEO4J_REAL_URI` (its only database is `realdata`). A load with any non-synthetic record goes there; the loader refuses (exit 2) to write a non-synthetic record to the default instance (`NEO4J_URI`), and refuses a load that mixes synthetic and non-synthetic records. The default instance, which the API on port 8000, the UI, the end-to-end tests and the Neo4j MCP server use, therefore only ever holds synthetic data.

PHASE-1.md rule 6 still holds through the generic relationship query of M2.11: `PAID.ts` is written as a `DATETIME` in UTC (the loader passes a timezone-aware datetime).

**Invariants added** (integration tests in `graph/tests/test_invariants.py`, and `neonradar graph verify`):

| Invariant | Check |
|---|---|
| I7 | Every `:SourceRecord` has exactly one outgoing `RESOLVED_TO`, to an `:Entity` whose `id` starts with `nr-` and whose `referents` contain the source record's `id` |
| I8 | Every `:Entity` with `cluster_size >= 2` has exactly `cluster_size` incoming `RESOLVED_TO` and `size(referents) = cluster_size`; every other `:Entity` has `referents = [id]` |
| I9 | No `:Entity` has source records whose `synthetic` values differ from its own |
| I10 | Every `POSSIBLY_SAME_AS` joins two different `:LegalEntity` nodes with the same `synthetic` value, from the smaller id to the larger, and no two nodes have more than one |
| I11 | For every merged entity, `topics` equals the union of its source records' `topics`; for every entity, the flag labels are exactly those its `topics` imply (PHASE-1.md 5.2) |
| I12 | No `OWNS` or `CONTROLS` relationship starts and ends at the same node |
| I13 | No `:Entity` has an `id` equal to the `id` of a `:SourceRecord` (a record that joined a merged entity has no node of its own left over) |
| I14 | Every `CONTROLS` with share bounds has `0 <= share_pct_min <= share_pct_max <= 100` |

### 5.3 C3: API 1.1.0

**Ownership** (`GET /api/v1/entities/{entity_id}/ownership`, parameters unchanged from 1.0.0):

1. `entity_id` is a canonical id or any id in `referents` (resolved as for entity detail); unknown ids give a 404 problem.
2. `direction=up` returns chains of `OWNS` relationships that end at the entity (its owners, their owners, and so on); `direction=down` returns chains that start at it.
3. Paths have 1 to `max_hops` relationships and never repeat a node.
4. For each path, `effective_share_min` and `effective_share_max` are the products of `share_pct_min / 100` and `share_pct_max / 100` over its relationships, times 100, rounded to 4 decimals; if any relationship lacks a bound, that bound is null. `PathRef` gains `effective_share_min_exclusive` (true when any relationship's lower bound is exclusive) and `effective_share_max_exclusive` (true when any upper bound is), each null when its bound is null: for positive bounds, a product reaches its bound only if every factor reaches its own. The UI and the copilot say "more than" or "at least", "less than" or "at most", accordingly (7.2). An effective share is NeonRadar's calculation from the published bands, not a figure any register records, and not the result of a sanctions ownership test (7.2).
5. `min_share = 0` keeps every path. `min_share > 0` keeps the paths whose effective share can reach `min_share`: `effective_share_max > min_share`, or equal to it with a closed upper bound, compared after rounding. Paths whose maximum is unknown are dropped.
6. At most 200 paths, ordered by `effective_share_max` descending (nulls last), then by length, then by the list of node ids. `subgraph` holds the nodes and relationships of the returned paths, at most 500 nodes, with `truncated` set when either limit cut something.
7. Only `OWNS` is traversed. `CONTROLS` and `CONSOLIDATES` are reachable through `/paths` and `/network`.

**Paths** (`GET /api/v1/paths`):

1. Up to 5 shortest paths between `from_id` and `to_id` (each resolved as above), ignoring direction, with 1 to `max_hops` relationships.
2. `rel_types` defaults to `OWNS`, `CONTROLS`, `CONSOLIDATES`, `DIRECTOR_OF`, `REPRESENTS`, `FAMILY_OF`, `ASSOCIATE_OF`, `MEMBER_OF`, `EMPLOYED_BY`, `SUCCEEDED_BY`, `HOLDS_POSITION`, `SUBJECT_OF`, `HOLDS_ACCOUNT` and `PAID`. `HAS_ADDRESS`, `LINKED_TO` and `POSSIBLY_SAME_AS` are used only when asked for. `FLAGS`, `PRODUCED` and `RESOLVED_TO` are never allowed (422).
3. Effective shares and their two flags are set only for a path made entirely of `OWNS` relationships that all point the same way along it; otherwise all four are null.

**Both endpoints** run read-only with a 5-second transaction timeout; a query that times out returns a 503 problem whose detail suggests a smaller `max_hops` or fewer relationship types.

**Resolution** (new: `GET /api/v1/entities/{entity_id}/resolution`):

```text
ResolutionMember   record_id, dataset, schema, caption, names: list[str],
                   method: "identity" | "anchor" | "deterministic" | "probabilistic" | "human",
                   rule: str | None, match_probability: float | None, decided_at: str | None,
                   explanation: str
PossibleMatch      entity: EntitySummary, match_probability: float | None,
                   method: "probabilistic" | "deterministic" | "source_hint", rule: str | None,
                   reasons: list[str], evidence: list[str], explanation: str
ResolutionResponse entity_id, canonical: bool, resolution: str, cluster_size: int,
                   members: list[ResolutionMember], possible_matches: list[PossibleMatch],
                   resolver_version: str | None, run_id: str | None
```

`canonical` is true for merged entities. A single-record entity has one member with method `identity`. `PossibleMatch.match_probability` is null for `deterministic` and `source_hint` possible matches, and `rule` names the D rule of a `deterministic` one. `explanation` and `evidence` are rendered from the templates in 7.2 and pass the wording lint; every `PossibleMatch.explanation` contains "not confirmed". `EntityDetail.provenance` lists one `ProvenanceRecord` per source record for merged entities, and the entity itself otherwise.

**Declared responses.** M2.1c declares, on the ownership, paths and resolution routes, every response M2.12 will return: 200 with the response model, and 404, 422 and 503 with the `Problem` model; any 501 declaration Phase 1 made on the ownership and paths routes stays. Until M2.12 merges, the three routes return a 501 problem naming M2.12. M2.12 then implements them without changing the OpenAPI document: its acceptance runs `make contracts && git diff --exit-code contracts/openapi/v1.json`. The OpenAPI snapshot `contracts/openapi/v1.json` and `ui/src/api/schema.d.ts` are regenerated in M2.1c.

**Wording-lint patterns.** M2.1c appends to `contracts/wording/forbidden-terms.txt`, under the comment line `# Phase 2 additions (PHASE-2.md 7.2)`, one case-insensitive regular expression for each "Never write" phrase of 7.2 that the table does not qualify with a condition ("about a node whose ...", "unless ...", "when ..."); each pattern matches the phrase's words with `\b` at both ends and `\s+` between words. The qualified phrases depend on context, so the template tests of M2.12 check them instead. The Phase 1 lint script (`scripts/check_wording.py`) also scans `graph/src/**/wording.py`, where the Phase 2 templates live (7.2).

**Real data notice, version 2** (verbatim; `contracts/wording/real-data-v2.txt`). From M2.1c, `GET /api/v1/meta` serves it as `Disclaimers.real_data`; `real-data-v1.txt` stays in the folder unchanged, for the record. It replaces "where licensed, sanctions and PEP lists", because Phase 2 loads official sanctions lists that need no licence and loads PEP data only where the data steward chose it (1.2).

```text
This view includes records from public sources (company registers, the GLEIF index, the ICIJ Offshore Leaks Database, which is built from leaked files, official sanctions lists and, where chosen, PEP data), listed with their licences on the Data sources page. Records about real people and companies are shown as their source published them and may be out of date. Where several records appear to describe the same person or company, NeonRadar may show them as one entity; a link marked as a possible match is not confirmed. NeonRadar adds no allegations: any payment activity shown next to a real entity is synthetic background activity, and a pattern that touches a real entity is a structural observation only. Names can match the wrong person or company, so confirm identities with addresses, dates or official identifiers before drawing any conclusion. A missing sanctions or PEP flag means only that the lists loaded here do not name the record. These records can include personal data, and whoever loads them is responsible for handling it lawfully.
```

### 5.4 Contract tests added

| Test file | Checks |
|---|---|
| `contracts/tests/test_records.py` | 1.1 examples validate; new keys accepted under `v` 1.0 and 1.1; `synthetic_kind` `list` and `leak`; `is_nominee` on `Ownership`; the share keys and flags on `Control`; unknown keys and unknown kinds still fail; manifest accepts both record contract versions |
| `contracts/tests/test_datasets.py` | new entries load; `kind` values valid; anchor priorities unique; every `list` dataset has `personal_data: true`; the 1.1.0 list attributions end with "Converted to FollowTheMoney records by NeonRadar." |
| `contracts/tests/test_graph_mapping.py` | `psc_statements` and `accounts_category` map to company properties; the two share flags and `is_nominee` map to `OWNS` properties and default to `false`; the `Control` band maps to the four `CONTROLS` properties (bounds null and flags `false` when absent); `POSSIBLY_SAME_AS` (with a nullable `match_probability` and `rule`) and the `:SourceRecord` properties appear in the mapping data and in 0002 |
| `contracts/tests/test_wording.py` | every unqualified "Never write" phrase of 7.2 (copied into the test) matches a forbidden pattern; every "Write" text of 7.2 passes the lint; `real-data-v2.txt` exists and equals the text in 5.3; the Phase 1 checks still pass |
| `graph/tests/test_migrations.py` | 0001 then 0002 on an empty database give 23 constraints and 9 indexes (query above); re-running is a no-op |
| `graph/tests/test_invariants.py` | I1 to I14 on a resolved demo load inside a Testcontainers database (M2.11 extends the Phase 1 file) |
| `api/tests/test_openapi_contract.py` | the running app's OpenAPI equals the snapshot (M2.12 changes nothing in it) |
| `api/tests/test_routes.py` | the ownership, paths and resolution routes declare 200, 404, 422 and 503; until M2.12 they return a 501 problem, and M2.12 replaces that check with 404 and 422 checks |

---

## 6. Milestones

Each milestone below is one pull request unless it says otherwise. The header table gives the squad and human owner, the dependencies (by milestone id, all merged), the branch, the labels, whether to plan first, whether it is a size exception (2.3), the ADR it drafts, and whether it has a real-data run. Acceptance commands run on synthetic data.

### M2.0 Phase 2 handover and agent kit update

| | |
|---|---|
| Squad, human owner | Tech lead (data steward reviews ADR-0018 and the real-data guards) |
| Depends on | The Phase 2 seed pull request (1.4); Gate 1 passed |
| Branch | `p2/m2-0-handover` |
| Labels | `agent`, `phase-2`, `squad:docs`, `size-exception` |
| Plan first | Yes |
| Size | exception (verbatim kit content from this spec, plus two package scaffolds) |
| ADR | ADR-0018 (real-data handling) |
| Real-data run | none |

**Goal.** Every Phase 2 session starts from the same rules; the real-data guards work deterministically, not just as instructions; real data gets its own Neo4j instance, so the tools the agent uses every day never reach it; the two new packages exist so later milestones can run in parallel; and this spec is reconciled with what Phase 1 actually built.

**Deliverables.**

1. `docs/build/phase-2-reconciliation.md`. Read `docs/build/reports/phase-1.md`, the deviations recorded in `docs/build/PROGRESS.md`, every report in `docs/data/spikes/`, and the code this spec builds on (the C1 validator, the dataset registry, `graph/src/neonradar_graph/mapping.py` and `loader.py`, the migration runner, the API search query, the circular-flow query template, the spike mappers in `ingest/src/neonradar_ingest/sources/`, `compose.yaml`, the Makefile, `.claude/agents/*.md`). For every place where this spec and Phase 1 differ (an id form, a header name, a function or command name, a file path, how query templates mark their placeholders, the wording of an agent file this milestone edits), write one row: what this spec says, what Phase 1 has, and the decision (mechanical: follow Phase 1 and note it here; behavioural: a question for the tech lead, and stop). Also list every Cypher statement Phase 1 runs from a Python string instead of a `.cypher` file (it moves into a file when a later milestone touches that code, not in this pull request), and the Phase 1 open items that block a Phase 2 milestone. One difference is decided, not a question: M2.3b changes the Phase 1 spike's PSC mapping (PHASE-1.md M1.8a), so `-as-trust` and `-as-firm` values become `Control` of type `trust-or-firm` and voting rights keep their band on `Control`; record it as a decided change.
2. `.claude/settings.json` (edit, keep everything else):
   - add to `allow`: `"Bash(git push -u origin p2/*)"`, `"Bash(git push origin p2/*)"`, and `WebFetch` entries for the documentation hosts `www.gov.uk`, `assets.publishing.service.gov.uk`, `www.legislation.gov.uk`, `ico.org.uk`, `ofac.treasury.gov`, `main.un.org`, `www.un.org`, `data.europa.eu`, `www.parliament.uk`, `creativecommons.org`, `moj-analytical-services.github.io` and `duckdb.org`;
   - add to `ask`: `WebFetch` entries for the hosts that also serve list, register or leak data: `sanctionslist.fcdo.gov.uk`, `sanctionslistservice.ofac.treas.gov`, `scsanctions.un.org`, `webgate.ec.europa.eu`, `download.companieshouse.gov.uk`, `goldencopy.gleif.org` and `members-api.parliament.uk` (a person approves each fetch, and the hook still blocks their data files; their schemas are downloaded with a command in any case);
   - add to `deny`: `"Read(./data/cache/real/**)"`, `"Read(./data/cache/spikes/**)"`, `"Edit(./data/cache/**)"`, `"Write(./data/cache/**)"`;
   - add a `PreToolUse` entry with matcher `Bash|Read|Grep|Glob|WebFetch|mcp__neo4j__.*` running `python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/guard_real_data.py` (after the existing `guard_git.py` entry). The deny rules are relative to the project; the hook also catches absolute paths and other worktrees of the repository.
3. `.claude/hooks/guard_real_data.py`, verbatim from the end of this milestone, executable. It needs nothing but the Python standard library and runs with the system `python3` (3.9 or later), like `guard_git.py`.
4. `scripts/tests/test_guard_real_data.py`, verbatim from the end of this milestone (171 cases). It runs in CI's `python` job with the other tests under `scripts/tests/` (M1.10a); if `scripts/tests` is not yet collected there, add it to `testpaths`. Add one line to `scripts/test_hooks.sh`:

   ```bash
   uv run --no-sync pytest -q scripts/tests/test_guard_real_data.py >/dev/null && echo "PASS guard_real_data.py (171 cases)" || { echo "FAIL guard_real_data.py"; failed=1; }
   ```

   If Phase 1's script names its failure flag differently, use that name instead of `failed`, so the script still exits non-zero on any failure.
5. **The real-data Neo4j instance.** Real profiles never load into the instance that the API, the UI, the tests and the agent use (C2 L17, M2.11).
   - `compose.yaml` (Phase 1's Compose file, PHASE-1.md M1.4): a service `neo4j-real` under the Compose profile `real`, with the same image, plugins, memory settings and healthcheck as `neo4j`, plus `NEO4J_AUTH=neo4j/${NEO4J_REAL_PASSWORD}`, `NEO4J_initial_dbms_default__database=realdata` (its only database is called `realdata`, so a query sent to the wrong instance fails because the database does not exist), ports `127.0.0.1:7475:7474` and `127.0.0.1:7688:7687`, and one named volume `neo4j-real-data` for `/data`. A plain `docker compose up` never starts it.
   - `.env.example`: `NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688`, `NEO4J_REAL_PASSWORD=` (empty; each approved machine sets its own) and `NR_REAL_DATA_MACHINE=` (empty; its owner sets `approved` only on a machine listed in `docs/data/real-data-machines.md`, 1.1).
   - Makefile targets `up-real` (`docker compose --profile real up -d --wait neo4j-real`) and `down-real` (`docker compose --profile real stop neo4j-real`). Deleting the instance's data is `neonradar data purge --graph` (M2.2).
   - Do not start the instance in this milestone: `docker compose --profile real config --services` proves the service exists, and `docker compose --profile real config --quiet` that the file is valid.
6. `.claude/rules/real-data.md` and `.claude/rules/er.md`, verbatim below. Each starts with `paths:` frontmatter.
7. `.claude/agents/data-guardian.md`, verbatim below. Two edits to the Phase 1 agents (if the merged wording differs from PHASE-1.md M1.2, make the same change to the merged text and record it in the reconciliation):
   - `contract-guardian.md`: "Compare the diff (`git diff main...HEAD`) with PHASE-1.md section 5." becomes "Compare the diff (`git diff main...HEAD`) with PHASE-1.md section 5 and section 5 of the current phase spec (PHASE-2.md lists the 1.1.0 changes)."
   - `reviewer.md`: "contracts (section 5) are respected" becomes "contracts (PHASE-1.md section 5 and section 5 of the current phase spec) are respected", and the guardrail line becomes "guardrails G1 to G10 (section 2.1 of the current phase spec): no real-person data, no OpenSanctions rows, no network in tests, no secrets, no accusatory wording, citations present for AML facts, no inferred flags, no real records read or printed, no labels or review decisions written by an agent;".
8. `.claude/skills/milestone/SKILL.md`: in the reading step, read the parent section of a sub-milestone too (M2.1, M2.3, M2.6 and M2.10 hold shared rules and build steps; 2.2 step 2); after step 2, add "If the milestone has a real-data run, follow step 6a of section 2.2: never run it unless the operator said in this session that the machine is approved; otherwise write the command into the pull request."
9. `CLAUDE.md` (stay under 200 lines): add the three rules, the commands, the layout entries and the traps in the block below; change "The build spec for the current phase is docs/build/PHASE-<n>.md" to name `docs/build/PHASE-2.md` as current.
10. **Two workspace members, empty but working.** `keys/` (`neonradar-keys`, import `neonradar_keys`, dependencies `rigour`, `normality` and `anyascii` with the pins in 3.1) and `resolve/` (`neonradar-resolve`, import `neonradar_resolve`, dependencies `neonradar-contracts`, `neonradar-graph`, `neonradar-keys`, and `splink`, `duckdb`, `pyarrow` with the pins in 3.1), each with `pyproject.toml`, `src/<pkg>/__init__.py` (`__version__ = "0.1.0"`), `py.typed`, `tests/test_<dir>_version.py` and a `CLAUDE.md` of at most 20 lines. Add both to the root `[tool.uv.workspace] members`, mypy `files` and pytest `testpaths`; make `cli`, `ingest` and `graph` depend on `neonradar-keys`, and `cli` on `neonradar-resolve`. Add one `[[tool.mypy.overrides]]` block now, `module = ["pyarrow", "pyarrow.*"]` with `ignore_missing_imports = true`: PyArrow 26.0.0 ships no type information, while Splink 5.0.0, DuckDB 1.5.6 and sqlglot 30.23 do (checked 18 October 2026), and M2.10a's verbatim `feature_schema.py` imports PyArrow. If another dependency turns out to ship no type information, add a block for exactly that module and say so in the pull request. Run `uv lock`.
11. **Cypher lint.** `scripts/cypher-lint/package.json` (private, `"type": "module"`, one dependency: `"@neo4j-cypher/language-support": "2.0.0-next.39"`, exact) with its `package-lock.json`, and `scripts/cypher-lint/lint.mjs` verbatim below. It lints every `.cypher` file under `graph/`, `detect/` and `api/` with Cypher 5 rules (errors and deprecation warnings fail). Templates declare their placeholder values in a header comment (`// lint-values: max_hops=1,2,8`) and write placeholders as `{{max_hops}}`; if Phase 1's circular-flow template uses another placeholder form, convert it to this one in this pull request and record that in the reconciliation. Makefile target `cypher-lint` (`npm ci --prefix scripts/cypher-lint --silent && node scripts/cypher-lint/lint.mjs`), added to `make check`; CI's `ui` job runs it (it already has Node 24). Rule from now on: every Cypher statement a new or changed piece of code runs lives in a `.cypher` file, so it is linted. Add `scripts/cypher-lint/package-lock.json` to `.github/pr-size-exclude.txt`.
12. **Masked validation messages.** `neonradar contracts validate-records` prints each issue as `<file>:<line>: <rule id>: <message>`. When the record's dataset is not synthetic, or is not in the registry, a wrapper in the CLI (`cli/src/neonradar_cli/masking.py`; the frozen validator under `contracts/` does not change) replaces every quoted value in the message with `<value>` (a quoted value is any text between single or double quotes, and anything after `input_value=` up to the next comma or closing bracket) and leaves out the record id (the line number identifies the record). Unit test with a non-synthetic look-alike record built in the test.
13. **`neonradar doctor` additions**, one line each, OK or WARN (never FAIL, never a question: doctor reads nothing from stdin and still exits 1 only on a Phase 1 FAIL):
    - free disk space in the repository's file system (WARN below 25 GB, the `uk-sample` need in 1.1);
    - DuckDB importable;
    - real data present under `data/cache/real/`, and the age of its oldest file against `access.real_data_days` (WARN when older);
    - leftover DuckDB spill folders under `data/cache/real/duckdb-tmp/` or `data/cache/synthetic/duckdb-tmp/` (WARN with the folder count; a finished run deletes its folder);
    - the `neo4j-real` container running (WARN: "the real-data instance is running; stop it with `make down-real` when you are done");
    - when `access.real_data_profiles` is not empty: a reminder that this machine must be listed in `docs/data/real-data-machines.md` before `NR_REAL_DATA_MACHINE=approved` is set, and WARN while `access.data_protection_filed` is false.
14. Labels in `.github/labels.yml` (`phase-2` is already there from Phase 1): `{ name: real-data-run, color: "e99695", description: "A named human runs a real-data command for this pull request" }` and `{ name: er, color: "006b75", description: "Entity resolution" }`, created with `scripts/sync_labels.py`; CODEOWNERS regenerated with the rows in 4.3.
15. `docs/build/project.yaml`: merge the keys in 1.3 into the existing `people`, `access` and `schedule` mappings with the defaults shown there (never add a second top-level key, which YAML would silently let win; keep every existing value): `people.er_labellers`, `people.er_senior_reviewers`, `access.real_data_profiles`, `access.real_data_days`, `access.label_days`, `access.data_protection_filed`, `access.real_data_machines_doc`, `access.sanctions_lists`, `access.pep_sources`, `access.pep_former_months` and the three `schedule` dates. `docs/build/PROGRESS.md`: append one `todo` row for each of these 27 ids, in this order: M2.0, M2.1a, M2.1b, M2.1c, M2.2, M2.3a, M2.3b, M2.3c, M2.4, M2.5, M2.6a, M2.6b, M2.6c, M2.6d, M2.6e, M2.7, M2.8, M2.9, M2.10a, M2.10b, M2.10c, M2.11, M2.12, M2.13, M2.14, M2.15, M2.16 (the parent headings M2.1, M2.3, M2.6 and M2.10 get no row of their own).
16. `docs/data/real-data-handling.md` (the rules in 7.4; how the guards work: the deny rules, the hook and what it blocks, the separate `neo4j-real` instance and how to start and stop it, the redaction guard; how to purge, including the instance's volume) and `docs/data/real-data-machines.md` (a table with columns handle, machine nickname, disk encryption, screen lock, checked on, checked by; no rows, the data steward fills it).
17. `THIRD_PARTY_NOTICES.md` at the repository root: one section per third-party work whose notice the project must carry, starting with the dependencies under licences other than permissive ones: `python-stdnum` (LGPL-2.1-or-later, required by rigour and FollowTheMoney, used unmodified and installed from PyPI; the project ships no copy of it). The pull request asks the tech lead and the project lead to confirm the decision in 1.2. Later milestones add sections: M2.6 for code ported from MIT-licensed crawlers, M2.8 for `ar_symbols.json.gz` (built from rigour's MIT-licensed data, whose names come from Wikidata) and `nationalities.csv` (built from Open Government Licence inputs).
18. `docs/decisions/0018-real-data-handling.md` (status `proposed`; decider: data steward): the rules in 7.4; the controls: the permission rules; the hook over Bash, Read, Grep, Glob, WebFetch and the Neo4j MCP server; the separate real-data instance (`neo4j-real`, database `realdata`, ports 7475 and 7688), which the tools the agent uses every day (the default instance, the API on port 8000, the UI, the end-to-end tests, the MCP server) never reach; the redaction guard for real-profile commands (M2.2); the terminal rule for human-only commands; counts-only summaries; the data-guardian subagent; retention and purge, including the volume-level purge of the real instance (`neonradar data purge --graph` deletes its Docker volume, so transaction logs and store files go too); incident handling; the honest limit that the hook stops accidents, not a determined person, and that people remain responsible.

**The `CLAUDE.md` additions:**

```markdown
## Non-negotiable rules (Phase 2 additions)
9. No inferred flags. Flags and topics come only from a node's own source records. A
   listed record merges with an unlisted one or one listed for another reason, and a
   leaked (ICIJ) record with another source, only by a deterministic identifier rule whose
   records share an exact name key, or by a human decision that two reviewers or a senior
   reviewer made; otherwise it is a POSSIBLY_SAME_AS link, always described as "not
   confirmed" (PHASE-2.md G8, 7.1.4).
10. Never read real data. Real records live in data/cache/real/, data/cache/spikes/ and the
    neo4j-real instance (ports 7475 and 7688). Never open, print, grep, fetch (WebFetch,
    curl, wget) or query them; the default Neo4j instance, the API on port 8000, the UI and the Neo4j MCP server
    hold synthetic data only. Real-data commands print counts only. Reproduce failures on
    the demo profile or the ER benchmark (G9). guard_real_data.py and the deny rules
    enforce this.
11. Humans label. Never write, edit, pre-fill or infer labels or review decisions, never
    run er label, er review or api serve --real, and never tune thresholds, rules or models
    on evaluation labels (G10).

## Commands (Phase 2 additions; each works once the milestone in brackets has merged)
- `make cypher-lint`              lint every .cypher file (Cypher 5 rules) [M2.0]
- `make up-real`, `make down-real` start or stop the real-data instance (approved machines) [M2.0]
- `uv run neonradar data status`  downloads, versions, ages, retention (counts only) [M2.2]
- `uv run neonradar er run --profile demo`   one resolution run (synthetic) [M2.10a]
- `uv run neonradar er bench --size small`   the ER benchmark with precision and recall [M2.10a]
- `uv run neonradar graph verify` graph invariants I1 to I14 [M2.11]
- `make load PROFILE=demo`        synthetic profile end to end: build, resolve, load, verify [M2.13]

## Layout (Phase 2 additions)
keys/ (matching keys, pure functions), resolve/ (entity resolution), ingest/profiles/,
data/cache/real/ (real data: never read), data/cache/synthetic/ (synthetic runs: free to read),
data/cache/reports/ (counts-only summaries)

## Known traps (Phase 2, verified 18 Oct 2026)
- Splink 5 only: `sdf = db_api.register(table, ...)`, then `Linker(sdf, settings)`; results
  with `as_record_list()`; no `db_api=` on Linker, no `as_record_dict`, no `bf_` columns.
- NameComparison always adds term-frequency adjustment: build name comparisons from levels.
- An empty DuckDB list is not NULL: write NULL for every empty list in feature tables.
- DuckDB memory and threads go on `duckdb.connect(config=...)`; tests use one thread.
- XML: defusedxml only (ruff S314); compare tags without namespaces (OFAC changed its).
- OFAC needs a User-Agent; never store the UN redirect URL or log the EU token.
- Companies House bulk headers start with spaces; PSC bands: (25,50], (50,75), [75,100].
- `person_number` comes only from /company/{n}/officers; D3 uses its first 8 characters.
- GLEIF Level 2 is accounting consolidation: CONSOLIDATES, never OWNS.
- `CALL { } IN TRANSACTIONS` only through `session.run()`; Neo4j 5.26 has no ON ERROR RETRY.
- `from rigour.text.scripts import text_scripts`; never fuzzy country lookups; keys come
  from neonradar_keys only.
```

**`.claude/rules/real-data.md`:**

```markdown
---
paths:
  - "ingest/**"
  - "keys/**"
  - "resolve/**"
  - "graph/**"
  - "api/**"
  - "cli/**"
  - "data/**"
  - "docs/data/**"
---
# Real-data rules (PHASE-2.md G2, G8, G9, G10 and 7.4)
- Never open, print, grep, WebFetch or query real records: data/cache/real/,
  data/cache/spikes/, the neo4j-real instance (ports 7475 and 7688, database realdata) and
  the real API (port 8001). The default Neo4j instance, the API on port 8000, the UI and the
  Neo4j MCP server hold synthetic data only. Reproduce problems on the demo profile or the
  ER benchmark.
- Fetch (WebFetch, curl, wget) documentation and schemas only: never a list, register or
  leak data file, and never a page about a real person (for example a Companies House
  officer page). The loaders download data; the agent never does.
- A command that runs on a real profile prints counts, timings, rates, versions and
  settings only, and writes the same summary to data/cache/reports/<profile>/. Its errors
  go through the redaction guard; full tracebacks stay in data/cache/real/logs/.
- Library code logs record ids and values only at DEBUG. When the dataset is not
  synthetic, exceptions name the rule and the step, never a value or a person's record id.
- Human-only commands (er label, er review, api serve --real) refuse to run when stdin is
  not a terminal. Never run them, and never wrap them in script, expect or unbuffer.
- Loaders set topics and flags only when the source states them; a probabilistic match
  never adds one; possible-match text always says "not confirmed".
- Tests and fixtures are synthetic. Build non-synthetic look-alikes in test code (ids such
  as gbch-co-T0000001, names such as "Test Holder Ltd"). Hand-written synthetic fixtures in
  a source's own format (for example list XML) may be committed under tests/fixtures/.
```

**`.claude/rules/er.md`:**

```markdown
---
paths:
  - "resolve/**"
  - "keys/**"
  - "graph/src/neonradar_graph/loader.py"
  - "graph/src/neonradar_graph/mapping.py"
---
# Entity resolution rules (PHASE-2.md 7.1)
- PHASE-2.md 7.1 is the authority: deterministic rules D1 to D7, cannot-link rules X1 to
  X8, policy P1 to P6, thresholds in resolve/config/er.yaml. Use the rule ids in code,
  tests, conflicts.jsonl and candidates.jsonl.
- Splink 5 only (the signatures in PHASE-2.md 7.1.5). Never write Splink 4 code.
- Results are deterministic: sorted inputs, fixed seeds, merges in the order of 7.1.6,
  sorted outputs. Tests compare bytes on the benchmark.
- Never compare or merge synthetic with real records; a POSSIBLY_SAME_AS link never
  carries a property between nodes.
- After the freeze (Thursday 29 October) thresholds, rules and policy change only with the
  tech lead's approval in the pull request, and the change voids the evaluation sample.
- Committed models hold settings only; parameters trained on real data stay in the run folder.
- Every matching change reports benchmark precision and recall before and after.
```

**`.claude/agents/data-guardian.md`:**

```markdown
---
name: data-guardian
description: Checks a NeonRadar diff for real-data leaks and flag safety (PHASE-2.md G2, G8, G9, G10). Use for any change under ingest/, keys/, resolve/, graph/, api/, cli/, data/ or docs/data/, and before any real-data run.
tools: Read, Grep, Glob, Bash
model: inherit
---
Read-only. You did not write this change. Use Bash only for git diff, git log, ls and grep
over tracked files (git grep). Never read anything under data/cache/real/ or
data/cache/spikes/, never query the neo4j-real instance, and never fetch a data file
(WebFetch, curl, wget).

Check `git diff main...HEAD` for:
1. Real data in the repository: fixtures, tests, examples, docs or reports holding names,
   birth dates, addresses, identifiers or record ids of real people; files under data/
   other than synthetic fixtures; anything copied from a download, an API response or a
   web page about a real person.
2. Output discipline: code paths that run on a real profile and print, log above DEBUG,
   raise or write values from records outside data/cache/real/; errors that bypass the
   redaction guard. Summaries hold counts, timings, rates, versions and settings only.
3. The real instance: code other than the graph loader's routing, the --real options of
   the graph commands and the human-only `api serve --real` that connects to neo4j-real
   (NR_NEO4J_REAL_URI, port 7688); anything that lets real records into the default
   instance, the API on port 8000, the UI or the end-to-end tests.
4. Flags (G8): a loader that sets a topic or flag its source does not state; a merge path
   that bypasses PHASE-2.md 7.1.4; any property copied across POSSIBLY_SAME_AS;
   possible-match wording without "not confirmed".
5. Labels (G10): code that writes, pre-fills or infers labels or decisions; threshold or
   rule changes after the freeze; evaluation code that drops or re-weights pairs.
6. Human-only commands (er label, er review, api serve --real) refuse to run when stdin is
   not a terminal.
Report findings as BLOCKING (file:line, why, fix), SHOULD FIX, NOTES. If none, say so.
```

**Instructions.**

1. Plan first: list the files, the reconciliation sources you will read, and how you will test the hook without real data (the test file below builds its own temporary project) and the Compose change without starting the real instance.
2. Claude Code reads hooks and permission rules when a session starts, so this session cannot rely on them yet. Prove them with `scripts/tests/test_guard_real_data.py`; the operator check after merge confirms them in a fresh session.
3. Do not create any file under `data/cache/real/` in this milestone, not even a dummy, and do not start `neo4j-real`.

**Acceptance.**

```bash
bash scripts/test_hooks.sh                                  # all PASS, including the real-data cases
uv run pytest scripts/tests/test_guard_real_data.py -q      # 171 passed
python3 -c "import ast; ast.parse(open('.claude/hooks/guard_real_data.py').read(), feature_version=(3, 9))"
jq empty .claude/settings.json
docker compose --profile real config --services | grep -qx neo4j-real   # the neo4j-real service exists
test "$(wc -l < CLAUDE.md)" -lt 200
grep -l '^name:' .claude/agents/*.md | wc -l                # prints 4
grep -L '^paths:' .claude/rules/*.md                        # prints nothing
uv lock && uv sync --all-packages --locked
uv run python -c "import neonradar_keys, neonradar_resolve; print(neonradar_keys.__version__, neonradar_resolve.__version__)"
make cypher-lint                                            # 0 problems
uv run neonradar doctor                                     # the new lines appear; exit 0
make check && make hygiene LABELS=size-exception
```

Operator check after merge, in a fresh session (the guards load when a session starts):

1. Run `/hooks` and confirm four hooks.
2. Create a dummy file yourself: `mkdir -p data/cache/real && echo dummy-word-7q > data/cache/real/dummy.txt`.
3. Ask Claude to show the file's content: it must be blocked (the deny rule and the hook stop Read; the hook stops `cat`). Ask it to Read the file by its absolute path: blocked too.
4. Ask Claude to Grep the whole repository for `dummy-word-7q`: the result must be empty (the search skips the gitignored `data/cache/`). If it finds the file, stop and tell the tech lead: the hook then has to block repository-wide Grep.
5. Ask it for `ls data/cache/real`: that works.
6. Ask it to WebFetch `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml`, to fetch the same file with `curl`, and to run `uv run neonradar er label --profile demo`: all three blocked.
7. Delete the dummy file.

**Review focus (humans).** Tech lead: would the hook have stopped the mistakes you can imagine an agent making on a Friday afternoon? Try three of your own against a copy of the test file. Data steward: is ADR-0018 what you want to be held to, and is a separate instance for real data enough, together with the approved-machine list? Does the reconciliation list anything that changes a Phase 2 milestone?

**`.claude/hooks/guard_real_data.py`** (verbatim):

```python
#!/usr/bin/env python3
"""PreToolUse hook: keep real records out of the agent's context (PHASE-2.md G9, M2.0).

Bash: a command line that names data/cache/real or data/cache/spikes (directly, through a
glob, through any path containing cache/real or cache/spikes, or as the current folder,
which cd and pushd change as the line runs) may only run listing and housekeeping programs
(ls, du, wc, stat, find without actions, mkdir, rm, ...), the git subcommands in GIT_SAFE
without the flags that read files outside the index, and the project's own commands
(uv run neonradar ..., make ...), which print counts only. Nobody may cd into data/,
data/cache/ or a real-data folder, recursive readers (grep -r, rg --no-ignore, tar, zip,
rsync, cp -r, find -exec) may not run over a folder that holds real data, and git never
runs with --no-index, --untracked or --no-exclude-standard. A command that names the real
Neo4j instance (neo4j-real, database realdata, ports 7475, 7688 and 8001, NR_NEO4J_REAL_*,
NEO4J_REAL_PASSWORD) may only be uv run neonradar, make, or docker compose up, start, stop,
down or ps. Human-only commands (neonradar er label, er review, api serve --real) and the
terminal wrappers script, expect, unbuffer and faketty are always blocked. Shell downloaders
(curl, wget, http, https, xh, aria2c) follow the WebFetch rule below, and docker compose
config (without --quiet or a listing flag) and docker inspect are blocked, because they
print passwords from .env.
Read, Grep and Glob: no path, glob or pattern may name data/cache/real or data/cache/spikes.
WebFetch: list, register and leak data files and pages about real people are blocked;
schemas (.xsd), API descriptions (swagger, openapi) and documentation pass.
Neo4j MCP: allowed, because the default instance holds synthetic data only (PHASE-2.md
M2.11), unless .mcp.json names the real instance.
Exit 2 blocks the call and shows the reason. Standard library only; Python 3.9 or later.
It stops accidents, not a determined person: the permission rules, CLAUDE.md and the people
who run the project remain responsible.
"""

import fnmatch
import json
import os
import re
import shlex
import sys
from urllib.parse import urlsplit

PROTECTED = ("data/cache/real", "data/cache/spikes")
MARKS = ("cache/real", "cache/spikes")
ANCESTORS = (".", "data", "data/cache")


def words(*parts):
    return frozenset(" ".join(parts).split())


OPERATORS = frozenset(["&&", "||", ";", "|", "&", "\n", "(", ")"])
SAFE = words(
    "ls du df wc stat file mkdir rm rmdir touch test [ echo printf true false sleep date pwd",
    "which type find",
)
GIT_SAFE = words("status log diff show grep ls-files blame rev-parse check-ignore branch")
GIT_NEVER = ("--no-index", "--untracked", "--no-exclude-standard")
GIT_NOT_ON_REAL = ("-F", "--file", "-f", "--pathspec-from-file")
TEXT_FLAGS = words("-m --message --title -t --body -b --notes --subject")
FIND_ACTIONS = words("-exec -execdir -ok -okdir -fprint -fprint0 -fprintf -fls")
INTERPRETERS = words(
    "python python3 node ruby perl bash sh zsh duckdb sqlite3 uv uvx jq awk gawk sed"
)
WRAPPERS = words("script expect unbuffer faketty")
FETCHERS = words("curl wget http https xh aria2c")
CONFIG_SAFE = words("--quiet -q --services --profiles --volumes --images")
BARE_HOST = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}(?::[0-9]+)?(?:/|$)")
COMPOSE_OK = words("up start stop down ps")
COMPOSE_VALUE_OPTIONS = words(
    "-f --file -p --project-name --profile --env-file --project-directory --ansi --progress",
    "--parallel",
)
UV_VALUE_OPTIONS = words(
    "--env-file --with --python -p --package --directory --project --group --extra --index"
)
REAL_INSTANCE = re.compile(
    r"neo4j-real|\brealdata\b|NR_NEO4J_REAL|NEO4J_REAL_PASSWORD"
    r"|(?<![0-9])(?:7475|7688|8001)(?![0-9])"
)
HUMAN_ONLY = re.compile(
    r"\bneonradar(?:_cli)?\b(?:\s+-\S+)*\s+(?:er\s+(?:-\S+\s+)*(?:label|review)\b"
    r"|api\s+serve\b[^;&|]*?\s--real\b)"
)
HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")
WEB_DATA = (
    # (host, path prefix, mode): "all" blocks every path under the prefix, "files" only data files
    ("sanctionslist.fcdo.gov.uk", "/", "all"),
    ("sanctionslistservice.ofac.treas.gov", "/", "all"),
    ("treasury.gov", "/ofac/downloads/", "all"),
    ("scsanctions.un.org", "/", "all"),
    ("webgate.ec.europa.eu", "/fsd/fsf/public/files", "all"),
    ("download.companieshouse.gov.uk", "/", "files"),
    ("api.company-information.service.gov.uk", "/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/company/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/officers/", "all"),
    ("find-and-update.company-information.service.gov.uk", "/search", "all"),
    ("goldencopy.gleif.org", "/storage/", "all"),
    ("goldencopy.gleif.org", "/api/v2/golden-copies/", "files"),
    ("api.gleif.org", "/api/", "all"),
    ("offshoreleaks-data.icij.org", "/", "all"),
    ("offshoreleaks.icij.org", "/nodes/", "all"),
    ("offshoreleaks.icij.org", "/search", "all"),
    ("data.opensanctions.org", "/", "all"),
    ("www.opensanctions.org", "/entities/", "all"),
    ("www.opensanctions.org", "/search", "all"),
    ("members-api.parliament.uk", "/api/", "all"),
)
DATA_FILE = re.compile(r"\.(?:zip|gz|bz2|csv|tsv|txt|xml|json|jsonl|xlsx?|ods|odt|parquet)$", re.I)


def block(reason):
    sys.stderr.write("Blocked by .claude/hooks/guard_real_data.py: " + reason + "\n")
    sys.exit(2)


def project_dir():
    return (os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).rstrip("/")


def strip_heredocs(command):
    """Remove heredoc bodies; block a body that feeds an interpreter and names real data."""
    lines = command.split("\n")
    kept, i = [], 0
    while i < len(lines):
        line = lines[i]
        kept.append(line)
        match = HEREDOC.search(line)
        i += 1
        if not match:
            continue
        body = []
        while i < len(lines) and lines[i].strip() != match.group(2):
            body.append(lines[i])
            i += 1
        if i < len(lines):
            kept.append(lines[i])
            i += 1
        before = line[: match.start()]
        tokens = re.findall(r"[A-Za-z0-9_.\-/]+", before.split("|")[-1])
        names = {os.path.basename(w) for w in tokens} & INTERPRETERS
        text = "\n".join(body)
        if names and (
            any(m in text for m in MARKS) or REAL_INSTANCE.search(text) or HUMAN_ONLY.search(text)
        ):
            block(
                "a script fed to " + ", ".join(sorted(names)) + " names real data, the real "
                "Neo4j instance or a human-only command"
            )
    return "\n".join(kept)


def split_commands(command):
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    commands, current = [], []
    for token in lexer:
        if token in OPERATORS or set(token) <= set("&|;()"):
            if current:
                commands.append(current)
            current = []
        else:
            current.append(token)
    if current:
        commands.append(current)
    return commands


def parse(command):
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


def absolute(value, cwd):
    """The value as a normalised absolute path, resolved against cwd (or the project)."""
    root = project_dir()
    value = value.replace("${CLAUDE_PROJECT_DIR}", root).replace("$CLAUDE_PROJECT_DIR", root)
    if value.startswith("~"):
        value = os.path.expanduser(value)
    if not value.startswith("/"):
        value = os.path.join(cwd or root, value)
    return os.path.normpath(value)


def relative(token, cwd):
    """The token as a path relative to the project directory, or None."""
    value = token.split("=", 1)[1] if token.startswith("-") and "=" in token else token
    if not value or value.startswith("-") or "\n" in value:
        return None
    root = project_dir()
    value = absolute(value, cwd)
    if value == root:
        return "."
    if value.startswith(root + "/"):
        return value[len(root) + 1 :]
    return None


def inside(rel):
    return rel is not None and any(rel == p or rel.startswith(p + "/") for p in PROTECTED)


def glob_reaches(pattern, protected, double_star=True):
    """True when a glob's leading segments can match the protected folder's segments."""
    pat, prot = pattern.split("/"), protected.split("/")
    for i, segment in enumerate(prot):
        if i >= len(pat):
            return False
        if pat[i] == "**":
            return double_star or i > 0
        if not fnmatch.fnmatch(segment, pat[i]):
            return False
    return True


def touches(token, cwd):
    """True when a token names a protected folder, something inside one, or a glob that can."""
    if any(m in token for m in MARKS):
        return True
    rel = relative(token, cwd)
    if rel is None:
        return False
    if inside(rel):
        return True
    return any(ch in rel for ch in "*?[") and any(glob_reaches(rel, p) for p in PROTECTED)


def checked_tokens(tokens):
    """Tokens that may be paths: for git and gh, values of message-like flags are text."""
    if program(tokens)[0] not in ("git", "gh"):
        return list(tokens)
    out, skip = [], False
    for token in tokens:
        if skip:
            skip = False
            continue
        if token in TEXT_FLAGS:
            skip = True
            continue
        if any(token.startswith(flag + "=") for flag in TEXT_FLAGS if flag.startswith("--")):
            continue
        out.append(token)
    return out


def program(tokens):
    while tokens and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", tokens[0]):
        tokens = tokens[1:]
    return (os.path.basename(tokens[0]), tokens[1:]) if tokens else ("", [])


def uv_run_target(args):
    """For `uv run [options] TARGET ...`, the target program, else None."""
    if args[:1] != ["run"]:
        return None
    rest, skip = args[1:], False
    for arg in rest:
        if skip:
            skip = False
            continue
        if arg in UV_VALUE_OPTIONS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return os.path.basename(arg)
    return None


def compose_subcommand(args):
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in COMPOSE_VALUE_OPTIONS:
            skip = True
            continue
        if arg.startswith("-"):
            continue
        return arg
    return None


def project_command(name, args):
    return name in ("make", "neonradar") or (name == "uv" and uv_run_target(args) == "neonradar")


def allowed_on_real(name, args):
    if name in SAFE:
        return not (name == "find" and any(a in FIND_ACTIONS for a in args))
    if project_command(name, args):
        return True
    if name == "git":
        if any(a in GIT_NOT_ON_REAL or a.split("=", 1)[0] in GIT_NOT_ON_REAL for a in args):
            return False
        sub = [a for a in args if not a.startswith("-")]
        return bool(sub) and sub[0] in GIT_SAFE
    return False


def allowed_on_real_instance(name, args):
    if project_command(name, args):
        return True
    if name == "git":  # git reads tracked files and history only (GIT_NEVER is checked first)
        sub = [a for a in args if not a.startswith("-")]
        return bool(sub) and sub[0] in GIT_SAFE
    if name == "docker" and args[:1] == ["compose"]:
        return compose_subcommand(args[1:]) in COMPOSE_OK
    if name == "docker-compose":
        return compose_subcommand(args) in COMPOSE_OK
    return False


def recursive(name, args):
    def short_flags(letters):
        return any(re.match(r"^-[a-zA-Z]+$", a) and any(c in a for c in letters) for a in args)

    if name in ("grep", "egrep", "fgrep"):
        return short_flags("rR") or any(
            a in ("--recursive", "--dereference-recursive") for a in args
        )
    if name == "rg":
        return any(
            a in ("--no-ignore", "--no-ignore-vcs", "-u", "-uu", "-uuu", "--unrestricted")
            for a in args
        )
    if name in ("ag", "ack", "tar", "zip", "rsync", "scp"):
        return True
    if name == "cp":
        return short_flags("rRa") or any(a in ("--recursive", "--archive") for a in args)
    if name == "find":
        return any(a in FIND_ACTIONS for a in args)
    return False


def walk(commands, cwd):
    """Each command with the folder it runs in, following cd, pushd and popd on the line."""
    root = project_dir()
    here = absolute(cwd, None) if cwd else root
    previous, stack, out = here, [], []
    for tokens in commands:
        name, args = program(tokens)
        out.append((tokens, name, args, here))
        targets = [a for a in args if not a.startswith("-")]
        if name in ("cd", "pushd"):
            if name == "pushd":
                stack.append(here)
            if not targets or targets[0] == "~":
                new = os.path.expanduser("~")
            elif targets[0] == "-":
                new = previous
            else:
                new = absolute(targets[0], here)
            previous, here = here, new
        elif name == "popd" and stack:
            previous, here = here, stack.pop()
    return out


def check_bash(command, cwd):
    command = strip_heredocs(command)
    commands = parse(command)
    if commands is None:
        if any(m in command for m in MARKS) or REAL_INSTANCE.search(command):
            block(
                "could not parse a command that names real data or the real Neo4j instance; "
                "use a simple ls, du or neonradar command"
            )
        return
    steps = walk(commands, cwd)
    line_touches = False
    for tokens, _name, _args, here in steps:
        if inside(relative(here, None)):
            line_touches = True
        if any(touches(t, here) for t in checked_tokens(tokens)):
            line_touches = True
    for tokens, name, args, here in steps:
        text = " ".join(checked_tokens(tokens))
        if name in WRAPPERS:
            block(
                "'" + name + "' fakes a terminal; human-only commands must be run by a human "
                "in a real terminal (PHASE-2.md G10)"
            )
        if HUMAN_ONLY.search(text):
            block(
                "er label, er review and api serve --real are human-only commands; ask the "
                "operator to run them in a terminal (PHASE-2.md G10)"
            )
        if name in FETCHERS:
            for arg in args:
                if "://" in arg:
                    check_url(arg, name)
                elif not arg.startswith("-") and BARE_HOST.match(arg):
                    check_url("https://" + arg, name)
        compose = None
        if name == "docker" and args[:1] == ["compose"]:
            compose = compose_subcommand(args[1:])
        elif name == "docker-compose":
            compose = compose_subcommand(args)
        if compose == "config" and not any(a in CONFIG_SAFE for a in args):
            block(
                "docker compose config prints the interpolated configuration, including "
                "passwords from .env (PHASE-1.md G6); use --quiet, --services or --profiles"
            )
        if name == "docker" and (
            args[:1] == ["inspect"] or args[:2] in (["container", "inspect"], ["volume", "inspect"])
        ):
            block("docker inspect prints container environments, including passwords from .env")
        if name in ("cd", "pushd"):
            targets = [a for a in args if not a.startswith("-")]
            if targets and (
                touches(targets[0], here) or relative(targets[0], here) in ANCESTORS[1:]
            ):
                block(
                    "do not cd into data/, data/cache/ or a real-data folder; "
                    "use paths from the project root"
                )
        if name == "git" and any(a in GIT_NEVER or a.split("=", 1)[0] in GIT_NEVER for a in args):
            block(
                "git with --no-index, --untracked or --no-exclude-standard reads files outside "
                "the index, including data/cache/; search tracked files with plain `git grep`"
            )
        if recursive(name, args):
            paths = [a for a in args if not a.startswith("-") and relative(a, here) is not None]
            if (
                name in ("grep", "egrep", "fgrep", "rg", "ag", "ack")
                and not paths[1:]
                and (name != "grep" or len(paths) <= 1)
            ):
                paths.append(".")
            if any(relative(a, here) in ANCESTORS or touches(a, here) for a in paths):
                block(
                    name + " would read into data/cache/real or data/cache/spikes; use `git grep`, "
                    "or name a folder that does not contain them"
                )
        if REAL_INSTANCE.search(text) and not allowed_on_real_instance(name, args):
            block(
                "'" + name + "' on a command that names the real Neo4j instance (neo4j-real, "
                "ports 7475, 7688 and 8001). Only uv run neonradar, make and docker compose "
                "up, start, stop, down or ps may use it; the default instance (7687) and the "
                "API on port 8000 hold synthetic data"
            )
        if line_touches and not allowed_on_real(name, args):
            block(
                "'" + name + "' on a command line that touches real data. Real records are read "
                "only by humans. Allowed: ls, du, wc, stat, find (no actions), rm, mkdir, "
                "git status, log, diff, show, grep, ls-files, blame, rev-parse, check-ignore, "
                "branch, uv run neonradar, make"
            )


def check_paths(tool, tool_input, cwd):
    """Read, Grep and Glob: refuse paths, globs and patterns that can reach real data."""
    keys = {"Read": ("file_path",), "Grep": ("path", "glob"), "Glob": ("path", "pattern")}[tool]
    here = absolute(cwd, None) if cwd else project_dir()
    search_root = here
    if isinstance(tool_input.get("path"), str) and tool_input["path"]:
        search_root = absolute(tool_input["path"].replace("\\", "/"), here)
    for key in keys:
        value = tool_input.get(key)
        if not isinstance(value, str) or not value:
            continue
        value = value.replace("\\", "/")
        if any(m in value for m in MARKS):
            block(tool + " may not name data/cache/real or data/cache/spikes (PHASE-2.md G9)")
        if key == "glob":
            continue
        full = absolute(value, search_root if key == "pattern" else here)
        rel = relative(full, None)
        if any(m in full for m in MARKS) or inside(rel):
            block(tool + " may not read data/cache/real or data/cache/spikes (PHASE-2.md G9)")
        if tool == "Grep" and key == "path" and rel in ANCESTORS[1:]:
            block("Grep over data/ or data/cache/ could reach real data; name another folder")
        if (
            rel
            and any(ch in rel for ch in "*?[")
            and any(glob_reaches(rel, p, double_star=False) for p in PROTECTED)
        ):
            block(tool + " pattern can reach data/cache/real or data/cache/spikes (PHASE-2.md G9)")


def check_url(url, via="WebFetch"):
    try:
        parts = urlsplit(url.strip())
    except ValueError:
        block("could not parse the URL")
        return
    host = (parts.hostname or "").lower()
    path = parts.path or "/"
    low = path.lower()
    if low.endswith(".xsd") or "swagger" in low or "openapi" in low:
        return
    for rule_host, prefix, mode in WEB_DATA:
        if host != rule_host and not host.endswith("." + rule_host):
            continue
        if not path.startswith(prefix):
            continue
        if mode == "files" and not DATA_FILE.search(path):
            continue
        block(
            via + " would bring list, register or leak data (or a page about real people) "
            "into the conversation; fetch documentation and schemas only, and let the loaders "
            "download data (PHASE-2.md G9)"
        )


def check_mcp():
    try:
        with open(os.path.join(project_dir(), ".mcp.json"), encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return
    if REAL_INSTANCE.search(text):
        block(
            ".mcp.json points the Neo4j MCP server at the real instance; it must use the "
            "default instance (bolt://localhost:7687), which holds synthetic data only"
        )


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return 0
    tool = data.get("tool_name") or ""
    tool_input = data.get("tool_input") or {}
    if not isinstance(tool_input, dict):
        return 0
    if tool.startswith("mcp__neo4j"):
        check_mcp()
    elif tool == "Bash":
        check_bash(str(tool_input.get("command") or ""), data.get("cwd"))
    elif tool in ("Read", "Grep", "Glob"):
        check_paths(tool, tool_input, data.get("cwd"))
    elif tool == "WebFetch":
        check_url(str(tool_input.get("url") or ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**`scripts/tests/test_guard_real_data.py`** (verbatim):

```python
"""Tests for .claude/hooks/guard_real_data.py (PHASE-2.md M2.0)."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[2] / ".claude" / "hooks" / "guard_real_data.py"
SLS = "https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/"
EU = "https://webgate.ec.europa.eu/fsd/fsf/public/"
CH = "https://find-and-update.company-information.service.gov.uk/"
GLEIF = "https://goldencopy.gleif.org/"

ALLOW = [
    "ls data/cache/real/sources",
    "du -sh data/cache/real",
    "du -sh data/cache/*",
    "ls data/fixtures/*/x",
    "cat data/fixtures/er-bench/*.csv",
    "uv run neonradar data status --profile uk-tiny",
    "uv run --no-sync neonradar er run --profile uk-tiny",
    "make load PROFILE=uk-tiny",
    "rm -rf data/cache/real/records/uk-tiny",
    "cat data/cache/reports/uk-tiny/er-run-20261102T091500.json",
    "cat data/cache/synthetic/resolution/demo/er-20261102T091500-3b7e/canonical.csv",
    "find data/cache/real -name '*.json' | wc -l",
    "wc -l data/cache/real/records/uk-tiny/*/*.ftm.jsonl",
    'git commit -m "docs: explain the data/cache/real layout"',
    "git commit -m \"$(cat <<'EOF'\nfeat(ingest): write records\n\n"
    'Records go to data/cache/real/records.\nEOF\n)"',
    "cat > docs/data/real-data-handling.md <<'EOF'\nReal data lives in data/cache/real/ only.\nEOF",
    'grep -rn "def load" graph/src',
    'rg "def load"',
    'git grep -n "data/cache/real"',
    "git check-ignore -v data/cache/real/x.json",
    "git log --oneline -3 && git diff --stat",
    'gh pr create --title "x" --body "outputs stay in data/cache/real"',
    "python3 -c 'print(1)'",
    "uv run pytest -m integration graph/tests/",
    "tar czf /tmp/docs.tgz docs/",
    "ls -la data/cache/",
    "stat data/cache/real/decisions.jsonl && echo ok",
    "cd docs && ls",
    "cd data/fixtures && ls",
    "cd graph && ls ../docs",
    "pushd docs && ls && popd",
    "make up-real",
    "docker compose --profile real up -d --wait neo4j-real",
    "docker compose --profile real stop neo4j-real",
    "docker compose ps neo4j-real",
    "uv run neonradar graph verify --real",
    "NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688 uv run neonradar graph load --profile uk-tiny",
    'git commit -m "feat(dev): add the neo4j-real service on port 7688"',
    'git commit -m "feat(resolve): add neonradar er label and er review"',
    'gh pr create --title "M2.10c" --body "er label refuses without a terminal"',
    "curl -s http://127.0.0.1:8000/api/v1/health",
    'docker compose exec neo4j cypher-shell -u neo4j -p x "MATCH (p:Person) RETURN p.names"',
    "curl -sO https://assets.publishing.service.gov.uk/media/x/SanctionsListSchema-4.33.3.xsd",
    "curl -fsSL https://raw.githubusercontent.com/opensanctions/rigour/v2.5.0/README.md",
    "git grep -n neo4j-real",
    "docker compose --profile real config --services",
    "uv run neonradar er sample --profile demo --run latest --seed 7",
]

BLOCK = [
    "cat data/cache/real/records/uk-tiny/gb_companies_house/x.ftm.jsonl",
    "head -n 5 data/cache/spikes/companies_house/out.ftm.jsonl",
    "zcat data/cache/real/sources/gb_companies_house/companies/2026-10-01/BasicCompanyData.zip",
    "python3 -c \"import json; print(open('data/cache/real/x.json').read())\"",
    "uv run python -c \"print(open('data/cache/real/x').read())\"",
    "jq . data/cache/real/resolution/uk-sample/er-x/candidates.jsonl",
    "duckdb -c \"select * from 'data/cache/real/x.parquet'\"",
    "strings data/cache/real/duckdb-tmp/er-x/duckdb_temp_storage-0.tmp",
    "cp data/cache/real/labels/er-x/a.jsonl /tmp/",
    "tar czf /tmp/x.tgz data/cache/real",
    "tar czf /tmp/repo.tgz .",
    'grep -r "SMITH" .',
    "grep -rn SMITH data/",
    "grep -r SMITH",
    "rg --no-ignore SMITH",
    "cd data/cache/real && ls",
    "cd data/cache && cat real/x",
    "cd data && ls",
    r"find data/cache/real -name '*.jsonl' -exec cat {} \;",
    "find data/cache/real -type f | xargs head",
    'ls data/cache/real | while read f; do cat "data/cache/real/$f"; done',
    "less data/cache/spikes/x",
    "python3 - <<'EOF'\nprint(open('data/cache/real/x').read())\nEOF",
    "cat data/cache/*/records/x",
    "cat data/*/real/x",
    "cat data/cache/**/x.json",
    "head data/cache/re*/records/a",
    "cat ./data/cache/real/x",
    "cat ../../../data/cache/real/x",
    "cat ~/neonradar-worktree/data/cache/real/x",
    "cat /home/dev/neonradar-wt2/data/cache/spikes/x",
    "git add -f data/cache/real/x.json",
    "gh gist create data/cache/real/x",
    "gh issue create --title t --body-file data/cache/real/x",
    "sort data/cache/real/x | head",
    "cp -r . /tmp/repo",
    "git grep --no-index SMITH data/cache/real",
    "git grep --no-index SMITH",
    "git grep --untracked SMITH",
    "git grep --no-exclude-standard --untracked SMITH",
    "git diff --no-index /dev/null data/cache/real/x",
    "git commit -F data/cache/real/x",
    "git grep -f data/cache/real/names.txt",
    'rm -rf data/cache/real/x && git commit -m "purge"',
    "cd data/fixtures && cat ../cache/real/x.jsonl",
    "cd scripts && head ../data/cache/re*/records/a",
    "pushd scripts && cat ../data/cache/sp*/x && popd",
    'docker compose exec neo4j-real cypher-shell "MATCH (n) RETURN n LIMIT 1"',
    "docker compose --profile real logs neo4j-real",
    "docker volume rm neonradar_neo4j-real-data",
    "curl -s 'http://127.0.0.1:8001/api/v1/search?q=smith'",
    "curl -s http://localhost:7475/browser/",
    'cypher-shell -a bolt://127.0.0.1:7688 "MATCH (n) RETURN count(n)"',
    'echo "MATCH (p:Person) RETURN p.names" | cypher-shell -a neo4j://localhost:7688',
    "bash -c \"cypher-shell -a bolt://localhost:7688 'MATCH (n) RETURN n'\"",
    'cypher-shell -d realdata "MATCH (n) RETURN n LIMIT 1"',
    "NR_NEO4J_REAL_URI=bolt://127.0.0.1:7688 python3 scripts/peek.py",
    "printenv NEO4J_REAL_PASSWORD",
    "uv run python -c \"from neo4j import GraphDatabase; GraphDatabase.driver('bolt://x:7688')\"",
    "python3 - <<'EOF'\nfrom neo4j import GraphDatabase\n"
    'GraphDatabase.driver("bolt://localhost:7688")\nEOF',
    "uv run neonradar er label --profile uk-sample",
    "uv run neonradar er review --profile demo",
    "uv run neonradar api serve --real",
    "neonradar er label --profile demo --run latest",
    "uv run python -m neonradar_cli er review --profile demo",
    'bash -c "uv run neonradar er label --profile uk-sample"',
    'script -qc "uv run neonradar er label" /dev/null',
    "unbuffer uv run neonradar er review --profile demo",
    "expect -c 'spawn uv run neonradar er label'",
    "faketty uv run neonradar er review",
    "curl -s https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml | head -50",
    "wget -qO- https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile.zip | zcat | head",
    "curl -s https://api.company-information.service.gov.uk/company/01800000/officers",
    "curl -s sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.csv",
    "docker compose --profile real config",
    "docker inspect $(docker ps -q)",
]

TOOL_ALLOW = [
    ("Read", {"file_path": "{project}/docs/data/real-data-handling.md"}),
    ("Read", {"file_path": "{project}/data/cache/reports/uk-tiny/er-run-20261102T091500.json"}),
    ("Read", {"file_path": "{project}/data/cache/synthetic/resolution/demo/er-1/canonical.csv"}),
    ("Grep", {"pattern": "def load", "path": "graph/src"}),
    ("Grep", {"pattern": "data/cache/real"}),
    ("Grep", {"pattern": "SMITH", "path": "{project}"}),
    ("Glob", {"pattern": "**/*.py"}),
    ("Glob", {"pattern": "data/fixtures/**/*.jsonl"}),
    ("WebFetch", {"url": "https://assets.publishing.service.gov.uk/media/x/SanctionsList.xsd"}),
    ("WebFetch", {"url": SLS + "XML.xsd"}),
    ("WebFetch", {"url": "https://members-api.parliament.uk/swagger/v1/swagger.json"}),
    ("WebFetch", {"url": "https://download.companieshouse.gov.uk/en_output.html"}),
    ("WebFetch", {"url": GLEIF + "api/v2/golden-copies/publishes/latest"}),
    ("WebFetch", {"url": "https://ofac.treasury.gov/faqs/topic/1521"}),
    ("WebFetch", {"url": "https://offshoreleaks.icij.org/pages/database"}),
    ("WebFetch", {"url": "https://www.opensanctions.org/datasets/gb_fcdo_sanctions/"}),
    ("WebFetch", {"url": EU + "rss"}),
    ("mcp__neo4j__read-cypher", {"query": "MATCH (p:Person) RETURN p.names LIMIT 3"}),
    ("mcp__neo4j__get-schema", {}),
]

TOOL_BLOCK = [
    ("Read", {"file_path": "{project}/data/cache/real/records/uk-tiny/x.ftm.jsonl"}),
    ("Read", {"file_path": "{project}/data/cache/spikes/companies_house/out.json"}),
    ("Read", {"file_path": "/home/dev/neonradar-wt2/data/cache/real/x.jsonl"}),
    ("Read", {"file_path": "{project}/data/fixtures/../cache/real/x.jsonl"}),
    ("Grep", {"pattern": "SMITH", "path": "data/cache/real"}),
    ("Grep", {"pattern": "SMITH", "path": "{project}/data/cache/spikes"}),
    ("Grep", {"pattern": "SMITH", "path": "data/cache"}),
    ("Grep", {"pattern": "SMITH", "path": "data"}),
    ("Grep", {"pattern": "SMITH", "glob": "data/cache/real/**"}),
    ("Glob", {"pattern": "data/cache/real/**/*.jsonl"}),
    ("Glob", {"pattern": "data/cache/*/records/*"}),
    ("Glob", {"pattern": "**/*.jsonl", "path": "{project}/data/cache"}),
    ("Glob", {"pattern": "*", "path": "{project}/data/cache/spikes"}),
    ("WebFetch", {"url": "https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml"}),
    ("WebFetch", {"url": SLS + "SDN_ADVANCED.XML"}),
    ("WebFetch", {"url": "https://www.treasury.gov/ofac/downloads/sdn.xml"}),
    ("WebFetch", {"url": "https://scsanctions.un.org/resources/xml/en/consolidated.xml"}),
    ("WebFetch", {"url": EU + "files/xmlFullSanctionsList_1_1/content?token=x"}),
    ("WebFetch", {"url": "https://download.companieshouse.gov.uk/BasicCompanyDataAsOneFile.zip"}),
    ("WebFetch", {"url": CH + "company/01800000/officers"}),
    (
        "WebFetch",
        {"url": "https://api.company-information.service.gov.uk/company/01800000/officers"},
    ),
    ("WebFetch", {"url": GLEIF + "storage/golden-copy-files/2026/10/17/x.csv.zip"}),
    ("WebFetch", {"url": GLEIF + "api/v2/golden-copies/publishes/lei2/latest.csv"}),
    (
        "WebFetch",
        {"url": "https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip"},
    ),
    ("WebFetch", {"url": "https://offshoreleaks.icij.org/nodes/12000001"}),
    (
        "WebFetch",
        {"url": "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json"},
    ),
    ("WebFetch", {"url": "https://members-api.parliament.uk/api/Members/Search?House=Commons"}),
]


def run(tmp_path, tool, tool_input, cwd=None, mcp_json=None):
    project = tmp_path / "project"
    project.mkdir(exist_ok=True)
    if mcp_json is not None:
        (project / ".mcp.json").write_text(mcp_json)
    env = dict(os.environ, CLAUDE_PROJECT_DIR=str(project))
    payload = {"tool_name": tool, "tool_input": tool_input, "cwd": str(cwd or project)}
    result = subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )
    return result.returncode


def filled(tmp_path, tool_input):
    project = str(tmp_path / "project")
    return {k: v.replace("{project}", project) for k, v in tool_input.items()}


@pytest.mark.parametrize("command", ALLOW)
def test_allowed(tmp_path, command):
    assert run(tmp_path, "Bash", {"command": command}) == 0


@pytest.mark.parametrize("command", BLOCK)
def test_blocked(tmp_path, command):
    assert run(tmp_path, "Bash", {"command": command}) == 2


@pytest.mark.parametrize(("tool", "tool_input"), TOOL_ALLOW)
def test_tools_allowed(tmp_path, tool, tool_input):
    assert run(tmp_path, tool, filled(tmp_path, tool_input)) == 0


@pytest.mark.parametrize(("tool", "tool_input"), TOOL_BLOCK)
def test_tools_blocked(tmp_path, tool, tool_input):
    assert run(tmp_path, tool, filled(tmp_path, tool_input)) == 2


def test_cwd_inside_real_data(tmp_path):
    inside = tmp_path / "project" / "data" / "cache" / "real" / "records"
    assert run(tmp_path, "Bash", {"command": "cat x.json"}, cwd=inside) == 2
    assert run(tmp_path, "Bash", {"command": "ls"}, cwd=inside) == 0


def test_mcp_server_must_use_the_default_instance(tmp_path):
    query = {"query": "MATCH (p:Person) RETURN p.names LIMIT 3"}
    default = '{"mcpServers": {"neo4j": {"env": {"NEO4J_MCP_URI": "bolt://localhost:7687"}}}}'
    real = '{"mcpServers": {"neo4j": {"env": {"NEO4J_MCP_URI": "bolt://localhost:7688"}}}}'
    assert run(tmp_path, "mcp__neo4j__read-cypher", query, mcp_json=default) == 0
    assert run(tmp_path, "mcp__neo4j__read-cypher", query, mcp_json=real) == 2
```

**`scripts/cypher-lint/lint.mjs`** (verbatim):

```javascript
#!/usr/bin/env node
// Lint every .cypher file under the given folders with Neo4j's Cypher language support,
// applying Cypher 5 rules. Errors and warnings fail; "Parameter $x is not defined" is
// ignored because parameters are bound at run time. A template declares its placeholder
// values in a header comment, for example: // lint-values: max_hops=1,2,8 rel_type=OWNS
// and uses them as {{max_hops}}; every combination is linted.
import { lintCypherQuery } from '@neo4j-cypher/language-support';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join } from 'node:path';

const roots = process.argv.length > 2 ? process.argv.slice(2) : ['graph', 'detect', 'api'];
const IGNORED = [/^Parameter \$[A-Za-z_][A-Za-z0-9_]* is not defined\.?$/];

function* cypherFiles(dir) {
  let entries;
  try { entries = readdirSync(dir); } catch { return; }
  for (const name of entries) {
    if (name === 'node_modules' || name.startsWith('.')) continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* cypherFiles(path);
    else if (name.endsWith('.cypher')) yield path;
  }
}

function statements(text) {
  const out = [];
  let lines = [];
  let start = 0;
  text.split('\n').forEach((line, index) => {
    if (lines.length === 0) {
      if (/^\s*(\/\/.*)?$/.test(line)) return;
      start = index + 1;
    }
    lines.push(line);
    if (/;\s*$/.test(line)) {
      out.push({ start, text: lines.join('\n').replace(/;\s*$/, '') });
      lines = [];
    }
  });
  if (lines.join('').trim()) out.push({ start, text: lines.join('\n') });
  return out;
}

function variants(text) {
  const header = text.match(/^\s*\/\/\s*lint-values:\s*(.+)$/m);
  if (!header) return [text];
  let combos = [{}];
  for (const pair of header[1].trim().split(/\s+/)) {
    const [key, values] = pair.split('=');
    combos = combos.flatMap((c) => values.split(',').map((v) => ({ ...c, [key]: v })));
  }
  return combos.map((c) => text.replace(/\{\{(\w+)\}\}/g, (_, k) => (k in c ? c[k] : `{{${k}}}`)));
}

let failures = 0;
let checked = 0;
for (const root of roots) {
  for (const file of cypherFiles(root)) {
    for (const variant of variants(readFileSync(file, 'utf8'))) {
      for (const { start, text } of statements(variant)) {
        checked += 1;
        const { diagnostics } = lintCypherQuery(`CYPHER 5 ${text}`, {});
        for (const d of diagnostics) {
          if (d.severity > 2 || IGNORED.some((re) => re.test(d.message))) continue;
          failures += 1;
          console.log(`${file}:${start + d.range.start.line}: ${d.severity === 1 ? 'error' : 'warning'}: ${d.message}`);
        }
        if (/\{\{\w+\}\}/.test(text)) {
          failures += 1;
          console.log(`${file}:${start}: error: placeholder without a lint-values entry`);
        }
      }
    }
  }
}
console.log(`cypher-lint: ${checked} statements checked, ${failures} problems`);
process.exit(failures ? 1 : 0);
```

### M2.1 Contracts 1.1.0 (three sub-milestones)

Each sub-milestone runs in a contract-change session (1.5): the tech lead has approved its issue (texts in 5.0) and set `NR_ALLOW_CONTRACT_CHANGE=1` for that session. Read section 5 of this spec and of PHASE-1.md before starting. Each pull request carries the label `contract-change` and runs `contract-guardian` in step 7 of the protocol.

#### M2.1a Record contract C1 1.1.0

| | |
|---|---|
| Squad, human owner | Tech lead (data steward approves the licence fields) |
| Depends on | M2.0; the C1 contract-change issue approved |
| Branch | `p2/m2-1a-record-1-1` |
| Labels | `agent`, `phase-2`, `contract-change`, `squad:ingest`, `data-source` |
| Plan first | No |
| Real-data run | none |

**Deliverables.**

1. `contracts/datasets.yaml`: the five entries in 5.1 verbatim, `kind` plus `anchor_priority` on all ten entries, and `status: active` on the three Phase 1 spike datasets (5.1).
2. `contracts/src/neonradar_contracts/datasets.py`: `Dataset` gains `kind: Literal["registry", "list", "leak", "synthetic"] | None = None` and `anchor_priority: int | None = None`; `load_registry()` checks that priorities are unique; `commercial_use` accepts `permission-required` (if Phase 1 typed it as a closed set).
3. `contracts/src/neonradar_contracts/records.py`: `NrExtension` gains `ch_person_number: str | None`, `psc_statements: list[str] | None`, `accounts_category: str | None`, `share_pct_min_exclusive: bool | None`, `share_pct_max_exclusive: bool | None`; `synthetic_kind` accepts `"list"` and `"leak"` besides `"registry"` and `"activity"`; wherever Phase 1's validator checks which schemata may carry a key, `is_nominee` is also allowed on `Ownership`, and `share_pct_min`, `share_pct_max` and the two exclusive flags on `Ownership` and `Control`; `v` accepts `"1.0"` and `"1.1"`; `Manifest.record_contract` accepts `"1.0.0"` and `"1.1.0"`.
4. `versions.py`: `RECORD = "1.1.0"`, `CONTRACTS = "1.1.0"`.
5. `contracts/examples/c1/demo-1.1.ftm.jsonl` (the seven lines in 5.1) and its manifest, validating in strict mode.
6. `contracts/C1-record.md`: a "Changes in 1.1.0" section (5.1, including the table of wider keys); `contracts/CHANGELOG.md`: `## 1.1.0 (unreleased)` with the C1 lines.
7. `make contracts` (JSON Schemas regenerated); tests in 5.4.
8. `DATA_SOURCES.md`: one row per new dataset with title, publisher, licence, the attribution line from 5.1, the personal-data note ("whoever loads it is a controller under UK GDPR"), and for the UK list and the Parliament data the no-endorsement sentence from 5.1; the data steward edits the wording in review.

**Acceptance.**

```bash
uv run neonradar contracts validate-records contracts/examples/c1/demo-1.1.ftm.jsonl --strict
uv run neonradar contracts validate-records contracts/examples/c1/demo.ftm.jsonl --strict   # 1.0 examples still valid
uv run pytest contracts/tests/test_records.py contracts/tests/test_datasets.py -q
make contracts && git diff --exit-code contracts/schemas/
make contracts-check && make check
```

**Review focus (humans).** Data steward: approve each new licence field and attribution line explicitly in the review (G2-11); is the EU licence reference (a `LicenseRef` for Decision 2011/833/EU, not CC BY 4.0) what you can defend? Tech lead: is every change additive, including the wider `synthetic_kind`, `is_nominee` and share keys?

#### M2.1b Graph schema C2 1.1.0

| | |
|---|---|
| Squad, human owner | Tech lead (Graph and Detection squads review) |
| Depends on | M2.1a; the C2 contract-change issue approved |
| Branch | `p2/m2-1b-graph-1-1` |
| Labels | `agent`, `phase-2`, `contract-change`, `squad:graph` |
| Plan first | Yes |
| ADR | none (ADR-0016 follows in M2.11) |
| Real-data run | none |

**Deliverables.**

1. `graph/schema/migrations/0002_resolution.cypher`, verbatim from 5.2.
2. `contracts/src/neonradar_contracts/graph.py`: the `:SourceRecord` properties, the extended `RESOLVED_TO` properties, `POSSIBLY_SAME_AS` with its properties (`match_probability` nullable, `rule`), the new entity and company properties, the new `OWNS` and `CONTROLS` properties, and the mappings from `nr` keys to them, all as data (as in Phase 1).
3. `graph/src/neonradar_graph/mapping.py`: map `nr.psc_statements` and `nr.accounts_category` to the company properties; the two share flags and `nr.is_nominee` of an `Ownership` to `OWNS` (`false` when absent); the band of a `Control` (`nr.share_pct_min`, `nr.share_pct_max` and the two flags) to `CONTROLS` (bounds null and flags `false` when absent). Nothing else changes in this pull request (M2.11 adds resolution and the separate real-data instance of L17).
4. `contracts/C2-graph-schema.md`: a "Changes in 1.1.0" section with the new properties, the loader rules L8 to L17 and the invariants I7 to I14 (5.2), and the Mermaid diagram updated with `SourceRecord`, `RESOLVED_TO` and `POSSIBLY_SAME_AS`.
5. `versions.py`: `GRAPH_SCHEMA = "1.1.0"`; `contracts/CHANGELOG.md` lines for C2.
6. Tests: `test_graph_mapping.py` and `test_migrations.py` as in 5.4 (the index count query is in 5.2).
7. Run `make contracts`. If the OpenAPI snapshot changes (for example because Phase 1 built the `rel_types` parameter from C2's relationship types, which now include `POSSIBLY_SAME_AS`), commit the regenerated `contracts/openapi/v1.json` and `ui/src/api/schema.d.ts` in this pull request and say so: it is a contract-change session, and M2.1c then starts from that snapshot.

**Acceptance.**

```bash
make up && uv run neonradar graph migrate          # applies 0002 to the default instance
uv run neonradar graph migrate                     # nothing to apply
docker compose exec neo4j cypher-shell -u neo4j -p "$NEO4J_PASSWORD" \
  "SHOW CONSTRAINTS YIELD name RETURN count(*) AS n"   # n = 23
uv run pytest contracts/tests/test_graph_mapping.py -q
uv run pytest -m integration graph/tests/test_migrations.py
make cypher-lint && make contracts-check && make check
```

**Review focus (humans).** Detection squad: can every Phase 3 detector ignore `POSSIBLY_SAME_AS` and still see canonical nodes? Does anything in the migration change what a Phase 1 query returns? (The full-text index keeps its name.) Graph mentor: is a voting-rights band on `CONTROLS` clearly separate from a share on `OWNS` for every reader of the schema?

#### M2.1c API contract C3 1.1.0

| | |
|---|---|
| Squad, human owner | Tech lead (Copilot and UI squads review; data steward reviews the notice) |
| Depends on | M2.1b; the C3 contract-change issue approved |
| Branch | `p2/m2-1c-api-1-1` |
| Labels | `agent`, `phase-2`, `contract-change`, `squad:copilot`, `squad:ui` |
| Plan first | No |
| Real-data run | none |

**Deliverables.**

1. `contracts/src/neonradar_contracts/api.py`: `ResolutionMember`, `PossibleMatch` (with `rule: str | None`) and `ResolutionResponse` exactly as 5.3; `PathRef` gains `effective_share_min_exclusive: bool | None` and `effective_share_max_exclusive: bool | None`, and its field descriptions carry the sentence from 5.3 item 4 ("an effective share is NeonRadar's calculation ...").
2. `api/src/neonradar_api/main.py`: the route `GET /api/v1/entities/{entity_id}/resolution` with its response model, returning 501 with a problem body naming M2.12; the descriptions of the ownership and paths routes and their parameters updated to the semantics in 5.3 (still 501 until M2.12); on all three routes, the declared responses of 5.3 ("Declared responses": 200 with the model; 404, 422 and 503 with `Problem`; any 501 declaration Phase 1 made stays), so that M2.12 changes no OpenAPI output.
3. `contracts/wording/real-data-v2.txt`, verbatim from 5.3, and the meta endpoint serving it as `Disclaimers.real_data` (`real-data-v1.txt` stays). `contracts/wording/forbidden-terms.txt`: the Phase 2 patterns of 5.3 ("Wording-lint patterns"), appended under their comment line. `scripts/check_wording.py` also scans `graph/src/**/wording.py`.
4. `make contracts` regenerates `contracts/openapi/v1.json`; `npm run --prefix ui gen:api` regenerates `ui/src/api/schema.d.ts`; the UI still type-checks.
5. `contracts/C3-api.md`: "Changes in 1.1.0" (new route, new fields, declared responses, notice v2, lint patterns); `versions.py`: `API = "1.1.0"`; `contracts/CHANGELOG.md` lines for C3.
6. Tests: `api/tests/test_routes.py`: the new route exists and returns a 501 problem; the three routes declare 200, 404, 422 and 503 in the app's OpenAPI document; the meta endpoint returns the v2 notice. `contracts/tests/test_wording.py` as in 5.4.

**Acceptance.**

```bash
make contracts && git diff --exit-code contracts/openapi/v1.json
npm run --prefix ui gen:api && git diff --exit-code ui/src/api/schema.d.ts
npm run --prefix ui type-check
uv run pytest -m contract contracts/tests/test_wording.py -q
uv run pytest api/tests/test_routes.py api/tests/test_openapi_contract.py -q
python3 scripts/check_wording.py
make contracts-check && make check
```

After this pull request merges, the tech lead tags `contracts-v1.1.0` (5.0, step 6).

**Review focus (humans).** UI squad: does `ResolutionResponse` give the explain panel everything it needs to say why two records were merged, and why a possible match was not? Copilot squad: can an answer about "who owns X" carry the effective share range and its "more than" lower bound? Data steward: is the v2 notice what you want every real-data view to show?

### M2.2 Data manager and profiles

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews the profiles, the gate, the purge and ADR-0013) |
| Depends on | M2.0 |
| Branch | `p2/m2-2-data-manager` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `size-exception` |
| Plan first | Yes |
| Size | exception (the three profiles are verbatim from 7.8, and the gate, the layout and the purge must land together with their tests) |
| ADR | ADR-0013 (data profiles and production sources) |
| Real-data run | none (the first real downloads happen in the loader milestones) |

**Goal.** One place decides which data a profile loads, whether it may run on this machine, where it goes, how long it stays and how it is deleted; every loader plugs into it instead of inventing its own folders or checks.

**Deliverables.**

1. `ingest/src/neonradar_ingest/data/project.py`: `load_project() -> Project`, a pydantic model of the `project.yaml` keys Phase 2 reads (1.3; other keys are allowed and ignored), from `docs/build/project.yaml`, or from the file named in `NR_PROJECT_FILE` when that variable is set. `NR_PROJECT_FILE` exists for tests and acceptance commands only; every summary records the project file's path relative to the repository and its SHA-256, so a reviewer sees which one a run used.
2. `ingest/src/neonradar_ingest/data/profiles.py`: a pydantic model `Profile` (with `extra="forbid"`) for the files in `ingest/profiles/`, and `load_profile(name) -> Profile`. Fields: `profile`, `description`, `real_data: bool`, `sources: dict[str, SourceConfig]` (one entry per dataset slug; unknown slugs fail), `resolution: {enabled: bool, config: str}` (M2.10a and M2.13 read them). Each `SourceConfig` has `enabled: bool` plus the source-specific block that its loader milestone defines (validated by a model the loader registers; until then the block is kept as a dict). `Profile.enabled_sources(project)` returns the datasets that are enabled in the profile and allowed by `project.yaml` (`access.sanctions_lists`, `access.pep_sources`, `access.opensanctions`); `access.companies_house_key` gates only the officers step (M2.3c), because the bulk products need no key. `Profile.record_dirs()` returns the folders the resolver and the loader read: `records_dir(profile, dataset)` for every enabled dataset, and for `nr_synthetic` the fixture folders listed in the profile.
3. `ingest/profiles/demo.yaml`, `uk-tiny.yaml` and `uk-sample.yaml`, verbatim from 7.8. The demo profile lists only `data/fixtures/demo-mini`; M2.9 adds `data/fixtures/er-bench` when the benchmark exists. The data steward approves the slices in review. The two `uk-tiny` seeds are real company numbers, which 7.4 rule 4 allows in this file, so committing the profile is not a stop-and-ask case (2.5 item 3); never add a company name next to them.
4. `ingest/src/neonradar_ingest/data/layout.py` (`neonradar_ingest.data.layout`): every path in 4.5 as functions, real or synthetic chosen from the profile: every function 4.5 names (`sources_dir(dataset, product, version)`, `records_dir(profile, dataset)`, `resolution_dir(profile, run_id)`, `latest_run(profile) -> str | None` (the id in `resolution/<profile>/LATEST`), `labels_dir(profile, run_id)` (`labels/<profile>/<run_id>/`), `decisions_file(profile)`, `duckdb_tmp_dir(profile, run_id)`, `logs_dir()`, `work_dir(profile, dataset)`, `reports_dir(profile)`, the two API cache folders `officer_cache_dir()` and `parliament_cache_dir()`, and `bench_dir(size)` for `data/cache/synthetic/er-bench-<size>/`). `resolution_dir`, `latest_run`, `labels_dir`, `duckdb_tmp_dir` and `decisions_file` also accept the synthetic pseudo-profiles `er-bench-small` and `er-bench-large` (M2.10a, M2.10b). A synthetic profile never gets a path under `data/cache/real/` (tested for every function). No other module builds these paths by hand.
5. `ingest/src/neonradar_ingest/data/gate.py`: `check_real_data(project, profile, dataset=None)` raises `RealDataRefused(rule, message)` and the CLI exits with code 3 and the message. For a profile with `real_data: true` it checks, in this order and before any network request or file write (with `dataset=None`, for commands that are not about one dataset such as `er`, `graph`, `load` and `bench queries`, condition 1 is skipped):
   1. the dataset is allowed by its access rule (`access.sanctions_lists`, `access.pep_sources`, `access.opensanctions` `licensed` or `exempt`, `access.companies_house_key` for the officers API), with that rule's message, for example "us_ofac_sdn is not in access.sanctions_lists";
   2. the profile is in `access.real_data_profiles`;
   3. `access.data_protection_filed` is true (1.1: the data steward has filed the controller documents);
   4. neither `CI` nor `CODESPACES` is set;
   5. `NR_REAL_DATA_MACHINE=approved` is set in the environment or in the repository's `.env` (read like PHASE-1.md M1.4's settings, where a real environment variable wins; a human sets it after the data steward lists the machine). `CI` and `CODESPACES` come from the environment only.
   Every command and builder step that reads real downloads or real records, or calls a real API, runs the gate first: `data fetch` and `ingest build` here, the officers step (M2.3c), the Parliament fetch (M2.6e), `er run` and the `er` labelling commands on a real profile (M2.10), and every command that addresses the real-data instance (`graph` commands with `--real`, M2.11; `api serve --real`, M2.12; `bench queries --real`, M2.13). A command that addresses the real instance without a profile runs conditions 3 to 5 and refuses while `access.real_data_profiles` is empty.
6. `ingest/src/neonradar_ingest/data/sources.py`: the plug-in interface each loader implements:
   - `RemoteFile(name, url, version, size: int | None, sha256: str | None, product: str = "main")`; products are `companies` (monthly Free Company Data) and `psc` (daily snapshot) for `gb_companies_house`, `golden-copy` for `gleif_lei`, and `main` for every other dataset;
   - `SourceSpec(dataset, discover)`, where `discover(client) -> list[RemoteFile]` finds the files of the current version of each product (a loader milestone writes it from section 3.3);
   - `Builder(dataset, build, steps=(), string_keys=(), list_keys=())`, where `build(profile, context: BuildContext) -> BuildResult` turns downloaded files into C1 records and manifests; `BuildContext` carries the project, the layout, the run id, the selected `steps` (empty means all, in the builder's order), `keep_work` and `accept_size`; `BuildResult` holds counts, plus short strings and lists of short strings under the builder's `string_keys` and `list_keys`, which `ingest build` passes to `emit` (deliverable 9; for example `slice_sha256` in M2.3a, `totals_check` and `snapshot_date` in M2.3b, `lei_headers` and `rr_headers` in M2.4, `list_generated` in M2.6);
   - a registry (`register_source`, `register_builder`) that the loader modules fill at import time.
7. `ingest/src/neonradar_ingest/data/download.py`: `fetch(spec, client)` downloads each file to `<name>.part` in `sources_dir(dataset, product, version)`, resumes with an HTTP `Range` request when a partial file exists and the server sent `Accept-Ranges: bytes` (a reply other than 206 restarts the file), renames on success, checks size and SHA-256 when the spec gives them, and writes `download.json` in the version folder: `{"files": [{name, url, version, product, size, sha256 (computed), etag, last_modified, downloaded_at, duration_s}]}`. URLs are stored without their query string (the EU download token, 3.3), here, in manifests and in summaries. It skips a file whose version is already complete. It checks free disk space before each file (twice the expected size plus 2 GB, or 2 GB when the size is unknown) and stops with a clear message otherwise. It uses the shared HTTP client from Phase 1 (`neonradar_ingest.http`: timeouts, explicit redirects, retries, rate limiter, User-Agent). It keeps the two newest complete versions per dataset and product and deletes older ones after a successful download, so a daily PSC download never removes the monthly companies files.
8. `ingest/src/neonradar_ingest/data/retention.py` and `purge.py`: `expired(project)` lists files under `data/cache/real/` older than `access.real_data_days`, label files older than `access.label_days`, files under `data/cache/spikes/` older than Phase 1's `access.spike_cache_days`, and leftover `duckdb-tmp/<run_id>/` folders (under `real/` and `synthetic/`) of runs that have finished: DuckDB spill files hold record values, so a crashed run must not leave them behind. `purge(...)` deletes by scope and returns counts of files and bytes:

   | Option | Deletes |
   |---|---|
   | `--expired` | everything `expired(project)` lists |
   | `--dataset <slug>` | that dataset's downloads, and its work and record folders in every real profile; for `gb_companies_house` also `officer_cache_dir()`, for `gb_parliament_members` also `parliament_cache_dir()` |
   | `--profile <name>` | the profile's record, work and resolution folders and `labels/<profile>/` (downloads stay: profiles share them) |
   | `--labels` | every label file under `data/cache/real/labels/` |
   | `--decisions` | `data/cache/real/decisions.jsonl` |
   | `--logs` | `data/cache/real/logs/` |
   | `--all-real` | everything under `data/cache/real/` and `data/cache/spikes/` |
   | `--graph` (with any option above, or alone) | the real-data Neo4j instance: the CLI stops and removes the `neo4j-real` container and deletes its `neo4j-real-data` volume (found by its Compose labels), so store files and transaction logs go too; the default instance is untouched (C2 L17) |

   `purge.py` deletes files only; the `--graph` step lives in the CLI (`cli/src/neonradar_cli/real_graph.py`), so `ingest` does not depend on `graph` (4.2).
9. `cli/src/neonradar_cli/summary.py`: `emit(profile, command, summary: dict, *, string_keys=(), list_keys=())` prints the summary and writes it to `reports_dir(profile)/<command>-<UTC yyyymmddThhmmss>.json`, where `<command>` is the command path joined with hyphens (`data-fetch`, `ingest-build`, `er-run`). It refuses (raises) any value that is not one of:
   - a number, a boolean or null;
   - a short string (at most 80 characters, matching `^[A-Za-z0-9 ._:/+()#,'&-]*$`) under a key in the common allow-list (`version`, `versions`, `product`, `run_id`, `dataset`, `datasets`, `profile`, `step`, `steps`, `file`, `files`, `status`, `rule`, `project_file`, `project_sha256`, `resolver_version`, `config_sha256`, keys starting with `threshold`, `started_at`, `finished_at`) or in the command's `string_keys`;
   - a list of such short strings under `headers` (file column names) or a key in the command's `list_keys`;
   - a nested dict of the above.
   Dict keys follow the same rule, with one exception for vocabularies: under a key ending in `_by_value`, keys may be enumeration values matching `^[a-z0-9][a-z0-9 ._#:/()&,'-]{0,79}$` (kinds, link types, `natures_of_control` values, ISO codes; loaders lower-case vocabulary values before reporting them), and the emitter folds every key whose count is below 10 into `<key>_rare` (a count), so a value that occurs once can never appear. A command that must report free text about the machine (M2.13's hardware line) strips other characters first. Every Phase 2 command that touches a real profile uses `emit`.
10. `cli/src/neonradar_cli/redact.py`: `guard(profile, command)`, a context manager that every CLI command enters with its profile. On a real profile an exception inside it prints only the exception class, the step, the dataset, the rule id (when the exception carries one) and a run-local reference such as `err-3`; the full traceback goes to `logs_dir()/<command>-<UTC timestamp>.log` (under `data/cache/real/`, purged with real data), and the exit code is the one the exception carries (its `exit_code`: 2 for a refusal such as L17, a pending migration or a missing step input, 3 for a gate refusal, 4 for a size or comparison cap), else 1. Counts-only messages, such as those of `common.check_bounds`, are printed in full. Messages never contain a record value or a record id of a person. On a synthetic profile it changes nothing.
11. CLI group `neonradar data`:
    - `data profiles`: the profiles, whether each may run on this machine (each gate condition shown as yes or no) and the datasets each enables.
    - `data fetch --profile <name> [--dataset <slug>]`: runs the gate, then `discover` and `fetch` for every enabled source with a `SourceSpec`.
    - `data status [--profile <name>]`: per dataset and product the versions present, sizes, ages and whether they are past retention; per profile the record folders, resolution runs, label files and leftover DuckDB temporary folders present (counts only).
    - `data purge (--expired | --dataset <slug> | --profile <name> | --labels | --decisions | --logs | --all-real) [--graph] --yes`, or `data purge --graph --yes` alone: refuses without `--yes`; prints what it deleted (counts and bytes).
12. CLI group `neonradar ingest`: `ingest build --profile <name> [--dataset <slug>] [--step <name>]... [--keep-work] [--accept-size]` runs the gate for a real profile, then the registered builders in a fixed order: `nr_synthetic` first (it validates each fixture folder the profile lists, in strict mode, and copies nothing), then `gb_companies_house` (GLEIF's slice depends on its company set), `gleif_lei`, `icij_offshore_leaks`, the four lists, `gb_parliament_members`, `opensanctions_default`. `--step` may be given several times and selects steps of a builder that has them (M2.3a defines the Companies House steps); `--keep-work` keeps a builder's work indexes; `--accept-size` lets a list builder accept a file outside its size bounds (M2.6a). Each dataset is written to a temporary folder next to `records_dir(profile, dataset)`, validated with the C1 validator in strict mode, and only then swapped for the old folder, so a rebuild never leaves stale files and a failed build leaves the previous records in place. The command emits the summary. A builder that is not implemented yet prints "not available until M2.x" and is skipped.
13. Human-only command guard: `neonradar_cli.tty.require_terminal(command)` raises a clear error when `sys.stdin.isatty()` is false. M2.10c uses it for `er label` and `er review`, and M2.12 for `api serve --real`.
14. Tests (all synthetic, network mocked with `httpx.MockTransport`, temporary trees for every path):
    - profile loading and validation errors; `enabled_sources` against a test project file in `NR_PROJECT_FILE`; every layout function for a synthetic profile stays outside `data/cache/real/`;
    - the gate (`ingest/tests/test_data_gate.py`): for each of the five conditions, a project file and environment where only that condition fails gives exit 3, its own message, and no request on the mock transport; the order of the checks;
    - download, resume after a cut connection (206 and non-206 replies), checksum failure, skip when complete, disk-space refusal (monkeypatched `shutil.disk_usage`), query strings never written, rotation per product with two products of different cadences (three daily PSC versions never delete the one companies version);
    - purge by each option on a temporary tree, with `--graph`'s Docker calls mocked and the command list asserted; retention for `real_data_days`, `label_days` and `spike_cache_days`;
    - `emit`: refusing a record-like value, a long string, a list under an unregistered key and a `_by_value` key with upper-case letters; folding rare `_by_value` keys; registered lists accepted;
    - `redact.guard`: an exception whose message holds a fake person's name and record id prints neither, and the log file lands under the temporary real tree;
    - `ingest build` swap: a failed validation leaves the old record folder in place; a successful one leaves no stale file;
    - `require_terminal`.
15. `docs/data/profiles.md`: the three profiles, what each loads, the resource needs from 7.8, the gate, and how to add a profile (a pull request reviewed by the data steward).
16. `docs/decisions/0013-data-profiles-and-sources.md` (status `proposed`; deciders: data steward and tech lead): profiles instead of ad hoc commands; a bounded, neutral `uk-sample` slice instead of the whole register (the scale target and data minimisation), with the ICIJ part tied to the same postcode districts (`district-linked`, M2.5; `gb-linked` only by the data steward's decision recorded here); bulk files where they exist (Companies House companies and PSC, GLEIF Golden Copy, ICIJ CSV), the API only for officers; the real-data gate and the separate Neo4j instance for real data (C2 L17); the online Python loader instead of `neo4j-admin import` (decision 6 in 0.5); counts-only summaries.

**Acceptance.**

```bash
uv run neonradar data profiles                       # three profiles; uk-* shown as not allowed by default
uv run pytest ingest/tests/test_data_gate.py -q      # every refusal in order, no request made
uv run neonradar data fetch --profile uk-tiny; echo "exit=$?"   # exit=3 with the first failing rule
uv run neonradar data status
uv run neonradar ingest build --profile demo         # validates the demo-mini fixture, prints a summary
ls data/cache/reports/demo/                          # the summary file exists
uv run pytest ingest/tests/test_data_*.py cli/tests/test_summary.py cli/tests/test_redact.py cli/tests/test_tty.py -q
make check && make hygiene LABELS=size-exception
```

**Review focus (humans).** Data steward: are the default slices in 7.8 neutral, and would you be comfortable explaining them to a person whose company is in one? Does `purge --all-real --graph` leave nothing real behind on a machine (downloads, records, runs, labels, decisions, logs, DuckDB spill files and the real Neo4j volume)? Is the order of the gate checks what you want people to see first? Ingest mentor: could a loader author write a new source against `SourceSpec` and `Builder` without asking?

### M2.3 Companies House (three sub-milestones)

The production loader for `gb_companies_house` replaces the Phase 1 spike. It reads the two bulk products (companies, PSCs), builds a bounded slice of the register, and fetches officers for that slice through the API within a request budget. Read `docs/research/2026-10-18/bulk-sources-loading.md` sections 2 to 5 first. The three pull requests run one after the other, because they share the module `ingest/src/neonradar_ingest/sources/companies_house/`.

**Build steps** (`neonradar ingest build --profile <p> --dataset gb_companies_house [--step <name>]...`; without `--step` every step whose milestone has merged runs, in this order; each step reads the previous steps' work files in `work_dir(profile, dataset)`, 4.5):

| Step | Milestone | Reads | Writes |
|---|---|---|---|
| `index` | M2.3a | the Free Company Data parts (product `companies`) | `companies.sqlite`: every live company's number, name, postcode district, category, status and country of origin |
| `psc-index` | M2.3b | the PSC snapshot (product `psc`, pass 1) | `corporate_pscs.sqlite`: table `corporate_psc` (every corporate and legal-person PSC with its company, outcome and normalised number) and table `statement` (`company_number`, `value`: every statement value without `ceased_on`, super-secure kind and exemption key) |
| `slice` | M2.3a (base), M2.3b (expansion) | the two indexes, the profile | `slice.csv`: `company_number,reason,level`, sorted by reason (`seed`, `parent`, `child`, `district`), then level, then sample hash, then number |
| `companies` | M2.3a | the Free Company Data parts (pass 2) and the `statement` table | `Company` (with `nr.psc_statements`) and `Address` records for the slice |
| `psc` | M2.3b | the PSC snapshot (pass 2) | PSC records, `Ownership` and `Control` |
| `officers` | M2.3c | the officers API, within the budget, in `slice.csv` order | officer records and `Directorship` |

The two products rotate separately (M2.2 keeps the two newest complete versions per dataset and product under `sources/gb_companies_house/<product>/<version>/`), so a daily PSC download never removes the monthly companies parts. Work files hold real data: they live under `data/cache/real/work/<profile>/gb_companies_house/` and are covered by `data purge`. After a successful build the two indexes are deleted unless `--keep-work` is given; `slice.csv` stays until the next `slice` step replaces it, because the `officers` step (M2.3c) and the `gleif_lei` builder (M2.4) read it in later runs. A step whose required input is missing stops and names the step to run first (exit 2); the `companies` step treats a missing `corporate_pscs.sqlite` as no statements and reports `statements: absent` in the summary.

#### M2.3a Free Company Data Product and the company slice

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews the slice) |
| Depends on | M2.1a, M2.2, M2.8 |
| Branch | `p2/m2-3a-ch-companies` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | Yes |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset gb_companies_house && uv run neonradar ingest build --profile uk-tiny --dataset gb_companies_house --step index --step slice --step companies` |

**Goal.** Every live UK company is indexed once a month, and a profile's slice of them becomes C1 records with their registered offices.

**Deliverables.**

1. `companies_house/bulk.py`, the `SourceSpec` of `gb_companies_house` with its `companies` product: read `https://download.companieshouse.gov.uk/en_output.html`, find the links `BasicCompanyData-<yyyy-mm-dd>-part<N>_<M>.zip`, take the newest date for which all `M` parts are listed, and return one `RemoteFile` per part (product `companies`; version: that date; size and checksum unknown, so `download.py` records the SHA-256 it computes). The parts are about 70 MB each, so a cut download resumes part by part (note 2.1).
2. **Reading** each part: iterate `ZipFile.namelist()`, open the member with `io.TextIOWrapper(..., encoding="utf-8", errors="strict", newline="")` and `csv.reader`. A decoding error stops the build with the part name (a mis-encoded release happened in August 2023, note 2.3). Strip every header cell (14 of them start with a space, note 2.2) and map columns by name; a missing column from the table below stops the build with its name; extra columns are counted. Skip and count empty rows and rows whose field count differs from the header's (a 56-field row broke another project's run on 2 September 2026, note 2.4).
3. **Values.** Decode only complete HTML character references in names (`&#039;`, `&AMP;`, `&#x1F4A9;`: the pattern `&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});` through `html.unescape`), so `A&B LIMITED` stays as it is. Dates are `dd/mm/yyyy` (parse strictly; anything else is dropped and counted). `CompanyNumber` stays an 8-character string. An address field holding only punctuation, digits or a bare outward postcode counts as missing (note 2.4).
4. **`index` step**: one pass over all parts into `companies.sqlite` (standard library `sqlite3`; table `company(number TEXT PRIMARY KEY, name, district, category, status, origin)`), where `district` is the outward code of `RegAddress.PostCode` through `neonradar_keys.postcodes`. About 5.7 million rows (note 2.5).
5. **`slice` step** (`slice.py`, profile block `companies`): `seeds` are always in the slice (a seed missing from the index is reported, never guessed); for each district in `postcode_districts`, the companies whose `district` matches, ordered by their sample hash `sha256("<sample_seed>|<company number>")` (hex), the first `max_per_district`; then (M2.3b) the PSC expansion; finally the cap `max_companies`, which removes expansion companies first (deepest level first; within a level, the highest sample hash first), then district companies (highest hash first), never a seed. A company reached in two ways keeps the first reason in the order `seed`, `district`, `parent`, `child`, at its lowest level. `slice.csv` is written in the order the officers step uses (M2.3c): by reason (`seed`, `parent`, `child`, `district`), then level, then sample hash, then number. The summary reports the count per reason, per district and per level, how many the cap removed, and the SHA-256 of `slice.csv` (string key `slice_sha256`, registered on the builder, M2.2).
6. **`companies` step**: a second pass over the parts, writing records for the companies in `slice.csv` (ids per 4.4, prefix `gbch`):

   | Column | FtM | Rule |
   |---|---|---|
   | `CompanyName` | `name` | references decoded |
   | `CompanyNumber` | `registrationNumber` | as given; id `gbch-co-<number>`; `nr.source_ref` the number |
   | `CompanyCategory`, `CompanyStatus` | `legalForm`, `status` | raw strings (for example `Private Limited Company`, note 2.5) |
   | `CountryOfOrigin` | `jurisdiction` | `gb` for numbers without a prefix and for the UK prefixes; for `FC`, `SF`, `NF` and `OE` numbers, `country_code(CountryOfOrigin)`, counted when it does not map (these companies are incorporated abroad and registered in the UK; check the prefix meanings against the URI customer guide, note 2.6 source B16, and record them in the source document) |
   | `IncorporationDate`, `DissolutionDate` | `incorporationDate`, `dissolutionDate` | ISO dates (the live file has no dissolution dates, note 2.5) |
   | `Accounts.AccountCategory` | `nr.accounts_category` | raw |
   | `SICCode.SicText_1` to `_4` | `sector` | the code before the first " - " |
   | `PreviousName_1.CompanyName` to `_10` | `previousName` | |
   | `RegAddress.*` | `addressEntity` | an `Address` record (below), with `nr.address_roles: {"<address record id>": "registered"}` (C1's object from Address id to role, PHASE-1.md 5.1) |
   | the `statement` table (M2.3b) | `nr.psc_statements` | the company's values, sorted; absent before M2.3b merges or when the company has none |

   `sourceUrl` is `https://find-and-update.company-information.service.gov.uk/company/<number>`. The summary also reports `top10_address_share`: the share of slice companies whose registered office is one of the ten most common address keys in the slice (a number only, never a key). City-centre districts hold many formation-agent addresses, and this number shows the reviewer how much of the slice they are.
7. **Address records** (shared by all three sub-milestones): one `Address` per distinct `neonradar_keys.addresses.address_key_from_parts(parts)` in the dataset, id `gbch-addr-<first 20 hex of sha1 of the key>` (4.4), with `full` (the non-empty parts joined with ", " in the order given to `address_key_from_parts`, so that `address_key(full)` is the record's key, which the graph loader recomputes, C2 L15), `street`, `city`, `region`, `postalCode` (normalised) and `country` (`country_code`, else `gb`). A record whose address has no key gets no `addressEntity` (counted). Every record that links an address sets its role in `nr.address_roles` as an object from the address record id to the role.
8. Profile block model for `companies` (fields in 7.8; unknown keys fail). Until M2.3b and M2.3c register their models, the `gb_companies_house` block keeps its `psc` and `officers` sub-blocks as plain mappings, so the 7.8 profiles validate after every merge.
9. `docs/data/sources/gb_companies_house.md`: the products used and their cadence (monthly `companies`, daily `psc`), what is loaded, the slice rule, the prefixes treated as overseas companies, the personal-data note and the Companies House statement that reusers "become controllers" (note 10).
10. Tests (synthetic parts built in memory as zip files, in the style of M1.8c; invented names and numbers): the header with leading spaces; a missing column; a 56-field row; an empty row; a mis-encoded byte; HTML references and a literal ampersand; dates; `FC`, `SF`, `NF` and `OE` jurisdictions; the district sample is deterministic for a seed and independent of row order; seeds always kept; the cap order; the `slice.csv` order; `slice.csv` kept after a successful build and the indexes deleted (kept with `--keep-work`); address deduplication; `address_key(full)` equal to the key from the parts; `nr.address_roles` as an object; `nr.psc_statements` from a `statement` table built in the test; `top10_address_share`; records validate in strict mode.

**Acceptance.** `uv run pytest ingest/tests/test_ch_bulk.py ingest/tests/test_ch_slice.py -q`; `uv run neonradar ingest build --profile demo` still passes; `make check`.

**Real-data run (operator).** The command in the header; paste the summary (rows read and skipped, slice counts, records by schema, `top10_address_share`, the snapshot date).

**Review focus (humans).** Data steward: is the slice in the summary what the profile promises, and nothing more? Does `top10_address_share` show a slice dominated by a few formation-agent addresses? Ingest mentor: does a re-run with the same snapshot and seed give the same `slice.csv` (compare the SHA-256 in the summary)?

#### M2.3b PSC snapshot and the ownership slice

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward and graph mentor review) |
| Depends on | M2.3a |
| Branch | `p2/m2-3b-ch-psc` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run`, `size-exception` |
| Plan first | Yes |
| Size | exception (two modules and their tests are verbatim from this spec) |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset gb_companies_house && uv run neonradar ingest build --profile uk-tiny --dataset gb_companies_house` |

**Goal.** People with significant control become owners and controllers in the graph, with the statutory bands exactly as the law states them, and corporate PSCs that are UK companies pull their parent companies into the slice.

**Deliverables.**

1. `companies_house/psc.py`, the `psc` product of the `gb_companies_house` `SourceSpec`: read `https://download.companieshouse.gov.uk/en_pscdata.html`, take the parts `psc-snapshot-<yyyy-mm-dd>_<N>of<M>.zip` of the newest date with all `M` parts (33 on 17 October 2026, 2.2 GB in total, note 3.1), one `RemoteFile` per part with product `psc`. Files are replaced daily; M2.2 keeps the two newest complete versions of each product, so the monthly companies parts stay.
2. **Reading**: each member line by line as bytes, parsed with `orjson.loads` (add `orjson==3.13.*` to `ingest`; it parses about twice as fast as `json`, note 9.5). A line is `{"company_number": ..., "data": {...}}`. A line without `company_number` is a totals record (`data.kind` `totals#persons-of-significant-control-snapshot`): when one is present, the data lines read must equal the sum of its three counts, and the summary reports `totals_check` as `passed`, `failed` or `absent` (whether every part carries one is not known, note 3.2); `totals_check` and `snapshot_date` are string keys the builder registers (M2.2). Unknown kinds and unknown `natures_of_control` values are counted by value under `_by_value` keys (M2.2), never dropped silently (both are enumerations).
3. **Kinds** (note 3.3):

   | `data.kind` | Record | Properties |
   |---|---|---|
   | `individual-person-with-significant-control`, `individual-beneficial-owner` | `Person` | `name`; `firstName`, `middleName`, `lastName` from `name_elements` (`forename`, `middle_name`, `surname`; the title is not loaded); `birthDate` `yyyy-mm` from `date_of_birth` (month and year only, note 3.3); `nationality` from each comma-separated demonym through `country_code`; `country` from `country_of_residence`; `address` as an `Address` record with role `service` in `nr.address_roles` |
   | `corporate-entity-person-with-significant-control`, `corporate-entity-beneficial-owner` | `Company` | `name`; `legalForm` from `identification.legal_form`; `registrationNumber` and `jurisdiction` by rule 5; the address as an `Address` record with role `registered` |
   | `legal-person-person-with-significant-control`, `legal-person-with-significant-control`, `legal-person-beneficial-owner` | `Organization` | `name`, `legalForm`; `jurisdiction` by rule 5; the address as above |
   | `super-secure-person-with-significant-control`, `super-secure-beneficial-owner` | none | the kind goes to the `statement` table (the `companies` step puts it in the company's `nr.psc_statements`); counted |
   | `persons-with-significant-control-statement` | none | the `statement` value, unchanged, goes to the `statement` table unless `ceased_on` is set (including the source's spelling `no-individual-or-entity-with-signficant-control`, note 4.4) |
   | `exemptions` | none | each key under `exemptions` goes to the `statement` table |

   PSC record ids are `gbch-psc-<last path segment of data.links.self>`; `nr.source_ref` is that segment. A beneficial owner with `is_sanctioned: true` gets `topics: ["sanction"]` (the register of overseas entities states it, note 3.7; 7.2 words it as "recorded as sanctioned on the register of overseas entities at Companies House (as declared by the overseas entity; it may be out of date)"). PSCs with `ceased_on` are skipped and counted unless the profile sets `psc.include_ceased: true` (then their links get an `endDate`).
4. **Interests**, from `natures_of_control` through `natures.classify` and `natures.interests` (verbatim below; the band table is the statute's, note 4.2; the capacities follow the long descriptions in `psc_descriptions.yml`, note 4.3):
   - `interests` groups one PSC's values in one company by kind, measure, capacity and held right; each `Interest` becomes one record, whose id (4.4) hashes the PSC record id, the company number and `Interest.key` (`shares`, `voting`, `shares-as-trust`, `trust-or-firm-shares-trust` and so on), `role` and `nr.natures_of_control` its raw values, and its band from `natures.combined_band` in `nr.share_pct_min`, `nr.share_pct_max`, `nr.share_pct_min_exclusive` and `nr.share_pct_max_exclusive` when the values have one;
   - an ownership interest becomes `Ownership` (owner the PSC, asset the company), with `percentage` `Band.percentage` and `ownershipType` `Interest.type_label` (`shares`, `surplus assets`, or `shares (as trustee)` for an overseas entity's beneficial owner who is a trustee);
   - a control interest becomes `Control` (controller the PSC, controlled the company), with `controlType` `Interest.type_label` (`voting`, `appointment`, `influence`, `nominee`, `trust-or-firm`, or for an overseas entity's trustee for example `voting (as trustee)`). Voting rights keep their band on the `Control` (C1 1.1.0 allows the four share keys there; C2 maps them to `CONTROLS`), because OFSI's ownership and control test counts "more than 50% of the shares or voting rights" (`sanctions-peps.md` 2.8);
   - controlling a trust or firm is not owning what it holds. The long description of `ownership-of-shares-25-to-50-percent-as-trust` reads "The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the shares in the company" (`psc_descriptions.yml` at `05067ab`, note 4.1; the fifth condition of Companies Act 2006 Schedule 1A Part 1, which the graph mentor checks). So the `-as-trust` and `-as-firm` values of companies, LLPs and Scottish partnerships, and the `-as-firm`, `-as-control-over-trust` and `-as-control-over-firm` values of overseas entities, become `Control` of type `trust-or-firm`, keeping the band of what the trust or firm holds. Only an overseas entity's beneficial owner who "is a trustee of a trust" holds the right itself;
   - a direct holding and a trust's holding of one PSC are two records, never one band: their union would describe neither (tested). This deliberately replaces the Phase 1 spike's mapping (PHASE-1.md M1.8a), which made every share and surplus-asset value an `Ownership` and kept `-as-trust` and `-as-firm` only in `role`; the M2.0 reconciliation lists it as a decided change, not a question;
   - `notified_on` is `startDate` and `ceased_on` `endDate` on each.
5. **Corporate PSCs and the UK register** (`identification.py`, verbatim below; written from the rule in note 3.6, no code copied): when `is_uk(identification, address country)` is true, `registrationNumber` is `uk_number(...)` (rule D1's normalisation from `neonradar_keys.ids`, so only Companies House forms count) and `jurisdiction` is `gb`; otherwise `registrationNumber` is the raw value and `jurisdiction` is `country_code(country_registered)`. `resolve_corporate` gives the outcome (`resolved`, `name_mismatch`, `number_not_found`, `no_number`, `non_uk`), which the summary counts and the slice expansion uses; for `non_uk` the summary also counts the ISO codes of `country_registered` (`country_code`), with unmapped values counted, never shown. It does not decide merges: rule D1 applies its own name check (7.1.2).
6. **`psc-index` step**: the first pass writes `corporate_pscs.sqlite` (standard library `sqlite3`): table `corporate_psc(company_number, psc_id, outcome, number)` for every corporate and legal-person PSC, looking up names in `companies.sqlite`, and table `statement(company_number, value)` for every statement value without `ceased_on`, super-secure kind and exemption key of every company. The `companies` step (M2.3a) reads the slice companies' rows into `nr.psc_statements`, so no record file is written twice.
7. **Slice expansion** (profile block `psc`): from the slice companies, follow `resolved` corporate PSCs upwards for `parent_depth` levels (adding the parent companies, even outside the districts; reason `parent`, level 1 to `parent_depth`), and, for `child_depth` levels, add the companies whose `resolved` corporate PSC is already in the slice (reason `child`). Then the `max_companies` cap and the `slice.csv` order of M2.3a apply.
8. **`psc` step**: the second pass writes the records for slice companies; PSC lines of other companies are counted, not loaded.
9. Profile block model for `psc` (`enabled`, `parent_depth`, `child_depth`, `include_ceased`).
10. Tests (synthetic snapshot parts in memory, invented names and numbers): every kind in the table; a totals line that passes and one that fails; unknown kinds and natures counted; ceased PSCs skipped, and loaded with `include_ceased`; every band, including a PSC with two ownership values; a PSC with a direct holding and a trust's holding gives an `Ownership` and a `trust-or-firm` `Control`; a voting `Control` with its band; an overseas entity's trustee (`shares (as trustee)`); record ids from `Interest.key`; statements, super-secure kinds and exemptions in the `statement` table; `is_sanctioned`; the five outcomes; expansion two levels up and one down on a small known graph, and the cap; `natures.py` and `identification.py` with their tests verbatim (48 tests), and the fixture `natures_of_control.txt` (the 86 published values; they are enumeration values, not data about anyone).

**Acceptance.** `uv run pytest ingest/tests/test_ch_psc.py ingest/tests/test_ch_natures_identification.py -q` (the verbatim file: 48 passed); `make check`.

**Real-data run (operator).** The command in the header (the full `gb_companies_house` build without officers, or with them once M2.3c is merged); paste the summary (lines read, totals check, records by kind, outcomes, unknown values with counts, the expansion counts).

**Review focus (humans).** Graph mentor: read the band table in `natures.py` against the statute's words in note 4.2, and the capacity rule against the long descriptions: is a `trust-or-firm` control what an investigator should see for a person who controls a trust? Data steward: do you agree with skipping ceased PSCs by default? Ingest mentor: the outcome counts: is `name_mismatch` small, and are the most common `non_uk` country codes really foreign?

**`ingest/src/neonradar_ingest/sources/companies_house/natures.py`** (verbatim):

```python
"""Companies House `natures_of_control` values and the statutory share bands (PHASE-2.md M2.3b).

The bands follow the statute and the API's short descriptions, not its long ones
(bulk-sources-loading.md 4.2): "more than 25% but not more than 50%" is (25, 50],
"more than 50% but less than 75%" is (50, 75), "75% or more" is [75, 100], and the overseas
entity value "more than 25%" is (25, 100].

Capacities follow the long descriptions in psc_descriptions.yml (note 4.3). For companies, LLPs
and Scottish partnerships, `-as-trust` and `-as-firm` mean that the person has significant
influence or control over a trust or firm whose trustees or members hold the right (the fifth
condition of Companies Act 2006 Schedule 1A). For registered overseas entities, `-as-trust`
means the beneficial owner is a trustee, `-as-firm` a member of a firm whose members hold the
right, and `-as-control-over-trust` and `-as-control-over-firm` control over the trust or firm.
Controlling or belonging to a trust or firm is not owning what it holds, so those values are
control of measure `trust-or-firm`, keeping the band of what the trust or firm holds. Only an
overseas entity's trustee holds the right itself ("shares (as trustee)").
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Band:
    pct_min: float
    pct_max: float
    min_exclusive: bool
    max_exclusive: bool

    @property
    def percentage(self) -> str:
        """The FtM `percentage` text, for example "25-50"."""
        return f"{self.pct_min:g}-{self.pct_max:g}"


BANDS = {
    "25-to-50": Band(25, 50, min_exclusive=True, max_exclusive=False),
    "50-to-75": Band(50, 75, min_exclusive=True, max_exclusive=True),
    "75-to-100": Band(75, 100, min_exclusive=False, max_exclusive=False),
    "more-than-25": Band(25, 100, min_exclusive=True, max_exclusive=False),
}


@dataclass(frozen=True)
class Nature:
    value: str
    kind: str  # "ownership" or "control"
    measure: str  # shares, surplus-assets, voting, appointment, influence, nominee, trust-or-firm
    band: Band | None
    capacity: str | None  # trust, firm, control-over-trust, control-over-firm
    held: str | None  # trust-or-firm only: the right the trust or firm holds (shares, voting, ...)
    overseas: bool  # a registered overseas entity value


@dataclass(frozen=True)
class Interest:
    """One `Ownership` or `Control` record of one PSC in one company (M2.3b rule 4)."""

    kind: str
    measure: str
    capacity: str | None
    held: str | None
    band: Band | None
    values: tuple[str, ...]  # the raw natures, sorted

    @property
    def key(self) -> str:
        """The part of the record id that tells the interests of one PSC apart (PHASE-2.md 4.4):
        "shares", "voting", "shares-as-trust" (an overseas entity's trustee) or
        "trust-or-firm-shares-trust" (control over a trust whose trustees hold shares)."""
        if self.measure == "trust-or-firm":
            return f"trust-or-firm-{self.held}-{self.capacity}"
        if self.capacity:
            return f"{self.measure}-as-{self.capacity}"
        return self.measure

    @property
    def type_label(self) -> str:
        """`ownershipType` or `controlType`: "shares", "surplus assets", "shares (as trustee)",
        "voting", "appointment", "influence", "nominee" or "trust-or-firm"."""
        label = "surplus assets" if self.measure == "surplus-assets" else self.measure
        if self.measure != "trust-or-firm" and self.capacity == "trust":
            label += " (as trustee)"
        return label


_BAND = r"(?P<band>25-to-50|50-to-75|75-to-100|more-than-25)-percent"
_CAP = r"(?:-as-(?P<cap>trust|firm|control-over-trust|control-over-firm))?"
_SUFFIX = r"(?:-limited-liability-partnership|(?P<oe>-registered-overseas-entity))?"
_PATTERNS = [
    ("ownership", "shares", re.compile(rf"ownership-of-shares-{_BAND}{_CAP}{_SUFFIX}")),
    (
        "ownership",
        "surplus-assets",
        re.compile(rf"(?:part-)?right-to-share-surplus-assets-{_BAND}{_CAP}{_SUFFIX}"),
    ),
    ("control", "voting", re.compile(rf"voting-rights-{_BAND}{_CAP}{_SUFFIX}")),
    (
        "control",
        "appointment",
        re.compile(rf"right-to-appoint-and-remove-(?:directors|members|person){_CAP}{_SUFFIX}"),
    ),
    ("control", "influence", re.compile(rf"significant-influence-or-control{_CAP}{_SUFFIX}")),
    (
        "control",
        "nominee",
        re.compile(
            r"registered-owner-as-nominee-(?:person|another-entity)"
            r"-(?:england-wales|scotland|northern-ireland)(?P<oe>-registered-overseas-entity)"
        ),
    ),
]


def classify(value: str) -> Nature | None:
    """The nature of one value, or None for a value this table does not know (count it)."""
    for kind, measure, pattern in _PATTERNS:
        match = pattern.fullmatch(value)
        if match is None:
            continue
        groups = match.groupdict()
        band = BANDS[groups["band"]] if groups.get("band") else None
        capacity = groups.get("cap")
        overseas = bool(groups.get("oe"))
        if capacity is None or (overseas and capacity == "trust"):
            return Nature(value, kind, measure, band, capacity, None, overseas)
        return Nature(value, "control", "trust-or-firm", band, capacity, measure, overseas)
    return None


def combined_band(bands: Iterable[Band]) -> Band | None:
    """One band for several values of one interest: the lowest minimum and the highest maximum.

    Where two bands share a bound, the bound is closed if either is closed. Combine only the
    values of one interest (`interests` groups them): a direct holding and a trust's holding
    are different facts, and their union would describe neither.
    """
    items = list(bands)
    if not items:
        return None
    low = min(b.pct_min for b in items)
    high = max(b.pct_max for b in items)
    min_open = all(b.min_exclusive for b in items if b.pct_min == low)
    max_open = all(b.max_exclusive for b in items if b.pct_max == high)
    return Band(low, high, min_exclusive=min_open, max_exclusive=max_open)


def interests(natures: Iterable[Nature]) -> list[Interest]:
    """The interests of one PSC in one company: one per kind, measure, capacity and held right,
    each with the combined band of its values, sorted by kind and key."""
    groups: dict[tuple[str, str, str, str], list[Nature]] = {}
    for nature in natures:
        group = (nature.kind, nature.measure, nature.capacity or "", nature.held or "")
        groups.setdefault(group, []).append(nature)
    found = [
        Interest(
            kind,
            measure,
            capacity or None,
            held or None,
            combined_band(n.band for n in items if n.band is not None),
            tuple(sorted({n.value for n in items})),
        )
        for (kind, measure, capacity, held), items in groups.items()
    ]
    return sorted(found, key=lambda i: (i.kind, i.key))
```

**`ingest/src/neonradar_ingest/sources/companies_house/identification.py`** (verbatim):

```python
"""Is a corporate PSC or corporate officer registered at Companies House? (PHASE-2.md M2.3b)

Written for NeonRadar from the rule described in bulk-sources-loading.md 3.6; no code was
copied from another project. The registry fields are free text and "isn't guaranteed to be
correct", so a number found here is evidence for rule D1, which still needs the name check.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from neonradar_keys.ids import uk_company_number
from neonradar_keys.names import name_similarity, org_key

UK_TOKENS = frozenset(
    {
        "united kingdom",
        "uk",
        "u.k.",
        "great britain",
        "gb",
        "england",
        "wales",
        "england and wales",
        "england & wales",
        "scotland",
        "northern ireland",
        "companies house",
        "uk companies house",
        "register of companies",
        "registrar of companies",
        "uk register of companies",
    }
)
UK_STARTS = (
    "companies house",
    "united kingdom (",
    "england and wales ",
    "england & wales ",
    "uk companies house",
    "uk register of companies",
)

Outcome = Literal["resolved", "name_mismatch", "number_not_found", "no_number", "non_uk"]


def _norm(text: str | None) -> str:
    return " ".join((text or "").strip().lower().split())


def _uk_like(value: str) -> bool:
    return value in UK_TOKENS or value.startswith(UK_STARTS)


def is_uk(identification: Mapping[str, str | None], address_country: str | None = None) -> bool:
    """True when the registry fields say Companies House.

    An explicit `country_registered` decides on its own. Without it, `place_registered` or
    `legal_authority` decides; with none of the three, the address country does.
    """
    country = _norm(identification.get("country_registered"))
    if country:
        return _uk_like(country)
    place = _norm(identification.get("place_registered"))
    authority = _norm(identification.get("legal_authority"))
    if place or authority:
        return _uk_like(place) or _uk_like(authority)
    return _uk_like(_norm(address_country))


def uk_number(raw: str | None) -> str | None:
    """A Companies House number in its 8-character form, or None: rule D1's normalisation
    (`neonradar_keys.ids.uk_company_number`), so a prefix Companies House does not use, or a
    value such as "N/A", gives None."""
    return uk_company_number(raw)


def names_agree(a: str, b: str, threshold: float = 0.85) -> bool:
    """The loader's name check for slice expansion: equal organisation keys, or Jaro-Winkler at
    least the threshold on them (the resolver applies its own check for D1)."""
    key_a, key_b = org_key(a).key, org_key(b).key
    return bool(key_a) and (key_a == key_b or name_similarity(key_a, key_b) >= threshold)


def resolve_corporate(
    name: str,
    identification: Mapping[str, str | None],
    address_country: str | None,
    company_names: Mapping[str, str],
) -> tuple[Outcome, str | None]:
    """Outcome and normalised number for one corporate PSC or officer.

    `company_names` maps company numbers in the Free Company Data index to company names.
    """
    if not is_uk(identification, address_country):
        return "non_uk", None
    number = uk_number(identification.get("registration_number"))
    if number is None:
        return "no_number", None
    known = company_names.get(number)
    if known is None:
        return "number_not_found", number
    if not names_agree(name, known):
        return "name_mismatch", number
    return "resolved", number
```

**`ingest/tests/test_ch_natures_identification.py`** (verbatim):

```python
"""Tests for the Companies House natures table and the corporate PSC rule (PHASE-2.md M2.3b)."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

import pytest

from neonradar_ingest.sources.companies_house.identification import (
    is_uk,
    names_agree,
    resolve_corporate,
    uk_number,
)
from neonradar_ingest.sources.companies_house.natures import (
    BANDS,
    Band,
    Nature,
    classify,
    combined_band,
    interests,
)

FIXTURE = Path(__file__).parent / "fixtures" / "natures_of_control.txt"


def all_values() -> list[str]:
    lines = FIXTURE.read_text(encoding="utf-8").splitlines()
    return [line for line in lines if line and not line.startswith("#")]


def test_every_published_value_is_classified() -> None:
    values = all_values()
    assert len(values) == 86
    natures = {v: classify(v) for v in values}
    assert [v for v, n in natures.items() if n is None] == []
    by_family = Counter(
        "llp"
        if v.endswith("-limited-liability-partnership")
        else "overseas"
        if v.endswith("-registered-overseas-entity")
        else "scottish-partnership"
        if v.startswith("part-") or v.startswith("right-to-appoint-and-remove-person")
        else "company"
        for v in values
    )
    assert by_family == {"company": 24, "llp": 24, "scottish-partnership": 12, "overseas": 26}
    by_measure = Counter((n.kind, n.measure) for n in natures.values() if n is not None)
    assert by_measure == {
        ("ownership", "shares"): 5,
        ("ownership", "surplus-assets"): 6,
        ("control", "voting"): 8,
        ("control", "appointment"): 5,
        ("control", "influence"): 4,
        ("control", "nominee"): 6,
        ("control", "trust-or-firm"): 52,
    }


def test_statutory_bands() -> None:
    assert BANDS["25-to-50"] == Band(25, 50, min_exclusive=True, max_exclusive=False)
    assert BANDS["50-to-75"] == Band(50, 75, min_exclusive=True, max_exclusive=True)
    assert BANDS["75-to-100"] == Band(75, 100, min_exclusive=False, max_exclusive=False)
    assert BANDS["more-than-25"] == Band(25, 100, min_exclusive=True, max_exclusive=False)
    assert BANDS["25-to-50"].percentage == "25-50"


@pytest.mark.parametrize(
    ("value", "kind", "measure", "band", "capacity", "held"),
    [
        ("ownership-of-shares-75-to-100-percent", "ownership", "shares", "75-to-100", None, None),
        # control over a trust whose trustees hold the shares: not ownership of the shares
        (
            "ownership-of-shares-25-to-50-percent-as-trust",
            "control",
            "trust-or-firm",
            "25-to-50",
            "trust",
            "shares",
        ),
        (
            "right-to-share-surplus-assets-50-to-75-percent-as-firm-limited-liability-partnership",
            "control",
            "trust-or-firm",
            "50-to-75",
            "firm",
            "surplus-assets",
        ),
        (
            "part-right-to-share-surplus-assets-25-to-50-percent",
            "ownership",
            "surplus-assets",
            "25-to-50",
            None,
            None,
        ),
        # an overseas entity's beneficial owner who is a trustee holds the shares as trustee
        (
            "ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity",
            "ownership",
            "shares",
            "more-than-25",
            "trust",
            None,
        ),
        (
            "ownership-of-shares-more-than-25-percent-as-firm-registered-overseas-entity",
            "control",
            "trust-or-firm",
            "more-than-25",
            "firm",
            "shares",
        ),
        (
            "ownership-of-shares-more-than-25-percent-as-control-over-trust-registered-overseas-entity",
            "control",
            "trust-or-firm",
            "more-than-25",
            "control-over-trust",
            "shares",
        ),
        ("voting-rights-50-to-75-percent", "control", "voting", "50-to-75", None, None),
        (
            "voting-rights-more-than-25-percent-as-trust-registered-overseas-entity",
            "control",
            "voting",
            "more-than-25",
            "trust",
            None,
        ),
        ("right-to-appoint-and-remove-directors", "control", "appointment", None, None, None),
        (
            "right-to-appoint-and-remove-person-as-firm",
            "control",
            "trust-or-firm",
            None,
            "firm",
            "appointment",
        ),
        (
            "significant-influence-or-control-as-trust",
            "control",
            "trust-or-firm",
            None,
            "trust",
            "influence",
        ),
        (
            "registered-owner-as-nominee-another-entity-scotland-registered-overseas-entity",
            "control",
            "nominee",
            None,
            None,
            None,
        ),
    ],
)
def test_classify(
    value: str,
    kind: str,
    measure: str,
    band: str | None,
    capacity: str | None,
    held: str | None,
) -> None:
    nature = classify(value)
    assert nature is not None
    assert (nature.kind, nature.measure, nature.capacity, nature.held) == (
        kind,
        measure,
        capacity,
        held,
    )
    assert nature.band == (BANDS[band] if band else None)
    assert nature.overseas is value.endswith("-registered-overseas-entity")


def test_unknown_values() -> None:
    assert classify("ownership-of-shares-10-to-25-percent") is None
    assert classify("OWNERSHIP-OF-SHARES-25-TO-50-PERCENT") is None
    assert classify("") is None


def test_combined_band() -> None:
    low, high = BANDS["25-to-50"], BANDS["75-to-100"]
    assert combined_band([low, high]) == Band(25, 100, min_exclusive=True, max_exclusive=False)
    assert combined_band([BANDS["50-to-75"]]) == BANDS["50-to-75"]
    closed = Band(50, 75, min_exclusive=False, max_exclusive=True)
    assert combined_band([BANDS["50-to-75"], closed]).min_exclusive is False  # type: ignore[union-attr]
    assert combined_band([]) is None


def natures_of(*values: str) -> list[Nature]:
    found = [n for n in (classify(v) for v in values) if n is not None]
    assert len(found) == len(values)
    return found


def test_interests_keep_direct_and_trust_holdings_apart() -> None:
    # One PSC: shares held directly, and control over a trust that holds more shares. These are
    # two facts, so two records, never one band of (25, 75).
    found = interests(
        natures_of(
            "ownership-of-shares-25-to-50-percent",
            "ownership-of-shares-50-to-75-percent-as-trust",
            "voting-rights-25-to-50-percent",
            "right-to-appoint-and-remove-directors",
        )
    )
    assert [(i.kind, i.key, i.type_label) for i in found] == [
        ("control", "appointment", "appointment"),
        ("control", "trust-or-firm-shares-trust", "trust-or-firm"),
        ("control", "voting", "voting"),
        ("ownership", "shares", "shares"),
    ]
    bands = {i.key: i.band for i in found}
    assert bands["shares"] == BANDS["25-to-50"]
    assert bands["trust-or-firm-shares-trust"] == BANDS["50-to-75"]
    assert bands["voting"] == BANDS["25-to-50"]  # voting control keeps its band
    assert bands["appointment"] is None


def test_interests_combine_values_of_one_interest_only() -> None:
    found = interests(
        natures_of(
            "ownership-of-shares-25-to-50-percent",
            "ownership-of-shares-75-to-100-percent",
            "ownership-of-shares-25-to-50-percent-as-trust",
            "voting-rights-25-to-50-percent-as-trust",
        )
    )
    assert {i.key: i.band for i in found} == {
        "shares": Band(25, 100, min_exclusive=True, max_exclusive=False),
        "trust-or-firm-shares-trust": BANDS["25-to-50"],
        "trust-or-firm-voting-trust": BANDS["25-to-50"],
    }
    assert [i.values for i in found if i.key == "shares"] == [
        ("ownership-of-shares-25-to-50-percent", "ownership-of-shares-75-to-100-percent")
    ]


def test_overseas_entity_trustee_interests() -> None:
    found = interests(
        natures_of(
            "ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity",
            "voting-rights-more-than-25-percent-as-trust-registered-overseas-entity",
            "ownership-of-shares-more-than-25-percent-as-control-over-firm-registered-overseas-entity",
        )
    )
    assert [(i.kind, i.key, i.type_label) for i in found] == [
        ("control", "trust-or-firm-shares-control-over-firm", "trust-or-firm"),
        ("control", "voting-as-trust", "voting (as trustee)"),
        ("ownership", "shares-as-trust", "shares (as trustee)"),
    ]
    assert all(i.band == BANDS["more-than-25"] for i in found)


@pytest.mark.parametrize(
    ("identification", "address_country", "expected"),
    [
        ({"country_registered": "England", "place_registered": "Companies House"}, None, True),
        ({"country_registered": "England And Wales"}, None, True),
        ({"country_registered": "Uk"}, None, True),
        ({"country_registered": "England & Wales Companies Register"}, None, True),
        ({"country_registered": "Jersey", "place_registered": "Companies House"}, None, False),
        ({"country_registered": "United States", "place_registered": "Delaware"}, None, False),
        ({"place_registered": "Companies House Cardiff"}, None, True),
        ({"legal_authority": "United Kingdom (England And Wales)"}, None, True),
        ({"legal_authority": "Companies Act 2006"}, None, False),
        ({"legal_authority": "Companies Act 2006"}, "England", False),  # an authority decides
        ({}, "England", True),
        ({}, "New South Wales", False),
        ({}, None, False),
    ],
)
def test_is_uk(
    identification: dict[str, str | None], address_country: str | None, expected: bool
) -> None:
    assert is_uk(identification, address_country) is expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234567", "01234567"),
        ("01234567", "01234567"),
        ("123 456", "00123456"),
        ("SC123456", "SC123456"),
        ("sc 12345", "SC012345"),
        ("R0012345", "R0012345"),
        ("OE001234", "OE001234"),
        ("HE123456", None),
        ("SY000101", None),
        ("123456789", None),
        ("N/A", None),
        ("", None),
        (None, None),
    ],
)
def test_uk_number(raw: str | None, expected: str | None) -> None:
    assert uk_number(raw) == expected


def test_names_agree() -> None:
    assert names_agree("QUARRY LANE INSTRUMENTS LIMITED", "Quarry Lane Instruments Ltd")
    assert not names_agree("QUARRY LANE INSTRUMENTS LIMITED", "Harbour Mill Foods Ltd")


def test_resolve_corporate() -> None:
    index = {"01234567": "QUARRY LANE INSTRUMENTS LIMITED"}
    uk = {"country_registered": "England", "registration_number": "1234567"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", uk, None, index) == (
        "resolved",
        "01234567",
    )
    assert resolve_corporate("Harbour Mill Foods Ltd", uk, None, index) == (
        "name_mismatch",
        "01234567",
    )
    other = {**uk, "registration_number": "7654321"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", other, None, index) == (
        "number_not_found",
        "07654321",
    )
    assert resolve_corporate("X", {"country_registered": "England"}, None, index) == (
        "no_number",
        None,
    )
    jersey = {"country_registered": "Jersey", "registration_number": "1234567"}
    assert resolve_corporate("Quarry Lane Instruments Ltd", jersey, None, index) == (
        "non_uk",
        None,
    )
```

**`ingest/tests/fixtures/natures_of_control.txt`** (verbatim):

```text
# The 86 natures_of_control values in companieshouse/api-enumerations psc_descriptions.yml
# (file changed 2025-11-07, read 2026-10-18; bulk-sources-loading.md 4.3). Enumeration values only.
ownership-of-shares-25-to-50-percent
ownership-of-shares-25-to-50-percent-as-firm
ownership-of-shares-25-to-50-percent-as-trust
ownership-of-shares-50-to-75-percent
ownership-of-shares-50-to-75-percent-as-firm
ownership-of-shares-50-to-75-percent-as-trust
ownership-of-shares-75-to-100-percent
ownership-of-shares-75-to-100-percent-as-firm
ownership-of-shares-75-to-100-percent-as-trust
ownership-of-shares-more-than-25-percent-as-control-over-firm-registered-overseas-entity
ownership-of-shares-more-than-25-percent-as-control-over-trust-registered-overseas-entity
ownership-of-shares-more-than-25-percent-as-firm-registered-overseas-entity
ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity
ownership-of-shares-more-than-25-percent-registered-overseas-entity
part-right-to-share-surplus-assets-25-to-50-percent
part-right-to-share-surplus-assets-25-to-50-percent-as-firm
part-right-to-share-surplus-assets-25-to-50-percent-as-trust
part-right-to-share-surplus-assets-50-to-75-percent
part-right-to-share-surplus-assets-50-to-75-percent-as-firm
part-right-to-share-surplus-assets-50-to-75-percent-as-trust
part-right-to-share-surplus-assets-75-to-100-percent
part-right-to-share-surplus-assets-75-to-100-percent-as-firm
part-right-to-share-surplus-assets-75-to-100-percent-as-trust
registered-owner-as-nominee-another-entity-england-wales-registered-overseas-entity
registered-owner-as-nominee-another-entity-northern-ireland-registered-overseas-entity
registered-owner-as-nominee-another-entity-scotland-registered-overseas-entity
registered-owner-as-nominee-person-england-wales-registered-overseas-entity
registered-owner-as-nominee-person-northern-ireland-registered-overseas-entity
registered-owner-as-nominee-person-scotland-registered-overseas-entity
right-to-appoint-and-remove-directors
right-to-appoint-and-remove-directors-as-control-over-firm-registered-overseas-entity
right-to-appoint-and-remove-directors-as-control-over-trust-registered-overseas-entity
right-to-appoint-and-remove-directors-as-firm
right-to-appoint-and-remove-directors-as-firm-registered-overseas-entity
right-to-appoint-and-remove-directors-as-trust
right-to-appoint-and-remove-directors-as-trust-registered-overseas-entity
right-to-appoint-and-remove-directors-registered-overseas-entity
right-to-appoint-and-remove-members-as-firm-limited-liability-partnership
right-to-appoint-and-remove-members-as-trust-limited-liability-partnership
right-to-appoint-and-remove-members-limited-liability-partnership
right-to-appoint-and-remove-person
right-to-appoint-and-remove-person-as-firm
right-to-appoint-and-remove-person-as-trust
right-to-share-surplus-assets-25-to-50-percent-as-firm-limited-liability-partnership
right-to-share-surplus-assets-25-to-50-percent-as-trust-limited-liability-partnership
right-to-share-surplus-assets-25-to-50-percent-limited-liability-partnership
right-to-share-surplus-assets-50-to-75-percent-as-firm-limited-liability-partnership
right-to-share-surplus-assets-50-to-75-percent-as-trust-limited-liability-partnership
right-to-share-surplus-assets-50-to-75-percent-limited-liability-partnership
right-to-share-surplus-assets-75-to-100-percent-as-firm-limited-liability-partnership
right-to-share-surplus-assets-75-to-100-percent-as-trust-limited-liability-partnership
right-to-share-surplus-assets-75-to-100-percent-limited-liability-partnership
significant-influence-or-control
significant-influence-or-control-as-control-over-firm-registered-overseas-entity
significant-influence-or-control-as-control-over-trust-registered-overseas-entity
significant-influence-or-control-as-firm
significant-influence-or-control-as-firm-limited-liability-partnership
significant-influence-or-control-as-firm-registered-overseas-entity
significant-influence-or-control-as-trust
significant-influence-or-control-as-trust-limited-liability-partnership
significant-influence-or-control-as-trust-registered-overseas-entity
significant-influence-or-control-limited-liability-partnership
significant-influence-or-control-registered-overseas-entity
voting-rights-25-to-50-percent
voting-rights-25-to-50-percent-as-firm
voting-rights-25-to-50-percent-as-firm-limited-liability-partnership
voting-rights-25-to-50-percent-as-trust
voting-rights-25-to-50-percent-as-trust-limited-liability-partnership
voting-rights-25-to-50-percent-limited-liability-partnership
voting-rights-50-to-75-percent
voting-rights-50-to-75-percent-as-firm
voting-rights-50-to-75-percent-as-firm-limited-liability-partnership
voting-rights-50-to-75-percent-as-trust
voting-rights-50-to-75-percent-as-trust-limited-liability-partnership
voting-rights-50-to-75-percent-limited-liability-partnership
voting-rights-75-to-100-percent
voting-rights-75-to-100-percent-as-firm
voting-rights-75-to-100-percent-as-firm-limited-liability-partnership
voting-rights-75-to-100-percent-as-trust
voting-rights-75-to-100-percent-as-trust-limited-liability-partnership
voting-rights-75-to-100-percent-limited-liability-partnership
voting-rights-more-than-25-percent-as-control-over-firm-registered-overseas-entity
voting-rights-more-than-25-percent-as-control-over-trust-registered-overseas-entity
voting-rights-more-than-25-percent-as-firm-registered-overseas-entity
voting-rights-more-than-25-percent-as-trust-registered-overseas-entity
voting-rights-more-than-25-percent-registered-overseas-entity
```

#### M2.3c Officers through the API

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.3b |
| Branch | `p2/m2-3c-ch-officers` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | No |
| Needs | `CH_API_KEY` in `.env` and `access.companies_house_key: available` on the machine that runs the fetch |
| Real-data run | `uv run neonradar ingest build --profile uk-tiny --dataset gb_companies_house --step officers` (for `uk-sample`, start it on Friday 30 October: about three hours, 1.1) |

**Goal.** Directors and secretaries of the slice companies, with the Companies House person number that rule D3 uses, fetched politely within a budget and resumable after any interruption.

**Deliverables.**

1. `companies_house/officers.py`: first the real-data gate (M2.2: dataset access, which for the officers API is `access.companies_house_key`, the profile, the data protection documents, CI and Codespaces, the approved machine), which exits 3 before any request; then, for each company in `slice.csv` in its order (seeds, then parents and children by level, then the district sample in hash order; M2.3a), `GET /company/{number}/officers?items_per_page=100&start_index=<k>`, advancing `k` by the number of items returned until `total_results` (whether a gateway caps the page size is not known, note 5). The Phase 1 client rules apply: basic auth with the key, 2 requests per second, on HTTP 429 wait until `X-Ratelimit-Reset` or 300 seconds.
2. **Budget, cache and resume** (profile block `officers`): stop when `request_budget` requests have been made in this run; cache every response in `data/cache/real/api/gb_companies_house/officers/<first 20 hex of sha1 of the company number>/<start_index>.json` for `cache_days` (folder names never show which companies a slice holds, so the `ls` that the hook allows prints none) (a cache hit costs no request); a re-run continues with the companies not yet complete. The summary reports requests, cache hits, companies complete, partial and not reached, and the duration. `appointments: false` means `/officers/{id}/appointments` is never called; `active_only: true` adds `filter=active`.
3. **Records** (ids per 4.4; one record per officer id across all companies, from the path of `links.officer.appointments`):
   - natural persons: `Person` with `name` as given (`SURNAME, Forenames`), `firstName` and `lastName` from `neonradar_keys.names.split_ch_name`, `birthDate` `yyyy-mm`, `nationality` (each comma-separated demonym through `country_code`), `country` from `country_of_residence`, `nr.ch_person_number` the item's `person_number` unchanged when present (12 digits in community examples; D3 uses the first 8, with the name check, 7.1.2; note 5), the service address as an `Address` record with role `service` in `nr.address_roles`; `occupation` is not loaded;
   - roles starting `corporate-`: `Company` when `identification.registration_number` is present, else `LegalEntity`; `registrationNumber` and `jurisdiction` by M2.3b rule 5 (`identification_type`, `legal_authority`, `legal_form`, `place_registered`, `registration_number`);
   - one `Directorship` per appointment: `director` the officer record, `organization` the company, `role` the raw `officer_role`, `startDate` `appointed_on`, `endDate` `resigned_on`, `nr.is_nominee` for `nominee-*` and `corporate-nominee-*` roles; id per 4.4.
4. Profile block model for `officers` (`enabled`, `request_budget`, `cache_days`, `appointments`, `active_only`).
5. Tests (mocked transport with `httpx.MockTransport`, invented officers): the gate (`-k gate`: `NR_PROJECT_FILE` points at a temporary project whose `access.real_data_profiles` lacks the profile, then one without `access.companies_house_key: available`; each exits 3 with its message and the transport sees no request); the missing key (`-k missing_key`: a project that allows the profile, with `access.companies_house_key: available` and `access.data_protection_filed: true`, `NR_REAL_DATA_MACHINE=approved`, and `CI`, `CODESPACES` and `CH_API_KEY` unset: the officers step's own message and no request); companies fetched in `slice.csv` order; paging until `total_results`, including a short page; the budget stopping mid-company and the re-run finishing it from the cache without new requests for cached pages; 429 handling with and without `X-Ratelimit-Reset`; one officer in two companies gives one record and two directorships; corporate officers with and without a registration number; `person_number` absent; nominee roles.

**Acceptance.** `uv run pytest ingest/tests/test_ch_officers.py -q`; `uv run pytest ingest/tests/test_ch_officers.py -k gate -q` (exit 3 before any request); `uv run pytest ingest/tests/test_ch_officers.py -k missing_key -q` (the officers step's own message when `CH_API_KEY` is missing, with the gate passed); `make check`.

**Real-data run (operator).** The command in the header; paste the summary.

**Review focus (humans).** Data steward: the cache holds personal data: is it inside `data/cache/real/` and covered by the purge? Ingest mentor: at 2 requests per second, does the summary's duration match the request count?

### M2.4 GLEIF Golden Copy

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor |
| Depends on | M2.1a, M2.2, M2.3a |
| Branch | `p2/m2-4-gleif` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | No |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset gleif_lei && uv run neonradar ingest build --profile uk-tiny --dataset gleif_lei` (run the fetch as soon as this merges: GLEIF announced brief interruptions between 19 October and 4 November, note 6.4) |

**Goal.** LEI records and their accounting-consolidation parents for the companies in the slice, from GLEIF's bulk files instead of the API, so that D1 and D2 can join them to Companies House records and the graph shows which group a company belongs to.

**Deliverables.**

1. `ingest/src/neonradar_ingest/sources/gleif/golden_copy.py`, `SourceSpec` with the product `golden-copy`: `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest` (the combined endpoint; `lei2/latest` served an older publish on 18 October, note 6.1), and from it the CSV files of type `lei2` (LEI-CDF 3.1, about 505 MB zipped) and `rr` (RR-CDF 2.1, about 24 MB). Version: the publish date and time (for example `20261017-1600`). Read the endpoint's JSON once in the session with a short `uv run python` command to confirm its field names (it is file metadata, no personal data; the real-data hook keeps WebFetch off data hosts, M2.0), and mock it in tests. If GLEIF's announced interruptions stop the read, retry later in the session; if it still fails, stop and ask (2.5 item 5): note 6.1 gives only `publish_date` and the file URL pattern, not the field names of the file entries. Reporting exceptions (`repex`) are not used in Phase 2.
2. **Reading**: each zip member through `io.TextIOWrapper(..., encoding="utf-8", errors="strict", newline="")` and `csv.DictReader` (quoted fields may contain line breaks, note 6.2). Columns are dotted paths; check the enforced set of note 6.2 on the LEI file and, on the RR file, `Relationship.StartNode.NodeID`, `Relationship.StartNode.NodeIDType`, `Relationship.EndNode.NodeID`, `Relationship.RelationshipType` and `Relationship.RelationshipStatus` (the RR 2.1 header is unverified, note 6.2); a missing column stops the build with its name. Optional columns (the period and quantifier columns of the RR file, the creation date of the LEI file) are found by their dotted names in the header and counted when absent. Every real build writes the two header rows (column names only) to the summary as the lists `lei_headers` and `rr_headers` (the builder's registered `list_keys`, M2.2; a name longer than 80 characters is counted as `headers_too_long`, not written), so the next spec update can confirm them.
3. **Scope** (profile block `gleif_lei.scope`): `slice` keeps the LEIs whose `Entity.RegistrationAuthority.RegistrationAuthorityID` is `RA000585`, `RA000586` or `RA000587` and whose `RegistrationAuthorityEntityID`, normalised with `neonradar_keys.ids.uk_company_number`, is in the profile's Companies House `slice.csv` (`work_dir(profile, "gb_companies_house")`, kept between builds, M2.3), plus their direct and ultimate consolidating parents from the RR file (any country); without that file the build stops with "build gb_companies_house for this profile first" (exit 2); `uk` keeps every LEI at those three authorities (119,382 on 18 October, note 6.1) plus their parents; `all` exists for tests only. Two passes over the LEI file: the first finds the scoped LEIs, the second the parents.
4. **Records** (`Company` `gleif-<LEI>`; `nr.source_ref` the LEI):

   | Column | FtM | Rule |
   |---|---|---|
   | `LEI` | `leiCode` | kept only if `is_valid_lei`; others counted |
   | `Entity.LegalName` | `name` | |
   | `Entity.OtherEntityNames.OtherEntityName.<n>`, `Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.<n>` | `alias` | `n` from 1 to 5, read when present |
   | `Entity.LegalJurisdiction` | `jurisdiction` | lower-cased through FollowTheMoney's country type (`GB` to `gb`, `GB-SCT` to `gb-sct`, `US-DE` to `us`) |
   | `Entity.RegistrationAuthority.RegistrationAuthorityEntityID` | `registrationNumber` | for the three UK authorities, `uk_company_number` (Companies House forms only; a value it rejects is kept raw and counted); raw for every other authority. The resolver treats a GLEIF number as a UK company number only when it is already in the 8-character Companies House form (M2.10a), so a raw number from another register is never padded into one |
   | `Entity.EntityStatus` | `status` | raw (`ACTIVE`, `INACTIVE`) |
   | `Entity.LegalForm.EntityLegalFormCode`, `Entity.LegalForm.OtherLegalForm` | `legalForm` | the code, else the text |
   | `Entity.EntityCreationDate` | `incorporationDate` | when the column exists: a date and time with an offset (`2012-06-06T15:52:00+02:00`), so through `lists.common.parse_iso` (M2.6a), which keeps the date |
   | `Entity.LegalAddress.*`, `Entity.HeadquartersAddress.*` | `addressEntity` | `Address` records `gleif-addr-<first 20 hex of sha1(address_key)>` built as in M2.3a deliverable 7, with the roles `registered` and `business` in `nr.address_roles` (an object from address id to role); when both addresses have the same key, one `Address` with role `registered` |
   | `Registration.RegistrationStatus` | none | records with `ANNULLED` or `DUPLICATE` are skipped and counted; the others load |

   `sourceUrl` is `https://search.gleif.org/#/record/<LEI>`. GLEIF's terms forbid implying endorsement (Phase 1 `contracts/datasets.yaml` notes): nothing NeonRadar shows may suggest that GLEIF endorses it.
5. **Relationships** (RR file, both ends LEIs, status `ACTIVE`, and both ends loaded records of this build; others skipped and counted by type and status): `IS_DIRECTLY_CONSOLIDATED_BY` and `IS_ULTIMATELY_CONSOLIDATED_BY` become `Ownership` with `nr.consolidation` `direct` or `ultimate` (owner the parent, the end node; asset the child, the start node), which C2 maps to `CONSOLIDATES`, never to `OWNS`. No percentage is set: GLEIF's Level 2 data is "accounting consolidation", not ownership (note 6.3); quantifier columns are counted when filled, not loaded. `startDate` and `endDate` from the period whose `periodType` is `RELATIONSHIP_PERIOD`, when present. Branch and fund relationship types (`IS_INTERNATIONAL_BRANCH_OF`, `IS_FUND-MANAGED_BY`, `IS_SUBFUND_OF`, `IS_FEEDER_TO`) are counted, not loaded. Ids per 4.4.
6. Profile block model (`enabled`, `scope`).
7. Tests (synthetic CSV files in in-memory zips, invented LEIs with valid check digits): the dotted header with optional columns absent and present; a missing enforced column; a quoted field with a line break; the `slice` scope with a UK child whose parent is foreign; a missing `slice.csv` (exit 2); `uk` scope; a UK-authority number that is not a Companies House form (kept raw, counted); a creation date with an offset; one `Address` when the legal and headquarters keys are equal; annulled and duplicate records skipped; consolidation mapping and direction; a relationship to an LEI outside the scope skipped; inactive and branch relationships skipped; the two header lists written to the summary.

**Acceptance.** `uv run pytest ingest/tests/test_gleif_*.py -q`; `make check`.

**Real-data run (operator).** The command in the header; paste the summary (publish date, records by scope reason, relationships by type, skipped counts, the two header rows).

**Review focus (humans).** Graph mentor: are GLEIF parents shown as consolidation (`CONSOLIDATES`), never as share ownership? Ingest mentor: does the number of slice companies with an LEI look plausible against the national figure in note 6.1 (about 2 percent of UK companies have one)?

### M2.5 ICIJ Offshore Leaks loader

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.1a, M2.2, M2.8 |
| Branch | `p2/m2-5-icij` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | No |
| Real-data run | `uv run neonradar data fetch --profile uk-sample --dataset icij_offshore_leaks && uv run neonradar ingest build --profile uk-sample --dataset icij_offshore_leaks` |

**Goal.** The Phase 1 spike becomes a production loader: a bounded slice tied to the same postcode districts as the register slice (or, by the data steward's decision, a wider one), with every link classified and ICIJ's own duplicate hints kept for the resolver.

**Deliverables.**

1. `ingest/src/neonradar_ingest/sources/icij/full.py`: a `SourceSpec` for `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip` (follow redirects; version from `Last-Modified`, else the download date; conditional requests with `If-None-Match` and `If-Modified-Since`) and a `Builder` that reads the six CSV members straight from the zip (`zipfile.ZipFile.open` wrapped in `io.TextIOWrapper(..., encoding="utf-8", newline="")` and `csv.DictReader`), never extracting to disk. Headers are matched by name. `node_id` and `name` (and `node_id_start`, `node_id_end`, `rel_type` and `link` in `relationships.csv`) are required: a missing one stops the build with its name. Every other column in the mapping is optional: read when present, its absence counted in the summary (only two header rows are confirmed, `bulk-sources-loading.md` 7). Extra columns are counted too; columns the mapping does not use (for example `note`) are never read into records.
2. **Modes** (profile block `mode`, `max_nodes`, `sample_seed`; the block model fails on unknown keys). In every mode, when the selected set exceeds `max_nodes`, the loader keeps whole levels in order and, inside the level that overflows, the nodes with the smallest `sha256("<sample_seed>|<node_id>")`; a relationship is kept only when both ends are kept.
   - `district-linked` (the `uk-sample` default): level 0 is every node of `nodes-addresses.csv` whose `address` contains a UK postcode (`neonradar_keys.postcodes.find_uk_postcode`) whose district is one of the same profile's `gb_companies_house.companies.postcode_districts`; level 1 adds every entity and officer linked to a level 0 address by `registered_address`; level 2 adds every officer and intermediary linked to a level 1 entity by `officer_of` or `intermediary_of`. Nothing further is followed. This ties the leak records to the geography of the register slice (data minimisation, ADR-0013). A profile without postcode districts cannot use this mode (the block model refuses it).
   - `gb-linked` (only when the data steward chooses it in the profile, recorded in ADR-0013): level 0 is every node whose `country_codes` (semicolon-separated ISO alpha-3 codes) contain `GBR`; level 1 adds every node directly linked to a level 0 node.
   - `full`: every node and relationship (`max_nodes` ignored; for local experiments only, never in a committed profile).
   Relationships are read before node records are written, so that `registered_address` links become `addressEntity` on the right record. The summary reports the nodes per level, the nodes dropped by the cap and the relationships dropped with them.
3. **Mapping to C1** (prefix `icij`, ids `icij-<node_id>` as in Phase 1; `nr.source_ref` the `node_id`; `icijId` the `node_id`; `publisher` the `sourceID`, for example "Panama Papers"; `sourceUrl` `https://offshoreleaks.icij.org/nodes/<node_id>`):

   | File | FtM schema | Properties |
   |---|---|---|
   | `nodes-entities.csv` | `Company` | `name`; `previousName` from `former_name`; `alias` from `original_name` when it differs; `jurisdiction` from `jurisdiction_description` through `neonradar_keys.countries.country_code`; `country` from `country_codes`; `incorporationDate` from `incorporation_date`; `dissolutionDate` from the first of `inactivation_date`, `struck_off_date`, `closed_date`; `status` |
   | `nodes-officers.csv` | `LegalEntity` (ICIJ does not say whether an officer is a person) | `name`, `country` |
   | `nodes-intermediaries.csv` | `LegalEntity` | `name`, `country`, `status` |
   | `nodes-others.csv` | `LegalEntity` | `name`; `jurisdiction` from `jurisdiction_description` through `country_code`; `country` from `country_codes`; `incorporationDate`; `dissolutionDate` from the first of `struck_off_date` and `closed_date` (the file has `type`, not `status`) |
   | `nodes-addresses.csv` | `Address` | `full` from `address`, `country` |

   The free-text `note` column is never loaded: matching does not use it and it can hold anything (data minimisation). Dates use the format `%d-%b-%Y` (for example `22-MAY-2006`) and become ISO dates. Some carry a two-digit year (another project changed its ICIJ parser for that on 5 August 2026, `bulk-sources-loading.md` 7): accept `%d-%b-%y` as well, read the year as `19YY` when `YY` is greater than the current year's last two digits and as `20YY` otherwise, and count these dates. Unparseable dates are dropped and counted. Names that are only question marks, or are one of the junk values the Phase 1 spike report lists, become empty; a record left without a name is skipped and counted (C1 R3 requires `name`).
4. **Relationships** (`relationships.csv`, keyed on `rel_type` and the lower-cased `link`):
   - `registered_address`: `addressEntity` on the start record and `nr.address_roles` `{"<address record id>": "registered"}` (C1 defines it as an object from address id to role);
   - `intermediary_of`: `Representation` (agent the intermediary, client the entity, `role` `intermediary`);
   - `officer_of`: a lookup table in `ingest/src/neonradar_ingest/sources/icij/links.yaml` maps each `link` value to one of:
     - `Ownership` (shareholder, owner, beneficial owner, ultimate beneficial owner, partner and the like; owner the officer, asset the entity, `role` the raw link); `nominee shareholder` and the other nominee shareholding values also set `nr.is_nominee: true` (C1 1.1.0);
     - `Directorship` (director, secretary, nominee director, president, treasurer, signatory, power of attorney and the like; `role` the raw link; `nr.is_nominee` for nominee roles);
     - `UnknownLink` with `role` the raw link, for the trust and foundation roles (settlor, founder, beneficiary, grantor, protector, trustee and the like: none of them is a holding of shares, and NeonRadar does not guess what control they give) and for everything else.
     Seed the table from the Phase 1 spike report's top links and the lists in `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md` C.1; unknown values map to `UnknownLink` and are counted by value under a `_by_value` key (M2.2: values seen fewer than 10 times are folded into one count), so the table can be extended;
   - `underlying`, `related_entity`, `connected_to`: `UnknownLink` with `role` the `rel_type`;
   - `same_name_as`, `same_id_as`, `same_as`, `similar`, `similar_company_as`, `same_company_as`, `same_intermediary_as`, `probably_same_officer_as` and the other `same_*` and `similar*` values between two non-address nodes: not loaded as relationships; written to `icij_offshore_leaks-<yyyymmdd>-hints.csv` (`record_a,record_b,hint`) beside the records, where the resolver reads them as `source_hint` possible matches (they never merge anything by themselves, 7.1);
   - `same_address_as` and any other hint whose ends are addresses: dropped and counted (addresses never become possible matches, 7.1);
   - `start_date` and `end_date` become `startDate` and `endDate`.
   Relationship ids: `icij-<schema in lower case>-<first 20 hex of sha1 of start, end, rel_type, link>`.
5. Manifest `licence` and `attribution` from `contracts/datasets.yaml`; the manifest `notes` include the ICIJ disclaimer line "There are legitimate uses for offshore companies and trusts." (re-fetched from the FAQ, as M1.8c says).
6. Tests (synthetic rows in an in-memory zip, as in M1.8c): every mapping row above, including that `note` never reaches a record; `district-linked` selection on a small graph with a known answer (an address inside and one outside the districts, the three levels, the cap order with a fixed `sample_seed`, relationships dropped with their ends); `gb-linked` selection the same way; the block model refusing `district-linked` without postcode districts and refusing unknown keys; `nr.address_roles` written as an object; a nominee shareholder becoming `Ownership` with `nr.is_nominee`; settlor, founder, beneficiary, grantor and protector becoming `UnknownLink`; hints written and never loaded, and address hints dropped; every link value in a test list maps to the expected schema; date parsing and junk names; the build validates in strict mode.

**Acceptance.** `uv run pytest ingest/tests/test_icij_*.py -q`; `uv run neonradar ingest build --profile demo` still passes (ICIJ is not in the demo profile); `make check`.

**Real-data run (operator).** The command in the header; paste the summary (counts by schema and link class, nodes per level and dropped by the cap, hints written and address hints dropped, unknown link values with counts but no names).

**Review focus (humans).** Data steward: does the summary contain only counts and link vocabulary? Is `district-linked` the slice you want, or does an investigation need `gb-linked` (then record why in ADR-0013)? Ingest mentor: are the five most common unknown link values really neither ownership nor directorship?

### M2.6 Official sanctions lists and the UK Parliament PEP source (five sub-milestones)

Four loaders for the official lists, which replace OpenSanctions as the default sanctions source (decision 2 in 0.5), and one optional loader for a public PEP source. Read `docs/research/2026-10-18/sanctions-peps.md` first; the section numbers below point into it. M2.6a writes the shared module and must merge first; M2.6b, M2.6c and M2.6d then run in parallel; M2.6e is optional and does not block Gate 2.

**Rules for every list loader** (M2.6a to M2.6d):

1. **Layout.** `ingest/src/neonradar_ingest/sources/lists/`: `common.py` (M2.6a, verbatim below), `bounds.yaml`, one module per list (`gb_fcdo.py`, `us_ofac.py`, `un_sc.py`, `eu_fsf.py`), each registering a `SourceSpec` and a `Builder` (M2.2). Tests in `ingest/tests/test_lists_<slug>.py`; fixtures in `ingest/tests/fixtures/lists/<slug>/`.
2. **Gating.** A list runs only when its slug is in `access.sanctions_lists` (`Profile.enabled_sources`, M2.2). That is the first check of the real-data gate (M2.2), so `neonradar data fetch --dataset <slug>` for a list that is not there exits 3 with the gate's message for that rule (for example "us_ofac_sdn is not in access.sanctions_lists") before the profile, data protection and machine checks and before any request. Each list's gate test (`-k gate`) points `NR_PROJECT_FILE` at a temporary project file that allows the profile on the machine but leaves the list out, sets `NR_REAL_DATA_MACHINE=approved`, and asserts exit 3, that message and no request on a mock transport. A session never edits `access.*` (the data steward's decision).
3. **XML.** Parse with `defusedxml.ElementTree.iterparse` (add `defusedxml==0.7.*` to `ingest`, and `types-defusedxml` to the dev group), one record element at a time, calling `element.clear()` after each. Compare tags after removing any namespace (`tag.rsplit("}", 1)[-1]`), because OFAC changed its namespace in 2024 (note 2.4). Ruff's `S314` rejects the standard library parsers; keep the rule on.
4. **Download.** The shared HTTP client (its User-Agent is required: OFAC answers 403 without one). `RemoteFile.version` is the UTC date of the fetch (`yyyy-mm-dd`, the download date of 4.4: a list file shows its own stamp only once downloaded, and the lists change several times a week); the builder writes the list's own stamp (UK `DateGenerated`, OFAC `DateOfIssue`, UN `dateGenerated`, EU `generationDate` and `globalFileId`) into the manifest `notes` and the summary (string key `list_generated`, registered on the builder, M2.2). `download.json`, the manifests and the summaries store the URL that was requested without its query string, never a redirect target, and every logged URL has its query string removed (the UN redirect carries a signature valid for one hour, note 3.1; the EU URL carries a token).
5. **One record per designated party.** Individuals become `Person`, entities `Organization`. Ships, aircraft, crypto wallets and securities are skipped and counted by type (`Vessel`, `Airplane`, `CryptoWallet` and `Security` are not C1 schemata).
6. **Party records.** `topics: ["sanction"]`. Strong names and aliases go to `name` and `alias`, weak ones to `weakAlias` (the UN calls a low quality alias "probably insufficient alone for a positive identification", note 9; M2.10a never builds name keys from `weakAlias`). Names in other scripts go to `alias`. Birth dates are ISO partial dates from `common.py`. Countries, nationalities and citizenship go through `neonradar_keys.countries.country_code`; a value that does not map is counted, never guessed. Passport numbers go to `passportNumber`, national identity numbers to `idNumber`, with spaces removed. UK company numbers and LEIs are taken only as each loader says, because they feed D1 and D2: a wrong number can merge a sanctions entry into a real company. A number from a typed identifier field goes through `neonradar_keys.ids.uk_company_number`, which accepts only Companies House forms; free text gives one only through `common.uk_company_numbers`, which needs a company-number label and a UK register right next to the number. `nr.source_ref` is the list's own key.
7. **Never loaded** (data minimisation, note 8): phone numbers, e-mail addresses, websites, "other information" and remarks. Statements of reasons only when the profile block sets `keep_reasons: true` (default `false`), and then only in `Sanction:reason`. Titles and positions only when the block sets `keep_positions: true` (default `false`): matching does not use them, and a title or position can reveal religious or political belief (special category data). Every list block model accepts `enabled`, `keep_reasons` and `keep_positions` (7.8) and rejects unknown keys.
8. **One `Sanction` per designation**, id `common.sanction_id(prefix, party_id, designation_key)` (4.4): `entity` (the party id), `authority` and `country` from the table below, `authorityId`, `unscId` (normalised with `neonradar_keys.ids.un_reference`), `program`, `programId` where given, `startDate`, `listingDate`, `modifiedAt`, `provisions`, `sourceUrl` where given.
9. **Relationships** only between two loaded parties of the same list (OFAC, M2.6b). A relationship to a skipped party is skipped and counted. Owners, parents and subsidiaries given only as names are counted, not loaded: a name-only stub would invite name-only matches (P3), and it must never carry `sanction` (note 6.1).
10. **Sanity checks.** `bounds.yaml` (verbatim below) holds a count range per list and schema. A build outside a range fails with exit code 4 and the message from `common.check_bounds`, unless `--accept-size` is given (a human decides after reading the list's publication page). The summary reports fill rates: the share of persons with a birth date, a nationality, and a passport or identity number; of designations with a programme and a start date; of organisations with a registration number or LEI. A fill rate of zero for persons with a birth date, or for designations with a programme, fails the build with exit code 4, which `--accept-size` does not override: the parser is broken.
11. **Fixtures** are hand-written source-format files with invented values (2.9), following the structure in the note (sections given per list): names from the M1.8e neutral word lists; company numbers Companies House has not issued, `99` followed by six digits where the loader must keep the number (eight digits pass the D1 form) and `SY` numbers where it must drop it; `SYN0` LEIs (valid check digits, as in `test_lists_common.py`); passport numbers `SYNP` plus six digits; and UN-style references in a `ZZ` regime (`ZZi.001`), which no real regime uses. Never copy a value from a real list or from OpenSanctions (G2, stop-and-ask 3). Where the publisher's XSD can be downloaded (UK, OFAC; an XSD holds no personal data), the milestone downloads it once, commits it beside the fixture, and a test validates the fixture against it with `xmlschema` (`xmlschema==4.3.*` in the dev group, loaded with `allow="sandbox"` so validation never fetches anything). Tests never use the network: if the committed XSD is missing, that test is skipped with the reason, and the pull request says why it could not be downloaded.
12. **OpenSanctions crawler code** (MIT) may be read and its logic ported (note 5). The MIT condition is that "the above copyright notice and this permission notice shall be included", so a module that ports logic carries the full MIT licence text with every copyright line of the repository's `LICENSE` file in a header comment, and `THIRD_PARTY_NOTICES.md` lists the module with the same text. Never copy their YAML lookup tables, any data file, or literal values from their Python code (names, numbers, identifiers, mappings of real values): they hold real data.
13. **Real-data run** as in each header; the summary carries counts and rates only.

| Slug | `authority` | `country` | `bounds.yaml` (persons; organisations) | Note sections |
|---|---|---|---|---|
| `gb_fcdo_sanctions` | UK Foreign, Commonwealth and Development Office | `gb` | 3,000 to 7,200; 900 to 3,000 | 1 |
| `us_ofac_sdn` | US Office of Foreign Assets Control | `us` | 5,000 to 11,000; 6,000 to 14,000 | 2 |
| `un_sc_sanctions` | United Nations Security Council | none | 500 to 1,100; 180 to 420 | 3 |
| `eu_fsf` | European Union | `eu` | 3,400 to 8,000; 970 to 2,300 | 4 |

The ranges bracket the counts in the note: OpenSanctions entity counts for its copies of the lists on 18 October 2026 (UK 4,023 persons; OFAC 7,492 persons and 9,934 organisations; EU 4,398 persons and 1,728 organisations) and the UN's own page for its list (736 individuals and 274 entities on 15 October 2026). OpenSanctions also creates entities from free-text names (note 1.3), which NeonRadar does not (rule 9), so NeonRadar's counts can be lower.

**`ingest/src/neonradar_ingest/sources/lists/bounds.yaml`** (verbatim):

```yaml
# Expected record counts per list and schema (PHASE-2.md M2.6, rule 10). A build outside a range
# fails with exit code 4 unless --accept-size is given. The data steward may widen a range in a
# reviewed pull request after reading the list's publication page.
gb_fcdo_sanctions:
  Person: [3000, 7200]
  Organization: [900, 3000]
us_ofac_sdn:
  Person: [5000, 11000]
  Organization: [6000, 14000]
un_sc_sanctions:
  Person: [500, 1100]
  Organization: [180, 420]
eu_fsf:
  Person: [3400, 8000]
  Organization: [970, 2300]
```

#### M2.6a UK Sanctions List and the shared list module

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.1a, M2.2, M2.8 |
| Branch | `p2/m2-6a-uk-sanctions` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run`, `size-exception` |
| Plan first | Yes |
| Size | exception (the shared module and its tests are verbatim from this spec) |
| ADR | ADR-0017 (official sources for sanctions and PEP data) |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset gb_fcdo_sanctions && uv run neonradar ingest build --profile uk-tiny --dataset gb_fcdo_sanctions` |

**Goal.** The UK Sanctions List, the only UK source since 28 January 2026 (note 1.1), loads as one record per designated person or entity, with the shared helpers every list loader uses.

**Deliverables.**

1. `common.py` and `ingest/tests/test_lists_common.py`, verbatim below, and `bounds.yaml`.
2. `gb_fcdo.py`, `SourceSpec`: one file, `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml` (static since January 2026; if it answers 404, stop and report, and point to the publication page `https://www.gov.uk/government/publications/the-uk-sanctions-list`).
3. **Entity details.** The note could not confirm the XML element names for type of entity, parent company, subsidiaries and business registration numbers (note 1.4). Download the schema `https://assets.publishing.service.gov.uk/media/6916e72cdb01ecfcf96fc96b/SanctionsListSchema-4.33.3.xsd` into the fixture folder and take the names from it. If the XSD cannot be downloaded or does not define them, stop and ask (2.5, item 5); the fallback is the CSV columns in note 1.5.
4. **Grouping** (note 1.7: one person can have several Unique IDs, one per regime, and the OFSI Group ID that groups them is absent for designations made since 28 January 2026), in this order:
   - designations with the same non-empty `OFSIGroupID` form one party, id `uksl-g<OFSIGroupID>`, `nr.source_ref` `g<OFSIGroupID>`;
   - a designation without a group id whose `UNReferenceNumber` (through `un_reference`) is also on a grouped designation joins that group: one UN listing is one party (if two groups carry that reference, the designation is not joined to either and counts as a `group_conflict`);
   - the remaining designations that share a UN reference form one party, id `uksl-un-<reference>`, `nr.source_ref` `un-<reference>`;
   - every other designation is its own party, `uksl-<UniqueID>`, `nr.source_ref` the Unique ID.
   A record of the last two forms may be one of several designations of one person under different regimes, so the resolver does not keep it apart from other UK records with X6 (`list_party` is set only for `uksl-g` records, 7.1.3, M2.10a); entity resolution may merge them. If designations in one group disagree on `IndividualEntityShip`, keep them as separate parties under their Unique IDs and count `group_conflicts`. The summary counts parties of each form.
5. **Mapping** (`IndividualEntityShip`: `Individual` to `Person`, `Entity` to `Organization`, `Ship` skipped):

   | XML | FtM | Rule |
   |---|---|---|
   | `Names/Name` with `NameType` `Primary Name` | `name` | Person: `join_name([Name1, ..., Name5, Name6])` (Name6 is the surname, note 1.6); Organization: `Name6`, else the join; for a Person, the first primary name (of the group's designation with the smallest Unique ID) also gives `firstName` (Name1) and `lastName` (Name6); further primary names go to `alias` |
   | `NameType` `Primary Name Variation` | `alias` | |
   | `NameType` `Alias` | `alias` or `weakAlias` | `AliasStrength` `Good quality a.k.a` to `alias`, `Low quality a.k.a` to `weakAlias`; empty strength: `alias` when the name has two or more words, else `weakAlias` |
   | `NonLatinNames/NonLatinName/NameNonLatinScript` | `alias` | |
   | `Titles/Title`, `Individual/Positions/Position` | `title`, `position` | only with `keep_positions` (M2.6 rule 7); Position split on `\|` |
   | `DOBs/DOB` | `birthDate` | `parse_dmy` (literal `dd`, `mm` and `00`, note 1.6); unparseable values counted |
   | `Nationalities/Nationality`, `BirthDetails/Location` | `nationality`; `birthPlace`, `birthCountry` | `TownOfBirth` to `birthPlace`; `CountryOfBirth` through `country_code` |
   | `Genders/Gender` | `gender` | `Male`, `Female` to `male`, `female` |
   | `PassportDetails/Passport/PassportNumber`; `NationalIdentifierDetails/.../NationalIdentifierNumber` | `passportNumber`; `idNumber` | the additional-information fields are not loaded |
   | `Addresses/Address` | `address`, `country` | lines 1 to 6, postcode and country joined with ", "; `AddressCountry` through `country_code` |
   | business registration numbers (Organization) | `registrationNumber`, `jurisdiction`, `leiCode` | `common.uk_company_numbers(text)` (a company-number label and a UK register next to the number) to `registrationNumber` with `jurisdiction: gb`; `common.extract_leis(text)` to `leiCode`; every other number is counted, not loaded |
   | parent company, subsidiaries | none | counted as `stub_names_skipped` (M2.6 rule 9) |

6. **Sanctions**, one per designation in the party: `sanction_id("uksl", party_id, UniqueID)`; `authorityId` the Unique ID; `unscId` from `UNReferenceNumber`; `program` `RegimeName`; `startDate` `parse_dmy(DateDesignated)`; `modifiedAt` `parse_dmy(LastUpdated)`; `provisions` `split_values(SanctionsImposed)`; `reason` `html.unescape(UKStatementofReasons)` only with `keep_reasons`.
7. Profile block model: `enabled`, `keep_reasons` (default false), `keep_positions` (default false), unknown keys fail; the same model serves M2.6b to M2.6d.
8. `docs/data/sources/gb_fcdo_sanctions.md`: what the list is, the licence and attribution from `contracts/datasets.yaml`, the personal-data note, the grouping rule, what is not loaded and why.
9. `docs/decisions/0017-official-sanctions-and-pep-sources.md` (status `proposed`; deciders: data steward and project lead): the four official lists instead of OpenSanctions; the UN list only with written permission (3.3); weak aliases never match on their own; no stubs from free-text names; UK company numbers from free text only with a label and a UK register next to them; data minimisation (reasons, titles and positions off by default); the UK grouping rule; the PEP choice (`access.pep_sources` and `access.pep_former_months`, M2.6e); the per-deployment lawful basis (note 8).
10. Tests (fixture `uk-sanctions-list.xml`, about twelve designations): two designations of one person grouped by `OFSIGroupID` into one party with two sanctions; designations without a group id: one that joins a group through its UN reference, two that share a UN reference (one `uksl-un-` party), and one alone (`uksl-<unique id>`); the group conflict; every row of the mapping table; placeholder dates; weak and empty alias strengths; an entity whose registration string holds a labelled UK company number (`99` plus six digits), an unlabelled number, a non-UK number and an LEI (only the labelled UK number and the LEI kept); a ship skipped; `keep_reasons` and `keep_positions` off and on; the bounds failure (exit 4) and `--accept-size`; the gate (M2.6 rule 2); the fixture validates against the committed XSD.

**Acceptance.** `uv run pytest ingest/tests/test_lists_common.py ingest/tests/test_lists_gb_fcdo_sanctions.py -q` (the verbatim `test_lists_common.py`: 78 passed); `uv run pytest ingest/tests/test_lists_gb_fcdo_sanctions.py -k gate -q`; `make check`.

**Real-data run (operator).** The command in the header; paste the summary (counts per schema, groups, conflicts, skipped types, fill rates, the list's `DateGenerated`).

**Review focus (humans).** Data steward: does the summary contain only counts? Is the grouping rule what the format guide and the move to a single list say (notes 1.1 and 1.7)? Ingest mentor: read the negative cases in `test_uk_company_numbers`. Can you think of a free-text pattern that would give a wrong UK company number?

**`ingest/src/neonradar_ingest/sources/lists/common.py`** (verbatim):

```python
"""Shared helpers for the official sanctions list loaders (PHASE-2.md M2.6).

Pure functions only: no I/O, no network. The loaders build FtM entities with them.
"""

from __future__ import annotations

import calendar
import hashlib
import re
from collections.abc import Iterable

from neonradar_keys.ids import is_valid_lei, uk_company_number, un_reference

MIN_YEAR = 1800
MAX_YEAR = 2100
MAX_YEAR_SPAN = 20  # a wider birth year range gives no birth date

_PLACEHOLDER = re.compile(r"^(?:d{1,2}|m{1,2}|0{1,2})$", re.I)
_DMY = re.compile(r"^\s*(\w{1,2})\s*[/.-]\s*(\w{1,2})\s*[/.-]\s*(\d{4})\s*$")
_ISO = re.compile(r"^\s*(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?(?:T[\d:.]+)?(?:Z|[+-]\d{2}:?\d{2})?\s*$")
_YEAR = re.compile(r"^\s*(\d{4})\s*$")
_LEI = re.compile(r"\b[A-Z0-9]{18}[0-9]{2}\b")
_UK_REGISTER = (
    r"(?:companies\s+house|united\s+kingdom|great\s+britain|england\s*(?:and|&)\s*wales"
    r"|(?<!new\s)england|scotland|northern\s+ireland|(?<![a-z])(?:uk|u\.k\.|gb)(?![a-z]))"
)
_NUMBER = r"(?<![a-z0-9])([a-z]{2}\d{6}|r0\d{6}|\d{8})(?![a-z0-9])"
# A number label: up to two words such as "company" or "registration", then "no", "number",
# "nr" or "#" ("UK Company Number", "Companies House No.", "Reg. No.", "Registered No:").
_LABEL = (
    r"(?:(?:company|companies|registration|registered|reg\.?|incorporation)\s*){0,2}"
    r"(?:no\b\.?|number|nr\b\.?|#)"
)
_GAP = r"[\s,:()-]{0,3}"  # between a register and a label: separators only, never words
_TO_NUMBER = r"[\s.:#-]{0,3}"
# "UK Company Number 01234567", "Registered in England and Wales under number 07654321"
_FORWARD = re.compile(
    _UK_REGISTER + _GAP + r"(?:(?:under|with)\s+)?" + _LABEL + _TO_NUMBER + _NUMBER, re.I
)
# "Company registration number (UK) OC301234"
_MIDDLE = re.compile(_LABEL + r"\s*\(\s*" + _UK_REGISTER + r"\s*\)" + _TO_NUMBER + _NUMBER, re.I)
# "Company number 01234567 (UK)", "Company no. 01234567, registered in England"
_BACKWARD = re.compile(
    _LABEL
    + _TO_NUMBER
    + _NUMBER
    + r"[\s,]{0,3}(?:\(\s*"
    + _UK_REGISTER
    + r"\s*\)|registered\s+in\s+(?:the\s+)?"
    + _UK_REGISTER
    + ")",
    re.I,
)
# Words that make the clause about another company ("Parent company: UK Company Number ...").
_RELATED = re.compile(
    r"\b(?:subsidiar|parent|owned\s+by|owner|shareholder|affiliate|holding\s+compan)", re.I
)
_CLAUSE_END = ";|\n"


def _int(value: int | str | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = value.strip()
    return int(text) if text.isdigit() else None


def partial_date(
    year: int | str | None, month: int | str | None = None, day: int | str | None = None
) -> str | None:
    """ISO date with the precision the source gives: "1970", "1970-05" or "1970-05-17".

    A missing or zero part ends the date there. An impossible month gives the year only, an
    impossible day gives the year and month. A year outside 1800 to 2100 gives None.
    """
    y, m, d = _int(year), _int(month), _int(day)
    if y is None or not MIN_YEAR <= y <= MAX_YEAR:
        return None
    if not m or not 1 <= m <= 12:
        return f"{y:04d}"
    if not d or not 1 <= d <= calendar.monthrange(y, m)[1]:
        return f"{y:04d}-{m:02d}"
    return f"{y:04d}-{m:02d}-{d:02d}"


def parse_dmy(text: str | None) -> str | None:
    """UK list dates: "17/05/1970", "dd/05/1970", "dd/mm/1970", "00/00/1970" or "1970"."""
    if not text or not text.strip():
        return None
    year_only = _YEAR.match(text)
    if year_only:
        return partial_date(year_only.group(1))
    match = _DMY.match(text)
    if not match:
        return None
    day, month, year = match.groups()
    if _PLACEHOLDER.match(month):
        return partial_date(year)
    if _PLACEHOLDER.match(day):
        return partial_date(year, month)
    if not (day.isdigit() and month.isdigit()):
        return None
    return partial_date(year, month, day)


def parse_iso(text: str | None) -> str | None:
    """ISO dates with an optional time or offset: "1970-05-17", "1970-05-17-04:00", "1970"."""
    if not text:
        return None
    match = _ISO.match(text)
    if not match:
        return None
    return partial_date(*match.groups())


def year_range(first: int | str | None, last: int | str | None) -> list[str]:
    """Birth years for a range such as the UN "BETWEEN" dates: every year of a range that spans
    at most 20 years, so rule X5 can compare each of them; nothing for a wider range, which says
    too little to compare. One known end gives that year."""
    a, b = _int(first), _int(last)
    years = sorted({y for y in (a, b) if y is not None and MIN_YEAR <= y <= MAX_YEAR})
    if len(years) == 2:
        if years[1] - years[0] > MAX_YEAR_SPAN:
            return []
        years = list(range(years[0], years[1] + 1))
    return [f"{y:04d}" for y in years]


def period_dates(
    start: tuple[int | None, int | None, int | None], end: tuple[int | None, int | None, int | None]
) -> list[str]:
    """Dates for an OFAC DatePeriod given as (year, month, day) at its start and end.

    Equal ends give that date; a whole calendar year gives the year; a whole month gives the
    year and month; anything else gives the years from year_range.
    """
    if start == end:
        value = partial_date(*start)
        return [value] if value else []
    (y1, m1, d1), (y2, m2, d2) = start, end
    if y1 is not None and y1 == y2:
        if (m1, d1, m2, d2) == (1, 1, 12, 31):
            value = partial_date(y1)
            return [value] if value else []
        if m1 is not None and m1 == m2 and d1 == 1 and d2 == calendar.monthrange(y1, m1)[1]:
            value = partial_date(y1, m1)
            return [value] if value else []
    return year_range(y1, y2)


def join_name(parts: Iterable[str | None]) -> str | None:
    """Join name parts in the given order with single spaces; None when nothing is left."""
    words = [" ".join(p.split()) for p in parts if p and p.strip()]
    return " ".join(words) or None


def split_values(text: str | None, separators: str = "|") -> list[str]:
    """Split a multi-value field on any of the separator characters, dropping empty values."""
    if not text:
        return []
    pattern = "[" + re.escape(separators) + "]"
    return [v.strip() for v in re.split(pattern, text) if v.strip()]


def extract_leis(text: str | None) -> list[str]:
    """Every 20-character token in the text that passes the ISO 17442 check digits."""
    if not text:
        return []
    found = (m.group(0) for m in _LEI.finditer(text.upper()))
    return sorted({lei for lei in found if is_valid_lei(lei)})


def uk_company_numbers(text: str | None) -> list[str]:
    """UK company numbers from free text, only where the text labels them as such.

    A candidate is exactly eight digits, or a Companies House prefix and six digits, written
    after a number label ("company number", "registration no.", "reg. no.", "no.", "#"). It
    counts when a UK register (Companies House, United Kingdom, UK, GB, England and Wales,
    Scotland, Northern Ireland) is named right before the label, in brackets between the label
    and the number, or right after the number in brackets or as "registered in ...". Only
    separators may come between the register and the label, so "registered in Cyprus" or
    "incorporated in Malta" can never sit between them. A clause (the text since the last ";",
    "|" or line break) that mentions a subsidiary, parent, owner or shareholder gives nothing:
    the number may belong to the other company. Anything else is not a UK company number.
    """
    if not text:
        return []
    numbers: set[str] = set()
    for pattern in (_FORWARD, _MIDDLE, _BACKWARD):
        for match in pattern.finditer(text):
            start = max(text.rfind(end, 0, match.start()) for end in _CLAUSE_END)
            clause = text[start + 1 : match.end()]
            if _RELATED.search(clause):
                continue
            number = uk_company_number(match.group(1))
            if number:
                numbers.add(number)
    return sorted(numbers)


def un_references(values: Iterable[str | None]) -> list[str]:
    """Normalised UN reference numbers (rule D4), deduplicated and sorted."""
    return sorted({ref for ref in (un_reference(v) for v in values) if ref})


def sanction_id(prefix: str, party_id: str, designation_key: str) -> str:
    """Id of the Sanction record for one designation of one party (PHASE-2.md 4.4)."""
    digest = hashlib.sha1(f"{party_id}|{designation_key}".encode(), usedforsecurity=False)
    return f"{prefix}-sanction-{digest.hexdigest()[:20]}"


def check_bounds(
    slug: str, counts: dict[str, int], bounds: dict[str, dict[str, list[int]]]
) -> list[str]:
    """Messages for every schema whose count is outside the range in bounds.yaml."""
    problems = []
    for schema, (low, high) in sorted(bounds.get(slug, {}).items()):
        count = counts.get(schema, 0)
        if not low <= count <= high:
            problems.append(
                f"unexpected size for {slug}: {schema} {count}, expected {low} to {high}; "
                "the format may have changed"
            )
    return problems
```

**`ingest/tests/test_lists_common.py`** (verbatim):

```python
"""Tests for neonradar_ingest.sources.lists.common (PHASE-2.md M2.6a). Synthetic values only."""

from __future__ import annotations

import pytest

from neonradar_ingest.sources.lists.common import (
    check_bounds,
    extract_leis,
    join_name,
    parse_dmy,
    parse_iso,
    partial_date,
    period_dates,
    sanction_id,
    split_values,
    uk_company_numbers,
    un_references,
    year_range,
)

# A synthetic LEI with valid ISO 17442 check digits (prefix SYN0, as in M2.9).
SYN_LEI = "SYN0000000000000AB65"


@pytest.mark.parametrize(
    ("args", "expected"),
    [
        ((1970, 5, 17), "1970-05-17"),
        (("1970", "05", "17"), "1970-05-17"),
        ((1970, 5, None), "1970-05"),
        ((1970, 0, 0), "1970"),
        ((1970, None, 17), "1970"),
        ((1970, 13, 1), "1970"),
        ((1970, 2, 30), "1970-02"),
        ((2024, 2, 29), "2024-02-29"),
        ((2023, 2, 29), "2023-02"),
        ((1799, 1, 1), None),
        ((None, 1, 1), None),
        (("19x0", 1, 1), None),
    ],
)
def test_partial_date(args: tuple[object, ...], expected: str | None) -> None:
    assert partial_date(*args) == expected  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("17/05/1970", "1970-05-17"),
        ("7/5/1970", "1970-05-07"),
        ("dd/05/1970", "1970-05"),
        ("DD/MM/1970", "1970"),
        ("dd/mm/1970", "1970"),
        ("00/00/1970", "1970"),
        ("00/05/1970", "1970-05"),
        ("1970", "1970"),
        ("31/02/1970", "1970-02"),
        ("05/17/1970", "1970"),  # never month first: 17 is not a month
        ("", None),
        ("circa 1970", None),
        (None, None),
    ],
)
def test_parse_dmy(text: str | None, expected: str | None) -> None:
    assert parse_dmy(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1970-05-17", "1970-05-17"),
        ("1970-05-17-04:00", "1970-05-17"),
        ("1970-05-17+02:00", "1970-05-17"),
        ("2026-10-15T10:20:30.123Z", "2026-10-15"),
        ("1970-05", "1970-05"),
        ("1970", "1970"),
        ("17/05/1970", None),
        ("", None),
    ],
)
def test_parse_iso(text: str, expected: str | None) -> None:
    assert parse_iso(text) == expected


def test_year_range() -> None:
    assert year_range(1960, 1962) == ["1960", "1961", "1962"]
    assert year_range("1960", "1965") == ["1960", "1961", "1962", "1963", "1964", "1965"]
    assert year_range(1950, 1960) == [str(y) for y in range(1950, 1961)]  # X5 sees 1955 too
    assert len(year_range(1950, 1970)) == 21  # a span of 20 years: every year
    assert year_range(1950, 1971) == []  # wider: no birth date at all
    assert year_range(1962, 1960) == ["1960", "1961", "1962"]
    assert year_range(1960, None) == ["1960"]
    assert year_range(None, None) == []


def test_period_dates() -> None:
    assert period_dates((1970, 5, 17), (1970, 5, 17)) == ["1970-05-17"]
    assert period_dates((1970, 1, 1), (1970, 12, 31)) == ["1970"]
    assert period_dates((1970, 2, 1), (1970, 2, 28)) == ["1970-02"]
    assert period_dates((1972, 2, 1), (1972, 2, 29)) == ["1972-02"]
    assert period_dates((1970, 1, 1), (1971, 12, 31)) == ["1970", "1971"]
    assert period_dates((1970, 3, 1), (1970, 6, 30)) == ["1970"]
    assert period_dates((1940, 1, 1), (1975, 12, 31)) == []
    assert period_dates((None, None, None), (None, None, None)) == []


def test_join_and_split() -> None:
    assert join_name(["Petra", None, "  ", "Anne  Marie", "MARLOWE"]) == "Petra Anne Marie MARLOWE"
    assert join_name([None, ""]) is None
    assert split_values("Asset freeze|Travel ban| |") == ["Asset freeze", "Travel ban"]
    assert split_values("a; b|c", ";|") == ["a", "b", "c"]
    assert split_values(None) == []


def test_extract_leis() -> None:
    assert extract_leis(f"LEI: {SYN_LEI}; INN 7700000000") == [SYN_LEI]
    assert extract_leis(SYN_LEI.lower()) == [SYN_LEI]
    assert extract_leis("SYN0000000000000AB66") == []  # wrong check digits
    assert extract_leis(None) == []


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("UK Company Number 01234567", ["01234567"]),
        ("Companies House number: SC123456", ["SC123456"]),
        ("Registered in England and Wales under number 07654321", ["07654321"]),
        ("Registered in England and Wales with company number 07654321", ["07654321"]),
        ("England and Wales Company Registration Number: 07654321", ["07654321"]),
        ("Registered in Scotland, No. SC123456", ["SC123456"]),
        ("UK Reg. No. 01234567", ["01234567"]),
        ("Company number 01234567 (UK)", ["01234567"]),
        ("Company number 01234567 (United Kingdom)", ["01234567"]),
        ("Company No: 01234567 (England and Wales)", ["01234567"]),
        ("Company no. 01234567, registered in England", ["01234567"]),
        ("United Kingdom, Company Number NI612345", ["NI612345"]),
        ("Company registration number (UK) OC301234", ["OC301234"]),
        ("Registration number (UK): 01234567", ["01234567"]),
        ("UK company number R0012345", ["R0012345"]),
        ("Company Number 12345678 (Cyprus), UK Company Number 87654321", ["87654321"]),
        ("Company Number 12345678 (Cyprus); UK Company Number 87654321", ["87654321"]),
        ("Company Number 12345678 (Cyprus)", []),
        ("UK-based, registered in Cyprus as number 12345678", []),
        ("Subsidiary of a UK group, incorporated in Malta, company 12345678", []),
        ("Parent company: UK Company Number 01234567", []),
        ("Owned by a UK company, company number 01234567 (UK)", []),
        ("UK company 01234567", []),  # no number label
        ("Registered in England and Wales; Tax number 01234567", []),
        ("Registered in England and Wales, number of employees 01234567", []),
        ("UK VAT number 12345678", []),
        ("Registration Number HE123456", []),
        ("UK Company Number HE123456", []),  # HE is not a Companies House prefix
        ("UK Company Number SY000101", []),  # SY is the synthetic prefix, not Companies House
        ("OGRN 1027700000000; INN 7700000000; KPP 770001001", []),
        ("Ukraine, EDRPOU 12345678", []),
        ("GBP 12345678", []),
        ("New England office 12345678", []),
        ("UK office; Tax ID 12345678", []),
        ("UK Company Number 1234567", []),  # seven digits are not taken from free text
        ("UK Company Number 123456789", []),
        ("UK Company Number 01234567 and 07654321", ["01234567"]),
        ("", []),
        (None, []),
    ],
)
def test_uk_company_numbers(text: str | None, expected: list[str]) -> None:
    assert uk_company_numbers(text) == expected


def test_un_references_and_ids() -> None:
    assert un_references(["QDi.123", " qdi.123. ", None, "KPe.001"]) == ["KPE.001", "QDI.123"]
    first = sanction_id("uksl", "uksl-g101", "SYN0001")
    assert first == sanction_id("uksl", "uksl-g101", "SYN0001")
    assert first != sanction_id("uksl", "uksl-g101", "SYN0002")
    assert first.startswith("uksl-sanction-")
    assert len(first) == len("uksl-sanction-") + 20


def test_check_bounds() -> None:
    bounds = {"eu_fsf": {"Person": [3400, 8000], "Organization": [970, 2300]}}
    assert check_bounds("eu_fsf", {"Person": 4398, "Organization": 1728}, bounds) == []
    problems = check_bounds("eu_fsf", {"Person": 12}, bounds)
    assert problems == [
        "unexpected size for eu_fsf: Organization 0, expected 970 to 2300; "
        "the format may have changed",
        "unexpected size for eu_fsf: Person 12, expected 3400 to 8000; the format may have changed",
    ]
    assert check_bounds("us_ofac_sdn", {"Person": 1}, bounds) == []
```

#### M2.6b OFAC SDN List (advanced XML)

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.6a |
| Branch | `p2/m2-6b-ofac` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | Yes |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset us_ofac_sdn && uv run neonradar ingest build --profile uk-tiny --dataset us_ofac_sdn` |

**Goal.** The SDN List from OFAC's advanced format, which keeps name parts, weak aliases, identity documents and the typed relationships between designated parties (note 2.1).

**Deliverables.**

1. `us_ofac.py`, `SourceSpec`: `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML` (about 122 MB). The consolidated non-SDN file uses the same format; it is a later dataset (`us_ofac_cons`), not Phase 2.
2. **Two streaming passes** (note 2.4: `SanctionsEntries` and `ProfileRelationships` come after `DistinctParties`). Pass 1 keeps only the small tables: every `ReferenceValueSets` table as `{set name: {ID: value}}` (with `PartySubType` to `PartyType` links), `Locations` by ID, `IDRegDocuments` by `IdentityID`, `SanctionsEntries` by `ProfileID`, and `ProfileRelationships`. Pass 2 streams `DistinctParty` elements and writes records one at a time. Peak memory stays under 1 GB: a test generates the fixture with 200 and with 2,000 parties and checks that the `tracemalloc` peak of pass 2 grows by less than a factor of 2 (pass 2 keeps no parties).
3. **Schema** from the profile's `PartySubTypeID`, through its `PartyType` when the subtype is `Unknown` (note 2.9): `Individual` to `Person`, `Entity` to `Organization`; `Vessel` and `Aircraft` skipped.
4. **Names.** Each `Alias` has an `AliasTypeID` (`Name`, `A.K.A.`, `F.K.A.`, `N.K.A.`), `@Primary` and `@LowQuality`. A name is built per `DocumentedName` from its parts, typed through `NamePartGroups`: Person `join_name([First Name, Middle Name, Patronymic, Matronymic, Last Name])`, with `firstName`, `middleName`, `fatherName`, `motherName`, `lastName` from the primary Latin name; Organization the `Entity Name` part. The primary alias in Latin script (`ScriptID` whose value is Latin) is `name`; other scripts go to `alias`; `F.K.A.` to `previousName`; other aliases to `alias`; any alias with `LowQuality="true"` to `weakAlias`. `Maiden Name` and `Nickname` are name part types (note 2.6), not alias types: a maiden name is left out of the joined name and gives its own `alias` (`join_name([First Name, Middle Name, Maiden Name])`), and a nickname gives a `weakAlias`.
5. **Features** (`FeatureTypeID`): `Birthdate` to `birthDate` with `common.period_dates(start, end)`, where `start` is the `DatePeriod`'s `Start/From` and `end` its `End/To` as (year, month, day), a missing part `None`; when `Start` or `End` is marked `Approximate`, only the years are kept (`common.year_range` of the two years); `Place of Birth` to `birthPlace`; `Nationality Country` to `nationality`; `Citizenship Country` to `citizenship`; `Gender` to `gender`; `Location` to `address` and `country` (location parts joined with ", " in the order `ADDRESS1`, `ADDRESS2`, `ADDRESS3`, `CITY`, `STATE/PROVINCE`, `REGION`, `POSTAL CODE`, then the country); `Organization Established Date` to `incorporationDate`. Every other feature type is counted by its name (values never logged).
6. **Identity documents** of the profile's identity, skipping any whose validity is `Fraudulent`: `Passport` and `Diplomatic Passport` to `passportNumber`; `National ID No.`, `Identification Number` and `Cedula No.` to `idNumber`; `UK Company Number` to `registrationNumber` through `neonradar_keys.ids.uk_company_number` (Companies House forms only; others counted) with `jurisdiction: gb`; `Company Number`, `Registration Number`, `Registration ID`, `Business Registration Number`, `Commercial Registry Number` and `Certificate of Incorporation Number` the same, but only when the issuing country is the United Kingdom; `Legal Entity Number` and `LE Number` to `leiCode` when `is_valid_lei`. Other document types are counted by type name.
7. **Sanctions**, one per `SanctionsEntry`: `sanction_id("ofac", party_id, entry ID)`; `authorityId` the party's `FixedRef` (the SDN UID, note 2.4); `program` the comments of the entry's measures whose type is `Program`; `provisions` the other measure types; `startDate` the earliest `EntryEvent` date (OpenSanctions does not read it; NeonRadar does, note 2.9); `sourceUrl` `https://sanctionssearch.ofac.treas.gov/Details.aspx?id=<FixedRef>`. Party id `ofac-<FixedRef>`, `nr.source_ref` the FixedRef, the same `sourceUrl`.
8. **Relationships** (`ProfileRelationship`, From and To profile ids; relationship id `ofac-<schema in lower case>-<first 20 hex of sha1 of from, to, relation type>`; `role` or `relationship` the raw relation type; `@Former="true"` sets `status: former`, or appends " (former)" to `relationship` for `Associate` and `Family`):

   | Relation type | FtM | From is | To is |
   |---|---|---|---|
   | `Owned or Controlled By` | `Control` | `controlled` | `controller` |
   | `Owns, controls, or operates` | `Control` | `controller` | `controlled` |
   | `Property in the interest of` | `Control` | `controlled` | `controller` |
   | `Acting for or on behalf of` | `Representation` | `agent` | `client` |
   | `Leader or official of`, `Principal Executive Officer` | `Directorship` | `director` | `organization` |
   | `playing a significant role in` | `Membership` | `member` | `organization` |
   | `Associate Of` | `Associate` (both persons, else `UnknownLink`) | `person` | `associate` |
   | `Family member of` | `Family` (both persons, else `UnknownLink`) | `person` | `relative` |
   | `Providing support to` and any other value | `UnknownLink` | `subject` | `object` |

   None of these becomes `Ownership`: OFAC's relation types give no share and do not say whether a link is ownership or control, so the ownership view must not treat them as shares (FAQ 398: the 50 Percent Rule "speaks only to ownership and not to control", note 2.8). For `Control`, `Directorship` and `Membership`, if the controlled or organisation end is a Person and the other end is not, swap the ends and count `relationships_flipped` (note 2.9); if both are persons, use `UnknownLink`.
9. Tests (fixture `sdn_advanced.xml`, written to the official XSD, which the agent downloads once from `http://www.treasury.gov/ofac/downloads/sanctions/1.0/sdn_advanced.xsd` and commits, M2.6 rule 11): reference-value lookups; a person with name parts in Latin and Arabic script; a maiden name and a nickname; a weak alias; an entity with a `UK Company Number` (`99` plus six digits) and an LEI, and one whose `UK Company Number` has a prefix Companies House does not use (counted); a vessel skipped; birth dates as an exact date, a whole year, a two-year range and an approximate date; a fraudulent passport skipped; every row of the relationship table, including a flipped one; namespace-agnostic parsing of the same fixture under both namespaces in note 2.4; the memory check of deliverable 2; the bounds check; the gate (M2.6 rule 2).

**Acceptance.** `uv run pytest ingest/tests/test_lists_us_ofac_sdn.py -q`; `uv run pytest ingest/tests/test_lists_us_ofac_sdn.py -k gate -q`; `make check`.

**Review focus (humans).** Graph mentor: do the relationship directions read correctly ("A owned or controlled by B" gives B controls A)? Data steward: are any feature types you would not want loaded in the "counted" list, or loaded when they should not be?

#### M2.6c UN Security Council Consolidated List

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.6a |
| Branch | `p2/m2-6c-un` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source` (`real-data-run` only if `un_sc_sanctions` is in `access.sanctions_lists`) |
| Plan first | No |
| Real-data run | only with written UN permission (3.3): `uv run neonradar data fetch --profile uk-tiny --dataset un_sc_sanctions && uv run neonradar ingest build --profile uk-tiny --dataset un_sc_sanctions` |

**Goal.** The loader is built and tested whether or not the UN list may be used; it runs only if the data steward has written permission (the UN website terms allow "personal, non-commercial use", note 3.5). Without it, the UK and EU lists still carry the UN listings. D4 links records of two loaded lists that carry the same UN reference number: the UK list gives it, but the EU field was empty in every record the note read (note 6), so with the UN list off D4 may link little or nothing, and UK and EU entries for one UN listing usually meet only through the probabilistic models (7.1.4).

**Deliverables.**

1. `un_sc.py`, `SourceSpec`: `https://scsanctions.un.org/resources/xml/en/consolidated.xml`, following the 302 redirect to the signed storage URL, which is never stored or logged (M2.6 rule 4).
2. **Mapping** (`INDIVIDUALS/INDIVIDUAL` to `Person`, `ENTITIES/ENTITY` to `Organization`; the value `na` means "not available" and is treated as missing, note 3.3):

   | XML | FtM | Rule |
   |---|---|---|
   | `FIRST_NAME` to `FOURTH_NAME` | `name`, `firstName`, `lastName` | Person: `join_name` of the four; `firstName` the first, `lastName` the last non-empty one; Organization: `FIRST_NAME` |
   | `NAME_ORIGINAL_SCRIPT` | `alias` | |
   | `INDIVIDUAL_ALIAS`, `ENTITY_ALIAS` | `alias` or `weakAlias` | `QUALITY` `Good` to `alias`, `Low` to `weakAlias`, empty as in M2.6a; `ALIAS_NAME` split on "; " |
   | `INDIVIDUAL_DATE_OF_BIRTH` | `birthDate` | `TYPE_OF_DATE` `EXACT`: `parse_iso(DATE)`; `APPROXIMATELY`: `partial_date(YEAR)`; `BETWEEN`: `year_range(FROM_YEAR, TO_YEAR)`, every year of a range of at most 20 years and none for a wider one (dates may carry an offset such as `-04:00`, note 3.4) |
   | `INDIVIDUAL_PLACE_OF_BIRTH` | `birthPlace`, `birthCountry` | city and state joined; country through `country_code` |
   | `NATIONALITY/VALUE` | `nationality` | through `country_code`; free text such as "Possibly ..." is counted |
   | `GENDER`, `TITLE/VALUE`, `DESIGNATION/VALUE` | `gender`, `title`, `position` | titles and designations only with `keep_positions` (M2.6 rule 7) |
   | `INDIVIDUAL_DOCUMENT` | `passportNumber`, `idNumber` | `TYPE_OF_DOCUMENT` `Passport`, `Numéro de passeport` or `Número de pasaporte` to `passportNumber`; `National Identification Number` and its French and Spanish forms to `idNumber`; others counted |
   | `INDIVIDUAL_ADDRESS`, `ENTITY_ADDRESS` | `address`, `country` | as in M2.6a |

3. **Sanctions**, one per entry: `sanction_id("unsc", party_id, REFERENCE_NUMBER)`; `authorityId` `DATAID`; `unscId` `REFERENCE_NUMBER`; `program` `UN_LIST_TYPE`; `startDate` and `listingDate` `parse_iso(LISTED_ON)`; `modifiedAt` the latest `LAST_DAY_UPDATED/VALUE`; `reason` `COMMENTS1` only with `keep_reasons`. Party id `unsc-<un_reference(REFERENCE_NUMBER)>`, `nr.source_ref` the reference number.
4. Tests (fixture `consolidated.xml` with two individuals and one entity in the invented `ZZ` regime): every mapping row; the three date types, an offset and a `BETWEEN` range wider than 20 years (no birth date); `na` values; `keep_positions` off and on; the redirect followed and its query string absent from `download.json` and the logs (mocked transport); the gate (M2.6 rule 2, with `un_sc_sanctions` left out of the test project's `access.sanctions_lists`).

**Acceptance.** `uv run pytest ingest/tests/test_lists_un_sc_sanctions.py -q`; `uv run pytest ingest/tests/test_lists_un_sc_sanctions.py -k gate -q`; `make check`.

**Review focus (humans).** Data steward: is the permission evidence in `docs/data/licences/un_sc_sanctions.md` before anyone adds the list to `access.sanctions_lists`?

#### M2.6d EU Financial Sanctions Files

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward reviews) |
| Depends on | M2.6a |
| Branch | `p2/m2-6d-eu` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | No |
| Real-data run | `uv run neonradar data fetch --profile uk-tiny --dataset eu_fsf && uv run neonradar ingest build --profile uk-tiny --dataset eu_fsf` |

**Goal.** The EU consolidated financial sanctions list from the Commission's XML 1.1 file, which keeps alias strength (the CSV does not, note 4.4).

**Deliverables.**

1. `eu_fsf.py`, `SourceSpec`: `https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=<token>`, the token from `NR_EU_FSF_TOKEN` in `.env` (default `dG9rZW4tMjAxNw`, the public token, note 4.1). The server builds the file on request: read timeout 300 seconds, up to five retries on HTTP 500 with backoff factor 3.
2. **Mapping** (`sanctionEntity`; `subjectType@code` `person` to `Person`, `enterprise` to `Organization`, anything else skipped and counted):

   | XML | FtM | Rule |
   |---|---|---|
   | `nameAlias@wholeName` | `name`, `alias`, `weakAlias` | `strong="false"` to `weakAlias`; of the strong ones, the first with no `nameLanguage` or `EN` is `name`, the rest `alias`; `firstName`, `middleName`, `lastName` from the chosen name's attributes |
   | `nameAlias@gender`, `@title`, `@function` | `gender`, `title`, `position` | `M`, `F` to `male`, `female`; title and function only with `keep_positions` (M2.6 rule 7) |
   | `citizenship@countryIso2Code` | `nationality` | lower-cased, accepted only if FollowTheMoney's country type accepts it; others counted |
   | `birthdate` | `birthDate`, `birthPlace`, `birthCountry` | `@birthdate` through `parse_iso`; else `partial_date(@year, @monthOfYear, @dayOfMonth)`; else `year_range(@yearRangeFrom, @yearRangeTo)` (at most 20 years, else none); with `@circa="true"` keep the year only; place from `@city` or `@place`; country from `@countryIso2Code` |
   | `identification` | `passportNumber`, `idNumber`, `registrationNumber` | skip when `@knownFalse="true"`; `passport` to `passportNumber`, `id` to `idNumber` (`@number`, else `@latinNumber`); `regnumber` with `@countryIso2Code="GB"` through `uk_company_number` (Companies House forms only) with `jurisdiction: gb`; other codes counted |
   | `address` | `address`, `country` | street, PO box, city, zip code, region and place joined; `@countryIso2Code` |

3. **Sanctions**, one per `regulation`: `sanction_id("eufsf", party_id, regulation@logicalId)`; `authorityId` `@euReferenceNumber` (else the entity `@logicalId`); `unscId` `@unitedNationId`; `program` `regulation@programme`; `programId` `regulation@numberTitle`; `startDate` the earlier of `sanctionEntity@designationDate` and `regulation@entryIntoForceDate`; `listingDate` `regulation@publicationDate`; `sourceUrl` `publicationUrl`; `reason` the entity `remark` only with `keep_reasons`. Party id `eufsf-<logicalId>`, `nr.source_ref` the logical id.
4. Tests (fixture `eu-fsf-1-1.xml` with a person under two regulations, a weak alias, a circa birth year, a false passport, a GB registration number (`99` plus six digits), and an entity with a subject type to skip): every mapping row; `keep_positions` off and on; the token taken from the environment and absent from `download.json`, the manifests, the summary and the logs; retries on 500 (mocked transport); the fill rate of `unscId` reported (the note saw it empty in every record read, note 6); the gate (M2.6 rule 2).

**Acceptance.** `uv run pytest ingest/tests/test_lists_eu_fsf.py -q`; `uv run pytest ingest/tests/test_lists_eu_fsf.py -k gate -q`; `make check`.

**Review focus (humans).** Data steward: the attribution line in `contracts/datasets.yaml` names the Commission and the reuse decision (3.3) and says the records were converted by NeonRadar; is it on every place NeonRadar shows EU data?

#### M2.6e UK Parliament members as a PEP source (optional)

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (data steward and project lead review) |
| Depends on | M2.6a, M2.6b, M2.6c, M2.6d |
| Branch | `p2/m2-6e-parliament` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source`, `real-data-run` |
| Plan first | Yes |
| Real-data run | only if `gb_parliament_members` is in `access.pep_sources`: `uv run neonradar ingest build --profile uk-tiny --dataset gb_parliament_members` |

**Goal.** A free, openly licensed PEP source without OpenSanctions: current members of both Houses and ministers, and those who left office within `access.pep_former_months` (default 12), from the UK Parliament Members API under the Open Parliament Licence (note 7.2). Members of either House are politically exposed persons while in office (MLR 2017 regulation 35(14)(b)); regulation 35(9) asks firms to keep enhanced measures for at least 12 months after a person leaves office, and for a domestic PEP the starting point is a lower level of risk (regulation 35(3A)) (note 7.1). So `role.pep` goes only on a person whose membership or government post the source shows as current, or as ended within the period; a former member outside it is not loaded, and no PEP flag is inferred for anyone else (G8). The milestone runs after the M2.6a to M2.6d pull requests are merged (header); if time runs out, it moves to Phase 3 without blocking Gate 2.

**What it does not do.** The API gives no birth dates, so PEP records will rarely reach the candidate threshold: they appear as their own nodes, found by search, with the `:PEP` flag from their own records. Name screening against PEPs is a Phase 3 topic. Family members and close associates are not loaded (note 7.3).

**Deliverables.**

1. `ingest/src/neonradar_ingest/sources/parliament/members.py`: an API source (no bulk file; the crawl runs in the builder, like the officers step of M2.3c, and `data fetch` has nothing to download for this dataset and says so) using the shared HTTP client, a request budget, a 2-requests-per-second limit, and a response cache in `data/cache/real/api/gb_parliament_members/` (kept for `cache_days`). Read `https://members-api.parliament.uk/swagger/v1/swagger.json` first for the exact parameter names and values (it holds no personal data); stop and ask if they differ from note 7.2.
2. **Members**: first the real-data gate (M2.2), whose first check is that `gb_parliament_members` is in `access.pep_sources`; it exits 3 before any request. Then `GET /api/Members/Search` for each House (`House` 1 for the Commons and 2 for the Lords, if the swagger file agrees), members on or after the date `access.pep_former_months` months before today (`MembershipInDateRange.WasMemberOnOrAfter`), `take=20` (the API caps it, note 7.2), `skip` advanced by the items returned until `totalResults`. Then `GET /api/Members/{id}/Biography` for each member for `governmentPosts`.
3. **Records** (dataset `gb_parliament_members`, prefix `ukparl`):
   - `Person` `ukparl-<member id>`, only for a member whose membership of a House or government post is current or ended within `access.pep_former_months` (others are counted, not loaded): `name` from `nameDisplayAs`, `alias` from `nameListAs`, `country: gb`, `topics: ["role.pep"]`, `sourceUrl` `https://members.parliament.uk/member/<id>`, `nr.source_ref` the member id. `nameFullTitle` (honours and styles are not names) and `gender` (matching does not use it) are not loaded.
   - `Position`: `ukparl-pos-commons` ("Member of the House of Commons") and `ukparl-pos-lords` ("Member of the House of Lords") with topics `gov.national` and `gov.legislative`; `ukparl-pos-gov-<post id>` for each government post, with `gov.national` and `gov.executive`; `country: gb`.
   - `Occupancy` `ukparl-occupancy-<first 20 hex of sha1 of member id, post id, start date>`, for the memberships and posts that are current or ended within the period: `holder`, `post`, `startDate`, `endDate`, `status` `current` when there is no end date, else `ended`.
   Opposition posts, committee memberships, constituencies, parties, registered interests and photographs are not loaded.
4. Profile block: `enabled`, `houses` (`[commons, lords]`), `request_budget` (default 3,000), `cache_days` (default 30); unknown keys fail. The period is the project's `access.pep_former_months` (1.3), a data steward and project lead decision, not a profile setting.
5. C1 entry `gb_parliament_members` (5.1) and the gate of deliverable 2.
6. `docs/data/sources/gb_parliament_members.md`: the scope, the licence and its attribution line, what is not loaded, and the wording rule in 7.2 for PEP flags.
7. Tests on recorded synthetic responses (invented members and posts): the gate (`-k gate`: `NR_PROJECT_FILE` points at a temporary project with `access.pep_sources: []`; exit 3 and no request on the mock transport); paging until `totalResults`; the request budget stopping the run with partial output kept and reported; records and occupancies; with `pep_former_months` 12, a former member who left 11 months ago is loaded with `role.pep` and a former member who left more than 12 months ago is not loaded; no `gender`; the cache.

**Acceptance.** `uv run pytest ingest/tests/test_parliament_*.py -q`; `uv run pytest ingest/tests/test_parliament_members.py -k gate -q`; `make check`.

**Review focus (humans).** Data steward and project lead: is `access.pep_former_months` a policy you can explain? Is the attribution line ("Contains Parliamentary information licensed under the Open Parliament Licence v3.0.") shown wherever PEP flags from this source appear?

### M2.7 OpenSanctions loader (only where `access.opensanctions` allows it)

| | |
|---|---|
| Squad, human owner | Ingestion; data steward |
| Depends on | M2.1a, M2.2 |
| Branch | `p2/m2-7-opensanctions` |
| Labels | `agent`, `phase-2`, `squad:ingest`, `data-source` (`needs-human-decision` while blocked) |
| Plan first | No |
| Real-data run | only when `access.opensanctions` is `licensed` or `exempt`, and after a pull request approved by the data steward sets `opensanctions_default: { enabled: true }` in the profile (7.8 ships it disabled): `uv run neonradar data fetch --profile uk-sample --dataset opensanctions_default && uv run neonradar ingest build --profile uk-sample --dataset opensanctions_default` |

**Goal.** If the organisation obtains a licence or qualifies for the free programme, OpenSanctions plugs in like any other list. If not, the code is ready and tested, and nothing runs.

**Deliverables.**

1. `ingest/src/neonradar_ingest/sources/opensanctions/bulk.py`: a `SourceSpec` for `https://data.opensanctions.org/datasets/latest/<collection>/index.json` (follow the 307 redirect; read the version and the `entities.ftm.json` resource URL and checksum from the index) and a `Builder` that streams `entities.ftm.json` line by line with `followthemoney.ValueEntity.from_dict`, keeps the schemata allowed in C1, re-ids every entity and every entity reference with the prefix `os-` (Phase 1 form), sets `datasets: ["opensanctions_default"]`, and keeps `topics` as published, except as item 2 says. Skipped schemata are counted. Profile block: `collection` (`sanctions` by default, `default` for everything), and `enabled`.
2. **PEP data only by decision.** When `opensanctions_default` is not in `access.pep_sources`:
   - every `role.*` topic is removed from every entity (a sanctioned person who is also a PEP keeps `sanction` and loses `role.pep`);
   - `Position` and `Occupancy` entities are skipped;
   - an entity whose only non-descriptive topics (7.1.1) were `role.*` topics is skipped, because it was in the data only as a PEP; entities that never had a non-descriptive topic (for example an associated company) stay;
   - relationships whose ends were skipped are dropped.
   Each of these is counted in the summary. So no PEP flag reaches the graph without the data steward's PEP decision.
3. The real-data gate of M2.2 runs first; its dataset rule for this source refuses with exit code 3 and the Phase 1 message unless `access.opensanctions` is `licensed` or `exempt` (an `evaluation` agreement covers the Phase 1 spike only).
4. Tests on a synthetic FtM fixture shaped like `entities.ftm.json` (the M1.8d fixture extended with a `Vessel`, a PEP-only person, a sanctioned person who is also a PEP, a `Position` with an `Occupancy`, a sanctioned company and an associated company without topics): re-id of entities and references; schema skipping; with `opensanctions_default` in `access.pep_sources`, topics kept exactly; without it, `role.*` removed from the sanctioned PEP, the PEP-only person, the `Position` and the `Occupancy` skipped, the associated company kept, the dropped relationships counted; the gate (`-k gate`: `NR_PROJECT_FILE` points at a project file that allows the profile and the machine but has `access.opensanctions: none`; exit 3 with the OpenSanctions message and no request on the mock transport).

**Acceptance.**

```bash
uv run pytest ingest/tests/test_opensanctions_*.py -q
uv run pytest ingest/tests/test_opensanctions_bulk.py -k gate -q   # exit 3 for the licence rule, no request
make check
```

**Review focus (humans).** Data steward: is the licence evidence in `docs/data/licences/opensanctions.md` what the run relies on? Does the summary of a run without the PEP decision show `role.*` topics removed and PEP-only entities skipped? Never merge a graph built with OpenSanctions data into anything published (G7).

### M2.8 Matching keys (`neonradar_keys`)

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (an Arabic reader and a Russian reader review the tests, if the team has them) |
| Depends on | M2.0 |
| Branch | `p2/m2-8-keys` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | No |
| Size | exception (the reference implementation and its tests are verbatim from this spec) |
| Real-data run | none |

**Goal.** One implementation of every normalisation that matching depends on: person and organisation name keys across Latin, Arabic and Cyrillic scripts, UK postcodes and addresses, countries and nationalities, and the identifiers of the deterministic rules. The loaders, the resolver and the graph loader all call it, so a key means the same thing everywhere.

**Why it is given verbatim.** Every expected value in the tests was produced by running this code on 18 October 2026 with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 and anyascii 0.3.3 (`docs/research/2026-10-18/names-addresses.md`, sections 3 to 10). The libraries alone get several of these wrong: rigour does not unify alef forms, ta marbuta, alef maqsura or hamza carriers and never transliterates Arabic; ICU's transliteration garbles unvocalised Arabic; rigour's Cyrillic ASCII loses digraphs ("Serbakov" for Щербаков) where anyascii keeps them; `normality.ascii_text` turns modifier-letter apostrophes into "?" (note 3, 12). Do not "simplify" a rule without a failing test that shows why.

**Deliverables.**

1. The modules below, verbatim, in `keys/src/neonradar_keys/`:

   | Module | Public functions | Note sections |
   |---|---|---|
   | `text.py` | `nfkc`, `scripts`, `latin_token` | 2.2, 3.3 |
   | `arabic.py` | `ar_normalize`, `arabic_rules`, `arabic_skeleton`; `HONORIFICS`, `NASAB` | 5.3, 5.5 |
   | `latin.py` | `latin_rules`, `latin_skeleton`, `joined_article_root`; `HONORIFICS` | 3.2, 5.4 |
   | `symbols.py` | `arabic_symbols` (QIDs of name groups for Arabic tokens) | 4 |
   | `names.py` | `person_key(name, given=None, family=None) -> PersonKey`, `org_key(name) -> OrgKey`, `split_ch_name`, `name_similarity`, `latin_forms` | 3, 4, 5 |
   | `postcodes.py` | `normalise_uk_postcode`, `find_uk_postcode`, `postcode_parts` | 7 |
   | `addresses.py` | `address_key(text)` (`"POSTCODE\|TOKENS"`, `"NOPC\|TOKENS"` or None), `address_key_from_parts(parts)` | 8 |
   | `companies_house.py` | `ch_same_as_key` (the "same as" name rules of SI 2015/17, approximate) | 10 |
   | `countries.py` | `country_code(value)` (names, demonyms and codes; UK nations to `gb`) | 9 |
   | `ids.py` | `uk_company_number(value, *, synthetic=False)` (Companies House forms only; the synthetic prefix `SY` only with `synthetic=True`), `CH_PREFIXES` (the 36 prefixes of note 2.6), `SYNTHETIC_PREFIX`, `has_ch_prefix`, `is_valid_lei`, `un_reference` | 7.1.2; `bulk-sources-loading.md` 2.6 |

2. **Data files** in `keys/src/neonradar_keys/data/`: `nationalities.csv` verbatim below (Companies House nationality values and FCDO citizen names mapped to ISO codes, with the overrides in `build_nationalities.py`); `ar_symbols.json.gz`, generated by running `uv run python keys/scripts/build_ar_symbol_index.py --tag v2.5.0 --sha256 be47a435969da3fa7311d8c682e462d6d20e6cf27cf90ad1473ce213c9a91c79` (it downloads `person_names.txt` from `raw.githubusercontent.com/opensanctions/rigour` at the tag that matches the rigour pin, an allowed domain (G3), checks the SHA-256, and writes 17,798 keys; the gzip header carries no timestamp, so a rebuild gives the same file, SHA-256 `7712414a8eb9b07cf7e2814ffd8d1460ae1c35a834a17a5ce39099f41f56f7e8`). Commit the generated file. Rebuild it whenever the installed rigour version changes, and bump `RULES_VERSION`: the pin `rigour==2.5.*` (3.1) allows patch releases, so `test_symbol_index_matches_installed_rigour` fails when the lock moves rigour away from the index's tag.
3. `keys/scripts/build_ar_symbol_index.py` and `keys/scripts/build_nationalities.py`, verbatim. The second needs two Open Government Licence inputs that are not in the repository; it documents how `nationalities.csv` was made and is run only when those lists change.
4. `keys/tests/test_keys.py`, verbatim (105 tests). Add `"keys/**" = ["RUF001", "RUF002", "RUF003"]` to the root ruff `per-file-ignores`: the Arabic and Cyrillic strings are deliberate, and those rules would flag their letters as look-alikes.
5. **Dependencies.** Add `typing-extensions>=4.12` to `keys`' dependencies besides `rigour`, `normality` and `anyascii`: rigour 2.5.0 imports it (`rigour/ids/__init__.py`, used by `is_valid_lei`) without declaring it, and the wheel must install on its own (checked 18 October 2026; in the workspace pydantic happens to supply it).
6. **Notices.** Two sections in `THIRD_PARTY_NOTICES.md` (M2.0): `keys/src/neonradar_keys/data/ar_symbols.json.gz`, built from rigour's `rust/data/names/person_names.txt` (MIT License, "Copyright (c) 2023-2025: OpenSanctions Datenbanken GmbH", with the full licence text; the name data comes from Wikidata, CC0); and `keys/src/neonradar_keys/data/nationalities.csv`, derived from the Companies House list of nationalities and the FCDO Geographical Names Index (both Open Government Licence v3.0: "Contains public sector information licensed under the Open Government Licence v3.0.").
7. `keys/CLAUDE.md` (at most 20 lines): pure functions, no I/O apart from the two packaged data files; every output change needs a test and a `RULES_VERSION` bump; never call fuzzy country lookups; `uk_company_number` accepts only Companies House forms, and `SY` only for synthetic records; rebuild the symbol index when rigour moves; the reasons above for not simplifying.
8. `docs/er/keys.md`: what each key is for, with the examples from the tests, and the known limits (Arabic is matched through normalisation, skeletons and Wikidata name groups, not by transliteration; names in scripts other than Latin, Arabic and Cyrillic get only anyascii folding; a company number with a prefix outside note 2.6's list is not a UK company number).

**Acceptance.**

```bash
uv run pytest keys/tests -q                      # 106 passed: test_keys.py (105) and the version test (M2.0)
uv run mypy                                      # keys/src is in mypy's files (M2.0)
KEYS_DIST="$(mktemp -d)" && uv build --package neonradar-keys --out-dir "$KEYS_DIST"
python3 -m zipfile -l "$KEYS_DIST"/neonradar_keys-*.whl | grep -c -E 'nationalities\.csv|ar_symbols\.json\.gz'   # 2
make check
```

**Review focus (humans).** Graph mentor: read the parametrised cases in `test_keys.py` and add the hard cases you know from real lists as new failing tests (synthetic names only), not as code changes. Arabic and Russian readers, if the team has them: do the normalised forms in the tests read as the same name?

**`keys/src/neonradar_keys/__init__.py`**:

```python
"""Matching keys for NeonRadar entity resolution (PHASE-2.md M2.8). Pure functions, no I/O."""

__version__ = "0.1.0"
# Bump RULES_VERSION whenever a function's output changes; persisted keys record it.
RULES_VERSION = "1"
```

**`keys/src/neonradar_keys/text.py`**:

```python
"""Script detection and Latin folding of single tokens."""

from __future__ import annotations

import re
import unicodedata

from anyascii import anyascii
from normality import ascii_text
from rigour.text.scripts import text_scripts

# Modifier letters and quotes that normality.ascii_text turns into "?" (research note 12).
_APOSTROPHES = re.compile("[\u02bb-\u02bf\u2018\u2019\u0060\u00b4]")


def nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def scripts(text: str) -> set[str]:
    """Unicode scripts of the letters and digits in the text (for example {"Latin", "Arabic"})."""
    return set(text_scripts(text))


def latin_token(token: str) -> str:
    """Lower-case ASCII form of one token: ICU folding for Latin, anyascii for other scripts."""
    token = _APOSTROPHES.sub("", token)
    found = scripts(token)
    if found <= {"Latin"}:
        return ascii_text(token).lower().replace("?", "")
    return anyascii(token).lower()
```

**`keys/src/neonradar_keys/arabic.py`**:

```python
"""Arabic-script name rules (research note names-addresses.md 5.3 to 5.5, credited to the
character rules of CAMeL Tools, MIT)."""

from __future__ import annotations

import re

from neonradar_keys.text import nfkc

# Tashkeel, shadda, sukun, superscript alef and Quranic marks (research note 5.3, step 2).
_MARKS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06dc\u06df-\u06e8\u06ea-\u06ed\u08d3-\u08ff]"
)
_MAP = str.maketrans(
    {
        **dict.fromkeys("آأإٱٲٳ", "ا"),  # alef forms
        **dict.fromkeys("ىیےئ", "ي"),  # alef maqsura, Farsi yeh, yeh barree, yeh with hamza
        "ة": "ه",  # ta marbuta
        "ؤ": "و",  # waw with hamza
        "ک": "ك",  # keheh
        **dict.fromkeys("ءـ", None),  # hamza, tatweel
        **dict.fromkeys(
            "\u200c\u200d\u200e\u200f\u061c", None
        ),  # zero-width joiners and direction marks
        **{chr(0x0660 + i): str(i) for i in range(10)},
        **{chr(0x06F0 + i): str(i) for i in range(10)},
    }
)
ARTICLE_EXCEPTIONS = frozenset({"الله", "الهام", "الياس", "اليسع"})
HONORIFICS = frozenset(
    {
        "الشيخ",
        "شيخ",
        "الشيخه",
        "الحاج",
        "حاج",
        "الحاجه",
        "الدكتور",
        "الدكتوره",
        "د",
        "المهندس",
        "المهندسه",
        "الاستاذ",
        "الاستاذه",
    }
)
NASAB = frozenset({"بن", "ابن", "بنت"})
_SKELETON = {
    "ب": "b",
    "ت": "t",
    "ث": "t",
    "ج": "j",
    "ح": "h",
    "خ": "k",
    "د": "d",
    "ذ": "d",
    "ر": "r",
    "ز": "z",
    "س": "s",
    "ش": "s",
    "ص": "s",
    "ض": "d",
    "ط": "t",
    "ظ": "z",
    "ع": "",
    "غ": "g",
    "ف": "f",
    "ق": "k",
    "ك": "k",
    "ل": "l",
    "م": "m",
    "ن": "n",
    "ه": "h",
    "و": "",
    "ي": "",
    "ا": "",
    "پ": "b",
    "چ": "j",
    "گ": "g",
    "ڤ": "f",
}


def ar_normalize(text: str) -> str:
    """NFKC; marks and tatweel removed; alef, yeh, heh and waw forms unified."""
    return _MARKS.sub("", nfkc(text)).translate(_MAP)


def arabic_rules(tokens: list[str]) -> list[str]:
    """Token rules for casefolded Arabic tokens (article detection needs the raw form)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        raw = tokens[i]
        token = ar_normalize(raw)
        following = tokens[i + 1] if i + 1 < len(tokens) else None
        if token in ("عبد", "ابو") and following is not None:
            out.append(token + ar_normalize(following))  # same key as the joined spelling
            i += 2
            continue
        if token in NASAB and i > 0:
            i += 1
            continue
        out.append(_strip_article(raw))
        i += 1
    return [t for t in out if t]


def _strip_article(raw: str) -> str:
    token = ar_normalize(raw)
    starts = raw.startswith("ال") or raw.startswith("ٱل")
    if starts and len(token) - 2 >= 3 and token not in ARTICLE_EXCEPTIONS:
        return token[2:]
    return token


def arabic_skeleton(token: str) -> str:
    """Consonant skeleton of a normalised Arabic token, comparable with latin.latin_skeleton."""
    if token.startswith("عبدال") and len(token) > 5:
        token = "عبد" + token[5:]
    skeleton = "".join(_SKELETON.get(c, "") for c in token)
    if skeleton.endswith("h") and token.endswith("ه"):
        skeleton = skeleton[:-1]
    return re.sub(r"(.)\1+", r"\1", skeleton)
```

**`keys/src/neonradar_keys/latin.py`**:

```python
"""Latin-side rules for Arabic-origin names and consonant skeletons (research note 5.4, 5.5)."""

from __future__ import annotations

import re


def _words(*parts: str) -> frozenset[str]:
    return frozenset(" ".join(parts).split())


ARTICLES = _words("al el ul ar ur as us ash ush at ut ad ud az uz an un")
NASAB = _words("bin ibn bint binti binte ben ould wuld")
HONORIFICS = _words("sheikh shaikh shaykh sheik haji hajji hajj alhaji alhaj haj")
_ABD = _words(
    "abd abdu abdul abdel abdal abdol abdil abdur abdar abdus abdas abdush abdash abdun abdan ",
    "abdud abdad abdut abdat abduz abdaz",
)
_ABD_JOINED = re.compile(
    r"^abd(?:ul|ol|el|al|il|ur|ar|us|as|ush|ash|ud|ad|ut|at|uz|az|un|an|u|e|a|o)?([a-z]{3,})$"
)
_ALLAH = _words("allah ullah ulla alla lah llah olah ollah ullahi")
_JOINED_ARTICLE = re.compile(r"^(?:al|el)([a-z]{3,})$")


def _abd(root: str) -> str:
    return "abdallah" if root in _ALLAH else "abd" + root


def latin_rules(tokens: list[str]) -> list[str]:
    """Join Abd and Abu compounds, drop articles and nasab particles (not as the first token)."""
    out: list[str] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        has_next = i + 1 < len(tokens)
        if token in _ABD and has_next:
            j = i + 1
            if tokens[j] in ARTICLES and j + 1 < len(tokens):
                j += 1
            out.append(_abd(tokens[j]))
            i = j + 1
            continue
        joined = _ABD_JOINED.match(token)
        if joined and token not in ("abdou", "abdi"):
            out.append(_abd(joined.group(1)))
            i += 1
            continue
        if token in ("abu", "abou", "abo") and has_next:
            j = i + 1
            if tokens[j] in ARTICLES and j + 1 < len(tokens):
                j += 1
            out.append("abu" + tokens[j])
            i = j + 1
            continue
        if token in ARTICLES and len(tokens) > 1:
            i += 1
            continue
        if token in NASAB and i > 0:
            i += 1
            continue
        out.append(token)
        i += 1
    return out


def latin_skeleton(token: str) -> str:
    text = token.lower()
    for a, b in (
        ("kh", "k"),
        ("gh", "g"),
        ("sh", "s"),
        ("ch", "s"),
        ("dj", "j"),
        ("th", "t"),
        ("dh", "d"),
        ("ph", "f"),
        ("q", "k"),
        ("c", "k"),
        ("x", "ks"),
    ):
        text = text.replace(a, b)
    text = re.sub(r"(?<=[aeiou])h$", "", text)
    text = re.sub(r"[aeiouyw']", "", text)
    return re.sub(r"(.)\1+", r"\1", text)


def joined_article_root(token: str) -> str | None:
    """For a token like "alattar", the root after a joined article ("attar"), else None."""
    match = _JOINED_ARTICLE.match(token)
    return match.group(1) if match else None
```

**`keys/src/neonradar_keys/symbols.py`**:

```python
"""Arabic index into rigour's Wikidata name groups (built by scripts/build_ar_symbol_index.py)."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable
from functools import lru_cache
from importlib.resources import files
from itertools import pairwise

from neonradar_keys.arabic import ar_normalize


@lru_cache(maxsize=1)
def _index() -> dict[str, list[str]]:
    resource = files("neonradar_keys") / "data" / "ar_symbols.json.gz"
    with resource.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as handle:
        data: dict[str, object] = json.load(handle)
    groups = data["groups"]
    if not isinstance(groups, dict):
        raise ValueError("ar_symbols.json.gz: 'groups' must be an object")
    return groups


def arabic_symbols(tokens: Iterable[str]) -> set[str]:
    """QIDs for normalised Arabic tokens and adjacent token pairs (for compound given names)."""
    items = [ar_normalize(t) for t in tokens]
    keys = set(items) | {a + " " + b for a, b in pairwise(items)}
    index = _index()
    return {qid for key in keys for qid in index.get(key, [])}
```

**`keys/src/neonradar_keys/names.py`**:

```python
"""Person and organisation name keys (PHASE-2.md M2.8; research note names-addresses.md 3 to 5)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from functools import lru_cache

from anyascii import anyascii
from rigour.names import (
    NameTypeTag,
    SymbolCategory,
    analyze_names,
    extract_org_types,
    remove_org_prefixes,
    remove_org_types,
    remove_person_prefixes,
    tokenize_name,
)
from rigour.text import jaro_winkler, metaphone

from neonradar_keys import arabic, latin
from neonradar_keys.symbols import arabic_symbols
from neonradar_keys.text import latin_token, nfkc, scripts

_CH_NAME = re.compile(r"^\s*([^,]+?)\s*,\s*([^,]+?)\s*$")
_AR_LEGAL_FORMS = re.compile(
    r"(?<!\w)(ش\.?\s?ذ\.?\s?م\.?\s?م|ذ\.?\s?م\.?\s?م|ش\.?\s?م\.?\s?م|ش\.?\s?م\.?\s?ع(\.?\s?[مق])?"
    r"|ش\.?\s?م\.?\s?ب|ش\.?\s?م\.?\s?ل|ش\.?\s?ش\.?\s?و|ذات مسؤولي[ةه] محدود[ةه])\.?(?!\w)"
)


@dataclass(frozen=True)
class PersonKey:
    tokens: tuple[str, ...]  # normalised tokens in name order
    key: str  # sorted unique tokens joined by spaces ("" when nothing is left)
    given: tuple[str, ...]  # given-name tokens when the source says which part is which
    family: tuple[str, ...]  # family-name tokens when known
    skeletons: tuple[str, ...]  # consonant skeletons (cross-script blocking aid)
    phonetic: tuple[str, ...]  # Metaphone codes of ASCII tokens
    symbols: tuple[str, ...]  # Wikidata QIDs of name groups (rigour, plus the Arabic index)


@dataclass(frozen=True)
class OrgKey:
    key: str  # name without legal forms and leading "The", folded
    legal_forms: tuple[str, ...]  # generic legal form codes (for example "llc", "jsc", "llc_ar")


def split_ch_name(text: str) -> tuple[str, str] | None:
    """Companies House officers write "SURNAME, Forenames": returns (given, family) or None."""
    match = _CH_NAME.match(text)
    if match and match.group(1).upper() == match.group(1):
        return match.group(2), match.group(1)
    return None


def _tokens(text: str) -> list[str]:
    text = remove_person_prefixes(nfkc(text))
    raw = tokenize_name(text.casefold())
    if "Arabic" in scripts(text):
        raw = [t for t in raw if t]
        while len(raw) > 2 and arabic.ar_normalize(raw[0]) in arabic.HONORIFICS:
            raw = raw[1:]
        return arabic.arabic_rules(raw)
    folded = [latin_token(t) for t in raw]
    folded = [t for t in folded if t]
    while len(folded) > 2 and folded[0] in latin.HONORIFICS:
        folded = folded[1:]
    return [t for t in latin.latin_rules(folded) if t]


def _skeletons(tokens: Iterable[str]) -> tuple[str, ...]:
    out: set[str] = set()
    for token in tokens:
        if "Arabic" in scripts(token):
            candidates = [arabic.arabic_skeleton(token)]
        else:
            candidates = [latin.latin_skeleton(token)]
            root = latin.joined_article_root(token)
            if root:
                candidates.append(latin.latin_skeleton(root))
        out.update(c for c in candidates if len(c) >= 2)
    return tuple(sorted(out))


@lru_cache(maxsize=200_000)
def _rigour_symbols(text: str) -> frozenset[str]:
    found: set[str] = set()
    for name in analyze_names(NameTypeTag.PER, [text]):
        found.update(str(s.id) for s in name.symbols if s.category == SymbolCategory.NAME)
    return frozenset(found)


def person_key(name: str, given: str | None = None, family: str | None = None) -> PersonKey:
    """Keys for one person name. Pass given and family when the source separates them."""
    ch = split_ch_name(name)
    if ch and given is None and family is None:
        given, family = ch
        name = f"{given} {family}"
    tokens = _tokens(name)
    given_tokens = tuple(_tokens(given)) if given else ()
    family_tokens = tuple(_tokens(family)) if family else ()
    symbols = set(_rigour_symbols(name))
    if "Arabic" in scripts(name):
        symbols |= arabic_symbols(tokens)
    phonetic = tuple(sorted({metaphone(t) for t in tokens if t.isascii() and metaphone(t)}))
    return PersonKey(
        tokens=tuple(tokens),
        key=" ".join(sorted(set(tokens))),
        given=given_tokens,
        family=family_tokens,
        skeletons=_skeletons(tokens),
        phonetic=phonetic,
        symbols=tuple(sorted(symbols)),
    )


def org_key(name: str) -> OrgKey:
    text = nfkc(name).casefold()
    forms = {form for _, form in extract_org_types(text, generic=True)}
    if _AR_LEGAL_FORMS.search(text):
        forms.add("llc_ar")
    text = _AR_LEGAL_FORMS.sub(" ", text)
    text = remove_org_types(remove_org_prefixes(text), replacement=" ")
    tokens = tokenize_name(text.replace("&", " and "))
    if "Arabic" in scripts(text):
        folded = [arabic.ar_normalize(t) for t in tokens]
    else:
        folded = [latin_token(t) for t in tokens]
    return OrgKey(key=" ".join(t for t in folded if t), legal_forms=tuple(sorted(forms)))


def name_similarity(left: str, right: str) -> float:
    """Jaro-Winkler on two keys (rigour returns 0.0 for scores at or below 0.6)."""
    if not left or not right:
        return 0.0
    return float(jaro_winkler(left, right))


def latin_forms(names: Iterable[str]) -> list[str]:
    """Latin renderings of non-Latin names, for the full-text search aid (C2 names_latin)."""
    out = {anyascii(nfkc(n)).strip() for n in names if scripts(n) - {"Latin"}}
    return sorted(f for f in out if f)
```

**`keys/src/neonradar_keys/postcodes.py`**:

```python
"""UK postcodes (research note names-addresses.md 7)."""

from __future__ import annotations

import re
from dataclasses import dataclass

POSTCODE_RE = re.compile(
    r"(?<![A-Z0-9])(GIR ?0AA|(?:[A-Z][0-9]{1,2}|[A-Z][A-HJ-Y][0-9]{1,2}|[A-Z][0-9][A-Z]"
    r"|[A-Z][A-HJ-Y][0-9][A-Z]) ?[0-9][ABD-HJLNP-UW-Z]{2})(?![A-Z0-9])"
)


@dataclass(frozen=True)
class PostcodeParts:
    postcode: str
    outward: str
    inward: str
    area: str
    district: str
    sector: str


def normalise_uk_postcode(text: str) -> str | None:
    """Upper case, one space before the inward code; None when the text is not a UK postcode."""
    compact = re.sub(r"\s+", "", text.upper())
    if len(compact) < 5:
        return None
    candidate = f"{compact[:-3]} {compact[-3:]}"
    return candidate if POSTCODE_RE.fullmatch(candidate) else None


def find_uk_postcode(text: str) -> tuple[str | None, str]:
    """The last UK postcode in a text, normalised, and the text without it."""
    upper = text.upper()
    matches = list(POSTCODE_RE.finditer(upper))
    if not matches:
        return None, text
    last = matches[-1]
    return normalise_uk_postcode(last.group(1)), text[: last.start()] + " " + text[last.end() :]


def postcode_parts(postcode: str) -> PostcodeParts:
    outward, inward = postcode.split(" ")
    area_match = re.match(r"[A-Z]{1,2}", outward)
    area = area_match.group(0) if area_match else outward
    return PostcodeParts(postcode, outward, inward, area, outward, f"{outward} {inward[0]}")
```

**`keys/src/neonradar_keys/addresses.py`**:

```python
"""Address keys for UK addresses (research note names-addresses.md 8)."""

from __future__ import annotations

import re
from collections.abc import Iterable

from anyascii import anyascii

from neonradar_keys.postcodes import find_uk_postcode
from neonradar_keys.text import nfkc

_COUNTRY_WORDS = [
    w.split()
    for w in (
        "UNITED KINGDOM",
        "GREAT BRITAIN",
        "NORTHERN IRELAND",
        "ENGLAND",
        "SCOTLAND",
        "WALES",
        "BRITAIN",
        "UK",
        "U K",
        "GB",
        "GBR",
    )
]
_ABBREVIATIONS = {
    "RD": "ROAD",
    "AVE": "AVENUE",
    "AV": "AVENUE",
    "LN": "LANE",
    "DR": "DRIVE",
    "CT": "COURT",
    "CRES": "CRESCENT",
    "PL": "PLACE",
    "SQ": "SQUARE",
    "GDNS": "GARDENS",
    "GRN": "GREEN",
    "CL": "CLOSE",
    "TERR": "TERRACE",
    "TER": "TERRACE",
    "PK": "PARK",
    "PDE": "PARADE",
    "HSE": "HOUSE",
    "HO": "HOUSE",
    "BLDG": "BUILDING",
    "BLDGS": "BUILDINGS",
    "CTR": "CENTRE",
    "EST": "ESTATE",
    "IND": "INDUSTRIAL",
    "APT": "FLAT",
    "APARTMENT": "FLAT",
    "FLT": "FLAT",
    "STE": "SUITE",
    "FLR": "FLOOR",
    "FIRST": "1ST",
    "SECOND": "2ND",
    "THIRD": "3RD",
    "FOURTH": "4TH",
    "FIFTH": "5TH",
    "MT": "MOUNT",
    "WY": "WAY",
    "HWY": "HIGHWAY",
}
_CARE_OF = re.compile(r"^(C\s*/\s*O|CARE OF)\b")


def address_key(text: str) -> str | None:
    """ "POSTCODE|TOKENS" for an address, or None when it has neither a postcode nor a street line.

    Real loaders build the text from structured fields (premises, address lines, locality,
    postcode). A key without a UK postcode starts with "NOPC|".
    """
    upper = anyascii(nfkc(text)).upper()
    postcode, rest = find_uk_postcode(upper)
    segments = [s.strip() for s in re.split(r"[,\n;]+", rest) if s.strip()]
    segments = [s for s in segments if not _CARE_OF.match(s)]
    grouped: list[list[str]] = []
    for segment in segments:
        segment = re.sub(r"(?<=\d)\s*-\s*(?=\d)", "-", segment.replace("&", " AND "))
        tokens = [t for t in re.split(r"[^A-Z0-9-]+", segment) if t and t != "-"]
        if tokens:
            grouped.append(tokens)
    flat = [t for group in grouped for t in group]
    changed = True
    while changed and flat:
        changed = False
        for words in _COUNTRY_WORDS:
            if flat[-len(words) :] == words:
                flat = flat[: -len(words)]
                changed = True
                break
    ends: set[int] = set()
    count = 0
    for group in grouped:
        count += len(group)
        ends.add(count - 1)
    out: list[str] = []
    for i, word in enumerate(flat):
        if word == "ST":
            street = (i in ends or i == len(flat) - 2) and i > 0 and not flat[i - 1].isdigit()
            out.append("STREET" if street else "SAINT")
        else:
            out.append(_ABBREVIATIONS.get(word, word))
    has_street_line = any(t.isdigit() or t[:1].isdigit() for t in out) or len(out) >= 3
    if not postcode and not has_street_line:
        return None
    return (postcode or "NOPC") + "|" + " ".join(out)


def address_key_from_parts(parts: Iterable[str | None]) -> str | None:
    """Key from structured fields: premises, lines, locality, region, postcode, country."""
    return address_key(", ".join(p for p in parts if p))
```

**`keys/src/neonradar_keys/companies_house.py`**:

```python
"""Companies House "same as" name key (SI 2015/17 Schedule 3), approximate (research note 10)."""

from __future__ import annotations

import re
import unicodedata

from anyascii import anyascii

_SCHEDULE_2 = sorted(
    [
        "COMMUNITY INTEREST PUBLIC LIMITED COMPANY",
        "COMMUNITY INTEREST PLC",
        "CWMNI BUDDIANT CYMUNEDOL CYHOEDDUS CYFYNGEDIG",
        "CWMNI BUDDIANT CYMUNEDOL CCC",
        "CWMNI CYFYNGEDIG CYHOEDDUS",
        "PUBLIC LIMITED COMPANY",
        "COMMUNITY INTEREST COMPANY",
        "CWMNI BUDDIANT CYMUNEDOL",
        "RIGHT TO ENFRANCHISEMENT",
        "HAWL I RYDDFREINIAD",
        "RIGHT TO MANAGE",
        "CWMNI RTM CYFYNGEDIG",
        "UK ECONOMIC INTEREST GROUPING",
        "INVESTMENT COMPANY WITH VARIABLE CAPITAL",
        "CWMNI BUDDSODDI A CHYFALAF NEWIDIOL",
        "LIMITED LIABILITY PARTNERSHIP",
        "PARTNERIAETH ATEBOLRWYDD CYFYNGEDIG",
        "LIMITED PARTNERSHIP",
        "PARTNERIAETH CYFYNGEDIG",
        "OPEN-ENDED INVESTMENT COMPANY",
        "CWMNI BUDDSODDIAD PENAGORED",
        "CHARITABLE INCORPORATED ORGANISATION",
        "SEFYDLIAD ELUSENNOL CORFFOREDIG",
        "INDUSTRIAL AND PROVIDENT SOCIETY",
        "CO-OPERATIVE SOCIETY",
        "PROTECTED CELL COMPANY",
        "PCC LIMITED",
        "PCC LTD",
        "CWMNI UNEDAU GWARCHODEDIG",
        "CUG CYFYNGEDIG",
        "CUG CYF",
        "COMMUNITY BENEFIT SOCIETY",
        "ANGHYFYNGEDIG",
        "UNLIMITED",
        "CYFYNGEDIG",
        "LIMITED",
        "UKEIG",
        "LTD",
        "CYF",
        "PLC",
        "CCC",
        "CIC",
        "CBC",
        "RTE",
        "RTM",
        "LLP",
        "LP",
        "PC",
        "PAC",
        "CIO",
        "SEC",
    ],
    key=len,
    reverse=True,
)
_PARA_4 = [
    ("&", ["AND", "&"]),
    ("+", ["PLUS", "+"]),
    ("0", ["0", "ZERO", "O"]),
    ("1", ["1", "ONE"]),
    ("2", ["2", "TWO", "TO", "TOO"]),
    ("3", ["3", "THREE"]),
    ("4", ["4", "FOUR", "FOR"]),
    ("5", ["5", "FIVE"]),
    ("6", ["6", "SIX"]),
    ("7", ["7", "SEVEN"]),
    ("8", ["8", "EIGHT"]),
    ("9", ["9", "NINE"]),
    ("£", ["£", "POUND"]),
    ("€", ["€", "EURO"]),
    ("$", ["$", "DOLLAR"]),
    ("¥", ["¥", "YEN"]),
    ("%", ["%", "PER CENT", "PERCENT", "PER CENTUM", "PERCENTUM"]),
    ("@", ["@", "AT"]),
]
_PARA_5 = sorted(
    [
        "& CO",
        "& COMPANY",
        "BIZ",
        "CO UK",
        "CO.UK",
        "CO",
        "COM",
        "COMPANY",
        "EU",
        "GB",
        "GREAT BRITAIN",
        "NET",
        "NI",
        "NORTHERN IRELAND",
        "ORG UK",
        "ORG.UK",
        "ORG",
        "UK",
        "UNITED KINGDOM",
        "WALES",
        "& CWMNI",
        "A'R CWMNI",
        "CWMNI",
        "CYM",
        "CYMRU",
        "DU",
        "PF",
        "PRYDAIN FAWR",
        "Y DEYRNAS UNEDIG",
    ],
    key=len,
    reverse=True,
)


def _strip_trailing(text: str, items: list[str], separators: str) -> str:
    changed = True
    while changed:
        changed = False
        for item in items:
            for form in (item, f"({item})", f"[{item}]", f"{{{item}}}"):
                pattern = re.compile(r"(^|[" + separators + r"])" + re.escape(form) + r"[.\s]*$")
                if pattern.search(text):
                    shorter = pattern.sub(r"\1", text).rstrip(" .")
                    if shorter and shorter != text:
                        text, changed = shorter, True
    return text


def ch_same_as_key(name: str) -> str:
    """Key for comparing UK company names; use as a blocking key and as strong evidence only."""
    text = anyascii(unicodedata.normalize("NFKC", name)).upper()
    text = re.sub(r"\s+", " ", text).strip()
    text = _strip_trailing(text, _SCHEDULE_2, r"\s")
    for canonical, forms in _PARA_4:
        for form in sorted(forms, key=len, reverse=True):
            text = re.sub(r"(?:(?<=\s)|^)" + re.escape(form) + r"(?=\s)", canonical, text)
    text = _strip_trailing(text, _PARA_5, r"\s.@")
    text = re.sub(r"[^\w&+£€$¥%@\s]|_", "", text)
    text = re.sub(r"S$", "", text.strip())[:60]
    text = re.sub(r"^(?:(?:@|THE\s|WWW)\s*)+", "", text)
    return text.replace(" ", "")
```

**`keys/src/neonradar_keys/countries.py`**:

```python
"""Country and nationality codes (research note names-addresses.md 9)."""

from __future__ import annotations

import csv
import io
from functools import lru_cache
from importlib.resources import files

from rigour.territories import lookup_territory


@lru_cache(maxsize=1)
def _nationalities() -> dict[str, str]:
    resource = files("neonradar_keys") / "data" / "nationalities.csv"
    text = resource.read_text(encoding="utf-8")
    return {row["value"].casefold(): row["country"] for row in csv.DictReader(io.StringIO(text))}


@lru_cache(maxsize=50_000)
def country_code(value: str | None) -> str | None:
    """Lower-case ISO alpha-2 code for a country name, demonym or code; UK nations map to "gb".

    Exact lookups in the Companies House and FCDO lists first, then rigour without fuzzy
    matching (fuzzy matching gives confident wrong answers). Unknown values give None.
    """
    if not value or not value.strip():
        return None
    text = value.strip()
    known = _nationalities().get(text.casefold())
    if known is not None:
        return known or None
    territory = lookup_territory(text)
    if territory is None:
        return None
    code = territory.ftm_country or territory.code
    return code.split("-")[0] if code else None
```

**`keys/src/neonradar_keys/ids.py`**:

```python
"""Identifiers used by the deterministic rules (PHASE-2.md 7.1.2)."""

from __future__ import annotations

import re

from rigour.ids import LEI

_COMPANY_NUMBER = re.compile(r"^([A-Z]{0,2})(\d+)$")

# Companies House company number prefixes (bulk-sources-loading.md 2.6): the official list of
# May 2012 plus the newer prefixes named by the community. "R0" is a prefix followed by six digits.
CH_PREFIXES = frozenset(
    {"AC", "FC", "GE", "GN", "GS", "IC", "IP", "LP", "NA", "NF", "NI", "NL", "NO", "NP", "NR"}
    | {"NZ", "OC", "R0", "RC", "SA", "SC", "SF", "SI", "SL", "SO", "SP", "SR", "SZ", "ZC"}
    | {"CE", "CS", "FE", "OE", "PC", "SE", "SG"}
)
# The synthetic benchmark's company number prefix (M2.9): not a Companies House prefix.
SYNTHETIC_PREFIX = "SY"


def uk_company_number(value: str | None, *, synthetic: bool = False) -> str | None:
    """Rule D1 normalisation: the 8-character Companies House form, or None.

    Upper case; spaces, dots and hyphens removed; all digits are left-padded to 8; one or two
    letters followed by digits keep the letters and pad the digits to 8 characters in all. The
    result must be all digits or start with a Companies House prefix. The synthetic prefix "SY"
    counts only when `synthetic` is true (records of a synthetic dataset). Anything else is not a
    UK company number.
    """
    if not value:
        return None
    text = re.sub(r"[\s.\-]", "", value).upper()
    match = _COMPANY_NUMBER.match(text)
    if not match:
        return None
    prefix, digits = match.groups()
    width = 8 - len(prefix)
    if len(digits) > width:
        return None
    number = prefix + digits.zfill(width)
    if has_ch_prefix(number) or (synthetic and number.startswith(SYNTHETIC_PREFIX)):
        return number
    return None


def has_ch_prefix(number: str) -> bool:
    """True for an all-digit number or one that starts with a Companies House prefix."""
    return number.isdigit() or number[:2] in CH_PREFIXES


def is_valid_lei(value: str | None) -> bool:
    if not value:
        return False
    return bool(LEI.is_valid(value.strip().upper()))


def un_reference(value: str | None) -> str | None:
    """UN Security Council reference such as "QDi.123": upper case, no spaces or final dot."""
    if not value:
        return None
    text = re.sub(r"\s+", "", value).upper().rstrip(".")
    return text or None
```

**`keys/src/neonradar_keys/data/nationalities.csv`**:

```text
value,country
Afghan,af
Albanian,al
Algerian,dz
American,us
Andorran,ad
Angolan,ao
Anguillan,ai
Argentine,ar
Armenian,am
Australian,au
Austrian,at
Azerbaijani,az
Bahamian,bs
Bahraini,bh
Bangladeshi,bd
Barbadian,bb
Belarusian,by
Belgian,be
Belizean,bz
Beninese,bj
Bermudian,bm
Bhutanese,bt
Bolivian,bo
Botswanan,bw
Brazilian,br
British,gb
British Virgin Islander,vg
Briton,gb
Bruneian,bn
Bulgarian,bg
Burkinan,bf
Burmese,mm
Burundian,bi
Cambodian,kh
Cameroonian,cm
Canadian,ca
Cape Verdean,cv
Cayman Islander,ky
Central African,cf
Chadian,td
Chilean,cl
Chinese,cn
Citizen of Antigua and Barbuda,ag
Citizen of Bosnia and Herzegovina,ba
Citizen of Guinea-Bissau,gw
Citizen of Kiribati,ki
Citizen of Lesotho,ls
Citizen of Madagascar,mg
Citizen of Myanmar,mm
Citizen of Naoero,nr
Citizen of Seychelles,sc
Citizen of St Christopher (St Kitts) and Nevis,kn
Citizen of the Dominican Republic,do
Citizen of the United Arab Emirates,ae
Citizen of Vanuatu,vu
Colombian,co
Comoran,km
Congolese (Congo),cg
Congolese (DRC),cd
Congolese (Republic of the Congo),cg
Cook Islander,ck
Costa Rican,cr
Croatian,hr
Cuban,cu
Cymraes,gb
Cymro,gb
Cypriot,cy
Czech,cz
Danish,dk
Djiboutian,dj
Dominican,dm
Dutch,nl
East Timorese,tl
Ecuadorean,ec
Egyptian,eg
Emirati,ae
English,gb
Equatorial Guinean,gq
Eritrean,er
Estonian,ee
Ethiopian,et
Faroese,fo
Fijian,fj
Filipino,ph
Finnish,fi
French,fr
Gabonese,ga
Gambian,gm
Georgian,ge
German,de
Ghanaian,gh
Gibraltarian,gi
Greek,gr
Greenlandic,gl
Grenadian,gd
Guamanian,gu
Guatemalan,gt
Guinean,gn
Guyanese,gy
Haitian,ht
Honduran,hn
Hong Konger,hk
Hungarian,hu
Icelandic,is
Indian,in
Indonesian,id
Iranian,ir
Iraqi,iq
Irish,ie
Israeli,il
Italian,it
Ivorian,ci
Jamaican,jm
Japanese,jp
Jordanian,jo
Kazakh,kz
Kenyan,ke
Kittitian,kn
Kosovan,xk
Kuwaiti,kw
Kyrgyz,kg
Lao,la
Latvian,lv
Lebanese,lb
Liberian,lr
Libyan,ly
Liechtenstein citizen,li
Lithuanian,lt
Luxembourger,lu
Macanese,mo
Macedonian,mk
Malagasy,mg
Malawian,mw
Malaysian,my
Maldivian,mv
Malian,ml
Maltese,mt
Marshallese,mh
Martiniquais,mq
Mauritanian,mr
Mauritian,mu
Mexican,mx
Micronesian,fm
Moldovan,md
Monegasque,mc
Mongolian,mn
Montenegrin,me
Montserratian,ms
Moroccan,ma
Mosotho,ls
Mozambican,mz
Namibian,na
Nauruan,nr
Nepalese,np
New Zealander,nz
Nicaraguan,ni
Nigerian,ng
Nigerien,ne
Niuean,nu
North Korean,kp
Northern Irish,gb
Norwegian,no
Omani,om
Pakistani,pk
Palauan,pw
Palestinian,ps
Panamanian,pa
Papua New Guinean,pg
Paraguayan,py
Peruvian,pe
Pitcairn Islander,pn
Polish,pl
Portuguese,pt
Prydeinig,gb
Puerto Rican,pr
Qatari,qa
Romanian,ro
Russian,ru
Rwandan,rw
Salvadorean,sv
Sammarinese,sm
Samoan,ws
San Marinese,sm
Sao Tomean,st
Saudi Arabian,sa
Scottish,gb
Senegalese,sn
Serbian,rs
Sierra Leonean,sl
Singaporean,sg
Slovak,sk
Slovenian,si
Solomon Islander,sb
Somali,so
South African,za
South Korean,kr
South Sudanese,ss
Spanish,es
Sri Lankan,lk
St Helenian,sh
St Lucian,lc
Stateless,
Sudanese,sd
Surinamese,sr
Swazi,sz
Swedish,se
Swiss,ch
Syrian,sy
Taiwanese,tw
Tajik,tj
Tanzanian,tz
Thai,th
Togolese,tg
Tongan,to
Trinidad and Tobago citizen,tt
Trinidadian,tt
Tristanian,sh
Tunisian,tn
Turk,tr
Turkish,tr
Turkmen,tm
Turks and Caicos Islander,tc
Tuvaluan,tv
Ugandan,ug
Ukrainian,ua
Uruguayan,uy
Uzbek,uz
Vatican citizen,va
Venezuelan,ve
Vietnamese,vn
Vincentian,vc
Wallisian,wf
Welsh,gb
Yemeni,ye
Zambian,zm
Zimbabwean,zw
```

**`keys/scripts/build_ar_symbol_index.py`**:

```python
"""Build keys/src/neonradar_keys/data/ar_symbols.json.gz from rigour's Wikidata name groups.

The source is rust/data/names/person_names.txt in github.com/opensanctions/rigour at the
tag that matches the pinned rigour version (MIT; the names come from Wikidata, CC0). Each
line is "form1, form2, ... => Qnnn". The index maps ar_normalize(form) of every form that
contains Arabic script to the sorted list of QIDs. Run it whenever the rigour pin changes:

    uv run python keys/scripts/build_ar_symbol_index.py --tag v2.5.0 \
        --sha256 be47a435969da3fa7311d8c682e462d6d20e6cf27cf90ad1473ce213c9a91c79
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

from neonradar_keys.arabic import ar_normalize
from neonradar_keys.text import scripts

URL = (
    "https://raw.githubusercontent.com/opensanctions/rigour/{tag}/rust/data/names/person_names.txt"
)
OUT = Path(__file__).resolve().parents[1] / "src" / "neonradar_keys" / "data" / "ar_symbols.json.gz"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--source", help="a local copy of person_names.txt instead of downloading")
    args = parser.parse_args()
    if args.source:
        data = Path(args.source).read_bytes()
    else:
        with urllib.request.urlopen(URL.format(tag=args.tag), timeout=60) as response:  # noqa: S310
            data = response.read()
    digest = hashlib.sha256(data).hexdigest()
    if digest != args.sha256:
        print(f"sha256 mismatch: {digest}", file=sys.stderr)
        return 1
    groups: dict[str, set[str]] = {}
    for line in data.decode("utf-8").splitlines():
        forms, _, qid = line.rpartition("=>")
        qid = qid.strip()
        for form in forms.split(","):
            form = form.strip()
            if form and "Arabic" in scripts(form):
                groups.setdefault(ar_normalize(form), set()).add(qid)
    payload = {
        "source": URL.format(tag=args.tag),
        "sha256": digest,
        "licence": "MIT (OpenSanctions Datenbanken GmbH); name data from Wikidata (CC0)",
        "groups": {key: sorted(qids) for key, qids in sorted(groups.items())},
    }
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    with (
        OUT.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as gz,
    ):
        gz.write(text.encode("utf-8"))  # mtime=0 keeps the header free of the build time
    print(f"{len(groups)} keys written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**`keys/scripts/build_nationalities.py`**:

```python
"""Build keys/src/neonradar_keys/data/nationalities.csv (value, ISO alpha-2 country).

Inputs (both Open Government Licence v3.0): the Companies House list of nationalities from
"Nationalities and countries for company filings" (one value per line), and the FCDO
Geographical Names Index citizen names (tab-separated: ISO alpha-2 code, comma-separated
citizen names). Values not in OVERRIDES are mapped with rigour.territories.lookup_territory
without fuzzy matching. Usage:

    uv run python keys/scripts/build_nationalities.py ch_nationalities.txt fcdo_citizen_names.tsv
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from rigour.territories import lookup_territory

OUT = Path(__file__).resolve().parents[1] / "src" / "neonradar_keys" / "data" / "nationalities.csv"
# Where rigour gives no code or a wrong one (names-addresses.md section 9), and the UK nations.
OVERRIDES = {
    "Anguillan": "ai",
    "Citizen of Antigua and Barbuda": "ag",
    "Bermudian": "bm",
    "Bhutanese": "bt",
    "Citizen of Bosnia and Herzegovina": "ba",
    "Bruneian": "bn",
    "Cape Verdean": "cv",
    "Cayman Islander": "ky",
    "Chadian": "td",
    "Comoran": "km",
    "Cook Islander": "ck",
    "Cymraes": "gb",
    "Cymro": "gb",
    "Citizen of the Dominican Republic": "do",
    "Guamanian": "gu",
    "Hong Konger": "hk",
    "Citizen of Kiribati": "ki",
    "Liechtenstein citizen": "li",
    "Martiniquais": "mq",
    "Montserratian": "ms",
    "Nauruan": "nr",
    "Palauan": "pw",
    "Papua New Guinean": "pg",
    "Pitcairn Islander": "pn",
    "Prydeinig": "gb",
    "Samoan": "ws",
    "Citizen of Seychelles": "sc",
    "Solomon Islander": "sb",
    "St Helenian": "sh",
    "Stateless": "",
    "Tristanian": "sh",
    "Turks and Caicos Islander": "tc",
    "Tuvaluan": "tv",
    "Vatican citizen": "va",
    "Citizen of Vanuatu": "vu",
    "Vincentian": "vc",
    "Wallisian": "wf",
    "Mauritian": "mu",
    "Congolese (Congo)": "cg",
    "Congolese (DRC)": "cd",
    "British": "gb",
    "English": "gb",
    "Scottish": "gb",
    "Welsh": "gb",
    "Northern Irish": "gb",
}


def code_for(value: str) -> str | None:
    if value in OVERRIDES:
        return OVERRIDES[value]
    territory = lookup_territory(value)
    if territory is None:
        return None
    code = territory.ftm_country or territory.code
    return code.split("-")[0] if code else None


def main() -> int:
    ch_path, fcdo_path = Path(sys.argv[1]), Path(sys.argv[2])
    rows: dict[str, str] = {}
    missing: list[str] = []
    for value in (v.strip() for v in ch_path.read_text(encoding="utf-8").splitlines()):
        if value:
            code = code_for(value)
            if code is None:
                missing.append(value)
            else:
                rows[value] = code
    for line in fcdo_path.read_text(encoding="utf-8").splitlines():
        code, _, names = line.partition("\t")
        for name in (n.strip() for n in names.split(",")):
            if name and name not in rows:
                rows[name] = code.strip().lower()
    if missing:
        print("no code for: " + ", ".join(missing), file=sys.stderr)
        return 1
    with OUT.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["value", "country"])
        for value in sorted(rows, key=str.casefold):
            writer.writerow([value, rows[value]])
    print(f"{len(rows)} values written to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

**`keys/tests/test_keys.py`**:

```python
"""Oracle tests for neonradar_keys (PHASE-2.md M2.8). Expected values were verified on
18 October 2026 with rigour 2.5.0, normality 3.1.0, PyICU 2.16.2 and anyascii 0.3.3."""

import gzip
import json
import re
from importlib.metadata import version
from importlib.resources import files

import pytest

from neonradar_keys.addresses import address_key
from neonradar_keys.arabic import ar_normalize
from neonradar_keys.companies_house import ch_same_as_key
from neonradar_keys.countries import country_code
from neonradar_keys.ids import CH_PREFIXES, has_ch_prefix, is_valid_lei, uk_company_number
from neonradar_keys.names import latin_forms, name_similarity, org_key, person_key, split_ch_name
from neonradar_keys.postcodes import normalise_uk_postcode, postcode_parts


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("أحمد", "احمد"),
        ("إحمد", "احمد"),
        ("آمنة", "امنه"),
        ("مُحَمَّد", "محمد"),
        ("محـــمد", "محمد"),
        ("فاطمة", "فاطمه"),
        ("مصطفى", "مصطفي"),
        ("عائشة", "عايشه"),
        ("ﷲ", "الله"),
        ("٢٠٢٦", "2026"),
    ],
)
def test_ar_normalize(raw, expected):
    assert ar_normalize(raw) == expected


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("سامر بن خليل العطار", "خليل سامر عطار"),
        ("عبد الرحمن العلي", "عبدالرحمن علي"),
        ("عبدالرحمن العلي", "عبدالرحمن علي"),
        ("Abdul Rahman Al Ali", "abdrahman ali"),
        ("Abdulrahman Al-Ali", "abdrahman ali"),
        ("Abd al-Rahman al-Ali", "abdrahman ali"),
        ("Abdel Rahman El Ali", "abdrahman ali"),
        ("AL-ALI, Abdul Rahman", "abdrahman ali"),
        ("SMITH, John Michael", "john michael smith"),
        ("AL-SAYED, Omar", "omar sayed"),
        ("Mr John Smith", "john smith"),
        ("Sheikh Hamad Saleh", "hamad saleh"),
        ("الشيخ سامر العطار", "سامر عطار"),
        ("الدكتور خليل حداد", "حداد خليل"),
        ("Abdullah Haddad", "abdallah haddad"),
        ("Abd Allah Haddad", "abdallah haddad"),
        ("Abu Bakr Haddad", "abubakr haddad"),
        ("Khalil bin Samer", "khalil samer"),
        ("Александр Сергеевич Иванов", "aleksandr ivanov sergeevich"),
        ("Пётр Щербаков", "petr shcherbakov"),
        ("Jürgen Müller", "jurgen muller"),
        ("Łukasz Wiśniewski", "lukasz wisniewski"),
        ("إلهام حداد", "الهام حداد"),
    ],
)
def test_person_keys(name, key):
    assert person_key(name).key == key


def test_ch_name_split_gives_family():
    assert split_ch_name("SMITH, John Michael") == ("John Michael", "SMITH")
    assert split_ch_name("Smith, John") is None
    keys = person_key("SMITH, John Michael")
    assert keys.family == ("smith",) and keys.given == ("john", "michael")


def test_cross_script_symbols_and_skeletons():
    assert "Q5837762" in person_key("محمد").symbols
    assert "Q5837762" in person_key("Mohammed").symbols
    assert "Q5837762" in person_key("Мухаммед").symbols
    assert {"Q923", "Q1511218", "Q17501806"} <= set(person_key("Alexander").symbols)
    assert "Q17501806" in person_key("Александр").symbols
    assert person_key("إحمد خليل").symbols  # the Arabic index catches spellings the tagger misses
    assert "bdrhmn" in person_key("Abdul Rahman").skeletons
    assert "mhmd" in person_key("Mohammed").skeletons and "mhmd" in person_key("محمد").skeletons


@pytest.mark.parametrize(
    ("name", "key", "forms"),
    [
        ("ACME TRADING LTD", "acme trading", ("llc",)),
        ("Acme Trading Limited", "acme trading", ("llc",)),
        ("ACME HOLDINGS PLC", "acme holdings", ("jsc",)),
        ("Acme Partners LLP", "acme partners", ("llp",)),
        ("ООО «Ромашка»", "romashka", ("llc",)),
        ("The Acme Company Limited", "acme company", ("llc",)),
        ("ACME & SONS (UK) LIMITED", "acme and sons uk", ("llc",)),
    ],
)
def test_org_keys(name, key, forms):
    result = org_key(name)
    assert (result.key, result.legal_forms) == (key, forms)


def test_arabic_legal_form():
    assert "llc_ar" in org_key("شركة النخيل للتجارة ذ.م.م").legal_forms


@pytest.mark.parametrize(
    ("name", "key"),
    [
        ("ACME LIMITED", "ACME"),
        ("Acme Ltd.", "ACME"),
        ("ACME UK LIMITED", "ACME"),
        ("ACME (UK) LIMITED", "ACME"),
        ("THE ACME COMPANY LIMITED", "ACME"),
        ("ACME & CO LTD", "ACME"),
        ("A.C.M.E. LIMITED", "ACME"),
        ("WWW.ACME.CO.UK LIMITED", "ACME"),
        ("ACMÉ LIMITED", "ACME"),
        ("ACME HOLDINGS LIMITED", "ACMEHOLDING"),
        ("ACME HOLDING LTD", "ACMEHOLDING"),
        ("BACK TO BASICS LIMITED", "BACK2BASIC"),
        ("BACK 2 BASICS LTD", "BACK2BASIC"),
    ],
)
def test_ch_same_as(name, key):
    assert ch_same_as_key(name) == key


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("n1 7gu", "N1 7GU"),
        ("N17GU", "N1 7GU"),
        ("ec1a1bb", "EC1A 1BB"),
        ("N1 7GC", None),
        ("QQ1 2AB", "QQ1 2AB"),
        ("ZZ1 2AB", None),
        ("hello", None),
    ],
)
def test_postcodes(raw, expected):
    assert normalise_uk_postcode(raw) == expected


def test_postcode_parts():
    parts = postcode_parts("N1 7GU")
    assert (parts.area, parts.district, parts.sector) == ("N", "N1", "N1 7")


@pytest.mark.parametrize(
    ("raw", "key"),
    [
        ("Flat 3, 12 High St., London, n1 7gu", "N1 7GU|FLAT 3 12 HIGH STREET LONDON"),
        (
            "FLAT 3, 12 HIGH STREET, LONDON, N1 7GU, UNITED KINGDOM",
            "N1 7GU|FLAT 3 12 HIGH STREET LONDON",
        ),
        (
            "Ste 4, Example Hse, 1-3 Example Rd., London N1 7GU",
            "N1 7GU|SUITE 4 EXAMPLE HOUSE 1-3 EXAMPLE ROAD LONDON",
        ),
        ("12 St Johns Road, London, N1 7GU", "N1 7GU|12 SAINT JOHNS ROAD LONDON"),
        (
            "c/o Example Accountants LLP, 2 Market Sq, Reading, RG1 2AA",
            "RG1 2AA|2 MARKET SQUARE READING",
        ),
        ("1st Floor 5 Church Ln Leeds LS12AB", "LS1 2AB|1ST FLOOR 5 CHURCH LANE LEEDS"),
        ("Moscow, Russia", None),
    ],
)
def test_address_keys(raw, key):
    assert address_key(raw) == key


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("British", "gb"),
        ("Welsh", "gb"),
        ("Scottish", "gb"),
        ("Irish", "ie"),
        ("Emirati", "ae"),
        ("Saudi Arabian", "sa"),
        ("Mauritian", "mu"),
        ("Congolese (Congo)", "cg"),
        ("Chadian", "td"),
        ("Stateless", None),
        ("United Kingdom", "gb"),
        ("England", "gb"),
        ("GBR", "gb"),
        ("VGB", "vg"),
        ("", None),
        ("Atlantis", None),
    ],
)
def test_country_codes(value, code):
    assert country_code(value) == code


@pytest.mark.parametrize(
    ("raw", "number"),
    [
        ("1800000", "01800000"),
        ("01800000", "01800000"),
        ("SC 12345", "SC012345"),
        ("OC300001", "OC300001"),
        ("sc-012345", "SC012345"),
        ("R0000123", "R0000123"),
        ("ABC", None),
        ("123456789", None),
        ("HE123456", None),  # a Cypriot number: HE is not a Companies House prefix
        ("GB123456", None),
        ("N1234567", None),
        ("SY000101", None),  # the synthetic prefix counts only for synthetic records
        (None, None),
    ],
)
def test_uk_company_number(raw, number):
    assert uk_company_number(raw) == number


def test_synthetic_company_numbers() -> None:
    assert uk_company_number("SY000101", synthetic=True) == "SY000101"
    assert uk_company_number("sy 101", synthetic=True) == "SY000101"
    assert uk_company_number("SC 12345", synthetic=True) == "SC012345"
    assert uk_company_number("HE123456", synthetic=True) is None


def test_lei():
    assert is_valid_lei("549300OWFMSO9NYV4H90")
    assert not is_valid_lei("549300OWFMSO9NYV4H91")
    assert not is_valid_lei(None)


def test_similarity_and_latin_forms():
    assert name_similarity("falcon ridge trading", "falcon ridge trade") > 0.95
    assert name_similarity("rana", "nora") == 0.0
    assert latin_forms(["Omar Haddad", "Омар Хаддад"]) == ["Omar Khaddad"]


def test_companies_house_prefixes() -> None:
    assert len(CH_PREFIXES) == 36  # 29 official and 7 newer prefixes (bulk-sources-loading.md 2.6)
    assert {"SC", "NI", "OC", "OE", "R0"} <= CH_PREFIXES
    assert "SY" not in CH_PREFIXES  # the synthetic benchmark prefix (M2.9)
    assert "NC" not in CH_PREFIXES  # in neither list of the research note
    assert has_ch_prefix("01234567")
    assert has_ch_prefix("SC123456")
    assert has_ch_prefix("R0012345")
    assert not has_ch_prefix("HE123456")


def test_symbol_index_matches_installed_rigour() -> None:
    # ar_symbols.json.gz is built from rigour's name data at the tag of the pinned version. A
    # lock update that moves rigour must rebuild it (scripts/build_ar_symbol_index.py).
    resource = files("neonradar_keys") / "data" / "ar_symbols.json.gz"
    with resource.open("rb") as raw, gzip.open(raw, "rt", encoding="utf-8") as handle:
        source = json.load(handle)["source"]
    match = re.search(r"/rigour/v([^/]+)/", source)
    assert match is not None
    assert match.group(1) == version("rigour")
```

### M2.9 Synthetic entity resolution benchmark

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (data steward reviews the names) |
| Depends on | M2.1a |
| Branch | `p2/m2-9-er-bench` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | Yes |
| Size | exception (the variant tables and the benchmark generator) |
| Real-data run | none |

**Goal.** A synthetic dataset with a known right answer, shaped like the real sources, hard enough to be informative, so thresholds are chosen without touching real data and CI can measure matching quality on every pull request, including the policies that keep list and leak records apart.

**Deliverables.**

1. `ingest/src/neonradar_ingest/synth/erbench.py` and `variants.py`: a seeded generator (same seed, byte-identical output; the PHASE-1.md M1.8e rules for seeds, sorted ids and the name denylist apply). It must not import `neonradar_keys`: the benchmark tests the keys, it must not be built from them.
2. **True entities.** `small`: 600 people and 300 organisations; `large`: 6,000 and 3,000.
   - People: 50 percent with English names (Faker `en_GB`), 30 percent with Arabic names (Faker `ar_SA`, carried in Arabic script and in Latin transliterations), 20 percent with Russian or Ukrainian names (Faker `ru_RU`, Cyrillic and Latin); given name, a middle name for half of them, surname, gender, a full birth date between 1940 and 2004, one or two nationalities, a home postcode.
   - **Invented surnames for listed and leaked people.** A person who gets a `list` or a `leak` record (item 3) takes an invented surname in every one of their records, so the public fixture never puts a realistic full name on a synthetic sanctions list or in a synthetic leak. `variants.py` holds a table of invented syllables, each with a Latin, an Arabic-script and a Cyrillic form; an invented surname joins two or three syllables in the person's script, and the generator redraws any result that is on the name denylist or in the surname lists of the three Faker locales used. Given names stay from Faker.
   - Postcodes use the area `QQ` (`QQ1 2AB` style): no real UK postcode starts with Q, so no synthetic person sits at a real address, and the format passes `neonradar_keys.postcodes` (an area such as `ZZ` would fail its second-letter rule).
   - Organisations: names from the neutral word lists of M1.8e plus a legal form, a synthetic UK company number (`SY` plus six digits; `SY` is not a Companies House prefix, `bulk-sources-loading.md` 2.6), an incorporation date, a registered postcode in `QQ`, and for 40 percent a synthetic LEI (prefix `SYN0`, valid ISO 17442 check digits). Every record that carries an `SY` number also carries `jurisdiction: gb`, so the resolver reads it as a UK company number (7.1.5).
3. **Records per entity**, each in the style of a real source (all in dataset `nr_synthetic`, ids `syn-erb-<p|o>-<entity number>-<record number>`, each with `nr.synthetic_kind` as the last column says):

   | Style | Shaped like | People | Organisations | `nr.synthetic_kind` |
   |---|---|---|---|---|
   | `officer` | Companies House officers | `SURNAME, Forenames` name, birth year and month, nationality as a demonym mapped to a code, a service postcode, a synthetic `nr.ch_person_number`, a `Directorship` to a company | corporate officers with a company number | `registry` |
   | `psc` | the PSC snapshot | title, forename, middle name, surname as parts, birth year and month, nationality, an `Ownership` band to a company with the open and closed bounds of 5.1 | corporate PSCs with name, company number (80 percent) and `place_registered`-style jurisdiction | `registry` |
   | `registry` | Free Company Data, GLEIF | none | the company record; a GLEIF-style record with legal name, company number and LEI | `registry` |
   | `list` | official sanctions lists | full name in list order, aliases including the original script, full birth date (70 percent), year only (20 percent) or two dates a year apart (10 percent), nationality, topic `sanction`, a `Sanction` (also `list`) with an `authority` (one of `Synthetic Authority A`, `B` and `C`) and an `authorityId`, and for half of them a shared `unscId` | entity entries with aliases, sometimes a company number, topic `sanction`, a `Sanction` as for people | `list` |
   | `leak` | ICIJ officers and entities | one upper-case name string, a country code half the time, schema `LegalEntity` | name and jurisdiction | `leak` |

   Record counts per person: 1 (40 percent), 2 (30), 3 (15), 4 (10), 5 (5); 15 percent of people get one to three `list` records, each under a different synthetic authority (at most one record per authority per entity, as on a real list, so cannot-link rule X6 holds on the benchmark); 10 percent get a `leak` record. Organisations get a `registry` record always, a GLEIF-style record when they have an LEI, one or two corporate PSC or officer records, a `list` record for 10 percent and a `leak` record for 10 percent. Because the resolver treats `list` and `leak` kinds like records of list and leak datasets (5.1, 7.1.1), the benchmark exercises policies P1, P2 and P6, and the gate on policy-blocked recall (M2.10b) covers all three.
4. **Variation**, drawn independently per record: one typo in a name token (10 percent); middle name reduced to an initial (20 percent) or dropped (30 percent); a Latin transliteration variant for Arabic and Cyrillic names (50 percent, from `variants.py`); given name and surname swapped (10 percent of `list` records); a service postcode that moved (30 percent of `officer` and `psc` records); nationality missing (20 percent). `ch_person_number`: the same first 8 characters on 60 percent of a person's officer records, a second person number on 10 percent, absent on the rest (D3 must not depend on it alone). For organisations: legal form spelled differently (`Ltd`, `Limited`, `LTD.`), `&` and `and`, a leading "The", punctuation, one typo (10 percent).
5. **Hard negatives.** 15 percent of people get a near twin: a different person with the same given name and surname, the same birth year (and the same month half of the time) and sometimes the same postcode district. 5 percent of organisations get a different organisation with the same name core and another legal form. These must never merge.
6. **`variants.py`**: transliteration tables for common Arabic given names and name particles (for example Mohammed, Muhammad, Mohamed, Mohamad; Abdul Rahman, Abdulrahman, Abd al-Rahman, Abdel Rahman; Yusuf, Youssef, Yousef; Hussein, Husain, Hussain; the article as `Al-`, `Al `, `El-` and joined) and Russian and Ukrainian given names and endings (Aleksandr, Alexander, Oleksandr; Sergei, Sergey, Serhiy; Dmitri, Dmitry, Dmytro; `-ov` and `-off`; `-sky`, `-ski` and `-skiy`), with the research note `names-addresses.md` cited in the module docstring, and the invented-syllable table of item 2. These are spelling conventions and invented sounds, not people.
7. **Ground truth** in `labels/er_truth.csv`, starting with `# synthetic: true`, then the header `record_id,entity_id,class,style,twin_of`; labels never go into records (C1 R9). `class` is `person` or `org`, the class of the true entity whatever the record's schema (a leak-style `LegalEntity` record of a person has class `person`); `twin_of` is the `entity_id` of the near twin (deliverable 5), empty otherwise; only resolvable records (7.1.1) get a row; relationship and `Sanction` records use PHASE-1.md 4.4's edge id form with the prefix `syn`. Benchmark records set no `nr.source_ref`, so D5 never links them.
8. CLI: `neonradar synth er-bench --size small|large --seed 20261026 --out <dir>`.
9. The committed fixture `data/fixtures/er-bench/` (size `small`, seed `20261026`): `nr_synthetic-20261026-er-bench.ftm.jsonl`, its manifest and `labels/er_truth.csv`. `ingest/profiles/demo.yaml` gains it in `fixtures` (`[data/fixtures/demo-mini, data/fixtures/er-bench]`), so `ingest build --profile demo` validates it and the resolver reads it (7.8 lists the demo profile as M2.2 ships it).
10. The Phase 1 generator (M1.8e) sets `nr.share_pct_min_exclusive` and `nr.share_pct_max_exclusive` on its share bands as 5.1 says (and the band keys on any voting-rights `Control` it generates), and `data/fixtures/demo-mini` is regenerated; only those fields may change (the pull request shows the diff).
11. Tests: same seed gives byte-identical files; every resolvable record has exactly one truth row and no other record has one; the fixture validates in strict mode; style and variation shares within 3 percentage points of the targets on `large`; every hard negative exists and differs from its twin in `entity_id`; no generated name contains a denylisted name; every id starts with `syn-` (the fixture check); every record has the `nr.synthetic_kind` of its style and every `Sanction` of a `list` record is `list`; no person with a `list` or `leak` record has a surname from the Faker surname lists; no entity has two `list` records under one authority; every record with an `SY` number has `jurisdiction: gb`.

**Acceptance.**

```bash
uv run neonradar synth er-bench --size small --seed 20261026 --out /tmp/a
uv run neonradar synth er-bench --size small --seed 20261026 --out /tmp/b
diff /tmp/a/*.ftm.jsonl /tmp/b/*.ftm.jsonl && diff -r /tmp/a/labels /tmp/b/labels && echo deterministic
diff /tmp/a/*.ftm.jsonl data/fixtures/er-bench/*.ftm.jsonl && echo "fixture up to date"
uv run neonradar contracts validate-records data/fixtures/er-bench/*.ftm.jsonl --strict
uv run neonradar ingest build --profile demo         # validates demo-mini and er-bench
uv run pytest ingest/tests/test_erbench.py -q
make check && make hygiene LABELS=size-exception
```

(Only the manifests' `created_at` may differ between runs, as in M1.8e.)

**Review focus (humans).** Graph mentor: would a resolver that only lower-cases names score well here? If yes, the benchmark is too easy. Data steward: read 30 generated names in each script, including the invented surnames of listed and leaked people; do any belong to a real public figure, or read as a real family name?

### M2.10 Resolver (three sub-milestones)

The resolver turns C1 records into a resolution run (7.1.8). Read section 7.1 in full before any of these. Every sub-milestone runs `data-guardian` in step 7 of the protocol and reports the benchmark numbers before and after in "Matching impact".

#### M2.10a Resolver core: records, rules, policy and constrained clustering

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (data steward, project lead and tech lead accept ADR-0015) |
| Depends on | M2.2, M2.8, M2.9 |
| Branch | `p2/m2-10a-resolver-core` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | Yes |
| Size | exception (the reference implementation and its tests are verbatim from this spec) |
| ADR | ADR-0015 (merge policy for listed and leaked records) |
| Real-data run | none |

**Goal.** Everything except the probabilistic model: the resolver can already run deterministic rules and the merge policy end to end and write a valid run, so the loader (M2.11) and the Splink work (M2.10b) proceed in parallel.

**Deliverables.**

1. `resolve/src/neonradar_resolve/records.py`: streams the C1 files of the record folders it is given (the CLI resolves them with `Profile.record_dirs()`; `neonradar_resolve` never imports `neonradar_ingest` or `neonradar_cli`, 4.2), keeps the resolvable records (7.1.1) and, from the relationship records, each record's context: the organisations it is linked to (`Directorship`, `Ownership`, `Control`, `Representation`, `UnknownLink`), and for listed records their `Sanction` entities (`authority`, `authorityId`, `unscId`, dataset). Dataset `kind` and `anchor_priority` come from `contracts/datasets.yaml`. Reads the ICIJ `*-hints.csv` side files (M2.5 writes no address hints) as `(record_a, record_b, hint)` tuples.
2. `resolve/src/neonradar_resolve/schemas.py`: `common_schema(names) -> str | None`, folding `followthemoney.model.common_schema(left, right)` over the names and returning `None` when it raises `followthemoney.exc.InvalidData` (verified with 4.11.0: `Person` and `LegalEntity` give `Person`; `Company`, `LegalEntity` and `Organization` give `Company`; `Person` and `Company`, and `Company` and `PublicBody`, have none).
3. `resolve/src/neonradar_resolve/policy.py`: `flag_topics(topics) -> frozenset[str]`, the topics that are not purely descriptive, exactly as 7.1.1 (descriptive: `{"corp.public", "fin", "gov", "pol.party", "pol.union", "rel", "mil"}` plus every topic starting `fin.` or `gov.`); `is_listed(topics)`, true when `flag_topics` is not empty; `record_kind(dataset_kind, nr)`, the dataset's kind, except that a synthetic record whose `nr.synthetic_kind` is `list` or `leak` takes that value (so the benchmark exercises P2, M2.9); `is_leaked(kind)`.
4. `resolve/src/neonradar_resolve/features.py`: builds one `Member` per resolvable record and the person and organisation feature tables of 7.1.5. `Member` fields:
   - `kind` and `flag_topics` from `policy.py`;
   - `list_source`: the dataset of a record from a `kind: list` dataset; for a synthetic list-style record, `nr_synthetic:<authority>` of its first `Sanction` (authorities sorted);
   - `list_party`: the same value, except none for `gb_fcdo_sanctions` records whose id does not start with `uksl-g` (UK designations not grouped by OFSI Group ID, M2.6a, which may belong to one person under several regimes);
   - company numbers from `registrationNumber` through `neonradar_keys.ids.uk_company_number` when the record's jurisdiction is `gb` or a `gb-` subdivision, and always for `gbch-co-` records, whose number is a Companies House number whatever the company's jurisdiction; for `gleif-` records only when the number is already in the 8-character Companies House form (8 characters and `has_ch_prefix`: all digits or a Companies House prefix), which M2.4 writes only for the three UK registration authorities `RA000585` to `RA000587`, so that no other register's number is padded into a false Companies House number; synthetic records pass `synthetic=True`, which accepts `SY` numbers;
   - LEIs through `is_valid_lei`; birth dates as ISO prefixes; name keys through `neonradar_keys.names` from `name`, `alias` and `previousName`, never from `weakAlias` (M2.6).

   The feature tables are typed by `resolve/src/neonradar_resolve/feature_schema.py` (verbatim below; it imports `pyarrow`, whose mypy override M2.0 added) and written to a DuckDB file `features.duckdb` inside the run folder (tables `person_features` and `org_features`), deleted at the end of the run unless `--keep-features`. Tests check each column's rule in 7.1.5 and each `Member` field above on records built in the test, including NULL for every empty list.
5. `resolve/src/neonradar_resolve/rules.py`: the deterministic links D1 to D6 (7.1.2) as `Link` objects, each with its rule id (D3 on the first 8 characters of `nr.ch_person_number`; D6 only between `Address` records); and D7 from a decisions file: for each pair the newest line decides `same` or `different`, and a `same` link carries `reviewers`, the handles whose own newest line for that pair says `same`. M2.10c writes the file; this milestone reads a test fixture.
6. `resolve/src/neonradar_resolve/cluster.py`: verbatim from the end of this milestone.
7. `resolve/src/neonradar_resolve/run.py`: `run(record_dirs, run_dir, config, decisions_file=None, probabilistic=True)` builds members, links and hints, calls `cluster.resolve(...)` (no probabilistic links yet), and writes `canonical.csv` (header in 7.1.8), `candidates.jsonl`, `conflicts.jsonl` and `run.json` with sorted rows: CSV through the `csv` module with `lineterminator="\n"`, floats as Python's shortest `repr`, JSON lines with sorted keys and `ensure_ascii=False`. The CLI `neonradar er run --profile <name> [--no-probabilistic] [--no-decisions] [--keep-features]` resolves the profile's record folders, its resolution folder (`resolution_dir(profile, run_id)`) and its decisions file (`decisions_file(profile)`, so a synthetic profile never opens a path under `data/cache/real/`), passes `people.er_senior_reviewers` into `Config.senior_reviewers`, reads the configuration file named in the profile's `resolution.config` (refusing, exit 2, a profile with `resolution.enabled: false`), calls `run.run`, writes the run id into `LATEST` in the profile's resolution folder, and emits the summary (M2.2) with the counts of 7.1.8, including `decisions_on_file`, `decisions_applied`, `decisions_not_applicable`, `decisions_awaiting_second_review`, `hints_used` and `hints_not_applicable`. `--no-decisions` ignores the decisions file (evaluation runs, 7.3). On a real profile the command runs the real-data gate of M2.2 first and works inside `neonradar_cli.redact.guard()`. `--no-probabilistic` stays available after M2.10b.
8. `resolve/config/er.yaml` with the starting values of 7.1.7 (thresholds unused until M2.10b) and `neonradar er show-config`.
9. `neonradar er bench --size small|large [--seed 20261026]` (deterministic part): runs the resolver on the benchmark (the committed fixture for `small`; `large` generated into `bench_dir("large")`, M2.2), writes the run under `resolution_dir("er-bench-<size>", run_id)` (the synthetic pseudo-profiles of M2.2), compares `canonical.csv` and `candidates.jsonl` with `labels/er_truth.csv`, and prints pairwise precision, recall and F1 per class, the number of hard negatives merged (must be 0), and the recall of policy-blocked true pairs as possible matches, all as defined in 7.1.7 ("Benchmark measures"). M2.10b adds the probabilistic numbers.
10. Tests:
    - `resolve/tests/test_cluster.py`: verbatim below (the oracle for 7.1.3, 7.1.4 and 7.1.6; 38 tests).
    - `resolve/tests/test_policy.py` (G2-07, with `test_cluster.py`): `flag_topics` and `is_listed` on each descriptive and listed topic; a test that every topic in `followthemoney.types.registry.topic.names` is classified (it fails when FollowTheMoney adds one, so a human decides); `record_kind` for synthetic `list` and `leak` records; `list_source` and `list_party` for grouped and ungrouped UK ids; P1 and P2 with non-synthetic look-alike records built in the test (for example a `gb_companies_house` person and a `gb_fcdo_sanctions` person with the same name and birth date stay apart; a `gb_parliament_members` look-alike and a `us_ofac_sdn` look-alike with the same name and birth month stay apart; a D1 link between a look-alike company and a look-alike list entity with exactly the same name merges, and with "Example Group" against "Example Group UK" it does not).
    - `resolve/tests/test_rules.py`: D1 normalisation (`"1800000"` to `"01800000"`, `"SC 12345"` to `"SC012345"`, `"OC300001"` unchanged, `"ABC"` and `"HE123456"` rejected, `"SY000101"` accepted only for synthetic records), D2 with a valid and an invalid check digit, D3 on the first 8 characters only, D4, D5, D6 between addresses only, D7 newest line and `reviewers`.
    - `resolve/tests/test_features.py`: the GLEIF number rule (a GB record at another registration authority gives no company number), `list_source` for a synthetic list-style record, and the column rules above.
    - `resolve/tests/test_run.py`: `er run --profile demo --no-probabilistic` writes all files, and twice gives byte-identical `canonical.csv`, `candidates.jsonl` and `conflicts.jsonl` (`run.json` holds the run id and timings, so it differs); no hard negative merged; every `nr-` id's anchor follows 7.1.6; a decision about a record outside the run is counted as not applicable; `--no-decisions` applies none.
11. `docs/decisions/0015-merge-policy-for-listed-and-leaked-records.md` (status `proposed`; deciders: data steward, project lead, tech lead): the harm a false sanctions or leak match does to a real person; why listed and leaked records merge with other sources only through identifiers with a name check or a human decision; possible matches instead, always "not confirmed"; no flag across them; the cost (some true matches stay unmerged, which the precision report counts as possible matches); cite `sanctions-peps.md` on authorities' guidance to confirm matches with identifiers, and ICIJ's warning about names. It lists the choices the deciders make, each with the spec's default: a pair that breaks X1 to X6 or X8 is never shown as a possible match (default: suppressed); a human `same` across P1 or P2 needs two reviewers or a senior reviewer (default: yes); addresses merge across datasets by D6 without P2, because addresses carry no flags (alternative: D6 within one dataset only); two listed person records from different lists merge by probability only with compatible birth years or a shared identifier (stricter alternative: a shared identifier or an exact full birth date). The form of D3 is the tech lead's choice and is recorded in ADR-0014 (M2.10b).

**Acceptance.**

```bash
uv run neonradar er run --profile demo --no-probabilistic       # summary with counts by rule
uv run neonradar er run --profile demo --no-probabilistic       # same canonical.csv, candidates.jsonl, conflicts.jsonl
uv run neonradar er bench --size small                          # deterministic numbers; 0 hard negatives merged
uv run pytest resolve/tests/test_cluster.py -q                  # 38 passed
uv run pytest resolve/tests -q
make check
```

**Review focus (humans).** Data steward and project lead: read `test_policy.py` and the choices listed in ADR-0015. Do the tests cover the cases you worry about? Graph mentor: read `cluster.py` against 7.1.6. Can a merge, or a possible match that a hard rule forbids, happen through any path the policy does not allow?

**`resolve/src/neonradar_resolve/feature_schema.py`** (verbatim):

```python
"""Feature tables for the Splink models (PHASE-2.md 7.1.5). `features.py` (M2.10a) writes them;
`models.py` (M2.10b) reads them. One row per resolvable record; every empty list is NULL.
"""

from __future__ import annotations

import pyarrow as pa

PERSON_SCHEMA = pa.schema(
    [
        ("unique_id", pa.string()),
        ("synthetic", pa.bool_()),
        ("name_key", pa.string()),  # neonradar_keys PersonKey.key
        ("name_key_rare", pa.string()),  # name_key when at most RARE_NAME_MAX records share it
        ("forename", pa.string()),  # first given-name token, when the source says which it is
        ("surname", pa.string()),  # first family-name token, when known
        ("initial", pa.string()),  # first letter of forename
        ("name_tokens", pa.list_(pa.string())),
        ("name_symbols", pa.list_(pa.string())),  # Wikidata QIDs of name groups
        ("skeletons", pa.list_(pa.string())),
        ("birth_full", pa.list_(pa.string())),  # yyyy-mm-dd values
        ("birth_ym", pa.list_(pa.string())),  # yyyy-mm values, including those of full dates
        ("birth_years", pa.list_(pa.int32())),
        ("birth_year_min", pa.int32()),
        ("birth_ym_min", pa.string()),
        ("countries", pa.list_(pa.string())),  # nationality, citizenship and residence codes
        ("postcode", pa.string()),  # one normalised UK postcode, or NULL
        ("linked_orgs", pa.list_(pa.string())),  # company keys of linked organisations
        ("identifiers", pa.list_(pa.string())),  # passport and national id numbers
    ]
)

ORG_SCHEMA = pa.schema(
    [
        ("unique_id", pa.string()),
        ("synthetic", pa.bool_()),
        ("name_key", pa.string()),  # neonradar_keys OrgKey.key
        ("name_key_rare", pa.string()),
        ("name_prefix", pa.string()),  # first four characters of name_key
        ("aliases", pa.list_(pa.string())),  # org keys of every name, alias and previous name
        ("ch_same_as", pa.string()),  # neonradar_keys ch_same_as_key
        ("name_tokens", pa.list_(pa.string())),
        ("jurisdiction", pa.string()),
        ("registration_numbers", pa.list_(pa.string())),
        ("incorporation_year", pa.int32()),
        ("postcode", pa.string()),
        ("legal_forms", pa.list_(pa.string())),
    ]
)

RARE_NAME_MAX = 50  # name_key_rare is NULL for keys shared by more records (no huge blocks)
```

**`resolve/src/neonradar_resolve/cluster.py`** (verbatim):

```python
"""Constrained clustering for NeonRadar entity resolution (PHASE-2.md 7.1.6).

Pure Python and deterministic: the same members, links, hints and config give the same result.
Splink scores pairs; this module decides merges and possible matches, applying the cannot-link
rules X1 to X8 and the merge policy P1 to P6 (PHASE-2.md 7.1.3 and 7.1.4).
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field, replace

from neonradar_keys.names import name_similarity

NAME_CHECK_RULES = frozenset({"D1", "D2", "D3", "D4"})
PROBABILITY_DECIMALS = 9  # Splink's floats can differ in the last bits between runs
RULE_ORDER = {"D1": 1, "D2": 2, "D3": 3, "D4": 4, "D5": 5, "D6": 6}
CONFLICT_ORDER = ("rule", "record_a", "record_b", "link_method", "link_rule")
COUNTS = (
    "decisions_applied",
    "decisions_awaiting_second_review",
    "decisions_not_applicable",
    "hints_not_applicable",
    "hints_used",
)


@dataclass(frozen=True)
class Member:
    """What the clustering needs to know about one resolvable record (7.1.1)."""

    record_id: str
    dataset: str
    kind: str  # registry | list | leak | synthetic (7.1.1: a synthetic record may be list or leak)
    priority: int  # anchor_priority (contracts/datasets.yaml)
    schema: str
    entity_class: str  # person | org | legal_entity | address
    synthetic: bool
    flag_topics: frozenset[str] = frozenset()  # the record's non-descriptive topics; listed if any
    list_source: str | None = None  # the list a listed record comes from (P6)
    list_party: str | None = None  # set when the record is a whole party of that list (X6)
    company_numbers: frozenset[str] = frozenset()  # the record's own UK company number(s)
    leis: frozenset[str] = frozenset()
    birth_dates: frozenset[str] = frozenset()  # ISO prefixes: 1979, 1979-08, 1979-08-23
    name_keys: frozenset[str] = frozenset()  # from name, alias and previousName, never weakAlias


@dataclass(frozen=True)
class Link:
    record_a: str
    record_b: str
    method: str  # deterministic | probabilistic | human
    rule: str | None = None  # D1 to D7
    probability: float = 1.0
    weight: float | None = None
    features: Mapping[str, str] = field(default_factory=dict)
    strong_evidence: bool = True  # P3: a non-name comparison agrees at a strong level
    birth_or_id_agrees: bool = True  # P6: birth years compatible, or an identifier shared
    model: str | None = None  # person | org: the Splink model that scored a probabilistic link
    reviewers: frozenset[str] = frozenset()  # D7: handles whose newest decision is "same"


@dataclass(frozen=True)
class Config:
    merge_threshold: Mapping[str, float]  # Splink model -> threshold
    candidate_threshold: float
    cluster_cap: int = 30
    name_check_jaro_winkler: float = 0.85
    senior_reviewers: frozenset[str] = frozenset()  # people.er_senior_reviewers


@dataclass
class Candidate:
    record_a: str
    record_b: str
    probability: float | None
    weight: float | None
    method: str  # probabilistic | deterministic | source_hint
    rule: str | None
    reasons: set[str]
    features: Mapping[str, str]


@dataclass
class Result:
    canonical: list[dict[str, object]]
    candidates: list[dict[str, object]]
    conflicts: list[dict[str, object]]
    counts: dict[str, int]


def dates_compatible(left: frozenset[str], right: frozenset[str]) -> bool:
    """X5: compatible when some pair is equal at the precision both have."""
    if not left or not right:
        return True
    return any(a.startswith(b) or b.startswith(a) for a in left for b in right)


def name_check(a: Member, b: Member, threshold: float, strict: bool) -> bool:
    """7.1.2: an exact shared name key; unless strict, also a Jaro-Winkler match."""
    if a.name_keys & b.name_keys:
        return True
    if strict:
        return False
    return any(name_similarity(x, y) >= threshold for x in a.name_keys for y in b.name_keys)


def flags(ms: list[Member]) -> frozenset[str]:
    return frozenset(t for m in ms for t in m.flag_topics)


def p1_reason(left: list[Member], right: list[Member]) -> str | None:
    """P1: merging would give records flag topics they do not have themselves."""
    fl, fr = flags(left), flags(right)
    if fl == fr:
        return None
    return "listed_unlisted" if not fl or not fr else "listed_differently"


def crosses_p2(left: list[Member], right: list[Member]) -> bool:
    """P2: merging would join a leaked record with a record from another kind of source."""
    kl, kr = {m.kind == "leak" for m in left}, {m.kind == "leak" for m in right}
    return (True in kl and False in kr) or (False in kl and True in kr)


def hard_conflict(
    left: list[Member],
    right: list[Member],
    different: set[frozenset[str]],
    common_schema: Callable[[Iterable[str]], str | None],
) -> str | None:
    """The first of X1 to X6 and X8 that merging the two clusters would break (X7 is separate)."""
    both = left + right
    if len({m.synthetic for m in both}) > 1:
        return "X1"
    if common_schema(sorted({m.schema for m in both})) is None:
        return "X2"
    if len({n for m in both for n in m.company_numbers}) > 1:
        return "X3"
    if len({n for m in both for n in m.leis}) > 1:
        return "X4"
    for a in left:
        for b in right:
            if a.entity_class == b.entity_class == "person" and not dates_compatible(
                a.birth_dates, b.birth_dates
            ):
                return "X5"
    parties = {m.list_party for m in left if m.list_party}
    if parties & {m.list_party for m in right if m.list_party}:
        return "X6"
    if any(frozenset((a.record_id, b.record_id)) in different for a in left for b in right):
        return "X8"
    return None


class _Clusters:
    def __init__(self, members: Iterable[Member]) -> None:
        self.members = {m.record_id: m for m in members}
        self.parent = {rid: rid for rid in self.members}
        self.items: dict[str, list[str]] = {rid: [rid] for rid in self.members}

    def find(self, rid: str) -> str:
        while self.parent[rid] != rid:
            self.parent[rid] = self.parent[self.parent[rid]]
            rid = self.parent[rid]
        return rid

    def records(self, root: str) -> list[Member]:
        return [self.members[r] for r in self.items[root]]

    def union(self, a: str, b: str) -> None:
        ra, rb = sorted((self.find(a), self.find(b)))
        self.parent[rb] = ra
        self.items[ra] = sorted(self.items[ra] + self.items.pop(rb))


def resolve(
    members: Iterable[Member],
    deterministic: Iterable[Link],
    probabilistic: Iterable[Link],
    human_same: Iterable[Link],
    human_different: Iterable[tuple[str, str]],
    hints: Iterable[tuple[str, str, str]],
    config: Config,
    common_schema: Callable[[Iterable[str]], str | None],
) -> Result:
    clusters = _Clusters(members)
    known = clusters.members
    counts = dict.fromkeys(COUNTS, 0)
    different: set[frozenset[str]] = set()
    for x, y in human_different:
        if x in known and y in known:
            different.add(frozenset((x, y)))
            counts["decisions_applied"] += 1
        else:
            counts["decisions_not_applicable"] += 1
    accepted: list[Link] = []
    candidates: list[Candidate] = []
    conflicts: list[dict[str, object]] = []

    def conflict(rule: str, a: str, b: str, method: str, link_rule: str | None) -> None:
        ra, rb = sorted((a, b))
        conflicts.append(
            {
                "rule": rule,
                "record_a": ra,
                "record_b": rb,
                "link_method": method,
                "link_rule": link_rule,
            }
        )

    def possible(link: Link, reason: str) -> None:
        a, b = sorted((link.record_a, link.record_b))
        probabilistic_link = link.method == "probabilistic"
        candidates.append(
            Candidate(
                a,
                b,
                link.probability if probabilistic_link else None,
                link.weight if probabilistic_link else None,
                link.method,
                link.rule if link.method == "deterministic" else None,
                {reason},
                dict(link.features),
            )
        )

    def sides(link: Link) -> tuple[list[Member], list[Member]] | None:
        for rid in (link.record_a, link.record_b):
            if rid not in known:
                raise ValueError(f"link to unknown record {rid}")
        ra, rb = clusters.find(link.record_a), clusters.find(link.record_b)
        return None if ra == rb else (clusters.records(ra), clusters.records(rb))

    def merge(link: Link) -> None:
        clusters.union(link.record_a, link.record_b)
        accepted.append(link)

    # D7: human "same" decisions first; they check X1 and X2 only (7.1.6).
    for link in sorted(human_same, key=lambda x: (x.record_a, x.record_b)):
        if link.record_a not in known or link.record_b not in known:
            counts["decisions_not_applicable"] += 1
            continue
        pair = sides(link)
        if pair is None:
            counts["decisions_applied"] += 1
            continue
        left, right = pair
        crossing = p1_reason(left, right) is not None or crosses_p2(left, right)
        if crossing and len(link.reviewers) < 2 and not link.reviewers & config.senior_reviewers:
            counts["decisions_awaiting_second_review"] += 1
            continue
        both = left + right
        rule = "X1" if len({m.synthetic for m in both}) > 1 else None
        if rule is None and common_schema(sorted({m.schema for m in both})) is None:
            rule = "X2"
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        merge(link)
        counts["decisions_applied"] += 1

    # D1 to D6, in rule order, then by record ids.
    for link in sorted(
        deterministic, key=lambda x: (RULE_ORDER[x.rule or ""], x.record_a, x.record_b)
    ):
        pair = sides(link)
        if pair is None:
            continue
        left, right = pair
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        too_big = len(left) + len(right) > config.cluster_cap
        a, b = known[link.record_a], known[link.record_b]
        if "address" in (a.entity_class, b.entity_class):  # D6: addresses carry no flags
            if too_big:
                conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            else:
                merge(link)
            continue
        crossing = p1_reason(left, right) is not None or crosses_p2(left, right)
        needs_check = link.rule in NAME_CHECK_RULES or crossing
        if needs_check and not name_check(a, b, config.name_check_jaro_winkler, strict=crossing):
            possible(link, "identifier_name_mismatch")
        elif too_big:
            conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            possible(link, "cluster_cap")
        else:
            merge(link)

    # Probabilistic pairs, by rounded probability descending, then by record ids.
    rounded = [
        replace(x, probability=round(x.probability, PROBABILITY_DECIMALS)) for x in probabilistic
    ]
    for link in sorted(rounded, key=lambda x: (-x.probability, x.record_a, x.record_b)):
        if link.probability < config.candidate_threshold:
            continue
        pair = sides(link)
        if pair is None:
            continue
        left, right = pair
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:
            conflict(rule, link.record_a, link.record_b, link.method, link.rule)
            continue
        if link.model is None:
            raise ValueError(f"probabilistic link {link.record_a} {link.record_b} has no model")
        a, b = known[link.record_a], known[link.record_b]
        reason = p1_reason(left, right)
        if link.probability < config.merge_threshold[link.model]:
            possible(link, "below_merge_threshold")
        elif reason is not None:
            possible(link, reason)
        elif crosses_p2(left, right):
            possible(link, "leaked_cross_source")
        elif not link.strong_evidence:
            possible(link, "name_only")
        elif (
            a.entity_class == b.entity_class == "person"
            and a.list_source is not None
            and b.list_source is not None
            and a.list_source != b.list_source
            and not link.birth_or_id_agrees
        ):
            possible(link, "listed_needs_birth_date")
        elif len(left) + len(right) > config.cluster_cap:
            conflict("X7", link.record_a, link.record_b, link.method, link.rule)
            possible(link, "cluster_cap")
        else:
            merge(link)

    # Source hints (ICIJ "same as" relationships) become possible matches, never merges.
    for record_a, record_b, hint in sorted(set(hints)):
        if record_a not in known or record_b not in known:
            counts["hints_not_applicable"] += 1
            continue
        if "address" in (known[record_a].entity_class, known[record_b].entity_class):
            counts["hints_not_applicable"] += 1
            continue
        link = Link(record_a, record_b, "source_hint")
        pair = sides(link)
        if pair is None:
            counts["hints_not_applicable"] += 1
            continue
        rule = hard_conflict(pair[0], pair[1], different, common_schema)
        if rule is not None:
            conflict(rule, record_a, record_b, "source_hint", None)
            continue
        possible(link, f"source_hint:{hint}")
        counts["hints_used"] += 1

    return _output(clusters, accepted, candidates, conflicts, counts, different, common_schema)


def _output(
    clusters: _Clusters,
    accepted: list[Link],
    candidates: list[Candidate],
    conflicts: list[dict[str, object]],
    counts: dict[str, int],
    different: set[frozenset[str]],
    common_schema: Callable[[Iterable[str]], str | None],
) -> Result:
    edges: dict[str, list[tuple[str, Link]]] = {}
    for link in accepted:
        edges.setdefault(link.record_a, []).append((link.record_b, link))
        edges.setdefault(link.record_b, []).append((link.record_a, link))
    canonical_of: dict[str, str] = {}
    rows: list[dict[str, object]] = []
    for root in sorted(clusters.items):
        group = clusters.records(root)
        anchor = min(group, key=lambda m: (m.priority, m.record_id)).record_id
        cid = anchor if len(group) == 1 else "nr-" + anchor
        # Accepted links form a tree in each cluster: walk it from the anchor in id order.
        parent: dict[str, tuple[str, Link] | None] = {anchor: None}
        queue = [anchor]
        while queue:
            node = queue.pop(0)
            for other, edge in sorted(edges.get(node, []), key=lambda e: e[0]):
                if other not in parent:
                    parent[other] = (node, edge)
                    queue.append(other)
        for m in sorted(group, key=lambda x: x.record_id):
            canonical_of[m.record_id] = cid
            row: dict[str, object] = {
                "record_id": m.record_id,
                "canonical_id": cid,
                "class": m.entity_class,
                "cluster_size": len(group),
                "method": "identity" if len(group) == 1 else "anchor",
                "rule": None,
                "match_probability": None if len(group) == 1 else 1.0,
                "via": None,
                "path_methods": None,
                "features": None,
            }
            step = parent.get(m.record_id)
            if step is not None:
                via, edge = step
                methods = {edge.method}
                up = parent[via]
                while up is not None:
                    methods.add(up[1].method)
                    up = parent[up[0]]
                probabilistic_link = edge.method == "probabilistic"
                row.update(
                    method=edge.method,
                    rule=edge.rule,
                    match_probability=edge.probability if probabilistic_link else 1.0,
                    via=via,
                    path_methods="+".join(sorted(methods)),
                    features=json.dumps(dict(sorted(edge.features.items())), separators=(",", ":"))
                    if probabilistic_link
                    else None,
                )
            rows.append(row)

    def rank(c: Candidate) -> tuple[float, str, str]:
        return (-(c.probability if c.probability is not None else -1.0), c.record_a, c.record_b)

    best: dict[tuple[str, str], Candidate] = {}
    for c in candidates:
        a, b = sorted((canonical_of[c.record_a], canonical_of[c.record_b]))
        if a == b:
            continue
        current = best.get((a, b))
        if current is None:
            best[(a, b)] = replace(c, reasons=set(c.reasons))
        elif rank(c) < rank(current):
            best[(a, b)] = replace(c, reasons=current.reasons | c.reasons)
        else:
            current.reasons |= c.reasons
    out: list[dict[str, object]] = []
    for (a, b), c in sorted(best.items()):
        left = clusters.records(clusters.find(c.record_a))
        right = clusters.records(clusters.find(c.record_b))
        rule = hard_conflict(left, right, different, common_schema)
        if rule is not None:  # a later merge made the two clusters incompatible
            conflicts.append(
                {
                    "rule": rule,
                    "record_a": c.record_a,
                    "record_b": c.record_b,
                    "link_method": c.method,
                    "link_rule": c.rule,
                }
            )
            continue
        record_a, record_b = (
            (c.record_a, c.record_b) if canonical_of[c.record_a] == a else (c.record_b, c.record_a)
        )
        out.append(
            {
                "a": a,
                "b": b,
                "record_a": record_a,
                "record_b": record_b,
                "match_probability": c.probability,
                "match_weight": c.weight,
                "method": c.method,
                "rule": c.rule,
                "reasons": sorted(c.reasons),
                "features": dict(sorted(c.features.items())),
            }
        )
    return Result(
        sorted(rows, key=lambda r: str(r["record_id"])),
        out,
        sorted(conflicts, key=lambda r: tuple(str(r[k]) for k in CONFLICT_ORDER)),
        counts,
    )
```

**`resolve/tests/test_cluster.py`** (verbatim):

```python
"""Oracle tests for the constrained clustering (PHASE-2.md 7.1)."""

from __future__ import annotations

import json
from collections.abc import Iterable

from neonradar_resolve.cluster import Config, Link, Member, dates_compatible, resolve

PARENTS = {
    "Person": "LegalEntity",
    "Organization": "LegalEntity",
    "Company": "Organization",
    "PublicBody": "Organization",
    "LegalEntity": None,
    "Address": None,
}

UK, EU, OFAC = "gb_fcdo_sanctions", "eu_fsf", "us_ofac_sdn"


def lineage(schema: str | None) -> list[str]:
    out = []
    while schema:
        out.append(schema)
        schema = PARENTS[schema]
    return out


def common_schema(schemas: Iterable[str]) -> str | None:
    """Stand-in for followthemoney.model.common_schema: the most specific schema, if one chain."""
    items = list(schemas)
    best = items[0]
    for s in items[1:]:
        if best in lineage(s):
            best = s
        elif s not in lineage(best):
            return None
    return best


CONFIG = Config(
    merge_threshold={"person": 0.99, "org": 0.995},
    candidate_threshold=0.80,
    senior_reviewers=frozenset({"@senior"}),
)


def person(
    rid,
    dataset="gb_companies_house",
    kind="registry",
    priority=1,
    flags=(),
    source=None,
    party=None,
    synthetic=False,
    dobs=(),
    names=("john smith",),
    schema="Person",
    entity_class="person",
):
    return Member(
        rid,
        dataset,
        kind,
        priority,
        schema,
        entity_class,
        synthetic,
        flag_topics=frozenset(flags),
        list_source=source,
        list_party=party,
        birth_dates=frozenset(dobs),
        name_keys=frozenset(names),
    )


def listed(rid, dataset=UK, priority=3, flags=("sanction",), party=True, **kw):
    """A sanctions list record; party=False marks a UK record not grouped by OFSI Group ID."""
    return person(
        rid,
        dataset=dataset,
        kind="list",
        priority=priority,
        flags=flags,
        source=dataset,
        party=dataset if party else None,
        **kw,
    )


def org(
    rid,
    number=None,
    lei=None,
    dataset="gb_companies_house",
    kind="registry",
    priority=1,
    flags=(),
    names=("falcon ridge trading",),
    schema="Company",
):
    return Member(
        rid,
        dataset,
        kind,
        priority,
        schema,
        "org",
        False,
        flag_topics=frozenset(flags),
        list_source=dataset if kind == "list" else None,
        list_party=dataset if kind == "list" else None,
        company_numbers=frozenset([number]) if number else frozenset(),
        leis=frozenset([lei]) if lei else frozenset(),
        name_keys=frozenset(names),
    )


def address(rid, dataset="gb_companies_house", kind="registry"):
    return Member(rid, dataset, kind, 1, "Address", "address", False)


def prob(a, b, p=0.999, strong=True, birth_or_id=True, model="person"):
    return Link(
        a, b, "probabilistic", None, p, 9.0, {"name": "exact"}, strong, birth_or_id, model=model
    )


def det(a, b, rule):
    return Link(a, b, "deterministic", rule)


def same(a, b, *reviewers):
    return Link(a, b, "human", "D7", reviewers=frozenset(reviewers or ("@labeller",)))


def canon(result):
    return {r["record_id"]: r["canonical_id"] for r in result.canonical}


def reasons(result):
    return {(c["a"], c["b"]): c["reasons"] for c in result.candidates}


def rules(result):
    return [c["rule"] for c in result.conflicts]


def run(members, det_links=(), prob_links=(), same_links=(), different=(), hints=(), config=CONFIG):
    return resolve(
        members, det_links, prob_links, same_links, different, hints, config, common_schema
    )


def test_dates_compatible():
    assert dates_compatible(frozenset({"1979-08"}), frozenset({"1979-08-23"}))
    assert dates_compatible(frozenset({"1979"}), frozenset({"1979-08"}))
    assert not dates_compatible(frozenset({"1979-08"}), frozenset({"1979-09"}))
    assert dates_compatible(frozenset({"1979-08", "1980"}), frozenset({"1980-02-01"}))
    assert dates_compatible(frozenset(), frozenset({"1980"}))


def test_probabilistic_merge_anchor_and_output_columns():
    r = run(
        [person("gbch-psc-b"), person("gbch-off-a")], prob_links=[prob("gbch-off-a", "gbch-psc-b")]
    )
    assert canon(r) == {"gbch-off-a": "nr-gbch-off-a", "gbch-psc-b": "nr-gbch-off-a"}
    rows = {x["record_id"]: x for x in r.canonical}
    assert rows["gbch-off-a"]["method"] == "anchor" and rows["gbch-off-a"]["via"] is None
    joined = rows["gbch-psc-b"]
    assert joined["method"] == "probabilistic" and joined["via"] == "gbch-off-a"
    assert joined["path_methods"] == "probabilistic"
    assert json.loads(str(joined["features"])) == {"name": "exact"}


def test_path_methods_cover_the_whole_path_from_the_anchor():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-x", number="00000001"),
        org("gleif-y"),
    ]
    links = [det("gbch-co-00000001", "gbch-psc-x", "D1")]
    r = run(
        members, det_links=links, prob_links=[prob("gbch-psc-x", "gleif-y", 0.999, model="org")]
    )
    rows = {x["record_id"]: x for x in r.canonical}
    assert rows["gbch-psc-x"]["path_methods"] == "deterministic"
    assert rows["gbch-psc-x"]["features"] is None
    assert rows["gleif-y"]["via"] == "gbch-psc-x"
    assert rows["gleif-y"]["path_methods"] == "deterministic+probabilistic"


def test_anchor_prefers_dataset_priority():
    members = [
        listed("uksl-g7"),
        listed("unsc-9", dataset="un_sc_sanctions", priority=4),
    ]
    r = run(members, prob_links=[prob("uksl-g7", "unsc-9")])
    assert set(canon(r).values()) == {"nr-uksl-g7"}


def test_singleton_keeps_its_id():
    r = run([person("gbch-off-a")])
    assert r.canonical[0]["canonical_id"] == "gbch-off-a"
    assert r.canonical[0]["method"] == "identity"


def test_x1_synthetic_and_real_never_merge():
    syn = person("syn-p-1", dataset="nr_synthetic", kind="synthetic", priority=10, synthetic=True)
    r = run([syn, person("gbch-off-a")], same_links=[same("syn-p-1", "gbch-off-a")])
    assert canon(r)["syn-p-1"] == "syn-p-1"
    assert rules(r) == ["X1"]


def test_x2_person_and_company_never_merge():
    r = run(
        [person("gbch-off-a"), org("gbch-co-1", names=("john smith",))],
        prob_links=[prob("gbch-off-a", "gbch-co-1")],
    )
    assert canon(r)["gbch-off-a"] == "gbch-off-a"
    assert rules(r) == ["X2"]


def test_x3_two_company_numbers_through_a_chain():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-x"),
        org("gbch-co-00000002", number="00000002"),
    ]
    links = [
        prob("gbch-co-00000001", "gbch-psc-x", 0.9999, model="org"),
        prob("gbch-psc-x", "gbch-co-00000002", 0.9998, model="org"),
    ]
    r = run(members, prob_links=links)
    assert canon(r)["gbch-psc-x"] == "nr-gbch-co-00000001"
    assert canon(r)["gbch-co-00000002"] == "gbch-co-00000002"
    assert rules(r) == ["X3"] and r.candidates == []


def test_x3_pair_below_the_merge_threshold_is_not_a_possible_match():
    members = [org("gbch-co-00000001", number="00000001"), org("gbch-psc-x", number="00000002")]
    r = run(members, prob_links=[prob("gbch-co-00000001", "gbch-psc-x", 0.95, model="org")])
    assert r.candidates == [] and rules(r) == ["X3"]


def test_x4_two_leis():
    members = [
        org("gleif-A", lei="549300AAAAAAAAAAAA00"),
        org("gleif-B", lei="549300BBBBBBBBBBBB00"),
    ]
    r = run(members, prob_links=[prob("gleif-A", "gleif-B", 0.9999, model="org")])
    assert canon(r) == {"gleif-A": "gleif-A", "gleif-B": "gleif-B"}
    assert rules(r) == ["X4"] and r.candidates == []


def test_x5_birth_dates_block_transitive_merge():
    members = [person("a", dobs=["1980-05"]), person("b"), person("c", dobs=["1981-03"])]
    r = run(members, prob_links=[prob("a", "b", 0.9999), prob("b", "c", 0.9995)])
    assert canon(r)["b"] == "nr-a" and canon(r)["c"] == "c"
    assert rules(r) == ["X5"]


def test_x5_suppresses_a_possible_match_with_a_listed_record():
    members = [person("gbch-off-a", dobs=["1975-04"]), listed("uksl-g1", dobs=["1975-03"])]
    r = run(members, prob_links=[prob("gbch-off-a", "uksl-g1", 0.9999)])
    assert r.candidates == [] and rules(r) == ["X5"]


def test_x6_two_parties_of_one_list():
    r = run([listed("uksl-g1"), listed("uksl-g2")], prob_links=[prob("uksl-g1", "uksl-g2")])
    assert canon(r)["uksl-g2"] == "uksl-g2" and rules(r) == ["X6"]


def test_x6_ungrouped_uk_designations_of_one_person_may_merge():
    members = [listed("uksl-11111", party=False), listed("uksl-g2")]
    r = run(members, prob_links=[prob("uksl-11111", "uksl-g2", 0.9999)])
    assert canon(r)["uksl-11111"] == "nr-uksl-11111"


def test_party_with_several_designations_merges_with_its_eu_entry_by_d4():
    members = [
        listed("uksl-g1", names=("ivan petrov",)),
        listed("eufsf-2", EU, 5, names=("ivan petrov",)),
    ]
    r = run(members, det_links=[det("uksl-g1", "eufsf-2", "D4")])
    assert canon(r)["eufsf-2"] == "nr-uksl-g1" and r.conflicts == []


def test_x7_cluster_cap_becomes_possible_match():
    members = [person(f"p{i:02d}") for i in range(32)]
    links = [prob("p00", f"p{i:02d}", 0.9999 - i / 100000) for i in range(1, 32)]
    r = run(members, prob_links=links)
    assert max(x["cluster_size"] for x in r.canonical) == 30
    assert any("cluster_cap" in v for v in reasons(r).values())


def test_x8_human_different_wins_over_probability():
    r = run(
        [person("a"), person("b")], prob_links=[prob("a", "b", 0.99999)], different=[("a", "b")]
    )
    assert canon(r) == {"a": "a", "b": "b"} and rules(r) == ["X8"]
    assert r.candidates == [] and r.counts["decisions_applied"] == 1


def test_different_decision_removes_possible_matches():
    members = [person("gbch-off-a"), listed("uksl-g1"), person("gbch-off-b")]
    links = [prob("gbch-off-a", "uksl-g1", 0.9999), prob("gbch-off-a", "gbch-off-b", 0.95)]
    different = [("gbch-off-a", "uksl-g1"), ("gbch-off-a", "gbch-off-b")]
    r = run(members, prob_links=links, different=different)
    assert r.candidates == [] and rules(r) == ["X8", "X8"]


def test_p1_listed_and_unlisted_only_possible_match():
    r = run(
        [person("gbch-off-a"), listed("uksl-g1")],
        prob_links=[prob("gbch-off-a", "uksl-g1", 0.99999)],
    )
    assert canon(r) == {"gbch-off-a": "gbch-off-a", "uksl-g1": "uksl-g1"}
    assert reasons(r)[("gbch-off-a", "uksl-g1")] == ["listed_unlisted"]


def test_p1_records_listed_for_different_reasons_never_merge_by_probability():
    pep = listed("ukparl-1", "gb_parliament_members", 7, flags=("role.pep",), dobs=["1970-02"])
    sanctioned = listed("ofac-5", OFAC, 6, dobs=["1970-02"])
    r = run([pep, sanctioned], prob_links=[prob("ofac-5", "ukparl-1", 0.999)])
    assert canon(r) == {"ofac-5": "ofac-5", "ukparl-1": "ukparl-1"}
    assert reasons(r)[("ofac-5", "ukparl-1")] == ["listed_differently"]


def test_p1_deterministic_with_name_check_merges():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("uksl-g7", number="00000001", dataset=UK, kind="list", priority=3, flags=("sanction",)),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "uksl-g7", "D1")])
    assert canon(r)["uksl-g7"] == "nr-gbch-co-00000001"


def test_identifier_link_across_p1_needs_an_exact_name_key():
    members = [
        org("gbch-co-00000001", number="00000001", names=("x group uk",)),
        org(
            "uksl-g7",
            number="00000001",
            dataset=UK,
            kind="list",
            priority=3,
            flags=("sanction",),
            names=("x group",),
        ),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "uksl-g7", "D1")])
    assert canon(r)["uksl-g7"] == "uksl-g7"
    [candidate] = r.candidates
    assert candidate["reasons"] == ["identifier_name_mismatch"] and candidate["rule"] == "D1"
    assert candidate["match_probability"] is None and candidate["method"] == "deterministic"


def test_name_check_failure_keeps_records_apart():
    members = [
        org("gbch-co-00000001", number="00000001"),
        org("gbch-psc-z", number="00000001", names=("quarry lane instruments",)),
    ]
    r = run(members, det_links=[det("gbch-co-00000001", "gbch-psc-z", "D1")])
    assert canon(r)["gbch-psc-z"] == "gbch-psc-z"
    assert reasons(r)[("gbch-co-00000001", "gbch-psc-z")] == ["identifier_name_mismatch"]


def test_d3_needs_the_name_check():
    members = [
        person("gbch-off-a", names=("john smith",)),
        person("gbch-off-b", names=("mary jones",)),
    ]
    r = run(members, det_links=[det("gbch-off-a", "gbch-off-b", "D3")])
    assert reasons(r) == {("gbch-off-a", "gbch-off-b"): ["identifier_name_mismatch"]}


def test_p2_leaked_records_stay_apart():
    leak = person(
        "icij-1",
        "icij_offshore_leaks",
        "leak",
        9,
        schema="LegalEntity",
        entity_class="legal_entity",
    )
    r = run([person("gbch-off-a"), leak], prob_links=[prob("gbch-off-a", "icij-1", 0.99999)])
    assert reasons(r)[("gbch-off-a", "icij-1")] == ["leaked_cross_source"]


def test_addresses_merge_by_d6_and_never_become_possible_matches():
    members = [address("gbch-addr-1"), address("icij-addr-2", "icij_offshore_leaks", "leak")]
    r = run(members, det_links=[det("gbch-addr-1", "icij-addr-2", "D6")])
    assert canon(r)["icij-addr-2"] == "nr-gbch-addr-1" and r.candidates == []
    many = [address(f"a{i:02d}") for i in range(32)]
    links = [det("a00", f"a{i:02d}", "D6") for i in range(1, 32)]
    r = run(many, det_links=links)
    assert max(x["cluster_size"] for x in r.canonical) == 30
    assert r.candidates == [] and set(rules(r)) == {"X7"}


def test_p3_name_only_never_merges():
    r = run([person("a"), person("b")], prob_links=[prob("a", "b", 0.99999, strong=False)])
    assert reasons(r)[("a", "b")] == ["name_only"]


def test_p5_below_merge_threshold():
    r = run(
        [person("a"), person("b"), person("c")],
        prob_links=[prob("a", "b", 0.95), prob("a", "c", 0.5)],
    )
    assert reasons(r) == {("a", "b"): ["below_merge_threshold"]}


def test_merge_threshold_follows_the_scoring_model():
    officers = [
        person(
            f"icij-{i}",
            "icij_offshore_leaks",
            "leak",
            9,
            schema="LegalEntity",
            entity_class="legal_entity",
        )
        for i in (1, 2)
    ]
    r = run(officers, prob_links=[prob("icij-1", "icij-2", 0.9999, model="person")])
    assert canon(r)["icij-2"] == "nr-icij-1"
    r = run(officers, prob_links=[prob("icij-1", "icij-2", 0.9940, model="org")])
    assert reasons(r) == {("icij-1", "icij-2"): ["below_merge_threshold"]}


def test_p6_listed_people_on_two_lists_need_birth_or_id():
    a, b = listed("uksl-g1"), listed("eufsf-2", EU, 5)
    r = run([a, b], prob_links=[prob("uksl-g1", "eufsf-2", 0.99999, birth_or_id=False)])
    assert reasons(r)[("eufsf-2", "uksl-g1")] == ["listed_needs_birth_date"]
    r2 = run([a, b], prob_links=[prob("uksl-g1", "eufsf-2", 0.99999, birth_or_id=True)])
    assert canon(r2)["eufsf-2"] == "nr-uksl-g1"


def test_human_same_overrides_policy_with_a_second_reviewer():
    members = [person("gbch-off-a"), listed("uksl-g1")]
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@one", "@two")])
    assert canon(r)["uksl-g1"] == "nr-gbch-off-a"
    assert {x["record_id"]: x["method"] for x in r.canonical}["uksl-g1"] == "human"


def test_human_same_across_p1_waits_for_a_second_reviewer():
    members = [person("gbch-off-a"), listed("uksl-g1")]
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@one")])
    assert canon(r)["uksl-g1"] == "uksl-g1"
    assert r.counts["decisions_awaiting_second_review"] == 1
    r = run(members, same_links=[same("gbch-off-a", "uksl-g1", "@senior")])
    assert canon(r)["uksl-g1"] == "nr-gbch-off-a"
    r = run([person("a"), person("b")], same_links=[same("a", "b", "@one")])
    assert canon(r)["b"] == "nr-a" and r.counts["decisions_applied"] == 1


def test_decisions_about_records_outside_the_run_are_skipped():
    r = run([person("a")], same_links=[same("a", "gone")], different=[("a", "gone-too")])
    assert canon(r) == {"a": "a"} and r.counts["decisions_not_applicable"] == 2


def test_source_hints_become_possible_matches_without_probability():
    members = [
        person(
            f"icij-{i}",
            "icij_offshore_leaks",
            "leak",
            9,
            schema="LegalEntity",
            entity_class="legal_entity",
        )
        for i in (1, 2)
    ]
    hints = [("icij-1", "icij-2", "same_name_as"), ("icij-1", "icij-9", "same_name_as")]
    r = run(members, hints=hints)
    [candidate] = r.candidates
    assert candidate["method"] == "source_hint" and candidate["match_probability"] is None
    assert candidate["reasons"] == ["source_hint:same_name_as"]
    assert r.counts["hints_used"] == 1 and r.counts["hints_not_applicable"] == 1


def test_possible_match_dropped_when_a_later_merge_breaks_a_hard_rule():
    members = [person("a", dobs=["1980-05"]), person("b"), person("c", dobs=["1981-03"])]
    links = [prob("a", "b", 0.9999, strong=False), prob("b", "c", 0.995)]
    r = run(members, prob_links=links)
    assert canon(r)["c"] == "nr-b" and r.candidates == []
    assert rules(r) == ["X5"]


def test_possible_matches_inside_one_cluster_are_dropped():
    members = [person("a"), person("b")]
    r = run(members, det_links=[det("a", "b", "D5")], prob_links=[prob("a", "b", 0.9)])
    assert r.candidates == []


def test_deterministic_output():
    members = [person(f"p{i}", dobs=[f"19{60 + i % 5}-0{1 + i % 3}"]) for i in range(40)]
    links = [
        prob(f"p{i}", f"p{(i * 7) % 40}", 0.99 + (i % 9) / 1000)
        for i in range(40)
        if i != (i * 7) % 40
    ]
    hints = [(f"p{i}", f"p{i + 1}", "similar") for i in range(0, 38, 3)]
    first = run(members, prob_links=links, hints=hints)
    second = run(
        list(reversed(members)), prob_links=list(reversed(links)), hints=list(reversed(hints))
    )
    assert first == second


def test_probabilities_are_rounded_before_ordering():
    # Probabilities that differ only after the ninth decimal count as equal, so the record ids
    # decide the order and floating-point noise between runs cannot change the result.
    members = [person("gbch-off-a"), person("gbch-off-b"), person("gbch-off-c")]
    links = [
        prob("gbch-off-a", "gbch-off-c", 0.9999999994),
        prob("gbch-off-a", "gbch-off-b", 0.9999999991),
    ]
    capped = Config(merge_threshold={"person": 0.99}, candidate_threshold=0.80, cluster_cap=2)
    r = run(members, prob_links=links, config=capped)
    assert canon(r)["gbch-off-b"] == "nr-gbch-off-a"
    assert canon(r)["gbch-off-c"] == "gbch-off-c"
    assert [c["match_probability"] for c in r.candidates] == [0.999999999]
```

#### M2.10b Splink models, calibration and the benchmark gates

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (tech lead and graph mentor accept ADR-0014) |
| Depends on | M2.10a |
| Branch | `p2/m2-10b-splink` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | Yes |
| Size | exception (the models module and its tests are verbatim from this spec) |
| ADR | ADR-0014 (entity resolution approach and thresholds) |
| Real-data run | none (thresholds come from the synthetic benchmark only; no real pair is labelled before the evaluation sample, 7.3) |

**Goal.** The probabilistic half of the resolver: two Splink 5 models scoring pairs for `cluster.resolve`, thresholds chosen on the large synthetic benchmark before the freeze on Thursday 29 October, and quality gates that CI enforces on every pull request.

**Deliverables.**

1. `resolve/src/neonradar_resolve/models.py` and `resolve/tests/test_models.py`, verbatim below. They were run on 18 October 2026 with Splink 5.0.0, DuckDB 1.5.6 and PyArrow 26.0.0 (four tests pass; one and two DuckDB threads gave identical pairs). The `pyarrow` mypy override is already in place (M2.0).
2. **`run.py` integration** (`er run` without `--no-probabilistic`): for each class, read the feature table from `features.duckdb` as a PyArrow table with its schema; register it and count comparisons with `splink.blocking_analysis.count_comparisons_from_blocking_rules(..., record_sample_proportion=1.0)` (exact counts), recording each rule's `marginal_comparison_count`; the total is the last record's `cumulative_comparison_count` (a pair found by several rules counts once); when the total exceeds `max_comparisons`, stop with exit code 4 and the counts. Open a DuckDB connection with `models.connect` (`threads` and `memory_limit` from `er.yaml`; `temp_directory` from the run configuration, which the CLI fills with `duckdb_tmp_dir(profile, run_id)` from the M2.2 layout: `data/cache/real/duckdb-tmp/<run_id>/` for a real profile, `data/cache/synthetic/duckdb-tmp/<run_id>/` otherwise), then `make_linker`, `train` (with `TrainingConfig(seed=<er.yaml seed>, ...)`), `predict(linker, kind, candidate_threshold)`. Turn each `ScoredPair` into `cluster.Link(record_a, record_b, "probabilistic", None, probability, weight, features, strong_evidence, birth_or_id_agrees, model=kind)`, so `cluster.resolve` applies `merge_threshold[kind]` of the model that scored the pair (7.1.6), and pass the links to `cluster.resolve` with the deterministic links, the human decisions and the hints of M2.10a. Delete the DuckDB temp folder in a `finally` block, so a failed run leaves no spill files.
3. **Run outputs** (7.1.8): `pairs.parquet` (record ids, class, model, probability, weight, one column per comparison with its level label; sorted by record ids); `models/person.json` and `models/org.json` from `linker.misc.save_model_to_json` (parameters only; they stay in the run folder, which for a real profile is under `data/cache/real/`); in `run.json`: the exact Splink, DuckDB and PyArrow versions, the comparison counts per blocking rule, the number of pairs scored, the levels Splink reported as untrained (counts only, from captured log warnings), and timings per step.
4. **Committed settings** `resolve/models/person.settings.json` and `org.settings.json`: `settings(kind).get_settings("duckdb").as_dict()` written with sorted keys and an indent of 2. A test regenerates them and fails on any difference, so every change to comparisons or blocking shows up in review as a diff of these files. They hold no trained parameters. (M2.10c's `test_wording_levels.py` reads them to check that every level label has investigator wording in 7.2.)
5. `neonradar er blocking --profile <name>`: the comparison count per rule and, per rule, the sizes of the five largest blocks (`splink.blocking_analysis.n_largest_blocks`). For a profile with `real_data: true` it prints sizes only, never the block keys (they are names and postcodes), and the CLI emits the summary (M2.2).
6. `neonradar er calibrate --size large [--seed 20261026]`: generates the large benchmark (M2.9) into `bench_dir("large")` (M2.2) (records and `labels/er_truth.csv`, as `er bench --size large` does, M2.10a), resolves it once with every pair scored down to probability 0.50 (`candidate_threshold` 0.50 for this run only), writing the run to `resolution_dir("er-bench-large", run_id)`, and then, without scoring again, re-runs `cluster.resolve` on the stored pairs for each value `t` of 0.50, 0.80, 0.90, 0.95, 0.98, 0.99, 0.995, 0.998, 0.999 and 0.9999. For each class and each `t` it reports pairwise precision and recall with `merge_threshold = t`, and the recall of policy-blocked true pairs as possible matches with `candidate_threshold = t` (definitions below). It proposes values with the rule of 7.1.7 (merge threshold: the lowest `t` whose precision is at least 0.98; candidate threshold: the highest `t` whose policy-blocked recall is at least 0.90) and writes the table and the proposal to `docs/data/er/benchmark.md`. It never edits `er.yaml`: the tech lead and the graph mentor set the values there and in ADR-0014.
7. **`er bench` gates** (G2-05): `er bench --size small` (M2.10a) adds the probabilistic numbers and exits 1 when, at the thresholds in `er.yaml`, pairwise precision is below 0.97 or recall below 0.80 for a class, when the recall of policy-blocked true pairs as possible matches is below 0.80, or when any hard negative merged. Add it to CI's `python` job (one DuckDB thread; it must finish within 3 minutes on the runner; record the time in the pull request). If the gates fail at the starting values of 7.1.7, do not change `er.yaml`, the rules or the models to make them pass: stop, open the pull request as a draft with the calibration table, and ask the tech lead and the graph mentor to choose values (G10).
8. `resolve/config/er.yaml`: add `duckdb` (`threads: 4`, `memory_limit: 4GiB`; DuckDB reads `GB` as decimal, `er-splink.md` 7), `training` (`u_max_pairs: 1.0e7`, `em_max_pairs: 5.0e6`, `prior_recall: 0.7`; the random-sampling seed is the top-level `seed`, 7.1.7) and `max_comparisons: 20000000`, as in 7.1.7; tests and the benchmark override `threads` to 1.
9. `docs/decisions/0014-entity-resolution-approach-and-thresholds.md` (status `proposed`; deciders: tech lead and graph mentor): deterministic rules first, then the two Splink models of 7.1.5 under the merge policy of ADR-0015; the form of D3, which the tech lead chooses before the freeze (the first 8 characters of the person number with the name check, the default and what this spec builds; or blocking only, in which case D3 merges nothing and the person number only helps find candidate pairs; 1.2 and 7.1.2); why the comparisons are built from levels; the calibration table from `docs/data/er/benchmark.md` and the chosen values; why no real pair is labelled before the evaluation (the thresholds come from the synthetic benchmark only, so labels never tune them); a line "Evaluation sample seed: (set at the freeze)", which the tech lead fills in at the freeze and `er sample` then uses (7.3 rule 1); the freeze on Thursday 29 October and what a later change needs (G10); citations `fellegi_sunter_1969` and `splink_docs` (7.5).
10. Tests (synthetic only): `test_models.py` verbatim; `test_run_probabilistic.py`: `er run --profile demo` writes `pairs.parquet` and both models, twice gives byte-identical `canonical.csv`, `candidates.jsonl` and `conflicts.jsonl` (not `run.json`, which holds the run id and timings), and leaves no DuckDB temp folder; the `ScoredPair` to `Link` conversion, including `model`; a pair scored by the organisation model is judged against `merge_threshold.org`; the comparison cap (monkeypatch the counter to return 20,000,001: exit 4 before training); `er blocking` with `real_data=True` prints no key value; the committed settings files match.

**Benchmark measures**: `er bench` and `er calibrate` use the definitions in 7.1.7 (true, mergeable and policy-blocked pairs, pairwise precision and recall, recall as a possible match, hard negatives merged).

**Acceptance.**

```bash
uv run pytest resolve/tests -q
uv run neonradar er run --profile demo
uv run neonradar er bench --size small        # exit 0: the G2-05 gates pass at the configured thresholds
uv run neonradar er calibrate --size large    # writes docs/data/er/benchmark.md
test ! -e data/cache/synthetic/duckdb-tmp || test -z "$(ls -A data/cache/synthetic/duckdb-tmp)"   # no spill files left
make check
```

**Review focus (humans).** Tech lead and graph mentor: read the calibration table before accepting ADR-0014 on Thursday 29 October. Does precision stay at or above 0.98 at the chosen merge threshold with some margin, and what does the policy cost in recall? Write the evaluation sample seed into ADR-0014 when you accept it. Graph mentor: are the level labels in `features` words an investigator understands when the API shows them (7.2, "Evidence")?

**`resolve/src/neonradar_resolve/models.py`** (verbatim):

```python
"""Splink 5 models for NeonRadar entity resolution (PHASE-2.md 7.1.5).

Splink scores pairs; `cluster.py` decides merges. Feature tables come from `features.py`:
one row per resolvable record, with every empty list written as NULL (Splink's null levels
test `IS NULL`, and an empty list is not NULL in DuckDB).
"""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any, Literal

import duckdb
import pyarrow as pa
import splink.comparison_level_library as cll
import splink.comparison_library as cl
from splink import DuckDBAPI, Linker, SettingsCreator, block_on

from neonradar_resolve.feature_schema import ORG_SCHEMA, PERSON_SCHEMA, RARE_NAME_MAX

__all__ = ["ORG_SCHEMA", "PERSON_SCHEMA", "RARE_NAME_MAX", "predict", "settings", "train"]

Kind = Literal["person", "org"]


def _person_comparisons() -> list[Any]:
    # NameComparison always adds term-frequency adjustment to its exact level, so the name
    # comparison is built from levels (er-splink.md 2.3).
    name = cl.CustomComparison(
        output_column_name="name",
        comparison_description="person name",
        comparison_levels=[
            cll.NullLevel("name_key"),
            cll.ExactMatchLevel("name_key", term_frequency_adjustments=True).configure(
                label_for_charts="name key equal"
            ),
            cll.And(
                cll.JaroWinklerLevel("forename", 0.92), cll.JaroWinklerLevel("surname", 0.92)
            ).configure(label_for_charts="forename and surname similar"),
            cll.And(cll.ExactMatchLevel("surname"), cll.ExactMatchLevel("initial")).configure(
                label_for_charts="surname equal, same initial"
            ),
            cll.ArrayIntersectLevel("name_symbols", 2).configure(
                label_for_charts="two name symbols shared"
            ),
            cll.JaroWinklerLevel("name_key", 0.88).configure(label_for_charts="name key similar"),
            cll.ExactMatchLevel("surname").configure(label_for_charts="surname equal"),
            cll.ArrayIntersectLevel("skeletons", 2).configure(
                label_for_charts="two skeletons shared"
            ),
            cll.ElseLevel(),
        ],
    )
    # DateOfBirthComparison misfiles month-year strings (er-splink.md 2.3), so birth is custom.
    birth = cl.CustomComparison(
        output_column_name="birth",
        comparison_description="birth date",
        comparison_levels=[
            cll.NullLevel("birth_years"),
            cll.ArrayIntersectLevel("birth_full", 1).configure(label_for_charts="same birth date"),
            cll.ArrayIntersectLevel("birth_ym", 1).configure(label_for_charts="same birth month"),
            cll.ArrayIntersectLevel("birth_years", 1).configure(label_for_charts="same birth year"),
            cll.CustomLevel(
                "abs(birth_year_min_l - birth_year_min_r) <= 1",
                label_for_charts="birth years one apart",
            ),
            cll.ElseLevel(),
        ],
    )
    return [
        name,
        birth,
        cl.ArrayIntersectAtSizes("countries", [1]),
        cl.PostcodeComparison("postcode"),
        cl.ArrayIntersectAtSizes("linked_orgs", [2, 1]),
        cl.ArrayIntersectAtSizes("identifiers", [1]),
    ]


def _org_comparisons() -> list[Any]:
    name = cl.CustomComparison(
        output_column_name="org_name",
        comparison_description="organisation name",
        comparison_levels=[
            cll.NullLevel("name_key"),
            cll.ExactMatchLevel("name_key", term_frequency_adjustments=True).configure(
                label_for_charts="name key equal"
            ),
            cll.ArrayIntersectLevel("aliases", 1).configure(
                label_for_charts="a name or alias shared"
            ),
            cll.ExactMatchLevel("ch_same_as").configure(
                label_for_charts="same name under the Companies House rules"
            ),
            cll.JaroWinklerLevel("name_key", 0.95).configure(
                label_for_charts="name key very similar"
            ),
            cll.JaroWinklerLevel("name_key", 0.88).configure(label_for_charts="name key similar"),
            cll.ArrayIntersectLevel("name_tokens", 2).configure(
                label_for_charts="two words shared"
            ),
            cll.ElseLevel(),
        ],
    )
    incorporation = cl.CustomComparison(
        output_column_name="incorporation",
        comparison_description="incorporation year",
        comparison_levels=[
            cll.NullLevel("incorporation_year"),
            cll.ExactMatchLevel("incorporation_year").configure(label_for_charts="same year"),
            cll.CustomLevel(
                "abs(incorporation_year_l - incorporation_year_r) <= 1",
                label_for_charts="one year apart",
            ),
            cll.ElseLevel(),
        ],
    )
    return [
        name,
        cl.ExactMatch("jurisdiction"),
        cl.ArrayIntersectAtSizes("registration_numbers", [1]),
        incorporation,
        cl.PostcodeComparison("postcode"),
        cl.ArrayIntersectAtSizes("legal_forms", [1]),
    ]


def blocking_rules(kind: Kind) -> list[Any]:
    """Every rule includes `synthetic`, so synthetic and real records are never compared (X1)."""
    if kind == "person":
        return [
            block_on("surname", "birth_year_min", "synthetic"),
            block_on("forename", "birth_ym_min", "synthetic"),
            block_on("postcode", "substr(surname, 1, 1)", "synthetic"),
            block_on("linked_orgs", "synthetic", arrays_to_explode=["linked_orgs"]),
            block_on(
                "name_symbols", "birth_year_min", "synthetic", arrays_to_explode=["name_symbols"]
            ),
            block_on("name_key_rare", "synthetic"),
        ]
    return [
        block_on("name_key", "synthetic"),
        block_on("ch_same_as", "synthetic"),
        block_on("registration_numbers", "synthetic", arrays_to_explode=["registration_numbers"]),
        block_on("aliases", "synthetic", arrays_to_explode=["aliases"]),
        block_on("postcode", "name_prefix", "synthetic"),
    ]


def settings(kind: Kind) -> SettingsCreator:
    return SettingsCreator(
        link_type="dedupe_only",
        unique_id_column_name="unique_id",
        comparisons=_person_comparisons() if kind == "person" else _org_comparisons(),
        blocking_rules_to_generate_predictions=blocking_rules(kind),
        retain_matching_columns=True,
        retain_intermediate_calculation_columns=False,
        linker_uid=f"neonradar_{kind}",
    )


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 20261026
    u_max_pairs: float = 1e7
    em_max_pairs: float | None = 5e6
    prior_recall: float = 0.7


def connect(threads: int, memory_limit: str, temp_directory: str) -> duckdb.DuckDBPyConnection:
    """DuckDB settings go on the connection; DuckDBAPI has no memory or thread options."""
    return duckdb.connect(
        ":memory:",
        config={
            "threads": threads,
            "memory_limit": memory_limit,
            "temp_directory": temp_directory,
            "preserve_insertion_order": False,
        },
    )


def make_linker(
    con: duckdb.DuckDBPyConnection, kind: Kind, table: pa.Table, model: str | None = None
) -> Linker:
    db_api = DuckDBAPI(connection=con)
    sdf = db_api.register(table, dataset_display_name=f"{kind}_features")
    return Linker(sdf, model if model is not None else settings(kind), log_level=logging.WARNING)


def train(linker: Linker, kind: Kind, config: TrainingConfig) -> None:
    """Prior, u by random sampling (seeded), then two EM sessions (er-splink.md 2.4, 3.4)."""
    t = linker.training
    if kind == "person":
        t.estimate_probability_two_random_records_match(
            [block_on("name_key", "birth_ym_min")], recall=config.prior_recall
        )
        t.estimate_u_using_random_sampling(max_pairs=config.u_max_pairs, seed=config.seed)
        t.estimate_parameters_using_expectation_maximisation(
            block_on("surname", "birth_year_min"), max_pairs=config.em_max_pairs
        )
        t.estimate_parameters_using_expectation_maximisation(
            block_on("postcode"), max_pairs=config.em_max_pairs
        )
    else:
        t.estimate_probability_two_random_records_match(
            [block_on("name_key")], recall=config.prior_recall
        )
        t.estimate_u_using_random_sampling(max_pairs=config.u_max_pairs, seed=config.seed)
        t.estimate_parameters_using_expectation_maximisation(
            block_on("name_key"), max_pairs=config.em_max_pairs
        )
        t.estimate_parameters_using_expectation_maximisation(
            block_on("postcode"), max_pairs=config.em_max_pairs
        )


def level_labels(model: Mapping[str, Any]) -> dict[str, dict[int, str]]:
    """Comparison name -> {gamma value: level label}, from a saved model dict.

    Splink gives the null level -1, the most similar level the highest value and the else
    level 0 (splink/internals/comparison.py, 5.0.0).
    """
    out: dict[str, dict[int, str]] = {}
    for comparison in model["comparisons"]:
        levels = comparison["comparison_levels"]
        counter = sum(1 for level in levels if not level.get("is_null_level")) - 1
        labels: dict[int, str] = {}
        for level in levels:
            label = str(level.get("label_for_charts") or level["sql_condition"])
            if level.get("is_null_level"):
                labels[-1] = label
            else:
                labels[counter] = label
                counter -= 1
        out[comparison["output_column_name"]] = labels
    return out


# P3 (7.1.4): agreeing evidence other than the name. P6: birth years compatible or an identifier.
STRONG_EVIDENCE: dict[Kind, dict[str, frozenset[str]]] = {
    "person": {
        "birth": frozenset({"same birth date", "same birth month"}),
        "postcode": frozenset({"Exact match on full postcode"}),
        "linked_orgs": frozenset({"Array intersection size >= 2", "Array intersection size >= 1"}),
        "identifiers": frozenset({"Array intersection size >= 1"}),
    },
    "org": {
        "registration_numbers": frozenset({"Array intersection size >= 1"}),
        "incorporation": frozenset({"same year"}),
        "postcode": frozenset({"Exact match on full postcode"}),
    },
}
BIRTH_OR_ID = {
    "birth": frozenset(
        {"same birth date", "same birth month", "same birth year", "birth years one apart"}
    ),
    "identifiers": frozenset({"Array intersection size >= 1"}),
}


@dataclass(frozen=True)
class ScoredPair:
    record_a: str
    record_b: str
    probability: float
    weight: float
    features: dict[str, str]
    strong_evidence: bool
    birth_or_id_agrees: bool


def _agrees(features: Mapping[str, str], rules: Mapping[str, frozenset[str]]) -> bool:
    return any(features.get(name) in allowed for name, allowed in rules.items())


def scored_pairs(
    rows: Iterable[Mapping[str, Any]], labels: Mapping[str, Mapping[int, str]], kind: Kind
) -> list[ScoredPair]:
    """Predict output rows (as_record_list) to pairs, ordered by record ids."""
    out = []
    for row in rows:
        a, b = sorted((str(row["unique_id_l"]), str(row["unique_id_r"])))
        features = {
            name: levels[int(row[f"gamma_{name}"])] for name, levels in sorted(labels.items())
        }
        out.append(
            ScoredPair(
                a,
                b,
                round(float(row["match_probability"]), 9),
                round(float(row["match_weight"]), 6),
                features,
                _agrees(features, STRONG_EVIDENCE[kind]),
                kind == "org" or _agrees(features, BIRTH_OR_ID),
            )
        )
    return sorted(out, key=lambda p: (p.record_a, p.record_b))


def predict(linker: Linker, kind: Kind, candidate_threshold: float) -> list[ScoredPair]:
    model = linker.misc.save_model_to_json()
    labels = level_labels(model)
    result = linker.inference.predict(threshold_match_probability=candidate_threshold)
    return scored_pairs(result.as_record_list(), labels, kind)
```

**`resolve/tests/test_models.py`** (verbatim):

```python
"""Tests for neonradar_resolve.models (PHASE-2.md M2.10b). Invented names only."""

from __future__ import annotations

import random
from itertools import combinations
from pathlib import Path
from typing import Any

import pyarrow as pa
import pytest

from neonradar_keys.names import org_key, person_key
from neonradar_resolve.models import (
    ORG_SCHEMA,
    PERSON_SCHEMA,
    STRONG_EVIDENCE,
    TrainingConfig,
    connect,
    level_labels,
    make_linker,
    predict,
    settings,
    train,
)

SYLLABLES = ["ka", "lo", "mir", "dan", "vel", "tor", "sa", "ri", "bel", "zan", "fen", "or", "ul"]


def _word(rng: random.Random) -> str:
    return "".join(rng.choice(SYLLABLES) for _ in range(rng.choice([2, 3]))).capitalize()


def _typo(rng: random.Random, text: str) -> str:
    i = rng.randrange(1, len(text) - 1)
    return text[:i] + text[i + 1 :]


def person_rows(
    seed: int, entities: int = 400
) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    rng = random.Random(seed)  # noqa: S311 (synthetic test data, not security)
    rows: list[dict[str, Any]] = []
    clusters: dict[int, list[str]] = {}
    for e in range(entities):
        given, family = _word(rng), _word(rng)
        year, month, day = rng.randint(1940, 2000), rng.randint(1, 12), rng.randint(1, 28)
        postcode = f"QQ{rng.randint(1, 20)} {rng.randint(1, 9)}AB"
        company = f"gbch-co-SY{rng.randint(0, 999_999):06d}"
        for r in range(rng.choice([1, 2, 2, 3])):
            g = _typo(rng, given) if r and rng.random() < 0.15 else given
            key = person_key(f"{g} {family}", given=g, family=family)
            full = f"{year:04d}-{month:02d}-{day:02d}" if r == 0 else None
            uid = f"syn-p-{e:04d}-{r}"
            clusters.setdefault(e, []).append(uid)
            rows.append(
                {
                    "unique_id": uid,
                    "synthetic": True,
                    "name_key": key.key,
                    "name_key_rare": key.key,
                    "forename": key.given[0] if key.given else None,
                    "surname": key.family[0] if key.family else None,
                    "initial": key.given[0][0] if key.given else None,
                    "name_tokens": list(key.tokens) or None,
                    "name_symbols": list(key.symbols) or None,
                    "skeletons": list(key.skeletons) or None,
                    "birth_full": [full] if full else None,
                    "birth_ym": [f"{year:04d}-{month:02d}"],
                    "birth_years": [year],
                    "birth_year_min": year,
                    "birth_ym_min": f"{year:04d}-{month:02d}",
                    "countries": ["gb"],
                    "postcode": postcode if rng.random() < 0.8 else None,
                    "linked_orgs": [company] if rng.random() < 0.7 else None,
                    "identifiers": None,
                }
            )
    truth = {tuple(sorted(p)) for ids in clusters.values() for p in combinations(ids, 2)}
    return rows, truth  # type: ignore[return-value]


def org_rows(seed: int, entities: int = 300) -> tuple[list[dict[str, Any]], set[tuple[str, str]]]:
    rng = random.Random(seed)  # noqa: S311 (synthetic test data, not security)
    rows: list[dict[str, Any]] = []
    clusters: dict[int, list[str]] = {}
    for e in range(entities):
        core = f"{_word(rng)} {_word(rng)}"
        number = f"SY{e:06d}"
        year = rng.randint(1990, 2025)
        home = f"QQ{rng.randint(1, 30)} {rng.randint(1, 9)}AB"
        for r, form in enumerate(rng.sample(["Limited", "Ltd", "LTD."], rng.choice([1, 2, 3]))):
            name = f"{core} {form}"
            key = org_key(name)
            uid = f"syn-o-{e:04d}-{r}"
            clusters.setdefault(e, []).append(uid)
            rows.append(
                {
                    "unique_id": uid,
                    "synthetic": True,
                    "name_key": key.key,
                    "name_key_rare": key.key,
                    "name_prefix": key.key[:4],
                    "aliases": [key.key],
                    "ch_same_as": key.key.replace(" ", "").upper(),
                    "name_tokens": key.key.split() or None,
                    "jurisdiction": "gb",
                    "registration_numbers": [number] if r == 0 or rng.random() < 0.6 else None,
                    "incorporation_year": year if rng.random() < 0.8 else None,
                    "postcode": home if rng.random() < 0.8 else f"QQ{rng.randint(1, 30)} 1AB",
                    "legal_forms": list(key.legal_forms) or None,
                }
            )
    truth = {tuple(sorted(p)) for ids in clusters.values() for p in combinations(ids, 2)}
    return rows, truth  # type: ignore[return-value]


def run(kind: str, tmp_path: Path, threads: int = 1) -> tuple[list[Any], set[tuple[str, str]]]:
    rows, truth = person_rows(7) if kind == "person" else org_rows(7)
    schema = PERSON_SCHEMA if kind == "person" else ORG_SCHEMA
    table = pa.Table.from_pylist(rows, schema=schema)
    con = connect(threads=threads, memory_limit="1GB", temp_directory=str(tmp_path / "duckdb"))
    linker = make_linker(con, kind, table)  # type: ignore[arg-type]
    train(linker, kind, TrainingConfig(u_max_pairs=2e5, em_max_pairs=None))  # type: ignore[arg-type]
    return predict(linker, kind, 0.5), truth  # type: ignore[arg-type]


def test_level_labels_follow_splink_order() -> None:
    model = settings("person").get_settings("duckdb").as_dict()
    labels = level_labels(model)
    assert labels["name"][-1] == "name_key is NULL"
    assert labels["name"][7] == "name key equal"
    assert labels["name"][0] == "All other comparisons"
    assert labels["postcode"][4] == "Exact match on full postcode"
    for kind, rules in STRONG_EVIDENCE.items():
        names = level_labels(settings(kind).get_settings("duckdb").as_dict())  # type: ignore[arg-type]
        for comparison, allowed in rules.items():
            assert allowed <= set(names[comparison].values()), (kind, comparison)


@pytest.mark.parametrize("kind", ["person", "org"])
def test_models_find_true_pairs(kind: str, tmp_path: Path) -> None:
    pairs, truth = run(kind, tmp_path)
    found = {(p.record_a, p.record_b) for p in pairs if p.probability >= 0.9}
    precision = len(found & truth) / max(len(found), 1)
    recall = len(found & truth) / len(truth)
    assert precision >= 0.95, precision
    assert recall >= 0.80, recall
    assert all(p.record_a < p.record_b for p in pairs)
    assert all(set(p.features) for p in pairs)


def test_single_thread_runs_are_identical(tmp_path: Path) -> None:
    first, _ = run("person", tmp_path / "a")
    second, _ = run("person", tmp_path / "b")
    assert first == second
```

#### M2.10c Decisions, sampling, labelling and the precision report

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (data steward reviews the labelling tool's screens) |
| Depends on | M2.10b |
| Branch | `p2/m2-10c-labelling` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | Yes |
| Size | exception (`stats.py` and the 7.2 wording tables are verbatim) |
| Real-data run | none (M2.15 uses these tools on `uk-sample`) |

**Goal.** The tools that let people review possible matches, label pairs and produce the published figure, built so that the agent cannot use them on real data, nothing they show leaves the machine, and the evaluation cannot be shaped after the fact.

**Deliverables.** Every `er` command here takes `--run <id>` or `--run latest` (the id in `LATEST`, `latest_run(profile)`, M2.2). On a real profile, `er sample`, `er label`, `er review` and `er precision` first apply the real-data gate (M2.2) and run inside the redaction guard, like every real-profile command.

1. `resolve/src/neonradar_resolve/decisions.py`: `load_decisions(path, member_ids)` reads the decisions file the CLI passes (`decisions_file(profile)`, M2.2: `data/cache/real/decisions.jsonl` for a real profile, `data/cache/synthetic/decisions.jsonl` otherwise; 7.1.8). For each pair of records the newest line wins; the supporters of a `same` decision are the distinct `by` handles whose own newest line for that pair says `same`. It returns D7 links (`Link(a, b, "human", "D7", reviewers=frozenset(supporters))`) and X8 pairs for the decisions whose two records are resolvable records of this run, and counts the rest. `run.json` records `decisions_on_file`, `decisions_applied`, `decisions_not_applicable` (a record is not in this run, for example a decision made on another profile) and `decisions_awaiting_second_review` (from `cluster.resolve`: a `same` decision that would cross P1 or P2 applies only with two supporters, or one supporter in `people.er_senior_reviewers`, 7.1.2). `append_decision(path, record_a, record_b, decision, by, note)` is the only writer; it refuses a `same` decision without a note. `er run --no-decisions` (M2.10a) ignores the decisions file; M2.10c makes `run.json` record `decisions_used` (`false` for such a run) next to `decisions_on_file`. The evaluation run of 7.3 is always a `--no-decisions` run.
2. `resolve/src/neonradar_resolve/sample.py` and `neonradar er sample --profile <name> --run <id> --seed <n> --labellers @a,@b,...`: builds the frames of 7.3 from `canonical.csv` and `candidates.jsonl`, sorted by record id: S1, every non-anchor record of class `person`, `org` or `legal_entity` whose `path_methods` include `probabilistic`; S2, every such record whose `path_methods` are exactly `deterministic`, with the D rule it joined by; the records whose path includes `human`, counted only; S3, every possible match. Each S1 or S2 item is the pair (record, anchor of its cluster); each S3 item is the possible match's `record_a` and `record_b`. It draws simple random samples with `random.Random(seed)` (a frame no larger than its sample size is taken whole and marked as a census), draws S4 as 40 pairs from the S1 sample and 10 from the S3 sample, puts all pairs into one seeded random order so that the strata are interleaved, and assigns them to labellers round-robin so that each S4 pair goes to two different people. It writes `labels_dir(profile, run_id)/sample.jsonl` (pair id, stratum, the two record ids, the assigned labellers) and prints counts only. For a real profile it refuses (exit 2) a run whose `run.json` does not say `decisions_used: false`, and a seed other than the one in ADR-0014 once that ADR is accepted (7.3 rule 1; it reads the status line and the line `Evaluation sample seed: <n>` of `docs/decisions/0014-entity-resolution-approach-and-thresholds.md`, and while the seed is not set it only prints the seed it used).
3. `resolve/src/neonradar_resolve/cards.py`: a record card for a pair: dataset title, schema, names in original scripts, birth dates, nationalities and countries, postcodes and towns, linked organisations (names and numbers), identifiers, source link. Built by streaming the record folders the CLI passes for the needed ids only. Never shows a match probability, a rule, a method, a stratum or anyone's label (7.3 rule 2).
4. `graph/src/neonradar_graph/wording.py`: the texts of 7.2, verbatim: `explain_member(member)`, `explain_possible_match(link)`, `evidence_lines(features)`, `absence_of_flags(datasets)`, and the tables `MEMBER_TEXTS`, `REASON_TEXTS`, `HINT_WORDS` and `LEVEL_WORDS`. A possible-match text names the agreeing evidence, then the differing evidence, then what neither record gives, from the link's `features` (7.2, "Evidence"). Tests: every method, D rule, reason and ICIJ hint value in 7.2 renders; every rendered string passes the forbidden-pattern lint, including the phrases M2.1c added, and `scripts/check_wording.py` (which scans `graph/src/**/wording.py` from M2.1c) passes; every possible-match text contains "not confirmed"; and `resolve/tests/test_wording_levels.py` reads `resolve/models/person.settings.json` and `org.settings.json` (M2.10b) and fails when a level label has no entry in `LEVEL_WORDS` (the test lives in `resolve`, which depends on `graph`). The texts live in `graph`, not `resolve`, so the API (M2.12) can use them without Splink; `er review` imports them.
5. `neonradar er label --profile <name> --run <id> --labeller @handle [--adjudicate]`: requires a terminal (`require_terminal`, M2.2); shows the next unlabelled pair assigned to the handle, two cards side by side, and asks `s` (same), `d` (different), `u` (unsure) and an optional note; appends each answer to `labels_dir(profile, run_id)/<handle>.jsonl` at once; resumes where it stopped. It never pre-selects an answer. `--adjudicate` shows only the S4 pairs whose two labels differ, without showing either label, and records the adjudicated label; it refuses (exit 2) the handles in `people.tech_lead` and `squads.graph.mentor` (they set the thresholds, ADR-0014) and anyone who labelled that pair. The project lead adjudicates by default (7.3 rule 4).
6. `neonradar er review --profile <name> --run <id> --reviewer @handle`: requires a terminal; walks possible matches in order of probability (those without one last); shows the two cards and the reasons in the words of 7.2, and above the question the agreeing and differing evidence (7.2, "Evidence"); pairs with a hard conflict (X1 to X6, X8) never reach review (7.1.3); records `same` or `different` through `append_decision`, and asks for a note before it accepts `same`. When a `same` answer would cross P1 or P2 and the reviewer is not in `people.er_senior_reviewers`, it says that the decision waits for a second reviewer. A later `er run` applies the decisions (never the evaluation run).
7. `resolve/src/neonradar_resolve/stats.py`: verbatim below (the Wilson interval, Cohen's kappa, and positive and negative agreement), and `precision.py` with `neonradar er precision --profile <name> --run <id> --out <path>`: reads the sample and every label file, applies adjudications, and computes for each stratum `k`, `n`, the unsure count `u`, the point estimate `k / n` and its Wilson 95 percent interval; for S1 also `k / (n + u)` with its interval (the precision if every unsure pair were wrong); S2 by D rule (D3 on its own line); the S4 percentage agreement, Cohen's kappa, the share of `same`, and positive and negative agreement, before adjudication; the census marks. It writes the report in the shape of 7.3 (counts and rates only, never a record id), including the README sentence and the sources-and-licences footer (from the attribution of every dataset in the run, `contracts/datasets.yaml`, plus the ICIJ notice when ICIJ records are in it), and the CLI emits the summary.
8. Tests (synthetic only): decisions: the newest line wins, supporters are counted per handle, a decision about a record outside the run is counted and not applied, `append_decision` refuses `same` without a note, and `er run --no-decisions` ignores the file and records `decisions_used: false`; sampling is deterministic for a seed, a record joined by D3 to a record that joined probabilistically lands in S1 and not S2, S4 holds 40 S1 and 10 S3 pairs each assigned to two different labellers, and the strata are interleaved; `sample.check_run(run_json, real_data=True)` refuses a run that used decisions (a dictionary built in the test; no file under `data/cache/real/`); labels from three handles and one adjudication combine correctly; `--adjudicate` refuses the tech lead's handle and a labeller of the pair; precision, the unsure bound and the agreement figures on a synthetic label set match `stats.py`; `er label` and `er review` refuse to run without a terminal (run them with `subprocess` and closed stdin); the report contains no record id (check with a regular expression for every id prefix in `contracts/datasets.yaml`) and contains the README sentence and the footer; `resolve/tests/test_stats.py` verbatim below (six tests).

**Acceptance.**

```bash
uv run neonradar er run --profile demo --no-decisions
RUN="$(cat data/cache/synthetic/resolution/demo/LATEST)"
uv run neonradar er sample --profile demo --run "$RUN" --seed 7 --labellers @a,@b,@c,@d
uv run pytest resolve/tests/test_decisions.py resolve/tests/test_sample.py resolve/tests/test_precision.py resolve/tests/test_stats.py -q
uv run pytest graph/tests/test_wording.py resolve/tests/test_wording_levels.py -q
python3 scripts/check_wording.py
make check
```

(`er label` and `er review` are human-only: the hook blocks them in agent sessions, so their terminal check is proven by the `subprocess` tests above.)

**Review focus (humans).** Data steward: run `uv run neonradar er label --profile demo --run latest --labeller @you` yourself. Is there anything on screen you would not want on a real person's card? Graph mentor: could a labeller infer the model's answer, or the stratum, from anything shown or from the order of the pairs? Project lead: try `--adjudicate` on the demo sample; can you see either earlier label?

**`resolve/src/neonradar_resolve/stats.py`** (verbatim):

```python
"""Precision and agreement statistics for the published figure (PHASE-2.md 3.4 and 7.3)."""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Sequence
from typing import NamedTuple

Z_95 = 1.959963984540054  # two-sided 95 percent normal quantile


def wilson_interval(k: int, n: int, z: float = Z_95) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials (Wilson 1927)."""
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("need 0 <= k <= n and n > 0")
    p = k / n
    z2 = z * z
    denominator = 1 + z2 / n
    centre = (p + z2 / (2 * n)) / denominator
    half = (z / denominator) * math.sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    low = 0.0 if k == 0 else max(0.0, centre - half)
    high = 1.0 if k == n else min(1.0, centre + half)
    return low, high


def cohens_kappa(first: Sequence[str], second: Sequence[str]) -> float:
    """Cohen's kappa for two labellers over the same items (Cohen 1960)."""
    if len(first) != len(second) or not first:
        raise ValueError("need two label lists of the same, non-zero length")
    n = len(first)
    observed = sum(a == b for a, b in zip(first, second, strict=True)) / n
    left, right = Counter(first), Counter(second)
    expected = sum(left[c] * right[c] for c in set(left) | set(right)) / (n * n)
    if expected == 1:
        return 1.0
    return (observed - expected) / (1 - expected)


class SpecificAgreement(NamedTuple):
    positive: float | None  # 2a / (2a + b + c); None when no item could count
    negative: float | None  # 2d / (2d + b + c)
    excluded: int  # items where either label is neither positive nor negative (unsure)


def specific_agreement(
    first: Sequence[str],
    second: Sequence[str],
    positive: str = "same",
    negative: str = "different",
) -> SpecificAgreement:
    """Positive and negative agreement (Cicchetti and Feinstein 1990).

    Reported next to kappa, which can be low or negative when almost every label is the
    same even though the labellers rarely disagree. Only items that both labellers marked
    `positive` or `negative` count; the others are returned as `excluded`.
    """
    if len(first) != len(second) or not first:
        raise ValueError("need two label lists of the same, non-zero length")
    allowed = {positive, negative}
    pairs = [(a, b) for a, b in zip(first, second, strict=True) if a in allowed and b in allowed]
    both_positive = sum(a == b == positive for a, b in pairs)
    both_negative = sum(a == b == negative for a, b in pairs)
    split = len(pairs) - both_positive - both_negative
    pos_denominator = 2 * both_positive + split
    neg_denominator = 2 * both_negative + split
    return SpecificAgreement(
        2 * both_positive / pos_denominator if pos_denominator else None,
        2 * both_negative / neg_denominator if neg_denominator else None,
        len(first) - len(pairs),
    )
```

**`resolve/tests/test_stats.py`** (verbatim):

```python
import pytest

from neonradar_resolve.stats import cohens_kappa, specific_agreement, wilson_interval


def test_worked_example():
    lo, hi = wilson_interval(180, 200)
    assert (round(lo, 4), round(hi, 4)) == (0.8506, 0.9343)


def test_edges():
    assert wilson_interval(0, 10)[0] == 0.0
    assert wilson_interval(10, 10)[1] == 1.0
    low, _ = wilson_interval(10, 10)
    assert round(low, 4) == 0.7225
    with pytest.raises(ValueError):
        wilson_interval(3, 0)


def test_unsure_bound():
    # 400 drawn: 330 same, 10 different, 60 unsure (7.3 rule 3). The headline excludes unsure;
    # the bound counts every unsure pair as wrong.
    assert [round(x, 4) for x in wilson_interval(330, 340)] == [0.9467, 0.9839]
    assert [round(x, 4) for x in wilson_interval(330, 400)] == [0.7847, 0.8591]


def test_kappa():
    a = ["same"] * 40 + ["different"] * 10
    b = ["same"] * 38 + ["different"] * 2 + ["different"] * 8 + ["same"] * 2
    assert round(cohens_kappa(a, b), 4) == 0.75
    assert cohens_kappa(["same"] * 5, ["same"] * 5) == 1.0


def test_high_agreement_low_kappa():
    # 48 pairs both "same", one split each way: 96 percent agreement, kappa below zero.
    a = ["same"] * 49 + ["different"]
    b = ["same"] * 48 + ["different", "same"]
    assert round(cohens_kappa(a, b), 4) == -0.0204
    agreement = specific_agreement(a, b)
    assert round(agreement.positive or 0, 4) == 0.9796
    assert agreement.negative == 0.0
    assert agreement.excluded == 0


def test_specific_agreement_leaves_out_unsure():
    first = ["same", "same", "unsure", "different"]
    second = ["same", "unsure", "different", "different"]
    assert specific_agreement(first, second) == (1.0, 1.0, 2)
    assert specific_agreement(["unsure"], ["same"]) == (None, None, 1)
    with pytest.raises(ValueError):
        specific_agreement(["same"], [])
```

### M2.11 Resolution-aware graph loader

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor |
| Depends on | M2.1b, M2.10a |
| Branch | `p2/m2-11-resolved-loader` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `size-exception` |
| Plan first | Yes |
| Size | exception (eight verbatim query files plus the loader, mapping and verify changes they need) |
| ADR | ADR-0016 (canonical ids and source records) |
| Real-data run | none (the first real load is in M2.13) |

**Goal.** The loader turns records plus a resolution run into canonical entities with their evidence, re-points every relationship, sends real data only to its own Neo4j instance, and still loads Phase 1 data and Phase 3's overlay exactly as before.

**Deliverables.**

1. `graph/src/neonradar_graph/resolution.py`: `ResolutionMap.load(run_dir)` reads `canonical.csv` (header `record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,path_methods,features`, 7.1.8), `candidates.jsonl` and `run.json` (for `run_id` and `resolver_version`), and checks them: every record of a cluster with two or more members maps to an id starting `nr-`; `cluster_size` matches the member count; every candidate joins two different canonical ids with `a < b`; and (L14) every candidate's two records have class `person`, `org` or `legal_entity`, otherwise the load stops with exit 1 and the count. `ResolutionMap.canonical(record_id)` returns the canonical id or the record id itself. It takes a folder, so `graph` never imports `ingest`: the CLI turns `--resolution latest` into `resolution_dir(profile, latest_run(profile))`, the run whose id `er run` wrote last into `LATEST` (M2.10a, M2.2), so an unfinished run is never loaded.
2. `graph/src/neonradar_graph/instances.py`: the two Neo4j instances (C2 L17, M2.0). `Instance.DEFAULT` uses `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` and the database of Phase 1's `NEO4J_DATABASE` setting (default `neo4j`, PHASE-1.md M1.4); `Instance.REAL` uses `NR_NEO4J_REAL_URI` (default `bolt://127.0.0.1:7688`), the same user, `NEO4J_REAL_PASSWORD` and database `realdata`. Every query the graph package sends names the database of its instance, so a query sent to the wrong instance fails ("database does not exist") before anything is written. Both instances get the same migrations: `neonradar graph migrate --real` applies them to the real instance, and a load into the real instance stops with exit 2 while a migration is pending there (loads into the default instance behave as in Phase 1).
3. `graph/src/neonradar_graph/mapping.py`:
   - `to_node_rows(records, resolution)`: single-record entities stream through as in Phase 1, with `cluster_size = 1`, `resolution = "identity"`, `referents = [id]`; members of merged clusters are buffered per canonical id and merged with the rules in 7.1.6 (the schema through `followthemoney.model.common_schema`). Labels come from the merged schema's mapping row; flags from the merged topics with Phase 1's `FLAG_LABELS`.
   - L15: `names_latin` and `names_latin_text` from `neonradar_keys.names.latin_forms(names)`; `Address.address_key` from `neonradar_keys.addresses.address_key(...)`.
   - `to_source_record_rows(records, resolution)` and `to_resolved_to_rows(resolution)`: one row per member of a merged entity (5.2 properties). `method`, `rule`, `match_probability` (1.0 for anchor, deterministic and human members) and `features` (the JSON text of the `features` column, set for probabilistic members only) come from that member's `canonical.csv` row; `run_id` and `resolver_version` from `run.json`, and `decided_at` is the run's start time, which its run id encodes (4.4). The graph package never reads `pairs.parquet` and imports neither PyArrow, DuckDB nor Splink, so the API image stays free of them (4.2).
   - `to_relationship_rows(records, resolution, loaded_ids)`: re-points `source` and `target` through the map (L12) and drops rows whose two ends are the same node, counted as `self_loops_dropped`. The derived ids of `HAS_ADDRESS` (`<entity id>|addr|<address id>`) and `SUBJECT_OF` (`<entity id>|sanction|<sanction id>`) are built from the canonical ids after re-pointing; rows that then share a type and an id become one row (`role`: the first of `registered`, `service`, `residential`, `business`, `unknown` among them; `datasets`: the union), counted as `duplicate_relationships_merged`. Rows whose ends are loaded in this run go to the direct query; the rest need the database lookup (L13, the resolving query).
   - `PAID`: `props.ts` is a timezone-aware `datetime` in UTC, never a string, so the generic relationship query stores a `DATETIME` (I3; PHASE-1.md loader rule 6).
   - `to_possibly_same_as_rows(resolution)`: id `<a>|psa|<b>` and the 5.2 properties, including `rule`, and a null `match_probability` for `deterministic` and `source_hint` possible matches.
4. `graph/src/neonradar_graph/loader.py`: `load(paths, resolution=None, replace=True, instance=Instance.DEFAULT)`:
   - L17, before connecting: it reads the manifests and the records' datasets; `Instance.DEFAULT` refuses (exit 2, nothing written) when any record is not synthetic, `Instance.REAL` refuses when any record is synthetic, and a load that mixes both is refused whichever instance it names.
   - L9, when a resolution run is given (unless `replace=False`): on the real instance `queries/purge_real.cypher`; on the default instance `queries/purge_superseded.cypher` with `$record_ids` set to every record id of the load, which removes the synthetic nodes an earlier load of the same records left behind (I13).
   - Then, in order: entity nodes, `:SourceRecord` nodes, `RESOLVED_TO`, relationships (direct, then resolving), `POSSIBLY_SAME_AS`, in batches of 5,000 rows through `driver.execute_query(..., database_=<the instance's database>)`; the purge statements go through `session.run()` because they use `CALL { } IN TRANSACTIONS`. The possible-match query returns `written`; a difference from the rows sent stops the load with exit 1.
   - `LoadReport` adds: canonical entities, merged entities, source records, possible matches, `self_loops_dropped`, `duplicate_relationships_merged`, superseded nodes removed, references resolved through `:SourceRecord`, dangling references. Real loads print it through the summary helper (M2.2): counts only.
5. CLI: `neonradar graph load PATH... [--resolution RUN_DIR | --profile NAME --resolution latest] [--no-replace] [--strict/--no-strict]`; `neonradar graph load --profile NAME` without paths loads `Profile.record_dirs()`. The CLI picks the instance from the records (L17): `--profile demo` goes to the default instance, `--profile uk-tiny` to `neo4j-real`, and any command that addresses the real instance first runs the real-data gate of M2.2 (before connecting). `neonradar graph migrate --real`, `graph verify --real`, `graph stats --real` and `graph wipe --real --yes` address the real instance and print counts only; no graph command prints a value from it. A command that addresses the real instance without a profile runs gate checks 3 to 5 of M2.2 and refuses (exit 3) while `access.real_data_profiles` is empty. `neonradar graph verify` runs I1 to I14 and prints one line per invariant with its violation count, adding up the statements of an invariant that has two (exit 1 on any).
6. The query files below, verbatim, in `graph/src/neonradar_graph/queries/`. They pass `make cypher-lint`. Python reads them by name and fills `{{rel_type}}` and `{{target_label}}` from the C2 mapping table only.
7. Tests (synthetic only; integration tests use Testcontainers, never the user's instances):
   - unit, `graph/tests/test_mapping_resolution.py`: features, rule and probability copied from a test-built `canonical.csv` row onto `RESOLVED_TO`; the `HAS_ADDRESS` merge after re-pointing (two members with the same address give one row and `duplicate_relationships_merged = 1`); a self-loop dropped; a `PAID` row whose `ts` is a timezone-aware `datetime`; a candidate line whose records are addresses makes `ResolutionMap.load` stop (L14).
   - unit, `graph/tests/test_instances.py`: with a fake driver that records queries, `load(..., instance=Instance.DEFAULT)` refuses a set of non-synthetic look-alike records built in test code (ids `gbch-co-T0000001` and so on, names like "Test Holder Ltd") before any query; `Instance.REAL` refuses synthetic records; a mixed set is refused by both; each instance names its own database; importing `neonradar_graph.loader` imports neither `pyarrow`, `duckdb` nor `splink` (checked through `sys.modules` in a subprocess).
   - integration, `graph/tests/test_loader_resolution.py`: a session-scoped fixture builds a resolution run of demo-mini and the ER benchmark in a folder from `tmp_path_factory` with `neonradar_resolve.run.run` (deterministic rules only; `graph`'s `dev` dependency group lists `neonradar-resolve` for this, the package code never imports it, and uv accepts this test-only cycle, checked with uv 0.11.32); load it; every invariant I1 to I14 holds; loading twice leaves every count unchanged (L16); one merged entity checked property by property against 7.1.6 (expected values computed in the test from the records); the number of `POSSIBLY_SAME_AS` equals the lines of `candidates.jsonl`; a second resolved load after a test-built change to the run (two more records merged) leaves no superseded node (I13) and counts them in the report; `PAID.ts` is a `DATETIME` after a resolved load; a Phase 1 load without `--resolution` gives exactly the Phase 1 counts.
   - integration, replacement (L9): a second container started like `neo4j-real` (`NEO4J_initial_dbms_default__database=realdata`) is loaded as `Instance.REAL` with a look-alike set and a resolution run, then with a different look-alike set: the first set is gone; a synthetic load into the first container leaves the second unchanged.
   - integration, `graph/tests/test_overlay_resolution.py` (G2-14): after a resolved load, load with `--no-replace` a test-built file holding a synthetic `BankAccount` and an `Ownership` whose `owner` is a record id that was merged; the `HOLDS_ACCOUNT` relationship ends on the canonical node, and the report counts one reference resolved through `:SourceRecord`.
   - integration, `graph/tests/test_invariants.py`: extended from I1 to I6 to I1 to I14 on the resolved demo load of the fixture above, so it no longer needs `make load`.
8. `docs/decisions/0016-canonical-ids-and-source-records.md` (status `proposed`; decider: tech lead): single-record entities keep their record id (stable Phase 1 ids, fewer nodes); merged entities get `nr-<anchor>` with the anchor rule of 7.1.6; source records only for merged entities; resolve then load, with a full replacement of real data on each resolved load and the removal of superseded synthetic nodes, because incremental re-resolution in the graph would be hard to explain and to test; real data only in its own instance (L17); Phase 3's overlay resolves record ids through `:SourceRecord`.

**Acceptance.**

```bash
make up && uv run neonradar graph migrate
uv run neonradar er run --profile demo --no-probabilistic
uv run neonradar graph load --profile demo --resolution latest      # counts; 0 dangling
uv run neonradar graph verify                                       # I1 to I14: 0 violations
uv run neonradar graph load --profile demo --resolution latest      # identical counts
uv run pytest graph/tests/test_mapping_resolution.py graph/tests/test_instances.py -q
uv run pytest -m integration graph/tests/test_loader_resolution.py graph/tests/test_overlay_resolution.py graph/tests/test_invariants.py
make cypher-lint && make check
```

**Review focus (humans).** Open Neo4j Browser on the demo load and pick a merged person: do its `:SourceRecord` nodes, `referents` and names tell the same story as `canonical.csv`? Find a `POSSIBLY_SAME_AS`: is anything on one side copied to the other? (It must not be.) Read `test_instances.py`: is there any path by which a non-synthetic record reaches the default instance?

**`queries/upsert_source_records.cypher`:**

```cypher
// L11: one :SourceRecord per member of a merged entity
UNWIND $rows AS row
MERGE (s:SourceRecord {id: row.id})
SET s += row.props;
```

**`queries/upsert_resolved_to.cypher`:**

```cypher
// L11: RESOLVED_TO from each source record to its canonical entity
UNWIND $rows AS row
MATCH (s:SourceRecord {id: row.record_id})
MATCH (e:Entity {id: row.canonical_id})
MERGE (s)-[r:RESOLVED_TO]->(e)
SET r += row.props;
```

**`queries/upsert_relationships.cypher`:**

```cypher
// L12: relationship rows whose endpoints the loader already re-pointed to loaded node ids.
// Labels and the type come from the C2 mapping table, never from data. For PAID, row.props.ts
// is a timezone-aware datetime from Python, so Neo4j stores a DATETIME (I3).
// lint-values: rel_type=OWNS,CONTROLS,CONSOLIDATES,DIRECTOR_OF,HOLDS_ACCOUNT,PAID,HAS_ADDRESS,REPRESENTS,FAMILY_OF,ASSOCIATE_OF,MEMBER_OF,EMPLOYED_BY,LINKED_TO,SUCCEEDED_BY,HOLDS_POSITION,SUBJECT_OF target_label=Entity,Sanction
UNWIND $rows AS row
MATCH (s:Entity {id: row.source})
MATCH (t:{{target_label}} {id: row.target})
MERGE (s)-[r:{{rel_type}} {id: row.id}]->(t)
SET r += row.props
RETURN count(r) AS written;
```

**`queries/upsert_relationships_resolving.cypher`:**

```cypher
// L13: rows with an endpoint that is neither loaded in this run nor in the resolution map,
// for example Phase 3 overlay records that reference a record id of a merged entity.
// lint-values: rel_type=OWNS,CONTROLS,DIRECTOR_OF,HOLDS_ACCOUNT,HAS_ADDRESS,REPRESENTS,LINKED_TO
UNWIND $rows AS row
CALL (row) {
  OPTIONAL MATCH (direct:Entity {id: row.source})
  OPTIONAL MATCH (:SourceRecord {id: row.source})-[:RESOLVED_TO]->(via:Entity)
  RETURN coalesce(direct, via) AS s
}
CALL (row) {
  OPTIONAL MATCH (direct:Entity {id: row.target})
  OPTIONAL MATCH (:SourceRecord {id: row.target})-[:RESOLVED_TO]->(via:Entity)
  RETURN coalesce(direct, via) AS t
}
WITH row, s, t
WHERE s IS NOT NULL AND t IS NOT NULL AND s <> t
MERGE (s)-[r:{{rel_type}} {id: row.id}]->(t)
SET r += row.props
RETURN count(r) AS written;
```

**`queries/upsert_possibly_same_as.cypher`:**

```cypher
// L14: one POSSIBLY_SAME_AS per line of candidates.jsonl, from the smaller id to the larger,
// only between two LegalEntity nodes (I10); the loader compares `written` with the rows sent
UNWIND $rows AS row
MATCH (a:Entity {id: row.a}) WHERE a:LegalEntity
MATCH (b:Entity {id: row.b}) WHERE b:LegalEntity
MERGE (a)-[r:POSSIBLY_SAME_AS {id: row.id}]->(b)
SET r += row.props
RETURN count(r) AS written;
```

**`queries/purge_real.cypher`** (real-data instance):

```cypher
// L9 (real-data instance): before a resolved load, remove every entity, sanction and source
// record, and every detection result (detections are re-run after a load)
MATCH (n) WHERE n:Entity OR n:Sanction OR n:SourceRecord
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
```

**`queries/purge_superseded.cypher`** (default instance):

```cypher
// L9 (default instance): before a resolved load, remove the synthetic entities and source
// records whose id or referents include a record id of this load ($record_ids), so a re-run
// after a resolver change leaves no stale node (I13), and every detection result
MATCH (n)
WHERE (n:Entity OR n:SourceRecord) AND n.synthetic = true
  AND (n.id IN $record_ids OR any(r IN coalesce(n.referents, []) WHERE r IN $record_ids))
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
MATCH (n) WHERE n:Alert OR n:DetectionRun
CALL (n) { DETACH DELETE n } IN TRANSACTIONS OF 10000 ROWS;
```

**`queries/verify_resolution.cypher`** (I7 to I14; `verify.py` also runs Phase 1's I1 to I6):

```cypher
// I7
MATCH (s:SourceRecord)
OPTIONAL MATCH (s)-[r:RESOLVED_TO]->(e:Entity)
WITH s, count(r) AS n, collect(e) AS es
WHERE n <> 1 OR NOT es[0].id STARTS WITH 'nr-' OR NOT s.id IN es[0].referents
RETURN count(s) AS violations;
// I8 (merged entities)
MATCH (e:Entity) WHERE e.cluster_size >= 2
OPTIONAL MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e)
WITH e, count(s) AS n
WHERE n <> e.cluster_size OR size(e.referents) <> e.cluster_size
RETURN count(e) AS violations;
// I8 (single-record entities)
MATCH (e:Entity) WHERE coalesce(e.cluster_size, 1) = 1 AND e.referents <> [e.id]
RETURN count(e) AS violations;
// I9
MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e:Entity) WHERE s.synthetic <> e.synthetic
RETURN count(s) AS violations;
// I10 (endpoints and direction)
MATCH (a)-[r:POSSIBLY_SAME_AS]->(b)
WHERE a = b OR NOT a:LegalEntity OR NOT b:LegalEntity OR a.synthetic <> b.synthetic OR a.id >= b.id
RETURN count(r) AS violations;
// I10 (at most one per pair)
MATCH (a)-[r:POSSIBLY_SAME_AS]-(b) WHERE a.id < b.id
WITH a, b, count(r) AS n WHERE n > 1
RETURN count(*) AS violations;
// I11 (topics of merged entities)
MATCH (s:SourceRecord)-[:RESOLVED_TO]->(e:Entity)
WITH e, collect(s.topics) AS lists
WITH e, reduce(acc = [], l IN lists | acc + [t IN coalesce(l, []) WHERE NOT t IN acc]) AS merged
WHERE size(merged) <> size(coalesce(e.topics, [])) OR any(t IN merged WHERE NOT t IN coalesce(e.topics, []))
RETURN count(e) AS violations;
// I11 (flags follow topics)
MATCH (e:Entity)
WHERE (e:Sanctioned) <> ('sanction' IN coalesce(e.topics, []))
   OR (e:PEP) <> ('role.pep' IN coalesce(e.topics, []))
   OR (e:RCA) <> ('role.rca' IN coalesce(e.topics, []))
RETURN count(e) AS violations;
// I12
MATCH (n)-[r:OWNS|CONTROLS]->(n)
RETURN count(r) AS violations;
// I13
MATCH (s:SourceRecord)
MATCH (e:Entity {id: s.id})
RETURN count(e) AS violations;
// I14
MATCH ()-[r:CONTROLS]->()
WHERE (r.share_pct_min IS NOT NULL AND (r.share_pct_min < 0 OR r.share_pct_min > 100))
   OR (r.share_pct_max IS NOT NULL AND (r.share_pct_max < 0 OR r.share_pct_max > 100))
   OR (r.share_pct_min IS NOT NULL AND r.share_pct_max IS NOT NULL AND r.share_pct_min > r.share_pct_max)
RETURN count(r) AS violations;
```

### M2.12 API: ownership, paths and resolution

| | |
|---|---|
| Squad, human owner | Investigation Copilot (API); copilot mentor (graph mentor reviews the queries) |
| Depends on | M2.1c, M2.10c, M2.11 |
| Branch | `p2/m2-12-ownership-api` |
| Labels | `agent`, `phase-2`, `squad:copilot`, `squad:graph`, `size-exception` |
| Plan first | Yes |
| Size | exception (five verbatim queries and two fixtures with their oracle) |
| ADR | ADR-0019 (ownership and effective share calculation) |
| Real-data run | none (latencies on `uk-sample` are measured in M2.13) |

**Goal.** The three endpoints that Phases 4 and 5 build on return exactly what C3 1.1.0 promises, with results a reviewer can check by hand, explanations an investigator can read, and no change to the OpenAPI snapshot.

**Deliverables.**

1. `graph/src/neonradar_graph/ownership.py`: `ownership(driver, root_id, direction, max_hops, min_share, limit=200, scan_limit=5000, max_nodes=500, max_edges=1000)` and `paths(driver, from_id, to_id, max_hops, rel_types, max_nodes=500, max_edges=1000)`. Both resolve ids with `queries/resolve_id.cypher` (404 when neither an entity nor a source record has the id), pick the query variant for `max_hops` (one rendered template per value, from the file below, never from input), run it read-only with `neo4j.Query(text, timeout=5.0)` and `routing_=RoutingControl.READ`, and build the `Subgraph` with Phase 1's subgraph builder (`limits` `{max_nodes: 500, max_edges: 1000}`; `truncated` when either limit cut something). The ownership queries round effective shares to 4 decimals (Cypher's `round(x, 4)`, half up) before they filter and order, and Python passes those values through unchanged, so a path is kept or dropped on exactly the figure the API returns. `ownership` asks for at most `scan_limit` paths; if it gets that many, or more than `limit` survive, it sets `truncated`. `paths` computes effective shares in Python only when every relationship is `OWNS` and all point the same way along the path (compare each relationship's start node with the path order), with the product rule of 5.3, rounded half up to 4 decimals (`decimal.ROUND_HALF_UP`), so both endpoints give the same figures for the same chain.
2. Every text the endpoints return comes from `neonradar_graph.wording` (M2.10c: the 7.2 templates, `LEVEL_WORDS` and their tests); this milestone adds no wording of its own.
3. API routes (replace the 501 handlers): `GET /entities/{entity_id}/ownership`, `GET /paths`, `GET /entities/{entity_id}/resolution`, exactly as 5.3. Update `api/tests/test_routes.py` (M2.1c, PHASE-1.md M1.7d): these routes no longer return 501, so replace those assertions with a 404 problem for an unknown id and a 422 for an invalid parameter, and keep the check that they declare 200, 404, 422 and 503; this is the planned behaviour change, not a weakened test (2.2 step 6). M2.1c already declared every response these routes return (200 with its model; 404, 422 and 503 as Problem), so the OpenAPI output does not change; if `make contracts` changes `contracts/openapi/v1.json`, stop and report it, because that is a contract change for the tech lead and not part of this milestone. Unknown ids give 404 problems; `rel_types` outside the allowed set gives 422; a timeout gives a 503 problem whose detail suggests a smaller `max_hops` or fewer relationship types (catch the driver's `ClientError` whose code contains `TransactionTimedOut`). The resolution route resolves the id, then runs `queries/resolution_members.cypher` and `queries/resolution_candidates.cypher`: `ResolutionMember.explanation` comes from `explain_member`; `PossibleMatch.match_probability` is null for deterministic and source-hint matches, `PossibleMatch.rule` is the link's `rule`, `explanation` comes from `explain_possible_match` and `evidence` from `evidence_lines`. `EntityDetail.provenance` comes from the `:SourceRecord` nodes of merged entities.
4. `neonradar api serve --real`, for a human on an approved machine: it refuses (exit 2) unless stdin is a terminal (`require_terminal`, M2.2), runs conditions 3 to 5 of the real-data gate (M2.2), binds `127.0.0.1:8001`, connects through `neonradar_graph.instances.Instance.REAL` (M2.11: `NR_NEO4J_REAL_URI`, `NEO4J_REAL_PASSWORD` and the real instance's only database, `realdata`), and prints one line saying that real data is being served on this machine only. Without `--real`, `api serve` connects through `Instance.DEFAULT` (database `neo4j`), which holds synthetic data only, as in Phase 1. The agent never runs `--real` (`guard_real_data.py` blocks it). Test: with closed stdin it exits 2 before opening any connection.
5. **Fixtures and integration tests.** The ownership fixture `graph/tests/fixtures/ownership/cases.ftm.jsonl` (synthetic, committed) and `expected.json`, built from the table below. The resolution fixture `api/tests/fixtures/resolution/` (synthetic, committed): the records and a hand-written resolution run (`canonical.csv`, `candidates.jsonl` and a minimal `run.json` with `run_id` and `resolver_version`, in the format of 7.1.8, which `ResolutionMap.load` reads, M2.11) with one entity merged from three records (its anchor, a D1 member and a probabilistic member), one single-record entity, a probabilistic possible match with `features`, a deterministic possible match with rule `D1` and reason `identifier_name_mismatch`, and a `source_hint` possible match. `api/tests/test_ownership.py`, `test_paths.py` and `test_resolution.py` (integration) load their fixture into their own Testcontainers database (the resolution fixture with `--resolution`). `test_resolution.py` checks every member's method and explanation, the order of the possible matches (the probabilistic one first, then the two without a probability by id), the null probability and rule `D1` of the deterministic one, and "not confirmed" in every possible-match explanation. The expected values are the oracle: a test that disagrees with the table is a failing test, not a reason to change the table.
6. `docs/decisions/0019-ownership-and-effective-share.md` (status `proposed`; deciders: tech lead and graph mentor): only `OWNS` in the ownership view (holdings through a trust or firm are `CONTROLS` of type `trust-or-firm`, M2.3b, so `/paths` reaches them but effective shares never include them); products of band bounds along a path, as ranges, rounded to 4 decimals before filtering; no sums across paths in the API (aggregation belongs to the reader and to Phase 3's `sanctions_exposure`, where PHASE-1.md 7.2 explains why the OFAC rule does not multiply down); an effective share is never presented as the result of a sanctions ownership test (7.2 rule 6); open and closed bounds taken from the statutory bands (5.1); simple paths only; limits and timeouts.

**Ownership fixture** (every id has the prefix `syn-own-`; companies are `co-1` to `co-6`, people `p-1` and `p-2`; bands as `Ownership` records with `percentage`, `nr.share_pct_min`, `nr.share_pct_max` and the two `nr` share flags). Intervals are written with `(` or `)` for an open bound and `[` or `]` for a closed one; in the API an open lower bound is `effective_share_min_exclusive: true` and an open upper bound `effective_share_max_exclusive: true`.

| Ownership | Owner to asset | Band |
|---|---|---|
| O1 | `p-1` to `co-1` | `(25, 50]` |
| O2 | `co-1` to `co-2` | `(50, 75)` |
| O3 | `co-2` to `co-3` | `[75, 100]` |
| O4 | `p-2` to `co-2` | `(25, 50]` |
| O5 | `co-4` to `co-3` | none (no percentage) |
| O6 | `co-5` to `co-6` | `(50, 75)` |
| O7 | `co-6` to `co-5` | `(25, 50]` |

Expected results:

| Request | Paths in order (node ids without the prefix), with effective share min and max |
|---|---|
| `co-3`, up, `max_hops=6`, `min_share=0` | `co-2, co-3` `[75, 100]`; `co-1, co-2, co-3` `(37.5, 75)`; `p-2, co-2, co-3` `(18.75, 50]`; `p-1, co-1, co-2, co-3` `(9.375, 37.5)`; `co-4, co-3` null |
| `co-3`, up, `max_hops=6`, `min_share=40` | the first three of the row above |
| `co-3`, up, `max_hops=6`, `min_share=37.5` | the first three: the fourth path's maximum, 37.5, is open, so it cannot reach 37.5 |
| `co-3`, up, `max_hops=6`, `min_share=50` | the first three: the third path's maximum, 50, is closed |
| `co-3`, up, `max_hops=1` | `co-2, co-3` `[75, 100]`; `co-4, co-3` null |
| `p-1`, down, `max_hops=6` | `p-1, co-1` `(25, 50]`; `p-1, co-1, co-2` `(12.5, 37.5)`; `p-1, co-1, co-2, co-3` `(9.375, 37.5)` |
| `co-5`, up, `max_hops=4` | `co-6, co-5` `(25, 50]` only: the cycle back to `co-5` repeats a node |
| paths `p-1` to `co-3`, `max_hops=4` | `p-1, co-1, co-2, co-3`, effective `(9.375, 37.5)` |
| paths `p-1` to `p-2`, `max_hops=4` | `p-1, co-1, co-2, p-2`, effective null and both flags null (the last relationship points the other way) |

**Acceptance.**

```bash
uv run pytest -m integration api/tests/test_ownership.py api/tests/test_paths.py api/tests/test_resolution.py -q
uv run pytest graph/tests/test_wording.py resolve/tests/test_wording_levels.py api/tests/test_serve_real.py -q
python3 scripts/check_wording.py
make up && uv run neonradar graph load graph/tests/fixtures/ownership/
uv run neonradar api serve --port 8010 & API_PID=$!; sleep 3
curl -s "http://127.0.0.1:8010/api/v1/entities/syn-own-co-3/ownership?direction=up&min_share=0" | jq '.paths | length'   # 5
kill "$API_PID"
make contracts && git diff --exit-code contracts/openapi/v1.json   # no OpenAPI change (M2.1c declared every response)
make contracts-check && make cypher-lint && make check
```

(Port 8010 keeps clear of the Compose API container on 8000 and of the human-only real API on 8001. The integration tests use their own Testcontainers databases; only the `curl` line uses the local default instance, which holds synthetic data only.)

**Review focus (humans).** Work out two rows of the expected table with a pencil. Then ask: would an investigator read `(9.375, 37.5)` correctly as "more than 9.375 and less than 37.5 percent", and `[75, 100]` as "at least 75 percent"? Read the three possible-match explanations of the resolution fixture aloud: does each say what agreed, what differed and why the records were kept apart, without suggesting they are the same? Copilot squad: is the 503 detail helpful enough to retry with a better request?

**`queries/ownership_up.cypher`** (`ownership_down.cypher` is the same with the pattern line `MATCH p = (root)-[:OWNS]->{1,{{max_hops}}}(bottom:LegalEntity)` and the matching header comment):

```cypher
// C3 1.1.0 ownership, direction=up: chains of OWNS that end at the root (its owners).
// One query per max_hops value; Python picks the file variant and never builds Cypher from input.
// Effective shares are rounded to 4 decimals here, so the filter, the order and the API see the same values.
// lint-values: max_hops=1,2,3,4,5,6,7,8
MATCH (root:Entity {id: $root_id})
MATCH p = (top:LegalEntity)-[:OWNS]->{1,{{max_hops}}}(root)
WHERE all(n IN nodes(p) WHERE single(m IN nodes(p) WHERE m = n))
WITH p, relationships(p) AS rels
WITH p, rels,
     CASE WHEN all(r IN rels WHERE r.share_pct_min IS NOT NULL)
          THEN round(reduce(acc = 1.0, r IN rels | acc * r.share_pct_min / 100.0) * 100.0, 4) END AS eff_min,
     CASE WHEN all(r IN rels WHERE r.share_pct_max IS NOT NULL)
          THEN round(reduce(acc = 1.0, r IN rels | acc * r.share_pct_max / 100.0) * 100.0, 4) END AS eff_max,
     any(r IN rels WHERE coalesce(r.share_min_exclusive, false)) AS min_open,
     any(r IN rels WHERE coalesce(r.share_max_exclusive, false)) AS max_open
WHERE $min_share = 0
   OR (eff_max IS NOT NULL AND (eff_max > $min_share OR (eff_max = $min_share AND NOT max_open)))
RETURN [n IN nodes(p) | n.id] AS node_ids, [r IN rels | r.id] AS edge_ids,
       eff_min, eff_max,
       CASE WHEN eff_min IS NULL THEN null ELSE min_open END AS eff_min_exclusive,
       CASE WHEN eff_max IS NULL THEN null ELSE max_open END AS eff_max_exclusive,
       size(rels) AS hops
ORDER BY eff_max IS NULL, eff_max DESC, hops, node_ids
LIMIT $scan_limit;
```

**`queries/paths.cypher`:**

```cypher
// C3 1.1.0 paths: up to 5 shortest paths, any direction, over the allowed relationship types.
// lint-values: max_hops=1,2,3,4,5,6
MATCH (a:Entity {id: $from_id})
WITH a
MATCH (b:Entity {id: $to_id})
MATCH p = SHORTEST 5 (a)((x)-[r]-(y) WHERE type(r) IN $rel_types){1,{{max_hops}}}(b)
RETURN [n IN nodes(p) | n.id] AS node_ids, [rel IN relationships(p) | rel.id] AS edge_ids,
       [rel IN relationships(p) | type(rel)] AS types,
       [rel IN relationships(p) | startNode(rel).id] AS starts,
       [rel IN relationships(p) | rel.share_pct_min] AS mins,
       [rel IN relationships(p) | rel.share_pct_max] AS maxes,
       [rel IN relationships(p) | coalesce(rel.share_min_exclusive, false)] AS mins_open,
       [rel IN relationships(p) | coalesce(rel.share_max_exclusive, false)] AS maxes_open,
       length(p) AS hops
ORDER BY hops, node_ids;
```

**`queries/resolve_id.cypher`:**

```cypher
// An entity id or the id of any record merged into it (C3: "accepts a canonical id or any id in referents").
MATCH (e:Entity {id: $id})
RETURN e.id AS id
UNION
MATCH (:SourceRecord {id: $id})-[:RESOLVED_TO]->(e:Entity)
RETURN e.id AS id;
```

**`queries/resolution_members.cypher`:**

```cypher
// C3 1.1.0 resolution, first query: the entity and its source records, in record id order.
MATCH (e:Entity {id: $id})
OPTIONAL MATCH (s:SourceRecord)-[r:RESOLVED_TO]->(e)
WITH e, s, r
ORDER BY s.id
WITH e, collect(CASE WHEN s IS NULL THEN NULL ELSE {record: properties(s), link: properties(r)} END) AS members
RETURN properties(e) AS entity, labels(e) AS labels, members;
```

**`queries/resolution_candidates.cypher`:**

```cypher
// C3 1.1.0 resolution, second query: at most 50 possible matches, highest match probability first;
// deterministic and source-hint matches have no probability and come last (Neo4j sorts nulls first in DESC).
MATCH (e:Entity {id: $id})-[p:POSSIBLY_SAME_AS]-(o:Entity)
RETURN properties(o) AS other, labels(o) AS labels, properties(p) AS link
ORDER BY p.match_probability IS NULL, p.match_probability DESC, o.id
LIMIT 50;
```

### M2.13 One command per profile, and the load benchmark

| | |
|---|---|
| Squad, human owner | Docs, DX and Launch; tech lead |
| Depends on | M2.3c, M2.4, M2.5, M2.6a to M2.6d, M2.10c, M2.11, M2.12 (M2.6e and M2.7 if they ran) |
| Branch | `p2/m2-13-load-profile` |
| Labels | `agent`, `phase-2`, `squad:docs`, `real-data-run` |
| Plan first | No |
| Real-data run | `make up-real`, `make load PROFILE=uk-tiny`, then `uv run neonradar load --profile uk-sample --skip-fetch`, `uv run neonradar bench queries --profile uk-sample --real` and the two `bench report` commands (operator, approved machine) |

**Deliverables.**

1. `cli/src/neonradar_cli/load.py` and the command `neonradar load --profile <name> [--skip-fetch] [--skip-officers]`: for a real profile it first applies the real-data gate (M2.2) and checks that the real instance answers (`make up-real`, M2.0); then it runs `data fetch` (real profiles only; `--skip-fetch` uses the downloads already present), `ingest build`, `er run`, `graph migrate`, `graph load --profile <name> --resolution latest` and `graph verify` (I1 to I14), with `--real` on `graph migrate` and `graph verify` for a real profile (`graph load` sends real records to the real instance by itself, loader rule L17), times each step, and emits one summary (M2.2) to `data/cache/reports/<profile>/load-<UTC timestamp>.json`: steps with durations, record counts by dataset and schema, resolution counts (7.1.8), node and relationship counts by label and type, invariant results, the versions of every source, and the hardware (CPU model and cores, RAM, operating system, Docker memory, the Neo4j memory settings), each under a key the command registers with `emit`. When the profile's `resolution.enabled` is false, `load` skips `er run` and loads without `--resolution`. `--skip-officers` sets the profile's `officers.request_budget` to 0 for this run only (in memory; the profile file does not change), so the officers step makes no request and builds officer records from the cache of earlier runs (M2.3c), counting the companies it could not reach. It stops at the first failing step, says which, and exits 1.
2. Makefile: `load` (`uv run neonradar load --profile $(PROFILE)`, `PROFILE ?= demo`). For the demo profile the stack must be up (`make up`); for a real profile, the real instance (`make up-real`).
3. `neonradar bench queries --profile <name> [--n 20] [--seed 20261102] [--real]` (with `--real` it runs the real-data gate first, M2.2): reads the ids of the eligible entities (`:Company` and `:Person` nodes with at least one `OWNS` relationship) with one read-only query, `graph/src/neonradar_graph/queries/bench_entities.cypher`, sorted by id, and picks `n` of them in Python by the order of `sha1(f"{seed}:{id}")` (Neo4j has no `sha1` without APOC). It times `/ownership` (up and down, `max_hops=6`), `/paths` between consecutive picks (`max_hops=4`), `/network` at depth 2 and `/search` with the first name token of each pick, through the API's own functions (no HTTP), and prints and emits only latencies (p50, p95, maximum per endpoint), counts of paths returned and timeouts, never an id or a name (`bench-queries-<UTC timestamp>.json`).
4. `neonradar bench report --profile <name> --out docs/data/benchmarks/<date>-<name>.md`: renders the newest `load` and `bench-queries` summaries of that profile as Markdown (counts only), with a line comparing against the plan's targets (graph load under 10 minutes, demo queries under 2 seconds) and the sources-and-licences footer of 7.3 for the datasets loaded.
5. CI: the `e2e` workflow (PHASE-1.md M1.9e) keeps its Phase 1 order (`make demo-mini`, then `make e2e`) and then gains two steps, `make load PROFILE=demo` and `uv run neonradar graph verify`, so the Playwright tests still see the graph they were written for and G2-03 has evidence on every push to `main`.
6. `docs/quickstart.md`: a section "Load real public data" (prerequisites: an approved machine, `access.real_data_profiles` and `access.data_protection_filed`, the Companies House key, disk space from 7.8; `make up-real`; `make load PROFILE=uk-tiny`; what the summary means; how to purge, including the real instance's volume).
7. Tests (`cli/tests/test_load.py`, every step function replaced by a fake): the steps run in order and stop at the first failure, which the command names, with exit 1; a synthetic profile never runs `data fetch` and never uses `--real`; `--skip-fetch` skips the fetch; `--skip-officers` sets the budget to 0 for the run and leaves the profile file unchanged; the summary has every field above and passes `emit`; `bench queries` picks the same ids for the same seed (a pure function) and its output contains no id.

**Acceptance.**

```bash
make up && make load PROFILE=demo                        # every step ok; invariants I1 to I14: 0 violations
uv run neonradar bench queries --profile demo --n 10     # latencies only
uv run neonradar bench report --profile demo --out /tmp/demo-bench.md && grep -q "graph load" /tmp/demo-bench.md
uv run pytest cli/tests/test_load.py -q
make cypher-lint && make check
```

**Real-data run (operator).** On an approved machine with `access.real_data_profiles: [uk-tiny, uk-sample]` and `access.data_protection_filed: true`: `make up-real`; `make load PROFILE=uk-tiny`; then, on Monday 2 November, `uv run neonradar load --profile uk-sample --skip-fetch` (it reuses Friday's downloads and officer cache, 1.8: a new fetch would bring a newer daily PSC snapshot, and possibly a new monthly companies file, and so change the slice away from the officer cache; add `--skip-officers` if Friday's crawl did not finish and there is no time for the rest); then `uv run neonradar bench queries --profile uk-sample --real`, and `uv run neonradar bench report --profile uk-tiny --out docs/data/benchmarks/2026-11-02-uk-tiny.md` and the same for `uk-sample`. Commit the two reports (counts only) to this pull request.

**Review focus (humans).** Is anything in the two reports more than counts, timings and versions? Did the graph load stay under 10 minutes? If not, which step was slow?

### M2.14 Entity resolution documentation and the Assignment 3 kit

| | |
|---|---|
| Squad, human owner | Graph and ER with Docs; graph mentor and technical writer |
| Depends on | M2.10b |
| Branch | `p2/m2-14-er-docs` |
| Labels | `agent`, `phase-2`, `squad:docs`, `squad:graph`, `er`, `learning` |
| Plan first | No |
| Real-data run | none |

**Deliverables.**

1. `docs/er/README.md`: how NeonRadar resolves entities, for a new intern: the pipeline (4.1), the keys (M2.8), the deterministic rules, the Splink models and the Fellegi-Sunter idea in plain words, constrained clustering, the merge policy and why it exists (G8), possible matches, the outputs, how precision is measured (7.3) and the benchmark, and the limitations (Arabic transliteration is lossy; common names; the UK slice; precision is not recall; sanctions, PEP and ICIJ records are never merged by probability, so the published figure does not measure screening accuracy; the absence of a flag says only that the loaded lists do not list a record, 7.2 rule 5). Diagrams in Mermaid. Every AML or legal statement cites a bibliography key.
2. `docs/er/labelling-guide.md`: what "the same entity" means (one real person, or one legal entity: a subsidiary is not its parent; a trading name is the same company); how to judge from partial information; the common traps with synthetic examples (transliterations, initials, swapped name order, moved addresses, near twins, parent and subsidiary, a name change); when to answer `unsure` (and that every `unsure` lowers the published bound, 7.3 rule 3); the privacy rules for labelling sessions (approved machine, no screenshots, no real names outside the session, labels stay in `data/cache/real/labels/`); how adjudication works (blind, by someone who did not set the thresholds); ten worked examples drawn from the synthetic benchmark, each with the right answer and the reason.
3. `docs/team/assignment-3.md` (due Tuesday 3 November): each intern reads the Splink introduction to the Fellegi-Sunter model and this project's `docs/er/README.md`, labels at least 20 pairs in one session with `neonradar er label` (the samples are split across every handle in `people.er_labellers`, which includes every intern, by `er sample`), and writes in their own learning log five hard cases described by their features only ("same surname, birth years one apart, different nationality"), never by name. At the teach-back on Thursday 5 November, each presents one case. AI help is allowed for understanding the method, never for labelling (G10).
4. `docs/glossary.md`: the entries in 7.6. `docs/sources/bibliography.yaml`: the entries in 7.5. `docs/learning/reading-list.md`: the sprint 1 entries (Splink documentation, the Fellegi-Sunter model). `docs/architecture/overview.md`: the Phase 2 data flow, including the separate real Neo4j instance.
5. `aml-claims-checker` and `data-guardian` report no BLOCKING findings.

**Acceptance.** `uv run python scripts/check_citations.py docs/` passes; every example in the labelling guide has an id that exists in `data/fixtures/er-bench/` (a small test reads the guide and checks); Mermaid renders in GitHub's preview (operator); `make check`.

**Review focus (humans).** Would a new intern, after reading the guide, label the ten examples the way the guide does? Does anything in the guide teach a habit that would leak real data?

### M2.15 The published precision figure

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor (labellers label; the project lead adjudicates; the tech lead signs the report) |
| Depends on | M2.13 (the `uk-sample` data), M2.14, ADR-0014 accepted (the freeze, with the evaluation sample seed) |
| Branch | `p2/m2-15-precision` |
| Labels | `agent`, `phase-2`, `squad:graph`, `er`, `real-data-run` |
| Plan first | No |
| Real-data run | the evaluation run, the sampling and the precision computation (the labelling and the adjudication are human work, outside the agent's session) |

**Steps.**

1. Operator (approved machine): `uv run neonradar er run --profile uk-sample --no-decisions`. This is the evaluation run (7.3 rule 1): the frozen configuration, no review decisions applied. It prints counts only; note its run id.
2. Operator: `uv run neonradar er sample --profile uk-sample --run <evaluation run id> --seed <the seed in ADR-0014> --labellers <every handle in people.er_labellers>`. It writes the samples of 7.3, interleaved and split across the labellers with the S4 overlap, and prints counts only.
3. Labellers, each in their own session on an approved machine: `uv run neonradar er label --profile uk-sample --run <run id> --labeller @handle`. Every intern labels at least 20 pairs (G2-13).
4. The project lead (or another person who did not set the thresholds) adjudicates the S4 disagreements without seeing either label: `uv run neonradar er label --profile uk-sample --run <run id> --adjudicate --labeller @handle`.
5. Operator, or the agent in a session on that machine if the operator says so: `uv run neonradar er precision --profile uk-sample --run <run id> --out docs/data/er/precision-<date>.md`.
6. The agent: put the figure into `README.md` (the sentence of 7.3 rule 7, verbatim with the values filled in, in a new "How well it works" section, with a link to the report) and into `docs/er/README.md`; open the pull request with the report.

**Acceptance.** The report has every field of the template in 7.3, including the unsure bound, the S2 interval, the four agreement figures and the sources-and-licences footer; S1 has at least 250 labels other than `unsure`, or the report's first line says why not (7.3 rule 5); at least four labellers; MANUAL: the graph mentor confirms that every intern in `people.interns` labelled at least 20 pairs (G2-13), because the agent never reads the label files; the evaluation run's `run.json` says `decisions_used: false`; `data-guardian` finds nothing but counts in the diff; `make check`.

**Review focus (humans).** Tech lead and graph mentor: was the configuration frozen, and the seed recorded in ADR-0014, before the sample was drawn? Is the unsure share under 15 percent, and how far apart are the headline and the unsure bound? Would you defend the sentence in the README in front of a sceptical journalist?

### M2.16 Gate 2 check and the Phase 2 report

| | |
|---|---|
| Squad, human owner | Release manager; the tech lead decides Gate 2 with the data steward |
| Depends on | Everything else in Phase 2 |
| Branch | `p2/m2-16-gate-2` |
| Labels | `agent`, `phase-2`, `squad:docs` |
| Plan first | No |
| Real-data run | none |

**Deliverables.**

1. `neonradar gate check --phase 2` in `cli/src/neonradar_cli/gate.py` (extend the Phase 1 command): one line per check in section 8 (`G2-01` to `G2-15`) with PASS, FAIL or MANUAL and the evidence. Checks that need Docker, `gh` or a real-data report that is not in the repository say MANUAL with the reason; G2-10 is always MANUAL (the data steward confirms the controls, including the documents in `docs/data/dpia/`). It never creates tags, approves anything or edits other people's files. Makefile `gate-2`. Unit tests for the checks that only read files.
2. `docs/build/reports/phase-2.md`: what was built (milestones and pull requests), metrics (merged pull requests and the share labelled `agent`; the benchmark numbers; the precision figure with its unsure bound; load and query timings from M2.13), deviations from `PROGRESS.md` and from the reconciliation, risks still open, the data steward's confirmations (the data protection documents were filed before any real profile ran; real data older than `access.real_data_days` and labels older than `access.label_days` were purged on every approved machine, including the real instance's volume), the inputs Phase 6 needs for the published benchmark, and the decisions Phase 3 to Phase 5 must know (canonical ids, possible matches in subgraphs, the resolution endpoint, the separate real instance).

**Acceptance.** `make gate-2` runs and every check that is not MANUAL passes or is explained in the report; `make check`.

---

## 7. Knowledge base and policy reference

### 7.1 Entity resolution reference

This is the authority for every matching decision in Phase 2. The resolver (M2.10), the loader (M2.11), the API (M2.12), the documentation (M2.14) and the reviewers all use it. Rule ids are stable: tests, `conflicts.jsonl`, `candidates.jsonl` and the pull requests refer to them.

#### 7.1.1 What gets resolved

| Class | FtM schemata | How |
|---|---|---|
| `person` | `Person` | deterministic rules, then the Splink person model |
| `org` | `Company`, `Organization`, `PublicBody` | deterministic rules, then the Splink organisation model |
| `legal_entity` | `LegalEntity` (for example ICIJ officers, whose kind the source does not state) | compared in both the person and the organisation pool; a merge must still pass X2 (schema compatibility) |
| `address` | `Address` | deterministic only (D6); addresses carry no topics or flags, so P1, P2 and the name check do not apply to them, and an address is never a possible match |
| not resolved | every other schema (accounts, payments, positions, sanctions, all relationship schemata) | passed through; their entity references are re-pointed to canonical ids by the loader |

Records are never compared across the synthetic and real boundary (X1), and every blocking rule includes `l.synthetic = r.synthetic`.

A record's **flag topics** are its `topics` that are not purely descriptive, and a record is **listed** when it has at least one. The descriptive topics are `corp.public`, `fin` and every `fin.*`, `gov` and every `gov.*`, `pol.party`, `pol.union`, `rel` and `mil`; every other topic in the FollowTheMoney 4.11 vocabulary (`sanction` and `sanction.*`, `role.*` including `role.pep` and `role.rca`, `crime` and `crime.*`, `debarment`, `export.*`, `asset.frozen`, `corp.disqual`, `corp.shell`, `poi`, `wanted`, `reg.*`, `mare.*` and the rest) is a flag topic. `neonradar_resolve.policy.flag_topics(topics)` implements this, and a test fails when FollowTheMoney adds a topic the rule has not classified. A record is **leaked** when its kind is `leak`: a record of `icij_offshore_leaks`, or a synthetic leak-style record (`nr.synthetic_kind: leak`, M2.9).

Two more facts about listed records feed the rules. A record's **list source** is the list it comes from: its dataset for a `kind: list` dataset, or `nr_synthetic:<authority>` for a synthetic list-style record (P6 compares them). A record is a **whole party** of its list when the list publisher keeps one entry per person or organisation: every record of `us_ofac_sdn`, `un_sc_sanctions`, `eu_fsf`, `gb_parliament_members` and `opensanctions_default`, and the UK Sanctions List records grouped by OFSI Group ID (`uksl-g...`). UK designations made without an OFSI Group ID (`uksl-un-...`, `uksl-<unique id>`) are not, because newly designated persons "will not be assigned an" OFSI Group ID and one person can hold one Unique ID per regime (`sanctions-peps.md` 1.1 and 1.9); X6 uses this.

#### 7.1.2 Deterministic rules

Applied in this order, before any probabilistic matching. Each produces links with `method = "deterministic"` and the rule id.

| Rule | Links | Conditions |
|---|---|---|
| D1 | UK company number | Org-class or `legal_entity` records with the same normalised UK company number: a `gbch-co-<n>` record; a GLEIF record whose registration authority is `RA000585`, `RA000586` or `RA000587` with entity id `<n>`; a corporate PSC or corporate officer whose identification resolves to the UK register (3.3, M2.3b) with number `<n>`; a sanctions entry with a UK company number from a typed identifier field, or from free text only when a company-number label and a UK register stand next to it (M2.6 rule 6). Each record links to the `gbch-co-<n>` record when the load has one, otherwise to the other records with the same `<n>`. Normalisation (`neonradar_keys.ids.uk_company_number`): upper case; remove spaces, dots and hyphens; all digits: left-pad with zeros to 8; two letters that are one of the 36 Companies House prefixes (`neonradar_keys.ids.CH_PREFIXES`, `bulk-sources-loading.md` 2.6) followed by digits: pad the digits so the whole number has 8 characters; `SY` plus digits only for synthetic records; anything else is not a UK company number. A GLEIF number counts only when it already has 8 characters. |
| D2 | LEI | Records with the same `leiCode`, after upper-casing and the ISO 17442 check-digit test (`neonradar_keys.ids.is_valid_lei`). |
| D3 | Companies House person number | Person records from the officers API with the same first 8 characters of `nr.ch_person_number` (3.3 explains why only the first 8), with the name check. A different person number never blocks a merge: one person can hold several. |
| D4 | UN reference number | Listed records from different lists that carry the same normalised UN Security Council reference number (3.3 gives the field in each list). |
| D5 | Same native id | Two records of one dataset with the same native id in `nr.source_ref` (for example one ICIJ `node_id` that appears in two node files). |
| D6 | Address key | `Address` records with the same non-empty `address_key` (`neonradar_keys.addresses.address_key`, M2.8) that contains a full postcode or a street line, across datasets (an ICIJ address merges with a register address with the same key). Synthetic with synthetic and real with real only (X1). No name check and no P1 or P2: addresses carry no flags. |
| D7 | Human decision | A `same` decision in the decisions file (7.1.8) about two records of this run. Applied first. A `same` decision whose merge would cross P1 or P2 applies only when two different reviewers' newest lines for the pair say `same`, or one of them is in `people.er_senior_reviewers`; until then it waits and is counted as `decisions_awaiting_second_review`. |

**Name check.** A D1, D2, D3 or D4 link merges only if the two linked records also share an exact name key, or some pair of their name keys has a Jaro-Winkler similarity of at least 0.85 (`neonradar_keys.names.name_similarity`). A deterministic link whose merge would cross P1 or P2 (7.1.4) needs the strict form: an exact shared name key (for organisations, an exact organisation key). Similar names are not enough there: the keys of "Example Group" and "Example Group UK" score 0.96, and a list entry that carries its UK subsidiary's number would otherwise put the parent's flag on the subsidiary. A link that fails the check becomes a possible match with reason `identifier_name_mismatch`, with no probability and with its D rule. The check catches mistyped registration numbers, and it is what lets G8 accept identifier links between listed and unlisted records.

#### 7.1.3 Cannot-link rules

A merge that would put records breaking one of these rules into one cluster is refused, and the refusal is written to `conflicts.jsonl` (rule id and record ids; never values). X1 to X6 and X8 are hard rules: two clusters that break one of them never become a possible match either, so a human `different` decision, two different identifiers or incompatible birth dates remove the pair from review. Only X7 turns a link into a possible match.

| Rule | Refuse when the merged cluster would contain |
|---|---|
| X1 | a synthetic and a real record |
| X2 | schemata with no common FtM schema (`followthemoney.model.common_schema` raises), for example a `Person` and a `Company` |
| X3 | two different UK company numbers (D1 normalisation) |
| X4 | two different LEIs |
| X5 | two person records with no compatible pair of birth dates: two dates are compatible when they are equal at the precision both have (year, year and month, or full date); a record without a birth date is compatible with anything; a list entry that gives a range of at most 20 birth years carries every year of it (M2.6), so any one of them can be compatible |
| X6 | two different records of one list that are each a whole party of it (7.1.1): two OFAC entries, two EU entries, two UK records with different OFSI Group IDs, and so on. Ungrouped UK designations may merge with each other and with a grouped record |
| X7 | more than 30 records; a person, organisation or legal-entity link becomes a possible match with reason `cluster_cap`; an address link is only refused |
| X8 | two records that a human decision marks `different` |

#### 7.1.4 Merge policy

The policy decides whether an allowed link becomes a merge or only a possible match. It is the operational form of G8. The data steward, the project lead and the tech lead accept it in ADR-0015; changing it afterwards needs all three.

| Rule | Situation | Merges only through | Otherwise |
|---|---|---|---|
| P1 | a merge of two clusters whose flag topics differ (the union of their members' flag topics): a listed with an unlisted cluster, or clusters listed for different reasons, for example a PEP record and a sanctions record | a deterministic rule (D1 to D5) with the strict name check passed, or D7 | possible match, reason `listed_unlisted` (one side has no flag topic) or `listed_differently` |
| P2 | a merge that would put a leaked record and a record of another kind in one cluster | a deterministic rule (D1 to D5) with the strict name check passed, or D7 | possible match, reason `leaked_cross_source` |
| P3 | probabilistic link whose only agreeing evidence is the name | never merges | possible match, reason `name_only` (agreeing evidence means one of: birth date at year and month or better, a full postcode, a shared company, a shared identifier; for organisations a registration number, the incorporation year or a full postcode) |
| P4 | person, organisation or legal-entity link that would break X7 | never merges | possible match, reason `cluster_cap` |
| P5 | probabilistic link with probability between the candidate threshold and the merge threshold of the model that scored it | never merges | possible match, reason `below_merge_threshold` |
| P6 | two listed person records from different lists (their list sources differ), linked probabilistically | also needs compatible birth years on both sides or a shared identifier | possible match, reason `listed_needs_birth_date` |

**Flags after resolution.** The loader computes each canonical node's topics as the union of its members' topics, and its flag labels from those topics (PHASE-1.md 5.2). P1 compares flag topics, not only whether a record is listed, so a merge by probability happens only between clusters that already carry the same flag topics: it never adds a flag topic to any record's entity. Flags can join other records only through an identifier with the strict name check, or a human decision. A `POSSIBLY_SAME_AS` link never moves a topic, a flag, a name or any other property between nodes.

#### 7.1.5 The probabilistic models

Two Splink 5 models, `person` and `org`. Each is a Fellegi-Sunter model over one feature table that holds every record of its class from every dataset (`link_type="dedupe_only"`); `legal_entity` records are in both tables. The code is `resolve/src/neonradar_resolve/feature_schema.py` (M2.10a) and `models.py` (M2.10b), verbatim in those milestones; this section is the reference they implement. The API facts come from the installed Splink 5.0.0 and were run on 18 October 2026 (`er-splink.md` sections 2 and 3).

**Person feature table** (`features.py` builds it from each record and its context; every empty list is written as NULL, because Splink's null levels test `IS NULL` and an empty DuckDB list is not NULL, `er-splink.md` 2.3):

| Column | Built from |
|---|---|
| `unique_id`, `synthetic` | the record id; the dataset's flag |
| `name_key` | `person_key(name, given, family).key` of the record's first `name`, with `given` and `family` from `firstName` and `lastName` when the record has them |
| `name_key_rare` | `name_key` when at most 50 records of the table share it, else NULL (a blocking key without huge blocks) |
| `forename`, `surname`, `initial` | the first given-name and family-name tokens of that key and the forename's first letter; NULL when the source does not say which part is which |
| `name_tokens`, `name_symbols`, `skeletons` | the union over `name`, `alias` and `previousName` (never `weakAlias`) of the keys' tokens, Wikidata name symbols and consonant skeletons, at most 50 each |
| `birth_full`, `birth_ym`, `birth_years`, `birth_year_min`, `birth_ym_min` | the `birthDate` values at day, month and year precision, and the smallest year and month |
| `countries` | `nationality`, `citizenship` and `country` as lower-case codes |
| `postcode` | the first UK postcode of the record's addresses: `addressEntity` records first, then `address` text through `find_uk_postcode` |
| `linked_orgs` | for each organisation the record is linked to (the relationship schemata of 7.1.1): `uk:<company number>` when that organisation has a UK company number (D1 normalisation), else its record id |
| `identifiers` | `passport:<number>` and `id:<number>`, upper case, spaces removed |

**Organisation feature table:**

| Column | Built from |
|---|---|
| `unique_id`, `synthetic` | as above |
| `name_key`, `name_key_rare`, `name_prefix` | `org_key(name).key` of the first `name`; the rare form as above; its first four characters |
| `aliases` | the org keys of every `name`, `alias` and `previousName` |
| `ch_same_as` | `ch_same_as_key(name)` |
| `name_tokens` | the words of `name_key` |
| `jurisdiction` | the first `jurisdiction`, a `gb-` subdivision written as `gb` |
| `registration_numbers` | `uk:<company number>`, `lei:<LEI>`, and other registration numbers as `reg:<jurisdiction>:<value>` |
| `incorporation_year` | the year of `incorporationDate` |
| `postcode` | as for persons |
| `legal_forms` | `org_key(name).legal_forms` |

**Comparisons** (levels from the most to the least similar; every comparison also has a null level). The name comparisons are built from levels, because Splink's `NameComparison` always adds term-frequency adjustment and `configure(term_frequency_adjustments=False)` does not remove it; birth dates are custom, because `DateOfBirthComparison` misfiles month-year strings (`er-splink.md` 2.3).

| Model | Comparison | Levels |
|---|---|---|
| person | `name` | name key equal (term-frequency adjusted); forename and surname both Jaro-Winkler at least 0.92; surname equal and same initial; two name symbols shared; name key Jaro-Winkler at least 0.88; surname equal; two skeletons shared; else |
| person | `birth` | same date; same month; same year; years one apart; else |
| person | `countries` | a code shared; else |
| person | `postcode` | full postcode; sector; district; area; else (Splink's `PostcodeComparison`) |
| person | `linked_orgs` | two or more shared; one shared; else |
| person | `identifiers` | one shared; else |
| org | `org_name` | name key equal (term-frequency adjusted); a name or alias shared; same name under the Companies House rules; Jaro-Winkler at least 0.95; at least 0.88; two words shared; else |
| org | `jurisdiction` | equal; else |
| org | `registration_numbers` | one shared; else |
| org | `incorporation` | same year; one year apart; else |
| org | `postcode` | as for persons |
| org | `legal_forms` | one shared; else |

**Blocking** (every rule also requires equal `synthetic`, which enforces X1): persons on (`surname`, `birth_year_min`), (`forename`, `birth_ym_min`), (`postcode`, first letter of `surname`), a shared linked organisation, a shared name symbol with the same `birth_year_min`, and `name_key_rare`; organisations on `name_key`, `ch_same_as`, a shared registration number, a shared alias, and (`postcode`, `name_prefix`).

**Training**, on each run's own data (no trained parameters are committed): the prior `probability_two_random_records_match` from a deterministic rule with recall 0.7 (persons on `name_key` and `birth_ym_min`, organisations on `name_key`); u by random sampling with `max_pairs` 10 million and seed 20261026; two EM sessions with `max_pairs` 5 million (persons blocked on `surname` and `birth_year_min`, then `postcode`; organisations on `name_key`, then `postcode`; a session does not estimate the comparisons in its own blocking rule, so the two cover each other). Then `predict` at `candidate_threshold`; each scored pair becomes a `Link` that records the model that scored it (`model`), whose merge threshold applies (a pair of two `legal_entity` records can be scored by both models). Every probability is rounded to 9 decimals and every weight to 6; each pair's `features` maps each comparison to its level label (Splink gives the null level the value -1, the else level 0 and the most similar level the highest value).

**Inputs to P3 and P6.** `strong_evidence` (P3) is true when, for persons, `birth` is the same date or month, `postcode` is the full postcode, `linked_orgs` shares one or more, or `identifiers` shares one; for organisations, `registration_numbers` shares one, `incorporation` is the same year, or `postcode` is the full postcode. `birth_or_id_agrees` (P6) is true when `birth` is the same date, month or year or the years are one apart, or `identifiers` shares one (`models.BIRTH_OR_ID`; X5 still refuses any merge whose birth dates are not compatible, so years one apart pass only when one record carries several birth years).

**Determinism and size.** DuckDB settings go on the connection (`DuckDBAPI` has no memory or thread options): `threads` and `memory_limit` from `er.yaml`, `temp_directory` `duckdb_tmp_dir(profile, run_id)` (`data/cache/real/duckdb-tmp/<run_id>/` for a real profile, `data/cache/synthetic/duckdb-tmp/<run_id>/` otherwise; deleted when the run ends, even after a failure), `preserve_insertion_order=false`. Tests and the benchmark use one thread (bitwise identical results); with more threads, weights differ around 1e-14, which the rounding absorbs (`er-splink.md` 3.3; checked on the M2.10b test data with one and two threads). If blocking would generate more than `max_comparisons` (20 million, the Splink documentation's guidance for a laptop, `er-splink.md` 7), `er run` stops before predicting and prints the counts per rule. Splink's HTML dashboards are not used on real data (they also fetch web fonts, `er-splink.md` 6).

#### 7.1.6 Constrained clustering and canonical entities

The resolver builds clusters with its own constrained union-find, not with Splink's clustering, because Splink's clustering cannot refuse a merge (it takes connected components of the links above a threshold).

```text
clusters = one cluster per resolvable record
for each human "same" decision about two records of this run, by (record_a, record_b):
    if the merge would cross P1 or P2 and neither two reviewers nor a senior reviewer said same:
        wait (decisions_awaiting_second_review); continue
    if merging would break X1 or X2:           write conflict; continue
    merge                                      (human decisions override the policy and X3 to X8)
for each deterministic link, in rule order D1, D2, D3, D4, D5, D6, then by (record_a, record_b):
    if merging would break X1..X6 or X8:       write conflict; continue
    if it links two addresses (D6):            merge, unless that breaks X7 (write conflict); continue
    if the name check is required and fails:   add possible match (identifier_name_mismatch); continue
                                               (the strict form when the merge would cross P1 or P2)
    if merging would break X7:                 write conflict; add possible match (cluster_cap); continue
    merge
round every probability to 9 decimals                (floating-point noise must not change the order)
for each probabilistic pair with p >= candidate_threshold,
        in order of p descending, then (record_a, record_b):
    if merging would break X1..X6 or X8:       write conflict; continue   (never a possible match)
    if p < merge_threshold[the pair's model]:  add possible match (below_merge_threshold); continue
    if P1, P2, P3 or P6 forbids it:            add possible match (reason); continue
    if merging would break X7:                 write conflict; add possible match (cluster_cap); continue
    merge
for each source hint between two records of this run that are not addresses:
    if the two clusters break X1..X6 or X8:    write conflict; continue
    add possible match (source_hint:<hint>, no probability)
collapse possible matches to pairs of clusters: keep the pair with the highest p (no probability
    counts as lowest), then the smallest record ids, and the union of reasons;
drop any possible match whose two records ended up in the same cluster, and write as a conflict any
    whose clusters now break X1..X6 or X8 (a later merge can add a birth date or an identifier)
```

Each X check is a set operation over the members of the two clusters (company numbers, LEIs, birth dates, whole-party lists, schemata, the synthetic flag, size, "different" decisions). The order makes the result deterministic: the same inputs, configuration and seed give byte-identical `canonical.csv`, `candidates.jsonl` and `conflicts.jsonl`.

**Anchor and canonical id.** A cluster with one record keeps that record's id. A cluster with two or more records gets `nr-<anchor record id>`. The anchor is the member whose dataset comes first in this list, then the lexicographically smallest record id: `gb_companies_house`, `gleif_lei`, `gb_fcdo_sanctions`, `un_sc_sanctions`, `eu_fsf`, `us_ofac_sdn`, `gb_parliament_members`, `opensanctions_default`, `icij_offshore_leaks`, `nr_synthetic`.

**Property merge rules** (applied by the loader, M2.11):

| Property | Rule |
|---|---|
| `schema` | the most specific common FtM schema of the members |
| `caption` | the anchor's caption |
| `names` | the union, anchor first, then members in anchor order, exact duplicates removed, at most 50 |
| `countries`, `topics`, `datasets`, `referents` | sorted unions |
| scalar schema properties (`registration_number`, `jurisdiction`, `lei`, `status`, `legal_form`, `incorporation_date`, `dissolution_date`, `gender`, `accounts_category`) | the anchor's value; if the anchor has none, the first non-empty value in member order (dataset priority, then record id) |
| list schema properties (`nationalities`, `psc_statements`) | sorted unions |
| `birth_date` | the most precise of the members' compatible values (X5 guarantees there is one) |
| `first_seen`, `last_seen` | minimum and maximum |
| `synthetic` | the members' common value (X1) |
| `cluster_size`, `resolution` | number of members; `identity`, `deterministic`, `probabilistic`, `human` or `mixed` (more than one method among the member links) |

#### 7.1.7 Thresholds and calibration

| Setting (`resolve/config/er.yaml`) | Starting value | Set by |
|---|---|---|
| `merge_threshold.person` | 0.99 | M2.10b calibration, then ADR-0014 |
| `merge_threshold.org` | 0.995 | M2.10b calibration, then ADR-0014 |
| `candidate_threshold` | 0.80 | M2.10b calibration, then ADR-0014 |
| `cluster_cap` | 30 | fixed (X7) |
| `name_check_jaro_winkler` | 0.85 | fixed (7.1.2; the strict form across P1 and P2 uses exact keys) |
| `seed` | 20261026 | fixed (the training seed, and the default of `--seed` for the benchmark commands) |
| `duckdb.threads`, `duckdb.memory_limit` | 4, `4GiB` (DuckDB reads `GB` as decimal) | operator (1 in tests and the benchmark) |
| `training.u_max_pairs`, `training.em_max_pairs`, `training.prior_recall` | 1e7, 5e6, 0.7 | M2.10b, then ADR-0014 |
| senior reviewers | `people.er_senior_reviewers` in `project.yaml`, not `er.yaml` | tech lead and graph mentor (1.2) |
| `max_comparisons` | 20,000,000 | fixed (7.1.5) |

Calibration protocol (M2.10b): run the resolver on the large synthetic benchmark (`--size large`), predict once at 0.50, and for each class report, at each value `t` of the sweep, the precision and recall with `merge_threshold = t` and the recall of policy-blocked true pairs as possible matches with `candidate_threshold = t`. Choose the lowest merge threshold whose precision among merged pairs of that class is at least 0.98, and the highest candidate threshold whose policy-blocked recall is at least 0.90. Write the curve and the chosen values to `docs/data/er/benchmark.md`. Thresholds come from the synthetic benchmark only: no real pair is labelled before the freeze. At the freeze (Thursday 29 October) the tech lead and the graph mentor accept ADR-0014 with the values and the seed for the precision sample (7.3); from then until Gate 2, changes need both of them and void the evaluation sample (G10).

**Benchmark measures** (`er bench` in M2.10a and M2.10b, `er calibrate` in M2.10b). A *true pair* is two records of the same class with the same `entity_id` in `labels/er_truth.csv`. A true pair is *policy-blocked* when its two records have different flag topics or exactly one of them is leak-style (P1, P2), and *mergeable* otherwise. *Pairwise precision* of a class is the share of record pairs of that class in one cluster that are true pairs (precision among merged pairs of that class); *recall* is the share of mergeable true pairs of that class whose two records ended up in one cluster. A policy-blocked true pair is *recalled as a possible match* when its two records ended up in one cluster through a deterministic rule with the name check or a decision, or when their two clusters are joined by a line of `candidates.jsonl`. A *hard negative merged* is any record of an entity in one cluster with a record of its `twin_of` entity. Pairs of address records are not counted.

#### 7.1.8 Resolver outputs and the decisions file

All files in `data/cache/<real|synthetic>/resolution/<profile>/<run_id>/`. Rows are sorted, so files are byte-stable.

| File | Content |
|---|---|
| `canonical.csv` | `record_id,canonical_id,class,cluster_size,method,rule,match_probability,via,path_methods,features` for every resolvable record. `method` is `identity` (single record), `anchor`, `deterministic`, `probabilistic` or `human`: how the record joined; `rule` is the D rule or empty; `match_probability` is empty for `identity`, the probability for `probabilistic` and 1.0 otherwise; `via` is the record at the other end of the link it joined through (empty for `identity` and `anchor`); `path_methods` lists the distinct methods on its path from the anchor, sorted and joined with `+` (for example `deterministic+probabilistic`; empty for `identity` and `anchor`), which is what the precision frames read (7.3); `features` is the joining link's comparison levels as compact JSON with sorted keys (probabilistic only), which the loader copies to `RESOLVED_TO` (M2.11) |
| `candidates.jsonl` | one possible match per line: `a`, `b` (canonical ids, `a < b`), `record_a`, `record_b` (the best pair, `record_a` in `a`), `match_probability` (null for `deterministic` and `source_hint`), `match_weight` (null unless probabilistic), `method` (`probabilistic`, `deterministic` or `source_hint`), `rule` (the D rule of a deterministic possible match, else null), `reasons` (`listed_unlisted`, `listed_differently`, `leaked_cross_source`, `name_only`, `listed_needs_birth_date`, `cluster_cap`, `below_merge_threshold`, `identifier_name_mismatch`, `source_hint:<hint>`), `features` (comparison name to level label). Every line joins two person, organisation or legal-entity clusters |
| `conflicts.jsonl` | `rule`, `record_a`, `record_b`, `link_method` (`human`, `deterministic`, `probabilistic` or `source_hint`), `link_rule`; never values |
| `pairs.parquet` | every scored pair at or above the candidate threshold: record ids, class, probability, weight, the level of each comparison; `er calibrate` re-clusters from it (M2.10b), while the precision sample is drawn from `canonical.csv` and `candidates.jsonl` (7.3) |
| `models/person.json`, `models/org.json` | the trained Splink models of this run (parameters only) |
| `run.json` | run id, profile, resolver version, `er.yaml` hash, thresholds, seeds, input manifests (dataset, file, records, sha256), `decisions_used` (false for `er run --no-decisions`), counts (records by class, links by rule, merges, possible matches by reason, conflicts by rule, cluster sizes in buckets 1, 2, 3 to 5, 6 to 10, 11 to 30, `decisions_on_file`, `decisions_applied`, `decisions_not_applicable`, `decisions_awaiting_second_review`, `hints_used`, `hints_not_applicable`), timings per step; also written there through `emit` as `er-run-<UTC timestamp>.json` (M2.2) |

**Decisions file** (`decisions_file(profile)`: `data/cache/real/decisions.jsonl` for a real profile, `data/cache/synthetic/decisions.jsonl` for a synthetic one, and for tests the synthetic `resolve/tests/fixtures/decisions.jsonl`): one JSON object per line, written only by `neonradar er review` (M2.10c) from a human's answer:

```json
{"record_a": "syn-erb-p-0101-1", "record_b": "syn-erb-p-0101-3", "decision": "same", "by": "@example", "at": "2026-11-02T10:15:00Z", "note": "same birth month, same company, initials match"}
```

`decision` is `same` or `different`. The newest line for a pair decides; for a `same`, the reviewers are the handles whose own newest line for the pair says `same` (D7 says when two are needed). Decisions refer to record ids, so they survive new resolution runs; a decision whose two records are not both in a run is skipped and counted as `decisions_not_applicable`. The evaluation run for the published figure ignores the file (`er run --no-decisions`, 7.3).

### 7.2 Wording for resolution, possible matches, flags and ownership

PHASE-1.md 7.1 still governs all entity-facing text. Phase 2 adds text about merges, possible matches, the absence of flags and effective shares, which the API's resolution endpoint renders (M2.12) and the UI and the copilot reuse. The templates below live in `graph/src/neonradar_graph/wording.py` (so the API can use them without the resolver's dependencies), are copied from this section verbatim, pass the forbidden-pattern lint, and are tested.

| Write | Never write |
|---|---|
| "Merged from 3 source records: Companies House officer, Companies House PSC, GLEIF." | "identified as", "is really" |
| "Joined by the same UK company number." / "... the same LEI." / "... the same Companies House person number (its first 8 characters) and similar names." / "... the same UN reference number." / "... the same address." / "... a reviewer's decision." / "... probabilistic matching (match probability 0.997)." | "proven to be the same" |
| "Possible match, not confirmed. Agreeing: same name, same birth month, a shared nationality or country. Differing: postcodes." | "is the same person as", "matches the sanctioned person", "sanctions hit" |
| "Kept separate because one record is on a sanctions or PEP list and the other is not (policy P1)." | "is on the sanctions list" about a node whose flag does not come from its own records |
| "Kept separate because the records are listed for different reasons, for example one on a sanctions list and one as a politically exposed person (policy P1)." | a flag of one record described on the node of the other |
| "Kept separate because one record comes from the ICIJ Offshore Leaks Database (policy P2)." | "appears in the leaks" about a node whose own records include no ICIJ record |
| "Possible match, not confirmed. Both records give the same UK company number, but the names differ, so they were not merged." | "is the same company as" |
| "The published bands along 2 ownership links give an indirect share of more than 12.5 and less than 37.5 percent (a NeonRadar calculation, not a figure the register records)." | "holds an indirect interest of", "falls under the 50 Percent Rule"; "is blocked" when it rests on a calculated share; "ultimate beneficial owner" unless the node is a natural person and the calculation supports it; "controls" when only ownership is known |
| "OFAC records that A is owned or controlled by B." (a `CONTROLS` link from the SDN List, M2.6b) | "B owns 50 percent or more of A", or any share, when the list gives none |
| "Has significant influence or control over a trust (or firm) whose trustees (or members) hold more than 25 and at most 50 percent of the shares, as declared to Companies House." (a `CONTROLS` link of type `trust-or-firm`, M2.3b) | "owns" when the link is a trust-or-firm control, or any effective share through it |
| "Holds more than 25 percent of the shares as a trustee of a trust (register of overseas entities)." (an `OWNS` link whose `ownership_type` is `shares (as trustee)`, M2.3b) | "owns" when the holding is recorded as a trustee's and the text leaves that out |
| "Holds more than 50 and less than 75 percent of the voting rights, as declared to Companies House." (a voting `CONTROLS` link with a band, M2.3b) | "owns" when only voting rights are recorded |
| "Recorded as sanctioned on the register of overseas entities at Companies House (as declared by the overseas entity; it may be out of date)." (a beneficial owner with `is_sanctioned`, M2.3b) | "is sanctioned" unless the text names the register or list that says so |
| "Listed in UK Parliament data as a member of the House of Commons since 2019. Members of the House of Commons are politically exposed persons while in office (MLR 2017 regulation 35(14)(b)); for a domestic PEP the starting point is a lower level of risk (regulation 35(3A))." | "corrupt", "high risk", "suspicious"; "is a PEP" about a node whose `:PEP` flag does not come from its own records |
| "No sanctions or PEP flag from the lists loaded here (UK Sanctions List; OFAC Specially Designated Nationals and Blocked Persons List; EU Financial Sanctions Files (consolidated list); UK Parliament members and ministers), which means only that these lists do not name the record. Other lists, and politically exposed persons outside them, are not loaded." | "not sanctioned", "not a PEP", "no sanctions exposure", "cleared", "passed screening" |

Rules:

1. Every possible-match text contains the words "not confirmed".
2. A flag is described only on the node that carries it, with its dataset ("listed in UK Sanctions List as sanctioned").
3. Effective shares are ranges, and each bound is said the way the statute says it: an open bound as "more than" or "less than", a closed one as "at least" or "at most" (`(25, 50]` is "more than 25 and at most 50 percent", `[75, 100]` is "at least 75 percent"; 5.1, 5.3). An effective share is always called a NeonRadar calculation.
4. "Beneficial owner" means a natural person (PHASE-1.md 7.4); an organisation at the top of a chain is "the top recorded owner".
5. The absence of a flag says only that the loaded sources do not list the record, as the real data notice says ("A missing sanctions or PEP flag means only that the lists loaded here do not name the record.", 5.3). Text about a node without a flag uses the absence template with the titles of the list datasets actually loaded (`GET /meta`, record count above 0), never a phrase from the "Never write" cell of that row. With no list dataset loaded it says: "No sanctions or PEP list is loaded here, so this view cannot show such flags."
6. Never present an effective share as the result of a sanctions ownership test. OFAC passes blocked status down a chain entity by entity (FAQ 401: X holds 50 percent of A and A holds 50 percent of B, so B is blocked; multiplying the shares would give 25 percent and miss B), and a band on the PSC register may already be an indirect holding (Companies Act 2006 Schedule 1A, paragraph 9), so multiplying it again can understate it. Effective shares show how published bands combine; Phase 3's `sanctions_exposure` applies each jurisdiction's own test (PHASE-1.md 7.2).
7. M2.1c turns every quoted phrase of the "Never write" column that the table does not qualify ("about a node whose ...", "unless ...", "when ...") into a forbidden pattern (5.3, "Wording-lint patterns"); in this table those are "identified as", "is really", "proven to be the same", "is the same person as", "matches the sanctioned person", "sanctions hit", "is the same company as", "holds an indirect interest of", "falls under the 50 Percent Rule", "corrupt", "high risk", "suspicious", "not sanctioned", "not a PEP", "no sanctions exposure", "cleared" and "passed screening". A qualified phrase depends on context, so the template tests of M2.12 and the reviewers check it. No "Write" text contains an unqualified "Never write" phrase (`contracts/tests/test_wording.py`), and `scripts/check_wording.py` scans `graph/src/**/wording.py`.

**Templates** (verbatim; `<...>` is filled in from the data; a probability is written with three decimals, rounded down, so it never shows 1.000).

The merged entity: "Merged from `<n>` source records: `<sources>`." where `<sources>` lists each member's dataset title, anchor first and then in anchor order (7.1.6), followed for Companies House by the record type (`company`, `PSC`, `officer`).

`explain_member` (one per `ResolutionMember`):

| Method | Rule | Text |
|---|---|---|
| `identity` | | "Built from one source record (`<dataset title>`)." |
| `anchor` | | "Anchor record: the entity takes its id and caption from this `<dataset title>` record." |
| `deterministic` | D1 | "Joined by the same UK company number." |
| `deterministic` | D2 | "Joined by the same LEI." |
| `deterministic` | D3 | "Joined by the same Companies House person number (its first 8 characters) and similar names." |
| `deterministic` | D4 | "Joined by the same UN reference number." |
| `deterministic` | D5 | "Joined because `<dataset title>` gives both records the same identifier." |
| `deterministic` | D6 | "Joined by the same address." |
| `probabilistic` | | "Joined by probabilistic matching (match probability `<p>`). `<evidence>`" |
| `human` | D7 | "Joined by a reviewer's decision." (The graph keeps no reviewer handle or decision date: `decided_at` is the time of the resolution run, M2.11.) |

`explain_possible_match` (one per `PossibleMatch`): "Possible match, not confirmed." followed by one sentence per reason, in the order of the link's `reasons`, and for a probabilistic match the evidence.

| Reason | Sentence |
|---|---|
| `below_merge_threshold` | "Probabilistic matching gave `<p>`, below the threshold for merging." |
| `name_only` | "Only the names agree, and NeonRadar never merges on a name alone (policy P3)." |
| `listed_unlisted` | "Kept separate because one record is on a sanctions or PEP list and the other is not (policy P1)." |
| `listed_differently` | "Kept separate because the records are listed for different reasons, for example one on a sanctions list and one as a politically exposed person (policy P1)." |
| `leaked_cross_source` | "Kept separate because one record comes from the ICIJ Offshore Leaks Database (policy P2)." |
| `listed_needs_birth_date` | "Entries from two different lists are merged only when their birth years agree or they share an identifier (policy P6)." |
| `cluster_cap` | "Kept separate because merging would have joined more than 30 records into one entity (rule X7)." |
| `identifier_name_mismatch` | "Both records give the same `<identifier>`, but the names differ, so they were not merged." (`<identifier>` from the link's `rule`: D1 "UK company number", D2 "LEI", D3 "Companies House person number", D4 "UN reference number", D5 "source identifier") |
| `source_hint:<hint>` | "The ICIJ Offshore Leaks Database marks these records as `<hint words>`." |

ICIJ hint words (`HINT_WORDS`): `same_name_as` "having the same name"; `same_id_as` "having the same identifier"; `same_as` "the same"; `same_company_as` "the same company"; `same_intermediary_as` "the same intermediary"; `probably_same_officer_as` "probably the same officer"; `similar` and `similar_company_as` "similar"; any other value "related (`<the value with underscores as spaces>`)".

PEP texts from UK Parliament data (M2.6e loads current members, and former members only within `access.pep_former_months`):

| Case | Text |
|---|---|
| current member | "Listed in UK Parliament data as a member of the `<House of Commons or House of Lords>` since `<year>`. Members of the `<House>` are politically exposed persons while in office (MLR 2017 regulation 35(14)(b)); for a domestic PEP the starting point is a lower level of risk (regulation 35(3A))." |
| current minister | "Listed in UK Parliament data as holding the government post `<post>` since `<year>`. Ministers are politically exposed persons while in office (MLR 2017 regulation 35(14)(a)); for a domestic PEP the starting point is a lower level of risk (regulation 35(3A))." |
| former member or minister, within the window | "Listed in UK Parliament data as a member of the `<House>` (or as holding `<post>`) until `<date>`. MLR 2017 regulation 35(9) asks firms to keep applying PEP measures for at least 12 months after a person leaves office; for a domestic PEP the starting point is a lower level of risk (regulation 35(3A))." |

**Evidence.** `<evidence>` is "Agreeing: `<words>`. Differing: `<words>`. Not on both records: `<words>`.", each part only when it has words, the words in the order of the table below. `evidence_lines(features)` gives one line per comparison: "Agrees: `<words>`", "Differs: `<words>`" or "Not on both records: `<words>`". `LEVEL_WORDS` maps each comparison and Splink level label (`models.py`, M2.10b) to what it counts as and its words; postcodes read the same for both models:

| Comparison | Level label | Counts as | Words |
|---|---|---|---|
| `name` | name key equal | agrees | same name |
| `name` | forename and surname similar | agrees | forename and surname spelled similarly |
| `name` | surname equal, same initial | agrees | same surname and initial |
| `name` | two name symbols shared | agrees | two name parts that match across scripts or spellings |
| `name` | name key similar | agrees | names spelled similarly |
| `name` | surname equal | agrees | same surname |
| `name` | two skeletons shared | agrees | two name parts with the same consonants |
| `name` | All other comparisons | differs | names |
| `name` | name_key is NULL | missing | name |
| `birth` | same birth date | agrees | same birth date |
| `birth` | same birth month | agrees | same birth month |
| `birth` | same birth year | agrees | same birth year |
| `birth` | birth years one apart | differs | birth years (one year apart) |
| `birth` | All other comparisons | differs | birth dates |
| `birth` | birth_years is NULL | missing | birth date |
| `countries` | Array intersection size >= 1 | agrees | a shared nationality or country |
| `countries` | All other comparisons | differs | nationalities and countries |
| `countries` | countries is NULL | missing | nationality or country |
| `postcode` | Exact match on full postcode | agrees | same postcode |
| `postcode` | Exact match on sector | agrees | same postcode sector |
| `postcode` | Exact match on district | agrees | same postcode district |
| `postcode` | Exact match on area | agrees | same postcode area |
| `postcode` | All other comparisons | differs | postcodes |
| `postcode` | postcode is NULL | missing | postcode |
| `linked_orgs` | Array intersection size >= 2 | agrees | two or more companies in common |
| `linked_orgs` | Array intersection size >= 1 | agrees | a company in common |
| `linked_orgs` | All other comparisons | differs | linked companies (none in common) |
| `linked_orgs` | linked_orgs is NULL | missing | linked companies |
| `identifiers` | Array intersection size >= 1 | agrees | a shared passport or identity number |
| `identifiers` | All other comparisons | differs | passport and identity numbers |
| `identifiers` | identifiers is NULL | missing | passport or identity number |
| `org_name` | name key equal | agrees | same name |
| `org_name` | a name or alias shared | agrees | a name, alias or former name in common |
| `org_name` | same name under the Companies House rules | agrees | the same name under the Companies House same-name rules |
| `org_name` | name key very similar | agrees | names spelled very similarly |
| `org_name` | name key similar | agrees | names spelled similarly |
| `org_name` | two words shared | agrees | two words of the name in common |
| `org_name` | All other comparisons | differs | names |
| `org_name` | name_key is NULL | missing | name |
| `jurisdiction` | Exact match on jurisdiction | agrees | same jurisdiction |
| `jurisdiction` | All other comparisons | differs | jurisdictions |
| `jurisdiction` | jurisdiction is NULL | missing | jurisdiction |
| `registration_numbers` | Array intersection size >= 1 | agrees | a shared registration number |
| `registration_numbers` | All other comparisons | differs | registration numbers |
| `registration_numbers` | registration_numbers is NULL | missing | registration number |
| `incorporation` | same year | agrees | same incorporation year |
| `incorporation` | one year apart | differs | incorporation years (one year apart) |
| `incorporation` | All other comparisons | differs | incorporation years |
| `incorporation` | incorporation_year is NULL | missing | incorporation year |
| `legal_forms` | Array intersection size >= 1 | agrees | same legal form |
| `legal_forms` | All other comparisons | differs | legal forms |
| `legal_forms` | legal_forms is NULL | missing | legal form |

### 7.3 Labelling protocol and the published precision figure

The plan asks for "a published precision figure". This protocol makes it honest and repeatable. The labellers follow `docs/er/labelling-guide.md` (M2.14); the numbers below are fixed by this spec.

**What is measured.** The precision of the merges the resolver made in the evaluation run: for a record `r` that joined a cluster with anchor `a`, does `r` refer to the same real person or organisation as `a`? The evaluation run is `neonradar er run --profile uk-sample --no-decisions` with the frozen configuration, so review decisions cannot remove wrong merges before they are measured; the report gives the number of decisions on file. Address merges (D6) are not part of the figure.

| Sample | Frame (from the evaluation run's `canonical.csv` and `candidates.jsonl`) | Size | Purpose |
|---|---|---|---|
| S1, headline | every non-anchor record of class `person`, `org` or `legal_entity` whose `path_methods` include `probabilistic` (its path to the anchor contains a probabilistic link) | 400, simple random sample; the whole frame when it holds 400 or fewer | the published precision figure |
| S2 | every non-anchor record of those classes whose `path_methods` are exactly `deterministic` | 50; the whole frame when smaller | deterministic precision, reported per rule (D3 on its own line) |
| not sampled | every non-anchor record whose path includes `human` | none | counted in the report |
| S3 | every possible match | 50 | how often a possible match is a true match (informs reviewers; not a precision of merges) |
| S4, overlap | 40 pairs from the S1 sample and 10 from the S3 sample | labelled a second time by a different labeller | agreement between labellers |

Rules:

1. **The run and the seed.** The sample is drawn from the evaluation run after the freeze, with `neonradar er sample --profile uk-sample --run <id> --seed <n> --labellers <every handle in people.er_labellers>`, where `n` is the seed the tech lead wrote into ADR-0014 at the freeze; `er sample` refuses a real-profile run that applied decisions, and any other seed once ADR-0014 is accepted. No real pair is labelled before this sample: the thresholds come from the synthetic benchmark only (7.1.7). The sample file holds record ids only.
2. **What labellers see.** Labellers do not see the match probability, the rule, the method, the stratum or anyone else's label, and all strata are mixed in one seeded random order. The tool shows each record's dataset, names in their original scripts, birth dates, countries, postcodes and towns, linked companies, identifiers and source link, side by side.
3. **Unsure.** Each label is `same`, `different` or `unsure`, with an optional note. `unsure` is excluded from the precision and reported as a count and a share; above 15 percent the report says so in its first line. The report also gives `k / (n + u)` with its Wilson interval: the precision if every unsure pair were wrong.
4. **Agreement and adjudication.** S4 pairs carry two labels from different labellers. Before adjudication, the report gives the percentage agreement, Cohen's kappa, the share of `same`, and positive and negative agreement (Cicchetti and Feinstein 1990, over the pairs both labellers marked `same` or `different`). Kappa alone can mislead: when almost every label is `same`, 48 agreeing pairs out of 50 can give a kappa below zero (`test_stats.py`), and the two specific agreements show why. Disagreements are adjudicated by a person who did not set the thresholds (the project lead by default; never the tech lead or the graph mentor), who sees the two cards but neither label; the adjudicated label counts.
5. **Precision.** `k / n`, where `n` is the number of labels other than `unsure` and `k` the number of `same` labels, with a Wilson score interval at 95 percent (section 3.4 gives the formula and a worked example). The report gives `k`, `n`, `u`, the point estimate, the interval, the frame size and the date, for S1 and for S2 (overall and per rule). Why 400: a Wilson interval of plus or minus 5 points needs 381 labels in the worst case (precision near 0.5) and 245 at 0.8 (`er-splink.md` 9). If fewer than 250 S1 labels other than `unsure` exist when labelling closes on Tuesday 3 November, the report publishes what there is and its first line says that the interval is wider than planned. When a frame is no larger than its sample, the whole frame is labelled and the report says so: the figure is then a census of this run's merges, and the interval describes the process rather than the sampling.
6. **No changes after labelling starts.** Nothing in the evaluation is changed after labelling starts. If the tech lead and the graph mentor change thresholds or rules after seeing S1 to S4 (for example because precision is far below the plan's 80 percent), the old figure is still published, the new configuration gets a new evaluation run and a fresh sample, and both appear in the report.
7. **The README sentence** (verbatim, with the values filled in): "On `<date>`, human labellers judged `<k>` of `<n>` sampled probabilistic merges on a slice of the UK register correct (precision `<p>`, Wilson 95% interval `<lo>` to `<hi>`; `<u>` unsure, excluded). Sanctions, PEP and ICIJ records are never merged by probability, so this does not measure screening accuracy."
8. **Sources and licences.** Every published report (the precision report, `docs/data/er/benchmark.md` and the load benchmarks of M2.13) ends with a sources-and-licences footer: the attribution of every real dataset in the run (`contracts/datasets.yaml`), and, when ICIJ records are in it, the ODbL notice: "Content in this report was obtained from the ICIJ Offshore Leaks Database, which is available under the Open Database License 1.0 (https://opendatacommons.org/licenses/odbl/1-0/). Always cite the International Consortium of Investigative Journalists when using this data."

**Report** (`docs/data/er/precision-<date>.md`, written by `neonradar er precision`, counts and rates only):

```text
# Entity resolution precision, uk-sample, <date>

Probabilistic merges (headline): <k> of <n> correct, precision <p> (Wilson 95% interval <lo> to <hi>);
<u> pairs (<u%>) marked unsure and excluded. If every unsure pair were wrong: <k> of <n+u>,
precision <p'> (Wilson 95% interval <lo'> to <hi'>).
Deterministic merges: <k2> of <n2> correct (Wilson 95% interval <lo2> to <hi2>); by rule: D1 <k> of <n>,
D2 <k> of <n>, D3 <k> of <n>, D4 <k> of <n>, D5 <k> of <n>.
Joined through a reviewer's decision: <h> records (not sampled).
Possible matches that labellers judged to be the same entity: <k3> of <n3>.
Agreement between labellers on <m> overlapping pairs (40 from S1, 10 from S3), before adjudication:
<a%>; Cohen's kappa <kappa>; share of same <s%>; positive agreement <pa>; negative agreement <na>.
<census note for any frame labelled whole>

Evaluation run <run id> (no decisions applied; <d> decisions on file); resolver <version>;
config <sha256>; thresholds <values>; frame sizes <N1>, <N2>, <N3>; sample seed <seed> (ADR-0014);
labelled by <count> people between <dates>; adjudicated by the <role>.

On <date>, human labellers judged <k> of <n> sampled probabilistic merges on a slice of the UK register
correct (precision <p>, Wilson 95% interval <lo> to <hi>; <u> unsure, excluded). Sanctions, PEP and
ICIJ records are never merged by probability, so this does not measure screening accuracy.

Limitations: one slice of the UK register; ...; precision of merges says nothing about recall.
How to reproduce: <commands>

Sources and licences: <one attribution line per real dataset in the run>; <the ICIJ notice of rule 8>
```

### 7.4 Real-data handling

These rules apply to every machine and every person, not only to the agent. The data steward owns them (ADR-0018, `docs/data/real-data-handling.md`).

1. **Before the first real run.** Robotat is the controller for the real data its staff and interns load in this project. Before any real profile runs, the data steward files in `docs/data/dpia/` a legitimate interests assessment, a data protection impact assessment, the condition from Schedule 1 to the Data Protection Act 2018 that the processing relies on with its appropriate policy document where that condition needs one (a designation may itself be criminal offence data under UK GDPR Article 10: the ICO says such data "is likely to include personal data about penalties, conditions or restrictions placed on an individual"), and the approach to Article 14 (the Article 14(5)(e) exception with the Article 14(7) safeguards, including published privacy information; the ICO expects a DPIA when that exception is used), and then sets `access.data_protection_filed: true`. Every real-profile command refuses to run while it is false (M2.2). This is not legal advice; the data steward decides.
2. **Where.** Real data lives only under `data/cache/real/` and `data/cache/spikes/`, and in the real Neo4j instance (`neo4j-real`, Docker volume `neo4j-real-data`), on a machine listed in `docs/data/real-data-machines.md` (full-disk encryption, screen lock). DuckDB spill files of a real run go to `data/cache/real/duckdb-tmp/<run_id>/` and are deleted when the run ends. Never in Codespaces, CI, cloud sessions, shared drives, chat tools or email. The default Neo4j instance (`neo4j`) only ever holds synthetic data: the loader refuses a real record there (M2.11).
3. **How long.** `neonradar data purge --expired` deletes downloads, records, resolution runs, decisions and logs older than `access.real_data_days`, labels older than `access.label_days`, and spike output older than `access.spike_cache_days`; `neonradar doctor` warns when anything is older, or when DuckDB spill files were left behind. `neonradar data purge --all-real --graph --yes` deletes all real data on the machine, including the real instance's volume (a volume-level wipe: Neo4j's transaction logs and store files go with it).
4. **What leaves the machine.** Only counts-only reports (`data/cache/reports/`, `docs/data/er/`, `docs/data/benchmarks/`, the spike and loader reports). No names, birth dates, addresses, identifiers or source record ids of real people in any pull request, issue, commit, screenshot, recording, slide or chat message. Real company numbers and LEIs of companies may appear in documentation where this spec puts them (the `uk-tiny` seeds), never with a pattern or a flag next to them.
5. **Logs and errors.** Library code logs record ids and values only at DEBUG, and real-data commands never run at DEBUG in a session with the agent. On a real profile every CLI command runs inside `neonradar_cli.redact.guard()`: an exception prints only its class, the step, the dataset, the rule id and a run-local reference, and the full traceback goes to `data/cache/real/logs/<command>-<UTC timestamp>.log`, which is purged with the rest. No message contains a record id of a person.
6. **The agent.** Permission rules deny it any read of `data/cache/real/**` and `data/cache/spikes/**`; `guard_real_data.py` blocks shell commands that would print from there, Read, Grep and Glob calls on those paths, WebFetch, curl or wget of list, register and leak data files, `docker compose config` without `--quiet` or `--services` and `docker inspect` (they print passwords from `.env`), any shell command that addresses the real instance except `uv run neonradar`, `make` and `docker compose up`, `start`, `stop`, `down` or `ps`, and the human-only commands (`er label`, `er review`, `api serve --real`). The Neo4j MCP server and `cypher-shell` reach the default instance only (G9).
7. **The local API and UI.** Bound to `127.0.0.1` (Phase 1) and connected to the default instance, so they show synthetic data. `neonradar api serve --real` (port 8001) serves the real instance to a human at a terminal on an approved machine (M2.12). Screenshots of real data are not taken; the demo uses synthetic data only.
8. **Labels and decisions** are personal data too: they stay in `data/cache/real/`, are purged as rule 3 says (labels after `access.label_days`, which the data steward may extend so that the published figure can be audited; they hold record ids and labels only), and are never copied into the repository.
9. **Questions from the public.** Anyone who believes NeonRadar shows wrong data about them is pointed to the source register for corrections (the standing disclaimer promises this), and the project corrects its own code if the error is NeonRadar's. Anyone else who runs NeonRadar on real data is the controller for their own copy (PHASE-1.md ADR-0006).
10. **If real data reaches the repository** (or any other place in rule 4): stop, tell the data steward and the tech lead at once, do not try to fix history yourself; an admin removes it, and the data steward records what happened in `docs/data/incidents.md` without repeating the data.

This is a practical project rule set, not legal advice. The research notes `bulk-sources-loading.md` (section 10) and `sanctions-peps.md` (section 8) quote what Companies House and the ICO say about reusing register and list data and about the duties of whoever loads it; section 3.3 summarises the licences.

### 7.5 Bibliography additions

Add these entries to `docs/sources/bibliography.yaml` (M2.14), in the Phase 1 format (PHASE-1.md 7.3). A milestone that cites one of these keys before M2.14 (for example M2.10b's ADR-0014) adds that entry in its own pull request, so the citation check passes. All were checked on 18 October 2026: the research notes in `docs/research/2026-10-18/` hold the exact quotations; the four journal articles (Fellegi and Sunter, Wilson, Cohen, Cicchetti and Feinstein) were checked against their Crossref records; and the Companies Act paragraph was read on legislation.gov.uk, where it was marked up to date to 29 August 2026.

| Key | Title | Publisher | Year | URL |
|---|---|---|---|---|
| `fellegi_sunter_1969` | A Theory for Record Linkage (Journal of the American Statistical Association 64(328), 1183 to 1210) | Ivan P. Fellegi and Alan B. Sunter | 1969 | https://doi.org/10.1080/01621459.1969.10501049 |
| `splink_docs` | Splink documentation (version 5) and its `llms.txt` | Ministry of Justice analytical services | living | https://moj-analytical-services.github.io/splink/ ; https://moj-analytical-services.github.io/splink/llms.txt |
| `splink_5_release_2026` | Splink 5.0.0 released | Ministry of Justice analytical services | 2026 | https://moj-analytical-services.github.io/splink/blog/2026/09/28/splink-500-released.html |
| `wilson_1927` | Probable Inference, the Law of Succession, and Statistical Inference (Journal of the American Statistical Association 22(158), 209 to 212) | Edwin B. Wilson | 1927 | https://doi.org/10.1080/01621459.1927.10502953 |
| `nist_handbook_7_2_4_1` | e-Handbook of Statistical Methods, 7.2.4.1 Confidence intervals | NIST/SEMATECH | living | https://www.itl.nist.gov/div898/handbook/prc/section2/prc241.htm |
| `cohen_1960` | A Coefficient of Agreement for Nominal Scales (Educational and Psychological Measurement 20(1), 37 to 46) | Jacob Cohen | 1960 | https://doi.org/10.1177/001316446002000104 |
| `cicchetti_feinstein_1990` | High agreement but low kappa: II. Resolving the paradoxes (Journal of Clinical Epidemiology 43(6), 551 to 558) | Domenic V. Cicchetti and Alvan R. Feinstein | 1990 | https://doi.org/10.1016/0895-4356(90)90159-M |
| `psc_regulations_2016_sch2` | The Register of People with Significant Control Regulations 2016 (SI 2016/339), Schedule 2 | legislation.gov.uk | 2016 | https://www.legislation.gov.uk/uksi/2016/339/schedule/2 |
| `llp_psc_regulations_2016_sch2` | The Limited Liability Partnerships (Register of People with Significant Control) Regulations 2016 (SI 2016/340), Schedule 2 | legislation.gov.uk | 2016 | https://www.legislation.gov.uk/uksi/2016/340/schedule/2 |
| `scottish_partnerships_psc_2017_sch3` | The Scottish Partnerships (Register of People with Significant Control) Regulations 2017 (SI 2017/694), Schedule 3 | legislation.gov.uk | 2017 | https://www.legislation.gov.uk/uksi/2017/694/schedule/3 |
| `ca_2006_sch1a_para9` | Companies Act 2006, Schedule 1A, paragraph 9 (interests held indirectly) | legislation.gov.uk | 2006 | https://www.legislation.gov.uk/ukpga/2006/46/schedule/1A/paragraph/9 |
| `ecta_2022_sch2` | Economic Crime (Transparency and Enforcement) Act 2022, Schedule 2, paragraph 6 | legislation.gov.uk | 2022 | https://www.legislation.gov.uk/ukpga/2022/10/schedule/2/paragraph/6 |
| `ch_psc_descriptions` | `psc_descriptions.yml` (natures of control enumerations) | Companies House | 2025 | https://github.com/companieshouse/api-enumerations/blob/master/psc_descriptions.yml |
| `ch_free_company_data` | Free Company Data Product | Companies House | living | https://download.companieshouse.gov.uk/en_output.html |
| `ch_psc_snapshot` | People with significant control (PSC) snapshot | Companies House | living | https://download.companieshouse.gov.uk/en_pscdata.html |
| `ch_personal_information_charter` | Personal information charter | Companies House | 2026 | https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter |
| `gleif_golden_copy_manual` | GLEIF Golden Copy and Delta Files user manual v2.2 | GLEIF | 2022 | https://www.gleif.org/lei-data/gleif-golden-copy/2022-02-23_gleif-golden-copy-and-delta-files_v2.2-final.pdf |
| `gleif_level2` | Level 2 data: who owns whom | GLEIF | living | https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom |
| `fcdo_uk_sanctions_list` | The UK Sanctions List | FCDO (GOV.UK) | living | https://www.gov.uk/government/publications/the-uk-sanctions-list |
| `fcdo_single_list_2026` | Moving to a single list for UK sanctions designations: 28 January 2026 | GOV.UK | 2025 | https://www.gov.uk/guidance/moving-to-a-single-list-for-uk-sanctions-designations-28-january-2026 |
| `fcdo_format_guide` | Format guide for the UK Sanctions List | FCDO (GOV.UK) | 2025 | https://www.gov.uk/guidance/format-guide-for-the-uk-sanctions-list |
| `ofsi_general_guidance_2026` | UK financial sanctions general guidance | OFSI | 2026 | https://www.gov.uk/government/publications/financial-sanctions-general-guidance/uk-financial-sanctions-general-guidance |
| `ofac_sls` | Sanctions List Service | OFAC | living | https://ofac.treasury.gov/sanctions-list-service |
| `ofac_advanced_xml_faq` | Frequently asked questions on the advanced sanctions list standard | OFAC | living | https://ofac.treasury.gov/sdn-list-data-formats-data-schemas/frequently-asked-questions-on-advanced-sanctions-list-standard |
| `ofac_50_percent_faqs` | FAQs 398 to 402 on the 50 Percent Rule | OFAC | 2020 | https://ofac.treasury.gov/faqs/topic/1521 |
| `ofac_sham_transactions_2026` | Guidance on Sham Transactions and Sanctions Evasion | OFAC | 2026 | https://ofac.treasury.gov/media/935441/download?inline |
| `ofac_faq_5` | FAQ 5: what to do when a party may match the SDN List | OFAC | 2026 | https://ofac.treasury.gov/faqs/5 |
| `ofac_search_faqs` | FAQs 246 to 250 on the Sanctions List Search tool | OFAC | living | https://ofac.treasury.gov/faqs/249 |
| `unsc_consolidated_list` | United Nations Security Council Consolidated List | United Nations | living | https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list |
| `un_terms_of_use` | Terms of Use | United Nations | living | https://www.un.org/en/about-us/terms-of-use |
| `eu_fsf` | Financial Sanctions Files (RSS of the consolidated list files) | European Commission | living | https://webgate.ec.europa.eu/fsd/fsf/public/rss |
| `eu_reuse_decision_2011` | Commission Decision 2011/833/EU on the reuse of Commission documents | European Union | 2011 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32011D0833 |
| `eu_best_practices_2024` | EU Best Practices for the effective implementation of restrictive measures (11623/24) | Council of the European Union | 2024 | https://data.consilium.europa.eu/doc/document/ST-11623-2024-INIT/en/pdf |
| `mlr_2017_reg_35` | The Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, regulation 35 | legislation.gov.uk | 2017 | https://www.legislation.gov.uk/uksi/2017/692/regulation/35 |
| `fca_fg25_3` | FG25/3 The treatment of politically exposed persons for anti-money laundering purposes | FCA | 2025 | https://www.fca.org.uk/publication/finalised-guidance/fg25-3.pdf |
| `parliament_members_api` | Members API | UK Parliament | living | https://members-api.parliament.uk/ |
| `open_parliament_licence_3` | Open Parliament Licence v3.0 | UK Parliament | living | https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/ |
| `uk_gdpr_art14` | UK GDPR Article 14 (latest revised text) | legislation.gov.uk | 2026 | https://www.legislation.gov.uk/eur/2016/679/article/14 |
| `ico_right_to_be_informed_exceptions` | The right to be informed: are there any exceptions? | ICO | 2025 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/are-there-any-exceptions/ |
| `ico_criminal_offence_data` | What is criminal offence data? | ICO | 2025 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/criminal-offence-data/what-is-criminal-offence-data/ |
| `ico_legitimate_interests` | Legitimate interests | ICO | 2026 | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/legitimate-interests/ |

"Year" is the publication or last-update year the notes record; "living" marks pages that change without versions. Where an entry stands for a group of FAQs, the note gives each number.

### 7.6 Glossary additions

Add to `docs/glossary.md` (M2.14), with a citation where the term is an AML or legal term:

| Term | Meaning in NeonRadar |
|---|---|
| Entity resolution | Deciding which records from one or more sources refer to the same real person or organisation, and merging them into one node |
| Source record | One record as a source published it (a Companies House officer appointment, a sanctions list entry); `:SourceRecord` in the graph |
| Canonical entity | The node built from one or more source records; `nr-` id when it was merged |
| Possible match | Two nodes that may be the same entity but were not merged (policy, threshold or a source's own hint); `POSSIBLY_SAME_AS`, always "not confirmed"; deterministic and source-hint possible matches have no probability |
| Deterministic rule | A merge rule based on a shared official identifier (D1 to D6) |
| Fellegi-Sunter model | The probabilistic record linkage model behind Splink: each comparison level has an m probability (agreement among true matches) and a u probability (agreement among non-matches), combined into a match weight |
| Blocking | Restricting comparisons to pairs that share some key, so that not every pair of records is compared |
| Match weight, match probability | The log-odds score of a pair and its conversion to a probability |
| Precision, recall | The share of merges that are correct; the share of true matches that were merged |
| Evaluation run | The resolution run whose merges the published precision figure measures: the frozen configuration, with no review decisions applied (7.3) |
| Wilson interval | A confidence interval for a proportion that behaves well for small samples and proportions near 0 or 1 |
| Cohen's kappa, positive and negative agreement | Measures of agreement between two labellers; kappa corrects for chance agreement, and the two specific agreements show agreement on `same` and on `different` separately, because kappa can be low when almost every label is the same |
| PSC | Person with significant control, recorded by Companies House; a corporate PSC is a relevant legal entity |
| Effective share | The product of the published bands along one ownership chain, as a range: a NeonRadar calculation that shows how bands combine. Sanctions ownership tests do not multiply shares down a chain (OFAC passes blocked status entity by entity), and a band on the PSC register may already be an indirect holding |
| Consolidation (GLEIF) | Accounting consolidation of a child by a parent, as reported to GLEIF; not an ownership percentage |
| Flag topic | A topic that is not purely descriptive, such as `sanction`, `role.pep` or `crime` (7.1.1); flags on nodes come only from these |
| Listed record | A record with at least one flag topic: on a sanctions, PEP or similar list (7.1.1) |

### 7.7 Architecture decision records for Phase 2

Numbers 0013 to 0019 are assigned here. The agent drafts each as `proposed`; the deciders edit and accept it.

| Number | Title | Written in | Status at Gate 2 (set by the deciders) | Deciders |
|---|---|---|---|---|
| 0013 | Data profiles and production sources | M2.2 | accepted | data steward, tech lead |
| 0014 | Entity resolution approach and thresholds | M2.10b | accepted at the freeze (29 Oct), with the D3 form and the evaluation sample seed | tech lead, graph mentor |
| 0015 | Merge policy for listed and leaked records | M2.10a | accepted | data steward, project lead, tech lead |
| 0016 | Canonical ids and source records | M2.11 | accepted | tech lead |
| 0017 | Official sources for sanctions and PEP data | M2.6a | accepted | data steward, project lead |
| 0018 | Real-data handling | M2.0 | accepted | data steward |
| 0019 | Ownership and effective share calculation | M2.12 | accepted | tech lead, graph mentor |

With Phase 1's twelve, the project then has nineteen ADRs, which covers the plan's definition of done for the schema (0004) and the resolution approach (0014); the detection design comes in Phase 3.

### 7.8 Profiles reference

The three profiles (verbatim; `ingest/profiles/*.yaml`, M2.2). Each loader milestone validates its own block with a pydantic model and fails on unknown keys. Real profiles run only where 1.2 and 7.4 allow and the real-data gate passes (M2.2); a source enabled here still runs only if `project.yaml` allows its dataset (`access.sanctions_lists`, `access.pep_sources`, `access.opensanctions`). Downloads are shared between real profiles and kept per dataset and product (4.5).

```yaml
# ingest/profiles/demo.yaml
profile: demo
description: Synthetic data only. The Phase 1 demo-mini fixture (and, from M2.9, the entity resolution benchmark).
real_data: false
sources:
  nr_synthetic:
    enabled: true
    fixtures: [data/fixtures/demo-mini]   # M2.9 adds data/fixtures/er-bench
resolution:
  enabled: true
  config: resolve/config/er.yaml
```

```yaml
# ingest/profiles/uk-tiny.yaml
profile: uk-tiny
description: >-
  A small real slice for developers: the companies of a large group quoted on the London
  Stock Exchange, found through Companies House PSC records, their officers and PSCs, their
  GLEIF records and the sanctions lists. A test input for the loaders; implies nothing about
  these companies.
real_data: true
sources:
  gb_companies_house:
    enabled: true
    companies:
      seeds: ["04190816", "01800000"]     # the Phase 1 spike pair: the group's holding company and its main subsidiary
      postcode_districts: []
      max_per_district: 0
      max_companies: 400
      sample_seed: 20261026
    psc:
      enabled: true
      parent_depth: 4                     # follow corporate PSCs up to 4 levels, even outside the slice
      child_depth: 3                      # add companies whose corporate PSC is in the set, 3 levels down
      include_ceased: false
    officers:
      enabled: true
      request_budget: 1500
      cache_days: 30
      appointments: false
      active_only: false
  gleif_lei:
    enabled: true
    scope: slice
  icij_offshore_leaks:
    enabled: false
  gb_fcdo_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }
  us_ofac_sdn: { enabled: true, keep_reasons: false, keep_positions: false }
  un_sc_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }   # runs only if access.sanctions_lists allows it
  eu_fsf: { enabled: true, keep_reasons: false, keep_positions: false }
  gb_parliament_members:                  # runs only if access.pep_sources allows it; former members kept for access.pep_former_months
    enabled: true
    houses: [commons, lords]
    request_budget: 3000
    cache_days: 30
  opensanctions_default: { enabled: false }
resolution:
  enabled: true
  config: resolve/config/er.yaml
```

```yaml
# ingest/profiles/uk-sample.yaml
profile: uk-sample
description: >-
  A neutral slice of the UK register for local investigation and the published entity
  resolution figure: companies registered in eight city-centre postcode districts across
  the UK, sampled evenly, with their ownership chains, officers, GLEIF records, the ICIJ
  records in the same postcode districts and their direct neighbours, and the sanctions
  lists. The districts were chosen for spread, not for anything about the companies in them.
real_data: true
sources:
  gb_companies_house:
    enabled: true
    companies:
      seeds: []
      postcode_districts: [EC2A, M1, B3, LS1, EH3, CF10, BS1, NE1]
      max_per_district: 5000              # deterministic sample per district (sha256 of seed and number)
      max_companies: 50000                # leaves room for the parent companies the PSC expansion adds
      sample_seed: 20261026
    psc:
      enabled: true
      parent_depth: 4
      child_depth: 0
      include_ceased: false
    officers:
      enabled: true
      request_budget: 20000               # about three hours at 2 requests per second
      cache_days: 30
      appointments: false
      active_only: false
  gleif_lei:
    enabled: true
    scope: slice
  icij_offshore_leaks:
    enabled: true
    mode: district-linked                 # addresses in the districts above, their entities and officers, one hop more (M2.5)
    max_nodes: 50000
    sample_seed: 20261026
  gb_fcdo_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }
  us_ofac_sdn: { enabled: true, keep_reasons: false, keep_positions: false }
  un_sc_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }   # runs only if access.sanctions_lists allows it
  eu_fsf: { enabled: true, keep_reasons: false, keep_positions: false }
  gb_parliament_members:                  # runs only if access.pep_sources allows it; former members kept for access.pep_former_months
    enabled: true
    houses: [commons, lords]
    request_budget: 3000
    cache_days: 30
  opensanctions_default: { enabled: false }   # a data-steward-approved pull request enables it, only with a licence (M2.7)
resolution:
  enabled: true
  config: resolve/config/er.yaml
```

`gb-linked` (every ICIJ node with a GB country code and its direct neighbours, up to 150,000 nodes) remains available to `uk-sample` only through a pull request that the data steward approves and that records the reason in ADR-0013 (M2.5).

**Expected size and resources** (estimates from the research notes; M2.13 replaces them with measurements in `docs/data/benchmarks/`):

| Item | `demo` | `uk-tiny` | `uk-sample` |
|---|---|---|---|
| Downloads (shared between real profiles; M2.2 keeps two versions per dataset and product) | none | about 3.5 GB: Companies House companies 0.47 GB and PSC 2.2 GB, GLEIF 0.53 GB, the four lists about 0.2 GB | the same plus ICIJ (626 MB uncompressed; zip size unverified) |
| Companies | about 30 synthetic | at most 400 | at most 50,000 (40,000 sampled, the rest parents) |
| Officer requests and time | none | at most 1,500, about 13 minutes | at most 20,000, about 3 hours at the rate limit |
| Sanctions list records (UK, US, EU) | synthetic only | about 16,000 persons and 13,000 organisations | the same |
| ICIJ nodes | none | none | at most 50,000 |
| Resolvable records | about 1,500 (with the benchmark, from M2.9) | about 35,000 | about 230,000 |
| Graph after resolution | a few hundred nodes | about 45,000 nodes, 40,000 relationships | about 300,000 nodes, 550,000 relationships (inside the scale target, leaving room for Phase 3) |
| Disk at peak (downloads, work files, records, DuckDB spill, the real Neo4j volume) | under 1 GB | about 10 GB | about 25 GB |
| Memory | the Phase 1 small profile | DuckDB 4 GB plus the real Neo4j instance | a 16 GB laptop: DuckDB 4 GB, the real Neo4j instance with 2 GB heap and 2 GB page cache (stop the default instance with `make down` during the load if Docker has only 8 GB) |
| Build time without officers (estimate) | under 2 minutes | about 15 minutes | about 30 minutes, then the officer fetch |

The counts come from the research notes (register and list sizes on 18 October 2026, the PSC sample shares) and the Phase 1 spikes; the times from the parse rates measured in `bulk-sources-loading.md` 9.5 and the Splink run in `er-splink.md` 7, on a 2-core container. M2.13 replaces every row with measurements.

---

## 8. Gate 2: graph loads end to end (Wednesday 4 November)

The tech lead decides Gate 2 with the release manager and the data steward. `make gate-2` (M2.16) gathers the evidence; checks it cannot verify are marked MANUAL and a named human confirms them in the Phase 2 report.

| ID | Check | Evidence | Blocks the gate |
|---|---|---|---|
| G2-01 | Contracts 1.1.0 merged and tagged | `make contracts-check` passes on `main`; `contracts/CHANGELOG.md` has 1.1.0 entries for C1, C2 and C3; tag `contracts-v1.1.0` exists | yes |
| G2-02 | CI green on `main` | latest `ci` workflow run on `main` succeeded, including the Cypher lint step (M2.0) | yes |
| G2-03 | Synthetic profile loads end to end | latest `e2e` workflow run on `main` ran `make load PROFILE=demo` and `neonradar graph verify` (I1 to I14) successfully | yes |
| G2-04 | A real profile loads end to end from at least three source families | `docs/data/benchmarks/<date>-uk-tiny.md` or `-uk-sample.md` (counts only) shows Companies House, GLEIF and at least one sanctions list built, resolved, loaded into the `neo4j-real` instance and verified (I1 to I14) | yes (MANUAL) |
| G2-05 | Benchmark quality at the frozen thresholds | `neonradar er bench --size small` in CI: pairwise precision at least 0.97 and recall at least 0.80 for each class; candidate recall of policy-blocked true pairs at least 0.80 | yes |
| G2-06 | Precision published | `docs/data/er/precision-<date>.md` passes with `n` of at least 250 S1 labels other than `unsure` (400 planned), or fewer with the first-line statement of 7.3; labelled by at least four labellers; with `k`, `n`, the Wilson interval, the unsure count with the bound if every unsure pair were wrong, and the agreement figures (7.3) | yes |
| G2-07 | Merge policy enforced | `resolve/tests/test_cluster.py` (X1 to X8 and P1 to P6 on the oracle cases, including possible matches that a cannot-link rule suppresses and the second review of human decisions) and `resolve/tests/test_policy.py` (which topics flag a record) pass in CI, and so does invariant I11 (no flag without an own source topic) | yes |
| G2-08 | Ownership, paths and resolution endpoints | `api/tests/test_ownership.py`, `test_paths.py`, `test_resolution.py` pass; effective shares and their open or closed bounds exact on the fixture | no |
| G2-09 | Scale measured | the `uk-sample` benchmark report gives the time of every step, node and relationship counts, query latencies and the hardware; targets: graph load under 10 minutes, ownership and paths queries p95 under 2 seconds | no |
| G2-10 | Real-data controls in place | data steward confirms: the data protection documents (legitimate interests assessment, DPIA, Schedule 1 condition with its appropriate policy document, Article 14 approach) are filed in `docs/data/dpia/`, and `access.data_protection_filed` was set to `true` only after that; approved machines listed; `access.real_data_days` and `access.label_days` set; purge tested on one machine, including the volume wipe of `neo4j-real`; real data loaded only into `neo4j-real`; the fixture check passes; every report under `docs/data/` is counts only | yes (MANUAL) |
| G2-11 | Licence fields approved | link to the data steward's approving review of the new entries in `contracts/datasets.yaml` (M2.1a) and of `DATA_SOURCES.md` | yes (MANUAL) |
| G2-12 | ADRs as in 7.7 | status lines of ADRs 0013 to 0019 match the table; each accepted ADR was accepted by its deciders | no |
| G2-13 | Assignment 3 done | each intern in `people.interns` (all of whom are in `people.er_labellers`, 1.3) labelled at least 20 pairs (the graph mentor reports counts per handle); the presentations follow at the teach-back on Thursday 5 November | no (MANUAL) |
| G2-14 | Phase 3 unblocked | `graph/tests/test_overlay_resolution.py` passes: overlay records that reference record ids load against a resolved graph | no |
| G2-15 | Phase 2 report written | `docs/build/reports/phase-2.md` with metrics, deviations, risks and the inputs Phase 6 needs for the published benchmark | no |

**Outcomes.**

- **Pass**: every check passes.
- **Pass with exceptions**: every blocking check passes and some others fail; each failed check gets an owner and a date in the Phase 2 report. A precision figure below the plan's 80 percent is published as measured and is an exception with an improvement plan, not a reason to hide it.
- **Fail**: a blocking check fails. Fix and re-run. If the gate slips past Wednesday, the project lead applies the next cut on the plan's kill list the same day.

The ER configuration (`resolve/config/er.yaml`, the rules in 7.1 and the models' settings) freezes at Gate 2 as the plan asks ("Freeze at the end of sprint 1"). Later changes need the tech lead, a new benchmark run and, if they affect real-data merges, a new precision sample.

---

## 9. Risks for Phase 2

| # | Risk | Likelihood | Impact | Response in this spec | Owner |
|---|---|---|---|---|---|
| R1 | Real personal data reaches the repository, a pull request or the agent's context | medium | high | G2, G9; deny rules and `guard_real_data.py` for Read, Grep, Glob, shell commands and WebFetch (M2.0); the separate `neo4j-real` database; counts-only commands and reports; error redaction on real profiles (M2.2); DuckDB spill files under `real/`; the fixture check; the `data-guardian` subagent; 7.4 | data steward |
| R2 | A wrong merge puts a sanctions or PEP flag on a real person | low | high | G8; P1 (flag topics must match) and P6; an exact name key for identifier links that cross P1 or P2; cannot-link rules checked before any possible match; X5 and X6; invariant I11; oracle tests (M2.10a); human review of possible matches | tech lead |
| R3 | Measured precision is far below 80 percent | medium | medium | Deterministic rules first; P3 (no merge on names alone); benchmark calibration; honest publication with an improvement plan (8) | graph mentor |
| R4 | The officer fetch is too slow or fails (rate limit, key, outages) | medium | medium | Request budget, cache and resume (M2.3c); `uk-tiny` fallback; start on Friday 30 October | ingest mentor |
| R5 | Bulk file formats differ from the research (headers, kinds, columns) | medium | medium | M2.0 reconciliation; parsers keyed on header names, not positions; unknown values counted, never guessed; stop and ask (2.5) | ingest mentor |
| R6 | An official list's reuse terms are not acceptable (the UN list already needs written permission) | medium | medium | Per-list decision by the data steward (`access.sanctions_lists`); the UN list is off by default, and the UK and EU lists carry its listings (the UK list with their UN reference numbers; the EU field was empty in every record read, so UK and EU entries for one listing meet only through the probabilistic model under P6); the loaders run independently | data steward |
| R7 | Laptops lack the disk or memory for `uk-sample` | medium | medium | Profile sizes in 7.8; DuckDB memory limit; `uk-tiny` and `demo` | docs squad |
| R8 | Labelling is too slow or inconsistent | medium | high | Labelling guide, the S4 overlap with adjudication, the `unsure` option, booked sessions, Assignment 3 | graph mentor |
| R9 | Contract changes land late and block Phases 3 to 5 | medium | high | Issue texts ready in 5.0; M2.1 on days 1 to 3; tag on Wednesday 28 October | tech lead |
| R10 | AI-written code uses the Splink 4 API or invents DuckDB and rigour functions | high | medium | Verified signatures in 3.2 and 7.1.5; traps in `CLAUDE.md`; tests on the benchmark | graph mentor |
| R11 | Arabic and Cyrillic names are under-matched | high | medium | The keys recipe (M2.8) with variant tables; script variants in the benchmark; documented limitation; sources' own Latin aliases | graph mentor |
| R12 | Hub nodes (mass registration addresses, very common names) blow up blocking or traversals | medium | medium | X7 caps; no city-only addresses; blocking analysis in M2.10b; bounded queries with timeouts (M2.12) | graph mentor |
| R13 | Shared screenshots or exports trigger ODbL or other licence duties | low | medium | No real-data screenshots (7.4); notices in `DATA_SOURCES.md` | data steward |
| R14 | Phase 2 and Phase 3 sessions wipe each other's synthetic data in the default local Neo4j, or a real load lands in the wrong database | medium | low | Real profiles load only into the separate `neo4j-real` instance, and the loader refuses real records on the default one (M2.11); rule in 1.8; Testcontainers for tests | tech lead |
| R15 | A source is down when a profile is built | medium | low | Cached versions are reused; `data fetch` keeps the last good version; retries | ingest mentor |
| R16 | GLEIF's announced service interruptions (19 October to 4 November) stop the Golden Copy download | medium | medium | Fetch the Golden Copy as soon as M2.4 merges and keep it (M2.2 keeps two versions); tests use fixtures; `gleif_lei` may be built from an older publish, which the summary states | ingest mentor |
| R17 | A free-text identifier on a sanctions list yields a wrong UK company number or LEI, so D1 or D2 links the entry to the wrong company | low | high | Numbers only next to a company-number label and a UK register, with negative tests (M2.6a); prefixes checked against `CH_PREFIXES`; LEI check digits; the name check on D1 and D2, which needs an exact name key when the link would merge a listed record with an unlisted one; X3 and X4 | ingest mentor |
| R18 | The EU public download token or the UN redirect stops working | low | low | The token is configurable (`NR_EU_FSF_TOKEN`); the UN list is optional; the last good download is kept | ingest mentor |
| R19 | A reader takes a range such as `(50, 75)` to include 75 percent, a control link from OFAC for a share, or an effective share for the result of a sanctions ownership test | low | medium | Open and closed bounds in the API (5.3) and in words (7.2); OFAC links load as `CONTROLS`, never as `OWNS` (M2.6b); effective shares described as a NeonRadar calculation (3.4, 7.2); oracle tests (M2.12) | copilot mentor |
| R20 | A single reviewer's `same` answer puts a sanctions or leak flag on a real person | low | high | A `same` decision that crosses P1 or P2 applies only after a second reviewer agrees or a senior reviewer made it; `er review` shows the differing evidence above the question and needs a note for `same`, and pairs with a hard conflict never reach review (M2.10c, 7.1.3); X8 applies a `different` at once | tech lead |
| R21 | Robotat processes real personal data before its own controller duties are met | medium | high | The 1.1 checkbox; every real profile refuses to run until `access.data_protection_filed` is true (M2.2); G2-10 | data steward |
| R22 | The published precision is flattered: unsure labels left out, earlier review decisions removing false merges, labellers or adjudicator influenced | medium | medium | The evaluation run ignores review decisions; the bound with every unsure pair counted wrong; no real labels before the freeze; the sample seed written into ADR-0014 at the freeze; blind adjudication by someone who did not set the thresholds (7.3) | graph mentor |

---

## 10. Appendix

### 10.1 Document history

| Version | Date | Change |
|---|---|---|
| 1.0 | 18 October 2026 | First version: Phase 2 build spec, verified baseline, contract changes 1.1.0, milestones, entity resolution reference, Gate 2 |

Record later changes here, with a matching note in `docs/build/PROGRESS.md`.

### 10.2 Build terms added in Phase 2

| Term | Meaning here |
|---|---|
| Profile | A named configuration of sources, slice and steps in `ingest/profiles/` (7.8) |
| Real-data run | A command on a real profile, run by a human on an approved machine, whose counts-only output goes into the pull request |
| Approved machine | A machine listed in `docs/data/real-data-machines.md` (7.4) whose `.env` sets `NR_REAL_DATA_MACHINE=approved` |
| Real database | The separate Neo4j instance `neo4j-real` that holds real data; the agent never reaches it (4.1, G9) |
| Resolution run | One execution of `neonradar er run`, with its own id and output folder (7.1.8) |
| Freeze (ER) | The moment, on Thursday 29 October, after which thresholds and rules do not change before the evaluation sample is labelled |
| Evaluation run | The frozen `uk-sample` resolution run made without review decisions (`er run --no-decisions`), from which S1 to S4 are drawn (7.3) |
| Evaluation sample | The labelled pairs S1 to S4 behind the published figure (7.3) |
| Senior reviewer | A person in `people.er_senior_reviewers`, who may confirm alone a `same` decision that crosses P1 or P2 (7.1) |
| Counts-only | Output that holds counts, timings, rates, versions and settings, and never a value from a record |

Phase 1's terms (PHASE-1.md 10.2) still apply.

### 10.3 Files delivered with this spec

| File | Goes to |
|---|---|
| `PHASE-2.md` (this document) | `docs/build/PHASE-2.md` |
| `research/README.md` and the research notes | `docs/research/2026-10-18/` |
| `README.md` (the kit's steps) | stays in the kit |
