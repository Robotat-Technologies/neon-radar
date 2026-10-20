# NeonRadar phase 1: data source verification (OpenSanctions, FollowTheMoney, ICIJ Offshore Leaks)

- Date checked: 2026-10-16 (every source in the Sources list was read on this date unless noted)
- Scope: loader inputs for an Apache-2.0, local-first AML knowledge graph (Python 3.12+, Neo4j) that uses FollowTheMoney (FtM) entities as its intermediate format and ships loader code plus tiny fixtures only.
- Citation style: `[S12]` refers to the numbered Sources list at the end (URL plus date checked). "UNVERIFIED" means I could not confirm the fact from an official source today.
- Not legal advice. Licence readings below quote the licensor's own words and flag where interpretation is involved.

## 0. Findings that change the plan

1. **OpenSanctions data needs a licence for use inside a company.** The data is CC BY-NC 4.0 and OpenSanctions states: "Any use inside a for-profit business requires a data license." [S18]. There is no published exemption for open-source projects; free API keys exist only for journalists, public-interest nonprofits, affiliated academics and public institutions of Ukraine, Georgia and Moldova [S18]. The licensing page does invite businesses to "integrate and evaluate our data before signing a license" [S17], which covers a short evaluation, not ongoing development. A 40-person for-profit company should get written confirmation or a licence before its team downloads and uses the data, and every commercial user of NeonRadar will need their own licence. Fixtures must be synthetic: copying OpenSanctions rows into an Apache-2.0 repository would relicense CC BY-NC material.
2. **The OpenSanctions download URLs changed.** Since 2026-08-17 `https://data.opensanctions.org/datasets/latest/<dataset>/<file>` redirects (the changelog names HTTP 307) to the immutable `https://data.opensanctions.org/artifacts/<dataset>/<version>/<file>` [S24][S49]. Clients must follow redirects (httpx does not by default). Pre-2024 date-stamped exports and `/graph/*` have required authenticated access since 2025-07-01 [S22]. The latest bulk files remain downloadable "without any login or API key" [S1].
3. **The hosted API is paid.** An API key is always required [S40]; usage is prepaid credits from EUR 0.10 down to EUR 0.03 per query, with 2,000 free credits for business sign-ups [S42][S30]. yente (MIT) can be self-hosted; non-commercial and exempt users may point it at the public "civic" manifest, commercial users need a licence and a delivery token [S45][S46].
4. **The FtM 4.x Python API changed.** followthemoney 4.0.0 (2025-07-13) absorbed the statement model and dataset metadata that used to live in nomenklatura 3.x (`nomenklatura.entity.CompositeEntity`, `nomenklatura.dataset`, `nomenklatura.statement` are gone in nomenklatura 4.x) [S55][S56][S59]. `followthemoney` now exports `EntityProxy`, `ValueEntity` (the recommended base class from 4.0), `StatementEntity`, `Statement` and `Dataset`. The basic `model.make_entity()`, `make_id()`, `add()`, `to_dict()` and `model.get_proxy()` calls still work (verified by running them). Current version 4.11.0 (2026-09-03) needs Python 3.11 or later and added the `Control` and `Territory` schemata, so pin `followthemoney>=4.11,<5` to parse current exports. Its PyICU dependency ships no wheels and needs `libicu-dev` to build [S50][S55].
5. **The ICIJ example URL is wrong.** ICIJ's download page links `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip`; `full-oea-data.zip` appears nowhere on it [S61]. ICIJ data is ODbL (database) plus CC BY-SA (contents), so commercial use is allowed [S61]. OpenSanctions republishes an FtM conversion of ICIJ (`icij_offshoreleaks`) but labels it CC BY-NC 4.0 [S16], so NeonRadar should load from ICIJ directly. The zip's size, Last-Modified date and HTTP range support are UNVERIFIED (see 0.1).

## 0.1 Method and limitations

- The research sandbox's egress proxy refused Bash connections to `www.opensanctions.org`, `data.opensanctions.org`, `api.opensanctions.org`, `followthemoney.tech`, `offshoreleaks.icij.org` and `offshoreleaks-data.icij.org` (policy denial, HTTP 403 on CONNECT). I did not route around it. Those sites were read with WebFetch instead. WebFetch returns verbatim quotes of up to about 100 to 125 characters each, so long passages below are reassembled from consecutive fragments, joined with single spaces. `data.opensanctions.org/.../index.json` was robots-disallowed for WebFetch, and binary downloads (the ICIJ zip) could not be fetched.
- PyPI, files.pythonhosted.org, raw.githubusercontent.com and `git clone` from github.com worked. I read the released followthemoney 4.11.0 sdist, shallow-cloned `opensanctions/followthemoney` (commit 9433b3d, 2026-10-05), `opensanctions/opensanctions` (blobless, commit d8d0c9c, 2026-10-15), `ICIJ/offshoreleaks-data-packages` (commit cfa316c, 2023-12-04) and `Senzing/mapper-icij` (commit af37066, 2026-10-15).
- I installed followthemoney 4.11.0 in a Python 3.12.3 virtual environment (after `apt-get install libicu-dev`) and ran every FtM snippet and property listing in this report against it.
- All 71 schema YAML files on GitHub `main` are byte-identical to the released 4.11.0 sdist, and `main` still declares version 4.11.0 [S55].

---

## A. OpenSanctions

### A.1 Bulk data

**Collections** (the slugs used in URLs) listed on the datasets index [S9]: `default`, `sanctions`, `peps`, `crime` ("Warrants and Criminal Entities"), `debarment`, `regulatory`, `maritime`, `securities`, `kyb`. OpenSanctions says not to use `all`: it is "an internal artifact of our data infrastructure", "a strictly inferior data product", updated only monthly since February 2025; use `default` instead [S34].

**Counts and current versions** (dataset pages, versions processed 2026-10-15):

| Collection | Total entities | Targets | Sources | Version string |
|---|---|---|---|---|
| default [S10] | 4,154,349 (2,046,988 searchable) | 1,242,508 | 474 | 20261015185439-hfs |
| sanctions [S11] | 309,108 | 75,356 | 93 | 20261015194704-koy |
| peps [S12] | 1,969,413 (938,803 searchable) | 718,813 | 212 | 20261015152705-dhx |
| crime [S13] | 518,495 | 251,437 | 62 | 20261015071904-jnj |
| debarment [S14] | 579,236 | 203,040 | 61 | 20261015005606-gud |
| regulatory [S15] | 392,535 | 163,192 | 37 | 20261015152705-div |

The datasets index page gives smaller figures that look like searchable-entity counts: sanctions 105,091; default 2,043,921; debarment 213,743; kyb 93,223,592; maritime 152,234; peps 935,434; regulatory 168,691; securities 337,309; crime 263,576 [S9].

**File sizes** (from the dataset pages, 2026-10-15 versions):

| File | default | sanctions | peps | crime | debarment | regulatory |
|---|---|---|---|---|---|---|
| entities.ftm.json | 2.47 GB | 359.27 MB | 888.52 MB | 360.76 MB | 400.04 MB | 275.59 MB |
| targets.nested.json | 3.74 GB | 438.46 MB | 1.25 GB | 361.65 MB | 403.39 MB | 275.55 MB |
| targets.simple.csv | 448.66 MB | 74.41 MB | 172.18 MB | 63.43 MB | 82.91 MB | 42.47 MB |
| senzing.json | 1.38 GB | 73.99 MB | 609.07 MB | 151.42 MB | 121.21 MB | 88.54 MB |
| names.txt | 104.95 MB | 11.07 MB | 24.49 MB | 5.57 MB | 5.52 MB | 3.99 MB |
| statements.csv | 8.91 GB | not offered | not offered | not offered | not offered | not offered |

**File formats** (titles and file names as defined in the exporter code [S49 zavod/zavod/exporters]; descriptions from [S3][S4][S5][S6][S7]):

| File | Exporter title | What it is |
|---|---|---|
| `entities.ftm.json` | FollowTheMoney entities | Line-delimited JSON: "The `entities.ftm.json` export includes one entity per line." [S4]. Every entity, including relationship entities (Ownership, Family, Sanction...). Each line is written with `id` as the first key so files sort with plain `sort` [S55 cli/util.py]. MIME type in metadata: `application/json+ftm`. The formats page labels it "Recommended" and describes it as "the native graph format, best for data pipelines" [S3]. |
| `targets.nested.json` | Targets as nested JSON | One line per target, with adjacent entities (addresses, sanctions, relations) nested inside `properties` [S4]. |
| `targets.simple.csv` | Targets as simplified CSV | 16 columns: `id, schema, name, aliases, birth_date, countries, addresses, identifiers, sanctions, phones, emails, program_ids, dataset, first_seen, last_seen, last_change`; comma-delimited, UTF-8, multi-values "stored as a nested CSV using the `;` (semicolon) delimiter"; "contains only risk-associated entities" [S5]. `program_ids` was added 2025-08-19 [S21]. |
| `names.txt` | Target names text file | Plain-text list of target names [S3]. |
| `senzing.json` | Senzing entity format | Records for the Senzing entity-resolution engine [S3]. |
| `statements.csv` | Statement-based granular CSV | `default` only. Documented columns: `entity_id, prop, prop_type, value, lang, original_value, dataset, schema, first_seen, last_seen, target, canonical_id` (the page lists them in a table; check the real header order) [S6]. `id` checksum statements were removed from this export in May 2026 [S26]. |
| `entities.delta.json` | Delta files | Per-version change log, lines like `{"op": "ADD", "entity": {...}}`, with `ADD`, `MOD` or `DEL`; `DEL` carries only the entity ID; the `delta_url` in index.json points to "an index of the last 100 versions" [S7]. |
| `securities.csv`, `maritime.csv` | Security-centric / Maritime-centric tabular format | Specialised exports for the securities and maritime collections [S49]. |
| `index.json`, `statistics.json`, `issues.json`, `versions.json`, `delta.json` | metadata | Run artifacts stored beside the data [S49 archive docstring]. Entity statistics were removed from index.json in January 2025 [S21]. |

`topics.nested.json` was removed on 2025-02-15 [S28].

**URL patterns** (layout documented in the OpenSanctions archive code [S49 zavod/zavod/archive/__init__.py]):

- Immutable, canonical: `https://data.opensanctions.org/artifacts/<dataset>/<version>/<file>`, for example `https://data.opensanctions.org/artifacts/default/20261015185439-hfs/entities.ftm.json` [S10]. The code says "`/artifacts/{dataset}/{version}/` is the canonical, immutable location for all outputs of a given run".
- Stable "latest" path: `https://data.opensanctions.org/datasets/latest/<dataset>/<file>`, for example `https://data.opensanctions.org/datasets/latest/default/entities.ftm.json` [S2]. Since 2026-08-17 it redirects: "We now redirect requests to the latest successful version in `/artifacts/`." [S49]; changelog #45 (marked Breaking) says to "check that your configuration supports HTTP status `307` redirects" [S24]. Changelog #24 (effective 2026-01-01) asked clients to handle 302, 303 and 307 [S23]. Not tested live from this sandbox.
- Version list: `https://data.opensanctions.org/artifacts/<dataset>/versions.json`, shaped like `{"items": ["20260629141001-mek", ...], "last_successful": "20260707123218-hai"}` [S49].
- Metadata: `https://data.opensanctions.org/datasets/latest/<dataset>/index.json` [S2]; global catalog `https://data.opensanctions.org/datasets/latest/index.json` [S46 civic.yml].
- Legacy dated paths `/datasets/YYYYMMDD/<dataset>/...`: redirected to `/artifacts/` "for dates >= 2026-08-17" [S49]. Paths matching `/datasets/2021*`, `/datasets/2022*`, `/datasets/2023*` and `/graph/*` have been access-controlled since 2025-07-01 because of "excessive bandwidth use"; "Bulk data customers and non-commercial users" can request authenticated access through support [S22].
- Commercial delivery service: `https://delivery.opensanctions.com`, header `Authorization: Token [yoursecret]`, token issued during customer onboarding; it also redirects large files to a CDN, and the token should not be sent to the redirect target domain [S8].

