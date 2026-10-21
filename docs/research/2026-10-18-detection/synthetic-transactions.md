# NeonRadar phase 3: synthetic transactions and benchmarks

Research date: Sunday 18 October 2026. How facts were verified: generator repositories were cloned with git and read without running their code; papers, dataset pages and dataset APIs (arXiv, Kaggle, Zenodo, Hugging Face, Springer) and UK statistics and rules (UK Finance, Pay.UK, Bank of England, ONS, Department for Business and Trade, GOV.UK, legislation.gov.uk, eCFR) were read with a web fetch tool on 18 October 2026; package facts came from the PyPI JSON API and installed wheels; every timing was measured in this container (Python 3.14.6, numpy 2.5.4, orjson 3.13.0, followthemoney 4.11.0, 2 vCPUs, 7 GiB RAM). UNVERIFIED marks a fact I could not confirm at a primary source. "Assumption" marks a modelling choice with no public statistic behind it. "Inference" marks my own reasoning from verified facts. Facts already established in part A of `synthetic-docs-mcp.md` (16 October 2026) are cited as [S2] and not repeated; section 1.1 lists what changed.

## 0. Answers for the spec writer

1. **Generators and datasets.** Nothing published since part A changes the decision: NeonRadar keeps its own seeded Python generator. AMLSim is still unmaintained (last commit 14 February 2022; Apache-2.0) [S5]. AMLworld is data only (Kaggle version 8 of 8 July 2025, CDLA-Sharing-1.0, generator not released); its label is an `Is Laundering` column plus a `*_Patterns.txt` file of BEGIN and END blocks per laundering attempt; its paper reports minority-class F1 [S8][S9][S10]. SAML-D is data only (CC BY-NC-SA 4.0, unchanged since January 2024) [S13]. AMLGentex (Apache-2.0, last commit 22 February 2026) plants the eight AMLSim shapes, labels transactions with `isSAR`, `patternID` and `modelType`, reports average precision at recall above 0.6, and as pinned cannot be installed on Python 3.14 [S15][S16][S19]. Tide (MIT, last commit 8 June 2026) is the closest in spirit: log-normal amounts and benign "counter-leakage" patterns, but only a binary `is_fraudulent` label [S20][S21]. New since part A: AMLNet version 2.0 (July 2026, CC BY-NC 4.0, code withheld, labels `isMoneyLaundering` and `laundering_typology`) [S23]. Reuse: ideas from all of them with citation; code only from AMLSim, AMLGentex (Apache-2.0) and Tide (MIT) with their notices kept; external data only as optional user downloads through importers.

2. **Background activity.** Calibrate to UK Finance's 2025 volumes (49.7 billion payments; debit card 54 percent; cash 8 percent; Faster Payments and remote banking 6.2 billion; Direct Debit 5.1 billion; Bacs Direct Credit 1.8 billion; business payments 8.1 billion) [S29], ONS earnings and rents [S39][S40], HMRC deadlines [S44][S45][S46] and the scheme calendars (Faster Payments any time; CHAPS 06:00 to 18:00 on business days; Bacs on working days) [S31][S35]. Generate in Europe/London time and store UTC, with the GOV.UK bank holidays and clock changes for 2025 and 2026 [S37][S38]. Amounts are log-normal per purpose, fitted from published means plus an assumed median, in integer pence. No public statistic was found for the share of accounts inactive for 180 days: that share is an assumption. Real registry entities get a "plain" background profile with no typology-shaped look-alikes.

3. **Scenarios.** Each scenario instance is one object (typology, variant, roles, drawn parameters, window). Section 3 gives, for all 14 typologies, parameter ranges with their sources, three to five variants (including the `circular_flow` return to another account of the same holder and the `fan_in_collection` ring), difficulty knobs, and the PHASE-1.md 7.2 look-alikes with the features that separate them from the illicit version. Parameter ranges deliberately reach beyond the detectors' defaults. Two contract gaps showed up: the depositor of a cash deposit and the payment scheme cannot be expressed in C1 1.x.

4. **Label files.** None of the external datasets labels participants with roles: AMLworld has no attempt id in its transaction file, Tide has only a binary flag, AMLGentex has a pattern id but no roles. Labels v2 keeps the Phase 1 files with new columns appended and adds `labels/participants.csv` (scenario, object kind, C2 id, role, core flag, for entities, accounts, addresses and relationships), `labels/scenario_params.jsonl` (drawn parameters and expected metrics) and `labels/manifest.json` (label schema version and the SHA-256 of the record files). The evaluator matches an alert to a scenario when the alert's C2 ids cover at least half of the scenario's core objects, and reports scenario recall, alert precision, look-alike hit rate, and transaction, account and entity precision and recall with Wilson intervals.

5. **Determinism and speed.** Measured here: 2,000,000 Payment records generated day by day and written with orjson in 7.7 to 8.5 s (785,319,260 bytes, peak RSS 68 MiB), and 500,000 entity records in 1.5 to 1.6 s (140,528,622 bytes, peak RSS 80 MiB); every rerun was byte-identical, and a sample of 62,500 lines passed FtM 4.11 validation with `to_dict()` reproducing each line byte for byte [S59]. Rules: named `SeedSequence` keys with an explicit `PCG64`, fixed draw sizes, sorted iteration, integer pence and seconds, numpy pinned to a minor version. Traps found: each orjson output held in memory takes about 4.2 KB whatever its length, so write in batches of about 1,000 lines; FtM's `ValueEntity.from_dict()` removes `datasets` and `referents` from the dict it is given.

6. **Validity.** The literature warns that synthetic data gives optimistic results [S61], that models learn shortcuts [S62], that reused holdouts overfit [S63] and that rankings depend on benchmark choice [S65]. Rules: generator and detectors are written and parameterised independently (no imports either way, as PHASE-2.md M2.9 forbids the ER benchmark from importing the keys it tests); parameters are drawn wider than detector defaults; look-alikes and counter-leakage live in the background; the holdout seed is chosen only after the detectors are frozen, and some variants appear only in the holdout; leakage probes run in CI; results are reported per typology and variant; and the report says plainly that synthetic recall measures agreement with NeonRadar's own typology definitions, not real-world effectiveness.

## 1. Generators and labelled datasets in October 2026

### 1.1 What changed since part A (16 October 2026)

- AMLNet has a version 2.0 dataset on Zenodo, published 7 July 2026, with a typology column; part A cited version 1 only [S23].
- AMLworld: the `*_Patterns.txt` format is now verified from a third-party copy of HI-Small on Hugging Face [S10]. The Kaggle dataset is unchanged (version 8, updated 8 July 2025) [S9].
- SAML-D: the author's PhD thesis (completed 28 July 2025) adds the Tab-AML model and its results; data and licence are unchanged [S13][S14].
- Tide: the configuration at the latest commit (8 June 2026) differs from the paper values quoted in part A. For example the illicit structuring band is 7,500 to 9,900 and U-turns return 70 to 90 percent [S20]. Its export has only a binary `is_fraudulent` flag, with no pattern type or instance id [S20].
- AMLGentex: no new commits. Newly checked here: its label columns, its seeding (`RandomState(random_seed + ACCOUNT_ID)`), its metrics code, and that its pins (`requires-python <3.14`, `numpy==2.1.0`) rule out Python 3.14 [S15][S19].
- AMLSim: no new commits; the issues page now shows 48 open issues (part A: 47), newest #93 of 10 October 2026 [S6].
- New items: a co-evolution simulator with adaptive launderer and detector agents (2025, data on request) [S25]; Elliptic2, a real Bitcoin dataset with subgraph-level labels [S26]; J.P. Morgan's synthetic AML action traces [S27]; a 2025 systematic review that finds synthetic data "can give overly optimistic results" [S61].

### 1.2 Summary

