# EU Financial Sanctions Files (`eu_fsf`)

The loader in `ingest/src/neonradar_ingest/sources/lists/eu_fsf.py` (PHASE-2.md M2.6d) turns the European Commission's consolidated list of persons, groups and entities subject to EU financial sanctions into C1 records. This page says what the list is, how the loader fetches and maps it, and what it leaves out. Licence and attribution come from [contracts/datasets.yaml](../../../contracts/datasets.yaml) and [DATA_SOURCES.md](../../../DATA_SOURCES.md). The facts about the list come from the research note [sanctions-peps.md](../../research/2026-10-18/sanctions-peps.md), section 4 (checked on 18 October 2026).

## What the list is

- **Publisher:** European Commission, Financial Sanctions Files (FSF), announced in the RSS feed <https://webgate.ec.europa.eu/fsd/fsf/public/rss> (note 4.1).
- **File:** the XML 1.1 file, the format that keeps alias strength (the CSV does not, note 4.4), at `https://webgate.ec.europa.eu/fsd/fsf/public/files/xmlFullSanctionsList_1_1/content?token=<token>`.
- **Updates:** several times a week. A download's version is the UTC date of the fetch. The file's own `generationDate` and `globalFileId` go into the manifest notes and the build summary as `list_generated` and `global_file_id`.
- **Scope:** financial sanctions (asset freezes) only. The EU Sanctions Map covers a broader set of measures and is not the data source (note 4.7).
- **Schema:** no XSD is published outside EU Login, so no schema is committed and the fixture is not validated against one.
- **Reuse:** the Commission's reuse decision, Decision 2011/833/EU, allows reuse for commercial or non-commercial purposes, with acknowledgement of the source and without distorting the meaning (note 4.6). Only the information published in the Official Journal of the EU is deemed authentic. The attribution line in `contracts/datasets.yaml` says so and says that NeonRadar converted the records.

## Personal data

The list names living people with their dates of birth, passport numbers and addresses, so whoever loads it is a controller under UK GDPR Article 4(7) [uk_gdpr], and a designation may be criminal offence data under Article 10 (the analysis in note 8, which is not legal advice). Robotat is the controller for the copies its staff and interns load; every other organisation that runs the loader needs its own lawful basis. The list runs only when the data steward has put `eu_fsf` into `access.sanctions_lists` in `docs/build/project.yaml` (it is there today, operator decision OD-22), on a real profile, on an approved machine, after the data protection documents are filed (the real-data gate, [real-data-handling.md](../real-data-handling.md)). Everything it writes stays under `data/cache/real/`.

## The download token and the slow server

- **Token.** The download URL carries a token. The loader reads it from `NR_EU_FSF_TOKEN` (the environment, then `.env`); when that is empty or absent it uses the public token the Commission publishes with its links (note 4.1). The Commission could revoke the public token, which is why it is configurable. The token never leaves the request: `download.json`, the manifest and the summaries store the URL without its query string, and the list client (`HttpClient(log_query=False)`) logs every URL without its query string, also in error messages.
- **Slow server.** The Commission builds the file on request (about 25 MB, over a minute) and sometimes answers with bursts of HTTP 500 (note 4.1). The client waits up to 300 seconds for a response and retries up to five times with backoff factor 3 (3, 6, 12, 24 and 48 seconds). After that the fetch of this list stops with "HTTP 500 after retries", and the other lists still run.

## How entries become records

- **Records.** Each `sanctionEntity` is one party. Subject type `person` becomes a `Person` and `enterprise` an `Organization`, with `topics: ["sanction"]`, the topic the list itself states. Any other subject type is skipped and counted. Each `regulation` of the party becomes one `Sanction`:
  - `authorityId` is the EU reference number, else the entity's logical id;
  - `unscId` is the UN reference number, normalised (the note saw it empty in every record it read, so the summary reports its fill rate);
  - `program` is the regulation's programme and `programId` its number and title;
  - `startDate` is the earlier of the designation date and the regulation's entry into force;
  - `listingDate` is the regulation's publication date and `sourceUrl` its publication URL.
- **Ids.** The party id is `eufsf-<logical id>`; a logical id outside the C1 id alphabet goes through `make_id` (`eufsf-lid-...`). `nr.source_ref` is the logical id.
- **Names.** A name marked `strong="false"` goes to `weakAlias`, which is never matched on its own. Of the strong names, the first without a language or in English becomes the name (with `firstName`, `middleName` and `lastName` from its own fields) and the rest become aliases. A party without such a name takes its first strong name in another language and is counted. A weak name never becomes the name, so a party with weak names only is skipped and counted (`no_strong_name`).
- **Birth dates.** The full date, else the year, month and day given, else every year of a range that spans at most 20 years (nothing for a wider range). With `circa="true"` only the year is kept. Values that do not parse are counted. The birth place comes from the city, else the place.
- **Countries.** Citizenship, the birth country and address countries keep the ISO code, lower-cased, only when FollowTheMoney's country type accepts it; other codes (such as `00` for unknown) are counted, never guessed.
- **Documents.** Documents marked `knownFalse="true"` are skipped and counted. Passports go to `passportNumber` and identity cards to `idNumber` (the number, else its Latin form, with spaces removed). A registration number is kept only on an organisation, only when its country is GB and it has a Companies House form, as `registrationNumber` with `jurisdiction: gb`. Every other number is counted, because a wrong number could merge a list entry into a real company (rule D1).

## What is not loaded, and why

| Field | Why |
|---|---|
| `contactInfo` (phone, fax, e-mail, website) | Not used for matching (data minimisation, note 8) |
| The entity `remark` | Off by default; only with `keep_reasons: true`, and then only in `Sanction:reason`. Remarks on names, documents and addresses are never read |
| `nameAlias@title`, `nameAlias@function` | Off by default; only with `keep_positions: true`. A title or position can reveal religious or political belief (special category data) |
| Documents marked false, document issue details, other document types | Not used for matching, or not a number NeonRadar can check |
| Citizenship of an enterprise | `Organization` has no nationality; counted |

The profile block is `eu_fsf: { enabled: true, keep_reasons: false, keep_positions: false }`; unknown keys fail.

## Checks

The build fails with exit code 4 when the number of persons or organisations is outside the range in `ingest/src/neonradar_ingest/sources/lists/bounds.yaml` (3,400 to 8,000 persons, 970 to 2,300 organisations), unless a person who has read the list's publication page passes `--accept-size`. A fill rate of zero for persons with a birth date, or for sanctions with a programme, always fails with exit code 4. The summary reports counts only: records per schema, values counted rather than loaded, fill rates (with `sanction_unsc_id`), `list_generated` and `global_file_id`.

## For developers

- `eu_fsf.make_client` is the list client with the EU settings: `log_query=False`, `retries=5`, `backoff=3.0` and a 300-second read timeout. Tests give it an `httpx.MockTransport` and a fake clock.
- The fixture `ingest/tests/fixtures/lists/eu_fsf/eu-fsf-1-1.xml` is hand-written with invented values: 99xxxx logical ids, `EU.99xxx` references, the `ZZ` regime, `SYNP` passports, `99` and `SY` company numbers, URLs on `example.invalid`, and names already checked under OD-12.

## Commands

```bash
uv run neonradar data fetch --profile uk-tiny --dataset eu_fsf
uv run neonradar ingest build --profile uk-tiny --dataset eu_fsf
```

Both refuse to run (exit code 3) until every condition of the real-data gate passes. The agent never runs them (G9).