**Update frequency:** "The default collection is republished about every 6 hours." and "sanctions lists are updated every 4 to 12 hours" [S2]. Dataset pages say "Updated files will be provided once a day at the same location." [S12]. Suggested client behaviour: poll index.json about every 30 minutes and watch `version` or `last_export`, compare the SHA1 `checksum` of resources, and re-download "at most every 6 hours to avoid excessive data transfers" [S2]. No numeric rate limit is published for bulk downloads [S2].

**Other data-model notes for loaders:**
- IDs can change after deduplication; track both `id` and `referents`. "we do not emit explicit markers for deleted entities" [S2].
- `last_seen` is "almost never what you need" [S35].
- `abbreviation` became a separate property on 2026-09-15. OpenSanctions said the backstop that copies abbreviations into `weakAlias` "will be removed in September 2026" [S27].
- Chinese Unified Social Credit codes moved to `uscCode` (2025-12-01); unused source identifiers were removed from `referents` (2025-10-15) [S21].

### A.2 Licensing

**Data licence:** CC BY-NC 4.0. Site footer: "The data is licensed under the terms of Creative Commons 4.0 Attribution NonCommercial" [S17]. The repository's COPYRIGHT.md: "Data files produced by OpenSanctions are licensed under [Creative Commons Attribution-NonCommercial 4.0 International](LICENSES/CC-BY-NC-4.0.txt) (`CC-BY-NC-4.0`). They are **not** covered by the MIT License." and "OpenSanctions asserts database rights, and copyright where applicable, in the OpenSanctions data as a collection." and "What counts as non-commercial use is set out at <https://www.opensanctions.org/docs/commercial/exemption/>." [S48].

**Bulk access:** "You can download bulk data extracts of the database directly from this website, without any login or API key." and "OpenSanctions is free for non-commercial users. Businesses must acquire a data license to use the dataset." [S1].

**What counts as commercial use** (page "Free and non-commercial use" [S18]):
- "Any use inside a for-profit business requires a data license."
- "Compliance screening is a commercial use even though it generates no revenue:" "it's a cost of doing business, like the rest of your compliance program."
- "If your use is non-commercial (e.g. a student project, a hobby analysis, personal research)," "you don't need our permission to download the data."
- The CC licence's own definition: "NonCommercial means not primarily intended for or directed towards commercial advantage or monetary compensation." [S74]
- The data GTC (effective 2025-09-01) does not define commercial use; section 2.4 says "The services of OpenSanctions are aimed exclusively at businesses" [S20].

**Exemptions:** free API keys, headed "Free API keys support public-interest work" [S18]:
- "Journalists (staff or freelance) publishing findings in the public interest."
- "Advocacy groups and nonprofits working to improve democratic governance or to expose corruption and financial crime."
- "Academic researchers with an institutional affiliation," "studying sanctions policy, illicit finance, or related topics."
- "Public institutions of countries invaded by the Russian Armed Forces (Ukraine, Georgia, Moldova)."
- Not covered: "The free key program also doesn't cover hobby projects, coursework, or investigation work" "without a public-interest mandate." Nonprofits that screen for compliance get "a discount, not free access" (section heading) [S18].
- No exemption for open-source software projects is mentioned on the exemption page, the commercial FAQ or the licensing page [S18][S19][S17].

**Evaluation before licensing** (licensing page [S17]): "All of it is open for download." "Inspect the coverage and run it against your own cases before you commit to a license." "You can integrate and evaluate our data before signing a license."

**Answer for NeonRadar's company (40 people, unpaid open-source internship project):** by OpenSanctions' published test ("Any use inside a for-profit business requires a data license") the company's own use of the data for development and testing falls inside a for-profit business, so it needs a data licence, apart from a short evaluation, which the licensing page explicitly invites. That the interns are unpaid and the code is open source does not change the test as OpenSanctions words it. The CC BY-NC definition ("primarily intended for ... commercial advantage") is arguably narrower, but OpenSanctions' exemption page is the interpretation it publishes and points to from COPYRIGHT.md [S48]. Recommended actions:
1. Email OpenSanctions (support or sales) describing the project and ask for written confirmation of what is allowed (for example, evaluation-scale downloads for building an open-source loader, no production screening) or for a quote.
2. Until then, develop and run CI against synthetic FtM fixtures, and stream at most an evaluation slice (spike A.5).
3. Ship the OpenSanctions loader as user-run, with documentation (and a CLI notice) saying commercial users need their own licence and pointing journalists, NGOs and academics to the free-key programme.
4. Never commit OpenSanctions-derived rows to the repository.

**Licensed customers** (GTC for Data Licensing, "Effective date: September 1, 2025", previous version 2024-03-01 to 2025-09-01) [S20]: rights are an "Internal License" or "Reseller License". Internal use means "to use the Data Collection for internal purposes". Section 4.3(a) excludes the right "to pass on the Data Collection or parts of the Data Collection to third-parties" and 4.3(g) excludes the right "to distribute the Data Collection in whole or in substantial parts". So even a licensed company could not publish the data, which fits the loaders-only plan. Licence options shown: "Screening license: A flat-rate license to use the full dataset inside your own organization."; "Reseller license: A wholesale license to redistribute our data inside the products you sell."; "Screening API: Hosted sanctions & PEP screening, billed by the query. No license, no infrastructure." Prices: "You'll get a quote during our first conversation" [S17].

