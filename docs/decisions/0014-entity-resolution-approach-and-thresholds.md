# 0014. Entity resolution approach and thresholds

- **Status:** proposed
- **Date:** 2026-10-23
- **Deciders:** @robotat-com (tech lead, graph mentor)

## Context

NeonRadar joins records from registers, sanctions lists, leaks and synthetic sources into one graph, so the same person or company has to become one node (`docs/build/PHASE-2.md` 7.1). Some joins are certain because the two records share an identifier; most are not, because records of one person spell the name differently, carry a birth month in one source and a full date in another, or give no date at all. A wrong merge puts one person's facts, and possibly a flag, on another person (guardrails G1 and G8), so the approach has to keep merges precise, show the uncertain ones as possible matches, and let people measure both.

The probabilistic part follows the Fellegi and Sunter model of record linkage: each pair of records gets an agreement level per compared field, the levels are weighed by how often they occur among true matches (m) and among non-matches (u), and the sum decides between a link, a possible link and no link [fellegi_sunter_1969]. Splink 5 implements this model on DuckDB [splink_docs]; the research note `docs/research/2026-10-18/er-splink.md` checked its API and its behaviour on 18 October 2026.

Two things are decided here: the approach (rules, models, clustering) and the three thresholds of `resolve/config/er.yaml`, which must be set before the precision sample is drawn (PHASE-2.md 7.3), so that no label can tune them (G10).

## Options considered

1. **Splink alone, with its own clustering.** Simple, but Splink's clustering takes connected components of the links above a threshold and cannot refuse a merge, so the cannot-link rules (X1 to X8) and the merge policy of ADR-0015 could not be applied. Rejected.
2. **Deterministic rules only.** Precise, but on the synthetic benchmark the rules alone recall 0.1186 of the mergeable true person pairs (`neonradar er bench --size small` before this change). Rejected as the whole approach; kept as its first step.
3. **Deterministic rules first, then two Splink models, under a constrained clustering and the merge policy** (chosen, PHASE-2.md 7.1).

## Decision

We will resolve records in the order of PHASE-2.md 7.1.6:

- **Deterministic rules first** (D1 to D7, PHASE-2.md 7.1.2): UK company number, LEI, Companies House person number (D3), UN reference number, native id, address key and human decisions, each identifier rule with the name check.
- **Then two Splink 5 models**, `person` and `org` (PHASE-2.md 7.1.5; `resolve/src/neonradar_resolve/models.py`), trained on each run's own data: the prior from a deterministic rule with recall 0.7, u by random sampling (10 million pairs, seed 20261026), two expectation-maximisation sessions of 5 million pairs each. Every blocking rule includes the `synthetic` flag, so synthetic and real records are never compared (X1). No trained parameter is committed: `resolve/models/*.settings.json` hold the settings only, and the trained models stay in each run folder.
- **Under a constrained clustering** (`resolve/src/neonradar_resolve/cluster.py`) that refuses merges breaking X1 to X8 and applies the merge policy P1 to P6 of ADR-0015. A scored pair merges only at or above the merge threshold of the model that scored it and only with agreeing evidence other than the name (P3); a pair between the candidate threshold and the merge threshold becomes a possible match, described as "not confirmed" (PHASE-2.md 7.2).

### Why the comparisons are built from levels

Splink's `NameComparison` always adds a term-frequency adjustment to its exact level, and `configure(term_frequency_adjustments=False)` does not remove it; `DateOfBirthComparison` misfiles month-and-year strings (er-splink.md 2.3). The name, birth and incorporation comparisons are therefore built level by level with `CustomComparison`, so that only the exact name-key level is term-frequency adjusted, birth dates compare at day, month and year precision, and every level has a label an investigator can read (the labels go into `candidates.jsonl`, `canonical.csv` and the API's evidence, PHASE-2.md 7.2). `resolve/tests/test_run_probabilistic.py` fails when the committed settings files and the code disagree, so every change to comparisons or blocking shows up in review as a diff of those files.

### The form of D3 (the tech lead chooses before the freeze)

| Option | What it does |
|---|---|
| **The first 8 characters of `nr.ch_person_number`, with the name check** (default; built; OD-22 accepted it for the build) | Two officer records whose person numbers share the first 8 characters merge when their names also pass the name check; a different number never blocks a merge, because one person can hold several (PHASE-2.md 1.2 and 7.1.2) |
| **Blocking only** | D3 merges nothing; the person number only helps the person model find candidate pairs |

Chosen form: (set by the tech lead at the freeze).

### Thresholds

The starting values of PHASE-2.md 7.1.7 are in `er.yaml`: `merge_threshold.person` 0.99, `merge_threshold.org` 0.995, `candidate_threshold` 0.80. `neonradar er calibrate --size large` scored the large synthetic benchmark (seed 20261026) once down to 0.50 and re-clustered it at each threshold; the full output is `docs/data/er/benchmark.md`:

| t | person precision | person recall | org precision | org recall | hard negatives merged | policy-blocked recall (person, org, all) |
|---|---|---|---|---|---|---|
| 0.5 | 0.8547 | 0.9746 | 0.9996 | 0.8956 | 418 | 0.5858, 0.4049, 0.5398 |
| 0.8 | 0.8573 | 0.9726 | 0.9996 | 0.8956 | 415 | 0.4977, 0.1261, 0.4032 |
| 0.9 | 0.8578 | 0.9716 | 0.9996 | 0.8956 | 414 | 0.4977, 0.1261, 0.4032 |
| 0.95 | 0.8587 | 0.9700 | 0.9996 | 0.8956 | 411 | 0.4932, 0.1261, 0.3999 |
| 0.98 | 0.8635 | 0.9611 | 1.0000 | 0.8956 | 390 | 0.4700, 0.1261, 0.3826 |
| 0.99 | 0.8816 | 0.9369 | 1.0000 | 0.8956 | 314 | 0.4379, 0.1261, 0.3586 |
| 0.995 | 0.8835 | 0.9110 | 1.0000 | 0.8956 | 290 | 0.2729, 0.1261, 0.2356 |
| 0.998 | 0.9371 | 0.8575 | 1.0000 | 0.8956 | 137 | 0.0594, 0.1261, 0.0764 |
| 0.999 | 0.9404 | 0.8572 | 1.0000 | 0.8956 | 126 | 0.0000, 0.1261, 0.0320 |
| 0.9999 | 1.0000 | 0.8393 | 1.0000 | 0.8956 | 0 | 0.0000, 0.1261, 0.0320 |

The rule of 7.1.7 proposes `merge_threshold.person` 0.9999 (the lowest value with precision at least 0.98), `merge_threshold.org` 0.5 (every value passes, because on the benchmark the organisation model merges no true pair that D1 has not merged already) and no `candidate_threshold` (no value reaches a policy-blocked recall of 0.90; the best is 0.5398 at 0.50).

**The starting values fail the G2-05 gates** of `neonradar er bench --size small` (person precision 0.8711 against 0.97, policy-blocked recall 0.4063 against 0.80, 29 hard negatives merged), and no choice of the three thresholds passes them all: person precision reaches 0.97 only at 0.9999, where the small benchmark's person recall falls to 0.7337, and policy-blocked recall stays below 0.80 at every candidate threshold. The false person merges are the benchmark's near twins (similar names, the same birth month, the same postcode district); the policy-blocked pairs that are missed are mostly list and leak records with a name and nothing else, which no blocking rule pairs or which score below 0.50. As PHASE-2.md M2.10b deliverable 7 says, `er.yaml`, the rules and the models are unchanged; the deciders choose.

Chosen values: (set by the deciders at the freeze, with the reason for each).

Evaluation sample seed: (set at the freeze)

### No real pair is labelled before the evaluation

The thresholds come from the synthetic benchmark only. No real pair is labelled before the evaluation sample is drawn, and the evaluation run ignores earlier review decisions (`er run --no-decisions`), so the published precision figure is measured on labels that never tuned a threshold, a rule or a model (G10, PHASE-2.md 7.3).

### The freeze

At the freeze (Thursday 29 October in PHASE-2.md 7.1.7; dates are informational under OD-1) the tech lead and the graph mentor accept this ADR with the D3 form, the three thresholds and the evaluation sample seed. From then until Gate 2, a change to a threshold, a rule, a comparison or the training settings needs both of them in the pull request and voids the evaluation sample (G10, PHASE-2.md 2.5 item 10).

## Consequences

- Every pull request that touches matching runs the G2-05 gates in CI (`er bench --size small`, one DuckDB thread) and reports the benchmark before and after.
- Resolution needs DuckDB memory and time on the operator's machine: `er run` stops with exit code 4 before training when blocking would generate more than 20 million comparisons (`max_comparisons`), and spill files go to the run's own DuckDB folder, which is deleted when the run ends.
- Splink, DuckDB and PyArrow versions are recorded in every `run.json`; a lock bump of any of them is a model change and re-runs the benchmark.
- Open for the deciders: the threshold values, and what to do about the gates that no threshold passes (a model or feature change, other gates, or another benchmark), before the evaluation sample.

## Sources

- `docs/build/PHASE-2.md` 2.1 (G1, G8, G10), 7.1.2, 7.1.5 to 7.1.7, 7.3, M2.10b.
- `docs/research/2026-10-18/er-splink.md` (Splink 5 API, comparisons, training, DuckDB settings).
- `docs/data/er/benchmark.md` (the calibration table, generated by `neonradar er calibrate`).
- ADR-0015 (merge policy for listed and leaked records).
- [fellegi_sunter_1969], [splink_docs] in `docs/sources/bibliography.yaml`.
