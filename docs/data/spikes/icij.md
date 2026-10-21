# Spike report: ICIJ Offshore Leaks Database (`icij_offshore_leaks`)

Milestone M1.8c ([PHASE-1.md](../../build/PHASE-1.md), section 6). This was a technical fetch test. The report holds counts, field names, header facts and link vocabulary only: no names, addresses or other record content from the database. The spike output (C1 records and manifest) stayed in `data/cache/spikes/icij/`, which is gitignored, and must be deleted with `neonradar spike clean` after `access.spike_cache_days` (7 days).

## 1. Command, date, duration, network

- Command: `uv run neonradar spike icij --rows 1000` (the network test `ingest/tests/test_icij_network.py` runs the same code). Validation: `uv run neonradar contracts validate-records data/cache/spikes/icij/*.ftm.jsonl --strict`.
- Date: 21 October 2026.
- Duration: 52.3 s from the HEAD request to the written manifest (54.8 s for the whole command, 19.8 s of it CPU). The archive was read over HTTP range requests: one HEAD and 14 range requests, 45,695,851 bytes received, which is about 64 percent of the archive. No archive copy was written to disk. The network test ran the same spike again in 72 s. After the review fixes (range checks with `If-Range`, `Content-Range` and `ETag`; the jurisdiction rule in section 4) the command ran again: same 14 range requests, same bytes and the same record counts, 57.9 s, strict validation 0 issues.
- Network: the build machine's internet connection to Amazon CloudFront (edge `FRA50-P1`). A single range request ran at about 1.8 MB/s. There were no errors, no retries and no rate limiting.
- Source: `https://offshoreleaks-data.icij.org/offshoreleaks/csv/full-oldb.LATEST.zip`, downloaded straight from ICIJ, not from the OpenSanctions copy (CC BY-NC).

## 2. What was fetched

**Archive headers** (HEAD, no redirect: the URL answered 200 directly):

| Header | Value |
|---|---|
| `Content-Length` | 71,935,075 bytes (68.6 MiB) |
| `Last-Modified` | Wed, 09 Sep 2026 10:55:34 GMT |
| `ETag` | `"a72fc063daa4a051827e2fbeaf6d8f15-9"` (an S3 multipart ETag, not an MD5 of the file) |
| `Accept-Ranges` | `bytes` (range requests answered 206) |
| `Content-Type` | `application/zip` |
| `Server` | `AmazonS3`, served through CloudFront |

**Members**, from the zip's central directory (sizes uncompressed; all deflate):

| Member | Size | Compressed |
|---|---|---|
| `GENERATED_ON_20260909.txt` | 0 (a marker; its name gives the export date) | 0 |
| `nodes-entities.csv` | 198,928,989 | 26,758,090 |
| `nodes-officers.csv` | 91,022,305 | 10,698,203 |
| `nodes-addresses.csv` | 72,467,125 | 11,657,727 |
| `nodes-intermediaries.csv` | 4,064,192 | 801,306 |
| `nodes-others.csv` | 398,436 | 48,100 |
| `relationships.csv` | 259,198,321 | 21,970,457 |

**Headers found** (exact order):

| File | Columns |
|---|---|
| `nodes-entities.csv` | `node_id, name, original_name, former_name, jurisdiction, jurisdiction_description, company_type, address, internal_id, incorporation_date, inactivation_date, struck_off_date, dorm_date, status, service_provider, ibcRUC, country_codes, countries, sourceID, valid_until, note` |
| `nodes-officers.csv` | `node_id, name, countries, country_codes, sourceID, valid_until, note` |
| `nodes-intermediaries.csv` | `node_id, name, status, internal_id, address, countries, country_codes, sourceID, valid_until, note` |
| `nodes-others.csv` | `node_id, name, type, incorporation_date, struck_off_date, closed_date, jurisdiction, jurisdiction_description, countries, country_codes, sourceID, valid_until, note` |
| `nodes-addresses.csv` | `node_id, address, name, countries, country_codes, sourceID, valid_until, note` |
| `relationships.csv` | `node_id_start, node_id_end, rel_type, link, status, start_date, end_date, sourceID` |

