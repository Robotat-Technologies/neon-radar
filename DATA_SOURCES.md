# Data sources

> Draft, owned by the data steward (@robotat-com, `people.data_steward` in [docs/build/project.yaml](docs/build/project.yaml)). The data steward approves every licence statement here before it is final (Gate 1 check GC-17). This page is not legal advice.

NeonRadar ships loaders, never data. The repository holds code and synthetic fixtures only; every public source below is fetched by a command you run yourself, into a local cache (`data/cache/`) that is never committed. The decision and its reasons are in [ADR-0006](docs/decisions/0006-data-licensing.md).

- **Licence fields are machine-readable.** Each dataset's licence, attribution text, commercial use, redistribution policy, personal data flag and access rule live in [contracts/datasets.yaml](contracts/datasets.yaml), part of the C1 record contract, which freezes at Gate 1. Loaders follow them.
- **Never publish a merged database.** A database that combines sources is never published or committed. In particular, in the project's reading, ICIJ data (ODbL, share-alike) and OpenSanctions data (CC BY-NC) cannot both be honoured by one published database.
- **Personal data is your responsibility.** Many company officers, persons with significant control and ICIJ officers, and all OpenSanctions persons, are real people. NeonRadar's position is that whoever loads them for their own purposes is normally a controller under UK or EU data protection law and needs their own lawful basis; whether that holds in a given setting is for that user to establish. Spike output is deleted after `access.spike_cache_days` days (currently 7).
- **Attribution travels with the data.** Wherever data from a source appears (the interface, exports, screenshots, reports), show that source's attribution text below.

## Summary

| Dataset slug | Source | Licence | Commercial use | Attribution | Phase 1 use |
|---|---|---|---|---|---|
| `gb_companies_house` | UK Companies House REST API | Register data is made available under the Companies Act 2006 and approvals under section 47 of the Copyright, Designs and Patents Act 1988, with no Companies House rules on reuse; Companies House's own material is under the Open Government Licence v3.0, which does not cover personal data, so, in the project's reading, whoever loads officers and PSCs for their own purposes is normally a UK GDPR controller | Yes | "Contains public sector information licensed under the Open Government Licence v3.0." plus "Source: Companies House" | Spike with one company number, output in cache only |
| `gleif_lei` | GLEIF API and Golden Copy | CC0 1.0; GLEIF's terms forbid using its logo or implying endorsement, with liquidated damages of CHF 100,000 per breach | Yes | Not required; courtesy line below | Spike with one LEI and its parents |
| `icij_offshore_leaks` | ICIJ Offshore Leaks Database (`full-oldb.LATEST.zip`) | ODbL 1.0 (database), CC BY-SA 3.0 (contents) | Yes, with citation. A publicly used derived database must be ODbL and offered in machine-readable form (clause 4.6); produced works such as screenshots and reports need a notice that the content came from the database under ODbL (clause 4.3); internal use is not public use | "Always cite the International Consortium of Investigative Journalists when using this data." plus the ODbL notices | Spike reading a slice over byte ranges ([report](docs/data/spikes/icij.md), go with changes); output, and an archive copy only if ranges are refused, in `data/cache/spikes/icij/` (gitignored) |
| `opensanctions_default` | OpenSanctions bulk data | CC BY-NC 4.0; "Any use inside a for-profit business requires a data license." | Licence required | No official text; NeonRadar's proposed wording below, following CC BY-NC 4.0 section 3(a)(1) | Only if `access.opensanctions` in `docs/build/project.yaml` is `evaluation`, `licensed` or `exempt` (currently `none`, so not used; spike [blocked on licence decision](docs/data/spikes/opensanctions.md)) |
| `nr_synthetic` | NeonRadar generator | Apache-2.0 (our own output) | Yes | None | Fixtures and the walking skeleton |
| `gb_fcdo_sanctions` | UK Sanctions List (FCDO) | Open Government Licence v3.0, which does not cover personal data | Yes | "Contains public sector information licensed under the Open Government Licence v3.0. Source: UK Sanctions List, Foreign, Commonwealth and Development Office. Converted to FollowTheMoney records by NeonRadar." | None in Phase 1. Phase 2 loader (M2.6a), run only when `access.sanctions_lists` includes it |
| `us_ofac_sdn` | OFAC Specially Designated Nationals and Blocked Persons List | CC0 1.0 (public domain) | Yes | "Source: US Department of the Treasury, Office of Foreign Assets Control, Specially Designated Nationals and Blocked Persons List (public domain). NeonRadar is not affiliated with OFAC. Converted to FollowTheMoney records by NeonRadar." | None in Phase 1. Phase 2 loader (M2.6b), run only when `access.sanctions_lists` includes it |
| `un_sc_sanctions` | United Nations Security Council Consolidated List | UN website terms of use; no licence for the list found | Only with the UN's written permission | "Source: United Nations Security Council Consolidated List. Converted to FollowTheMoney records by NeonRadar." | None in Phase 1. Phase 2 loader (M2.6c), tested on synthetic data; run only when `access.sanctions_lists` includes it, which needs the UN's written permission |
| `eu_fsf` | EU Financial Sanctions Files (consolidated list) | The Commission's reuse policy, Decision 2011/833/EU (not CC BY 4.0) | Yes, with acknowledgement and without distorting the meaning | "Source: European Commission, Financial Sanctions Files, reused under the Commission's reuse policy (Decision 2011/833/EU). Only the information published in the Official Journal of the EU is deemed authentic. Converted to FollowTheMoney records by NeonRadar." | None in Phase 1. Phase 2 loader (M2.6d), run only when `access.sanctions_lists` includes it |
| `gb_parliament_members` | UK Parliament members and ministers (Members API) | Open Parliament Licence v3.0, which does not cover personal data | Yes | "Contains Parliamentary information licensed under the Open Parliament Licence v3.0. Converted to FollowTheMoney records by NeonRadar." | None in Phase 1. Optional Phase 2 loader (M2.6e), run only when `access.pep_sources` includes it |

