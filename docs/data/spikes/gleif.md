# Spike report: GLEIF (`gleif_lei`)

Milestone M1.8b ([PHASE-1.md](../../build/PHASE-1.md)). Research note checked: [sources-ch-gleif.md](../../research/2026-10-16/sources-ch-gleif.md) part B. This report has counts, field names and API behaviour only. The two LEIs named below are the spec's spike example and its parent.

## 1. Command, date, duration, network

| | |
|---|---|
| Command | `uv run neonradar spike gleif --lei 549300OWFMSO9NYV4H90 --ch-number 01800000 --coverage` |
| Date | 21 October 2026, 11:41 UTC (golden copy `publishDate` 2026-10-21T00:00:00Z) |
| Duration | 17 requests in 16.3 s (17.8 s wall clock), 0 retries, 0 responses with 429; without `--coverage`, 9 requests in 8.5 s |
| Network | Direct HTTPS from the build machine (macOS); nothing else about the network was measured. Requests went through `neonradar_ingest.http.HttpClient` at 1 per second (GLEIF allows 60 per minute). |
| Output | `data/cache/spikes/gleif/gleif_lei-20261021-549300OWFMSO9NYV4H90.ftm.jsonl` with its manifest (gitignored) |
| Validation | `uv run neonradar contracts validate-records data/cache/spikes/gleif/*.ftm.jsonl --strict`: 8 records, OK, 0 issues |
| Maintenance window | GLEIF warned of brief interruptions from 19 October to 4 November 2026. No interruption was seen between 11:31 and 11:46 UTC: all 63 GLEIF requests answered, each in 0.3 to 2.5 s. |

The `@pytest.mark.network` test (`cli/tests/test_cli_spike_gleif.py::test_real_gleif_spike`) ran the same command without `--coverage`: 9 requests, 8.5 s, passed. A last change made the client build every path from the checked LEI instead of following URLs found in responses. After it, the network test and `uv run neonradar spike gleif` were run again, with the same output and validation, 9 requests each. Further measurements used the same client from one-off scripts that were not committed, 19 requests in all: response shapes (8), paging limits (3), cursor paging (2), name types (2) and synthetic LEI absence (4).

## 2. What was fetched

