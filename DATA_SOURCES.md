# Data sources

> Draft, owned by the data steward (@robotat-com, `people.data_steward` in [docs/build/project.yaml](docs/build/project.yaml)). The data steward approves every licence statement here before it is final.

NeonRadar ships loaders, never data. The repository holds code and synthetic fixtures only; every public source below is fetched by a command you run yourself, into a local cache that is never committed. A database that merges sources is never published or committed. The licence fields that loaders follow are frozen in `contracts/datasets.yaml` (from milestone M1.7a).

| Dataset slug | Source | Licence | Commercial use | Attribution | Phase 1 use |
|---|---|---|---|---|---|
| `gb_companies_house` | UK Companies House REST API | Register data is made available under the Companies Act 2006 and approvals under section 47 of the Copyright, Designs and Patents Act 1988, with no Companies House rules on reuse; Companies House's own material is under the Open Government Licence v3.0, which does not cover personal data, so whoever loads officers and PSCs becomes a UK GDPR controller | Yes | "Contains public sector information licensed under the Open Government Licence v3.0." plus "Source: Companies House" | Spike with one company number, output in cache only |
| `gleif_lei` | GLEIF API and Golden Copy | CC0 1.0; GLEIF's terms forbid using its logo or implying endorsement, with liquidated damages of CHF 100,000 per breach | Yes | Not required; courtesy line in `contracts/datasets.yaml` | Spike with one LEI and its parents |
| `icij_offshore_leaks` | ICIJ Offshore Leaks Database (`full-oldb.LATEST.zip`) | ODbL 1.0 (database), CC BY-SA 3.0 (contents) | Yes, with citation. A publicly used derived database must be ODbL and offered in machine-readable form (clause 4.6); produced works such as screenshots and reports need a notice that the content came from the database under ODbL (clause 4.3); internal use is not public use | "Always cite the International Consortium of Investigative Journalists when using this data." plus the ODbL notices | Spike reading a slice, cache outside the repository |
| `opensanctions_default` | OpenSanctions bulk data | CC BY-NC 4.0; "Any use inside a for-profit business requires a data license." | Licence required | No official text; proposed wording in `contracts/datasets.yaml`, following CC BY-NC 4.0 section 3(a)(1) | Only if `access.opensanctions` in `docs/build/project.yaml` is `evaluation`, `licensed` or `exempt` (currently `none`, so not used) |
| `nr_synthetic` | NeonRadar generator | Apache-2.0 (our own output) | Yes | None | Fixtures and the walking skeleton |

Sources and reasoning for each row are in [docs/research/2026-10-16/sources-ch-gleif.md](docs/research/2026-10-16/sources-ch-gleif.md) and [docs/research/2026-10-16/sources-opensanctions-ftm-icij.md](docs/research/2026-10-16/sources-opensanctions-ftm-icij.md), summarised in [docs/build/PHASE-1.md](docs/build/PHASE-1.md) section 3.3.
