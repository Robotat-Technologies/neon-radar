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
- **Then two Splink 5 models**, `person` and `org` (PHASE-2.md 7.1.5; `resolve/src/neonradar_resolve/models.py`), trained on each run's own data: the prior from a deterministic rule with recall 0.7, u by random sampling (10 million pairs, seed 20261026), two expectation-maximisation sessions of 5 million pairs each (for persons, the postcode and then the first linked organisation with the birth year, OD-26 below; for organisations, the name key and then the postcode). Every prediction blocking rule includes the `synthetic` flag, so no synthetic-real pair is scored, and X1 refuses any such merge. The training rules (the prior and both expectation-maximisation sessions) and the random sampling for u do not include it: they estimate parameters and score no pair. No trained parameter is committed: `resolve/models/*.settings.json` hold the settings only, and the trained models stay in each run folder.
- **Under a constrained clustering** (`resolve/src/neonradar_resolve/cluster.py`) that refuses merges breaking X1 to X8 and applies the merge policy P1 to P6 of ADR-0015. A scored pair merges only at or above the merge threshold of the model that scored it and only with agreeing evidence other than the name (P3); a pair between the candidate threshold and the merge threshold becomes a possible match, described as "not confirmed" (PHASE-2.md 7.2).

### Why the comparisons are built from levels

Splink's `NameComparison` always adds a term-frequency adjustment to its exact level, and `configure(term_frequency_adjustments=False)` does not remove it; `DateOfBirthComparison` misfiles month-and-year strings (er-splink.md 2.3). The name, birth and incorporation comparisons are therefore built level by level with `CustomComparison`, so that only the exact name-key level is term-frequency adjusted, birth dates compare at day, month and year precision, and every level has a label an investigator can read (the labels go into `candidates.jsonl`, `canonical.csv` and the API's evidence, PHASE-2.md 7.2). `resolve/tests/test_run_probabilistic.py` fails when the committed settings files and the code disagree, so every change to comparisons or blocking shows up in review as a diff of those files.

### The form of D3 (the tech lead chooses before the freeze)

| Option | What it does |
|---|---|
| **The first 8 characters of `nr.ch_person_number`, with the name check** (default; built; OD-22 accepted it for the build) | Two officer records whose person numbers share the first 8 characters merge when their names also pass the name check; a different number never blocks a merge (PHASE-2.md 1.2 and 7.1.2). Both halves rest on community observations: posts read the first 8 characters as the person, and one person has been seen under several numbers. Companies House has not confirmed either (PHASE-2.md 3.3; `docs/research/2026-10-18/bulk-sources-loading.md` section 5) |
| **Blocking only** | D3 merges nothing; the person number only helps the person model find candidate pairs |

Chosen form: (set by the tech lead at the freeze).

### Training the person model (OD-26)

PHASE-2.md 7.1.5 blocks the person model's first expectation-maximisation session on surname and birth year. Those pairs are full of namesakes: different people with the same given name, surname and birth year, which the synthetic benchmark plants as near twins. The session counted them as matches. It learned that a postcode in the same district is evidence of a match (+2.75 bits on the large benchmark) and that different postcodes cost little. Trained that way, every false person merge at the starting values joined near twins (all 166 false pairs on the small benchmark, 1,540 of 1,544 on the large one), and no threshold of the calibration grid passed the gates.

Under OD-26 (an orchestrator decision under autopilot, which the deciders confirm with this ADR), the person sessions changed. The postcode session now runs first. The second session blocks on the first linked organisation with the birth year, and those pairs are mostly one person's records. Between them the two sessions still estimate every comparison: the postcode in the second, the birth date and the linked organisations in the first. A same-district postcode now weighs -0.76 bits on the large benchmark. The order matters: with the organisation session first, Splink's expectation maximisation drove the m of "birth years one apart" to exactly 0 on a development benchmark and refused it. The comparisons, the blocking rules and the settings files are unchanged; `models.py` differs from the spec in `train()` only, a recorded deviation. The change was developed on the large benchmark and on two small benchmarks with other seeds (11 and 12), never on the gate's fixture and never with a human label. The thresholds still come only from the rule of 7.1.7.

