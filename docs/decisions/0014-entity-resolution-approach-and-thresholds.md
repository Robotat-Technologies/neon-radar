# 0014. Entity resolution approach and thresholds

- **Status:** proposed
- **Date:** 2026-10-23
- **Deciders:** @robotat-com (tech lead, graph mentor)

## Context

NeonRadar joins records from registers, sanctions lists, leaks and synthetic sources into one graph, so the same person or company has to become one node (`docs/build/PHASE-2.md` 7.1). Some joins are certain because the two records share an identifier; most are not, because records of one person spell the name differently, carry a birth month in one source and a full date in another, or give no date at all. A wrong merge puts one person's facts, and possibly a flag, on another person (guardrails G1 and G8), so the approach has to keep merges precise, show the uncertain ones as possible matches, and let people measure both.

The probabilistic part follows the Fellegi and Sunter model of record linkage: each pair of records gets an agreement level per compared field, the levels are weighed by how often they occur among true matches (m) and among non-matches (u), and the sum decides between a link, a possible link and no link [fellegi_sunter_1969]. Splink 5 implements this model on DuckDB [splink_docs]; the research note `docs/research/2026-10-18/er-splink.md` checked its API and its behaviour on 18 October 2026.

Four things are decided here: the approach (rules, models, clustering), the three thresholds of `resolve/config/er.yaml`, the form of D3 and the evaluation sample seed. The thresholds must be set before the precision sample is drawn (PHASE-2.md 7.3), so that no label can tune them (G10).

## Options considered

1. **Splink alone, with its own clustering.** Simple, but Splink's clustering takes connected components of the links above a threshold and cannot refuse a merge, so the cannot-link rules (X1 to X8) and the merge policy of ADR-0015 could not be applied. Rejected.
2. **Deterministic rules only.** Precise, but on the synthetic benchmark the rules alone recall 0.1186 of the mergeable true person pairs (`neonradar er bench --size small` before this change). Rejected as the whole approach; kept as its first step.
3. **Deterministic rules first, then two Splink models, under a constrained clustering and the merge policy** (chosen, PHASE-2.md 7.1).

## Decision

We will resolve records in the order of PHASE-2.md 7.1.6:

- **Deterministic rules first** (D1 to D7, PHASE-2.md 7.1.2): UK company number, LEI, Companies House person number (D3), UN reference number, native id, address key and human decisions; D1 to D4 with the name check.
- **Then two Splink 5 models**, `person` and `org` (PHASE-2.md 7.1.5; `resolve/src/neonradar_resolve/models.py`), trained on each run's own data: the prior from a deterministic rule with recall 0.7, u by random sampling (10 million pairs, seed 20261026), two expectation-maximisation sessions of 5 million pairs each. Every prediction blocking rule includes the `synthetic` flag, so no synthetic-real pair is scored, and X1 refuses any such merge. The training rules (the prior and both expectation-maximisation sessions) and the random sampling for u do not include it: they estimate parameters and score no pair. No trained parameter is committed: `resolve/models/*.settings.json` hold the settings only, and the trained models stay in each run folder.
- **Under a constrained clustering** (`resolve/src/neonradar_resolve/cluster.py`) that refuses merges breaking X1 to X8 and applies the merge policy P1 to P6 of ADR-0015. A scored pair merges only at or above the merge threshold of the model that scored it and only with agreeing evidence other than the name (P3); a pair between the candidate threshold and the merge threshold becomes a possible match, described as "not confirmed" (PHASE-2.md 7.2).

### Why the comparisons are built from levels

Splink's `NameComparison` always adds a term-frequency adjustment to its exact level, and `configure(term_frequency_adjustments=False)` does not remove it; `DateOfBirthComparison` misfiles month-and-year strings (er-splink.md 2.3). The name, birth and incorporation comparisons are therefore built level by level with `CustomComparison`, so that only the exact name-key level is term-frequency adjusted, birth dates compare at day, month and year precision, and every level has a label an investigator can read (the labels go into `candidates.jsonl`, `canonical.csv` and the API's evidence, PHASE-2.md 7.2). `resolve/tests/test_run_probabilistic.py` fails when the committed settings files and the code disagree, so every change to comparisons or blocking shows up in review as a diff of those files.

### The form of D3 (the tech lead chooses before the freeze)

| Option | What it does |
|---|---|
| **The first 8 characters of `nr.ch_person_number`, with the name check** (default; built; OD-22 accepted it for the build) | Two officer records whose person numbers share the first 8 characters merge when their names also pass the name check; a different number never blocks a merge (PHASE-2.md 1.2 and 7.1.2). Both halves rest on community observations: posts read the first 8 characters as the person, and one person has been seen under several numbers. Companies House has not confirmed either (PHASE-2.md 3.3; `docs/research/2026-10-18/bulk-sources-loading.md` section 5) |
| **Blocking only** | D3 merges nothing; the person number only helps the person model find candidate pairs |

