# Spike report: UK Companies House (`gb_companies_house`)

| | |
|---|---|
| Milestone | M1.8a ([PHASE-1.md](../../build/PHASE-1.md) section 6, M1.8a) |
| Code | `ingest/src/neonradar_ingest/sources/companies_house/` (client, mapping, spike) and `neonradar spike companies-house` |
| Status | **Pending network run (API key not yet available).** Everything is built and tested against synthetic responses; the live run waits for the operator's key (`access.companies_house_key: pending` in [project.yaml](../../build/project.yaml); operator decision OD-14) |
| Written | 21 October 2026, by the M1.8a build agent |
| Research note | [sources-ch-gleif.md](../../research/2026-10-16/sources-ch-gleif.md), Part A; tags such as [CH2] point to its Sources section |

This report holds counts, field names and coverage only. It says nothing about any company or person. The spike is a technical fetch test.

## 1. Command run, date, duration, network conditions

**Not run against the live API yet.** No Companies House API key is available to the build, and agents never read or write `.env` (OD-14). Every figure below marked "mock run" comes from the synthetic response bodies in `ingest/tests/fixtures/companies_house/` (21 October 2026, offline, no network).

**What the operator runs once `CH_API_KEY` is in `.env`** (main checkout, then set `access.companies_house_key: available`):

```bash
uv run neonradar spike companies-house --company 01800000 --max-pages 5
uv run neonradar contracts validate-records data/cache/spikes/companies_house/*.ftm.jsonl --strict
CH_SPIKE_COMPANY=01800000 uv run pytest -m network ingest/tests/test_companies_house_network.py -v
```

`01800000` is the spec's default company number (PHASE-1.md M1.8a step 1), used here only as a command-line example. The first command prints the counts this report needs (records by schema, requests and pages, rate-limit waits and headers, officer and PSC counts, identity verification field names) and writes the records and manifest to `data/cache/spikes/companies_house/`. Paste its output into the pull request and fill in the "Network run" columns below; then set the verdict in section 7.

Mock run, for comparison (synthetic company `SYN00001`, first lines of the summary; the command then prints the strict validation of its output, here 20 records, 0 issues):

```text
company SYN00001: 20 records
requests: 4; pages: officers 2, persons-with-significant-control 1; status codes: 200 4
time: 0.3 s; at 2 requests/s the company costs 2.0 s
rate limit waits: none; headers seen: none
officer appointments: 5 (1 corporate, 20%); natural names as 'SURNAME, Forenames': 4 of 4 (100%)
skipped: psc:super-secure-person-with-significant-control 1
values FtM could not parse: Person.nationality 1
```

Without a key the command stops before any request: `FAIL  CH_API_KEY is not set: the operator adds it to .env (OD-14)`, exit code 1.

## 2. What was fetched

Endpoints (PHASE-1.md M1.8a step 4), all `GET` on `https://api.company-information.service.gov.uk` with the key as the basic auth username and an empty password [CH1]:

| Endpoint | Paging | Mock run | Network run |
|---|---|---|---|
| `/company/{number}` | none | 1 request | to fill in |
| `/company/{number}/officers` | `items_per_page=100`, `start_index`; next page starts after the items received; stops at `total_results` or `--max-pages` | 2 pages (the mock server returned 3 of the 100 asked for, as real servers may) | to fill in |
| `/company/{number}/persons-with-significant-control` | same | 1 page | to fill in |

Records by FtM schema:

| Schema | Built from | Mock run | Network run |
|---|---|---|---|
| `Company` | the company; corporate officers with a company identification; corporate-entity PSCs | 3 | to fill in |
| `LegalEntity` | other corporate officers; legal-person PSCs | 1 | to fill in |
| `Person` | natural officers (one per officer id); individual PSCs | 4 | to fill in |
| `Address` | the registered office | 1 | to fill in |
| `Directorship` | one per officer appointment | 5 | to fill in |
| `Ownership` | one per share or surplus-asset nature of control | 2 | to fill in |
| `Control` | one per voting, appointment or influence nature of control | 4 | to fill in |
| skipped (manifest `counts.skipped`) | super-secure PSCs, unknown PSC kinds, natures that do not map | 1 | to fill in |

The output validated with `neonradar contracts validate-records ... --strict`: 20 records, 0 issues (mock run).

## 3. Measured facts that confirm or correct the research note

Nothing was measured against the live API. The client is built so that the network run measures each of these, and the spike prints them:

| Fact in the research note | What the spike records | Mock run | Network run |
|---|---|---|---|
| 600 requests per 5 minutes; 429 for the rest of the window [CH2] | client-side limiter at 2 requests per second (`REQUESTS_PER_SECOND = 600 / 300`); every 429 wait in seconds | tested: waits until `X-Ratelimit-Reset`, else 300 s, at most three times | to fill in |
| Rate-limit headers `X-Ratelimit-Limit`, `-Remain`, `-Reset`, `-Window` are community-reported, not documented [CHF10] | the names of every `X-Ratelimit-*` header seen (never their values) | none (mock) | to fill in |
| Officers list caps `items_per_page` at 100 (community) [CHF12] | pages per list and items per page | 3 per page by design | to fill in |
| PSC list types `items_per_page` as a string [CH13] | the client never reads it; paging uses `len(items)` and `total_results` | fixture uses `"25"` | to fill in |
| How 404 behaves for a company without PSC data is **UNVERIFIED** [research note A6] | a 404 on a list ends that list with 0 items; a 404 on the profile stops the spike with "not found" | tested | to fill in |
| Officers list has no `name_elements` [CH10] | names kept as given; the share in `SURNAME, Forenames` form is counted | 4 of 4 | to fill in |

## 4. Mapping notes

Ids follow PHASE-1.md 4.4 and `neonradar_contracts.records.make_id` ([C1-record.md](../../../contracts/C1-record.md)); the raw identifier is kept in `nr.source_ref`.

| Source | C1 record and property | Notes |
|---|---|---|
| company `company_number` | `Company` id `gbch-co-<number>`; `registrationNumber`; `nr.source_ref` | number normalised: upper case, no spaces, all-digit numbers zero-padded to 8 |
| `company_name` | `name` | HTML entities unescaped, NFC |
| `jurisdiction` | `jurisdiction` `gb` for `england-wales`, `wales`, `scotland`, `northern-ireland`, `united-kingdom`, `england` | `european-union` and `noneu` are not mapped; counted as `company.jurisdiction=<value>` |
| `company_status`, `type` | `status`, `legalForm` | raw enumeration values |
| `date_of_creation`, `date_of_cessation` | `incorporationDate`, `dissolutionDate` | |
| `previous_company_names[].name` | `previousName` | dates of the name changes are not kept |
| `registered_office_address` | `Address` id `gbch-addr-<first 20 hex of SHA-1 of the full text>`; `full`, `street` (premises and line 1), `street2`, `city`, `region`, `postalCode`, `postOfficeBox`, `country`; the company's `addressEntity` plus `nr.address_roles` `registered` | equal address texts share one record; `care_of` is left out (it can name a person) |
| officer `links.officer.appointments` | id `gbch-off-<officer id>` through `make_id` (`_` becomes `.`); `nr.source_ref` the raw officer id | one record per officer id; an officer with two roles gets one record and two `Directorship`s |
| officer, natural roles | `Person`: `name` (as given), `birthDate` `YYYY-MM` from `date_of_birth`, `nationality` and `country` (from `country_of_residence`), each split on commas and cleaned by FtM | values FtM cannot parse (for example "Not Specified") are dropped and counted |
| officer, `corporate-*` roles | `Company` when `identification.identification_type` is `uk-limited-company`, `eea`, `non-eea` or `registered-overseas-entity-corporate-managing-officer`, else `LegalEntity`; `name`, `registrationNumber`, `legalForm` | not linked to `gbch-co-<number>`: the number "isn't guaranteed to be correct" [CHF21] |
| each officer item | `Directorship` id `gbch-directorship-<hash>`; `director`, `organization`, `role` (raw `officer_role`), `startDate` (`appointed_on`), `endDate` (`resigned_on`), `nr.is_nominee` (true for `nominee-*` and `corporate-nominee-*`), `nr.source_ref` the appointment id | |
| PSC `links.self` | id `gbch-psc-<PSC id>` through `make_id`; `nr.source_ref` the raw id | |
| PSC kinds `individual-person-with-significant-control`, `individual-beneficial-owner` | `Person`: `name`, `firstName`, `middleName`, `lastName`, `title` (from `name_elements`), `birthDate`, `nationality`, `country` | |
| PSC kinds `corporate-entity-*` | `Company`: `name`, `registrationNumber`, `legalForm`, `jurisdiction` (from `identification.country_registered`) | |
| PSC kinds `legal-person-person-with-significant-control`, `legal-person-with-significant-control`, `legal-person-beneficial-owner` | `LegalEntity`, same properties | both documented spellings accepted [CH14] |
| PSC kinds `super-secure-*`, anything else | skipped, counted under `psc:<kind>` | |
| share and surplus-asset natures (`ownership-of-shares-*`, `right-to-share-surplus-assets-*`, `part-right-to-share-surplus-assets-*`) | `Ownership` id `gbch-ownership-<hash>`: `owner` the PSC, `asset` the company, `percentage` `25-50`, `nr.share_pct_min` 25, `nr.share_pct_max` 50, `role` the raw value (keeps `-as-trust`, `-as-firm`), `startDate` (`notified_on`), `endDate` (`ceased_on`), `nr.natures_of_control` | overseas-entity "more than 25%" values become 25 to 100 |
| `voting-rights-*`, `right-to-appoint-and-remove-*`, `significant-influence-or-control*` | `Control` with `controlType` `voting`, `appointment` or `influence`; `controller`, `controlled`, `role`, dates, `nr.natures_of_control` | the voting band stays in `role` and `nr.natures_of_control` (`Control` has no percentage) |
| `registered-owner-as-nominee-*` (overseas entities) | not mapped; counted under `nature:<value>` | Phase 2 decides |

