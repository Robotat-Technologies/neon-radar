# Phase 1 report

M1.12 deliverable 2 ([PHASE-1.md](../PHASE-1.md), M1.12 and section 8). It covers what Phase 1 built, the metrics, the deviations from the spec, the risks that are still open, the decisions Phase 2 needs, the inputs the Phase 2 spec expects, and the Gate 1 sign-offs that only people can give.

**State: as of `main` at `bbed6e5` on 22 October 2026.** Every Phase 1 milestone has merged except M1.5 (devcontainer), which the operator paused (#19). Times are UTC. Pull request numbers refer to `robotat-com/neon-radar`.

This report records facts and decisions. It states no AML facts; those live in the typology explainers and case notes, with their citations.

## 1. Summary

- 44 pull requests merged between 20 October 21:16 and 21 October 23:12. 40 are for Phase 1; the other four are the spec seeds for Phases 2 to 4 and the Phase 2 handover (M2.0, #45).
- All four contracts (C1 to C4) are in `contracts/`, and the contract suite is green on `main`. The tag `contracts-v1.0.0` does not exist yet; the tech lead creates it (OD-5).
- What is built on `main`:
  - the loader, the migration runner, the detection runner with the `circular_flow` detector, the Phase 1 API endpoints and the UI shell;
  - `make demo-mini` and the end-to-end test (#43);
  - the synthetic generator, the demo-mini fixture and the synthetic join;
  - four data source spikes;
  - 15 typology drafts with explainers;
  - the knowledge base and the onboarding kits.
- Not merged: the devcontainer (M1.5), which the operator paused (#19).
- `make gate-1` on a clean checkout of `main`: 5 PASS, 9 FAIL, 3 MANUAL (section 4).
  - Of the five freeze checks, GC-01 to GC-04 pass. GC-17 needs the data steward.
  - Every FAIL is one of four kinds: the paused devcontainer (#19), the Companies House key, a human sign-off (OD-5), or the empty intern list (OD-6). GC-16 fails only until this report merges.

## 2. What was built

| Milestone | What | Pull requests | State |
|---|---|---|---|
| M1.0 | Operator decisions OD-1 to OD-25 and the project roles | #1, #9, #11, #37 | merged |
| M1.1 | Repository bootstrap and governance files, ADR-0001 | #2 | merged |
| M1.2 | Agent kit: `CLAUDE.md`, guard hooks, subagents, skills | #3 | merged |
| M1.3 | uv workspace, tooling, `neonradar --version` and `doctor` (ADR-0007) | #4, #5 | merged |
| M1.4 | Local Neo4j 5.26 stack with a pinned GDS jar, `make plugins`, `up`, `smoke` (ADR-0002) | #6, #7 | merged |
| M1.5 | Devcontainer and Codespaces | #19 | paused by the operator (#19) |
| M1.6 | CI workflows, pull request hygiene checks, protection script, `docs/build/ci.md` | #10 | merged |
| M1.7a | C1 record contract, dataset registry, validator (ADR-0003); fixes | #8, #17, #33 | merged |
| M1.7b | C2 graph schema, mapping, migration `0001_init` and runner (ADR-0004) | #15 | merged |
| M1.7c | C4 alert contract and canonical wording (ADR-0009); tightenings | #16, #28, #42 | merged |
| M1.7d | C3 API contract, API skeleton, OpenAPI snapshot (ADR-0008) | #24 | merged |
| M1.8-0 | Shared HTTP client; spike command group and `spike clean` | #12, #13 | merged |
| M1.8a | Companies House spike, built and tested with mocks | #23 | merged; live run waits for `CH_API_KEY` |
| M1.8b | GLEIF spike and the Companies House join | #20 | merged |
| M1.8c | ICIJ Offshore Leaks spike | #21 | merged |
| M1.8d | OpenSanctions spike behind the licence gate | #18 | merged; no data fetched |
| M1.8e | Synthetic generator v0, demo-mini fixture (ADR-0005); synthetic join | #27, #41 | merged |
| M1.9a | Graph loader | #31 | merged |
| M1.9b | Detection runner and the `circular_flow` detector | #38 | merged |
| M1.9c | API: Phase 1 endpoints | #44 | merged |
| M1.9d | UI shell | #35 | merged |
| M1.9e | `make demo-mini`, the e2e workflow and test, quickstart | #43 | merged |
| M1.10a | Bibliography, glossary, wording guide (ADR-0006) | #14 | merged |
| M1.10b | 15 typology definitions and explainers, all `draft` | #25, #26, #30 | merged |
| M1.10c | Case notes, reading list, architecture overview (ADR-0010, ADR-0012) | #29 | merged |
| M1.11a | Onboarding and learning kit (Assignment 1) | #22 | merged |
| M1.11b | Assignment 2 kit | #34 | merged |
| M1.12 | Gate 1 check command (`make gate-1`); this report | #32, #46 | #32 merged; #46 open |
| Later phases | Spec seeds for Phases 2, 3 and 4; Phase 2 handover (M2.0) | #36, #39, #40, #45 | merged, before Gate 1 (OD-18, OD-23) |

## 3. Metrics

| Metric | Value | Source |
|---|---|---|
| Merged pull requests | 44: 40 for Phase 1, plus the later-phase spec seeds #36, #39 and #40 and the Phase 2 handover #45 | `gh pr list --state merged --limit 200 --json number,title,labels,mergedAt` |
| Share labelled `agent` | 43 of 44 (97.7%); Phase 1 only: 39 of 40 (97.5%). #1 (operator decisions, M1.0) has no labels | same |
| Pull requests with `size-exception` | 21 of 44 (OD-15) | same |
| First and last merge | 20 October 21:16, 21 October 23:12 | same |
| Median CI duration (`ci.yml`) | **103 s** over the 118 successful runs (68 s to 350 s). All 150 runs from 21 October 10:05 to 23:12: 118 succeeded, 1 failed, 31 were cancelled when a newer push superseded them | `gh run list --workflow ci.yml --limit 400 --json status,conclusion,createdAt,startedAt,updatedAt`; duration is `updatedAt - createdAt` of completed runs (no run waited in a queue: `startedAt` equals `createdAt`) |
| `make demo-mini` time | **216 s to 226 s** on a first (cold) CI run; **57 s to 112 s** locally. The target is under 5 minutes | M1.9e evidence in #43 |
| Tests on `main` (`bbed6e5`, with this report) | `make check`: 1,399 Python unit tests, 381 contract tests and 56 UI unit tests pass; ruff and mypy strict are clean; 4 generated contract files match the models | `make check` |
| Knowledge base | 54 bibliography entries; 15 typology files and 15 explainers, all `draft`; 12 ADRs, all `proposed` | GC-10, GC-14 |

## 4. Gate 1 check

`make gate-1` on a clean, detached checkout of `main` at `bbed6e5` (22 October 2026, after the ci and e2e runs of that commit finished; gh signed in, Docker running, 58 s):

```
Gate 1 checks (PHASE-1.md section 8) at bbed6e5
GC-01 PASS   Contract suite green on main: contracts/CHANGELOG.md 1.0.0 has C1 to C4; make contracts-check: OK, 4 generated files match the models; ran on main (bbed6e5)
GC-02 PASS   Graph schema applies cleanly: graph/schema/migrations/0001_init.cypher declares 22 constraints and 7 indexes; pytest -m integration graph/tests/test_migrations.py: 3 passed in 36.81s
GC-03 PASS   Walking skeleton runs end to end: latest e2e.yml run on main (bbed6e5, https://github.com/robotat-com/neon-radar/actions/runs/39691928071) succeeded
GC-04 PASS   CI green on main: latest ci.yml run on main (bbed6e5, https://github.com/robotat-com/neon-radar/actions/runs/39691927972) succeeded
GC-05 PASS   Repository basics: 32 of 32 M1.1 governance files; generate_codeowners.py --check passes; the 27 labels of .github/labels.yml exist on GitHub
GC-06 MANUAL Protection in place, or the plan limitation recorded: protection API: gh: Upgrade to GitHub Pro or make this repository public to enable this feature. (HTTP 403); docs/build/ci.md records the plan limitation and interim controls; a person confirms the OD-16 interim controls are in use
GC-07 FAIL   Devcontainer works: no .devcontainer/devcontainer.json (pending M1.5)
GC-08 FAIL   Every source fetched end to end in a spike: companies-house: verdict 'Pending network run (API key not yet available)' (pending M1.8a); gleif: Go; icij: Go with changes; opensanctions: Blocked on licence decision
GC-09 MANUAL Synthetic join proven: demo-mini: 454 records, strict OK, regenerates identically; M1.8e pull requests: #27 merged, #41 merged; a person confirms the synthetic-join output in PR #41
GC-10 FAIL   Knowledge base seeded: circular_flow is draft (a typology researcher approves it, OD-5); bibliography: 54 entries; check_citations.py passes; 15 typology files and 15 explainers of 15
GC-11 FAIL   Every intern has a merged pull request: people.interns is empty, so not met (OD-6; the operator decides at the gate)
GC-12 FAIL   Learning logs started: people.interns is empty, so not met (OD-6; the operator decides at the gate)
GC-13 FAIL   Assignment 2 under way: people.interns is empty, so not met (OD-6; the operator decides at the gate)
GC-14 FAIL   ADRs as in 7.6: proposed, 7.6 says accepted (the deciders accept ADRs, OD-5): 0001, 0002, 0003, 0004, 0005, 0006, 0007, 0008, 0009, 0011
GC-15 FAIL   Legal and communications conversation started: no note in docs/build/PROGRESS.md mentions legal or communications (PHASE-1.md 1.2)
GC-16 FAIL   Phase 1 report written: no docs/build/reports/phase-1.md (pending M1.12-2)
GC-17 MANUAL Data steward approved the licence fields: contracts/datasets.yaml last changed in 5fa31d6; DATA_SOURCES.md last changed in 574864d; link the data steward's approving review in the Phase 1 report
Gate 1: 5 PASS, 9 FAIL, 3 MANUAL. Freeze checks: GC-01 PASS, GC-02 PASS, GC-03 PASS, GC-04 PASS, GC-17 MANUAL
```

GC-16 fails on `main` only because this report has not merged yet. On this branch, the same command reports GC-16 as PASS (see the pull request).

Section 8 says a named human confirms each MANUAL check in this report, and that each check left failed at a "pass with exceptions" outcome gets an owner and a date here. Every role is held by @robotat-com (OD-6). Dates are set by the operator at the gate (OD-1). The **Confirmed by** column is for the person; no agent fills it in.

| Check | Result | Why | What clears it | Owner | Confirmed by (name, date) |
|---|---|---|---|---|---|
| GC-06 | MANUAL | the protection API answers 403 on a private GitHub Free repository; `docs/build/ci.md` records the limitation and the interim controls (OD-16) | a person confirms the interim controls are in use; `scripts/setup_repo_protection.sh` runs after the organisation move or at launch | project lead | |
| GC-07 | FAIL | there is no devcontainer on `main`: M1.5 is paused by the operator (#19) | the operator resumes #19, it merges, and one Windows or Codespaces user confirms it works | docs mentor | |
| GC-08 | FAIL | the Companies House spike was built with mocks; its live run waits for `CH_API_KEY` (OD-14). The GLEIF, ICIJ and OpenSanctions verdicts are accepted | the operator adds the key, runs the commands in `docs/data/spikes/companies-house.md` section 1, and sets the verdict | ingest mentor | |
| GC-09 | MANUAL | the demo-mini checks pass; the synthetic-join output is in #41 | a person reads the synthetic-join output in #41 and confirms it | data steward | |
| GC-10 | FAIL | `circular_flow` is `draft`; the bibliography, the citation check and the 15 typologies with explainers pass | a typology researcher approves `circular_flow` in their own pull request (OD-5) | typology researcher | |
| GC-11, GC-12, GC-13 | FAIL | `people.interns` is empty (OD-6) | interns join, or the operator decides at the gate | project lead | |
| GC-14 | FAIL | ten ADRs are `proposed` where section 7.6 says `accepted` | each ADR's deciders accept it (OD-5); see section 9 | ADR deciders | |
| GC-15 | FAIL | `docs/build/PROGRESS.md` has no note on the legal and communications heads-up | the project lead adds the note (PHASE-1.md 1.2) | project lead | |
| GC-16 | FAIL on `main` | this report is not merged yet | this pull request merges | release manager | |
| GC-17 (freeze) | MANUAL | the licence fields need the data steward's approval. `contracts/datasets.yaml` was last changed in #8; `DATA_SOURCES.md` in #2, #14, #18 and #21 | the data steward links an approving review, or records the approval in this row (an author cannot approve their own pull request on GitHub) | data steward | |

## 5. Deviations from the spec

Each pull request lists its own deviations under "Deviations from spec", and `docs/build/PROGRESS.md` summarises them per milestone. This table collects the ones that change how the project works or what a later phase can rely on.

| Id | What | Why | Decision |
|---|---|---|---|
| D-01 | The orchestrating session merges pull requests, after the acceptance commands, an independent review and green CI; humans review merged work | the operator authorised an unattended build | OD-2, OD-3, OD-4, OD-8, OD-9 |
| D-02 | One person holds every role, and `people.interns` is empty | the team has not joined yet | OD-6 |
| D-03 | Dates in the specs are informational | the build runs as fast as the gates allow | OD-1 |
| D-04 | The repository is `robotat-com/neon-radar`, while `project.yaml` names `neonradar/neon-radar` | the organisation move is pending | OD-7 |
| D-05 | The orchestrator takes the recommended option and records it | operator instruction | OD-10 |
| D-06 | C1 ids use FollowTheMoney's reference alphabet, through `make_id` (#8) | every valid id can then be referenced | OD-11; tech lead sign-off at Gate 1 |
| D-07 | Synthetic names are checked on the Companies House company and officer searches. The spec's example company and example person were replaced (#16, #17) | both matched live records | OD-12 |
| D-08 | GDS is a pinned jar that `make plugins` downloads once, not part of the image (#6, #7, #15) | the Neo4j Community image has no GDS jar (PHASE-1.md 3.1 was wrong); nothing is downloaded at start (G3) | OD-13 |
| D-09 | Agents never create, read or edit `.env`. Acceptance runs use throwaway containers | secrets stay with people | OD-14 |
| D-10 | 21 pull requests carry `size-exception` instead of being split into serial pull requests | critical path; each review still covered the whole diff | OD-15 |
| D-11 | No branch protection; the interim controls are documented in `docs/build/ci.md` (#10) | GitHub answers 403 for a private repository on the Free plan | OD-16 |
| D-12 | `contracts/C1-record.md` (and each later contract document) is the authority over the spec text | the merged contract was reviewed against measured behaviour | OD-17 |
| D-13 | The Phases 2 to 4 specs were seeded before Gate 1 (#36, #39, #40), and the Phase 2 handover M2.0 merged before Gate 1 (#45). Milestones that do not need frozen contracts may start | operator decision | OD-18, OD-23 |
| D-14 | C2 flags: `:PEP` and `:RCA` also come from sub-topics, `:Sanctioned` only from the exact topic, and `:Synthetic` is also set on `:Sanction` (#15) | precision of the flags; invariant I2 | orchestrator; tech lead sign-off at Gate 1 (`contracts/CHANGELOG.md`) |
| D-15 | C2, C3 and C4 clarifications and tightenings before the freeze (#24, #28, #33, #42) | review findings | orchestrator; tech lead sign-off at Gate 1 (`contracts/CHANGELOG.md`) |
| D-16 | Some milestones were split into two pull requests each: M1.3, M1.4, M1.8-0, M1.8e, M1.12. The shared HTTP client got its own pull request (#12) | the 400-line rule (2.3) | orchestrator (2.3) |
| D-17 | GLEIF ids are `gleif-lei-<LEI>`, made with `make_id` (#20) | the C1 id rules | OD-17 |
| D-18 | The ICIJ spike slice is the first 1,000 entities plus every relationship that touches them (#21) | the first rows of each file share no edges | orchestrator |
| D-19 | No OpenSanctions data was fetched; the spike verdict is "blocked on licence decision" (#18) | `access.opensanctions: none` | OD-19 (evaluation route sought); OD-22 (official lists for Phase 2) |
| D-20 | The Companies House spike is built and tested with mocks; the live run is pending (#23) | the API key is pending | OD-14 |
| D-21 | Faker's `ar_SA` surnames are not used; a curated list is used instead (#27) | the Faker list includes real prominent families | `CLAUDE.md` known trap; orchestrator |
| D-22 | Only live registry organisations (`gb_companies_house`, `gleif_lei`) may hold synthetic accounts in the synthetic join. ICIJ and `PublicBody` records never do (#41) | guardrail G1 | orchestrator; ADR-0005 rule 2, listed for Gate 1 |
| D-23 | The API serves no `/docs` or `/redoc` pages, and FastAPI's built-in OpenTelemetry is switched off (#24) | they load from a CDN or phone home (G3) | orchestrator |
| D-24 | UI scaffold pins follow 3.1 rather than create-vue's output. An npm override points openapi-typescript at TypeScript 6.0.3. The devtools plugin is dropped (#35) | version pins and G3 | autopilot (OD-10) |
| D-25 | The detector registry is used instead of module paths in typology files. The runner does not wait for typology approval (#38) | safer imports; the M1.9b acceptance runs a draft typology | orchestrator; to reconcile at Gate 1 |
| D-26 | `neonradar graph load` is strict by default; a C2 documentation clarification carried the `contract-change` label (#31) | safer default; reload behaviour documented | orchestrator |
| D-27 | Some bibliography entries keep the research note's checked date. One OCCRP key was renamed, and PHASE-1.md 7.3 and 7.5 cite the new key (#14) | several sites answer automated clients with a bot challenge | orchestrator |
| D-28 | `make gate-1` adds `--report-only` and `--offline`. GC-06 is MANUAL when only the limitation is recorded; GC-09 is MANUAL with the M1.8e-2 pull request (#32) | review findings | autopilot (OD-10) |
| D-29 | In the 1MDB case note, one person is described by role only (#29) | the note attributes every statement to its source and states the presumption of innocence | OD-21 |
| D-30 | Phase 2 runs on synthetic data only until the data protection documents are filed. Sanctions data comes from the UK, US and EU official lists | data protection and licences | OD-22 |
| D-31 | Licences: GDS is treated as GPLv3 and never redistributed; `python-stdnum` (LGPL) is accepted as an unmodified dependency | licence review | OD-20 |

## 6. Risks still open

The risks of PHASE-1.md section 9, as they stand on 22 October.

| Risk | State | Still open |
|---|---|---|
| R1 OpenSanctions licence | It happened: no OpenSanctions data was fetched (#18). The evaluation route is being sought (OD-19). Phase 2 takes sanctions data from the UK, US and EU official lists (OD-22) | yes, for OpenSanctions only |
| R2 GLEIF interruptions until 4 November | The live spike ran on 21 October (#20). Phase 2 uses the Golden Copy files (PHASE-2.md 0.5 item 8) | yes, until 4 November |
| R3 Companies House key not ready | It happened: `access.companies_house_key: pending`, so the live spike has not run (#23, GC-08) | yes |
| R4 PyICU builds | ICU 78.3 is installed on the build machine (#5). The devcontainer (#19) is paused. The demo's API image compiles PyICU from source (#43) | yes |
| R5 Review capacity | 44 pull requests merged in about 26 hours. The orchestrator reviews and merges (OD-2, OD-4); people review after the merge | yes |
| R6 Contracts change after the freeze | The tag does not exist yet. The contracts were tightened four times before the freeze (#28, #33, #42 and the #31 clarification) | yes, until the tag exists |
| R7 Plausible but wrong AI output | No typology is approved yet. The `circular_flow` return ratio has no upper bound (#38). The case notes need browser checks (#29) | yes |
| R8 No branch protection | It happened: GitHub answers 403 (#10). The interim controls are in `docs/build/ci.md` (OD-16) | yes |
| R9 Memory on 8 GB laptops | The small memory profile exists (M1.4); the devcontainer is paused by the operator (#19) | yes |
| R10 Synthetic names collide with real ones | OD-12 checks; two spec example names were replaced. Arabic-script and Cyrillic names cannot be checked on Companies House (#27) | yes |
| R11 Personal data reaches the repository | Spike output stays in `data/cache/`, plus the fixture check and gitleaks. A first-draft fixture name that matched a live officer record is still in the git history of #23; the current tree does not contain it | yes |
| R12 Interns learn little | There are no interns yet (OD-6) | yes |
| R13 Version drift | Pins held. Deviations were recorded where a scaffold or a library differed (#24, #35) | low |
| R14 GDS downloaded at start | It happened as feared (the image has no GDS), and it is fixed with the pinned jar (OD-13) | no |

## 7. Decisions needed for Phase 2

| Decision | State | Where |
|---|---|---|
| Sanctions source and licence | Decided. UK, US and EU official lists (`gb_fcdo_sanctions`, `us_ofac_sdn`, `eu_fsf`); no UN list without the UN's written permission; no PEP sources yet. OpenSanctions: the evaluation route is being sought, and `access.opensanctions` stays `none` until the written confirmation is filed | OD-19, OD-22; PHASE-2.md 0.5 item 2 |
| Officer fetching under the Companies House rate limit | Decided in the Phase 2 spec: fetch per company within a budget (default 20,000 requests, about three hours), cached and resumable; the `person_number` rule D3. Still needs the API key and a measured live run (M1.8a) | PHASE-2.md 0.5 item 5; OD-22 |
| Entity resolution thresholds | Decided in the Phase 2 spec: deterministic rules first, then Splink 5. The thresholds are chosen on the synthetic benchmark and frozen before any pair is labelled, and precision is measured on 400 human-labelled pairs. `people.er_labellers` and `people.er_senior_reviewers` are `@TODO` | PHASE-2.md 0.5 items 3 and 4; OD-22 |
| Bulk-load with `neo4j-admin import` | Not in Phase 2: the online loader stays the only loading path, and M2.13 measures it | PHASE-2.md 0.5 item 6 |
| Real data | Phase 2 runs on synthetic data only until the data protection documents are filed and approved machines are listed | OD-22; PHASE-2.md 1.1 |

## 8. Inputs the Phase 2 spec needs

PHASE-2.md 0.6 lists what Phase 2 expects from Phase 1. M2.0 (#45) reconciles the rest in `docs/build/phase-2-reconciliation.md`.

| Input | State |
|---|---|
| Tag `contracts-v1.0.0` on `main` and `make contracts-check` green | the contract suite is green (GC-01); GC-02 to GC-04 pass too; the tag waits for the tech lead (OD-5) after GC-17 |
| `docs/build/reports/phase-1.md` with the deviations and the Phase 2 decisions | this report (sections 5 and 7) |
| Spike reports for Companies House, GLEIF, ICIJ and OpenSanctions, with measured headers, field names and verdicts | GLEIF: go (live run, #20). ICIJ: go with changes (live run, #21). OpenSanctions: blocked on the licence decision, no data (#18). Companies House: mocks only, verdict pending the live run (#23) |
| Walking skeleton: `make demo-mini` and `make e2e` passing, plus the loader, migration runner, API and detection runner | merged: the loader (#31), the migration runner (#15), the detection runner (#38), the API endpoints (#44), and `make demo-mini` and `make e2e` with the e2e workflow (#43); the latest e2e run on `main` succeeded (GC-03) |
| The C1 validator, the dataset registry and the fixture check | merged (#8, #10) |

## 9. Gate 1 sign-offs for people

These items need a person (OD-5). The orchestrator listed them and does none of them. While OD-6 holds, every role is @robotat-com. Tick an item when it is done, and record the decision where it says.

**Tech lead**

- [ ] Review `contracts/CHANGELOG.md` 1.0.0, and sign off every "Changed from" and "Clarifications" subsection for C1 to C4 and C4's "Tightened after the M1.7c review" subsection (#8, #15, #16, #24, #28, #33, #42).
- [ ] Decide the three C2 items under "Open for Gate 1 sign-off":
  - single-valued `registration_number`, `lei` and `account_number`;
  - `PAID.amount` as a FLOAT or as integer minor units;
  - `MIGRATIONS_DIR` in the source tree.
- [ ] Sign off the C1 id alphabet (OD-11, #8) and the C2 flag rules (#15).
- [ ] Sign off the C3 decisions D1 to D15 (#24).
- [ ] Reconcile "a detector waits for its typology's approval" (`detect/CLAUDE.md`) with the runner, which runs a draft typology (#38).
- [ ] API (#44):
  - decide whether to declare the 500 problem on `GET /alerts/{alert_id}` in the OpenAPI document (C3 describes the case; the snapshot does not list it);
  - decide the alert pruning policy across runs: a new detection run keeps earlier runs' alerts, so an alert whose evidence changed stays until the graph is wiped;
  - note that a stored alert whose evidence left the graph answers a 500 problem; serving it with partial evidence would need a C3 change.
- [ ] With the data steward: confirm that in the synthetic join only registry records (`gb_companies_house`, `gleif_lei`; `Company` or `Organization`) hold synthetic accounts, and that ICIJ and `PublicBody` records never do (#41; ADR-0005 rule 2).
- [ ] With the project lead: confirm two MPL-2.0 dependencies (licence decisions stay human, OD-5):
  - `lightningcss`, a build-time CSS tool that Vite brings in; nothing of it reaches `ui/dist/` (#35);
  - `orjson` (MPL-2.0 AND (Apache-2.0 OR MIT)), which FollowTheMoney brings in (#8).
- [ ] Decide the Gate 1 outcome (pass, pass with exceptions, or fail). Give each failed check an owner and a date in section 4.
- [ ] Create and push the tag `contracts-v1.0.0` once GC-01 to GC-04 and GC-17 pass (PHASE-1.md 5.5).

**ADR deciders (section 7.6)**

- [ ] Edit and accept:
  - ADR-0001 and ADR-0011 (project lead, tech lead);
  - ADR-0002, ADR-0003, ADR-0004, ADR-0007 and ADR-0008 (tech lead);
  - ADR-0005 (tech lead, data steward), including rule 2 on which records hold synthetic accounts (#41);
  - ADR-0006 (data steward, project lead);
  - ADR-0009 (tech lead, typology researchers).
- ADR-0010 and ADR-0012 stay `proposed` (GC-14).

**Data steward**

- [ ] Approve the licence fields in `contracts/datasets.yaml` (#8) and `DATA_SOURCES.md` (#2, #14, #18, #21), and record it in section 4, row GC-17. This check blocks the freeze.
- [ ] Read the synthetic-join output in #41 (GC-09).
- [ ] Read the demo-mini fixture names, and search the Cyprus register for the Latin-script name of the synthetic sanctioned company. Names in Arabic or Cyrillic script cannot be checked on Companies House (#27).
- [ ] Add `CH_API_KEY` to `.env`, run the Companies House spike live and set its verdict (#23, OD-14; GC-08).
- [ ] Before Phase 2 uses Companies House data: decide whether Companies House's `is_sanctioned` field ever becomes a flag on a real person (a G1 decision, #23).
- [ ] File OpenSanctions' written answer and the confirmed line in `docs/data/licences/opensanctions.md` when it arrives (OD-19). This does not block Phase 2.
- [ ] Before the first real-data run: test `.claude/hooks/guard_real_data.py` with your own bypass attempts, and record the results in the pull request that enables the first real profile (#45).

**Typology researcher**

- [ ] Approve `circular_flow` (`status` and `approved_by`, in your own pull request; GC-10).
- [ ] Decide the open question on `circular_flow`: the return ratio has a lower bound (`min_return_ratio`) and no upper bound, and only the first and last payment are compared (#38).

**Project lead**

- [ ] Add the legal and communications heads-up note to `docs/build/PROGRESS.md` (GC-15).
- [ ] Decide GC-11 to GC-13 while `people.interns` is empty (OD-6).
- [ ] Confirm the interim controls in `docs/build/ci.md` (GC-06). Run `scripts/setup_repo_protection.sh` when convenient (OD-16).
- [ ] Review the autopilot decisions OD-11 to OD-17 (OD-10).
- [ ] Fill in `project.security_contact` and `project.conduct_contact` in `project.yaml`; both are `TODO` (#2).
- [ ] Do the browser checks of the justice.gov and OCCRP statements in the case notes (#29; OD-21 keeps them on the Gate 1 list).
- [ ] Decide whether `docs/research/` is published on the Phase 6 documentation site (#29).
- [ ] Resume or close the devcontainer, which the operator paused (#19). One Windows or Codespaces user confirms it (GC-07).
- [ ] Two people who did not build it run `make demo-mini` from a clean clone (M1.9e review focus, #43).
