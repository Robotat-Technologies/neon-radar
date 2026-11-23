# Sign-off tracker

The human decisions NeonRadar is waiting on, and who owns each. Agents never take these decisions (operator decision [OD-5](operator-decisions.md)); this page only lists them, with the evidence in the repository that each one is still open, so that nothing waits unseen.

**State: as of `dev` at `2cbd71c` on 23 November 2026.** Each row was checked against the file it names. When you take a decision, record it where the row says, then delete the row from this page in the same pull request. If you find a decision that is missing here, add a row.

**Owners.** Owners are roles from `people` in [project.yaml](project.yaml), plus the operator, who decides for the organisation (see [operator-decisions.md](operator-decisions.md)). Until the team joins, `@robotat-com` holds every role ([OD-6](operator-decisions.md)), so every row below is currently theirs. Where a role is still `@TODO`, naming that person is itself a row in section 3.

## 1. Approvals

| Decision | Still open because | Owner | Record it in |
|---|---|---|---|
| Accept the Phase 1 decision records 0001 to 0009 and 0011 | All say `Status: proposed`. Gate 1 check GC-14 asks for them to be `accepted` ([Phase 1 report](reports/phase-1.md), section 4) | Each record's deciders, as its row in [decisions/README.md](../decisions/README.md) names them | The record's `Status` line and the index |
| Accept the Phase 2 decision records 0013 (data profiles) and 0018 (real-data handling) | Both say `Status: proposed` | Data steward with the tech lead (0013); data steward (0018) | The record and the index |
| ADR-0010 (copilot) and ADR-0012 (documentation site) | `proposed` on purpose: they are decided in Phase 4 and Phase 6 ([decisions/README.md](../decisions/README.md)) | Tech lead with the copilot mentor; technical writer with the tech lead | The record and the index |
| Approve the `circular_flow` typology | All 15 files in `detect/typologies/` are `status: draft`. Gate 1 check GC-10 needs `circular_flow` approved | Typology researchers | The typology file (`status` and `approved_by`), in the researcher's own pull request; checks of the other explainers come from Assignment 2 |
| The `circular_flow` return ratio | Open question in the Phase 1 report, section 9: the ratio has a lower bound (`min_return_ratio`) and no upper bound, and only the first and last payment are compared (#38) | Typology researchers | The typology file |
| Record the tech lead's sign-off on the contract changes | The tags `contracts-v1.0.0` to `v1.2.0` were created on 23 October 2026, so the contracts froze as written. [contracts/CHANGELOG.md](../../contracts/CHANGELOG.md) still lists three C2 items under "Open for Gate 1 sign-off" (single-valued identifiers, `PAID.amount` as a float, `MIGRATIONS_DIR` in the source tree) and heads 1.0.0, 1.1.0 and 1.2.0 "(unreleased)" | Tech lead | `contracts/CHANGELOG.md`; changing a frozen item goes through `/contract-change` |
| Reconcile "a detector waits for its typology's approval" with the runner | `detect/CLAUDE.md` says a detector waits for approval; the runner runs draft typologies (Phase 1 report, deviation D-25 and section 9) | Tech lead | `detect/CLAUDE.md` or the runner, and the report |
| Two API behaviours | Phase 1 report, section 9 (#44): whether to declare the 500 problem on `GET /alerts/{alert_id}` in the OpenAPI document, and how alerts from earlier detection runs are pruned | Tech lead | `contracts/CHANGELOG.md` or a C3 change |
| Gate 1 outcome and the open Gate 1 checks | The "Confirmed by" column of the Phase 1 report, section 4, is empty for every MANUAL and FAIL check from GC-06 to GC-17 except GC-16, which cleared when the report merged | Project lead; each check's owner as that table names it | [reports/phase-1.md](reports/phase-1.md), section 4 |
| Review the autopilot decisions OD-11 to OD-17 | Taken under autopilot ([OD-10](operator-decisions.md)) and listed for review in the Phase 1 report, section 9 | Project lead | `operator-decisions.md` |
| Case-note statements and the research folder | Phase 1 report, section 9 (#29): browser checks of the justice.gov and OCCRP statements in the case notes, kept on the list by [OD-21](operator-decisions.md); and whether `docs/research/` is published on the documentation site | Project lead | The case notes; ADR-0012 |
| Legal and communications heads-up note | Gate 1 check GC-15: [PROGRESS.md](PROGRESS.md) has no such note | Project lead | `PROGRESS.md` |

## 2. Licences and data

| Decision | Still open because | Owner | Record it in |
|---|---|---|---|
| Approve the licence fields and statements | [DATA_SOURCES.md](../../DATA_SOURCES.md) opens with "Draft, owned by the data steward", and Gate 1 check GC-17 (approval of the licence fields in [contracts/datasets.yaml](../../contracts/datasets.yaml) and of `DATA_SOURCES.md`) has no confirmation recorded | Data steward | An approving review on the pull request, or the GC-17 row of the Phase 1 report |
| Which records hold synthetic accounts | Confirm that in the synthetic join only registry records hold synthetic accounts, and ICIJ and `PublicBody` records never do (ADR-0005 rule 2; Gate 1 check GC-09; #41) | Data steward with the tech lead | ADR-0005 and the GC-09 row of the Phase 1 report |
| Companies House `is_sanctioned` | Before Phase 2 uses Companies House data: whether that field ever becomes a flag on a real person. This is a G1 decision (Phase 1 report, section 9; #23) | Data steward | An operator decision or an ADR |
| Test the real-data guard | Before the first real-data run, the data steward tests `.claude/hooks/guard_real_data.py` with their own bypass attempts (Phase 1 report, section 9; #45) | Data steward | The pull request that enables the first real profile |
| Two MPL-2.0 dependencies: `lightningcss` (build time only) and `orjson` | Listed for a human licence decision in the Phase 1 report, section 9; no decision about either is in [operator-decisions.md](operator-decisions.md) | Tech lead with the project lead | `operator-decisions.md`, as [OD-20](operator-decisions.md) did for two other dependencies |
| OpenSanctions evaluation agreement | `access.opensanctions` is `none`. [OD-19](operator-decisions.md) waits for OpenSanctions' written confirmation, filed in `docs/data/licences/opensanctions.md`, which does not exist yet | Data steward, project lead | That file, then `access.opensanctions: evaluation` in `project.yaml` |
| UN sanctions list | `un_sc_sanctions` is not in `access.sanctions_lists`. It may be loaded only with the UN's written permission ([DATA_SOURCES.md](../../DATA_SOURCES.md), [OD-22](operator-decisions.md)) | Data steward | `access.sanctions_lists` in `project.yaml`, with the permission filed |
| Data protection documents for real data | `access.data_protection_filed` is `false` and `docs/data/dpia/` does not exist. Until both change, `access.real_data_profiles` stays `[]` and every run is synthetic ([OD-22](operator-decisions.md)) | Data steward, project lead | `docs/data/dpia/`, then `project.yaml` |
| Approved real-data machines | The table in [real-data-machines.md](../data/real-data-machines.md) has no rows | Data steward | That table |
| PEP sources | `access.pep_sources` is `[]`, so PEP flags exist only in synthetic data ([OD-22](operator-decisions.md)) | Data steward | `access.pep_sources` in `project.yaml` |
| Companies House live spike | `access.companies_house_key` is `pending`. The spike was built with mocks, and its live run and verdict wait for the key (Gate 1 check GC-08) | Operator; the verdict by the ingest mentor | `docs/data/spikes/companies-house.md` |

## 3. People to name

| Decision | Still open because | Owner | Record it in |
|---|---|---|---|
| Interns | `people.interns` is `[]`, so Gate 1 checks GC-11 to GC-13 fail ([OD-6](operator-decisions.md)) | Project lead | `people.interns` in `project.yaml` |
| Entity-resolution labellers and senior reviewer | `people.er_labellers` and `people.er_senior_reviewers` are `@TODO`. Labelling and the published precision figure wait for them ([PHASE-2.md](PHASE-2.md) G10) | Project lead | `project.yaml` |
| Detection freeze deciders | `people.freeze_deciders` is `@TODO` (typology researchers, detect mentor and tech lead; ADR-0022, not yet written; [PHASE-3.md](PHASE-3.md) 1.3) | Project lead | `project.yaml` |
| Held-out question owner | `people.heldout_owner` is `@TODO`. Assignment 5 cannot start without them: they assign each person's cards privately ([PHASE-4.md](PHASE-4.md) 1.3, [OD-25](operator-decisions.md)) | Project lead | `project.yaml` |
| Security and conduct contacts | `project.security_contact` and `project.conduct_contact` are `TODO@example.com`, which [SECURITY.md](../../SECURITY.md) and the [Code of Conduct](../../CODE_OF_CONDUCT.md) rely on | Project lead | `project.yaml` and those two files |

## 4. Repository

| Decision | Still open because | Owner | Record it in |
|---|---|---|---|
| Repository home | `project.repo` says `neonradar/neon-radar` and the squads name `@neonradar/nr-*` teams ([OD-7](operator-decisions.md)), but the repository is `Robotat-Technologies/neon-radar` | Operator | `project.yaml` and OD-7 |
| Branch protection | Gate 1 check GC-06 is MANUAL: a person confirms the interim controls ([ci.md](ci.md)) until `scripts/setup_repo_protection.sh` can run | Project lead | The GC-06 row of the Phase 1 report |
| Devcontainer | Milestone M1.5 is paused by the operator in pull request #19, which is still open (Gate 1 check GC-07) | Operator; the docs mentor confirms it works | Pull request #19 |

## 5. Coming up

Decisions the specs already reserve for people, which fall due when their milestone arrives.

| Decision | When | Owner | Record it in |
|---|---|---|---|
| Detection freeze | Milestone M3.11, after the freeze deciders are named ([PHASE-3.md](PHASE-3.md) 1.3) | Freeze deciders | ADR-0022 and `eval/freeze.json` |
| Holdout seeds | After the freeze record is accepted; nobody, human or agent, draws them earlier ([PHASE-3.md](PHASE-3.md) 1.3) | Tech lead | ADR-0022 and `eval/seeds.yaml` |
| Tag `contracts-v1.3.0` | After milestone M4.2 (the copilot contract) merges (`schedule.contracts_1_3_0` in [project.yaml](project.yaml)) | Tech lead | The tag and `contracts/CHANGELOG.md` |
