# 0006. Data licensing

- **Status:** proposed
- **Date:** 2026-10-21
- **Deciders:** @robotat-com (data steward, project lead)

## Context

NeonRadar builds its ownership graph from public sources with different licences, and adds synthetic activity of its own (`docs/build/PHASE-1.md` sections 3.3 and 4.1). The repository is licensed under Apache-2.0 and will be public from launch. Two guardrails apply: the repository holds code and synthetic fixtures only (G2), and licences decide what a loader may do (G7). The licence fields that loaders follow are in [`contracts/datasets.yaml`](../../contracts/datasets.yaml), part of the C1 record contract that freezes at Gate 1.

The sources and their licences (`PHASE-1.md` 3.3; research of 16 October 2026, re-checked on 21 October 2026 where the publisher's site allowed it, see Sources):

| Dataset slug | Source | Licence | Commercial use | Attribution | Phase 1 use |
|---|---|---|---|---|---|
| `gb_companies_house` | UK Companies House REST API | Register data is made available under the Companies Act 2006 and approvals under section 47 of the Copyright, Designs and Patents Act 1988, with no Companies House rules on reuse; Companies House's own material is under the Open Government Licence v3.0, which does not cover personal data | Yes | "Contains public sector information licensed under the Open Government Licence v3.0." plus "Source: Companies House" | Spike with one company number, output in cache only |
| `gleif_lei` | GLEIF API and Golden Copy | CC0 1.0; GLEIF's terms forbid using its logo or implying endorsement, with liquidated damages of CHF 100,000 per breach | Yes | Not required; courtesy line in `contracts/datasets.yaml` | Spike with one LEI and its parents |
| `icij_offshore_leaks` | ICIJ Offshore Leaks Database (`full-oldb.LATEST.zip`) | ODbL 1.0 (database), CC BY-SA 3.0 (contents) | Yes, with citation | "Always cite the International Consortium of Investigative Journalists when using this data." plus the ODbL notices | Spike reading a slice, cache outside the repository |
| `opensanctions_default` | OpenSanctions bulk data | CC BY-NC 4.0; "Any use inside a for-profit business requires a data license." | Licence required | No official text; proposed wording in `contracts/datasets.yaml`, following CC BY-NC 4.0 section 3(a)(1) | Only if `access.opensanctions` allows it |
| `nr_synthetic` | NeonRadar generator | Apache-2.0 (our own output) | Yes | None | Fixtures and the walking skeleton |

Three facts shape the decision:

- **OpenSanctions is not free for companies.** Its exemption page says: "Any use inside a for-profit business requires a data license." Free API keys go only to "Journalists (staff or freelance) publishing findings in the public interest", which "includes journalists at commercial media organizations"; advocacy groups and nonprofits working to improve democratic governance or to expose corruption and financial crime; academic researchers with an institutional affiliation; and public institutions of Ukraine, Georgia and Moldova. Its licensing page invites businesses to "integrate and evaluate our data before signing a license". The operator recorded `access.opensanctions: none` in `docs/build/project.yaml`.
- **ICIJ data is share-alike.** The database is under ODbL 1.0 and its contents under CC BY-SA. A produced work (a screenshot, a chart, a report) needs a notice that the content came from the database under ODbL (clause 4.3). A derivative database that is used publicly must be offered under ODbL (clause 4.4), together with a machine-readable copy of the database or of the changes (clause 4.6). Clause 4.6 also covers a produced work from a derivative database that is used publicly: whoever publishes, for example, a screenshot of a graph built with ICIJ data must offer its recipients that machine-readable copy too. "Publicly" means to persons other than the user or those under the user's control, so internal use is not public use.
- **Much of the data is about people.** Companies House officers and persons with significant control, ICIJ officers and OpenSanctions persons who are natural persons are personal data under Article 4(1) of the UK GDPR and of the EU GDPR [uk_gdpr] [eu_gdpr_2016]; some officers and persons with significant control are companies. Companies House says that organisations which reuse register data "become controllers of your personal data"; the Open Government Licence "does not cover: personal data in the Information". OpenSanctions also tags people with crime-related topics, and both GDPR texts restrict the processing of "personal data relating to criminal convictions and offences" (Article 10) [uk_gdpr] [eu_gdpr_2016].

## Options considered

1. **What the repository ships.**
   - **Data or derived fixtures from public sources:** a quicker start for users, but it would put personal data and other licensors' terms into an Apache-2.0 repository, and OpenSanctions-derived rows cannot be relicensed under Apache-2.0: CC BY-NC 4.0 does not allow it, and OpenSanctions' licensed customers may pass data on only under a reseller licence.
   - **Loaders only:** each user fetches the data with a command they run, into a local cache that is never committed. Users need network access and time for the first load.
2. **OpenSanctions route** (`PHASE-1.md` 1.2).
   - **`none`:** synthetic fixtures only; the loader stays gated. No licence risk; no real sanctions data in development.
   - **`evaluation`:** a 1,000-entity stream for the spike, only after OpenSanctions confirms in writing.
   - **`licensed`:** a paid data licence for the organisation running NeonRadar.
   - **`exempt`:** only if the organisation itself qualifies for OpenSanctions' free programme; never for the for-profit team running this project.
3. **Merged databases.**
   - **Publish a combined graph** (for example a Neo4j dump of every source): convenient, but in the project's reading ODbL share-alike and CC BY-NC cannot both be met by one published database, and every source's attribution and personal data duties would travel with it.
   - **Never publish a database that merges sources:** each user builds their own graph locally.

## Decision

We will:

- **Ship loaders, never data.** The repository holds code and synthetic fixtures only. Every public source is fetched by an explicit loader or spike command into `data/cache/` (gitignored). No bulk data, no API responses about real people, no personal data and no row derived from OpenSanctions is ever committed (G2).
- **Follow `contracts/datasets.yaml`.** Each loader reads its dataset's licence, attribution, `commercial_use`, `redistribution` and `access` fields, and shows the attribution text wherever the data appears (the data sources page, exports, screenshots).
- **Keep OpenSanctions at `none`** until the data steward records another route in `access.opensanctions`, with the request and OpenSanctions' written answer filed in `docs/data/licences/opensanctions.md`. The loader and its documentation say that every commercial user needs their own data licence, and point journalists, qualifying nonprofits (democratic governance, exposing corruption and financial crime), academics and public institutions of Ukraine, Georgia and Moldova to OpenSanctions' free-key programme.
- **Meet the ODbL obligations for ICIJ data.** NeonRadar's documentation tells users that a produced work showing ICIJ content carries a notice that the content came from the ICIJ Offshore Leaks Database under ODbL 1.0, and that a derivative database used publicly must be offered under ODbL with a machine-readable copy. Clause 4.6 extends that offer to a produced work from a derivative database used publicly, such as a published screenshot of a graph built with ICIJ data; how far this reaches is a question for the data steward. The interface shows ICIJ's disclaimer next to ICIJ data and the citation "Always cite the International Consortium of Investigative Journalists when using this data."
- **Never imply GLEIF's endorsement** and never use its logo.
- **Never publish or commit a database that merges sources**, in particular one that merges ICIJ data with OpenSanctions data.
- **Treat officers, persons with significant control, ICIJ officers and OpenSanctions persons who are natural persons as personal data.** NeonRadar's position is that whoever loads them for their own purposes is normally a controller under UK or EU data protection law [uk_gdpr] [eu_gdpr_2016] and needs their own lawful basis; whether that holds in a given setting is for that user to establish. NeonRadar's documentation says so, and the real data notice says that "whoever loads them is responsible for handling it lawfully". OpenSanctions crime-related topics need particular care. Whether Article 10 applies to those topics is for the data steward to decide; until then NeonRadar shows no source topics next to entities other than the sanctioned, PEP and RCA flags (`docs/wording.md`).
- **Keep personal data no longer than needed.** Spike output, which holds personal data from Companies House and ICIJ, is deleted after `access.spike_cache_days` days (currently 7). Loaders never try to reconstruct residential addresses or full dates of birth, and prefer re-fetching to long-term caching, so that removals at the source flow through.

## Consequences

- **Easier:** the repository stays Apache-2.0 with no third-party data inside it, and contributors can work entirely with synthetic fixtures. No licence question blocks development.
- **Harder:** every user needs network access and patience for the first load, and commercial users of the OpenSanctions loader must get their own licence. The public demo runs on synthetic data only.
- **Follow-up work:**
  - The data steward approves the licence fields in `contracts/datasets.yaml` and the statements in `DATA_SOURCES.md` before the freeze (GC-17).
  - M1.8d records the OpenSanctions request and answer, or a spike report that says "blocked on licence decision".
  - Phase 2 loaders print each dataset's attribution and enforce `access` and `redistribution`; the interface's data sources page shows the licences and attribution texts.
  - The data steward decides whether OpenSanctions crime topics fall under Article 10 and whether the current consolidated EU text of the GDPR changes Articles 4 or 10 (the build could read only the text as adopted in 2016).
  - The licence of the GDS plugin jar, raised in [ADR-0002](0002-neo4j-5-26-lts.md), is a software question and stays outside this ADR.
- **Not legal advice.** These readings come from the licensors' own words and the UK and EU GDPR texts. Open questions for the data steward: Article 10 and OpenSanctions crime topics; the consolidated EU text; clause 4.6 for published screenshots; the free-key status of journalists at commercial media. The deciders confirm the readings and may ask for legal advice before launch.

## Sources

- `docs/build/PHASE-1.md`: sections 1.2 (OpenSanctions route), 2.1 (guardrails G2, G3, G7), 3.3 (licence summary) and 5.1 (`contracts/datasets.yaml`).
- `docs/research/2026-10-16/sources-ch-gleif.md`: A4 (Companies House licence, personal data, residential addresses), B5 (GLEIF licence) and the licence summary.
- `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md`: A.2 (OpenSanctions licensing), A.4 (topics, including the crime-related ones), C.2 (ICIJ licence and what ODbL means for a derived graph, with the ODbL 1.0 text at https://opendatacommons.org/licenses/odbl/1-0/) and C.3 (ICIJ disclaimer).
- Re-checked on 2026-10-21:
  - Companies House personal information charter: https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter
  - Companies House public task and Crown copyright: https://www.gov.uk/government/publications/companies-house-accreditation-to-information-fair-traders-scheme/public-task-copyright-and-crown-copyright
  - Open Government Licence v3.0: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/
  - GLEIF LEI data terms of use: https://www.gleif.org/en/meta/lei-data-terms-of-use/
  - ICIJ Offshore Leaks Database, download page and FAQ: https://offshoreleaks.icij.org/pages/database and https://offshoreleaks.icij.org/pages/faq
  - OpenSanctions free and non-commercial use: https://www.opensanctions.org/docs/commercial/exemption/ ; licensing: https://www.opensanctions.org/licensing/
- [uk_gdpr] The National Archives (legislation.gov.uk), *United Kingdom General Data Protection Regulation*, Articles 4 and 10 (read 2026-10-21). <https://www.legislation.gov.uk/eur/2016/679/contents>
- [eu_gdpr_2016] European Parliament and Council, *Regulation (EU) 2016/679*, Articles 4 and 10 in the text as adopted, read on legislation.gov.uk on 2026-10-21 (<https://www.legislation.gov.uk/eur/2016/679/article/4/adopted>); EUR-Lex (<https://eur-lex.europa.eu/eli/reg/2016/679/oj>) answered with a bot challenge.
