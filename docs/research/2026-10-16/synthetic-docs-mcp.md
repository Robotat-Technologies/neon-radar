# NeonRadar phase 1: synthetic AML data, documentation tooling, Neo4j MCP and the Claude Code GitHub Action

Research date: 16 October 2026. Every fact below was checked on 2026-10-16 against the source given in square brackets. The Sources list at the end gives the full URL of every source with its check date. A fact that could not be confirmed against a primary source is marked UNVERIFIED. A statement marked "Inference" is reasoning from verified facts, not something a source says.

Scope: NeonRadar is an Apache-2.0, local-first, open-source anti-money-laundering knowledge graph (Python 3.12+, Neo4j, Vue 3 frontend), built mostly by Claude Code agents and reviewed by humans. Typology definitions are not repeated here; see `aml-domain.md` section 2 in this folder. Neo4j versions, APOC and Docker setup are in `neo4j.md` and `stack.md`.

## How this was verified (read this first)

- GitHub repositories were cloned read-only (partial clones) and files, tags and commit dates were read with git: IBM/AMLSim, IBM/Multi-GNN, aidotse/AMLGentex, mntijn/Tide, EdgarLopezPhD/PaySim, eclab/mason, stleary/JSON-java, vuejs/vitepress, zensical/zensical, zensical/docs, withastro/starlight, neo4j/mcp, neo4j-contrib/mcp-neo4j, anthropics/claude-code-action. The GitHub REST API was not available in this session, so star, fork and issue counts come from the rendered GitHub pages.
- Package versions come from the PyPI JSON API and the npm registry, queried directly. The Faker, mimesis and neo4j-mcp-server wheels were downloaded and inspected. Faker and mimesis were run in an isolated virtual environment to sample names. `uvx neo4j-mcp-server@1.6.0 --version`, `uvx neo4j-mcp-server@1.6.0 --help` and `uvx mcp-neo4j-cypher@0.6.0 --help` were executed (no database connection).
- Empirical test: networkx 1.11, which AMLSim pins, was installed and imported on Python 3.12 and 3.13.
- Kaggle pages render client-side, so Kaggle facts come from Kaggle's public API endpoints (`/api/v1/datasets/view/...` and `/api/v1/datasets/list/...`).
- Access limits on 2026-10-16: direct downloads from cs.gmu.edu (MASON), kaggle.com, search.maven.org and arxiv.org PDFs were refused by the egress proxy when using curl; the web fetch tool was used for arXiv and the Kaggle API instead. A full AMLSim build and run could not be attempted because the MASON jar could not be downloaded here.

## Recommendations at a glance

1. Synthetic data: write a small, seeded, pure-Python generator inside NeonRadar. Do not run AMLSim. Borrow design ideas (and, with attribution, small pieces of code) from AMLGentex (Apache-2.0) and Tide (MIT). Treat AMLworld (CDLA-Sharing-1.0), SAML-D (CC BY-NC-SA 4.0) and AMLSim output as optional external benchmarks that users download themselves; never commit them to the repository.
2. When users run locally against real registry companies, give real companies only background activity by default and inject labelled typology scenarios among synthetic entities added next to them, so that synthetic allegations never attach to real names.
3. Names: use Faker (MIT) for person names in ar_SA, ru_RU and en_GB with a denylist of real prominent family names. Build company names compositionally. Never use mimesis `Finance.company()`, which returns real listed companies.
4. Documentation: VitePress (Vue-native, offline local search, official GitHub Pages workflow). Native right-to-left support was merged to VitePress `main` on 2026-09-13 but is not in any published release yet; if Arabic documentation is needed before VitePress 2 ships it, Astro Starlight is the strongest RTL option. Do not start new documentation on Material for MkDocs (maintenance mode). Zensical is promising but still alpha.
5. Neo4j MCP: the official `neo4j/mcp` server v1.6.0, launched with `uvx neo4j-mcp-server@1.6.0`, in read-only mode with telemetry off. It is GPL-3.0 (fine as an external developer tool; do not vendor it) and requires APOC. Keep the Labs memory server away from the NeonRadar database.
6. Pull request review: `anthropics/claude-code-action@v1` on `pull_request` with a custom prompt, an `ANTHROPIC_API_KEY` (or `CLAUDE_CODE_OAUTH_TOKEN`) secret, `id-token: write`, and the Claude GitHub App installed. Fork pull requests on public repositories receive no secrets, so automatic review runs only for branches in the same repository.

---

## Part A. Synthetic AML transaction data with labels

### A1. IBM AMLSim (github.com/IBM/AMLSim)

| Item | Finding | Source |
|---|---|---|
| Licence | Apache-2.0 ("Apache License Version 2.0, January 2004" in LICENSE) | [A1][A2] |
| Last commit on `master` | 2022-02-14, merge of PR #66 by Hiroki Kanezashi (commit 7338a4bc) | [A2] |
| Other branches | `new-schema` (2019-05-15) and `refactor-conffile` (2019-05-17), which the README calls "outdated and unstable"; unmerged bot branches `dependabot/maven/org.json-json-20230227` (2023-04-14), `renovate/configure` (2025-05-08), `whitesource/configure` (2025-09-17) | [A2] |
| Activity signals | 237 commits; 385 stars; 119 forks; 47 open issues; 4 open pull requests; no archive notice | [A1] |
| Recent issues | #93 (2026-10-10, an adaptation for AI-agent payment graphs); #87 "Add Modern AML Typologies to Alert Pattern Library" (2026-02-10); #86 "Does it work?" (2025-12-01); #83 "Working project setup on Windows 11 2025?" (2025-03-06); #78 "Error trying to run sh scripts/run_AMLSim.sh conf.json" (2023-06-01); #73 "Is this project alive. Anyone recently implemented?" (2022-11-23); #70 "Upgrade Python and networkx" (2022-07-14); #68 "Maven Install and Use Issue (MASON and Paysim)" (2022-02-13); #60 "java.lang.NoSuchMethodError when running the simulator." (2021-12-01) | [A3] |
| Maintenance status | Inference: unmaintained in practice. No commit on `master` for 4 years and 8 months, unanswered "does it work" questions, and only automated bots have pushed branches since 2022. | [A2][A3] |

Runtime requirements (README and build files on `master`) [A2]:

- Java 8. The README says "Java 8 (Download and copy all jar files to `jars/` directory: See also `jars/README.md`)", and `pom.xml` sets `maven.compiler.source` to 1.8. Listed jars: MASON 20, Commons-Math 3.6.1, JSON in Java 20180813, WebGraph 3.6.1, DSI Utilities 2.5.4, fastutil 8.2.3, Sux for Java 4.2.0, JSAP 2.1, SLF4J 1.7.25, MySQL Connector for Java 5.1, JUnit5, Mockito Core and Mockito Inline 4.0.0, Byte Buddy and Byte Buddy Agent 1.11.19, Objenesis 3.2.
- Maven is optional: "If you choose to use Maven, you only manually need to fetch and place 1 jar file (MASON) in your `jars/` folder", then install it with `mvn install:install-file -Dfile=jars/mason.20.jar -DgroupId=mason -DartifactId=mason -Dversion=20 -Dpackaging=jar -DgeneratePom=true`.
- MASON: the GMU project page lists MASON 22 as current and still offers `mason.20.jar` under previous releases [A5]. MASON is mostly under the Academic Free License 3.0, with a few files under the Artistic License and partial Sun licences [A6]. Its repository is active (last commit 2026-07-10) [A6].
- Python: the README says "Python 3.7". `requirements.txt` pins `networkx==1.11` and lists numpy, `matplotlib>=3.1.2`, pygraphviz, powerlaw, python-dateutil and Faker. The README still says "matplotlib==2.2.3 (The latest version is not compatible)", which contradicts `requirements.txt`. The README justifies the networkx pin: "We do not support version 2.* due to performance issues when creating a large graph".
- `pom.xml` pins org.json 20180813. The LICENSE at that upstream tag contains "The Software shall be used for Good, not Evil." Upstream replaced its licence with Public Domain on 2022-08-23 [A7]. The Dependabot branch that bumps it was never merged [A2].

Empirical test of the Python stage (run 2026-10-16) [A4]:

- `pip install networkx==1.11` succeeds on Python 3.12 and 3.13, but `import networkx` fails with `ImportError: cannot import name 'gcd' from 'fractions'`. Python 3.9 removed it: "`fractions.gcd()` function has been removed, it was deprecated since Python 3.5" [A4]. AMLSim's generator therefore needs Python 3.8 or earlier, both end of life.
- The generator also uses the networkx 1.x API (`self.g.node[_acct]` in `add_aml_typology`), so moving to networkx 2 or 3 is a code port, not a pin bump [A2].

How laundering patterns are configured [A2]:

- `conf.json` `input.alert_patterns` names `alertPatterns.csv` inside the parameter directory (for example `paramFiles/1K`).
- Columns, from `paramFiles/README.md`: `count` (number of typology instances), `type` (pattern name), `schedule_id`, `min_accounts`, `max_accounts`, `min_amount`, `max_amount` (initial amount range), `min_period`, `max_period` (days), `bank_id` (optional; empty means members may come from any bank), `is_sar` ("Whether the alert is SAR (True) or false alert (False)").
- Example file `paramFiles/typologies/alertPatterns.csv`, one instance of each type:

```
count,type,schedule_id,min_accounts,max_accounts,min_amount,max_amount,min_period,max_period,bank_id,is_sar
1,fan_in,2,5,5,100,200,10,20,,True
1,fan_out,2,5,5,100,200,10,20,,True
1,bipartite,2,5,5,100,200,10,20,,True
1,stack,2,5,5,100,200,10,20,,True
1,random,2,5,5,100,200,10,20,,True
1,cycle,2,5,5,100,200,10,20,,True
1,scatter_gather,2,7,7,100,200,10,20,,True
1,gather_scatter,2,11,11,100,200,10,20,,True
```

- Pattern types and model IDs, from `self.alert_types` and the code comments in `scripts/transaction_graph_generator.py`:

| `type` | Model ID | Shape (code comment) |
|---|---|---|
| `fan_out` | 1 | "single (main) account --> multiple accounts" |
| `fan_in` | 2 | "multiple accounts --> single (main) account" |
| `cycle` | 3 | "Cycle transactions"; in Java each hop subtracts a margin (`amount = amount - margin`, with `margin = amount * marginRatio`) |
| `bipartite` | 4 | "originators -> many-to-many -> beneficiaries" |
| `stack` | 5 | "stacked bipartite layers" |
| `random` | 6 | "Random transactions among members" |
| `scatter_gather` | 7 | "fan-out -> fan-in" |
| `gather_scatter` | 8 | "fan-in -> fan-out" |

- Schedules, from `AMLTypology.java`: 0 `FIXED_INTERVAL` ("All accounts send money in order with the same interval"), 1 `RANDOM_INTERVAL`, 2 `UNORDERED` ("All accounts send money randomly"), 3 `SIMULTANEOUS` ("All transactions are performed at single step simultaneously"). The CSV README documents only 0 to 2.
- Background behaviour is set in `accounts.csv` with model IDs 0 single transactions, 1 fan-out, 2 fan-in, 3 mutual, 4 forward, 5 periodical; the graph structure comes from `degree.csv` through networkx's directed configuration model.
- Amounts: typology initial amounts come from `RoundedAmount`, which picks round values on a 10, 100 or 1000 grid between the minimum and maximum. The Java simulator then draws `TargetedTransactionAmount` uniformly between the configured minimum and the target or balance. Inference: if only alert patterns use rounded amounts, roundness becomes an easy shortcut feature for a detector.
- Seeds: `general.random_seed` in `conf.json`, overridden by the `RANDOM_SEED` environment variable; both Python `random` and `numpy.random` are seeded. One simulation step is one day (`total_steps` 720 from `base_date` 2017-01-01 in the README example).
- `is_sar=False` rows create typology-shaped "false alerts", which is a useful hard-negative mechanism.

What the output contains [A2]:

- Output files (`conf.json` `output` section): `accounts.csv`, `transactions.csv` (all transactions), `cash_tx.csv`, `alert_accounts.csv`, `alert_transactions.csv`, `sar_accounts.csv`, `individuals-bulkload.csv`, `organizations-bulkload.csv`, `accountMapping.csv`, `resolvedentities.csv`, and the logs `tx_log.csv`, `tx_count.csv`, `diameter.csv`.
- Columns, from `paramFiles/1K/schema.json`:
  - transactions: `tran_id, orig_acct, bene_acct, tx_type, base_amt, tran_timestamp, is_sar, alert_id`
  - alert transactions: `alert_id, alert_type, is_sar, tran_id, orig_acct, bene_acct, tx_type, base_amt, tran_timestamp`
  - alert members: `alert_id, alert_type, acct_id, acct_name, is_sar, model_id, start, end, schedule_id, bank_id`
  - accounts: `acct_id, dsply_nm, type, acct_stat, acct_rptng_crncy, prior_sar_count, branch_id, open_dt, close_dt, initial_deposit, tx_behavior_id, bank_id, first_name, last_name, street_addr, city, state, country, zip, gender, birth_date, ssn, lon, lat`
- Labels therefore exist at transaction level (`is_sar`, `alert_id`) and at alert level (alert members with type, schedule and time window).
- Pipeline: `python3 scripts/transaction_graph_generator.py conf.json`, then `sh scripts/build_AMLSim.sh` and `sh scripts/run_AMLSim.sh conf.json` (Java), then `python3 scripts/convert_logs.py conf.json`; optional checks with `scripts/validation/validate_alerts.py`.

How hard it is to run in 2026 (assessment):

- It needs two legacy toolchains at once: Python 3.7 or 3.8 with networkx 1.11 and pygraphviz (which needs Graphviz development headers), and a JDK that still compiles Java 8 sources plus a manually downloaded MASON 20 jar. Inference: feasible inside a pinned container (a Python 3.8 image plus a JDK), but every contributor and CI job would inherit end-of-life runtimes and an unmaintained codebase.
- UNVERIFIED: whether an end-to-end run succeeds today. It could not be attempted because cs.gmu.edu was unreachable from this environment. Open issues #60, #78, #83 and #86 report run failures or ask whether it works [A3].
- AMLSim creates its own synthetic accounts and people. It has no notion of attaching accounts to entities that already exist in an external graph [A2].

### A2. IBM AMLworld (Altman et al., NeurIPS 2023 Datasets and Benchmarks)

- Paper: Erik Altman, Jovan Blanuša, Luc von Niederhäusern, Béni Egressy, Andreea Anghel, Kubilay Atasu, "Realistic Synthetic Financial Transactions for Anti-Money Laundering Models", Advances in Neural Information Processing Systems 36 (NeurIPS 2023), Datasets and Benchmarks Track, DOI 10.52202/075280-1300 [A11]. arXiv 2306.16424: v1 submitted 2023-06-22, latest v3 dated 2024-01-25 [A8].
- Naming: v1 calls the generator IT-AML ("between our approach (IT-AML), detailed in Section 3") [A9]. v3 renames it AMLworld ("our approach AMLworld, detailed in Section 3") and no longer uses "IT-AML" [A10]. The old name still appears in some literature, including `aml-domain.md`.
- Laundering patterns injected: the eight AMLSim patterns, namely fan-out, fan-in, gather-scatter, scatter-gather, simple cycle, random, bipartite and stack [A10][A12]. Laundering is not limited to these patterns: in LI-Large, Table 8 counts 19,461 laundering transactions in patterns and 81,143 outside them (100,604 in total, 1 per 1,750 transactions) [A10].
- Laundering model: placement from nine criminal sources (extortion, loan sharking, gambling, prostitution, kidnapping, robbery, embezzlement, drugs, smuggling), then layering, then integration. Labels are transitive through co-mingled funds: when illicit money is partly passed on, each downstream portion is also labelled laundering [A10].
- Background model: banks, individuals and companies in a circular-flow economy; several accounts per entity across banks; company cross-ownership; payment formats ACH, wire, cheque, credit card, cash, reinvestment and bitcoin; currencies including dollars, euros, yuan, yen and bitcoin. The authors state "Our model uses no seed of real transactions from which to expand" and tune parameters with feedback loops against Federal Reserve statistics and IRS 2018 data [A10].
- Dataset sizes (v3 Table 4) [A10]:

| Statistic | HI-Small | LI-Small | HI-Medium | LI-Medium | HI-Large | LI-Large |
|---|---|---|---|---|---|---|
| Days spanned | 10 | 10 | 16 | 16 | 97 | 97 |
| Bank accounts | 515K | 705K | 2,077K | 2,028K | 2,116K | 2,064K |
| Transactions | 5M | 7M | 32M | 31M | 180M | 176M |
| Laundering transactions | 3.6K | 4.0K | 35K | 16K | 223K | 100K |
| Laundering rate (1 per N) | 981 | 1,942 | 905 | 1,948 | 807 | 1,750 |

  HI has a relatively higher illicit ratio and LI a lower one [A14].
- Hosting: Kaggle, "IBM Transactions for Anti Money Laundering (AML)", owner Erik Altman (ealtman2019) [A13][A14]. Current version 8, last updated 2025-07-08, 41,608,549,656 bytes in total [A14]. 18 files: for each of the six datasets a `*_Trans.csv`, a `*_Patterns.txt` and a `*_accounts.csv` (for example `HI-Small_Trans.csv` is 475,664,283 bytes and `LI-Large_Trans.csv` 16,742,513,790 bytes) [A15]. The Kaggle description still says it provides 12 files [A14]; Inference: the text predates the accounts files.
- Transaction CSV columns, as read by IBM's own preprocessing script: `Timestamp`, `From Bank`, `Account`, `To Bank`, `Account` (second occurrence), `Amount Received`, `Receiving Currency`, `Amount Paid`, `Payment Currency`, `Payment Format`, `Is Laundering` [A16].
- Licence: the Kaggle API reports `licenseName` "Community Data License Agreement - Sharing - Version 1.0" [A14]. The paper and supplement only say the data is published "under a Community Data License Agreement", without naming the variant [A10][A12]. Under CDLA-Sharing-1.0, "The Data (including the Enhanced Data) must be Published under this Agreement", credit must be preserved and changes marked, and "This Agreement imposes no obligations or restrictions on Your Use or Publication of Results" [A17].
- Generator code: not released. v3 says "what we have open-sourced is a set of data -not the code to generate the data", because "If launderers had our source code, it would be easier for them to tweak the data produced" [A10].
- Evaluation advice from the authors: a chronological 60/20/20 train, validation and test split; do not use account IDs as features; compute graph features in timestamp order; report minority-class F1 [A10][A14].
- Inference for NeonRadar: usable as an optional benchmark that users download themselves. Do not commit the data to the Apache-2.0 repository, because redistributing it carries CDLA-Sharing obligations for that data.