## UK Companies House (`gb_companies_house`)

- **Publisher:** Companies House, through the Public Data REST API (<https://developer.company-information.service.gov.uk/>). Each user needs their own API key, kept in `.env` as `CH_API_KEY` and never committed.
- **Licence:** register data is made available under the Companies Act 2006 and approvals under section 47 of the Copyright, Designs and Patents Act 1988; Companies House "imposes no rules or requirements on how the information on the public register is used" (its GOV.UK page [Public task, copyright and Crown copyright](https://www.gov.uk/government/publications/companies-house-accreditation-to-information-fair-traders-scheme/public-task-copyright-and-crown-copyright), read on 21 October 2026; a Companies House developer-forum post of 4 November 2021 says the same). Its own material is Crown copyright under the [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
- **Attribution text:**

  > Contains public sector information licensed under the Open Government Licence v3.0. Source: Companies House.

- **Personal data:** most officers and persons with significant control are real people (some are companies). The Open Government Licence "does not cover: personal data in the Information", and Companies House says that organisations which reuse register data "become controllers of your personal data". The API shows only the month and year of birth and a correspondence address. Never try to reconstruct residential addresses or full dates of birth, and prefer re-fetching to long-term caching, so that removals made at Companies House flow through.

## GLEIF Global LEI Index (`gleif_lei`)

- **Publisher:** the Global Legal Entity Identifier Foundation (<https://www.gleif.org/>), through its API and Golden Copy files.
- **Licence:** [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/). No attribution is required.
- **Courtesy line** (NeonRadar's own, not required by GLEIF):

  > LEI data from the GLEIF Global LEI Index, available under CC0 1.0. NeonRadar is not affiliated with or endorsed by GLEIF.

- **Conditions:** GLEIF's terms forbid using its trademark or logo without permission and creating the impression that a product is provided, supported or authorised by GLEIF; breaches can incur liquidated damages of CHF 100,000 per case.
- **Personal data:** none (legal entities only).

## ICIJ Offshore Leaks Database (`icij_offshore_leaks`)

- **Publisher:** the International Consortium of Investigative Journalists (<https://offshoreleaks.icij.org/>). The database is built from leaked files. Load it from ICIJ directly: the copy that OpenSanctions republishes is under CC BY-NC 4.0.
- **Licence:** "The ICIJ Offshore Leaks Database is licensed under the Open Database License and its contents under Creative Commons Attribution-ShareAlike license" ([ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/), [CC BY-SA 3.0](https://creativecommons.org/licenses/by-sa/3.0/)). Commercial use is allowed.
- **Attribution text:**

  > Always cite the International Consortium of Investigative Journalists when using this data.

- **ODbL obligations:**
  - A produced work (a screenshot, chart or report) that shows ICIJ content carries a notice that the content came from the ICIJ Offshore Leaks Database and is available under ODbL 1.0 (clause 4.3).
  - A derivative database (for example a Neo4j graph built from ICIJ data) that you use publicly must be offered under ODbL (clause 4.4), together with a machine-readable copy of the database or of your changes (clause 4.6).
  - Clause 4.6 also covers a produced work from a derivative database that you use publicly: if you publish, for example, a screenshot of a graph built with ICIJ data, offer its recipients that machine-readable copy too. How far this reaches is a question for the data steward.
  - "Publicly" means to people other than you or those under your control, so internal use is not public use. The repository ships loaders only, so it creates no ODbL obligation itself.
- **Disclaimer:** show ICIJ's disclaimer with the data. ICIJ's FAQ says: "We do not intend to suggest or imply that any individuals, companies or other entities included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted improperly."
- **Personal data:** officers and intermediaries include real people; in NeonRadar's position, whoever loads them for their own purposes is normally a controller.
- **Never** publish a database that merges ICIJ data with OpenSanctions data.

## OpenSanctions (`opensanctions_default`)

- **Publisher:** OpenSanctions Datenbanken GmbH (<https://www.opensanctions.org/>).
- **Licence:** [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/). OpenSanctions states: "Any use inside a for-profit business requires a data license." Compliance screening counts as commercial use.
- **NeonRadar's decision:** `access.opensanctions` is `none`, so the project uses synthetic fixtures only and the loader stays gated (see the access decision below).
- **Free access:** OpenSanctions gives free API keys to "Journalists (staff or freelance) publishing findings in the public interest", which "includes journalists at commercial media organizations"; to advocacy groups and nonprofits working to improve democratic governance or to expose corruption and financial crime; to academic researchers with an institutional affiliation; and to public institutions of Ukraine, Georgia and Moldova. For genuinely non-commercial use it says: "If your use is genuinely non-commercial, the bulk data above is yours to work with." Every other commercial user needs their own data licence.
- **Attribution text** (NeonRadar's proposal: OpenSanctions publishes no official wording, so this follows CC BY-NC 4.0 section 3(a)(1)):

  > Contains data from OpenSanctions (https://www.opensanctions.org), (c) OpenSanctions Datenbanken GmbH, licensed under CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/), provided without warranty. Converted and filtered by NeonRadar.

- **Redistribution:** never. No OpenSanctions row, and nothing derived from one, is ever committed.
- **Personal data:** the data includes people tagged with crime-related topics. Handle it with particular care. NeonRadar's data steward decides how the project's loader treats these topics; if you load them, you, as controller, decide whether Article 10 of the UK or EU GDPR (personal data relating to criminal convictions and offences) applies to your processing ([ADR-0006](docs/decisions/0006-data-licensing.md)).

### Access decision and the spike command

OpenSanctions data is licensed under CC BY-NC 4.0, and OpenSanctions states: "Any use inside a for-profit business requires a data license." The reasoning and sources are in [docs/research/2026-10-16/sources-opensanctions-ftm-icij.md](docs/research/2026-10-16/sources-opensanctions-ftm-icij.md) section A.2. NeonRadar therefore ships the OpenSanctions loader code but never OpenSanctions data, and the loader runs only when the organisation running it has decided how it may use the data.

That decision is `access.opensanctions` in [docs/build/project.yaml](docs/build/project.yaml). The data steward and the project lead make it ([docs/build/PHASE-1.md](docs/build/PHASE-1.md) section 1.2) and file the request to OpenSanctions and its written answer in `docs/data/licences/opensanctions.md`. `uv run neonradar spike opensanctions` follows it:

| `access.opensanctions` | When it applies | What the command does |
|---|---|---|
| `none` (the default, and the current value) | No decision recorded | Exits with code 3 and "OpenSanctions use inside a company needs a data licence; see DATA_SOURCES.md". It sends no request. Development and tests use synthetic fixtures only. |
| `evaluation` | OpenSanctions has confirmed in writing that the organisation may evaluate the data. The data steward files that answer in `docs/data/licences/opensanctions.md` and adds, at the start of a line, `confirmed: <YYYY-MM-DD> <who>` (for example `confirmed: 2026-11-02 @robotat-com`). The command refuses while that line is missing. | Reads the collection's `index.json`, streams the first rows of `entities.ftm.json` (1,000 by default), maps them to C1 in memory and prints counts. It writes nothing to disk. |
| `licensed` | The organisation holds an OpenSanctions data licence | As `evaluation`, and it also writes the C1 records and their manifest to `data/cache/spikes/opensanctions/` (gitignored), to be deleted after `access.spike_cache_days`. |
| `exempt` | The organisation running NeonRadar itself qualifies for OpenSanctions' free programme: public-interest journalists, advocacy groups and nonprofits working on democratic governance or exposing corruption and financial crime, affiliated academics, or public institutions of Ukraine, Georgia and Moldova. Never a company team. | As `evaluation`: it streams, counts and writes nothing. |

A missing file, a missing key or any other value counts as `none`. Under every route, no OpenSanctions row is ever committed (guardrail G2), OpenSanctions data is never redistributed (`redistribution: never` in `contracts/datasets.yaml`), and a database that merges it with other sources is never published (G7). Every commercial user of NeonRadar needs their own OpenSanctions licence. The spike report is [docs/data/spikes/opensanctions.md](docs/data/spikes/opensanctions.md).

## NeonRadar synthetic data (`nr_synthetic`)

- **Publisher:** NeonRadar's own generator. Licence: Apache-2.0. No attribution needed.
- **No personal data:** every company, person, address, account and payment is generated. Synthetic names are checked against a denylist of real prominent family names. Company names committed to the repository are checked against the Companies House search API when a key is available; without a key, they are checked against the public Companies House search or listed in the pull request for the data steward to check.
- **Synthetic laundering scenarios** run only among synthetic entities (ids starting `syn-`); real entities may receive synthetic background activity only.

## Official sanctions lists and UK Parliament data (Phase 2)

Added with the record contract C1 1.1.0 (`docs/build/PHASE-2.md` 5.1). The licence fields, attribution lines and notes in [contracts/datasets.yaml](contracts/datasets.yaml) are the machine-readable form of this section; the quotations come from [docs/research/2026-10-18/sanctions-peps.md](docs/research/2026-10-18/sanctions-peps.md), checked on 18 October 2026. The data steward approves each licence field and attribution line in the review of M2.1a. Whether a list is loaded is decided by `access.sanctions_lists` and `access.pep_sources` in [docs/build/project.yaml](docs/build/project.yaml) and by the profile, never by the dataset's `status`. Every list holds data about real people: whoever loads it is a controller under UK GDPR.

### UK Sanctions List (`gb_fcdo_sanctions`)

- **Title and publisher:** UK Sanctions List, Foreign, Commonwealth and Development Office (FCDO) (<https://www.gov.uk/government/publications/the-uk-sanctions-list>). It is the only UK sanctions list since 28 January 2026.
- **Licence:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). Commercial use is allowed.
- **Attribution text:**

  > Contains public sector information licensed under the Open Government Licence v3.0. Source: UK Sanctions List, Foreign, Commonwealth and Development Office. Converted to FollowTheMoney records by NeonRadar.

- **Personal data:** the Open Government Licence does not cover "personal data in the Information": whoever loads it is a controller under UK GDPR.
- **No endorsement:** no endorsement by the FCDO is implied.

### OFAC SDN List (`us_ofac_sdn`)

- **Title and publisher:** Specially Designated Nationals and Blocked Persons List, US Department of the Treasury, Office of Foreign Assets Control (<https://ofac.treasury.gov/sanctions-list-service>).
- **Licence:** OFAC's data catalogue marks the list files [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) ("No restrictions on public access"); the data.gov record says "This data is in the public domain and may be used without restriction." Commercial use is allowed.
- **Attribution text:**

  > Source: US Department of the Treasury, Office of Foreign Assets Control, Specially Designated Nationals and Blocked Persons List (public domain). NeonRadar is not affiliated with OFAC. Converted to FollowTheMoney records by NeonRadar.

- **Personal data:** public-domain status does not remove data protection duties: whoever loads it is a controller under UK GDPR.
- **Note:** OFAC does not confirm matches; NeonRadar output is not a screening result.

### UN Security Council Consolidated List (`un_sc_sanctions`)

- **Title and publisher:** United Nations Security Council Consolidated List, United Nations Security Council (<https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list>).
- **Licence:** the [UN website terms of use](https://www.un.org/en/about-us/terms-of-use) allow download "for the User's personal, non-commercial use", and no licence for the list was found. NeonRadar loads it only with written permission from sc-sanctionslists@un.org, filed in `docs/data/licences/un_sc_sanctions.md` (`commercial_use: permission-required`). Until then it is not in `access.sanctions_lists`, and the UK list carries UN listings with their UN reference numbers.
- **Attribution text:**

  > Source: United Nations Security Council Consolidated List. Converted to FollowTheMoney records by NeonRadar.

- **Personal data:** whoever loads it is a controller under UK GDPR.

### EU Financial Sanctions Files (`eu_fsf`)

- **Title and publisher:** EU Financial Sanctions Files (consolidated list), European Commission (<https://webgate.ec.europa.eu/fsd/fsf/public/rss>).
- **Licence:** the Commission's reuse policy, [Decision 2011/833/EU](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX:32011D0833), which allows reuse "for commercial or non-commercial purposes", with acknowledgement of the source and without distorting the meaning. The registry records it as `LicenseRef-EC-Reuse-Decision-2011-833`, not CC BY 4.0: no licence statement attached to the files themselves was found.
- **Attribution text:**

  > Source: European Commission, Financial Sanctions Files, reused under the Commission's reuse policy (Decision 2011/833/EU). Only the information published in the Official Journal of the EU is deemed authentic. Converted to FollowTheMoney records by NeonRadar.

- **Personal data:** whoever loads it is a controller under UK GDPR.
- **Note:** the public download token can be revoked, so it is configurable (`NR_EU_FSF_TOKEN`), and stored URLs never include it.

### UK Parliament members and ministers (`gb_parliament_members`)

- **Title and publisher:** UK Parliament members and ministers, UK Parliament, through the Members API (<https://members-api.parliament.uk/>). An optional source of politically exposed person flags (M2.6e).
- **Licence:** [Open Parliament Licence v3.0](https://www.parliament.uk/site-information/copyright-parliament/open-parliament-licence/). Commercial use is allowed. Photographs are outside the licence and are not loaded.
- **Attribution text:**

  > Contains Parliamentary information licensed under the Open Parliament Licence v3.0. Converted to FollowTheMoney records by NeonRadar.

- **Personal data:** the Open Parliament Licence does not cover personal data: whoever loads it is a controller under UK GDPR.
- **No endorsement:** no endorsement by Parliament is implied.

## Sources

Sources and reasoning for each section are in [docs/research/2026-10-16/sources-ch-gleif.md](docs/research/2026-10-16/sources-ch-gleif.md) and [docs/research/2026-10-16/sources-opensanctions-ftm-icij.md](docs/research/2026-10-16/sources-opensanctions-ftm-icij.md), summarised in [docs/build/PHASE-1.md](docs/build/PHASE-1.md) section 3.3. The licence terms of Companies House, the Open Government Licence, GLEIF, ICIJ and OpenSanctions quoted above were re-checked on 21 October 2026 (the ODbL and CC BY-NC clause readings come from the research note); the links are in [ADR-0006](docs/decisions/0006-data-licensing.md).
