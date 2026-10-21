# NeonRadar Phase 2 research: bulk sources and graph loading

- Checked: Sunday 18 October 2026. Every source in the Sources list was read on that date.
- Scope: facts the Phase 2 build spec needs for production loaders that read bulk files (Companies House, GLEIF, ICIJ), the ownership graph, and loading about 500,000 nodes and 2 million relationships into Neo4j 5.26.32 Community in under 10 minutes on a 16 GB laptop (plus a small mode of about 10,000 nodes).
- Builds on the Phase 1 notes in `neonradar-phase1/kit/research/` (`sources-ch-gleif.md` A3 to A5 and B1 to B4, `sources-opensanctions-ftm-icij.md` part C, `neo4j.md` section 6). Facts verified there are not repeated unless they changed or were time-sensitive. Section 12 lists Phase 1 statements this note corrects.
- Tags such as [B12] point to the Sources list. "Community" marks third-party code, forum posts by non-staff, or third-party pages. "UNVERIFIED" marks anything not confirmed. "Observed" marks a live API response read on 18 October.
- No personal data is copied here. Examples use invented placeholder values only.
- Not legal advice (section 10 is analysis).

## 0. Answers for the spec writer

1. **Free Company Data Product.** Snapshot 2026-10-01, monthly within 5 working days of month end: `BasicCompanyDataAsOneFile-2026-10-01.zip` (471 MB) or `BasicCompanyData-2026-10-01-part1_7.zip` to `part7_7.zip` (50 to 70 MB each) [B1]. UTF-8 CSV with 55 columns; 14 header cells start with a space (for example `" CompanyNumber"`), so strip them; values are double-quoted, dates `dd/mm/yyyy`, missing values `""` [B43][B17][B19]. 2026 defects: a 56-field row (a fifth SIC code), an empty row in part 4 of 7, HTML entities such as `&#039;` and `&AMP;` in names [B39][B18]. Live register only, 5,695,465 rows in mid-2026 (community) [B39]. `CompanyCategory` strings include `Private Limited Company`, `PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital)` and `Overseas Entity`; OE inclusion rests on third-party evidence (UNVERIFIED) [B45].
2. **PSC snapshot.** 2026-10-17, daily before 10:00 GMT: `persons-with-significant-control-snapshot-2026-10-17.zip` or 33 parts `psc-snapshot-2026-10-17_1of33.zip` to `_33of33.zip` (2,202 MB in total) [B4]. NDJSON lines `{"company_number": ..., "data": {...}}`; the last line is a totals record with no `company_number`, kind `totals#persons-of-significant-control-snapshot`, three counts and `generated_at` (November 2024: 12,799,821 PSCs, 774,422 statements, 77 exemptions) [B43]. Kinds: four PSC kinds, `*-beneficial-owner` kinds under `OE` numbers carrying `is_sanctioned`, statements, `exemptions`, totals [B43][B39]. About 38.5% of records concern companies no longer live [B39]. No project resolves corporate PSCs robustly offline (3.5); use rule 3.6: UK test on the registry fields, zero-pad digits to 8, require a hit in the company index plus a name check.
3. **`natures_of_control`.** 86 values in `psc_descriptions.yml` (24 company, 24 LLP, 12 Scottish partnership, 26 overseas entity); file last changed 2025-11-07 (`0d3fb78`), repository head 2026-09-11 (`05067ab`) [B5]. Statutory bands: `25-to-50` is `(25, 50]`, `50-to-75` is `(50, 75)` ("less than 75%"), `75-to-100` is `[75, 100]` ("75% or more"): exclusive lower bounds for the first two, inclusive for the top band [B28][B29][B30]. The API long descriptions ("not more than 75%", "more than 75%") contradict the statute; the short ones match it. Overseas entity values: "more than 25%", `(25, 100]` [B31]. Appoint or remove, significant influence or control, and nominee values carry no percentage.
4. **Officers API.** `person_number` (string) is on `/company/{n}/officers` items and absent from `/officers/{id}/appointments` items (official specs and Companies House's own service code) [B6][B7][B8]. Community posts (January 2025, February 2026): 12 digits, an 8-digit person part plus a 4-digit counter, and one party seen under several numbers; no staff answer [B21][B22]. Page size: appointments default 35, maximum 50; company officers default 35, no cap in the service code [B8]. Rate limit unchanged at 600 requests per 5 minutes, no 2026 notice [B9]. Officer bulk products 195, 198 and 216 remain by request to `bulkproducts@companieshouse.gov.uk`; price, licence and terms unpublished (UNVERIFIED) [B23][B10].
5. **GLEIF.** Discovery: `https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest` (also `/{lei2|rr|repex}/latest`) [B48][B51]. Publish 2026-10-17 16:00: LEI-CDF CSV zip 504,971,197 bytes, 3,465,810 records; RR-CDF 24,497,804 bytes, 491,462; reporting exceptions 62,274,887 bytes, 6,424,906 [B48]. UK: 119,382 LEIs at RA000585 to RA000587, 62,736 active and issued [B50]. CSV columns are dotted paths (`LEI`, `Entity.LegalName`, `Entity.RegistrationAuthority.RegistrationAuthorityEntityID`, ...; section 6.2); RR 2.1 and repex headers UNVERIFIED [B60][B62]. Level 2 is accounting consolidation, not ownership [B55]. The 19 October to 4 November notice names no services and `lei2/latest` served a stale publish today: cache the files now [B58][B49].
6. **ICIJ.** Nothing new: same `full-oldb.LATEST.zip` URL, no size or date shown, no data added after 2022 [B64]; Last-Modified and size UNVERIFIED (host blocked to the shell). No GitHub parser hard-codes the header rows; a community copy on Hugging Face (January 2025) gives exact headers for `nodes-others.csv` and `nodes-intermediaries.csv` and uncompressed sizes (626 MB in total) [B65]. Read every file by column name.
7. **Neo4j.** `neo4j` 6.4.1 and `neo4j-rust-ext` 6.4.1.0 (15 October 2026; the extension has cp314 wheels and claims a "3x to 10x speedup") [B71][B72][B70]. `execute_query` runs in a transaction function, so `CALL { } IN TRANSACTIONS` fails there; use `session.run` (corrects Phase 1) [B71]. On 5.26: `CONCURRENT TRANSACTIONS` since 5.21, `ON ERROR CONTINUE|BREAK|FAIL` since 5.7, no `ON ERROR RETRY` [B69]. `neo4j-admin database import full` options are in section 8.3; Community has no `STOP DATABASE`, so stop the server and run a one-off container on the same `/data` volume [B68][B73]. Recommendation: not needed for 500,000 nodes and 2 million relationships; use batched `UNWIND` writes and keep the importer as an optional rebuild path [B74].
8. **DuckDB.** 1.5.6 (28 September 2026), MIT, cp314 wheels, `json` built in [B75][B84]. No core ZIP support (`gzip` and `zstd` only) [B76][B77]; the `zipfs` community extension (MIT) downloads from `http://community-extensions.duckdb.org` at `INSTALL`, a runtime network call [B81][B84]. Extract members to a temp file instead (fastest), or pass a file object or an fsspec zip filesystem (needs `fsspec`) [B84]. Read the PSC NDJSON with `columns={company_number: 'VARCHAR', data: 'JSON'}`; auto-detection fails on the totals line [B84]. Defaults: `memory_limit` 80% of RAM, `threads` = cores, `maximum_object_size` 16 MB; set `preserve_insertion_order=false` [B78][B76][B79]. Measured on 2 vCPUs: orjson 230,000 lines/s, DuckDB up to 860,000; the full PSC file takes about 1 to 2 minutes.
9. **Data protection (analysis, not legal advice).** Companies House says reusers "become controllers of your personal data" and "third-parties are responsible for making sure they comply with data protection law" [B12][B13]. UK GDPR Article 14 covers data taken from the register: privacy information within one month, naming the source and "whether it came from publicly accessible sources"; since 5 February 2026 the disproportionate effort exemption is Article 14(5)(e), with factors in (6) and safeguards in (7) "including by making the information available publicly" [B32]. ICO: treat it as "the exception, not the rule", document it, publish privacy information, consider a DPIA [B33]. The likely lawful basis is legitimate interests (three-part test; guidance updated 23 March 2026) [B35][B36].
10. **Statistics.** 5,516,377 companies on the register at end June 2026 (next release 29 October 2026) [B14]; 5,720,308 corporate bodies at 31 March 2026, including 33,137 overseas entities [B15]. No official PSC-by-kind statistics found. OpenSanctions' live-company PSC dataset on 14 October 2026: 7,540,242 Person, 6,488,510 Company, 11,263 Organization entities [B40].

## 1. Method and limits

- The shell reached only PyPI, npm and GitHub (git clone works; the GitHub REST API refused the session token). Companies House, GLEIF, ICIJ and DuckDB extension hosts were refused by the egress proxy, so no bulk file was downloaded. Pages were read with a web fetch tool, which cannot open ZIP archives.
- Evidence about the inside of the Companies House files comes from (a) test fixtures that Open Ownership extracted from real snapshots (`bods-uk-psc-pipeline`, AGPL-3.0) [B43], (b) OpenSanctions crawler code and commit messages (MIT) [B39], and (c) forum posts. Those fixtures contain real personal data. Only aggregate shapes (keys, kinds, counts, patterns) were computed from them; nothing was copied. NeonRadar must not vendor them.
- Local tests ran in a Python 3.14.6 virtual environment (uv) with DuckDB 1.5.6, orjson 3.13.0, fsspec 2026.9.0 and neo4j 6.4.1 on a 2 vCPU, 7 GB container, using generated placeholder files shaped like the Companies House files (scripts in the scratchpad, see [B84]). Neo4j itself could not be run (Docker Hub and Neo4j downloads blocked).

## 2. Companies House Free Company Data Product (Q1)

### 2.1 Files

| Item | Value |
|---|---|
| Page | `https://download.companieshouse.gov.uk/en_output.html` [B1] |
| Snapshot | 2026-10-01; "updated within 5 working days of the previous month end", compiled to the end of the previous month [B1] |
| One file | `BasicCompanyDataAsOneFile-2026-10-01.zip`, 471 MB [B1] |
| Parts | `BasicCompanyData-2026-10-01-part1_7.zip` 69 MB, parts 2 to 6 70 MB each, `part7_7` 50 MB (469 MB in total) [B1] |
| Member names | `BasicCompanyData-YYYY-MM-DD-partN_7.csv` inside each part (Community) [B18]; iterate `namelist()` rather than hard-coding |
| Terms | "provided free of charge and will not be supported"; no licence text on the page [B1] |
| Order | "The data in the files is in alphabetical order based on Company Name" [B3] |

### 2.2 Exact header

Literal header line, from a fixture cut from the real file (Community, committed 2025-01-07) [B43]. The header cells are not quoted:

```text
CompanyName, CompanyNumber,RegAddress.CareOf,RegAddress.POBox,RegAddress.AddressLine1, RegAddress.AddressLine2,RegAddress.PostTown,RegAddress.County,RegAddress.Country,RegAddress.PostCode,CompanyCategory,CompanyStatus,CountryOfOrigin,DissolutionDate,IncorporationDate,Accounts.AccountRefDay,Accounts.AccountRefMonth,Accounts.NextDueDate,Accounts.LastMadeUpDate,Accounts.AccountCategory,Returns.NextDueDate,Returns.LastMadeUpDate,Mortgages.NumMortCharges,Mortgages.NumMortOutstanding,Mortgages.NumMortPartSatisfied,Mortgages.NumMortSatisfied,SICCode.SicText_1,SICCode.SicText_2,SICCode.SicText_3,SICCode.SicText_4,LimitedPartnerships.NumGenPartners,LimitedPartnerships.NumLimPartners,URI,PreviousName_1.CONDATE, PreviousName_1.CompanyName, PreviousName_2.CONDATE, PreviousName_2.CompanyName,PreviousName_3.CONDATE, PreviousName_3.CompanyName,PreviousName_4.CONDATE, PreviousName_4.CompanyName,PreviousName_5.CONDATE, PreviousName_5.CompanyName,PreviousName_6.CONDATE, PreviousName_6.CompanyName,PreviousName_7.CONDATE, PreviousName_7.CompanyName,PreviousName_8.CONDATE, PreviousName_8.CompanyName,PreviousName_9.CONDATE, PreviousName_9.CompanyName,PreviousName_10.CONDATE, PreviousName_10.CompanyName,ConfStmtNextDueDate, ConfStmtLastMadeUpDate
```

The 14 cells with a leading space:

```text
' CompanyNumber', ' RegAddress.AddressLine2', ' PreviousName_1.CompanyName', ' PreviousName_2.CONDATE',
' PreviousName_2.CompanyName', ' PreviousName_3.CompanyName', ' PreviousName_4.CompanyName',
' PreviousName_5.CompanyName', ' PreviousName_6.CompanyName', ' PreviousName_7.CompanyName',
' PreviousName_8.CompanyName', ' PreviousName_9.CompanyName', ' PreviousName_10.CompanyName',
' ConfStmtLastMadeUpDate'
```

Corroboration: a forum post (16 July 2024, no staff reply) names `" CompanyNumber"`, `" RegAddress.AddressLine2"` and `" PreviousName_x.CompanyName"` [B17]; OpenSanctions strips every header cell and reads `CountryOfOrigin`, `SICCode.SicText_1` to `_4`, `PreviousName_1.CONDATE` and `Accounts.AccountRefDay` [B39]. The official field list PDF uses logical names, not these literals (for example `CountryofOrigin`, `AccountingRefDay`, `SICCode1`) [B2]. DuckDB's CSV reader trims the leading spaces itself (Observed, section 9.5).

### 2.3 Encoding, quoting, values

- UTF-8. In August 2023 a release replaced characters with `?` (0x3F); staff said "Yes, we are aware of the encoding issue" and regenerated the file [B19]. Community readers decode it as UTF-8 [B46]. The fixture has no byte order mark [B43]. Line endings: UNVERIFIED (use `newline=""` with Python's `csv`).
- Data values are double-quoted, including empty ones (`""`) [B43]. DuckDB turns quoted empty strings into NULL unless `allow_quoted_nulls=false` (Observed) [B84].
- Dates are `dd/mm/yyyy` (OpenSanctions sets `formats: ["%d/%m/%Y"]`) [B39][B43].
- `SICCode.SicText_N` holds code and text in one cell, `"70100 - Activities of head offices"` style; split on the first `" - "` [B39][B43].
- `URI` is `http://business.data.gov.uk/id/company/{CompanyNumber}` [B43].
- `CompanyNumber` is an 8-character string (zero-padded digits or a 2-letter prefix plus 6 digits); never cast to integer.

### 2.4 Quirks seen 2024 to 2026

| Quirk | Evidence | Loader rule |
|---|---|---|
| Header cells with a leading space | [B17][B43] | Strip header cells before mapping |
| A row with 56 fields (five SIC codes) shifted every later column; it crashed the OpenSanctions run on 2026-09-02 | Community [B39] | Compare field count with header; log and skip |
| Unexpected empty row in `part4_7`, reported for May, June, July (line 476129) and August 2026 (line 454678) | Community [B18] | Skip empty rows |
| HTML character references, escaped before upper-casing: `&#039;`, `&AMP;`, `&#128169;` | Community [B39] | Decode only complete references with `html.unescape` (regex below) |
| Address fields holding only punctuation, digits or a bare outward postcode | Community [B39] | Treat as missing |
| Mis-encoded release (August 2023) | CH staff [B19] | Validate UTF-8 strictly; fail loudly |

OpenSanctions' reference pattern, which leaves a literal ampersand such as `A&B LIMITED` untouched [B39]:

```python
HTML_ENTITY_RE = re.compile(r"&(?:#\d{1,7}|#[xX][0-9a-fA-F]{1,6}|[A-Za-z][A-Za-z0-9]{1,31});")
name = HTML_ENTITY_RE.sub(lambda m: html.unescape(m.group(0)), name)
```

### 2.5 Categories, statuses and overseas entities

- `CompanyCategory` is `corporate_body_type_desc` and `CompanyStatus` is `action_code_desc` in the official field list [B2].
- Category strings, with counts as of June 2024, from a third-party platform whose labels match the bulk file style (Community) [B45]:

```text
Private Limited Company (5,040,169)
PRI/LTD BY GUAR/NSC (Private, limited by guarantee, no share capital) (116,245)
Limited Partnership (58,503)
Limited Liability Partnership (51,889)
PRI/LBG/NSC (Private, Limited by guarantee, no share capital, use of 'Limited' exemption) (38,527)
Charitable Incorporated Organisation (35,380)
Community Interest Company (32,334)
Overseas Entity (30,740)
Other company type (14,710)
Registered Society (10,563)
Scottish Charitable Incorporated Organisation (6,405)
Public Limited Company (4,665)
Private Unlimited Company (4,234)
Royal Charter Company (898)
Investment Company with Variable Capital (617)
Scottish Partnership (267)
United Kingdom Economic Interest Grouping (258)
Industrial and Provident Society (160)
Private Unlimited (95)
Investment Company with Variable Capital(Umbrella) (69)
United Kingdom Societas (17)
Old Public Company (16)
PRIV LTD SECT. 30 (Private limited company, section 30 of the Companies Act) (15)
Investment Company with Variable Capital (Securities) (9)
Protected Cell Company (5)
Other Company Type (3)
Converted/Closed (1)
```

- The string is `Overseas Entity`, not `Registered Overseas Entity`. That list, the official count of 33,137 overseas entities among 5,720,308 corporate bodies [B15], and the mid-2026 row count of 5,695,465 [B39] together suggest OE entities (numbers `OE` plus 6 digits) are in the product. Companies House does not say so: UNVERIFIED. The loader must accept OE numbers either way.
- Live only: "BasicCompanyDataAsOneFile covers only companies still on the register (5,695,465 rows, no Dissolved status, DissolutionDate always empty)" (OpenSanctions commit, 7 August 2026) [B39].
- Full list of `CompanyStatus` strings: UNVERIFIED (count them on first download).

### 2.6 Company number prefixes (for validation)

Official list (URI customer guide, May 2012): `AC`, `FC`, `GE`, `GN`, `GS`, `IC`, `IP`, `LP`, `NA`, `NF`, `NI`, `NL`, `NO`, `NP`, `NR`, `NZ`, `OC`, `R0`, `RC`, `SA`, `SC`, `SF`, `SI`, `SL`, `SO`, `SP`, `SR`, `SZ`, `ZC`; Scottish prefixes start with `S`, Northern Ireland with `N` or `R0` [B16]. Newer prefixes named by the community: `OE` (overseas entity), `FE`, `PC`, `SG`, `CE`/`CS` (charitable incorporated organisations), `SE` [B25][B47]. Use the prefix only as a consistency check (for example `SC` should pair with GLEIF `RA000587`).

## 3. PSC snapshot (Q2)

### 3.1 Files

- Page `https://download.companieshouse.gov.uk/en_pscdata.html`, "Last Updated: 17/10/2026 08:09hrs", "updated every morning before 10am GMT", compiled to the end of the previous day, files overwritten daily, free and unsupported [B4].
- `persons-with-significant-control-snapshot-2026-10-17.zip` (no size shown) or `psc-snapshot-2026-10-17_1of33.zip` to `_33of33.zip`: 1 to 30 are 67 to 75 MB, 31 is 42 MB, 32 is 31 MB, 33 is 3 MB, 2,202 MB in total [B4]. In November 2024 there were 28 parts (Community) [B43].
- Member file names inside the zips: UNVERIFIED; iterate `namelist()`.
- Size on disk: Open Ownership reports "approximately 12GB" uncompressed for the PSC and company files together (2024) [B43].
- A July 2024 outage was a delay, not a stop: "this has not been stopped, but rather delayed" (CH staff, 3 July 2024) [B20].

### 3.2 Line format and the totals line

- One JSON object per line: `{"company_number": "...", "data": {...}}`, where `data` is the API resource for the PSC, statement or exemptions record, with `links.self` [B39][B43].
- The last line of the single-file snapshot is a totals record with no `company_number` (Community, fixture of the 22 November 2024 snapshot) [B43]:

```json
{"data":{"kind":"totals#persons-of-significant-control-snapshot","persons_of_significant_control_count":12799821,"statements_count":774422,"exemptions_count":77,"generated_at":"2024-11-22T03:43:03Z"}}
```

- Open Ownership skips it by kind and uses `generated_at` as the data date; OpenSanctions skips any line without `company_number` [B43][B39]. Whether each of the 33 parts carries a totals line, or only the last: UNVERIFIED.
- Use the totals line as a completeness check: data lines read should equal the sum of the three counts.
- Line count today: about 15 million ("~15M lines", OpenSanctions comment, August 2026) [B39].

Placeholder example of a corporate PSC line (invented values):

```json
{"company_number":"01234567","data":{"kind":"corporate-entity-person-with-significant-control","name":"EXAMPLE HOLDINGS LIMITED","identification":{"legal_authority":"Companies Act 2006","legal_form":"Private Limited Company","place_registered":"Companies House","country_registered":"England","registration_number":"7654321"},"natures_of_control":["ownership-of-shares-75-to-100-percent","voting-rights-75-to-100-percent"],"notified_on":"2016-04-06","address":{"premises":"1","address_line_1":"Example Street","locality":"Exampletown","postal_code":"AB1 2CD","country":"England"},"etag":"0000","links":{"self":"/company/01234567/persons-with-significant-control/corporate-entity/EXAMPLEID"}}}
```

### 3.3 `data.kind` values

```text
individual-person-with-significant-control          seen in snapshot [B43]
corporate-entity-person-with-significant-control    seen [B43]
legal-person-person-with-significant-control        seen [B43] (the API spec also spells it legal-person-with-significant-control)
super-secure-person-with-significant-control        seen; keys ceased, description, etag, kind, links only [B43]
individual-beneficial-owner                         handled by both parsers; not in the fixtures [B39][B43]
corporate-entity-beneficial-owner                   seen under OE numbers with is_sanctioned, principal_office_address [B43]
legal-person-beneficial-owner                       seen under OE numbers with is_sanctioned, principal_office_address [B43]
super-secure-beneficial-owner                       handled by Open Ownership; OpenSanctions would log it as unknown [B43][B39]
persons-with-significant-control-statement          seen; keys ceased_on, etag, kind, links, notified_on, statement [B43]
exemptions                                          handled by both parsers; 77 in November 2024 [B39][B43]
totals#persons-of-significant-control-snapshot      last line [B43]
```

- In the first 10,000 records of the November 2024 snapshot: 9,108 individual, 879 corporate entity, 13 legal person PSCs; 2,175 had `ceased_on` (Community aggregate) [B43].
- `exemptions` records follow the API exemptions resource: `kind`, `exemptions` with optional keys `psc_exempt_as_trading_on_regulated_market`, `psc_exempt_as_shares_admitted_on_market`, `psc_exempt_as_trading_on_uk_regulated_market`, `psc_exempt_as_trading_on_eu_regulated_market`, `disclosure_transparency_rules_chapter_five_applies`, each `{exemption_type, items: [{exempt_from, exempt_to}]}`, plus `links.self` and `etag` [B11]. Their exact shape inside the snapshot: UNVERIFIED.
- Dates of birth appear as `{month, year}` only (all 9,108 sampled individuals) [B43].
- Stale records: "The PSC snapshot retains statements long after a company leaves the register", and dropping records for companies absent from the live base file removed "38.5% of records in a sampled snapshot part" (OpenSanctions, August 2026) [B39].

### 3.4 The `identification` object in practice

- Corporate entity PSCs in the sample: 793 of 879 had all five keys (`country_registered`, `legal_authority`, `legal_form`, `place_registered`, `registration_number`); 86 had only `legal_authority` and `legal_form`. All 13 legal persons had only `legal_authority` and `legal_form` [B43].
- The values are free text, apparently title-cased. Most frequent values in the sample (generic registry strings, Community aggregate) [B43]:

```text
country_registered: England 280, United Kingdom 160, England And Wales 147, (absent) 86, England & Wales 50, Uk 49, Scotland 33, Northern Ireland 6, United States 5
place_registered:   Companies House 315, England And Wales 94, (absent) 86, England & Wales 51, England 47, Uk Companies House 20, Uk 16, United Kingdom 16, Register Of Companies 9, Uk Register Of Companies 9, Companies House England & Wales 8, Scotland 8, Cardiff 7
legal_authority:    Companies Act 2006 318, Companies Act 93, United Kingdom (England And Wales) 57, United Kingdom 42, England And Wales 33, United Kingdom (England) 29, English 21
legal_form:         Limited Company 290, Private Limited Company 131, Limited By Shares 110, Private Company Limited By Shares 66, Public Limited Company 35
registration_number patterns: 8 digits 501, 7 digits 148, AA999999 57, 6 digits 39, 5 digits 10, other formats (mostly foreign) 38
```

- So about a quarter of UK-looking numbers lack leading zeros, and some are foreign.
- Companies House warned that a corporate officer's registration number "isn't guaranteed to be correct" and is not correlated with the register (Phase 1, CH staff 2019). Treat PSC numbers the same way.

### 3.5 How other projects resolve a corporate PSC

| Project, file, licence | Rule |
|---|---|
| OpenSanctions `datasets/gb/coh/psc_parse.py`, MIT, last change 2026-09-03 [B39] | No resolution. Each corporate PSC becomes its own `Company` with id `gb-coh-psc-{company_number}-{psc id}`; `registration_number` is copied to `registrationNumber`; `country_registered` goes to `jurisdiction` through fuzzy country cleaning with YAML overrides (values such as `Companies House` or `England & Wales Companies Register` map to null, `contains: Scotland` to `gb-sct`, England, Wales, United Kingdom and similar to `gb`); `place_registered` is ignored (the line is commented out); the dataset sets `resolve: false`. |
| Open Ownership `register-transformer-psc`, `lib/register_transformer_psc/bods_mapping/entity_statement.rb`, Ruby, no licence file, last commit 2024-08-05 [B41] | `company_number = identification.registration_number`, left-padded with `"0"` while shorter than 8 characters (no strip or upper-casing, so prefixed short numbers get a wrong zero), then sent with `country_registered` (or `address.country`), `region` and `name` to an OpenCorporates resolver. |
| Open Ownership `register-sources-oc`, `services/resolver_service.rb` and `jurisdiction_code_service.rb`, Apache-2.0 [B42] | Country and region go through the Google Geocoding API, then the OpenCorporates jurisdiction API; the company is looked up by number in OpenCorporates, or reconciled by name. Not offline and not deterministic. |
| Open Ownership `bods-uk-psc-pipeline` (BODS 0.4, March 2025), `bodsukpscpipeline/source.py`, AGPL-3.0 [B43] | Deterministic. `is_local(x)`: `x.strip().lower()` in `{"united kingdom", "uk", "england and wales", "england & wales", "england", "wales", "scotland", "northern ireland"}`. A corporate PSC is UK when `registration_number` is present and not `n/a`/`na` (any case) and `country_registered` is local, or failing that `address.country` is local. `fix_company_number(n)`: 7 characters gets `"0"` prepended, 6 characters gets `"00"`, anything else unchanged. The entity id `GB-COH-{fixed number}` equals the id built from the base file's `CompanyNumber`, which is the join. `place_registered` is used only as a late fuzzy fallback to guess a country (and for Chinese subdivisions); `legal_authority` in a fixed list (`Companies Act`, `Companies Act 2006`, `English Law`, `Uk Companies Act 2006`, `UK Companies Act 2006`, `Companies Act 1985`, `Limited Companys Act 2006`, `Companies Acts`, `Companies Act 2014`, `Company Act 2006`) marks a Companies House scheme for non-local cases, whose ids then use the raw, unpadded number. |

This pipeline produced Open Ownership's CC0 "UK PSC Register and Register of Overseas Entities" BODS 0.4 dataset dated 2025-03-11 [B44]. The AGPL-3.0 code cannot be copied into Apache-2.0 NeonRadar; the rule below is a reimplementation from the description.

The 2024 interest parser in `register-transformer-psc` also mapped `ownership-of-shares-more-than-25-percent*` to 75 to 100 (a bug), and set `exclusiveMaximum: true` for 50 to 75 and an inclusive 75 for 75 to 100 (which matches the statute) [B41].

### 3.6 Recommended deterministic rule for NeonRadar

```python
UK_TOKENS = {"united kingdom", "uk", "u.k.", "great britain", "gb", "england", "wales",
             "england and wales", "england & wales", "scotland", "northern ireland",
             "companies house", "uk companies house", "register of companies",
             "registrar of companies", "uk register of companies"}
PREFIXED = re.compile(r"^(SC|SO|SL|SZ|SF|SA|SI|SP|SR|NI|NC|NL|NF|NA|NZ|NO|NP|NR|R0|OC|LP|FC|OE|IP|RC|AC|IC|GE|GN|GS|CE|CS|FE|PC|SG|SE|ZC)(\d{1,6})$")

def norm_text(s): return re.sub(r"\s+", " ", (s or "").strip().lower())
def is_uk(ident, address):
    vals = [norm_text(ident.get(k)) for k in ("country_registered", "place_registered", "legal_authority")]
    vals.append(norm_text((address or {}).get("country")))
    return any(v in UK_TOKENS or v.startswith(("companies house", "united kingdom (")) for v in vals)
def norm_number(raw):
    n = re.sub(r"\s+", "", (raw or "").upper())
    if n in {"", "N/A", "NA", "NONE"}: return None
    if n.isdigit() and len(n) <= 8: return n.zfill(8)
    m = PREFIXED.match(n)
    return m.group(1) + m.group(2).zfill(6) if m else None
# resolved iff is_uk(...) and norm_number(...) is in the company index (live file, plus API or GLEIF
# for dissolved ones) and the PSC name matches the company name after normalisation (Splink
# comparison, or a token-set ratio threshold); otherwise keep an unresolved LegalEntity for ER.
```

Record the outcome per edge (`resolved`, `number_not_found`, `name_mismatch`, `non_uk`) so the spec can test it.

### 3.7 Overseas entities and `is_sanctioned`

- Yes (Community evidence): the November 2024 fixtures contain `corporate-entity-beneficial-owner` and `legal-person-beneficial-owner` records under `OE` company numbers, with `is_sanctioned: false` and `principal_office_address` [B43]. OpenSanctions maps `is_sanctioned: true` to the topic `sanction` [B39]. The download page does not mention overseas entities [B4].

## 4. `natures_of_control` (Q3)

### 4.1 Source

`psc_descriptions.yml` in `companieshouse/api-enumerations`, read at repository head `05067ab` (2026-09-11); the file itself last changed in `0d3fb78` (2025-11-07, "Use the correct quotation mark characters"). It has 86 `description` keys, 86 matching `short_description` keys, 28 `statement_description` keys and 2 `super_secure_description` keys [B5].

### 4.2 Bounds

| Band key fragment | Statute (companies, LLPs, Scottish partnerships) | Interval | API long description | API short description |
|---|---|---|---|---|
| `25-to-50-percent` | "more than 25% but not more than 50%" [B28][B29][B30] | `(25, 50]`, lower exclusive | same | "More than 25% but not more than 50%" |
| `50-to-75-percent` | "more than 50% but less than 75%" [B28][B29][B30] | `(50, 75)`, both exclusive | "more than 50% but not more than 75%" (wrong) | "More than 50% but less than 75%" |
| `75-to-100-percent` | "75% or more" [B28][B29][B30] | `[75, 100]`, lower inclusive | "more than 75%" (wrong), except the `-as-firm` surplus asset texts which say "75% or more" | "75% or more" |
| `more-than-25-percent` (overseas entities) | "more than 25% of the shares" / "of the voting rights" [B31] | `(25, 100]` | same | "More than 25%" |

Store `pct_min`, `pct_max`, `min_exclusive`, `max_exclusive` per edge from the statute column. Short descriptions in the YAML contain an en dash character after "Ownership of shares"; normalise it if displayed.

### 4.3 The 86 values, grouped

Companies (24):

```text
shares:  ownership-of-shares-25-to-50-percent, ownership-of-shares-50-to-75-percent, ownership-of-shares-75-to-100-percent
         ownership-of-shares-25-to-50-percent-as-trust, ownership-of-shares-50-to-75-percent-as-trust, ownership-of-shares-75-to-100-percent-as-trust
         ownership-of-shares-25-to-50-percent-as-firm, ownership-of-shares-50-to-75-percent-as-firm, ownership-of-shares-75-to-100-percent-as-firm
votes:   voting-rights-25-to-50-percent, voting-rights-50-to-75-percent, voting-rights-75-to-100-percent
         voting-rights-25-to-50-percent-as-trust, voting-rights-50-to-75-percent-as-trust, voting-rights-75-to-100-percent-as-trust
         voting-rights-25-to-50-percent-as-firm, voting-rights-50-to-75-percent-as-firm, voting-rights-75-to-100-percent-as-firm
board:   right-to-appoint-and-remove-directors, right-to-appoint-and-remove-directors-as-trust, right-to-appoint-and-remove-directors-as-firm
SIoC:    significant-influence-or-control, significant-influence-or-control-as-trust, significant-influence-or-control-as-firm
```

LLPs (24):

```text
surplus: right-to-share-surplus-assets-25-to-50-percent-limited-liability-partnership
         right-to-share-surplus-assets-50-to-75-percent-limited-liability-partnership
         right-to-share-surplus-assets-75-to-100-percent-limited-liability-partnership
         right-to-share-surplus-assets-25-to-50-percent-as-trust-limited-liability-partnership
         right-to-share-surplus-assets-50-to-75-percent-as-trust-limited-liability-partnership
         right-to-share-surplus-assets-75-to-100-percent-as-trust-limited-liability-partnership
         right-to-share-surplus-assets-25-to-50-percent-as-firm-limited-liability-partnership
         right-to-share-surplus-assets-50-to-75-percent-as-firm-limited-liability-partnership
         right-to-share-surplus-assets-75-to-100-percent-as-firm-limited-liability-partnership
votes:   voting-rights-25-to-50-percent-limited-liability-partnership
         voting-rights-50-to-75-percent-limited-liability-partnership
         voting-rights-75-to-100-percent-limited-liability-partnership
         voting-rights-25-to-50-percent-as-trust-limited-liability-partnership
         voting-rights-50-to-75-percent-as-trust-limited-liability-partnership
         voting-rights-75-to-100-percent-as-trust-limited-liability-partnership
         voting-rights-25-to-50-percent-as-firm-limited-liability-partnership
         voting-rights-50-to-75-percent-as-firm-limited-liability-partnership
         voting-rights-75-to-100-percent-as-firm-limited-liability-partnership
members: right-to-appoint-and-remove-members-limited-liability-partnership
         right-to-appoint-and-remove-members-as-trust-limited-liability-partnership
         right-to-appoint-and-remove-members-as-firm-limited-liability-partnership
SIoC:    significant-influence-or-control-limited-liability-partnership
         significant-influence-or-control-as-trust-limited-liability-partnership
         significant-influence-or-control-as-firm-limited-liability-partnership
```

Eligible Scottish partnerships (12):

```text
surplus: part-right-to-share-surplus-assets-25-to-50-percent, part-right-to-share-surplus-assets-50-to-75-percent, part-right-to-share-surplus-assets-75-to-100-percent
         part-right-to-share-surplus-assets-25-to-50-percent-as-trust, part-right-to-share-surplus-assets-50-to-75-percent-as-trust, part-right-to-share-surplus-assets-75-to-100-percent-as-trust
         part-right-to-share-surplus-assets-25-to-50-percent-as-firm, part-right-to-share-surplus-assets-50-to-75-percent-as-firm, part-right-to-share-surplus-assets-75-to-100-percent-as-firm
persons: right-to-appoint-and-remove-person, right-to-appoint-and-remove-person-as-firm, right-to-appoint-and-remove-person-as-trust
```

Registered overseas entities (26): `-as-trust` means the beneficial owner is a trustee; `-as-firm` a member of a firm; `-as-control-over-trust` and `-as-control-over-firm` mean control over the trust or firm [B5][B31].

```text
shares:  ownership-of-shares-more-than-25-percent-registered-overseas-entity
         ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity
         ownership-of-shares-more-than-25-percent-as-firm-registered-overseas-entity
         ownership-of-shares-more-than-25-percent-as-control-over-trust-registered-overseas-entity
         ownership-of-shares-more-than-25-percent-as-control-over-firm-registered-overseas-entity
votes:   voting-rights-more-than-25-percent-registered-overseas-entity
         voting-rights-more-than-25-percent-as-trust-registered-overseas-entity
         voting-rights-more-than-25-percent-as-firm-registered-overseas-entity
         voting-rights-more-than-25-percent-as-control-over-trust-registered-overseas-entity
         voting-rights-more-than-25-percent-as-control-over-firm-registered-overseas-entity
board:   right-to-appoint-and-remove-directors-registered-overseas-entity
         right-to-appoint-and-remove-directors-as-trust-registered-overseas-entity
         right-to-appoint-and-remove-directors-as-firm-registered-overseas-entity
         right-to-appoint-and-remove-directors-as-control-over-trust-registered-overseas-entity
         right-to-appoint-and-remove-directors-as-control-over-firm-registered-overseas-entity
SIoC:    significant-influence-or-control-registered-overseas-entity
         significant-influence-or-control-as-trust-registered-overseas-entity
         significant-influence-or-control-as-firm-registered-overseas-entity
         significant-influence-or-control-as-control-over-trust-registered-overseas-entity
         significant-influence-or-control-as-control-over-firm-registered-overseas-entity
nominee: registered-owner-as-nominee-person-england-wales-registered-overseas-entity
         registered-owner-as-nominee-person-scotland-registered-overseas-entity
         registered-owner-as-nominee-person-northern-ireland-registered-overseas-entity
         registered-owner-as-nominee-another-entity-england-wales-registered-overseas-entity
         registered-owner-as-nominee-another-entity-scotland-registered-overseas-entity
         registered-owner-as-nominee-another-entity-northern-ireland-registered-overseas-entity
```

In the 10,000-record sample, 43 distinct values occurred; the most frequent were `ownership-of-shares-75-to-100-percent` (4,039), `ownership-of-shares-25-to-50-percent` (3,690) and `right-to-appoint-and-remove-directors` (2,563) [B43]. Unknown values must be logged, not dropped (OpenSanctions does this) [B39].

### 4.4 Statements and super-secure keys

```text
no-individual-or-entity-with-signficant-control   (misspelt "signficant" in the source; match exactly)
psc-exists-but-not-identified, psc-details-not-confirmed, steps-to-find-psc-not-yet-completed,
psc-contacted-but-no-response, psc-has-failed-to-confirm-changed-details, restrictions-notice-issued-to-psc,
and the seven "-partnership" variants of the above,
all-beneficial-owners-identified, no-beneficial-owner-identified, at-least-one-beneficial-owner-unidentified,
information-not-provided-for-at-least-one-beneficial-owner,
at-least-one-beneficial-owner-unidentified-and-information-not-provided-for-at-least-one-beneficial-owner,
nobody-has-become-or-ceased-to-be-a-beneficial-owner, somebody-has-become-or-ceased-to-be-a-beneficial-owner,
no-change-beneficial-owner-relevant-period, change-beneficial-owner-relevant-period,
no-trust-involved-relevant-period, trust-involved-relevant-period,
no-change-beneficiary-relevant-period, change-beneficiary-relevant-period, awaiting-confirmation-from-psc
super_secure_description keys: super-secure-persons-with-significant-control, super-secure-beneficial-owner
```

The super-secure key `super-secure-persons-with-significant-control` differs from the snapshot kind `super-secure-person-with-significant-control` [B5][B43].

## 5. Officers through the REST API (Q4)

- `/company/{n}/officers` items (`officerSummary`) include `person_number`, type string, "Unique person identifier as displayed in bulk products 195, 198, 208, 209 and 216" (checked today) [B6]. Companies House's service code maps it into every officer summary (`CompanyAppointmentMapper.map`: `.personNumber(data.getPersonNumber())`) [B8].
- `/officers/{officer_id}/appointments` items (`officerAppointmentSummary`) have no `person_number`: absent from the swagger definition and from the service's `ItemsMapper` [B7][B8].
- Format: string. Community examples (February 2026) are 12 digits ending `0001`, for example `123456780001` as a placeholder; a January 2025 post understands "the first 8 characters identify the person, and the subsequent 4 characters represent an increment of changes", and reports "multiple distinct 8-character 'person IDs' for what appears to be the same individual" [B21][B22]. The February 2026 post shows one corporate secretary under two numbers across Products 195/216 and 198 [B22]. No Companies House staff reply in these 2025 and 2026 threads. Treat `person_number` as a strong but fallible blocking key for entity resolution, never as an identity.
- Paging, from Companies House's `company-appointments.api.ch.gov.uk` (MIT, commit `69cc249`, 2026-06-16) [B8]:
  - officer appointments: `DEFAULT_ITEMS_PER_PAGE = 35`, `MAX_ITEMS_PER_PAGE_EXTERNAL = 50` (internal callers up to `OFFICER_APPOINTMENTS_THRESHOLD`, default 500);
  - company officers: default 35, the requested value goes straight to the MongoDB `limit` with no cap in this service; the controller also accepts `filter=active`. Whether a gateway caps it (100 was reported in 2019): UNVERIFIED. Request 100, advance by `len(items)`, stop at `total_results`.
- Rate limit: "You can make up to 600 requests within a 5 minute period", then `429` for the rest of the window; no change notice on the page [B9]. In December 2025 a user asking for more was redirected to `xml@companieshouse.gov.uk` [B24].
- Officer bulk products: still not on the GOV.UK data products page (last updated 25 October 2022) [B10]. Requests go to `bulkproducts@companieshouse.gov.uk` (forum reply, 25 June 2026); a user reported Product 216 is produced monthly ("first Tuesday of every month") and re-posted it to a public bucket [B23]. That mirror is unofficial and full of personal data: do not use it. A May 2026 public request for Products 195, 198 and 216 has no reply [B27]. Price, licence and approval terms: UNVERIFIED.

## 6. GLEIF Golden Copy (Q5)

### 6.1 Discovery API and current files

- `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest`; also `/{lei2|rr|repex}/latest`, `/{filetype}/latest.{csv|json|xml}` (for example `.../publishes/lei2/latest.csv`), `/{filetype}/{publish date}` and the paginated history `/publishes` [B48][B51]. Files are ZIP; three publishes a day ("02:00, 10:00, and 18:00 UTC+0" in the manual, stamped 0000, 0800, 1600 in the API); `LastDay`, `LastWeek` and `LastMonth` deltas are kept 31 days [B51].
- Latest combined publish read today, 2026-10-17 16:00 [B48]:

| Type | CDF | Records | CSV zip bytes | JSON zip | XML zip | LastDay delta CSV |
|---|---|---|---|---|---|---|
| `lei2` | LEI_3.1 | 3,465,810 | 504,971,197 | 924,562,713 | 890,098,305 | 13,191 records, 1,891,135 bytes |
| `rr` | RR_2.1 | 491,462 | 24,497,804 | 35,179,850 | 33,294,545 | 2,474 records |
| `repex` | REPEX_2.1 | 6,424,906 | 62,274,887 | 64,420,543 | 69,690,355 | 4,723 records |

- URL pattern: `https://goldencopy.gleif.org/storage/golden-copy-files/2026/10/17/1289720/20261017-1600-gleif-goldencopy-lei2-golden-copy.csv.zip` [B48].
- Staleness (Observed): `lei2/latest` returned the 2026-10-15 16:00 publish while the combined endpoint returned 2026-10-17 16:00 and API records carried `publishDate` 2026-10-18T00:00:00Z [B49][B48][B50]. Phase 1 saw the same. Pick the newest `publish_date` from the history listing.
- UK counts (Observed): `filter[entity.registeredAt]=RA000585,RA000586,RA000587` gives 119,382; with `entity.status=ACTIVE` and `registration.status=ISSUED`, 62,736 [B50].

### 6.2 CSV columns

LEI-CDF 3.1 CSV columns that a current parser enforces as present ("Column names verified against the published LEI-CDF 3.1 CSV", Community, `@fin.cx/opendata` 4.10.0, MIT, 13 October 2026) [B60]:

```text
LEI, Entity.LegalName, Entity.LegalName.xmllang, Entity.LegalJurisdiction, Entity.EntityStatus, Entity.EntityCategory,
Entity.LegalForm.EntityLegalFormCode, Entity.LegalForm.OtherLegalForm,
Entity.RegistrationAuthority.RegistrationAuthorityID, Entity.RegistrationAuthority.OtherRegistrationAuthorityID,
Entity.RegistrationAuthority.RegistrationAuthorityEntityID,
Registration.RegistrationStatus, Registration.InitialRegistrationDate, Registration.LastUpdateDate,
Entity.LegalAddress.FirstAddressLine, Entity.LegalAddress.City, Entity.LegalAddress.Country,
Entity.HeadquartersAddress.FirstAddressLine, Entity.HeadquartersAddress.City, Entity.HeadquartersAddress.Country
```

Further columns the same parser reads by pattern if present (Community, not enforced, so treat as UNVERIFIED until the first download):

```text
Entity.OtherEntityNames.OtherEntityName.{1..5}            plus .xmllang and .type
Entity.TransliteratedOtherEntityNames.TransliteratedOtherEntityName.{1..5}   plus .xmllang and .type
Entity.LegalAddress.{AdditionalAddressLine.1..3, Region, PostalCode, AddressNumber, AddressNumberWithinBuilding, MailRouting, xmllang}
Entity.HeadquartersAddress.{same parts}
```

- GLEIF confirms the convention (dotted XML paths, `.xmllang`, up to 5 numbered repeats, "the columns will be left empty if there are less or none", columns inserted between existing ones in 3.1), for example `Entity.EntityCreationDate`, `Entity.EntitySubCategory`, `Entity.SuccessorEntity.1.SuccessorLEI`, `Entity.LegalEntityEvents.LegalEntityEvent.1.LegalEntityEventType` [B52]. Entries beyond five are dropped from the CSV but kept in XML and JSON [B54].
- CSV syntax (Community): comma, `"` quoting with doubled quotes, embedded CR/LF in quoted fields, strict UTF-8 [B60]. A second community adapter reads `LEI`, `Entity.LegalName`, `Entity.EntityStatus` and `Entity.LegalAddress.Country` from the same file [B61]. GLEIF's own CSV samples (2021-11-23, v1.1) exist only as a ZIP, unreadable here [B53].
- RR CSV header from a 2019 fixture written with GLEIF (Community, CC0) [B62]. RR-CDF 2.1 exact header: UNVERIFIED; GLEIF's breaking-change document lists no RR or repex CSV changes [B52]:

```text
Relationship.StartNode.NodeID, Relationship.StartNode.NodeIDType, Relationship.EndNode.NodeID, Relationship.EndNode.NodeIDType,
Relationship.RelationshipType, Relationship.RelationshipStatus, Registration.InitialRegistrationDate, Registration.LastUpdateDate,
Registration.RegistrationStatus, Registration.NextRenewalDate, Registration.ManagingLOU, Registration.ValidationSources,
Registration.ValidationDocuments, Registration.ValidationReference,
then for N = 1 to 5: Relationship.Period.N.startDate, Relationship.Period.N.endDate, Relationship.Period.N.periodType
then for N = 1 to 5: Relationship.Qualifiers.N.QualifierDimension, Relationship.Qualifiers.N.QualifierCategory
then for N = 1 to 5: Relationship.Qualifiers.N.MeasurementMethod, Relationship.Qualifiers.N.QuantifierAmount, Relationship.Qualifiers.N.QuantifierUnits
(54 columns; the quantifier columns carry the "Qualifiers" prefix in this fixture)
```

- Reporting exceptions CSV header: UNVERIFIED; the XML fields are `LEI`, `ExceptionCategory`, `ExceptionReason`, `ExceptionReference` (Phase 1 B3).
- Loader advice: map columns by name or prefix, assert the enforced set above, and write the observed header to a test fixture on first download. Filter UK rows with `Entity.RegistrationAuthority.RegistrationAuthorityID` in {RA000585, RA000586, RA000587} or `Entity.LegalJurisdiction` starting `GB`.

### 6.3 Level 2 is accounting consolidation

- RR-CDF: `IS_DIRECTLY_CONSOLIDATED_BY` and `IS_ULTIMATELY_CONSOLIDATED_BY` mean "The StartNode of the "child" entity has its accounts fully consolidated by the EndNode "parent" entity"; other types are branches and funds [B55].
- GLEIF's Level 2 page speaks only of the "direct accounting consolidating parent" and "ultimate accounting consolidating parent" [B56]. The ROC approach: "the identification of the parent would be based on the accounting definition of consolidation"; the ultimate parent is "the highest level legal entity preparing consolidated financial statements"; entities controlled by natural persons report no parent [B57]. A secondary reference puts it as "accounting consolidation under IFRS/US-GAAP, not percentage ownership and not beneficial ownership" [B63].
- Quantifier fields (`MeasurementMethod`, `QuantifierAmount`, `QuantifierUnits`) exist but GLEIF gives no ownership semantics; how often they are populated: UNVERIFIED (count after download). Model RR edges as `CONSOLIDATED_BY`, never as `OWNS` with a percentage.

### 6.4 Maintenance window

- "Brief service interruptions may occur between 19 October and 4 November 2026." Neither the home page nor the service availability page names the services affected [B58][B59]. Whether Golden Copy downloads are affected: UNVERIFIED. Download the three CSV zips (about 592 MB) on 18 October, record SHA-256 and `publish_date`, and run tests from fixtures.

## 7. ICIJ Offshore Leaks (Q6)

- Download page unchanged: `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip`, Neo4j dumps 4.4.26 and 5.13.0, ODbL plus CC BY-SA, "Always cite the International Consortium of Investigative Journalists when using this data."; no size, date or post-2022 additions shown [B64]. OpenSanctions' ICIJ crawler last changed on 2026-08-05 (two-digit year handling) and still reads the same six members by name [B66]; Senzing's mapper changed only a dependency on 2026-10-16 [B67].
- Size and Last-Modified: UNVERIFIED (the host is blocked to the shell; the fetch tool cannot read binaries).
- Header rows: no GitHub parser hard-codes them (OpenSanctions, Senzing and ICIJ's own repository read by name). A community copy on Hugging Face (space `Didier/ICIJ_SQL_agent`, January 2025) gives two exact header rows and the uncompressed sizes [B65]:

```text
nodes-others.csv:         node_id,name,type,incorporation_date,struck_off_date,closed_date,jurisdiction,jurisdiction_description,countries,country_codes,sourceID,valid_until,note
nodes-intermediaries.csv: node_id,name,status,internal_id,address,countries,country_codes,sourceID,valid_until,note
sizes: nodes-entities.csv 199 MB, relationships.csv 259 MB, nodes-officers.csv 91 MB, nodes-addresses.csv 72.5 MB,
       nodes-intermediaries.csv 4.06 MB, nodes-others.csv 398 kB (626 MB in total)
```

- The other four files: column sets from Phase 1 (OpenSanctions' consumed columns), order UNVERIFIED. Read with `csv.DictReader` and audit unknown columns.

## 8. Neo4j 5.26 Community loading at this scale (Q7)

### 8.1 Python driver 6.x

- `neo4j` 6.4.1 (uploaded 2026-10-15, Python 3.10 or later, Apache-2.0 AND Python-2.0, pure Python wheel); `neo4j-rust-ext` 6.4.1.0 (2026-10-15, Apache-2.0 AND MIT, cp314 wheels for Linux, macOS and Windows; version tracks the driver; Python 3.14 since 6.1.0.0) [B71][B72].
- Speed claims: the driver manual says the extension "yields a 3x to 10x speedup compared to the regular driver"; the package says "up to 10x faster" [B70][B72]. Install `neo4j-rust-ext==6.4.1.0` in place of `neo4j`.
- `driver.execute_query()` "Execute[s] a query in a transaction function ... this means that queries using `CALL {} IN TRANSACTIONS` or the older `USING PERIODIC COMMIT` will not work (use :meth:`Session.run` for these)" (docstring, 6.4.1) [B71].
- Manual guidance: always pass the database name; batch with `UNWIND` (its example sends 10,000 rows per query); use `CREATE` instead of `MERGE` when the data is known to be new; for "throughput over data integrity" run many queries in one auto-commit session, for integrity use `execute_query` or `execute_write`; for an initial large load it recommends `neo4j-admin database import` [B70].
- Batch sizes (Neo4j-maintained skill, MIT, 2026-10-09): 10,000 rows below 100,000 rows; 10,000 to 50,000 for 100,000 to 1 million; 5,000 for relationship batches "each batch does 2x MATCH"; `neo4j-admin` above 10 million rows [B74]. That skill describes 2025.x and 2026.x behaviour (for example `ON ERROR RETRY`, `--bad-tolerance` default -1, `--dry-run`), which 5.26 does not have.
- `session.run` (6.x) retries an auto-commit query only when the server marks the error idempotent; `disable_auto_commit_retries` turns that off [B71]. Do not rely on it for 5.26.

### 8.2 `CALL { } IN TRANSACTIONS` on 5.26

- "By default, inner transactions group together batches of 1000 rows"; "CALL { … } IN TRANSACTIONS is only allowed in implicit transactions" [B69].
- `IN [n] CONCURRENT TRANSACTIONS` introduced in 5.21; without `n`, "a default value based on the amount of available CPU cores"; slotted runtime only; batch order and size per batch undefined; deadlocks roll back batches unless an error mode is set [B69].
- Error modes `ON ERROR CONTINUE | BREAK | FAIL` and `REPORT STATUS AS s` since 5.7; `ON ERROR RETRY` since 2025.03, so not on 5.26 [B69].
- Use concurrency for node batches with disjoint keys; keep relationship loads single-threaded or partition them by start node to avoid lock contention on hub nodes.

### 8.3 `neo4j-admin database import full` (5.26)

Syntax from the 5.x Operations Manual source (branch `5.x`, `neo4j-version-exact: 5.26.32`) [B68]:

```text
neo4j-admin database import full [-h] [--expand-commands] [--verbose] [--auto-skip-subsequent-headers[=true|false]]
  [--ignore-empty-strings[=true|false]] [--ignore-extra-columns[=true|false]] [--legacy-style-quoting[=true|false]]
  [--normalize-types[=true|false]] [--overwrite-destination[=true|false]] [--skip-bad-entries-logging[=true|false]]
  [--skip-bad-relationships[=true|false]] [--skip-duplicate-nodes[=true|false]] [--strict[=true|false]]
  [--trim-strings[=true|false]] [--additional-config=<file>] [--array-delimiter=<char>] [--bad-tolerance=<num>]
  [--delimiter=<char>] [--format=<format>] [--high-parallel-io=on|off|auto] [--id-type=string|integer|actual]
  [--input-encoding=<character-set>] [--input-type=csv|parquet] [--max-off-heap-memory=<size>] [--quote=<char>]
  [--read-buffer-size=<size>] [--report-file=<path>] [--schema=<path>] [--threads=<num>]
  --nodes=[<label>[:<label>]...=]<files>... [--relationships=[<type>=]<files>...]...
  [--multiline-fields=true|false|<path>[,<path>] [--multiline-fields-format=v1|v2]] <database>
```

| Option | 5.26 default and meaning [B68] |
|---|---|
| `--id-type` | `string`; also `integer`, `actual` (advanced) |
| `--array-delimiter` | `;`; accepts `\t`, `\59` or `U+XXXX` (use `U+001F` if values may contain `;`) |
| `--multiline-fields` | null; in v1 `true` or `false` ("can severely degrade the performance"); in v2 (new in 5.26, `--multiline-fields-format=v2`) a list of files, with text fields quoted |
| `--overwrite-destination` | `false`; "Delete any existing database files prior to the import" |
| `--bad-tolerance` | `1000`; "Number of bad entries before the import is aborted" |
| `--skip-duplicate-nodes` | `false`; keeps the first node per ID and group, logs the rest |
| `--skip-bad-relationships` | `false`; skips relationships to missing node IDs |
| `--strict` | `false` since 5.8 |
| `--trim-strings`, `--ignore-empty-strings` | `false`, `false` |
| `--max-off-heap-memory` | `90%` |
| `--threads` | available processors |
| `--schema` | Enterprise and `block` format only; Community creates constraints afterwards |

- Headers: nodes `<name>:ID(<group>)`, `:LABEL` (labels split by the array delimiter), typed properties `name:string`, `incorporated:date`, `natures:string[]`; relationships `:START_ID(<group>)`, `:END_ID(<group>)`, `:TYPE`. A separate header file must be the first file of each data source. UTF-8; RFC 4180 quoting by doubling `"` [B68].
- Requirements: database "non-existent or empty", "CSV data is clean/fault-free (nodes are not duplicated and relationships' start and end nodes exist)"; the tool "can handle data faults but performance is not optimized" [B68].
- Picocli quirk: a positional database name after a multi-value option is swallowed; put the database name first or after `--` [B68].
- How `--skip-*` interacts with the `--bad-tolerance` abort threshold is not spelled out: UNVERIFIED. Deduplicate in DuckDB and run with `--bad-tolerance=0` in CI.

### 8.4 Running it in Docker for Community

- Community "can have exactly one standard database", and the create, start and stop database page is Enterprise-only, so `STOP DATABASE neo4j` is not available; the server must be stopped [B68].
- The docs' pattern runs the importer as the container command with the same volumes: `docker run --interactive --tty --rm --volume=$HOME/neo4j/data:/data --volume=$HOME/neo4j/import:/import neo4j:5.26.32 neo4j-admin database import full ...` [B68].
- The 5.x entrypoint executes any command other than `neo4j` as `su-exec neo4j:neo4j "$@"` after applying `NEO4J_*` settings; the initial password is set only when the server itself starts [B73].
- Proposed compose sequence (not run here; same image tag as the server):

```bash
docker compose stop neo4j
docker compose run --rm --no-deps -v "$PWD/build/neo4j-import:/import:ro" neo4j \
  neo4j-admin database import full neo4j \
  --overwrite-destination=true --id-type=string --array-delimiter="U+001F" --bad-tolerance=0 \
  --report-file=/logs/import.report \
  --nodes=Company=/import/company_header.csv,/import/company.csv \
  --nodes=Person=/import/person_header.csv,/import/person.csv \
  --relationships=HAS_PSC=/import/psc_header.csv,/import/psc.csv
docker compose up -d neo4j          # then CREATE CONSTRAINT ... IF NOT EXISTS through cypher-shell
```

### 8.5 Recommendation for 500,000 nodes and 2 million relationships

- Phase 2 does not need `neo4j-admin`. Primary path: Python driver, uniqueness constraints first, nodes before relationships, `UNWIND $rows` batches of 10,000 nodes and 5,000 relationships in explicit write transactions (`session.execute_write`) or `session.run` with `CALL { } IN TRANSACTIONS`; `CREATE` on a fresh build, `MERGE` for incremental runs; `neo4j-rust-ext` installed.
- Expected time: well inside 10 minutes, but no 5.26 laptop benchmark was found or possible here (UNVERIFIED). Phase 1 estimated 5 to 20 minutes for the driver path and 10 to 40 seconds for the importer. Add a CI benchmark gate on the 500,000-node fixture; if the online load exceeds 6 minutes on the reference laptop, make the importer the default full-build path.
- Keep `neo4j-admin database import full` as an optional `--rebuild` path: have the DuckDB stage write node and relationship CSVs in the importer header format, so the same files serve both paths.

## 9. DuckDB as the ETL engine (Q8)

### 9.1 Versions

- `duckdb` 1.5.6 (2026-09-28), `License :: OSI Approved :: MIT License`, cp314 wheels for macOS (universal2, x86_64, arm64), manylinux x86_64 and aarch64, Windows [B75]. In the Python 3.14.6 wheel, `json` and `parquet` are installed and loaded; `httpfs` is not (Observed) [B84].
- `splink` 5.0.0 (2026-09-28, MIT) requires `duckdb>=0.9.2`, so 1.5.6 is compatible [B83]. `orjson` 3.13.0 has cp314 wheels; `fsspec` 2026.9.0 is BSD-3-Clause [B83][B82].

### 9.2 ZIP files

- Core DuckDB does not read ZIP: `read_csv` and `read_json` take `compression` `none`, `gzip`, `zstd` or `auto` [B76][B77].
- Community extension `zipfs`: "Read files within zip archives", version 1.5.6, MIT, maintainer `isaacbrodsky`, `INSTALL zipfs FROM community; LOAD zipfs;`, paths like `zip://my_zip.zip/my_file.csv` [B81].
- Installing it is a network call at runtime: "Failed to download extension "zipfs" at URL "http://community-extensions.duckdb.org/v1.5.6/linux_amd64/zipfs.duckdb_extension.gz"" (Observed, the host is blocked here) [B84]. The `community` repository is `http://community-extensions.duckdb.org`; community extensions are built and signed by the DuckDB team; installed files go to `~/.duckdb/extensions/<version>/<platform>/` or `extension_directory`; `allow_community_extensions` defaults to true [B80][B78]. Pre-installing at build time would work offline later, but it adds a third-party binary for little gain.
- Alternatives that worked (Observed, section 9.5): extract the member with `zipfile` to a temp directory and read the path (fastest); `con.read_json(fileobj)` or `con.read_csv(fileobj)` on a `ZipFile.open()` handle (needs `fsspec`; without it: "required module 'fsspec' is not installed"); `con.register_filesystem(fsspec.filesystem("zip", fo=path))` then `read_json('zip://member')`.

### 9.3 Newline-delimited JSON

- `read_json(path, format='newline_delimited')` (alias `read_ndjson`); `maximum_object_size` default 16,777,216 bytes; `sample_size` default 20,480; `ignore_errors` only for newline-delimited input; `maximum_depth` default -1; `columns` struct to skip detection; `map_inference_threshold` 200 [B76].
- With auto-detection the PSC file fails at the totals line: "Object {"kind":"totals#persons-of-significant-control-sna... has unknown key "persons_of_significant_control_count"" (Observed). Fix: `columns={company_number: 'VARCHAR', data: 'JSON'}` and extract fields with `data->>'kind'` (also the fastest variant), or `ignore_errors=true` (silently drops the totals line) [B84]. Parenthesise JSON arrows in predicates: `(data->'natures_of_control') IS NOT NULL`.

```sql
SET preserve_insertion_order = false;
CREATE TABLE psc_raw AS
SELECT company_number, data->>'kind' AS kind, data
FROM read_json('/tmp/nr/psc.txt', format = 'newline_delimited',
               columns = {company_number: 'VARCHAR', data: 'JSON'});
CREATE TABLE basic_raw AS
SELECT * FROM read_csv('/tmp/nr/basic.csv', header = true, delim = ',', quote = '"', escape = '"',
                       all_varchar = true, allow_quoted_nulls = false,
                       ignore_errors = true, store_rejects = true);   -- rejected rows land in reject_errors
```

### 9.4 Memory settings

- `memory_limit` (alias `max_memory`) default "80% of RAM"; `threads` default number of cores; `temp_directory` default `<database>.tmp` or `.tmp`; `max_temp_directory_size` default 90% of free disk; `preserve_insertion_order` default true [B78].
- For larger-than-memory loads "consider setting the `preserve_insertion_order` configuration option to `false`"; spilling goes to `temp_directory`; at least 125 MB per thread, 1 to 4 GB per thread for good performance [B79].
- Suggested laptop settings next to Neo4j (2 GB heap, 2 GB page cache): `SET memory_limit = '4GB'; SET threads = 4; SET temp_directory = '<cache>/duckdb_tmp'; SET preserve_insertion_order = false;`.
- CSV strictness: the default reader raises "CSV Error on Line" on the 56-field row, and the dialect sniffer itself fails when such a row falls in its sample; pin the dialect and use `ignore_errors=true, store_rejects=true` (rejects recorded as `TOO MANY COLUMNS`). `strict_mode=false, null_padding=true` keeps the row with shifted values: do not use it (Observed) [B84].

### 9.5 Local measurements (synthetic placeholder data)

2 vCPUs, 7 GB RAM, Python 3.14.6, DuckDB 1.5.6, orjson 3.13.0; files generated by `gen.py` [B84]:

| Workload | Time | Rate |
|---|---|---|
| CSV 500,000 rows x 55 columns (218 MB raw, 33 MB zip): `zipfile` + `csv.reader`, dict per row | 3.45 s | 145,000 rows/s |
| same, DuckDB `read_csv` (`ignore_errors=true`) on the extracted file | 0.68 to 1.39 s | 360,000 to 740,000 rows/s |
| same, DuckDB on the zip member file object / fsspec zip | 1.25 / 1.43 s | 400,000 / 350,000 rows/s |
| NDJSON 1,000,000 lines (700 MB raw, 120 MB zip): `zipfile` + `orjson.loads` | 4.34 s | 230,000 lines/s |
| same with `json.loads` | 8.97 s | 111,000 lines/s |
| DuckDB `read_json` with `columns={...data: JSON}`, extracted file | 1.16 to 1.71 s | 584,000 to 860,000 lines/s |
| same, including the extraction of the member | 2.8 s | 350,000 lines/s |
| DuckDB `read_json` auto-detect (`ignore_errors=true`) | 1.78 to 3.06 s | 326,000 to 561,000 lines/s |
| DuckDB on the zip member file object / fsspec zip | 2.8 to 5.0 s | 200,000 to 360,000 lines/s |
| Extract both members to disk | 2.39 s | |

- Synthetic lines average 700 bytes, close to the real snapshot (about 12 GB raw for both files in 2024) [B43]. Extrapolated to 15 million PSC lines: about 65 s with orjson streaming or 45 to 90 s with DuckDB plus extraction on this 2 vCPU box; 5.7 million company rows: about 40 s with `csv` or under 15 s with DuckDB. A laptop with more cores should be faster. UNVERIFIED on real files.
- Documented elsewhere: OpenSanctions measured 0.59 s with `json.loads` against 0.25 s with `orjson.loads` on 168,955 real snapshot records (about 290,000 and 680,000 records/s for parsing alone) [B39]. Open Ownership's AWS pipeline took 6.7 hours to ingest and 14.5 hours to transform the full dataset (Elasticsearch and Kinesis, not comparable) [B43].

## 10. Companies House data and data protection (Q9)

This is analysis, not legal advice.

- Companies House, personal information charter (last updated 7 September 2026): organisations that use register data "then become controllers of your personal data" and "must establish how they comply with the data protection law"; the usual residential address and "the day of your date of birth" are not made public [B12].
- Companies House guidance (last updated 12 May 2026): "Other organisations have the right to make copies of any information available on the public register"; "we cannot stop third-parties from finding and using this information"; "Once they hold your information, third-parties are responsible for making sure they comply with data protection law" [B13]. The data products page: "You are responsible for complying with any applicable data protection, copyright and other legislation and regulations" [B10]. A 2017 staff post expected GDPR to have no impact on re-use [B26]; it predates and is superseded by the charter.
- UK GDPR Article 14 (data not obtained from the data subject), latest revised text [B32]:
  - 14(2)(f): "from which source the personal data originate, and if applicable, whether it came from publicly accessible sources";
  - 14(3)(a): "within a reasonable period after obtaining the personal data, but at the latest within one month";
  - 14(5)(b) was omitted by the Data (Use and Access) Act 2025 with effect from 5 February 2026; the exemption is now 14(5)(e): "providing the information is impossible or would involve a disproportionate effort"; 14(6) lists "the number of data subjects, the age of the personal data and any appropriate safeguards applied to the processing" among the factors; 14(7) requires appropriate measures "including by making the information available publicly".
- ICO, right to be informed (dated 22 September 2025, under review for the DUAA): disproportionate effort "should be treated as the exception, not the rule"; document the assessment; "you must publish the privacy information (eg on your website), and you should carry out a DPIA"; the one-month limit applies even if first contact comes later [B33][B34]. ICO direct marketing guidance adds that a public profile "doesn't mean that you are free to use their personal information" for direct marketing [B37].
- Lawful basis: the ICO legitimate interests guidance was updated on 23 March 2026 for the DUAA; the three-part test is purpose ("Do you have a legitimate interest"), necessity, and balancing ("Do the person's interests, rights or freedoms override the legitimate interest"); reasonable expectations are judged objectively [B35][B36]. The new recognised legitimate interests include "crime prevention and detection" with no balancing test (secondary source, June 2026) [B38]; whether a NeonRadar user's use fits: UNVERIFIED.
- Implications for the spec: NeonRadar ships code, not data, so each operator is the controller. The docs should tell operators to record a legitimate interests assessment, publish an Article 14 notice (source: Companies House public register, publicly accessible) if they rely on 14(5)(e), run a DPIA for officer and PSC processing, keep month and year of birth only, and set retention so re-downloads replace stale personal data.

## 11. Statistics (Q10)

- Incorporated companies in the UK, April to June 2026 (published 30 July 2026): "5,516,377 companies on the register as of end June 2026", 192,287 incorporations and 156,515 dissolutions in the quarter; next release 29 October 2026 [B14].
- Companies register activities 2025 to 2026 (published 25 June 2026), table 6.1 at 31 March 2026: private limited 5,275,466; limited by guarantee, no share capital 157,414; limited partnership 60,658; LLP 51,301; charitable incorporated organisation 39,259; limited by guarantee with exemption 36,704; overseas entity 33,137; Authorised Company Service Provider 20,093; overseas company 15,164; registered society 10,892; other 20,220; total 5,720,308. "Total register size" was 5,479,045 [B15].
- Free Company Data row counts: only one community figure, 5,695,465 rows (OpenSanctions, 7 August 2026) [B39]; no monthly history found.
- PSC counts by kind: no official statistics found. Totals line, 22 November 2024: 12,799,821 PSC records, 774,422 statements, 77 exemptions [B43]. OpenSanctions' live-company subset on 14 October 2026: 22,375,319 entities, of which 7,540,242 Person, 6,488,510 Company (including the base companies), 11,263 Organization [B40].

## 12. Corrections to Phase 1 notes

1. `neo4j.md` section 6 says `driver.execute_query` is fine for `CALL { } IN TRANSACTIONS`. It is not: use `session.run` [B71].
2. `sources-ch-gleif.md` A2 says to use the long `natures_of_control` descriptions. The statute matches the short descriptions: `50-to-75` excludes 75 and `75-to-100` includes 75 [B28].
3. `sources-ch-gleif.md` A3 gives PDF field names (`CountryofOrigin`, `AccountingRefDay`); the literal headers are `CountryOfOrigin`, `Accounts.AccountRefDay`, and so on, with 14 leading spaces (section 2.2).
4. The PSC totals line and overseas entity beneficial owners in the snapshot were UNVERIFIED; both are now confirmed by community evidence (sections 3.2, 3.7).
5. The 100-item officers cap (2019) is not in today's service code; officer appointments cap at 50 (section 5).

## 13. Still UNVERIFIED

- Free Company Data: overseas entities included (official statement), line endings, full `CompanyStatus` list, whether the empty-row defect persists in the October file.
- PSC snapshot: member file names, totals line in each part, exact `exemptions` shape.
- Officers: gateway cap for `/company/{n}/officers`; bulk product price, licence and terms.
- GLEIF: RR-CDF 2.1 and repex CSV headers; the optional LEI columns in 6.2; services affected by the maintenance window; population of RR quantifiers.
- ICIJ: zip size, Last-Modified, header order of four files.
- Neo4j: throughput for the driver path on 5.26; interaction of `--skip-*` flags with `--bad-tolerance`.
- Data protection: applicability of recognised legitimate interests to NeonRadar operators.

## Sources

All checked 2026-10-18. "Community" marks third-party code, non-staff forum posts and third-party pages.

Companies House and GOV.UK (official)
- [B1] Free Company Data Product page. https://download.companieshouse.gov.uk/en_output.html (checked 2026-10-18)
- [B2] Free Company Data field list (PDF). https://resources.companieshouse.gov.uk/toolsToHelp/pdf/freeDataProductDataset.pdf (checked 2026-10-18)
- [B3] Companies House FAQ on the public data product. https://resources.companieshouse.gov.uk/infoAndGuide/faq/publicDataProduct.shtml (checked 2026-10-18)
- [B4] PSC snapshot page. https://download.companieshouse.gov.uk/en_pscdata.html (checked 2026-10-18)
- [B5] companieshouse/api-enumerations, `psc_descriptions.yml` (head 05067ab 2026-09-11; file commit 0d3fb78 2025-11-07), git clone. https://github.com/companieshouse/api-enumerations/blob/master/psc_descriptions.yml (checked 2026-10-18)
- [B6] officerSummary resource. https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/officersummary (checked 2026-10-18)
- [B7] officerAppointmentList swagger. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/officerAppointmentList.json (checked 2026-10-18)
- [B8] companieshouse/company-appointments.api.ch.gov.uk (MIT, commit 69cc249 2026-06-16): `officerappointments/ItemsPerPageService.java`, `officerappointments/ItemsMapper.java`, `service/CompanyAppointmentService.java`, `mapper/CompanyAppointmentMapper.java`, `controller/CompanyAppointmentController.java`, `application.properties`. https://github.com/companieshouse/company-appointments.api.ch.gov.uk (checked 2026-10-18)
- [B9] Developer guidelines (rate limit). https://developer.company-information.service.gov.uk/developer-guidelines (checked 2026-10-18)
- [B10] Companies House data products (last updated 25 October 2022). https://www.gov.uk/guidance/companies-house-data-products (checked 2026-10-18)
- [B11] Company exemptions resource. https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/companyexemptions (checked 2026-10-18)
- [B12] Companies House personal information charter (updated 7 September 2026). https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter (checked 2026-10-18)
- [B13] Your personal information on the Companies House register (updated 12 May 2026). https://www.gov.uk/guidance/your-personal-information-on-the-companies-house-register (checked 2026-10-18)
- [B14] Incorporated companies in the UK, April to June 2026. https://www.gov.uk/government/statistics/incorporated-companies-in-the-uk-april-to-june-2026/incorporated-companies-in-the-uk-april-to-june-2026 (checked 2026-10-18)
- [B15] Companies register activities, April 2025 to March 2026. https://www.gov.uk/government/statistics/companies-register-activities-statistical-release-april-2025-to-march-2026/companies-register-activities-statistical-release-april-2025-to-march-2026 (checked 2026-10-18)
- [B16] Uniform Resource Identifiers Customer Guide (prefix list, v1.1, May 2012). https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/809682/uniformResourceIdentifiersCustomerGuide.pdf (checked 2026-10-18)

Companies House developer forum
- [B17] Leading space character at front of field names (community, 16 July 2024). https://forum.companieshouse.gov.uk/t/leading-space-character-at-front-of-field-names/8194 (checked 2026-10-18)
- [B18] Invalid BasicCompanyData part4_7 (community, 6 July and 3 August 2026). https://forum.companieshouse.gov.uk/t/invalid-basiccompanydata-yyyy-mm-dd-part4-7/12863 (checked 2026-10-18)
- [B19] Coding error in basic company info data, UTF-8 (CH staff MArkWilliams, 21 and 22 August 2023). https://forum.companieshouse.gov.uk/t/coding-error-in-basic-company-info-data-utf-8/6735 (checked 2026-10-18)
- [B20] PSC snapshot has been stopped (CH staff, 3 July 2024). https://forum.companieshouse.gov.uk/t/people-with-significant-control-psc-snapshot-has-been-stopped/8142 (checked 2026-10-18)
- [B21] Identifying officers across Prod195 and the stream (community, 20 January 2025). https://forum.companieshouse.gov.uk/t/how-to-definitively-identify-company-officers-across-snapshot-prod195-and-streaming-api-data/10740 (checked 2026-10-18)
- [B22] Linking person_number to company number in bulk data (community, February 2026). https://forum.companieshouse.gov.uk/t/linking-person-number-to-company-number-in-bulk-data/12670 (checked 2026-10-18)
- [B23] Is bulk officer data available (community, June and July 2026). https://forum.companieshouse.gov.uk/t/is-bulk-officer-data-available/12850 (checked 2026-10-18)
- [B24] Rate limit increase request (December 2025). https://forum.companieshouse.gov.uk/t/rate-limit-increase-request/12486 (checked 2026-10-18)
- [B25] Missing prefixes in Companies House document (community, November 2024). https://forum.companieshouse.gov.uk/t/missing-prefixes-in-companies-house-document/10257 (checked 2026-10-18)
- [B26] GDPR and ICO considerations (CH staff rmcneil, 9 August 2017). https://forum.companieshouse.gov.uk/t/gdpr-and-ico-considerations/1268 (checked 2026-10-18)
- [B27] Bulk officers data request (community, 15 May 2026, no reply). https://forum.companieshouse.gov.uk/t/bulk-officers-data-request-route13-b2b-financial-intelligence/12783 (checked 2026-10-18)

Legislation
- [B28] Register of People with Significant Control Regulations 2016 (SI 2016/339), Schedule 2. https://www.legislation.gov.uk/uksi/2016/339/schedule/2 (checked 2026-10-18)
- [B29] Limited Liability Partnerships (Register of People with Significant Control) Regulations 2016 (SI 2016/340), Schedule 2. https://www.legislation.gov.uk/uksi/2016/340/schedule/2 (checked 2026-10-18)
- [B30] Scottish Partnerships (Register of People with Significant Control) Regulations 2017 (SI 2017/694), Schedule 3. https://www.legislation.gov.uk/uksi/2017/694/schedule/3 (checked 2026-10-18)
- [B31] Economic Crime (Transparency and Enforcement) Act 2022, Schedule 2, paragraph 6. https://www.legislation.gov.uk/ukpga/2022/10/schedule/2/paragraph/6 (checked 2026-10-18)
- [B32] UK GDPR Article 14 (latest revised text). https://www.legislation.gov.uk/eur/2016/679/article/14 (checked 2026-10-18)

ICO and commentary
- [B33] ICO, right to be informed: are there any exceptions. https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/are-there-any-exceptions/ (checked 2026-10-18)
- [B34] ICO, right to be informed: when should we provide privacy information. https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/individual-rights/the-right-to-be-informed/when-should-we-provide-privacy-information/ (checked 2026-10-18)
- [B35] ICO, legitimate interests (updated 23 March 2026). https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/legitimate-interests/ (checked 2026-10-18)
- [B36] ICO, what is the legitimate interests basis. https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/legitimate-interests/what-is-the-legitimate-interests-basis/ (checked 2026-10-18)
- [B37] ICO, direct marketing: collect information and generate leads. https://ico.org.uk/for-organisations/direct-marketing-and-privacy-and-electronic-communications/direct-marketing-guidance/collect-information-and-generate-leads/ (checked 2026-10-18)
- [B38] Freeths, ICO publishes new guidance on recognised legitimate interests (secondary, 9 June 2026). https://www.freeths.co.uk/insights-events/legal-articles/2026/ico-publishes-new-guidance-on-recognised-legitimate-interests/ (checked 2026-10-18)

Community code and pages
- [B39] OpenSanctions `datasets/gb/coh/psc_parse.py` and `gb_coh_psc.yml` (MIT; file commit 8d60ff9ce 2026-09-03; commit messages of 254903469 and 6b56ea35e, 2026-08-07; repo head fc8e631 2026-10-17), community. https://github.com/opensanctions/opensanctions/tree/main/datasets/gb/coh (checked 2026-10-18)
- [B40] OpenSanctions dataset page `gb_coh_psc` (version 20261014130242-gcj), community. https://www.opensanctions.org/datasets/gb_coh_psc/ (checked 2026-10-18)
- [B41] Open Ownership `register-transformer-psc` (Ruby, no licence file, 5cd7fff 2024-08-05): `bods_mapping/entity_statement.rb`, `bods_mapping/interest_parser.rb`, community. https://github.com/openownership/register-transformer-psc (checked 2026-10-18)
- [B42] Open Ownership `register-sources-oc` (Apache-2.0, 4ab8cf4 2024-06-28): `services/resolver_service.rb`, `services/jurisdiction_code_service.rb`, community. https://github.com/openownership/register-sources-oc (checked 2026-10-18)
- [B43] Open Ownership `bods-uk-psc-pipeline` (AGPL-3.0, 1904567 2025-03-06): `bodsukpscpipeline/source.py`, `transforms.py`, `utils.py`, `config.py`, `README.md`, `tests/fixtures/basic-company-data-1.csv`, `tests/fixtures/psc-data-*.json` (aggregates only), community. https://github.com/openownership/bods-uk-psc-pipeline (checked 2026-10-18)
- [B44] Open Ownership BODS data site (UK PSC and ROE 0.4, 2025-03-11). https://bods-data.openownership.org/ (checked 2026-10-18)
- [B45] The Data City, identifying different company types (counts as of June 2024), community. https://docs.thedatacity.com/our-data/using-our-data/identifying-different-company-types (checked 2026-10-18)
- [B46] bolster `data_sources.companies_house` (UTF-8 decoding), community. https://bolster.readthedocs.io/en/main/_modules/bolster/data_sources/companies_house.html (checked 2026-10-18)
- [B47] mrbrianevans/companies-db `CompanyNumberClassifier.js`, community. https://github.com/mrbrianevans/companies-db/blob/master/company-number-utils/CompanyNumberClassifier.js (checked 2026-10-18)

GLEIF
- [B48] Golden Copy latest publish, all types (Observed). https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest (checked 2026-10-18)
- [B49] Golden Copy latest LEI publish (Observed, stale). https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest (checked 2026-10-18)
- [B50] GLEIF API counts for RA000585 to RA000587, with and without ACTIVE and ISSUED filters (Observed). https://api.gleif.org/api/v1/lei-records?filter[entity.registeredAt]=RA000585,RA000586,RA000587&page[size]=1 (checked 2026-10-18)
- [B51] GLEIF Golden Copy and Delta Files user manual v2.2 (PDF). https://www.gleif.org/lei-data/gleif-golden-copy/2022-02-23_gleif-golden-copy-and-delta-files_v2.2-final.pdf (checked 2026-10-18)
- [B52] GC Export Breaking Changes Documentation. https://www.gleif.org/content/4_lei-data/1_access-and-use-lei-data/6_supporting-documents/GC-Export-Breaking-Changes-Documentation.html (checked 2026-10-18)
- [B53] LEI CDF supporting documents (CSV samples ZIP listed). https://www.gleif.org/en/about-lei/common-data-file-format/current-versions/supporting-documents (checked 2026-10-18)
- [B54] GLEIF Data Dictionary v1.2 (PDF, 2025-11-18). https://www.gleif.org/lei-data/access-and-use-lei-data/gleif-data-dictionary/2025-11-18_gleif-data-dictionary_v1.2_final.pdf (checked 2026-10-18)
- [B55] RR-CDF format page. https://www.gleif.org/en/about-lei/common-data-file-format/relationship-record-cdf-format (checked 2026-10-18)
- [B56] Level 2 data: who owns whom. https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-who-owns-whom (checked 2026-10-18)
- [B57] GLEIF blog on the ROC parent definition. https://www.gleif.org/en/newsroom/blog/taking-the-next-step-legal-entity-identifier-regulatory-oversight-committee-proposes-process-for-collecting-data-on-direct-and-ultimate-parents-of-legal-entities (checked 2026-10-18)
- [B58] GLEIF home page (maintenance notice). https://www.gleif.org/en (checked 2026-10-18)
- [B59] GLEIF daily service availability. https://www.gleif.org/en/about/gleif-services/daily-service-availability (checked 2026-10-18)
- [B60] `@fin.cx/opendata` 4.10.0 (MIT, npm, published 2026-10-13): `ts/gleif/records.ts`, `ts/gleif/csv.ts`, `readme.md`, community. https://www.npmjs.com/package/@fin.cx/opendata (checked 2026-10-18)
- [B61] `@absolutejs/dataset-gleif` 0.0.3 (Apache-2.0) and absolutejs/dataset-adapters (2c99faf 2026-09-27), community. https://github.com/absolutejs/dataset-adapters (checked 2026-10-18)
- [B62] CorrelAid gleif-level2-server `src/test_data/rr-test.csv` (CC0, 95ce0dc 2019-11-14), community. https://github.com/CorrelAid/gleif-level2-server (checked 2026-10-18)
- [B63] GDELT Cloud, GLEIF Level 2 relationships (secondary). https://docs.gdeltcloud.com/api-reference/reference-data/gleif-level-2-relationships.md (checked 2026-10-18)

ICIJ
- [B64] ICIJ Offshore Leaks database download page. https://offshoreleaks.icij.org/pages/database (checked 2026-10-18)
- [B65] Hugging Face space Didier/ICIJ_SQL_agent, `icij_data` folder at commit 8507fc0 (2025-01-12), header rows and sizes only, community. https://huggingface.co/spaces/Didier/ICIJ_SQL_agent/tree/8507fc048717cb5f67e96d02b19f1d3cdb7e573b/icij_data (checked 2026-10-18)
- [B66] OpenSanctions `datasets/_global/icij_offshoreleaks/crawler.py` (MIT, last change ef82defae 2026-08-05), community. https://github.com/opensanctions/opensanctions/tree/main/datasets/_global/icij_offshoreleaks (checked 2026-10-18)
- [B67] Senzing mapper-icij (Apache-2.0, 0eb331a 2026-10-16), community. https://github.com/Senzing/mapper-icij (checked 2026-10-18)

Neo4j
- [B68] neo4j/docs-operations branch `5.x` (9fe3944 2026-10-09, display version 5.26, exact 5.26.32): `tools/neo4j-admin/neo4j-admin-import.adoc`, `docker/operations.adoc`, `database-administration/standard-databases/create-databases.adoc`, `database-administration/index.adoc`; rendered at https://neo4j.com/docs/operations-manual/5/tools/neo4j-admin/neo4j-admin-import/ and https://neo4j.com/docs/operations-manual/5/docker/operations/. https://github.com/neo4j/docs-operations/tree/5.x (checked 2026-10-18)
- [B69] neo4j/docs-cypher branch `cypher-5` (3b2f6c2 2026-10-16) `subqueries/subqueries-in-transactions.adoc`; rendered https://neo4j.com/docs/cypher-manual/5/subqueries/subqueries-in-transactions/ (checked 2026-10-18)
- [B70] Neo4j Python driver manual, performance recommendations. https://neo4j.com/docs/python-manual/current/performance/ (checked 2026-10-18)
- [B71] `neo4j` 6.4.1 on PyPI and its installed source (`neo4j/_sync/driver.py` docstring of `execute_query`, `neo4j/_sync/work/session.py`, `neo4j/_conf.py`). https://pypi.org/project/neo4j/6.4.1/ (checked 2026-10-18)
- [B72] `neo4j-rust-ext` 6.4.1.0 on PyPI and CHANGELOG. https://pypi.org/project/neo4j-rust-ext/ and https://github.com/neo4j/neo4j-python-driver-rust-ext/blob/HEAD/CHANGELOG.md (checked 2026-10-18)
- [B73] neo4j/docker-neo4j `docker-image-src/5/coredb/docker-entrypoint.sh` (fd9e4ec 2026-09-30). https://github.com/neo4j/docker-neo4j (checked 2026-10-18)
- [B74] neo4j-contrib/neo4j-skills `neo4j-import-skill/SKILL.md` (MIT, bb30e1f 2026-10-09). https://github.com/neo4j-contrib/neo4j-skills/blob/main/neo4j-import-skill/SKILL.md (checked 2026-10-18)

DuckDB and Python packages
- [B75] `duckdb` 1.5.6 on PyPI. https://pypi.org/project/duckdb/1.5.6/ (checked 2026-10-18)
- [B76] DuckDB docs, loading JSON (duckdb/duckdb-web e56402c 2026-10-18, `docs/current/data/json/loading_json.md`). https://duckdb.org/docs/stable/data/json/loading_json (checked 2026-10-18)
- [B77] DuckDB docs, CSV import overview. https://duckdb.org/docs/stable/data/csv/overview (checked 2026-10-18)
- [B78] DuckDB docs, configuration overview. https://duckdb.org/docs/stable/configuration/overview (checked 2026-10-18)
- [B79] DuckDB docs, how to tune workloads and environment. https://duckdb.org/docs/stable/guides/performance/how_to_tune_workloads and https://duckdb.org/docs/stable/guides/performance/environment (checked 2026-10-18)
- [B80] DuckDB docs, installing extensions and extension distribution (signing). https://duckdb.org/docs/stable/extensions/installing_extensions and https://duckdb.org/docs/stable/extensions/extension_distribution (checked 2026-10-18)
- [B81] DuckDB community extension `zipfs` (MIT, 1.5.6; repo isaacbrodsky/duckdb-zipfs). https://duckdb.org/community_extensions/extensions/zipfs (checked 2026-10-18)
- [B82] `fsspec` 2026.9.0 on PyPI. https://pypi.org/project/fsspec/ (checked 2026-10-18)
- [B83] `splink` 5.0.0, `orjson` 3.13.0 on PyPI. https://pypi.org/project/splink/ and https://pypi.org/project/orjson/ (checked 2026-10-18)
- [B84] Local tests, 18 October 2026: Python 3.14.6 venv with duckdb 1.5.6, orjson 3.13.0, fsspec 2026.9.0, neo4j 6.4.1; scripts `gen.py`, `bench.py` to `bench8.py` in `/tmp/claude-0/-home-claude/0b4b6737-68ec-5e27-9a94-821f67f5d857/scratchpad/p2-bulk/lab/scripts/` (placeholder data only; scratchpad, not kept)