**Rows read.** `relationships.csv` and the four smaller node files were streamed in full and counted. Rows outside the slice were dropped as they were read, never stored. `nodes-entities.csv` stopped after the first 1,000 rows.

| File | Rows read | Of |
|---|---|---|
| `relationships.csv` | 3,339,267 | all |
| `nodes-officers.csv` | 771,315 | all |
| `nodes-addresses.csv` | 402,246 | all |
| `nodes-intermediaries.csv` | 26,768 | all |
| `nodes-others.csv` | 2,989 | all |
| `nodes-entities.csv` | 1,000 | first rows only (the total was not measured) |

**`rel_type` values** (the complete list, over every row): `officer_of` 1,720,357; `registered_address` 832,721; `intermediary_of` 598,546; `same_name_as` 104,170; `similar` 46,761; `same_company_as` 15,523; `connected_to` 12,145; `same_as` 4,272; `same_id_as` 3,120; `underlying` 1,308; `similar_company_as` 203; `probably_same_officer_as` 132; `same_address_as` 5; `same_intermediary_as` 4. There are 976 distinct `(rel_type, lower(link))` pairs.

**`sourceID` values.** There are 22 distinct labels in the form `<leak>` or `<leak> - <registry or service provider>`: Offshore Leaks, Panama Papers and Bahamas Leaks; Paradise Papers with Appleby and eight corporate registries; Pandora Papers with ten service providers. Rows per leak:

| Leak | relationships | officers | intermediaries | others | addresses |
|---|---|---|---|---|---|
| Paradise Papers (all labels) | 1,335,600 | 350,009 | 1,568 | 2,919 | 223,353 |
| Panama Papers | 674,102 | 238,402 | 14,110 | 0 | 93,454 |
| Offshore Leaks | 561,393 | 107,190 | 9,526 | 0 | 57,600 |
| Bahamas Leaks | 249,190 | 25,262 | 541 | 0 | 551 |
| Pandora Papers (all labels) | 0 | 50,452 | 1,023 | 70 | 27,288 |
| empty | 518,982 | 0 | 0 | 0 | 0 |

The first 1,000 entity rows are all Panama Papers.

**Top 30 `(rel_type, link)` pairs**, with the classification the spike applied:

| Rows | rel_type | link (lower case) | Mapped to |
|---|---|---|---|
| 589,938 | officer_of | shareholder of | Ownership |
| 566,910 | registered_address | registered address | addressEntity, role `registered` |
| 516,650 | intermediary_of | intermediary of | Representation (`intermediary`) |
| 457,922 | officer_of | director of | Directorship |
| 164,287 | registered_address | registered office | addressEntity, role `registered` |
| 115,652 | officer_of | secretary of | Directorship |
| 109,526 | officer_of | judicial representative of | Directorship |
| 104,170 | same_name_as | same name as | not loaded (resolution hint) |
| 99,181 | officer_of | legal representative of | Directorship |
| 78,737 | intermediary_of | registered agent of | Representation (`intermediary`) |
| 46,761 | similar | similar name and address as | not loaded (resolution hint) |
| 36,318 | officer_of | records & registers of | UnknownLink |
| 27,242 | officer_of | auditor of | UnknownLink |
| 25,883 | officer_of | ultimate beneficial owner | Ownership |
| 25,317 | registered_address | residential address | addressEntity, role `residential` |
| 23,830 | officer_of | managing director of | Directorship |
| 23,637 | officer_of | beneficiary of | Ownership |
| 20,514 | officer_of | director | Directorship |
| 20,405 | officer_of | owner of | Ownership |
| 19,678 | officer_of | vice-president of | Directorship |
| 17,365 | officer_of | liquidator of | Directorship |
| 16,853 | registered_address | mailing address; residential address | addressEntity, role `residential` |
| 16,158 | officer_of | is signatory for | Directorship |
| 16,135 | registered_address | mailing address | addressEntity, role `unknown` |
| 15,523 | same_company_as | same company as | not loaded (resolution hint) |
| 13,498 | officer_of | president of | Directorship |
| 13,444 | registered_address | residential address; mailing address | addressEntity, role `residential` |
| 12,145 | connected_to | connected to | UnknownLink |
| 9,231 | officer_of | beneficial owner | Ownership |
| 6,379 | officer_of | auditor | UnknownLink |