Chosen form: (set by the tech lead at the freeze).

### Thresholds

The starting values of PHASE-2.md 7.1.7 are in `er.yaml`: `merge_threshold.person` 0.99, `merge_threshold.org` 0.995, `candidate_threshold` 0.80. `neonradar er calibrate --size large` scored the large synthetic benchmark (seed 20261026) once down to 0.50 and re-clustered it at each threshold; the full output, which defines each column, is `docs/data/er/benchmark.md`:

| t | person precision | person recall | org precision | org recall | hard negatives merged | person-organisation pairs merged (merge, candidate) | policy-blocked recall (person, org, all) |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.8547 | 0.9746 | 0.9996 | 0.8956 | 418 | 0, 0 | 0.5858, 0.4049, 0.5398 |
| 0.8 | 0.8573 | 0.9726 | 0.9996 | 0.8956 | 415 | 0, 0 | 0.4977, 0.1261, 0.4032 |
| 0.9 | 0.8578 | 0.9716 | 0.9996 | 0.8956 | 414 | 0, 0 | 0.4977, 0.1261, 0.4032 |
| 0.95 | 0.8587 | 0.9700 | 0.9996 | 0.8956 | 411 | 0, 0 | 0.4932, 0.1261, 0.3999 |
| 0.98 | 0.8635 | 0.9611 | 1.0000 | 0.8956 | 390 | 0, 0 | 0.4700, 0.1261, 0.3826 |
| 0.99 | 0.8816 | 0.9369 | 1.0000 | 0.8956 | 314 | 0, 0 | 0.4379, 0.1261, 0.3586 |
| 0.995 | 0.8835 | 0.9110 | 1.0000 | 0.8956 | 290 | 0, 0 | 0.2729, 0.1261, 0.2356 |
| 0.998 | 0.9371 | 0.8575 | 1.0000 | 0.8956 | 137 | 0, 0 | 0.0594, 0.1261, 0.0764 |
| 0.999 | 0.9404 | 0.8572 | 1.0000 | 0.8956 | 126 | 0, 0 | 0.0000, 0.1261, 0.0320 |
| 0.9999 | 1.0000 | 0.8393 | 1.0000 | 0.8956 | 0 | 0, 0 | 0.0000, 0.1261, 0.0320 |

The rule of 7.1.7 proposes `merge_threshold.person` 0.9999 (the lowest value with precision at least 0.98), `merge_threshold.org` 0.5 and no `candidate_threshold` (no value reaches a policy-blocked recall of 0.90; the best is 0.5398 at 0.50). Organisation recall is 0.8956 at every `t`, so this benchmark does not tell organisation merge thresholds apart: 0.5 is the rule's mechanical output, the lowest value of the grid. Above a merge threshold of `er.yaml`, the policy-blocked column describes that merge threshold raised to `t`: the clustering drops every pair below the candidate threshold, so a candidate threshold above a merge threshold in effect raises it. No candidate threshold passes today, so this changes no proposal.

**The starting values fail the G2-05 gates** of `neonradar er bench --size small`, the benchmark CI runs: person precision 0.8711 against 0.97, policy-blocked recall 0.4063 against 0.80, and 29 hard negatives merged. The same sweep on that benchmark (`neonradar er calibrate --size small --output <file>`, one DuckDB thread; `docs/data/er/benchmark.md` holds the large table only):

| t | person precision | person recall | org precision | org recall | hard negatives merged | person-organisation pairs merged (merge, candidate) | policy-blocked recall (person, org, all) |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.8461 | 0.9629 | 1.0000 | 0.8738 | 43 | 0, 0 | 0.5809, 0.3978, 0.5322 |
| 0.8 | 0.8461 | 0.9629 | 1.0000 | 0.8738 | 43 | 0, 0 | 0.4756, 0.2151, 0.4063 |
| 0.9 | 0.8464 | 0.9605 | 1.0000 | 0.8738 | 42 | 0, 0 | 0.4756, 0.2151, 0.4063 |
| 0.95 | 0.8485 | 0.9540 | 1.0000 | 0.8738 | 40 | 0, 0 | 0.4756, 0.2151, 0.4063 |
| 0.98 | 0.8725 | 0.9169 | 1.0000 | 0.8738 | 29 | 0, 0 | 0.4016, 0.2151, 0.3519 |
| 0.99 | 0.8711 | 0.9056 | 1.0000 | 0.8738 | 29 | 0, 0 | 0.1891, 0.2151, 0.1960 |
| 0.995 | 0.9326 | 0.8491 | 1.0000 | 0.8738 | 14 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.998 | 0.9485 | 0.8475 | 1.0000 | 0.8738 | 9 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.999 | 0.9568 | 0.8402 | 1.0000 | 0.8738 | 8 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.9999 | 1.0000 | 0.7337 | 1.0000 | 0.8738 | 0 | 0, 0 | 0.0000, 0.2151, 0.0572 |

