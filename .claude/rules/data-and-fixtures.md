---
paths:
  - "data/**"
  - "**/fixtures/**"
  - "ingest/**"
  - "contracts/examples/**"
---
# Data and fixture rules
- Committed fixtures are synthetic: every record id starts with `syn-`, dataset
  `nr_synthetic`, `nr.synthetic: true`.
- Never commit API responses, downloads or samples from real sources. Spike and loader
  output goes to data/cache/ (gitignored).
- Synthetic names: Faker (ar_SA, ru_RU, en_GB) through the denylist filter; company names
  from neutral word lists plus a legal form; no real brands or listed companies.
- Synthetic accounts: `NRSYN` plus 10 digits; never set iban or bic.
- Ground-truth labels never go into records or the graph; they go to separate label files.
- Respect each source's rate limit and licence (contracts/datasets.yaml).