Applied to every row of `relationships.csv`, the classification gives Directorship 947,936; addressEntity 832,721; Ownership 678,773; Representation 598,546; resolution hints (not loaded) 174,190; UnknownLink 107,101.

**The C1 slice.** The slice holds the first 1,000 entities, every relationship that touches one of them, and the nodes those relationships name. That is 6,002 records:

| FtM schema | Records |
|---|---|
| Company | 1,000 |
| LegalEntity (officers and intermediaries) | 1,780 |
| Address | 23 |
| Ownership | 2,196 |
| Representation | 1,000 |
| Directorship | 3 |

The slice left out 12 resolution-hint rows. It found every endpoint (none outside the slice) and no node without a usable name. Dates: 4,925 of 4,926 values parsed; the one miss has the shape `99-AAA-9999` (a year before 1000). `validate-records --strict`: "OK, 0 issues".

Property coverage in the slice (records with the property / records of the schema): Company `name`, `icijId`, `jurisdiction`, `status`, `incorporationDate`, `publisher`, `notes` 1,000/1,000; `country` 999; `address` 999; `registrationNumber` 951; `dissolutionDate` 665; `alias` 31; `previousName` 29; `addressEntity` 29. LegalEntity `name`, `icijId`, `publisher`, `notes` 1,780/1,780; `country` 1,189; `status` 242; `address` 166. Ownership `role` 2,196/2,196; `startDate` 2,188; `endDate` 507. Every `addressEntity` in the slice has the role `registered`; all three Directorships have `nr.is_nominee` false.

## 3. Measured facts that confirm or correct the research note

Against `docs/research/2026-10-16/sources-opensanctions-ftm-icij.md`, part C:

- **Size, date, ETag and range support (C.1, marked UNVERIFIED):** now measured (section 2). Range requests work, so the spike never downloads the whole archive. The archive was generated on 9 September 2026, after the research note's indirect hint of an August change.
- **URL (0, item 5):** confirmed. `full-oldb.LATEST.zip` answers directly with 200; no redirect today. Clients should still set `follow_redirects=True`.
- **Members (C.1):** confirmed: the six CSV files the note lists, plus the zero-byte `GENERATED_ON_<yyyymmdd>.txt` marker.
- **Columns (C.1, header order and `internal_id` marked UNVERIFIED):** now known (section 2). `internal_id` sits in `nodes-entities.csv` and `nodes-intermediaries.csv`. Corrections to the per-file table: entities have no `type` and no `closed_date` (those are in `nodes-others.csv`); `nodes-others.csv` also has `type`, `incorporation_date`, `struck_off_date` and `closed_date`; intermediaries also have `internal_id` and `note`; officers list `countries` before `country_codes`.
- **`rel_type` list (C.1, marked UNVERIFIED):** the complete list is in section 2. The GraphQL names `SAME_NAME_AS` and `SAME_ID_AS` appear in lower case. `underlying` exists (1,308 rows). `related_entity` does not occur in this export.
- **Counts (C.1, third-party figures):** confirmed: `officer_of` 1,720,357, `registered_address` 832,721, `intermediary_of` 598,546, about 3.3 million relationships in total (3,339,267), 771,315 officers, 402,246 addresses. Intermediaries: 26,768 rows, not 25,629. The difference, 1,139, is exactly the number of node ids that appear in both the officers file and the intermediaries file. Link subtypes "ultimate beneficial owner" 25,883, "beneficiary of" 23,637 and "owner of" 20,405 are confirmed. Resolution-type rows total 174,190 (the note says about 166,000).
- **Encoding (C.5, marked UNVERIFIED):** UTF-8 with `"` quoting. Strict UTF-8 decoding raised no error in any file read in full.
- **Question-mark names (C.5):** 46 officers and 5 intermediaries have names made only of `?`; none in the slice.
- **Same `node_id` in more than one file (C.5):** 1,139 ids are shared by officers and intermediaries. No id is shared between officers, intermediaries, others and addresses otherwise. The entities file was not read in full, so it was not compared.
- **`sourceID` (C.5, marked UNVERIFIED):** 22 labels (section 2). 518,982 relationship rows have an empty `sourceID`, and no relationship row carries a Pandora Papers label, although Pandora Papers nodes exist. The empty rows are `officer_of` 196,030, `registered_address` 113,303, `intermediary_of` 80,153, `same_name_as` 78,393, `similar` 46,761, `same_as` 4,272 and `underlying` 70.
- **Dates (C.5):** relationship dates have the shapes `DD-MON-YYYY` (942,194 values), ISO `YYYY-MM-DD` (260,379), and about 13,000 slash or dot forms (`99/99/9999` 10,702, `9/9/9999` 867, `99/99/99` 533 and smaller ones), plus 10 values of `*`. FtM's `%d-%b-%Y` parser accepts a year below 1000 and then fails its own validation (`21-AUG-0200` becomes `0200-08-21`, which C1 R5 rejects). The mapping therefore checks every cleaned date before adding it.
- **Relationship `status`:** only two values, `resigned` (131,441) and `appointed` (43,505).
- **`valid_until`:** one sentence per leak, the same wording as the FAQ's "How current is the data?" answer.
- **Disclaimer wording:** re-fetched from the FAQ on 21 October 2026 (section 5). The FAQ says "individuals", as in C.3. The "persons" variant quoted in `aml-domain.md` section 4 is not on the FAQ page.

## 4. Mapping notes

Ids come from `neonradar_contracts.records.make_id`. Every node is `icij-node-<node_id>`, whichever file it came from, so a relationship row maps without a lookup. `nr.source_ref` keeps the `node_id`. Edges are `icij-<schema in lower case>-<first 20 hex of SHA-1 over the eight relationship columns>`; an exact duplicate row gets the same id and is skipped and counted.

| Source | FtM |
|---|---|
| `nodes-entities.csv` row | `Company` |
| `nodes-officers.csv`, `nodes-intermediaries.csv`, `nodes-others.csv` rows | `LegalEntity` (many officers are not people) |
| `nodes-addresses.csv` row | `Address` |
| `node_id` | `icijId` (LegalEntity) and `nr.source_ref` |
| `name` (empty when it is only `?`) | `name`; a LegalEntity without a usable name is skipped and counted |
| `original_name` | `alias`, unless it repeats `name` |
| `former_name` | `previousName` |
| `jurisdiction_description`; the `jurisdiction` code only when the description is empty or does not clean to a country | `jurisdiction`. ICIJ's codes are not ISO codes: FtM cleans "ANG" to Angola, but ICIJ uses it for Anguilla. "XXX" and "Undetermined" are dropped. |
| `company_type` (entities), `type` (others) | `legalForm` |
| `address` (entities, intermediaries) | `address` (text) |
| `address`, then `name` (addresses) | `full` |
| `status` | `status` |
| `ibcRUC` | `registrationNumber` |
| `incorporation_date` | `incorporationDate` |
| `inactivation_date`, `struck_off_date`, `closed_date` | `dissolutionDate` |
| `country_codes`, `countries` (`;`-separated) | `country` |
| `note`, `valid_until` | `notes` |
| `sourceID` | `publisher` |
| `officer_of` | `Ownership` (owner the officer, asset the entity), `Directorship` or `UnknownLink`, chosen by the first term of the lookup table found in the lower-case link; `role` is the raw link |
| lookup table, Ownership | shareholder, beneficiary, owner |
| lookup table, Directorship | director, secretary, nominee, signatory, president, treasurer, chairman, board member, officer, protector, attorney, manager, representative, liquidator; `nr.is_nominee` is true when the link contains "nominee" |
| `intermediary_of` | `Representation` (agent the intermediary, client the entity), `role` `intermediary` |
| `registered_address` | `addressEntity` on the start node, with `nr.address_roles` from the link: the first of `registered`, `residential`, `business` and `service`, checked in that order, that the link contains, else `unknown`. So "mailing address; residential address" gives `residential`. |
| other `rel_type` values (`connected_to`, `underlying`) | `UnknownLink`, `role` the raw link |
| `same_*`, `similar*` and `probably_same_*` rows | not loaded; counted as resolution hints |
| relationship `status`, `start_date`, `end_date`, `sourceID` | `status`, `startDate`, `endDate`, `publisher` |