No comparison level was added. Of the false person pairs the large benchmark scores at 0.99 or more after the change, 650 of 803 join two Companies House records whose forename and surname agree while the full names differ, with the same birth month and no shared postcode or company; the register shows a birth month and no day, and a different postcode or company is common in one person's records too. The benchmark varies one person's middle name only by an initial, a dropped name or another spelling, so two different middle names are the evidence left that tells these near twins apart, and a level for conflicting middle names is the change left to try. It is not in this pull request: every level label needs investigator wording in PHASE-2.md 7.2 (M2.10c), and the policy-blocked gate fails at every threshold whatever the person model scores. It is open for the deciders.

### Thresholds

The starting values of PHASE-2.md 7.1.7 are in `er.yaml`: `merge_threshold.person` 0.99, `merge_threshold.org` 0.995, `candidate_threshold` 0.80. `neonradar er calibrate --size large` scored the large synthetic benchmark (seed 20261026) once down to 0.50 and re-clustered it at each threshold; the full output, which defines each column, is `docs/data/er/benchmark.md`:

| t | person precision | person recall | org precision | org recall | hard negatives merged | person-organisation pairs merged (merge, candidate) | policy-blocked recall (person, org, all) |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.8576 | 0.9745 | 0.9996 | 0.8956 | 410 | 0, 0 | 0.5852, 0.4049, 0.5393 |
| 0.8 | 0.8585 | 0.9725 | 0.9996 | 0.8956 | 409 | 0, 0 | 0.4961, 0.1261, 0.4020 |
| 0.9 | 0.8596 | 0.9713 | 0.9996 | 0.8956 | 406 | 0, 0 | 0.4961, 0.1261, 0.4020 |
| 0.95 | 0.8612 | 0.9699 | 0.9996 | 0.8956 | 400 | 0, 0 | 0.4917, 0.1261, 0.3987 |
| 0.98 | 0.8747 | 0.9573 | 1.0000 | 0.8956 | 348 | 0, 0 | 0.4686, 0.1261, 0.3816 |
| 0.99 | 0.9028 | 0.9227 | 1.0000 | 0.8956 | 234 | 0, 0 | 0.4365, 0.1261, 0.3576 |
| 0.995 | 0.9040 | 0.9096 | 1.0000 | 0.8956 | 217 | 0, 0 | 0.2726, 0.1261, 0.2353 |
| 0.998 | 1.0000 | 0.8562 | 1.0000 | 0.8956 | 0 | 0, 0 | 0.0594, 0.1261, 0.0764 |
| 0.999 | 1.0000 | 0.8559 | 1.0000 | 0.8956 | 0 | 0, 0 | 0.0000, 0.1261, 0.0320 |
| 0.9999 | 1.0000 | 0.8402 | 1.0000 | 0.8956 | 0 | 0, 0 | 0.0000, 0.1261, 0.0320 |

The rule of 7.1.7 proposes `merge_threshold.person` 0.998 (the lowest value with precision at least 0.98; before OD-26 it was 0.9999, with recall 0.8393), `merge_threshold.org` 0.5 and no `candidate_threshold` (no value reaches a policy-blocked recall of 0.90; the best is 0.5393 at 0.50). Organisation recall is 0.8956 at every `t`, so this benchmark does not tell organisation merge thresholds apart: 0.5 is the rule's mechanical output, the lowest value of the grid. Above a merge threshold of `er.yaml`, the policy-blocked column describes that merge threshold raised to `t`: the clustering drops every pair below the candidate threshold, so a candidate threshold above a merge threshold in effect raises it. No candidate threshold passes today, so this changes no proposal.

**The starting values fail the G2-05 gates** of `neonradar er bench --size small`, the benchmark CI runs: policy-blocked recall 0.4020 against 0.80, and 1 hard negative merged. Person precision 0.9953, person recall 0.8547, organisation precision 1.0000 and organisation recall 0.8738 pass. The same sweep on that benchmark (`neonradar er calibrate --size small --output <file>`, one DuckDB thread; `docs/data/er/benchmark.md` holds the large table only):

