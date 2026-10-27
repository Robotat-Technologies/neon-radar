# 0022. Evaluation protocol and the detection freeze

- **Status:** proposed
- **Date:** 2026-10-24 (drafted in M3.6; M3.11 adds the freeze date and the holdout seeds)
- **Deciders:** the typology researchers, the detect mentor and the tech lead (all held by @robotat-com until the team joins, OD-6); M3.11 replaces these roles with the handles in `people.freeze_deciders`

## Context

Phase 3 publishes, for each of its fourteen typologies, how often the detector finds a planted scenario and how often its alerts are right (PHASE-3.md 0.4, M3.12). The figures come from synthetic worlds, so the protocol decides what they mean. Five forces shape it:

- **The unit decides the number.** Scoring payments would weigh a 40-payment fan-in ten times more than a four-payment cycle and reward partial evidence; an analyst reviews alerts, one decision each, and a scenario is found or missed as a whole (`docs/research/2026-10-18-detection/evaluation-alerting.md` 1.2).
- **Small samples.** Ten scenarios per typology per world give wide intervals, and scenarios of one world share their background, so an interval that treats them as independent covers too little: in simulation the pooled Wilson interval alone covered 69 to 80 percent when seeds differed strongly, and the wider of it and a t interval across seeds covered 92 to 98.5 percent (`evaluation-alerting.md` 2.2, 2.3; PHASE-3.md 3.4).
- **Tuning leaks into figures.** The detectors are written and tuned on development worlds, so figures from those worlds are optimistic; only worlds nobody has seen before the code is fixed give an honest estimate (`evaluation-alerting.md` 2.5).
- **Silent drift.** A detector, a generator change or a numpy upgrade can move a count without anyone noticing; a version string moves only when someone remembers to bump it (`evaluation-alerting.md` 3.4; PHASE-3.md 3.1).
- **Claims travel.** A published table is quoted out of context; it must say what it measures and what it does not (PHASE-3.md 7.6.4).

## Options considered

1. **Payment-level precision and recall on one large world.** One number per typology and easy to compute; it rewards partial evidence, weighs typologies by their payment counts, and gives no honest interval.
2. **Scenario recall and alert precision on development seeds only.** Simple and reproducible by anyone; the figures are the ones the detectors were tuned on, so they overstate performance.
3. **Scenario recall and alert precision with one-to-one matching, open development seeds, a CI seed that gates every pull request, and holdout seeds that a person runs once after a freeze.** More machinery (a freeze file, a human-only command), in exchange for figures that mean what they say.

## Decision

We will take option 3, as PHASE-3.md 7.6 sets out and `neonradar eval` implements (M3.6).

1. **Units.** Recall counts planted illicit scenarios; precision counts alerts. Per typology: recall = scenarios detected / scenarios planted, precision = true alerts / all alerts of the typology (PHASE-3.md 7.6.3).
2. **Matching** (`detect/src/neonradar_detect/evaluation/match.py`, rules version 1, PHASE-3.md 7.6.2). An alert is compared only with scenarios of its own typology, by the rule of the typology's kind: intersection over union of `PAID` edges for payment typologies, of evidence nodes in the chain roles for `shell_chain`, the exposed organisation with every planted listed owner or PEP among the evidence for the two exposure typologies, and the hub for the three hub typologies. Pairs with an overlap of at least 0.5 are assigned one to one, best first, ties broken by ids (`evaluation-alerting.md` 1.3). An alert that covers half of a planted chain and half of an unrelated one has an overlap below 0.5 and is `partial`, never true.
3. **Counts.** Every alert counts as exactly one kind: `true`, `lookalike`, `duplicate`, `partial`, `other` (another typology's scenario) or `background`, and all but `true` count against precision. The report also gives look-alikes alerted out of look-alikes planted and precision among `high` and `medium` alerts (PHASE-3.md 7.6.3).
4. **Intervals.** Each rate carries the wider of the pooled Wilson 95 percent interval and the t interval across seeds; a rate with nothing to count is `None` in JSON and "n = 0" in the table, never 0 or 1. Macro figures are unweighted means over typologies, and macro F1 is the mean of per-typology F1, named as such (PHASE-3.md 3.4; `evaluation-alerting.md` 1.5).
5. **Seeds** (`eval/seeds.yaml`). Development seeds 1 to 10 are open to anyone for tuning and are always called development figures. Seed 1 is the CI seed: the `eval` job reruns it in memory and fails when any count of a merged detector differs from `eval/baselines/ci.json`, naming the typology and the count; a pull request that changes a detector on purpose updates its rows and explains each one under "Detection impact". Ten holdout seeds are drawn by the tech lead after this ADR is accepted, never chosen by hand and never redrawn because of a result (M3.11).
6. **The freeze** (`eval/freeze.json`, M3.11) pins everything that could move a published figure: the parameters of `synth-eval` with their hash, each detector's version, the typology files, the tracked code under the detectors, the generator and the evaluation, the Neo4j loader the holdout run uses, the profile, the seeds and the CI baseline, the matching rules, the label schema, the generator version, the planted mix, and the numpy and Faker versions (PHASE-3.md 7.6.1).
7. **The holdout run is human-only.** `neonradar eval run` with the test split runs only for a person at a terminal, never in CI or Codespaces, only when `eval/freeze.json` exists, `eval/seeds.yaml` lists the ten holdout seeds and the configuration equals the freeze; otherwise it exits 2. It always uses Neo4j and all ten seeds, and writes into `data/cache/holdout/`, which the build agent cannot read; the terminal gets each seed's record count and timings and the folder, never the figures, which stay in that folder until M3.12 publishes them. The agent hook blocks the agent from starting it (G11). Until M3.11 wires the freeze check in, the command always refuses.
8. **What the table may claim** (PHASE-3.md 7.6.4). It states what each column counts and what the figures do not show, in the fixed paragraphs of `report.py`. It never claims performance on real data, a false-positive rate for a bank, a comparison with a commercial system or a ranking of typologies by importance, and it never presents development figures as the evaluation. A typology with `n = 0`, or with figures far from the development figures, is published as measured. A pattern match is not evidence of wrongdoing.

## Consequences

- Every pull request runs the CI seed (about 70 seconds on two cores once all fourteen detectors have merged), so a count can no longer move without a "Detection impact" explanation; rows of typologies without a detector are reported as pending, never as failures.
- `neonradar eval run --split dev --seeds 1-5` reproduces the development table of PHASE-3.md 7.6.5 for every merged typology; a difference points to a verbatim file or the graph mapping.
- Precision depends on how many look-alikes and other scenarios were planted, so it says nothing about alert volumes in a bank; the report says so (`evaluation-alerting.md` 2.4).
- After the freeze, any change to a pinned file makes the holdout run refuse until the deciders accept a new freeze, which costs a human step but keeps the published figures tied to one configuration.
- M3.11 completes this record with the freeze date, the holdout seeds and who drew them; M3.12 publishes the holdout table; M3.13 compares it with the development table.

## Sources

- `docs/build/PHASE-3.md` 3.4 (formulas), 7.6 (protocol, matching, metrics, report, development figures), M3.6, M3.11, M3.12.
- `docs/research/2026-10-18-detection/evaluation-alerting.md` 1 (units, matching, counting), 2 (intervals, sample sizes, holdout seeds), 3 (CI gates), 6 (what other projects publish).
- `eval/seeds.yaml`, `eval/baselines/ci.json`, `detect/src/neonradar_detect/evaluation/`, `cli/src/neonradar_cli/evaluate.py`, `cli/src/neonradar_cli/eval_commands.py`.