Range checks: when the endpoints do not fit a schema's FtM ranges (for example a `Directorship` whose target is not an Organization, or any link with an Address end other than `registered_address`), the row becomes an `UnknownLink`.

Not mapped: `internal_id`, `dorm_date` (FtM has no matching property), `service_provider`. Ownership has no share percentage in ICIJ data.

## 5. Licence and personal-data notes for the data steward

- Licence, re-fetched from the FAQ on 21 October 2026, verbatim: "Remember that the ICIJ Offshore Leaks Database is licensed under the Open Database License and contents under Creative Commons Attribution-ShareAlike license. Always cite the International Consortium of Investigative Journalists when using this data." The manifest carries `licence.id` `ODbL-1.0` with the attribution from `contracts/datasets.yaml`, plus a note naming CC BY-SA 3.0 for the contents.
- ICIJ's disclaimer, FAQ, "Should I assume that everyone named in the database has committed a crime?", verbatim (21 October 2026):

  > "No, there are legitimate uses for offshore companies and trusts. We do not intend to suggest or imply that any individuals, companies or other entities included in the ICIJ Offshore Leaks Database have broken the law or otherwise acted improperly."

  FAQ, "What should I keep in mind before using the data or publishing any findings?", verbatim (21 October 2026):

  > "The information contained in the ICIJ Offshore Leaks Database is just a fraction of the leaked files of the Pandora Papers, Paradise Papers, Bahamas Leaks, Panama Papers and Offshore Leaks investigations. We recommend caution before drawing any conclusions, as many people and entities have the same or similar names. We suggest you confirm the identities of any individuals or entities found in the database using addresses or other identifiable information. In the case of the corporate registries leaked to ICIJ as part of the Paradise Papers investigation, entities appearing in the database aren’t necessarily offshore companies, but can also be local businesses. The inclusion of a person or entity in the ICIJ Offshore Leaks Database is not intended to suggest or imply that they have engaged in illegal or improper conduct. The data comes directly from the leaked files ICIJ has received throughout different investigations and each set goes through a specific year. Keep in mind that some information, like the status of a company and its shareholders, might have changed over time."

- Personal data: the slice holds names of natural persons among the 1,780 LegalEntity records (officers are not separated from companies), plus addresses. It exists only in `data/cache/spikes/icij/` (gitignored) and must be deleted after 7 days (`access.spike_cache_days`) with `neonradar spike clean`. In range mode nothing else is written. If a server ever refuses ranges, the fallback downloads the archive to `--cache-dir`. Its default is `data/cache/spikes/icij/download/`, not the spec's `~/.cache/neonradar/icij`, so that `spike clean` also removes the archive, which holds the same personal data. Please decide where the Phase 2 loader should keep its archive copy.
- Nothing from the database is committed. The test fixtures are synthetic CSV rows shaped like the real files. Their node ids are ten digits starting with 99, a form that none of the 1.2 million node ids in the four node files read in full has. Their names were checked against the Companies House search on 21 October 2026 (listed in the pull request).
- A graph built from this data is a Derivative Database under ODbL. Internal use is not public use. Never publish it merged with OpenSanctions data (`contracts/datasets.yaml` notes).