On the calibration grid (0.50 to 0.9999; pairs below 0.50 were not scored), no value of `merge_threshold.person` passes both person gates, and no value of `candidate_threshold` passes the policy-blocked gate. On the small benchmark person precision reaches 0.97 only at 0.9999, where person recall is 0.7337, below 0.80; on the large one person precision is 0.9404 at 0.999 and 1.0000 at 0.9999. Policy-blocked recall is at most 0.5322 on the small benchmark and 0.5398 on the large one, both at 0.50.

Two observations describe the failures. They were counted for this ADR on the run folders of `er bench --size small` and `er calibrate --size large` (`canonical.csv` and `candidates.jsonl`; the clusters of both use the merge thresholds of `er.yaml`) against `labels/er_truth.csv`, and, for the missed pairs, on every pair the blocking rules generate, scored once at threshold 0 with the same models and seed:

- **The false person merges join near twins.** At the starting values, all 166 false person pairs of the small benchmark, and 1,540 of the 1,544 of the large one, join records of two near twins. These are the hard negatives of M2.9: different people with the same given name and surname and the same birth year, half of them with the same birth month, some with the same postcode district. They make the 29 and 314 hard negatives merged.
- **The missed policy-blocked pairs carry little besides a name.** The small benchmark misses 415 policy-blocked true pairs at the starting values. Of these, 154 were never paired by a blocking rule, 186 scored below 0.50, and 75 scored between 0.50 and the candidate threshold of 0.80. In the 269 person pairs, the list or leak records carry at most a birth year and a country, never a postcode, an identifier or a linked organisation, and in 81 pairs one of them carries a name alone. In the 146 organisation pairs, they carry at most a jurisdiction, apart from 3 pairs where the record also carries a registration number, and never a postcode or an incorporation year; in 53 pairs one of them carries a name alone.

As PHASE-2.md M2.10b deliverable 7 says, `er.yaml`, the rules and the models are unchanged; the deciders choose.

Chosen values: (set by the deciders at the freeze, with the reason for each).

Evaluation sample seed: (set at the freeze)

### No real pair is labelled before the evaluation

The thresholds come from the synthetic benchmark only. No real pair is labelled before the evaluation sample is drawn, and the evaluation run ignores earlier review decisions (`er run --no-decisions`), so the published precision figure is measured on labels that never tuned a threshold, a rule or a model (G10, PHASE-2.md 7.3).

### The freeze

At the freeze (Thursday 29 October in PHASE-2.md 7.1.7; dates are informational under OD-1) the tech lead and the graph mentor accept this ADR with the D3 form, the three thresholds and the evaluation sample seed. From then until Gate 2, a change to a threshold, a rule, a comparison or the training settings needs both of them in the pull request and voids the evaluation sample (G10, PHASE-2.md 7.1.7). A change to the merge policy P1 to P6 also needs the deciders of ADR-0015: the data steward, the project lead and the tech lead (PHASE-2.md 7.1.4). Before any such change the build agent stops and asks (PHASE-2.md 2.5 item 10).

## Consequences

- Every pull request runs the G2-05 gates in CI (`er bench --size small`, one DuckDB thread, the last step of the `python` job), and every pull request that changes matching reports the benchmark before and after. The step fails until the deciders' values, or a model or feature change, pass the gates, so until then it fails on every pull request.
- Resolution needs DuckDB memory and time on the operator's machine: `er run` stops with exit code 4 before training when blocking would generate more than 20 million comparisons (`max_comparisons`), and spill files go to the run's own DuckDB folder, which is deleted when the run ends.
- Splink, DuckDB and PyArrow versions are recorded in every `run.json`; a lock bump of any of them is a model change and re-runs the benchmark.
- Open for the deciders: the threshold values, and what to do about the gates that no threshold passes (a model or feature change, other gates, or another benchmark), before the evaluation sample.
- Also open for the deciders (orchestrator decisions under OD-10): a class with fewer than two records or no comparison gets no model and is counted under `splink.models_skipped` in `run.json`. When Splink cannot train a model on the run's data (too few pairs for the prior or an expectation-maximisation session), a synthetic profile skips the class in the same way, scoring no pair of it, but a real profile fails the run; any other training error (an interrupt, a memory or disk error) fails every run. The alternatives: fail every run whose model cannot be trained, or skip on real profiles too.

## Sources

- `docs/build/PHASE-2.md` 2.1 (G1, G8, G10), 2.5, 3.3, 7.1.2, 7.1.4 to 7.1.7, 7.3, M2.9, M2.10b.
- `docs/research/2026-10-18/er-splink.md` (Splink 5 API, comparisons, training, DuckDB settings).
- `docs/research/2026-10-18/bulk-sources-loading.md` section 5 (the Companies House person number).
- `docs/data/er/benchmark.md` (the calibration table, generated by `neonradar er calibrate`).
- ADR-0015 (merge policy for listed and leaked records).
- [fellegi_sunter_1969], [splink_docs] in `docs/sources/bibliography.yaml`.
