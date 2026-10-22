# UN Security Council Consolidated List (`un_sc_sanctions`)

The loader in `ingest/src/neonradar_ingest/sources/lists/un_sc.py` (PHASE-2.md M2.6c) turns the UN Security Council Consolidated List into C1 records. **It runs only with the UN's written permission.** This page says what the list is, why it needs permission, how the loader maps it and what it leaves out. Licence and attribution come from [contracts/datasets.yaml](../../../contracts/datasets.yaml) and [DATA_SOURCES.md](../../../DATA_SOURCES.md). The facts about the list come from the research note [sanctions-peps.md](../../research/2026-10-18/sanctions-peps.md), section 3 (checked on 18 October 2026).

## What the list is

- **Publisher:** United Nations Security Council, page <https://main.un.org/securitycouncil/en/content/un-sc-consolidated-list>.
- **File:** one XML file ordered by reference number, at `https://scsanctions.un.org/resources/xml/en/consolidated.xml` (note 3.1). That address redirects to a storage URL whose signature is valid for one hour. The loader follows the redirect but never stores or logs the signed URL: the download record and the manifest keep the address above, and the list client logs URLs without their query string.
- **Updates:** no fixed frequency (note 3.1). A download's version is the UTC date of the fetch. The file's own `dateGenerated` goes into the manifest notes and the build summary as `list_generated`.
- **Schema:** the file refers to an XSD that could not be fetched (note 3.1), so no schema is committed and the fixture is not validated against one.

## Why it needs permission

The UN website terms allow download "for the User's personal, non-commercial use", and no licence for the list itself was found (note 3.5). The loader is built and tested on synthetic data, and it runs only when both of these are true:

1. The data steward has filed the UN's written permission (asked for at sc-sanctionslists@un.org) in `docs/data/licences/un_sc_sanctions.md`. Until that file exists, `data fetch` and `ingest build` refuse with exit code 3 (rule `un_written_permission`) before any request or read.
2. `un_sc_sanctions` is in `access.sanctions_lists` in `docs/build/project.yaml`. It is not there today (operator decision OD-22).

Without permission, the UK and EU lists carry the UN listings, and the UK list gives their UN reference numbers.

## Personal data

The list names living people with their dates of birth, passport numbers and addresses, so whoever loads it is a controller under UK GDPR Article 4(7) [uk_gdpr]. Note 8 gives the analysis, which is not legal advice. The real-data gate applies as for every list ([real-data-handling.md](../real-data-handling.md)), and everything the loader writes stays under `data/cache/real/`.

## How entries become records

- **Records.** Each `INDIVIDUAL` becomes one `Person` and each `ENTITY` one `Organization`, with `topics: ["sanction"]`, the topic the list itself states. Each entry also gets one `Sanction`:
  - `authorityId` is the `DATAID`;
  - `unscId` is the reference number;
  - `program` is `UN_LIST_TYPE`;
  - `startDate` and `listingDate` are `LISTED_ON`;
  - `modifiedAt` is the latest `LAST_DAY_UPDATED`.
- **Ids.** The party id is `unsc-<reference>`, for example `unsc-ZZI.001` (normalised: upper case, no spaces, no final dot). A reference outside the C1 id alphabet goes through `make_id`.
- **Missing values.** The value `na` ("not available") counts as missing everywhere, so it never becomes a name or a country code.
- **Names.** A person's name joins the four name fields. `firstName` is the first field and `lastName` the last non-empty field after it. An entity's name is `FIRST_NAME`. The original-script name becomes an alias. An entry with no name fields takes its first strong alias as its name. A weak alias never becomes the name, so an entry without a strong alias is skipped and counted (`no_strong_name`).
- **Aliases.** A good quality alias goes to `alias` and a low quality one to `weakAlias`, which is never matched on its own: the UN calls such an alias "probably insufficient alone for a positive identification" (note 3.4). An alias without a quality goes to `alias` only when it has two or more words. Any other quality is counted and treated as weak.
- **Birth dates.** An exact date (its offset ignored), else its year. An approximate year. For a range, every year when it spans at most 20 years, and nothing for a wider range. Dates that do not parse are counted.
- **Countries.** Nationalities, the country of birth and address countries go through `neonradar_keys.countries.country_code`. Free text such as "Possibly ..." is counted, never guessed.
- **Documents.** Passports (in English, French or Spanish) go to `passportNumber` and national identification numbers to `idNumber`, with spaces removed. Every other document type is counted.

## What is not loaded, and why

| Field | Why |
|---|---|
| `COMMENTS1` | Off by default; only with `keep_reasons: true`, and then only in `Sanction:reason`. It often describes alleged conduct. Numbers in it are never read as registration numbers |
| `TITLE`, `DESIGNATION` | Off by default; only with `keep_positions: true`. A title or position can reveal religious or political belief (special category data) |
| Interpol links, notes, list type, sort keys, version numbers | Not used for matching (data minimisation, note 8) |
| Document issue details | Not used for matching |

The profile block is `un_sc_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }`; unknown keys fail.

## Checks

The build fails with exit code 4 when the number of persons or organisations is outside the range in `ingest/src/neonradar_ingest/sources/lists/bounds.yaml` (500 to 1,100 persons, 180 to 420 organisations), unless a person who has read the list's page passes `--accept-size`. A fill rate of zero for persons with a birth date, or for sanctions with a programme, always fails with exit code 4. The summary reports counts only: records per schema, values counted rather than loaded, duplicate references, unknown elements, fill rates and `list_generated`. The UN gives no registration numbers as fields, so the organisation registration rate is always zero.

## For developers

- A list URL that redirects to a signed URL or carries a token uses `shared.list_client`, whose `HttpClient(log_query=False)` keeps query strings out of every log line and error.
- `require_permission()` runs first in `discover` and in `build`; tests point `un_sc.PERMISSION_FILE` at a temporary file. Never create the real file: only the data steward files it, with the permission.
- The fixture `ingest/tests/fixtures/lists/un_sc_sanctions/consolidated.xml` is hand-written with invented values: the `ZZ` regime, 99xxxx `DATAID`s, `SYNP` passports and names already checked under OD-12.

## Commands

```bash
uv run neonradar data fetch --profile uk-tiny --dataset un_sc_sanctions
uv run neonradar ingest build --profile uk-tiny --dataset un_sc_sanctions
```

Both refuse to run (exit code 3) until the permission file exists and every condition of the real-data gate passes. The agent never runs them (G9).
