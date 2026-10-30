# OFAC SDN List (`us_ofac_sdn`)

The loader in `ingest/src/neonradar_ingest/sources/lists/us_ofac.py` (PHASE-2.md M2.6b) turns the Specially Designated Nationals and Blocked Persons List of the US Office of Foreign Assets Control (OFAC) into C1 records. This page says what the list is, how the loader reads it and what it leaves out. Licence and attribution come from [contracts/datasets.yaml](../../../contracts/datasets.yaml) and [DATA_SOURCES.md](../../../DATA_SOURCES.md). The facts about the list come from the research note [sanctions-peps.md](../../research/2026-10-18/sanctions-peps.md), section 2 (checked on 18 October 2026).

## What the list is

- **Publisher:** US Department of the Treasury, Office of Foreign Assets Control, through its Sanctions List Service (note 2.1).
- **File:** the advanced XML, `https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ADVANCED.XML`, about 122 MB (note 2.3). It keeps name parts, weak aliases, identity documents and typed relationships between designated parties. The host answers 403 without a User-Agent; the shared list client sends one and logs URLs without their query string.
- **Updates:** frequent and irregular (note 2.2). A download's version is the UTC date of the fetch. The file's own `DateOfIssue` goes into the manifest notes and the build summary as `list_generated`.
- **Schema:** `sdn_advanced.xsd`, committed unchanged beside the test fixture in `ingest/tests/fixtures/lists/us_ofac_sdn/` (see [THIRD_PARTY_NOTICES.md](../../../THIRD_PARTY_NOTICES.md)). OFAC moved the file to a new XML namespace in 2024 (note 2.4), so the loader compares tags without their namespace; a test reads the fixture under the old namespace, the new one and none.
- **Licence:** OFAC's data catalogue marks the list files CC0 1.0 (note 2.7). Commercial use is allowed.
- **Whether it runs:** `us_ofac_sdn` is in `access.sanctions_lists` (operator decision OD-22); the real-data gate still applies to every run.

## Personal data

The list names living people with their dates of birth, identity documents and addresses, so whoever loads it is a controller under UK GDPR Article 4(7) [uk_gdpr], whatever the list's copyright status. Note 8 gives the analysis, which is not legal advice. The real-data gate applies as for every list ([real-data-handling.md](../real-data-handling.md)), and everything the loader writes stays under `data/cache/real/`.

## How the file becomes records

- **Two passes.** Every type, country and feature in the file is an id into its reference tables, and the sanctions entries and relationships come after the parties (note 2.4). Pass 1 keeps only those small tables; pass 2 reads one `DistinctParty` at a time and keeps none, so memory does not grow with the list.
- **Records.** An individual becomes a `Person` and an entity an `Organization`, with `topics: ["sanction"]`, the topic the list itself states. A subtype of "Unknown" is read through its party type. Vessels and aircraft are skipped and counted. Each sanctions entry becomes one `Sanction`: `authorityId` is the party's `FixedRef` (the SDN UID), `program` the programme tags of the entry, `provisions` its other measure types, `startDate` its earliest entry event, and `sourceUrl` OFAC's search page for the party.
- **Ids.** The party id is `ofac-<FixedRef>`; a FixedRef outside the C1 id alphabet goes through `make_id`.
- **Names.** Each documented name is built from its typed parts. The primary name in Latin script is `name`, with `firstName`, `middleName`, `fatherName`, `motherName` and `lastName`; names in other scripts and other aliases go to `alias`, former names ("F.K.A.") to `previousName`, and any low quality alias to `weakAlias`, which is never matched on its own. A maiden name gives its own alias; a nickname a weak alias. A weak alias never becomes the name, so a party without a strong name is skipped and counted (`no_strong_name`), with its relationships.
- **Dates.** A birth date keeps the precision the list gives: a day, a month, a whole year, or every year of a range of at most 20 years; an approximate date keeps its years only. A date with an impossible month is counted, not loaded.
- **Countries.** Nationalities, citizenship and address countries go through `neonradar_keys.countries.country_code`; a value that does not map is counted, never guessed. A location with only a country gives `country`, not an address.
- **Documents.** Passports and diplomatic passports go to `passportNumber`; national ID, identification and cedula numbers to `idNumber`, with spaces removed. Documents marked fraudulent are skipped and counted. On an `Organization` only, a `UK Company Number`, or another company number issued by the United Kingdom, goes to `registrationNumber` with `jurisdiction: gb` when it has a Companies House form, and an LEI to `leiCode` when its check digits are valid; on a person these are counted, never loaded, because they feed the identifier rules D1 and D2.
- **Relationships.** A link between two loaded parties becomes `Control`, `Representation`, `Directorship`, `Membership`, `Associate`, `Family` or `UnknownLink`, with the relation type as its `role` or `relationship`. None becomes `Ownership`: OFAC's relation types give no share, and OFAC's 50 Percent Rule is about entities owned 50 percent or more by blocked persons [ofac_50_percent_2014], so a control link from the list must never be read as a share. "A is owned or controlled by B" gives "B controls A". A link whose controlled or organisation end is a person and whose other end is not has its ends swapped and counted (note 2.9); between two persons it becomes `UnknownLink`. A former link has `status: former`, or " (former)" after its relationship.

## What is not loaded, and why

| Field | Why |
|---|---|
| Phone numbers, e-mail addresses, websites | Contact data, not used for matching (data minimisation, note 8) |
| Titles and every other feature type the mapping does not name | Counted by type name, never loaded: a title can reveal religious or political belief (special category data), and `keep_positions` does not change this for OFAC |
| Digital currency addresses | Not a C1 schema; counted as `CryptoWallet` |
| Vessels, aircraft | Not C1 schemata; counted |
| Other document types (tax numbers, foreign company numbers and the like) | Counted by type name; a number that is not a UK company number or an LEI could merge a list entry into the wrong company |
| Relationships to a skipped party | Counted; a link needs two loaded records |

OFAC gives no statement of reasons, so `keep_reasons` changes nothing. The profile block is `us_ofac_sdn: { enabled: true, keep_reasons: false, keep_positions: false }`; unknown keys fail.

## Checks

The build fails with exit code 4 when the number of persons or organisations is outside the range in `ingest/src/neonradar_ingest/sources/lists/bounds.yaml` (5,000 to 11,000 persons, 6,000 to 14,000 organisations), unless a person who has read the list's page passes `--accept-size`. A fill rate of zero for persons with a birth date, or for sanctions with a programme, always fails with exit code 4. The summary reports counts only: records per schema, values counted rather than loaded (type names under `*_by_value`, rare ones folded), flipped and skipped relationships, fill rates and `list_generated`.

## For developers

- The fixture `ingest/tests/fixtures/lists/us_ofac_sdn/sdn_advanced.xml` is hand-written to the committed XSD with invented values: 99xxxx party ids, `99` and `SY` company numbers, `SYN0` LEIs, `SYNP` passports, and names already checked under OD-12.
- The XSD test checks the 48 keyrefs from the schema's own declarations, because xmlschema needs about 15 seconds for their selectors; a broken reference fails it.

## Commands

```bash
uv run neonradar data fetch --profile uk-tiny --dataset us_ofac_sdn
uv run neonradar ingest build --profile uk-tiny --dataset us_ofac_sdn
```

Both refuse to run (exit code 3) until every condition of the real-data gate passes. The agent never runs them (G9).
