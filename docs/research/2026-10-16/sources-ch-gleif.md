# NeonRadar Phase 1: UK Companies House and GLEIF source verification

All sources checked on **16 October 2026**. Scope: what NeonRadar's loaders need from UK Companies House (CH) and the Global Legal Entity Identifier Foundation (GLEIF), plus short notes on OpenCorporates and Open Ownership. The repository ships loader code and tiny fixtures only; nothing here assumes bulk data in the repo.

## How to read this report

- Every fact carries a source tag such as `[CH2]`. The Sources section at the end gives each tag's URL and the date checked (all 2026-10-16).
- Evidence levels used in the text:
  - **Official**: Companies House, GOV.UK, GLEIF documents, or the official API specifications. No label is added for these.
  - **CH staff**: a reply by a named Companies House staff member on the official developer forum (forum.companieshouse.gov.uk).
  - **Community**: a non-staff forum post or third-party code. Useful, not authoritative.
  - **Observed**: behaviour of a live public API seen on 2026-10-16 (GLEIF API responses were read directly).
  - **UNVERIFIED**: could not be confirmed from an official source.
- Method note: the sandbox's egress policy blocked direct downloads from Companies House and GLEIF hosts, so pages and API responses were read through a web fetch tool. Bulk files were **not** downloaded. Facts about the inside of bulk files (CSV headers, JSON line shapes) therefore come from documentation and third-party parsers, and are labelled as such.

## Findings that change or sharpen the plan

1. **A deterministic CH to GLEIF join exists, but it needs three registration authority codes and a two-part key.** GLEIF `entity.registeredAs` holds the Companies House company number in exactly the CH format (8 characters, zero padded, `SC`/`NI` prefixes) when `entity.registeredAt.id` is `RA000585` (England and Wales), `RA000587` (Scotland) or `RA000586` (Northern Ireland) [GL18][GL19][GL20]. Keying on the number alone is unsafe: `RA000590` (Scottish Charity Register) uses `SC` numbers too [GL18][GL21]. The GLEIF API can look up an LEI by company number (`filter[entity.registeredAs]`), which is undocumented but works (Observed) [GL19].
2. **GLEIF covers only a small slice of UK companies.** About 119,300 LEIs are registered against the three CH authorities, 62,736 of them both active and issued (Observed) [GL20]. GLEIF is an enrichment layer for regulated and larger entities, not a backbone for the UK graph.
3. **There is no free self-serve bulk officers file.** Free CH bulk downloads cover live companies (monthly CSV) and PSCs (daily JSON lines, about 2.2 GB zipped) [CH22][CH24]. Officer bulk products (195/216 snapshot, 198 daily updates) are by email request to `bulkproducts@companieshouse.gov.uk`, with no published price or terms (CH staff) [CHF15]. Officers must come from the REST API per company (600 requests per 5 minutes) or the officers stream [CH2][CH17].
4. **Identity verification data is now in the API, and the transition ends inside the project window.** `identity_verification_details` is on officers, appointments and PSC resources and on the streams [CH11][CH12][CH14][CH20]. Existing directors and PSCs must be verified by mid-November 2026 [CH27]. There is no boolean "verified" flag, and the officers bulk product does not carry these fields (CH staff) [CHF5][CHF7]. After the deadline, "statement due date passed and no start date" becomes a usable red flag.
5. **Officer identity is weak in CH data.** `officer_id` is per appointment chain, not per human (Community) [CHF9]. `person_number` (added April 2024) helps but is not a guaranteed person key (CH staff, Community) [CHF8][CHF9]. Entity resolution remains essential, as planned.
6. **Licence position is permissive for CH and GLEIF, with a personal data catch.** CH imposes no rules on reuse of register data, and CH material is under OGL v3.0 (CH staff, Official) [CHF18][CH37]. OGL v3.0 explicitly does not cover personal data, so anyone loading officers or PSCs becomes a UK GDPR controller [CH36][CH40]. GLEIF LEI data is CC0 with no attribution requirement [GL31].
7. **GLEIF API limits are tighter than they look.** No key, 60 requests per minute, `page[size]` maximum 200, and a hard cap of 10,000 reachable records per query (the last two are undocumented, Observed) [GL10][GL22]. A GB slice (233,828 records) needs date-window partitioning or a streamed golden copy file [GL21][GL26].
8. **GLEIF warns of maintenance during the build.** "Brief service interruptions may occur between 19 October and 4 November 2026" [GL40]. Tests and demos must run from fixtures and cached files.
9. **GLEIF Level 2 is accounting consolidation, not beneficial ownership.** Use CH PSC data for UK beneficial ownership; use GLEIF parents and reporting exceptions as a cross-check [GL27][GL29].
10. **The optional sources are weaker than hoped.** OpenCorporates requires an API key, defaults to 50 calls a day, and its free tier is share-alike ODbL by application [OC2][OC4]. The Open Ownership Register closed on 29 November 2024, and its CC0 BODS 0.4 UK dataset is dated 2025-03-11 [OO4][OO5][OO6].

---

## Part A. UK Companies House

### A1. Public Data REST API: access, keys and rate limits

**Base URLs**

- Live: `https://api.company-information.service.gov.uk` [CH1].
- Sandbox: `https://api-sandbox.company-information.service.gov.uk`, with test keys only. The sandbox search API "responds with live data", and the streaming and document APIs do not run in the sandbox [CH5].
- Data is JSON over TLS only, with TLS 1.2 recommended [CH2].

**Authentication**

- HTTP basic authentication. The API "takes the username as the API or stream key and ignores the password, so it can be left blank" [CH1].
- Example from the docs: `curl -XGET -u my_api_key: https://api.company-information.service.gov.uk/company/00000006`, equivalent to `Authorization: Basic bXlfYXBpX2tleTo=` [CH1].
- So yes: the key is the basic auth username and the password is empty.
- The swagger file declares an `api_key` header scheme [CH8], which conflicts with the authentication page. Follow the authentication page [CH1].

**Registering an application and getting a key**

1. Register a Companies House user account and sign in [CH4][CH6].
2. Create an application: give a name and description, choose between "a test application for use against our sandbox environment" and a live application, and optionally add privacy policy and terms links [CH3].
3. Create a key inside the application [CH3]. Three client types are available:
   - **API key**: for GET requests on public resources.
   - **Stream key**: for the Streaming API.
   - **OAuth web client**: a client ID and secret, used for filing APIs.
4. On Create, "Unique API client credentials will be generated" [CH3]. No approval or review step is described.

Time to issue: **UNVERIFIED** (the docs state no timescale). The wording implies immediate issue.

Live vs test keys: a test application is "for use against our sandbox environment". When switching environments, an application must swap both its base URLs and its keys or OAuth client details [CH3][CH5].

The developer guidelines also set key hygiene rules [CH2]:
- Keep keys out of code; use environment variables.
- Restrict each key to IP addresses or domains.
- Regenerate keys regularly.
- Delete unused keys.

**Rate limit and 429 behaviour**

- Limit: "You can make up to 600 requests within a 5 minute period" [CH2].
- Once over the limit, requests receive `429 Too Many Requests` for the rest of that 5 minute window, and the quota resets at the end of the window [CH2].
- Companies House may ban applications "that regularly exceed or attempt to bypass the rate limits". Higher limits are requested through the GOV.UK contact page [CH2].
- Whether the limit applies per key or per application is not stated: **UNVERIFIED**. The community assumes it is per key and confirms it is not per IP address [CHF10].
- CH staff (MArkWilliams, 24 October 2024) said "Rate limit increases are possible, but only small increases". He added that the API "is designed for real time retrieval of data as it is required, not for the collection of large data sets", and pointed users to the bulk products and streaming service [CHF11].
- A February 2026 staff reply mentions "600 submissions every 5 minutes" with a ceiling of 1,200. That reply concerns XML gateway filing submissions (`xml@companieshouse.gov.uk`), not the REST API [CHF23].

**Rate limit response headers**

These headers are not in the official documentation. Community reports list them as follows [CHF10][CHF11]:

| Header | Content |
|---|---|
| `X-Ratelimit-Limit` | `600` |
| `X-Ratelimit-Remain` | Requests left in the current window |
| `X-Ratelimit-Reset` | Unix epoch seconds |
| `X-Ratelimit-Window` | `5m` |

The Document API spells the second header `X-Ratelimit-Remaining` [CHF10]. Treat all four as hints, and make the code work without them.

**Other guideline rules**

- Accept JSON members in any order.
- Ignore members the client has not seen before.
- Take enumeration mappings from the `companieshouse/api-enumerations` GitHub repository [CH2][CH21].

### A2. Endpoints, fields and enumerations

All endpoints are `GET`, relative to the base URL [CH7][CH8].

| Purpose | Path | Parameters (from the specs) |
|---|---|---|
| Company profile | `/company/{company_number}` | none |
| Registered office | `/company/{company_number}/registered-office-address` | none |
| Officers of a company | `/company/{company_number}/officers` | `items_per_page`, `start_index`, `register_type` (`directors`, `secretaries`, `llp_members`; only with `register_view`), `register_view` (`true`/`false`, default false), `order_by` (`appointed_on`, `resigned_on`, `surname`) [CH10] |
| One appointment | `/company/{company_number}/appointments/{appointment_id}` | none [CH10] |
| All appointments of an officer | `/officers/{officer_id}/appointments` | `items_per_page`, `start_index` (first row is 0), `filter=active` [CH12] |
| PSC list | `/company/{company_number}/persons-with-significant-control` | `items_per_page`, `start_index`, `register_view` (default false) [CH13] |
| One PSC by kind | `.../persons-with-significant-control/individual/{notification_id}`, `/individual-beneficial-owner/{id}`, `/corporate-entity/{id}`, `/corporate-entity-beneficial-owner/{id}`, `/legal-person/{id}`, `/legal-person-beneficial-owner/{id}`, `/super-secure/{super_secure_id}`, `/super-secure-beneficial-owner/{super_secure_id}` | none [CH7] |
| PSC statements | `/company/{company_number}/persons-with-significant-control-statements` and `/{statement_id}` | none [CH7] |
| Search everything | `/search` | `q`, `items_per_page`, `start_index` [CH15] |
| Company search | `/search/companies` | `q`, `items_per_page`, `start_index`, `restrictions` (space separated, for example `active-companies legally-equivalent-company-name`) [CH15] |
| Officer search | `/search/officers` | `q`, `items_per_page`, `start_index` [CH15] |
| Disqualified officer search | `/search/disqualified-officers` | `q`, `items_per_page`, `start_index` [CH15] |
| Advanced company search | `/advanced-search/companies` | `company_name_includes`, `company_name_excludes`, `company_status`, `company_subtype`, `company_type`, `dissolved_from`, `dissolved_to`, `incorporated_from`, `incorporated_to`, `location`, `sic_codes`, `size` (1 to 5000), `start_index` [CH16] |
| Alphabetical search | `/alphabetical-search/companies` | `q`, `search_above`, `search_below`, `size` (1 to 100, else 422) [CH16] |
| Dissolved search | `/dissolved-search/companies` | `q`, `search_type` (`alphabetical`, `best-match`, `previous-name-dissolved`), `search_above`, `search_below`, `size` (1 to 100), `start_index` [CH16] |
| Also available | charges, filing history, insolvency, exemptions, registers, UK establishments, disqualified officers (natural and corporate) | [CH7] |

`search.json` also defines a PSC search operation [CH15], but no path for it appears in the API reference or the swagger path list [CH7][CH8]. Treat PSC search as unavailable (**UNVERIFIED**).

#### Company profile: `/company/{company_number}` [CH9]

Required fields: `company_name`, `company_number`, `type`, `can_file`, `links`.

Fields NeonRadar needs:

| Field | Values or shape |
|---|---|
| `company_status` | `active`, `dissolved`, `liquidation`, `receivership`, `administration`, `voluntary-arrangement`, `converted-closed`, `insolvency-proceedings`, `registered`, `removed`, `closed`, `open` |
| `company_status_detail` | for example `active-proposal-to-strike-off`, `petition-to-restore-dissolved` |
| `type` | for example `ltd`, `plc`, `llp`, `limited-partnership`, `scottish-partnership`, `oversea-company`, `uk-establishment`, `registered-overseas-entity` |
| `subtype` | for example `community-interest-company`, `private-fund-limited-partnership` |
| `date_of_creation`, `date_of_cessation` | dates |
| `jurisdiction` | `england-wales`, `wales`, `scotland`, `northern-ireland`, `european-union`, `united-kingdom`, `england`, `noneu` |
| `registered_office_address` | `care_of`, `premises`, `address_line_1`, `address_line_2`, `locality`, `region`, `postal_code`, `country`, `po_box` |
| `sic_codes` | array of strings |
| `previous_company_names` | array of `{name, effective_from, ceased_on}` |
| `links` | `self`, `officers`, `persons_with_significant_control`, `persons_with_significant_control_statements`, `filing_history`, `charges`, `insolvency`, `registers`, `uk-establishments`, `overseas`, `exemptions` |

Also present: `accounts`, `confirmation_statement`, `foreign_company_details`, `external_registration_number`, `service_address`, `super_secure_managing_officer_count`, `corporate_annotation[]` (`created_on`, `description`, `type`), `registered_office_is_in_dispute`, `undeliverable_registered_office_address`, `partial_data_available` and `etag`.

`has_charges`, `has_insolvency_history`, `has_been_liquidated` and `is_community_interest_company` are deprecated [CH9].

The enumerations repository holds more values than the swagger enums, for example the `eeig-establishment` and `ukeig` types and the `transferred-from-uk` status detail [CH21]. Load enumerations from that repository, not from the swagger enums [CH2].

#### Officers: `/company/{company_number}/officers` [CH10][CH11]

Top-level fields: `items`, `items_per_page`, `start_index`, `total_results`, `active_count`, `resigned_count`, `etag`, `kind` (`officer-list`) and `links.self`.

Each item (`officerSummary`) has these fields:

| Field | Notes |
|---|---|
| `name` | required |
| `officer_role` | required, see the role list below |
| `appointed_on`, `resigned_on` | dates |
| `appointed_before`, `is_pre_1992_appointment` | for pre-1992 appointments |
| `date_of_birth` | `{month, year}` only; the schema has no day field |
| `nationality`, `country_of_residence`, `occupation` | strings |
| `address` | the correspondence (service) address; every subfield optional |
| `former_names[]` | `{forenames, surname}` |
| `identification` | for corporate officers: `identification_type` (`eea`, `non-eea`, `uk-limited-company`, `other-corporate-body-or-firm`, `registered-overseas-entity-corporate-managing-officer`), `legal_authority`, `legal_form`, `place_registered`, `registration_number` |
| `identity_verification_details` | see A5 |
| `person_number` | "Unique person identifier, as shown in bulk products 195, 198, 208, 209, and 216" [CH11] |
| `responsibilities`, `contact_details`, `principal_office_address` | used for overseas entity managing officers |
| `links` | `self`, and `officer.appointments`, which is `/officers/{officer_id}/appointments` |

The officers list has no `name_elements`. That field appears only in the appointments resource [CH10][CH12].

`officer_role` values in the schema [CH10]:

- **Natural persons**: `director`, `secretary`, `llp-member`, `llp-designated-member`, `nominee-director`, `nominee-secretary`, `managing-officer`, `cic-manager`, `judicial-factor`, `receiver-and-manager`, `manager-of-an-eeig`, `member-of-a-management-organ`, `member-of-a-supervisory-organ`, `member-of-an-administrative-organ`, `person-authorised-to-accept`, `person-authorised-to-represent`, `person-authorised-to-represent-and-accept`, `general-partner-in-a-limited-partnership`, `limited-partner-in-a-limited-partnership`.
- **Corporate officers** (prefix `corporate-`): `corporate-director`, `corporate-secretary`, `corporate-llp-member`, `corporate-llp-designated-member`, `corporate-nominee-director`, `corporate-nominee-secretary`, `corporate-managing-officer`, `corporate-manager-of-an-eeig`, `corporate-member-of-a-management-organ`, `corporate-member-of-a-supervisory-organ`, `corporate-member-of-an-administrative-organ`.
- **Added in February 2026 for limited partnership reform** (enumeration file only) [CH21]:
  - roles `corporate-general-partner-in-a-limited-partnership` and `corporate-limited-partner-in-a-limited-partnership`;
  - identification type `limited-partnership-corporate-partner`.

#### Officer appointments: `/officers/{officer_id}/appointments` [CH12]

Top-level fields: `kind` (`personal-appointment`), `is_corporate_officer`, `name`, `date_of_birth` (`{month, year}`), `total_results`, `items_per_page`, `start_index`, `items`, `links.self` and `etag`.

Each item has these fields:

- `appointed_to`: `{company_name, company_number (required), company_status}`.
- `appointed_on`, `resigned_on`. For managing officers, these are the dates Companies House was notified.
- `officer_role`, `name`.
- `name_elements`: `surname` (required), `forename`, `other_forenames`, `title`, `honours`.
- `nationality`, `occupation`, `country_of_residence`, `address`, `principal_office_address`.
- `identification`, `former_names`, `appointed_before`, `is_pre_1992_appointment`.
- `identity_verification_details`, `contact_details`, `responsibilities`.
- `links.company`.

#### Persons with significant control: `/company/{company_number}/persons-with-significant-control` [CH13][CH14]

Top-level fields: `items`, `items_per_page`, `start_index`, `total_results`, `active_count`, `ceased_count` and `links`.

Item fields (the list summary model; required fields are `etag`, `name`, `links`, `address`, `notified_on`, `natures_of_control`):

| Field | Notes |
|---|---|
| `kind` | see the kind list below |
| `name` | display name |
| `name_elements` | `{title, forename, middle_name, surname}` |
| `notified_on`, `ceased_on`, `ceased` | `ceased` is a boolean |
| `date_of_birth` | `{month, year}` in the list model; see note below |
| `nationality`, `country_of_residence` | strings |
| `address` | service address |
| `natures_of_control[]` | full list below |
| `identification` | `{legal_authority, legal_form, place_registered, registration_number, country_registered}` |
| `identity_verification_details` | see A5 |
| `is_sanctioned` | beneficial owners of overseas entities |
| `principal_office_address` | overseas entities |
| `description` | super-secure records |
| `links` | `self`, `statement`, `persons_with_significant_control.notifications` |

Date of birth note: the individual PSC model defines `day`, `month` and `year`, with only month and year required [CH14]. Companies House does not place the day of birth on the public register [CH36]. Treat PSC dates of birth as month and year only.

`kind` values [CH14]:

- `individual-person-with-significant-control`
- `corporate-entity-person-with-significant-control`
- `legal-person-person-with-significant-control`
- `super-secure-person-with-significant-control`
- `individual-beneficial-owner`
- `corporate-entity-beneficial-owner`
- `legal-person-beneficial-owner`
- `super-secure-beneficial-owner`

The spec contradicts itself on one kind. The list summary enum spells it `legal-person-with-significant-control`, while the legal person model uses `legal-person-person-with-significant-control` [CH14]. OpenSanctions' production parser matches the latter (Community) [T1]. Accept both.

The PSC snapshot also contains records of kind `persons-with-significant-control-statement` and `exemptions` (Community) [T1].

Required fields by kind [CH14]:

| Kind | Required fields |
|---|---|
| Individual | `etag`, `notified_on`, `kind`, `country_of_residence`, `date_of_birth`, `name`, `name_elements`, `links`, `nationality`, `address`, `natures_of_control` |
| Corporate entity | `etag`, `notified_on`, `kind`, `name`, `links`, `address`, `identification` (with `legal_authority` and `legal_form` required inside), `natures_of_control` |
| Beneficial owners (overseas entities) | only `etag`, `kind`, `links` |
| Super-secure | `etag`, `kind`, `description`, `links`. No name or address is ever shown; since November 2025 they carry only `identity_verification_details.appointment_verification_start_on` and `_end_on` (CH staff) [CHF3] |

**`natures_of_control`: the complete list of 86 values with official meanings**

These are generated from `psc_descriptions.yml` in `companieshouse/api-enumerations`, last commit 2026-09-11 [CH21].

How to read the values:

- Bands: `25-to-50` means more than 25% but not more than 50%; `50-to-75` means more than 50% but not more than 75%; `75-to-100` means more than 75%.
  - The official short descriptions instead say "75% or more" and "less than 75%" [CH21], which contradicts the long text. Use the long descriptions below.
- `-as-trust`: the person controls a trust whose trustees hold the right.
- `-as-firm`: the person controls a firm without legal personality whose members hold the right.
- Overseas entity values use a single "more than 25%" threshold, plus nominee values for land held in England and Wales, Scotland or Northern Ireland.

##### Companies (24 values)

| Value | Meaning (official description) |
|---|---|
| `ownership-of-shares-25-to-50-percent` | The person holds, directly or indirectly, more than 25% but not more than 50% of the shares in the company. |
| `ownership-of-shares-50-to-75-percent` | The person holds, directly or indirectly, more than 50% but not more than 75% of the shares in the company. |
| `ownership-of-shares-75-to-100-percent` | The person holds, directly or indirectly, more than 75% of the shares in the company. |
| `ownership-of-shares-25-to-50-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the shares in the company. |
| `ownership-of-shares-50-to-75-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the shares in the company. |
| `ownership-of-shares-75-to-100-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 75% of the shares in the company. |
| `ownership-of-shares-25-to-50-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the shares in the company. |
| `ownership-of-shares-50-to-75-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the shares in the company. |
| `ownership-of-shares-75-to-100-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 75% of the shares in the company. |
| `voting-rights-25-to-50-percent` | The person holds, directly or indirectly, more than 25% but not more than 50% of the voting rights in the company. |
| `voting-rights-50-to-75-percent` | The person holds, directly or indirectly, more than 50% but not more than 75% of the voting rights in the company. |
| `voting-rights-75-to-100-percent` | The person holds, directly or indirectly, more than 75% of the voting rights in the company. |
| `voting-rights-25-to-50-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the voting rights in the company. |
| `voting-rights-50-to-75-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the voting rights in the company. |
| `voting-rights-75-to-100-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 75% of the voting rights in the company. |
| `voting-rights-25-to-50-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the voting rights in the company. |
| `voting-rights-50-to-75-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the voting rights in the company. |
| `voting-rights-75-to-100-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 75% of the voting rights in the company. |
| `right-to-appoint-and-remove-directors` | The person holds the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `right-to-appoint-and-remove-directors-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `right-to-appoint-and-remove-directors-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `significant-influence-or-control` | The person has the right to exercise, or actually exercises, significant influence or control over the company. |
| `significant-influence-or-control-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |
| `significant-influence-or-control-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |

##### LLPs (24 values)