Seen but not mapped (the spike counts how often each appears):

- `identity_verification_details` on officers and PSCs (M1.8a step 6; Phase 2 decides). The fields documented since the 2025 announcement are `appointment_verification_start_on`, `appointment_verification_end_on`, `appointment_verification_statement_date`, `appointment_verification_statement_due_on`, `identity_verified_on`, `authorised_corporate_service_provider_name`, `anti_money_laundering_supervisory_bodies` and `preferred_name` [CH11][CH14][CHF1][CHF4][CHF5]. The object went live on 18 November 2025 and its name was corrected to snake case on 20 October 2025 [CHF1][CHF2]. There is no boolean "verified" field [CHF5]. Super-secure PSCs carry only the start and end dates [CHF3]. The mock run exercises the start, statement date and due date fields.
- Officer `person_number`, `address` (service address), `occupation`, `former_names`, `appointed_before`; PSC `address`, `principal_office_address`, `is_sanctioned`; company `sic_codes`, `accounts`, `confirmation_statement`, `corporate_annotation`.

## 5. Licence and personal-data notes for the data steward

- Licence as recorded in `contracts/datasets.yaml`: register data is made available under the Companies Act 2006 and section 47 approvals, with no Companies House rules on reuse; Companies House's own material is under OGL v3.0, which does not cover personal data [CHF18][CH37][CH40]. Every manifest carries `licence.id` `OGL-UK-3.0` and the attribution line from the registry.
- The spike output holds personal data: officer and PSC names, month and year of birth, nationality and country of residence. It is written only to `data/cache/spikes/companies_house/` (gitignored), and should be deleted after `access.spike_cache_days` (7) with `neonradar spike clean`. A new run for the same company replaces the earlier files. Whoever runs the spike is a UK GDPR controller for that output [CH36].
- Minimised on purpose: no service addresses, no `care_of`, no day of birth (the register never shows it [CH36]), no identity verification values.
- `is_sanctioned` (overseas entity owners) is not mapped. Turning it into a C2 flag on a real person is a data steward decision under guardrail G1.
- Committed test data is synthetic: company numbers start with `SYN`, officer and PSC ids contain `SYN`, and the names were checked against the public Companies House company and officer searches on 21 October 2026 (OD-12; results in the M1.8a pull request). The expected output is a JSON array, never a committed `.ftm.jsonl` file.

## 6. Gotchas and recommendations for the Phase 2 loader

1. **Budget.** The spike costs 1 request for the profile plus one per officer page and per PSC page: at least 3 requests, 1.5 seconds at 2 requests per second, so at most about 200 companies per 5-minute window. The research note's estimate of about 4 requests per company includes PSC statements [research note A6]. Seed the graph from the PSC snapshot and Free Company Data, and use the API for a focus subgraph [CH2][CHF11].
2. **Officer pages.** The officers list includes resigned appointments, so long-lived companies can need several pages. `--max-pages` caps the spike; when it stops early, the manifest `notes` say how many items were read.
3. **One record per officer id, not per human.** `officer_id` is per appointment chain and `person_number` is not a guaranteed person key [CHF9]. Officers and PSCs of the same human get separate records (`gbch-off-...` and `gbch-psc-...`); entity resolution links them.
4. **Names.** The officers list gives `SURNAME, Forenames[, Title]` [CHF19]; PSCs give `name_elements`. Phase 2 computes matching keys at load time (C1 R10), so records keep names as given.
5. **Duplicates across files.** The records of two spike runs for companies that share an officer have the same officer id, so validating both files as one load reports a duplicate id (R4). A production loader merges records by id before writing.
6. **Free-text countries.** `nationality` and `country_of_residence` are free text ("British", "England", "British,Irish"). FtM cleans most of them; the spike splits on commas and counts what FtM drops.
7. **PSC statements.** Not fetched in Phase 1 (M1.8a step 4 lists three endpoints). Phase 2 should decide whether to load `/persons-with-significant-control-statements`.
8. **Tolerate change.** New enumeration values keep arriving (limited partnership reform, February 2026 [CH21]); unknown PSC kinds and natures are skipped and counted rather than failing.

## 7. Verdict

**Pending network run (API key not yet available).**

What the mocks and the documentation already show: the three endpoints map to C1 records that pass the strict validator, and the rate limit allows a per-company spike in a few seconds. Whether the source is "go", "go with changes" or "drop" depends on the live run: authentication works with the key, the field shapes match the documentation, and the officer and PSC counts and the rate-limit behaviour are as expected. The operator runs the commands in section 1, fills in the "Network run" columns, and sets this verdict. `contracts/datasets.yaml` keeps `status: spike` and `DATA_SOURCES.md` is unchanged until then.