| Name | State on 18 October 2026 | Licence | Runs on Python 3.14 | Reuse by NeonRadar |
|---|---|---|---|---|
| AMLSim (IBM) | Unmaintained; last `master` commit 2022-02-14 [S5] | Apache-2.0 code, no NOTICE file [S5] | No: networkx 1.11 needs Python 3.8 or older (Inference from part A's test on 3.12 and 3.13) [S2] | Ideas and code, keeping the licence; no dependency |
| AMLworld (IBM) | Data only; Kaggle v8 2025-07-08; generator not released [S8][S9] | CDLA-Sharing-1.0 data [S9] | Not applicable | Ideas with citation; data only as an optional user download |
| SAML-D | Data only; Kaggle v2 2024-01-12 [S13] | CC BY-NC-SA 4.0 data [S13] | Not applicable | Ideas with citation; never bundle the data |
| AMLGentex (AI Sweden) | Slow; last commit 2026-02-22 [S15] | Apache-2.0 code; Hugging Face data: 7 MIT, 5 without a licence tag [S17] | No as pinned [S15][S19] | Ideas and code with attribution; no dependency |
| Tide | Small and active; last commit 2026-06-08 [S20] | MIT code; data CC BY 4.0 [S2] | Not tested; pure Python, `requires-python >=3.10` [S20] | Ideas and code, keeping the MIT notice |
| AMLNet v2.0 | Data only; 2026-07-07; code withheld [S23] | CC BY-NC 4.0 [S23] | Not applicable | Ideas only |
| SynthAML | Static since 2023 [S2] | CC0 data; code withheld [S2] | Not applicable | Alert outcomes, not typologies; not useful for scenarios |
| PaySim | Unmaintained [S2] | GPL-3.0 code; CC BY-SA 4.0 data [S2] | Not applicable | No code reuse (GPL is barred by PHASE-1.md 2.6 [S1]) |
| FCA synthetic AML data | Sprint participants only [S24] | Not open [S24] | Not applicable | Ideas only |

### 1.3 Details per generator

#### AMLSim

- **Maintenance.** `master` is at commit 7338a4bc of 14 February 2022; later branches come only from bots (`renovate/configure` 8 May 2025, `whitesource/configure` 17 September 2025) [S5]. The issues page shows 48 open issues; the newest, #93 of 10 October 2026, describes an adaptation for AI-agent payment graphs [S6].
- **Patterns planted.** `fan_out`, `fan_in`, `cycle`, `bipartite`, `stack`, `random`, `scatter_gather`, `gather_scatter`, set per row of `alertPatterns.csv` with `count`, `min_accounts`, `max_accounts`, `min_amount`, `max_amount`, `min_period`, `max_period`, `bank_id` and `is_sar`; rows with `is_sar` False create typology-shaped false alerts [S2].
- **How it plants them.** A Python stage builds the account graph from `degree.csv` with networkx's directed configuration model and attaches alert subgraphs; a Java MASON stage executes them with schedules `FIXED_INTERVAL`, `RANDOM_INTERVAL`, `UNORDERED` or `SIMULTANEOUS`; cycle hops subtract a margin [S2].
- **Background.** Normal models single, fan-out, fan-in, mutual, forward and periodical, assigned in `accounts.csv`; one step is one day [S2].
- **Labels.** `transactions.csv` carries `is_sar` and `alert_id`; `alert_accounts.csv` lists alert members with `alert_type`, `start`, `end` and `schedule_id`; `alert_transactions.csv` and `sar_accounts.csv` complete the set [S2].
- **Metrics.** The simulator has no benchmark table of its own. The 2018 workshop paper that introduced it reports only preliminary efficiency results [S7].

#### AMLworld (Altman et al., NeurIPS 2023)

- **Maintenance.** arXiv 2306.16424 is at v3 (25 January 2024) [S8]. Kaggle shows version 8, updated 8 July 2025, 41,608,549,656 bytes, licence "Community Data License Agreement - Sharing - Version 1.0" [S9]. The generator code is not released [S2].
- **Patterns planted.** The paper's eight: Fan-out, Fan-in, Gather-scatter, Scatter-gather, Simple cycle, Random, Bipartite and Stack [S8]. In the patterns file the headers read `FAN-OUT`, `FAN-IN`, `GATHER-SCATTER`, `SCATTER-GATHER`, `CYCLE`, `RANDOM`, `BIPARTITE` and `STACK`, each with a size note, for example `BEGIN LAUNDERING ATTEMPT - FAN-OUT:  Max 16-degree Fan-Out` and `BEGIN LAUNDERING ATTEMPT - CYCLE:  Max 10 hops` [S10].
- **How it plants them.** Criminal agents receive funds from nine illicit sources (placement), then layer and integrate. Laundering "is not limited to specific patterns": in LI-Large 81,143 of 100,604 laundering transactions lie outside the eight patterns, and labels follow commingled funds downstream [S8][S2].
- **Background.** Individuals, corporations, partnerships, sole proprietors and banks in a "Circular Flow" economy, with several accounts per entity across banks and company cross-ownership. Payment formats are cheque, credit card, ACH, cash, reinvestment, wire and bitcoin. Calibration targets are the Atlanta Fed 2019 Survey of Consumer Payment Choice, the Federal Reserve Payments Study and IRS 2018 data (62.5 percent of people with salaries, 18.3 percent with pensions) [S8].
- **Labels.** `*_Trans.csv` has eleven columns ending in `Is Laundering` (0 or 1) [S11]. `*_Patterns.txt` lists each attempt as a `BEGIN LAUNDERING ATTEMPT - <PATTERN>: <note>` line, the attempt's transactions in the same eleven-column format, and an `END LAUNDERING ATTEMPT - <PATTERN>` line [S10]. The transaction file has no attempt id, so linking a transaction to its attempt means matching the whole row (Inference).
- **Metrics.** Minority-class F1 (percent) with a 60/20/20 temporal split. HI-Small: GIN 28.70, GIN+EU 47.73, PNA 56.77, GFP+LightGBM 62.86, GFP+XGBoost 63.23. LI-Small: 7.90, 20.62, 16.45, 20.83 and 27.30 [S8]. The paper names the main advantage of synthetic data: "the ground truth labels are complete", and warns that "performance might not translate one-to-one to real data" [S8].

#### SAML-D (Oztas et al., 2023)

- **Maintenance.** Kaggle version 2, updated 12 January 2024, one file `SAML-D.csv` of 996,168,850 bytes, CC BY-NC-SA 4.0; Kaggle's column metadata is empty [S13]. The PhD thesis (Bournemouth, 2025, CC BY-NC 4.0) does not mention released generator code [S14].
- **Typologies.** 28: 17 suspicious (Fan-Out, Fan-In, Cycle, Bipartite, Stacked Bipartite, Scatter-Gather, Gather-Scatter, Layered Fan-In, Layered Fan-Out, Structuring, Smurfing, Over-Invoicing, Deposit-Send, Cash Withdrawal, Single Large Transaction, Behaviour Change 1, Behavioural Change 2) and 11 normal (Single Transaction, Fan-Out, Fan-In, Mutual, Forward, Periodical, Cash Withdrawal, Cash Deposit, Small Fan-out, Mutual Plus, Normal Group) [S2].
- **How it plants them.** Agent-based plus typology-based simulation; each suspicious typology is generated separately; "The typologies with the same structure will have different parameter values that also overlap with each other"; layered fan typologies change value by 10 to 20 percent per layer; suspicious accounts also run normal typologies [S12].
- **Background.** Each normal account gets its "own unique combination of normal typologies"; the focus is the United Kingdom; payment types are credit card, debit card, cash, ACH, cross-border and cheque [S12].
- **Labels.** A binary "Is Suspicious" flag and a "Type" column per transaction (the paper's names). The exact CSV header spellings are UNVERIFIED, because Kaggle's column metadata is empty [S12][S13].
- **Metrics.** TPR, TNR, FPR, FNR and AUC for SVM, naive Bayes, decision tree and random forest, given only in figures [S12]. The thesis reports Tab-AML at 93.01 percent ROC-AUC, with a 17 percent lower false positive rate at a 98 percent true positive rate [S14].

#### AMLGentex (Östman et al., 2025)

- **Maintenance.** `main` is at 4b9a69db of 22 February 2026, 678 commits [S15]; arXiv 2506.13989 v2 is dated 25 September 2025 [S16]; the twelve Hugging Face datasets were last modified on 25 September 2025 [S17]. `pyproject.toml` says `requires-python = ">=3.10,<3.14"` and pins `numpy==2.1.0`, which has wheels only for cp310 to cp313, although the README says "Python 3.10+" [S15][S18][S19].
- **Patterns planted.** SAR types `fan_out` 1, `fan_in` 2, `cycle` 3, `bipartite` 4, `stack` 5, `random` 6, `scatter_gather` 7, `gather_scatter` 8; normal types `single` 10, `fan_out` 11, `fan_in` 12, `forward` 13, `mutual` 14, `periodical` 15; generic behaviour 0 (`src/utils/pattern_types.py`) [S15].
- **How it plants them.** A blueprint network comes from a truncated discrete power law (template: average degree 4). Normal patterns are kept only "if they can be fully accommodated", alert patterns are injected "regardless of fit", and launderer accounts are reused across patterns [S16]. An account selector weights candidates by personalised PageRank, degree, betweenness and KYC attributes [S15]. The temporal stage uses four burstiness levels drawn from Beta distributions (1,1), (2,2), (0.5,3) and (0.1,5), and funds come either as visible transfers or as cash invisible to the bank [S15][S16].
- **Background.** A source node pays log-normal salaries calibrated on Swedish demographics; a sink node receives spending with a sigmoid of the balance deviation; amounts are truncated Gaussians (template: normal mean 600, SD 250; SAR mean 667, SD 207; 1 to 150,000) [S15][S16].
- **Labels.** `tx_log.parquet` with `step`, `type` (`INITALBALANCE`, `TRANSFER`, `CASH`), `amount`, `nameOrig`, `nameDest`, `bankOrig`, `bankDest`, balance columns, `isSAR` (int8), `patternID` (int32, the instance) and `modelType` (int16, the type); node labels `is_sar` are derived; `noise.py` offers `flip_labels`, `missing_labels`, `flip_neighbours` and `topology_noise` [S15].
- **Metrics.** The paper's main metric is average precision at recall above 0.6, averaged over 10 seeds [S16]. `metrics.py` also computes precision at K (alert budget), recall at a maximum false positive rate and precision at a minimum recall [S15].
- **Seeding.** `np.random.RandomState(self.random_seed + row['ACCOUNT_ID'])` and `RandomState(self.random_seed + model_id)` [S15], the `seed + id` pattern NumPy calls "UNSAFE" [S58].

#### Tide (van den Beukel et al., 2026)

- **Maintenance.** `master` at 522ccebf of 8 June 2026, 107 commits [S20]; arXiv 2603.01863 v1 of 2 March 2026 [S21]; MIT licence; dependencies networkx, PyYAML and faker [S20].
- **Patterns planted.** `RepeatedOverseasTransfers`, `RapidFundMovement`, `FrontBusinessActivity`, `SynchronisedTransactions` and `UTurnTransactions`, plus a layering option that adds 2 to 5 extra hops with 1 to 48 hours between hops and 1 to 5 percent decay per hop [S20].
- **Parameters at the current commit** (`configs/patterns.yaml`) [S20]: structuring deposits 7,500 to 9,900 against a USD 10,000 threshold, 5 to 12 deposits; rapid movement 10 to 20 inflows of 500 to 3,000 from up to 30 senders, 5 to 12 withdrawals of 200 to 2,000, 1 to 24 hours later, 85 to 95 percent passed on; U-turn through 4 to 8 intermediaries, 3,000 to 15,000, 70 to 90 percent returned, 1 to 3 percent fee per hop, 1 to 7 days, business hours 9 to 16; synchronised deposits by 5 to 12 entities of 5,000 to 9,500 within 3 hours; a camouflage probability of 0.15 to 0.25 that a fraud transaction uses an everyday amount of 20 to 500.
- **Background.** Eleven weighted patterns: `randomPayments` 0.35, `fraudsterBackground` 0.25, `legitimateCashOperations` 0.15, `legitimateHighRiskActivity` 0.15, `legitimatePeriodicPayments` 0.12, `legitimateChains` 0.12, `salaryPayments` 0.08, `legitimateHighPayments` 0.08, `legitimateBurst` 0.08, `legitimateStructuring` 0.05 and `legitimateRapidFlow` 0.05. Amounts are log-normal per type (payment mu 3.8, sigma 1.2; transfer 5.5 and 2.0; deposit 5.3 and 1.5; withdrawal 4.8 and 0.9; salary 7.4 and 0.6; high value 9.6 and 1.5). Counter-leakage is deliberate: 3 percent of random payments fall in 7,000 to 9,900, 4 percent of users make legitimate deposits of 7,500 to 9,999, and legitimate rapid flows wait 4 to 72 hours. The default `configs/graph.yaml` targets a fraud ratio of 0.0005 [S20].
- **Labels.** `is_fraudulent` (boolean) on transaction edges and on nodes; the CSV export has no pattern type or instance id [S20].
- **Metrics.** PR-AUC: LightGBM 78.05 at the low illicit ratio (0.10 percent), XGBoost 85.12 at the higher one (0.19 percent) [S21].

#### AMLNet (Huda et al., 2025 and 2026)

- **Version 1** (arXiv 2509.11595 v1, 15 September 2025): 1,090,173 transactions, about 0.16 percent laundering, placement, layering and integration, 75 percent coverage of AUSTRAC rules, and an ensemble F1 of 0.90 (precision 0.84, recall 0.97) on internal test partitions [S22].
- **Version 2.0** (Zenodo 21237971, 7 July 2026, modified 11 August 2026): about 1.09 million transactions, 1,411 suspicious (about 0.13 percent), 195 days from 13 October 2025 to 27 April 2026, one 764.6 MB CSV; label columns `isFraud`, `isMoneyLaundering` and `laundering_typology` (normal, structuring, layering, integration); CC BY-NC 4.0; the generator is withheld "due to security concerns" [S23].

#### Other items from 2024 to 2026

- **FCA synthetic AML data** (15 April 2026): built with the Adaptive and Iterative Mechanism (AIM) from UK retail-banking data, with "structuring, layering, roundtripping, high-risk jurisdiction transfers, and so on"; the FCA warns about "firms optimising their systems to detect the specific typologies embedded in the dataset" and says users "should not treat the dataset as exhaustive"; access only during a data sprint [S24].
- **Hide and seek** (Wang et al., Complex and Intelligent Systems, 2025): laundering and legitimate agents "continuously adapt their strategies to either evade or follow detection" while a detector agent evolves; data "available from the corresponding author upon reasonable request"; article CC BY-NC-ND 4.0 [S25].
- **Elliptic2** (Bellei et al., 2024): real Bitcoin data, not synthetic, with 122K labelled subgraphs in a background graph of 49 million node clusters; a precedent for subgraph-level (scenario-level) labels; licence not stated on arXiv (UNVERIFIED) [S26].
- **J.P. Morgan synthetic AML data**: sequences of customer and bank interactions "generated by running an AI planning-execution simulator"; no fields, size or licence on the page (UNVERIFIED) [S27].
- **Crypto simulation** (Srivasthav and Apte, arXiv 2501.00757, January 2025): entity-specific behaviour simulation for crypto AML; code release not stated (UNVERIFIED) [S28].

### 1.4 What NeonRadar takes from them

- Benign shapes as labelled scenarios: AMLSim's `is_sar` False rows [S2] become look-alike scenarios with `is_lookalike` true.
- Some illicit money outside templates: AMLworld labels most LI-Large laundering outside the eight patterns [S8]. Inference: an optional `other_illicit` scenario class lets the report show what no detector targets.
- Overlapping parameters between scenarios of the same shape (SAML-D) [S12], and benign background in illicit-looking ranges (Tide) [S20].
- Burstiness levels from Beta distributions for scenario timing (AMLGentex) [S15].
- Label noise and per-bank partial observability for robustness experiments only, never for the Gate 3 numbers (AMLGentex) [S15][S16].
- Alert-budget metrics, precision at K (AMLGentex) [S15], because C4 alerts carry a `pattern_strength` order [S1].
- Instance ids and roles in labels: AMLGentex has `patternID`, the others do not; NeonRadar goes further with roles (section 4).
- Do not copy AMLGentex's `seed + id` seeding [S15][S58].

## 2. Background activity that looks ordinary

### 2.1 UK payment volumes in 2025

UK Finance, UK Payment Markets 2026 (published August 2026, 2025 data) [S29]:

| Flow | 2025 volume | Note |
|---|---|---|
| All payments, excluding CHAPS | 49.7 billion | 2 percent more than in 2024 |
| Consumer payments | 41.6 billion | 35.0 billion spontaneous, 6.5 billion regular bills and commitments |
| Business payments | 8.1 billion | 5.0 billion business to business, 3.1 billion business to individual |
| Debit card | 26,610 million | 54 percent of payments; 63 percent of consumer payment volume, 40 percent of value |
| Credit and charge card | 5,333 million | |
| Faster Payments and other remote banking | 6,190 million | 10 percent more than in 2024 |
| Direct Debit | 5,090 million | about 7 in 10 regular bills |
| Bacs Direct Credit | 1,835 million | 23 percent of business payments |
| Cash | 3,942 million | 8 percent of payments (17 percent in 2020) |
| Standing orders | 551 million | |
| Cheques | 77 million | 16 percent fewer than in 2024 |
| CHAPS | 53.3 million | worth £93.9 trillion |
| Contactless, cards and wallets | 19.2 billion | 39 percent of payments |

Pay.UK adds that the Faster Payment System processed 5.55 billion transactions worth £4.84 trillion in 2025 [S31], and Bacs 6.86 billion payments worth £6.05 trillion, including 5.0 billion Direct Debits [S34].

Rates derived from those figures (Inference; the adult base is UK Finance's own "45.9 million adults (80% of adults)", about 57.4 million adults):

| Measure | Value | Derivation |
|---|---|---|
| Debit card payments per adult | about 464 a year, 8.9 a week | 26,610 million / 57.4 million [S29] |
| Credit card payments per adult | about 93 a year, 1.8 a week | 5,333 million / 57.4 million [S29] |
| Consumer cash payments per adult | about 66 a year, 1.3 a week | 3.8 billion / 57.4 million [S29] |
| Regular bills per adult | about 113 a year, 9.4 a month | 6.5 billion / 57.4 million [S29] |
| Business payments per business | about 1,420 a year, very skewed | 8.1 billion / 5.69 million businesses [S29][S42] |
| Mean Faster Payment | about £872 | £4.84 trillion / 5.55 billion [S31] |
| Mean Bacs payment | about £882 | £6.05 trillion / 6.86 billion [S34] |
| Mean CHAPS payment | about £1.76 million | £93.9 trillion / 53.3 million [S29] |
| Mean debit card payment | about £29 | £68.7 billion / 2,333 million, March 2026 [S30] |
| Mean credit card payment | about £57 | £23.8 billion / 419 million, March 2026 [S30] |
| Mean Post Office cash deposit | about £424 | £2.87 billion / 6.77 million, October 2025 [S49] |
| Mean Post Office cash withdrawal | about £140 | £1.04 billion / 7.44 million, October 2025 [S49] |

### 2.2 Companies

UK businesses at the start of 2025: 5.7 million, of which 75 percent have no employees, 1,150,875 have 1 to 9, 220,085 have 10 to 49, 38,435 have 50 to 249 and 8,335 have 250 or more [S42]. So most synthetic companies should have no payroll at all, and "no payroll" is a weak signal for any typology (Inference).

| Flow | Frequency and timing | C1 `nr.channel` | Amount | Basis |
|---|---|---|---|---|
| Payroll | Monthly for about 76 percent of jobs (ASHE April 2019, via a secondary source), otherwise weekly, fortnightly or four-weekly; a fixed payday, moved to the previous working day when it falls on a weekend or bank holiday | `wire` | Net pay from a log-normal gross; full-time median £39,039 a year, part-time median £280 a week (April 2025); deductions at 2026-27 rates | Frequency [S41]; earnings [S39]; rates [S48]; the payday rule is an assumption |
| PAYE to HMRC | Monthly, due by the 22nd of the next tax month (tax months start on the 6th); small employers may pay quarterly | `wire` | Employee tax and NI of the month, plus employer NI (assumption) | [S44] |
| VAT | Quarterly; due one calendar month and 7 days after the period ends | `wire` | Assumption: 20 percent of value added | [S45] |
| Corporation tax | Yearly, 9 months and 1 day after the accounting period ends (taxable profits up to £1.5 million) | `wire` | Assumption: share of profit | [S46] |
| Suppliers | Invoices paid on average 32 days after issue (large businesses, 2025; 15 percent late by number); weekly or fortnightly payment runs (assumption) | `wire` | Log-normal per supplier, stable per relationship | [S43] |
| Customer receipts | Card settlements from an acquirer every working day; business customers by Faster Payment or Bacs (assumption) | `wire` | Proportional to sales | Assumption |
| Rent and premises | Quarterly in advance or monthly (assumption) | `wire` | Scales with size band | Assumption |
| Utilities, insurance, leases | Monthly Direct Debits | `wire` | Fixed or seasonal | Assumption |
| Loans | Drawdown, then monthly repayments with interest | `wire` | Repayments total above principal | Assumption; benign `circular_flow` look-alike [S1] |
| Owners | Director salary monthly, dividends quarterly or yearly | `wire` | Assumption | Assumption |
| Company cards | Weekly fuel, travel and subscriptions | `card` | Log-normal | Assumption |

### 2.3 People

| Flow | Frequency and timing | C1 `nr.channel` | Amount | Basis |
|---|---|---|---|---|
| Salary | Monthly for most, on payday, posted early on the settlement day | `wire` | Median full-time net about £2,636 a month (calculation: £39,039 gross in April 2025, 2026-27 personal allowance £12,570, 20 percent basic rate, employee NI 8 percent between £1,048 and £4,189 a month, no pension deduction) | [S39][S48] |
| Rent | Monthly | `wire` | UK average £1,400 a month in August 2026 (England £1,459, Scotland £1,013, Wales £846, London £2,332) | [S40] |
| Mortgage | Monthly Direct Debit | `wire` | Assumption scaled from the UK average house price of £273,000 (July 2026) | [S40] |
| Council Tax | "usually split into 10 monthly payments", 12 on request | `wire` | Assumption by band | [S47] |
| Other bills | About 9.4 regular payments per adult per month | `wire` | Fixed or seasonal | Derived from [S29] |
| Card spending | About 8.9 debit and 1.8 credit payments per adult per week; 75 percent of debit payments contactless (March 2026); contactless limits set by each firm since March 2026 | `card` | Means about £29 (debit) and £57 (credit) | [S29][S30][S55] |
| Cash | About 1.3 cash payments per adult per week; withdrawals average about £140 at the Post Office | `cash_withdrawal` | Log-normal | [S29][S49] |
| Transfers to people | A few a month (assumption) | `wire` | Log-normal, lower than the £872 mean of all Faster Payments (assumption) | [S31] |
| Savings | Monthly to an own savings account | `internal` | Fixed, often round | Assumption |
| No account | About 0.9 million adults were unbanked in 2024 | none | none | [S56] |

### 2.4 Cash-intensive businesses

- Cash was 8 percent of all UK payments in 2025 [S29] but 19.9 percent of retail transactions in 2023 [S50]; Post Office cash deposits averaged about £424 in October 2025, business and personal combined [S49].
- Model (assumption): daily takings = size baseline x weekday factor x season x noise; a sector cash share (for example cafe 0.25, takeaway 0.30, convenience store 0.25, car wash 0.50, market trader 0.60: all assumptions to be documented in the generator); cash banked one to six times a week on opening days only; card settlements every working day; supplier, payroll and rent outflows in proportion to revenue.
- Each cash deposit is a `Payment` from a synthetic branch `cash_ledger` account with `nr.channel` `cash_deposit` (C1) [S1].

### 2.5 Shape of amounts

- Log-normal per purpose, stored as integer pence and written as a two-decimal string (C1 R7) [S1]. With a published mean m and an assumed median M: sigma = sqrt(2 ln(m / M)) and mu = ln(M). Example: debit cards, m = £29.45 [S30] and M = £15 (assumption), give sigma = 1.16 and mu = 2.71.
- Precedents: Tide uses one log-normal per transaction type [S20]; AMLGentex uses truncated Gaussians and log-normal salaries [S15][S16]; AMLworld calibrates to Federal Reserve and IRS statistics [S8].
- Fixed amounts where life is fixed (assumption): salary within plus or minus 3 percent month to month, rent fixed for 12 months, Direct Debits fixed or seasonal.
- Round amounts occur in both classes (rent, transfers to people, savings) at the same base rate, so roundness is never a free label (Inference; part A noted this leak in AMLSim [S2]).

### 2.6 Timing

- Generate in Europe/London time and store UTC (C1 R5 requires UTC without an offset) [S1]. British Summer Time ran from 30 March to 26 October 2025 and runs from 29 March to 25 October 2026 [S38]. `zoneinfo` converts correctly across these dates (tested here) [S59].
- Schemes: the Faster Payment System "is available day and night, 365 days per year" [S31], and online and phone payments "must arrive by the end of the following business day at the latest" [S33]. Single Faster Payments of up to £1 million are possible, but each provider sets its own limits [S32] (assumption: personal transfers clipped at £25,000). CHAPS settles in "the current 6am to 6pm window" on business days, with contingency from 6pm to 8pm [S35]; an optional 01:30 start is planned for September 2027 [S36]. Bacs runs on working days; its three-day cycle is UNVERIFIED at a primary source here (assumption: credits land on day three). Which bank-holiday calendar the schemes follow is UNVERIFIED (assumption: England and Wales).
- Hours (assumption, local time): card payments 07:00 to 22:00 with peaks at 12:00 to 14:00 and 17:00 to 19:00; transfers between people 08:00 to 23:00; company payment runs on working days 08:00 to 18:00; Bacs credits posted 00:00 to 06:00 on the settlement day; cash deposits during branch hours 09:00 to 17:30, Monday to Saturday.
- Bank holidays (GOV.UK JSON) [S37]:

| Date | England and Wales | Scotland | Northern Ireland | Name |
|---|---|---|---|---|
| 2025-01-01 | yes | yes | yes | New Year's Day |
| 2025-01-02 | | yes | | 2nd January |
| 2025-03-17 | | | yes | St Patrick's Day |
| 2025-04-18 | yes | yes | yes | Good Friday |
| 2025-04-21 | yes | | yes | Easter Monday |
| 2025-05-05 | yes | yes | yes | Early May bank holiday |
| 2025-05-26 | yes | yes | yes | Spring bank holiday |
| 2025-07-14 | | | yes | Battle of the Boyne (substitute day) |
| 2025-08-04 | | yes | | Summer bank holiday |
| 2025-08-25 | yes | | yes | Summer bank holiday |
| 2025-12-01 | | yes | | St Andrew's Day (substitute day) |
| 2025-12-25 | yes | yes | yes | Christmas Day |
| 2025-12-26 | yes | yes | yes | Boxing Day |
| 2026-01-01 | yes | yes | yes | New Year's Day |
| 2026-01-02 | | yes | | 2nd January |
| 2026-03-17 | | | yes | St Patrick's Day |
| 2026-04-03 | yes | yes | yes | Good Friday |
| 2026-04-06 | yes | | yes | Easter Monday |
| 2026-05-04 | yes | yes | yes | Early May bank holiday |
| 2026-05-25 | yes | yes | yes | Spring bank holiday |
| 2026-06-15 | | yes | | World Cup bank holiday |
| 2026-07-13 | | | yes | Battle of the Boyne (substitute day) |
| 2026-08-03 | | yes | | Summer bank holiday |
| 2026-08-31 | yes | | yes | Summer bank holiday |
| 2026-11-30 | | yes | | St Andrew's Day |
| 2026-12-25 | yes | yes | yes | Christmas Day |
| 2026-12-28 | yes | yes | yes | Boxing Day (substitute day) |

- Commit this table as data rather than fetching it at runtime (guardrail G3 forbids runtime network calls [S1]).

### 2.7 Currency, counterparties, opening dates and dormancy

- **Currency.** GBP for `gb` accounts; a share of trading companies also hold EUR or USD accounts (assumption: 5 to 15 percent); offshore synthetic companies (`cy`, `vg`, `ae`) hold EUR or USD (assumption). C1 `Payment` has one `amount` and one `currency` [S1], so a cross-currency transfer is two payments through an internal FX account (assumption).
- **Counterparties.** Each entity draws a fixed set of relationships first (employer, landlord, 10 to 40 merchants, 3 to 15 contacts, 5 to 200 suppliers by size band; all assumptions) and then draws events from those sets with heavy-tailed weights, so most payments repeat known counterparties. Precedents: AMLGentex's power-law blueprint [S15][S16], Tide's hub-and-spoke random payments [S20] and AMLworld's circular-flow economy [S8].
- **Opening dates.** Company accounts open 0 to 60 days after incorporation (assumption). Personal accounts follow a tenure mixture (assumption: 60 percent 5 to 30 years, 30 percent 1 to 5 years, 10 percent under a year). Context for low churn: the Current Account Switch Service completed 1,054,521 switches in the 12 months to the end of 2025 [S51]. Mule-like accounts in scenarios are recent, following the FATF, INTERPOL and Egmont indicator of accounts opened at three or more institutions within 20 days, quoted in `aml-domain.md` (e) [S3].
- **Dormancy.** In UK law an account is "dormant" after 15 years with no transactions by the holder [S52]; the catalog's AML default is 180 days [S1]. I found no public statistic for the share of UK accounts with no activity for 180 days (UNVERIFIED). Assumption: at any time 5 percent of personal current accounts, 20 percent of personal savings accounts and 10 percent of company accounts are dormant in that sense, and 1 to 3 percent of them reactivate each month for ordinary reasons. Phase 2 loads the Companies House accounts category (for example `DORMANT`) into `nr.accounts_category` [S4]; a counts-only operator report could calibrate the synthetic share (Inference).
- **Time span.** Use 24 months of background (for example January 2025 to December 2026), so dormancy gaps of 180 days and yearly seasonality are both visible (Inference).

### 2.8 Background on real registry entities

- Guardrails: real entities receive background activity only, never a scenario role (G1) [S1]; the agent never reads real data, real profiles live only in `neo4j-real`, and the loader refuses a load that mixes synthetic and non-synthetic records (G9, L17) [S4].
- So the overlay for real entities is a file of synthetic records only (accounts, account `Ownership` records, payments) that reference real record ids, loaded additively with `--no-replace` and resolved through `:SourceRecord` (L9, L13) [S4]. Humans run it; commands print counts only [S4].
- Recommendation (Inference from G1 and G5 [S1]): give real entities a "plain" background profile without typology-shaped look-alikes (no sub-threshold cash series, no pass-through behaviour, no cycles among real entities, no dormancy followed by a burst, no payments among real companies that share an address or a director). Any alert that still touches a real entity is a `structural_pattern` alert with `synthetic_activity` true, as C4 defines [S1].
- Key each real entity's background stream by its record id (section 5), so its activity stays the same when the registry slice changes.
- Precision and recall are measured only on fully synthetic benchmarks. Mixing `syn-` scenarios with real `gbch-` entities would let a detector score perfectly from the id prefix (Inference).

## 3. Scenario designs for each typology

### 3.1 Rules for all scenarios

- **G1.** Every scenario participant (illicit or look-alike) is a synthetic record whose id starts with `syn-`; the generator asserts it and the label tests check it [S1].
- **Scenario object.** `scenario_id`, `typology`, `variant`, `is_lookalike`, `difficulty`, `split`, roles (role to C2 ids), drawn parameters, expected metrics and a time window. It writes payments and relationships into the common record stream; labels go only to label files (C1 R9) [S1].
- **Participants.** Mostly drawn from the existing synthetic population, keeping their normal history as camouflage; new scenario entities (shells, mules) are created by the same registry code that creates benign entities, and an equal number of benign entities is created the same way (for example start-ups), so "recently created" is not a label by itself (Inference).
- **No leaks through ids or order.** Assign payment ids only after background and scenario payments are merged and sorted (by time, payer account, beneficiary account, amount, then a fixed tie-break), so ids, file position and manifest counts carry no label (Inference).
- **Look-alikes.** Each illicit scenario has look-alikes of the same shape (default two per illicit scenario; assumption), drawn from the PHASE-1.md 7.2 list for that typology [S1].
- **Presets.** HI and LI illicit ratios in line with published datasets: AMLworld 1 per 807 to 1 per 1,948 transactions [S2], Tide 0.10 and 0.19 percent [S21], AMLNet 0.13 percent [S23].
- **Ranges past the defaults.** Parameter ranges come from the typology researcher and the sources; they are wider than the detector defaults on purpose (section 6).

### 3.2 Difficulty knobs for every typology

| Knob | Easy | Hard | Basis |
|---|---|---|---|
| Overlap of illicit and benign parameter ranges | none | large | SAML-D overlapping parameters [S12] |
| Counter-leakage: benign background in illicit ranges | none | 3 to 5 percent of the relevant flows | Tide [S20] |
| Camouflage: normal activity on illicit accounts | none | all illicit accounts | Tide `fraudsterBackground`, AMLSim [S20][S2] |
| Everyday-amount camouflage within a scenario | 0 | 0.25 of scenario payments | Tide camouflage probability [S20] |
| Timing burstiness | level 4 (bursty) | level 1 (spread) | AMLGentex Beta levels [S15] |
| Partial patterns: scenario cut short but still labelled | 0 | 30 percent of scenarios | Assumption |
| Boundary variants just outside detector defaults | 0 | 20 percent | Section 6 |
| Hidden hops: some hops at a bank outside the data | 0 | 1 hop | AMLGentex partial observability [S16] |
| Look-alike ratio | 0.5 per illicit | 3 per illicit | Assumption |

### 3.3 `structuring` (core)

- **Pattern.** Cash deposits (`cash_deposit` payments from branch `cash_ledger` accounts) into one account, or several accounts of one holder, within a short window, each just under a threshold, often through several branches, with a daily total above it [S1].
- **Roles.** `target_account`, `target_holder`, `branch_ledger`, `onward_beneficiary`.
- **Parameters.** Threshold T, default 10,000 with a 10 percent band (catalog) [S1]. UK anchor: a high value dealer applies the regulations to cash of "at least £10,000 in total", including operations "which appear to be linked" [S53]. US anchor: currency transactions over $10,000 are reported, and several are aggregated per business day [S54]. Deposits at 0.80 to 0.999 of T (Tide uses 7,500 to 9,900 for 10,000 [S20]); 3 to 15 deposits, 1 to 4 a day, over 1 to 10 days, through 1 to 4 branches, into 1 to 3 accounts; optional onward wire of 80 to 98 percent of the total within 1 to 5 days (assumption).
- **Variants.** `single_account_burst`; `multi_branch`; `multi_account_same_holder`; `spread_below_daily` (every daily total stays under T, only the weekly total exceeds it; harder, and the reason the US rule aggregates per day [S54]; holdout-only, see 6.2); `with_onward_wire`.
- **Knobs.** Band width; share of round amounts (same as benign); deposit count; the holder's ordinary deposits; partial bursts.
- **Look-alikes** [S1] and the features that separate them: cash businesses banking daily takings (months of deposits on opening days, amounts that follow weekday and season and sometimes exceed T, card income in proportion, no onward wire); deposit caps set by insurers or cash-in-transit contracts (near-identical amounts just under a fixed cap for months, one branch, a business holder); fixed weekly savings (the same round sum every week, the holder's own money, often an `internal` transfer). A rule that looks only at "amount in band" flags all three.
- **Gap.** The depositor (the person at the counter) cannot be recorded in C1, so the "several depositors" signal of smurf teams cannot be planted (section 3.17).

### 3.4 `rapid_pass_through` (core)

- **Pattern.** Inbound money within a window leaves again within hours or a few days, keeping a small residual; inbound from several unrelated accounts, outbound to few beneficiaries [S1].
- **Roles.** `conduit_account`, `conduit_holder`, `source`, `beneficiary`.
- **Parameters.** 3 to 30 inbound payments (Tide 10 to 20 from up to 30 senders [S20]); dwell 1 to 72 hours (Tide 1 to 24 [S20]); 85 to 99 percent passed on (Tide 85 to 95 [S20]); 1 to 3 beneficiaries; 1 to 8 cycles over 1 to 12 weeks.
- **Variants.** `wire_transit`; `cash_funnel` (cash deposited in one area and withdrawn elsewhere, FinCEN's funnel account in `aml-domain.md` (b) [S3]); `cross_border_out` (beneficiaries are synthetic `cy`, `ae` or `vg` companies); `sawtooth_repeat`.
- **Knobs.** Dwell overlap with benign flows (Tide's benign rapid flows wait 4 to 72 hours [S20]); residual size; cycle count; normal card spending on the conduit account.
- **Look-alikes** [S1]: payment service providers, payroll bureaus, escrow and client accounts, marketplace settlement and treasury sweep accounts. Separating features: the holder's `sector` and the account's `accountType` (for example a client account), long history, many outbound beneficiaries with recurring relationships (a payroll bureau pays the same employees each month), fixed schedules (a sweep every working day to an account in the same ownership group), and business rather than unrelated personal senders. Short dwell plus low residual alone flags them all.

### 3.5 `layering_chain` (core)

- **Pattern.** A time-ordered path of three or more hops through accounts of different legal entities, short dwell times, amounts shrinking slightly or split and merged, intermediate holders with little other activity, often sharing an address, an agent or a director [S1].
- **Roles.** `origin_account`, `origin_holder`, `intermediary_account`, `intermediary_holder`, `terminal_account`, `terminal_holder`.
- **Parameters.** 3 to 8 hops (C2 bounds traversals at 8 [S1]); 1 to 72 hours per hop (Tide 1 to 48 [S20]); 0.5 to 5 percent decay per hop (Tide 1 to 5 [S20]) or, for split and merge, changes of 10 to 20 percent per layer (SAML-D [S12]); split factor 2 to 4 with probability up to 0.5; intermediates share an address, agent or director with probability 0.3 to 0.8 (assumption).
- **Variants.** `linear`; `split_merge` (stack or bipartite shape); `cross_border`; `currency_switch`; `hidden_hop` (one hop at a bank outside the data).
- **Knobs.** Background on intermediates; dwell variance; amount noise; hidden hops.
- **Look-alikes** [S1]: intra-group treasury flows (holders linked by `OWNS` or `CONSOLIDATES`, regular schedules); multi-tier supply chains (amounts grow tier by tier with margins, suppliers have payroll and other customers, invoice references in `purpose`); correspondent banking hops (intermediate holders are banks). "Three hops within days" alone flags supply chains and treasury.

### 3.6 `circular_flow` (core)

- **Pattern.** Funds return to the originating account (Phase 1) or to another account of the same holder (Phase 3) through time-ordered hops with near-equal amounts and a short total duration [S1].
- **Roles.** `origin`, `origin_holder`, `intermediary`, `intermediary_holder`, `return_account`, `controller`.
- **Parameters.** Cycle length 2 to 8 (catalog bounds; detector default 2 to 6) [S1]; fee 0 to 5 percent per hop (Phase 1 `round_trip` about 2 percent [S1]; Tide 1 to 3 percent [S20]); 2 hours to 5 days between hops (Phase 1 1 to 2 days [S1]; Tide 1 to 7 days [S20]); total window 1 to 30 days (detector default 14, maximum 90 [S1]); return ratio 0.70 to 0.99 (detector default minimum 0.8 [S1]; Tide 0.7 to 0.9 [S20]).
- **Variants.** `same_account` (Phase 1 `round_trip`); `same_holder_other_account` (money leaves account A of holder H and returns to account B of H, possibly at another bank or in another currency, so a detector must join through `HOLDS_ACCOUNT`); `related_party_return` (returns to a company H owns or to a relative's account, needing `OWNS` or `FAMILY_OF`; holdout-only, see 6.2); `cross_border`; `dressed_as_trade` (invoice-like `purpose` on every hop).
- **Knobs.** Share outside the detector envelope (window over 14 days, return ratio under 0.8); decoys with one hop out of time order (like Phase 1 fixture case C [S1]); one hop split in two.
- **Look-alikes** [S1]: refunds and reversals (two hops, near-equal amounts, a merchant with an earlier card payment, a refund `purpose`); loan drawdown and repayment (a lender, repayments over months, a return ratio above 1 because of interest); FX hedging legs (a bank counterparty, two currencies); intra-group cash pooling (all accounts in one ownership group, daily sweeps). The cycle shape alone flags all of these.

### 3.7 `fan_in_collection` (core)

- **Pattern.** One account receives from many person-held accounts with no earlier relationship to it or to each other, within a short window, often from recently opened accounts, followed by onward transfers or cash withdrawals; a ring variant is found with weakly connected components or Louvain over recent `PAID` edges [S1].
- **Roles.** `collector_account`, `collector_holder`, `sender_account`, `sender_holder`, `exit_beneficiary`.
- **Parameters.** 5 to 50 senders (AMLGentex template 3 to 15 accounts [S15]; Tide 5 to 12 coordinated senders [S20]); for 30 to 90 percent of senders an account opened 0 to 120 days earlier (assumption, informed by the 20-day indicator in [S3]); 100 to 3,000 per payment (Tide 500 to 3,000 [S20]); window 1 to 14 days; 70 to 98 percent moved on within 1 to 7 days.
- **Variants.** `star`; `ring` (3 to 8 collectors and 15 to 80 senders, each sender paying 1 to 3 collectors, collectors paying each other and 1 or 2 exits, a dense community over 7 to 21 days with few links to the rest); `two_tier` (people pay mules, mules pay the collector; holdout-only, see 6.2); `synchronised` (senders pay within a few hours, after Tide [S20]).
- **Knobs.** Share of new sender accounts; senders' earlier activity; ordinary senders mixed in; window length; partial collections.
- **Look-alikes** [S1]: charities and donation drives, crowdfunding, landlords, clubs, small online sellers and school fee accounts. Separating features: senders with long histories who pay again (monthly rent, termly fees, recurring donors), the holder's sector, and outflows to suppliers or programmes over weeks rather than to one exit within days. For the ring, a savings club in which members pay equal sums every month and each member receives the pot once in turn (reciprocal, periodic, long-lived). In-degree within a window alone flags all of these.

### 3.8 `fan_out_distribution` (core)

- **Pattern.** One account pays many accounts in a short window, with similar or round amounts, to recipients without earlier relationship, followed by cash withdrawals or a second layer [S1].
- **Roles.** `distributor_account`, `distributor_holder`, `recipient_account`, `recipient_holder`, `second_layer_beneficiary`.
- **Parameters.** 5 to 50 recipients (AMLGentex 3 to 15 [S15]); window 1 hour to 3 days; coefficient of variation of amounts 0 to 0.15; round amounts in 0 to 80 percent (same range in benign batches; assumption); recipients withdraw 60 to 100 percent as cash within 1 to 3 days, or forward to 1 to 3 second-layer accounts.
- **Variants.** `cash_out`; `second_layer` (scatter-gather when the second layer converges); `after_fan_in` (gather-scatter).
- **Knobs.** Roundness; share of recipients with an earlier relationship (10 to 40 percent); recipients' account age.
- **Look-alikes** [S1]: payroll runs (monthly, recipients linked by `Employment` to the payer), supplier batches (invoice references, suppliers with their own trade), dividend, benefit and insurance payouts (periodic, recipients with long histories), refunds after a cancelled event (recipients paid the payer earlier). Out-degree plus similar amounts alone flags them all.

### 3.9 `dormant_reactivation` (core)

- **Pattern.** No `PAID` for a long gap (default 180 days), then within days a burst of inbound and outbound volume, often soon after a new `DIRECTOR_OF` or `OWNS` on the holder; a company variant is a newly incorporated or long-dormant company that suddenly moves large sums [S1].
- **Roles.** `dormant_account`, `holder`, `new_controller`, `source`, `beneficiary`.
- **Parameters.** Gap 180 to 900 days (decoys 120 to 179); burst 1 to 21 days; volume 10 to 200 times the pre-gap monthly mean; out over in 0.8 to 1.0; a control change 0 to 30 days before the burst in 30 to 90 percent of cases (assumption); company variant: first large inflow 0 to 90 days after incorporation, or accounts filed as `DORMANT` (`nr.accounts_category`) before the burst [S4].
- **Variants.** `account_reactivation`; `after_control_change`; `shelf_company` (old incorporation date, no activity, a new director, then the burst); `new_company_burst`.
- **Knobs.** Gap close to the threshold; burst size; control change present or absent; activity before the gap.
- **Look-alikes** [S1]: seasonal businesses (the pattern repeats every year, which needs the 24-month window of 2.7), holders returning from abroad (salary and card spending resume, no pass-through), inheritances and property sales (one large inflow from a solicitor's client account, then slow outflows), genuine restarts and acquisitions (payroll and suppliers resume). Gap plus burst alone flags all of these.

### 3.10 `shell_chain` (core)

- **Pattern.** An `OWNS` chain of two or more company layers, often across jurisdictions, ending at a person, a company with no recorded owner, or looping back; nominee directorships or directors with many appointments; chain companies move money without payroll or supplier activity [S1].
- **Roles.** `top_owner`, `layer_company`, `subject_company`, `nominee_director`, `ownership_link`, `directorship_link`.
- **Parameters.** 2 to 6 layers (the sanctions path bound is 6 [S1]); jurisdiction sequences drawn from `gb`, `cy`, `vg`, `ae`; end type person 50 percent, ownerless 30 percent (a PSC statement in `nr.psc_statements` [S4]), loop 20 percent (assumption); nominee probability per company 0.3 to 1.0 (`nr.is_nominee`); share bands as Phase 2 sets them [S4]; money moved through the chain with no payroll, supplier or tax payments.
- **Variants.** `linear`; `loop_back`; `ownerless_top`; `nominee_fronted`; `mixed_with_operating` (one real operating subsidiary in the chain).
- **Knobs.** Share bands near 25 percent; missing ownership data for foreign layers; amount of operating-looking activity.
- **Look-alikes** [S1]: lawful holding structures (operating activity somewhere in the group: payroll, suppliers, PAYE and VAT payments; `CONSOLIDATES` links), special purpose vehicles (one financing pattern), funds with corporate directors, joint ventures (two parents at 50 percent each), start-ups not yet trading (no money movement at all). Depth or an offshore layer alone flags all of these, and 75 percent of real businesses have no employees [S42].

### 3.11 `mass_registration_address` (core)

- **Pattern.** An `Address` with many incoming `HAS_ADDRESS {role: 'registered'}` edges; stronger when the companies there pay each other [S1].
- **Roles.** `address`, `registered_company`, `paying_company`, `has_address_link`.
- **Parameters.** Illicit cluster: 10 to 80 companies at one residential-looking or small-office address, incorporated in bursts (5 to 30 within 14 days), 20 to 60 percent of them paying each other (assumption). Benign hubs: registered agent and corporate service addresses with 50 to 2,000 companies each, at realistic frequency (the catalog requires it [S1]); calibrate the share of companies at the ten most common addresses with Phase 2's counts-only `top10_address_share` from the operator's run [S4] (Inference).
- **Variants.** `residential_flat`; `agent_office_with_payments`; `normalisation_split` (one address written several ways, testing the Phase 2 address keys) [S4].
- **Knobs.** Cluster size relative to benign hubs; share of companies paying each other; incorporation burstiness.
- **Look-alikes** [S1]: registered agents and corporate service firms, serviced offices, law and accounting firms, and clusters created by normalisation errors. Separating features: payments among co-located companies, shared directors, bursts of incorporations. The address in-degree alone flags all of these.

### 3.12 `sanctions_exposure` (core)

- **Pattern.** `OWNS` paths of at most 6 hops from `:Sanctioned` nodes to the subject, with an effective share range as a teaching metric and an OFAC-style flag that passes blocked status down the chain; `CONTROLS` and `DIRECTOR_OF` links create exposure without ownership [S1].
- **Roles.** `sanctioned_party`, `intermediate_owner`, `subject`, `ownership_link`, `control_link`, `director_link`, `counterparty`.
- **Synthetic list entries.** `Person` or `Company` records with topic `sanction` and a `Sanction` record from `Synthetic Authority A`, `B` or `C`, with invented surnames, as Phase 2's benchmark does [S4].
- **Parameters.** Path length 1 to 6; shares per link from the Companies House bands [S4]; 1 to 3 sanctioned owners; aggregate blocked share 0 to 100 percent; control-only links; optional payments from the subject.
- **Variants.** `direct_majority`; `aggregate_50` (two or three blocked owners together at 50 percent or more); `chain_pass_down` (every intermediate at 50 percent or more, so blocked status passes down although the multiplied share is under 50 percent) [S1]; `control_only`; `payments_exposure`.
- **Expected metrics in labels.** Effective share minimum and maximum, the OFAC-style flag and the paths, so the evaluator can check the alert's numbers as well as its hit.
- **Look-alikes** [S1]: name-matching errors (a synthetic namesake with another birth date and nationality), minority stakes (aggregate under 50 percent and no control), delisted parties (`Sanction` `endDate` in the past), diffuse shareholding (many small owners), lawful state-owned counterparties (a `PublicBody` owner without a sanction topic). Any path to a sanctioned name alone flags all of these.

### 3.13 `formation_agent_cluster` (extended)

- **Pattern.** One agent with `REPRESENTS` edges to many companies, or one formation agent's registered address, with incorporation bursts and shared nominee directors or secretaries, plus payments among those companies [S1].
- **Roles.** `agent`, `client_company`, `nominee_director`, `representation_link`.
- **Parameters.** 20 to 300 clients per agent, the same range for benign agents; bursts of 5 to 30 incorporations within 1 to 14 days; a nominee shared by 3 to 20 companies; payments among 20 to 60 percent of the burst (assumptions).
- **Variants.** `burst_with_payments`; `shared_nominee`; `agent_address_only`.
- **Look-alike** [S1]: company formation is lawful and most companies an agent forms are ordinary: same agent, but different directors, their own trade and no payments among them. Agent in-degree alone flags every agent.

### 3.14 `recycled_directors` (extended)

- **Pattern.** A director with many `DIRECTOR_OF` edges, appointments that start and end in bursts, relatives of a controller as directors (`FAMILY_OF`), and payments between companies that share the director [S1].
- **Roles.** `director`, `company`, `controller`, `relative`, `directorship_link`, `family_link`.
- **Parameters.** 10 to 80 appointments; bursts of 5 to 20 appointments within 30 days and resignations in bursts 3 to 12 months later; a `FAMILY_OF` link to the controller in 30 to 70 percent; payments among 20 to 60 percent of the director's companies (assumptions).
- **Variants.** `burst_appointments`; `family_directors`; `paying_network`.
- **Look-alikes** [S1]: professional directors in fund jurisdictions (stable tenure, unrelated companies that do not pay each other), corporate secretaries, directors across one corporate group (the companies share ownership, so payments are intra-group). Appointment count alone flags them all.

### 3.15 `pep_exposure` (extended)

- **Pattern.** Paths of at most 4 hops from a `:PEP` or `:RCA` person through `FAMILY_OF`, `ASSOCIATE_OF`, `OWNS`, `CONTROLS` or `DIRECTOR_OF` to the subject; PEP measures are preventive and being a PEP is not wrongdoing [S1].
- **Roles.** `pep`, `relative_or_associate`, `intermediate_entity`, `subject`, `family_link`, `ownership_link`, `director_link`.
- **Parameters.** 1 to 4 hops; a mix of link types; PEP status current or ended within 12 months (Phase 2's `pep_former_months` default) [S4]; optional payments from the subject to a relative's company (assumption).
- **Variants.** `family_ownership`; `associate_director`; `chain_via_company`; `payments_to_relative_company`.
- **Look-alikes** [S1]: homonyms (another birth date and nationality), people long out of office (`Occupancy` end date more than 12 months back), ordinary family relationships (no ownership, control or flows). Any path to a PEP-named person alone flags all of these. Wording stays structural (G5) [S1].

### 3.16 `cash_commingling` (extended)

- **Pattern.** A company account whose `cash_deposit` volume is far above peers in the same `sector`, deposited on days unrelated to trading, with outflows to owners or related parties rather than to suppliers and payroll; the generator documents its calibration [S1].
- **Roles.** `cash_business_account`, `cash_business`, `owner`, `related_party`, `branch_ledger`.
- **Parameters.** Cash 1.5 to 5 times the sector median for the size band; 10 to 50 percent of deposits on closed days; 30 to 80 percent of outflows to owners or related parties; 1 to 6 months (all assumptions). Anchors: cash is 8 percent of UK payments [S29] and 19.9 percent of retail transactions [S50]; the mean Post Office deposit is about £424 [S49].
- **Variants.** `steady_excess`; `sudden_increase`; `owner_network` (2 to 6 businesses of one owner with the same anomaly, the Egmont chapter quoted in `aml-domain.md` (l) [S3]).
- **Look-alikes** [S1]: busy or growing cash businesses (supplier and payroll outflows grow in proportion), seasonal peaks (repeat every year), a new branch (a new address and new staff). Cash volume alone flags them all.

### 3.17 `trade_based_ml` and contract gaps

- `trade_based_ml` is `explainer_only`: no scenario, because C2 has no invoices or shipments [S1].
- **Gap 1, the depositor.** A cash deposit's payer is the branch's `cash_ledger` account, and C2 `PAID` has no payer-entity property [S1]. So smurf teams (several depositors for one account) cannot be expressed. Options: accept it (patterns use branches, accounts, amounts and times), or a minor C1 and C2 change adding an optional depositor reference.
- **Gap 2, the scheme.** `nr.channel` has five values (`wire`, `card`, `cash_deposit`, `cash_withdrawal`, `internal`) [S1]. Faster Payments, Bacs, CHAPS, Direct Debit and standing order cannot be told apart, although timing can still follow their calendars. Option: a minor change adding an optional `nr.scheme`.
- **Not gaps.** The separating features above exist in FtM 4.11 and C2: `BankAccount.accountType`, `openingDate`, `closingDate`; `Company.sector`, `status`; `Payment.purpose`; `Employment`, `Representation`, `Occupancy.endDate`, `Sanction.endDate` (checked with `followthemoney.model` here) [S59][S1]. `purpose` texts must appear in illicit and benign payments alike, or they leak the label (Inference).

## 4. Label files

### 4.1 What the existing datasets use

| Dataset | Transaction label | Instance id | Pattern type | Participants and roles | Account or node label |
|---|---|---|---|---|---|
| AMLSim | `is_sar`, `alert_id` in `transactions.csv` [S2] | `alert_id` | `alert_type` in alert files | Alert members, no roles [S2] | `sar_accounts.csv` [S2] |
| AMLworld | `Is Laundering` [S11] | none in `*_Trans.csv`; blocks in `*_Patterns.txt` [S10] | block header [S10] | none | none |
| SAML-D | "Is Suspicious" [S12] | none | "Type" [S12] | none | none |
| AMLGentex | `isSAR` [S15] | `patternID` [S15] | `modelType` [S15] | none | derived `is_sar` [S15] |
| Tide | `is_fraudulent` [S20] | none | none | none | `is_fraudulent` on nodes [S20] |
| AMLNet v2.0 | `isMoneyLaundering`, `isFraud` [S23] | none | `laundering_typology` [S23] | none | none |
| Elliptic2 (real) | none | subgraph | subgraph label [S26] | subgraph members | none |
| NeonRadar Phase 1 | `labels/transactions.csv`: `tx_id, scenario_id, typology, step, role, is_illicit` [S1] | `scenario_id` | `typology`, `variant` | a `participants` column in `labels/scenarios.csv` [S1] | none |

None of them records roles for entities and accounts, and none labels relationship-level participants (ownership, directorships, addresses), which six NeonRadar typologies need.

### 4.2 Proposal: labels v2

Rules carried over: labels never appear in records (C1 R9) [S1] and are never loaded into Neo4j; every CSV label file starts with `# synthetic: true` (M1.8e) [S1], and the JSON files carry `"synthetic": true` in the manifest; same seed, same bytes. New: a second comment line `# label_schema: 2.0.0` in each CSV file; Phase 1 columns stay first and in order, and new columns are appended, so a reader that selects columns by header name keeps working.

Files in `labels/`:

1. `scenarios.csv`, one row per scenario, illicit or look-alike:
   `scenario_id, typology, variant, is_lookalike, start_ts, end_ts, participants, difficulty, split, n_transactions, n_accounts, n_entities, n_relationships`.
   `variant` holds the illicit variant or the look-alike kind (for example `loan_drawdown_repayment`). `participants` is kept for Phase 1 readers but deprecated; `participants.csv` is authoritative. `split` is `dev`, `test` or `holdout`. Timestamps use the C1 R5 form [S1].
2. `participants.csv`, one row per scenario participant:
   `scenario_id, object_kind, object_id, role, is_core`.
   `object_kind` is `entity` (any `LegalEntity`), `account`, `address`, `relationship` or `sanction`. `object_id` is the C2 id: the record id for nodes, the FtM interval entity id for `OWNS`, `CONTROLS`, `DIRECTOR_OF`, `HOLDS_ACCOUNT`, `REPRESENTS`, `FAMILY_OF` and `ASSOCIATE_OF`, `<entity id>|addr|<address id>` for `HAS_ADDRESS` and `<entity id>|sanction|<sanction id>` for `SUBJECT_OF` [S1]. `is_core` marks what an alert must cover to count as a hit; peripheral participants (for example an exit account that also serves other flows) are `false`.
3. `transactions.csv`, one row per scenario payment and scenario (a payment may belong to two scenarios, for example a fan-in followed by a fan-out):
   `tx_id, scenario_id, typology, step, role, is_illicit, variant, is_lookalike, is_core`.
   `tx_id` is the `Payment` record id, which is also the C2 `PAID` id [S1]. `step` is the order by time within the scenario; `role` is the payment's role (`deposit`, `hop`, `return`, `collection`, `distribution`, `cash_out`, `onward`). Normal activity of illicit accounts (camouflage) gets no row, so it counts as negative at transaction level while the account counts as positive at account level.
4. `scenario_params.jsonl`, one JSON object per scenario: the drawn parameters, the expected metrics (for example `cycle_length` and `return_ratio` for `circular_flow`, effective share bounds for `sanctions_exposure`), the stream key, and the generator component and version.
5. `manifest.json`: `label_schema`, `synthetic: true`, the dataset seed, the SHA-256 of each record file the labels belong to, counts by typology, variant and look-alike kind, illicit ratios at transaction, account and entity level, the split definitions and the generator version.

Example lines (synthetic ids):

```text
# synthetic: true
# label_schema: 2.0.0
scenario_id,typology,variant,is_lookalike,start_ts,end_ts,participants,difficulty,split,n_transactions,n_accounts,n_entities,n_relationships
scn-000041,circular_flow,same_holder_other_account,false,2026-03-02T09:00:00,2026-03-08T16:40:00,,medium,test,4,4,4,0
scn-000042,circular_flow,loan_drawdown_repayment,true,2026-01-05T10:00:00,2026-07-06T10:00:00,,medium,test,7,2,2,0
```

```text
# synthetic: true
# label_schema: 2.0.0
scenario_id,object_kind,object_id,role,is_core
scn-000041,account,syn-acct-0000007,origin,true
scn-000041,entity,syn-co-000003,origin_holder,true
scn-000041,account,syn-acct-0000031,return_account,true
scn-000107,relationship,syn-ownership-3f2a9c0d1e2b3a4c5d6e,ownership_link,true
scn-000107,relationship,syn-co-000101|addr|syn-addr-000007,registered_address,false
```

```json
{"scenario_id": "scn-000041", "params": {"cycle_length": 4, "fee_per_hop": 0.02, "hop_gap_hours": [26, 31, 40]}, "expected_metrics": {"cycle_length": 4, "return_ratio": 0.94, "duration_days": 7}, "stream_key": ["scenario", "circular_flow", "scn-000041"], "generator": {"component": "scenarios.circular_flow", "version": "0.3.0"}}
```

### 4.3 Matching alerts to scenarios

An alert's objects are its `evidence.edge_ids`, its `evidence.node_ids` and its `subjects` (C4) [S1]. If entity resolution has merged records, map canonical `nr-` ids back to record ids through the resolution run first (Phase 2 [S4]). A scenario is hit when the alert has the scenario's typology and covers at least half of its core objects; purity (the share of the alert's objects that belong to the scenario) is reported and must be at least 0.25. Both thresholds are fixed in the evaluator's configuration before any run.

```python
from dataclasses import dataclass


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    typology: str
    is_lookalike: bool
    core: frozenset[str]     # C2 ids of core participants and core payments
    members: frozenset[str]  # every participant and payment id of the scenario


def alert_objects(alert: dict) -> frozenset[str]:
    evidence = alert["evidence"]
    subjects = {s["entity_id"] for s in alert["subjects"]}
    return frozenset(evidence["edge_ids"]) | frozenset(evidence["node_ids"]) | frozenset(subjects)


def hits(alert: dict, scenarios: list[Scenario], min_coverage: float = 0.5, min_purity: float = 0.25) -> list[str]:
    objects = alert_objects(alert)
    found = []
    for s in scenarios:
        if s.typology != alert["typology"] or not s.core or not objects:
            continue
        coverage = len(objects & s.core) / len(s.core)
        purity = len(objects & s.members) / len(objects)
        if coverage >= min_coverage and purity >= min_purity:
            found.append(s.scenario_id)
    return sorted(found)
```

### 4.4 Metrics to report

- **Scenario level** (the headline): recall = illicit scenarios hit by at least one alert / illicit scenarios; precision = alerts that hit at least one illicit scenario / alerts; look-alike hit rate = look-alike scenarios hit / look-alike scenarios; background alerts = alerts that hit no scenario at all.
- **Transaction level**: flagged payments are the payment ids in the alerts of a typology; positives are the core payments of its illicit scenarios.
- **Account level**: evidence nodes that are accounts, against core accounts.
- **Entity level**: subjects plus holders of evidence accounts (the C4 definition) [S1], against core entities.
- **Breakdowns**: per typology, variant, difficulty, split, and in-envelope versus out-of-envelope parameters (6.2); cross-typology hits as a confusion table; precision at K by `pattern_strength`, as AMLGentex computes precision at K [S15].
- **Uncertainty**: Wilson 95 percent intervals, as Phase 2 uses for precision [S4]. With p the observed rate over n cases and z = 1.96: centre (p + z^2/(2n)) / (1 + z^2/n), half-width z sqrt(p(1 - p)/n + z^2/(4n^2)) / (1 + z^2/n).
- **Imbalance**: precision and recall (and PR curves), never accuracy or ROC alone [S66].

## 5. Determinism and speed in Python 3.14

### 5.1 Rules

1. One root seed per dataset. Every component gets its own stream from `SeedSequence(root, spawn_key=(key64("background"), key64("payments"), ...))`, where `key64` is a 64-bit BLAKE2b digest of the name, never Python's salted `hash()`. Named keys mean that adding a component does not shift the others, which positional `spawn(n)` would (Inference). NumPy's parallel guide calls `root_seed + worker_id` "UNSAFE" and recommends spawning or mixing ids into the seed [S58]; large `spawn_key` integers are accepted (tested) [S59].
2. Use an explicit `PCG64`, not `default_rng`, because NumPy may change `default_rng`'s BitGenerator; pin numpy to a minor version, because stream changes for new features may come in X.Y releases; keep draw sizes fixed, because "Calling rng.random() 5 times is not guaranteed to give the same numbers as rng.random(5)" [S57].
3. Per-day event streams (`stream(seed, "background", "payments", "2026-03-14")`) bound memory to one day and allow days to be generated in parallel and concatenated in date order.
4. Per-entity streams keyed by record id only where stability matters (real entities in synthetic-join mode): they cost about 12 microseconds each (measured) [S59].
5. Sorted iteration everywhere: entities by id, payments by time with an index tie-break (`np.lexsort`). Never iterate a set: set order changed from run to run here, because string hashing is randomised [S59].
6. No floats in output: integer pence formatted as `f"{p // 100}.{p % 100:02d}"`, integer seconds formatted by `np.datetime_as_string`.
7. Time zones through `zoneinfo` with a pinned `tzdata` (2026.5 on PyPI) [S60], or the committed clock-change table of 2.6.
8. Record Python, numpy, orjson, Faker, followthemoney and tzdata versions in the manifest; only `created_at` may differ between runs (M1.8e) [S1].
9. Emit keys in the order FtM 4.11 `to_dict()` produces (`id`, `schema`, `nr`, `properties`, `referents`, `datasets`); then a validator round trip reproduces each line exactly (tested on 62,500 lines) [S59].
10. Write in batches of about 1,000 lines (5.3).
11. CI: generate twice and compare SHA-256 (M1.8e already does this) [S1]; run the two generations in separate processes so string-hash order differs between them.

### 5.2 Measurements (18 October 2026, this container)

Environment: Python 3.14.6, numpy 2.5.4, orjson 3.13.0, followthemoney 4.11.0, Faker 40.43.0; 2 vCPUs (Intel Xeon at 2.1 GHz), 7 GiB RAM, Linux 6.18 [S59][S60]. Records are C1-shaped (`syn-` ids, `nr_synthetic`, `nr` block, R7 fields). Times include generation, serialisation and writing; hashing is separate.

| Run | Records | Wall time | File size | Peak RSS | SHA-256 (first 16 hex) |
|---|---|---|---|---|---|
| Payments, day by day, batches of 1,000 (5 runs) | 2,000,000 | 7.7 to 8.5 s | 785,319,260 bytes (393 per record) | 68 MiB | `439d1fcc8dc4255d` (all runs) |
| Payments, one set of global arrays, batches of 1,000 | 2,000,000 | 7.0 s (1.5 s drawing, 5.5 s building and writing) | 785,314,754 bytes | 597 MiB | `682ab85e4939b5d7` |
| Payments, global arrays, batches of 100,000 (3 runs) | 2,000,000 | 11.2 to 11.8 s | 785,314,754 bytes | 958 MiB | `682ab85e4939b5d7` |
| Payments, day by day, another seed (20261027), one batch per day | 2,000,000 | 8.3 s | not recorded | 100 MiB | `16c2bce4b8642fb2` |
| Entities, batches of 1,000 (3 runs) | 500,000 (40,000 Address, 60,000 Company, 120,000 Person, 140,000 BankAccount, 140,000 Ownership) | 1.5 to 1.6 s | 140,528,622 bytes (281 per record) | 80 MiB | `1c31b704d8e37be7` (all runs) |
| Entities, batches of 100,000 (earlier version of the script with other name tokens, same shape; 3 runs) | 500,000 | 1.9 to 2.4 s | 140,307,005 bytes | 507 MiB | `7e549d9e69300db4` (also with batches of 1,000 and 10,000) |

Full hashes: day-by-day payments `439d1fcc8dc4255d918fba75748229f92def51853df53f7f9b1d778d6056ed20`; global payments `682ab85e4939b5d727f4c7ef2cdaa38e1c939fbf8f58fbac9f5eee6a8c1abe78`; entities `1c31b704d8e37be7cc5530d0ec9d9c7056609a12c0bda2f2e6e6212485e10dc9` [S59]. The batch size never changed the bytes. SHA-256 of a 785 MB file took 0.55 to 0.65 s.

Micro-benchmarks [S59]:

| Operation | Rate |
|---|---|
| Build a Payment dict and `orjson.dumps` | 270,402 records/s |
| Same with `json.dumps` (identical bytes) | 175,363 records/s |
| Same with a bytes `%` template (identical bytes) | 2,070,442 records/s |
| FtM 4.11 `ValueEntity.from_dict` plus `to_dict` | 191,270 records/s |
| FtM 4.11 `schema.validate` | 167,224 records/s |
| One Generator per entity: `SeedSequence` with `spawn_key` plus `PCG64` | 12.3 microseconds each |
| One Generator per entity: `Philox(key=...)` | 9.4 microseconds each |
| `SeedSequence.spawn(n)` positional children | 3.9 microseconds each |
| 500,000 per-entity Generators, one draw each | 7.4 s |
| Faker 40.43 names, `en_GB` / `ar_SA` / `ru_RU` | 31,790 / 141,518 / 112,785 names/s |

### 5.3 Findings

- 2 million payments plus 500,000 entities take about 10 s and about 925 MB on disk on this 2 vCPU box, so generation is not the bottleneck; FtM validation of every record would add about 12 s per 2 million (167,000 per second) [S59]. Loading 2 million `PAID` relationships into Neo4j was not measured (Neo4j cannot run here): UNVERIFIED.
- Each orjson 3.13.0 output object occupied about 4.2 KB in tracemalloc whatever its length (a 309-byte output traced at 4,209 bytes; 100,000 outputs held in a list took 390.7 MiB), although `sys.getsizeof` reports 346 bytes [S59]. Batches of about 1,000 lines cut peak memory from 507 to 80 MiB for entities and from 958 to 597 MiB for global-array payments, and were also faster [S59].
- Global numpy arrays for 2 million payments need about 600 MiB; day-by-day generation needs 68 MiB [S59].
- A bytes template is 7.7 times faster than dict plus orjson and gives the same bytes, but it is safe only for records without free text (payments carry ids, numbers and fixed words only). Keep orjson unless speed becomes a problem (Inference).
- FtM 4.11 `ValueEntity.from_dict(d)` removes `datasets` and `referents` from `d` itself; validators must pass a copy [S59].
- orjson 3.13.0's licence expression is `MPL-2.0 AND (Apache-2.0 OR MIT)` (file-level copyleft, compatible with use as a dependency; Phase 2 already pins `orjson==3.13.*`) [S60][S4].
- AMLGentex's `RandomState(seed + id)` would make two seeds share streams; NeonRadar's named keys avoid it [S15][S58].

### 5.4 The code that was timed

Run as `python -I synth_bench.py payments-daily --n 2000000 --seed 20261026 --chunk 1000 --out <file>`, `python -I synth_bench.py payments --n 2000000 --chunk 1000 --out <file>`, `python -I synth_bench.py entities --n 500000 --chunk 1000 --out <file>` and `python -I synth_bench.py streams --n 500000` in a uv virtual environment (`uv venv --python 3.14`; `uv pip install numpy orjson psutil followthemoney==4.11.0 faker==40.43.0`). The amount, channel, currency and hour parameters in it are placeholders for timing, not the calibrated values of section 2.

```python
"""Timing probe for NeonRadar Phase 3 research: deterministic synthetic records as
FollowTheMoney-style JSON lines (C1 shape), written with orjson.

Usage:
  python -I synth_bench.py payments --n 2000000 --seed 20261026 --out /path/payments.ftm.jsonl
  python -I synth_bench.py entities --n 500000 --seed 20261026 --out /path/entities.ftm.jsonl
  python -I synth_bench.py streams --n 500000 --seed 20261026

Every random draw comes from a numpy Generator whose SeedSequence is keyed by a
component name (and, for per-entity streams, by the entity id), so adding a
component never shifts the streams of the others. Records are produced in sorted
order (entities by id, payments by timestamp then draw index), amounts are integer
pence formatted as decimal strings, timestamps are integer seconds formatted by numpy,
so no float formatting or hash-seed-dependent ordering reaches the output.
"""

import argparse
import hashlib
import os
import resource
import sys
import time

import numpy as np
import orjson

NR_ACT = {"v": "1.0", "synthetic": True, "synthetic_kind": "activity"}
NR_REG = {"v": "1.0", "synthetic": True, "synthetic_kind": "registry"}
DS = ["nr_synthetic"]
APPEND_NL = orjson.OPT_APPEND_NEWLINE


def key64(name: str) -> int:
    """Stable 64-bit key for a component or entity name (not Python's salted hash())."""
    return int.from_bytes(hashlib.blake2b(name.encode("utf-8"), digest_size=8).digest(), "little")


def stream(root_seed: int, *names: str) -> np.random.Generator:
    """Independent Generator for a named component, e.g. stream(seed, 'background', 'card')."""
    ss = np.random.SeedSequence(root_seed, spawn_key=tuple(key64(n) for n in names))
    return np.random.Generator(np.random.PCG64(ss))


def peak_rss_mib() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


# ---------------------------------------------------------------- payments

CHANNELS = np.array(["card", "wire", "cash_deposit", "cash_withdrawal", "internal"])
CHANNEL_P = np.array([0.62, 0.30, 0.03, 0.03, 0.02])
# log-normal parameters per channel for amounts in GBP (modelling assumptions)
LN_MU = np.array([3.4, 6.2, 5.6, 4.6, 6.5])
LN_SIGMA = np.array([1.0, 1.6, 1.2, 0.8, 1.4])
CURRENCIES = np.array(["GBP", "EUR", "USD"])
CURRENCY_P = np.array([0.97, 0.02, 0.01])
# hour-of-day weights in UTC (assumption: business-hour peak, quiet nights)
HOUR_W = np.array([1, 1, 1, 1, 1, 2, 4, 7, 10, 12, 12, 12, 12, 12, 12, 11, 10, 9, 8, 7, 6, 4, 3, 2], dtype=float)


def gen_payments(n: int, seed: int, out: str, n_accounts: int = 140_000, chunk: int = 100_000) -> dict:
    t0 = time.perf_counter()
    # accounts and their holders: account i is held by entity holder[i]
    rng_acct = stream(seed, "accounts")
    holder_is_co = rng_acct.random(n_accounts) < 0.30
    holder_num = rng_acct.integers(0, 120_000, n_accounts)
    holder_ids = [
        (f"syn-co-{h % 60_000:06d}" if is_co else f"syn-p-{h:06d}")
        for is_co, h in zip(holder_is_co.tolist(), holder_num.tolist())
    ]
    acct_ids = [f"syn-acct-{i:07d}" for i in range(n_accounts)]
    activity = rng_acct.lognormal(0.0, 1.0, n_accounts)  # heavy-tailed activity weights
    p_act = activity / activity.sum()

    rng = stream(seed, "background", "payments")
    payer = rng.choice(n_accounts, size=n, p=p_act)
    bene = rng.choice(n_accounts, size=n, p=p_act)
    clash = payer == bene
    bene[clash] = (bene[clash] + 1) % n_accounts
    ch = rng.choice(len(CHANNELS), size=n, p=CHANNEL_P)
    pence = np.rint(rng.lognormal(LN_MU[ch], LN_SIGMA[ch]) * 100.0).astype(np.int64)
    np.clip(pence, 1, 99_999_999_99, out=pence)
    cur = rng.choice(len(CURRENCIES), size=n, p=CURRENCY_P)
    start = np.datetime64("2026-01-01T00:00:00", "s").astype(np.int64)
    day = rng.integers(0, 273, n)  # 1 January to 30 September 2026
    hour = rng.choice(24, size=n, p=HOUR_W / HOUR_W.sum())
    sec = rng.integers(0, 3600, n)
    ts = start + day * 86400 + hour * 3600 + sec
    order = np.lexsort((np.arange(n), ts))  # sort by time, ties by draw index: deterministic
    payer, bene, ch, pence, cur, ts = payer[order], bene[order], ch[order], pence[order], cur[order], ts[order]
    ts_str = np.datetime_as_string(ts.astype("datetime64[s]"), unit="s")
    t_draw = time.perf_counter() - t0

    ch_names = CHANNELS.tolist()
    cur_names = CURRENCIES.tolist()
    nr_by_channel = [dict(NR_ACT, channel=c) for c in ch_names]
    t1 = time.perf_counter()
    with open(out, "wb") as f:
        for lo in range(0, n, chunk):
            hi = min(n, lo + chunk)
            buf = []
            for i, a, b, c, p, k, d in zip(
                range(lo, hi),
                payer[lo:hi].tolist(), bene[lo:hi].tolist(), ch[lo:hi].tolist(),
                pence[lo:hi].tolist(), cur[lo:hi].tolist(), ts_str[lo:hi].tolist(),
            ):
                rec = {
                    "id": f"syn-payment-{i + 1:010d}",
                    "schema": "Payment",
                    "nr": nr_by_channel[c],
                    "properties": {
                        "payer": [holder_ids[a]],
                        "beneficiary": [holder_ids[b]],
                        "payerAccount": [acct_ids[a]],
                        "beneficiaryAccount": [acct_ids[b]],
                        "amount": [f"{p // 100}.{p % 100:02d}"],
                        "currency": [cur_names[k]],
                        "date": [d],
                    },
                    "referents": [],
                    "datasets": DS,
                }
                buf.append(orjson.dumps(rec, option=APPEND_NL))
            f.write(b"".join(buf))
    t_write = time.perf_counter() - t1
    return {"records": n, "draw_s": t_draw, "build_serialise_write_s": t_write,
            "total_s": time.perf_counter() - t0}


# ---------------------------------------------------------------- entities

WORDS_A = ["Falcon", "Cedar", "Quarry", "Harbour", "Willow", "Granite", "Meadow", "Copper", "Lantern", "Orchard",
           "Summit", "Beacon", "Thistle", "Juniper", "Marlow", "Kestrel", "Bramble", "Osprey", "Hollin", "Tamar"]
WORDS_B = ["Ridge", "Gate", "Lane", "Works", "Field", "Bridge", "Vale", "Point", "Yard", "Cross"]
WORDS_C = ["Trading", "Holdings", "Logistics", "Instruments", "Foods", "Consulting", "Textiles", "Services", "Supplies", "Media"]
FORMS = ["Ltd", "Ltd", "Ltd", "LLP", "Limited"]
# invented tokens only (no real given names or surnames), in the spirit of PHASE-2.md M2.9
FIRST = ["Avelin", "Borrik", "Calvra", "Dresko", "Elvanna", "Fennor", "Galvi", "Hesken", "Ilvara", "Jorvik",
         "Kavren", "Lussa", "Morvane", "Nelvi", "Orsken", "Pellira", "Quarne", "Rusvel", "Selvora", "Tavrin"]
LAST = ["Kestrane", "Braske", "Vorlund", "Quillan", "Darnovi", "Elsktra", "Fornavel", "Gravick", "Hollenvar", "Iskarn",
        "Jessavik", "Korrane", "Lusterin", "Morvask", "Nerrowe", "Ostravin", "Pellvane", "Quorsk", "Ravellin", "Strovane"]


def gen_entities(n: int, seed: int, out: str, chunk: int = 100_000) -> dict:
    # mix: 12% Company, 24% Person, 8% Address, 28% BankAccount, 28% Ownership (account holder)
    n_co, n_p, n_addr = int(n * 0.12), int(n * 0.24), int(n * 0.08)
    n_acct = (n - n_co - n_p - n_addr) // 2
    n_own = n - n_co - n_p - n_addr - n_acct
    t0 = time.perf_counter()
    rc, rp, ra, rb = (stream(seed, "registry", k) for k in ("company", "person", "address", "account"))
    co_w = rc.integers(0, [len(WORDS_A), len(WORDS_B), len(WORDS_C), len(FORMS)], size=(n_co, 4))
    co_inc = (np.datetime64("1995-01-01", "D") + rc.integers(0, 11_600, n_co)).astype(str)
    co_addr = rc.integers(0, n_addr, n_co)
    p_w = rp.integers(0, [len(FIRST), len(LAST)], size=(n_p, 2))
    p_birth = (np.datetime64("1950-01", "M") + rp.integers(0, 600, n_p)).astype(str)
    a_num = ra.integers(1, 400, n_addr)
    b_open = (np.datetime64("2005-01-01", "D") + rb.integers(0, 7_900, n_acct)).astype(str)
    b_holder_co = rb.random(n_acct) < 0.30
    b_holder = rb.integers(0, n_p, n_acct)
    t_draw = time.perf_counter() - t0

    def records():
        for i in range(n_addr):
            yield {"id": f"syn-addr-{i:06d}", "schema": "Address", "nr": NR_REG,
                   "properties": {"full": [f"Unit {i % 40 + 1}, {a_num[i]} Example Street, Synthton, QQ{i % 90 + 1} {i % 9}AB"],
                                  "city": ["Synthton"], "country": ["gb"]},
                   "referents": [], "datasets": DS}
        for i in range(n_co):
            w = co_w[i]
            addr = f"syn-addr-{co_addr[i]:06d}"
            yield {"id": f"syn-co-{i:06d}", "schema": "Company",
                   "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "registry", "address_roles": {addr: "registered"}},
                   "properties": {"name": [f"{WORDS_A[w[0]]} {WORDS_B[w[1]]} {WORDS_C[w[2]]} {FORMS[w[3]]}"],
                                  "jurisdiction": ["gb"], "registrationNumber": [f"SY{i:06d}"],
                                  "incorporationDate": [co_inc[i]], "addressEntity": [addr]},
                   "referents": [], "datasets": DS}
        for i in range(n_p):
            w = p_w[i]
            yield {"id": f"syn-p-{i:06d}", "schema": "Person", "nr": NR_REG,
                   "properties": {"name": [f"{FIRST[w[0]]} {LAST[w[1]]}"], "birthDate": [p_birth[i]], "nationality": ["gb"]},
                   "referents": [], "datasets": DS}
        for i in range(n_acct):
            yield {"id": f"syn-acct-{i:07d}", "schema": "BankAccount",
                   "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "activity", "account_kind": "customer"},
                   "properties": {"accountNumber": [f"NRSYN{i:010d}"], "bankName": ["Synthetic Bank One"],
                                  "currency": ["GBP"], "openingDate": [b_open[i]]},
                   "referents": [], "datasets": DS}
        for i in range(n_own):
            owner = f"syn-co-{b_holder[i] % n_co:06d}" if b_holder_co[i] else f"syn-p-{b_holder[i]:06d}"
            yield {"id": f"syn-ownership-acct-{i:07d}", "schema": "Ownership", "nr": NR_ACT,
                   "properties": {"owner": [owner], "asset": [f"syn-acct-{i:07d}"], "role": ["account holder"]},
                   "referents": [], "datasets": DS}

    t1 = time.perf_counter()
    count = 0
    with open(out, "wb") as f:
        buf = []
        for rec in records():
            buf.append(orjson.dumps(rec, option=APPEND_NL))
            if len(buf) == chunk:
                f.write(b"".join(buf))
                count += len(buf)
                buf = []
        if buf:
            f.write(b"".join(buf))
            count += len(buf)
    t_write = time.perf_counter() - t1
    return {"records": count, "mix": {"Address": n_addr, "Company": n_co, "Person": n_p, "BankAccount": n_acct,
                                      "Ownership": n_own},
            "draw_s": t_draw, "build_serialise_write_s": t_write, "total_s": time.perf_counter() - t0}


def bench_streams(n: int, seed: int) -> dict:
    """Cost of one Generator per entity (keyed by entity id) versus one per component."""
    t0 = time.perf_counter()
    acc = 0.0
    for i in range(n):
        g = stream(seed, "background", f"gbch-co-{i:08d}")
        acc += g.random()
    per_entity = time.perf_counter() - t0
    t1 = time.perf_counter()
    g = stream(seed, "background")
    acc2 = g.random(n).sum()
    per_component = time.perf_counter() - t1
    return {"entities": n, "per_entity_generators_s": per_entity, "one_component_generator_s": per_component,
            "checksum": round(float(acc + acc2), 6)}


def gen_payments_daily(n: int, seed: int, out: str, n_accounts: int = 140_000, chunk: int = 1_000) -> dict:
    """Same record shape, generated day by day from per-day streams, so memory is bounded by
    one day's payments and days could be produced in parallel and concatenated in date order."""
    t0 = time.perf_counter()
    rng_acct = stream(seed, "accounts")
    holder_is_co = rng_acct.random(n_accounts) < 0.30
    holder_num = rng_acct.integers(0, 120_000, n_accounts)
    holder_ids = [
        (f"syn-co-{h % 60_000:06d}" if is_co else f"syn-p-{h:06d}")
        for is_co, h in zip(holder_is_co.tolist(), holder_num.tolist())
    ]
    acct_ids = [f"syn-acct-{i:07d}" for i in range(n_accounts)]
    activity = rng_acct.lognormal(0.0, 1.0, n_accounts)
    cdf = np.cumsum(activity / activity.sum())
    days = np.arange(np.datetime64("2026-01-01"), np.datetime64("2026-10-01"))
    weekday = (days.astype(np.int64) + 3) % 7  # 0 = Monday
    w = np.where(weekday < 5, 1.0, 0.55)  # assumption: weekend volume 55% of a weekday
    per_day = np.floor(n * w / w.sum()).astype(np.int64)
    per_day[: n - per_day.sum()] += 1  # distribute the remainder to the first days
    ch_names = CHANNELS.tolist()
    cur_names = CURRENCIES.tolist()
    nr_by_channel = [dict(NR_ACT, channel=c) for c in ch_names]
    hour_p = HOUR_W / HOUR_W.sum()
    seq = 0
    with open(out, "wb") as f:
        for day, k in zip(days.astype(str).tolist(), per_day.tolist()):
            rng = stream(seed, "background", "payments", day)
            payer = np.searchsorted(cdf, rng.random(k), side="right")
            bene = np.searchsorted(cdf, rng.random(k), side="right")
            np.minimum(payer, n_accounts - 1, out=payer)
            np.minimum(bene, n_accounts - 1, out=bene)
            clash = payer == bene
            bene[clash] = (bene[clash] + 1) % n_accounts
            ch = rng.choice(len(CHANNELS), size=k, p=CHANNEL_P)
            pence = np.rint(rng.lognormal(LN_MU[ch], LN_SIGMA[ch]) * 100.0).astype(np.int64)
            np.clip(pence, 1, 99_999_999_99, out=pence)
            cur = rng.choice(len(CURRENCIES), size=k, p=CURRENCY_P)
            secs = rng.choice(24, size=k, p=hour_p) * 3600 + rng.integers(0, 3600, k)
            order = np.lexsort((np.arange(k), secs))
            ts = (np.datetime64(day, "s") + secs[order]).astype(str).tolist()
            buf = []
            for a, b, c, p, cu, d in zip(payer[order].tolist(), bene[order].tolist(), ch[order].tolist(),
                                         pence[order].tolist(), cur[order].tolist(), ts):
                seq += 1
                rec = {
                    "id": f"syn-payment-{seq:010d}",
                    "schema": "Payment",
                    "nr": nr_by_channel[c],
                    "properties": {
                        "payer": [holder_ids[a]],
                        "beneficiary": [holder_ids[b]],
                        "payerAccount": [acct_ids[a]],
                        "beneficiaryAccount": [acct_ids[b]],
                        "amount": [f"{p // 100}.{p % 100:02d}"],
                        "currency": [cur_names[cu]],
                        "date": [d],
                    },
                    "referents": [],
                    "datasets": DS,
                }
                buf.append(orjson.dumps(rec, option=APPEND_NL))
                if len(buf) == chunk:
                    f.write(b"".join(buf))
                    buf = []
            if buf:
                f.write(b"".join(buf))
    return {"records": seq, "days": len(days), "max_per_day": int(per_day.max()),
            "total_s": time.perf_counter() - t0}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("what", choices=["payments", "payments-daily", "entities", "streams"])
    ap.add_argument("--n", type=int, required=True)
    ap.add_argument("--seed", type=int, default=20261026)
    ap.add_argument("--out")
    ap.add_argument("--chunk", type=int, default=1_000, help="records per write batch")
    a = ap.parse_args()
    if a.what == "payments":
        res = gen_payments(a.n, a.seed, a.out, chunk=a.chunk)
    elif a.what == "payments-daily":
        res = gen_payments_daily(a.n, a.seed, a.out, chunk=a.chunk)
    elif a.what == "entities":
        res = gen_entities(a.n, a.seed, a.out, chunk=a.chunk)
    else:
        res = bench_streams(a.n, a.seed)
    if a.out:
        res["bytes"] = os.path.getsize(a.out)
        th = time.perf_counter()
        res["sha256"] = sha256_file(a.out)
        res["sha256_s"] = time.perf_counter() - th
    res["peak_rss_mib"] = peak_rss_mib()
    res["python"] = sys.version.split()[0]
    res["numpy"] = np.__version__
    res["orjson"] = orjson.__version__
    print(orjson.dumps(res, option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS).decode())


if __name__ == "__main__":
    main()
```

The orjson memory check and the FtM round trip check, as run [S59]:

```python
import tracemalloc

import orjson
from followthemoney import ValueEntity

tracemalloc.start()
rec = {"id": "syn-acct-0000001", "schema": "BankAccount",
       "nr": {"v": "1.0", "synthetic": True, "synthetic_kind": "activity", "account_kind": "customer"},
       "properties": {"accountNumber": ["NRSYN0000000001"], "bankName": ["Synthetic Bank One"],
                      "currency": ["GBP"], "openingDate": ["2020-01-15"]},
       "referents": [], "datasets": ["nr_synthetic"]}
buf = [orjson.dumps(rec, option=orjson.OPT_APPEND_NEWLINE) for _ in range(100_000)]
current, peak = tracemalloc.get_traced_memory()
print("100,000 outputs held:", round(current / 2**20, 1), "MiB")  # printed 390.7 MiB

line = buf[0]
d = orjson.loads(line)
out = ValueEntity.from_dict(d).to_dict()
print(sorted(d))  # 'datasets' and 'referents' are gone from d
print(orjson.dumps(out, option=orjson.OPT_APPEND_NEWLINE) == line)  # True
```

## 6. Validity of synthetic benchmarks

### 6.1 What the literature says

- **Synthetic results are optimistic.** A systematic review and experiment on Elliptic (real) and IBM HI-Small (synthetic) concludes that "care should be taken with synthetic data as this can give overly optimistic results", citing detection bias when the patterns a model looks for are planted in the data [S61]. AMLworld's authors: "performance might not translate one-to-one to real data" [S8]. A 2025 flow-analysis study injected one simple sanctions-evasion pattern (three intermediaries) into a 200-node synthetic network and flagged all three injected paths plus one false positive caused by noise [S71]; an injection that simple says little about the variety of real cases (Inference).
- **Tuning to the planted typologies.** The FCA warns about "firms optimising their systems to detect the specific typologies embedded in the dataset" and varied its typologies so "suspicious behaviour does not appear in identical forms each time" [S24]. AMLworld withheld its generator code for a related reason (part A) [S2].
- **Shortcuts.** Models adopt decision rules that score well on benchmarks but fail in harder conditions [S62]. Tide therefore adds legitimate patterns in its illicit amount and timing ranges (legitimate structuring, rapid flows and bursts) [S20], and AMLworld advises against account ids as features [S2].
- **Holdout reuse.** Reusing one holdout set adaptively overfits it; Dwork et al. give a way to reuse it safely [S63]. Even a fresh test set built by the same process cost ImageNet models 11 to 14 points of accuracy [S64]: expect some drop between generator seeds and variants.
- **Benchmark choice.** Changing the benchmark tasks can reorder method rankings [S65]: report per typology and variant, not one average.
- **Imbalance.** Precision-recall plots are more informative than ROC plots on imbalanced data [S66].
- **Drift.** On Elliptic, all methods "perform poorly after the shutdown" of a dark market [S67]; AMLGentex models drift by changing typologies mid-run [S16].
- **Real labels.** Esteban et al. judge synthetic data by training a model on it and testing on real data, and the reverse [S68]; NeonRadar has no real labelled data for that check. Work on real bank data looks different: a Feedzai alert-triage study validated on a real banking dataset reports an 80 percent cut in false positives while detecting over 90 percent of true positives [S69]. Adding public real-world features to synthetic data has been proposed to raise its utility for training [S70].
- **Adaptive adversaries.** AMLGentex states it "does not model a dynamic feedback loop" with criminals [S16]; the 2025 co-evolution framework lets launderer agents adapt to the detector [S25].

### 6.2 Rules for NeonRadar

1. **Independence.** The generator must not import `neonradar_detect`, and detectors must not import `neonradar_ingest.synth`, enforced by a test that scans imports, in the spirit of M2.9's rule that the ER benchmark "must not import `neonradar_keys`" [S4]. Detectors read no `synthetic` property, `:Synthetic` label or id prefix (Inference).
2. **Parameter sources.** Generator ranges come from the typology researcher and the cited sources (section 3); detector thresholds come from the approved typology YAML (5.4) [S1]. The ingest squad owns the first and the detect squad the second (Inference).
3. **Wider draws.** Scenario parameters cover values outside the detector defaults (for example cycles of 7 or 8 hops and windows up to 30 days against defaults of 6 and 14 [S1]). Report "in-envelope" and "out-of-envelope" recall separately, so a low overall recall is explained rather than hidden.
4. **Look-alikes and counter-leakage.** Every typology has look-alike scenarios (section 3) and background flows in its illicit ranges (Tide [S20]); look-alike hit rate is reported next to precision.
5. **Splits by seed.** `dev` seeds are free to use; a fixed `test` seed runs in CI; the `holdout` seed is chosen at Gate 3 only after the detector versions are tagged (for example derived from the SHA-256 of the tagged commit), run once, and published with the results; each later phase picks a new holdout [S63].
6. **Holdout-only variants.** Some variants never appear in dev or test (for example `structuring/spread_below_daily`, `circular_flow/related_party_return`, `fan_in_collection/two_tier`), to measure generalisation.
7. **Adversarial variants.** Boundary variants just outside the defaults, and mimicry variants in which illicit scenarios copy a look-alike's features (for example a periodic schedule), reported as their own split. Co-evolution is future work [S25].
8. **Leakage probes in CI** (extending part A's single-feature probe [S2]): for each label class compare distributions of amount cents, round-amount share, hour, weekday, second-of-minute, account age, degree, id rank and file position; a feature not named in the typology definition that separates the classes fails the build.
9. **Noise only where intended.** Label noise and partial observability (AMLGentex [S15]) are for robustness studies; the Gate 3 numbers use clean labels.
10. **Realism report.** The manifest records generated aggregates next to their targets (channel shares, per-adult rates and mean amounts from section 2), so drift in the background is visible in review (Inference).
11. **Honest framing.** The evaluation report states that synthetic precision and recall measure agreement with NeonRadar's own typology definitions and generator, not effectiveness on real data [S61][S8][S24].

## Sources

All sources were read on 18 October 2026 unless a command says otherwise.

- [S1] NeonRadar PHASE-1.md: G1 (2.1), C1 record rules R5 to R9 and `nr` keys (5.1), C2 (5.2), C4 alert and typology file (5.4), M1.8e, M1.9b, 7.2. Local file `/home/claude/neonradar-phase1/doc/PHASE-1.md`.
- [S2] NeonRadar research note `synthetic-docs-mcp.md`, part A (16 October 2026). Local file `/home/claude/neonradar-phase1/research/synthetic-docs-mcp.md`.
- [S3] NeonRadar research note `aml-domain.md`, section 2. Local file `/home/claude/neonradar-phase1/research/aml-domain.md`.
- [S4] NeonRadar PHASE-2.md: C1 1.1.0 keys (`psc_statements`, `accounts_category`, synthetic `list` and `leak` kinds), loader rules L9, L13 and L17, G9, M2.3a `top10_address_share`, M2.9 ER benchmark, `pep_former_months`, Wilson intervals, `orjson==3.13.*`. Local file `/home/claude/neonradar-phase2/doc/PHASE-2.md`.
- [S5] IBM/AMLSim, `git clone --filter=blob:none --no-checkout https://github.com/IBM/AMLSim.git`; `git log -1 origin/master` (7338a4bcb1af9bcfea2201ad7daccfe2a4d569ca, 2022-02-14); `git branch -r` with dates; README and LICENSE.
- [S6] AMLSim issues: https://github.com/IBM/AMLSim/issues
- [S7] Weber et al., "Scalable Graph Learning for Anti-Money Laundering: A First Look", 2018: https://arxiv.org/abs/1812.00076
- [S8] Altman et al., "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models": https://arxiv.org/abs/2306.16424 ; https://arxiv.org/html/2306.16424v3
- [S9] Kaggle API, AMLworld metadata: https://www.kaggle.com/api/v1/datasets/view/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- [S10] Third-party Hugging Face copy of AMLworld HI-Small (tagged cdla-sharing-1.0; the `HI-Small_Trans.csv` size, 475,664,283 bytes, equals the Kaggle file size in [S2]): https://huggingface.co/api/datasets?search=HI-Small&limit=50 ; https://huggingface.co/api/datasets/OsamaMIT/IBM-AML-HI-Small/tree/main ; https://huggingface.co/datasets/OsamaMIT/IBM-AML-HI-Small/resolve/main/HI-Small_Patterns.txt
- [S11] IBM/Multi-GNN (Apache-2.0), `git clone --filter=blob:none --no-checkout https://github.com/IBM/Multi-GNN.git`, `format_kaggle_files.py` (commit 252b0252, 2024-02-13).
- [S12] Oztas et al., "Enhancing Anti-Money Laundering: Development of a Synthetic Transaction Monitoring Dataset", ICEBE 2023, accepted manuscript: https://eprints.bournemouth.ac.uk/40982/1/Full_IEEE_Dataset_Conference_Paper%20%284%29.pdf
- [S13] Kaggle API, SAML-D metadata and file list: https://www.kaggle.com/api/v1/datasets/view/berkanoztas/synthetic-transaction-monitoring-dataset-aml ; https://www.kaggle.com/api/v1/datasets/list/berkanoztas/synthetic-transaction-monitoring-dataset-aml
- [S14] Oztas, PhD thesis record, Bournemouth University, 2025: https://eprints.bournemouth.ac.uk/41326/
- [S15] aidotse/AMLGentex, `git clone --filter=blob:none --no-checkout https://github.com/aidotse/AMLGentex.git`; `git log -1 origin/HEAD` (4b9a69dbd2edcf02fcec8eb3efe54937b6d77f1f, 2026-02-22); files `pyproject.toml`, `LICENSE`, `src/utils/pattern_types.py`, `experiments/template_experiment/config/*`, `src/data_creation/temporal_simulation/simulator.py`, `src/data_creation/temporal_simulation/alert_patterns.py`, `src/feature_engineering/noise.py`, `src/ml/metrics/metrics.py`.
- [S16] Östman et al., "AMLgentex: Mobilizing Data-Driven Research to Combat Money Laundering": https://arxiv.org/abs/2506.13989 ; https://arxiv.org/html/2506.13989v2
- [S17] Hugging Face API, AMLGentex datasets: https://huggingface.co/api/datasets?author=AMLGentex&full=true
- [S18] AMLGentex repository page: https://github.com/aidotse/AMLGentex
- [S19] PyPI, numpy 2.1.0 wheel tags (cp310 to cp313): https://pypi.org/pypi/numpy/2.1.0/json
- [S20] mntijn/Tide, `git clone --filter=blob:none --no-checkout https://github.com/mntijn/Tide.git`; `git log -1 origin/master` (522ccebf266d6a77ddf29e59725d5b27a5a8a0a3, 2026-06-08); files `LICENSE`, `pyproject.toml`, `configs/patterns.yaml`, `configs/graph.yaml`, `tide/datastructures/attributes.py`, `tide/patterns/manager.py`, `tide/patterns/*.py`.
- [S21] van den Beukel, Rožanec and Varbanescu, "Tide: A Customisable Dataset Generator for Anti-Money Laundering Research": https://arxiv.org/abs/2603.01863
- [S22] Huda et al., "AMLNet: A Knowledge-Based Multi-Agent Framework to Generate and Detect Realistic Money Laundering Transactions": https://arxiv.org/abs/2509.11595
- [S23] AMLNet: Synthetic Anti-Money Laundering Benchmark Dataset, Version 2.0, Zenodo: https://zenodo.org/records/21237971
- [S24] FCA, "Research Note: Synthetic Data and Anti-Money Laundering, Project Report", 15 April 2026: https://www.fca.org.uk/publications/research-notes/research-note-synthetic-data-anti-money-laundering-project-report ; https://www.fca.org.uk/publication/research-notes/synthetic-data-anti-money-laundering-project-report.pdf
- [S25] Wang et al., "Hide and seek in transaction networks: a multi-agent framework for simulating and detecting money laundering activities", Complex and Intelligent Systems 11, 271 (2025): https://link.springer.com/article/10.1007/s40747-025-01913-w
- [S26] Bellei et al., "The Shape of Money Laundering: Subgraph Representation Learning on the Blockchain with the Elliptic2 Dataset": https://arxiv.org/abs/2404.19109
- [S27] J.P. Morgan, synthetic data, Anti-Money Laundering: https://jpmorgan.com/technology/artificial-intelligence/initiatives/synthetic-data/anti-money-laundering
- [S28] Srivasthav and Apte, "Beyond Static Datasets: A Behavior-Driven Entity-Specific Simulation...": https://arxiv.org/abs/2501.00757
- [S29] UK Finance, UK Payment Markets 2026, Summary (2025 data): https://www.ukfinance.org.uk/system/files/2026-08/PaymentMarketsReport_2026Summary.pdf
- [S30] UK Finance, Card Spending Update, March 2026 (published 16 June 2026): https://www.ukfinance.org.uk/system/files/2026-06/Card%20Spending%20Update%20-%20March%202026.pdf
- [S31] Pay.UK, Faster Payment System: https://www.wearepay.uk/what-we-do/payment-systems/faster-payment-system/
- [S32] Pay.UK, Faster Payments transaction limits (individual payments up to £1 million; providers set their own limits): https://www.wearepay.uk/what-we-do/payment-systems/faster-payment-system/transaction-limits/
- [S33] Pay.UK, how Faster Payments work: https://www.wearepay.uk/what-we-do/payment-systems/faster-payment-system/how-faster-payments-work/
- [S34] Pay.UK, Bacs payment system: https://www.wearepay.uk/what-we-do/payment-systems/bacs-payment-system/
- [S35] Bank of England, "Proposal to extend RT2 and CHAPS settlement hours (phase 1)", 29 July 2025: https://www.bankofengland.co.uk/paper/2025/cp/proposal-extend-rt2-chaps-settlement-hours-phase-1
- [S36] Bank of England, "Extending RTGS and CHAPS settlement hours: early morning extension", 24 February 2026: https://www.bankofengland.co.uk/paper/2026/ps/extending-rtgs-and-chaps-settlement-hours-early-morning-extension
- [S37] GOV.UK bank holidays JSON: https://www.gov.uk/bank-holidays.json
- [S38] GOV.UK, when do the clocks change: https://www.gov.uk/when-do-the-clocks-change
- [S39] ONS, Annual Survey of Hours and Earnings 2025 (23 October 2025): https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/earningsandworkinghours/bulletins/annualsurveyofhoursandearnings/2025
- [S40] ONS, Private rent and house prices, UK, release of 16 September 2026: https://www.ons.gov.uk/economy/inflationandpriceindices/bulletins/privaterentandhousepricesuk/latest
- [S41] FCSA, article citing ONS ASHE April 2019 pay periods (secondary source): https://www.fcsa.org.uk/37-of-temporary-casual-employee-jobs-paid-outside-a-monthly-pay-cycle
- [S42] Department for Business and Trade, Business population estimates 2025 (2 October 2025): https://www.gov.uk/government/statistics/business-population-estimates-2025/business-population-estimates-for-the-uk-and-regions-2025-statistical-release
- [S43] Department for Business and Trade, Large businesses' payment practices and performance statistics 2025, commentary (14 July 2026): https://www.gov.uk/government/statistics/large-businesses-payment-practices-and-performance-statistics-2025/large-businesses-payment-practices-and-performance-statistics-2025-commentary
- [S44] GOV.UK, pay employers' PAYE: https://www.gov.uk/pay-paye-tax ; running payroll, reporting to HMRC: https://www.gov.uk/running-payroll/reporting-to-hmrc
- [S45] GOV.UK, VAT return deadlines: https://www.gov.uk/vat-returns/deadlines
- [S46] GOV.UK, pay Corporation Tax: https://www.gov.uk/pay-corporation-tax
- [S47] GOV.UK, Council Tax, paying your bill: https://www.gov.uk/council-tax/paying-your-bill
- [S48] GOV.UK, Income Tax rates 2026-27: https://www.gov.uk/income-tax-rates ; National Insurance rates: https://www.gov.uk/national-insurance-rates-letters
- [S49] Post Office press release, 19 November 2025 (October 2025 cash deposits and withdrawals): https://post-office.mynewsdesk.com/pressreleases/highest-month-on-record-for-number-of-cash-deposits-made-at-post-offices-3417323
- [S50] British Retail Consortium, Payments Survey 2024 (2023 data): https://brc.org.uk/news/finance/brc-payments-survey-2024-1
- [S51] Pay.UK, Current Account Switch Service records over one million switches in 2025 (29 January 2026): https://www.wearepay.uk/current-account-switch-service-records-over-one-million-switches-in-2025/
- [S52] Dormant Bank and Building Society Accounts Act 2008, section 10: https://www.legislation.gov.uk/ukpga/2008/31/section/10
- [S53] Money Laundering, Terrorist Financing and Transfer of Funds (Information on the Payer) Regulations 2017, regulation 14 (current text reads £10,000): https://www.legislation.gov.uk/uksi/2017/692/regulation/14
- [S54] 31 CFR 1010.311 and 1010.313: https://www.ecfr.gov/current/title-31/subtitle-B/chapter-X/part-1010/subpart-C/section-1010.311 ; https://www.ecfr.gov/current/title-31/subtitle-B/chapter-X/part-1010/subpart-C/section-1010.313
- [S55] FCA press release, "Greater flexibility to be given for setting future contactless limits", 19 December 2025: https://www.fca.org.uk/news/press-releases/greater-flexibility-be-given-setting-future-contactless-limits
- [S56] FCA press release on Financial Lives 2024, 16 May 2025: https://www.fca.org.uk/news/press-releases/more-people-have-bank-accounts-one-ten-have-no-cash-savings
- [S57] NumPy v2.5 manual, random Generator compatibility policy: https://numpy.org/doc/stable/reference/random/compatibility.html
- [S58] NumPy v2.5 manual, parallel random number generation: https://numpy.org/doc/stable/reference/random/parallel.html
- [S59] Local measurements on 18 October 2026 in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p3/research-synth/bench/` (Python 3.14.6 via `uv venv --python 3.14`): `python -I scripts/synth_bench.py payments-daily|payments|entities|streams ...`; `scripts/stream_micro.py`, `scripts/serialise_micro.py`, `scripts/ftm_probe.py`, `scripts/faker_micro.py`; tracemalloc checks of orjson outputs; FtM 4.11 validation and round trip of every 40th line of the final payment and entity files; `zoneinfo` conversions around the 2026 clock changes; three runs of `python -I -c "print(list({...}))"` showing different set orders; `followthemoney.model` property checks.
- [S60] PyPI JSON API: https://pypi.org/pypi/followthemoney/json (4.11.0) ; https://pypi.org/pypi/numpy/json (2.5.4) ; https://pypi.org/pypi/orjson/json (3.13.0; licence expression read from the installed wheel's METADATA) ; https://pypi.org/pypi/Faker/json (40.43.0) ; https://pypi.org/pypi/tzdata/json (2026.5)
- [S61] Deprez et al., "Network Analytics for Anti-Money Laundering: A Systematic Literature Review and Experimental Evaluation", DOI 10.1287/ijds.2024.0042: https://arxiv.org/abs/2405.19383v4 ; https://arxiv.org/html/2405.19383v4
- [S62] Geirhos et al., "Shortcut Learning in Deep Neural Networks", DOI 10.1038/s42256-020-00257-z: https://arxiv.org/abs/2004.07780
- [S63] Dwork et al., "Generalization in Adaptive Data Analysis and Holdout Reuse", 2015: https://arxiv.org/abs/1506.02629
- [S64] Recht et al., "Do ImageNet Classifiers Generalize to ImageNet?", 2019: https://arxiv.org/abs/1902.10811
- [S65] Dehghani et al., "The Benchmark Lottery", 2021: https://arxiv.org/abs/2107.07002
- [S66] Saito and Rehmsmeier, "The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets", PLOS ONE 10(3), 2015: https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0118432
- [S67] Weber et al., "Anti-Money Laundering in Bitcoin: Experimenting with Graph Convolutional Networks for Financial Forensics", 2019: https://arxiv.org/abs/1908.02591 ; https://arxiv.org/html/1908.02591v1
- [S68] Esteban, Hyland and Rätsch, "Real-valued (Medical) Time Series Generation with Recurrent Conditional GANs", 2017: https://arxiv.org/abs/1706.02633
- [S69] Eddin et al., "Anti-Money Laundering Alert Optimization Using Machine Learning with Graphs", 2021: https://arxiv.org/abs/2112.07508
- [S70] Chung et al., "Hybrid Data can Enhance the Utility of Synthetic Data for Training Anti-Money Laundering Models", 2025: https://arxiv.org/abs/2509.18499
- [S71] Capozzi et al., "FlowSeries: flow analysis on financial networks", Applied Network Science 10, 28 (2025): https://appliednetsci.springeropen.com/articles/10.1007/s41109-025-00711-0