### A3. SAML-D (Oztas et al., 2023)

- Paper: B. Oztas, D. Cetinkaya, F. Adedoyin, M. Budka, H. Dogan and G. Aksu, "Enhancing Anti-Money Laundering: Development of a Synthetic Transaction Monitoring Dataset", 2023 IEEE International Conference on e-Business Engineering (ICEBE), Sydney, 4 to 6 November 2023, pp. 47-54, DOI 10.1109/ICEBE59045.2023.00028 [A18].
- Typologies: "A total of 28 typologies are included in the dataset, split between 11 normal and 17 suspicious" [A19].
  - Suspicious (17): Fan-Out, Fan-In, Cycle, Bipartite, Stacked Bipartite, Scatter-Gather, Gather-Scatter, Layered Fan-In, Layered Fan-Out, Structuring, Smurfing, Over-Invoicing, Deposit-Send, Cash Withdrawal, Single Large Transaction, Behaviour Change 1, Behavioural Change 2.
  - Normal (11): Single Transaction, Fan-Out, Fan-In, Mutual, Forward, Periodical, Cash Withdrawal, Cash Deposit, Small Fan-out, Mutual Plus, Normal Group.
  - The Kaggle description adds that there are 15 graphical network structures [A20].
- Size: paper Table I gives 9,411,384 transactions, of which 11,658 (0.124%) are suspicious [A19]. Kaggle version 2 (updated 2024-01-12, about 996 MB) states 9,504,852 transactions with 0.1039% suspicious and says the data was updated after the paper [A20]. 12 features: time, date, sender and receiver accounts, amount, payment type, sender and receiver bank locations, payment and receiver currencies, "Is Suspicious", and typology type [A19][A20].
- Licence: CC BY-NC-SA 4.0 on Kaggle [A20]. The accepted manuscript on the Bournemouth repository is CC BY-NC 4.0 [A18]. Inference: non-commercial and share-alike, so unsuitable for bundling in an Apache-2.0 repository.
- Hosting: Kaggle, `berkanoztas/synthetic-transaction-monitoring-dataset-aml` [A20]. Generator code: the paper does not say it is released; UNVERIFIED whether any public code exists.
- Design notes from the paper: in layered typologies "the transaction values can increase or decrease by margins of 10% to 20% across each layer"; typologies with the same structure use overlapping parameter values "to increase intricacy, mimic real-world situations, and make detection harder"; suspicious accounts also make normal transactions with accounts not involved in suspicious activity; high-risk countries include Mexico, Turkey, Morocco and the United Arab Emirates; six payment types (credit card, debit card, cash, ACH, cross-border, cheque) [A19].

### A4. Other open generators and benchmarks, 2024 to 2026

| Name | What it is | Code licence and runtime | Data licence and hosting | Maintenance on 2026-10-16 | Sources |
|---|---|---|---|---|---|
| AMLGentex (AI Sweden with Handelsbanken and Swedbank) | Generator plus benchmark derived from AMLSim, now pure Python (137 `.py` files, no Java). Normal patterns fan-in, fan-out, mutual, forward, periodical, single; alert patterns fan-in, fan-out, cycle, bipartite, stack, random, gather-scatter, scatter-gather; cash-based placement; label noise, per-bank partial observability, concept drift, camouflage; Bayesian tuning of generator parameters | Apache-2.0; `requires-python >=3.10,<3.14`; heavy dependencies (torch, torch_geometric, optuna, scikit-learn) | 12 datasets on Hugging Face (Sweden, US, Spain; 100K and 1M; easy and difficult; drift variants), updated 2025-09-25; 7 tagged MIT, 5 without a licence tag | Last commit 2026-02-22; 678 commits; 25 stars; arXiv 2506.13989 v2 dated 2025-09-25 | [A21][A22][A23] |
| Tide (van den Beukel, Rožanec, Varbanescu) | Generator of entity-rich graphs (individuals, businesses, accounts, institutions). Fraud patterns: repeated overseas transfers (sub-threshold deposits then transfers abroad), rapid fund movement, front business activity, synchronised transactions, U-turn; 11 background types including "counter-leakage" patterns; per-pattern camouflage probability | MIT; Python >=3.10; dependencies networkx, PyYAML, faker | LI and HI reference datasets on Zenodo (record 18804069, 2026-02-27), CC BY 4.0, about 1.8 GB | Last commit 2026-06-08; 107 commits; 4 stars; arXiv 2603.01863 (2026-03-02) | [A24][A25][A26] |
| AMLNet (Griffith University) | Dataset from a regulation-aware multi-agent generator aligned with AUSTRAC rules: 1,090,173 transactions, 1,745 laundering (about 0.16%), 195 simulated days, Australian payment types | No code repository linked; UNVERIFIED whether code is public | CC BY-NC 4.0 on Zenodo (record 16736515, 2025-08-04); an earlier record (16482144) is deprecated and embargoed | arXiv 2509.11595 (2025-09-15) | [A27][A28] |
| SynthAML (Jensen et al., Scientific Data 2023) | Synthetic alerts and transactions derived from a Danish bank's data with SDV HMA1: about 20,000 alerts and over 16 million transactions; alert outcome labels (Report or Dismiss, about 17% reported) | Generator code withheld for confidentiality | CC0 on figshare (articles 22396057 and 22396054, published 2023-09-25) | Static dataset | [A29] |
| PaySim | Mobile-money fraud simulator, not AML typologies | GPL-3.0; last commit 2021-05-30 (README), last code change 2019-04-02 | Kaggle "Synthetic Financial Datasets For Fraud Detection", CC BY-SA 4.0, updated 2017-04-03; labels `isFraud` and `isFlaggedFraud`; the description warns against using the balance columns because detected fraud is cancelled | Unmaintained | [A30][A31] |
| FCA synthetic AML dataset (FCA with the Alan Turing Institute, Plenitude Consulting and Napier AI) | Fully synthetic UK retail-banking data produced with a differentially private method (AIM), with injected structuring, rapid movement across accounts, round-tripping and high-risk jurisdiction transfers | Not open | Available only through the FCA Digital Sandbox, subject to "strict controls and contractual obligations" (research note dated 2026-04-15) | Not applicable | [A32] |

### A5. Recommendation: write a seeded Python generator, do not run AMLSim

Recommendation: write a small seeded Python generator in the NeonRadar codebase (for example a `neonradar.synth` package). Reasons:

1. Requirement (a) decides it. AMLSim generates its own accounts and people from aggregate parameters [A2]; attaching them to entities that already exist in our graph would need a fragile post hoc remapping. A native generator takes the entity list (registry companies locally, synthetic companies in the public demo) as its input.
2. Typology coverage. Of the seven required scenarios, AMLSim has three directly (fan_in, fan_out, cycle), two only as shapes without the defining timing (gather_scatter for rapid pass-through, stack or bipartite for layering), and none for structuring below a threshold or dormant reactivation [A2]. Thresholds, dwell times and dormancy gaps are the essence of those typologies (`aml-domain.md` section 2).
3. Toolchain and maintenance. AMLSim needs end-of-life Python (3.8 or earlier; import failure verified on 3.12 and 3.13) plus a Java 8 build with a manually installed MASON jar, and it is unmaintained [A2][A4][A5]. A project built mostly by coding agents should not depend on that.
4. Licence hygiene. AMLSim is Apache-2.0, but its Java dependency chain includes MASON (Academic Free License 3.0) and org.json 20180813 (the "Good, not Evil" licence) [A6][A7]. A native generator avoids the question.
5. Reproducibility and review. A few hundred lines of typed Python using numpy's seeded `Generator`, with property tests and a manifest, is easier to review than a three-stage Python, Java and Python pipeline.
6. Prior art without lock-in. AMLGentex (Apache-2.0) and Tide (MIT) are compatible with Apache-2.0, so ideas or small pieces of code can be reused with attribution (keep the copyright notice for MIT; keep the licence and any NOTICE for Apache-2.0) [A22][A25]. AMLGentex is too heavy to adopt as a dependency (torch and torch_geometric) and also generates its own accounts [A22].

Keep importers for the AMLworld, SAML-D and AMLSim CSV formats as optional extras outside the core, so users can benchmark detection rules on external data they download themselves.

Guard for local runs with real registry companies (Inference, consistent with `aml-domain.md` section 2(g): "real names must never be attached to synthetic allegations"): injecting labelled laundering scenarios into accounts held by real, named companies would attach synthetic allegations to real names. Recommended default: in local mode, real registry entities receive only background activity, and typology scenarios are injected among synthetic entities added next to them (synthetic shells, mules and collectors with a reserved ID namespace and `synthetic=true`). Allow real entities as scenario participants only behind an explicit opt-in flag, with every synthetic transaction and label watermarked in the interface and excluded from exports.

#### Suggested generator design

Inputs:

- Entities: ID, type (company or person), country, sector, size band and incorporation date, read from Neo4j or a fixture.
- Configuration (YAML): root seed, date window, currency and thresholds per jurisdiction, account counts per entity type, background behaviour profiles, typology mix and rates, an HI or LI preset, and noise options.

Steps:

1. Accounts: one to three accounts per entity (current, savings, and a card or cash channel for cash-intensive sectors), synthetic bank IDs across several banks so that cross-bank views exist, and open dates consistent with incorporation dates.
2. Background activity, generated first and at realistic volume: payroll fan-outs with references, supplier payments, customer receipts (fan-in), cash deposits for cash-intensive sectors, refunds and loan repayments (benign cycles), intra-group transfers, seasonal and weekday or business-hour timing, occasional dormancy with benign reactivation, and legitimate pass-through intermediaries (payroll bureaus, marketplaces). These benign look-alikes are what stop detectors from learning shape alone (see the "typical false positive" entries in `aml-domain.md` section 2).
3. Typology scenarios: each instance is a scenario object with a typology, a variant, role assignments, parameters drawn from ranges, and a time window. Parameters to vary for the seven required typologies:
   - Structuring: number of deposits, amounts as a fraction of the threshold (for example 0.70 to 0.999), number of branches or depositors, burst length (hours to days). Tide draws structuring amounts uniformly from USD 7,000 to 9,999 and deliberately places 3 to 5% of legitimate background transactions in the same range [A24].
   - Rapid pass-through: inflow count, dwell time (minutes to days), retained fraction. Tide's rapid fund movement uses burst inflows over about 24 hours followed by withdrawals totalling 85 to 95% of the inflows [A24].
   - Layering chain: number of hops (Tide default 2 to 5), decay per hop (Tide 1 to 5%; SAML-D 10 to 20% up or down), delay per hop (Tide 1 to 48 hours), optional split and re-merge [A19][A24].
   - Round-tripping cycle: cycle length, fee per hop (Tide's U-turn uses 1 to 3% per hop with hops 1 to 5 days apart), return to the originator or to a related entity [A24].
   - Fan-in collection: number of senders, sender account age and profile, time window, and what follows (often a fan-out).
   - Fan-out distribution: number of recipients, amount similarity or roundness, onward cash-out.
   - Dormant reactivation: length of the dormancy gap, an optional preceding change of signatory or director, burst size and direction.
4. Camouflage and noise: laundering accounts also run normal activity; benign and illicit variants share overlapping parameter ranges (SAML-D) [A19]; benign look-alike scenarios are generated and labelled as such (AMLSim's `is_sar=False` false alerts) [A2]; optional label noise (missing labels, wrong typology) and per-bank partial observability (AMLGentex) [A21]; some illicit flows fall outside any template, as in AMLworld's "natural" laundering [A10]; instances vary so that no typology repeats identically (FCA) [A32].
5. Outputs: transactions without labels go to the main output or graph; labels go to separate files:
   - `labels/transactions.csv`: `tx_id, scenario_id, typology, variant, step, role, is_illicit`
   - `labels/scenarios.csv` (or JSON): `scenario_id, typology, variant, is_lookalike, start_ts, end_ts, participants` (account and entity IDs with roles), `params`
   - `manifest.json`: root seed, configuration hash, generator version, Python, numpy and Faker versions, counts and illicit ratio.

Design practices from the literature:

- Amount distributions: heavy-tailed and specific to each transaction type. Tide uses a log-normal per type clipped to bounds (for example payments mu 3.8 and sigma 1.2; transfers mu 5.5 and sigma 2.0) [A24]. AMLGentex uses truncated Gaussians with separate normal and suspicious parameters (normal mean 637 and SD 300; laundering mean 799 and SD 163; in SEK) and log-normal salaries [A21][A22]. AMLworld calibrates against Federal Reserve payment statistics and IRS data [A10]. Tide's stronger advice is to keep amount distributions identical across classes "so that amount distributions do not distinguish fraudulent from legitimate accounts" [A24].
- Time windows: AMLSim offers fixed-interval, random-interval, unordered and simultaneous schedules [A2]. AMLGentex samples each pattern's window from a log-normal and controls burstiness with four Beta-distribution levels [A22]. Tide uses a 12-month window with business-hours background activity and hour-level fraud timing [A24]. AMLworld datasets span 10 to 97 days [A10]. Use timestamps with a time of day, because several typologies are defined in hours.
- Camouflage and noise: see step 4. AMLGentex reports class homophily (0.98 for normal accounts against 0.52 for launderers) as a camouflage measure [A21]. Tide mixes 50 to 90% of fraud accounts into counter-leakage patterns [A24].
- Class imbalance: published illicit transaction ratios cluster around 0.05% to 0.2%: AMLworld from 1 in 807 to 1 in 1,948 [A10], SAML-D 0.10 to 0.12% [A19][A20], Tide 0.10% and 0.19% [A24], AMLNet about 0.16% [A28]. AMLGentex has 1,850 laundering accounts out of 100,000 [A21]. SynthAML's 17% is a rate of reported alerts, not of transactions [A29]. Provide HI and LI presets and evaluate with PR-AUC or minority-class F1 rather than ROC-AUC or accuracy [A10][A24].
- Reproducibility: one root seed that spawns independent streams per component (numpy `SeedSequence`), in the spirit of Tide, where "a random seed is applied at every step of the pipeline" [A24]; AMLSim's `random_seed` with a `RANDOM_SEED` override is a simpler precedent [A2]. Iterate over entities in sorted order. Inference: name-data changes between Faker or mimesis releases change outputs for the same seed, so pin them in the lock file and record their versions in the manifest.
- Avoiding detection rules that trivially match the generator:
  - Generate legitimate examples of every transaction type, timing pattern and amount range that the illicit scenarios use (Tide's counter-leakage) [A24].
  - Give illicit accounts normal prior activity so that "absence of prior activity" is not a giveaway [A24].
  - Hide generation-only attributes (risk scores, scenario IDs, roles) from anything detectors read [A24].
  - Do not use account IDs as features, and use chronological splits [A10].
  - Write detection rules from the typology definitions in `aml-domain.md`, not from the generator code, and keep a held-out evaluation seed and held-out typology variants that rule authors never see (Inference).
  - Add a leakage check to CI: train a trivial model on single features (amount roundness, hour of day, account age, degree); if any single feature reaches a high PR-AUC, the generator leaks (Inference).
  - Treat the synthetic data as non-exhaustive and refresh its variants; the FCA warns that firms may tune to embedded typologies without improving general detection [A32].

#### Names in several scripts: Faker and mimesis

| | Faker | mimesis |
|---|---|---|
| Latest version | 40.43.0 (2026-10-09) | 22.2.0 (2026-09-23) |
| Licence | MIT | MIT |
| Python | >=3.10 | >=3.10 |
| ar_SA | Only `person` and `automotive` providers (Arabic-script names inherited from ar_AA). Everything else falls back to the default locale: in our run `company()` produced the mixed-script "آل عواض and Sons" and `iban()` a GB IBAN | `ar-sa` locale, plus ar-ae, ar-dz, ar-eg, ar-jo, ar-om, ar-kw, ar-ma, ar-qa, ar-sy, ar-tn and ar-ye |
| ru_RU | Full set: address, automotive, bank, color, company, credit_card, currency, date_time, internet, job, lorem, passport, person, phone_number, ssn | `ru` locale |
| en_GB | address, automotive, bank, internet, person, phone_number, ssn (company falls back to the default) | `en-gb` locale |
| Locale count | About 110 locale codes across providers (counted in the wheel) | 48 locales |
| Seeding | `Faker.seed()` or `seed_instance()` | `seed=` per provider |

Sources: [A33][A34] (PyPI metadata, wheel inspection and a local run on 2026-10-16).

Findings that matter for an AML tool:

- Faker's ar_SA surname list contains real, prominent family names, for example "آل سعود" (Al Saud), "بن لادن" (Bin Laden), "العليان" (Olayan) and "كانو" (Kanoo) [A33]. Synthetic suspects carrying those surnames would be a reputational problem. Keep a denylist of notable family names and filter Faker output against it.
- mimesis `Finance.company()` returns real listed companies. The ar-sa list begins with "أرامكو السعودية" (Saudi Aramco), "سابك" (SABIC), "الاتصالات السعودية (STC)" and "مجموعة بن لادن السعودية" (Saudi Binladin Group); en-gb has 315 entries such as "3i Grp.", "Admiral Grp" and "Aggreko"; ru has 588 entries such as "Mail.ru group" and "Google". Our seeded run returned "Centrica" and "«Мособлгаз»" [A34]. Never use it for synthetic companies.
- mimesis `Person(Locale.RU).full_name()` without a gender returned a male first name with a female surname ("Альберт Замятина") in our run; pass the gender explicitly (Inference from one sample) [A34].
- Recommendation: Faker for person names (ar_SA, ru_RU, en_GB) with the denylist and an explicit gender; company names built from neutral word lists plus legal-form suffixes per jurisdiction (for example Ltd and LLP; ООО and АО; Arabic forms such as "شركة ... ذ.م.م"), checked against the registry names already in the graph to avoid collisions; every synthetic entity flagged `synthetic=true` in a reserved ID namespace.

---

## Part B. Documentation site tooling for late 2026

### B1. VitePress

- Versions: the npm `latest` tag is 1.6.4 (published 2025-08-05) and `next` is 2.0.0-alpha.20 (2026-09-04); there have been 20 alphas since 2.0.0-alpha.1 on 2025-01-22. Licence MIT [B1].
- Dependencies: 1.6.4 uses Vite ^5.4.14 and Vue ^3.5.13; 2.0.0-alpha.20 uses Vite ^8.2.1, Vue ^3.5.41, shiki ^4.4.3, minisearch ^7.2.0 and @docsearch/js ^4.7.0 [B1]. Vue's latest release is 3.5.44 (2026-10-13) [B14], and `stack.md` pins Vite 8.3.4 for the NeonRadar frontend.
- Maintenance: actively developed, with 342 commits on `main` since 2026-01-01 and the latest on 2026-10-15 [B2]. Inference: the stable line has had no release for 14 months while work goes into the 2.0 alphas.
- i18n: `locales` with per-locale `label`, `lang`, `dir`, `title`, `titleTemplate`, `description`, `head` and `themeConfig`; a directory per locale; per-locale Markdown strings (in the `main` docs) [B2].
- Right-to-left:
  - The stable 1.6.4 documentation has "RTL Support (Experimental)": set `dir: 'rtl'` and use an RTLCSS PostCSS plugin configured with `:where([dir="ltr"])` and `:where([dir="rtl"])` prefixes [B2].
  - Native RTL support, with the default theme laid out using CSS logical properties ("No PostCSS plugin is needed"), was merged to `main` on 2026-09-13 (commit 304207c4, "feat(theme): native rtl support (#5437)"). It is not contained in 2.0.0-alpha.20, so no published release has it yet [B2]. A follow-up fix, "correct RTL external link icons and scroll locking", landed on 2026-10-11 [B2].
  - VitePress's own documentation includes a Persian locale configured as `lang: 'fa-IR', dir: 'rtl'` [B2].
- Offline search: `themeConfig.search.provider: 'local'` gives "fuzzy full-text search using an in-browser index" built with minisearch, with per-locale translations of the search interface; alternatives are Algolia DocSearch and community plugins such as a Pagefind plugin [B2]. minisearch's default tokenizer splits on `/[\n\r\p{Z}\p{P}]+/u` (Unicode spaces and punctuation), so Arabic words are tokenised [B3]; Inference: there is no Arabic stemming or diacritic normalisation unless you supply a custom `processTerm`.
- GitHub Pages: the deploy guide has an official workflow (build with `npm run docs:build`, upload `docs/.vitepress/dist` with `actions/upload-pages-artifact`, deploy with `actions/deploy-pages`, permissions `contents: read`, `pages: write`, `id-token: write`, and set `base` for project pages) [B2]. The example pins older action majors (checkout v5, setup-node v6, configure-pages v4, upload-pages-artifact v3, deploy-pages v4); the latest releases are checkout v7.0.1, configure-pages v6.0.0, upload-pages-artifact v5.0.0 and deploy-pages v5.0.1 [B4].
- Fit for a Vue 3 team: custom themes and components are Vue single-file components, so the frontend's components and skills carry over (Inference from the theme examples in the docs [B2]).

### B2. MkDocs, Material for MkDocs and Zensical (and ProperDocs)

- MkDocs: the last stable release is 1.6.1 (2024-08-30) [B5]. MkDocs 2.0 pre-releases are on PyPI, from 2.0.dev2 (2026-08-29) to 2.0.dev6 (2026-09-15); dev6 depends on `httpx>=1.0.dev6` [B5]. According to the Material team, MkDocs 2.0 is "deliberately removing plugin support to simplify the codebase", rewrites theming, moves configuration from YAML to TOML, and "is incompatible with Material for MkDocs"; MkDocs 1.x is unmaintained, with no releases for 18 months at the time of writing and uncertain security fixes [B11].
- Material for MkDocs: latest 9.7.7 (2026-07-17), MIT [B6]. On 2025-11-11 the team wrote "Material for MkDocs is entering maintenance mode", "no new features will be added to Material for MkDocs", and "we'll continue to fix critical bugs and security issues for 12 month at least" [B10]. Version 9.7.5 (2026-03-10) caps MkDocs below 2 [B11]. The Insiders features became free for everyone on 2025-11-11 [B9].
- Zensical: "A modern static site generator built by the creators of Material for MkDocs", MIT, PyPI 0.0.70 (2026-10-12) with the classifier "Development Status :: 3 - Alpha", Python >=3.11 [B7]. The repository is very active (422 commits since 2026-01-01, latest 2026-10-14) [B12]. It reads `zensical.toml` or `mkdocs.yml` and provides native reimplementations of a listed set of MkDocs plugins; configuration for unsupported plugins is "silently ignored" [B13].
  - Languages: templates are "localized into more than 60 languages", with Arabic listed as complete; directionality is "deduced from the selected language" or set with `theme.direction`; a project has one canonical language, and multi-language sites use separate builds joined by an `alternate` language selector [B13].
  - Search: client-side and works offline, but "Search is currently only available in English" for the search interface; multilingual search itself is not affected [B13].
  - A GitHub Pages workflow is documented (using `actions/configure-pages@v6` and `actions/deploy-pages@v5`) [B13].
- ProperDocs: a BSD-2-Clause "fork of MkDocs, aiming to be a complete drop-in replacement for it", created because "development of the original MkDocs project was abandoned"; releases 1.6.5 (2026-03-16) to 1.6.7 (2026-03-20); configuration file `properdocs.yml` [B8].
- Should a new project still choose Material for MkDocs? No (Inference): it is in maintenance mode with a 12-month guarantee that runs to about November 2026 [B10], it is incompatible with MkDocs 2.0 [B11], and its successor Zensical is pre-1.0 alpha [B7]. A Python-first team would choose Zensical once it stabilises.

### B3. Astro Starlight

- Versions: `@astrojs/starlight` 0.42.6 (2026-10-08), MIT, peer dependency `astro ^7.2.10`; Astro 7.4.0 (2026-10-15) requires Node >=22.22.0 [B15]. Very active: 511 commits since 2026-01-01 [B16]. Inference: 0.x versioning means minor releases may contain breaking changes.
- Right-to-left: "Starlight provides built-in support for multilingual sites, including routing, fallback content, and full right-to-left (RTL) language support", and the i18n guide's own example is an Arabic locale with `dir: 'rtl'` [B16]. Built-in interface translations include Arabic (`packages/starlight/src/translations/ar.json`), Hebrew and Persian [B16].
- Search: Pagefind by default, with no configuration needed [B16]. Pagefind supports Arabic stemming and Arabic interface strings, detects each page's language from the `lang` attribute on the `html` element, and runs indexing separately for each language [B17].
- GitHub Pages: `withastro/action@v6` (latest 6.1.3) with `actions/deploy-pages@v5`; set `site` and usually `base` [B18][B4].
- Vue: Astro has an official Vue integration, `@astrojs/vue` 7.1.0 (2026-10-15, peers `vue ^3.5.24` and `astro ^7.0.0`) [B15]. Inference: Vue components can be embedded as islands in Starlight pages, but the site framework is Astro, not Vue.

### B4. Recommendation (one paragraph)

For a team whose frontend is Vue 3 and who may later add Arabic documentation, choose VitePress: it is Vue-native (theme and custom components are Vue single-file components, so the team reuses its components and skills), its built-in local search needs no external service and works on GitHub Pages, and the official GitHub Pages workflow is short (update the action versions it pins). Start on the 2.0 line rather than 1.6.4 if you can accept an alpha: it uses Vite 8 like the NeonRadar frontend, while 1.6.4 is 14 months old and built on Vite 5, and native RTL using CSS logical properties is already merged to `main` (2026-09-13) and will arrive with the next 2.0 pre-release. Write custom CSS with logical properties from day one so Arabic needs no rework, and plan an Arabic-aware `processTerm` (or the community Pagefind plugin) for Arabic search quality. If Arabic documentation becomes urgent before VitePress 2 ships native RTL, or Arabic search quality matters a lot, Astro Starlight is the strongest alternative: full RTL, built-in Arabic interface strings and Pagefind with Arabic stemming, at the cost of a second framework (Astro, Node >=22.22) in which Vue appears only as islands. Do not start on Material for MkDocs (maintenance mode, incompatible with MkDocs 2.0), and treat Zensical as promising but still alpha.

---

## Part C. Neo4j and GitHub integrations for Claude Code

### C1. Neo4j MCP servers

There are two families: the official product server `neo4j/mcp`, and the Neo4j Labs servers in `neo4j-contrib/mcp-neo4j`. The Labs README itself says "If you are looking for the official product Neo4j MCP server please find it here", linking to `neo4j/mcp` [C5].

Official server, `neo4j/mcp`:

| Item | Finding | Source |
|---|---|---|
| Language and licence | Go; GPL-3.0 (LICENSE.txt and NOTICE.txt; PyPI licence expression `GPL-3.0-only`) | [C1][C3] |
| Current version | v1.6.0 (2026-09-10); v1.0.0 was tagged 2025-11-24; v2.0 alpha Docker images also exist (latest `v2.0-alpha.1.7.3`, 2026-08-24) | [C1][C2][C4] |
| Activity | 441 commits since 2026-01-01, latest 2026-10-15 | [C1] |
| Tools | `get-schema`, `read-cypher`, `write-cypher`, `list-gds-procedures` | [C1] |
| Requirements | The startup check fails unless APOC's `apoc.meta.schema` is available ("please ensure the APOC plugin is installed and includes the 'meta' component"); GDS is optional and its tools are hidden when it is absent | [C1] |
| Install with uvx or pip | `uvx neo4j-mcp-server@1.6.0` or `pip install neo4j-mcp-server`; platform wheels bundle the Go binary and expose the `neo4j-mcp-server` console script. Verified: `uvx neo4j-mcp-server@1.6.0 --version` prints `neo4j-mcp version: 1.6.0` | [C1][C3] |
| Install as a binary | GitHub release assets `neo4j-mcp_Linux_x86_64.tar.gz`, `neo4j-mcp_Linux_arm64.tar.gz`, `neo4j-mcp_Linux_i386.tar.gz`, `neo4j-mcp_Darwin_arm64.tar.gz`, `neo4j-mcp_Darwin_x86_64.tar.gz`, `neo4j-mcp_Windows_x86_64.zip`, `neo4j-mcp_Windows_arm64.zip`, `neo4j-mcp_Windows_i386.zip` and `neo4j-mcp_1.6.0_checksums.txt` | [C2] |
| Install with Docker | Docker Hub `neo4j/mcp:v1.6.0` and `neo4j/mcp:latest` (amd64 and arm64); the image is built `FROM scratch`, runs as UID 65532, entrypoint `/app/neo4j-mcp` | [C1][C4] |
| Environment variables | Canonical since v1.6.0: `NEO4J_MCP_URI`, `NEO4J_MCP_USERNAME` and `NEO4J_MCP_PASSWORD` (required in stdio mode), `NEO4J_MCP_DATABASE` (default `neo4j`), `NEO4J_MCP_READ_ONLY` (default false), `NEO4J_MCP_TELEMETRY` (default true), `NEO4J_MCP_SCHEMA_SAMPLE_SIZE` (default 100), `NEO4J_MCP_LOG_LEVEL`, `NEO4J_MCP_LOG_FORMAT`, `NEO4J_MCP_TRANSPORT_MODE` (default stdio), plus `NEO4J_MCP_HTTP_*` settings for HTTP mode | [C1] |
| Old variable names | `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `NEO4J_READ_ONLY`, `NEO4J_TELEMETRY` and the others still work as deprecated aliases, and each one present prints a deprecation warning to stderr. The `--neo4j-*` flags are deprecated in favour of `--uri`, `--username`, `--password`, `--database`, `--read-only`, `--telemetry` and so on | [C1] |
| Read-only mode | Yes: `NEO4J_MCP_READ_ONLY=true` or `--read-only true`. Write tools are then not registered at all. `read-cypher` runs `EXPLAIN` and accepts only read queries; the README warns that custom procedures or functions "incorrectly classified as read-only by Neo4j may bypass this check" | [C1] |

Labs servers, `neo4j-contrib/mcp-neo4j`:

- Status: "a part of the Neo4j Labs program", "not supported by the Neo4j product team", with no SLAs or guarantees on backwards compatibility; MIT; last commit 2026-09-09; 20 commits since 2026-01-01 [C5].
- Current versions on PyPI: `mcp-neo4j-cypher` 0.6.0 (2026-04-10), `mcp-neo4j-memory` 0.4.5 (2026-02-23), `mcp-neo4j-data-modeling` 0.8.2 (2025-12-22) and `mcp-neo4j-aura-manager` 0.4.8 (2026-02-23), all for Python >=3.10 [C6].
- `mcp-neo4j-cypher`: tools `read_neo4j_cypher`, `write_neo4j_cypher` and `get_neo4j_schema` (which needs APOC). Environment variables `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`, `NEO4J_READ_ONLY`, `NEO4J_NAMESPACE`, `NEO4J_TRANSPORT`, `NEO4J_READ_TIMEOUT`, `NEO4J_RESPONSE_TOKEN_LIMIT`, `NEO4J_SCHEMA_SAMPLE_SIZE`, and `NEO4J_MCP_SERVER_HOST`, `_PORT`, `_PATH`, `_ALLOWED_HOSTS` and `_ALLOW_ORIGINS` for HTTP. Read-only through `--read-only` or `NEO4J_READ_ONLY=true`, which disables the write tool; write queries are detected with `EXPLAIN`. Install with `uvx mcp-neo4j-cypher@0.6.0 --transport stdio` (its `--help` was verified to run) or the Docker image `mcp/neo4j-cypher:latest` [C5].
- `mcp-neo4j-data-modeling`: creates, validates and visualises graph data models and imports or exports Arrows.app models. Its README configuration passes no database credentials and its source does not import the Neo4j driver (Inference: it works without a database) [C5].
- `mcp-neo4j-memory`: reads `NEO4J_URL` (falling back to `NEO4J_URI`) and writes `:Memory` nodes and a full-text index named `search` into the target database [C5]. Neo4j Community Edition has a single user database and no role-based access control, which is Enterprise-only [C7]. Do not point the memory server at the NeonRadar database; give it a separate Neo4j container if you want it.
- Because Community Edition has no role-based access control, a read-only database user cannot be created; the MCP server's read-only mode is the main guard [C7].

Example project-scoped `.mcp.json` for Claude Code (official server, local Neo4j at bolt://localhost:7687):

```json
{
  "mcpServers": {
    "neo4j": {
      "type": "stdio",
      "command": "uvx",
      "args": ["neo4j-mcp-server@1.6.0"],
      "env": {
        "NEO4J_MCP_URI": "bolt://localhost:7687",
        "NEO4J_MCP_USERNAME": "${NEO4J_USERNAME:-neo4j}",
        "NEO4J_MCP_PASSWORD": "${NEO4J_PASSWORD}",
        "NEO4J_MCP_DATABASE": "neo4j",
        "NEO4J_MCP_READ_ONLY": "true",
        "NEO4J_MCP_TELEMETRY": "false"
      }
    }
  }
}
```

Notes (from the Claude Code MCP documentation [C9], located through the Claude Code documentation map [C8], unless another source is given):

- Project-scoped servers are stored in `.mcp.json` at the project root and shared through version control; local and user scopes are stored in `~/.claude.json`.
- `${VAR}` and `${VAR:-default}` are expanded in `command`, `args`, `env`, `url` and `headers`. If a variable is unset and has no default, Claude Code warns and passes the literal `${VAR}` text, so each developer must export `NEO4J_PASSWORD`. Never commit the password.
- "For security reasons, Claude Code prompts for approval in interactive sessions before using project-scoped servers from `.mcp.json` files"; `claude mcp reset-project-choices` resets those choices. In `claude -p` runs, Agent SDK sessions and cloud sessions the prompt cannot be shown, and project-scoped servers load without asking. `disabledMcpjsonServers` blocks a server in every permission mode.
- The docs show `"type":"stdio"` in their `claude mcp add-json` example, and their `.mcp.json` examples omit `type`; Inference: both forms are accepted.
- Equivalent CLI (adapted from the documented syntax; `--` separates Claude's own options from the server command): `claude mcp add --scope project --env NEO4J_MCP_URI=bolt://localhost:7687 --env NEO4J_MCP_READ_ONLY=true --env NEO4J_MCP_TELEMETRY=false --transport stdio neo4j -- uvx neo4j-mcp-server@1.6.0` (add the username and password the same way, or edit `.mcp.json` afterwards to use `${NEO4J_PASSWORD}`). The docs warn that a server name placed directly after `--env` is read as another pair, so another option (here `--transport stdio`) must sit between them.
- `MCP_TIMEOUT` sets the server startup timeout (for example `MCP_TIMEOUT=10000 claude`); the first `uvx` run downloads the package.
- Use the `NEO4J_MCP_*` names: the unprefixed names still work but print deprecation warnings [C1]. Set telemetry off explicitly, because it defaults to on [C1].
- Neo4j must have APOC Core installed (see `neo4j.md`), or the official server will not start [C1].
- Licence (Inference, not legal advice): running the GPL-3.0 server as a separate developer tool does not change NeonRadar's Apache-2.0 licence. Do not vendor its binary into the repository or into images the project distributes.

Alternatives:

- Docker (official server): use `"command": "docker"` with `"args": ["run", "-i", "--rm", "-e", "NEO4J_MCP_URI", "-e", "NEO4J_MCP_USERNAME", "-e", "NEO4J_MCP_PASSWORD", "-e", "NEO4J_MCP_READ_ONLY", "-e", "NEO4J_MCP_TELEMETRY", "neo4j/mcp:v1.6.0"]`, keeping the same `env` block (`-e NAME` without a value passes the variable through from the environment Claude Code sets). From inside a container `localhost` is the container itself, so use `bolt://host.docker.internal:7687` on Docker Desktop (the Labs README uses this form [C5]); on Linux add `--add-host=host.docker.internal:host-gateway` or join the Compose network and use the Neo4j service name. The Linux and Compose networking advice is standard Docker behaviour and was not verified against Neo4j documentation in this research (UNVERIFIED).
- MIT-licensed Labs alternative, with the data-modeling server alongside:

```json
{
  "mcpServers": {
    "neo4j-cypher": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-neo4j-cypher@0.6.0", "--transport", "stdio", "--read-only"],
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "${NEO4J_USERNAME:-neo4j}",
        "NEO4J_PASSWORD": "${NEO4J_PASSWORD}",
        "NEO4J_DATABASE": "neo4j"
      }
    },
    "neo4j-data-modeling": {
      "type": "stdio",
      "command": "uvx",
      "args": ["mcp-neo4j-data-modeling@0.8.2", "--transport", "stdio"]
    }
  }
}
```

### C2. Claude Code GitHub Action (`anthropics/claude-code-action`)

- Current major version: v1. The moving `v1` tag points to v1.0.251 (2026-10-15). `@beta` is superseded; to migrate, change `@beta` to `@v1`, remove the `mode` input, replace `direct_prompt` with `prompt`, and move CLI options such as `max_turns` and `model` into `claude_args` [C10][C11]. Licence MIT; 423 commits since 2026-01-01 [C11].
- Modes: without a `prompt` input the action waits for the trigger phrase (`@claude` by default); with a `prompt` it runs automatically on any GitHub event (automation mode) [C10].
- Required secret: `ANTHROPIC_API_KEY` (a Claude Console API key) or `CLAUDE_CODE_OAUTH_TOKEN` (a subscription token generated with `claude setup-token`); workload identity federation needs no static secret [C10][C11].
- GitHub App: install the Claude GitHub App (https://github.com/apps/claude) for the default authentication path, or pass `github_token` or a token from a custom GitHub App [C10][C11]. Running `/install-github-app` in Claude Code installs the app, stores the secret and opens a pull request with the workflow; repository admin access is required [C10].
- Permissions: `id-token: write` is "required for the Claude Code GitHub Action's default GitHub App authentication" [C10]; reviews need `contents: read` plus pull request access; `actions: read` "lets Claude read CI results on PRs" [C10].
- Who can trigger it: on issue and pull request events the triggering user must have write access, and bot actors are rejected unless listed in `allowed_bots` [C10]. The security guide warns "Allowed bots are not checked for repository permissions" [C11]. Inference for NeonRadar: if agent pull requests are opened by a bot account, list that specific bot in `allowed_bots`, never `'*'` on a public repository.
- Forks: "On public repositories, GitHub withholds secrets from runs triggered by fork pull requests, so the review runs only on pull requests from branches in the same repository" [C10]. Do not switch to `pull_request_target` with a checkout of the pull request head without reading the action's security guide, because such runs get the base repository's secrets [C11].
- README: the README no longer contains a workflow example; it links to the Solutions Guide, the Usage Guide and the examples directory [C11]. The minimal examples below come from the official Claude Code documentation and the action's own docs.

Minimal workflow from the official Claude Code documentation (respond to `@claude` mentions) [C10]:

```yaml
name: Claude Code
on:
  issue_comment:
    types: [created]
  pull_request_review_comment:
    types: [created]
jobs:
  claude:
    if: contains(github.event.comment.body, '@claude')
    runs-on: ubuntu-latest
    permissions:
      contents: write
      pull-requests: write
      issues: write
      id-token: write
      actions: read
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1
      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
```

Automatic pull request review with a custom prompt, verbatim from the action's Solutions Guide (`docs/solutions.md`, "Automatic PR Code Review", "Basic Example (No Tracking)") [C11]:

```yaml
name: Claude Auto Review
on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      pull-requests: write
      id-token: write
    steps:
      - uses: actions/checkout@v6
        with:
          fetch-depth: 1

      - uses: anthropics/claude-code-action@v1
        with:
          anthropic_api_key: ${{ secrets.ANTHROPIC_API_KEY }}
          prompt: |
            REPO: ${{ github.repository }}
            PR NUMBER: ${{ github.event.pull_request.number }}

            Please review this pull request with a focus on:
            - Code quality and best practices
            - Potential bugs or issues
            - Security implications
            - Performance considerations

            Note: The PR branch is already checked out in the current working directory.

            Use `gh pr comment` for top-level feedback.
            Use `mcp__github_inline_comment__create_inline_comment` (with `confirmed: true`) to highlight specific code issues.
            Only post GitHub comments - don't submit review text as messages.

          claude_args: |
            --allowedTools "mcp__github_inline_comment__create_inline_comment,Bash(gh pr comment:*),Bash(gh pr diff:*),Bash(gh pr view:*)"
```

The Claude Code documentation also shows a plugin-based review: the `code-review@claude-code-plugins` plugin with `prompt: "/code-review:code-review --comment ${{ github.repository }}/pull/${{ github.event.pull_request.number }}"`, triggered on `pull_request` types `[opened, synchronize, ready_for_review, reopened]`, with permissions `contents: read`, `pull-requests: read`, `issues: read` and `id-token: write`. `--comment` makes Claude post on the pull request, and the `claude_args: '--allowedTools "mcp__github_inline_comment__create_inline_comment"'` line must stay, because the action starts the inline-comment server only when `--allowedTools` names it [C10]. Inference: this example posts comments with only `pull-requests: read` because comments are made with the Claude GitHub App token; grant `pull-requests: write` when you pass your own `github_token`.

Suggested NeonRadar variant (adapted, not verbatim): the Solutions Guide example above plus `ready_for_review` and `reopened` triggers, `if: github.event.pull_request.draft == false`, `timeout-minutes: 20`, a `concurrency` group per pull request with `cancel-in-progress: true`, `--max-turns` in `claude_args`, `actions/checkout@v7` (the current major, see `stack.md`), and a prompt that points Claude to `CLAUDE.md` and the project's review checklist (AML framing rules, no real names in synthetic allegations, Cypher safety). The docs recommend `--max-turns`, workflow timeouts and concurrency controls to manage cost [C10].

---

## Sources

All sources were checked on 2026-10-16.

Part A

- [A1] IBM/AMLSim repository page (licence, stars, forks, open issues and pull requests): https://github.com/IBM/AMLSim
- [A2] IBM/AMLSim git clone (master at 7338a4bcb1af9bcfea2201ad7daccfe2a4d569ca and all branches): https://github.com/IBM/AMLSim.git ; README https://github.com/IBM/AMLSim/blob/master/README.md ; requirements https://github.com/IBM/AMLSim/blob/master/requirements.txt ; build file https://github.com/IBM/AMLSim/blob/master/pom.xml ; parameter docs https://github.com/IBM/AMLSim/blob/master/paramFiles/README.md ; example patterns https://github.com/IBM/AMLSim/blob/master/paramFiles/typologies/alertPatterns.csv ; generator https://github.com/IBM/AMLSim/blob/master/scripts/transaction_graph_generator.py ; amounts https://github.com/IBM/AMLSim/blob/master/scripts/amlsim/rounded_amount.py and https://github.com/IBM/AMLSim/blob/master/src/main/java/amlsim/TargetedTransactionAmount.java ; schedules https://github.com/IBM/AMLSim/blob/master/src/main/java/amlsim/model/aml/AMLTypology.java ; cycle https://github.com/IBM/AMLSim/blob/master/src/main/java/amlsim/model/aml/CycleTypology.java ; output schema https://github.com/IBM/AMLSim/blob/master/paramFiles/1K/schema.json
- [A3] IBM/AMLSim issues: https://github.com/IBM/AMLSim/issues
- [A4] networkx 1.11 install and import test on Python 3.12 and 3.13 (local run): https://pypi.org/project/networkx/1.11/ ; Python 3.9 What's New, removal of `fractions.gcd()`: https://docs.python.org/3/whatsnew/3.9.html
- [A5] MASON project page: https://cs.gmu.edu/~eclab/projects/mason/
- [A6] MASON repository and LICENSE: https://github.com/eclab/mason ; https://github.com/eclab/mason/blob/master/LICENSE
- [A7] JSON-java LICENSE at tag 20180813 and licence history: https://github.com/stleary/JSON-java/blob/20180813/LICENSE ; https://github.com/stleary/JSON-java/commits/master/LICENSE
- [A8] arXiv 2306.16424 abstract page: https://arxiv.org/abs/2306.16424
- [A9] arXiv 2306.16424 v1: https://arxiv.org/pdf/2306.16424v1 ; https://arxiv.org/html/2306.16424v1
- [A10] arXiv 2306.16424 v3: https://arxiv.org/pdf/2306.16424v3 ; https://arxiv.org/html/2306.16424v3
- [A11] NeurIPS 2023 proceedings page: https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract.html
- [A12] NeurIPS 2023 supplementary material: https://papers.neurips.cc/paper_files/paper/2023/file/5f38404edff6f3f642d6fa5892479c42-Supplemental-Datasets_and_Benchmarks.pdf
- [A13] Kaggle dataset page (AMLworld): https://www.kaggle.com/datasets/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- [A14] Kaggle API metadata (AMLworld): https://www.kaggle.com/api/v1/datasets/view/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- [A15] Kaggle API file list (AMLworld): https://www.kaggle.com/api/v1/datasets/list/ealtman2019/ibm-transactions-for-anti-money-laundering-aml
- [A16] IBM/Multi-GNN (commit 252b0252afca109d1d216c411c59ff70753b25fc, 2024-02-13): https://github.com/IBM/Multi-GNN ; https://github.com/IBM/Multi-GNN/blob/main/format_kaggle_files.py
- [A17] CDLA-Sharing-1.0 text: https://cdla.dev/sharing-1-0/
- [A18] SAML-D record, Bournemouth University repository: https://eprints.bournemouth.ac.uk/40982/
- [A19] SAML-D paper (accepted manuscript): https://eprints.bournemouth.ac.uk/40982/1/Full_IEEE_Dataset_Conference_Paper%20%284%29.pdf
- [A20] Kaggle API metadata (SAML-D): https://www.kaggle.com/api/v1/datasets/view/berkanoztas/synthetic-transaction-monitoring-dataset-aml
- [A21] AMLgentex paper: https://arxiv.org/abs/2506.13989 ; https://arxiv.org/pdf/2506.13989v2
- [A22] AMLGentex repository (git clone; LICENSE, pyproject.toml, README.md): https://github.com/aidotse/AMLGentex
- [A23] AMLGentex on Hugging Face: https://huggingface.co/AMLGentex ; https://huggingface.co/api/datasets?author=AMLGentex&full=true
- [A24] Tide paper: https://arxiv.org/abs/2603.01863 ; https://arxiv.org/pdf/2603.01863v1
- [A25] Tide repository (git clone; LICENSE, pyproject.toml, requirements.txt, README.md): https://github.com/mntijn/Tide
- [A26] Tide reference datasets on Zenodo: https://zenodo.org/records/18804069
- [A27] AMLNet paper: https://arxiv.org/abs/2509.11595v1
- [A28] AMLNet dataset on Zenodo: https://zenodo.org/records/16736515 ; deprecated record https://zenodo.org/records/16482144
- [A29] SynthAML article and data: https://pmc.ncbi.nlm.nih.gov/articles/PMC10539331/ ; https://api.figshare.com/v2/collections/6504421/articles ; https://api.figshare.com/v2/articles/22396057 ; https://api.figshare.com/v2/articles/22396054
- [A30] PaySim repository (git clone): https://github.com/EdgarLopezPhD/PaySim
- [A31] Kaggle API metadata (PaySim1): https://www.kaggle.com/api/v1/datasets/view/ealaxi/paysim1
- [A32] FCA research note and PDF: https://www.fca.org.uk/publications/research-notes/research-note-synthetic-data-anti-money-laundering-project-report ; https://www.fca.org.uk/publication/research-notes/synthetic-data-anti-money-laundering-project-report.pdf ; secondary news report used only for orientation: https://www.crowdfundinsider.com/?p=273914
- [A33] Faker on PyPI and the inspected wheel: https://pypi.org/pypi/Faker/json ; https://files.pythonhosted.org/packages/81/ed/0d6d0d6467ae3d009fb82fb411867c7fcfeadbdd25602cab0d7a7963f400/faker-40.43.0-py3-none-any.whl ; project https://github.com/joke2k/faker
- [A34] mimesis on PyPI and the inspected wheel: https://pypi.org/pypi/mimesis/json ; https://files.pythonhosted.org/packages/89/a6/1031fb1c0f453abd96589e2126707a42bcc4d19ec1d705886df6188182df/mimesis-22.2.0-py3-none-any.whl ; project https://github.com/lk-geimfari/mimesis

Part B

- [B1] npm registry, vitepress: https://registry.npmjs.org/vitepress
- [B2] vuejs/vitepress repository (git clone): https://github.com/vuejs/vitepress ; i18n guide on main https://github.com/vuejs/vitepress/blob/main/docs/en/guide/i18n.md ; i18n guide at v1.6.4 https://github.com/vuejs/vitepress/blob/v1.6.4/docs/en/guide/i18n.md ; search reference https://github.com/vuejs/vitepress/blob/main/docs/en/reference/default-theme-search.md ; deploy guide https://github.com/vuejs/vitepress/blob/main/docs/en/guide/deploy.md ; docs site configuration https://github.com/vuejs/vitepress/blob/main/docs/.vitepress/config.ts ; native RTL commit https://github.com/vuejs/vitepress/commit/304207c497b66126f60d47be1e7bdf9689181aed ; rendered docs https://vitepress.dev/guide/i18n (content read from the source files above)
- [B3] minisearch 7.2.0 (npm tarball, `src/MiniSearch.ts`): https://registry.npmjs.org/minisearch ; https://registry.npmjs.org/minisearch/-/minisearch-7.2.0.tgz
- [B4] Latest release tags via `git ls-remote`: https://github.com/actions/checkout ; https://github.com/actions/configure-pages ; https://github.com/actions/upload-pages-artifact ; https://github.com/actions/deploy-pages ; https://github.com/withastro/action ; https://github.com/anthropics/claude-code-action
- [B5] PyPI, mkdocs: https://pypi.org/pypi/mkdocs/json ; https://pypi.org/pypi/mkdocs/2.0.dev6/json
- [B6] PyPI, mkdocs-material: https://pypi.org/pypi/mkdocs-material/json
- [B7] PyPI, zensical: https://pypi.org/pypi/zensical/json
- [B8] ProperDocs: https://pypi.org/pypi/properdocs/json ; https://github.com/properdocs/properdocs
- [B9] Material for MkDocs blog index: https://squidfunk.github.io/mkdocs-material/blog/
- [B10] Material for MkDocs blog, 2025-11-11: https://squidfunk.github.io/mkdocs-material/blog/2025/11/11/insiders-now-free-for-everyone/
- [B11] Material for MkDocs blog, 2026-02-18: https://squidfunk.github.io/mkdocs-material/blog/2026/02/18/mkdocs-2.0/
- [B12] zensical/zensical repository (git clone): https://github.com/zensical/zensical
- [B13] zensical/docs repository (git clone): https://github.com/zensical/docs ; language https://github.com/zensical/docs/blob/master/docs/setup/language.md ; search https://github.com/zensical/docs/blob/master/docs/setup/search.md ; plugins https://github.com/zensical/docs/blob/master/docs/compatibility/mkdocs/plugins.md ; publishing https://github.com/zensical/docs/blob/master/docs/publish-your-site.md ; language list https://github.com/zensical/docs/blob/master/includes/languages.html ; site https://zensical.org/ (the rendered docs could not be read by the fetch tool)
- [B14] npm registry, vue: https://registry.npmjs.org/vue
- [B15] npm registry: https://registry.npmjs.org/@astrojs/starlight ; https://registry.npmjs.org/astro ; https://registry.npmjs.org/@astrojs/vue
- [B16] withastro/starlight repository (git clone): https://github.com/withastro/starlight ; i18n guide https://github.com/withastro/starlight/blob/main/docs/src/content/docs/guides/i18n.mdx ; site search guide https://github.com/withastro/starlight/blob/main/docs/src/content/docs/guides/site-search.mdx ; Arabic interface strings https://github.com/withastro/starlight/blob/main/packages/starlight/src/translations/ar.json
- [B17] Pagefind multilingual search: https://pagefind.app/docs/multilingual/
- [B18] Astro, deploy to GitHub Pages: https://docs.astro.build/en/guides/deploy/github/

Part C

- [C1] neo4j/mcp repository (git clone of main and tag v1.6.0): https://github.com/neo4j/mcp ; README https://github.com/neo4j/mcp/blob/main/README.md ; changelog https://github.com/neo4j/mcp/blob/main/CHANGELOG.md ; configuration https://github.com/neo4j/mcp/blob/main/internal/config/config.go ; tool registration https://github.com/neo4j/mcp/blob/main/internal/server/tools_register.go ; startup checks https://github.com/neo4j/mcp/blob/main/internal/server/server.go ; CLI flags https://github.com/neo4j/mcp/blob/main/internal/cli/args.go ; Dockerfile https://github.com/neo4j/mcp/blob/main/Dockerfile ; Docker release workflow https://github.com/neo4j/mcp/blob/main/.github/workflows/docker-release.yml ; LICENSE https://github.com/neo4j/mcp/blob/main/LICENSE.txt ; NOTICE https://github.com/neo4j/mcp/blob/main/NOTICE.txt
- [C2] neo4j/mcp release v1.6.0 and its assets: https://github.com/neo4j/mcp/releases/tag/v1.6.0 ; https://github.com/neo4j/mcp/releases/expanded_assets/v1.6.0
- [C3] PyPI, neo4j-mcp-server (wheel inspected; `uvx neo4j-mcp-server@1.6.0 --version` and `--help` run locally): https://pypi.org/pypi/neo4j-mcp-server/json
- [C4] Docker Hub tags for neo4j/mcp: https://hub.docker.com/v2/repositories/neo4j/mcp/tags?page_size=10
- [C5] neo4j-contrib/mcp-neo4j repository (git clone): https://github.com/neo4j-contrib/mcp-neo4j ; top README https://github.com/neo4j-contrib/mcp-neo4j/blob/main/README.md ; Cypher server README https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-cypher/README.md ; Cypher server code https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-cypher/src/mcp_neo4j_cypher/server.py ; memory server README https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-memory/README.md ; memory server code https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-memory/src/mcp_neo4j_memory/neo4j_memory.py ; data modeling README https://github.com/neo4j-contrib/mcp-neo4j/blob/main/servers/mcp-neo4j-data-modeling/README.md
- [C6] PyPI: https://pypi.org/pypi/mcp-neo4j-cypher/json ; https://pypi.org/pypi/mcp-neo4j-memory/json ; https://pypi.org/pypi/mcp-neo4j-data-modeling/json ; https://pypi.org/pypi/mcp-neo4j-aura-manager/json
- [C7] Neo4j Operations Manual, introduction and edition comparison (role-based access control is Enterprise Edition only): https://raw.githubusercontent.com/neo4j/docs-operations/dev/modules/ROOT/pages/introduction.adoc ; rendered at https://neo4j.com/docs/operations-manual/current/introduction/
- [C8] Claude Code documentation map: https://code.claude.com/docs/en/claude_code_docs_map.md (redirected from https://docs.anthropic.com/en/docs/claude-code/claude_code_docs_map.md)
- [C9] Claude Code documentation, MCP: https://code.claude.com/docs/en/mcp.md
- [C10] Claude Code documentation, GitHub Actions: https://code.claude.com/docs/en/github-actions.md
- [C11] anthropics/claude-code-action repository (git clone; tags): https://github.com/anthropics/claude-code-action ; README https://github.com/anthropics/claude-code-action/blob/main/README.md ; Solutions Guide https://github.com/anthropics/claude-code-action/blob/main/docs/solutions.md ; Usage Guide https://github.com/anthropics/claude-code-action/blob/main/docs/usage.md ; security https://github.com/anthropics/claude-code-action/blob/main/docs/security.md ; setup https://github.com/anthropics/claude-code-action/blob/main/docs/setup.md ; example workflow https://github.com/anthropics/claude-code-action/blob/main/examples/claude.yml