| Value | Meaning (official description) |
|---|---|
| `right-to-share-surplus-assets-25-to-50-percent-limited-liability-partnership` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets of the LLP on a winding up. |
| `right-to-share-surplus-assets-50-to-75-percent-limited-liability-partnership` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets of the LLP on a winding up. |
| `right-to-share-surplus-assets-75-to-100-percent-limited-liability-partnership` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 75% of any surplus assets of the LLP on a winding up. |
| `right-to-share-surplus-assets-25-to-50-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets on a winding up of the LLP. |
| `right-to-share-surplus-assets-50-to-75-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets on a winding up of the LLP. |
| `right-to-share-surplus-assets-75-to-100-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 75% of any surplus assets on a winding up of the LLP. |
| `right-to-share-surplus-assets-25-to-50-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets of the LLP on a winding up. |
| `right-to-share-surplus-assets-50-to-75-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets of the LLP on a winding up. |
| `right-to-share-surplus-assets-75-to-100-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share 75% or more of any surplus assets of the LLP on a winding up. |
| `voting-rights-25-to-50-percent-limited-liability-partnership` | The person holds, directly or indirectly, more than 25% but not more than 50% of the voting rights in the LLP. |
| `voting-rights-50-to-75-percent-limited-liability-partnership` | The person holds, directly or indirectly, more than 50% but not more than 75% of the voting rights in the LLP. |
| `voting-rights-75-to-100-percent-limited-liability-partnership` | The person holds, directly or indirectly, more than 75% of the voting rights in the LLP. |
| `voting-rights-25-to-50-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the voting rights in the LLP. |
| `voting-rights-50-to-75-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the voting rights in the LLP. |
| `voting-rights-75-to-100-percent-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 75% of the voting rights in the LLP. |
| `voting-rights-25-to-50-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% but not more than 50% of the voting rights in the LLP. |
| `voting-rights-50-to-75-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 50% but not more than 75% of the voting rights in the LLP. |
| `voting-rights-75-to-100-percent-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) hold, directly or indirectly, more than 75% of the voting rights in the LLP. |
| `right-to-appoint-and-remove-members-limited-liability-partnership` | The person holds the right, directly or indirectly, to appoint or remove a majority of the members who are entitled to take part in the management of an LLP. |
| `right-to-appoint-and-remove-members-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the members who are entitled to take part in the management of the LLP. |
| `right-to-appoint-and-remove-members-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the members who are entitled to take part in the management of the LLP. |
| `significant-influence-or-control-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the LLP. |
| `significant-influence-or-control-as-trust-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the LLP. |
| `significant-influence-or-control-as-firm-limited-liability-partnership` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed is not a legal person; and the members of that firm (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the LLP. |

##### Partnerships, eligible Scottish partnerships (12 values)

| Value | Meaning (official description) |
|---|---|
| `part-right-to-share-surplus-assets-25-to-50-percent` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets of the partnership on a winding up. |
| `part-right-to-share-surplus-assets-50-to-75-percent` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets of the partnership on a winding up. |
| `part-right-to-share-surplus-assets-75-to-100-percent` | The person holds or is treated as holding, directly or indirectly, the right to share in more than 75% of any surplus assets of the partnership on a winding up. |
| `part-right-to-share-surplus-assets-25-to-50-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets on a winding up of the partnership. |
| `part-right-to-share-surplus-assets-50-to-75-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets on a winding up of the partnership. |
| `part-right-to-share-surplus-assets-75-to-100-percent-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust; and the trustee of that trust (in their capacity as such) hold or are treated as holding, directly or indirectly, the right to share in more than 75% of any surplus assets on a winding up of the partnership. |
| `part-right-to-share-surplus-assets-25-to-50-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share in more than 25% but not more than 50% of any surplus assets of the partnership on a winding up. |
| `part-right-to-share-surplus-assets-50-to-75-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share in more than 50% but not more than 75% of any surplus assets of the partnership on a winding up. |
| `part-right-to-share-surplus-assets-75-to-100-percent-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold or as treated as holding, directly or indirectly, the right to share 75% or more of any surplus assets of the partnership on a winding up. |
| `right-to-appoint-and-remove-person` | The person holds the right, directly or indirectly, to appoint or remove a majority of the persons who are entitled to take part in the management of the partnership. |
| `right-to-appoint-and-remove-person-as-firm` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a firm that, under the law by which it is governed, is not a legal person; and the members of that firm (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the persons who are entitled to take part in the management of the partnership. |
| `right-to-appoint-and-remove-person-as-trust` | The person has the right to exercise, or actually exercises, significant influence or control over the activities of a trust, and the trustees of that trust (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the persons who are entitled to take part in the management of the partnership. |

##### Overseas entities, ROE (26 values)

| Value | Meaning (official description) |
|---|---|
| `ownership-of-shares-more-than-25-percent-registered-overseas-entity` | The beneficial owner holds, directly or indirectly, more than 25% of the shares in the entity. |
| `ownership-of-shares-more-than-25-percent-as-trust-registered-overseas-entity` | Beneficial owner is a trustee of a trust and: the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% of the shares in the entity. |
| `ownership-of-shares-more-than-25-percent-as-firm-registered-overseas-entity` | The beneficial owner is a member of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% of the shares in the entity. |
| `ownership-of-shares-more-than-25-percent-as-control-over-trust-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a trust, and: the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% of the shares in the entity. |
| `ownership-of-shares-more-than-25-percent-as-control-over-firm-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% of the shares in the entity. |
| `voting-rights-more-than-25-percent-registered-overseas-entity` | The beneficial owner holds, directly or indirectly, more than 25% of the voting rights in the entity. |
| `voting-rights-more-than-25-percent-as-trust-registered-overseas-entity` | Beneficial owner is a trustee of a trust and: the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% of the voting rights in the entity. |
| `voting-rights-more-than-25-percent-as-firm-registered-overseas-entity` | The beneficial owner is a member of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% of the voting rights in the entity. |
| `voting-rights-more-than-25-percent-as-control-over-trust-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a trust, and: the trustees of that trust (in their capacity as such) hold, directly or indirectly, more than 25% of the voting rights in the entity. |
| `voting-rights-more-than-25-percent-as-control-over-firm-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold, directly or indirectly, more than 25% of the voting rights in the entity. |
| `right-to-appoint-and-remove-directors-as-control-over-trust-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a trust, and: the trustees of that trust (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `right-to-appoint-and-remove-directors-as-control-over-firm-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `significant-influence-or-control-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant influence or control over the entity. |
| `significant-influence-or-control-as-trust-registered-overseas-entity` | Beneficial owner is a trustee of a trust and: the trustees of that trust (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |
| `significant-influence-or-control-as-firm-registered-overseas-entity` | The beneficial owner is a member of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |
| `significant-influence-or-control-as-control-over-trust-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a trust, and: the trustees of that trust (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |
| `significant-influence-or-control-as-control-over-firm-registered-overseas-entity` | The beneficial owner has the right to exercise, or actually exercises, significant control or influence over the activities of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) have the right to exercise, or actually exercise, significant influence or control over the company. |
| `right-to-appoint-and-remove-directors-registered-overseas-entity` | The beneficial owner holds the right, directly or indirectly, to appoint or remove a majority of the board of directors of the entity. |
| `right-to-appoint-and-remove-directors-as-trust-registered-overseas-entity` | Beneficial owner is a trustee of a trust and: the trustees of that trust (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `right-to-appoint-and-remove-directors-as-firm-registered-overseas-entity` | The beneficial owner is a member of a firm that is not a legal person under its governing law, and: the members of that firm (in their capacity as such) hold the right, directly or indirectly, to appoint or remove a majority of the board of directors of the company. |
| `registered-owner-as-nominee-person-england-wales-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for this person: England and Wales. |
| `registered-owner-as-nominee-person-scotland-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for this person: Scotland. |
| `registered-owner-as-nominee-person-northern-ireland-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for this person: Northern Ireland. |
| `registered-owner-as-nominee-another-entity-england-wales-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for another entity of which this person is a registered beneficial owner: England and Wales. |
| `registered-owner-as-nominee-another-entity-scotland-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for another entity of which this person is a registered beneficial owner: Scotland. |
| `registered-owner-as-nominee-another-entity-northern-ireland-registered-overseas-entity` | The overseas entity is the registered owner of property or land in the following UK jurisdictions, as a nominee for another entity of which this person is a registered beneficial owner: Northern Ireland. |

**PSC statement values (28)** [CH21]

- `no-individual-or-entity-with-signficant-control`. The key really is misspelled "signficant" in the official enumeration, so match it exactly.
- `psc-exists-but-not-identified`, `psc-details-not-confirmed`, `steps-to-find-psc-not-yet-completed`, `psc-contacted-but-no-response`, `psc-has-failed-to-confirm-changed-details`, `restrictions-notice-issued-to-psc`.
- `-partnership` variants of the seven values above.
- Overseas entity statements: `all-beneficial-owners-identified`, `no-beneficial-owner-identified`, `at-least-one-beneficial-owner-unidentified`, `information-not-provided-for-at-least-one-beneficial-owner`, `at-least-one-beneficial-owner-unidentified-and-information-not-provided-for-at-least-one-beneficial-owner`.
- Update and relevant-period statements: `nobody-has-become-or-ceased-to-be-a-beneficial-owner`, `somebody-has-become-or-ceased-to-be-a-beneficial-owner`, `no-change-beneficial-owner-relevant-period`, `change-beneficial-owner-relevant-period`, `no-trust-involved-relevant-period`, `trust-involved-relevant-period`, `no-change-beneficiary-relevant-period`, `change-beneficiary-relevant-period`.
- `awaiting-confirmation-from-psc`.

For AML work, "PSC exists but not identified", "contacted but no response" and "restrictions notice issued" are direct risk signals.

#### Pagination

All list endpoints use `items_per_page` and `start_index`. The swagger specs publish no defaults or maximums for the officers, PSC or search lists [CH10][CH13][CH15]. Known limits:

| Endpoint | Limit | Evidence |
|---|---|---|
| Officers list | maximum `items_per_page` of 100 | Community, 2019 [CHF12] |
| Company search | requests above 100 per page return 100; results beyond about 1,000 are unreachable (`start_index=1000` returned HTTP 416) | Community, November 2025 [CHF13] |
| Officer search | a paging depth cap was "deliberately introduced to prevent behaviour that was causing performance issues" | CH staff (rmcneil), 22 December 2016 [CHF14] |
| Officer search | cap later observed at 400 results | Community, 2017 [CHF14] |
| Advanced search | `size` 1 to 5000 per request | Official [CH16] |
| Alphabetical and dissolved search | `size` 1 to 100 | Official [CH16] |
| Appointments list | first row is index 0 | Official [CH12] |
| PSC list and appointments list | maximum page size | **UNVERIFIED** |

The server may return fewer items than requested, so advance by `len(items)` and stop on `total_results` (Community) [CHF13].

### A3. Bulk products and the Streaming API

**Free Company Data Product** [CH22][CH23][CH25]

- URL: `https://download.companieshouse.gov.uk/en_output.html`
- Content: "basic company data of live companies on the register". Live companies only, with no officers and no PSCs.
- Format and size:
  - CSV inside ZIP.
  - One file: `BasicCompanyDataAsOneFile-2026-10-01.zip`, 471 MB.
  - Or seven parts: `BasicCompanyData-2026-10-01-part1_7.zip` to `part7_7.zip`, 50 to 70 MB each.
- Frequency: monthly. "The latest snapshot will be updated within 5 working days of the previous month end." Current file dated 2026-10-01.
- Support and licence: "provided free of charge and will not be supported". No licence is stated on the page.
- Columns, from the official field list PDF, in order [CH23]:
  - `CompanyName` (160), `CompanyNumber` (8).
  - Registered office: CareOf, POBox, AddressLine1, AddressLine2, PostTown, County, Country, PostCode.
  - `CompanyCategory`, `CompanyStatus`, `CountryofOrigin`, `DissolutionDate`, `IncorporationDate`.
  - Accounts: AccountingRefDay, AccountingRefMonth, NextDueDate, LastMadeUpDate, AccountsCategory.
  - Returns: NextDueDate, LastMadeUpDate.
  - Mortgages: NumMortCharges, NumMortOutstanding, NumMortPartSatisfied, NumMortSatisfied.
  - SIC codes 1 to 4 (code and text).
  - LimitedPartnerships: NumGenPartners, NumLimPartners.
  - `URI`.
  - Previous names 1 to 10 (change date and name).
  - `ConfStmtNextDueDate`, `ConfStmtLastMadeUpDate`.
- Literal header names (Community): OpenSanctions' parser uses dotted headers such as `RegAddress.PostTown`, `SICCode.SicText_1`, `PreviousName_1.CONDATE`, `PreviousName_1.CompanyName` and `Accounts.AccountRefDay`, and strips whitespace from header cells [T1]. Exact headers are **UNVERIFIED** by direct download.
- Data quality notes, from the same parser's comments (Community) [T1]:
  - Some rows carry an extra field, such as a fifth SIC code, which shifts later columns. Skip those rows.
  - Names can contain HTML entities such as `&amp;`.

**PSC snapshot** [CH24][CH26]

- URL: `https://download.companieshouse.gov.uk/en_pscdata.html`
- Files:
  - One file: `persons-with-significant-control-snapshot-2026-10-15.zip`.
  - Or 33 parts: `psc-snapshot-2026-10-15_1of33.zip` to `_33of33.zip`, 3 to 72 MB each, about 2.2 GB zipped in total (sum of the listed part sizes).
- Frequency: daily. The file "will be updated every morning before 10am GMT", with data compiled to the end of the previous day. Free and unsupported.
- Format: the page says only JSON in ZIP.
  - Forum users and OpenSanctions' parser confirm one JSON object per line, with top-level `company_number` and `data` keys. `data` is the API PSC resource, with `links.self` (Community) [CHF22][T1].
  - A trailing summary or totals line: **UNVERIFIED** (OpenSanctions skips lines without `company_number`) [T1].
- Contents: PSC records plus statements and exemptions [T1]. Whether overseas entity beneficial owners are included is **UNVERIFIED** from an official source. Open Ownership built its UK and overseas entity dataset from the snapshot plus the API [OO8].
- Data quality (Community) [T1]: the snapshot keeps PSC statements long after a company leaves the register, so filter against the live company list.
- Licence: data.gov.uk's licence field for this dataset reads "TBD" [CH26].

**Accounts data**: daily and monthly iXBRL files, free [CH25]. Not needed for Phase 1.

**Officers bulk data (not free self-serve)**

- The GOV.UK data products page lists no officers product [CH25].
- On 4 March 2026, a staff member directed a request for Product 216 (officer appointments snapshot), Product 198 (daily updates), and Products 199 and 201 (charges) to `bulkproducts@companieshouse.gov.uk` (CH staff, kadach) [CHF15].
- Older threads name Product 195 (active officer appointments snapshot) and 198 (updates) (Community) [CHF16][CHF17]. The official officer resource names products 195, 198, 208, 209 and 216 [CH11].
- Price, licence terms and approval time: **UNVERIFIED** (not published).
- Prod195 does not contain `identity_verification_details`: "It is not currently possible to get the identity_verification_details in bulk for officers" (CH staff, cbaldwin, 9 December 2025) [CHF7].

**Streaming API** [CH5][CH17][CH18][CH19][CH20]

- Host: `https://stream.companieshouse.gov.uk`.
- Paths: `/companies`, `/filings`, `/insolvency-cases`, `/charges`, `/officers`, `/persons-with-significant-control`, `/disqualified-officers`, `/company-exemptions`, `/persons-with-significant-control-statements`.
- Authentication: a stream key, created like an API key [CH3][CH19] and sent as the basic auth username [CH1].
- Format: a long-lived HTTP response, "returned one-per-line" [CH18]. Each event envelope has these fields [CH20]:
  - `resource_kind`, `resource_uri`, `resource_id`, `data`;
  - `event`, containing `timepoint`, `published_at`, `type` (`changed` or `deleted`) and `fields_changed`.
- Blank lines are heartbeats [CH17].
- Resuming: pass `timepoint` to resume from a past event. A timepoint that is too old, or a consumer that is too slow, gets `416` [CH17][CH18]. How far back a timepoint can reach: **UNVERIFIED**.
- Connection rules [CH17]:
  - "A maximum of two concurrent connections per-account". A third closes the oldest.
  - On `429`, wait one minute.
  - Retry other retryable errors after 10 seconds.
  - A client that does not handle 429 may have its IP blocked.
- The officers stream carries `identity_verification_details` and `person_number` [CH20][CHF7]. The stream is not available in the sandbox [CH5].

### A4. Licence and terms

**Register data**

- Companies House's Service Owner, Robert McNeil (4 November 2021), said the register is made available under the Companies Act 2006 and that database right is not infringed by extracting or using its contents (CH staff) [CHF18]. In his words:
  - "Companies House imposes no rules or requirements on how the information on the public register is used."
  - "You are responsible for complying with any applicable data protection, copyright and other legislation and regulations."
- The GOV.UK public task page says [CH37]:
  - Material produced by Companies House is Crown copyright and available under the Open Government Licence v3.0 "except where otherwise stated".
  - Register data is made available through approvals under section 47 of the Copyright, Designs and Patents Act 1988 and Schedule 1 of the Database Regulations (SI 1997/3032).
  - There are no restrictions on use, except three: take your own advice on third-party copyright (for example in filed documents); do not reproduce the Crown insignia; credit Companies House when using its guidance, website, publications or statistics.
- The Crown copyright page asks that "the source of the material must be identified and the copyright status acknowledged" [CH38].

**Exact OGL v3.0 attribution statement**

"Contains public sector information licensed under the Open Government Licence v3.0." [CH40]

- Conditions: "acknowledge the source of the Information in your product or application by including or linking to any attribution statement", and "where possible, provide a link to this licence" [CH40].
- The National Archives' own page could not be fetched on 2026-10-16 [CH39]. The text above was verified from SPDX's copy [CH40].

**Recommended NeonRadar attribution line** (a proposal combining the OGL statement with the source credit Companies House asks for, not a text Companies House mandates):

> Contains public sector information licensed under the Open Government Licence v3.0. Source: Companies House (https://www.gov.uk/government/organisations/companies-house).

**Personal data (officers and PSCs are real people)**

- OGL v3.0 "does not cover: personal data in the Information" [CH40].
- Companies House's personal information charter says organisations that reuse register data "become controllers of your personal data" and "must establish how they comply with the data protection law" [CH36].
- So every NeonRadar user who loads officer or PSC data is a UK GDPR controller, with their own lawful basis and retention duties. The project should say so in its docs. This report is not legal advice.

**Residential addresses and full dates of birth**

- The usual residential address and the day of the date of birth "will not be placed on the public register" [CH36].
- The API exposes month and year of birth only, and a correspondence address [CH11][CH20].
- Overseas entity data shows month and year of birth only and no home addresses [CH33].
- People can apply to remove their home address from register documents [CH31]:
  - where it was used as a service address;
  - or where it was used as a registered office, if the company is dissolved or has moved.
- Since 21 July 2025, people can also remove the day of birth (from documents filed before 10 October 2015), signatures and business occupation, at £34 per document (fee updated 1 February 2026) [CH31].
- For accepted removals the register shows only the first half of a UK postcode [CH31].

Implications for NeonRadar:
- Never attempt to reconstruct residential addresses or full dates of birth.
- Prefer re-fetching to long-term caching of personal data, so suppressions flow through.

**Other conditions**

- The register search services "are not intended to be a source for bulk downloads". Heavy automated users "may be denied access to these services without notice" [CH35].
- Companies House "cannot take any responsibility for the consequences of errors or omissions" [CH35].

### A5. 2024 to 2026 changes that affect the data

**Economic Crime and Corporate Transparency Act 2023 (ECCTA) timeline**

| Date | Change | Source |
|---|---|---|
| 4 March 2024 | First set of ECCTA changes. The campaign page lists registrar powers to query information, new registered office rules and a registered email address among the changes, without per-item dates | [CH30] |
| 6 April 2024 | `person_number` added to officer resources and the officers stream; `address` and `appointed_on` made optional (CH staff, MArkWilliams, 28 March 2024) | [CHF8] |
| 18 March 2025 | Authorised Corporate Service Provider (ACSP) registration service launched | [CH29] |
| 8 April 2025 | Voluntary identity verification opened | [CH27] |
| 21 July 2025 | Wider removal of personal details (day of birth, signatures, occupation) | [CH31] |
| 31 August 2025 | Overseas entity trust information available on request | [CH32] |
| 18 November 2025 | Identity verification mandatory for new directors and PSCs. Existing directors verify at their next confirmation statement within 12 months. Existing PSCs get a 14 day window, which for PSCs who are not directors starts on the first day of their birth month. Statutory company registers of directors, residential addresses, secretaries and PSCs abolished | [CH27][CH28][CH30]; register abolition date from a law firm summary of the DBT report [CH41][CH42] |
| mid-November 2026 | 12 month phase-in ends; "6 to 7 million individuals" expected to verify | [CH27] |
| no earlier than November 2027 | Identity verification for presenters (filers) | [CH29] |
| by 1 April 2027 (expected) | Secondary legislation for limited partnership reform and filer verification | [CH41] (secondary) |
| April 2028 | Accounts reform: small companies file profit and loss accounts; software-only iXBRL filing | [CH29][CH41] |
| Later | Corporate directors, corporate LLP members and officers of corporate PSCs: requirements commence later | [CH27] |

On what the public register will show, Companies House says only: "In the future, we'll publish a note against your name on the Companies House public register" [CH28].

**Identity verification in the API**

`identity_verification_details` is an optional object on:
- `officerSummary` (company officers list);
- appointment items;
- individual PSCs and PSC list items;
- the officers and PSC streams.

Sources: [CH11][CH12][CH14][CH20], announced by cbaldwin on 9 September 2025 with a 18 November 2025 go-live [CHF1]. The name was corrected to snake case `identity_verification_details` on 20 October 2025 (CH staff) [CHF2].

| Field | Meaning |
|---|---|
| `appointment_verification_start_on` | Date an identity verification statement was supplied for this appointment. Present for "ALL appointments" where a statement was submitted (CH staff) [CHF5] |
| `appointment_verification_end_on` | Date the statement was removed; statements "can be revoked" [CHF4] |
| `appointment_verification_statement_date` | Date from which a statement can be supplied. In the PSC model and the announcement, but not listed on the officer resource page [CH11][CH14][CHF1] |
| `appointment_verification_statement_due_on` | Deadline for supplying the statement. Populated "approximately 4 weeks in advance" [CHF1] |
| `identity_verified_on` | Date an ACSP verified the person. ACSP verifications only (CH staff) [CHF5] |
| `authorised_corporate_service_provider_name`, `anti_money_laundering_supervisory_bodies` | ACSP verifications only [CH11][CHF5] |
| `preferred_name` | Name given to the ACSP [CH11] |

How to read these fields:

- **No boolean "verified" flag exists.** People who verify through GOV.UK One Login get no `identity_verified_on` (Community, consistent with CH staff) [CHF5][CHF6].
- Proposed status logic (our inference, not an official rule):
  - verified for this appointment = `appointment_verification_start_on` present and `appointment_verification_end_on` absent;
  - overdue = `appointment_verification_statement_due_on` in the past and no start date.
- Super-secure PSCs show only the start and end dates [CHF3].
- None of this is in officers bulk Prod195 [CHF7].

**Other data-affecting changes**

- `person_number` is "the same number" as in the officer bulk product (CH staff, 2 April 2024) [CHF8].
  - A community analysis says the first 8 characters identify the person and the last 4 are a change counter. It also reports several 8-character IDs for one apparent person (Community, January 2025) [CHF9].
  - A unique officer identifier is still missing [CHF9].
- New `corporate_annotation` types [CH21][CH9]:
  - strike-off under section 1002A for misleading, false or deceptive incorporation or restoration information;
  - `overseas-entity-dissolved-wound-up-or-ceased-to-exist`.
- Limited partnership reform: new company subtypes (October 2025) and officer roles and identification types (February 2026) [CH21]. Expect unknown enum values and tolerate them [CH2].
- Dissolved companies: Companies House now keeps dissolved records for 20 years and has added companies dissolved since January 2010 to the online service. Making older records free online waits until "the law is changed to allow greater protection of personal information on the public register" [CH35].

**Register of Overseas Entities (ROE)**

- In force since 1 August 2022. Each entity gets "a unique Overseas Entity ID" [CH33].
- Not public: home addresses, full dates of birth ("only the month and year will be shown"), email addresses and trust information [CH33].
- Overseas entities appear in the same API as companies:
  - Example: `OE000002`, HANLEY PARKS LTD, company type "Overseas entity", status "Registered", registered on 3 August 2022, incorporated in the Isle of Man [CH34].
  - Company type `registered-overseas-entity`, with statuses `registered` and `removed` [CH9].
  - Beneficial owners via the PSC endpoints, with `*-beneficial-owner` kinds and overseas entity `natures_of_control` [CH14][CH21].
  - Managing officers via the officers endpoint, with the `managing-officer` and `corporate-managing-officer` roles [CH10].
  - `is_sanctioned` is a field on beneficial owners [CH14].
- Trust information: on request only, since 31 August 2025, at £55 per overseas entity, with no API or bulk access [CH32]. Rules:
  - Anyone can request one entity; minors' details are removed.
  - Requests covering several entities, or a minor, need evidence of legitimate interest (money laundering, tax evasion, terrorist financing or sanctions breaches).
  - Day of birth and home addresses are never shared.
- Open Ownership counted more than 30,000 overseas entities when it converted the register to BODS in March 2025 [OO8].

### A6. Minimal spike (Python 3.12+, httpx)

This was compiled and exercised offline against mocked responses shaped like the documented JSON: short pages, a 429 retry, and corporate officers. It was **not** run against the live API, because no key was available and the sandbox blocked the host.

```python
"""Companies House spike: one company profile, its officers and its PSCs.

Usage:  CH_API_KEY=xxxx python ch_spike.py 00617987
Needs:  pip install httpx   (Python 3.12+)
"""

from __future__ import annotations

import os
import sys
import time
from collections.abc import Iterator
from typing import Any

import httpx

BASE_URL = "https://api.company-information.service.gov.uk"
PAGE_SIZE = 100  # community-reported ceiling; always trust len(items), not this number


class CompaniesHouse:
    def __init__(self, api_key: str, timeout: float = 30.0) -> None:
        # The API key is the HTTP basic auth username; the password is empty.
        self._client = httpx.Client(
            base_url=BASE_URL,
            auth=httpx.BasicAuth(api_key, ""),
            timeout=timeout,
            headers={"User-Agent": "neonradar-spike/0.1"},
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for attempt in range(6):
            r = self._client.get(path, params=params)
            if r.status_code == 404:
                return None  # unknown number, or no resource of this kind for the company
            if r.status_code == 429:
                # 429 lasts for the rest of the 5 minute window. X-Ratelimit-Reset is
                # community-reported (epoch seconds), so fall back to 60 s if absent.
                reset = r.headers.get("X-Ratelimit-Reset")
                wait = float(reset) - time.time() if reset and reset.isdigit() else 60.0
                time.sleep(min(max(wait, 1.0), 300.0))
                continue
            if r.status_code >= 500:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            remain = r.headers.get("X-Ratelimit-Remain")
            if remain is not None and remain.isdigit() and int(remain) < 20:
                time.sleep(5.0)  # slow down near the 600 per 5 minutes ceiling
            return r.json()
        raise RuntimeError(f"giving up on {path}")

    def paged(self, path: str) -> Iterator[dict[str, Any]]:
        start = 0
        while True:
            page = self.get(path, {"items_per_page": PAGE_SIZE, "start_index": start})
            if not page:
                return
            items = page.get("items") or []
            yield from items
            start += len(items)  # the server may return fewer than requested
            total = page.get("total_results")
            if not items or (total is not None and start >= total):
                return


def normalise_company_number(raw: str) -> str:
    n = raw.strip().upper().replace(" ", "")
    return n.zfill(8) if n.isdigit() else n  # 617987 -> 00617987; SC045551 unchanged


def split_officer_name(name: str) -> dict[str, str | None]:
    """Natural officers come back as 'SURNAME, Forenames[, Title]'."""
    parts = [p.strip() for p in name.split(",")]
    return {
        "surname": parts[0] if parts else None,
        "forenames": parts[1] if len(parts) > 1 else None,
        "title": ", ".join(parts[2:]) or None,
    }


def main(raw_number: str) -> None:
    ch = CompaniesHouse(os.environ["CH_API_KEY"])
    number = normalise_company_number(raw_number)

    profile = ch.get(f"/company/{number}")
    if profile is None:
        sys.exit(f"{number}: not found (unknown, or dissolved outside the online window)")
    print(
        "COMPANY", number, profile["company_name"], profile.get("company_status"),
        profile.get("type"), profile.get("date_of_creation"), profile.get("date_of_cessation"),
        profile.get("sic_codes"), len(profile.get("previous_company_names") or []),
    )

    for o in ch.paged(f"/company/{number}/officers"):
        role = o["officer_role"]
        corporate = role.startswith("corporate-")
        officer_id = o["links"]["officer"]["appointments"].split("/")[2]
        dob = o.get("date_of_birth") or {}  # month and year only
        idv = o.get("identity_verification_details") or {}
        ident = o.get("identification") or {}
        print(
            "OFFICER", role, o["name"],
            None if corporate else split_officer_name(o["name"]),
            o.get("appointed_on"), o.get("resigned_on"),
            f"{dob.get('year')}-{dob.get('month'):02d}" if dob.get("month") else None,
            o.get("nationality"), o.get("country_of_residence"),
            officer_id, o.get("person_number"),
            ident.get("identification_type"), ident.get("registration_number"),
            idv.get("appointment_verification_start_on"),
            idv.get("appointment_verification_statement_due_on"),
        )

    for p in ch.paged(f"/company/{number}/persons-with-significant-control"):
        ident = p.get("identification") or {}
        print(
            "PSC", p.get("kind"), p.get("name"), p.get("name_elements"),
            p.get("notified_on"), p.get("ceased_on"), p.get("natures_of_control"),
            ident.get("legal_form"), ident.get("registration_number"),
            ident.get("country_registered"), ident.get("place_registered"),
        )

    for s in ch.paged(f"/company/{number}/persons-with-significant-control-statements"):
        print("PSC-STATEMENT", s.get("statement"), s.get("notified_on"), s.get("ceased_on"))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "00617987")
```

Budget: one company costs about 4 requests (profile, officers, PSCs, statements). At 600 requests per 5 minutes that is about 150 companies per 5 minutes, or about 1,800 per hour per key. Expanding a network through `/officers/{id}/appointments` multiplies the cost. Seed bulk from the PSC snapshot and Free Company Data, and use the API only to enrich a focus subgraph [CH2][CHF11].

**Realistic gotchas**

1. **Rate limits.** 429 lasts for the rest of the 5 minute window [CH2]. Rate limit headers are undocumented [CHF10]. Companies House discourages bulk harvesting through the API [CHF11].
2. **Name formats.**
   - Natural officers come back as `SURNAME, Forenames[, Title]`, for example "ELGAMAL, Nivin Saad Eldin Mohamed, Duchess". Staff confirmed the format would be "consistent" (forum reply, 5 July 2018) [CHF19].
   - The officers list has no `name_elements`; appointments and PSCs do [CH10][CH12][CH14].
   - The allowed character set is undocumented (Community, May 2026) [CHF20].
   - Expect HTML entities in names [T1].
3. **Corporate officers.** `identification.registration_number` "isn't guaranteed to be correct". "There is no attempt to correlate the corporate officer with any company on the register", and the number "could be foreign too" (CH staff, Steve Bowen, 29 November 2019) [CHF21]. Normalise the number and verify it against `/company/{n}` before linking.
4. **No person key.** `officer_id` and `person_number` both fragment for one human (Community) [CHF9]. Entity resolution must combine name, month and year of birth, nationality and service address.
5. **Dissolved companies.**
   - Online only for companies dissolved since January 2010, with 20 year retention [CH35].
   - Free Company Data has live companies only [CH22].
   - The PSC snapshot retains statements for companies that have left the register [T1].
   - What a 404 means for the PSC endpoint of a company with no PSC data: **UNVERIFIED**.
6. **Optional and partial data.**
   - `address` and `appointed_on` have been optional since April 2024 [CHF8].
   - Beneficial owner records require only `etag`, `kind` and `links` [CH14].
   - `partial_data_available` marks companies whose data sits with another regulator [CH9].
7. **Spec inconsistencies.**
   - The legal person kind is spelled two ways [CH14].
   - The PSC list types `items_per_page` as a string [CH13].
   - A statement key is misspelled [CH21].
   - The 75% band wording conflicts between short and long descriptions [CH21].
8. **Format normalisation.** Company numbers are 8 characters. Left-pad all-digit numbers with zeros (`617987` becomes `00617987`) and keep prefixes such as `SC`, `NI` and `OE` [CH34][GL19].

---

## Part B. GLEIF

### B1. Golden Copy, delta and concatenated files

**Latest golden copy publish** (Observed from the discovery API on 2026-10-16) [GL1][GL2]

| File | CDF version | Records | CSV zip | JSON zip | XML zip |
|---|---|---|---|---|---|
| Level 1 LEI-CDF (`lei2`) | LEI_3.1 | 3,462,481 (15 Oct 00:00 publish); 3,463,426 (15 Oct 16:00) | 481 MB | 881 MB | 848 MB |
| Level 2 RR-CDF (`rr`) | RR_2.1 | 491,006 | 23.3 MB | 33.5 MB | 31.7 MB |
| Level 2 Reporting Exceptions (`repex`) | REPEX_2.1 | 6,418,310 | 59.3 MB | 61.4 MB | 66.4 MB |

**Delta files**: four per publish, each in CSV, JSON and XML [GL1][GL5]. They list new LEIs and changed reference data against an earlier golden copy:

| API name | Compared against | Example size (`lei2`, 15 Oct 00:00 publish) |
|---|---|---|
| `IntraDay` | 8 hours earlier | 5,127 records |
| `LastDay` | 24 hours earlier | 22,283 records, 3.0 MB CSV zip |
| `LastWeek` | 7 days earlier | 119,813 records |
| `LastMonth` | 31 days earlier | 410,355 records |

**Frequency**

- "GLEIF issues three sets of Golden Copy Files daily" [GL5][GL6].
- The golden copy page gives publication times of 02:00, 10:00 and 18:00 UTC [GL5].
- The discovery API's `publish_date` stamps read 00:00, 08:00 and 16:00, with no timezone stated [GL4]. These are probably data cut-off times: **UNVERIFIED**.
- The golden copy database itself is updated "up to ten times a day" [GL5].

**Compression**: ZIP (file names end `.csv.zip`, `.json.zip` and `.xml.zip`) [GL1].

**Discovery API**

- `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest` returns all three types [GL1].
- `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes/{lei2|rr|repex}/latest` returns one type [GL2][GL3][GL7].
- `GET https://goldencopy.gleif.org/api/v2/golden-copies/publishes` returns the history [GL4].
- Response shape: `data.{lei2|rr|repex}.{publish_date, full_file.{csv|json|xml}.{url, size, record_count, cdf_version}, delta_files.{IntraDay|LastDay|LastWeek|LastMonth}.{csv|json|xml}}` [GL1].
- File URL pattern [GL1]:
  `https://goldencopy.gleif.org/storage/golden-copy-files/YYYY/MM/DD/{id}/YYYYMMDD-HHMM-gleif-goldencopy-{lei2|rr|repex}-{golden-copy|intra-day|last-day|last-week|last-month}.{csv|json|xml}.zip`
- `leidata-preview.gleif.org` is a legacy domain for the same API [GL7].

**Observed caveat**: repeated "latest" calls returned different publish dates (Observed) [GL1][GL2][GL3]:
- 2026-09-10 08:00 for the combined endpoint with a query string;
- 2026-09-27 16:00 for `rr/latest`;
- 2026-10-15 00:00 for the combined endpoint;
- 2026-10-15 16:00 for `lei2/latest`.

This may be caching somewhere in the fetch path. Loaders should check that `publish_date` is recent (within about 8 hours) and never older than the last one processed, and fall back to the history listing.

**Golden copy vs concatenated files** [GL5][GL7][GL8]

- Concatenated files combine each LEI issuer's daily file unmodified, in XML only. During a transfer between issuers they can list an LEI twice, and technical glitches can drop records.
- The golden copy lists each LEI once and "always contain[s] all LEIs ever published". It adds geocoding and normalised addresses, comes in XML, CSV and JSON, and has delta files.
- Concatenated files for 2026-10-15, with URLs `https://leidata.gleif.org/api/v1/concatenated-files/{lei2|rr|repex}/get/{id}/zip` [GL8]:

| File | Records | Size |
|---|---|---|
| LEI-CDF 3.1 | 3,463,231 | 521 MB |
| RR-CDF 2.1 | 674,077 | 36.5 MB |
| Reporting Exceptions 2.1 | 6,252,332 | 48.2 MB |

- Why the concatenated RR count (674,077) differs from the golden copy (491,006): **UNVERIFIED**.
- The golden copy content is also published as RDF [GL6].

**CSV columns**

- LEI CSV columns are indexed for repeating elements, for example `Entity.SuccessorEntity.1.*` to `.5.*` [GL7].
- The registry number column corresponds to the XML element `Entity/RegistrationAuthority/RegistrationAuthorityEntityID` (Community: OpenSanctions' crawler reads that element) [T2]. The exact CSV header is **UNVERIFIED** (download blocked).
- A third-party RR CSV fixture shows the columns `Relationship.StartNode.NodeID`, `Relationship.EndNode.NodeID`, `Relationship.RelationshipType`, `Relationship.RelationshipStatus`, `Registration.*`, `Relationship.Period.{1..5}.{startDate,endDate,periodType}` and `Relationship.Qualifiers.{1..5}.*` (Community) [T3].

### B2. GLEIF REST API (`https://api.gleif.org/api/v1`)

**Access**

- No key or registration. Every call made for this report was unauthenticated and succeeded (Observed) [GL11].
- Use of LEI data carries no charge, and GLEIF does not enter individual contracts with users [GL10].
- The API is built on the GLEIF Golden Copy. It offers filters, full-text search, "fuzzy" matching, parent and child relationships, BIC lookups and ISIN mappings [GL9].

**Rate limit**

- "Rate limiting is currently set at 60 requests, per minute, per user, for all users" [GL10].
- Rate limit headers and 429 behaviour: **UNVERIFIED** (undocumented).

**Pagination**

- Parameters: `page[number]` and `page[size]` [GL10].
- Maximum `page[size]` is **200**: 201 and 500 were rejected (Observed) [GL22].
- Deep paging stops at **10,000 records**: page 50 at size 200 (records 9,801 to 10,000) worked, while pages 51 and 60 were rejected (Observed) [GL22].
- Neither limit is documented [GL10]. The exact error status is **UNVERIFIED**.

**Filters** [GL10]

- Documented: `filter[lei]`, `filter[bic]`, `filter[isin]`, `filter[fulltext]`, `filter[entity.legalName]`, `filter[entity.legalAddress.country]`, `filter[entity.category]`, `filter[registration.status]`, `filter[entity.expiration.date]`, `filter[owns]`, `filter[ownedBy]`.
- Operators:
  - `a,b` (in a list);
  - `!a` (not);
  - `x..y` (range);
  - `>`, `>=`, `<`, `<=`;
  - dates written as `YYYYMMDD`.
- Sorting: `sort=field`.
- Undocumented but working (Observed) [GL19][GL20][GL21][GL26]: `filter[entity.jurisdiction]`, `filter[entity.status]`, `filter[entity.registeredAs]`, `filter[entity.registeredAt]`, `filter[registration.initialRegistrationDate]`, `filter[entity.creationDate]`.
- `filter[entity.registeredAt.id]` is rejected (Observed). Use `filter[entity.registeredAt]`.

**Endpoints**

Read from the record's relationship links (Observed) [GL11][GL12][GL13][GL14][GL15]:

| Purpose | Path |
|---|---|
| One record | `/lei-records/{lei}` |
| Direct parent | `/lei-records/{lei}/direct-parent` (record), `/direct-parent-relationship` (RR record), `/direct-parent-reporting-exception` |
| Ultimate parent | `/lei-records/{lei}/ultimate-parent`, `/ultimate-parent-relationship`, `/ultimate-parent-reporting-exception` |
| Children | `/lei-records/{lei}/direct-children`, `/direct-child-relationships`, `/ultimate-children`, `/ultimate-child-relationships` |
| Branches and others | `/branches`, `/branch-relationships`, `/isins`, `/managing-lou`, `/lei-issuer`, `/field-modifications` |
| Fuzzy name search | `/fuzzycompletions?field={entity.legalName\|fulltext\|owns\|ownedBy}&q=...` [GL10] |
| Type-ahead | `/autocompletions?field=fulltext&q=...` [GL17] |
| Registration authority | `/registration-authorities/{RA code}` [GL18] |
| Field catalogue | `/fields` (336 fields) [GL23] |

How the parent links behave:

- A record's `relationships.direct-parent.links` holds either `relationship-record` plus `lei-record` (a parent with an LEI is reported) or `reporting-exception` (no parent reported) [GL11][GL12]. Branch on which key is present.
- Example: HSBC Bank plc (`MP6I5ZYZBEU3UXPYFY54`) has a direct and an ultimate parent, both HSBC Holdings plc (`MLU0ZO3ML4LN2LL2TL39`) [GL12][GL13].
- HSBC Holdings plc has 58 direct children across CN, BM, VG, US-DE and other jurisdictions [GL15].

Search examples:

- `fuzzycompletions` with the misspelled `q=hsbc holdngs` returned HSBC HOLDINGS PLC first, plus three near matches [GL16].
- Each item is `{type, attributes.value, relationships.lei-records.data.id}`.
- `autocompletions` adds `highlighting`. It omits the LEI when the completion is not itself a legal name [GL17].

**Key JSON fields** (HSBC Holdings plc, Observed) [GL11]

| Field | Example or shape |
|---|---|
| `lei` | `MLU0ZO3ML4LN2LL2TL39` |
| `entity.legalName` | `{name, language}` |
| `entity.otherNames[]` | `{name, language, type}` |
| `entity.transliteratedOtherNames[]` | `{name, language, type}` |
| `entity.legalAddress`, `entity.headquartersAddress` | `language`, `addressLines[]`, `addressNumber`, `addressNumberWithinBuilding`, `mailRouting`, `city`, `region` (ISO 3166-2, for example `GB-LND`), `country`, `postalCode` |
| `entity.registeredAt` | `{id: "RA000585", other}` |
| `entity.registeredAs` | `"00617987"` |
| `entity.jurisdiction` | `"GB"` |
| `entity.legalForm` | `{id: "B6ES", other}` (an ISO 20275 ELF code) |
| `entity.category`, `entity.subCategory` | for example `GENERAL` |
| `entity.status` | `ACTIVE` or `INACTIVE` |
| `entity.creationDate`, `entity.expiration` | dates; `expiration` is `{date, reason}` |
| `entity.successorEntity`, `entity.successorEntities[]`, `entity.associatedEntity` | successor and fund links |
| `registration` | `initialRegistrationDate`, `lastUpdateDate`, `status` (`ISSUED` etc.), `nextRenewalDate`, `managingLou`, `corroborationLevel`, `validatedAt.id`, `validatedAs`, `otherValidationAuthorities` |
| Mapped identifiers | `bic`, `mic`, `ocid` (OpenCorporates ID, `gb/00617987`), `qcc`, `gem`, `spglobal` |
| Other | `conformityFlag`; `meta.goldenCopy.publishDate` |

**Transliteration data relevant to the mission** (Observed) [GL24][GL25]

- A Saudi record has legal name "شركة تمرة المالية" (language `ar`).
  - `transliteratedOtherNames`: "Tamra Financial Company", type `PREFERRED_ASCII_TRANSLITERATED_LEGAL_NAME`.
  - `otherNames`: "Tamra Capital", type `TRADING_OR_OPERATING_NAME`.
- A Chinese record carries a `PREVIOUS_LEGAL_NAME` alongside its ASCII transliteration.
- Many records have empty name arrays.
- Other name type values: **UNVERIFIED** in this check.

### B3. Relationship records (RR-CDF 2.1) and reporting exceptions

**RR-CDF 2.1** (XSD dated 2021-03-04; state transition and validation rules v2.8.5 dated 2025-07-03) [GL27][GL28]

| Element | Values |
|---|---|
| Relationship type | `IS_DIRECTLY_CONSOLIDATED_BY`, `IS_ULTIMATELY_CONSOLIDATED_BY`, `IS_INTERNATIONAL_BRANCH_OF`, `IS_FUND-MANAGED_BY`, `IS_SUBFUND_OF`, `IS_FEEDER_TO` |
| Relationship status | `ACTIVE`, `INACTIVE`, `NULL` |
| Period type | `ACCOUNTING_PERIOD`, `RELATIONSHIP_PERIOD`, `DOCUMENT_FILING_PERIOD` |
| Qualifier dimension | `ACCOUNTING_STANDARD` |
| Accounting standard (qualifier category) | `US_GAAP`, `IFRS`, `OTHER_ACCOUNTING_STANDARD`, `GOVERNMENT_ACCOUNTING_STANDARD` |
| Quantifiers | `MeasurementMethod`: `ACCOUNTING_CONSOLIDATION`; `QuantifierUnits`: `PERCENTAGE`; `QuantifierAmount`: decimal |
| Corroboration (ValidationSources) | `PENDING` (never published), `ENTITY_SUPPLIED_ONLY`, `PARTIALLY_CORROBORATED`, `FULLY_CORROBORATED` |
| Validation documents | `ACCOUNTS_FILING`, `REGULATORY_FILING`, `SUPPORTING_DOCUMENTS`, `CONTRACTS`, `OTHER_OFFICIAL_DOCUMENTS` |
| Registration status | `PENDING_VALIDATION`, `PUBLISHED`, `DUPLICATE`, `LAPSED`, `RETIRED`, `ANNULLED`, `TRANSFERRED`, `PENDING_TRANSFER`, `PENDING_ARCHIVAL` |
| Node ID type | `LEI`, `ISO_17442_COMPATIBLE` |

**Direction**: the start node is the child and the end node is the parent. Example: start HSBC Bank plc, end HSBC Holdings plc, type `IS_DIRECTLY_CONSOLIDATED_BY` (Observed) [GL12].

The same API record shows the typical fields [GL12]:
- `periods`: an `ACCOUNTING_PERIOD` from 2025-01-01 to 2025-12-31, and a `RELATIONSHIP_PERIOD` from 2024-06-30 with no end;
- `registration.status`: `PUBLISHED`;
- `corroborationLevel`: `ENTITY_SUPPLIED_ONLY`;
- `corroborationDocuments`: `ACCOUNTS_FILING`;
- `corroborationReference`: a URL to the annual report.

**Reporting Exceptions 2.1** (XSD dated 2021-07-20) [GL29][GL30]

- Exception categories: `DIRECT_ACCOUNTING_CONSOLIDATION_PARENT` and `ULTIMATE_ACCOUNTING_CONSOLIDATION_PARENT` only. There are no exception categories for fund or branch links.
- Fields: `LEI`, `ExceptionCategory`, `ExceptionReason`, `ExceptionReference` (free text, up to 500 characters), `NextVersion`, `Extension`.

| Reason | Meaning |
|---|---|
| `NATURAL_PERSONS` | Controlled by natural person(s) with no intermediate legal entity |
| `NON_CONSOLIDATING` | Controlled by legal entities not subject to consolidation |
| `NO_KNOWN_PERSON` | No known person controls the entity, for example dispersed shareholders |
| `NO_LEI` | The parent does not consent to obtaining an LEI |
| `NON_PUBLIC` | Disclosure is restricted. Since 1 March 2022 this replaces `LEGAL_OBSTACLES`, `CONSENT_NOT_OBTAINED`, `BINDING_LEGAL_COMMITMENTS`, `DETRIMENT_NOT_EXCLUDED` and `DISCLOSURE_DETRIMENTAL`, which stay in the schema as deprecated values |

Example: HSBC Holdings plc's direct parent exception has reason `NON_CONSOLIDATING` (Observed) [GL14].

AML use: compare reasons against Companies House PSC data. For example, a company whose GLEIF exception says `NATURAL_PERSONS` should have an individual PSC; a mismatch is worth surfacing.

### B4. Registration authority codes and the deterministic join

**Registration authorities** (Observed) [GL18]

| Code | Register | Organisation | Jurisdiction |
|---|---|---|---|
| `RA000585` | Companies Register | Companies House | England and Wales |
| `RA000586` | Companies Register | Companies House | Northern Ireland |
| `RA000587` | Companies Register | Companies House | Scotland |
| `RA000590` | Scottish Charity Register | Scottish Charity Regulator (OSCR) | Scotland |
| `RA999999` | "No Registration Authority available" | none | none |

**`registeredAs` holds the Companies House number** (Observed) [GL11][GL19][GL20]

| Company | Code | `registeredAs` |
|---|---|---|
| HSBC Holdings plc | RA000585 | `00617987` |
| HSBC Bank plc | RA000585 | `00014259` |
| NatWest Group plc | RA000587 | `SC045551` |
| FEEHOGUE HOLDINGS LIMITED | RA000586 | `NI741128` |

- The format matches Companies House: zero-padded 8 digits, or a 2-letter prefix plus 6 digits.
- Queries for unpadded numbers (`617987`, `14259`, `1942105`) returned nothing [GL20].
- `registration.validatedAt` and `validatedAs` repeat the registry details for HSBC [GL11].
- `ocid` gives a second key into OpenCorporates (`gb/00617987`) [GL11].

**Coverage on 2026-10-16** (Observed) [GL20][GL21][GL22]

| Query | Records |
|---|---|
| Jurisdiction `GB` | 233,828 |
| Jurisdiction `GB`, entity active, registration issued | 95,351 |
| Legal address country `GB` | about 230,500 to 233,147 (the count varied between calls) |
| `RA000585` (England and Wales) | 113,227 (113,118 with jurisdiction `GB`) |
| `RA000587` (Scotland) | 4,831 |
| `RA000586` (Northern Ireland) | 1,258 |
| All three CH codes, entity active, registration issued | 62,736 |
| Jurisdiction `GB-ENG`, `GB-SCT`, `GB-WLS` or `GB-NIR` | 881 |

Data quality points from these queries:

- 881 records use a subdivision jurisdiction instead of `GB`. Example: NORTH COAST WIND LIMITED, `RA000586`, jurisdiction `GB-NIR`.
- Some `RA000585` records have a null `registeredAs`, for example sub-funds of umbrella investment companies [GL20].
- Roughly half of GB-jurisdiction LEIs (233,828 in total, against about 119,300 at the three Companies House codes) are not registered at Companies House. Samples include trusts, pension schemes, clubs and charities with `RA999999` or another authority such as `RA000590` [GL20][GL21][GL26].

**Join rule (recommended)**

```text
gleif.entity.registeredAt.id IN {RA000585, RA000586, RA000587}
AND norm(gleif.entity.registeredAs) == norm(ch.company_number)
norm(x) = x.strip().upper().replace(" ", ""); if x.isdigit(): x = x.zfill(8)
optional check: SC -> RA000587, NI -> RA000586, otherwise RA000585
```

- Overseas entities (`OE...`) and overseas companies (`FC...`) have no verified Companies House registration authority code in GLEIF: **UNVERIFIED**.
- Reverse lookup through the API: `/lei-records?filter[entity.registeredAs]=00617987&filter[entity.registeredAt]=RA000585,RA000586,RA000587` (Observed) [GL19][GL20].

**Mapping files**

- **BIC-to-LEI**
  - Built on "a mapping process established by SWIFT and certified by GLEIF". CSV in ZIP, updated monthly; latest `LEI-BIC-20260925.zip` [GL34].
  - Licence: a custom "BIC/LEI Mapping Table License Agreement" version 1.0 [GL35]. It allows any purpose, including commercial, and is transferable and sub-licensable.
  - Every copy must include a notice reading "SWIFT © and database rights" with the version date and a reference to www.swift.com/bic. No trademark rights are granted. The data is provided as-is.
- **ISIN-to-LEI**
  - GLEIF with ANNA. A daily full CSV with columns `ISIN` and `LEI`, and no delta files; latest `isin-lei-20261015T071508.zip` [GL36][GL37].
  - Described as "publicly available, open source relationship files" [GL38]. No licence is named on any page checked: **UNVERIFIED**.
  - The API also offers `/lei-records/{lei}/isins` and `filter[isin]` [GL10][GL11].
- **OpenCorporates-to-LEI**: bi-weekly CSV; latest `oc-lei-20261013T071215.zip`; no licence stated (**UNVERIFIED**) [GL39].
- **Other mapping files**: MIC (monthly), S&P CIQ (weekly), QCC (monthly), GEM (monthly) [GL33].

### B5. Licence

- "The data available through the Access Service are provided under the CC0 licence", and the service "is provided for free" [GL31].
- No attribution is required, and no attribution text is recommended [GL31].
- Conditions [GL31]:
  - Users acquire no intellectual property rights in LEIs or LEI reference data.
  - Using GLEIF's trademark or logo requires contacting GLEIF.
  - Users must not create "the impression that" their data or services are provided, supported or authorised by GLEIF, and must not make statements that "may mislead the public" about any relationship with GLEIF or the LEI issuers.
  - Data is provided "AS IS".
  - Breaches can incur liquidated damages of CHF 100,000 per case, under Swiss law with Basel courts.
- GLEIF's AI Terms of Use cover only GLEIF's own chatbot. Its outputs may not be used to train AI without permission. They do not govern LEI data [GL32].
- Optional courtesy line for NeonRadar (not required; avoids implying endorsement):

  > LEI data from the GLEIF Global LEI Index, available under CC0 1.0 (https://www.gleif.org). NeonRadar is not affiliated with or endorsed by GLEIF.

### B6. Minimal spike and a GB slice without the golden copy

This was compiled and exercised offline against mocked responses shaped like the live JSON observed on 2026-10-16: parent and exception branching, the join lookup, and window bisection. It was not run live from the sandbox, because the host was blocked for scripts.

```python
"""GLEIF spike: one LEI record, its direct and ultimate parents, a CH join, a GB slice.

Usage:  python gleif_spike.py
Needs:  pip install httpx   (Python 3.12+). No API key.
"""

from __future__ import annotations

import calendar
import datetime as dt
import time
from collections.abc import Iterator
from typing import Any

import httpx

API = "https://api.gleif.org/api/v1"
CH_RAS = ("RA000585", "RA000586", "RA000587")  # Companies House: E&W, NI, Scotland
GB_JURISDICTIONS = "GB,GB-ENG,GB-SCT,GB-WLS,GB-NIR"
MAX_PAGE_SIZE = 200  # 201 is rejected (observed 2026-10-16)
MAX_REACHABLE = 10_000  # page[number] * page[size] beyond this is rejected (observed)


class Gleif:
    def __init__(self) -> None:
        self._c = httpx.Client(
            base_url=API,
            headers={"Accept": "application/vnd.api+json", "User-Agent": "neonradar-spike/0.1"},
            timeout=60.0,
        )
        self._last = 0.0

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        for attempt in range(6):
            wait = 1.05 - (time.monotonic() - self._last)  # 60 requests per minute per user
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            r = self._c.get(path, params=params)
            if r.status_code == 404:
                return None
            if r.status_code == 429:
                time.sleep(60.0)
                continue
            if r.status_code >= 500:
                time.sleep(2**attempt)
                continue
            r.raise_for_status()
            return r.json()
        raise RuntimeError(f"giving up on {path}")


def summary(rec: dict[str, Any]) -> dict[str, Any]:
    a = rec["attributes"]
    e = a["entity"]
    return {
        "lei": a["lei"],
        "name": e["legalName"]["name"],
        "translit": [n["name"] for n in e.get("transliteratedOtherNames") or []],
        "ra": (e.get("registeredAt") or {}).get("id"),
        "registered_as": e.get("registeredAs"),
        "jurisdiction": e.get("jurisdiction"),
        "entity_status": e.get("status"),
        "registration_status": a["registration"]["status"],
    }


def parents(g: Gleif, lei: str) -> dict[str, Any]:
    rec = g.get(f"/lei-records/{lei}")
    if rec is None:
        raise KeyError(lei)
    rels = rec["data"]["relationships"]
    out: dict[str, Any] = {"self": summary(rec["data"])}
    for kind in ("direct-parent", "ultimate-parent"):
        links = (rels.get(kind) or {}).get("links") or {}
        if "lei-record" in links:  # parent has an LEI and a published relationship
            parent = g.get(f"/lei-records/{lei}/{kind}")
            rr = g.get(f"/lei-records/{lei}/{kind}-relationship")
            r = rr["data"]["attributes"]["relationship"] if rr else {}
            out[kind] = {
                "parent": summary(parent["data"]) if parent else None,
                "type": r.get("type"),
                "status": r.get("status"),
                "periods": r.get("periods"),
            }
        elif "reporting-exception" in links:  # no parent reported, with a reason
            ex = g.get(f"/lei-records/{lei}/{kind}-reporting-exception")
            out[kind] = {"exception": ex["data"]["attributes"]["reason"] if ex else None}
    return out


def lei_for_company_number(g: Gleif, company_number: str) -> list[dict[str, Any]]:
    """Deterministic CH -> LEI join: registration authority AND registry number."""
    data = g.get(
        "/lei-records",
        {
            "filter[entity.registeredAs]": company_number,
            "filter[entity.registeredAt]": ",".join(CH_RAS),
        },
    )
    return [summary(r) for r in (data or {}).get("data", [])]


def _window_records(
    g: Gleif, window: str, bisect: tuple[dt.date, dt.date] | None = None
) -> Iterator[dict[str, Any]]:
    """Yield every record in one initialRegistrationDate window. If the window is over
    the 10,000 record cap and is a date range, bisect it and recurse."""
    params: dict[str, Any] = {
        "filter[entity.jurisdiction]": GB_JURISDICTIONS,
        "filter[registration.initialRegistrationDate]": window,
        "page[size]": MAX_PAGE_SIZE,
        "page[number]": 1,
    }
    page = g.get("/lei-records", params)
    if not page or not page.get("data"):
        return
    pagination = page["meta"]["pagination"]
    if pagination["total"] > MAX_REACHABLE:
        if bisect is None or bisect[0] == bisect[1]:
            raise RuntimeError(f"{window}: {pagination['total']} records, cannot split further")
        start, end = bisect
        mid = start + (end - start) // 2
        nxt = mid + dt.timedelta(days=1)
        yield from _window_records(g, f"{start:%Y%m%d}..{mid:%Y%m%d}", (start, mid))
        yield from _window_records(g, f"{nxt:%Y%m%d}..{end:%Y%m%d}", (nxt, end))
        return
    while True:
        for rec in page["data"]:
            yield summary(rec)
        if params["page[number]"] >= pagination["lastPage"]:
            return
        params["page[number]"] += 1
        page = g.get("/lei-records", params)
        if not page or not page.get("data"):
            return


def gb_slice(g: Gleif, first_year: int = 2012, last_year: int = 2026) -> Iterator[dict[str, Any]]:
    """All GB-jurisdiction LEIs without the golden copy, partitioned by initial
    registration month (bisected further where a month is over the cap)."""
    yield from _window_records(g, f"<={first_year - 1}1231")  # registered before first_year
    for y in range(first_year, last_year + 1):
        for m in range(1, 13):
            start = dt.date(y, m, 1)
            end = dt.date(y, m, calendar.monthrange(y, m)[1])
            yield from _window_records(g, f"{start:%Y%m%d}..{end:%Y%m%d}", (start, end))


if __name__ == "__main__":
    g = Gleif()
    print(parents(g, "MP6I5ZYZBEU3UXPYFY54"))  # HSBC Bank plc -> HSBC Holdings plc
    print(lei_for_company_number(g, "00617987"))  # HSBC Holdings plc
    print(lei_for_company_number(g, "SC045551"))  # NatWest Group plc (RA000587)
    for i, rec in enumerate(gb_slice(g)):  # about 1,200 requests (~20 min) for all of GB
        if i >= 5:
            break
        print(rec)
```

**Options for a country slice**

1. **API, partitioned (no bulk download)**
   - Filter on `filter[entity.jurisdiction]=GB,GB-ENG,GB-SCT,GB-WLS,GB-NIR` with `page[size]=200`.
   - Split by `filter[registration.initialRegistrationDate]=YYYYMMDD..YYYYMMDD` so that each window stays under 10,000 records. The GB window for January 2024 holds 978 records (Observed) [GL26].
   - About 233,800 records means about 1,170 requests: roughly 20 minutes at 60 requests per minute.
2. **Only Companies House-registered entities**
   - `filter[entity.registeredAt]=RA000585,RA000586,RA000587`: about 119,300 records, or 62,736 adding `filter[entity.status]=ACTIVE&filter[registration.status]=ISSUED` (Observed) [GL20].
3. **Golden copy, streamed** (simplest for a one-command demo)
   - Stream the 481 MB LEI CSV zip, keeping GB rows or CH authority codes, then apply `LastDay` deltas (about 3 MB) [GL1].
   - Level 2 is small: RR is 23 MB and reporting exceptions 59 MB as CSV zips. Load them whole and filter by the kept LEIs [GL1].
4. **Single lookups** during entity resolution: use `filter[entity.registeredAs]` or `/fuzzycompletions` [GL16][GL19].

---

## Part C. Optional sources

**OpenCorporates.**
- Access: "An API key is required in order to use the OpenCorporates API". The token goes in `?api_token=` [OC2].
- Default allowance: "up to 200 requests per month, and 50 requests per day". Rate limiting is signalled with HTTP 403, not 429 [OC2]. Current API version: 0.4 [OC2].
- "The API throttles usage based on the IP address of the request". Remaining calls can be read from the `account_status` call [OC3].
- Data is "Available as either share-alike attribution open data or commercially" [OC1].
- Free access exists in two forms:
  - "API accounts are free if you are going to be using the data in an open data project or product", subject to share-alike attribution [OC2]. The licence page says share-alike keys require evidence that the project gives back to the open data community [OC4].
  - The pricing page offers "free at-scale access" to investigative journalists, NGOs, universities and anti-corruption researchers, by application through a service desk form [OC5].
- Paid self-serve plans run from £2,250 a year (Essentials: 500 calls a month, 200 a day) to £12,000 a year (Basic: 5,000 a month). Enterprise and bulk prices are not listed [OC5].
- Licence: the database is under the Open Database License (no version is stated; ODbL v1.0 is the only published version) [OC4].
  - Attribution must be a hyperlink reading "from OpenCorporates", "no smaller than 70% of the largest font relating to the information or 7px" [OC4].
  - Share-alike: combining OpenCorporates data with your own means "the resultant information must be published under the Attribution Share-Alike ODbL" [OC4].
  - Paid non-share-alike licences remove these obligations [OC2][OC4].
- For NeonRadar: keep OpenCorporates optional, behind a key each user supplies, and never ship its data. The `ocid` field in GLEIF records already gives a join key [GL11].

**Open Ownership and BODS.**
- Standard: the current Beneficial Ownership Data Standard is version 0.4, released on 2024-05-08. The changelog says only that "Future changes are anticipated before a version 1.0 release", with no newer version listed [OO1][OO2]. The BODS schema is licensed under Apache 2.0 [OO3], which is compatible with NeonRadar.
- Register closure: the Open Ownership Register was retired. The closure was announced on 30 October 2024, and register.openownership.org closed on 29 November 2024 [OO4][OO5]. The old URL still serves a page [OO9].
- Bulk data: republished datasets remain downloadable at `bods-data.openownership.org`. On 2026-10-16 the home page listed two BODS 0.4 datasets, both dated 2025-03-11, under CC0 1.0, with the warning "These mappings are currently a work in progress and should be treated with caution" [OO6]:
  - "UK PSC & ROE";
  - "GLEIF".
- The UK conversion was announced on 6 March 2025. It covers the PSC register and more than 30,000 overseas entities, built from the PSC snapshot and the Companies House API, and it "will be refreshed on a regular basis" [OO8].
- No refresh after March 2025 was visible, and the UK source page returned "Not Found" on 2026-10-16 [OO7]. The dataset is stale. It suits schema reference and test design, not a live source.

---

## Licence summary

| Source | Licence | Commercial use | Attribution text | Redistribution allowed | Notes |
|---|---|---|---|---|---|
| Companies House register data (REST API, streams, Free Company Data, PSC snapshot) | Register made available under the Companies Act 2006 and CDPA s.47 approvals, with no Companies House rules on use; Companies House material is under OGL v3.0 [CHF18][CH37] | Yes [CHF18][CH37] | "Contains public sector information licensed under the Open Government Licence v3.0." plus a Companies House credit [CH40][CH38] | Yes as far as Companies House is concerned. OGL does not license personal data; UK GDPR controller duties apply [CH40][CH36] | Month and year of birth only; no residential addresses; trust data excluded [CH36][CH33] |
| Companies House officers bulk (Products 195/216, 198) | Not published | UNVERIFIED | UNVERIFIED | UNVERIFIED | By request to bulkproducts@companieshouse.gov.uk; no identity verification fields [CHF15][CHF7] |
| GLEIF LEI data, Level 1 and Level 2 (API, golden copy, concatenated) | CC0 1.0 [GL31] | Yes | None required | Yes | No GLEIF logo use or implied endorsement; CHF 100,000 liquidated damages for breaching the terms [GL31] |
| GLEIF BIC-to-LEI file | BIC/LEI Mapping Table License Agreement v1.0 (SWIFT, GLEIF) [GL35] | Yes | Required notice: "SWIFT © and database rights" with the version date, plus www.swift.com/bic | Yes (transferable, sub-licensable), with the notice | No trademark rights [GL35] |
| GLEIF ISIN-to-LEI file | Not named; described as "open source" [GL38] | UNVERIFIED | UNVERIFIED | UNVERIFIED | Daily full file, no deltas [GL37] |
| GLEIF OpenCorporates-to-LEI file | Not stated [GL39] | UNVERIFIED | UNVERIFIED | UNVERIFIED | Bi-weekly |
| OpenCorporates | ODbL with share-alike, or a paid non-share-alike licence [OC4] | Only on a paid licence, or under ODbL share-alike terms [OC2][OC4] | Hyperlink "from OpenCorporates", at least 70% of the largest related font or 7px [OC4] | Yes under ODbL; derived databases must also be ODbL [OC4] | API key required; 50 calls a day by default [OC2] |
| Open Ownership BODS schema | Apache 2.0 [OO3] | Yes | Apache 2.0 notice | Yes | Version 0.4 [OO1] |
| Open Ownership BODS datasets (UK PSC and ROE, GLEIF) | CC0 1.0 [OO6] | Yes | None required | Yes | Dated 2025-03-11; "work in progress" [OO6] |

## Open items marked UNVERIFIED

- Companies House:
  - time to issue a key;
  - whether the rate limit is per key or per application;
  - the rate limit headers (community-reported only);
  - maximum page sizes for the PSC and appointments lists;
  - how 404 behaves for companies without PSC data;
  - a trailing totals line in the PSC snapshot;
  - whether the PSC snapshot includes overseas entity beneficial owners;
  - exact Free Company Data CSV headers;
  - officer bulk price and terms;
  - how far back a stream `timepoint` can reach.
- GLEIF:
  - rate limit headers and 429 behaviour;
  - the error status for the 10,000 record cap;
  - meaning of the 00:00, 08:00 and 16:00 `publish_date` stamps;
  - why the concatenated and golden copy RR counts differ;
  - exact LEI CSV column names;
  - licences of the ISIN-to-LEI and OpenCorporates-to-LEI files;
  - registration authority codes for overseas entities and overseas companies.

---

## Sources

All checked on 2026-10-16. Forum posts are on the official Companies House developer forum; the poster and post date are given where they matter.

### Companies House and GOV.UK (official)

- [CH1] Companies House API authentication. https://developer.company-information.service.gov.uk/authentication (checked 2026-10-16)
- [CH2] Developer guidelines (rate limits, key security, enumerations). https://developer.company-information.service.gov.uk/developer-guidelines (checked 2026-10-16)
- [CH3] How to create an application. https://developer.company-information.service.gov.uk/how-to-create-an-application (checked 2026-10-16)
- [CH4] Get started. https://developer.company-information.service.gov.uk/get-started (checked 2026-10-16)
- [CH5] API testing (sandbox). https://developer.company-information.service.gov.uk/api-testing (checked 2026-10-16)
- [CH6] Developer Hub home and footer links. https://developer.company-information.service.gov.uk/ (checked 2026-10-16)
- [CH7] Public Data API reference index. https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference (checked 2026-10-16)
- [CH8] Swagger root spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/swagger.json (checked 2026-10-16)
- [CH9] Company profile spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/companyProfile.json (checked 2026-10-16)
- [CH10] Company officer list spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/companyOfficerList.json (checked 2026-10-16)
- [CH11] officerSummary resource. https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/officersummary (checked 2026-10-16)
- [CH12] Officer appointment list spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/officerAppointmentList.json (checked 2026-10-16)
- [CH13] PSC operations spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/psc.json (checked 2026-10-16)
- [CH14] PSC models spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/pscModels.json (checked 2026-10-16)
- [CH15] Search spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/search.json (checked 2026-10-16)
- [CH16] Advanced, alphabetical and dissolved search spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/search-companies.json (checked 2026-10-16)
- [CH17] Streaming API overview. https://developer-specs.company-information.service.gov.uk/streaming-api/guides/overview (checked 2026-10-16)
- [CH18] Officers stream reference. https://developer-specs.company-information.service.gov.uk/streaming-api/reference/officers/stream (checked 2026-10-16)
- [CH19] Streaming swagger spec. https://developer-specs.company-information.service.gov.uk/api.ch.gov.uk-specifications/swagger-2.0/spec/streaming.json (checked 2026-10-16)
- [CH20] Officers stream resource. https://developer-specs.company-information.service.gov.uk/streaming-api/resources/officersstream (checked 2026-10-16)
- [CH21] companieshouse/api-enumerations (psc_descriptions.yml, constants.yml, psc_verification.yml; last commit 2026-09-11). https://github.com/companieshouse/api-enumerations, raw files at https://raw.githubusercontent.com/companieshouse/api-enumerations/master/psc_descriptions.yml and https://raw.githubusercontent.com/companieshouse/api-enumerations/master/constants.yml (checked 2026-10-16)
- [CH22] Free Company Data Product. https://download.companieshouse.gov.uk/en_output.html (checked 2026-10-16)
- [CH23] Free Company Data Product field list (PDF). https://resources.companieshouse.gov.uk/toolsToHelp/pdf/freeDataProductDataset.pdf (checked 2026-10-16)
- [CH24] PSC snapshot. https://download.companieshouse.gov.uk/en_pscdata.html (checked 2026-10-16)
- [CH25] Companies House data products (GOV.UK). https://www.gov.uk/guidance/companies-house-data-products (checked 2026-10-16)
- [CH26] data.gov.uk PSC dataset. https://www.data.gov.uk/dataset/people-with-significant-control-psc (checked 2026-10-16)
- [CH27] Press release: identity verification rollout from 18 November 2025 (published 5 August 2025). https://www.gov.uk/government/news/companies-house-confirms-identity-verification-rollout-from-18-november-2025 (checked 2026-10-16)
- [CH28] Verifying your identity for Companies House (last updated 1 June 2026). https://www.gov.uk/guidance/verifying-your-identity-for-companies-house (checked 2026-10-16)
- [CH29] ECCTA outline transition plan for Companies House (last updated 5 August 2026). https://www.gov.uk/government/publications/economic-crime-and-corporate-transparency-act-outline-transition-plan-for-companies-house (checked 2026-10-16)
- [CH30] Changes to UK company law campaign site. https://changestoukcompanylaw.campaign.gov.uk/ (checked 2026-10-16)
- [CH31] Removing your home address and other personal details from the register (last updated 23 February 2026). https://www.gov.uk/guidance/removing-your-home-address-from-the-companies-house-register (checked 2026-10-16)
- [CH32] Ask Companies House for information about a trust (last updated 9 July 2026). https://www.gov.uk/guidance/ask-companies-house-for-information-about-a-trust (checked 2026-10-16)
- [CH33] Register an overseas entity and its beneficial owners (last updated 1 February 2026). https://www.gov.uk/guidance/register-an-overseas-entity (checked 2026-10-16)
- [CH34] OE000002 entity page (Find and update company information). https://find-and-update.company-information.service.gov.uk/company/OE000002 (checked 2026-10-16)
- [CH35] Searching the Companies House register (last updated 9 June 2026). https://www.gov.uk/guidance/search-the-companies-house-register (checked 2026-10-16)
- [CH36] Companies House personal information charter. https://www.gov.uk/government/organisations/companies-house/about/personal-information-charter (checked 2026-10-16)
- [CH37] Public task, copyright and Crown copyright. https://www.gov.uk/government/publications/companies-house-accreditation-to-information-fair-traders-scheme/public-task-copyright-and-crown-copyright (checked 2026-10-16)
- [CH38] Companies House Crown copyright page. https://resources.companieshouse.gov.uk/legal/crown.shtml (checked 2026-10-16)
- [CH39] Open Government Licence v3.0 (The National Archives). https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ (checked 2026-10-16; server error from the fetch tool, text verified via CH40)
- [CH40] OGL-UK-3.0 licence text (SPDX). https://spdx.org/licenses/OGL-UK-3.0.html (checked 2026-10-16)
- [CH41] HSF Kramer, "UK government updates ECCTA implementation timeline" (19 June 2026; secondary source). https://www.hsfkramer.com/notes/corporate/2026-posts/uk-government-updates-eccta-implementation-timeline (checked 2026-10-16)
- [CH42] DBT, third report on Parts 1 to 3 of ECCTA (cited by CH41; not opened directly). https://assets.publishing.service.gov.uk/media/6a28300ee371d9d2c0052b3e/third-report-on-the-implementation-and-operation-of-parts-1-to-3-of-the-economic-crim-and-corporate-transparency-act-2023.pdf (checked 2026-10-16 via CH41)

### Companies House developer forum

- [CHF1] "Officers and Persons with significant control resource specification update", cbaldwin, 9 September 2025. https://forum.companieshouse.gov.uk/t/officers-and-persons-with-significant-control-resource-specification-update/12087 (checked 2026-10-16)
- [CHF2] Identity verification update (v2), cbaldwin, 20 October 2025. https://forum.companieshouse.gov.uk/t/officers-and-persons-with-significant-control-resource-specification-identify-verification-update-v2/12257 (checked 2026-10-16)
- [CHF3] Super-secure PSC resource specification update, cbaldwin, 7 November 2025. https://forum.companieshouse.gov.uk/t/super-secure-person-with-significant-control-resource-specification-update/12371 (checked 2026-10-16)
- [CHF4] More information on the new elements in the officers and PSC APIs, snicholas (role not shown), 26 to 30 September 2025. https://forum.companieshouse.gov.uk/t/more-information-on-the-new-elements-in-the-officers-and-psc-apis/12142 (checked 2026-10-16)
- [CHF5] Officer appointment verified but identity not verified, cbaldwin, 25 November 2025. https://forum.companieshouse.gov.uk/t/officer-appointment-verified-but-identify-is-not-verified/12446 (checked 2026-10-16)
- [CHF6] The "Unverified" gap (community), December 2025. https://forum.companieshouse.gov.uk/t/the-unverified-gap-handling-new-idv-statuses-vs01-schemas/12491 (checked 2026-10-16)
- [CHF7] Does the Prod195 dataset contain identity_verification_details, cbaldwin, 9 December 2025. https://forum.companieshouse.gov.uk/t/does-the-prod195-dataset-contains-identity-verification-details/12524 (checked 2026-10-16)
- [CHF8] Resource specifications updates, MArkWilliams, 28 March and 2 April 2024. https://forum.companieshouse.gov.uk/t/resource-specifications-updates/7669 (checked 2026-10-16)
- [CHF9] How to identify officers across Prod195 and the stream (community), January 2025. https://forum.companieshouse.gov.uk/t/how-to-definitively-identify-company-officers-across-snapshot-prod195-and-streaming-api-data/10740 (checked 2026-10-16)
- [CHF10] View your request count for rate limiting (community), February 2020. https://forum.companieshouse.gov.uk/t/view-your-request-count-for-rate-limiting/2880 (checked 2026-10-16)
- [CHF11] Companies House API limits, MArkWilliams, 24 and 28 October 2024. https://forum.companieshouse.gov.uk/t/companies-house-api-limits/8626 (checked 2026-10-16)
- [CHF12] Max number of officers capped at 100 (community), October 2019. https://forum.companieshouse.gov.uk/t/max-number-of-officers-capped-at-100/2682 (checked 2026-10-16)
- [CHF13] Using pagination on search companies (community), 7 November 2025. https://forum.companieshouse.gov.uk/t/using-pagination-on-search-companies/12373 (checked 2026-10-16)
- [CHF14] Search officers returns HTTP 416 when start_index is over 300, rmcneil, 22 December 2016, plus community posts from 2017. https://forum.companieshouse.gov.uk/t/search-company-officers-returns-http-416-when-start-index-over-300/897 (checked 2026-10-16)
- [CHF15] Bulk data access request (officers, charges), kadach, 4 March 2026. https://forum.companieshouse.gov.uk/t/bulk-data-access-request-officers-charges-snapshots-updates/12697 (checked 2026-10-16)
- [CHF16] Officer and Director data (community and staff), 2021 to 2023. https://forum.companieshouse.gov.uk/t/officer-and-director-data/4516 (checked 2026-10-16)
- [CHF17] Bulk Officer Request (no reply), 6 July 2026. https://forum.companieshouse.gov.uk/t/bulk-officer-request/12865 (checked 2026-10-16)
- [CHF18] Is data provided under the OGL, Robert McNeil (Service Owner), 4 November 2021. https://forum.companieshouse.gov.uk/t/is-data-provided-under-the-ocs/4513 (checked 2026-10-16)
- [CHF19] Company officer name in the officers API, mfairhurst (role not shown), 5 July 2018. https://forum.companieshouse.gov.uk/t/company-officer-name-in-company-officer-api/1900 (checked 2026-10-16)
- [CHF20] Format of officer and PSC names (community), May 2026. https://forum.companieshouse.gov.uk/t/format-of-officer-pwsc-names/12788 (checked 2026-10-16)
- [CHF21] Company number for corporate officer, Steve Bowen, 29 November 2019. https://forum.companieshouse.gov.uk/t/company-number-for-corporate-officer-bulk-data/2760 (checked 2026-10-16)
- [CHF22] PSC daily JSON snapshot syntax error (community), March 2018. https://forum.companieshouse.gov.uk/t/companies-house-psc-daily-json-snapshot-syntax-error/1719 (checked 2026-10-16)
- [CHF23] Request for 2,500 rate limit (XML gateway), kadach, 3 February 2026. https://forum.companieshouse.gov.uk/t/request-for-2-500-rate-limit/12646 (checked 2026-10-16)

### GLEIF (official pages and live API responses)

- [GL1] Golden Copy latest publish (all types). https://goldencopy.gleif.org/api/v2/golden-copies/publishes/latest (checked 2026-10-16)
- [GL2] Golden Copy latest LEI publish. https://goldencopy.gleif.org/api/v2/golden-copies/publishes/lei2/latest (checked 2026-10-16)
- [GL3] Golden Copy latest RR publish. https://goldencopy.gleif.org/api/v2/golden-copies/publishes/rr/latest (checked 2026-10-16)
- [GL4] Golden Copy publish history. https://goldencopy.gleif.org/api/v2/golden-copies/publishes (checked 2026-10-16)
- [GL5] GLEIF Golden Copy overview. https://www.gleif.org/en/lei-data/gleif-golden-copy (checked 2026-10-16)
- [GL6] Download the Golden Copy and Delta Files. https://www.gleif.org/en/lei-data/gleif-golden-copy/download-the-golden-copy (checked 2026-10-16)
- [GL7] GLEIF data consumers quick guide (PDF). https://www.gleif.org/about-lei/common-data-file-format/current-versions/supporting-documents/gleif-data-consumers-quick-guide.pdf (checked 2026-10-16)
- [GL8] Download the Concatenated Files. https://www.gleif.org/en/lei-data/gleif-concatenated-file/download-the-concatenated-file (checked 2026-10-16)
- [GL9] GLEIF API overview. https://www.gleif.org/en/lei-data/gleif-api (checked 2026-10-16)
- [GL10] GLEIF API documentation (Postman; https://api.gleif.org/docs redirects here). https://documenter.getpostman.com/view/7679680/SVYrrxuU?version=latest (checked 2026-10-16)
- [GL11] LEI record, HSBC Holdings plc. https://api.gleif.org/api/v1/lei-records/MLU0ZO3ML4LN2LL2TL39 (checked 2026-10-16)
- [GL12] Direct parent relationship, HSBC Bank plc. https://api.gleif.org/api/v1/lei-records/MP6I5ZYZBEU3UXPYFY54/direct-parent-relationship (checked 2026-10-16)
- [GL13] Ultimate parent, HSBC Bank plc. https://api.gleif.org/api/v1/lei-records/MP6I5ZYZBEU3UXPYFY54/ultimate-parent (checked 2026-10-16)
- [GL14] Direct parent reporting exception, HSBC Holdings plc. https://api.gleif.org/api/v1/lei-records/MLU0ZO3ML4LN2LL2TL39/direct-parent-reporting-exception (checked 2026-10-16)
- [GL15] Direct children, HSBC Holdings plc. https://api.gleif.org/api/v1/lei-records/MLU0ZO3ML4LN2LL2TL39/direct-children?page[size]=5 (checked 2026-10-16)
- [GL16] Fuzzy completions. https://api.gleif.org/api/v1/fuzzycompletions?field=entity.legalName&q=hsbc%20holdngs (checked 2026-10-16)
- [GL17] Autocompletions. https://api.gleif.org/api/v1/autocompletions?field=fulltext&q=hsbc%20hold (checked 2026-10-16)
- [GL18] Registration authorities. https://api.gleif.org/api/v1/registration-authorities/RA000585, also /RA000586, /RA000587, /RA000590 and /RA999999 (checked 2026-10-16)
- [GL19] Lookup by registeredAs. https://api.gleif.org/api/v1/lei-records?filter[entity.registeredAs]=00617987, also =SC045551 and =00014259 (checked 2026-10-16)
- [GL20] Filters on registeredAt. https://api.gleif.org/api/v1/lei-records?filter[entity.registeredAt]=RA000585, also RA000586, RA000587, the three combined with filter[entity.status]=ACTIVE and filter[registration.status]=ISSUED, the unpadded registeredAs test, and sort=entity.registeredAs (checked 2026-10-16)
- [GL21] Filters on jurisdiction. https://api.gleif.org/api/v1/lei-records?filter[entity.jurisdiction]=GB, also with ACTIVE and ISSUED, and =GB-ENG,GB-SCT,GB-WLS,GB-NIR (checked 2026-10-16)
- [GL22] Paging limits. https://api.gleif.org/api/v1/lei-records?filter[entity.legalAddress.country]=GB&page[size]=200&page[number]=50, also page 51, page 60, page[size]=201 and page[size]=500 (checked 2026-10-16)
- [GL23] Field catalogue. https://api.gleif.org/api/v1/fields (checked 2026-10-16)
- [GL24] LEI record with transliterated and previous names. https://api.gleif.org/api/v1/lei-records/213800UUZLD8OSOT5198 (checked 2026-10-16)
- [GL25] Saudi records with Arabic names. https://api.gleif.org/api/v1/lei-records?filter[entity.legalAddress.country]=SA&page[size]=3 (checked 2026-10-16)
- [GL26] Date window filters. https://api.gleif.org/api/v1/lei-records?filter[entity.jurisdiction]=GB&filter[registration.initialRegistrationDate]=20240101..20240131, also filter[entity.creationDate]=20200101..20200131 (checked 2026-10-16)
- [GL27] RR-CDF format page. https://www.gleif.org/en/about-lei/common-data-file-format/relationship-record-cdf-format (checked 2026-10-16)
- [GL28] RR-CDF 2.1 XSD. https://www.gleif.org/lei-data/access-and-use-lei-data/level-2-data-relationship-record-rr-cdf-2-1-format/2021-03-04_rr-cdf-v2-1.xsd (checked 2026-10-16)
- [GL29] Reporting Exceptions 2.1 format page. https://www.gleif.org/en/lei-data/access-and-use-lei-data/level-2-data-reporting-exceptions-2-1-format (checked 2026-10-16)
- [GL30] Reporting Exceptions 2.1 XSD. https://www.gleif.org/lei-data/access-and-use-lei-data/level-2-data-reporting-exceptions-2-1-format/2021-07-20_reporting-exceptions-format-v2-1.xsd (checked 2026-10-16)
- [GL31] LEI Data Terms of Use. https://www.gleif.org/en/meta/lei-data-terms-of-use/ (checked 2026-10-16)
- [GL32] AI Terms of Use. https://www.gleif.org/en/meta/ai-terms-of-use (checked 2026-10-16)
- [GL33] LEI mapping overview. https://www.gleif.org/en/lei-data/lei-mapping (checked 2026-10-16)
- [GL34] BIC-to-LEI relationship files. https://www.gleif.org/en/lei-data/lei-mapping/download-bic-to-lei-relationship-files (checked 2026-10-16)
- [GL35] BIC/LEI Mapping Table License Agreement v1.0 (PDF). https://www.gleif.org/lei-data/lei-mapping/download-bic-to-lei-relationship-files/2017-12-21_annex-2_bic-to-lei-mapping-table-license-agreement_final.pdf (checked 2026-10-16)
- [GL36] ISIN-to-LEI relationship files. https://www.gleif.org/en/lei-data/lei-mapping/download-isin-to-lei-relationship-files (checked 2026-10-16)
- [GL37] ISIN-to-LEI factsheet v1 (PDF). https://www.gleif.org/lei-data/lei-mapping/download-isin-to-lei-relationship-files/2021-06-08_isin-to-lei_factsheet_v1.pdf (checked 2026-10-16)
- [GL38] GLEIF blog on the ANNA and GLEIF mapping initiative (4 April 2019). https://gleif.org/en/newsroom/blog/a-progress-report-on-the-anna-and-gleif-mapping-initiative-first-pilot-isin-to-lei-relationship-file-published (checked 2026-10-16)
- [GL39] OpenCorporates ID-to-LEI relationship files. https://www.gleif.org/en/lei-data/lei-mapping/download-oc-to-lei-relationship-files (checked 2026-10-16)
- [GL40] GLEIF home page (maintenance notice). https://www.gleif.org/en (checked 2026-10-16)

### OpenCorporates

- [OC1] API landing page. https://api.opencorporates.com/ (checked 2026-10-16)
- [OC2] API reference. https://api.opencorporates.com/documentation/API-Reference (checked 2026-10-16)
- [OC3] API FAQs. https://api.opencorporates.com/documentation/FAQs (checked 2026-10-16)
- [OC4] Legal and licence information. https://opencorporates.com/info/licence (checked 2026-10-16)
- [OC5] Pricing. https://opencorporates.com/pricing/ (checked 2026-10-16)

### Open Ownership

- [OO1] BODS documentation (v0.4). https://standard.openownership.org/en/latest/ (checked 2026-10-16)
- [OO2] BODS changelog. https://standard.openownership.org/en/main/standard/changelog.html (checked 2026-10-16)
- [OO3] BODS about page (schema licence). https://standard.openownership.org/en/0.4.0/about (checked 2026-10-16)
- [OO4] "Evolving from the Open Ownership Register to increase our impact" (30 October 2024). https://www.openownership.org/en/news/evolving-from-the-open-ownership-register-to-increase-our-impact/ (checked 2026-10-16)
- [OO5] Open Ownership Register topic page. https://www.openownership.org/en/topics/open-ownership-register/ (checked 2026-10-16)
- [OO6] BODS data home page. https://bods-data.openownership.org/ (checked 2026-10-16)
- [OO7] UK BODS 0.4 source page. https://bods-data.openownership.org/source/uk_version_0_4/ (checked 2026-10-16; returned "Not Found")
- [OO8] "United Kingdom beneficial ownership data available in line with latest version of global standard" (6 March 2025). https://www.openownership.org/en/news/united-kingdom-beneficial-ownership-data-available-in-line-with-latest-version-of-global-standard/ (checked 2026-10-16)
- [OO9] Former register site. https://register.openownership.org/ (checked 2026-10-16)

### Third-party code (community evidence)

- [T1] OpenSanctions Companies House PSC parser, `datasets/gb/coh/psc_parse.py` (last commit d8d0c9c, 2026-10-15). https://github.com/opensanctions/opensanctions/blob/main/datasets/gb/coh/psc_parse.py (checked 2026-10-16)
- [T2] OpenSanctions GLEIF crawler, `datasets/_global/gleif/crawler.py`. https://github.com/opensanctions/opensanctions/blob/main/datasets/_global/gleif/crawler.py (checked 2026-10-16)
- [T3] CorrelAid gleif-level2-server, RR CSV test fixture `src/test_data/rr-test.csv`. https://github.com/CorrelAid/gleif-level2-server (checked 2026-10-16)