**Attribution text:** UNVERIFIED. OpenSanctions publishes no specific attribution or citation wording; none was found on the licensing, exemption, commercial FAQ, terms, about or open-source FAQ pages or in the repository README or COPYRIGHT.md [S17][S18][S19][S20][S47][S48]. CC BY-NC 4.0 section 3(a)(1) requires, when sharing: "identification of the creator(s) of the Licensed Material", "a copyright notice;", "a notice that refers to this Public License;", "a notice that refers to the disclaimer of warranties;", "a URI or hyperlink to the Licensed Material to the extent reasonably practicable;", to "indicate if You modified the Licensed Material", and to "indicate the Licensed Material is licensed under this Public License, and include the text of, or the URI or hyperlink to, this Public License." [S74]. Suggested wording (ours, not OpenSanctions'): "Contains data from OpenSanctions (https://www.opensanctions.org), (c) OpenSanctions Datenbanken GmbH, licensed under CC BY-NC 4.0 (https://creativecommons.org/licenses/by-nc/4.0/), provided without warranty. Converted and filtered by NeonRadar."

**2025 to 2026 changes in access** [S21]:

| Effective | Change |
|---|---|
| 2025-02-01 | Do not use `all`; monthly updates only [S34] |
| 2025-02-15 | `topics.nested.json` removed [S28] |
| 2025-07-01 | Historical exports (pre-2024) and `/graph/*` need authenticated access [S22] |
| 2025-09-01 | New GTC for data licensing [S20] |
| 2025-11-13 | Billing moved to Stripe [S21] |
| 2025-12-31 | KYB/Graph API at `api.graph.opensanctions.org` shut down [S33] |
| 2026-01-01 | Bulk clients must support 302/303/307 redirects [S23] |
| 2026-05-01 | `id` statements removed from `statements.csv` [S26] |
| 2026-08-17 | `datasets/latest/...` and dated paths redirect (307) to `/artifacts/<dataset>/<version>/` (Breaking) [S24] |
| 2026-09-15 | `abbreviation` property; weakAlias backstop ends September 2026 [S27] |
| 2026-09-24 | Hosted API prepaid credit bundles [S30] |

Commercial customers can use the token-authenticated delivery service [S8]. No accounts or tokens are needed for current bulk files from `data.opensanctions.org` [S1].

### A.3 Hosted API and yente

**Hosted API (`api.opensanctions.org`):**
- Key required: "you must always provide an API key when you make requests."; header `Authorization: ApiKey <your-key>` [S40].
- Metering: counted "per logical query rather than per HTTP request"; "Only successful calls (HTTP response code 200) count."; `/match` and `/reconcile` cost 1 credit per query, `/search` 1 credit per request, `/entities` and `/statements` are free. Each key has a request quota, and excess requests get HTTP 429. Credits are "valid for a year from purchase" [S41].
- Pricing (EUR, excluding VAT): 500 credits for EUR 50 (EUR 0.10 per query); 5,000 for EUR 400 (0.08); 30,000 for EUR 2,000 (0.067); 100,000 for EUR 5,000 (0.05); 500,000 for EUR 15,000 (0.03); 1,000,000 or more through sales [S42][S30]. Free trial: "Sign up with your business email address and start with 2,000 free credits." [S42]. Existing customers keep their billing unless migrated [S30].
- Non-commercial pricing: there is none. Non-commercial users outside the public-interest free-key programme have no free API path [S18]; they can use the bulk files or self-host yente.
- The data licence still governs the right to use the data; the on-premise API (yente) is not metered [S41].

**yente** (the self-hostable matching API):
- Code licence: MIT. LICENSE file "Copyright (c) 2022-2025 OpenSanctions Datenbanken GmbH" [S46]; docs: "This is an open source project released under" the MIT License [S44]. Latest release 5.5.0, 2026-06-23, Python `<3.15,>=3.11` [S54].
- Self-hosting with the bulk data for non-commercial use is permitted: "Non-commercial users and users exempted from commercial licensing may set" "`YENTE_MANIFEST: "/app/manifests/civic.yml"` instead of `"/app/manifests/commercial.yml"` to access OpenSanctions directly." [S45]. `civic.yml` loads `https://data.opensanctions.org/datasets/latest/index.json` (scope `default`, resource `entities.ftm.json`); `commercial.yml` loads `https://delivery.opensanctions.com/datasets/latest/index.json` with `auth_token: "$OPENSANCTIONS_DELIVERY_TOKEN"` [S46].
- Commercial self-hosting: "Once you have decided to adopt the OpenSanctions database in a commercial setting, you need to purchase a license subscription." [S45]; on-premise docs: "Acquire a bulk data license so that you're legally entitled to use the OpenSanctions dataset." [S43].
- yente can also index custom datasets, for example "custom watchlists" [S44].
- Sizing: "8GB RAM, 1vCPU, 60GB hard drive" baseline with an Elasticsearch index; 16 GB RAM and SSD suggested; docker-compose starting point [S43].
- Upcoming: the Elasticsearch 9 upgrade for on-premise yente (effective 2027-01-15) and retirement of the `name-based` and `name-qualified` algorithms (2027-01-18). `logic-v2` has been the default scoring algorithm since 2025-12-01 [S21].
- Dependency pins: yente 5.5.0 pins `followthemoney==4.9.2`, `nomenklatura==4.10.0`, `rigour==2.1.2` and `pyicu==2.16.2` exactly [S54]. If NeonRadar uses yente, run it in its own container, not in the same Python environment as loaders pinned to followthemoney 4.11.

### A.4 Topics vocabulary, PEPs and RCAs

**Vocabulary:** FtM 4.11.0 defines 75 topic codes in `followthemoney/types/topic.py`, and 30 of them form the `RISKS` set, docstring "A set of topics that imply a counterparty risk in business dealings." [S55]. The FtM docs: "Some topics imply a risk association of an entity (see table below), while others act as a purely descriptive taxonomy" and "Risk associations do not consistently imply wrongdoing" [S55 docs/explorer/types/topic.md].

Risk topics (code = FtM label; OpenSanctions definition where given [S36]):
- `sanction` = Sanctioned. Designated by a government to prohibit specific interactions with them.
- `sanction.linked` = Sanction-linked. Direct relationship with a `sanction` or `sanction.control` entity; superset of `sanction.control`.
- `sanction.control` = Sanction ownership or control. Direct or indirect subsidiaries of sanctioned entities, regardless of percentage or depth.
- `sanction.counter` = Counter-sanctioned. Listed by non-democratic countries, often activists and journalists.
- `debarment` = Debarred. Excluded from public procurement.
- `role.pep` = PEP. Currently or previously held a position of political influence.
- `role.rca` = Close Associate. "Family members and key business associates of politically exposed persons", "often used as nominees or front-people" [S36].
- `poi` = Person of interest. Public-interest case for scrutiny, but not a PEP and not sanctioned.
- `reg.action` = Regulator action; `reg.warn` = Regulator warning.
- `crime`, `crime.fin`, `crime.fraud`, `crime.terror`, `crime.theft`, `crime.traffick`, `crime.war`, `crime.boss` = Crime, Financial crime, Fraud, Terrorism, Theft, Trafficking, War crimes, Criminal leadership.
- `wanted` = Wanted; `role.oligarch` = Oligarch; `corp.clone` = Clone of real entity; `corp.disqual` = Disqualified.
- `export.control`, `export.control.linked`, `export.risk` = Export controlled, Export control-linked, Trade risk.
- `invest.risk`, `invest.ban` = Investment risk, Investment ban; `geo.risk` = High-risk area; `mare.detained`, `mare.shadow` = Maritime detention, Shadow fleet.

Descriptive (non-risk) topics: `crime.cyber`, `crime.env`, `crime.traffick.drug`, `crime.traffick.human`, `forced.labor`, `asset.frozen`, `corp.offshore`, `corp.shell`, `corp.public`, `gov`, `gov.national`, `gov.state`, `gov.muni`, `gov.soe`, `gov.igo`, `gov.head`, `gov.admin`, `gov.executive`, `gov.legislative`, `gov.judicial`, `gov.security`, `gov.financial`, `gov.religion`, `fin`, `fin.bank`, `fin.fund`, `fin.adivsor` (sic, misspelled in the code), `mare.sts`, `role.pep.frmr`, `role.pep.intl`, `role.pep.natl`, `role.pol`, `role.judge`, `role.civil`, `role.diplo`, `role.lawyer`, `role.acct`, `role.spy`, `role.journo`, `role.act`, `role.lobby`, `pol.party`, `pol.union`, `rel`, `mil` [S55]. Whether OpenSanctions currently emits `role.pep.frmr`, `role.pep.intl` and `role.pep.natl` is UNVERIFIED.

**Target:** glossary: "The `target` flag included in entities is a simplified representation of the risk topics which apply to that entity." [S37]. Changelog #13 (effective 2025-01-15) switched `targets.*` exports to topics and listed 22 topics: corp.disqual, crime.boss, crime.fin, crime.fraud, crime.terror, crime.theft, crime.traffick, crime.war, crime, debarment, export.control, export.risk, poi, reg.action, reg.warn, role.oligarch, role.pep, role.rca, sanction.counter, sanction.linked, sanction, wanted [S28]. The current exporter code computes `target` as true when any topic is in FtM `RISKS` (30 topics; it adds e.g. `sanction.control`, `export.control.linked`, `invest.*`, `mare.detained`, `mare.shadow`, `geo.risk`, `corp.clone`) and writes `"target": bool` into every line [S49 zavod/zavod/entity.py]. Treat `target` as legacy and filter on `topics` [S35].

**PEP representation** (OpenSanctions):
- A `Person` with topic `role.pep`, a `Position` entity whose `topics` describe level and branch (e.g. `gov.national`, `gov.legislative`), and an `Occupancy` (edge `holder` -> `post`) with `startDate`, `endDate`, `periodStart`, `periodEnd` and `status` [S38][S49 zavod/zavod/helpers/positions.py].
- `status` values are `current`, `ended` and `unknown` [S49 zavod/zavod/stateful/positions.py]. The exporter adds `role.pep` to the person (origin "inferred") when the occupancy qualifies [S49].
- Retention after leaving office: heads of state or government 50 years, other national-level, intergovernmental and diplomatic positions 20 years, everything else 5 years [S39].
- Since 2025-07-01 `Person:classification` carries values like "National government (current)" or "State government (past)", "only available in the `default` dataset" [S29].
- Use `default`, not `peps`, for relatives and associates: "The `default` collection contains all of this." [S38].

**RCA representation:** the RCA is a `Person` with topic `role.rca` [S39]. The link is a `Family` entity (`person` = the PEP, `relative` = the RCA, `relationship`), for example the Nigeria "Joining the Dots" crawler [S49 datasets/ng/join_dots/crawler.py], or an `Associate` entity (`person`, `associate`, `relationship`) for non-family links (nomenklatura Wikidata enricher, which emits `Family` for family claims and `Associate` for association claims) [S59]. Automatic `role.rca` tagging of every Wikidata relative of a PEP was removed (code comment citing opensanctions issue 3354), so not every `Family` partner of a PEP carries `role.rca` [S59].

### A.5 Spike A: stream 1,000 OpenSanctions entities (under one minute, nothing stored)

Goal: prove download, redirect handling and FtM parsing without writing bulk data anywhere. Use the `sanctions` collection (359 MB file, of which the first 1,000 lines are well under 1 MB) or a single source such as `us_ofac_sdn`. Licence note: for the company this counts as evaluation (A.2); confirm with OpenSanctions first.

```python
# scratch spike: python spike_os.py https://data.opensanctions.org/datasets/latest/sanctions/entities.ftm.json 1000
import collections, json, sys
import requests
from followthemoney import ValueEntity
from followthemoney.exc import InvalidData

url, limit = sys.argv[1], int(sys.argv[2])
schemata, topics, n = collections.Counter(), collections.Counter(), 0
with requests.get(url, stream=True, timeout=60) as resp:   # requests follows the 307; httpx needs follow_redirects=True
    resp.raise_for_status()
    print("served from", resp.url, [r.status_code for r in resp.history])
    for line in resp.iter_lines():
        if not line:
            continue
        try:
            entity = ValueEntity.from_dict(json.loads(line))   # keeps datasets, referents, first_seen, last_change; 'target' stays in context
        except InvalidData as exc:                              # schema newer than the pinned FtM
            print("skip", exc); continue
        schemata[entity.schema.name] += 1
        topics.update(entity.get("topics", quiet=True))
        n += 1
        if n >= limit:
            break                                               # leaving the with-block closes the connection
print(n, dict(schemata), topics.most_common(10))
```

Status: the parsing path ran successfully on synthetic lines shaped like the documented export (including `target` and an unknown schema, which raises `InvalidData: No schema for entity.`). The live HTTP run could not be executed here because the sandbox proxy blocks `data.opensanctions.org`. Before streaming, fetch `index.json` and log `version`, `last_export` and the resource `checksum` [S2]. CI should never touch the network.

---

## B. FollowTheMoney

### B.1 Package, version and the 4.x Python API

| Package | Latest | Released | Licence | Python | Source |
|---|---|---|---|---|---|
| followthemoney | 4.11.0 | 2026-09-03 | MIT ("Copyright (c) 2017-2024 Journalism Development Network, Inc." and "Copyright (c) 2025 OpenSanctions Datenbanken GmbH") | `>=3.11`; classifiers 3.11, 3.12, 3.13, 3.14 | [S50] |
| nomenklatura | 4.17.2 | 2026-10-12 | MIT (classifier; licence text "Copyright (c) 2023-2025, OpenSanctions Datenbanken GmbH") | `>=3.11`; classifiers 3.11, 3.12 | [S51] |
| rigour | 2.5.0 | 2026-09-10 | MIT (classifier and LICENSE file) | `>=3.10`; wheels cp310 to cp314 | [S52][S60] |
| normality | 3.1.0 | 2026-03-08 | MIT; requires `pyicu>=2.10.0` | `>=3.10` | [S53] |
| yente | 5.5.0 | 2026-06-23 | MIT | `<3.15,>=3.11` | [S54] |
| pyicu | 2.16.2 | n/a | n/a | sdist only, no wheels | [S50] |

Repository: `https://github.com/opensanctions/followthemoney` (PyPI project URLs) [S50]. Release cadence: 4.0.0 on 2025-07-13, then 4.1 to 4.11 through 2026-09-03 [S50]. The requirement went from `>=3.10` (4.0.0) to `>=3.11` (4.11.0) [S50]. Installing needs ICU headers to build PyICU; the docs say "On a Debian-based Linux system ... `apt install libicu-dev`" then `pip install pyicu` [S57]. Verified here: the install failed without `libicu-dev` and succeeded with it.

**What 4.x changed** (release notes for v4.0.0, released 13 July 2025 [S56], plus code inspection [S55][S59]):
- "Introduces a statement data model" (language, first/last seen, dataset, original value) and "a dataset metadata model, including a `Dataset` class and a `DataCatalog` grouping" (release-notes summary).
- These came from nomenklatura. nomenklatura 3.17.5 shipped `nomenklatura/entity.py` (`class CompositeEntity(EntityProxy)`), `nomenklatura/dataset/` and `nomenklatura/statement/`, and its `__init__` exported `Dataset` and `CompositeEntity`. nomenklatura 4.x has none of these and exports only `Judgement, Linker, Resolver, Store, View`. nomenklatura 4.0.0 required `followthemoney<5.0.0,>=4.0.0`; 4.17.2 requires `>=4.10.2` [S59][S51].
- `followthemoney/__init__.py` (4.11.0) exports `Dataset, DS, E, EntityProxy, Model, Property, PropertyType, Schema, SE, Statement, StatementEntity, UndefinedDataset, Value, ValueEntity, Values, VE, model, registry, set_model_locale` [S55].
- `ValueEntity` docstring: "This class has the extended attributes from `StatementEntity` but without statements. Useful for streaming around. Starting from followthemoeny 4.0, applications should use this entity class as the base class." (typo in the original) [S55 entity.py].
- `model.make_entity()` still returns a plain `EntityProxy` (verified).
- Breaking changes in the release notes: `Post` and `Assessment` schemata removed; `UserAccount:number` renamed to `UserAccount:phone`; `CryptoWallet:mangingExchange` typo fixed (now `managingExchange`); `Sanction:duration` and `License:area` became `number`; `Company:ibcRuc` removed; the `iban` property type removed in favour of `identifier` with format `iban`; "`EntityProxy.from_dict()` no longer takes a `model` argument"; the `fingerprints` dependency was dropped in favour of `rigour.names`; `followthemoney.offshore` removed; RDF export moved to its own module [S56][S25].
- Schemata added later: `Risk` (by 4.5.0), `Documentation` (by 4.8.0), `Control` and `Territory` (4.11.0). Properties `LegalEntity:abbreviation` (by 4.5.0) and `Thing:riskSource` (by 4.9.2) [S50 wheels diffed]. Loaders pinned below 4.11 will fail on `Control` entities with `InvalidData`.

**`make_id`:** `EntityProxy.make_id(*parts)` sets and returns the SHA1 hex digest of the parts, salted with the proxy's `key_prefix` if set, or `None` if no parts are given (`followthemoney.util.make_entity_id`) [S55]. Unchanged in 4.x. For sources with native IDs, readable slugs such as `icij-10000001` are easier to debug than hashes.

**Recommended create, validate, serialise** (documented pattern from `docs/python/index.md` / https://followthemoney.tech/python/ [S57][S55]; this exact code ran on 4.11.0 and the outputs in the comments are real):

```python
from followthemoney import model, ValueEntity
from followthemoney.exc import InvalidData

company = model.make_entity("Company")            # EntityProxy
company.make_id("gb-coh", "01234567")              # -> '5be8140e5e982d86e62133264d9ec8a6b43a88f9'
company.add("name", "Acme Holdings Ltd")
company.add("jurisdiction", "United Kingdom")      # cleaned to 'gb'
company.add("registrationNumber", "01234567")
company.add("leiCode", "5493001KJTIIGC8Y1R12")
company.add("incorporationDate", "2001-03-15")

person = model.make_entity("Person")
person.make_id("person", "Ivan Petrov", "1970-01-01")
person.add("name", ["Ivan Petrov", "Иван Петров"])
person.add("birthDate", "1970-01-01")
person.add("nationality", "Russia")                # cleaned to 'ru'
person.add("nationality", "Atlantis")              # invalid value: silently dropped

own = model.make_entity("Ownership")
own.make_id("own", person.id, company.id)
own.add("owner", person)                           # entity or its id
own.add("asset", company)
own.add("percentage", "25.5")

data = own.to_dict()       # {'id': ..., 'schema': 'Ownership', 'properties': {'owner': [...], 'asset': [...], 'percentage': ['25.5']}}
again = model.get_proxy(data)                      # round trip; equal to own
model["Ownership"].validate(data)                  # raises InvalidData if a value is invalid

# Required properties: Schema.validate only flags a required key that is present but empty,
# so check missing ones yourself:
missing = [p for p in own.schema.required if not own.has(p)]   # [] here

# With provenance fields (datasets, referents, first_seen, last_seen, last_change):
ve = ValueEntity(model["Company"], {"id": "icij-10000001", "datasets": ["icij_offshoreleaks"]})
ve.add("incorporationDate", "23-MAR-2006", format="%d-%b-%Y")   # -> '2006-03-23'
```

Verified behaviours: unknown property names raise `InvalidData` ("Unknown property (<Schema('Company')>): birthDate") unless `quiet=True`; invalid typed values (country "Atlantis") are dropped silently by `add()`; `Schema.validate` raises `InvalidData` with `errors={'properties': {'birthDate': "Invalid value: 'BANANA'"}}` for invalid values; a required property absent from the dict entirely passes `validate()` (returns `None`) [S76]. The docs snippet itself has a typo (`enttiy.add(...)`) [S55 docs/python/index.md].

**Statement-level provenance and language** (verified):

```python
from followthemoney import Dataset, StatementEntity
ds = Dataset.make({"name": "neonradar_test", "title": "NeonRadar test"})
se = StatementEntity(ds, {"schema": "Person", "id": "p-1"})
se.add("name", "Владимир Путин", lang="rus")
se.add("name", "Vladimir Putin", lang="eng")
se.add("name", "فلاديمير بوتين", lang="ara")
se.to_dict()       # caption 'Vladimir Putin'; properties.name holds all three; datasets ['neonradar_test']
list(se.statements) # one Statement per value with .lang, plus an internal 'id' checksum statement
```

The FtM CLI provides `ftm export-cypher`, `ftm export-neo4j-bulk`, `ftm statements` and `ftm aggregate-statements` [S55 cli/exports.py, docs/docs/statements.md].

### B.2 nomenklatura and rigour

- **nomenklatura** 4.17.2 (2026-10-12), MIT, active (more than 80 releases since 4.0.0 on 2025-07-16) [S51]. It is now the integration, resolution and matching layer: `Resolver`, `Linker`, `Judgement`, `Store`/`View` (LevelDB or DuckDB), matching algorithms (`logic_v1`, `logic_v2`, `regression_v1`, `name_based`, `erun`), enrichers (Wikidata, OpenCorporates, GLEIF via yente, PermID, OpenFIGI and others) and xref [S59]. Heavy dependencies: `duckdb`, `scikit-learn==1.9.1` (exact pin), `sqlalchemy>=2.1.0`, `textual`, `lxml`, `fingerprints` [S51].
- **rigour** 2.5.0 (2026-09-10), MIT, Rust core with wheels for CPython 3.10 to 3.14 [S52]. README: "Data cleaning and validation functions for processing various types of text emanating and describing the business world. This applies to human and company names, language, territory and country codes, corporate and tax identifiers, etc." and it consolidates "`languagecodes`, `pantomime`, `fingerprints`" [S60]. Modules: `addresses`, `boolean`, `dates`, `ids`, `langs`, `mime`, `names`, `territories`, `text`, `time`, `units`, `urls` [S76].
- Transliteration limit (module docstring `rigour/text/translit.py`): "Covers only six admitted scripts (Latin, Cyrillic, Greek, Armenian, Georgian, Hangul)"; "For broader-script, lossy transliteration (Han, Arabic, Devanagari, etc.) use `normality.ascii_text` / `normality.latinize_text`" [S60]. Verified: `maybe_ascii("Владимир Путин")` gives "Vladimir Putin", but Arabic passes through unchanged, and `normality.ascii_text("فلاديمير بوتين")` gives "fladymyr bwtyn" (lossy, not matchable against "Vladimir Putin") [S76].

### B.3 JSON shape of a serialised entity

Plain `EntityProxy.to_dict()` gives `{"id", "schema", "properties"}` plus any extra keys passed in at construction (kept as "context") [S55 proxy.py]. `properties` maps property names to lists of strings: "all properties are multi-valued" [S35].

`ValueEntity.to_dict()` adds `referents` (list), `datasets` (list), and when set `caption`, `first_seen`, `last_seen`, `last_change` [S55 entity.py]. `StatementEntity.to_dict()` emits `id`, `caption`, `schema`, `referents`, `datasets`, optional `origin` (list), `first_seen`, `last_seen`, `last_change` and `properties` [S55 statement/entity.py]. OpenSanctions' exporter adds `"target": true|false` [S49 zavod/zavod/entity.py] and writes one line per entity with `id` first.

Example from the OpenSanctions docs [S35]:

```json
{
    "id": "NK-xxxx",
    "schema": "Person",
    "caption": "John Doe",
    "datasets": ["us_ofac_sdn"],
    "referents": ["ofac-12345"],
    "first_seen": "2025-08-22T10:15:20+00:00",
    "last_change": "2025-08-22T10:15:20+00:00",
    "properties": {
        "name": ["John Doe"],
        "nationality": ["us", "au"],
        "birthDate": ["1982"]
    }
}
```

Field meanings [S35]:
- `caption` "is an algorithmically-picked, preferred display name".
- `referents` are "All the source entity IDs which have been grouped into a merged entity".
- `first_seen` is "The first time an entity was included in the dataset".
- `last_change` is "The last time some value in the entity changed".
- `target` is a "Legacy field".

Merged IDs use an `NK-` prefix, or a Wikidata QID when linked [S6]. References between entities are plain ID strings inside `properties` (e.g. `"owner": ["NK-..."]`).

### B.4 Schema hierarchy and properties (followthemoney 4.11.0, read from `followthemoney/schema/*.yaml` and the loaded model)

Hierarchy (`extends`):
- `Thing` (abstract) -> `LegalEntity` -> `Person`, `Organization`
- `Organization` -> `Company` (also `Asset`), `PublicBody`
- `Value` (abstract) + `Thing` -> `Asset` -> `BankAccount`, `Company`, and others
- `Thing` -> `Address`, `Position`, `Territory`
- `Interval` (abstract) -> `Interest` (abstract) -> `Ownership`, `Directorship`, `Control`, `Membership`, `Employment`, `Representation`, `UnknownLink`, `Succession`, `Documentation`
- `Interval` directly -> `Family`, `Associate`, `Occupancy`, `Sanction`, `Risk`, `Identification` (-> `Passport`), `Payment` (also `Value`)

There are 71 schemata in total [S55]. Properties without an explicit `type` default to `string` (`type_ = data.get("type") or "string"` in property.py) [S55].

Warnings from the sources:
- Interval.yaml: "Intervals are not graph edges." and "You will find there are intervals that link to only one thing (e.g. Sanction) or to much more than two (e.g. FEA)." [S55]
- OpenSanctions on treating Thing-derived entities as nodes and Interval-derived ones as edges: "This assumption is false and will lead to nasty bugs in your code." [S35]
- Rule: use `schema.edge` (true only when the YAML declares `edge.source` and `edge.target`), not inheritance.

Notation below: `name (type)`; `entity:X` means an entity reference whose range is schema X; "featured" marks properties for UI prominence [S58]; "required" is used by `Schema.validate` (see B.1 caveat). Flags: `nm` = not matchable, `dep` = deprecated, `hid` = hidden.

**Thing** (abstract; featured name, country; required name; caption name): `name` (name), `alias` (name), `previousName` (name), `weakAlias` (name, nm), `country` (country), `summary` (text), `notes` (text), `description` (text), `sourceUrl` (url), `publisher` (string), `publisherUrl` (url), `alephUrl` (url, hid), `wikipediaUrl` (url), `wikidataId` (identifier, format wikidata), `keywords` (string), `topics` (topic), `address` (address), `addressEntity` (entity:Address), `program` (string), `programId` (identifier, hid), `proof` (entity:Document), `riskSource` (entity:Thing), `indexText` (text, hid), `createdAt` (date), `modifiedAt` (date), `retrievedAt` (date).

**addressEntity:** defined on `Thing`, so it is available on every LegalEntity: "A reference to an `Address` entity with structured place information", `type: entity`, `range: Address`, reverse property `things` labelled "Located there". The plain `address` property (type `address`) is "A textual description of an address linked to the entity" [S55 Thing.yaml]. Verified: `company.add("addressEntity", address_entity)` stores the Address entity's ID.

**LegalEntity** (extends Thing; matchable; featured name, country, legalForm, status; required name; temporal extent incorporationDate to dissolutionDate): `abbreviation` (name, nm), `email` (email), `phone` (phone), `website` (url), `legalForm` (string), `incorporationDate` (date), `dissolutionDate` (date), `taxStatus` (string), `status` (string), `sector` (string), `classification` (string), `registrationNumber` (identifier), `idNumber` (identifier), `taxNumber` (identifier), `licenseNumber` (identifier), `vatCode` (identifier), `jurisdiction` (country), `mainCountry` (country), `opencorporatesUrl` (url), `bvdId` (identifier), `sayariId` (identifier), `brightQueryId` (identifier), `brightQueryOrgId` (identifier, hid), `uscCode` (identifier, format uscc), `icijId` (string), `okpoCode` (identifier), `innCode` (identifier, format inn), `ogrnCode` (identifier, format ogrn), `okvedCode` (identifier), `leiCode` (identifier, format lei), `dunsCode` (identifier), `uniqueEntityId` (identifier, format uei), `npiCode` (identifier, format npi), `swiftBic` (identifier, format bic), `parent` (entity:LegalEntity, dep: "Deprecated, use `Ownership` link instead").

**Person** (extends LegalEntity; featured name, nationality, birthDate; required name; temporal extent birthDate to deathDate): `title`, `firstName`, `secondName` (dep), `middleName`, `fatherName`, `motherName`, `lastName`, `nameSuffix` (all string; the YAML notes they "intentionally do not use the `name` property type"), `birthDate` (date), `birthPlace` (string), `birthCountry` (country), `deathDate` (date), `position` (string), `biography` (text), `nationality` (country), `citizenship` (country), `passportNumber` (identifier), `socialSecurityNumber` (identifier, format ssn), `gender` (gender), `ethnicity`, `height` (number), `weight` (number), `eyeColor`, `hairColor`, `appearance`, `religion`, `political`, `profession`, `education` (strings), `spokenLanguage` (language).

**Organization** (extends LegalEntity; featured name, country, legalForm, status; required name): `cageCode` (identifier), `permId` (identifier), `imoNumber` (identifier, format imo), `giiNumber` (identifier).

**Company** (extends Organization and Asset; featured name, jurisdiction, registrationNumber, incorporationDate; required name): `capital` (number), `voenCode`, `coatoCode`, `irsCode`, `ipoCode`, `cikCode`, `jibCode`, `mbsCode` (identifiers), `caemCode` (string), `kppCode` (identifier), `okopfCode` (string), `fnsCode` (identifier), `fssCode` (string), `bikCode`, `pfrNumber` (identifiers), `oksmCode` (string), `isinCode` (identifier, dep), `ticker` (identifier), `ricCode` (identifier). Because Company is an Asset it can be the `asset` of an Ownership and carries Value's `amount`, `currency`, `amountUsd`, `amountEur` (number, string, number, number).

**PublicBody** (extends Organization; featured name, country, legalForm, status; required name): no own properties.

**Asset** (extends Thing and Value; featured name, amount; not abstract, not matchable): no own properties beyond Value's.

**BankAccount** (extends Asset; matchable; featured accountNumber, bankName; no required properties; caption name, iban, accountNumber): `bankName` (string), `accountNumber` (identifier), `iban` (identifier, format iban), `bic` (identifier, format bic), `bank` (entity:Organization), `accountType` (string), `openingDate` (date), `closingDate` (date), `balance` (number), `balanceDate` (date), `maxBalance` (number), `maxBalanceDate` (date), `bankAddress` (string).

**Address** (extends Thing; matchable; featured full, city, street, country; no required properties): `full` (address), `remarks`, `postOfficeBox`, `street`, `street2`, `city`, `postalCode`, `region`, `state` (strings), `latitude` (number), `longitude` (number), `osmId` (identifier), `googlePlaceId` (identifier).

**Interval** (abstract): `startDate`, `endDate`, `date` (dates), `summary`, `description` (text), `recordId` (string), `sourceUrl` (url), `proof` (entity:Document), `publisher` (string), `publisherUrl` (url), `alephUrl` (url, hid), `namesMentioned` (name, hid), `indexText` (text, hid), `modifiedAt`, `retrievedAt` (dates).

**Interest** (abstract, extends Interval): `role` (string), `status` (string).

Edge and link schemata:

| Schema | Parent | Edge source -> target | Directed | Edge label | Required | Featured | Own properties (type) |
|---|---|---|---|---|---|---|---|
| Ownership | Interest | `owner` -> `asset` | yes | owns | owner, asset | owner, asset, role, percentage, startDate, endDate | `owner` (entity:LegalEntity), `asset` (entity:Asset), `percentage`, `sharesCount`, `sharesValue`, `sharesCurrency`, `sharesType`, `legalBasis`, `ownershipType` (all string) |
| Directorship | Interest | `director` -> `organization` | yes | directs | director, organization | director, organization, role, startDate, endDate | `director` (entity:LegalEntity), `organization` (entity:Organization), `secretary` (string) |
| Control (new in 4.11.0) | Interest | `controller` -> `controlled` | yes | controls | controller, controlled | controller, controlled, controlType, startDate, endDate | `controller`, `controlled` (entity:LegalEntity), `controlType` (string; examples voting, appointment, management, contractual, trust, nominee, state, indirect), `legalBasis` (string) |
| Family | Interval | `person` -> `relative` | no | related to | person, relative | person, relative, relationship | `person`, `relative` (entity:Person), `relationship` (string, "from the `person`'s perspective, e.g. 'mother', where `relative` is the mother of `person`") |
| Associate | Interval | `person` -> `associate` | no | associated with | person, associate | person, associate, relationship | `person`, `associate` (entity:Person), `relationship` (string) |
| Membership | Interest | `member` -> `organization` | yes | belongs to | member, organization | member, organization, role, startDate, endDate | `member` (entity:LegalEntity), `organization` (entity:Organization) |
| Employment | Interest | `employee` -> `employer` | yes | works for | employer, employee | employer, employee, role, startDate, endDate | `employer` (entity:Organization), `employee` (entity:Person) |
| Representation | Interest | `agent` -> `client` | yes | represents | agent, client | agent, client, role | `agent`, `client` (entity:LegalEntity) |
| UnknownLink | Interest | `subject` -> `object` | no | linked to | subject, object | subject, object, role | `subject`, `object` (entity:Thing) |
| Succession | Interest | `predecessor` -> `successor` | yes | preceeds (sic) | predecessor, successor | predecessor, successor, date | `predecessor`, `successor` (entity:LegalEntity) |
| Payment | Interval and Value | `payer` -> `beneficiary` | yes | paid | payer, beneficiary | payer, beneficiary, date, amount, purpose | `sequenceNumber`, `transactionNumber` (string), `purpose` (text), `programme` (string), `payer`, `beneficiary` (entity:LegalEntity), `payerAccount`, `beneficiaryAccount` (entity:BankAccount), `contract` (entity:Contract), `project` (entity:Project); plus Value `amount`, `currency`, `amountUsd`, `amountEur` |
| Occupancy | Interval | `holder` -> `post` | yes | holds | holder, post | holder, post | `holder` (entity:Person), `post` (entity:Position), `declarationDate`, `electionDate`, `periodStart`, `periodEnd` (dates), `constituency`, `politicalGroup`, `status` (string; examples current, ended) |
| Sanction | Interval | not an edge | n/a | n/a | entity | entity, country, authority, program, startDate | `entity` (entity:Thing), `authority` (string), `authorityId` (identifier), `unscId` (identifier), `program` (string), `programId` (identifier), `programUrl` (url), `provisions` (string), `status` (string), `duration` (number), `reason` (text), `country` (country), `listingDate` (date) |
| Identification | Interval | not an edge | n/a | n/a | holder, number | number, country, type, holder, startDate, endDate | `holder` (entity:LegalEntity), `type` (string), `country` (country), `number` (identifier), `authority` (string). `Passport` extends it, adding `birthDate`, `birthPlace`, `gender`, `personalNumber`, plus deprecated `passportNumber`, `surname`, `givenName` |
| Position | Thing (a node) | not an edge | n/a | n/a | name | name, country, subnationalArea | `organization` (entity:Organization), `inceptionDate`, `dissolutionDate` (dates), `subnationalArea` (string), `numberOfSeats` (number) |

Source: YAML in [S55], confirmed by loading the model (`schema.edge_source`, `edge_target`, `edge_directed`, `required`, `featured`) [S76].

**Type system:** 20 property types: address, checksum, country, date, email, entity, gender, html, identifier, ip, json, language, mimetype, name, number, phone, string, text, topic, url [S76].
- `country` holds 281 codes: lower-case ISO 3166-1 alpha-2 plus specials such as `xk` (Kosovo), `zz` (Global), `gb-sct`, `ua-cri`, `suhh`, `csxx`, `yucs`. Cleaning accepts names and alpha-3: "VGB" gives `vg`, "UK" gives `gb`.
- `date` holds ISO 8601 prefixes ("1979", "1979-08", "1979-08-23", or a datetime). Non-ISO strings are rejected unless a `format=` hint is passed ("31-DEC-2005" with `format="%d-%b-%Y"` gives "2005-12-31").
- `number` keeps raw text ("25.5%" stays "25.5%") [S76]. The 4.0 notes describe a stricter "NNNN.DD UNIT" semantic that "the library doesn't fully enforce yet" [S56].

**FtM to Neo4j quick test:** `ftm export-cypher` on a synthetic fixture produced:
- `MERGE (p { id: "entity:nr-p-1" }) ... SET p :Person:Thing:LegalEntity`
- `MERGE (s)-[:OWNERSHIP { percentage: "25.5", ... }]->(t)` for Ownership
- `[:ADDRESSENTITY]` for the `addressEntity` reference
- a `:Sanction:Interval` node with an `[:ENTITY]` relationship to the person.

Multi-valued properties were joined into one string ("Ivan Petrov; Иван Петров") and nodes were merged without a label [S76]. Fine for a spike; production loaders should write their own Cypher (indexed labels, list properties, provenance).

### B.5 How FtM represents the AML-relevant facts

| Fact | FtM representation | Notes |
|---|---|---|
| Beneficial ownership percentage | `Ownership:percentage` (string) | Not a number type, so values like "25.5" or "75-100%" are kept as text; parse in the loader. `Ownership:ownershipType` examples: beneficial, direct, indirect, ultimate. Also `role`, `status`, `startDate`, `endDate`, `legalBasis` [S55]. OpenSanctions docs: an Ownership entity sits between a person and a company, "with references to the person as its `owner` property and to the company as its `asset` property" [S35]. |
| Control without ownership | `Control` (4.11.0): `controller` -> `controlled`, `controlType`, `legalBasis` | Fits UK PSC "significant influence or control" natures [S55]. |
| Share classes | `Ownership:sharesType` ("Type of shares"), `sharesCount`, `sharesValue`, `sharesCurrency` (all string) | One Ownership entity per holding per class [S55]. |
| Company registration number | `LegalEntity:registrationNumber` (identifier) | Other national IDs have their own properties (`innCode`, `ogrnCode`, `uscCode`, `vatCode`, `taxNumber`...) [S55]. |
| Jurisdiction | `LegalEntity:jurisdiction` (country) | "Country or region in which this entity operates; prefer over broader `country` when relevant" [S55]. |
| LEI code | `LegalEntity:leiCode` (identifier, format `lei`, maxLength 32) | Format validation available (`registry.identifier.validate(value, format="lei")` returned True for a valid LEI) [S76]. |
| Status | `LegalEntity:status` (string, not matchable) | Free text: "Active / Inactive", "Dissolved (last known activity October 2024)" [S55]. Also `incorporationDate`, `dissolutionDate`, `legalForm`. |
| Date of birth | `Person:birthDate` (date) | Partial dates allowed ("1982", "1982-05") [S35][S76]. |
| Nationality | `Person:nationality` and `Person:citizenship` (country) | Split since 2024-11-01; consumers "should check both properties", plus `birthCountry` and `country` (which may reflect residence) [S32]. |
| Alternative spellings | `alias` (name), `weakAlias` (name, not matchable: "should not be used for matching in screening systems"), `previousName` (name), `abbreviation` (name, not matchable, LegalEntity) | OpenSanctions moved EU FSF name translations from `name` to `alias` (2025-11-30), aiming to "ensure that the `name` field only contains the highest-quality names available" [S31][S55]. |
| Transliterations across Arabic, Cyrillic, Latin | Each spelling is a separate value of `name` or `alias`; FtM never stores machine transliterations | Plain JSON carries no per-value language. Statements carry `lang` (3-letter code) and `original_value` (statement table and `StatementEntity.add(..., lang=...)`) [S55 docs/docs/statements.md][S6]. Matching transliterates at comparison time: rigour covers Latin, Cyrillic, Greek, Armenian, Georgian and Hangul; Arabic falls back to lossy ICU transliteration in normality [S60][S76]. For Arabic names rely on source-provided Latin aliases, keep the original script, and do not expect ICU output to match English spellings. |

### B.6 Spike B: FtM fixture to Neo4j, offline, seconds

1. Build 6 to 10 synthetic entities (Person with Cyrillic and Latin names, Company, Address via `addressEntity`, Ownership, Directorship, Sanction) with the B.1 code; validate with `Schema.validate` plus the missing-required check; write JSONL with `json.dumps(e.to_dict())` per line into `tests/fixtures/*.ftm.json` (synthetic data only).
2. Load into Neo4j (testcontainers or local) with a small loader: entities with `schema.edge` true become relationships from `edge_source` to `edge_target`, keeping the FtM entity ID as a relationship property; everything else becomes a node labelled by schema; entity-typed properties of non-edge schemata (`Sanction:entity`, `Identification:holder`, `addressEntity`) become relationships named after the property.
3. Compare against `ftm export-cypher -i fixture.ftm.json` (built into FtM) for a quick visual check.
4. Assert counts in Cypher.

Runtime: under one second for the FtM part. The verified example output is in B.4.

---

## C. ICIJ Offshore Leaks Database

### C.1 Bulk download

**URLs** (download page [S61]):
- CSV zip, all leaks: `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip`. The page says the archive covers Offshore Leaks (2013), Panama Papers (2016), Bahamas Leaks (2016), Paradise Papers (2017) and Pandora Papers (2021).
- Neo4j 4 dump: `https://offshoreleaks-data.icij.org/offshoreleaks/neo4j/icij-offshoreleaks-4.4.26.dump`
- Neo4j 5 dump: `https://offshoreleaks-data.icij.org/offshoreleaks/neo4j/icij-offshoreleaks-5.13.0.dump`
- The same zip URL is used by OpenSanctions' crawler (`data.url`) [S49] and listed on its dataset page [S16]. A dated name, `full-oldb.20220503.zip`, is referenced by Senzing's mapper for the May 2022 release [S68].
- `full-oea-data.zip` (the example in the brief) is not referenced on ICIJ's download page; a WebFetch of it errored. Treat it as incorrect.

**Size, Last-Modified, ETag, range support:** UNVERIFIED. The download page shows no size or date [S61]. The sandbox proxy denies Bash access to `offshoreleaks-data.icij.org`, and WebFetch cannot retrieve binaries or a bucket listing. Indirect signal only: OpenSanctions' `icij_offshoreleaks` dataset (crawled monthly, last processed 2026-10-13) shows "Last change" 2026-08-06 [S16]; that date may reflect OpenSanctions' processing rather than a new ICIJ release. Spike C records the real headers on first run.

**Files inside** (file names exactly as opened by OpenSanctions' crawler [S49], same list in [S68]): `nodes-entities.csv`, `nodes-officers.csv`, `nodes-intermediaries.csv`, `nodes-others.csv`, `nodes-addresses.csv`, `relationships.csv`. ICIJ describes them as "several CSV files, one per type of node and one for all the relationships in the whole Offshore Leaks Database." [S61].

**Columns.** ICIJ publishes no per-file header list (the schema pages under `/schema/oldb` are empty stubs for a beta REST API [S65]). Two sources pin the column names down:
- OpenSanctions' production crawler pops every column it knows and audits the leftovers [S49]. For `relationships.csv` it consumes exactly `node_id_start, node_id_end, rel_type, link, status, start_date, end_date, sourceID`. For `nodes-addresses.csv` it consumes `node_id, address, name, countries, country_codes, sourceID, valid_until, note`. Across the four other node files it consumes the union `node_id, name, original_name, former_name, company_type, type, jurisdiction, jurisdiction_description, address, internal_id, incorporation_date, inactivation_date, struck_off_date, closed_date, dorm_date, status, service_provider, ibcRUC, country_codes, countries, note, valid_until, sourceID`.
- ICIJ's own data-shape guide and GraphQL schema document the properties per node type [S67].

The table below combines these per file. The header order, and the file that carries `internal_id`, are UNVERIFIED.

| File | Properties documented by ICIJ for this node type [S67] |
|---|---|
| nodes-entities.csv | `node_id, name, original_name, former_name, jurisdiction, jurisdiction_description, company_type, type, address, incorporation_date, inactivation_date, struck_off_date, dorm_date, closed_date, status, service_provider, ibcRUC, country_codes, countries, note, valid_until, sourceID` |
| nodes-officers.csv | `node_id, name, country_codes, countries, note, valid_until, sourceID` |
| nodes-intermediaries.csv | `node_id, name, address, status, country_codes, countries, valid_until, sourceID` |
| nodes-others.csv | `node_id, name, jurisdiction, jurisdiction_description, status, country_codes, countries, note, valid_until, sourceID` |
| nodes-addresses.csv | `node_id, address, name, country_codes, countries, valid_until, sourceID` (plus `note` per [S49]) |
| relationships.csv | `node_id_start, node_id_end, rel_type, link, status, start_date, end_date, sourceID` (from [S49]) |

ICIJ's field notes [S67 documentation/datashape.html]:
- Entity `address` "includes the registered address connected to the entity only when the address is the same as the one of the intermediary. Otherwise, the registered address information is stored in the address node connected to this Entity node through a registered_address relationship."
- `incorporation_date, inactivation_date, struck_off_date, dorm_date` are "dates for events in the company's development".
- `sourceID` is "Offshore Leaks Pandora Papers Panama Papers or Paradise Papers depending on the data's source".

Format history (Senzing mapper comments [S68]): in December 2020 ICIJ "went to a single database - 1 set of csv files for all"; in May 2022 it "changed format again": "Now all edges contain the sourceID value related to the project they belong to. We removed the _id columns, and kept only node_id columns to link between nodes and relationships."

**Relationship types (`rel_type`)** documented by ICIJ:
- `intermediary_of` (Intermediary -> Entity), `officer_of` (Officer or Intermediary -> Entity), `registered_address` (Intermediary, Officer or Entity -> Address).
- `underlying` (Officer or Intermediary -> Intermediary or Officer; "relationships such as NOMINEE_DIRECTOR_OF ... This applies to all relationship types beginning with NOMINEE_").
- `related_entity` (Entity -> Entity) [S67 datashape].
- ICIJ's GraphQL schema adds `connected_to`, `SAME_NAME_AS` and `SAME_ID_AS` [S67 graphql/schema.graphql].
- OpenSanctions' crawler handles `same_as` and `same_address_as` rows whose start node is an address [S49].

A complete official list of distinct `rel_type` values is UNVERIFIED; compute it in spike C.

**`link` values** (free text, lower-cased by OpenSanctions before lookup) [S49 icij_offshoreleaks.yml]. Examples by the FtM schema OpenSanctions maps them to:
- **Directorship:** "director of", "secretary of", "president", "treasurer", "chairman of", "board member", "nominee name of", "protector of", "trust settlor of", "authorised person / signatory of", "bank signatory of", "officer of", "alternate director", "power of attorney of", "legal representative of", "liquidator of", and dozens of job-title strings.
- **Ownership:** "shareholder of", "beneficiary of", "owner of", "beneficial owner", "partner of", "founder", "shareholder", "ubo", "person of significant control", "settlor", "grantor", "trustee of trust of".
- **Representation:** "intermediary of", "registered agent of", "registered office", "attorney of", "auditor", "accountant", "registrar and transfer agent of", and address-like strings ("registered address", "business address", "mailing address").
- **UnknownLink:** "connected to", "auditor of", "custodian of", "underlying company of", "member of", "linked to".
- **Skipped as resolution or duplicate hints:** "same name as", "same_name_as", "similar", "same as", "same id as", "same address as", "same company as", "similar company as", "same intermediary as", "probably same officer as", "same name and registration date as", "entity similar to", "related entity", "similar name and address as".

**Counts.** ICIJ publishes no per-type counts (UNVERIFIED officially). Third-party figures from "the full public ICIJ CSV export" in an arXiv paper dated August 2026 [S69]:
- Nodes: Entities 814,344; Officers 771,315; Intermediaries 25,629; Addresses 402,246.
- Relationships: `officer_of` 1,720,357; `registered_address` 832,721; `intermediary_of` 598,546; about 166,000 resolution edges; about 3.3 million in total.
- Beneficial-owner link subtypes: "ultimate beneficial owner" 25,883; "beneficiary of" 23,637; "owner of" 20,405; "beneficial owner (of)" 14,247.

### C.2 Licence

- Verbatim: "The ICIJ Offshore Leaks Database is licensed under the Open Database License and its contents under Creative Commons Attribution-ShareAlike license." The links point to ODbL 1.0 (`http://opendatacommons.org/licenses/odbl/1.0/`) and CC BY-SA 3.0 (`http://creativecommons.org/licenses/by-sa/3.0/`) [S61].
- Required attribution, verbatim: "Always cite the International Consortium of Investigative Journalists when using this data." [S61][S62]
- Commercial use is allowed by both licences, so ICIJ data has no non-commercial restriction.

**What ODbL share-alike would mean for a published derived graph** [S73]:
- A Neo4j dump or FtM export built from ICIJ data is a "Derivative Database" ("Extracting or Re-utilising the whole or a Substantial part of the Contents in a new Database").
- 4.4: "Any Derivative Database that You Publicly Use must be only under the terms of: i. This License; ii. A later version of this License similar in spirit to this License; or iii. A compatible license."
- 4.2 notice duties apply "If You Publicly Convey this Database, any Derivative Database, or the Database as part of a Collective Database".
- 4.6: "If You Publicly Use a Derivative Database or a Produced Work from a Derivative Database, You must also offer to recipients of the Derivative Database or Produced Work a copy in a machine readable form of:" (the derivative database or the alteration file).
- Produced Works (charts, reports, screenshots) are not share-alike, but 4.3 requires a notice "that Content was obtained from the Database ... and that it is available under this License".
- "Publicly" means "to Persons other than You or under Your control by either more than 50% ownership or by the power to direct their activities (such as contracting with an independent consultant)", so internal use inside the company, interns included, is not public use.
- Since NeonRadar ships loaders only, the repository creates no ODbL obligation. A user who publishes a graph built from ICIJ data must publish it under ODbL with notices and credit ICIJ.
- Analysis, not legal advice: a published database merging ICIJ (ODbL share-alike, which permits commercial reuse) with OpenSanctions (CC BY-NC) cannot satisfy both licences, so never publish merged graphs.

### C.3 ICIJ's standing disclaimer

FAQ, "Should I assume that everyone named in the database has committed a crime?" (verbatim, reassembled from consecutive fragments) [S62]:

> "No, there are legitimate uses for offshore companies and trusts. We do not intend to suggest or imply that any individuals, companies or other entities included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted improperly."

FAQ, "What should I keep in mind before using the data or publishing any findings?" (verbatim) [S62]:

> "The information contained in the ICIJ Offshore Leaks Database is just a fraction of the leaked files of the Pandora Papers, Paradise Papers, Bahamas Leaks, Panama Papers and Offshore Leaks investigations. We recommend caution before drawing any conclusions, as many people and entities have the same or similar names. We suggest you confirm the identities of any individuals or entities found in the database using addresses or other identifiable information. In the case of the corporate registries leaked to ICIJ as part of the Paradise Papers investigation, entities appearing in the database aren’t necessarily offshore companies, but can also be local businesses. The inclusion of a person or entity in the ICIJ Offshore Leaks Database is not intended to suggest or imply that they have engaged in illegal or improper conduct. The data comes directly from the leaked files ICIJ has received throughout different investigations and each set goes through a specific year. Keep in mind that some information, like the status of a company and its shareholders, might have changed over time."

The database pages show a "Disclaimer" heading whose text is rendered client-side, so it did not appear in fetched HTML [S61][S66]. Search-engine snippets show a variant beginning "There are legitimate uses for offshore companies and trusts. We do not intend to suggest or imply that any persons, ..." [S75]; that exact variant is UNVERIFIED today, so quote the FAQ text above. The About page adds: "While many of the activities carried out through offshore entities are perfectly legal" [S63].

### C.4 Neo4j dumps, sandbox, leaks and counts

- **Neo4j dumps:** yes, version 4 (`icij-offshoreleaks-4.4.26.dump`) and version 5 (`icij-offshoreleaks-5.13.0.dump`): "The data is also made available as Neo4j exported databases, you can download a version 4 or a version 5 as Neo4j dumped files." [S61].
- **Data packages repository** `ICIJ/offshoreleaks-data-packages`: Neo4j Browser guide, Bloom perspective, code examples, GraphQL API; last commit 2023-12-04; README.adoc targets Neo4j 4.4 (`data/icij-offshoreleaks-44.dump`, loaded with `neo4j-admin load`) [S67].
- **Neo4j Sandbox:** a sandbox-hosted guide exists at `guides.neo4j.com/sandbox/icij-offshoreleaks/` [S70], and a 2021 Neo4j blog links the Paradise Papers sandbox use case `sandbox.neo4j.com/?usecase=icij-paradise-papers` [S71]. Whether a launchable ICIJ sandbox exists today is UNVERIFIED.
- **Labels:** `Entity`, `Officer`, `Intermediary`, `Address`, `Other` [S67][S70].

Leaks covered, with officially published entity counts:

| Leak | Added | Published entity count | Source |
|---|---|---|---|
| Offshore Leaks (2013; Portcullis TrustNet, Commonwealth Trust Limited) | 2013-06-14 | "more than 100,000 additional offshore entities" (2016 article) | [S72][S63] |
| Panama Papers (2016; Mossack Fonseca) | 2016-05-09 | "nearly 214,000 offshore entities created in 21 jurisdictions" | [S72] |
| Bahamas Leaks (2016; Bahamas registry) | 2016-09-21 | "more than 175,000" | [S64] |
| Paradise Papers (2017-2018; Appleby plus seven registries) | 2017-11 to 2018-02 | "more than 290,000 entities" | [S64] |
| Pandora Papers (2021-2022; Alcogal, Fidelity, Alpha Consulting, seven more providers) | 2021-12-06, 2022-04-11, 2022-05-03 | "more than 15,000", "more than 2,000", "more than 9,000" | [S64] |

Totals: "more than 810,000 offshore companies, foundations and trusts" and "more than 750,000 names of people and companies"; records "cover more than 80 years up to 2020" and reach "more than 200 countries and territories" [S63][S62]. No additions after May 2022 are listed [S63]. China Leaks records were added on 2014-01-23 [S62]. Officer, intermediary and address counts per leak: UNVERIFIED (not published; see the third-party totals in C.1).

### C.5 Practical gotchas

- **Encoding:** ICIJ does not state an encoding (UNVERIFIED). Both reference consumers read the files as UTF-8 CSV with `"` quoting (Senzing: `encoding="utf-8", quotechar='"'`; OpenSanctions: `DictReader(..., delimiter=",", quotechar='"')`) [S68][S49]. Some names consist only of question marks (likely lost characters); OpenSanctions nulls names matching `^\?+$` and junk such as "360", "0" or "." [S49].
- **Duplicates:** "ICIJ did not merge records with similar names, so there may be duplicates." [S62]; "there may be duplicates, including in the same leak" [S63]. The same `node_id` can appear in more than one node file (Senzing: "they are the same real entity, just of a different type as in entity vs intermediary") [S68]. Probable duplicates are linked by `same_*` and `similar*` relationships, which OpenSanctions skips [S49]. ICIJ removes isolated nodes during publication [S69].
- **Officers are not all people:** Senzing's mapper notes "not all officers are actually people!" [S68]; OpenSanctions maps officers, intermediaries and others to `LegalEntity`, entities to `Company`, and upgrades schemata from relationship ranges [S49].
- **`sourceID`:** names the leak, and the relationships file carries it too since May 2022 [S67][S68]. The exact distinct values are UNVERIFIED (compute them). OpenSanctions stores it in FtM `publisher` [S49].
- **Country codes:** `country_codes` and `countries` are `;`-separated lists [S49][S68]. Codes are three-letter (ISO 3166-1 alpha-3 in most cases; FtM cleans "VGB" to `vg`). OpenSanctions' cleaning table shows non-standard or placeholder values: "XXX", "ZAM" (mapped to ZM), "Undetermined", "Not identified", "Netherlands Antilles", "Channel Islands" [S49]. ICIJ tags unmatched records "not identified" [S62]. OpenSanctions uses `jurisdiction_description` (a country name), not the `jurisdiction` code, for FtM `jurisdiction` [S49]. The `jurisdiction` code format is UNVERIFIED.
- **Dates:** mostly `DD-MON-YYYY` (the node page shows "Incorporated: 23-MAR-2006" [S66]). OpenSanctions tries `%d-%b-%Y`, `%b %d, %Y`, `%Y-%m-%d`, `%Y`, `%d/%m/%Y`, `%d.%m.%Y`, `%d/%m/%y` in that order, sets two-digit relationship years with base 1950, and keeps a fix-up table for impossible values (e.g. "5012-05-22" to 2012-05-22, "29/02/2006" to 2006-02, "31/02/2013" to 2013-02, "OCT-2019" to 2019-10) [S49]. FtM needs `format="%d-%b-%Y"` to parse these [S76].
- **Addresses:** address nodes often hold the text in `name` rather than `address` [S68]. Some address strings concatenate several addresses with `;` [S49]. OpenSanctions folds address nodes into the `address` text of linked entities instead of creating Address entities [S49]. NeonRadar can instead create FtM `Address` entities and link them with `addressEntity`.
- **Free-text roles:** `link` values are messy (typos, multiple roles in one string, values over 50 characters; Senzing truncates and maps ";"-joined values to "MULTIPLE USE") [S68][S49]. Keep the raw `link` in `role` and classify with a lookup table such as OpenSanctions'.
- **Currency of data:** each leak stops at a different year (Offshore Leaks "current through 2010", Panama Papers through 2015) [S62]. The node page shows "Data current through: 2015", probably the `valid_until` column, which OpenSanctions copies to `notes` [S66][S49] (inference, UNVERIFIED).
- **Re-publication via OpenSanctions:** the `icij_offshoreleaks` dataset (3,924,656 entities; `entities.ftm.json` 1.82 GB; `senzing.json` 1.16 GB; version 20261013173649-len) is labelled CC BY-NC 4.0 and sits in the `kyb` collection [S16]. Do not use it as the ICIJ source for a commercial-friendly loader.

### C.6 Spike C: ICIJ slice without committing data

1. `HEAD https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip` (follow redirects); log `Content-Length`, `Last-Modified`, `ETag`, `Accept-Ranges`. This fills the UNVERIFIED gaps in C.1.
2. **If `Accept-Ranges: bytes`:** wrap the URL in a small seekable HTTP range reader and pass it to `zipfile.ZipFile`. Python reads the central directory from the tail of the file, then streams only the start of `relationships.csv` and `nodes-entities.csv` (first 1,000 rows each) without downloading the archive. I verified this technique against a 5.97 MB wheel on files.pythonhosted.org: one 1 MiB range request (12.1% of the file) listed all members and read 1,000 lines of a member in 0.1 s [S76]. Whether ICIJ's host supports ranges is UNVERIFIED.
3. **Otherwise:** download once to a cache outside the repository (e.g. `~/.cache/neonradar/icij/full-oldb.LATEST.zip`), skip re-downloads with `If-None-Match`/`If-Modified-Since`, and read members straight from the zip (`zipfile.ZipFile(path).open("relationships.csv")` wrapped in `io.TextIOWrapper(..., encoding="utf-8", newline="")`) without extracting. Whether the first download finishes in under two minutes depends on the unknown zip size.
4. In both cases compute `Counter((row["rel_type"], row["link"].lower()))` over the slice (or the whole file once cached) and the distinct `sourceID` values. Map a few rows to FtM (`Company` for entities, `LegalEntity` for officers, `Ownership`/`Directorship`/`Representation`/`UnknownLink` by link lookup, `Address` plus `addressEntity` for addresses), then run spike B's Neo4j load.

Range-reader sketch (full tested version used for the verification above):

```python
class HTTPRangeFile(io.RawIOBase):           # seekable, read-only, 1 MiB blocks
    def __init__(self, url, session):
        head = session.head(url, allow_redirects=True, timeout=30); head.raise_for_status()
        self.session = session
        self.url, self.size, self.pos, self._cache = head.url, int(head.headers["Content-Length"]), 0, {}
    def seekable(self): return True
    def readable(self): return True
    def tell(self): return self.pos
    def seek(self, off, whence=0):
        self.pos = off if whence == 0 else self.pos + off if whence == 1 else self.size + off
        return self.pos
    def _block(self, i):
        if i not in self._cache:
            start = i << 20; end = min(start + (1 << 20), self.size) - 1
            r = self.session.get(self.url, headers={"Range": f"bytes={start}-{end}"}, timeout=60)
            assert r.status_code == 206, "server ignored Range"
            self._cache[i] = r.content
        return self._cache[i]
    def read(self, n=-1): ...                  # assemble from blocks, advance self.pos
# zipfile.ZipFile(io.BufferedReader(HTTPRangeFile(url, s), 1 << 20)).open("relationships.csv")
```

---

## Licence summary

| Source | Licence | Commercial use | Attribution text | Redistribution allowed | Notes |
|---|---|---|---|---|---|
| OpenSanctions bulk data (all collections, incl. `default`, `sanctions`, `peps`, `crime`, `debarment`) | CC BY-NC 4.0; OpenSanctions asserts database rights [S48] | Needs a data licence: "Any use inside a for-profit business requires a data license." [S18]; evaluation before licensing is invited [S17] | None published (UNVERIFIED); CC BY-NC 4.0 s.3(a)(1) applies: creator, copyright notice, licence notice and link, disclaimer, link to material, mark modifications [S74] | Non-commercially under CC BY-NC with attribution; licensed customers may not pass data to third parties without a Reseller licence [S20] | Free API keys only for public-interest journalists, nonprofits, affiliated academics, and public institutions of UA/GE/MD [S18]. Pre-2024 history needs authenticated access [S22]. Never commit derived fixtures. |
| OpenSanctions hosted API | API GTC (202609) plus the data licence | Paid credits, EUR 0.10 to 0.03 per query; 2,000 free credits on business sign-up [S42][S30] | n/a | n/a | Key always required (`Authorization: ApiKey`) [S40]; 429 on quota [S41] |
| OpenSanctions republication of ICIJ (`icij_offshoreleaks`) | Labelled CC BY-NC 4.0 by OpenSanctions [S16] | Needs an OpenSanctions licence | As above, plus ICIJ citation | As above | Use ICIJ's original files instead |
| yente, followthemoney, nomenklatura, rigour, zavod, normality (code) | MIT [S46][S50][S51][S52][S53][S47] | Yes | Keep the MIT copyright notice | Yes | PyICU sdist build needs ICU headers |
| ICIJ Offshore Leaks Database | ODbL 1.0 (database); CC BY-SA 3.0 (contents) [S61] | Yes | "Always cite the International Consortium of Investigative Journalists when using this data." [S61] plus ODbL 4.2/4.3 notices | Yes; a publicly used Derivative Database must be ODbL (share-alike) and offered in machine-readable form; Produced Works need a notice [S73] | Internal company use is not "Public" [S73]; show the ICIJ disclaimer (C.3); never publish an ICIJ plus OpenSanctions merged database |

---

## Sources (all checked 2026-10-16)

OpenSanctions (read via WebFetch unless noted):
- [S1] https://www.opensanctions.org/docs/bulk/ (bulk data overview; no login or API key; licence statements)
- [S2] https://www.opensanctions.org/docs/bulk/updates.md (latest URL pattern, update cadence, polling, IDs and referents)
- [S3] https://www.opensanctions.org/docs/bulk/formats.md (format list and recommendation)
- [S4] https://www.opensanctions.org/docs/bulk/json.md (entities.ftm.json, targets.nested.json)
- [S5] https://www.opensanctions.org/docs/bulk/csv/ (targets.simple.csv columns and delimiters)
- [S6] https://www.opensanctions.org/docs/statements.md (statements.csv columns, canonical_id)
- [S7] https://www.opensanctions.org/docs/bulk/delta.md (delta files)
- [S8] https://www.opensanctions.org/docs/bulk/delivery-service.md (delivery.opensanctions.com, token header)
- [S9] https://www.opensanctions.org/datasets/ (collections index)
- [S10] https://www.opensanctions.org/datasets/default/ (counts, version, file sizes, artifact URLs)
- [S11] https://www.opensanctions.org/datasets/sanctions/
- [S12] https://www.opensanctions.org/datasets/peps/
- [S13] https://www.opensanctions.org/datasets/crime/
- [S14] https://www.opensanctions.org/datasets/debarment/
- [S15] https://www.opensanctions.org/datasets/regulatory/
- [S16] https://www.opensanctions.org/datasets/icij_offshoreleaks/ (OpenSanctions' ICIJ conversion, CC BY-NC label, source zip URL)
- [S17] https://www.opensanctions.org/licensing/ (licence options, evaluation wording, footer licence)
- [S18] https://www.opensanctions.org/docs/commercial/exemption/ (free and non-commercial use; free key programme)
- [S19] https://www.opensanctions.org/docs/commercial/faq/ (commercial FAQ; no open-source or attribution terms)
- [S20] https://www.opensanctions.org/docs/terms/ and https://www.opensanctions.org/docs/terms/data/202509/ (GTC for Data Licensing, effective 2025-09-01)
- [S21] https://www.opensanctions.org/changelog/ (index of entries 1 to 52)
- [S22] https://www.opensanctions.org/changelog/25/ (historical data requires authenticated access)
- [S23] https://www.opensanctions.org/changelog/24/ (enable HTTP 3xx support)
- [S24] https://www.opensanctions.org/changelog/45/ (HTTP redirects from data.opensanctions.org to /artifacts/)
- [S25] https://www.opensanctions.org/changelog/20/ (pre-announcement of FtM 4.0)
- [S26] https://www.opensanctions.org/changelog/40/ (statements.csv format change)
- [S27] https://www.opensanctions.org/changelog/39/ (new property abbreviation)
- [S28] https://www.opensanctions.org/changelog/13/ (target files generated from topics; 22-topic list)
- [S29] https://www.opensanctions.org/changelog/23/ (PEP level of influence classification)
- [S30] https://www.opensanctions.org/changelog/51/ (API credit bundles)
- [S31] https://www.opensanctions.org/changelog/36/ (EU FSF name translations moved to alias)
- [S32] https://www.opensanctions.org/changelog/1/ (nationality and citizenship split)
- [S33] https://www.opensanctions.org/changelog/31/ (KYB/Graph API discontinued)
- [S34] https://www.opensanctions.org/changelog/18/ (do not use the all dataset)
- [S35] https://www.opensanctions.org/docs/entities.md (entity JSON example and field meanings; Interval warning)
- [S36] https://www.opensanctions.org/docs/topics.md (risk topic definitions)
- [S37] https://www.opensanctions.org/docs/glossary.md (target, collection, entity of interest)
- [S38] https://www.opensanctions.org/docs/coverage/pep/using.md (PEP modelling and filtering)
- [S39] https://www.opensanctions.org/docs/coverage/pep/methodology.md (RCAs, retention windows)
- [S40] https://www.opensanctions.org/docs/api/authentication.md (API key header)
- [S41] https://www.opensanctions.org/docs/api/faq.md (metering, quotas, credit expiry)
- [S42] https://www.opensanctions.org/api/ (pricing, 2,000 free credits)
- [S43] https://www.opensanctions.org/docs/on-premise.md (self-hosting, sizing, licence requirement)
- [S44] https://yente.followthemoney.tech/ (yente overview, MIT)
- [S45] https://yente.followthemoney.tech/delivery/ (civic and commercial manifests, licensing)
- [S46] https://raw.githubusercontent.com/opensanctions/yente/main/manifests/civic.yml, .../manifests/commercial.yml, .../LICENSE (read with curl)
- [S47] https://www.opensanctions.org/faq/6/replication/ (open-source components are MIT; building your own data); also https://www.opensanctions.org/faq/api/embed/ and https://www.opensanctions.org/docs/about.md (no attribution text found)
- [S48] https://raw.githubusercontent.com/opensanctions/opensanctions/main/README.md, .../COPYRIGHT.md, .../LICENSE (read with curl)
- [S49] https://github.com/opensanctions/opensanctions, blobless git clone at commit d8d0c9c1bb34 (2026-10-15): `datasets/_global/icij_offshoreleaks/{crawler.py,icij_offshoreleaks.yml,README.md}`, `datasets/_externals/ext_icij_offshoreleaks.yml`, `meta/programs/ICIJ-*.yml`, `zavod/zavod/archive/__init__.py`, `zavod/zavod/entity.py`, `zavod/zavod/exporters/*.py`, `zavod/zavod/helpers/positions.py`, `zavod/zavod/stateful/positions.py`, `datasets/ng/join_dots/crawler.py`

FollowTheMoney and libraries:
- [S50] https://pypi.org/pypi/followthemoney/json plus per-version JSON for 3.8.5, 4.0.0, 4.11.0, wheels for 4.0.0, 4.5.0, 4.8.0, 4.9.2 and 4.10.2 from files.pythonhosted.org (schema diffs), and https://pypi.org/pypi/pyicu/json
- [S51] https://pypi.org/pypi/nomenklatura/json and https://pypi.org/pypi/nomenklatura/3.17.5/json
- [S52] https://pypi.org/pypi/rigour/json
- [S53] https://pypi.org/pypi/normality/json
- [S54] https://pypi.org/pypi/yente/json
- [S55] followthemoney 4.11.0 sdist (https://files.pythonhosted.org/, `followthemoney-4.11.0.tar.gz`) and https://github.com/opensanctions/followthemoney, git clone at commit 9433b3d50d63 (2026-10-05): `followthemoney/schema/*.yaml`, `__init__.py`, `entity.py`, `proxy.py`, `model.py`, `schema.py`, `property.py`, `util.py`, `statement/*.py`, `types/topic.py`, `cli/util.py`, `cli/exports.py`, `export/neo4j.py`, `docs/python/index.md`, `docs/python/entity.md`, `docs/docs/statements.md`, `docs/explorer/types/topic.md`, `docs/explorer/types/name.md`
- [S56] https://github.com/opensanctions/followthemoney/releases/tag/v4.0.0 (release notes, 13 July 2025)
- [S57] https://followthemoney.tech/python/ (Python SDK docs, pyicu note)
- [S58] https://followthemoney.tech/explorer/schemata/Ownership/ (schema explorer; featured semantics)
- [S59] nomenklatura wheels 3.17.5 and 4.17.2 from files.pythonhosted.org (module listings, `nomenklatura/__init__.py`, `nomenklatura/entity.py` in 3.17.5, `nomenklatura/enrich/wikidata.py` in 4.17.2)
- [S60] https://raw.githubusercontent.com/opensanctions/rigour/main/README.md and .../LICENSE; installed rigour 2.5.0 `rigour/text/translit.py`

ICIJ and related:
- [S61] https://offshoreleaks.icij.org/pages/database (download links, licence, citation)
- [S62] https://offshoreleaks.icij.org/pages/faq (disclaimer, duplicates, update history, citation)
- [S63] https://offshoreleaks.icij.org/pages/about (leaks, totals, limitations)
- [S64] https://offshoreleaks.icij.org/pages/data (per-leak additions and counts)
- [S65] https://offshoreleaks.icij.org/schema/oldb and https://offshoreleaks.icij.org/schema/oldb/entity (beta REST API schema stubs)
- [S66] https://offshoreleaks.icij.org/nodes/10000001 (node page fields, date format)
- [S67] https://github.com/ICIJ/offshoreleaks-data-packages, git clone at commit cfa316c0d58e (2023-12-04): `README.md`, `README.adoc`, `relate.project-install.json`, `graphql/schema.graphql`, `documentation/datashape.html`
- [S68] https://github.com/Senzing/mapper-icij, git clone at commit af3706690b50 (2026-10-15): `README.md`, `src/icij_mapper.py`
- [S69] https://arxiv.org/html/2609.26171 (J. Bingham, arXiv v1 dated 10 Aug 2026; third-party node and relationship counts)
- [S70] https://guides.neo4j.com/sandbox/icij-offshoreleaks/index.html (Neo4j sandbox guide)
- [S71] https://neo4j.com/blog/developer/exploring-the-pandora-papers-with-neo4j/ (2021; Paradise Papers sandbox use case link)
- [S72] https://www.icij.org/inside-icij/2016/05/icij-releases-panama-papers-offshore-company-data/ (Panama Papers and 2013 counts)

Licences:
- [S73] https://opendatacommons.org/licenses/odbl/1-0/ (ODbL 1.0 text)
- [S74] https://creativecommons.org/licenses/by-nc/4.0/legalcode.en (CC BY-NC 4.0 legal code)

Other:
- [S75] Web search result pointers to node pages carrying the header disclaimer variant (e.g. https://offshoreleaks.icij.org/nodes/81027198); used only as a pointer, variant UNVERIFIED
- [S76] Local verification runs in a Python 3.12.3 virtual environment with followthemoney 4.11.0, rigour 2.5.0, normality 3.1.0, PyICU 2.16.2: FtM API snippet, validation behaviour, property and edge listings for all schemata above, type cleaning, `ftm export-cypher` output, rigour/normality transliteration, HTTP range zip-read test against https://files.pythonhosted.org (rigour 2.5.0 cp312 wheel)