| t | person precision | person recall | org precision | org recall | hard negatives merged | person-organisation pairs merged (merge, candidate) | policy-blocked recall (person, org, all) |
|---|---|---|---|---|---|---|---|
| 0.5 | 0.8484 | 0.9621 | 1.0000 | 0.8738 | 42 | 0, 0 | 0.5809, 0.3978, 0.5322 |
| 0.8 | 0.8484 | 0.9621 | 1.0000 | 0.8738 | 42 | 0, 0 | 0.4698, 0.2151, 0.4020 |
| 0.9 | 0.8487 | 0.9596 | 1.0000 | 0.8738 | 41 | 0, 0 | 0.4698, 0.2151, 0.4020 |
| 0.95 | 0.8556 | 0.9516 | 1.0000 | 0.8738 | 37 | 0, 0 | 0.4698, 0.2151, 0.4020 |
| 0.98 | 0.8886 | 0.9144 | 1.0000 | 0.8738 | 24 | 0, 0 | 0.3957, 0.2151, 0.3476 |
| 0.99 | 0.9953 | 0.8547 | 1.0000 | 0.8738 | 1 | 0, 0 | 0.1871, 0.2151, 0.1946 |
| 0.995 | 0.9952 | 0.8410 | 1.0000 | 0.8738 | 1 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.998 | 0.9952 | 0.8378 | 1.0000 | 0.8738 | 1 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.999 | 1.0000 | 0.8362 | 1.0000 | 0.8738 | 0 | 0, 0 | 0.0000, 0.2151, 0.0572 |
| 0.9999 | 1.0000 | 0.7337 | 1.0000 | 0.8738 | 0 | 0, 0 | 0.0000, 0.2151, 0.0572 |

On the calibration grid (0.50 to 0.9999; pairs below 0.50 were not scored), no value of `candidate_threshold` passes the policy-blocked gate on either benchmark. On the small benchmark the person gates pass together from 0.999 (precision 1.0000, recall 0.8362); at 0.99 to 0.998, including the proposed 0.998, one hard negative is still merged.

Two observations describe the failures. They were counted for this ADR on the run folders of `er bench --size small` and `er calibrate --size large` (`canonical.csv` and `pairs.parquet`; the clusters of both use the merge thresholds of `er.yaml`) against `labels/er_truth.csv`, and on the benchmarks' records:

- **The false person merges still join near twins.** At the starting values, all 5 false person pairs of the small benchmark (the one hard negative merged) and all 1,219 of the large one join records of two near twins. Records of near twins that agree on name and birth month and share no postcode or company are scored like two records of one person who moved; a merge threshold above that score (0.998 on the large benchmark) keeps them apart.
- **Policy-blocked recall cannot reach 0.80 at any threshold of the grid.** A third of the policy-blocked true pairs join a leak-style record: 233 of 699 on the small benchmark, 2,367 of 6,927 on the large one. Such a record carries a name and at most a country, and the models score such pairs below 0.80. On the large benchmark, 196 of the 24,967 pairs scored at 0.50 or more include a leak-style record; none reaches 0.80, and the highest is 0.6332. The prior, about 1 in 13,500 pairs on the large benchmark, outweighs what a name and a country can show. Without those pairs, recall as a possible match is at most 0.6667 on the small benchmark and 0.6583 on the large one.

`er.yaml` and the rules are unchanged, and the deciders choose the values.

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
- Open for the deciders, before the evaluation sample: the threshold values; OD-26, the person training sessions; a level for conflicting middle names (above); and the policy-blocked gate, which no threshold of the grid and no model change within 7.1.5 can pass while a third of the policy-blocked pairs join a leak-style record that carries a name and at most a country. The options for that gate: a way for such records to become possible matches without a probability, as source hints do (a change to the clustering of 7.1.6, and for P2 to ADR-0015's deciders), other gate values, or another benchmark.
- Also open for the deciders (orchestrator decisions under OD-10): a class with fewer than two records or no comparison gets no model and is counted under `splink.models_skipped` in `run.json`. When Splink cannot train a model on the run's data (too few pairs for the prior or an expectation-maximisation session), a synthetic profile skips the class in the same way, scoring no pair of it, but a real profile fails the run; any other training error (an interrupt, a memory or disk error) fails every run. The alternatives: fail every run whose model cannot be trained, or skip on real profiles too.

## Sources

- `docs/build/PHASE-2.md` 2.1 (G1, G8, G10), 2.5, 3.3, 7.1.2, 7.1.4 to 7.1.7, 7.3, M2.9, M2.10b.
- `docs/research/2026-10-18/er-splink.md` (Splink 5 API, comparisons, training, DuckDB settings).
- `docs/research/2026-10-18/bulk-sources-loading.md` section 5 (the Companies House person number).
- `docs/data/er/benchmark.md` (the calibration table, generated by `neonradar er calibrate`).
- ADR-0015 (merge policy for listed and leaked records).
- [fellegi_sunter_1969], [splink_docs] in `docs/sources/bibliography.yaml`.