| Endpoint | Requests | Result |
|---|---|---|
| `/lei-records/{lei}` | 1 | the spike record |
| `/lei-records/{lei}/direct-parent`, `/direct-parent-relationship` | 2 | parent record and relationship record |
| `/lei-records/{lei}/ultimate-parent`, `/ultimate-parent-relationship` | 2 | parent record and relationship record (same parent as the direct one) |
| `/lei-records/{parent}/direct-parent-reporting-exception`, `/ultimate-parent-reporting-exception` | 2 | 2 reporting exceptions (the parent's own parent links) |
| `/lei-records/{lei}/direct-children?page[size]=1` | 1 | `meta.pagination.total` = 0 |
| `/lei-records?filter[entity.registeredAs]=01800000&filter[entity.registeredAt]=RA000585,RA000586,RA000587` | 1 | 1 record: the spike LEI |
| `/lei-records?filter[...]&page[size]=1` (coverage) | 8 | counts in section 3 |

Records written, by FtM schema: `Company` 2, `Address` 4, `Ownership` 2 (8 in total; `counts.skipped` empty). Manifest notes: 2 reporting exceptions (category and reason), the count of direct children, and the join result.

Spec checks (M1.8b step 1):

- The record is at `RA000585` with `registeredAs` `01800000`. Its direct and ultimate parent are the same LEI, `213800LRO7NS5CYQMN21`, `registeredAs` `04190816` at `RA000585`.
- The parent's own direct and ultimate parent links are reporting exceptions, as the spec expected. Both give the reason `NO_KNOWN_PERSON`.
- **Join:** `registeredAs` matched the Companies House number for the spike company. The reverse lookup returned exactly the spike LEI, at the authority the research note's prefix rule expects (`RA000585`).

## 3. Measured facts against the research note

| Topic | Research note (16 Oct) | Measured (21 Oct) |
|---|---|---|
| Access | No key | Confirmed |
| Rate limit headers, 429 behaviour | UNVERIFIED | No rate limit headers on any response. No 429 at 1 request per second over 63 requests. |
| Content type, redirects | not stated | `application/vnd.api+json`; no redirects |
| `page[size]` maximum | 200; 201 rejected, error status UNVERIFIED | 201 gives **HTTP 400**, a JSON:API error with `title` "Invalid Query Parameter" and `detail` "The page.size must be between 1 and 200." |
| Deep paging | page 50 at size 200 works, page 51 rejected; status UNVERIFIED | Page 50 works (records 9,801 to 10,000). Page 51 gives **HTTP 400**: "Deep page-based pagination is not supported beyond 10000 results ... Alternatively, you can use page[cursor]=* to start cursor-based pagination and then follow the `$.links.next` URL". |
| **Cursor paging (new)** | not known; the note recommends bisecting by registration date | `page[cursor]=*` works: `links` has `first` and `next`, the `next` URL carries `page[cursor]`, two pages had no overlap, and `meta.pagination` gives only `perPage` and `total` |
| Golden copy date | `meta.goldenCopy.publishDate` | Confirmed, on every response |
| Parent links | `lei-record` plus `relationship-record`, or `reporting-exception` | Confirmed. A record without children has no `direct-children` or `ultimate-children` link; the endpoint still answers 200 with `total` 0. |
| Relationship record | `periods` with `ACCOUNTING_PERIOD` and `RELATIONSHIP_PERIOD` | Confirmed. The relationship `id` is `child|LEI|type|<number>|<hash>|` and changes with each new version. |
| Reporting exception | fields `lei`, `category`, `reason`, `reference` | Confirmed (`reference` was null for both) |
| Name types | UNVERIFIED | Five values seen in 100 records with SA and CN legal addresses: `otherNames` `ALTERNATIVE_LANGUAGE_LEGAL_NAME` (30), `TRADING_OR_OPERATING_NAME` (4), `PREVIOUS_LEGAL_NAME` (1); `transliteratedOtherNames` `PREFERRED_ASCII_TRANSLITERATED_LEGAL_NAME` (15), `AUTO_ASCII_TRANSLITERATED_LEGAL_NAME` (29) |
| `registeredAs` format | zero-padded 8 digits, as at Companies House | Confirmed (`01800000`, `04190816`) |

GB coverage (each count is `meta.pagination.total` of one query):

| Query | Research note | Measured | |
|---|---|---|---|
| Jurisdiction `GB` | 233,828 | 234,019 | confirmed (+0.1%) |
| Jurisdiction `GB`, entity active, registration issued | 95,351 | 95,348 | confirmed |
| Legal address country `GB` | about 230,500 to 233,147 | 233,336 | slightly above the range |
| `RA000585` (England and Wales) | 113,227 | 113,359 | confirmed (+0.1%) |
| `RA000587` (Scotland) | 4,831 | 4,839 | confirmed |
| `RA000586` (Northern Ireland) | 1,258 | 1,257 | confirmed |
| All three Companies House codes, active and issued | 62,736 | 62,739 | confirmed |
| Jurisdiction `GB-ENG`, `GB-SCT`, `GB-WLS` or `GB-NIR` | 881 | 882 | confirmed |

The research note's conclusion stands. About 119,455 LEIs are registered at the three Companies House authorities, 62,739 of them active and issued: an enrichment layer for regulated and larger entities, not a backbone.

## 4. Mapping notes

Ids come from `neonradar_contracts.records.make_id`:

- the company is `gleif-lei-<LEI>`;
- its addresses are `gleif-addr-<LEI>-legal` and `gleif-addr-<LEI>-hq`;
- each consolidation link is `gleif-ownership-<20 hex>`, where `make_id` hashes `child|parent|level` into PHASE-1.md 4.4's edge form;
- `nr.source_ref` keeps the native LEI, or the GLEIF relationship record id on an `Ownership`.

| GLEIF field | FtM property (record) |
|---|---|
| `lei` | `leiCode` (Company). FtM checks the LEI check digits and drops an invalid value. |
| `entity.legalName.name` | `name`, in its original script |
| `entity.otherNames[]` of type `ALTERNATIVE_LANGUAGE_LEGAL_NAME`, `TRADING_OR_OPERATING_NAME` | `alias` |
| `entity.otherNames[]` of type `PREVIOUS_LEGAL_NAME` | `previousName` |
| `entity.transliteratedOtherNames[]` of type `PREFERRED_ASCII_TRANSLITERATED_LEGAL_NAME` | `alias` |
| `entity.transliteratedOtherNames[]` of type `AUTO_ASCII_TRANSLITERATED_LEGAL_NAME` | not written (C1 R10: no machine transliterations); counted in the notes |
| `entity.jurisdiction` | `jurisdiction`. FtM writes `GB` as `gb`, keeps `GB-NIR` as `gb-nir`, and reduces `US-DE` to `us`. |
| `entity.registeredAs` | `registrationNumber` (null on some records; the research note found `RA000585` sub-funds without it) |
| `entity.status` | `status` (`ACTIVE`, `INACTIVE`) |
| `entity.legalAddress` | `Address`, role `registered` (`nr.address_roles` on the Company) |
| `entity.headquartersAddress` | `Address`, role `business` |
| address `addressLines`, `addressNumber` | `street`, with the number before the first line |
| address `city`, `postalCode`, `region` (ISO 3166-2), `country` | `city`, `postalCode`, `region`, `country`; `full` joins street, city, postcode and country |
| relationship (`IS_DIRECTLY_CONSOLIDATED_BY`, `IS_ULTIMATELY_CONSOLIDATED_BY`) | `Ownership`, owner the parent and asset the child, with `nr.consolidation` `direct` or `ultimate` (C2 `CONSOLIDATES`, never `OWNS`) |
| relationship `type`, `status` | `role`, `status` |
| `RELATIONSHIP_PERIOD` `startDate`, `endDate` | `startDate`, `endDate`, as dates (FtM would keep a time to the minute) |
| reporting exception `category`, `reason` | manifest `notes` |

Not mapped in the spike, with the field names for Phase 2 to decide:

- `entity.legalForm.id` (an ISO 20275 ELF code such as `H0PO`), `category`, `subCategory`, `creationDate`, `expiration`;
- `successorEntity`, `successorEntities`, `associatedEntity`, `otherAddresses`, `eventGroups`;
- the address fields `mailRouting`, `addressNumberWithinBuilding` and `language`;
- `registration.*` (`initialRegistrationDate`, `status`, `corroborationLevel`, `validatedAt`, `validatedAs`, `managingLou`);
- the identifiers `bic`, `mic`, `ocid`, `qcc`, `gem`, `spglobal`, and `conformityFlag`;
- relationship `ACCOUNTING_PERIOD`, quantifiers and corroboration;
- reporting exception `reference` (free text, up to 500 characters, deliberately left out);
- branch and fund relationships (`IS_INTERNATIONAL_BRANCH_OF`, `IS_FUND-MANAGED_BY`, `IS_SUBFUND_OF`, `IS_FEEDER_TO`), which the spike does not fetch.

The spike follows only one level of parents. For each parent it fetches, it reads that parent's own links, fetching only reporting exceptions; a parent of a parent is noted, not fetched.

## 5. Licence and personal data (for the data steward)

- **Licence:** CC0 1.0, with no attribution required. The manifest carries the courtesy line from `contracts/datasets.yaml`, which says NeonRadar is not affiliated with or endorsed by GLEIF. GLEIF's terms forbid using its logo or implying endorsement, with liquidated damages of CHF 100,000 per breach (research note B5), so no GLEIF logo or "powered by GLEIF" wording may appear anywhere.
- **Personal data:** LEI records describe legal entities, and the spike output holds no natural persons. Two places could carry personal data, and neither is written:
  - a reporting exception with reason `NATURAL_PERSONS` says that people control an entity without naming them;
  - the free-text exception `reference` could name someone.

  Records keep only the category and reason. `datasets.yaml` keeps `personal_data: false`.
- **Output:** the output stays in `data/cache/spikes/gleif/` (gitignored). `neonradar spike clean` deletes it after `access.spike_cache_days`.
- **Committed fixture:** `ingest/tests/fixtures/gleif/responses.json` is synthetic.
  - Its LEIs `SYN00000000000000128`, `...225`, `...322` and `...419` have valid check digits, and GLEIF answered 404 for each on 21 October 2026.
  - Its company numbers `ZZ000001` to `ZZ000004` and postcodes `ZZ0 0ZZ` and `ZZ9 9ZZ` are never issued.
  - Its names were checked on 21 October 2026 in the Companies House search (find-and-update.company-information.service.gov.uk/search/companies?q=), with no exact match for any of: SYNTHETIC CHILD EXAMPLE LIMITED, SYNTHETIC PARENT EXAMPLE PLC, SYNTHETIC APEX EXAMPLE HOLDINGS (PLC), SYNTHETIC JOIN EXAMPLE LIMITED, SYNTHETIC CHILD TRADING, SYNTHETIC CHILD EXAMPLE PUBLIC LIMITED COMPANY.

## 6. Gotchas and recommendations for the Phase 2 loader

1. **Bulk:** load the golden copy (LEI-CDF CSV or JSON plus Level 2 RR and reporting exceptions), not the API. For API slices beyond 10,000 results, use cursor paging (`page[cursor]=*`, then follow `links.next`) instead of bisecting by date. It is simpler and needs no window arithmetic.
2. **The join is deterministic and cheap:** `registeredAt` in `RA000585`, `RA000586` or `RA000587`, plus `registeredAs` equal to the normalised Companies House number (upper case, no spaces, digits zero-padded to 8). Keep the authority filter; `RA000590` also uses `SC` numbers.
3. **No rate limit headers:** throttle on the client side (1 per second) and treat a 400 as a query error, not a reason to retry. The shared client already retries only 429, 500, 502, 503 and 504.
4. **Relationship record ids change with each version** (they embed a number and a hash). Key consolidation links on `child|parent|level`, as the spike does, and keep the GLEIF id in `nr.source_ref`.
5. **Legal and headquarters addresses are often identical.** The spike writes two `Address` records (one per role), and Phase 2's `address_key` deduplicates them.
6. **Strip times from dates.** GLEIF dates carry `T00:00:00Z`, and FtM would keep a minute-precision time.
7. **Subdivision jurisdictions:** 882 records use `GB-ENG`, `GB-SCT`, `GB-WLS` or `GB-NIR`. FtM keeps `gb-nir` and the like, so C2 queries on `jurisdiction = 'gb'` must allow them.
8. **Invalid LEIs vanish quietly.** FtM's `leiCode` drops a value whose check digits are wrong, so a loader should count records whose `leiCode` came out empty.
9. **Maintenance window until 4 November 2026:** the GLEIF client gives up when told to wait more than 120 s, and every test runs on fixtures.

## 7. Verdict

**Go.** The API answered every call. The record, both parents, the reporting exceptions, the children count and the Companies House join all worked as the spec expects, and the output validates in strict mode. The coverage figures confirm the research note within normal daily change. The source stays `status: spike` in `contracts/datasets.yaml` until the Phase 2 loader exists, so the verdict changes neither `DATA_SOURCES.md` nor the registry.
