# NeonRadar build spec, Phase 3: Transactions and detection

| | |
|---|---|
| File | `docs/build/PHASE-3.md` |
| Code book | `docs/build/PHASE-3-CODE.md`: every verbatim file of this phase, with its SHA-256 (2.10) |
| Version | 1.0, 19 October 2026 |
| Phase window | Monday 26 October to Friday 13 November 2026 (Gate 3, Friday 13 November: detections green); two Phase 3 items are checked at Gate 2 on Wednesday 4 November |
| Built by | Claude Code (VS Code extension or CLI), one milestone per pull request |
| Reviewed and merged by | Humans only |
| Facts verified on | 18 October 2026 (section 3, with the full research notes in `docs/research/2026-10-18-detection/`); the code was tested again on 19 October after three independent reviews |
| Starts from | Gate 1 passed (tag `contracts-v1.0.0`), Phase 2 under way (`docs/build/PHASE-2.md`) |
| Runs alongside | `PHASE-2.md` (Ownership graph) until 4 November; `PHASE-4.md` (API and copilot) and `PHASE-5.md` (Explorer UI) from 2 November |

This document is both a plan and a set of executable instructions, in the format of `docs/build/PHASE-1.md` and `docs/build/PHASE-2.md`. Humans read it to know what will be built, what they must decide and what they must do themselves (above all approving the typology tests, freezing the detectors before the published evaluation, and running that evaluation). Claude Code reads it to build the transaction layer and the detectors milestone by milestone.

Phase 3 is where NeonRadar starts to produce alerts, and where synthetic payments first sit next to real companies. A pattern found in synthetic payments next to a real company says nothing about that company, so a new guardrail (G12, section 2.1) withholds every such alert, and every alert that would name a real person; a second one (G11) keeps the published detection figures honest. Read section 2.1 before anything else.

This phase carries more verbatim code than the earlier ones: 141 files and about 18,000 lines, tested before this spec was written. So that this document stays readable, the code lives in a companion file, the code book `PHASE-3-CODE.md`, with one section per milestone, and the milestones here say which files to take from it. A script (`scripts/spec_extract.py`, M3.0) copies the files exactly and checks them afterwards (2.10).

---

## 0. How to use this document

### 0.1 Who reads what

| Reader | Reads | Why |
|---|---|---|
| Operator (tech lead or project lead) | Sections 0, 1 and 8 in full, then the "Review focus" box of each milestone | Prepares access and decisions, opens the contract-change issue, runs the real-data commands on an approved machine, runs the holdout evaluation, checks the Gate 2 items and Gate 3 |
| Claude Code (the build agent) | Sections 0, 2, 3, 4 and 5 once per session, then only the active milestone in section 6 and the files it names in the code book, plus section 7 when a milestone points there | Executes milestones within the rules |
| Reviewers (mentors and interns) | The pull request, the milestone's "Review focus" box, the parts of section 7 the milestone points to, and the output of `spec_extract check` | Decide whether the work is correct and understood; verbatim files are checked by the script, so reviews concentrate on the adapted code and the behaviour |
| Typology researchers | Section 7.3 (one subsection per typology), the test files of each detector in the code book, and every pull request labelled `typology` | Approve each typology's definition, parameters and test cases before the detection freeze; only they set `status: approved` (G4) |
| Data steward | Sections 1.1, 1.2, 2.1 (G1, G9, G12), 5.2 (L18), 7.7 and every pull request labelled `real-data-run` | Decides which real profiles may receive a synthetic overlay; checks that real-profile output is counts only |
| Interns | `docs/team/assignment-4.md` (M3.10) and the typology they own from Assignment 2 | Write one test case by hand (Assignment 4) and present it at the teach-back on Thursday 12 November |

### 0.2 How the build runs

```text
operator: /milestone M3.x  (or the explicit prompt in 1.7)
   |
   v
Claude Code: read spec -> plan -> branch -> copy the milestone's verbatim files from the code book
             (spec_extract extract) -> adapt the reference files -> build the rest -> run the
             acceptance commands (synthetic data) -> spec_extract check -> independent review
             subagent -> update PROGRESS.md -> open PR -> STOP
   |
   v
humans: CI + review checklist + named reviewer -> request changes or approve -> MERGE
   |
   +--> milestones marked "Real-data run": the operator runs the listed command on an approved
   |    machine and pastes the counts-only output into the pull request
   +--> the holdout evaluation (M3.12) is run by a human after the detection freeze (M3.11)
   |
   v
next milestone (or several in parallel, see 1.8)
```

Claude Code never merges, never reads real records, never runs the evaluation on holdout seeds and never changes a frozen detector parameter. Every acceptance command in this document runs on synthetic data unless it is marked as a real-data run, and every real-data command prints counts, timings and rates only.

### 0.3 The six phases

| Phase | Name | Dates (2026) | Ends with | Main output |
|---|---|---|---|---|
| 1 | Foundation and contracts | Fri 16 Oct to Fri 23 Oct | Gate 1, Fri 23 Oct: schema frozen | Repository, tooling, CI, agent kit, four frozen contracts, data source spikes, a thin end-to-end walking skeleton |
| 2 | Ownership graph | Mon 26 Oct to Wed 4 Nov | Gate 2, Wed 4 Nov: graph loads end to end | Production loaders, entity resolution with a published precision figure, ownership, paths and resolution endpoints |
| **3** | **Transactions and detection (this document)** | **Mon 26 Oct to Fri 13 Nov** | **Gate 3, Fri 13 Nov: detections green** | **Synthetic transaction overlay attached to entities, typology detections with fixtures, evaluation harness with precision and recall** |
| 4 | API and investigation copilot | Mon 2 Nov to Fri 13 Nov | Part of Gate 3 | Complete API v1, a template-first local copilot that answers the 10 benchmark questions |
| 5 | Explorer UI | Mon 2 Nov to Tue 17 Nov | Gate 4, Tue 17 Nov: feature freeze | Vue explorer: search, network canvas, alert queue, explain panel |
| 6 | Hardening, documentation and launch | Mon 16 Nov to Fri 20 Nov | Gate 5, Fri 20 Nov: public launch | Documentation site, benchmark, demo video, launch post, every definition-of-done box ticked |

Phase 3 builds against the same contracts as Phase 2, in parallel with it. Its overlay attaches synthetic accounts to entities by their record ids; Phase 2's resolution-aware loader (M2.11, rule L13) maps those ids to canonical entities, so the two phases share no data files. Phases 4 and 5 read the alerts Phase 3 writes (C4, unchanged) from Neo4j.

### 0.4 Phase 3 scope

In scope:

- Phase 3 handover: reconcile this spec with what Phases 1 and 2 actually built, and update the agent kit (the code book script, rules for detection and the generator, guardrails G11 and G12, labels, the human-only holdout command).
- One contract change, C2 graph schema 1.2.0, additive: overlay loads into either Neo4j instance (rule L18), the bridge invariants I15 to I17, detection-run fields (L19) and `:Sanction.provisions`. C1, C3 and C4 stay as Phase 2 leaves them.
- The detection core: a `Source` interface of bounded candidate steps with two implementations (Cypher on Neo4j, and an in-memory oracle over the same C2 graph), time-respecting path expansion, the real-data detection rule R-REAL, C4 alert building, entity-facing wording, the runner, and `circular_flow` 0.2.0 in place of the Phase 1 detector.
- Generator v1: a synthetic register (the world) and an overlay engine that attaches accounts and ordinary background activity to any base, synthetic or real, and plants scenarios and benign look-alikes for fourteen typologies among synthetic entities only, with label files v2.
- Overlay loading, the synthetic profiles (`synth-eval`, `synth-demo`, `synth-scale`) and overlay and detection blocks for the Phase 2 profiles; `make load` gains the overlay and detection steps.
- Fourteen detectors, each with a verbatim test file: the ten `core` typologies of PHASE-1.md 7.2 and the four `extended` ones. `trade_based_ml` stays explainer only.
- The evaluation harness: matching alerts to planted scenarios, per-typology recall and precision with intervals, a CI gate with exact counts, a detection freeze, and the published figures from holdout seeds in the README.
- A demo world with `make demo`, and a scale world at the plan's target (500,000 nodes and 2 million relationships) with measured generation, load and detection times.
- Typology explainers updated with the detection definitions, ADRs 0020 to 0024, bibliography and glossary additions, the Assignment 4 kit, the Gate 3 check and the Phase 3 report.

Out of scope (later phases or not at all): the copilot and new API endpoints (Phase 4; the Phase 1 alert endpoints keep working); UI changes (Phase 5); the documentation site and the published scale benchmark page (Phase 6, which reuses M3.9's measurements); trade-based laundering detection (it needs invoices and shipments, which C2 does not model); external labelled datasets (AMLworld, SAML-D, AMLGentex) beyond a note on how a user could import them later; machine-learned detectors; any alert about a real person; publishing any alert about a real entity.

### 0.5 Decisions this spec makes

These change the project plan or a Phase 1 or Phase 2 assumption. Humans should know them before the build starts. Evidence is in section 3 and `docs/research/2026-10-18-detection/`.

| # | Plan, Phase 1 or Phase 2 said | Phase 3 does | Why |
|---|---|---|---|
| 1 | "a laundering chain can run through a genuine shell company structure from Companies House" (plan) | Planted scenarios never involve a real entity. Real organisations receive only plain background activity; every scenario and look-alike creates its own synthetic companies, people and accounts, which live in the same graph next to the real register | PHASE-1.md G1 and ADR-0005 already decided this; a scenario role on a real company would label it suspicious (`typology-detection-definitions.md` 16) |
| 2 | "Where a pattern touches a real company, the output says 'structural pattern present'" (plan) | Rule R-REAL (guardrail G12): a finding that rests on payments and involves a real entity is withheld and only counted, because every payment in NeonRadar is synthetic and says nothing about that entity; a finding that names a real person, as its subject or anywhere in its evidence, is withheld too (anything legal that is not an organisation counts as a person). Registry findings about real organisations whose evidence names only organisations and addresses remain, worded as structural patterns | An alert built from invented payments next to a real company would be invented information about it; profiling and criminal-offence data rules point the same way, and data protection by design asks for such outputs to be off by default and minimised; NeonRadar takes the stricter course of not producing them at all (ADR-0021; `typology-detection-definitions.md` 16.3 to 16.5, answers 22 and 24) |
| 3 | PHASE-1.md M1.9b case F expected an alert on a real holder with `structural_pattern` | Case F now expects no alert and one `activity_on_real` in the run summary (M3.2) | Decision 2 |
| 4 | "10 typology detections" (plan) and "Eight or more typologies detected, each with a test" (Gate 3) | Fourteen detectors: the ten `core` and the four `extended` typologies of PHASE-1.md 7.2, each with a verbatim test file; Gate 3 needs eight | All fourteen were built and evaluated before this spec was written; the extended ones land last (M3.5f) and never block the gate |
| 5 | Detection as one Cypher query per typology (PHASE-1.md M1.9b) | Hybrid: bounded, parameterised Cypher candidate steps (one query file per step), the typology logic in Python, and an in-memory oracle with the same interface; payment paths are expanded one hop per query with time and amount limits | Cypher 5 quantified path patterns cannot compare a hop with the previous one, so time order cannot prune the expansion (`detection-cypher-gds.md` 1.2); the oracle makes every detector testable without a database and the parity tests prove the two agree |
| 6 | Phase 1's `circular_flow` query `(a)-[:PAID]->{2,6}(a)` | Replaced by hop expansion from anchored starts, version 0.2.0, with the same-holder variant the typology file names and a three-payment minimum for a cycle back to the same account | The unanchored pattern enumerates paths before filtering (`detection-cypher-gds.md` 2.6); on the development worlds a two-payment minimum added 130 alerts and no true one: 50 on look-alikes, 50 on other typologies' scenarios and 30 on background activity (7.6.5) |
| 7 | Generator v0 (M1.8e): one scenario, labels v1 | Generator v1: a world (synthetic register) and an overlay engine for any base; named random streams, so the same seed and base give the same bytes and names never change a structural draw; scenarios and look-alikes for fourteen typologies; labels v2 | `synthetic-transactions.md` 0 and 4.2; no external generator attaches to existing entities |
| 8 | Labels "live in separate label files (Phase 3)" (C1 R9) | Label files v2: the Phase 1 files with new columns, plus `participants.csv`, `scenario_params.jsonl` and `manifest.json` (7.2.8) | Matching needs each scenario's participants, roles and core members; no external dataset labels roles (`synthetic-transactions.md` 4.1) |
| 9 | "One script, one table, run in CI" (plan) | Recall per planted scenario and precision per alert, per typology, with matching rules by kind of typology; a CI gate with exact counts on one development seed; a detection freeze on Monday 9 November, holdout seeds drawn after it by the tech lead, and the published table from ten holdout seeds with the wider of two 95 percent intervals (7.6) | `evaluation-alerting.md` 0, answers 1 to 6: honest figures need parameters frozen before the test data exists |
| 10 | Contracts change in Phase 3 (Phase 2 4.1 note) | Only C2 changes, to 1.2.0 (5.2). C1, C3 and C4 stay at the versions Phase 2 leaves | Labels stay outside records; overlay metadata lives in `overlay.json`; alerts are built for C4 1.0.0 (metric values are numbers, strings or booleans), and M3.2 and every detector milestone validate them against the C4 model |
| 11 | C2 L17: the real-data instance refuses synthetic records | L18 adds one exception: an overlay load (every record id starts `syn-ov-`, the bridge checks pass) may load onto a real base in `neo4j-real`, for the real profiles the data steward lists in `access.real_overlay_profiles` | The plan's Gate 2 item "Synthetic transactions generated and attached to real entities" needs the overlay next to the real base |
| 12 | Every real organisation could get an account | Real profiles give activity to a share of their eligible organisations (`overlay.background.share`, 0.05 for `uk-sample`), and never to a person | Phase 2 left `uk-sample` at about 300,000 nodes and 550,000 relationships so that Phase 3 fits inside the scale target (PHASE-2.md 7.8); invented payments next to an identifiable person would be invented financial data about them |
| 13 | GDS "gives us community detection" (plan) | GDS weakly connected components for the `fan_in_collection` ring only, called through the driver with `stream` and concurrency 4, the projection dropped in a `finally` block; no `graphdatascience` client, no `write` mode | `detection-cypher-gds.md` 4: the client caps `pyarrow` below 26, which conflicts with the Phase 2 pin; `write` would add properties C2 does not define |
| 14 | PHASE-1.md 7.2 definitions | Seven entries corrected from primary sources (3.5): the structuring band follows the threshold's own wording (a USD deposit of exactly 10,000 is below the US threshold), the US, UK and EU sanctions tests are three different calculations, PEP family and associate exposure is one hop and ends with the office, cash peers are the same sector in the same area, and more; and registry relationships count only while they still hold | `typology-detection-definitions.md` 17 |
| 15 | Verbatim code inline in the spec (PHASE-2.md) | The code book `PHASE-3-CODE.md` holds every verbatim file with its SHA-256; `scripts/spec_extract.py` copies them and checks the copies in every pull request | About 18,000 lines of tested code; a copy made by a script cannot drift by a character |
| 16 | Plan learning track: "The human writes or approves the test" | The typology researchers approve each detector's verbatim tests in the seed pull request, before any detector exists (1.4); Assignment 4: each intern writes one more test case by hand for the typology they own and presents it on Thursday 12 November | Keeps detection logic from being written before its fixture, and gives every intern a test they wrote themselves |

### 0.6 What Phase 3 needs from Phases 1 and 2

This spec was written on 18 October, before Gate 1. M3.0 reconciles it with what was actually built. It expects:

- From Phase 1: tag `contracts-v1.0.0`; the detection runner, `neonradar detect run` and `detect list`, the `circular_flow` detector with its fixture and integration test (M1.9b); `TypologyFile` and `load_catalog()` in `detect/src/neonradar_detect/catalog.py` and `render_headline` in `wording.py` (M1.7c); `compute_alert_id` in `neonradar_contracts.alert`; the wording lint over `contracts/wording/forbidden-terms.txt`; the fifteen typology files in `detect/typologies/` (M1.10b); generator v0 with its name modules and denylist (M1.8e); the graph mapping and loader (M1.7b, M1.9a); `make demo-mini` and `make e2e`.
- From Phase 2, by milestone: M2.0 (the real-data guard hook, the Cypher linter, the `neo4j-real` instance) before M3.0; M2.1a (C1 1.1.0: the exclusive share-bound flags and the `list` record kind, which the generator and the test kit write) and M2.2 (profiles, data layout, the project model, the real-data gate) before M3.3; M2.1c and the tag `contracts-v1.1.0` before M3.1, so that 1.2.0 is tagged on top of 1.1.0; M2.11 (the resolution-aware loader with L13 and L17, and `graph verify`) before M3.4; M2.13 (`make load`) before M3.7.

Phase 2 and Phase 3 run in the same weeks, so M3.0 (Monday 26 October) can record only what Phase 1 and the Phase 2 milestones merged by then have built. Where that code differs from what this document assumes (a different function name, a model field, a CLI option, the type of a field of the C4 `Alert` model), M3.0 records it in `docs/build/phase-3-reconciliation.md`, and each later milestone checks again the seams it adapts and appends what it found (2.2 step 2). The measured fact wins for mechanical details. The places where verbatim Phase 3 code meets earlier code are few and listed in 2.10 as the seams. Anything that changes behaviour, a contract or a guardrail goes to the tech lead (2.5).

---

## 1. Operator setup (humans, before the first prompt)

Phase 1's section 1 still applies (accounts, tools, Claude Code settings), and so do Phase 2's additions (real-data machines, the separate real-data instance, the data protection documents). This section lists only what Phase 3 adds.

### 1.1 Accounts, tools and access

Tick each box before the Phase 3 kickoff prompt.

- [ ] **Gate 1 passed and Phase 2's M2.0 merged.** The tag `contracts-v1.0.0` exists, and the Phase 2 agent kit (the `guard_real_data.py` hook, the Cypher linter, the `neo4j-real` service) is on `main`. M3.0 builds on both.
- [ ] **Typology researchers available.** The people in `people.typology_researchers` review the test files of the fourteen detectors in the code book (twelve files; `test_detector_extended_registry.py` holds three typologies) during the seed pull request (1.4), before any detector exists, and the parameters in section 7.3 before the detection freeze on Monday 9 November. Book about three hours each for the first and two for the second.
- [ ] **Docker on every machine that runs integration tests.** Phase 3 adds two kinds: every detector test run a second time on Neo4j (`NR_DETECT_SOURCE=neo4j`, M3.2) and the world parity test. Each starts one Testcontainers database with APOC and GDS (about 2 GB of memory while it runs).
- [ ] **Memory for the scale world.** Generating `synth-scale` (M3.9) needs about 3 GB of free memory outside Docker for a few minutes (2.1 GB was measured), and loading it needs the standard memory profile (Neo4j heap 2 GB, page cache 2 GB). Laptops with 8 GB use `synth-demo` instead.
- [ ] **Real overlays.** The data steward reads 7.7 and decides which real profiles may receive a synthetic overlay (`access.real_overlay_profiles`, default `[uk-tiny]`). Phase 2's conditions still hold for every real-data command: `access.data_protection_filed: true`, an approved machine, the profile in `access.real_data_profiles`.
- [ ] **Holdout seeds.** The tech lead plans to draw ten seeds on Monday 9 November, after the freeze ADR is accepted, with the command in M3.11, and never earlier. Nobody, human or agent, generates or looks at a holdout world before that.
- [ ] **Required checks.** After M3.6 merges, the tech lead adds the new `eval` job to the required checks with the Phase 1 protection script (M1.6; it needs admin rights).
- [ ] **Assignment 4 slots.** Each intern knows which typology they own (the one they checked in Assignment 2) and has a slot at the teach-back on Thursday 12 November.

### 1.2 Decisions to record before the build

| Decision | Owner | Options | Where it goes |
|---|---|---|---|
| Typology tests | Typology researchers, with the detect mentor | Approve the test files of the fourteen detectors in the code book as written (default), or ask for changes in the seed pull request. A change after the seed pull request goes through a typology researcher, never through a detector pull request (2.10) | Review of the seed pull request (1.4) |
| Typology parameters | Typology researchers | The defaults in 7.3 (default), or other values inside each parameter's bounds, until the freeze. Each value is marked in 7.3 as sourced or as a modelling choice | A pull request labelled `typology` that changes the typology file, the detector's default and their code book blocks together (2.10) |
| R-REAL scope (G12) | Data steward and project lead | As written (default): withhold findings that rest on payments and involve a real entity, and findings that name a real person as their subject or in their evidence; keep registry findings about real organisations whose evidence names only organisations and addresses, as structural patterns. Stricter: also withhold those, so real profiles produce counts only. (Showing findings about people with the people replaced by their role is a possible later design; Phase 3 does not build it) | `access.real_registry_alerts` (`true` by default; `false` is the stricter option) and ADR-0021 |
| Real profiles with an overlay | Data steward | `[]`; `[uk-tiny]` (default); `[uk-tiny, uk-sample]` | `access.real_overlay_profiles` |
| Share of real organisations with activity | Data steward and tech lead | `uk-tiny` 1.0 and `uk-sample` 0.05 (defaults, 7.11); a lower share keeps `uk-sample` further inside the scale target | `overlay.background.share` in the profile |
| Detection freeze | Freeze deciders (typology researchers, detect mentor, tech lead) | Monday 9 November (default). A later freeze leaves less time for the holdout run before Gate 3 | ADR-0022 (M3.11) |
| Holdout seeds | Tech lead | Ten seeds drawn with the M3.11 command after the freeze ADR is accepted | ADR-0022 and `eval/seeds.yaml` |
| Matching rules and planted mix | Detect mentor and typology researchers | As in 7.6 (default): intersection over union of at least 0.5 for payment typologies, the rules per kind, 10 illicit scenarios and 10 look-alikes per typology and seed | ADR-0022 |
| Published wording | Technical writer and typology researchers | The fixed text of 7.6.4 (default) | `README.md` and `docs/data/detection/` (M3.12) |
| GDS licence position | Tech lead and project lead | Accept GDS Community Edition (GPLv3 in Neo4j's repository) as a plugin of the Neo4j image users run themselves, called over Bolt and never shipped by NeonRadar (default; Phase 1 already runs it) | ADR-0024 |
| Assignment 4 pairing | Project lead and typology researchers | Each intern takes the typology they checked in Assignment 2 (default); two interns may share one | `docs/team/assignment-4.md` (M3.10) |

### 1.3 Additions to `docs/build/project.yaml`

M3.0 merges these keys into the existing mappings with the defaults shown. The operator edits the values; Claude Code stops when a milestone needs a value that is still `TODO`. Only M3.11 needs `people.freeze_deciders`.

```yaml
# Phase 3 additions to docs/build/project.yaml
people:
  freeze_deciders: ["@TODO", "@TODO", "@TODO"]   # typology researchers, detect mentor, tech lead (ADR-0022)
access:
  real_overlay_profiles: [uk-tiny]      # real profiles that may receive a synthetic overlay (C2 L18, 7.7)
  real_registry_alerts: true            # false: withhold registry findings about real organisations too (G12)
schedule:
  phase_3_start: 2026-10-26
  assignment_4_due: 2026-11-06
  detection_freeze: 2026-11-09
  holdout_run: 2026-11-10
  teach_back_detection: 2026-11-12
```

### 1.4 Seed the Phase 3 documents

From Phase 2 on, `main` changes only through reviewed pull requests, including this one.

```bash
git fetch origin && git switch -c p3/spec-seed origin/main
mkdir -p docs/research/2026-10-18-detection
# copy the kit files you received:
#   PHASE-3.md          -> docs/build/PHASE-3.md
#   PHASE-3-CODE.md     -> docs/build/PHASE-3-CODE.md
#   research/*.md       -> docs/research/2026-10-18-detection/
git add docs && git commit -m "docs(build): add phase 3 build spec, code book and research notes"
git push -u origin p3/spec-seed
gh pr create --base main --title "docs(build): add phase 3 build spec [M3.0 seed]" \
  --body "Phase 3 build spec, code book and research notes, as delivered." --label phase-3
```

Add `docs/build/PHASE-3-CODE.md` to `.github/pr-size-exclude.txt` in the same pull request. The tech lead reviews the spec. The typology researchers review, in the code book, the twelve test files of the fourteen detectors (`test_detector_<slug>.py`, with `test_detector_extended_registry.py` for three typologies; sections M3.2 and M3.5a to M3.5f) against the case tables in 7.3, and approve the pull request only when every case says what the definition means. That review is the plan's "the human writes or approves the test": it happens before any detector is written. M3.0 starts from `main` with the spec in place.

### 1.5 Claude Code settings for this build

Everything in PHASE-1.md 1.5 and PHASE-2.md 1.5 applies. Phase 3 adds:

- **Copy, never retype.** Verbatim files come out of the code book with `uv run python scripts/spec_extract.py extract --milestone M3.x` (M3.0), and `check` proves the copies before the pull request opens (2.10).
- **The contract-change session for M3.1** works as in PHASE-2.md 1.5: the tech lead approves the issue (text in 5.0), sets `NR_ALLOW_CONTRACT_CHANGE` in `.claude/settings.local.json`, starts a fresh session, and removes the setting when the pull request is open.
- **Holdout runs are human-only.** From M3.0 the guard hook blocks the agent from running `neonradar eval run --split test`, and the command itself refuses to run without a terminal (Phase 2's `tty.py`) or in CI (G11).
- **Neo4j mode for detector tests.** `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration"` reruns every detector test on a Testcontainers database. Run it before opening any pull request that touches a detector, a query file or the `Source` implementations.
- **Model.** Use your most capable model for M3.2, M3.3, M3.6 and every review.

### 1.6 The Phase 3 kickoff prompt (paste once, in a fresh session)

```text
You are the build agent for NeonRadar, Phase 3 (Transactions and detection).

The build spec is docs/build/PHASE-3.md and its code book, with every verbatim file of this
phase, is docs/build/PHASE-3-CODE.md. PHASE-1.md still defines the contracts in its section 5
and the knowledge base rules in its section 7; PHASE-2.md section 5 and PHASE-3.md section 5
list the changes since. Project facts are in docs/build/project.yaml. Verified research notes
are in docs/research/2026-10-18-detection/ (Phase 3), docs/research/2026-10-18/ (Phase 2) and
docs/research/2026-10-16/ (Phase 1).

Before doing anything else:
1. Read docs/build/PHASE-3.md sections 0, 2, 3, 4 and 5 in full, and read
   docs/build/project.yaml. Read only the milestone you are executing from section 6, and from
   the code book only that milestone's section.
2. Reply with seven short bullets: the milestone order and dependencies, the rules you must
   never break (including G11 and G12), what you may and may not do with real data, how you
   copy verbatim files and what you may change in them, when you must stop and ask, how you
   prove a milestone is done, and what you do after opening a pull request.

Then execute milestone M3.0 exactly as section 6 describes, following the milestone protocol
in section 2.2. Stop when the pull request is open and you have reported its URL and the
verification evidence. Do not start another milestone until I name it.
```

### 1.7 Milestone prompts and goal conditions

After M3.0 is merged, the `/milestone` skill reads `docs/build/PHASE-3.md` for any `M3.x` id (M3.0 extends it to read the code book section too), so the prompt is one line.

| Milestone | Prompt | Optional goal line (paste after the prompt has started) |
|---|---|---|
| M3.0 | Kickoff prompt (1.6) | `/goal M3.0 acceptance commands from PHASE-3.md were run in this session and passed, PROGRESS.md marks M3.0 pr-open with the PR URL, and the PR is open; stop after 40 turns` |
| M3.1 | `/milestone M3.1` (in a contract-change session, 1.5) | `/goal M3.1 acceptance commands passed in this session, the PR is labelled contract-change, CI is green (gh pr checks), and PROGRESS.md records the PR URL; stop after 60 turns` |
| M3.11 | `/milestone M3.11` on Friday 6 November, once M3.5a to M3.5e, M3.6 and M3.10 have merged; the freeze deciders act on its pull request on Monday 9 November | `/goal M3.11 acceptance commands passed in this session and the PR is open; stop after 30 turns` |
| M3.12 | `/milestone M3.12` once the human holdout run's two files are pushed to the branch `p3/m3-12-published-evaluation` | `/goal M3.12 acceptance commands passed in this session and the PR is open; stop after 30 turns` |
| Other milestones | `/milestone M3.5a` (and so on) | `/goal <id> acceptance commands passed in this session, spec_extract check passed for the milestone, CI on the PR is green (gh pr checks), and PROGRESS.md records the PR URL; stop after 60 turns` |

When review comments arrive: `Address the review comments on PR #<n>. Reply to each comment with what you changed, re-run the milestone's acceptance commands, push, and stop.`

### 1.8 Parallel work and the merge rhythm

```text
seed PR (humans, typology researchers approve the tests)  -> M3.0 handover and agent kit
M3.0 (after M2.0)                          -> M3.3 generator v1 (after M2.1a, M2.2)
M3.0 (after M2.1c, tag contracts-v1.1.0)   -> M3.1 C2 1.2.0 (contract-change session)
M3.1 + M3.3                                -> M3.2 detection core and circular_flow 0.2.0
M3.2                                       -> M3.5a structuring, rapid_pass_through
M3.2                                       -> M3.5b mass_registration_address, shell_chain
M3.2                                       -> M3.5c fan_in_collection, fan_out_distribution, dormant_reactivation
M3.2                                       -> M3.5d layering_chain
M3.2                                       -> M3.5e sanctions_exposure
M3.2                                       -> M3.5f formation_agent_cluster, recycled_directors,
                                              pep_exposure, cash_commingling (extended)
M3.2                                       -> M3.6 evaluation harness and the CI gate
M3.2 (after M2.11)                         -> M3.4 overlay loading and profiles (real-data run: uk-tiny overlay)
M3.4 + M3.6 (after M2.13)                  -> M3.7 make load steps (real-data run: uk-tiny with detection)
M3.7 + M3.5a..e                            -> M3.8 demo world and make demo
M3.7                                       -> M3.9 scale world and benchmark
M3.5a..e + M3.6                            -> M3.10 documentation, ADRs, Assignment 4 kit
M3.5a..e + M3.6 + M3.10 (M3.5f if merged)  -> M3.11 detection freeze (prepared Friday 6 November)
M3.11 (+ the human holdout run)            -> M3.12 published evaluation
everything                                 -> M3.13 Gate 3 check and Phase 3 report
```

The milestone headers in section 6 are the authority; this graph summarises them. M3.2 depends on M3.1 and M3.3, so everything after it does too.

Suggested calendar:

| Day | Agent work (pull requests) | Human work |
|---|---|---|
| Fri 23 Oct (after Gate 1) | none | Seed pull request (1.4), with the typology researchers' review of the test files; open the C2 contract-change issue (5.0); record the 1.2 decisions |
| Mon 26 Oct | M3.0 (after M2.0 merges) | Review M3.0 first: every later session depends on its script and rules |
| Tue 27 Oct | M3.3 (once M2.1a and M2.2 merge) | Ingest mentor and data steward review the generator (names, G1, the bridge rule) |
| Wed 28 Oct | M3.1 (once M2.1c merges and `contracts-v1.1.0` is tagged) | Tech lead approves M3.1 and tags `contracts-v1.2.0` after it merges |
| Thu 29 Oct | M3.2 | Detect mentor reviews the detection core; teach-back (Phase 2: entity resolution) |
| Fri 30 Oct | M3.5a, M3.5b, M3.6, M3.4 (once M2.11 merges) | Typology researchers review M3.5a and M3.5b; tech lead adds the `eval` job to the required checks after M3.6 merges |
| Mon 2 Nov | M3.5c, M3.5d, M3.5e, M3.7 (once M2.13 merges) | On an approved machine, after the `uk-tiny` base is loaded: the M3.4 real-data run (overlay on `uk-tiny`), then the M3.7 one (`uk-tiny` with detection) |
| Tue 3 Nov | M3.5f, M3.8, M3.10 | Gate 2 evidence for the Phase 3 items (8.1) |
| Wed 4 Nov | M3.9 | Gate 2 decision (with Phase 2) |
| Thu 5 Nov | fixes from review, M3.10 continues | Teach-back (Assignment 3 presentations, Phase 2) |
| Fri 6 Nov | M3.11 prepared (freeze file), fixes | Assignment 4 due; typology researchers finish the parameter review; the holdout rehearsal (M3.12) |
| Mon 9 Nov | M3.11 merged | Freeze deciders accept ADR-0022; the tech lead draws the holdout seeds |
| Tue 10 Nov | M3.12 prepared from the human run | The tech lead (or a named human) runs the holdout evaluation and pushes its two files |
| Wed 11 Nov | M3.12 merged, fixes | Technical writer and typology researchers review the published text |
| Thu 12 Nov | M3.13 | Teach-back on detection; Assignment 4 presentations |
| Fri 13 Nov | none | Gate 3 decision (with Phase 4) |

Merge rule (unchanged): merge in dependency order and bring a branch up to date with `git merge origin/main`, never by rebasing. The busy days are Thursday 29 October to Monday 2 November, when the detection core, the first detectors, the evaluation and the overlay loader land together; the detect and ingest mentors should keep review time free then. A detector pull request is small to review because its verbatim files are proven by `spec_extract check`: the review is the typology's behaviour, its baseline rows and the evaluation output.

Parallel sessions on one machine share the default local Neo4j, which holds synthetic data only; the milestones that load it (M3.4, M3.7, M3.8, M3.9) run one at a time per machine, and Phase 2's loads share it too (PHASE-2.md 1.8). Integration tests start their own Testcontainers database and are safe in parallel.

### 1.9 What humans do themselves

Everything in PHASE-1.md 1.9 and PHASE-2.md 1.9 still applies. Phase 3 adds:

- **Approving the tests before the detectors.** The typology researchers approve the verbatim test files in the seed pull request (1.4). After that, a test file changes only through a pull request that a typology researcher approves, never inside a detector milestone.
- **Typology status.** Only a typology researcher sets `status: approved` in `detect/typologies/<slug>.yaml` (G4); the agent's files say `draft`, and `spec_extract` keeps whatever the researchers set while the rest of the file is unchanged (2.10).
- **The detection freeze.** The freeze deciders accept ADR-0022 on Monday 9 November, after which no detector parameter, detector version, matching rule or planted mix changes without a new freeze and new holdout seeds (G11).
- **The holdout seeds and run.** The tech lead draws the seeds after the freeze (M3.11) and a named human runs the holdout evaluation (M3.12). The agent prepares the pull request from the run's output files; it never runs the holdout command.
- **Real-data runs.** A named human runs (or explicitly lets the agent run, in a session on an approved machine) the commands marked "Real-data run" in M3.4 and M3.7, and checks that the output pasted into the pull request holds counts only.
- **Assignment 4.** Each intern writes their test case by hand and presents it (M3.10 kit). The agent never writes, completes or fixes an intern's case; it may explain a failing run when asked.
- **Approvals.** ADR-0020 to ADR-0024 (deciders in 7.10), the R-REAL scope and real overlays (data steward and project lead), the published wording (technical writer and typology researchers), and the GDS licence position (tech lead and project lead).
- **Names in the demo.** Before M3.8 publishes `synth-demo`, the data steward checks its company names, and the names of its list, PEP and RCA personas, against a loaded register on an approved machine, counts only (M3.8): the demo says that nothing in it exists.

---

## 2. Operating rules for the build agent

This section is the agent's constitution for Phase 3. It repeats the earlier rules that still hold, so that a session needs only this document, and adds what alerts and the evaluation require. M3.0 updates `CLAUDE.md` to match; this section wins if they ever disagree.

### 2.1 Mission guardrails (never break these)

| ID | Rule |
|---|---|
| G1 | **No real person or company is ever labelled suspicious.** Synthetic scenarios and look-alikes run only among synthetic entities that the scenario itself created (ids starting `syn-ov-`). Real registry entities receive synthetic background activity only, never a scenario role. The generator's scenario context refuses any id it did not create, and the overlay loader checks the bridge rule (I15, I16) before writing. Any exception needs an ADR approved by the project lead and the data steward (PHASE-1.md G1). |
| G2 | **The repository holds code and synthetic fixtures only.** Generated worlds, overlays, label files, detection runs and evaluation outputs live under `data/cache/` (gitignored). The repository holds the code, the test kit, the CI baseline counts (`eval/baselines/ci.json`), the freeze file and the published, counts-only evaluation report. Never commit an artefact of a real-data run except the counts-only reports this spec names. |
| G3 | **Nothing phones home.** The generator, the detectors and the evaluation never use the network. Tests never use the network. |
| G4 | **AML facts carry citations.** Every factual AML statement in documentation cites a key from `docs/sources/bibliography.yaml` (7.8 adds the Phase 3 keys). Only a typology researcher sets a typology to `approved`. |
| G5 | **Patterns, not accusations.** Alert text describes the shape and its numbers, never the conduct a typology is named after: no headline, summary or step says "structuring", "smurfing", "layering", "laundering", "mule" or "shell", even on synthetic data, and none says an entity is sanctioned, blocked, suspicious or guilty, laundered money or committed a crime (PHASE-1.md 7.1, PHASE-2.md 7.2, 7.5.2). `wording.render` lints every text it renders, with the names of the entities masked, and stops the run on a match. |
| G6 | **Secrets stay out.** API keys and passwords live in `.env` or GitHub secrets. Never print, log, commit or request them in chat. |
| G7 | **Licences decide what a loader may do.** Phase 3 adds no data source. External labelled datasets (AMLworld, SAML-D, AMLNet) are never downloaded, vendored or used by the build (3.3). |
| G8 | **No inferred flags.** Flags (`:Sanctioned`, `:PEP`, `:RCA`) come only from a node's own source records (PHASE-2.md G8). A detector never adds a flag, a topic or a label to an entity; detections exist only as `:Alert` nodes and their `FLAGS` relationships. |
| G9 | **Real data stays local, and the agent never reads it** (PHASE-2.md G9, unchanged). A real profile's overlay, its detection run and its summaries are real-profile outputs: they live under `data/cache/real/`, the agent sees only their counts-only summaries in `data/cache/reports/<profile>/`, and an overlay or detection on a real profile prints counts only. |
| G10 | **Humans label, and labels stay honest** (PHASE-2.md G10, unchanged). Synthetic scenario labels are written by the generator, never by hand, and never enter records or the graph (C1 R9). |
| G11 | **The evaluation stays honest.** The published detection figures come from holdout seeds that the tech lead draws after the detection freeze, run by a human, with the code, parameters, detector versions, matching rules and planted mix pinned in `eval/freeze.json` (M3.11). The agent never runs an evaluation with `--split test`, never generates, reads or looks at a holdout world, its labels or its alerts (the holdout run writes under `data/cache/holdout/`, which the agent's tools cannot reach, M3.0), never tunes a parameter, a rule or a scenario after seeing holdout results, and never edits a verbatim test, the CI baseline or the freeze file to make a check pass. Figures from development seeds are always called development figures. A change after the freeze needs a new freeze and new holdout seeds, and both results are published. |
| G12 | **No alert names a real person, and no payment-based alert involves a real entity (rule R-REAL).** Every payment in NeonRadar is synthetic. A finding that rests on payments (a `PAID` in its evidence, or a detector that says so) and involves a non-synthetic entity (an evidence node, a subject, or a holder of an evidence account) is withheld and only counted (`activity_on_real`). A finding whose subject is a non-synthetic person is withheld (`real_person_subject`), and so is one whose evidence names a non-synthetic person (`real_person_evidence`); a person here is any `:LegalEntity` that is not an `:Organization`, because some sources do not state what kind of entity a record is. With `access.real_registry_alerts: false`, every finding that involves a non-synthetic entity is withheld (`registry_on_real`). What remains on a real profile are registry patterns about real organisations whose evidence names only organisations and addresses. Withheld findings are never stored, never logged with ids and never shown; the run summary holds their counts by typology. Invariant I17 checks the subjects, the evidence and the payments of every alert after every detection load. |

### 2.2 Milestone protocol

Run these steps for every milestone or sub-milestone. They are Phase 2's steps with Phase 3 names, plus steps 4a, 6b and 6c.

1. **Sync and check dependencies.** `git fetch origin`. Read `docs/build/PROGRESS.md` as it is on `origin/main` (`git show origin/main:docs/build/PROGRESS.md`). If a dependency in the milestone header is not `merged`, stop and report which one; a row still marked `pr-open` counts as merged when `gh pr view <number> --json state` reports `MERGED`, and you say so in your pull request. Phase 2 dependencies (M2.x) are read from the same file.
2. **Read.** Read the whole milestone section, the parent section of a sub-milestone (M3.5 holds rules shared by its six parts), everything it links to, the milestone's section of the code book, and `docs/build/project.yaml`. If a value the milestone needs is `TODO`, stop and ask for it. If the milestone adapts a seam of 2.10, check that seam in the repository as it is now and append what you found to `docs/build/phase-3-reconciliation.md` in this pull request: M3.0 could record only what had merged by Monday 26 October, and Phase 2 keeps merging until 4 November.
3. **Plan.** If the milestone is marked "Plan first" and the operator is in the session, present a plan (files, order, risks, how you will verify) and wait for approval. If the milestone was started with a `/goal` condition, write the plan into the pull request description draft and continue.
4. **Branch.** `git switch -c <branch named in the milestone header> origin/main`, then `uv sync --all-packages` and `npm ci --prefix ui`.
   - 4a. **Copy the verbatim files.** `uv run python scripts/spec_extract.py extract --milestone M3.x --reference /tmp/m3x-reference` (both parts of M3.4 use `--milestone M3.4`; M3.7, M3.8, M3.9 and M3.11 to M3.13 copy nothing, and skip this step; from M3.0 on; in M3.0 itself, copy `scripts/spec_extract.py` out of the code book by hand once, then use it). Commit the copies alone, with the message `chore(<scope>): copy verbatim files from the code book [M3.x]`, before any other change, so the diff of every later commit is the adaptation. Read the reference files in the scratch folder; write the adapters they describe yourself.
5. **Build in small commits.** Conventional Commits (2.3). Tests go in the same commit as the code they test.
6. **Verify.** Run every command in the milestone's "Acceptance" list. They run on synthetic data. Fix until all pass. Never weaken, skip or delete a test to make it pass; if a test is wrong, say so in the pull request.
   - 6a. **Real-data run** (only where the milestone has one). As PHASE-2.md 2.2 step 6a: do not run it yourself unless the operator said in this session that this machine is approved, the profile is in `access.real_data_profiles` (and, for an overlay, in `access.real_overlay_profiles`) and `access.data_protection_filed` is true. Otherwise write the exact command into the pull request under "Real-data run (operator)" and continue. The output that goes into the pull request is counts only.
   - 6b. **Prove the copies.** `uv run python scripts/spec_extract.py check --milestone M3.x` must report every verbatim file of the milestone as matching or as a recorded deviation (for a milestone that copies nothing it says so and exits 0). A mechanical change you had to make to a verbatim file (an import path the reconciliation names, a renamed Phase 1 function) gets a row in `docs/build/phase-3-deviations.json` (the path, the SHA-256 of your file, the milestone, the reason) and a line under "Deviations from spec"; test files, `eval/baselines/ci.json` and `eval/freeze.json` never deviate (2.10). The check output goes into the pull request as it is.
   - 6c. **Detectors on Neo4j.** For a milestone that adds or changes a detector, a query file or a `Source` implementation: `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration" -q`, and `uv run neonradar eval check` (from M3.6 on). Both outputs go into the pull request.
7. **Independent review.** Ask the `reviewer` subagent to review the branch diff against the milestone's acceptance list and section 2. Also run `contract-guardian` for M3.1, `aml-claims-checker` for anything under `docs/typologies/` or `docs/detection/`, and `data-guardian` for anything that touches the overlay, real profiles or R-REAL. Fix every finding that affects correctness, the stated requirements or the guardrails. Record the rest under "Not addressed".
8. **Record progress.** Update the milestone's row in `docs/build/PROGRESS.md` (2.8).
9. **Open the pull request** with `/open-pr`, using the template, the labels named in the milestone header and a mention of the human owner.
10. **Wait for CI** with `gh pr checks <number> --watch` (up to 20 minutes; the `eval` job takes about five). If CI fails, fix, push and wait again.
11. **Stop and report**: pull request URL, what changed, the acceptance commands with their results, the `spec_extract check` output, any real-data run still to do, deviations from this spec, open questions. Do not merge. Do not start another milestone.

When asked to address review comments: switch to the branch, make the changes, re-run the acceptance commands, push, reply to each comment with what changed, and stop. When the branch is behind `main`, `git fetch origin && git merge origin/main`, resolve conflicts, re-run the acceptance commands and push normally. Never rebase a pushed branch.

### 2.3 Branches, commits and pull requests

- **Branch names:** `p3/<milestone>-<slug>`, for example `p3/m3-2-detection-core`, `p3/m3-5a-flow-detectors`.
- **Commits:** Conventional Commits 1.0.0, `type(scope): summary`. Scopes: the earlier lists plus `synth`, `eval` and `typology`.
- **Pull request title:** `type(scope): summary [M3.x]`.
- **Pull request body:** the Phase 1 template, plus three sections when they apply: "Real-data run (operator)" with the command and its counts-only output; "Verbatim files" with the `spec_extract check` output; and "Detection impact" (the typologies whose counts in `eval/baselines/ci.json` change, with the `eval check` output before and after).
- **Labels:** always `agent` and `phase-3`; the squad label(s); `contract-change` for M3.1; `typology` for detector milestones and changes under `detect/typologies/`; `eval` for the evaluation; `docs` for documentation milestones; `freeze-change` for any change to what `eval/freeze.json` pins after M3.11; `real-data-run` when the milestone has one. M3.0 adds the new ones to `.github/labels.yml` and syncs them.
- **Size:** at most 400 changed lines, counted as in Phase 1. Verbatim files copied from the code book count in full, so every milestone that copies more than that says `| Size | exception (...) |` in its header, and `/open-pr` adds the `size-exception` label for that header form only. Any other milestone that would exceed the limit is split as PHASE-2.md 2.3 describes.
- **Human owner:** every agent pull request names one accountable human: the squad mentor for squad work, the tech lead for contract and agent-kit work, a typology researcher for detector milestones (with the detect mentor), the data steward for real-data handling.

### 2.4 Verification standard

"Done" means: every acceptance command passed in this session; CI is green on the pull request; the pull request body shows the evidence (the commands and the meaningful lines of their output, including `spec_extract check` and, for detector work, the Neo4j-mode run and `eval check`); and, where the milestone has a real-data run, either its counts-only output is in the pull request or the pull request says who will run it and the milestone row in `PROGRESS.md` says `pr-open (real-data run pending)`. Claims without output do not count.

### 2.5 Stop and ask

Stop, explain, and wait for a human when:

1. A value in `project.yaml` that the milestone needs is `TODO`.
2. Anything requires a secret, an account, a payment, an admin permission or a licence decision.
3. A fixture, test, log line, report or document would contain data about a real person or company, any value from a real record, or any OpenSanctions row.
4. A change would touch `contracts/**` or `graph/schema/**` outside the approved contract-change session (M3.1).
5. The spec and reality disagree in a way that changes behaviour (for example a field of `TypologyFile`, a row of the graph mapping, an option of the loader, or the C4 `Alert` model rejecting a field of a Phase 3 alert, 2.10). Small mechanical deviations can be fixed and recorded instead (2.2 step 6b).
6. An AML definition, threshold or legal statement has no source in `docs/sources/bibliography.yaml` or `docs/research/`.
7. An acceptance command still fails after three focused attempts.
8. Work would require pushing to `main`, force-pushing, deleting branches or tags, changing repository settings, or merging.
9. A real-data command would run on a machine that is not approved, for a profile not in `access.real_data_profiles` (or, for an overlay, not in `access.real_overlay_profiles`), before `access.data_protection_filed` is true, or in CI, Codespaces or a cloud session.
10. A verbatim test fails, or a verbatim file looks wrong. Never change the test to make it pass (G11): report the failing case, what the detector returned and what the case expects.
11. A change would alter a detector parameter default, a detector version, a matching rule or the planted mix after the freeze ADR is accepted (M3.11).
12. Anything would run, read or generate a holdout world, run `neonradar eval run --split test`, or pick seeds for the holdout.
13. A detector, a query or an overlay would produce an alert about a non-synthetic person, a payment-based alert involving a non-synthetic entity, a payment between two base entities, or an overlay record that references a base entity other than as an account holder (G12, I15, I16).
14. A pull request would change counts in `eval/baselines/ci.json` for a typology its milestone does not name.

### 2.6 Never

- Never merge a pull request, push to `main`, force-push in any form, delete a remote branch, or change repository settings. The `guard_git.py` hook blocks these; never try to get around it.
- Never write learning logs, exit posts, self-assessments, assignment submissions (including Assignment 4 cases), labels or review decisions for people.
- Never mark a typology `approved`, a contract `frozen` or an ADR `accepted`.
- Never retype a file the code book holds: extract it (2.10).
- Never edit a verbatim test file, `eval/baselines/ci.json` or `eval/freeze.json` to make a check pass. (Writing `eval/freeze.json` with `neonradar eval freeze --write` on the M3.11 branch, before ADR-0022 is accepted, is how the file is made, not an edit.)
- Never run `neonradar eval run --split test`, never choose holdout seeds, never generate a world or an overlay for a holdout seed, and never open a holdout world, its labels or its alerts, or anything under `data/cache/holdout/` (G11).
- Never plant a scenario on, or give a scenario role to, a non-synthetic entity; never create an account or a payment for a person from a real dataset (G1, G12).
- Never read, print, grep, sample or query real records (G9), and never paste a real name, birth date, address or identifier into a pull request, an issue, a commit message or the chat. Use synthetic examples.
- Never write alert text that names the conduct a typology is named after, even for a synthetic scenario (G5, 7.5.2).
- Never use GDS `write` procedures, the `graphdatascience` client or `apoc.periodic.*` in detection; never leave a GDS projection behind (7.1.6).
- Never add `@neo4j-nvl/*`, GPL-licensed Python dependencies, or vendor the GPL-3.0 Neo4j MCP binary.
- Never disable a test, lint rule, type check, hook or permission rule to make something pass without saying so in the pull request.
- Never invent an AML typology, regulation, threshold, file format, function signature or API field. Check the sources; if absent, stop and ask.

### 2.7 When the spec seems wrong

Facts in this document were verified on 18 October 2026. When a command, version, file format or API behaves differently:

1. Check the official source. Allowed domains: Phase 2's list (PHASE-2.md 2.7) plus `ecfr.gov`, `fincen.gov`, `bsaaml.ffiec.gov`, `ffiec.gov`, `fca.org.uk`, `handbook.fca.org.uk`, `ukfinance.org.uk`, `wearepay.uk`, `ons.gov.uk`, `bankofengland.co.uk`, `egmontgroup.org`, `europol.europa.eu`, `wolfsberg-group.org`, `numpy.org` and `arxiv.org`. Documentation only: Phase 3 downloads no data.
2. If the difference is mechanical (a renamed flag, a newer patch version, a function of Phase 1 with another name), adapt, and record it under "Deviations from spec" in the pull request and in the milestone's row of `PROGRESS.md`.
3. If it changes behaviour, a contract, a guardrail, a typology definition or the evaluation protocol, stop and ask (2.5).

### 2.8 Progress log format

`docs/build/PROGRESS.md` keeps its Phase 1 format. M3.0 appends one row per Phase 3 milestone and sub-milestone with status `todo`. Status values gain one note form: `pr-open (real-data run pending)` until the operator's counts-only output is in the pull request. M3.12 opens only after the human holdout run's output files are on its branch. Each pull request edits only its own row.

### 2.9 Fixtures and test data

- Tests use synthetic inputs only and never use the network.
- Detector tests build their records at run time with the test kit (`detect/tests/kit.py`, 7.4). Phase 1's committed `circular_flow` fixture stays; its case F changes (M3.2).
- A record that must look real to a test is built in the test code at run time with a test id and a test name, never committed: `gbch-co-T0000002` "Test Holding Ltd", `gbch-p-T0000003` "Test Person", and list look-alikes `ofac-T0000001`, `uksl-gT0000001`, `eufsf-T0000001` (PHASE-2.md 2.9).
- Generated worlds are never committed. CI regenerates them from their seeds (the generator is deterministic, 7.2.1), and `eval/baselines/ci.json` pins the counts they give.
- Synthetic values cannot collide with real ones: postcodes in the `QQ` area, company numbers `SY6` to `SY9` plus five digits, account numbers `NRSYN` plus ten digits, synthetic offices and lists in the `zz` jurisdiction, synthetic list authorities named "Synthetic Authority". People on synthetic lists, PEP personas and their relatives and associates have invented surnames (PHASE-2.md M2.9's rule), so no realistic full name is ever put on a synthetic list. Company names are drawn from neutral words, and before the demo is published the data steward checks every company name of `synth-demo`, and the names of its list, PEP and RCA personas, against a loaded register, counts only (M3.8).

### 2.10 Verbatim files and the code book

`docs/build/PHASE-3-CODE.md` holds every file this spec gives verbatim, grouped by milestone (`## M3.x ...`). Each entry is a heading with the repository path, a status line and one fenced block:

- **Verbatim** files are copied exactly. They were tested together on 19 October 2026: of the 116 verbatim tests, 115 passed and 1 was skipped (the world parity test, which needs Neo4j in Docker), and the reference `test_query_plans.py` was skipped for the same reason; `ruff check`, `ruff format --check` and `mypy --strict` were clean; and the 47 Cypher statements passed both linters with no problem (3.4). Never edit one beyond a recorded mechanical deviation (2.2 step 6b).
- **Reference** files show the behaviour of an adapter that meets Phase 1 or Phase 2 code; the milestone writes the adapter itself, keeping the interface the verbatim code uses. `spec_extract extract --reference DIR` writes them to `DIR` to read; it never copies them into the repository.
- **Typology files** (`detect/typologies/*.yaml`) are verbatim except their `owner:`, `status:` and `approved_by:` lines, which belong to the typology researchers: `extract` keeps the repository's lines and `check` ignores them (G4). When anything else in the file differs from the repository's copy (a new version, or new parameters, wording or a detector under the same version, as for the four extended typologies, whose Phase 1 drafts are also 0.1.0), `extract` keeps only the owner line: the changed definition starts as `status: draft` with `approved_by: null`, because an approval of one definition never carries over to another.

The script also checks each block against the SHA-256 on its status line and refuses a damaged code book. Run it from the repository root:

```bash
uv run python scripts/spec_extract.py list --milestone M3.2
uv run python scripts/spec_extract.py extract --milestone M3.2 --reference /tmp/m3-2-reference
uv run python scripts/spec_extract.py check --milestone M3.2
uv run python scripts/spec_extract.py update --path detect/typologies/structuring.yaml
```

**Changing a verbatim file later.** There is one way, so that `check` passes on `main` at every point (G3-04):

- **During its milestone**, only a mechanical deviation, recorded in `docs/build/phase-3-deviations.json` (2.2 step 6b), which `check` reads. Test files, `eval/baselines/ci.json` and `eval/freeze.json` never deviate.
- **After its milestone**, an accepted change (a fix found in review, a parameter value the typology researchers chose) changes the file and its code book block in the same pull request: make the change, then `spec_extract update --path <file>`, which rewrites the block and its SHA-256 line. A change to a test file or a typology file needs a typology researcher's approval in the pull request. A parameter value changes in three places that `test_alert_builder.py` keeps in step: the typology file's default, the detector's `Params` default and their code book blocks, plus the rows of `eval/baselines/ci.json` the change moves (updated the same way, with the `eval check` output before and after). After the freeze (M3.11) the freeze rules apply as well.

**Approval and detectors.** PHASE-1.md M1.10b says a detector is built only after its typology is approved. In Phase 3 that approval is the typology researchers' review of the verbatim test files in the seed pull request (1.4), before any detector exists. A typology file whose version changes starts again as a draft, and a typology researcher sets `status: approved` in the detector's pull request or after it; a detector milestone does not wait for it, and Gate 3 does not need it.

**The seams.** Verbatim Phase 3 code meets earlier code in these places only. M3.0's reconciliation (`docs/build/phase-3-reconciliation.md`) records, for each, what the repository has; the milestone that adapts a seam checks it again (2.2 step 2).

| Seam | Phase 3 side (verbatim) | Earlier side | Who adapts | The interface to keep |
|---|---|---|---|---|
| Graph rows | `graphrows.py` (verbatim since this version), `memgraph.py`, `memsource.py`, every detector test | `neonradar_graph.mapping` (PHASE-1.md M1.7b, PHASE-2.md M2.11) | none: the oracle reads C1 records itself, so that it is an independent implementation | `from_records(records) -> MemGraph` with exactly the C2 labels and properties of 7.1.2 (`test_graphrows.py`); every detector test in Neo4j mode, and the world parity test, compare it with the loader (7.1.5) |
| Catalog | `wording.py`, `runner.py`, `alerts.py`, tests | `TypologyFile` and `load_catalog()` (M1.7c) | M3.2: `catalog.py` | `load() -> dict[str, Typology]` (the dataclass of the reference file) and `params_for(typology, module, overrides)`; `TypologyFile` gains `shape_name`, `wording.variants` and `wording.detail` (7.5.2) |
| Wording lint | `wording.render` (every rendered text, at run time), `runner` and `alerts` tests | Phase 1's lint over `contracts/wording/forbidden-terms.txt` | M3.2: `wording_lint.py` | `violations(text, masked) -> list[str]`, calling Phase 1's function with the captions masked and adding `PHRASES` and `CONDUCT` |
| Phase 1 detection code | `runner.py`, `wording.py` | Phase 1's run logic and `render_headline` (M1.9b, M1.7c), their tests, `contracts/tests/test_wording.py` (PHASE-1.md 5.5) | M3.2 (and M3.1 for `contracts/**`) | Phase 1's `render_headline` stays as a thin wrapper over `wording.render_template`, so its callers and tests keep working; a contract test that cannot take the Phase 3 typology files is changed in M3.1's contract-change session (M3.0 says which) |
| Alert model | `alerts.py`, `test_alert_contract.py`, every detector milestone | `neonradar_contracts.alert.Alert` (M1.7c) and `compute_alert_id` | none | Phase 3 metric values are numbers, strings or booleans, never lists or nulls; M3.0 records the types the model accepts, and an alert it rejects is a stop-and-ask case (2.5 item 5) |
| Names | the generator and its tests | `names.py`, `companies.py`, `denylist.txt` (M1.8e), Phase 2's invented surnames (`variants.py`, M2.9) | M3.3: `namesource.py` | `default_names()` with the five methods of `ctx.NameSource`, drawing only from the generator it is given, with at least 1,000,000 distinct company names (7.2.3); extra words live in `namesource.py`, never in Phase 1's lists |
| Test fixtures | detector tests, the world parity test | the Testcontainers fixture and loader of Phases 1 and 2 | M3.2: `detect/tests/conftest.py`, `neo4j_mode.py` | `kit.SOURCE_FACTORY`, the `neo4j_source_factory` fixture, and `NR_DETECT_SOURCE=neo4j` (7.1.5) |
| Detection store | `RunResult` from `runner.run_detection` | Phase 1's run folder writer and alert queries (M1.9b) | M3.2 | C2 1.2.0 L19 (5.2) |
| Project file | the CLI commands of M3.2, M3.4, M3.6, M3.11 | `neonradar_ingest.data.project.Project` (M2.2) | M3.0 | the keys of 1.3, read through the model, never parsed ad hoc |
| CLI | `neonradar_cli/evaluate.py` | the `neonradar` typer app (M1.3) | M3.3, M3.4, M3.6, M3.7 | the commands and options of each milestone |
| Profiles and layout | the three synthetic profiles (M3.3) | `neonradar_ingest.data` (M2.2) | M3.3 (synthetic profiles, `worlds_dir`, `eval_dir`), M3.4 (real profiles, `runs_dir`, `latest_detection_run`) | the YAML of 7.11 and the paths of 4.5 |

---

## 3. Verified technical baseline (18 October 2026)

PHASE-1.md section 3 and PHASE-2.md section 3 still apply. This section adds what Phase 3 needs. Every version was checked against PyPI, Docker Hub or the official documentation on 18 October 2026, and every code fact was checked by running code. The four research notes in `docs/research/2026-10-18-detection/` hold the sources and the reasoning: `detection-cypher-gds.md` (Cypher 5, GDS 2.13, testing), `typology-detection-definitions.md` (definitions, thresholds, the three sanctions tests, PEP rules, wording and legal risk), `synthetic-transactions.md` (generators, calibration, scenarios, label files, determinism) and `evaluation-alerting.md` (matching, statistics, CI gates, the queue, explanations).

### 3.1 Pinned versions (additions)

| Component | Pin | Notes |
|---|---|---|
| numpy | `==2.5.*` (2.5.4) | The generator's random streams. NumPy keeps a stream only on the same build and may change `Generator` methods in a feature release (`evaluation-alerting.md` 3.4), so a lock bump of numpy is a generator change: the pull request runs `neonradar eval check` and explains any count that moves. Dependabot puts numpy and Faker in a group of their own (M3.0) |
| Faker | unchanged (`>=40.43,<41`, 40.43.0) | Names only: a Faker change moves names, never structure, because names draw from their own streams (7.2.1) |
| PyYAML | `>=6.0.3,<7` (6.0.3) | The typology catalog; M3.0 keeps Phase 1's pin if `detect` already has one, else adds this one |
| neo4j driver | unchanged (`>=6.4,<7`; 6.4.1) | Detector queries run as `session.run(neo4j.Query(text, timeout=...), parameters)`: auto-commit, ended by the server on timeout, never retried by the driver (`detection-cypher-gds.md` 3.4) |
| Neo4j, APOC, GDS | unchanged: `neo4j:5.26.32-community` with APOC Core 5.26.32 and GDS 2.13.14 | CI pins the image digest `sha256:0a6e7aedf54a531f76286032d4365ead65b11cca05e4a15cdf23b8e53d6db02b` (18 October 2026; the tag was re-pushed on 17 October) and bumps it in reviewed pull requests (`detection-cypher-gds.md` 5.2) |
| testcontainers | unchanged (`[neo4j]>=4.15,<5`; 4.15.0) | `NEO4J_PLUGINS='["apoc", "graph-data-science"]'` and `dbms.security.procedures.unrestricted=apoc.*,gds.*` (setting it replaces the image's line, so list both) |
| graphdatascience | not used | Version 2.2 caps `pyarrow` below 26, which conflicts with the Phase 2 pin (decision 13) |
| Python | 3.14 (3.14.6 tested) | unchanged |

### 3.2 Known traps for AI-written code (additions)

| Area | Trap | Do this instead |
|---|---|---|
| Cypher 5 paths | Inside a quantified path pattern each iteration has fresh variables, so a predicate cannot compare a hop with the previous one; strictly increasing `PAID.ts` cannot prune the expansion. `allReduce()`, which can, is Cypher 25 only (2025.08) | Expand one hop per query from anchored starts, with the time and amount limits in the query and the path kept in Python (7.1.3) |
| Cypher 5 | 5.26 has only the default match mode and no path modes; `SHORTEST k` and friends exist but return arbitrary evidence among equals | Use the hop expansion; where a shortest path is needed, `ALL SHORTEST` with an id order |
| Cypher indexes | The `paid_ts` index serves only a relationship the plan seeks directly; an expansion from a node reads all of that node's `PAID` relationships, and a cash ledger can have tens of thousands | Anchor window queries on the `paid_ts` range seek; exclude `cash_ledger` accounts from flow and path queries (7.1.2) |
| Cypher values | Durations do not compare (`duration < duration` gives null); a naive datetime parameter or a null list silently drops rows; an undirected pattern counts every relationship twice | Pass times as UTC ISO strings into `datetime($t)`; compare `duration.inSeconds(a, b).seconds`; `coalesce(x, [])`; directed patterns |
| Cypher ids | `MATCH (n {id: $id})` without a label scans every node | Name `:Entity` (or `:Sanction`) so the uniqueness index is used |
| Cypher order | Without `ORDER BY`, Neo4j does not guarantee row order, so `LIMIT` keeps different rows on different runs | `ORDER BY` a total order that ends in a C2 id before every `LIMIT` |
| GDS 2.13 | `gds.graph.project.cypher` is deprecated; concurrency above 4 fails on Community; Louvain can vary at concurrency above 1; component ids are not stable between runs; `write` adds properties C2 does not define | The Cypher aggregation `gds.graph.project(...)`, `gds.wcc.stream` with concurrency 4, components named by their smallest member id, the projection dropped in `finally` (7.1.6) |
| Neo4j driver 6 | Managed transactions (`execute_read`) retry `TransientError`, and the memory-limit error is one, so a heavy query can run several times | Auto-commit `session.run(neo4j.Query(text, timeout=s))` for detector queries |
| numpy | `default_rng(seed)` shared across components makes every later draw depend on every earlier one | Named streams: `SeedSequence(entropy=seed, spawn_key=...)` per component and key, with an explicit `PCG64` (7.2.1) |
| Python | `PYTHONHASHSEED` is random by default, so set iteration order differs between processes | Sort before every output; never let a set's order reach a record, a label, an id or a query |
| FollowTheMoney 4.11 | `ValueEntity.from_dict()` removes `datasets` and `referents` from the dict it is given | Never pass a shared dict; the generator writes dicts directly (7.2.2) |
| Money | Floating-point sums drift at the last cent | Integer pence inside the generator and in cash profiles; two-decimal strings in records (C1 R7) |
| Memory | A Python dict per payment costs about 1.7 KB; two million of them do not fit beside Neo4j on a 16 GB laptop | The generator keeps payments as their C1 lines and the writer streams (7.2.3, 7.2.8) |
| pytest | With `--import-mode=importlib`, helper modules next to the tests are not importable | The conftest puts the tests folder on `sys.path` (7.4) |
| Testcontainers | The default wait is 120 s; with both plugins Neo4j may take 20 to 60 s to start | `TC_MAX_TRIES=180` in CI; one container per session |

### 3.3 Data sources and licences (Phase 3)

Phase 3 adds no dataset. Its synthetic output stays the `nr_synthetic` dataset (Apache-2.0, `synthetic: true`). The published figures and the scenario designs draw on these works, cited, never vendored:

| Work | Licence | Phase 3 use |
|---|---|---|
| AMLSim (IBM) | Apache-2.0; unmaintained since 14 February 2022 | Ideas only (the eight classic shapes); its code is not used |
| AMLworld (IBM, Kaggle version 8, July 2025) | CDLA-Sharing-1.0; the generator is not released | Not used; its transaction-level F1 is the kind of figure NeonRadar does not publish |
| SAML-D | CC BY-NC-SA 4.0 | Not used |
| AMLGentex | Apache-2.0; cannot be installed on Python 3.14 as pinned | Ideas only (typology knobs, average precision at recall 0.6) |
| Tide | MIT | Ideas only (benign "counter-leakage" look-alikes in the background) |
| AMLNet 2.0 | CC BY-NC 4.0; code withheld | Not used |
| UK Finance, ONS, HMRC, Pay.UK and GOV.UK figures and calendars | published statistics and guidance | Calibration of the background activity (7.2.9), cited |

A user who wants an external dataset later imports it themselves; NeonRadar ships no importer in Phase 3 (`synthetic-transactions.md` 1.4).

### 3.4 Formulas and verified figures

**Wilson score interval**: as PHASE-2.md 3.4, implemented again in `neonradar_detect.evaluation.stats` so that `detect` does not depend on `resolve` (it would bring Splink, DuckDB and PyArrow).

**Across-seed t interval.** For per-seed rates `r_1 ... r_m` (seeds with nothing to count are left out), `mean +- t(0.975, m - 1) * s / sqrt(m)`, clipped to [0, 1], where `s` is the sample standard deviation; none for fewer than two seeds. **The published interval is the wider of the two**: scenarios of one seed share their background, so the pooled Wilson interval alone covered only 69 to 80 percent in simulation when seeds differ strongly, and the wider-of-two rule covered 92 to 98.5 percent (`evaluation-alerting.md` 2.3).

**Overlap** of two sets: intersection over union, `|A and B| / |A or B|`, zero for two empty sets; a match needs at least 0.5 (the PASCAL VOC convention, `evaluation-alerting.md` 1.3).

**Recall and precision per typology**: recall = planted illicit scenarios detected / planted illicit scenarios; precision = true alerts / all alerts of the typology (7.6.2 defines "true"); a rate with nothing to count is published as "n = 0". Macro figures are unweighted means over typologies; macro F1 is the mean of per-typology F1 (one of two formulas in use, named in the report).

**Pattern strength** is a typology's own weighted mean of three to five closeness-to-the-definition terms, clipped to [0, 1], documented in each detector's docstring and in 7.3. It orders the queue (`high` from 0.75, `medium` from 0.5, PHASE-1.md 5.4) and is never called a risk score; it does not compare across typologies.

**Sample sizes**: a 10-point half-width needs 93 scenarios at an observed rate of 0.5, 60 at 0.8 and 37 at 0.9; hence 100 illicit and 100 look-alike scenarios per typology on the holdout seeds (ten seeds of ten each) (`evaluation-alerting.md` 2.2).

**Verified on 18 October 2026, and again on 19 October after the three independent reviews** (the code book, run together, Python 3.14.6): of the 116 verbatim tests, 115 passed and 1 was skipped (the world parity test, which needs Neo4j in Docker), and the reference `test_query_plans.py` was skipped for the same reason; `ruff check`, `ruff format --check` and `mypy --strict` clean; 33 query files with 40 Cypher statements, plus 3 graph query files with 7 statements, with no problem under the project linter (PHASE-2.md M2.0) and a stricter registry check (`detection-cypher-gds.md` 2.19); every record the test kit builds, and a generated world and overlay, passed a prototype check of the C1 1.1.0 rules (the repository's own validator first sees them in M3.2's Neo4j mode and M3.3's strict validation); every alert of the `synth-demo` world and of development seed 1 had C4's field types (metric values are numbers, strings or booleans), a run id in C4's form and a headline short enough not to be cut; the CI seed reproduced `eval/baselines/ci.json` exactly. There was no Docker daemon and no Neo4j server where the code book was built, so **no query has been executed on a server**: M3.2's Neo4j-mode run is the first (7.1.5). The development figures of 7.6.5 came from the same code.

### 3.5 Corrections to Phases 1 and 2

| Earlier spec said | Correct | Source |
|---|---|---|
| Structuring: the threshold "after the US reporting threshold described in FIN-2014-A005", "with a daily total above the threshold" (PHASE-1.md 7.2 entry 1) | The US threshold is 31 CFR 1010.311, "more than $10,000", so 10,000 exactly is below it and the band is closed at the top; structuring is "in any amount" and "on one or more days", so a daily total above the threshold is a strength term, not a condition; GBP and EUR are modelled on the UK high value dealer rule ("£10,000 or more") and the AMLR's due diligence threshold ("at least EUR 10 000"), under which exactly 10,000 is not below the threshold: modelling choices (7.3.1), and the AMLR's report of cash deposits covers those "above the limit" (Article 80(4)), so the inclusive edge depends on the currency (`below_inclusive_currencies`) | `typology-detection-definitions.md` 1 and 17.1 |
| Circular flow: same-account cycles only in Phase 1, the same-holder variant "Phase 3 work" | Both variants; a payment straight back to the same account is not a finding (7.3.4) | `typology-detection-definitions.md` 4 |
| Fan-in: "often from recently opened accounts" applied to the senders (PHASE-1.md 7.2 entry 5) | Recency and short use apply to the collector and the first-layer accounts; senders are often victims | `typology-detection-definitions.md` 5 |
| Dormant reactivation: "no `PAID` edges for a long gap (default 180 days)" | "An account with little activity" (low, not zero); 180 days is a modelling choice; the history before the gap must exist, or a new account looks dormant | `typology-detection-definitions.md` 7 |
| Sanctions exposure: the sum over paths of the product of shares as a teaching metric, an OFAC-style flag, and "`CONTROLS` and `DIRECTOR_OF` links create exposure without ownership" (PHASE-1.md 7.2 entry 10) | Three tests, each computed as a fixed point on band bounds and reported in full sentences as met, left open by the bands, or not met: US (50 percent or more, added across blocked owners, status passing entity by entity, control never counts), UK (more than 50 percent of the shares or votes, or the right to appoint or remove a majority of the board, per person along majority-stake chains; holdings of different listed persons are not simply added up unless, for example, they are held under a joint arrangement or one party controls the rights of another, which registry records cannot show; a nominee's share counts for the person it is held for; the control condition of reg 7(4) is left to assess), EU (50 percent or more, added up, plus control criteria that can be rebutted). Shares are never multiplied down a chain for these tests, and the reporting floor adds up recorded holdings | `typology-detection-definitions.md` 10 |
| PEP exposure: "paths of at most 4 hops ... through `FAMILY_OF`, `ASSOCIATE_OF`, `OWNS`, `CONTROLS` or `DIRECTOR_OF`" (PHASE-1.md 7.2 entry 13) | One family hop (a spouse or civil partner, children and their spouses or civil partners, parents; siblings in FCA guidance), read in the direction FtM records the relationship, and one associate hop for close business relations or a joint holding, then ownership or control to the subject; once the PEP leaves office the firm "is no longer required to apply" the measures to family members and associates, and the PEP stays in scope for at least 12 months after | MLR 2017 reg 35(9), (11), (12); `typology-detection-definitions.md` 13 |
| Cash commingling: "far above peers with the same `sector`" | The same sector in the same area (FFIEC: "similar restaurants in the area") | `typology-detection-definitions.md` 14 |
| Mass registration addresses: a count threshold only | Skip the three Companies House default addresses; flag PO boxes (Annex E's "Only a post-box address"; for UK companies, not accepted as a registered office since 4 March 2024); the threshold is a percentile of the loaded data on real profiles | `typology-detection-definitions.md` 9 |
| Registry typologies (PHASE-1.md 7.2 entries 8 to 13): silent on relationships that have ended | Only relationships that still hold at the end of the window count (no end date, or a later one): a resigned director or a sold holding is history, and below 50 percent an entity "is no longer considered automatically to be a blocked entity" (OFAC FAQ 402); this is NeonRadar's reading, with the limits 7.3.10 states (property already blocked stays blocked, and a sham transfer does not end a blocked interest) | `typology-detection-definitions.md` 10.1 and 12 |
| PHASE-1.md M1.9b circular-flow query `(a:Account)-[t:PAID]->{2,6}(a)` | Unanchored: it enumerates paths before filtering; replaced (decision 6) | `detection-cypher-gds.md` 2.6 |
| PHASE-1.md M1.9b case F: an alert on a real holder with `structural_pattern` | Withheld and counted under R-REAL (decision 3) | 2.1 G12 |
| PHASE-2.md C2 L17: the real-data instance refuses every synthetic record | L18: overlay loads are the one exception (5.2) | decision 11 |
| `aml-domain.md` (Phase 1 research): three quotes (a FinCEN shell-company indicator, a joined FIN-2025-A003 quote, the ICIJ disclaimer wording) and the EU test as "more than 50 percent" | Re-check the first two before reuse; the ICIJ FAQ reads "any individuals, companies or other entities" and "found in the database using addresses"; the EU test is "50% or more" | `typology-detection-definitions.md` 17.2 |

---

## 4. Architecture and repository layout

### 4.1 Components and data flow

```text
 ingest/profiles/<profile>.yaml        which base, which overlay, which detection settings
            |
            v
 neonradar synth world   (ingest)  ->  synthetic profiles only: the base, a synthetic register
            |                          data/cache/synthetic/worlds/<world>/<seed>/
            |                          (real profiles: the Phase 2 records and resolution run are the base)
            v
 neonradar synth overlay (ingest)  ->  data/cache/<real|synthetic>/overlay/<profile>/<overlay_id>/
            |                          accounts for eligible base organisations, background payments,
            |                          scenarios and look-alikes among new synthetic entities,
            |                          overlay.json, labels/ (label files v2)
            v
 neonradar graph load    (graph)   ->  the base load (Phase 2), then the overlay (C2 1.2.0, L18):
   --overlay latest                    syn-ov- records, HOLDS_ACCOUNT from base organisations;
            |                          synthetic profiles: neo4j; real profiles: neo4j-real
            v
 neonradar graph verify  (graph)   ->  invariants I1 to I17 (I15 to I17 new)
            v
 neonradar detect run    (detect)  ->  data/cache/<real|synthetic>/runs/<profile>/<run_id>/
            |                          alerts.jsonl, summary.json; :DetectionRun, :Alert, FLAGS (L19)
            v
 neonradar eval run      (cli)     ->  data/cache/synthetic/eval/<eval_id>/ (synthetic profiles only)
                                       report.md, report.json, one folder per seed

 detect/ results  -->  api/ (Phase 1 alert endpoints; Phase 4)  -->  ui/ (Phase 5), copilot/ (Phase 4)
```

`make load PROFILE=<name>` gains three steps (M3.7): `world` first for a synthetic profile with a world block, then, after Phase 2's `load`, `overlay` (generate and load) and `detect`; `verify` (I1 to I17) stays last.

**Inside a detection run.**

```text
params_for(typology, module, profile overrides)        catalog defaults, within bounds (7.3, 7.11)
      |
      v
detector.run(source, params, window)  ---- candidate steps (source.py, rows.py) ---->  Source
      |                                                                     MemSource: MemGraph (the oracle)
      |  Findings (model.py)                                                Neo4jSource: queries/*.cypher
      v
runner: node_info, edge_info -> policy.data_flags -> policy.decide (R-REAL: emit or withhold)
      -> wording.render -> alerts.build (C4 1.0.0) -> RunResult(alerts, summary with withheld counts)
```

Every detector sees the graph only through the `Source` protocol, so the same detector code runs on the in-memory oracle (unit tests, the CI gate, development evaluations) and on Neo4j (`detect run`, the world parity test, the published evaluation). The parity tests prove the two give the same rows and the same alerts (7.1.5).

**Package rules.** `neonradar_detect` depends on `contracts` (alert ids, the C4 model), the `neo4j` driver (for `Neo4jSource`) and PyYAML, and imports neither `neonradar_graph` nor `neonradar_ingest`. `graphrows.py` is the oracle's own reading of C2, written apart from the loader's mapping on purpose, so that every detector test in Neo4j mode and the world parity test compare two independent implementations (7.1.5). The generator and the detectors are written and parameterised independently, so the generator cannot leak its labels into detection and the detectors cannot be fitted to its internals (`synthetic-transactions.md` 6.2). `neonradar_ingest.synth` never imports `neonradar_detect`. `neonradar_cli` imports both and is where they meet (`evaluate.py`). Tests may import across packages: `detect`'s `dev` dependency group lists `neonradar-ingest` and `neonradar-cli` for the Neo4j test mode and the world parity test, as Phase 2 did for one `graph` fixture.

### 4.2 Repository changes at the end of Phase 3

```text
neonradar/
  detect/
    src/neonradar_detect/
      model.py rows.py source.py memgraph.py graphrows.py memsource.py neo4jsource.py
      expand.py policy.py alerts.py wording.py wording_lint.py catalog.py runner.py   (M3.2)
      queries/*.cypher                  33 query files: candidate steps and the evidence query (M3.2)
      detectors/<slug>.py               14 detectors (circular_flow in M3.2, the rest in M3.5a to M3.5f)
      evaluation/match.py metrics.py stats.py harness.py report.py                    (M3.6)
    typologies/<slug>.yaml              14 files updated (M3.2, M3.5); trade_based_ml.yaml unchanged
    tests/kit.py neo4j_mode.py conftest.py test_*.py
  ingest/
    src/neonradar_ingest/synth/         generator v1 beside v0: streams, dates, records, ctx, base,
                                        background, world, overlay, labels, writer, namesource,
                                        scenarios/<slug>.py for 14 typologies (M3.3)
    profiles/synth-eval.yaml, synth-demo.yaml, synth-scale.yaml (NEW, M3.3); overlay and
                                        detection blocks added to demo.yaml, uk-tiny.yaml, uk-sample.yaml (M3.4)
    tests/test_synth_v1.py names_simple.py
  graph/src/neonradar_graph/queries/    verify_overlay.cypher (M3.1), overlay_purge.cypher,
                                        overlay_unresolved.cypher (M3.4)
  cli/src/neonradar_cli/evaluate.py     the evaluation run (M3.6); synth, detect and eval commands
  eval/
    seeds.yaml                          development, CI and holdout seeds (M3.6; holdout in M3.11)
    baselines/ci.json                   exact counts on the CI seed (M3.6)
    freeze.json                         the frozen detection configuration (M3.11)
  docs/
    detection/README.md                 method: candidate steps, R-REAL, evaluation (M3.10)
    typologies/*.md                     explainers with the detection definitions (M3.10)
    data/detection/evaluation-<date>.md published figures, counts only (M3.12)
    data/benchmarks/<date>-synth-scale.md   scale world measurements (M3.9)
    decisions/0020 to 0024              ADRs (M3.10; 0022 accepted at the freeze, M3.11)
    team/assignment-4.md                Assignment 4 (M3.10)
    build/PHASE-3.md, PHASE-3-CODE.md, phase-3-reconciliation.md, reports/phase-3.md
    research/2026-10-18-detection/      Phase 3 research notes
  scripts/spec_extract.py               the code book script (M3.0)
  .claude/rules/detect.md, .claude/rules/synth.md   (M3.0)
```

### 4.3 Ownership map additions

| Path | Owner (CODEOWNERS) | Required reviewer for |
|---|---|---|
| `eval/` | `nr-detect` and the tech lead | seeds, baselines, the freeze file |
| `eval/freeze.json`, `eval/seeds.yaml` | the tech lead and the typology researchers | the frozen configuration and the holdout seeds |
| `detect/tests/` | `nr-detect` and the typology researchers | the approved test cases (1.9) |
| `ingest/src/neonradar_ingest/synth/scenarios/` | `nr-ingest` and the typology researchers | what each scenario and look-alike plants |
| `docs/detection/`, `docs/data/detection/` | `nr-detect` | method and published figures |
| `.claude/rules/detect.md`, `.claude/rules/synth.md` | tech lead | agent kit |

`scripts/generate_codeowners.py` keeps its ordering rule: a specific path comes after the broader one that contains it (`eval/freeze.json` after `eval/`, `detect/tests/` after `detect/`).

### 4.4 Naming conventions added in Phase 3

| Thing | Convention | Example |
|---|---|---|
| World record id | `syn-w-<kind>-<6 digits>`, numbered per kind in generation order | `syn-w-co-000042` |
| Overlay record id | `syn-ov-<kind>-<first 16 hex of SHA-256 of seed, kind and key>`: it says what the record is, never its role in a scenario (C1 R9) | `syn-ov-pay-3f9a2c41d07e88b1` |
| Scenario id (labels only) | `scn-<6 digits>`, in catalog order within an overlay | `scn-000017` |
| Overlay id | `ov-<UTC yyyymmddThhmmss>-<4 hex>` | `ov-20261030T101500-7c2e` |
| Detection run id | unchanged (C4): `run-<UTC yyyymmddThhmmss>-<4 hex>` | `run-20261102T090000-0001` |
| Evaluation id | `eval-<split>-<UTC yyyymmddThhmmss>-<4 hex>` | `eval-dev-20261029T140000-a1b2` |
| Synthetic profiles | `synth-<purpose>` | `synth-eval`, `synth-demo`, `synth-scale` |
| World name | the profile's purpose | `eval`, `demo`, `scale` |
| Variants and look-alike kinds | lower snake case, one set per typology (7.3) | `same_holder`, `payroll_run` |
| Query files | `<Source method>.cypher`, one per step; four files `recent_account_*` for the GDS ring step | `paid_hop.cypher` |
| Detector versions | the typology file's `version` equals the module's `VERSION` (tested) | `0.2.0` |

### 4.5 Data directories

Phase 2's tree (PHASE-2.md 4.5) gains these folders. Real-profile outputs stay under `data/cache/real/`, where the agent never reads (G9); the counts-only summaries of every command go to `data/cache/reports/<profile>/` as before.

```text
data/cache/
  synthetic/
    worlds/<world>/<seed>/              nr_synthetic-<yyyymmdd>-world.ftm.jsonl + manifest (synth world)
    overlay/<profile>/<overlay_id>/     nr_synthetic-<yyyymmdd>-overlay.ftm.jsonl + manifest,
                                        overlay.json, labels/ (synth overlay)
    overlay/<profile>/LATEST            id of the newest complete overlay (written last)
    runs/<profile>/<run_id>/            alerts.jsonl, summary.json, run.json (detect run)
    runs/<profile>/LATEST
    eval/<eval_id>/                     report.md, report.json, seeds.json, seed-<n>/labels/,
                                        seed-<n>/alerts.jsonl (eval run, development split)
  holdout/<eval_id>/                    the same for the test split (the human holdout run, M3.12);
                                        closed to the agent like real/ (M3.0, G11)
  real/
    overlay/<profile>/<overlay_id>/     a real profile's overlay (synthetic records next to real ones)
    overlay/<profile>/LATEST
    runs/<profile>/<run_id>/            a real profile's detection run
    runs/<profile>/LATEST
```

`neonradar_ingest.data.layout` (M2.2) gains `worlds_dir(world, seed)`, `overlay_dir(profile, overlay_id)`, `latest_overlay(profile)`, `eval_dir(eval_id)` and `holdout_dir(eval_id)` (M3.3), and `runs_dir(profile, run_id)` and `latest_detection_run(profile)` (M3.4). A synthetic profile never opens a path under `data/cache/real/`; a real profile's overlay and runs never go anywhere else. Runs without a profile keep Phase 1's `data/runs/<run_id>/`. Retention: `access.real_data_days` governs `real/overlay/` and `real/runs/` like every other real-profile output; synthetic worlds, overlays, runs and evaluations can be deleted at any time and regenerated from their seeds.

**`overlay.json`** (written last, then `LATEST`): `overlay_id`, `profile`, `seed`, `split` (`dev` or `test`), `generator_version`, `label_schema`, `period` (`start`, `end`), `config` (the overlay block as used), `base` (`datasets`, the record files with their SHA-256 from the manifests, and the resolution run id when there is one), `records_sha256`, `counts` (records by schema, eligible and active organisations, scenarios and look-alikes by typology) and `created_at`. It holds no record values, so on a real profile it is counts only.

---

## 5. Contract changes in Phase 3 (C2 1.2.0)

The four contracts are defined in PHASE-1.md section 5 and changed by PHASE-2.md section 5. Phase 3 changes one, C2, and only additively (a minor version under PHASE-1.md 5.0): nothing is renamed or removed, and every graph that was valid under 1.1.0 stays valid.

| Contract | Version after Phase 3 | Milestone | What changes |
|---|---|---|---|
| C1 record | 1.1.0 (unchanged) | none | Overlay records are ordinary 1.1.0 records; L18 defines how an overlay load meets R4 and R8 |
| C2 graph schema | 1.2.0 | M3.1 | `:Sanction.provisions`; five `:DetectionRun` properties; two `:Alert` properties (the evidence ids); loader rules L18 (overlay loads) and L19 (detection loads); invariants I15 to I17 |
| C3 API | 1.1.0 (unchanged) | none | The Phase 1 alert endpoints read `:Alert` as before; the run summary is exposed in Phase 4 |
| C4 alert | 1.0.0 (unchanged) | none | New typologies document their `metrics` and subject roles in their typology files (7.3), as C4 allows |

`neonradar_contracts.versions` becomes `GRAPH_SCHEMA = "1.2.0"` and `CONTRACTS = "1.2.0"`; `RECORD`, `API` and `ALERT` keep Phase 2's values.

### 5.0 The change procedure for Phase 3

The freeze tag `contracts-v1.0.0` stays where it is, so the guard hook and the CI label check keep protecting `contracts/**` and `graph/schema/**`. The procedure is Phase 2's (PHASE-2.md 5.0), once:

1. The operator opens a `contract-change` issue with the text below. It may be opened on Friday 23 October, but M3.1 starts only after Phase 2's last contract change (M2.1c) has merged and `contracts-v1.1.0` is tagged, because versions are applied and tagged in order.
2. The tech lead approves it in a comment ("Approved for M3.1"). The data steward also approves it, because L18 lets synthetic records into the real-data instance.
3. The tech lead adds `{"env": {"NR_ALLOW_CONTRACT_CHANGE": "1"}}` to `.claude/settings.local.json` and starts a fresh Claude Code session.
4. `/milestone M3.1` follows the `/contract-change` skill: bump the version, update `contracts/CHANGELOG.md` and `contracts/C2-graph.md`, update every consumer and test in the same pull request, label it `contract-change`.
5. After the pull request is open, the tech lead removes the setting.
6. When M3.1 is merged (and Phase 2's `contracts-v1.1.0` exists), the tech lead runs `make check && make contracts-check` on `main` and tags it: `git tag -a contracts-v1.2.0 -m "NeonRadar contracts v1.2.0 (Phase 3)" && git push origin contracts-v1.2.0`.

Issue text (copy it as it is):

```markdown
Title: Contract change: C2 graph schema 1.2.0 (overlays, bridge invariants, detection runs)

Classification: minor (additive). Milestone: M3.1, PHASE-3.md 5.2.
Change: add :Sanction.provisions (LIST<STRING>); add :DetectionRun properties profile,
params_sha256, summary, window_start, window_end; add :Alert properties evidence_node_ids
and evidence_edge_ids (LIST<STRING>); loader rule L18 (overlay loads: synthetic syn-ov-
records onto a loaded base, in the base's instance, including neo4j-real for the profiles
in access.real_overlay_profiles, after the bridge check; the previous overlay and all
detection results are removed first); loader rule L19 (a detection load replaces the
previous detection results); invariants I15 (the only synthetic to non-synthetic
relationship is HOLDS_ACCOUNT from a non-synthetic organisation to a synthetic account),
I16 (no PAID between two accounts held by non-synthetic entities) and I17 (no :Alert names
a non-synthetic person, a :LegalEntity that is not an :Organization, as a subject or in its
evidence, and no :Alert that involves a non-synthetic entity has a PAID in its evidence);
graph/src/neonradar_graph/queries/verify_overlay.cypher. If the M3.0 reconciliation says
so, also contracts/tests/test_wording.py and test_alert.py, test-only, so that they accept
the Phase 3 typology files (placeholder filters, wording.variants, wording.detail).
Consumers: graph mapping (provisions), graph loader (L18 in M3.4), graph verify (I15 to
I17, wired in M3.4 once PHASE-2.md M2.11's verify exists), detection store (L19 and the two
:Alert properties in M3.2), detectors (sanctions_exposure reads provisions).
Compatibility: a 1.1.0 graph is a valid 1.2.0 graph; no migration (no constraint or index
changes).
Approvals needed: tech lead (contract), data steward (L18 and the real-data instance).
```

### 5.1 C1: unchanged (1.1.0)

Overlay records are ordinary C1 1.1.0 records: dataset `nr_synthetic`, ids starting `syn-ov-`, `nr.synthetic: true`, and `nr.synthetic_kind` `registry` (synthetic companies, people and addresses), `activity` (accounts, account holdings, payments) or `list` (synthetic list entries and their designations). Labels stay in label files outside the records (R9; the generator's tests check that no record names a scenario, a typology, a role or a look-alike, 7.2.8).

Two rules need a word, because an overlay is loaded on top of a base that is not in its files:

- **R4** (references may point to records in other files of the same load) and **R8** (every `BankAccount` has a `LegalEntity` holder in the same load): for an overlay load, the base counts as part of the same load. L18 makes the check exact: every reference to a non-overlay id must resolve in the target instance before anything is written.
- **R8's account numbers**: the generator gives every new account a stable `NRSYN` number from a hash of its id and skips any number the base already uses (7.2.2).

Payment channels stay the C1 enumeration (`wire`, `card`, `cash_deposit`, `cash_withdrawal`, `internal`). Two facts that C1 cannot carry, the person who made a cash deposit and the payment scheme, are not modelled (`synthetic-transactions.md` 0, answer 3); the structuring detector works per receiving holder, which does not need them.

### 5.2 C2: Graph schema 1.2.0

**New node properties.**

| Label | Property | Type | Rule |
|---|---|---|---|
| `:Sanction` | `provisions` | LIST<STRING> | every value of FtM `Sanction.provisions`, as published (for example `Asset freeze`, `Travel ban`); the UK sanctions test counts only asset-freeze designations (7.3.10). Empty when the source gives none |
| `:DetectionRun` | `profile` | STRING | the profile the run belongs to, or null for a run without one |
| `:DetectionRun` | `params_sha256` | STRING | SHA-256 of the parameters every detector actually used, as canonical JSON (`runner.params_sha256`) |
| `:DetectionRun` | `window_start`, `window_end` | STRING | the detection window, UTC ISO datetimes |
| `:DetectionRun` | `summary` | STRING | the run summary as JSON (7.5.3): per typology the findings, alerts, duplicates, withheld counts by reason and the detector's own counts; the totals. Counts only, on every profile |
| `:Alert` | `evidence_node_ids`, `evidence_edge_ids` | LIST<STRING> | the alert's `evidence.node_ids` and `evidence.edge_ids` (C4), so that I17 can check the evidence of every alert without parsing `payload` |

**Loader rules added** (numbered after PHASE-2.md L8 to L17):

- **L18. Overlay loads.** `neonradar graph load --overlay DIR` (or `--profile NAME --overlay latest`) loads one overlay folder onto the base already loaded for its profile:
  1. Before connecting: every record's id starts with `syn-ov-` and its dataset is `nr_synthetic`; `overlay.json` names the profile; and the bridge check passes on the records: the only records that name a non-overlay id are `Ownership` records with role `account holder` whose asset is an overlay `BankAccount`, and `Payment` records whose `payer` or `beneficiary` is the holder of the account the payment names (C1 R7; `PAID` joins the accounts, so these names create no relationship); and no `Payment` joins two accounts whose holders are both non-overlay ids. Otherwise exit 2, nothing written.
  2. The target is the base's instance: the default instance for synthetic profiles, `neo4j-real` for real profiles. This is the one exception to L17's rule that the real-data instance refuses synthetic records, and it holds only for profiles in `access.real_overlay_profiles` (exit 3 otherwise, before connecting) and after the real-data gate of M2.2.
  3. Every reference to a non-overlay id (account holders, and the payers and beneficiaries that are those holders) must resolve in the target, directly or through `:SourceRecord` (L13): `overlay_unresolved.cypher` counts the ones that do not, and a non-zero count stops the load (exit 1) before anything is written. For C1 R4 and R8 the base counts as part of the same load.
  4. `overlay_purge.cypher` then removes the previous overlay (every `:Entity` and `:Sanction` whose id starts with `syn-ov-`, with its relationships) and every `:Alert` and `:DetectionRun`.
  5. Nodes, then relationships, through the Phase 2 queries; the account holdings go through the resolving query of L13, so a holding of a merged record lands on its canonical node.
  6. After the load, I15 and I16 hold, and loading the same overlay twice leaves every count unchanged.
  7. A base load invalidates the overlay: on the real-data instance L9 removes every `:Entity`, the overlay's included; on the default instance a superseded base node takes its account holdings with it. `make load` therefore always loads the overlay after the base (M3.7), and an overlay is reloaded, never patched.
- **L19. Detection loads.** `neonradar detect run` on Neo4j (the default engine) writes the run folder first (`alerts.jsonl`, `summary.json`, `run.json`), then replaces the detection results on the instance it read; with `--engine memory` it writes the run folder only and opens no database (M3.2). The load: it deletes every `:Alert` and `:DetectionRun` (detections are a function of the graph; `--keep-previous` keeps them, for comparisons), then MERGEs the `:DetectionRun` with its 1.2.0 properties, the `:Alert` nodes with their two 1.2.0 properties, `FLAGS` and `PRODUCED`, as Phase 1 does. After the load I6 and I17 hold. On a real profile the alerts stay in the real-data instance and `data/cache/real/runs/`; what is printed and written to `data/cache/reports/` is the counts-only summary.

**Invariants added** (`graph/src/neonradar_graph/queries/verify_overlay.cypher`, verbatim in the code book under M3.1; `neonradar graph verify` runs them after I1 to I14 and prints one line each, from M3.4, because `graph verify` arrives with PHASE-2.md M2.11):

| Invariant | Check |
|---|---|
| I15 | The only relationship between a synthetic and a non-synthetic node is `HOLDS_ACCOUNT` from a non-synthetic `:Organization` to a synthetic `:Account` (the bridge rule; support nodes have no `synthetic` property and never count) |
| I16 | No `PAID` joins two accounts that are both held by non-synthetic entities |
| I17 | No `:Alert` names a non-synthetic person (a `:LegalEntity` that is not an `:Organization`) through `FLAGS` or among its `evidence_node_ids`, and no `:Alert` with `involves_real_entities` has a `PAID` among its `evidence_edge_ids` (G12) |

**What the detectors read.** Detection queries read only labels, types and properties defined in C2 (PHASE-1.md 5.2). The ones they read are listed in 7.1.2 and pinned by `test_graphrows.py`; all of them exist in 1.1.0 except `:Sanction.provisions`.

No migration: 1.2.0 adds no constraint and no index. The overlay purge seeks `syn-ov-` ids through the existing uniqueness constraints (a range index answers `STARTS WITH`).

### 5.3 C3 and C4: unchanged

C3 stays at 1.1.0: the Phase 1 alert list and detail endpoints read `:Alert` and its `payload` as before, and the run summary waits for Phase 4's complete API. C4 stays at 1.0.0: every Phase 3 alert validates against `contracts/schemas/alert.v1.json` (tested in M3.2 and in every detector milestone); `metrics` and subject roles are typology-defined and documented in each typology file and in 7.3, which C4 allows. `wording_class` keeps its C4 meaning; under R-REAL, every emitted alert that involves a real entity is a registry pattern about an organisation, worded with `headline_structural`.

### 5.4 Contract tests added

| Test file | Checks |
|---|---|
| `contracts/tests/test_graph_mapping.py` | `Sanction.provisions` maps to the `:Sanction` property `provisions`; the `:DetectionRun` properties of 5.2 appear in the mapping data or the C2 document's tables |
| `contracts/tests/test_versions.py` (or the Phase 1 file that checks versions) | `GRAPH_SCHEMA == "1.2.0"`, `CONTRACTS == "1.2.0"`, the other three unchanged; `contracts/CHANGELOG.md` has a 1.2.0 entry |
| `graph/tests/test_invariants.py` (integration) | I15 to I17 hold on the demo load, and each fails on a test-built violation (a `LINKED_TO` from a synthetic to a non-synthetic node built in test code; a payment between two accounts held by test look-alikes; for I17, an alert flagging a test look-alike person, an alert with a look-alike legal entity of unstated kind among its `evidence_node_ids`, and an alert with `involves_real_entities` and a `PAID` among its `evidence_edge_ids`), each in its own Testcontainers database; the statements run directly, because `graph verify` arrives with M2.11 |
| `graph/tests/test_overlay_load.py` (integration, M3.4) | L18 steps 1 to 6, including exit 2 on a doctored overlay record, exit 1 on an unresolved holder, a holding of a merged record landing on the canonical node, and a second load leaving every count unchanged |
| `detect/tests/test_detection_store.py` (integration, M3.2) | L19: two runs leave one `:DetectionRun` and the second run's alerts; the five new `:DetectionRun` properties and the two `:Alert` properties are set; `summary` parses as JSON |

---

## 6. Milestones

Each milestone below is one pull request unless it says otherwise. The header table gives the squad and human owner, the dependencies (by milestone id, all merged; `M2.x` ids are Phase 2 milestones), the branch, the labels, whether to plan first, whether it is a size exception (2.3), the ADR it drafts, and whether it has a real-data run. "The code book" means the milestone's section of `docs/build/PHASE-3-CODE.md`. Acceptance commands run on synthetic data.

### M3.0 Phase 3 handover and agent kit update

| | |
|---|---|
| Squad, human owner | Docs and agent kit; tech lead |
| Depends on | Gate 1, the seed pull request (1.4), M2.0 |
| Branch | `p3/m3-0-handover` |
| Labels | `agent`, `phase-3`, `squad:docs`, `size-exception` |
| Plan first | Yes |
| Size | exception (the code book script, its tests and two rule files are verbatim) |
| ADR | none |
| Real-data run | none |

**Goal.** Reconcile this spec with what Phases 1 and 2 built, install the code book script, and update the agent kit for alerts and the evaluation, so that every later session starts from the right facts and the right rules.

**Deliverables.**

1. `docs/build/phase-3-reconciliation.md`: one section per seam of 2.10 and per item of 0.6, each saying what the repository has today (file, class or function, signature, the fields of a model, the options of a command), and what the milestone that adapts it will do. Record what Phase 1 and the Phase 2 milestones merged by now have built; for a seam that a Phase 2 milestone still has to build (M2.1a's validator, M2.2's profile model and layout functions, M2.11's mapping and loader), write "pending M2.x" and the Phase 3 milestone that checks it again (2.2 step 2). Find the facts by reading code and by running read-only commands on synthetic data, for example: the fields of `TypologyFile` and the signature of `load_catalog()`; Phase 1's `render_headline` and run logic, every caller of them, and the Phase 1 tests that cover them; `contracts/tests/test_wording.py` and `contracts/tests/test_alert.py`, and whether they would accept the Phase 3 typology files (placeholder filters such as `{total_amount|money}`, `wording.variants`, `wording.detail`) and alerts (if not, M3.1 changes those tests, 5.0); the C4 `Alert` model's type for `metrics` values (Phase 3 writes numbers, strings and booleans) and its `run_id` pattern; the name and signature of the wording lint function; `uv run neonradar graph load --help` and `uv run neonradar detect run --help`; the functions of the Phase 1 name modules (`names.py`, `companies.py`) and whether Phase 2's `variants.py` (M2.9) exists yet; where Phase 1 writes `alerts.jsonl` and the queries that load `:Alert` and `:DetectionRun`; the integration-test fixture that starts Neo4j; the project model (`neonradar_ingest.data.project`) if M2.2 has merged. Where a fact differs from this spec, write the difference and its classification: mechanical (the adapting milestone records it as a deviation, 2.2 step 6b) or behavioural (stop and ask, 2.5).
2. `scripts/spec_extract.py` and `scripts/tests/test_spec_extract.py`, verbatim from the code book. The script cannot copy itself before it exists: take its two blocks out of the code book once by hand (a few lines of Python that cut the file at its headings will do), then run `check` to prove the copy. Makefile target `spec-check` (`uv run python scripts/spec_extract.py check --milestone $(M)`). `docs/build/phase-3-deviations.json` with `{}` (the record of mechanical deviations, 2.2 step 6b). The tests run in CI's `python` job with the other tests under `scripts/tests/`.
3. `.claude/rules/detect.md` and `.claude/rules/synth.md`, verbatim from the code book. Each starts with `paths:` frontmatter.
4. `CLAUDE.md`: insert each of the four blocks below verbatim after the matching Phase 2 block (its "Non-negotiable rules", "Commands", "Layout" and "Known traps" additions), and change the line that names the current phase spec so that it names `docs/build/PHASE-2.md` and `docs/build/PHASE-3.md`. The file must stay under Phase 1's line limit; shorten Phase 1 or Phase 2 lines that 2.1 now covers if needed, and say which in the pull request.
5. `.claude/hooks/guard_real_data.py`:
   - add `neonradar eval run` with `--split test` (in any position, with `=` or a space) to the human-only commands, in the same way the hook blocks `neonradar er label`;
   - add `data/cache/holdout` to the protected paths, in the same way as `data/cache/real` (the Read, Grep and Glob tools, shell commands that name it, relative and absolute paths): the holdout run writes there (M3.6, G11);
   - eight cases in `scripts/tests/test_guard_real_data.py`: blocked `uv run neonradar eval run --split test`, `neonradar eval run --split=test --engine neo4j`, `uv run neonradar eval run --seeds 3 --split test`, a `Read` of `data/cache/holdout/eval-test-x/report.md`, and `ls data/cache/holdout`; allowed `uv run neonradar eval run --split dev`, `uv run neonradar eval check` and a `Read` of `data/cache/synthetic/eval/eval-dev-x/report.md`. The line in `scripts/test_hooks.sh` that prints the hook's case count gets the new count.
6. The `/milestone` skill (`.claude/skills/milestone/SKILL.md`, PHASE-1.md M1.2): for an `M3.x` id it reads `docs/build/PHASE-3.md` and the matching section of the code book, and its steps include 2.2 steps 4a, 6b and 6c.
7. `docs/build/project.yaml`: merge the keys of 1.3 into the existing mappings with the defaults shown (never a second top-level key). The project model (`neonradar_ingest.data.project.Project`, M2.2; if M2.2 has not merged when M3.0 runs, record it in the reconciliation, and M3.3, the first Phase 3 milestone that depends on M2.2, does this as its deliverable 7) gains `access.real_overlay_profiles`, `access.real_registry_alerts`, `people.freeze_deciders` and the five `schedule` dates, with unit tests, so that later milestones read them through the model. `docs/build/PROGRESS.md`: one `todo` row for each of M3.0 to M3.13, with M3.4-1, M3.4-2 and M3.5a to M3.5f as separate rows.
8. Labels in `.github/labels.yml`, synced with `uv run --no-project --with pyyaml python scripts/sync_labels.py` (PHASE-1.md M1.1; `phase-3` and `typology` are there from Phase 1): `{ name: eval, color: "5319e7", description: "Detection evaluation" }`, `{ name: assignment-4, color: "fbca04", description: "Assignment 4 test cases" }`, `{ name: docs, color: "0075ca", description: "Documentation" }` (if missing) and `{ name: freeze-change, color: "b60205", description: "Changes what eval/freeze.json pins" }`. CODEOWNERS rows of 4.3 through `scripts/generate_codeowners.py`.
9. `.github/dependabot.yml`: a `generator` group holding `numpy` and `faker`, excluded from the group of all other Python updates, so their upgrades arrive alone (3.1). `.github/pr-size-exclude.txt`: `docs/build/PHASE-3-CODE.md` (if the seed pull request did not add it) and `eval/baselines/*.json`.
10. Pins: `numpy==2.5.*` in `ingest/pyproject.toml` (replacing Phase 1's unpinned `numpy`) and PyYAML as 3.1 says; `uv lock`.
11. `.claude/settings.json` (edit, keep everything else), as PHASE-2.md M2.0 did for `p2/*`: add to `allow` `"Bash(git push -u origin p3/*)"`, `"Bash(git push origin p3/*)"` and `WebFetch` entries for the documentation hosts of 2.7 (`www.ecfr.gov`, `www.fincen.gov`, `bsaaml.ffiec.gov`, `www.ffiec.gov`, `www.fca.org.uk`, `www.handbook.fca.org.uk`, `www.ukfinance.org.uk`, `www.wearepay.uk`, `www.ons.gov.uk`, `www.bankofengland.co.uk`, `egmontgroup.org`, `www.europol.europa.eu`, `wolfsberg-group.org`, `numpy.org`, `arxiv.org`); add to `deny` `"Read(./data/cache/holdout/**)"`.

**`CLAUDE.md` additions** (verbatim):

```markdown
## Non-negotiable rules (Phase 3 additions)

- G11: never run `neonradar eval run --split test`, never choose holdout seeds, never generate
  or open a holdout world or anything under data/cache/holdout/; never edit a verbatim test,
  `eval/baselines/ci.json` or `eval/freeze.json` to make a check pass.
- G12 (R-REAL): no payment-based alert involves a real entity, and no alert names a real
  person as subject or in evidence; such findings are withheld and counted only.
- Verbatim files come from docs/build/PHASE-3-CODE.md through scripts/spec_extract.py.
- No scenario touches a base entity, and base people never get accounts or payments (G1).
```

```markdown
## Commands (Phase 3 additions; each works once the milestone in brackets has merged)

- `uv run python scripts/spec_extract.py check --milestone M3.x` and `update --path FILE` (M3.0)
- `uv run neonradar synth world --profile synth-eval --seed 1` and `synth overlay` (M3.3)
- `uv run neonradar graph load --profile synth-eval --overlay latest` (M3.4)
- `uv run neonradar detect run --profile synth-eval` (M3.2; synthetic profiles from M3.3, real ones from M3.4)
- `NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -m "not integration"` (M3.2)
- `uv run neonradar eval check` and `uv run neonradar eval run --split dev --seeds 1-5` (M3.6)
- `make load PROFILE=synth-demo` (M3.7) and `make demo` (M3.8)
```

```markdown
## Layout (Phase 3 additions)

- detect/src/neonradar_detect/: source.py (candidate steps), memsource.py (the oracle),
  neo4jsource.py and queries/ (one file per step), detectors/, evaluation/
- ingest/src/neonradar_ingest/synth/: generator v1 (world.py, overlay.py, scenarios/)
- eval/: seeds.yaml, baselines/ci.json, freeze.json
```

```markdown
## Known traps (Phase 3, verified 18 Oct 2026)

- A Cypher 5 path pattern cannot compare a hop with the previous one: expand one hop per query.
- ORDER BY a C2 id before every LIMIT; durations do not compare; name :Entity in id lookups.
- GDS: stream only, concurrency 4, drop projections in finally; no graphdatascience client.
- Detector queries run as session.run(neo4j.Query(text, timeout)), never in execute_read.
- numpy streams change between numpy minor versions: a numpy bump must pass eval check.
- Generator payments are C1 lines (Ctx.payments); read one with Ctx.record(id).
```

**Acceptance.**

```bash
uv run python scripts/spec_extract.py list | tail -n 3          # files of the last milestones
uv run python scripts/spec_extract.py check --milestone M3.0    # 4 of 4 verbatim files match the code book, 0 recorded deviations
uv run pytest scripts/tests/test_spec_extract.py -q             # 8 passed
bash scripts/test_hooks.sh                                      # includes the eight new cases
uv run --no-project --with pyyaml python scripts/sync_labels.py && gh label list --search freeze-change   # the labels exist
make check
```

**Review focus (humans).** Tech lead: does the reconciliation give the real names and signatures for every seam that exists today, and say "pending M2.x" for the rest? Change one character of a copied file and run `make spec-check M=M3.0`: does it fail and name the file? Data steward: ask the agent, in a new session, to run `uv run neonradar eval run --split test`, and to read a file under `data/cache/holdout/`: is each blocked?

### M3.1 C2 1.2.0: overlays, bridge invariants and detection runs

| | |
|---|---|
| Squad, human owner | Graph and ER; tech lead (the data steward approves L18) |
| Depends on | M3.0, M2.1c (and the tag `contracts-v1.1.0`, 5.0) |
| Branch | `p3/m3-1-c2-1-2-0` |
| Labels | `agent`, `phase-3`, `squad:graph`, `contract-change` |
| Plan first | No |
| Size | normal |
| ADR | none (ADR-0021 records the real-data rule, M3.10) |
| Real-data run | none |

Run it in a contract-change session (1.5, 5.0), after the issue is approved.

**Goal.** C2 says what an overlay load may do, which relationships may join synthetic and real nodes, and what a detection run records, before any loader or detector depends on it.

**Deliverables.**

1. `contracts/C2-graph.md` and the graph mapping data: everything in 5.2 (the node property tables, L18 and L19, I15 to I17), version 1.2.0. The mapping maps FtM `Sanction.provisions` to the `:Sanction` property `provisions`; `neonradar_graph.mapping` sets it (a list, empty when absent). If PHASE-2.md M2.11 is still open, it rewrites the same module: keep the change to one place, and the later of the two merges `origin/main` as usual.
2. `contracts/CHANGELOG.md` entry for 1.2.0; `neonradar_contracts.versions`: `GRAPH_SCHEMA = "1.2.0"`, `CONTRACTS = "1.2.0"`.
3. `graph/src/neonradar_graph/queries/verify_overlay.cypher`, verbatim from the code book. `neonradar graph verify` arrives with PHASE-2.md M2.11, so this milestone only adds the file and its tests; M3.4 adds its three statements to `graph verify` (and `--real`).
4. Tests of 5.4 that belong here: the mapping and version tests (contract marker), and `graph/tests/test_invariants.py` extended with I15 to I17, which run the three statements directly, each also shown to fail on a test-built violation (for I17, the three cases of 5.4). The look-alike records for those cases are built in the test code at run time (2.9), and the violating nodes and relationships are written with a test-only Cypher statement in the test, never through the loader.
5. Only if the M3.0 reconciliation says so: `contracts/tests/test_wording.py` and `contracts/tests/test_alert.py` changed, test-only, so that they accept the Phase 3 typology files (placeholder filters, `wording.variants`, `wording.detail`) and alerts (metric values that are strings or booleans). The issue text (5.0) names this item; nothing else under `contracts/**` changes.
6. No migration file: 1.2.0 changes no constraint or index (`graph/tests/test_migrations.py` still expects 23 constraints and 9 indexes).

**Acceptance.**

```bash
make contracts && git diff --exit-code contracts/schemas/           # schemas unchanged (C2 only)
make cypher-lint                                                    # verify_overlay.cypher: 3 statements, 0 problems
uv run pytest -m contract contracts/tests/ -q
uv run pytest -m integration graph/tests/test_invariants.py graph/tests/test_migrations.py
make contracts-check && make check
```

**Review focus (humans).** Tech lead: read I15. Is there any relationship a real-data load could legitimately create between a synthetic and a non-synthetic node, other than an account holding? (A `POSSIBLY_SAME_AS` cannot, by I10.) Data steward: read L18 step 2. Is the condition for loading synthetic records into `neo4j-real` narrow enough, and does `access.real_overlay_profiles` say what you want to allow?

### M3.2 Detection core and `circular_flow` 0.2.0

| | |
|---|---|
| Squad, human owner | Typologies and Detection; detect mentor (a typology researcher reviews `circular_flow`) |
| Depends on | M3.0, M3.1, M3.3, M2.1a |
| Branch | `p3/m3-2-detection-core` |
| Labels | `agent`, `phase-3`, `squad:detect`, `typology`, `size-exception` |
| Plan first | Yes |
| Size | exception (the detection core, 33 query files, the `circular_flow` detector and their tests are verbatim) |
| ADR | ADR-0020 (detector design) |
| Real-data run | none |

**Goal.** Every detector runs on one tested core: candidate steps behind a `Source` interface with a Cypher implementation and an in-memory oracle, the R-REAL rule, C4 alerts and their wording, and the runner. `circular_flow` 0.2.0 replaces the Phase 1 detector, and `neonradar detect run` keeps working on `demo-mini`.

**Deliverables.**

1. **Verbatim files** (the code book, M3.2): in `detect/src/neonradar_detect/`, `model.py`, `rows.py`, `source.py`, `memgraph.py`, `graphrows.py`, `memsource.py`, `neo4jsource.py`, `expand.py`, `policy.py`, `alerts.py`, `wording.py`, `runner.py` and `detectors/circular_flow.py`; the 33 files of `queries/`; `detect/typologies/circular_flow.yaml` (2.10 says which three lines stay the repository's); in `detect/tests/`, `kit.py`, `test_alert_builder.py`, `test_detector_circular_flow.py`, `test_graphrows.py` and `test_detector_queries.py`. The verbatim `wording.py` replaces Phase 1's; Phase 1's `render_headline` stays as a thin wrapper over `wording.render_template(wording.templates(typology, "")[key], metrics)`, so its callers and tests (the reconciliation lists them) keep working; if a Phase 1 test depends on a formatting detail the new code does not reproduce, that is a behavioural difference (2.5 item 5). The verbatim `runner.py` replaces Phase 1's run logic; Phase 1's file writing and alert loading stay (deliverable 5), and so do Phase 1's tests of them. Phase 1's `queries/circular_flow.cypher` (the unanchored pattern, decision 6) is no longer used: delete it, so that `queries/` holds the 33 files.
2. **`graphrows.py`** is verbatim: the oracle's own reading of C1 records into the C2 labels and properties of 7.1.2, one node per record (no entity resolution, so the memory engine is for synthetic data). It does not call `neonradar_graph.mapping`, so that the oracle is an independent implementation: deliverable 7's Neo4j mode loads the same records with the project's loader and runs every detector test again, and M3.6's world parity test compares the two on a generated world (7.1.5). `test_graphrows.py` must pass unchanged; when the Neo4j mode shows that the loader writes a 7.1.2 property differently, find which side departs from C2, fix it, and record it (7.1.5).
3. **`catalog.py`** (reference): extend Phase 1's `TypologyFile` with `shape_name` (required when `detector` is set; it must pass the wording lint), the optional `wording.variants` (variant name to a pair of `headline_structural` and `headline_synthetic`, with the same placeholder rules as the main pair) and the optional `wording.detail` (a template for the summary, 7.5.2); `load()` validates every file with `TypologyFile` and returns the reference's frozen `Typology` view for each; `params_for` as in the reference. Two Phase 1 rules widen: a parameter may give only a `default` (booleans, strings and lists have no bounds), and the placeholder rule accepts the filters of 7.5.2 (`{name|money}`, `{name|pct}`, `{name|n:noun}`), checking the name before the bar against `metrics`. A typology without a detector (`trade_based_ml`) still loads.
4. **`wording_lint.py`** (reference): `violations(text, masked)` masks the given captions (longest first) and returns the patterns of Phase 1's lint that still match, by calling Phase 1's function on `contracts/wording/forbidden-terms.txt`; it adds the reference's `PHRASES` (Phase 2) and `CONDUCT` (Phase 3) as they are. `wording.render` calls it on every text it renders and raises `WordingError` on a match, so a run never emits text that names conduct (G5; PHASE-1.md M1.9b's run-time check).
5. **Detection store and CLI** (C2 L19):
   - `neonradar detect run [--profile NAME] [--typology SLUG]... [--run-id ID] [--engine neo4j|memory] [--window START END] [--keep-previous]`. The `Source` is `Neo4jSource(driver, database, timeout_s=600)` on the profile's instance (the default instance without a profile; a real profile goes through the M2.2 gate first), or, with `--engine memory`, `MemSource(graphrows.from_records(records))` over the profile's record folders (base and overlay), or over `data/fixtures/demo-mini/` without a profile. The memory engine refuses (exit 2) a real profile and a profile whose resolution is enabled, because the oracle does not merge records. The parameters are `catalog.params_for(typology, module, overrides)` with the profile's `detection.overrides`. The window is `--window`, else the profile's `detection.window` (`overlay`: the period in the latest `overlay.json`; `data`: the `PAID` time range), else Phase 1's behaviour, the `PAID` time range (`Source.paid_time_range()`). The synthetic profiles have both blocks from M3.3, a dependency of this milestone, so this milestone reads them for every profile that has them; M3.4 adds the blocks to the Phase 2 profiles and the real-profile path. `query_sha256` of a typology is the SHA-256 of the texts of its module's `QUERIES` files, in that order, joined with a newline. `real_registry_alerts` is `access.real_registry_alerts`.
   - A `WordingError` from the runner stops the run with exit 1, naming the typology, the part and the pattern (never the text). Every alert is validated with `neonradar_contracts.alert.Alert` before anything is written (exit 1 on a failure, naming the alert's typology and the field, never its values). Then the run folder (`runs_dir(profile, run_id)` from M3.4, Phase 1's `data/runs/<run_id>/` before it or without a profile): `alerts.jsonl` (one alert per line, sorted keys), `summary.json` (the runner's summary) and `run.json` (Phase 1's fields plus `profile`, `params_sha256`, `window`, `engine`), and, last, `LATEST` in the folder above it with the run id (Phase 1's runs folder gets one too). With `--engine neo4j`, the L19 load follows: delete the previous `:Alert` and `:DetectionRun` (unless `--keep-previous`) and MERGE the new ones, with the five `:DetectionRun` properties and the two `:Alert` properties of 5.2. With `--engine memory`, the run folder is the whole output: no database is opened, because the records it read need not be loaded anywhere, so its alerts' evidence would not be in the graph (`verify-alert` checks Neo4j runs).
   - The printed summary: per typology the findings, alerts, duplicates and withheld counts; on a real profile, counts only (the run folder stays under `data/cache/real/runs/`).
   - `neonradar detect list`: Phase 1's table plus each typology's tier, version and whether its detector exists.
   - `neonradar detect verify-alert (ALERT_ID | --run RUN_ID | --run latest) [--profile NAME]`: for one alert, or every alert of a run, reads the `payload`, runs `queries/evidence.cypher` with its node and edge ids, and exits 1 unless every evidence node and relationship exists.
6. **Phase 1's `circular_flow` fixture test**: cases A to E keep their expectations (A and B found, C, D and E not) on Neo4j. Case F moves to memory: it mixes a non-synthetic holder with synthetic accounts, and PHASE-2.md M2.11's rule L17 refuses any load that mixes the two on either instance, so the integration test can no longer load it. `test_alert_builder.py::test_r_real_withholds_activity_on_a_real_entity` is case F under R-REAL (no alert, `withheld.activity_on_real == 1`, decision 3): remove case F from the integration test in the same commit and say so in the pull request (this is the spec's change, not a weakened test; if M2.11 already handled case F, keep what it did and record it). On `demo-mini`, the labelled `round_trip` scenario is still found (Phase 1 M1.9b deliverable 6).
7. **Tests on Neo4j** (references `conftest.py` and `neo4j_mode.py`): merge the conftest additions into Phase 1's `detect/tests/conftest.py`, and adapt `neo4j_mode.py` to the project's Testcontainers fixture and loader. Then `NR_DETECT_SOURCE=neo4j` runs every detector test on a test database; a test whose records are not all synthetic is skipped in that mode, because L17 refuses them, and its in-memory run covers it. CI's `integration` job runs this mode on every pull request (M1.6's job; add the step).
8. **New tests written in this milestone**: `detect/tests/test_alert_contract.py` (every alert the runner builds in `test_alert_builder.py`'s cases, and every alert of a small generated world run in memory, validates against `neonradar_contracts.alert.Alert`, and `wording_class` is `synthetic_scenario` exactly when `involves_real_entities` is false); `detect/tests/test_detection_store.py` (integration, L19 as 5.4 describes); `detect/tests/test_query_plans.py` from the reference, with `neo4j_driver_with_world` loading a small world and overlay made with M3.3's `world.generate` and `overlay.generate` (80 companies, 120 people, one scenario and one look-alike per typology, seed 5: the settings M3.6's `test_world_parity.py` uses).
9. `docs/decisions/0020-detector-design.md` (status `proposed`; deciders: detect mentor and tech lead): candidate steps in bounded Cypher with the typology logic in Python; one hop per query for payment paths, because Cypher 5 cannot prune on the previous hop (3.2); an in-memory oracle behind the same interface and the same tests run on both; R-REAL applied in the runner on every instance; alert ids and evidence queries make every alert checkable (`verify-alert`). Cite `detection-cypher-gds.md` 0 and 2.17.

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.2      # every verbatim file matches
uv run pytest detect/tests -q -m "not integration"               # the oracle: the 14 verbatim tests and the new ones pass
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests -q -m "not integration"   # the same tests on Neo4j
make cypher-lint                                                  # 0 problems (the 33 detection files hold 40 statements)
make up && uv run neonradar graph migrate && uv run neonradar graph load data/fixtures/demo-mini/ --strict
uv run neonradar detect run --typology circular_flow              # the round_trip alert
uv run neonradar detect run --typology circular_flow              # the same alert ids
uv run neonradar detect verify-alert --run latest                 # every evidence node and relationship exists
uv run pytest detect/tests/test_alert_contract.py -q              # every alert validates against C4
uv run pytest -m integration detect/tests                         # Phase 1 fixture (cases A to E), store, query plans
make check && make hygiene
```

**Review focus (humans).** Detect mentor: pick two `Source` methods and read `memsource.py` beside the query file: same rows, same order, same limits? Typology researcher: read 7.3.4 and `test_detector_circular_flow.py`. Is a payment straight back to the sender rightly not a cycle? Open the `demo-mini` alert in Neo4j Browser with its evidence query: does the picture match the explanation steps?

### M3.3 Generator v1: world, overlay, scenarios and labels

| | |
|---|---|
| Squad, human owner | Ingestion; ingest mentor (the data steward reviews G1, the bridge rule and the names; a typology researcher reviews the scenarios) |
| Depends on | M3.0, M2.1a, M2.2 |
| Branch | `p3/m3-3-generator-v1` |
| Labels | `agent`, `phase-3`, `squad:ingest`, `size-exception` |
| Plan first | Yes |
| Size | exception (the generator, its fourteen scenario modules, three profiles and their tests are verbatim) |
| ADR | ADR-0023 (generator v1 and its look-alikes) |
| Real-data run | none |

**Goal.** One generator makes the synthetic register and the overlay for any base, with the same bytes for the same seed and base; no scenario can touch a base entity; every planted scenario and look-alike is labelled outside the records.

**Deliverables.**

1. **Verbatim files** (the code book, M3.3): in `ingest/src/neonradar_ingest/synth/`, `streams.py`, `dates.py`, `records.py`, `ctx.py`, `base.py`, `background.py`, `world.py`, `overlay.py`, `labels.py`, `writer.py`, and `scenarios/` (`__init__.py`, `common.py` and one module per typology); `ingest/tests/test_synth_v1.py` and `ingest/tests/names_simple.py` (and merge the two lines of the reference `ingest/tests/conftest.py` into the ingest tests' conftest, because the helpers sit next to the tests); `ingest/profiles/synth-eval.yaml`, `synth-demo.yaml` and `synth-scale.yaml`. Generator v0 (`rng.py`, `names.py`, `companies.py`, `registry.py`, `activity.py`) stays, and `neonradar synth demo-mini` keeps producing the committed `demo-mini` fixture byte for byte.
2. **`namesource.py`** (reference): `default_names()` returns an object with the five methods of `ctx.NameSource`, built on the Phase 1 modules: `person(rng, locale)` gives every spelling of one invented person's name and a gender, for the locales `en_GB`, `ar_SA` and `ru_RU`, with honorifics stripped and the denylist applied (PHASE-1.md 7.1); `invented_person(rng, locale)` the same with an invented surname from Phase 2's syllable table (`variants.py`, PHASE-2.md M2.9: two or three invented syllables in the person's script, redrawn while the result is on the denylist or in the surname lists of the three Faker locales), for people on synthetic lists, PEP personas and their relatives and associates (if M2.9 has not merged, use the reference's table and record it in the reconciliation); `company(rng, jurisdiction)` gives a neutral-word name with the jurisdiction's legal form; `street(rng)` and `town(rng)`. Every method draws only from the generator it is given (seed Faker per call with `fake.seed_instance(int(rng.integers(0, 2**31)))`), so names never move a structural draw. The company space must hold at least 1,000,000 distinct names before the legal form, because the scale world needs about 160,000 (7.2.3); if Phase 1's word lists give fewer, add neutral words in `namesource.py` itself, never in Phase 1's `companies.py` (generator v0 draws from those lists, and `demo-mini` must not change), and never real company names. The verbatim test `test_names_never_move_a_structural_draw` must pass with this adapter.
3. **Profiles** (M2.2's model, extended): the profile model accepts `sources.nr_synthetic.world` (the fields of `world.WorldConfig`, plus `name` and `seed`) and the top-level `overlay` and `detection` blocks of 7.11, and still fails on unknown keys; `resolution.config` becomes optional when `resolution.enabled` is false, and `overlay.typologies: all` means every typology in `overlay.SCENARIOS`. For a synthetic profile with a world block, `Profile.record_dirs(seed=None)` is the world's folder for that seed (the profile's `world.seed` by default; `worlds_dir(name, seed)`, 4.5), the profile's base; when the folder holds no records, the commands that need it stop with exit 2 and the message "no world for seed N: run `neonradar synth world --profile NAME --seed N` first". Layout functions of 4.5 that this milestone needs: `worlds_dir`, `overlay_dir`, `latest_overlay`, `eval_dir` and `holdout_dir` (M3.6 uses the last two; the real-profile ones come in M3.4).
4. **CLI.**
   - `neonradar synth world --profile NAME [--seed N] [--out DIR]`: `world.generate(seed, WorldConfig(...), default_names())`; every record validated with Phase 1's `validate_record(data)`, and the records together with `validate_batch(records, strict=True)` (R4, R8); written with `writer.write_part(dir, "nr_synthetic-<today>-world", writer.items(records), seed=..., git_sha=...)`, where `<today>` is the world's `today` as `yyyymmdd`, never the clock, so the file name and the manifest are the same on every day; a summary with the counts by schema.
   - `neonradar synth overlay --profile NAME [--seed N] [--base DIR] [--out DIR]` for synthetic profiles: reads the base's record files (`--base`, or `Profile.record_dirs(seed)`) line by line (never all at once), the dataset kinds from `contracts/datasets.yaml` (`kind`, C1 1.1.0) and, when the profile has a resolution run, its `canonical.csv`, which it passes on: `overlay.generate(base_records, kinds, OverlayConfig(...), default_names(), canonical_csv)`. It validates every overlay record with `validate_record` and the overlay's records with `validate_batch(records, strict=True)`, then drops the R4 and R8 issues that the base resolves (L18's rule: the base counts as part of the same load): an R4 issue whose missing id is a base id, and an R8 issue whose account's holder is a base `LegalEntity`, both looked up in an index of the base's ids and schemas built while reading the base (a set of strings, never the base's records; the validator under `contracts/` does not change). Any other issue stops it with exit 1. It writes the records (`writer.write_part(..., ov.items(), ...)`), `labels/` (`labels.write(dir, labels.files(...))`, with the records file's SHA-256) and `overlay.json` (4.5): with `--out`, into that folder itself and nothing else; without it, into `overlay_dir(profile, overlay_id)` and, last, `LATEST` in the folder above. Real profiles come in M3.4: here a real profile stops with exit 3 before reading anything.
   - The world seed and the overlay seed are the profile's (`world.seed`; `overlay.seed`, null meaning the world's), `--seed` overriding both; output under `data/cache/synthetic/` unless `--out`. A holdout seed (one of `eval/seeds.yaml`'s `test.seeds`, once M3.11 has written them) is refused by both commands with exit 2: a holdout world is generated only inside `neonradar eval run --split test`, which a human runs (G11). The overlay has no `--split` option.
5. **New tests** written in this milestone: `ingest/tests/test_synth_namesource.py` (the denylist holds over 10,000 person draws in each locale; over 10,000 `invented_person` draws in each locale give no surname of the Faker locales or the denylist; the same generator state gives the same name; 200,000 company draws give at least 190,000 distinct names); `ingest/tests/test_synth_cli.py` (world and overlay of `synth-demo` twice with the same seed into `tmp_path`: identical record files and label files; strict validation passes, including the base-resolved R4 and R8 issues; `labels/manifest.json` holds the records file's SHA-256; an overlay without a world stops with exit 2; a holdout seed listed in a test `seeds.yaml` is refused with exit 2; a world with `companies: 30` and the profile's other settings runs in under 30 seconds).
6. `docs/decisions/0023-generator-v1.md` (status `proposed`; deciders: ingest mentor, data steward, a typology researcher): a world and an overlay for any base, because real profiles need the same overlay; named streams, with names on streams of their own; plain background on base organisations and look-alikes planted beside every typology, because a detector that only meets illicit shapes cannot show its false positives; labels v2 outside the records; no external generator (AMLSim unmaintained, AMLworld and SAML-D data only, AMLGentex not installable on Python 3.14). Cite `synthetic-transactions.md` 0 and 1.
7. **The project model keys, if M3.0 could not add them** (the reconciliation says so when M2.2 had not merged then): M3.0 deliverable 7's keys and their unit tests, here, before anything reads them.

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.3
uv run pytest ingest/tests/test_synth_v1.py ingest/tests/test_synth_namesource.py ingest/tests/test_synth_cli.py -q
uv run neonradar synth world --profile synth-eval --seed 1            # the profile's own folder (4.5)
uv run neonradar synth world --profile synth-eval --seed 1 --out /tmp/w1
uv run neonradar synth world --profile synth-eval --seed 1 --out /tmp/w2
diff /tmp/w1/*.ftm.jsonl /tmp/w2/*.ftm.jsonl && echo deterministic        # about 4,200 records
uv run neonradar synth overlay --profile synth-eval --seed 1 --base /tmp/w1 --out /tmp/o1
PYTHONHASHSEED=7 uv run neonradar synth overlay --profile synth-eval --seed 1 --out /tmp/o2
diff /tmp/o1/*.ftm.jsonl /tmp/o2/*.ftm.jsonl && diff -r /tmp/o1/labels /tmp/o2/labels && echo deterministic
uv run neonradar contracts validate-records /tmp/w1/*.ftm.jsonl /tmp/o1/*.ftm.jsonl --strict   # about 379,000 records
uv run neonradar synth demo-mini --seed 20261023 --out /tmp/dm && diff /tmp/dm/*.ftm.jsonl data/fixtures/demo-mini/*.ftm.jsonl
make check && make hygiene
```

The world of `synth-eval` seed 1 holds about 4,200 records and its overlay about 375,000 (355,090 payments, 140 scenarios and 140 look-alikes); generation takes about 20 seconds on a 2-core machine (7.2.9).

**Review focus (humans).** Data steward: read `ScenarioCtx` in `ctx.py` and `check_bridge` in `overlay.py`. Is there any path by which a scenario reaches a base entity, or a base person gets an account? Read 20 generated names from `/tmp/o1`, including the people on the synthetic lists and the PEP personas: any real person or company, or a realistic full name on a list? Ingest mentor: change `default_names()` to `SimpleNames` in a scratch branch and diff the overlays: only names may differ. Typology researcher: read two scenario modules against 7.2.5 and their typology's 7.3 section: do the look-alikes look like what the sources call ordinary activity?

### M3.4 Overlay loading and real profiles

| | |
|---|---|
| Squad, human owner | Graph and ER with Ingestion; graph mentor (the data steward reviews the real-data handling and the real-data run) |
| Depends on | M3.2 (and through it M3.1 and M3.3), M2.2, M2.11 |
| Branch | `p3/m3-4-1-overlay-load`, then `p3/m3-4-2-real-profiles` |
| Labels | `agent`, `phase-3`, `squad:graph`, `squad:ingest`, `real-data-run` |
| Plan first | Yes |
| Size | normal, split in two (2.3): M3.4-1 is the loader and its CLI with the `graph verify` wiring (deliverables 1 and 2, and the integration tests of deliverable 5); M3.4-2 is real profiles in `synth overlay`, the profile blocks, the remaining layout functions, `detect run --profile` on every profile, ADR-0021 and the real-data run (deliverables 3, 4 and 6, and the unit tests of deliverable 5), and carries `real-data-run`. Each part has its own acceptance list |
| ADR | ADR-0021 (the synthetic overlay and the real-data detection rule) |
| Real-data run | the `uk-tiny` overlay (a Gate 2 item, 8.1) |

**Goal.** An overlay loads onto its base in the base's instance, synthetic or real, under C2 L18; real profiles get an overlay only where the data steward allows it; detection reads its window and parameters from the profile.

**Deliverables.**

1. **L18 in the graph loader** (`neonradar_graph.loader`): an overlay mode for `load(...)` (or a separate `load_overlay(...)`, as the reconciliation decides) that performs L18 steps 1 to 6 in order: the record checks and the bridge check before connecting (exit 2), the instance choice with the L17 exception for profiles in `access.real_overlay_profiles` (exit 3 otherwise), `overlay_unresolved.cypher` (exit 1 on any unresolved reference), `overlay_purge.cypher` through `session.run()` (it uses `CALL { } IN TRANSACTIONS`), then nodes and relationships through Phase 2's queries, the account holdings through the resolving query of L13. Both query files are verbatim from the code book. `LoadReport` adds: overlay records loaded, previous overlay nodes removed, references resolved through `:SourceRecord`, detection results removed.
2. **CLI**: `neonradar graph load --overlay DIR` and `neonradar graph load --profile NAME --overlay latest` (the folder `latest_overlay(profile)` names). On a real profile the command first runs the real-data gate of M2.2 and prints counts only. The CLI passes `access.real_overlay_profiles` to the loader as an argument and keeps the gate itself, as PHASE-2.md M2.11 does, so the loader's tests can run in CI, where the gate always refuses. `neonradar graph verify` (and `--real`) runs the three statements of `verify_overlay.cypher` after I1 to I14, one line per invariant with its violation count (exit 1 on any).
3. **Real profiles in `synth overlay`**: first the real-data gate of M2.2 (an approved machine, the profile in `access.real_data_profiles`, `access.data_protection_filed`; 7.7 rule 1), then the profile must be in `access.real_overlay_profiles`: either fails with exit 3 before any record is read. The base is the profile's record folders and its latest resolution run, passed to `overlay.generate` as `canonical_csv` (so a merged entity gets one account, through its anchor record, and none when any of its records is flagged or comes from a list or a leak); output under `data/cache/real/overlay/<profile>/` (4.5); the summary is counts only (eligible and active organisations, skipped by reason, accounts, payments, scenarios and look-alikes by typology). `labels/` are written as for synthetic profiles: they name only `syn-ov-` ids.
4. **Profiles**: the overlay and detection blocks of 7.11 merged into `ingest/profiles/demo.yaml`, `uk-tiny.yaml` and `uk-sample.yaml` (the data steward approves them in review). The remaining layout functions of 4.5 (`runs_dir`, `latest_detection_run`). `neonradar detect run --profile NAME`, which reads `detection.window` and `detection.overrides` since M3.2, now works for these profiles too, writes under `runs_dir(profile, run_id)`, and on a real profile prints counts only.
5. **Tests** (synthetic only; integration tests in their own Testcontainers databases):
   - `graph/tests/test_overlay_load.py` (integration): the cases of 5.4 for L18, on the world and overlay of `synth-demo` with `companies: 40`; the overlay on a resolved Phase 2 demo load, where a holding of a merged record lands on the canonical node; an overlay load into a second container started like `neo4j-real`, loaded with test look-alike records (registry companies, a person, a legal entity of unstated kind) as `Instance.REAL`, succeeds only with the profile in the list passed to the loader, and leaves I15 and I16 at zero. Then detection runs on that container through `Neo4jSource`: the withheld counts are above zero, no alert names a look-alike person or legal entity of unstated kind, no alert on a look-alike rests on a payment, and I17 is zero (R-REAL on Neo4j, which the detector tests cannot reach because L17 refuses mixed loads).
   - `graph/tests/test_invariants.py` (integration): `graph verify` prints I15 to I17 after I1 to I14.
   - `cli/tests/test_overlay_cli.py` (unit): `synth overlay --profile uk-tiny` stops with exit 3 before reading a record when the machine is not approved, and when the profile is not in `access.real_overlay_profiles` (a test project file through `NR_PROJECT_FILE`, or the project model's test hook), so no acceptance command ever touches real data (G9).
   - `ingest/tests/test_profile_blocks.py` (unit): the three Phase 2 profiles load with their new blocks; an unknown key fails; `share` outside [0, 1] fails; a `window` other than `overlay` or `data` fails.
   - `graph/tests/test_overlay_resolution.py` (PHASE-2.md M2.11) still passes.
6. `docs/decisions/0021-synthetic-overlay-and-real-data-rule.md` (status `proposed`; deciders: data steward, project lead, tech lead): real organisations receive plain background activity only, from a share of them, and people from a real dataset none; the bridge rule and I15 to I17; L18 as the one exception to L17; R-REAL (G12, 7.1.4) with its four reasons, a person being every legal entity that is not an organisation, and its stricter option; why an alert built on invented payments next to a real entity, or naming a real person, is never shown (`typology-detection-definitions.md` 16, answers 22 and 24), citing `defamation_act_2013`, `ewhc_qb_1337_2019`, `uk_gdpr_adm_2026` and `dpa_criminal_data_s11_2018`, whose entries this pull request adds to `docs/sources/bibliography.yaml` (7.8).

**Acceptance, M3.4-1.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.4
make up && uv run neonradar graph migrate
uv run neonradar synth world --profile synth-demo && uv run neonradar graph load --profile synth-demo --strict
uv run neonradar synth overlay --profile synth-demo
uv run neonradar graph load --profile synth-demo --overlay latest     # counts; 0 unresolved
uv run neonradar graph load --profile synth-demo --overlay latest     # identical counts
uv run neonradar graph verify                                         # I1 to I17: 0 violations
uv run pytest -m integration graph/tests/test_overlay_load.py graph/tests/test_overlay_resolution.py graph/tests/test_invariants.py
make cypher-lint && make check
```

**Acceptance, M3.4-2.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.4
make up && uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar graph load --profile synth-demo --strict && uv run neonradar graph load --profile synth-demo --overlay latest
uv run neonradar detect run --profile synth-demo                      # alerts for every merged detector, under runs_dir
uv run neonradar detect verify-alert --run latest --profile synth-demo
uv run pytest cli/tests/test_overlay_cli.py ingest/tests/test_profile_blocks.py -q   # real profiles refused before reading; blocks
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make check
```

**Real-data run (operator)**, on an approved machine with `uk-tiny` resolved and loaded into `neo4j-real` (PHASE-2.md M2.11, M2.13), `uk-tiny` in `access.real_overlay_profiles`:

```bash
uv run neonradar synth overlay --profile uk-tiny
uv run neonradar graph load --profile uk-tiny --overlay latest
uv run neonradar graph verify --real                                  # I1 to I17: 0 violations
```

The pull request carries the counts-only output: eligible and active organisations, accounts, payments, scenarios and look-alikes by typology, the load report, and the invariant lines. This is the evidence for the Gate 2 item "Synthetic transactions generated and attached to real entities" (8.1).

**Review focus (humans).** Data steward: read L18 in the loader. Can a doctored overlay record reach `neo4j-real` without the bridge check? Run `graph load --overlay` on a copied overlay folder where one `Directorship` names a base company: does it stop with exit 2 before connecting? Graph mentor: after the synthetic load, open Neo4j Browser and find a base company of `synth-demo` with its overlay account: is `HOLDS_ACCOUNT` the only relationship between it and any `syn-ov-` node? (Every node of `synth-demo` is synthetic, so ask about `syn-ov-` ids; on the `uk-tiny` run, I15 answers it.)

### M3.5 Detectors (six sub-milestones)

**Goal.** Thirteen more detectors on the core of M3.2, each with the test file the typology researchers approved before it was written, each agreeing with its definition in 7.3 and with the Neo4j run of its tests.

**Rules shared by M3.5a to M3.5f.**

1. Copy the milestone's files from the code book: the detector modules, their typology files (2.10 says which three lines stay the repository's, and when they reset) and their test files. Add to `docs/sources/bibliography.yaml` every key the copied typology files cite that is not there yet (7.8 gives each key, and the row below names them), so that `scripts/check_citations.py` passes in CI. Nothing else is needed for a detector: the core, the queries and the kit came with M3.2.
2. The test files are the approved fixtures (1.4, 1.9). A detector milestone never edits them. A failing verbatim test is a stop-and-ask case (2.5 item 10).
3. `test_alert_builder.py::test_catalog_templates_and_parameters_match_the_detectors` checks every new typology file against its module: version, parameters and defaults, metrics, every headline template (main and variants) against the wording lint, the `shape_name` and the false-positive notes.
4. Every detector test passes on both sources (2.2 step 6c). Every alert the milestone's detectors give on `synth-demo` validates against the C4 `Alert` model: `detect run --engine memory` checks each one before writing (M3.2), so the acceptance runs it on the `synth-demo` world and overlay (M3.3) and the pull request gives its alert counts per typology. Once M3.6 has merged, `uv run neonradar eval check` shows no difference for the milestone's typologies (their rows are already in `eval/baselines/ci.json`, M3.6), and the pull request's "Detection impact" section quotes its lines.
5. The typology explainers are updated in M3.10, not here. The one exception: if M3.10 has merged before M3.5f, M3.5f's pull request adds the detection sections of its four typologies and their README rows itself (M3.10 deliverables 1 and 6).
6. Human owner: a typology researcher, with the detect mentor. The review is about behaviour: read the 7.3 section beside the detector's docstring and its test cases, and open two alerts of the `synth-demo` run in Neo4j Browser.

| | M3.5a | M3.5b | M3.5c | M3.5d | M3.5e | M3.5f |
|---|---|---|---|---|---|---|
| Typologies | `structuring`, `rapid_pass_through` | `mass_registration_address`, `shell_chain` | `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation` | `layering_chain` | `sanctions_exposure` | `formation_agent_cluster`, `recycled_directors`, `pep_exposure`, `cash_commingling` (extended) |
| Depends on | M3.2 | M3.2 | M3.2 | M3.2 | M3.2 (C2 1.2.0's `provisions` came with M3.1 before it) | M3.2 |
| Branch | `p3/m3-5a-cash-and-flow` | `p3/m3-5b-registry` | `p3/m3-5c-fans-and-dormancy` | `p3/m3-5d-layering` | `p3/m3-5e-sanctions` | `p3/m3-5f-extended` |
| Test files (verbatim tests) | `test_detector_structuring.py` (6), `test_detector_rapid_pass_through.py` (3) | `test_detector_mass_registration_address.py` (4), `test_detector_shell_chain.py` (6) | `test_detector_fan_in_collection.py` (3), `test_detector_fan_out_distribution.py` (3), `test_detector_dormant_reactivation.py` (5) | `test_detector_layering_chain.py` (4) | `test_detector_sanctions_exposure.py` (25) | `test_detector_extended_registry.py` (12), `test_detector_cash_commingling.py` (2) |
| New bibliography keys (7.8) | `cfr_31_1010_100_2026`, `cfr_31_1010_311_2026`, `cfr_31_1010_313_2026`, `mlr_reg_27_2017` | `ca_registered_office_s86_2006`, `ch_default_address_rules_2024` | `fincen_mule_advisory_2020`, `ca_dormant_company_s1169_2006` | none | `russia_sanctions_regs_2019`, `eu_reg_2580_2001`, `ec_asset_freeze_faq_2026` | `ca_acsp_s1098a_2006`, `ca_director_idv_s167m_2006` |
| CI seed rows (alerts; true; detected of 10) | structuring 15; 10; 10. rapid_pass_through 20; 8; 8 | mass_registration_address 23; 7; 7. shell_chain 19; 9; 9 | fan_in_collection 19; 10; 10. fan_out_distribution 9; 9; 9. dormant_reactivation 18; 10; 10 | layering_chain 28; 8; 8 | sanctions_exposure 22; 17; 10 | formation_agent_cluster 13; 8; 8. recycled_directors 55; 9; 9. pep_exposure 25; 25; 10. cash_commingling 12; 10; 10 |
| Reference | 7.3.1, 7.3.2 | 7.3.9, 7.3.8 | 7.3.5, 7.3.6, 7.3.7 | 7.3.3 | 7.3.10 | 7.3.11 to 7.3.14 |
| ADR | none | none | ADR-0024 (GDS use) | none | none | none |

Every sub-milestone: labels `agent`, `phase-3`, `squad:detect`, `typology`, `size-exception`; plan first: no (yes for M3.5e); size: exception (verbatim detectors and tests); real-data run: none. `shell_chain` imports two names from `mass_registration_address`, and `fan_out_distribution` one from `fan_in_collection`, which is why each pair lands together.

#### M3.5a Cash deposits and pass-through: `structuring`, `rapid_pass_through`

**Deliverables.** The two detectors, their typology files and their test files (the code book, M3.5a).

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5a
uv run pytest detect/tests/test_detector_structuring.py detect/tests/test_detector_rapid_pass_through.py detect/tests/test_alert_builder.py -q
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_structuring.py detect/tests/test_detector_rapid_pass_through.py -q
uv run neonradar eval check          # from M3.6 on: no difference for the two typologies
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology structuring --typology rapid_pass_through   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

**Review focus (humans).** Typology researcher: in 7.3.1, is a GBP deposit of exactly 10,000 rightly outside the band while a USD deposit of exactly 10,000 is inside? Is the headline free of the word the typology is named after? For `rapid_pass_through`, are 72 hours and a 10 percent residual what you would defend as "within a few days" and "a small end-of-day balance"?

#### M3.5b Registry patterns: `mass_registration_address`, `shell_chain`

**Deliverables.** The two detectors, their typology files and their test files (the code book, M3.5b).

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5b
uv run pytest detect/tests/test_detector_mass_registration_address.py detect/tests/test_detector_shell_chain.py detect/tests/test_alert_builder.py -q
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_mass_registration_address.py detect/tests/test_detector_shell_chain.py -q
uv run neonradar eval check
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology mass_registration_address --typology shell_chain   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

**Review focus (humans).** Typology researcher: are the three Companies House default addresses the ones its guidance names (7.3.9)? `shell_chain` needs two indicators, or a loop: would one indicator alone flag most lawful groups, as the development worlds showed (7.6.5)?

#### M3.5c Fans and dormancy: `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation`

**Deliverables.** The three detectors, their typology files and their test files (the code book, M3.5c). `docs/decisions/0024-gds-use.md` (status `proposed`; deciders: tech lead and project lead): GDS weakly connected components for the ring variant only, on a Cypher projection of the window's payments between recently opened accounts, `stream` with concurrency 4, the projection dropped in `finally`, components named by their smallest member id; the licence position of 1.2 (GPLv3 in Neo4j's repository; a plugin of the image users run, called over Bolt, never shipped); why not the `graphdatascience` client (3.1). Cite `detection-cypher-gds.md` 4.

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5c
uv run pytest detect/tests/test_detector_fan_in_collection.py detect/tests/test_detector_fan_out_distribution.py detect/tests/test_detector_dormant_reactivation.py detect/tests/test_alert_builder.py -q
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_fan_in_collection.py detect/tests/test_detector_fan_out_distribution.py detect/tests/test_detector_dormant_reactivation.py -q
uv run neonradar eval check
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology fan_in_collection --typology fan_out_distribution --typology dormant_reactivation   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

After the Neo4j run, `CALL gds.graph.list() YIELD graphName RETURN count(*)` on the test database returns 0: no projection is left behind.

**Review focus (humans).** Typology researcher: `fan_in_collection` tests recency on the collector, not on the senders, who are often victims (3.5): do the test cases say so? `dormant_reactivation` treats "little activity" as at most two small payments in the quiet period: too lenient, too strict? Tech lead: read ADR-0024's licence paragraph.

#### M3.5d Payment chains: `layering_chain`

**Deliverables.** The detector, its typology file and its test file (the code book, M3.5d).

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5d
uv run pytest detect/tests/test_detector_layering_chain.py detect/tests/test_alert_builder.py -q
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_layering_chain.py -q
uv run neonradar eval check
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology layering_chain   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

**Review focus (humans).** Typology researcher: the chain allows up to 20 percent total shrinkage (Europol's fee range, 7.3.3) and needs three payments through accounts of three different holders. On the CI seed half the alerts sit on other typologies' scenarios (`other` 14 of 28, all inside `circular_flow` round trips, 7.3.3): read three of them in the `eval run` output. Are they chains a human would also call chains?

#### M3.5e Sanctions exposure: `sanctions_exposure`

Plan first: yes. The three tests are the most legally loaded calculation in the project.

**Deliverables.** The detector, its typology file and its test file (the code book, M3.5e). It reads `:Sanction.provisions` (C2 1.2.0, M3.1).

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5e
uv run pytest detect/tests/test_detector_sanctions_exposure.py detect/tests/test_alert_builder.py -q   # 25 + 6 passed
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_sanctions_exposure.py -q
uv run neonradar eval check
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology sanctions_exposure   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

**Review focus (humans).** Typology researcher and data steward together: read 7.3.10 with the OFAC FAQ 401 examples beside the five `test_faq_401_*` tests. Does each test's expected outcome match the example? Read the `assessment` sentences of three alerts of the `synth-demo` run: is "left open by the published share bands" worded so that nobody reads it as "met", does every regime with a recorded control link get its control sentence, and does any text say an entity "is sanctioned" or "is blocked" (G5, PHASE-2.md 7.2)? Is each NeonRadar reading in 7.3.10 one you accept?

#### M3.5f Extended typologies: `formation_agent_cluster`, `recycled_directors`, `pep_exposure`, `cash_commingling`

These are PHASE-1.md's `extended` tier ("Phase 3 if capacity"). They never block Gate 3.

**Deliverables.** The four detectors, their typology files and their two test files (the code book, M3.5f).

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.5f
uv run pytest detect/tests/test_detector_extended_registry.py detect/tests/test_detector_cash_commingling.py detect/tests/test_alert_builder.py -q
NR_DETECT_SOURCE=neo4j uv run pytest detect/tests/test_detector_extended_registry.py detect/tests/test_detector_cash_commingling.py -q
uv run neonradar eval check          # all fourteen typologies match; nothing pending
uv run neonradar synth world --profile synth-demo && uv run neonradar synth overlay --profile synth-demo
uv run neonradar detect run --profile synth-demo --engine memory --typology formation_agent_cluster --typology recycled_directors --typology pep_exposure --typology cash_commingling   # every alert validates (C4)
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make cypher-lint && make check
```

**Review focus (humans).** Typology researcher: `pep_exposure` follows one family hop, read in the direction FtM records it, and one associate hop for business associates and joint holders only, and stops family and associate exposure when the person leaves office (3.5): do the tests show all three? `recycled_directors` has the lowest development precision (7.6.5), mostly from alerts on other typologies' scenarios: is that the right behaviour for a hub pattern that formation agents and nominee directors also form? `cash_commingling` compares with the same sector in the same area: is the area (the postcode district) right for a city with few businesses of that sector?

### M3.6 Evaluation harness and the CI gate

| | |
|---|---|
| Squad, human owner | Typologies and Detection; detect mentor (the tech lead reviews the CI job and the human-only rule) |
| Depends on | M3.2, M3.3 |
| Branch | `p3/m3-6-evaluation` |
| Labels | `agent`, `phase-3`, `squad:detect`, `eval`, `size-exception` |
| Plan first | Yes |
| Size | exception (the evaluation package, the evaluation run, their tests, the seeds and the CI baseline are verbatim) |
| ADR | ADR-0022 (evaluation protocol and the detection freeze), `proposed` until M3.11 |
| Real-data run | none |

**Goal.** One command turns seeds into the per-typology table of recall and precision with intervals; CI fails when any detector's counts on the CI seed change without an explanation; the holdout run exists but only a human can start it, and only after the freeze.

**Deliverables.**

1. **Verbatim files** (the code book, M3.6): `detect/src/neonradar_detect/evaluation/` (`__init__.py`, `match.py`, `metrics.py`, `stats.py`, `harness.py`, `report.py`); `cli/src/neonradar_cli/evaluate.py`; `detect/tests/test_evaluation_match.py`, `test_evaluation_harness.py` and `test_world_parity.py`; `cli/tests/test_eval_run.py`; `eval/seeds.yaml`; `eval/baselines/ci.json` (all fourteen rows; rows whose typology has no detector yet are reported as pending, never as failures). `ci.json` changes only as 2.10 says for every verbatim file: in the pull request that changes a detector on purpose, with its code book block, its SHA-256 and the "Detection impact" section explaining each count that moved (2.3); it never goes into the deviations file.
2. **Settings from the profile**: `EvalSettings` built from `ingest/profiles/synth-eval.yaml` (the world block, the overlay block, the detection overrides), with `created_at` fixed at 2026-11-02T00:00:00Z so that alert ids and texts do not depend on the clock.
3. **CLI.**
   - `neonradar eval check [--baseline eval/baselines/ci.json]`: the CI seed of `eval/seeds.yaml` through `evaluate.run_seed` with the in-memory source; prints one line per typology (its counts, and each difference); prints the pending rows; exit 1 on any difference.
   - `neonradar eval run --split dev [--seeds 1-5 | --seeds 1,3,7] [--engine memory|neo4j] [--out DIR]`: one `run_seed` per seed, then `evaluate.figures`, `report.markdown` and `report.to_json`, into `eval_dir(eval_id)` (M3.3, 4.5) with each seed's labels and counts, and its alerts from `SeedRun.alerts` as `seed-<n>/alerts.jsonl`; prints the table. `--engine neo4j` uses a source factory that writes the seed's records to a temporary folder, wipes the default instance, loads them with the project loader and returns a `Neo4jSource`; it refuses to run if the default instance holds any non-synthetic node.
   - `--split test` is the holdout run: human-only (it needs a terminal, through Phase 2's `tty.py`, refuses in CI and in Codespaces, and the M3.0 hook blocks the agent), and it runs only when `eval/freeze.json` exists, `eval/seeds.yaml` lists the ten holdout seeds, and the current configuration equals the freeze; exit 2 otherwise. Until M3.11 adds `eval freeze` and wires its check in here, the freeze file is missing, so the command always refuses. It always uses `--engine neo4j` and all ten holdout seeds, passes `allow_holdout=True` to `run_seed` only after these checks, and writes `report.md` and `report.json` with `split: test` into `holdout_dir(eval_id)` under `data/cache/holdout/`, which the agent cannot read (M3.0, G11).
   - Seeds of `--split dev` must be in `eval/seeds.yaml` under `dev`, so a holdout seed can never be run as a development seed; `synth world` and `synth overlay` refuse holdout seeds (M3.3), and `run_seed` refuses the test split, and any seed `eval/seeds.yaml` lists under `test.seeds` in either split, unless the CLI passes `allow_holdout=True` (`test_holdout_seeds_need_the_cli`), so a call that bypasses the CLI cannot generate a holdout world.
4. **CI**: a new job `eval` in `.github/workflows/ci.yml` (the fragment below, verbatim and already indented for its place under `jobs:`). The `integration` job needs no new step: `uv run pytest -m integration` already collects `test_world_parity.py`, and M3.2 set `NR_DETECT_SOURCE=neo4j` there.
5. `docs/decisions/0022-evaluation-protocol.md` (status `proposed`; deciders named by role: the typology researchers, the detect mentor and the tech lead; M3.11 replaces the roles with the handles in `people.freeze_deciders`, which only M3.11 needs): the unit (planted scenarios for recall, alerts for precision), the matching rules of 7.6.2, the counts of 7.6.3, the intervals (3.4), development seeds and holdout seeds, the freeze and what it pins, the human-only holdout run, and what the published table may and may not claim (7.6.4). M3.11 completes it with the date and the holdout seeds.
6. **Tests written in this milestone**: `cli/tests/test_eval_cli.py` (unit, through the CLI's test runner): `eval run --split test` with stdin closed, `CI=1` and no `eval/freeze.json` exits 2 and creates nothing under `data/cache/` (the folder is a temporary one through the layout's test hook); `eval run --split dev --seeds 99` (not a development seed) exits 2; `eval check` against a copy of `ci.json` with one count changed exits 1 and names the typology and the count.

**CI job** (verbatim, indented for its place under `jobs:` in `.github/workflows/ci.yml`, with the same pinned actions as Phase 1):

```yaml
  eval:
    runs-on: ubuntu-24.04
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v7
      - name: ICU headers for PyICU
        run: sudo apt-get update && sudo apt-get install -y --no-install-recommends pkg-config libicu-dev
      - uses: astral-sh/setup-uv@v10.3.0
        with:
          enable-cache: true
      - run: uv python install 3.14
      - run: uv sync --all-packages --locked
      - run: uv run neonradar eval check --baseline eval/baselines/ci.json
```

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.6
uv run pytest detect/tests/test_evaluation_match.py detect/tests/test_evaluation_harness.py cli/tests/test_eval_run.py -q   # 13 passed
uv run pytest cli/tests/test_eval_cli.py -q   # the holdout run refused without a terminal and a freeze (exit 2)
uv run neonradar eval check             # every merged detector matches its row; the others are pending
uv run neonradar eval run --split dev --seeds 1-5
uv run pytest -m integration detect/tests/test_world_parity.py
make check
```

`eval run --split dev --seeds 1-5` reproduces, for every merged typology, the rows of the development table in 7.6.5 exactly: the code is the same and names never move a structural draw (7.2.1). A difference means a verbatim file or the graph mapping differs from what the code book was tested with; find it before opening the pull request (2.5 item 5). With the in-memory source each seed takes about 70 seconds on a 2-core machine (about 23 to generate, 7 to build the graph, 42 to detect).

**Review focus (humans).** Detect mentor: read `match.py` with 7.6.2 beside it. Would an alert that covers half of a planted chain plus half of an unrelated one count as true? (It must not: intersection over union.) Tech lead: open `eval/baselines/ci.json`, change one count in a scratch branch and push: does the `eval` job fail and name the typology? In your own terminal, run `uv run neonradar eval run --split test`: does it refuse because there is no freeze yet? Ask the agent to run it: does the hook block it before it starts?

### M3.7 `make load` steps and the real-data detection run

| | |
|---|---|
| Squad, human owner | Docs and agent kit with Graph and ER; graph mentor (the data steward reviews the real-data run) |
| Depends on | M3.4, M3.6, M2.13 |
| Branch | `p3/m3-7-make-load` |
| Labels | `agent`, `phase-3`, `squad:docs`, `squad:graph`, `real-data-run` |
| Plan first | No |
| Size | normal |
| ADR | none |
| Real-data run | `uv run neonradar load --profile uk-tiny --skip-fetch` with the overlay and detection steps |

**Goal.** One command loads any profile end to end, overlay and detections included, and reports counts and times; the Phase 3 items of Gate 2 have their evidence.

**Deliverables.**

1. Phase 2's `make load PROFILE=<name>` (M2.13) gains steps, each timed and each skippable as M2.13's are: `world` first for a synthetic profile with a world block (`synth world --profile`); after Phase 2's `load`, `overlay` (`synth overlay --profile` and `graph load --profile ... --overlay latest`, when the profile's overlay is enabled and, for a real profile, listed in `access.real_overlay_profiles`) and `detect` (`detect run --profile`, when detection is enabled); `verify` (I1 to I17) stays last. `neonradar load` (the command behind the target, PHASE-2.md M2.13) gains `--reuse-world` and `--reuse-overlay` (load the latest generated folder instead of generating again) and `--skip-detect`. The counts-only summary gains the overlay counts and, per typology, the alerts, the duplicates and the withheld counts by reason.
2. `make gate-2-detect` (`scripts/gate_2_detect.py`): prints the evidence for G2-16 and G2-17 (8.1): the latest counts-only `uk-tiny` overlay and verify reports from `data/cache/reports/uk-tiny/` (it reads only that folder), the merge state of M3.2, M3.4-1, M3.4-2 and M3.5a (`gh pr view`), and the latest `integration` run on `main` (`gh run list`); lines it cannot check are printed as MANUAL for the tech lead. The release manager runs it beside Phase 2's `make gate-2` (PHASE-2.md M2.16) and adds its lines to the Gate 2 evidence.
3. `docs/data/profiles.md` (Phase 2): the steps and the expected sizes of the three synthetic profiles (7.11).

**Acceptance.**

```bash
make up && make load PROFILE=synth-demo     # world, load, overlay, detect, verify; times and counts
make load PROFILE=synth-demo                # identical counts
make load PROFILE=demo                      # Phase 2's steps, detection on, no overlay (7.11)
make gate-2-detect
make check
```

**Real-data run (operator)**, on an approved machine with `make up-real` running: `uv run neonradar load --profile uk-tiny --skip-fetch` (the command behind `make load`, PHASE-2.md M2.13; `--skip-fetch` reuses the downloads already present). The pull request carries the counts-only summary: the times of the steps, the overlay counts, the alerts per typology (registry typologies only can produce any on real organisations), the withheld counts by reason (`activity_on_real`, `real_person_subject` and `real_person_evidence` are expected to be above zero) and the invariant lines (I15 to I17 at zero).

**Review focus (humans).** Data steward: in the `uk-tiny` summary, does anything other than counts appear? Does every typology that rests on payments show zero alerts on real entities? Graph mentor: is the overlay reloaded after every base load (L18 step 7)?

### M3.8 Demo world and `make demo`

| | |
|---|---|
| Squad, human owner | Docs; demo producer (the detect mentor reviews) |
| Depends on | M3.7, M3.5a to M3.5e (and M3.5f when it has merged) |
| Branch | `p3/m3-8-demo` |
| Labels | `agent`, `phase-3`, `squad:docs` |
| Plan first | No |
| Size | normal |
| ADR | none |
| Real-data run | none |

**Goal.** A stranger runs one command and gets a graph with alerts for every merged typology beside look-alikes, most of which drew none, in under ten minutes (the plan's definition of done), on a laptop or in a Codespace.

**Deliverables.**

1. `make demo`: `make up`, then `make load PROFILE=synth-demo`, then the URLs of the UI and of Neo4j Browser and three Cypher queries to start from (the alert queue, one alert's evidence, one look-alike). The UI shows the synthetic demo notice (PHASE-1.md 7.1), as every all-synthetic view does.
2. `docs/data/benchmarks/<date>-synth-demo.md`: measured from `make reset CONFIRM=yes`: the time of every step, node and relationship counts, alerts per typology, the hardware.
3. `docs/detection/demo.md`: a walkthrough written from the actual run: for each merged typology one alert (its headline, its evidence query, what to look at in the picture) and one look-alike of the same typology with what makes it ordinary. Synthetic data only; the synthetic demo notice first.
4. The `e2e` workflow (PHASE-1.md M1.9e): load `synth-demo` and check that the Phase 1 alert list endpoint returns alerts of at least ten typologies and that the UI smoke test opens one alert's explain panel.
5. **The names check (data steward, before the pull request merges)**: on an approved machine with a register profile loaded, the data steward compares every company name of the `synth-demo` world and overlay with the loaded register's company names, and the full names of its list, PEP and RCA personas and their relatives with the register's officer names (exact matches after case folding), and adds the two counts, never the names, to the pull request. Both should be zero. A matching company name goes to the ingest mentor, who adds its distinctive word to the name source's denylist (M3.3) and regenerates the demo before it is published (2.9); a matching persona name means the invented surnames failed, which is a bug to fix first. Ordinary synthetic people have realistic names by design and are not counted: none of them is ever on a list or flagged.

**Acceptance.**

```bash
make reset CONFIRM=yes && time make demo    # under 10 minutes; at least one alert for every merged typology
uv run neonradar detect verify-alert --run latest --profile synth-demo
make e2e
make check
```

`make reset` removes the Compose volumes, and on some Compose versions the `neo4j-real-data` volume too (PHASE-2.md 4.5): run the timing on a machine without a real instance, or reload the real profile afterwards. The `synth-demo` world and overlay hold about 5,500 nodes and 156,000 relationships (151,000 payments), and its detection run gives about 100 alerts, at least three for every typology once all fourteen have merged (7.2.9, 7.11).

**Review focus (humans).** Demo producer: follow `docs/detection/demo.md` from a clean clone. Does each alert's picture tell the story its headline promises, and does each look-alike look ordinary? Detect mentor: are the alerts the walkthrough picks typical, not the strongest ones? Data steward: are the two names counts in the pull request, and are both zero?

### M3.9 Scale world and benchmark

| | |
|---|---|
| Squad, human owner | Graph and ER; graph mentor |
| Depends on | M3.7 |
| Branch | `p3/m3-9-scale` |
| Labels | `agent`, `phase-3`, `squad:graph` |
| Plan first | No |
| Size | normal |
| ADR | none |
| Real-data run | none |

**Goal.** The plan's scale target (500,000 nodes, 2 million relationships, a 16 GB laptop) is generated, loaded, verified and searched, with measured times, so that Phase 6 can publish the benchmark.

**Deliverables.**

1. `make load PROFILE=synth-scale` end to end on a 16 GB laptop with the standard memory profile (Neo4j heap 2 GB, page cache 2 GB), measured: generation time and peak memory of the world and the overlay, load times of the base and the overlay, verify time, detection time per typology on Neo4j, node and relationship counts (`neonradar graph stats`), and the latencies of Phase 2's query benchmark (M2.13) on this graph, p50 and p95.
2. `docs/data/benchmarks/<date>-synth-scale.md`, counts and times only, with the hardware and the software versions. Targets from the plan: at least 500,000 nodes and 2 million relationships; the load under 10 minutes; interactive queries p95 under 2 seconds. Detection has no target: report its time.
3. When a detector query hits its timeout (600 seconds) or the transaction memory limit, record it with the typology and the query file; a mechanical fix (a chunk size, a parameter of the driver) may go into this pull request with a "Deviations" note; anything that would change what a detector finds is a stop-and-ask case.

**Acceptance.**

```bash
uv run neonradar synth world --profile synth-scale     # about 970,000 records in about 90 s, 1.4 GB peak
uv run neonradar synth overlay --profile synth-scale   # about 1.6 million records in about 75 s, 2.2 GB peak
time uv run neonradar load --profile synth-scale --reuse-world --reuse-overlay   # the folders above
uv run neonradar graph stats                           # at least 500,000 nodes and 2,000,000 relationships
make check
```

(Measured in the prototype on 18 October 2026, 2 cores: 959,143 world records in 81 s and 1,537,739 payments in the overlay in 67 s, peak 2.1 GB, 1.0 GB of record files, about 495,000 nodes and 2.05 million relationships before `HAS_ADDRESS`; `synth-scale` adds 1.4 percent more companies and people to clear the node target.)

**Review focus (humans).** Graph mentor: is the hardware described well enough that a stranger could compare? Are the query latencies measured warm and cold, as Phase 2's benchmark does? Is any detector unusable at this size, and is that stated plainly?

### M3.10 Documentation, ADRs and the Assignment 4 kit

| | |
|---|---|
| Squad, human owner | Docs with Typologies and Detection; technical writer (the typology researchers review every explainer) |
| Depends on | M3.5a to M3.5e, M3.6, and M3.5f when it has merged (if M3.5f merges after M3.10, its own pull request adds the detection sections of its four typologies and their README rows, under deliverables 1 and 6) |
| Branch | `p3/m3-10-docs` |
| Labels | `agent`, `phase-3`, `squad:docs`, `squad:detect`, `docs` |
| Plan first | Yes |
| Size | normal (documentation; the Assignment 4 file is verbatim) |
| ADR | completes ADR-0020 to ADR-0024 (7.10) |
| Real-data run | none |

**Goal.** Every detector is explained in plain language with its sources, the method and the evaluation are documented for strangers, the decisions are recorded, and the interns have their assignment.

**Deliverables.**

1. The explainers of the typologies whose detectors have merged (fourteen once M3.5f has; each typology file's `doc` path, the slug with hyphens: `docs/typologies/shell-chain.md`): a new section "Detection in NeonRadar" written from 7.3. A typology named after a conduct (`structuring`, `layering_chain`, `shell_chain` and the others) starts the section by saying that an organisation or account matching the shape has not thereby done what the typology is named after, because alerts about real organisations link here (7.5.2). Then: the definition as the detector reads it, every parameter with its default and either its source key or the words "a modelling choice", the variants, what an alert shows (one headline from the `synth-demo` run, quoted), the look-alikes the generator plants and the false positives the typology file lists, the development figures of 7.6.5 labelled as development figures, and the limits. Every factual statement cites a key (G4); `aml-claims-checker` reviews each file. `docs/typologies/trade-based-ml.md` gains a short section on why there is no detector (3.5, 7.3.15). Run `neonradar docs typology-index` after the edits (PHASE-1.md M1.7c).
2. `docs/detection/README.md`: how detection works (candidate steps, the oracle and the parity tests, R-REAL, pattern strength and the queue, alert ids and evidence queries), how the evaluation works (7.6.1 to 7.6.4), and the limitations, in the order a stranger asks.
3. `docs/sources/bibliography.yaml`: the keys of 7.8, each checked against its source on the day of the pull request (the `checked` date in each entry). Glossary additions (7.9).
4. ADR-0020 to ADR-0024: complete the drafts of M3.2, M3.4, M3.6, M3.3 and M3.5c with what was built; all stay `proposed` (ADR-0022 is accepted in M3.11 by its deciders).
5. `docs/team/assignment-4.md`, verbatim from the code book.
6. `README.md`: a "Detections" section listing the merged typologies with links to their explainers, and the development table of 7.6.5 under the heading "Development figures (not the published evaluation)", until M3.12 replaces it with the holdout table.

**Acceptance.**

```bash
uv run python scripts/spec_extract.py check --milestone M3.10
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md   # every key exists
uv run neonradar docs typology-index --check
make check && make hygiene
```

**Review focus (humans).** Typology researchers: read each detection section beside 7.3 and the detector's docstring. Does it say anything the sources do not? Is every modelling choice called one? Technical writer: read `docs/detection/README.md` as a stranger: can you tell, from it alone, what an alert means and what it does not?

### M3.11 Detection freeze

| | |
|---|---|
| Squad, human owner | Typologies and Detection; the freeze deciders (`people.freeze_deciders`) |
| Depends on | M3.5a to M3.5e, M3.6, M3.10, and M3.5f only if it has merged by Friday 6 November (an extended typology left out is listed in the freeze as not evaluated) |
| Branch | `p3/m3-11-freeze` |
| Labels | `agent`, `phase-3`, `squad:detect`, `eval` |
| Plan first | No |
| Size | normal |
| ADR | ADR-0022 accepted (by its deciders, not by the agent) |
| Real-data run | none |

**Goal.** On Monday 9 November everything that decides the published figures is pinned, and only then are the holdout seeds drawn (G11).

Start on Friday 6 November (1.7): the agent prepares the pull request that day, and the humans act on it on Monday.

**Deliverables (agent, prepared on Friday 6 November).**

1. `neonradar eval freeze --write`: writes `eval/freeze.json` with the fields of 7.6.1, in its canonical form: the SHA-256 of the `synth-eval` detection parameters, the detector versions, the SHA-256 of every typology file without its `owner`, `status` and `approved_by` lines, the SHA-256 of every tracked code file 7.6.1 lists (the detection package with its queries and its evaluation package, the generator package, the evaluation CLI, and the graph loader and mapping modules the Neo4j source factory uses), of the `synth-eval` profile, of the development and CI parts of `eval/seeds.yaml` and of `eval/baselines/ci.json`, the matching rules version, the label schema, the generator version, the planted mix, the numpy and Faker versions from `uv.lock`, the git commit and the date.
2. `neonradar eval freeze --check`: recomputes every field except `git_commit` and `frozen_at` and exits 1 on any difference, naming each field and path. CI's `python` job runs it once the file exists. `eval run --split test` now calls the same check before anything else and refuses with exit 2 unless it passes (replacing M3.6's refusal for a missing file).
3. **The freeze-change rule**: `scripts/check_contract_paths.py` (PHASE-1.md M1.6) gains a rule: once `eval/freeze.json` exists on the base branch, a pull request that changes it, or any path it pins, without the label `freeze-change` fails, as for `contract-change`. Such a change invalidates the holdout seeds (G11). The label comes from M3.0's `labels.yml`.
4. **Tests** (unit): `cli/tests/test_eval_freeze.py`: a freeze written and checked at once passes; a changed query file, a changed parameter default, a changed numpy pin in a test `uv.lock` and a changed file of the generator each fail with the field named; a change to the `owner`, `status` or `approved_by` line of a typology file, a new `git_commit` and the test seeds of `eval/seeds.yaml` do not; `eval run --split test` with a freeze that does not match exits 2. `scripts/tests/test_check_contract_paths.py` gains the cases of the new rule.
5. The pull request: `eval/freeze.json` and ADR-0022 completed except the human fields, with the deciders' handles from `people.freeze_deciders`, and a checkbox for each typology researcher's parameter review ("I read the parameter table of 7.3 for my typology against its file"). Until ADR-0022 is accepted, the agent may run `eval freeze --write` again on this branch when a reviewer asks for a change; after the acceptance, only a `freeze-change` pull request does (2.6).

**What humans do (Monday 9 November, in this order).**

1. The freeze deciders read the parameter tables of 7.3 against the typology files and accept ADR-0022 (status `accepted`, deciders, date).
2. The tech lead draws ten seeds on their own machine and pastes them, with the date and their handle, into ADR-0022 and into `eval/seeds.yaml` (`test.seeds`, `drawn_by`, `drawn_at`), as a human commit on the branch:

   ```bash
   python3 -c "import secrets; print(sorted(secrets.randbelow(2**31 - 1) + 1 for _ in range(10)))"
   ```

   Seeds are never chosen by hand and never drawn again because of a result.
3. A reviewer merges the pull request.

**Acceptance.**

```bash
uv run neonradar eval freeze --check     # matches
uv run pytest cli/tests/test_eval_freeze.py scripts/tests/test_check_contract_paths.py -q
uv run neonradar eval check              # unchanged counts
make check
```

**Review focus (humans).** Freeze deciders: does `freeze.json` pin everything that could move a published figure (parameters, the code of the detectors, the sources, R-REAL, the matcher, the generator, the planted mix, the CI baseline)? Is anything missing, for example a profile override? Tech lead: in a scratch branch, change one character of a query file and push without the label: does CI fail?

### M3.12 Published evaluation

| | |
|---|---|
| Squad, human owner | Typologies and Detection; detect mentor, and the human who runs the holdout |
| Depends on | M3.11, and the human holdout run (the pull request opens only after its two files are on the branch, 2.8) |
| Branch | `p3/m3-12-published-evaluation` |
| Labels | `agent`, `phase-3`, `squad:detect`, `eval`, `docs` |
| Plan first | No |
| Size | normal |
| ADR | none |
| Real-data run | none (the holdout run is synthetic, but human-only, G11) |

**Goal.** The README carries the plan's table: precision and recall per typology against labelled synthetic data, measured on worlds nobody had seen, with honest intervals and limits.

**Rehearsal (Friday 6 November, the same human and machine).** `uv run neonradar eval run --split dev --seeds 1-2 --engine neo4j`: development seeds only, to check Docker, memory and time before the day.

**What a human does (Tuesday 10 November).** On any machine with Docker (the data is synthetic):

```bash
uv run neonradar eval run --split test       # ten holdout worlds through Neo4j; about 15 to 30 minutes
```

The command prints its `holdout_dir` under `data/cache/holdout/`. The human copies `report.md` and `report.json` from it into exactly one pair of files, `docs/data/detection/raw/eval-test-<date>.md` and `.json`, commits them on the branch `p3/m3-12-published-evaluation` (created from `main`) and pushes. The agent never runs the command and never opens a holdout world or anything under `data/cache/holdout/` (G11); it works only from those two committed files. It starts from the human's branch (`git fetch origin && git switch p3/m3-12-published-evaluation`), never with `git switch -c`, so the human's commit stays.

**Deliverables (agent).**

1. `docs/data/detection/evaluation-<date>.md`: the run's `report.md` exactly as produced, after a short paragraph saying what was run, when, by whom, with which freeze (ADR-0022), and before a short list of the planted mix and the matching rules version.
2. `README.md`: the "Detections" section's development table is replaced by the holdout table (the same numbers as the evaluation file), with the fixed texts of 7.6.4 and the comparison sentence of 7.6.4; the development figures move to `docs/detection/README.md`, labelled as such.
3. Every figure is published as measured, including a typology with `n = 0` or results far from the development figures; the Phase 3 report explains such differences (M3.13). Nothing is re-run because of a result.

**Acceptance.**

```bash
uv run neonradar eval freeze --check
ls docs/data/detection/raw/eval-test-*.json | wc -l                                    # exactly 1
uv run python -c "import json, sys; d = json.load(open(sys.argv[1])); assert d['meta']['split'] == 'test' and len(d['meta']['seeds']) == 10" docs/data/detection/raw/eval-test-*.json
uv run python scripts/check_citations.py docs/ detect/typologies/ README.md
make check && make hygiene
```

**Review focus (humans).** Detect mentor: do the README table, the evaluation file and `report.json` agree number for number? Technical writer and typology researchers: read the fixed texts as a sceptical reader. Could anyone take these figures as a claim about real-world performance?

### M3.13 Gate 3 check and the Phase 3 report

| | |
|---|---|
| Squad, human owner | Docs and agent kit; tech lead (the release manager runs the check) |
| Depends on | every Phase 3 milestone |
| Branch | `p3/m3-13-gate-3` |
| Labels | `agent`, `phase-3`, `squad:docs` |
| Plan first | No |
| Size | normal |
| ADR | none |
| Real-data run | none |

**Deliverables.**

1. `make gate-3` (`scripts/gate_3.py`): checks G3-01 to G3-12 of 8.2 where it can (CI runs, files, `eval freeze --check`, `eval check`, the published file, ADR status lines) and prints MANUAL for the rest.
2. `docs/build/reports/phase-3.md`: the detectors and their tests; development and holdout figures side by side, with possible reasons for differences larger than the intervals, written from the two published report files and the development seeds only (the agent never opens a holdout world, its labels or its alerts to explain a difference, G11; a reason it cannot check on development seeds is stated as a hypothesis); the times of `make demo` and of the scale world; deviations from this spec; open risks; and what Phases 4 to 6 need (the alert fields the copilot and the UI will show, the benchmark inputs for Phase 6, the published table for the launch post).

**Acceptance.** `make gate-3` (every automatic check passes; MANUAL lines listed for the release manager).

**Review focus (humans).** Release manager: run `make gate-3` yourself and confirm each MANUAL line with its evidence.

---

## 7. Knowledge base and detection reference

This section is the reference the milestones point to. The verbatim code in the code book implements it; where the two ever disagree, stop and ask (2.5), because one of them is wrong.

### 7.1 Detector design

#### 7.1.1 What a detector is

A detector is one module, `detect/src/neonradar_detect/detectors/<slug>.py`, that turns candidate rows into findings. It defines:

| Name | What it is | Checked by |
|---|---|---|
| `SLUG` | the typology slug | `runner.detectors` (the catalog's `detector` must name a module whose `SLUG` is that typology) |
| `VERSION` | the detector version; equals the typology file's `version` | `test_alert_builder.py` |
| `QUERIES` | the sorted names of the query files its candidate steps run; `detect run` hashes their texts into `detector.query_sha256` (C4) | `test_detector_queries.py` (exact list, files exist) |
| `Params` | a frozen dataclass; its fields and defaults equal the typology file's `parameters` | `test_alert_builder.py` |
| `run(source, params, window)` | returns `DetectorOutput(findings, stats)`; `stats` holds the detector's own counts (candidates read, windows skipped, paths cut), which the run summary carries | the detector's tests |
| `priority(finding)` (optional) | a typology's own priority rule (C4 allows one); only `sanctions_exposure` has one | `test_detector_sanctions_exposure.py` |

A `Finding` (`model.py`) holds ids, numbers and the grouping of evidence relationships into explanation steps, never text:

| Field | Rule |
|---|---|
| `typology`, `variant` | the slug and one of the variants named in 7.3 |
| `anchor` | the evidence node the finding is about (the account, the address, the organisation); it must be an evidence node |
| `node_ids`, `edge_ids` | C2 ids of the evidence, sorted and unique |
| `subjects` | at least one `(entity_id, role)`; roles per typology in 7.3 |
| `metrics` | the values the typology file lists under `metrics`, and nothing else |
| `pattern_strength` | in [0, 1], rounded to four decimals (`model.clip01`); the typology's formula in 7.3 |
| `steps` | tuples of evidence edge ids; each tuple becomes one explanation step (7.5.2) |
| `window` | the time span of the evidence, when the typology has one |
| `activity` | true when the finding rests on payments; R-REAL treats a finding as payment-based when this is true or a `PAID` relationship is among its evidence (7.1.4) |

Rules every detector follows:

1. It reads the graph only through the `Source` protocol (7.1.2). No driver, no Cypher, no file, no clock: the window is passed in.
2. It is deterministic. Every set is sorted before it is iterated into an output, ties are broken by ids, and nothing random is drawn.
3. It is bounded. Every candidate step takes a limit from `Params` (`max_candidates`, `max_starts`, `max_paths`, `max_links`, `max_branching`, `max_frontier`), and whatever a limit cuts is counted in `stats`. A limit that cuts on the evaluation worlds is a defect to report, not a tuning knob.
4. It never imports `neonradar_ingest` (4.1), and never adds a flag, a topic or a label to an entity (G8).
5. It leaves real and synthetic data to the runner, which applies R-REAL after it on every instance (7.1.4). One exception keeps a registry finding from resting on payments: `mass_registration_address`, `formation_agent_cluster` and `recycled_directors` add payments among an organisation group to the strength only when every organisation of the group is synthetic, and set `activity` when they do (`test_detector_mass_registration_address.py` shows both cases).
6. A registry relationship counts only while it holds: no end date, or one after the end of the window (`LinkRow.current`, and the `as_of` parameter of `appointment_counts`, `ownership_paths` and `ownership_cycles`). A resigned director, a sold holding or an ended family link is history, not structure (`typology-detection-definitions.md` 12 lists resigned appointments counted as active among the misleading alerts).

#### 7.1.2 Candidate steps

`source.py` defines the steps a detector may ask for. `Neo4jSource` runs the query file of the same name in `detect/src/neonradar_detect/queries/`; `MemSource` runs reference code on an in-memory graph (7.1.5). Both return the typed rows of `rows.py`, in the order the query file's header comment states.

| Step | Returns (`rows.py`) | Order | Used by |
|---|---|---|---|
| `paid_time_range()` | first and last `PAID.ts`, or none | | `detect run` (default window), `rapid_pass_through`, `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation`, `cash_commingling` (left-censoring) |
| `node_info(ids)`, `edge_info(ids)` | `NodeInfo` (labels, caption, synthetic, datasets, the holders of an account), `EdgeInfo` | by id | the runner, for every finding (7.1.4, 7.5) |
| `paid_starts(min_amount, start, end, limit)` | `Hop` (with the holders of both ends) | (ts, id) | `circular_flow`, `layering_chain` |
| `paid_hop(frontier)` | `Hop` per frontier key | key, (ts, id) | `circular_flow`, `layering_chain` (7.1.3) |
| `flows_by_inbound(min_counterparties, start, end, channel, bucket_hours, limit)` | `AccountFlows`: accounts with many payers in one bucket, with every payment in and out | by account | `rapid_pass_through`, `fan_in_collection` |
| `flows_by_outbound(min_counterparties, start, end, bucket_hours, limit)` | `AccountFlows`: accounts with many payees in one bucket | by account | `fan_out_distribution` |
| `counterparty_info(accounts)` | opening date, holders and their labels | by account | `fan_in_collection` |
| `paid_times(pairs)` | the times of every payment between two accounts | by pair | `fan_in_collection`, `fan_out_distribution` (prior relationships) |
| `payments_from(accounts, start, end)`, `payments_into(...)` | `Pay` lists | (ts, id) per account | `fan_in_collection`, `fan_out_distribution`, `cash_commingling` |
| `payments_among(accounts, start, end)` | (edge id, payer, payee) between members of a set | by edge id | `mass_registration_address`, `formation_agent_cluster`, `recycled_directors` |
| `activity_counts(accounts, start, end)` | payments in or out per account | by account | `layering_chain` (quiet intermediaries) |
| `holder_cash_deposits(band_low, threshold, min_in_band, start, end, limit)` | `HolderDeposits`: holders with enough in-band cash deposits, with every cash deposit of the period | by holder; (ts, id) | `structuring` |
| `quiet_account_histories(...)` | `AccountHistory`: accounts whose quiet period ends in the window, with all their payments | by account; (ts, id) | `dormant_reactivation` |
| `company_account_histories(incorporated_since, start, end, min_payments, limit)` | `AccountHistory` of accounts of dormant-filed or new companies | by account | `dormant_reactivation` (company variants) |
| `recent_account_components(new_days, start, end, min_size)` | `Component`: weakly connected components of payments between recently opened accounts | by smallest account id | `fan_in_collection` (ring variant, 7.1.6) |
| `entities(ids)` | `EntityRow` | by id | seven registry and dormancy detectors |
| `links_into(ids, types)`, `links_from(ids, types)` | `LinkRow`: registry relationships of the given types | by id, then relationship id | every registry detector, `layering_chain`, `dormant_reactivation`, `cash_commingling` |
| `appointment_counts(people, as_of)` | current `DIRECTOR_OF` count per person (no end date, or one after `as_of`) | by id | `shell_chain` |
| `ownership_paths(max_hops, limit, as_of)`, `ownership_cycles(max_hops, limit, as_of)` | `OwnershipPath` over current `OWNS` relationships | by the node ids along the path | `shell_chain` |
| `registered_clusters(min_members, active_only, limit)`, `registered_count_quantile(q, active_only)` | `AddressCluster`; one integer | by address id | `mass_registration_address` |
| `hubs(rel_type, min_members, limit)` | `Hub`: agents (`REPRESENTS`) or directors (`DIRECTOR_OF`) with many organisations | by hub id | `formation_agent_cluster`, `recycled_directors` |
| `listed_entities()` | `ListedRow`: every `:Sanctioned` entity with its `:Sanction` nodes | by id | `sanctions_exposure` |
| `flagged_ids(flag)` | ids with one flag label (`Sanctioned`, `PEP` or `RCA`) | sorted | `pep_exposure` |
| `cash_profiles(prior_start, start, end, currency, limit)` | `CashProfile`: cash deposits per company, in pence, with sector and area | by holder | `cash_commingling` |

`queries/evidence.cypher` is the 33rd file. It is not a step: every alert's `evidence.query` is that text with the alert's own ids, and `neonradar detect verify-alert` runs it (7.5.1).

**Rules for the query files** (each file was linted with both linters, 3.4; `.claude/rules/detect.md` repeats the main ones for later changes, and a change to a query file needs the same change in `memsource.py`):

1. One file per step, named after it; the ring step has four (7.1.6). Every value is a parameter. Four files are templates (`ownership_paths`, `ownership_cycles`, `flagged_ids`, `hubs`) whose `{{max_hops}}`, `{{flag}}` or `{{rel_type}}` is filled from the fixed lists in `neo4jsource.TEMPLATE_VALUES`, checked before substitution, with a `// lint-values:` header for the linter (PHASE-2.md M2.0).
2. Times go in as UTC ISO strings and are parsed in the query with `datetime($x)`; durations are compared as `duration.inSeconds(a, b).seconds`; lists are wrapped in `coalesce(x, [])`; patterns are directed.
3. A lookup by id names `:Entity` (or `:Sanction`), so the uniqueness index serves it. Window steps anchor on the `paid_ts` range seek.
4. Every `LIMIT` follows an `ORDER BY` that ends in a C2 id.
5. Flow and path steps exclude cash ledger accounts (`account_kind` `cash_ledger`, the synthetic banks' branches), whose tens of thousands of payments would join everything; `holder_cash_deposits` and `cash_profiles` read them, because cash deposits come from them.
6. Queries run auto-commit, `session.run(neo4j.Query(text, timeout=timeout_s), parameters)`: 600 seconds in `detect run`, 60 in tests. Never `execute_read`, which retries a memory-limit error (3.2).

**What the detectors read.** Only these C2 labels, types and properties; `test_graphrows.py` pins every one of them on a small graph built by `graphrows.py`, the oracle's own reading of C2, and the Neo4j mode of every detector test checks that the loader writes them the same way (7.1.5). All exist in C2 1.1.0 except `:Sanction.provisions` (1.2.0).

| Node label | Properties |
|---|---|
| every `:Entity` | `id`, `caption`, `schema`, `synthetic`, `datasets`, `countries`; the labels `:Synthetic`, `:Sanctioned`, `:PEP`, `:RCA`, `:Person`, `:Organization`, `:Company`, `:Account`, `:Address` |
| `:Organization` (and `:Company`) | `jurisdiction`, `incorporation_date`, `dissolution_date`, `status`, `sector`, `accounts_category`, `psc_statements` |
| `:Account` | `opening_date`, `account_kind`, `account_number` (its caption) |
| `:Address` | `full`, `postal_code`, `city` |
| `:Position` | `country` |
| `:Sanction` | `id`, `datasets`, `authority`, `program`, `provisions`, `start_date`, `end_date` |

| Relationship | Properties |
|---|---|
| `PAID` | `id`, `ts`, `amount`, `currency`, `channel`, `synthetic` |
| `OWNS` | `id`, `share_pct_min`, `share_pct_max`, `share_min_exclusive`, `share_max_exclusive`, `is_nominee`, `start_date`, `end_date` |
| `CONTROLS` | `id`, `control_type`, `share_pct_min`, `share_pct_max`, `share_min_exclusive`, `share_max_exclusive`, `start_date`, `end_date` |
| `CONSOLIDATES` | `id`, `start_date`, `end_date` (and `level`, pinned for later use) |
| `DIRECTOR_OF` | `id`, `role`, `is_nominee`, `start_date`, `end_date` |
| `HOLDS_ACCOUNT`, `SUBJECT_OF` | `id` |
| `HAS_ADDRESS` | `id`, `role` |
| `REPRESENTS` | `id`, `role` |
| `FAMILY_OF`, `ASSOCIATE_OF` | `id`, `relationship` |
| `HOLDS_POSITION` | `id`, `start_date`, `end_date` |

#### 7.1.3 Path expansion

`circular_flow` and `layering_chain` need paths of two to six payments in time order. A Cypher 5 quantified path pattern cannot compare a hop with the previous one, so a query cannot prune on time and amount as it goes; it enumerates every path first (3.2). `expand.py` therefore keeps the paths in Python and asks the source for one hop of every partial path at a time:

1. The starts are `paid_starts`: payments of at least `min_amount` in the window between customer accounts, in (ts, id) order, at most `max_starts` of them. They are expanded 10,000 at a time, so the frontier stays bounded however many starts there are.
2. For each partial path, the detector's `extend` gives a frontier item: the account to leave from, the open interval `(after, until]` for the next payment, the amount range, the currency and the accounts already visited. One `paid_hop` call answers the whole frontier.
3. The detector's `keep` drops hops a query cannot judge (holder overlaps); `accept` says whether a path is a result.
4. Per partial path at most `max_branching` next hops are kept (earliest first, then by edge id), and per level at most `max_frontier` partial paths. Whatever is cut is counted in `stats.truncated`; on the development worlds nothing was cut.

`circular_flow` measures every hop against the first payment (between `min_return_ratio` and `1 + max_hop_gain` of it, within `max_window_days` of it); `layering_chain` measures each hop against the previous one (between `min_hop_ratio` and `1 + max_hop_gain`, within `max_dwell_hours`). Both follow strictly later payments only, so each path starts at its earliest payment and is found once.

#### 7.1.4 R-REAL in the runner

The runner (7.5.3) asks the source for `node_info` and `edge_info` of every finding, then `policy.data_flags` computes the C4 data flags and `policy.decide` applies G12, the first rule that applies giving the reason:

- **Involved nodes** are the evidence nodes, the subjects, and the holders of every evidence account. `involves_real_entities` is true when any involved node is not synthetic; `synthetic_activity` is true when every evidence relationship is synthetic; `datasets` lists the involved nodes' datasets.
- **A person** is any `:LegalEntity` that is not an `:Organization`: a `:Person`, or a legal entity whose kind the source does not state (ICIJ officers and intermediaries are mapped to `LegalEntity`, PHASE-2.md M2.5), which may be a person.
- **(a) `activity_on_real`**: the finding rests on payments (its `activity` flag, or a `PAID` among its evidence relationships) and involves a non-synthetic node. Withheld.
- **(b) `real_person_subject`**: a subject is a non-synthetic person. Withheld.
- **(c) `real_person_evidence`**: another involved node is a non-synthetic person: a listed person behind a company, a PEP or a relative, a director, a top owner. Withheld, so that no alert names a real person anywhere (data protection by design, `typology-detection-definitions.md` 16.5).
- **(d) `registry_on_real`**: with `access.real_registry_alerts: false`, any other finding that involves a non-synthetic node. Withheld.
- Otherwise the alert is emitted. `wording_class` is `structural_pattern` when it involves a real entity (which, after (a) to (d), can only be a registry pattern about organisations, with organisations and addresses as its evidence) and `synthetic_scenario` otherwise.

On a real profile this leaves, for example, a company owned through a chain of companies by a company on a sanctions list, or an address with many companies and no shared director; `pep_exposure` and `recycled_directors` never emit there, because every finding of theirs names a person. A withheld finding is never rendered, stored or logged; the run summary counts it by typology and reason (7.5.3). The rule runs on every instance: on a synthetic profile it never fires, because every node is synthetic, which the tests of `test_alert_builder.py`, `test_detector_extended_registry.py` and `test_detector_sanctions_exposure.py` show with run-time look-alike records, and M3.4's integration test shows on Neo4j. I17 checks the result after every detection load: the subjects, the evidence nodes and the evidence payments of every alert (5.2).

#### 7.1.5 Two sources and the parity tests

- **`MemSource`** (`memsource.py`) runs a reference implementation of every step on a `MemGraph` (`memgraph.py`: nodes, relationships and adjacency, every listing in id order). The graph comes from `graphrows.from_records(records)`, the oracle's own reading of C1 records into C2 (verbatim, one node per record, no entity resolution). It does not reuse the loader's mapping, so that an error in either shows up as a difference between the two sources instead of being shared by both. Unit tests, the CI gate and development evaluations use it: no database needed. The memory engine refuses a real profile and a profile with resolution enabled (M3.2).
- **`Neo4jSource`** (`neo4jsource.py`) runs the query files. `detect run`, the world parity test and the published evaluation use it.
- **Detector tests run on both.** Tests build records with the kit (7.4) and turn them into a source with `kit.source_of`, which calls `kit.SOURCE_FACTORY`. With `NR_DETECT_SOURCE=neo4j`, the conftest replaces the factory with one that wipes a Testcontainers database, writes the records to a temporary folder, loads them with the project's loader in strict mode, and returns a `Neo4jSource` (`neo4j_mode.py`, reference). A test whose records are not all synthetic is skipped in that mode, because the default instance refuses them (L17); its in-memory run covers it.
- **The world parity test** (`test_world_parity.py`, integration) generates a small `synth-eval` world (80 companies, one scenario and one look-alike per typology, seed 5) and runs the whole evaluation of that seed twice, through `MemSource` and through `Neo4jSource`: the record digests, the alert ids (and there must be some), the per-typology run summaries and the baseline counts must be identical.

**When the two differ.** The rows each step returns are defined by its query file's header comment and by `rows.py`; the definition of each typology is in 7.3. Find which side departs from that, fix it, and record the change under "Deviations from spec" with the failing test (both sides are verbatim files, so `spec_extract check` will name the file). If it is not clear which side is right, stop and ask (2.5 item 5). The query files were linted but never run on a server before this spec was written (3.4): M3.2's Neo4j-mode run is their first execution, and M3.6's world parity test the first on a generated world.

#### 7.1.6 GDS use and query plans

Only the ring variant of `fan_in_collection` uses GDS (ADR-0024). `Neo4jSource.recent_account_components` runs four files:

1. `recent_account_edges.cypher`: the payments of the window between two customer accounts each opened at most `new_account_days` before the payment (the rows the oracle also computes).
2. `recent_account_components_project.cypher`: a Cypher aggregation projection (`gds.graph.project`, undirected, `readConcurrency: 4`) named `nr-ring-` plus 32 random hex digits, unique per call.
3. `recent_account_components_wcc.cypher`: `gds.wcc.stream` with `concurrency: 4`, ordered by component and account id.
4. `recent_account_components_drop.cypher`: drops the projection, in a `finally` block, so a failure never leaves one behind.

Component ids are not stable between runs, so each component is named by its smallest account id. Weakly connected components give the same components on every run; Louvain, which the plan mentioned, does not at a concurrency above 1, so it is not used (`detection-cypher-gds.md` 4). `MemSource` computes the same components with union-find. Never use GDS `write` or `mutate` procedures, the `graphdatascience` client, or `apoc.periodic.*` in detection (2.6).

**Query plans.** The offline linters cannot see the planner. `detect/tests/test_query_plans.py` (integration, reference; M3.2 adapts its fixture names) loads the parity world into a test database and runs `EXPLAIN` on every query file with sample parameters. It fails when a query is not read only (the three GDS files that project, stream and drop excepted), when the server reports a deprecation, an unfulfillable hint, a missing parameter (an `01N` status other than `01N50` to `01N52`, which only say a label, type or property is absent), a cartesian product (`03N90`), an unbounded or exhaustive shortest path (`03N91`, `03N92`) or a shadowed subquery variable (`03N60`), and when an anchored window query does not seek the `paid_ts` index.

### 7.2 Generator v1

Generator v1 lives beside generator v0 in `ingest/src/neonradar_ingest/synth/`. It has two parts: the **world**, a synthetic register that stands in for Companies House on synthetic profiles, and the **overlay**, which attaches accounts and ordinary activity to any base (a world, a fixture or a real profile) and plants scenarios and look-alikes among synthetic entities it creates itself. Generator v0 and `make demo-mini` keep working unchanged.

#### 7.2.1 Determinism

The same code, seed and base give the same bytes. `test_synth_v1.py` checks it, and the CI baseline (7.6.1) depends on it.

1. **Named streams.** Every draw comes from `streams.stream(seed, *keys)`: a `numpy.random.Generator(PCG64(SeedSequence(entropy=seed, spawn_key=...)))` whose spawn key is the first four bytes of the SHA-256 of each key string. A stream depends only on what it is for (`("background", "<organisation id>")`, `("scenario", "scn-000017")`, `("place", ...)`), never on how many draws came before, so adding a scenario leaves every other entity's activity unchanged.
2. **Names on streams of their own.** Every name (people, companies, streets, towns) is drawn from a separate stream (`("address-name", key)` and the like) through the `NameSource` interface (7.2.3). A different name source changes names and nothing else: `test_names_never_move_a_structural_draw` swaps in `names_simple.py` and compares everything but names.
3. **No hidden order.** Sets are sorted before they reach a record, a label or an id (`PYTHONHASHSEED` differs between processes); records are written in id order as compact JSON with sorted keys (`writer.line`).
4. **Exact money.** Amounts are drawn, rounded to pence and written as two-decimal strings (C1 R7); sums in the cash profiles are integer pence.
5. **Pinned numpy.** NumPy keeps a stream stable only within a version line, so `numpy==2.5.*` is pinned and a bump goes through `eval check` (3.1).
6. **Time.** Activity is generated in Europe/London local time (working hours, the England and Wales bank holidays of 2025 and 2026 committed in `dates.py`) and stored in UTC; `dates.COVERED` is 2025 and 2026, and a period outside it is refused.

#### 7.2.2 Records and ids

`records.py` builds plain C1 1.1.0 dicts (dataset `nr_synthetic`, `nr.v` "1.1", `nr.synthetic` true) for every schema the overlay writes: `Company`, `Organization`, `Person`, `Address`, `BankAccount`, `Ownership` (account holdings, shareholdings as Companies House bands or exact shares, consolidations), `Control`, `Directorship`, `Representation`, `Family`, `Associate`, `Sanction`, `Position`, `Occupancy` and `Payment`. `synthetic_kind` is `registry` for the register, `activity` for accounts, holdings and payments, and `list` for a record with a flag topic and its designation.

| What | Rule |
|---|---|
| World ids | `syn-w-<kind>-<6 digits>`, numbered in generation order (4.4) |
| Overlay ids | `syn-ov-<kind>-<first 16 hex of SHA-256 of seed, kind and key>`: nothing in an id says what role the record plays (C1 R9) |
| Company numbers | `SY6` to `SY8` plus five digits in a world, `SY9` plus five digits in an overlay |
| Account numbers | `NRSYN` plus ten digits from a hash of the seed and the account id, the next free number on a collision, skipping every number the base already uses (`Ctx.assign_account_numbers`, R8) |
| Postcodes | `QQ<district> <digit><letter><letter>`; `QQ` is not a UK postcode area |
| Synthetic offices and lists | jurisdiction `zz`; list authority "Synthetic Authority A" |
| Payments | `payer` and `beneficiary` are the account holders, `payerAccount` and `beneficiaryAccount` the accounts; `nr.channel` from the C1 enumeration; cash deposits come from a synthetic bank branch's `cash_ledger` account, cash withdrawals go to one |

No record carries a label (C1 R9): `test_bridge_rules_and_no_labels_in_records` checks that no record, id or property names a scenario, a typology, a role or a look-alike.

#### 7.2.3 The context, the bridge and names

`Ctx` (`ctx.py`) owns everything an overlay writes: records by id, payments kept as their C1 lines (a dict per payment would not fit beside Neo4j at scale; `Ctx.record(id)` parses one), the holder of every new account, the names already used, the bank branches and the shared background counterparties.

- **Background code** may give a base organisation an account and pay into and out of it, always to or from a synthetic counterparty.
- **Scenario code** works only through `ScenarioCtx`, which refuses any id the scenario did not create itself (or a bank branch ledger) with a `PermissionError`. A scenario therefore cannot reach a base entity, a base entity's account, or another scenario's entities (G1). `test_scenarios_never_reach_base_entities` tries.
- **The bridge check** (`overlay.check_bridge`) runs on the finished overlay, over every property that can name an entity (`overlay.REFERENCE_PROPERTIES`, `addressEntity` included): the only record that names a base entity is the account holding of a base organisation; a payment names a base entity only as the `payer` or `beneficiary` of an account such a holding holds; and no payment joins two accounts held by base entities (I15 and I16 before anything is written; the loader checks again over every reference, L18).
- **Names.** `NameSource` has five methods, each drawing only from the generator it is given: `person(rng, locale)` returns the spellings of one invented person and a gender (`en_GB`, `ar_SA`, `ru_RU`); `invented_person(rng, locale)` the same with an invented surname (two or three invented syllables in the person's script, PHASE-2.md M2.9's table), which `Ctx.person` uses for anyone with a list, PEP or RCA topic and for the relatives and associates of PEP personas, so that no realistic full name is ever put on a synthetic list; `company(rng, jurisdiction)` a neutral-word name with the jurisdiction's legal form; `street(rng)` and `town(rng)`. Listed persons take the synthetic nationality `zz` and a script the name stream chooses. M3.3 writes `namesource.py` as an adapter over the Phase 1 name modules and their denylist and Phase 2's syllable table (reference in the code book). A new name never repeats the name of a non-synthetic base record, and avoids the names of synthetic base records where it can (`BaseView.names`, `synthetic_names`). The scale world needs about 160,000 distinct company names, so the company space must hold at least 1,000,000. Word lists cannot rule out that a combination of ordinary words is a real company's name, so the data steward checks every company name of `synth-demo` against a loaded register before the demo is published (M3.8). Ordinary synthetic people have realistic names by design and are never on a list or flagged; only the list, PEP and RCA personas and their relatives carry invented surnames, and the same check counts their matches.

#### 7.2.4 Background activity

`BaseView.from_records` reads the base (record by record, never all at once) and, for a resolved profile, the resolution run's `canonical.csv`, so a merged entity counts once, through its anchor record. An organisation is **eligible** for an account when it is a `Company` or `Organization` from a registry or synthetic dataset, carries no flag topic, is not dissolved or closed, and (for a merged entity) none of its records is flagged or comes from a list or leak dataset. People are never eligible (decision 12).

`BackgroundConfig.share` of the eligible organisations get an account and activity for the whole period. The choice is a hash of the seed and the organisation's id compared with the share (`background.selected`), so it draws nothing from any stream and stays the same when the base grows. An organisation whose last accounts were filed as dormant gets an account and no activity.

Each active organisation gets, in London working hours: invoices from one to four customers every 10, 20 or 30 working days, with occasional credit notes; daily card settlements from an acquirer (card-taking sectors); cash banking one to five days a week at a random branch (cash sectors); salaries on the last working day of the month to its synthetic employees (most businesses have none) and PAYE on the 22nd of the next month; rent on the first working day; supplier payment runs every 5, 10 or 20 working days, scaled so that outflows come to 85 to 97 percent of inflows (a working balance, so the business does not pass on what it has just received); VAT a month and seven days after each quarter; and, for some, a loan drawdown with twelve repayments. Seasonal sectors close from October to March. Employees (synthetic people the overlay creates) pay rent, shop by card and draw cash.

Nothing in a base organisation's background is typology-shaped: no cash just under a threshold, no pass-through, no cycles, no quiet gap followed by a burst, no payments between two base organisations (`synthetic-transactions.md` 2.8). The look-alikes that test precision are planted as scenarios (7.2.5), among synthetic entities.

#### 7.2.5 Scenarios and look-alikes

`overlay.SCENARIOS` holds one module per typology, in catalog order. Each module defines `TYPOLOGY`, `ILLICIT` (variant and difficulty pairs), `LOOKALIKES` (kinds), `SPAN_DAYS` (how long the scenario runs), `LEAD_DAYS` (history it needs before its start) and two functions, `illicit(s, variant, difficulty, start)` and `lookalike(s, kind, start)`. Every scenario creates its own companies, people, addresses and accounts through `ScenarioCtx`, adds a few unlabelled ordinary payments to its accounts (`common.camouflage`, so a scenario account is not an account with nothing else on it), labels the payments and participants that make up the pattern, and calls `finish` with its parameters. Variants and look-alike kinds alternate in the order listed.

| Typology | Illicit variants (difficulty) | Look-alikes | Span, lead (days) |
|---|---|---|---|
| `structuring` | `single_account` (easy): 4 to 8 cash deposits of 9,100 to 9,980 within 1 to 4 days at 2 to 4 branches; `multi_account` (hard): 4 to 9 deposits of 8,600 to 9,990 over 2 or 3 accounts of one holder within 2 to 7 days | `daily_takings`, `deposit_cap` (each deposit capped at 9,500, an unconfirmed hypothesis, 7.3.1), `weekly_savings` | 40, 0 |
| `rapid_pass_through` | `funnel` (easy): 3 to 8 payers, 25,000 to 200,000 in 1 to 4 days, 90 to 98 percent sent on within 2 to 36 hours to 1 or 2 beneficiaries; `slow_funnel` (hard): dwell of 20 to 70 hours, 2 to 5 beneficiaries | `payroll_bureau`, `marketplace_settlement`, `escrow` (holds 20 to 40 days) | 45, 0 |
| `layering_chain` | `chain` (easy): 50,000 to 500,000 through 3 to 6 companies, each keeping 0.5 to 3 percent, onward within 2 to 48 hours, two or more intermediaries sharing an address or a director; `split_chain` (hard): one hop split in two and merged again, or one dwell of 60 to 100 hours | `supply_chain` (each tier adds a margin), `group_treasury` | 30, 0 |
| `circular_flow` | `round_trip` (easy): 30,000 to 400,000 through 2 to 5 companies, often abroad, back to the same account within 2 to 12 days; `same_holder_return` (hard): back to another account of the same holder, or a trip of 12 to 20 days | `refund`, `loan`, `cash_pool` | 45, 0 |
| `fan_in_collection` | `collector` (easy): 10 to 30 people's accounts, most of them years old (a fifth opened 10 to 60 days earlier: the senders are often victims, and recency belongs to the collector, 3.5), pay 300 to 2,000 each into one account opened 20 to 90 days earlier, within 2 to 6 days; 80 to 95 percent is paid on or withdrawn 1 to 3 days after the last contribution; `ring` (hard): 5 to 12 new accounts each fed by 2 to 4 people pass the money to one or two new hubs | `charity`, `landlord`, `crowdfunding` | 100, 70 |
| `fan_out_distribution` | `cash_out` (easy): one account pays 10 to 25 new accounts similar or round amounts within 1 to 2 days, most withdrawn or passed on within 1 to 4 days; `spread_out` (hard): amounts vary widely, about half move the money on | `payroll`, `dividend`, `event_refunds` | 100, 70 |
| `dormant_reactivation` | `reactivated` (easy): a few small payments, 200 to 300 quiet days, then 6 to 15 payments totalling 50,000 to 300,000 within 3 to 10 days, 5 to 30 days after a new director; `dormant_company` (hard): a dormant-filed holder, 150 to 260 quiet days, 4 to 10 payments of 15,000 to 60,000 in all; `capital_flip` (medium): a company 20 to 80 days old receives 80,000 to 400,000 in two or three payments and pays 85 to 100 percent on within five days | `seasonal`, `property_sale` (flagged by design: the shape is the same), `restart` | 25, 420 |
| `shell_chain` | `layered` (easy): a person or an ownerless company owns a chain of 3 to 5 companies in 2 to 4 jurisdictions, with a nominee and a professional director; `loop` (hard): 3 or 4 companies own each other in a loop, or a chain of only two companies | `group_holding`, `fund_vehicle` | 1, 0 |
| `mass_registration_address` | `factory` (easy): 25 to 60 companies at one address, most incorporated within a month, 2 or 3 nominee directors shared, payments among some; `quiet_factory` (hard): 18 to 30 companies over a year, one shared director, no payments | `registered_agent` (30 to 120 ordinary clients over years), `serviced_office` | 30, 0 |
| `sanctions_exposure` | `majority_chain` (easy): a listed entity owns 75 percent or more of a company directly or through one or two majority-held companies; `split_or_control` (hard): two listed owners above 25 percent each, or a listed person with a board appointment right, significant influence or a directorship and no shares | `minority_stake` (20 to 40 percent two links away), `diffuse_holding` (3 to 15 percent) | 1, 0 |
| `formation_agent_cluster` | `agent_factory` (easy): one agent, 12 to 30 companies incorporated within three weeks, most at the agent's address, 2 or 3 shared nominee directors, payments among a few; `spread_agent` (hard): 12 to 18 companies over 20 to 40 days, two directors shared across about half | `busy_agent` (40 to 80 clients over years), `group_formation` (10 to 14 group companies in one week; flagged by design) | 45, 0 |
| `recycled_directors` | `strawman` (easy): one person directs 12 to 20 unrelated new companies, eight or more within a month, resigns from some within three months, a few pay each other; `slow_strawman` (hard): 8 to 13 companies over four to eight months, no payments | `fund_director` (flagged by design), `group_director` | 240, 0 |
| `pep_exposure` | `family_vehicle` (easy): a PEP in office, a spouse, child or parent with 75 percent or more of a company that owns a second; `associate_vehicle` (hard): a business partner holds more than half of a company through two intermediate companies. PEPs, relatives and associates have invented surnames | `former_pep` (out of office 18 to 36 months, spouse owns a company), `distant_relative` (a cousin) | 1, 0 |
| `cash_commingling` | `front_business` (easy): four to eight times the cash of five to eight local peers of its sector, some on Sundays, most paid on to the owner and a relative; `blended_business` (hard): three to four times, no Sundays, about a third to the owner | `busy_business` (1.5 to 2.5 times, pays suppliers), `new_site` | 120, 0 |

A look-alike marked "flagged by design" has exactly the shape the definition describes; the detector is expected to alert on it, and the evaluation counts that alert against precision as a `lookalike` hit (7.6.2). Every look-alike exists to show a false positive the typology file names.

#### 7.2.6 The world

`world.generate(seed, WorldConfig, names)` makes the register of a synthetic profile. It plants no scenario and writes no labels: every pattern found in a world alone is background.

| `WorldConfig` field | Default (`synth-eval`) | What it controls |
|---|---|---|
| `companies`, `people` | 600, 900 | size of the register |
| `today` | 2026-07-01 | the register date: incorporations before it, appointments up to it |
| `agent_every` | 300 | one formation agent per this many companies; agents' and one serviced office's addresses host 25 to 150 (15 to 40) companies |
| `professional_every` | 200 | one professional director with many appointments per this many companies |
| `dissolved_share`, `dormant_share` | 0.05, 0.08 | dissolved companies; companies whose last accounts were filed as dormant |
| `corporate_owner_share`, `parent_owner_share`, `no_owner_share` | 0.15, 0.85, 0.06 | companies owned by another company, how many of those parents have an owner of their own, and companies with no recorded owner |
| `listed` | 6 | synthetic list entries (two of them hold small stakes in ordinary companies) |
| `peps` | 4 | politically exposed people holding synthetic offices in `zz`, with no links (exposure is planted only by the overlay, so the evaluation can count it) |
| `districts` | 30 | postcode districts, so businesses of one sector have local peers |

Sectors follow a fixed mix (services 22 percent, construction 12, retail 10, real estate and technology 8 each, and so on, `world.SECTORS`); foreign parents come from a fixed list of jurisdictions (`gb` most often, then `ie`, `nl`, `lu`, `je`, `gg`, `us`, `de`, `cy`, `vg`).

#### 7.2.7 The overlay

`overlay.generate(base_records, dataset_kinds, OverlayConfig, names, canonical_csv=None)` reads nothing but the resolution run's `canonical.csv` when it is given, and writes nothing; the CLI streams the base in and writes the result (M3.3, M3.4).

| `OverlayConfig` field | Default | Rule |
|---|---|---|
| `seed` | the profile's | the overlay seed (the world's seed when null) |
| `start`, `end` | 2025-01-01, 2026-07-01 | the activity period, 18 months |
| `split` | `dev` | `dev` or `test`; written into every label row; `test` only through `neonradar eval run --split test`, which a human runs (G11; `evaluate.run_seed` refuses it otherwise) |
| `illicit`, `lookalikes` | 10, 10 | per typology |
| `typologies` | all fourteen | which scenario modules run |
| `background` | `BackgroundConfig()` | 7.2.4 and 7.2.9 |

The steps: the base view; the background of every selected organisation; then, per typology in catalog order, its illicit scenarios and its look-alikes, numbered `scn-000001` upwards. Each scenario's start day is drawn from its own stream between the period start plus `max(LEAD_DAYS, 100)` days (`HISTORY_DAYS`: the detectors look back up to 90 days, so a scenario never sits at the left edge of the data) and the period end minus `SPAN_DAYS + 7`. Then account numbers, the bridge check, and the counts (`stats`: background organisations and employees, scenarios by typology, eligible and skipped organisations, records).

#### 7.2.8 Label files v2 and record files

**Record files** (`writer.py`): one `<name>.ftm.jsonl` per part with its `.manifest.json` (C1 1.1.0). Lines are the records in id order; `write_part` streams them and hashes them as it goes, and returns the file's SHA-256. Two runs differ only in the manifest's `created_at`.

**Label files** (`labels.py`), in `labels/` next to the records. Every CSV starts with `# synthetic: true` and `# label_schema: 2.0.0`; the Phase 1 columns come first, in their Phase 1 order, so a reader that selects columns by name keeps working; rows are sorted; booleans are `true` and `false`; files end with a newline.

| File | Columns or content |
|---|---|
| `scenarios.csv` | `scenario_id`, `typology`, `variant`, `is_lookalike`, `start_ts`, `end_ts`, `participants` (a Phase 1 column, left empty: `participants.csv` holds them), `difficulty`, `split`, `n_transactions`, `n_accounts`, `n_entities`, `n_relationships` |
| `transactions.csv` | `tx_id` (the payment's record id, which is its `PAID` id), `scenario_id`, `typology`, `step` (time order), `role`, `is_illicit`, `variant`, `is_lookalike`, `is_core` |
| `participants.csv` | `scenario_id`, `object_kind` (`entity`, `account`, `address`, `relationship`), `object_id` (the C2 id), `role`, `is_core` |
| `scenario_params.jsonl` | per scenario: `params` (what was drawn), `expected_metrics`, `stream_key`, `generator` (component and version) |
| `manifest.json` | `label_schema`, `synthetic`, `seed`, `records` (the record files' SHA-256), `counts` (scenarios by typology, variant and kind), `splits`, `generator_version` |

The evaluation reads these files with its own reader (`evaluation/harness.py`), because `neonradar_detect` never imports the generator, and refuses a file whose label schema major version is not 2.

#### 7.2.9 Calibration and measured sizes

The background is a plain UK small-business profile, not a model of any bank's book. Defaults of `BackgroundConfig`, each a published figure or a stated modelling choice (`synthetic-transactions.md` 2):

| Setting | Default | Basis |
|---|---|---|
| Businesses with no employees, with one to nine | 70 and 25 percent | 75 percent of UK businesses have no employees (`dbt_business_population_2025`) |
| Salary, monthly median | 2,300 (log-normal, sigma 0.35) | below a full-time median net of about 2,636 a month, which NeonRadar calculated from the ONS ASHE 2025 median gross of 39,039 a year (`ons_ashe_2025`) and the 2026-27 income tax and National Insurance rates (`govuk_income_tax_rates`), to allow for part-time jobs (modelling choice) |
| Payday and PAYE | last working day; 32 percent of payroll on the 22nd of the next month | GOV.UK PAYE deadlines (`govuk_paye`); the payday rule is a modelling choice |
| VAT | 7 to 11 percent of the quarter's receipts, one month and seven days after the quarter | GOV.UK VAT return deadlines (`govuk_vat_deadlines`); the rate of value added is a modelling choice |
| Rent | business median 1,500; personal median 1,400 for 60 percent of employees | ONS private rents: UK average 1,400 a month (August 2026, `ons_private_rent_2026`) |
| Card spending | 2 to 6 card payments a month per employee, median 15 (sigma 1.16) | UK Finance: about 8.9 debit card payments per adult per week, mean about 29 (`uk_finance_card_spending_2026`); fewer payments here to keep worlds small (modelling choice) |
| Cash | businesses bank cash 1 to 5 days a week, median 1,200 per banking day for five; employees withdraw a median of 100 | Post Office: average cash withdrawal about 140 (October 2025, `post_office_cash_2025`); the rest is a modelling choice |
| Customers, suppliers | 1 to 4 customers, 2 to 6 suppliers from shared pools | modelling choice |
| Working balance | outflows 85 to 97 percent of inflows over the period | modelling choice |
| Loans, refunds | 8 percent of businesses have a loan; 5 percent of invoices get a credit note | modelling choice (benign cycle shapes for `circular_flow`) |
| Calendar | London time, England and Wales bank holidays | GOV.UK bank holidays and clock changes (`govuk_bank_holidays`) |

**Measured on 18 and 19 October 2026** (prototype, 2 cores, Python 3.14.6):

| Profile | Records | Time | Peak memory | Graph |
|---|---|---|---|---|
| `synth-eval`, seed 1 | world 4,160; overlay about 375,000 (355,090 payments, 140 scenarios, 140 look-alikes) | about 20 s to generate, 7 s to build the in-memory graph, 40 s to run the fourteen detectors in memory | under 1 GB | 14,429 nodes, 367,333 relationships |
| `synth-demo` | world 2,060; overlay about 158,000 (150,963 payments, 42 scenarios, 42 look-alikes) | about 8 s to generate, 16 s to detect in memory | under 1 GB | 5,509 nodes, 155,916 relationships; 99 alerts, at least three for every typology |
| `synth-scale` (at 140,000 companies) | world 959,143; overlay 1,537,739 payments | 81 s and 67 s | 1.3 GB and 2.1 GB | 494,676 nodes and 2,054,473 relationships before `HAS_ADDRESS`; the profile adds 1.4 percent more companies and people to clear 500,000 nodes |

These are generator figures. The load into Neo4j and detection on Neo4j are measured in M3.8 and M3.9.

### 7.3 Typology reference

One subsection per typology, in catalog order. Each gives the definition as the detector reads it, its parameters with their bases, the variants and subjects, the pattern strength, the look-alikes, the corrections to PHASE-1.md 7.2, the test cases of its verbatim test file and its row on the CI seed. The typology researchers approve these subsections and the test files together (1.4) and review the parameters before the freeze (M3.11). The sources and their quotations are in `typology-detection-definitions.md`, section by section; source keys are those of `docs/sources/bibliography.yaml` (7.8).

How to read the parameter tables:

- **Default** is the value in the typology file and in the detector's `Params`; a test checks that they agree. **Bounds** are the typology file's `min` and `max`: `catalog.params_for` refuses a profile override outside them.
- **Basis** is a source key when a source gives the value, and "modelling choice" when no source gives a number (most thresholds: AML sources describe shapes, not cut-offs). A modelling choice is a decision of this project, which the typology researchers may change before the freeze.
- **Work limits** (`max_candidates`, `max_starts`, `max_paths`, `max_links`, `max_steps`, `max_branching`, `max_frontier`, `max_evidence_companies`) bound the work and the evidence, not the definition. They are frozen like the others, and anything they cut is counted in the run summary.
- **CI seed** is the typology's row of `eval/baselines/ci.json` on seed 1 of `synth-eval` (ten illicit scenarios and ten look-alikes): alerts; true alerts; planted scenarios detected; look-alikes alerted; and the other kinds when they are not zero (7.6.2). The development figures over five seeds are in 7.6.5.
- Every headline below is the `headline_structural` form, with its placeholders shown without their filters (`{total_amount}` for `{total_amount|money}`, `{pass_ratio} percent` for `{pass_ratio|pct}`, `{span_days} days` for `{span_days|n:day}`); the typology file holds the exact template. On synthetic data the alert uses `headline_synthetic`, the same text after "Synthetic scenario: " (7.5.2).

#### 7.3.1 `structuring` (core, 0.2.0)

**Definition.** Cash deposits (`PAID` from a `cash_ledger` account with `channel` `cash_deposit`) into the accounts of one holder: at least `min_deposits` of them within `window_days`, each in the band just below the threshold, and in-band deposits at least `min_band_share` of the holder's cash deposits in that window. A deposit is in band when `threshold * (1 - band) <= amount` and it is below the threshold. Whether exactly the threshold is below it depends on the rule the threshold stands for. The US report covers cash "of more than $10,000" (`cfr_31_1010_311_2026`), so 10,000 is below it. No UK bank cash-deposit report was found (UNVERIFIED as a negative, `typology-detection-definitions.md` 1), so GBP is modelled on the high value dealer rule, "£10,000 or more" (reg 27(3), `mlr_reg_27_2017`; reg 14 defines the dealer by "at least £10,000", `mlr_reg_14_2017`), and EUR on the AMLR's due diligence threshold, "at least EUR 10 000" (Article 19(1)(b), `eu_amlr_2024`, which applies from 10 July 2027); under both, exactly 10,000 is not below. Both mappings are modelling choices. The AMLR's report of cash deposits at banks covers deposits "above the limit" (Article 80(4)), which would put exactly EUR 10,000 below it: the typology researchers may add EUR to `below_inclusive_currencies`, the currencies that use the US form (1.2). Structuring is "in any amount" and "on one or more days", and the transactions "need not exceed the $10,000 reporting threshold at any single financial institution on any single day" (`cfr_31_1010_100_2026`), so a daily total above the threshold adds to the strength but is not required. Overlapping qualifying windows of one holder merge into one finding. C2 cannot say who carried the cash or why, and the purpose is part of the legal definition, so the alert describes deposits only.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `threshold` | 10,000 | 0 to 100,000 | `cfr_31_1010_311_2026`, `mlr_reg_27_2017`, `eu_amlr_2024`; the same number in every currency, and the UK and EU rules standing for bank deposits, are modelling choices |
| `band` | 0.1 | 0 to 0.5 | modelling choice: FFIEC says "just below" with no width (`ffiec_appendix_f`) |
| `below_inclusive_currencies` | USD | | `cfr_31_1010_311_2026` ("more than"); GBP ("or more", `mlr_reg_27_2017`) and EUR ("at least", `eu_amlr_2024`) as modelled above |
| `window_days` | 7 | 1 to 70 | modelling choice within "one or more days" (`cfr_31_1010_100_2026`) |
| `min_deposits` | 3 | 1 to 30 | modelling choice |
| `min_band_share` | 0.5 | 0 to 1 | modelling choice: a cash business whose takings vary does not qualify on a few in-band days |
| `max_candidates` | 100,000 | 1 to 1,000,000 | work limit |

**Variants.** `single_account`; `multi_account` (deposits into two or more accounts of the holder). **Subjects:** `holder`, `receiving_account` (each account). **Metrics:** `deposits`, `total_amount`, `threshold`, `band_low`, `currency`, `branches`, `accounts`, `days`, `span_days`, `max_day_total`, `band_share`.

**Pattern strength** = 0.3 * min(1, deposits / (2 * `min_deposits`)) + 0.3 * mean closeness to the threshold (0 at the band's lower edge, 1 at the threshold) + 0.2 * min(1, (branches - 1) / 2) + 0.2 when one day's in-band total exceeds the threshold.

**Headline.** "{deposits} cash deposits just below {threshold} within {span_days} days, {total_amount} in total", for example "4 cash deposits just below GBP 10,000 within 3 days, GBP 38,900 in total".

**Look-alikes.** Planted: `daily_takings`, `deposit_cap` (each deposit capped at 9,500, as an insurer's or a carrier's limit might do: a Phase 1 hypothesis that no source read on 18 October confirmed, kept because it is the hardest shape to tell apart), `weekly_savings`. The typology file's false-positive notes: a cash business banking its daily takings; a business that caps each cash deposit (unconfirmed); a person saving the same sum every week. FFIEC's own look-alike is a machine limit: "several bank deposits below a specified threshold" at an ATM (`ffiec_appendix_f`). A deposit cap does put deposits in the band on busy days; the minimum count and the band share keep most of them out.

**Corrections to PHASE-1.md 7.2.** The band is closed at the top for USD and, as modelled, open for GBP and EUR; a daily total above the threshold is a strength term, not a condition (3.5).

| Test (`test_detector_structuring.py`) | Records | Expected |
|---|---|---|
| `test_burst_below_threshold_across_branches` | four deposits of 9,300 to 9,800 at three branches over three days | one `single_account` finding with all four deposits, three branches, three days, a day total of 19,200 and three steps (one per day) |
| `test_two_accounts_of_one_holder` | three deposits into two accounts of one company | `multi_account`; subjects the holder and both accounts |
| `test_lookalikes_are_not_found` | a shop banking 2,800 to 15,000 on twelve days; a person saving 9,500 a week; two deposits of 9,500 on one day | nothing |
| `test_band_edges` | GBP 9,000 (the lower edge, in band), 9,999.99 (in), 10,000 (out) | nothing (two in band); a fourth deposit of 9,500 gives one finding with three deposits and a band share of 0.75 |
| `test_a_usd_deposit_of_exactly_the_threshold_is_below_it` | three deposits of exactly 10,000 into a USD account and three into a GBP account | one finding, on the USD account |
| `test_headline_through_the_runner` | four deposits of 9,500 to 9,900 into a person's account | the headline "Synthetic scenario: 4 cash deposits just below GBP 10,000 within 3 days, GBP 38,900 in total" |

**CI seed.** 15 alerts; 10 true; 10 of 10 detected; 3 of 10 look-alikes alerted; 2 alerts on other typologies' scenarios (the cash deposits of two `cash_commingling` front businesses).

#### 7.3.2 `rapid_pass_through` (core, 0.2.0)

**Definition.** An account that passes on what it receives within hours or days, from several sources. FATF and Egmont describe a "pay-through" or "transit" account with "a rapid movement of high-volume transactions and a small end-of-day balance without clear business reasons" (`fatf_egmont_tbml_indicators_2021`); FinCEN's funnel account is one "in one geographic area that receives multiple cash deposits, often in amounts below the cash reporting threshold, and from which the funds are withdrawn in a different geographic area with little time elapsing between the deposits and withdrawals" (`fincen_fin_2014_a005`); FFIEC lists transfers that are "Almost immediately" wired on (`ffiec_appendix_f`). The detector uses the speed and the residual only: C2 records neither where a deposit or a withdrawal was made nor the business reasons, and its sources need not be cash. No source gives a number of hours.

Per account and currency, inflows are matched to later outflows first in, first out, over the window and the `history_days` before it, so money the account already held is spent first: a business with a working balance does not pass on what it has just received. The part of an inflow that leaves within `max_dwell_hours` of arriving counts as passed through. Money is fungible, so this allocation is a modelling choice, not a fact. Windows that start less than `history_days` after the first payment in the data are skipped, because the earlier balance is unknown there (left-censoring). A window of `window_days` starting at an inflow qualifies when its inflows total at least `min_inflow`, at least `min_pass_ratio` of that total was passed through, and the inflows came from at least `min_sources` accounts. Few beneficiaries add to the strength but are not required: "a small number of foreign beneficiaries" (`ffiec_appendix_f`) is a red flag, not the definition. Among qualifying windows the detector takes the one with the largest passed amount, then the largest that overlaps none already taken, so findings never share an inflow.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `window_days` | 7 | 1 to 70 | modelling choice |
| `max_dwell_hours` | 72 | 1 to 720 | modelling choice anchored on "within a few days of receipt" (`fatf_pml_2018`) |
| `min_inflow` | 10,000 | 0 to 100,000 | modelling choice |
| `min_pass_ratio` | 0.9 | 0 to 1 | modelling choice for "a small end-of-day balance" (`fatf_egmont_tbml_indicators_2021`) |
| `min_sources` | 3 | 1 to 30 | modelling choice |
| `max_beneficiaries` | 3 | 1 to 30 | modelling choice, strength only; anchored on "a small number of foreign beneficiaries" (`ffiec_appendix_f`) |
| `history_days` | 90 | 1 to 900 | modelling choice (the balance before the window) |
| `max_candidates` | 100,000 | 1 to 1,000,000 | work limit |

**Variants.** None. **Subjects:** `pass_through_account`, `holder`. **Metrics:** `inflow_amount`, `passed_amount`, `pass_ratio`, `currency`, `sources`, `beneficiaries`, `median_dwell_hours`, `window_days`.

**Pattern strength** = 0.35 * pass ratio + 0.3 * (1 - median dwell / `max_dwell_hours`) + 0.15 * min(1, sources / (2 * `min_sources`)) + 0.2 * concentration, where concentration is 1 with at most `max_beneficiaries` beneficiaries and `max_beneficiaries` / beneficiaries above that.

**Headline.** "{pass_ratio} percent of {inflow_amount} received from {sources} accounts paid on within {window_days} days".

**Look-alikes.** Planted: `payroll_bureau` (one client in, many employees out), `marketplace_settlement` (many buyers in, one payout to the merchant next day), `escrow` (holds 20 to 40 days). False-positive notes: payroll bureaus funding salaries; marketplaces settling with sellers; escrow and client accounts. A marketplace settlement account has exactly this shape and is found (the test says so); a payroll bureau has one source, and escrow holds too long.

**Corrections.** None to the Phase 1 entry; the dwell, ratio and source counts are now parameters with bases, and the first-in, first-out allocation is documented as a modelling choice.

| Test (`test_detector_rapid_pass_through.py`) | Records | Expected |
|---|---|---|
| `test_funnel_found_and_slow_dwell_not` | four people pay 6,000 each into an account over two days; 23,500 leaves for an account abroad two days later | one finding with all five payments, a pass ratio of 0.9792, four sources, one beneficiary; the same money leaving after seven days gives nothing |
| `test_lookalikes` | a payroll bureau (one client, twenty employees); an escrow account holding for six weeks; then a marketplace account (ten buyers, one payout next day) | nothing for the first two; the marketplace is found (a documented false positive) |
| `test_two_bursts_give_two_findings` | the same funnel twice, 18 days apart | two findings, in time order |

**CI seed.** 20 alerts; 8 true; 8 of 10 detected; 3 of 10 look-alikes alerted; 4 on other typologies' scenarios (`fan_in_collection` collectors, which also pay on fast); 5 on background activity.

#### 7.3.3 `layering_chain` (core, 0.2.0)

**Definition.** Funds passed on through a chain of accounts of different holders. In layering, "the launderer engages in a series of conversions or movements of the funds to distance them from their source", for example by wiring them "through a series of accounts at various banks" (`fatf_faq`); FATF and Europol describe layers of companies in several jurisdictions (`fatf_pml_2018`, `europol_efecta_2023`).

Starts are payments of at least `min_amount`. Each next hop leaves the account the previous hop reached, within `max_dwell_hours` after it, in the same currency, for between `min_hop_ratio` and `1 + max_hop_gain` times the previous amount, to an account none of whose holders held an account earlier in the chain (so a return to the origin's side is left to `circular_flow`). A chain of `min_hops` to `max_hops` payments whose last amount is at least `min_retained_ratio` of its first is a finding, unless it lies inside a longer chain that is one. Europol puts laundering fees at "5-20 % of the laundered sum" (`europol_efecta_2023`), a total, so the retained ratio is checked end to end. Splits and merges are not followed: a chain that splits is found only up to the split, a documented limitation that the `split_chain` scenarios measure.

What makes a chain more than commerce is the registry around it: the detector counts pairs of holders in the chain that share a registered address, a director or an agent, and intermediate accounts with little other activity (at most `max_quiet_payments` payments in the `quiet_days` around the chain, outside it). These are strength terms. On a real profile R-REAL withholds every chain that touches a real entity, so they only ever combine synthetic data.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_hops` | 3 | 2 to 8 | modelling choice (no source gives a count) |
| `max_hops` | 6 | 1 to 8 | modelling choice; C2 traversals stop at 8 |
| `max_dwell_hours` | 72 | 1 to 720 | modelling choice, as `rapid_pass_through` |
| `min_hop_ratio` | 0.85 | 0 to 1 | modelling choice (a fee per hop) |
| `max_hop_gain` | 0.02 | 0 to 0.5 | modelling choice (rounding and small top-ups) |
| `min_retained_ratio` | 0.8 | 0 to 1 | `europol_efecta_2023` (fees of 5 to 20 percent of the sum) |
| `min_amount` | 10,000 | 0 to 100,000 | modelling choice |
| `quiet_days` | 30 | 1 to 300 | modelling choice (quiet intermediaries; Annex E's "No personnel", `fatf_egmont_concealment_2018`) |
| `max_quiet_payments` | 5 | 1 to 50 | modelling choice |
| `max_starts`, `max_branching`, `max_frontier` | 1,000,000; 10; 50,000 | 1 to 10,000,000; 1 to 100; 1 to 500,000 | work limits (7.1.3) |

**Variants.** None. **Subjects:** `origin`, `origin_holder`, `destination`, `destination_holder`. **Metrics:** `chain_length`, `first_amount`, `last_amount`, `currency`, `duration_hours`, `duration_days`, `retained_ratio`, `longest_dwell_hours`, `holders`, `linked_holder_pairs`, `quiet_intermediaries`.

**Pattern strength** = 0.25 * min(1, (hops - 2) / 4) + 0.25 * retained ratio + 0.2 * (1 - longest dwell / `max_dwell_hours`) + 0.15 * share of quiet intermediaries + 0.15 * min(1, linked holder pairs / 2).

**Headline.** "{first_amount} passed on through {chain_length} transfers between accounts of different holders within {duration_days} days".

**Look-alikes.** Planted: `supply_chain` (each tier adds a margin, so hop gains break the amount rule), `group_treasury` (sweeps between companies of one group). False-positive notes: supply chains paying on for goods; group treasury moving funds between subsidiaries.

**Corrections.** None; the fee range is now the end-to-end retained ratio of Europol's figure rather than a per-hop rule.

| Test (`test_detector_layering_chain.py`) | Records | Expected |
|---|---|---|
| `test_four_hop_chain_with_shared_address` | 250,000 through four payments over four days; the three intermediaries share a registered address | one finding: the four payments as the first four steps, three linked holder pairs, three quiet intermediaries, seven steps in all; subjects origin, origin holder, destination, destination holder |
| `test_prefix_and_suffix_are_not_reported_separately` | a chain of five payments | one finding of length 5, not its three- and four-payment parts |
| `test_dwell_amount_and_holder_rules` | a chain with a six-day dwell; a chain whose second hop takes only 60 percent; a chain that ends at another account of the first holder | nothing |
| `test_three_hops_found_when_allowed_but_not_below_min_amount` | a three-payment chain starting at 9,000 | nothing by default (below `min_amount`); one finding with `min_amount` 5,000 |

**CI seed.** 28 alerts; 8 true; 8 of 10 detected; 6 of 10 look-alikes alerted; 14 on other typologies' scenarios, all inside `circular_flow` round trips, whose outward legs are chains between different holders.

#### 7.3.4 `circular_flow` (core, 0.2.0)

**Definition.** Funds that return to the originating account, or to another account of the same holder. Annex E lists a transaction that "appears cyclical (outgoing and incoming transactions are similar in size and are sent to, and received from, the same accounts, indicating that outgoing funds are being returned with little loss)" (`fatf_egmont_concealment_2018`); FATF's proxy networks return funds "to the accounts controlled by the initial clients" (`fatf_pml_2018`), which supports the same-holder variant.

Starts are payments of at least `min_amount`. From each start the expansion (7.1.3) follows later payments in the same currency, each between `min_return_ratio` and `1 + max_hop_gain` times the first amount, within `max_window_days` of the first payment, through accounts not visited yet. A cycle closes at the first account that is the origin (variant `same_account`) or, with `same_holder`, another account of one of the origin's holders (variant `same_holder`). It is a finding when it has `min_hops` to `max_hops` payments and returns at least `min_return_ratio` of the first amount. A cycle back to the very account it left needs `min_hops_same_account` payments: a payment straight back is the shape of a refund, a loan repaid or a cash pool sweep, and on the development worlds the 130 extra alerts that a two-payment minimum gave were none of them true: 50 on look-alikes, 50 on other typologies' scenarios and 30 on background activity (7.6.5). A return to another account of the same holder counts from two payments. Time order makes each cycle start at its earliest payment, so it is found once.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_hops` | 2 | 2 to 8 | Annex E "sent to, and received from, the same accounts" allows two payments (`fatf_egmont_concealment_2018`) |
| `min_hops_same_account` | 3 | 2 to 8 | modelling choice from the development figures (7.6.5) |
| `max_hops` | 6 | 1 to 8 | modelling choice |
| `max_window_days` | 14 | 1 to 140 | modelling choice |
| `min_return_ratio` | 0.8 | 0 to 1 | "returned with little loss" (`fatf_egmont_concealment_2018`); Europol's fee range (`europol_efecta_2023`) |
| `min_amount` | 1,000 | 0 to 10,000 | modelling choice (Phase 1 default) |
| `max_hop_gain` | 0.05 | 0 to 0.5 | modelling choice |
| `same_holder` | true | | `fatf_pml_2018` (funds returned to accounts the initial clients control) |
| `max_starts`, `max_branching`, `max_frontier` | 1,000,000; 20; 50,000 | 1 to 10,000,000; 1 to 200; 1 to 500,000 | work limits (7.1.3) |

**Variants.** `same_account`, `same_holder`. **Subjects:** `origin`, `origin_holder`, and `return_account` for `same_holder`. **Metrics:** `cycle_length`, `sent_amount`, `returned_amount`, `currency`, `duration_hours`, `duration_days`, `return_ratio`, `return_point`.

**Pattern strength** = 0.5 * return ratio + 0.3 * (1 - duration / window) + 0.2 * min(1, (hops - 1) / 4), clipped to [0, 1].

**Headline.** "Funds returned to {return_point} through {cycle_length} transfers within {duration_days} days", where the return point is "the originating account" or "another account of the same holder".

**Look-alikes.** Planted: `refund`, `loan`, `cash_pool`. False-positive notes: refunds and payment reversals; loan drawdown followed by repayment; intra-group cash pooling and treasury sweeps. The group variant (back to an account of another company in the same group) is not built: it would flag routine treasury (`typology-detection-definitions.md` 4).

**Corrections.** Both variants, from Phase 3; the Phase 1 query `(a)-[:PAID]->{2,6}(a)` is replaced (decision 6). PHASE-1.md M1.9b case F now expects no alert and one `activity_on_real` (decision 3).

| Test (`test_detector_circular_flow.py`) | Records | Expected |
|---|---|---|
| `test_phase1_cases_a_to_e` | Phase 1's cases: A (four payments back to the origin in seven days), B (three payments), C (a hop earlier than the one before it), D (a 40-day trip), E (a last payment of 36,000 of 120,000) | A and B only; A is `same_account` with length 4, a return ratio of 0.96, seven days and a strength of 0.7946, one step per payment |
| `test_same_holder_return` | 80,000 out of one account and 78,000 back into another account of the same company | `same_holder`, the return point "another account of the same holder", subjects origin, origin holder, return account; nothing with `same_holder` off |
| `test_hop_above_first_amount_and_own_account_transfer_are_not_cycles` | a cycle whose second hop is 2.5 times the first; a transfer between two accounts of one holder followed by two payments back | only the two-payment `same_holder` cycle that starts at the second account |
| `test_payment_straight_back_needs_three_hops_by_default` | 5,000 paid and the same 5,000 paid back two days later | nothing; found with `min_hops_same_account` 2 (the documented false positive) |
| `test_case_f_real_holder_is_reported_for_the_policy_to_withhold` | case A with a non-synthetic look-alike holder | the detector reports it, with `activity` set and the holder among the subjects; the runner then withholds it (`test_alert_builder.py`) |

**CI seed.** 10 alerts; 10 true; 10 of 10 detected; no look-alike alerted.

#### 7.3.5 `fan_in_collection` (core, 0.2.0)

**Definition.** Many unrelated accounts paying one account in a short window, which passes the money on; and a connected group of recently opened accounts (the ring). A money mule "receives money from a third party in their bank account and transfers it to another one or takes it out in cash" (`europol_money_muling`; also `fincen_mule_advisory_2020`). Sources tie recency and short use to the accounts that collect and pass on: "large deposits and withdrawals during a short time period after opening" (`ffiec_appendix_f`), accounts used "for a specific and limited period of time" (`fatf_cyber_fraud_2023`). The senders are often victims (`typology-detection-definitions.md` 5, on Europol's description), so recency is tested on the collector, never on the senders, and no text describes a sender as a participant.

**Variant `collector`.** Per account and currency (cash deposits excluded), a window of `window_days` starting at an inflow qualifies when at least `min_senders` accounts paid in at least `min_total`, at least `min_person_share` of them are held by people, at most `max_prior_share` of them had a payment with the account (either way) in the `prior_days` before the window, and the account paid on at least `min_onward_ratio` of the inflow by `onward_hours` after the window's last inflow. Windows that start less than `prior_days` after the first payment in the data are skipped, because earlier relationships cannot be judged there. A collector account opened within `new_account_days` before the window adds to the strength. Findings never share an inflow (largest total first).

**Variant `ring`.** The payments of the window between two accounts that were each opened at most `new_account_days` before the payment form weakly connected components (GDS on Neo4j, union-find in the oracle, 7.1.6). A component of `min_ring_accounts` to `max_ring_accounts` accounts, at least `min_person_share` of them held by people, moving at least `min_total`, with one to three hubs (accounts paid by at least three other accounts of the component) that at least half of the component's accounts pay, is a finding. Its evidence adds what fed the ring (payments into its accounts from outside it in the `window_days` before its first payment and during it) and what left it (the hubs' payments out up to `onward_hours` after its last payment).

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `window_days` | 7 | 1 to 70 | modelling choice |
| `min_senders` | 10 | 1 to 100 | modelling choice |
| `min_total` | 5,000 | 0 to 50,000 | modelling choice |
| `min_person_share` | 0.8 | 0 to 1 | modelling choice (a mule receives money "from a third party", `europol_money_muling`; the share of people among the senders is NeonRadar's) |
| `prior_days` | 90 | 1 to 900 | modelling choice ("no prior relation") |
| `max_prior_share` | 0.2 | 0 to 1 | modelling choice |
| `onward_hours` | 72 | 1 to 720 | modelling choice, as `rapid_pass_through` |
| `min_onward_ratio` | 0.8 | 0 to 1 | modelling choice |
| `new_account_days` | 90 | 1 to 900 | modelling choice: sources say "a short time period after opening" with no number (`ffiec_appendix_f`, `europol_efecta_2023`) |
| `ring` | true | | modelling choice (rings of new accounts, `fatf_cyber_fraud_2023`) |
| `min_ring_accounts`, `max_ring_accounts` | 5, 200 | 1 to 50; 1 to 2,000 | modelling choice; the upper bound keeps a component that background payments joined from becoming one alert |
| `max_candidates` | 100,000 | 1 to 1,000,000 | work limit |

**Subjects:** `collector` (each hub for a ring), `collector_holder`. **Metrics:** `senders`, `total_amount`, `currency`, `window_days`, `person_share`, `prior_share`, `onward_ratio`, `onward_beneficiaries`, `collector_account_days`, `ring_accounts`, `hubs`, `span_days`, `feeding_share`, `fed_payments`, `out_payments`.

**Pattern strength** (collector) = 0.3 * min(1, senders / (2 * `min_senders`)) + 0.25 * (1 - prior share) + 0.25 * min(1, onward ratio) + 0.2 when the collector account is new. (Ring) = 0.4 * share of accounts paying a hub + 0.3 * min(1, accounts / (2 * `min_ring_accounts`)) + 0.3 * person share.

**Headlines.** Collector: "{senders} accounts paid {total_amount} into one account within {window_days} days, and {onward_ratio} percent of it was paid on". Ring: "{ring_accounts} recently opened accounts paying into {hubs} collecting accounts, {total_amount} in total".

**Look-alikes.** Planted: `charity`, `landlord`, `crowdfunding`. False-positive notes: donation drives; rent collection by a landlord; crowdfunding campaigns paying their beneficiary. A crowdfunding campaign that pays its beneficiary at once has the collector's shape and is sometimes found.

**Corrections.** "Often from recently opened accounts" applied to the senders in PHASE-1.md 7.2 entry 5; it applies to the collector (3.5).

| Test (`test_detector_fan_in_collection.py`) | Records | Expected |
|---|---|---|
| `test_collector_opened_recently_pays_on` | ten people with old accounts pay 800 each into a person's account opened two weeks earlier; 7,500 leaves for an account abroad; the same without the onward payment within 72 hours | one `collector` finding: ten senders, a collector account 14 days old, an onward ratio of 0.9375, no prior relationship, a strength of 0.8344; nothing for the late version |
| `test_charity_and_landlord_lookalikes` | forty donors give 200 each to a charity that keeps the money; ten tenants pay rent for three months to a landlord who pays a lender | nothing (the donations stay; the tenants paid before) |
| `test_ring_of_new_accounts` | four new accounts each fed by two old accounts pay a new hub, which pays a sixth new account | one `ring` finding: six accounts, one hub, eight feeding payments in the evidence, a feeding share of 0.6667; nothing with `ring` off |

**CI seed.** 19 alerts; 10 true; 10 of 10 detected; 4 of 10 look-alikes alerted; 2 partial; 3 on other typologies' scenarios (the `marketplace_settlement` look-alikes of `rapid_pass_through`).

#### 7.3.6 `fan_out_distribution` (core, 0.2.0)

**Definition.** One account paying many new counterparties in a short window, who then move the money on. FinCEN: "An unusually large number and variety of beneficiaries receive wire transfers from one company" (`fincen_fin_2006_g014`); FFIEC: "Unusually large number and variety of beneficiaries are receiving funds transfers from one company" (`ffiec_appendix_f`); money split and "forwarded to non-related multiple accounts" (`fatf_egmont_tbml_indicators_2021`). Per account and currency, a window of `window_hours` starting at an outflow qualifies when it pays at least `min_recipients` accounts at least `min_total` in all, at most `max_prior_share` of the recipients had a payment with the account (either way) in the `prior_days` before the window, and at least `min_onward_share` of the recipients paid out at least `onward_fraction` of what they received within `onward_hours` of receiving it (cash withdrawals or transfers). Similar amounts and round amounts add to the strength but are not required. Windows that start less than `prior_days` after the first payment in the data are skipped. Findings never share an outflow (largest total first). The onward condition is what separates the pattern from payroll: salaries stay with the employees.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `window_hours` | 72 | 1 to 720 | modelling choice |
| `min_recipients` | 10 | 1 to 100 | modelling choice |
| `min_total` | 5,000 | 0 to 50,000 | modelling choice |
| `prior_days` | 90 | 1 to 900 | modelling choice ("no prior relation") |
| `max_prior_share` | 0.2 | 0 to 1 | modelling choice |
| `max_amount_cv` | 0.2 | 0 to 1 | strength only; modelling choice |
| `round_unit` | 100 | 0 to 1,000 | strength only; modelling choice (the round-amount indicator of `fatf_egmont_tbml_indicators_2021` is about trade) |
| `onward_hours` | 72 | 1 to 720 | modelling choice |
| `onward_fraction` | 0.8 | 0 to 1 | modelling choice |
| `min_onward_share` | 0.5 | 0 to 1 | modelling choice |
| `max_candidates` | 100,000 | 1 to 1,000,000 | work limit |

**Variants.** None. **Subjects:** `distributor`, `distributor_holder`. **Metrics:** `recipients`, `total_amount`, `currency`, `window_hours`, `amount_cv`, `round_share`, `prior_share`, `onward_share`.

**Pattern strength** = 0.3 * min(1, recipients / (2 * `min_recipients`)) + 0.3 * (1 - prior share) + 0.2 * onward share + 0.2 * max(amount similarity, round share), where amount similarity is 1 - min(1, coefficient of variation / `max_amount_cv`).

**Headline.** "One account paid {total_amount} to {recipients} new counterparties within {window_hours} hours, and {onward_share} percent of them paid it on".

**Look-alikes.** Planted: `payroll`, `dividend`, `event_refunds`. False-positive notes: payroll; dividends to shareholders; refunds after a cancelled event.

**Corrections.** None.

| Test (`test_detector_fan_out_distribution.py`) | Records | Expected |
|---|---|---|
| `test_distribution_to_new_accounts_that_cash_out` | one company pays 950 each to ten new accounts, which withdraw 900 in cash two days later | one finding with all twenty payments, ten recipients, an onward share of 1.0, an amount variation of 0 |
| `test_payroll_and_refund_lookalikes` | three months of salaries to ten employees who spend a little; twelve refunds of 400 to earlier buyers | nothing (repeat recipients, money kept) |
| `test_first_payroll_is_not_found_because_salaries_stay` | a first payroll to ten new employees, who spend 250 each | nothing (the money stays) |

**CI seed.** 9 alerts; 9 true; 9 of 10 detected; no look-alike alerted.

#### 7.3.7 `dormant_reactivation` (core, 0.2.0)

**Definition.** An account with little activity for a long time that suddenly moves large sums in and out, often soon after a change of director or owner; and two company variants. FFIEC: "an account with little activity may suddenly experience large deposit and withdrawal activity" (`ffiec_appendix_f`); FATF and Egmont: "unexplained periods of dormancy" and "recently re-activated" entities (`fatf_egmont_tbml_indicators_2021`); Annex E: legal persons with "a long period of inactivity following incorporation" followed by "a sudden and unexplained increase in financial activities", or that "receive large sums of capital funding quickly following incorporation/formation, which is spent or transferred elsewhere in a short period of time without commercial justification" (`fatf_egmont_concealment_2018`). No AML source gives a period; UK law's dormant account is one with no transaction "by or on the instructions of the holder" for 15 years, for unclaimed balances (`dormant_accounts_act_2008`), and a dormant company is one with no significant accounting transaction (`ca_dormant_company_s1169_2006`).

**Variant `account`.** A quiet period is at least `min_gap_days` with at most `max_quiet_payments` payments totalling at most `max_quiet_amount`, between a payment of the account (or its opening date) and the payment that ends it. An opening date counts only when it is on or after the first payment in the data: before that, the data cannot say whether the account was quiet (left-censoring). The quiet period must end inside the window. A burst follows: the payments from the one that ends the quiet period to `burst_days` after it, at least `min_burst_payments` of them, in both directions, totalling at least max(`min_burst_amount`, `burst_ratio` times the account's mean monthly volume before the quiet period). The ratio keeps seasonal businesses and genuine restarts, which come back at their usual level, below the threshold. A director appointed to, or an owner acquiring, a holder within `change_days` before the burst is the change event.

**Variant `dormant_company`.** An account whose holder's last accounts were filed as dormant (`accounts_category` `DORMANT`) with a burst in the window, quiet period or not; an account finding on such an account takes this variant. **Variant `new_company`.** A burst that starts at most `new_company_days` after the holder's incorporation, in which the inflow alone is at least `min_burst_amount`, the three largest inflows bring at least `min_inflow_concentration` of it, and at least `min_moved_on` of it leaves within the burst. A new business's ordinary trading (receipts and supplier payments of similar size) does not qualify.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_gap_days` | 180 | 1 to 1,800 | modelling choice (no source gives a period; Phase 1 default) |
| `max_quiet_payments` | 2 | 1 to 20 | modelling choice for "little activity" (`ffiec_appendix_f`) |
| `max_quiet_amount` | 1,000 | 0 to 10,000 | modelling choice |
| `burst_days` | 14 | 1 to 140 | modelling choice |
| `min_burst_payments` | 4 | 1 to 40 | modelling choice |
| `min_burst_amount` | 50,000 | 0 to 500,000 | modelling choice |
| `burst_ratio` | 10 | 1 to 100 | modelling choice |
| `change_days` | 30 | 1 to 300 | modelling choice |
| `company_variants` | true | | `fatf_egmont_concealment_2018` (Annex E), `ca_dormant_company_s1169_2006` |
| `new_company_days` | 90 | 1 to 900 | modelling choice for "quickly following incorporation" (`fatf_egmont_concealment_2018`) |
| `min_inflow_concentration` | 0.8 | 0 to 1 | modelling choice ("large sums of capital funding") |
| `min_moved_on` | 0.8 | 0 to 1 | modelling choice ("spent or transferred elsewhere") |
| `max_candidates` | 100,000 | 1 to 1,000,000 | work limit |

**Subjects:** `reactivated_account`, `holder`. **Metrics:** `gap_days`, `quiet_payments`, `pre_gap_monthly_mean`, `burst_threshold`, `burst_payments`, `burst_in_amount`, `burst_out_amount`, `burst_amount`, `currency`, `burst_days`, `change_event`.

**Pattern strength** = 0.3 * min(1, gap days / (2 * `min_gap_days`)) (0.3 for the company variants) + 0.3 * min(1, burst amount / (5 * burst threshold)) + 0.2 * min(1, burst payments / (3 * `min_burst_payments`)) + 0.2 when there is a change event.

**Headlines.** Account: "Account active again after {gap_days} quiet days: {burst_amount} in {burst_payments} payments within {burst_days} days". `dormant_company`: "Company whose last accounts were filed as dormant moved {burst_amount} in ...". `new_company`: "Recently incorporated company moved {burst_amount} in ...".

**Look-alikes.** Planted: `seasonal`, `property_sale` (flagged by design), `restart`. False-positive notes: seasonal businesses reopening; a property sale paid into a quiet personal account; a business restarting under a new owner.

**Corrections.** "No `PAID` edges for a long gap" in PHASE-1.md 7.2 becomes little activity; the history before the gap must exist (3.5).

| Test (`test_detector_dormant_reactivation.py`) | Records | Expected |
|---|---|---|
| `test_long_gap_then_burst_after_new_director` | a company account with two small payments in February 2025, a new director in February 2026, six payments of about 10,000 each way on 2 March 2026 | one `account` finding: a quiet period of 392 days with one payment in it, the change event "director appointed", six burst payments, a burst threshold of 50,000, the director among the evidence nodes |
| `test_little_activity_is_allowed_in_the_quiet_period` | as above with two more small payments in the gap | found with two quiet payments and 375 days; nothing with `max_quiet_payments` 1 |
| `test_quiet_period_needs_history_before_it` | data from February 2025; an account opened in 2020 and one opened in March 2025, each with a burst in 2026 | only the account opened after the data starts, with 367 quiet days |
| `test_seasonal_business_comes_back_at_its_usual_level` | a tourism business open April to September 2025, a burst in April 2026 at its usual level | nothing; found with `burst_ratio` 1 |
| `test_company_variants` | a dormant-filed company with a burst; a company two weeks old that receives 80,000 and pays 75,000 on; a new company trading normally | `dormant_company` and `new_company`, not the trader; nothing with `company_variants` off |

**CI seed.** 18 alerts; 10 true; 10 of 10 detected; 3 of 10 look-alikes alerted; 1 on another typology's scenario (a `layering_chain` intermediary); 4 on background activity.

#### 7.3.8 `shell_chain` (core, 0.2.0)

**Definition.** Ownership of a company layered through other companies, with the concealment indicators of FATF and Egmont. Their report describes "Adding numerous layers of ownership between an asset and the beneficial owner in different jurisdictions" (paragraph 55) and found that more than half of its cases "made use of complicated ownership structures" (paragraph 56); its Annex E lists the indicators below (`fatf_egmont_concealment_2018`). FinCEN: "Most shell companies are formed by individuals and businesses for legitimate reasons" (`fincen_fin_2006_g014`), so layers alone are not a finding. Registry evidence only, and only relationships that still hold at the end of the window (no end date, or a later one): a sold holding or a resigned director is history, not structure. The detector also runs on real profiles, where R-REAL lets registry patterns about organisations through as structural patterns only when their evidence names no person (7.1.4): a real chain with a person at the top, or with a person as nominee or as a director of many companies, is withheld and counted.

Candidates are the maximal `OWNS` paths from a top owner (a node no current `OWNS` points to) down to a leaf company (one that owns no organisation), and the `OWNS` cycles. A leaf's paths qualify when they pass through at least `min_company_layers` organisations, the leaf included, and show at least `min_indicators` of:

| Indicator | What the graph shows | Source |
|---|---|---|
| `nominee` | `is_nominee` on an `OWNS` of a path, or on a directorship of a path company | Annex E "Nominee owners and directors" |
| `professional_director` | a director of a path company with at least `professional_appointments` current appointments | Annex E: formal nominees "may be "mass" nominees who are nominated agents for a large number of shell companies" |
| `unknown_owner` | a top owner that is an organisation with no recorded owner or controller, or a path company whose PSC statements say no registrable person was found or identified | Annex E; PSC statements (C2 1.1.0) |
| `loop` | the ownership returns to itself (the cycle variant) | the report's "complicated ownership structures" (paragraph 56) |
| `mass_registration_address` | a path company registered at an address shared by at least `mass_address_companies` active organisations (Companies House default addresses excepted) | Annex E "Address of mass registration" |
| `po_box` | a path company whose registered address is a PO box | Annex E "Only a post-box address" |

A loop needs no other indicator. Jurisdictions are a strength term, not a condition ("different jurisdictions", with no number). One finding per leaf company, or per loop, with every qualifying path in its evidence.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_company_layers` | 2 | 1 to 20 | modelling choice: sources say "numerous layers" with no number (`fatf_egmont_concealment_2018`) |
| `min_indicators` | 2 | 1 to 20 | modelling choice from the development figures (7.6.5): one indicator alone flagged most lawful groups; FFIEC: "The mere presence of a red flag is not by itself evidence of criminal activity" (`ffiec_appendix_f`) |
| `professional_appointments` | 10 | 1 to 100 | modelling choice, as `recycled_directors` |
| `mass_address_companies` | 25 | 1 to 250 | as `mass_registration_address` |
| `max_hops` | 6 | 1 to 8 | modelling choice |
| `max_paths` | 200,000 | 1 to 2,000,000 | work limit |

**Variants.** `chain`, `loop`. **Subject:** `owned_company`. **Metrics:** `company_layers`, `jurisdictions`, `jurisdiction_list`, `indicators`, `indicator_text`, `nominee_links`, `professional_directors`, `unknown_owner_statements`, `top_kind` (`person`, `company`, `legal entity of unstated kind`, `company without a recorded owner` or `loop`), `paths`.

**Pattern strength** = 0.15 * min(1, (layers - 1) / 3) + 0.15 * min(1, (jurisdictions - 1) / 2) + 0.2 * nominee + 0.15 * professional director + 0.15 * (unknown owner or loop) + 0.1 * mass registration address + 0.1 * PO box.

**Headlines.** Chain: "Ownership layered through {company_layers} companies in {jurisdictions} jurisdictions, with {indicator_text}". Loop: "Ownership loop through {company_layers} companies with no outside owner recorded".

**Look-alikes.** Planted: `group_holding` (a lawful group with ordinary directors), `fund_vehicle` (professional directors in a fund jurisdiction). False-positive notes: holding company groups with a person at the top; funds and special purpose vehicles with professional directors; subsidiaries of foreign groups whose owners are not on the UK register. Never call a real company a shell (PHASE-1.md 7.1): the alert describes layers and indicators, the API and the UI show the typology's `shape_name` instead of its slug on every alert about a real organisation, and the explainer says first that a company matching the shape is not thereby a shell company (7.5.2).

**Corrections.** Two indicators (or a loop) instead of layers and one signal; only current relationships (3.5 and 7.6.5).

| Test (`test_detector_shell_chain.py`; every case but `test_default_needs_two_indicators_except_for_a_loop` sets `min_indicators` 1, to test each indicator alone) | Records | Expected |
|---|---|---|
| `test_chain_across_jurisdictions_with_a_nominee_owner` | a person owns `vg` company A, A owns `cy` company B through a nominee holding, B owns `gb` company C | one `chain` finding on C: three layers, the jurisdictions "cy, gb, vg", the indicator `nominee`, top kind "person", registry evidence only |
| `test_layers_alone_are_not_enough_and_two_layers_with_an_indicator_are` | a three-company chain across three jurisdictions with a person at the top; then a two-company chain with a nominee director | nothing for the first; the second is found with two layers; nothing with `min_company_layers` 3 |
| `test_ownerless_top_loop_and_professional_director` | a chain under an ownerless `vg` company; a loop of three companies; a chain with a director of twelve other companies | the chain (top kind "company without a recorded owner") and the loop; once a controller is recorded for the top, only the loop; the professional director among the evidence |
| `test_psc_statement_po_box_and_crowded_address` | a company with an unidentified-PSC statement at a PO box; a company at an address of 26 organisations | indicators "unknown_owner, po_box"; "mass_registration_address", and nothing with `mass_address_companies` 27 |
| `test_default_needs_two_indicators_except_for_a_loop` | an ownerless foreign parent and its subsidiary; then a nominee director added; a two-company loop | nothing with the default; found with "nominee, unknown_owner"; the loop is found alone |
| `test_ended_holdings_and_resigned_appointments_are_history` | a chain whose nominee holding at the top was sold in June 2025; a chain with a director whose twelve other appointments ended in 2020 | the first is found with two layers below the sale and only `unknown_owner`, no nominee link; nothing for the second (one current appointment is not a director of many companies) |

**CI seed.** 19 alerts; 9 true; 9 of 10 detected; 5 of 10 look-alikes alerted; 5 on background activity (the world's corporate groups with two indicators).

#### 7.3.9 `mass_registration_address` (core, 0.2.0)

**Definition.** Many active organisations registered at one address, with the signals that set a formation factory apart from an ordinary registered agent. Annex E: "Address of mass registration (usually the address of a TCSP that manages a number of shell companies on behalf of its customers)" (`fatf_egmont_concealment_2018`); providing a registered office is a TCSP service (`fatf_tcsp_2010`).

An address qualifies when at least `min_companies` active organisations (no dissolution date, a status that is not an inactive one) have it as their registered address (`HAS_ADDRESS` role `registered`) and, when `top_share` is set, its count is at least the nearest-rank (1 - `top_share`) quantile of the counts of all loaded addresses ("in the top 0.1 percent"). Small synthetic worlds set `top_share` to 0 in their profile: a quantile over a few thousand addresses leaves only the largest one (7.6.5). The three Companies House default addresses are never findings: companies are moved there when their own address was not appropriate (`ch_default_address_rules_2024`, `ca_registered_office_s86_2006`). The strength adds four signals: incorporations in bursts, directors shared between organisations at the address (current directorships only: no end date, or one after the end of the window), payments among their accounts ("Transacting businesses share the same address", `fincen_fin_2006_g014`; counted only when every organisation at the address is synthetic, R-REAL), and a PO box address (Annex E's "Only a post-box address", `fatf_egmont_concealment_2018`; for UK companies, Companies House has also refused PO boxes as registered offices since 4 March 2024, `ca_registered_office_s86_2006`, `ch_register_data_quality_2025`). The evidence holds at most `max_evidence_companies` organisations (those in the largest burst first, then by id), the shared directors' appointments and the payments among them; the metrics count all of them. On a real profile an address whose evidence holds a shared director who is a real person is withheld (R-REAL (c), 7.1.4) and counted; one without shared directors remains, as a structural pattern.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_companies` | 25 | 1 to 250 | modelling choice |
| `top_share` | 0.001 | 0 to 0.1 | modelling choice ("the top 0.1 percent of loaded addresses"); 0 in the synthetic profiles |
| `active_only` | true | | modelling choice |
| `exclude_postcodes` | CF14 8LH, EH7 9HR, BT1 9DY | | `ch_default_address_rules_2024` (Cardiff, Edinburgh and Belfast default addresses) |
| `burst_days` | 30 | 1 to 300 | modelling choice |
| `max_evidence_companies` | 100 | 1 to 1,000 | work limit (evidence size) |
| `max_candidates` | 50,000 | 1 to 500,000 | work limit |

**Variants.** None. **Subject:** `registered_address`. **Metrics:** `companies`, `companies_shown`, `incorporated_in_burst`, `burst_days`, `shared_directors`, `companies_with_shared_director`, `paying_pairs`, `po_box`.

**Pattern strength** = 0.3 * min(1, companies / (5 * `min_companies`)) + 0.2 * burst share + 0.2 * share of organisations with a shared director + 0.2 * min(1, paying pairs / 3) + 0.1 for a PO box.

**Headline.** "{companies} active companies registered at one address, {incorporated_in_burst} of them incorporated within {burst_days} days".

**Look-alikes.** Planted: `registered_agent` (30 to 120 ordinary clients over many years), `serviced_office`. False-positive notes: registered agents and company secretarial firms; serviced offices; accountants and law firms. A busy agent's address has the count by definition, so look-alike hits are expected here (9 of 10 on the CI seed): the queue order, not the threshold, separates them (the high and medium column of 7.6.5).

**Corrections.** The default addresses are skipped, PO boxes are flagged, only current directorships count as shared, and the threshold is a percentile of the loaded data on real profiles (3.5).

| Test (`test_detector_mass_registration_address.py`; `top_share` 0 unless set) | Records | Expected |
|---|---|---|
| `test_factory_address_with_bursts_shared_directors_and_payments` | 25 companies at one address, 15 incorporated within two weeks, two directors shared across ten, a third director whose four appointments there ended in 2024, payments among four | one finding: 25 companies, 15 in the burst, two shared directors over ten companies (the third is not counted), three paying pairs, three payment steps, no PO box |
| `test_below_threshold_dissolved_and_real_cluster_without_payment_terms` | 24 active companies and a dissolved one at an address; 24 synthetic companies and a non-synthetic look-alike at another, two of them paying each other | nothing (24 active), one with `active_only` off; the second address is found with 25 companies, no paying pairs and no payment evidence (R-REAL) |
| `test_default_addresses_are_skipped_and_po_boxes_flagged` | 30 companies at the Cardiff default address, 30 at a PO box | only the PO box, flagged |
| `test_top_share_raises_the_threshold_to_the_quantile` | 100 addresses: 40, 30 and 98 single companies | `top_share` 0.01 keeps the 40 and the 30; 0.001 keeps the 40 |

**CI seed.** 23 alerts; 7 true; 7 of 10 detected; 9 of 10 look-alikes alerted; 4 on other typologies' scenarios (the offices of `formation_agent_cluster`'s busy-agent look-alikes); 3 on background activity.

#### 7.3.10 `sanctions_exposure` (core, 0.2.0)

**Definition.** An organisation with no sanctions flag of its own that listed parties own or control, judged with each regime's own test. Registry evidence only, and only relationships that still hold at the end of the window (no end date, or a later one): a listed director who resigned or a listed owner who sold no longer counts. That is NeonRadar's reading of current ownership, with two limits it states: when combined ownership falls below 50 percent the entity "is no longer considered automatically to be a blocked entity", but property already blocked stays blocked (OFAC FAQ 402, `ofac_50_percent_faqs`), and "sham transactions do not terminate a blocked interest in property" (`ofac_sham_transactions_2026`); a transfer near a designation date is a red flag the detector does not test (`typology-detection-definitions.md` 10.5). Each regime is seeded with its own list only:

- **US, the OFAC 50 Percent Rule** (`ofac_50_percent_2014`, `ofac_50_percent_faqs`): entities designated on `us_ofac_sdn`. An entity "owned in the aggregate, directly or indirectly, 50 percent or more by one or more blocked persons is itself considered to be a blocked person", so owners count in full, are added up across all listed owners, and the status passes on entity by entity (FAQ 399 and 401). Ownership only: "OFAC's 50 Percent Rule speaks only to ownership and not to control" (FAQ 398). A control link from a listed party gets the caution OFAC advises ("act with caution" where blocked persons "may control by means other than a majority ownership interest"), never "met".
- **EU** (`eu_best_practices_2024` paragraphs 63 to 66, `eu_reg_2580_2001` Article 1(5), `ec_asset_freeze_faq_2026`): entities designated on `eu_fsf`. "50% or more of the proprietary rights", and "the aggregated ownership of the entity should , also be taken into account" (the stray comma is the Council's). Control criteria are reported apart: an appointment right is criterion (a), a `CONSOLIDATES` link from a listed parent criterion (g). The criteria hold "unless the contrary can be established on a case by case basis" (paragraph 65), and control is "a factual assessment to be carried out by the relevant national competent authorities" (Commission FAQ 43), so a criterion is reported as recorded, never as met.
- **UK** (`russia_sanctions_regs_2019` reg 7 and Schedule 1, `ofsi_general_guidance_2026` section 4): entities with a `gb_fcdo_sanctions` designation whose `provisions` include an asset freeze (C2 1.2.0). The first condition of reg 7(2): more than 50 percent of the shares or of the voting rights, or the right to appoint or remove a majority of the board, held directly or through entities the person has a majority stake in (a voting band of more than 50 percent, or a board right). Per listed person: "OFSI would not simply aggregate different designated persons' holdings in a company, unless, for example, the shares or rights are subject to a joint arrangement between the designated parties or one party controls the rights of another"; C2 cannot show either exception, and the summary says so whenever the UK test is not met or left open and two or more UK-listed parties have recorded holdings in the organisation. A share held as nominee "is to be treated as held by the other (and not by the nominee)" (Schedule 1 paragraph 10): a holding recorded as a nominee holding is not counted for the nominee, because the records do not name the person it is held for, and `uk_nominee_holdings` counts such holdings. The control condition of reg 7(4) ("by whatever means") cannot be decided from registry records: significant influence or a directorship from a listed party is reported as `uk_control_to_assess`, never as met or not met. A UK entry with empty `provisions` (the source gives none) may or may not include an asset freeze: what it would reach is reported as left open at most, with `uk_measures_unknown`.

**NeonRadar's readings**, each a choice the typology researchers confirm in M3.5e's review, not the law as written: the entity-by-entity chain for the EU (FAQ 401 is OFAC's); the UK sum of a person's direct holding with the holdings of its majority-stake entities (a reading of "directly or indirectly" with Schedule 1 paragraphs 4 and 9); shares standing in for votes where a link records no voting band (`votes_follow_shares`); a missing upper bound counted as 100 (`unbounded`); a `CONSOLIDATES` link as criterion (g) ("while publishing consolidated accounts"); and the Russia regulations' test applied to every UK regime (only those regulations were read, UNVERIFIED for the others).

A synthetic listed entity (dataset `nr_synthetic`) seeds all three tests. A designation with an end date on or before the end of the window seeds nothing. The candidate step collects the current `OWNS` and `CONTROLS` relationships within `max_hops` of a seed (one `links_from` call per hop) and the current `CONSOLIDATES` and `DIRECTOR_OF` relationships that start at a seed.

**The calculation.** Each test runs twice, on the lower and on the upper bounds of the published bands, as a fixed point: the set of entities that pass only grows, so the loop ends. On lower bounds a sum meets "at least 50" (US, EU) when it exceeds 50 or equals 50, and "more than 50" (UK) when it exceeds 50, or equals 50 with an open bound. On upper bounds (capped at 100) "at least 50" is possible when the sum exceeds 50, or equals 50 with every bound closed, and "more than 50" when it exceeds 50. The results are **met on the records** (met on the lower bounds), **left open by the bands** (possible only on the upper bounds), **not met on the records**, or **no listed owner from this list**. Nothing is multiplied for the tests: the effective share (products along each `OWNS` path, summed per listed owner, the largest owner reported) is a teaching figure only (PHASE-2.md 7.2 rule 6). Natural persons are never owned; only organisations become subjects, and other non-person legal entities pass a status on.

A finding is made for an organisation with a test met or left open, a direct `CONTROLS`, `CONSOLIDATES` or `DIRECTOR_OF` link from a seed, or listed holdings that can reach `min_reported_share` percent: `listed_share_min` and `listed_share_max` add up the recorded holdings in the organisation of listed parties and of entities that pass the US and EU test on the same bounds, each in full and capped at 100, never multiplied. The floor of 25 is a modelling choice: the PSC register does not record holdings of 25 percent or less (`psc_regulations_2016_sch2`), and OFAC advises caution with "a significant ownership interest that is less than 50 percent" (`ofac_50_percent_2014`).

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `max_hops` | 6 | 1 to 8 | modelling choice (PHASE-1.md 7.2) |
| `min_reported_share` | 25 | 0 to 100 | modelling choice: the PSC register's floor (`psc_regulations_2016_sch2`); OFAC's caution below 50 percent (`ofac_50_percent_2014`) |
| `max_links`, `max_paths`, `max_steps` | 200,000; 1,000; 12 | 1 to 2,000,000; 1 to 10,000; 1 to 120 | work limits (relationships collected, paths kept, explanation steps) |

A change to a test or to one of the readings above is a detector change with a new version, never a parameter.

**Variants.** `ownership` (an ownership path), `control` (control without an ownership path), `director` (a directorship only). **Subject:** `exposed_entity`. **Metrics:** `listed_parties`, `shortest_path`, `ownership_paths`, `paths_capped`, `listed_share_min`, `listed_share_max`, `effective_share_min`, `effective_share_max`, `us_test`, `eu_test`, `uk_test`, `votes_follow_shares`, `unbounded`, `bands_inconsistent`, `control_links`, `consolidation_links`, `director_links`, `us_control_caution`, `uk_control_to_assess`, `uk_nominee_holdings`, `uk_measures_unknown`, `eu_control_criteria`, `lists`, `lists_text`, `assessment`.

**Pattern strength** = 0.6 * ownership score + 0.2 * proximity + 0.2 * control score: the ownership score is 1 when a test is met, 0.7 when one is left open, else `listed_share_min` / 100; proximity is 1 - (shortest path - 1) / `max_hops`; the control score is 1 for a direct `CONTROLS` or `CONSOLIDATES` link from a seed, 0.5 for a directorship alone. **Priority:** high whenever a test is met on the records (`priority`, the typology's own rule, C4).

**Wording.** The headline names the shape and the lists only, never a result: "Organisation with recorded ownership or control links to parties on {lists_text}" (`lists_text`: "the OFAC SDN List", "the EU consolidated list", "the UK Sanctions List", joined with "and", or "a synthetic sanctions list"); `director`: "Organisation with a current director on {lists_text}". The results go into the summary, after the headline, through `wording.detail` and the `assessment` metric (7.5.2): one sentence per regime that has a seed, in full ("US test: recorded holdings of parties on the OFAC SDN List reach at least 50 percent, counting in full any entity that itself reaches that level (the method of OFAC FAQ 401)."; "UK test: the published share bands leave open whether one party on the UK Sanctions List holds more than 50 percent."), then the sentences that apply: OFAC's caution for a control link, the UK control condition left to assess, the OFSI sentence on adding parties up, votes standing in for shares, nominee holdings not counted, a UK entry without recorded measures, the EU criteria recorded (rebuttable, for the national authorities to assess), and always the closing sentence "These are NeonRadar calculations from the recorded share bands and links, not findings by OFAC, OFSI, the EU or a national authority." The sentences are verbatim in the detector (`RESULT`, `US_CAUTION`, `UK_CONTROL`, `UK_SEVERAL`, `UK_VOTES`, `UK_NOMINEE`, `UK_UNKNOWN`, `EU_CONTROL`, `CLOSING`) and come from `typology-detection-definitions.md` 10.4. A minority holding is reported with its tests not met, and an EU appointment right with no ownership gives its criterion sentence, never "no test applies". No text says an entity "is sanctioned", "is blocked" or "falls under" a rule (G5, G8, PHASE-2.md 7.2), and the UI shows the `assessment`, never the short `us_test`, `eu_test` and `uk_test` values on their own.

**Real profiles.** A listed party in the evidence that is a real person, or a person on an ownership path, makes R-REAL withhold the finding (`real_person_evidence`, 7.1.4), so on a real profile only exposure through listed organisations reaches an alert, worded as a structural pattern with the standing disclaimer.

**Look-alikes.** Planted: `minority_stake` (20 to 40 percent two links away), `diffuse_holding` (3 to 15 percent). False-positive notes: minority stakes; diffuse shareholdings; a listed record that is a different party with a similar name. A minority stake above `min_reported_share` is reported with its tests not met, and the evaluation counts it as a look-alike hit.

**Corrections.** Three tests on band bounds, reported as met, left open or not met in full sentences, replace the product-of-shares metric and the single OFAC-style flag; control never creates US ownership exposure; ended relationships and nominee holdings are handled; the reporting floor uses summed holdings (3.5).

| Test (`test_detector_sanctions_exposure.py`, 25 cases) | Records | Expected (US, UK, EU) |
|---|---|---|
| `test_faq_401_example_1_status_passes_entity_by_entity` | X 50 percent of A; A 50 percent of B | A and B: met, not met, met; B's effective share 25 (a teaching figure); priority high |
| `test_faq_401_example_2_two_owned_entities_add_up` | X 50 percent of A and of B; A and B 25 percent each of C | C: met, not met, met |
| `test_faq_401_example_3_direct_and_indirect_add_up` | X 50 percent of A and 10 of B; A 40 of B | B: met, not met, met |
| `test_faq_401_example_4_an_entity_below_50_does_not_pass_its_holding_on` | X 50 of A and 25 of B; A and B 25 each of C | B: not met on all three, no priority; C: not met on all three, reported with a listed share of 25 (only A passes, so only A's holding counts) |
| `test_faq_401_example_5_two_minority_stakes_do_not_pass_on` | X 25 of A and of B; A and B 50 each of C | A: not met on all three, listed share 25; C not reported (no listed holding reaches it) |
| `test_one_listed_owner_with_a_band` (three cases) | X holds (25, 50], (50, 75) or [75, 100] of E | left open, not met, left open; met on all; met on all |
| `test_two_listed_owners_add_up_except_in_the_uk` | X and Y each (25, 50] of E | met, not met, met; two listed parties |
| `test_band_left_open_down_a_chain` | X [75, 100] of A; A (25, 50] of B | A met on all, without votes standing in; B left open, not met, left open, lower strength, no priority rule |
| `test_uk_chain_through_shares_says_votes_follow_shares` | X [75, 100] of A; A [75, 100] of B; then X's votes in A recorded | met on all with `votes_follow_shares` true; false once the votes are recorded |
| `test_uk_majority_stake_chain` | X (50, 75) of A; A (50, 75) of B | B met on all three |
| `test_uk_voting_rights_carry_a_chain_that_ownership_does_not` | X holds (50, 75) of A's votes only; A [75, 100] of B | A and B: no listed owner (US, EU), met (UK); variant `control`; US caution on A |
| `test_board_appointment_right_meets_the_uk_test_and_eu_criterion_a` | X has the right to appoint C's board | UK met; EU criterion "(a)"; US caution |
| `test_significant_influence_and_directorship_are_reported_apart` | a listed company with significant influence over D; a listed person directing E | D: UK not met, to be assessed, variant `control`; E: variant `director`, lower strength |
| `test_consolidation_is_eu_criterion_g` | a listed parent consolidates C | EU criterion "(g)", one consolidation link |
| `test_each_regime_uses_its_own_list` | an OFAC entry owns A; a UK asset-freeze entry owns B; a UK travel-ban-only entry owns C | A: US only; B: UK only; C: nothing |
| `test_ended_designation_seeds_nothing_and_listed_targets_are_skipped` | an EU entry that ended in 2025 owns A; a listed party owns another listed company | nothing |
| `test_missing_upper_bound_counts_as_100_and_is_reported` | a holding with no upper bound | `unbounded`; left open on all three |
| `test_small_holdings_that_meet_no_test_are_left_out` | X 20 of A, 30 of B; B 40 of C (12 percent through B) | only B, not met on all; A and B with `min_reported_share` 10 (C's holding runs through B, which does not pass) |
| `test_registry_alert_about_a_real_organisation_is_a_structural_pattern` | a listed company owns 75 to 100 percent of a non-synthetic look-alike company | one alert, `structural_pattern`, `involves_real_entities`, the result-free headline naming the UK Sanctions List, the UK sentence and the closing sentence in the summary and no US sentence, priority high |
| `test_ended_links_count_no_more` | a listed person's directorship that ended in February 2026, a holding sold in May 2026, a holding that ends in December 2026 | only the last company is reported |
| `test_uk_nominee_holdings_and_entries_without_provisions` | a listed person's nominee holding of [75, 100]; a UK entry with no recorded provisions holding [75, 100] | met, not met, met with one nominee holding and its sentence; no listed owner, left open, no listed owner with `uk_measures_unknown` and its sentence |
| `test_the_assessment_names_control_left_unassessed_and_eu_criteria` | a UK-listed company with significant influence over D; an EU-listed company with the right to appoint E's board | D's summary says the UK control condition cannot be decided; E's names EU control criterion (a), though no ownership test applies |
| `test_the_stricter_option_withholds_registry_alerts_about_real_organisations` | a listed company owns a non-synthetic look-alike, with `real_registry_alerts` false | no alert; one `registry_on_real` |

**CI seed.** 22 alerts; 17 true (an exposure scenario exposes several organisations, each a correct alert, 7.6.2); 10 of 10 detected; 5 of 10 look-alikes alerted.

#### 7.3.11 `formation_agent_cluster` (extended, 0.1.0)

**Definition.** One agent behind a burst of company formations whose officers recur across the companies. TCSP services include "Acting as a formation agent of legal persons" and arranging nominees; risks include "The formation by TCSPs of shell companies that can then be used by money launderers" (`fatf_tcsp_2010`; `fatf_pml_2018`). Company formation is a lawful trade, and most providers "appear to be established for legitimate purposes" (`fatf_tcsp_2010`). Registry evidence only.

Candidates are the agents with `REPRESENTS` relationships to at least `min_companies` organisations. An agent qualifies when at least `min_companies` of its clients were incorporated within `window_days` of each other (the largest such set is the burst) and at least `min_shared_officers` people or organisations are current directors (no end date, or one after the end of the window) of two or more burst companies. The strength adds the share of burst companies with a shared officer, the share registered at one of the agent's own addresses, nominee officers among the shared ones, and payments among the burst companies' accounts (only when every burst company is synthetic, R-REAL). An authorised corporate service provider's name or an AML supervisor in the register (`ca_acsp_s1098a_2006`; not in C2 1.2.0) would be context, never a trigger.

On real data the agent is the subject: an agent that is a person, or a legal entity whose kind the source does not state (an ICIJ intermediary may be a person), is withheld by R-REAL (b), and a cluster whose shared officers include a real person by R-REAL (c) (7.1.4). ICIJ data comes from leaked files, and ICIJ says inclusion "is not intended to suggest or imply that they have engaged in illegal or improper conduct" (`icij_faq`): every alert whose evidence holds an ICIJ record carries ICIJ's caution among its notes (7.5.1).

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_companies` | 10 | 1 to 100 | modelling choice |
| `window_days` | 30 | 1 to 300 | modelling choice |
| `min_shared_officers` | 2 | 1 to 20 | modelling choice |
| `max_evidence_companies` | 100 | 1 to 1,000 | work limit (evidence size) |
| `max_candidates` | 50,000 | 1 to 500,000 | work limit |

**Variants.** None. **Subject:** `agent`. **Metrics:** `clients`, `incorporated_in_burst`, `burst_first`, `burst_last`, `window_days`, `shared_officers`, `companies_with_shared_officer`, `at_agent_address`, `nominee_officers`, `paying_pairs`, `companies_shown`.

**Pattern strength** = 0.3 * min(1, burst / (3 * `min_companies`)) + 0.25 * share with a shared officer + 0.15 * share at the agent's address + 0.15 when a shared officer is a nominee + 0.15 * min(1, paying pairs / 3).

**Headline.** "One agent behind {incorporated_in_burst} companies incorporated within {window_days} days, with {shared_officers} officers shared across them".

**Look-alikes.** Planted: `busy_agent` (40 to 80 clients over years), `group_formation` (one group's companies formed in a week, flagged by design). False-positive notes: corporate groups formed in one go by their agent; busy lawful formation agents.

| Test (`test_detector_extended_registry.py`, three of its twelve cases) | Records | Expected |
|---|---|---|
| `test_agent_behind_a_burst_with_shared_officers_and_payments` | one agent, twelve clients incorporated on consecutive days, six at the agent's office, two officers shared across eight (one a nominee), payments among four | one finding: twelve in the burst, two shared officers over eight companies, six at the agent's address, one nominee, three paying pairs, payment evidence |
| `test_spread_out_formations_or_one_shared_officer_are_not_a_cluster` | the same agency with formations 30 days apart; another with one shared officer | nothing |
| `test_an_agent_whose_kind_the_source_does_not_state_is_withheld` | an ICIJ look-alike legal entity of unstated kind representing twelve companies formed on consecutive days, with two shared officers | no alert; one `real_person_subject` |

**CI seed.** 13 alerts; 8 true; 8 of 10 detected; 5 of 10 look-alikes alerted.

#### 7.3.12 `recycled_directors` (extended, 0.1.0)

**Definition.** One person serving as director of many unrelated companies, or appointed to many in a short time. Annex E: formal nominees "may be "mass" nominees who are nominated agents for a large number of shell companies", and directors "listed against the accounts of other legal persons" indicate "the use of professional nominees" (`fatf_egmont_concealment_2018`); "Strawmen may be associated with multiple legal entities" (`europol_efecta_2023`). Small numbers can matter: "two of the group's central figures hired 10 nominees to establish 25 shell companies" (`fatf_pml_2018`, Box 10). Registry evidence only.

Candidates are the people with `DIRECTOR_OF` relationships to at least min(`min_active_appointments`, `burst_appointments`) organisations. The companies are first put into groups: two are in one group when one owns or consolidates the other or a common parent owns or consolidates both, because appointments across one group are ordinary. A person qualifies when the active appointments (no end date on or before the end of the window, company active) span at least `min_active_appointments` groups (variant `many_boards`), or appointments starting within `burst_days` of each other span at least `burst_appointments` groups (variant `burst`). Short tenures (ended within `short_tenure_days`), a nominee appointment, a directorship of a company owned by the person's own relative ("family members with no role or involvement", Annex E) and payments among the companies (only when all are synthetic, R-REAL) add to the strength. The subject is a person, so on a real profile R-REAL (b) withholds every finding about a real person and the run summary counts it (decision 2). UK identity verification for directors (`ca_director_idv_s167m_2006`) links appointments to one verified identity; it says nothing about independence.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `min_active_appointments` | 10 | 1 to 100 | modelling choice; PML Box 10 shows smaller counts can matter (`fatf_pml_2018`) |
| `burst_appointments` | 5 | 1 to 50 | modelling choice |
| `burst_days` | 30 | 1 to 300 | modelling choice |
| `short_tenure_days` | 90 | 1 to 900 | modelling choice |
| `max_evidence_companies` | 100 | 1 to 1,000 | work limit (evidence size) |
| `max_candidates` | 50,000 | 1 to 500,000 | work limit |

**Variants.** `many_boards`, `burst`. **Subject:** `director`. **Metrics:** `appointments`, `active_appointments`, `active_groups`, `burst_appointments`, `burst_groups`, `burst_days`, `short_tenures`, `nominee_appointments`, `relative_owned_companies`, `paying_pairs`, `companies_shown`.

**Pattern strength** = 0.3 * min(1, active groups / (2 * `min_active_appointments`)) + 0.25 * min(1, burst groups / (2 * `burst_appointments`)) + 0.15 * min(1, short tenures / 3) + 0.15 * (nominee or family) + 0.15 * min(1, paying pairs / 3).

**Headlines.** "One person recorded as director of {active_groups} unrelated active companies"; `burst`: "One person appointed director of {burst_groups} unrelated companies within {burst_days} days".

**Look-alikes.** Planted: `fund_director` (flagged by design), `group_director` (one group). False-positive notes: professional directors of funds; company secretaries; directors across one group. This typology has the lowest development precision (7.6.5): most of its other alerts sit on the directors that other typologies' scenarios plant (formation factories, nominee chains), which have the same shape.

| Test (`test_detector_extended_registry.py`) | Records | Expected |
|---|---|---|
| `test_many_unrelated_boards_but_not_one_group` | one person directs ten unrelated companies; another directs a holding company and its eleven subsidiaries | only the first, `many_boards`, ten groups; subject `director` |
| `test_burst_of_short_appointments_and_a_relative_owner` | five appointments in five days, each ended after two months; the person's sibling owns one company | `burst`: five groups, five short tenures, one relative-owned company, no active appointments, the sibling among the evidence |
| `test_a_real_person_as_subject_is_withheld` | a non-synthetic look-alike person directing ten companies | no alert; one `real_person_subject` |

**CI seed.** 55 alerts; 9 true; 9 of 10 detected; 5 of 10 look-alikes alerted; 38 on other typologies' scenarios (19 on the shared directors of `mass_registration_address` factories, 9 on `formation_agent_cluster` officers, 10 on the professional directors of `shell_chain` scenarios and look-alikes); 3 on background activity.

#### 7.3.13 `pep_exposure` (extended, 0.1.0)

**Definition.** An organisation that a politically exposed person, a family member of one or a close associate owns, controls or directs, directly or through up to three companies. Registry evidence only, and only relationships that still hold at the end of the window (no end date, or a later one). The people it starts from:

- every `:PEP` person in scope: in office (a `HOLDS_POSITION` with no end date, or one ending on or after the end of the window), out of office for at most `after_office_months` (the measures continue "for a period of at least 12 months after the date on which that person ceased to be entrusted with that public function", MLR 2017 reg 35(9), `mlr_2017_reg_35`), or with no recorded position (then `office_dates_unknown`, because missing end dates make former PEPs look current);
- while the PEP is in office (or the dates are unknown), the family members one `FAMILY_OF` hop away whose relationship to the PEP is in `family_relationships` (reg 35(12)(b): "a spouse or civil partner of the PEP", "children of the PEP and the spouses or civil partners of the PEP's children" and "parents of the PEP"; FCA FG25/3 adds siblings, `fca_fg25_3`). FtM records the relationship "from the `person`'s perspective, e.g. 'mother', where `relative` is the mother of `person`" (the FtM `Family` schema, which C2's `FAMILY_OF` keeps, source `person`, target `relative`), so a link whose `relative` is the PEP is turned round first: a PEP recorded as someone's mother makes that someone the PEP's child, and a PEP recorded as someone's son-in-law makes that someone a parent-in-law, who is outside reg 35(12)(b). A bare "partner" is not in the default list, because the word does not say whether the partner is a civil partner;
- while the PEP is in office (or the dates are unknown), the people one `ASSOCIATE_OF` hop away whose relationship is in `associate_relationships`, or who hold an `OWNS` or `CONTROLS` into a legal entity the PEP also holds into. Reg 35(12)(c) counts "joint beneficial ownership of a legal entity" and "any other close business relations"; the word list is NeonRadar's reading of the second (a modelling choice), so a link recorded only as a friend or an adviser does not count. When the PEP leaves office the firm "is no longer required to apply" the measures to family members and associates (reg 35(11));
- every `:RCA` person, as the source data gives it, with the office of the PEPs it is linked to by `FAMILY_OF` or `ASSOCIATE_OF`: in office when any of them is, unknown when none is linked, and out of scope when every linked PEP has left office (reg 35(11)).

From each of them, up to `ownership_control_hops` `OWNS`, `CONTROLS` or `DIRECTOR_OF` relationships lead to organisations; every organisation reached is a finding, with the PEP, the family or associate link and the paths in its evidence. "Being a PEP does not prejudge a link to criminal activities" (`fatf_peps_2013`, Annex 1): the alert says only which records connect the organisation to a public function. People are never subjects, and every finding names people in its evidence, so on a real profile R-REAL (c) withholds each one that involves a real person and the run summary counts it (7.1.4): PEP exposure reaches an alert on synthetic data only.

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `family_relationships` | spouse, civil partner, husband, wife, child, son, daughter, child's spouse, child's civil partner, son-in-law, daughter-in-law, parent, father, mother, sibling, brother, sister | | `mlr_2017_reg_35` (35(12)(b)), `fca_fg25_3` (siblings); the synonyms are the relationship words sources use, read from the relative's side |
| `associate_relationships` | business partner, business associate, co-owner, joint owner | | modelling choice, reading `mlr_2017_reg_35` (35(12)(c): "any other close business relations"); a joint holding qualifies whatever the word |
| `associate_hops` | 1 | 0 to 1 | `mlr_2017_reg_35` (35(12)(c)), `fatf_peps_2013` para 49 |
| `ownership_control_hops` | 3 | 1 to 4 | modelling choice |
| `after_office_months` | 12 | 12 to 240 | `mlr_2017_reg_35` (35(9), "at least 12 months", so never fewer); FATF prefers risk to fixed limits (`fatf_peps_2013`) |
| `domestic_countries` | gb | | `mlr_2017_reg_35` (35(3A): a domestic PEP starts from a lower risk) |
| `max_paths`, `max_steps` | 1,000; 12 | 1 to 10,000; 1 to 120 | work limits |

**Variants.** `pep`, `family`, `associate`, `rca`. **Subject:** `exposed_entity`. **Metrics:** `relation`, `office`, `office_dates_unknown`, `domestic`, `shortest_path`, `paths`, `peps`, `first_link`, `family_relationship` (what the relative is to the PEP, after turning round).

**Pattern strength** = 0.35 * relation (PEP 1, family 0.7, associate or RCA 0.6) + 0.3 * proximity (1 - (hops - 1) / `ownership_control_hops`) + 0.2 * first link (a majority holding or appointment right 1, other ownership or control 0.7, a directorship 0.5) + 0.15 * office (in office 1, unknown 0.8, former 0.5), less 0.1 when every position of the PEP is in `domestic_countries`.

**Headlines.** "Organisation within {shortest_path} recorded links of a person listed as politically exposed" ("1 recorded link" in the singular); `family`: "... of a relative of a person listed as politically exposed"; `associate`: "... of a close associate of a person listed as politically exposed"; `rca`: "... of a person listed as a relative or close associate of a politically exposed person".

**Look-alikes.** Planted: `former_pep` (out of office 18 to 36 months, the spouse owns a company), `distant_relative` (a cousin). False-positive notes: ordinary family businesses of public office holders; people long out of office; homonyms.

**Corrections.** One family hop, read in the direction FtM records it, and one associate hop for business associates and joint holders only, both ending with the office, instead of paths of up to four hops through any link; only current relationships; an RCA follows its PEP's office (3.5).

| Test (`test_detector_extended_registry.py`) | Records | Expected |
|---|---|---|
| `test_pep_holdings_through_companies` | a PEP in office owns 75 to 100 percent of A, which owns 25 to 50 percent of B | A and B, variant `pep`, in office; strengths 1.0 and 0.9; B two links away with the PEP in its evidence |
| `test_family_while_in_office_only_and_former_peps_for_twelve_months` | a PEP in office whose spouse owns C and cousin owns D, and who directs another company; a PEP who left office six months before the window's end, whose spouse owns G; a PEP who left eighteen months before | C (`family`, "spouse") and the directed company (first link `DIRECTOR_OF`), not D; for the second PEP only its own company, `former`; nothing for the third, and its company with `after_office_months` 24 |
| `test_family_links_are_read_from_the_relatives_side` | a PEP recorded as someone's mother, as someone's son-in-law, and with a "partner"; each of the three owns a company | only the company of the PEP's child, `family`, relationship "child" |
| `test_associates_need_business_relations_or_a_joint_holding_and_links_must_be_current` | a PEP's "friend" with a company of their own; another "friend" who holds a company jointly with the PEP and owns a second one; a directorship of the PEP that ended in March 2025 | the jointly held company and the joint holder's second company (`associate`); nothing for the plain friend or the ended directorship |
| `test_rca_follows_the_office_of_the_pep_it_is_linked_to` | an RCA linked to a PEP who left office in 2023; an RCA linked to a PEP in office | only the second RCA's company, `rca`, in office |
| `test_associates_rca_and_domestic_peps` | a `gb` PEP's business partner holds 50 to 75 percent of a company; an RCA with no linked PEP and a board appointment right | `associate`, domestic, strength lowered by 0.1; `rca` with `office_dates_unknown` |

**CI seed.** 25 alerts; 25 true (each scenario exposes two or three organisations); 10 of 10 detected; no look-alike alerted.

#### 7.3.14 `cash_commingling` (extended, 0.1.0)

**Definition.** A business banking far more cash than similar businesses in its area, with money moving on to its own people. FFIEC: "the volume of currency in a restaurant used to launder money will most likely be higher in comparison with similar restaurants in the area" (`ffiec_cash_intensive`); cash-intensive businesses "provide opportunities to mix licit and illicit proceeds" (`europol_efecta_2023`). For each company with cash deposits in `currency` in the window, the peer group is the other companies of the same sector and the same area: the postcode district of the registered address, or its city when there is no postcode. A company with at least `min_peers` peers and at least `min_window_amount` banked qualifies when its cash in the window is at least `min_ratio` times the median of its peers'. The strength adds the change over time (the daily mean of the last `change_days` of the window against the `prior_days` before them, when at least `change_days` of earlier data exist; -1 when they do not), the share of its outflows in the window paid to accounts of its owners, directors or their relatives, and cash banked on Sundays (London time; C2 has no opening hours, so this is a weak proxy).

The generator's calibration is the only benchmark in synthetic data, so the peer comparison is circular there (`typology-detection-definitions.md` 14, "misleading alerts"); the evaluation report says so. Every finding rests on payments, and every payment is synthetic, so on a real profile R-REAL (a) withholds each finding about a real business (7.1.4).

| Parameter | Default | Bounds | Basis |
|---|---|---|---|
| `currency` | GBP | | modelling choice |
| `min_peers` | 5 | 1 to 50 | modelling choice |
| `min_ratio` | 3.0 | 1 to 20 | modelling choice |
| `min_window_amount` | 10,000 | 0 to 100,000 | modelling choice |
| `change_days` | 90 | 1 to 900 | modelling choice ("a sudden change", `ffiec_appendix_f`) |
| `prior_days` | 365 | 1 to 3,650 | modelling choice |
| `related_party_share` | 0.5 | 0 to 1 | strength only; modelling choice |
| `max_candidates` | 200,000 | 1 to 2,000,000 | work limit |

**Variants.** None. **Subjects:** `business`, `receiving_account`. **Metrics:** `cash_amount`, `cash_deposits`, `currency`, `peers`, `peer_ratio`, `sector`, `area`, `change_ratio`, `related_party_share`, `sunday_share`.

**Pattern strength** = 0.4 * min(1, ratio / (2 * `min_ratio`)) + 0.2 * min(1, max(0, change - 1) / 2) + 0.25 * min(1, related-party share / `related_party_share`) + 0.15 * min(1, 4 * Sunday share).

**Headline.** "Cash banked at {peer_ratio} times the median of {peers} similar businesses in the area, {cash_amount} in total".

**Look-alikes.** Planted: `busy_business` (1.5 to 2.5 times its peers, paying suppliers), `new_site` (a second site half way through). False-positive notes: busy or growing businesses; a new site or branch; communities that prefer cash.

**Corrections.** Peers are the same sector in the same area, not the same sector everywhere (3.5).

| Test (`test_detector_cash_commingling.py`) | Records | Expected |
|---|---|---|
| `test_front_business_against_its_peers` | five restaurants in one district bank 900 to 1,100 a week on Tuesdays; a sixth banks 5,000 every Sunday and pays most of it to its owner | one finding on its account: five peers, a ratio of 4.62, the area "QQ1", a related-party share of 0.9, a Sunday share of 1.0, no change ratio (-1), two steps |
| `test_peers_must_share_sector_and_area` | a restaurant in another district; a shop in the same district; a restaurant at 2.5 times the median | nothing; the last one is found with `min_ratio` 2.5 |

**CI seed.** 12 alerts; 10 true; 10 of 10 detected; no look-alike alerted; 2 on background activity.

#### 7.3.15 `trade_based_ml` (explainer only)

No detector. Trade-based laundering is "the process of disguising the proceeds of crime and moving value through the use of trade transactions", through over- and under-invoicing, over- and under-shipment, multiple invoicing and falsely described goods (`fatf_egmont_tbml_2020`). Every one of these compares a payment with an invoice, a shipment or a market price, and C2 has none of them: payment data alone cannot show a misrepresented price or quantity (`typology-detection-definitions.md` 15). The typology file stays `explainer_only`; M3.10 adds a short section to `docs/typologies/trade-based-ml.md` on why there is no detector and what data one would need (`fatf_egmont_tbml_indicators_2021`).

### 7.4 Fixtures and the test kit

Detector tests build their records at run time with `detect/tests/kit.py` (verbatim, M3.2) and commit nothing (2.9). A test reads like the case it checks:

```python
k = Kit()
branch = k.account("branch", k.company("bank"), kind="cash_ledger")
acct = k.account("dep", k.person("depositor"))
for d, amount in enumerate((9500, 9800, 9700, 9900)):
    k.pay(branch, acct, amount, f"2026-04-0{1 + d}T11:00", channel="cash_deposit")
[alert] = detect(k.records, {"structuring": st.Params()}).alerts
```

| Kit call | Builds (C1 1.1.0) | Notes |
|---|---|---|
| `company(cid, name, jurisdiction=, incorporated=, sector=, address=, accounts_category=, psc_statements=, topics=, real=, dataset=)` | `Company` `syn-fx-co-<cid>` | `real=True` or a non-synthetic `dataset` gives a look-alike with the id as given (for example `gbch-co-T0000002`), without `nr.synthetic` (C1 R6) |
| `person(pid, name, topics=, real=, dataset=)` | `Person` `syn-fx-p-<pid>` | `topics=("sanction",)` or `("role.pep",)` makes a list look-alike |
| `account(aid, holder, currency=, opened=, kind=)` | `BankAccount` `syn-fx-acct-<aid>` and its holding | `kind="cash_ledger"` for a bank branch |
| `hold(holder, account)` | a second holding of an account | |
| `pay(src, dst, amount, "YYYY-MM-DDTHH:MM", channel=, currency=, pid=)` | `Payment` between the accounts' holders | times are UTC |
| `owns(owner, asset, band)` | `Ownership` with the share bounds of a PSC band (`"25-50"`, `"50-75"`, `"75-100"`) or an exact share (`"exact:40"`) | `nominee=`, `start=` |
| `controls(controller, controlled, control_type, band=)` | `Control` (`voting`, `appointment`, `influence`), a voting band when given | |
| `consolidates`, `director`, `represents`, `family`, `associate`, `position`, `occupancy`, `sanction(entity, dataset, provisions=, end=)` | the matching relationship records | `sanction` on a non-synthetic dataset gives `<prefix>-sanction-T<n>` |
| `address(aid, full)`, `address_at(aid, full, postcode, city)` | `Address` | postcodes in the `QQ` area unless a test needs a real-looking one (a default address) |
| `history(when)` | one unrelated payment at `when` | starts the data's history, for detectors that skip the first `history_days` or `prior_days` |

`kit.detect(records, params)` runs the runner (with R-REAL, the catalog and the wording) over `kit.WINDOW` (1 January to 1 July 2026) with a fixed run id and creation time, as `detect run` would. `kit.source_of(records)` returns the source from `kit.SOURCE_FACTORY`: the in-memory oracle, or Neo4j under `NR_DETECT_SOURCE=neo4j` (7.1.5). The conftest puts the tests folder on `sys.path`, because `--import-mode=importlib` does not (3.2).

Assignment 4 (M3.10, `docs/team/assignment-4.md`) asks each intern to write one more case for the typology they own, by hand and in this style, in a new file `detect/tests/test_a4_<slug>_<handle>.py`. The approved test files stay as they are (1.9, G11).

### 7.5 Alerts

#### 7.5.1 Building an alert

`alerts.build` turns a finding into a C4 1.0.0 alert. A detector never sets these fields:

| C4 field | Value |
|---|---|
| `alert_id` | `compute_alert_id(typology, detector_version, node_ids, edge_ids)` (C4, M1.7c): the same evidence gives the same id on every run |
| `contract_version`, `disclaimer_id` | `1.0.0`, `standing-v1` |
| `typology`, `typology_version`, `detector` | the slug, the typology file's version; the module name, `VERSION` and `query_sha256` (the SHA-256 of the texts of the module's `QUERIES` files, in order, joined with a newline; M3.2) |
| `run_id`, `created_at` | from the run, `run_id` in C4's form `run-<UTC yyyymmddThhmmss>-<4 hex>` (`detect run` uses the clock; the evaluation fixes `created_at` at 2026-11-02 and takes the four hex digits from the profile, split and seed, so that texts and ids do not depend on the clock) |
| `priority` | the typology's own rule when it has one (`sanctions_exposure`), else `high` from a pattern strength of 0.75, `medium` from 0.5, `low` below (PHASE-1.md 5.4) |
| `pattern_strength`, `metrics`, `subjects` | from the finding; each subject gets its node's caption. Metric values are numbers, strings or booleans, never lists or nulls (2.10, the C4 model) |
| `headline`, `explanation.summary`, `explanation.steps` | rendered (7.5.2); each step keeps its edge ids |
| `explanation.typology_reference`, `false_positive_notes` | the typology file's `doc`, `citations` and `false_positives`, then the note a data source asks for when its records are in the evidence (`alerts.DATASET_NOTES`: ICIJ's caution for `icij_offshore_leaks`, as PHASE-1.md 5.1's register asks, "Show ICIJ's disclaimer with the data"; `icij_faq`) |
| `evidence` | `node_ids`, `edge_ids`, `window` (when the finding has one), and `query`: the text of `queries/evidence.cypher` with the alert's ids as parameters |
| `data_flags`, `wording_class` | from the policy (7.1.4) |

`neonradar detect verify-alert` runs every alert's evidence query and exits 1 unless each node and relationship comes back, so an alert can always be checked against the graph it came from. The detection store also writes `evidence.node_ids` and `evidence.edge_ids` as the `:Alert` properties of C2 1.2.0, so I17 checks the evidence of every stored alert (5.2).

#### 7.5.2 Wording

Alert text describes the shape and its numbers. It never names the conduct a typology is named after, even on synthetic data (G5): no headline, summary or step says "structuring", "smurfing", "layering", "laundering", "mule" or "shell", and none says an entity is sanctioned, blocked, suspicious or guilty (PHASE-1.md 7.1, PHASE-2.md 7.2). `typology-detection-definitions.md` 16 explains why: an alert built from synthetic payments next to a real name would be an invented statement about that name, and the conduct words impute purpose. An alert's `typology` field and `typology_reference.slug` still carry the slug (`shell_chain`, for example), because C4 needs them; the API and the UI (Phases 4 and 5) show the typology's `shape_name` to people, never the slug or the typology's name, for every alert with `involves_real_entities`, and the explainer behind `doc_path` starts by saying that a real organisation matching the shape is not thereby a shell company or anything else the typology is named after.

**The typology file** (PHASE-1.md 5.4) gains three fields, which `catalog.py` reads:

- `shape_name`: the neutral name of the shape, used in every summary ("cash deposits just below a threshold"); required when `detector` is set, and it must pass the lint.
- `wording.variants.<variant>`: a `headline_structural` and `headline_synthetic` pair for a variant, with the same rules as the main pair. A finding uses its variant's pair when there is one.
- `wording.detail` (optional, also allowed in a variant's pair): a template whose text goes into the summary after the headline, for what a headline cannot hold. Only `sanctions_exposure` has one (`{assessment}`: the result of every regime in full sentences, 7.3.10).

**Templates.** A placeholder is `{metric}` or `{metric|filter}`, and it may name only the typology's `metrics`:

| Form | Renders | Example |
|---|---|---|
| `{deposits}` | the value (floats with `:g`, booleans as yes or no) | `4` |
| `{total_amount|money}` | the finding's `currency` and the amount, whole amounts without pence | `GBP 38,900` |
| `{pass_ratio|pct}` | a ratio as a whole percent | `98 percent` |
| `{span_days|n:day}`, `{company_layers|n:company:companies}` | a count with its noun, plural with `s` or as given | `3 days`, `1 company` |

Headlines are cut at 140 characters and steps at 280, at the last word boundary, with an ellipsis; the templates are written so that headlines are never cut on the development worlds. `headline_synthetic` starts with "Synthetic scenario: "; `wording_class` chooses between the two (7.1.4).

**The summary** is always "<the structural headline>. <the detail, when the typology has one> This matches the graph pattern of <shape_name>. The records show the shape only; the notes below list ordinary activity that looks the same."

**Steps** come from the finding's groups of evidence relationships. One relationship gives a sentence of its own: "{payer} paid GBP 50,000 to {payee} on 2 March 2026.", "GBP 9,500 in cash was paid into {account} on 2 March 2026.", "{owner} is recorded as holding more than 25 and at most 50 percent of {company} from 1 January 2020.", "{person} is recorded as a director of {company} from 1 January 2020.", and so on for every C2 type `edge_sentence` knows; a registry relationship gives the full start and end dates it records. A group of payments is summarised ("10 accounts paid GBP 8,000 in 10 payments to {account} between 1 March 2026 and 3 March 2026."); other groups are joined, or summarised as the first relationship "and N more recorded relationships of the same kind". Names are node captions; share bands are read with their open and closed ends (PHASE-2.md 7.2).

**The lint.** `wording.render` lints every text it renders (`wording_lint.violations`: Phase 1's patterns, Phase 2's never-write phrases and Phase 3's conduct words), with the captions and ids of every node it names masked out, so that a company called "Test Mule Transport Ltd" does not fail it, and raises `WordingError` on a match: the run stops (exit 1), and the error names the typology, the part and the pattern, never the text (PHASE-1.md M1.9b's run-time check). `test_alert_builder.py` also renders every template of every typology file (main and variants) with sample metrics, checks the false-positive notes and the shape name, and shows that a typology file whose template names conduct makes the run fail.

#### 7.5.3 The runner and the run summary

`runner.run_detection(source, params, window, catalog, run_id=, created_at=, query_sha256=, real_registry_alerts=)` is the one path every caller uses: `detect run`, `make load`, the evaluation and the tests. It never writes; the CLI writes the run folder and, on Neo4j, loads the results (L19).

1. Detectors run in `runner.ORDER` (PHASE-1.md 7.2 order), for every typology whose catalog file names a detector and whose parameters are given.
2. Each finding gets its node and edge information, its data flags and the R-REAL decision (7.1.4). A withheld finding is counted and dropped.
3. An emitted finding is rendered and built. A second alert with an id already emitted in the run (the same evidence found twice, for example a joint account under each holder) is counted as a duplicate and dropped.
4. Alerts are sorted by priority (high, medium, low), then by pattern strength descending, then by alert id: the queue order.
5. The summary (the `:DetectionRun.summary` property, C2 1.2.0, and `summary.json`; counts only on every profile):

```json
{
  "run_id": "run-20261102T090000-0001",
  "window": {"start": "2025-01-01T00:00:00Z", "end": "2026-07-01T00:00:00Z"},
  "params_sha256": "<SHA-256 of the parameters used, canonical JSON>",
  "typologies": {
    "structuring": {
      "findings": 16, "alerts": 15, "duplicates": 1,
      "withheld": {"activity_on_real": 0, "real_person_subject": 0, "real_person_evidence": 0,
                   "registry_on_real": 0},
      "stats": {"candidates": 412}
    }
  },
  "alerts": 288,
  "withheld": {"activity_on_real": 0, "real_person_subject": 0, "real_person_evidence": 0,
               "registry_on_real": 0}
}
```

`params_sha256` is the SHA-256 of `{slug: parameters}` as JSON with sorted keys and no spaces (`runner.params_sha256`); the freeze pins the same value for `synth-eval` (7.6.1). The numbers in the example are illustrative.

### 7.6 Evaluation

#### 7.6.1 Protocol

**What is measured.** For each typology: recall over planted illicit scenarios, and precision over its alerts, on synthetic worlds generated from seeds (the `synth-eval` profile: a 600-company world, 18 months of background, 10 illicit scenarios and 10 look-alikes per typology). The unit for recall is the scenario and the unit for precision is the alert, one review decision in the queue. Payment-level scoring would weigh a 40-payment fan-in ten times more than a four-payment cycle and reward partial evidence (`evaluation-alerting.md` 1.2).

**Seeds** (`eval/seeds.yaml`, verbatim in the code book):

```yaml
# eval/seeds.yaml: the seeds of the detection evaluation (PHASE-3.md 7.6.1)
version: 1
profile: synth-eval
dev:
  seeds: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]   # development: tuning and development figures, anyone may run them
ci:
  seed: 1                                  # the CI gate, with eval/baselines/ci.json
test:
  seeds: []                                # the holdout: ten seeds drawn by the tech lead after the freeze (M3.11)
  drawn_by: null
  drawn_at: null
  freeze: eval/freeze.json
```

- **Development seeds** (1 to 10) are open: anyone may run them, tune on them and look at their worlds. Their figures are always called development figures.
- **The CI seed** (1) is the gate: `neonradar eval check` reruns it in memory and compares every count with `eval/baselines/ci.json`; any difference fails the `eval` job and names the typology and the count. A pull request that changes a detector on purpose updates its rows and explains each change ("Detection impact", 2.3).
- **Holdout seeds** are drawn by the tech lead after the freeze ADR is accepted (M3.11), never chosen by hand and never redrawn because of a result. Only a human runs them, once, on Neo4j (M3.12; G11).

**A seed run** (`evaluate.run_seed`): generate the world and the overlay with the profile's settings and the seed (split `dev` or `test`), write the label files and read them back with the evaluation's own reader, build a source (the oracle by default; with `--engine neo4j`, write the records, wipe the default instance, load them with the project's loader and return a `Neo4jSource`), run every detector with the profile's parameters over the overlay period, and match the alerts to the scenarios (7.6.2). `created_at` is fixed at 2026-11-02, so alert ids and texts do not depend on the clock. Names never move a structural draw, so the counts depend only on the code, the seed and the settings.

**The evaluation folder** (`eval_dir(eval_id)` for the development split, `holdout_dir(eval_id)` under `data/cache/holdout/` for the test split, 4.5): `report.md` and `report.json` (7.6.4), `seeds.json` (per seed the record digest, counts and times), and per seed `seed-<n>/labels/` and `seed-<n>/alerts.jsonl`. The agent's settings and the M3.0 hook close `data/cache/holdout/` to the agent, so a holdout world, its labels and its alerts never reach it (G11).

**The freeze** (`eval/freeze.json`, M3.11) pins everything that could move a published figure, the code as well as the numbers, because a version string only moves when someone remembers to bump it:

| Field | What it pins |
|---|---|
| `params_sha256` | the detection parameters of `synth-eval`, as `runner.params_sha256` computes them, with the profile's overrides |
| `detectors` | each typology's detector version |
| `typology_files` | the SHA-256 of each `detect/typologies/*.yaml` without its `owner`, `status` and `approved_by` lines |
| `code_files` | the SHA-256 of every tracked file (`git ls-files`, so caches and untracked files never count) under `detect/src/neonradar_detect/` (detectors, queries, sources, runner, R-REAL, wording, the evaluation package) and `ingest/src/neonradar_ingest/synth/` (the generator, the scenarios, the names), of `cli/src/neonradar_cli/evaluate.py` and the CLI module of the `eval` commands, and of the modules of `graph/src/neonradar_graph/` that the Neo4j source factory loads each seed with (the loader and the mapping with their query files, which M3.11 lists from the reconciliation), because the holdout run goes through them; keyed by path |
| `profile_sha256` | `ingest/profiles/synth-eval.yaml` |
| `seeds_sha256`, `baseline_sha256` | the `version`, `profile`, `dev` and `ci` parts of `eval/seeds.yaml` (not `test`, which M3.11 fills after the freeze), and `eval/baselines/ci.json` |
| `rules_version`, `label_schema`, `generator_version` | the matching rules (`match.RULES_VERSION`), the label schema, the generator |
| `planted_mix` | illicit scenarios and look-alikes per typology, and the typologies |
| `numpy`, `faker` | the versions in `uv.lock` (the random streams and the names) |
| `git_commit`, `frozen_at` | the commit the file was written from, and the date: recorded, never compared |

`neonradar eval freeze --write` writes the file as JSON with sorted keys and two-space indents; file hashes are of the bytes of the tracked files in the working tree, and the YAML parts are hashed as JSON with sorted keys and no spaces. `neonradar eval freeze --check` recomputes every field except `git_commit` and `frozen_at`, compares each with the file and names every field (and every path, for the file maps) that differs or is missing on either side, exit 1. `eval run --split test` runs the check first and refuses to start unless it passes (M3.11).

#### 7.6.2 Matching alerts to scenarios

An alert is compared only with scenarios of its own typology, by the rule of the typology's kind (`evaluation/match.py`, rules version 1):

| Kind | Typologies | Overlap of an alert with a scenario |
|---|---|---|
| payment | `structuring`, `rapid_pass_through`, `layering_chain`, `circular_flow`, `fan_in_collection`, `fan_out_distribution`, `dormant_reactivation`, `cash_commingling` | intersection over union of the alert's `PAID` edge ids with the scenario's labelled payments. For a look-alike, the share of the alert's `PAID` edges that the look-alike labelled: a look-alike recurs (rent every month), and an alert on one recurrence is a look-alike hit |
| chain | `shell_chain` | intersection over union of the alert's evidence nodes with the scenario's participants in the roles `owned_company`, `layer`, `top_owner`, `nominee`, `professional_director` |
| exposure | `sanctions_exposure`, `pep_exposure` | per exposed organisation: 1 when the alert's `exposed_entity` subject is that organisation and every planted listed owner (or PEP) is among its evidence nodes, else 0 |
| hub | `mass_registration_address`, `formation_agent_cluster`, `recycled_directors` | 1 when the alert's subject is the scenario's hub (the address, the agent, the director), else 0 |

Pairs with an overlap of at least 0.5 (the PASCAL VOC convention, 3.4) are assigned one to one, best overlap first, ties broken by alert id and then by scenario (or unit) id. An exposure scenario can expose several organisations (a listed owner's company and the companies it owns in turn), and each is a correct alert of its own, so each exposed organisation is a unit; the scenario counts as detected when an alert takes one of its core units. Every alert then counts as exactly one kind:

| Kind | Meaning |
|---|---|
| `true` | matched an illicit scenario (or unit) |
| `lookalike` | matched a look-alike, or overlaps one by at least 0.5 |
| `duplicate` | overlaps an illicit scenario by at least 0.5 that another alert took |
| `partial` | overlaps an illicit scenario of its typology, but below 0.5 |
| `other` | matches nothing of its typology but shares a labelled payment or participant with another typology's scenario (a factory address with nominee directors is also a recycled-director shape) |
| `background` | none of these: a shape in the ordinary background activity |

An alert that covers half of a planted chain and half of an unrelated one has an intersection over union below 0.5 and is `partial`, not true.

#### 7.6.3 Metrics

Per typology over the seeds of a run (`evaluation/metrics.py`):

- **Recall** = planted illicit scenarios detected / planted; **precision** = true alerts / all alerts of the typology. Duplicates, look-alike hits, partial overlaps, alerts on other scenarios and background alerts all count against precision.
- **Intervals**: the pooled Wilson 95 percent interval over all scenarios (or alerts), the t interval over per-seed rates (seeds with nothing to count left out; none below two seeds), and the headline interval, the wider of the two (3.4).
- **A rate with nothing to count** is `None` in JSON and "n = 0" in the table, never 0 or 1.
- **Also reported**: the counts of every kind; look-alikes alerted out of look-alikes planted; precision among `high` and `medium` alerts (does the queue order help?); payment coverage (the share of labelled illicit payments inside true alerts, payment typologies only); the minimum, median and maximum of per-seed recall.
- **Macro figures**: unweighted means over typologies (recall over typologies with planted scenarios, precision over typologies with alerts), and macro F1 as the mean of per-typology F1, one of two definitions in use, named in the report (`evaluation-alerting.md` 1.5).

#### 7.6.4 The report and what it may claim

`report.markdown` gives a title, one line with the split, seeds, profile, engine and date, one with the generator version, label schema, matching rules and the first twelve characters of `params_sha256`, then the table (typology; recall and its interval; precision and its interval; precision among high and medium alerts; true, duplicate, look-alike, partial, other and background counts; look-alikes alerted), the macro line, and two fixed paragraphs. `report.to_json` holds the same numbers, unrounded, with the counts. The fixed texts are verbatim in `report.py`:

> How to read this table. Recall counts planted scenarios: a scenario is detected when an alert of its own typology matches it (PHASE-3.md 7.6.2). Precision counts alerts: true alerts divided by all alerts of the typology, so duplicates, look-alike hits, partial overlaps, alerts on other typologies' scenarios and alerts on background activity all count against it. Each interval is the wider of the pooled Wilson 95 percent interval and a t interval across seeds. The high and medium column is precision among the alerts the queue puts first. Look-alikes alerted counts planted benign look-alikes that drew an alert.

> What these figures do not show. Every scenario, look-alike and payment is synthetic and was written by the same team that wrote the detectors, so the figures measure how well the detectors find NeonRadar's own definitions of each pattern, not how they would perform on real data. The similar businesses that `cash_commingling` compares a business with were made by the same generator, so for that typology the comparison is circular. Precision depends on how many scenarios and look-alikes were planted, so it says nothing about alert volumes in a bank. A pattern match is not evidence of wrongdoing.

The README (M3.12) adds one comparison sentence, with its date, and nothing stronger:

> As far as we could find (18 October 2026), no other open-source AML transaction monitoring project publishes per-typology precision and recall, with confidence intervals, measured against labelled synthetic scenarios (`nr_oss_accuracy_search_2026`).

The basis is the search in `evaluation-alerting.md` 6, which the key names (7.8); it never says "first" or "only", and Phase 6 runs the search again before the launch post. What the published table may not claim: performance on real data, a false-positive rate for a bank, a comparison with any commercial system, a ranking of typologies by importance, or a figure from development seeds presented as the evaluation. A typology with `n = 0`, or with figures far from the development figures, is published as measured (M3.12).

#### 7.6.5 Development figures

Seeds 1 to 5 of `synth-eval`, in memory, on the code book as delivered (19 October 2026; generator 1.0.0, label schema 2.0.0, matching rules 1, parameters `241fe08f02d1`). These are development figures: the detectors were written and tuned on these seeds, so they are optimistic, and they are not the published evaluation.

| Typology | Recall | 95% interval | Precision | 95% interval | Precision, high and medium | True / dup / look-alike / partial / other / background | Look-alikes alerted |
|---|---|---|---|---|---|---|---|
| `structuring` | 0.92 (46/50) | [0.76, 1.00] | 0.51 (46/90) | [0.40, 0.63] | 0.66 (42/64) | 46 / 0 / 16 / 1 / 23 / 4 | 15/50 |
| `rapid_pass_through` | 0.84 (42/50) | [0.70, 0.98] | 0.41 (42/103) | [0.32, 0.50] | 0.41 (42/103) | 42 / 0 / 15 / 1 / 12 / 33 | 15/50 |
| `layering_chain` | 0.76 (38/50) | [0.62, 0.90] | 0.30 (38/128) | [0.22, 0.38] | 0.30 (38/125) | 38 / 0 / 28 / 1 / 61 / 0 | 27/50 |
| `circular_flow` | 0.94 (47/50) | [0.83, 1.00] | 1.00 (47/47) | [0.92, 1.00] | 1.00 (47/47) | 47 / 0 / 0 / 0 / 0 / 0 | 0/50 |
| `fan_in_collection` | 0.98 (49/50) | [0.90, 1.00] | 0.51 (49/96) | [0.41, 0.61] | 0.51 (49/96) | 49 / 1 / 21 / 11 / 14 / 0 | 21/50 |
| `fan_out_distribution` | 0.88 (44/50) | [0.72, 1.00] | 0.96 (44/46) | [0.85, 0.99] | 0.96 (44/46) | 44 / 0 / 0 / 1 / 0 / 1 | 0/50 |
| `dormant_reactivation` | 0.78 (39/50) | [0.62, 0.94] | 0.49 (39/79) | [0.38, 0.63] | 0.48 (36/75) | 39 / 0 / 15 / 0 / 7 / 18 | 15/50 |
| `shell_chain` | 0.78 (39/50) | [0.65, 0.87] | 0.35 (39/112) | [0.25, 0.48] | 0.50 (25/50) | 39 / 0 / 25 / 0 / 0 / 48 | 25/50 |
| `mass_registration_address` | 0.76 (38/50) | [0.57, 0.95] | 0.34 (38/113) | [0.26, 0.43] | 0.89 (25/28) | 38 / 0 / 41 / 0 / 20 / 14 | 41/50 |
| `sanctions_exposure` | 1.00 (50/50) | [0.93, 1.00] | 0.82 (76/93) | [0.73, 0.88] | 1.00 (71/71) | 76 / 0 / 17 / 0 / 0 / 0 | 17/50 |
| `formation_agent_cluster` | 0.94 (47/50) | [0.83, 1.00] | 0.65 (47/72) | [0.54, 0.75] | 0.50 (25/50) | 47 / 0 / 25 / 0 / 0 / 0 | 25/50 |
| `recycled_directors` | 0.86 (43/50) | [0.75, 0.97] | 0.15 (43/282) | [0.12, 0.20] | 0.30 (25/84) | 43 / 0 / 25 / 0 / 199 / 15 | 25/50 |
| `pep_exposure` | 1.00 (50/50) | [0.93, 1.00] | 1.00 (125/125) | [0.97, 1.00] | 1.00 (125/125) | 125 / 0 / 0 / 0 / 0 / 0 | 0/50 |
| `cash_commingling` | 0.96 (48/50) | [0.87, 0.99] | 0.89 (48/54) | [0.79, 1.00] | 1.00 (33/33) | 48 / 0 / 0 / 0 / 0 / 6 | 0/50 |

Macro recall 0.89, macro precision 0.60 over 14 typologies with alerts, macro F1 0.69 (the mean of per-typology F1) over 14 typologies. Each seed took about 70 seconds on 2 cores (21 to 25 to generate, 5 to 8 to build the graph, 37 to 46 to detect).

How to read them:

- The misses are the hard variants, as designed: 79 of the 80 missed scenarios, led by `split_chain` (12 of 25 missed), `quiet_factory` (12 of 25), the `loop` variant of `shell_chain` (11 of 25), `dormant_company` (11 of 15), `slow_funnel` and `slow_strawman` (7 of 25 each). The other one is an easy `funnel`.
- Low precision mostly comes from the look-alikes and from the other typologies' scenarios, both planted at a far higher rate than any real book would hold. `layering_chain`'s 61 `other` alerts all sit inside `circular_flow` round trips, whose outward legs are chains; `recycled_directors`' 199 are the shared directors of mass registration factories (84), formation agent clusters (65) and `shell_chain` scenarios and look-alikes (50), which have the same shape; `structuring`'s 23 are the cash deposits of `cash_commingling` front businesses.
- The queue order helps where the strength terms carry the typology's red flags: `mass_registration_address` goes from 0.34 to 0.89 among high and medium alerts, `sanctions_exposure` from 0.82 to 1.00. It does not help `formation_agent_cluster` (0.65 overall, 0.50 among high and medium): its look-alike `group_formation` has every strength signal by design.

**What the development figures led to** (measured again for this table, seeds 1 to 5):

| Change | Before | After |
|---|---|---|
| `circular_flow`: `min_hops_same_account` 3 (a payment straight back is not a cycle) | with 2: 177 alerts, 47 true; every one of the 50 look-alikes alerted; 50 `other`, 30 `background`; precision 0.27 | 47 alerts, 47 true, recall unchanged at 0.94; precision 1.00 |
| `shell_chain`: `min_indicators` 2 (one indicator is common in lawful groups) | with 1: 1,184 alerts, 50 true (recall 1.00); 796 `other`, 313 `background`; precision 0.04 | 112 alerts, 39 true (recall 0.78); precision 0.35 |
| `mass_registration_address`: `top_share` 0 in the synthetic profiles | with 0.001 on a 600-company world: 10 alerts, none true (the quantile leaves only the largest agents' addresses) | 113 alerts, 38 true |

The holdout figures will differ from these. M3.13's report sets the two tables side by side and explains each difference that is larger than the intervals.

### 7.7 Real-data handling (Phase 3 additions)

PHASE-2.md 7.4 still applies in full. Phase 3 puts synthetic records next to real ones for the first time, so these rules are added. The data steward owns them (ADR-0021).

1. **Which real profiles get an overlay.** Only those in `access.real_overlay_profiles` (default `[uk-tiny]`); every other real profile refuses `synth overlay` and `graph load --overlay` with exit 3 before reading a record. Phase 2's conditions hold first: an approved machine, the profile in `access.real_data_profiles`, `access.data_protection_filed: true`.
2. **What a real overlay holds.** Accounts and plain background payments for a share of the eligible organisations (`overlay.background.share`): companies and organisations from a registry dataset, not flagged, not dissolved, never a person (7.2.4). The counterparties, employees, banks and scenario entities are synthetic records the overlay creates. Scenarios and look-alikes run among their own synthetic entities only (G1), so a real profile's alerts on scenarios are synthetic and say nothing about the real register beside them. Labels name only `syn-ov-` ids.
3. **The bridge.** The only link between a synthetic and a real node is `HOLDS_ACCOUNT` from a real organisation to its synthetic account (I15); no payment joins two real holders' accounts (I16); no alert names a real person, as a subject or in its evidence, and no alert that involves a real entity has a payment in its evidence (I17, which reads the evidence ids every `:Alert` stores, C2 1.2.0). The generator checks I15 and I16 before writing, the loader checks them again before connecting (L18), and `graph verify --real` checks the graph after.
4. **Where it lives.** The overlay under `data/cache/real/overlay/<profile>/`, the detection runs under `data/cache/real/runs/<profile>/`, both in the `neo4j-real` instance (L18, L19), both purged by `access.real_data_days` like every other real-profile output, and both deleted with the real instance's volume by `neonradar data purge --all-real --graph --yes`. A base load removes the overlay (L18 step 7); `make load` reloads it.
5. **What detection may say about a real entity.** R-REAL (G12, 7.1.4): no finding that rests on a payment and involves a real entity is ever stored or shown; no finding names a real person, as its subject or anywhere in its evidence, and a person here is every legal entity that is not an organisation, so an ICIJ officer whose kind the source does not state counts as one. Registry findings about real organisations with no real person in them (ownership layered through companies, a mass registration address, a formation agent's cluster, sanctions or PEP exposure through ownership by organisations) remain, built only from relationships that still hold, worded as structural patterns, with the standing disclaimer; with `access.real_registry_alerts: false` they are withheld too and the profile gives counts only. They are stored in `neo4j-real` only and shown only to a human through Phase 2's `api serve --real` on an approved machine. They never appear in a pull request, a document, a screenshot or the demo.
6. **What leaves the machine.** The counts-only summaries in `data/cache/reports/<profile>/`: overlay counts (eligible and active organisations, skipped by reason, accounts, payments, scenarios and look-alikes by typology), load counts, the invariant lines, and per typology the findings, alerts, duplicates and withheld counts by reason. No alert, no id, no name.
7. **Why.** An alert built from invented payments next to a real company would be invented information about that company. In England and Wales a statement that imputes wrongdoing can be defamatory (`defamation_act_2013`, `ewhc_qb_1337_2019`), and an automated pattern about a person can be profiling and, where it suggests an offence, may involve criminal offence data (`uk_gdpr_adm_2026`, `dpa_criminal_data_s11_2018`); data protection by design asks for such outputs to be off by default and minimised (`uk_gdpr_adm_2026`, Article 25; `typology-detection-definitions.md` 16.5), and NeonRadar takes the stricter course of not producing them at all (ADR-0021). This is a project rule, not legal advice; the data steward and the project lead decide its scope (1.2).
8. **The evaluation never uses real data.** Published figures come from synthetic worlds only; a real profile's alert counts are operational counts, never a precision or recall figure.

### 7.8 Bibliography additions

Add these entries to `docs/sources/bibliography.yaml` in the Phase 1 format (PHASE-1.md 7.3), keeping Phase 2's additions. **A milestone that copies a typology file whose `citations` name one of these keys adds that entry in the same pull request**, so the citation check passes: M3.5a the structuring keys, M3.5b the Companies Act and default-address keys, M3.5c `fincen_mule_advisory_2020` and `ca_dormant_company_s1169_2006`, M3.5e the sanctions keys, M3.5f the ACSP and director keys (the table in M3.5 names each). M3.4-2 adds the four legal keys of ADR-0021 (`defamation_act_2013`, `ewhc_qb_1337_2019`, `uk_gdpr_adm_2026`, `dpa_criminal_data_s11_2018`). M3.10 adds the rest and checks every entry against its source on the day of its pull request (`checked`). All were checked on 18 October 2026; the research notes hold the quotations.

**Keys the typology files cite.**

| Key | Title | Publisher | Year | URL |
|---|---|---|---|---|
| `cfr_31_1010_100_2026` | 31 CFR 1010.100(xx): definition of structure (Legal Information Institute copy) | US Code of Federal Regulations | living | https://www.law.cornell.edu/cfr/text/31/1010.100 |
| `cfr_31_1010_311_2026` | 31 CFR 1010.311: filing obligations for reports of transactions in currency | US Code of Federal Regulations | living | https://www.law.cornell.edu/cfr/text/31/1010.311 |
| `cfr_31_1010_313_2026` | 31 CFR 1010.313: aggregation of currency transactions | US Code of Federal Regulations | living | https://www.law.cornell.edu/cfr/text/31/1010.313 |
| `mlr_reg_27_2017` | The Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, regulation 27 | legislation.gov.uk | 2017 | https://www.legislation.gov.uk/uksi/2017/692/regulation/27 |
| `fincen_mule_advisory_2020` | FinCEN Advisory FIN-2020-A003: Imposter Scams and Money Mule Schemes Related to COVID-19 (its full red-flag list could not be extracted; quote only what was read) | FinCEN | 2020 | https://www.fincen.gov/sites/default/files/advisory/2020-07-07/Advisory_%20Imposter_and_Money_Mule_COVID_19_508_FINAL.pdf |
| `ca_dormant_company_s1169_2006` | Companies Act 2006, section 1169 (dormant companies) | legislation.gov.uk | 2006 | https://www.legislation.gov.uk/ukpga/2006/46/section/1169 |
| `ca_registered_office_s86_2006` | Companies Act 2006, section 86 (registered office at an appropriate address) | legislation.gov.uk | 2006 | https://www.legislation.gov.uk/ukpga/2006/46/section/86 |
| `ch_default_address_rules_2024` | Registrar's Rules Volume 6: Nomination of Default Address | Companies House | 2024 | https://assets.publishing.service.gov.uk/media/6925c5422945773cf12dd069/Registrar_s_Rules___Volume_6-_Nomination_of_Default_Address.pdf |
| `ca_acsp_s1098a_2006` | Companies Act 2006, section 1098A (authorised corporate service providers) | legislation.gov.uk | 2006 | https://www.legislation.gov.uk/ukpga/2006/46/section/1098A |
| `ca_director_idv_s167m_2006` | Companies Act 2006, section 167M (directors' identity verification) | legislation.gov.uk | 2006 | https://www.legislation.gov.uk/ukpga/2006/46/section/167M |
| `russia_sanctions_regs_2019` | The Russia (Sanctions) (EU Exit) Regulations 2019, regulation 7 and Schedule 1 | legislation.gov.uk | 2019 | https://www.legislation.gov.uk/uksi/2019/855/regulation/7 ; https://www.legislation.gov.uk/uksi/2019/855/schedule/1 |
| `eu_reg_2580_2001` | Council Regulation (EC) No 2580/2001, Article 1 | EUR-Lex | 2001 | https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32001R2580 |
| `ec_asset_freeze_faq_2026` | Frequently asked questions: asset freeze and prohibition to make funds and economic resources available (Council Regulation 269/2014); FAQs 8, 9, 17 and 43 | European Commission | 2026 | https://finance.ec.europa.eu/system/files/2023-07/faqs-sanctions-russia-assets-freezes_en.pdf |

**Keys the explainers and `docs/detection/README.md` cite** (7.3, 7.6, 7.2.9).

| Key | Title | Publisher | Year | URL |
|---|---|---|---|---|
| `eu_amlr_2024` | Regulation (EU) 2024/1624 (the AML Regulation), Articles 2, 19 and 80; applies from 10 July 2027 | EUR-Lex | 2024 | https://eur-lex.europa.eu/eli/reg/2024/1624/oj/eng |
| `mlr_reg_14_2017` | The Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, regulation 14 (high value dealers) | legislation.gov.uk | 2017 | https://www.legislation.gov.uk/uksi/2017/692/regulation/14 |
| `mlr_amendment_regs_2026` | The Money Laundering and Terrorist Financing (Amendment) Regulations 2026, S.I. 2026/621 (the sterling sums of regulations 14 and 27 from 30 June 2026; its commencement regulation could not be read, so quote the annotation on regulation 27) | legislation.gov.uk | 2026 | https://www.legislation.gov.uk/uksi/2026/621/regulation/20 |
| `dormant_accounts_act_2008` | Dormant Bank and Building Society Accounts Act 2008, section 10 | legislation.gov.uk | 2008 | https://www.legislation.gov.uk/ukpga/2008/31/section/10 |
| `ch_register_data_quality_2025` | Improving the quality of data on our registers | Companies House | 2025 | https://changestoukcompanylaw.campaign.gov.uk/improving-the-quality-of-data-on-our-registers/ |
| `everingham_voc_2010` | The Pascal Visual Object Classes (VOC) Challenge (International Journal of Computer Vision 88) | Mark Everingham, Luc Van Gool, Christopher K. I. Williams, John Winn and Andrew Zisserman | 2010 | https://doi.org/10.1007/s11263-009-0275-4 |
| `opitz_burst_macro_f1_2019` | Macro F1 and Macro F1 | Juri Opitz and Sebastian Burst | 2019 | https://arxiv.org/abs/1911.03347 |
| `cawley_talbot_2010` | On Over-fitting in Model Selection and Subsequent Selection Bias in Performance Evaluation (JMLR 11) | Gavin C. Cawley and Nicola L. C. Talbot | 2010 | https://www.jmlr.org/papers/v11/cawley10a.html |
| `altman_amlworld_2023` | Realistic Synthetic Financial Transactions for Anti-Money Laundering Models (NeurIPS 2023 Datasets and Benchmarks) | Erik Altman and others (IBM) | 2023 | https://arxiv.org/abs/2306.16424 |
| `oztas_saml_d_2023` | Enhancing Anti-Money Laundering: Development of a Synthetic Transaction Monitoring Dataset (ICEBE 2023, accepted manuscript) | Berkan Oztas and others | 2023 | https://eprints.bournemouth.ac.uk/40982/ |
| `ostman_amlgentex_2025` | AMLgentex: Mobilizing Data-Driven Research to Combat Money Laundering | Johan Östman and others | 2025 | https://arxiv.org/abs/2506.13989 |
| `beukel_tide_2026` | Tide: A Customisable Dataset Generator for Anti-Money Laundering Research | van den Beukel, Rožanec and Varbanescu | 2026 | https://arxiv.org/abs/2603.01863 |
| `ibm_amlsim` | AMLSim (repository; unmaintained since 14 February 2022) | IBM | 2022 | https://github.com/IBM/AMLSim |
| `fca_synthetic_data_aml_2026` | Research Note: Synthetic Data and Anti-Money Laundering, Project Report | FCA | 2026 | https://www.fca.org.uk/publications/research-notes/research-note-synthetic-data-anti-money-laundering-project-report |
| `uk_finance_payment_markets_2026` | UK Payment Markets 2026, Summary (2025 data) | UK Finance | 2026 | https://www.ukfinance.org.uk/system/files/2026-08/PaymentMarketsReport_2026Summary.pdf |
| `ons_ashe_2025` | Employee earnings in the UK: Annual Survey of Hours and Earnings 2025 | ONS | 2025 | https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/bulletins/annualsurveyofhoursandearnings/2025 |
| `ons_private_rent_2026` | Private rent and house prices, UK (release of 16 September 2026) | ONS | 2026 | https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/privaterentandhousepricesuk/latest |
| `dbt_business_population_2025` | Business population estimates for the UK and regions 2025 | Department for Business and Trade | 2025 | https://www.gov.uk/government/statistics/business-population-estimates-2025/business-population-estimates-for-the-uk-and-regions-2025-statistical-release |
| `post_office_cash_2025` | Highest month on record for number of cash deposits made at Post Offices (press release, 19 November 2025) | Post Office | 2025 | https://post-office.mynewsdesk.com/pressreleases/highest-month-on-record-for-number-of-cash-deposits-made-at-post-offices-3417323 |
| `govuk_bank_holidays` | UK bank holidays | GOV.UK | living | https://www.gov.uk/bank-holidays |
| `govuk_paye` | Pay employers' PAYE | GOV.UK | living | https://www.gov.uk/pay-paye-tax |
| `govuk_vat_deadlines` | VAT returns: deadlines | GOV.UK | living | https://www.gov.uk/vat-returns/deadlines |
| `govuk_income_tax_rates` | Income Tax rates and Personal Allowances; National Insurance rates and categories (2026 to 2027) | GOV.UK | living | https://www.gov.uk/income-tax-rates ; https://www.gov.uk/national-insurance-rates-letters |
| `uk_finance_card_spending_2026` | Card Spending Update, March 2026 (published 16 June 2026) | UK Finance | 2026 | https://www.ukfinance.org.uk/system/files/2026-06/Card%20Spending%20Update%20-%20March%202026.pdf |
| `nr_oss_accuracy_search_2026` | What open-source AML monitoring projects publish about detection accuracy: NeonRadar's search of 18 October 2026 (Jube, Marble, Tazama, ezrules, blnk watch and Osprey; Watchman for screening), method and results in `docs/research/2026-10-18-detection/evaluation-alerting.md` 6 | NeonRadar | 2026 | https://github.com/opensource-finance/osprey ; https://github.com/moov-io/watchman ; https://github.com/jube-home/aml-fraud-transaction-monitoring ; https://github.com/checkmarble/marble ; https://github.com/tazama-lf/docs ; https://github.com/sofeikov/ezrules ; https://github.com/blnkfinance/watch |

**Keys ADR-0021 cites** (7.7 rule 7; `typology-detection-definitions.md` 16).

| Key | Title | Publisher | Year | URL |
|---|---|---|---|---|
| `defamation_act_2013` | Defamation Act 2013, sections 1 (serious harm) and 4 (publication on matter of public interest) | legislation.gov.uk | 2013 | https://www.legislation.gov.uk/ukpga/2013/26/section/1 ; https://www.legislation.gov.uk/ukpga/2013/26/section/4 |
| `ewhc_qb_1337_2019` | Travel Insurance Facilities Plc v Times Newspapers Plc [2019] EWHC 1337 (QB), paragraph 16 | The National Archives, Find Case Law | 2019 | https://caselaw.nationalarchives.gov.uk/ewhc/qb/2019/1337 |
| `uk_gdpr_adm_2026` | UK GDPR (retained Regulation (EU) 2016/679, as amended), Articles 4(4) (profiling), 22A to 22C (automated decision-making) and 25 (data protection by design) | legislation.gov.uk | 2026 | https://www.legislation.gov.uk/eur/2016/679/article/4 ; https://www.legislation.gov.uk/eur/2016/679/article/22A ; https://www.legislation.gov.uk/eur/2016/679/article/22B ; https://www.legislation.gov.uk/eur/2016/679/article/22C ; https://www.legislation.gov.uk/eur/2016/679/article/25 |
| `dpa_criminal_data_s11_2018` | Data Protection Act 2018, section 11 (criminal offence data) | legislation.gov.uk | 2018 | https://www.legislation.gov.uk/ukpga/2018/12/section/11 |

Phase 1 and Phase 2 keys that Phase 3 cites again, unchanged: `cfr_31_1010_314`, `ffiec_appendix_f`, `ffiec_appendix_g`, `ffiec_cash_intensive`, `fincen_fin_2014_a005`, `fincen_fin_2006_g014`, `fatf_faq`, `fatf_pml_2018`, `fatf_tcsp_2010`, `fatf_egmont_concealment_2018`, `fatf_egmont_tbml_2020`, `fatf_egmont_tbml_indicators_2021`, `fatf_cyber_fraud_2023`, `fatf_peps_2013`, `fatf_recommendations_2026`, `europol_efecta_2023`, `europol_shadow_money_2021`, `europol_money_muling`, `ofac_50_percent_2014`, `ofac_50_percent_faqs`, `ofac_sham_transactions_2026`, `ofsi_general_guidance_2026`, `eu_best_practices_2024`, `mlr_2017_reg_35`, `fca_fg25_3`, `psc_regulations_2016_sch2`, `wilson_1927`.

### 7.9 Glossary additions

Add to `docs/glossary.md` (M3.10), with a citation where the term is an AML or legal term:

| Term | Meaning in NeonRadar |
|---|---|
| Candidate step | One bounded query a detector asks the graph (a `Source` method and its query file); the typology logic runs in Python on the rows it returns |
| Oracle | The in-memory implementation of every candidate step (`MemSource`), which unit tests and the CI gate use; the parity tests show it agrees with Neo4j |
| World | A synthetic register generated from a seed, standing in for Companies House on synthetic profiles |
| Overlay | Synthetic accounts, background payments, scenarios and look-alikes generated on top of a base (a world or a real profile) |
| Bridge rule | The only link between a synthetic and a real node is a real organisation's holding of its synthetic account (I15), and no payment joins two real holders (I16) |
| R-REAL | The real-data detection rule (G12): no payment-based alert involving a real entity and no alert about a real person; such findings are withheld and only counted |
| Withheld finding | A finding R-REAL kept out of the alerts; it exists only as a count in the run summary |
| Planted scenario | A pattern the generator plants among its own synthetic entities, with labels outside the records |
| Look-alike | A planted benign scenario with the shape of a typology (a refund, a payroll run), so that precision counts false positives honestly |
| Variant | One form of a typology a detector reports separately (`same_holder`, `ring`, `dormant_company`) |
| Development seeds, holdout seeds | Seeds anyone may run and tune on; seeds drawn after the detection freeze, run once by a human for the published figures |
| Detection freeze | The point (Monday 9 November) after which no parameter, detector version, matching rule or planted mix changes without a new freeze and new holdout seeds (`eval/freeze.json`) |
| Intersection over union | The overlap of two sets: the size of their intersection divided by the size of their union; a match needs at least 0.5 (`everingham_voc_2010`) |
| Recall, precision (detection) | Planted scenarios detected out of planted; true alerts out of all alerts of a typology (7.6.3) |
| Wider-of-two interval | The published 95 percent interval: the wider of the pooled Wilson interval and the t interval across seeds (3.4) |
| Alert kinds | `true`, `duplicate`, `lookalike`, `partial`, `other` and `background` (7.6.2) |
| Queue order | Alerts by priority band, then pattern strength descending, then alert id |
| Left-censoring | Data that starts part way through an account's life: earlier activity is unknown, so detectors skip the first `history_days` or `prior_days` and never treat an account opened before the data starts as quiet |
| Dormant | In NeonRadar, an account with little activity for at least 180 days (a modelling choice); in UK law, a bank account with no transaction "by or on the instructions of the holder" for 15 years (`dormant_accounts_act_2008`) or a company with no significant accounting transaction (`ca_dormant_company_s1169_2006`) |
| Default address | A Companies House address (Cardiff, Edinburgh or Belfast) to which a company is moved when its registered office is not appropriate (`ch_default_address_rules_2024`) |
| 50 Percent Rule | OFAC's rule that an entity owned 50 percent or more, in the aggregate, directly or indirectly, by blocked persons is itself treated as blocked (`ofac_50_percent_2014`); NeonRadar reports whether the recorded bands meet it, never that an entity is blocked |
| Majority stake (UK) | The Schedule 1 test through which UK ownership passes down a chain (paragraph 9(3)): A holds a majority of the voting rights in B; is a member of B with the right to appoint or remove a majority of its board; is a member of B and controls alone, by agreement with other members, a majority of its voting rights; or has the right to exercise, or actually exercises, dominant influence or control over B (`russia_sanctions_regs_2019`). NeonRadar tests the first two only, without the membership condition, which C2 does not record; a PSC entry for significant influence or control is not the fourth |
| Left open by the bands | A sanctions test result that the published share bands cannot settle: met on their upper bounds, not on their lower bounds |

### 7.10 Architecture decision records for Phase 3

Numbers 0020 to 0024 are assigned here. The agent drafts each as `proposed` in the milestone named, completes it in M3.10, and never accepts one.

| Number | Title | Drafted in | Status at Gate 3 (set by the deciders) | Deciders |
|---|---|---|---|---|
| 0020 | Detector design: candidate steps, hop expansion and the oracle | M3.2 | accepted | detect mentor, tech lead |
| 0021 | The synthetic overlay and the real-data detection rule | M3.4 | accepted | data steward, project lead, tech lead |
| 0022 | Evaluation protocol and the detection freeze | M3.6 | accepted at the freeze (Monday 9 November), with the holdout seeds | the freeze deciders (`people.freeze_deciders`) |
| 0023 | Generator v1 and its look-alikes | M3.3 | accepted | ingest mentor, data steward, a typology researcher |
| 0024 | GDS use for rings of new accounts | M3.5c | accepted | tech lead, project lead |

With the nineteen of Phases 1 and 2, the project then has twenty-four ADRs, which covers the plan's definition of done for the detection design.

### 7.11 Profiles reference

**The synthetic profiles** are verbatim in the code book (M3.3): `ingest/profiles/synth-eval.yaml`, `synth-demo.yaml` and `synth-scale.yaml`. Each has a world block under `sources.nr_synthetic.world` (the fields of `WorldConfig`, with `name` and `seed`), an `overlay` block (the fields of `OverlayConfig`; `seed: null` means the world's seed; `background` holds `BackgroundConfig` overrides) and a `detection` block (`enabled`; `window`: `overlay`, the overlay period, or `data`, the `PAID` time range; `overrides`: per typology, parameter values within the typology file's bounds).

| Profile | World | Overlay | Purpose |
|---|---|---|---|
| `synth-eval` | 600 companies, 900 people, seed from `eval/seeds.yaml` | 18 months; 10 illicit and 10 look-alikes per typology; `top_share` 0 for `mass_registration_address` | the evaluation and the CI gate |
| `synth-demo` | 300 companies, 450 people, seed 20261103 | 18 months; 3 and 3 per typology | `make demo`, Codespaces, 8 GB laptops |
| `synth-scale` | 142,000 companies, 213,000 people, seed 20261105 | 18 months; background for 3 percent of companies, no employees' personal payments; 2 and 2 per typology | the scale benchmark (M3.9) |

**Blocks added to the Phase 2 profiles** (M3.4 merges them; the data steward approves them in review):

```yaml
# ingest/profiles/demo.yaml: Phase 3 blocks
overlay:
  enabled: false        # demo-mini carries its own payments; synth-demo is the overlay demo
detection:
  enabled: true
  window: data          # the PAID time range of the loaded records
  overrides:
    mass_registration_address: { top_share: 0.0 }
```

```yaml
# ingest/profiles/uk-tiny.yaml: Phase 3 blocks
overlay:
  enabled: true         # runs only while uk-tiny is in access.real_overlay_profiles
  seed: 20261026
  start: 2025-01-01
  end: 2026-07-01
  illicit: 2            # per typology, among new synthetic entities only (G1)
  lookalikes: 2
  typologies: all
  background:
    share: 1.0          # every eligible organisation gets an account and plain activity
detection:
  enabled: true
  window: overlay
  overrides: {}
```

```yaml
# ingest/profiles/uk-sample.yaml: Phase 3 blocks
overlay:
  enabled: true         # runs only if the data steward adds uk-sample to access.real_overlay_profiles
  seed: 20261027
  start: 2025-01-01
  end: 2026-07-01
  illicit: 3
  lookalikes: 3
  typologies: all
  background:
    share: 0.05         # about 2,500 organisations of the 50,000-company slice
detection:
  enabled: true
  window: overlay
  overrides: {}
```

**Expected sizes** (synthetic rows measured on 18 October 2026, 7.2.9; real rows estimated from about 550 background payments per active organisation on `synth-eval` (342,409 for 619 organisations on seed 1); M3.7 to M3.9 replace them with measurements):

| Profile | Overlay | Graph after the overlay | Detection |
|---|---|---|---|
| `synth-eval` (one seed) | about 375,000 records (355,090 payments) | 14,429 nodes, 367,333 relationships | 278 to 302 alerts on development seeds 1 to 5 (288 on seed 1) |
| `synth-demo` | about 158,000 records (150,963 payments) | 5,509 nodes, 155,916 relationships | 99 alerts, at least three for every typology |
| `synth-scale` | about 1.56 million payments | at least 500,000 nodes and 2 million relationships (M3.9) | measured in M3.9 |
| `demo` | none | Phase 2's | the `demo-mini` round trip (PHASE-1.md M1.9b) |
| `uk-tiny` | accounts for every eligible organisation of at most 400 companies: about 200,000 payments | about 50,000 nodes and 250,000 relationships | registry typologies only reach alerts on real organisations; payment typologies only on the synthetic scenarios; counts only |
| `uk-sample` | about 2,500 accounts and 1.4 million payments | about 310,000 nodes and 2 million relationships; a lower `share` keeps it smaller | as `uk-tiny` |

---

## 8. Gates

### 8.1 Gate 2 items for Phase 3 (Wednesday 4 November)

Gate 2 belongs to Phase 2 (PHASE-2.md 8). The plan puts two Phase 3 items in it: "Synthetic transactions generated and attached to real entities. First three detections correct on a known fixture." They are numbered after Phase 2's checks. `make gate-2-detect` (M3.7) prints their evidence; the release manager runs it beside Phase 2's `make gate-2` (PHASE-2.md M2.16), which covers G2-01 to G2-15, and adds its lines to the Gate 2 evidence.

| ID | Check | Evidence | Blocks the gate |
|---|---|---|---|
| G2-16 | Synthetic transactions generated and attached to real entities | M3.4-1 and M3.4-2 merged; M3.4-2's pull request carries the counts-only output of the `uk-tiny` real-data run (eligible and active organisations, accounts, payments, the load report) and `graph verify --real` with I15 to I17 at zero | yes (MANUAL: the data steward confirms the output is counts only) |
| G2-17 | First three detections correct on a known fixture | M3.2 and M3.5a merged (`circular_flow`, `structuring`, `rapid_pass_through`); their verbatim tests pass in CI on both sources (the `integration` job's Neo4j mode); Phase 1's `circular_flow` fixture test passes with cases A to E on Neo4j and case F, in memory, withheld (a fixture with a real holder cannot be loaded into the default instance, C2 L17; M3.2) | yes |

If G2-16 is late because Phase 2's M2.11 is (the overlay needs the resolved `uk-tiny` load), Gate 2 passes with an exception for it, with an owner and a date in the Phase 2 report; the synthetic overlay of M3.4 shows the mechanism meanwhile.

### 8.2 Gate 3: detections green (Friday 13 November)

The tech lead decides Gate 3 with the release manager, the detect mentor and the data steward. `make gate-3` (M3.13) gathers the evidence; checks it cannot verify are marked MANUAL and a named human confirms them in the Phase 3 report. Phase 4's items (the copilot and the benchmark questions) are checked in PHASE-4.md.

| ID | Check | Evidence | Blocks the gate |
|---|---|---|---|
| G3-01 | Contracts 1.2.0 merged and tagged | `make contracts-check` passes on `main`; `contracts/CHANGELOG.md` has the 1.2.0 entry; tag `contracts-v1.2.0` exists | yes |
| G3-02 | CI green on `main` | the latest `ci` run on `main` succeeded, with the `eval` job, the detector tests in Neo4j mode and the world parity test in `integration` | yes |
| G3-03 | Eight or more typologies detected, each with a test | at least eight detectors merged (the ten core ones are planned, the four extended ones are extra), each with its verbatim test file passing on both sources; `neonradar detect list` shows them | yes |
| G3-04 | Verbatim files intact | `spec_extract check --milestone` passes on `main` for every merged Phase 3 milestone (M3.4 for both of its parts; a milestone that copies nothing says so); every difference is a recorded deviation | yes |
| G3-05 | The evaluation harness reports precision and recall per typology | `neonradar eval check` matches `eval/baselines/ci.json` with no pending row for a merged detector; `eval run --split dev --seeds 1-5` reproduces 7.6.5 for the merged typologies | yes |
| G3-06 | Detection frozen before the holdout | `eval/freeze.json` on `main` and `eval freeze --check` passes; ADR-0022 accepted by its deciders; the holdout seeds in `eval/seeds.yaml` were committed after the acceptance (dates in the ADR and the commit) | yes (MANUAL for the order of events) |
| G3-07 | Published figures | `docs/data/detection/evaluation-<date>.md` from a human holdout run (split `test`, ten seeds, engine `neo4j`); the README table, that file and `report.json` agree; the fixed texts of 7.6.4 are present | yes |
| G3-08 | No alert names a real person, and no payment-based alert involves a real entity (G12) | the M3.7 `uk-tiny` summary: I15 to I17 at zero (I17 reads the subjects and the evidence of every stored alert), withheld counts by reason, counts only; the registry alerts about real organisations that remain are structural patterns, stored only in `neo4j-real`; nothing from a real profile anywhere in the repository but counts; the data steward confirms | yes (MANUAL) |
| G3-09 | One command loads the demo | `docs/data/benchmarks/<date>-synth-demo.md`: `make demo` from `make reset CONFIRM=yes` in under 10 minutes, alerts for every merged typology | no |
| G3-10 | Scale measured | `docs/data/benchmarks/<date>-synth-scale.md`: at least 500,000 nodes and 2 million relationships, load and query times, detection time per typology, the hardware | no |
| G3-11 | Documentation | `docs/typologies/*.md` with their detection sections; `docs/detection/README.md`; `scripts/check_citations.py` passes; ADRs 0020 to 0024 as in 7.10 | no |
| G3-12 | Assignment 4 and the Phase 3 report | each intern's test case merged (MANUAL, the detect mentor reports counts per handle) and presented on Thursday 12 November; `docs/build/reports/phase-3.md` written | no |

**Outcomes** (as Phase 2's).

- **Pass**: every check passes.
- **Pass with exceptions**: every blocking check passes and some others fail; each failed check gets an owner and a date in the Phase 3 report. Published figures below the development figures are published as measured and explained, never a reason to rerun or hide them (G11).
- **Fail**: a blocking check fails. Fix and re-check. If the gate slips past Friday, the project lead applies the next cut on the plan's kill list the same day; the extended typologies (M3.5f) and the scale benchmark (M3.9) are the first candidates.

After Gate 3, a change to a detector, a parameter, the matching rules or the planted mix needs a new freeze, new holdout seeds and a second published table beside the first (G11).

---

## 9. Risks for Phase 3

| # | Risk | Likelihood | Impact | Response in this spec | Owner |
|---|---|---|---|---|---|
| R1 | An alert about a real person, or a payment-based alert about a real entity, is shown, stored or published | low | high | G12 and R-REAL in the runner on every instance (7.1.4), with every legal entity that is not an organisation treated as a person, in the subjects and in the evidence; I17 after every detection load; tests with run-time look-alikes, and M3.4's detection run on a look-alike overlay in Neo4j; counts-only real-profile output (7.7); the `data-guardian` subagent | data steward |
| R2 | A scenario or look-alike touches a real entity | low | high | G1; `ScenarioCtx` refuses ids it did not create; the bridge check in the generator and again in the loader (L18); I15 and I16; `test_scenarios_never_reach_base_entities` | data steward |
| R3 | The published figures are flattered: tuning on the holdout, a rerun after a look, chosen seeds | medium | high | G11; the freeze file and its check; the holdout run is human-only (hook, terminal check, CI refusal); seeds drawn with `secrets` after ADR-0022 is accepted; any re-freeze publishes both tables | tech lead |
| R4 | The query files fail on a server or disagree with the oracle (they were linted but never executed before this spec) | medium | medium | M3.2 runs every detector test on Neo4j first; the world parity test (M3.6); the `EXPLAIN` test; the rule of 7.1.5 for which side to fix, as a recorded deviation | detect mentor |
| R5 | Detection is too slow or runs out of memory on the scale world | medium | medium | bounded steps with limits; hop expansion instead of path patterns; cash ledgers excluded; auto-commit queries with timeouts; M3.9 records each failure and allows only mechanical fixes | graph mentor |
| R6 | A numpy or Faker upgrade moves the random streams and the CI baseline | medium | low | pins (3.1); a Dependabot group of their own; `eval check` names every moved count; names on streams of their own | ingest mentor |
| R7 | Synthetic figures are read as real-world performance | medium | high | the fixed texts of 7.6.4; development figures always labelled; the dated comparison sentence and nothing stronger; review by the technical writer and the typology researchers | technical writer |
| R8 | A test or parameter misreads the law (the three sanctions tests, PEP scope, the structuring threshold) | medium | high | quoted sources in `typology-detection-definitions.md`; the researchers approve the tests before any detector exists (1.4); OFAC FAQ 401's five examples as tests; plan first for M3.5e | typology researchers |
| R9 | Alert text names conduct or says an entity "is sanctioned" | low | medium | text only from templates; every template linted with captions masked (7.5.2), and every rendered text linted again at run time, which stops the run (`WordingError`); Phase 2's never-write phrases and G5's conduct words in the lint; the API and the UI show the `shape_name`, not the slug, on alerts about real organisations | technical writer |
| R10 | Detectors fit the generator rather than the typology (label leakage) | medium | medium | ids say nothing about roles; the generator and the detectors never import each other; look-alikes with the same shapes; camouflage payments on scenario accounts; precision reported with every kind of false positive; ADR-0023 | detect mentor |
| R11 | Phase 2 slips and blocks Phase 3: M2.1a and M2.2 hold back M3.3, M2.1c (with the tag `contracts-v1.1.0`) holds back M3.1, and through M3.1 and M3.3 every milestone from M3.2 on; M2.11 holds back M3.4 and M2.13 M3.7 and the Gate 2 items | medium | high | explicit dependencies (1.8); the tech lead watches M2.1c and M2.2 first, because the detection core waits for both; M3.0 needs only M2.0; the exception rule of 8.1 | tech lead |
| R12 | GDS changes in the image, or its licence is questioned | low | medium | GDS only for the ring variant, with the oracle's union-find beside it; `ring: false` switches it off; ADR-0024 records the licence position | tech lead |
| R13 | Laptops lack memory for the scale world or the integration tests | medium | low | `synth-demo` for 8 GB laptops; the scale world needs about 3 GB to generate; one Testcontainers database per test session | docs squad |
| R14 | A real overlay makes `uk-sample` too big for a laptop | low | medium | `share` 0.05; `uk-sample` is not in `access.real_overlay_profiles` by default; sizes in 7.11 | data steward |
| R15 | The holdout run fails on the day (Docker, memory, time) | medium | medium | the same human rehearses with `eval run --split dev --seeds 1-2 --engine neo4j` on the same machine on Friday 6 November (M3.12); a failed run is fixed and rerun with the same seeds, which is not a look at results | detect mentor |

---

## 10. Appendix

### 10.1 Document history

| Version | Date | Change |
|---|---|---|
| 1.0 | 19 October 2026 | First version: Phase 3 build spec and its code book, verified baseline, C2 1.2.0, milestones M3.0 to M3.13, detection and generator reference, evaluation protocol with development figures, Gate 2 items and Gate 3; written on 18 October and corrected on 19 October after three independent reviews (a dry run of the milestones, an AML and legal review, an engineering review), with the code tested again |

Record later changes here, with a matching note in `docs/build/PROGRESS.md`. A change to a verbatim file changes the code book too: its block and its SHA-256 line, in the same pull request.

### 10.2 Build terms added in Phase 3

| Term | Meaning here |
|---|---|
| Code book | `docs/build/PHASE-3-CODE.md`: every verbatim and reference file of this phase, grouped by milestone, each with its SHA-256 (2.10) |
| Verbatim file | A file copied exactly from the code book by `spec_extract extract` and proven by `spec_extract check` |
| Reference file | A file in the code book that shows how an adapter must behave; the milestone writes the adapter itself |
| Seam | A place where verbatim Phase 3 code meets Phase 1 or Phase 2 code (2.10); M3.0's reconciliation records each |
| Real overlay | A synthetic overlay on a real profile's base, in `neo4j-real`, for the profiles in `access.real_overlay_profiles` (7.7) |
| Development figures | Figures from development seeds, on which the detectors were written and tuned (7.6.5) |
| Holdout run | The one evaluation run on the holdout seeds, by a human, after the freeze (M3.12) |
| Freeze file | `eval/freeze.json`, which pins what could move a published figure (7.6.1) |
| CI baseline | `eval/baselines/ci.json`: the exact counts per typology on the CI seed (7.6.1) |

Phase 1's and Phase 2's terms (PHASE-1.md 10.2, PHASE-2.md 10.2) still apply.

### 10.3 Files delivered with this spec

| File | Goes to |
|---|---|
| `PHASE-3.md` (this document) | `docs/build/PHASE-3.md` |
| `PHASE-3-CODE.md` (the code book) | `docs/build/PHASE-3-CODE.md` |
| `research/README.md` and the four research notes | `docs/research/2026-10-18-detection/` |
| `README.md` (the kit's steps) | stays in the kit |