## 6. Gotchas and recommendations for the Phase 2 loader

1. Read the whole archive once per release. It is 72 MB compressed, and 46 MB of it streamed in about 52 s here. Either stream it over ranges as the spike does, or download it once and revalidate with `If-None-Match` and `If-Modified-Since`. Key the release on `GENERATED_ON_<date>` (written to the manifest as `source_version`) rather than the ETag. The spike's range reader sends `If-Range` with the ETag and checks every answer's `Content-Range` and `ETag`, so a file replaced during a read fails with "the archive changed during the read; run again" instead of mixing two versions. It resumes a body that breaks off, at most 5 times per read.
2. Load nodes before relationships. Merge the 1,139 officer and intermediary rows that share a `node_id` into one record instead of keeping the first, as the spike does (it counts them as `node ids in more than one file`).
3. A slice must be closed to pass strict validation. The first 1,000 rows of `relationships.csv` touch none of the first 1,000 rows of the node files (they are 677 `registered_address`, 319 `same_as` and 4 `same_address_as` rows), so the spec's "first rows of each file" gives no edges. The spike instead takes a neighbourhood of the first entities. A full load has no such problem.
4. Review the long tail of the 976 `(rel_type, link)` pairs with the typology researchers: multi-role strings ("mailing address; residential address", role lists joined with `;`), roles such as "records & registers of" and "auditor of", and whether `judicial representative of` (Paradise Papers, Malta registry) belongs in Directorship.
5. Address roles: the spec said every `registered_address` link has the role `registered`, but the links name residential and mailing addresses too (71,749 rows among the top 30 pairs alone). The spike maps the word in the link and leaves `mailing address` as `unknown`. C1 has a `service` role, so Phase 2 should decide whether mailing means service.
6. Dates: about 13,000 relationship dates use `/` or `.` with an ambiguous day and month order and two-digit years. Use OpenSanctions' order and fix-up table (C.5) or drop them, and validate every cleaned date (FtM accepts years below 1000 through `format=` and then rejects them).
7. `sourceID` is empty on 518,982 relationship rows, and no relationship row carries a Pandora Papers label. Take the leak from the endpoint nodes when the row has none.
8. `valid_until` repeats one sentence per leak on every record. Consider putting it in the manifest notes per leak instead of in `notes`.
9. Officers stay `LegalEntity` in Phase 1. Upgrading them to `Person` or `Company` (OpenSanctions upgrades schemata from relationship ranges) is a Phase 2 entity-resolution decision.
10. The 174,190 resolution-hint rows (`same_name_as`, `similar`, `same_company_as`, `same_as`, `same_id_as` and others) are candidate evidence for Phase 2 entity resolution, never merges by themselves.
11. Cost is low: the full scans of 4.5 million rows took about 20 s of CPU, and memory stays small because rows outside the slice are dropped as they stream.

## 7. Verdict

**Go with changes.** The source works end to end: a direct, licence-compatible download from ICIJ, byte-range access, stable UTF-8 CSV headers, and a mapped slice that validates in strict mode. The changes for Phase 2 are in section 6: merge nodes that share an id, classify links with a reviewed table, take address roles from the link, harden date parsing, and fill a missing `sourceID` from the endpoint nodes. `contracts/datasets.yaml` keeps `status: spike` until the Phase 2 loader exists, so this verdict changes neither it nor `DATA_SOURCES.md`.
