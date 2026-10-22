# UK Sanctions List (`gb_fcdo_sanctions`)

The loader in `ingest/src/neonradar_ingest/sources/lists/gb_fcdo.py` (PHASE-2.md M2.6a) turns the UK Sanctions List into C1 records. This page says what the list is, under which terms it is used, how the loader groups and maps it, and what it leaves out. Licence and attribution come from [contracts/datasets.yaml](../../../contracts/datasets.yaml) and [DATA_SOURCES.md](../../../DATA_SOURCES.md); the facts about the list come from the research note [sanctions-peps.md](../../research/2026-10-18/sanctions-peps.md) section 1 (checked on 18 October 2026).

## What the list is

- **Publisher:** Foreign, Commonwealth and Development Office (FCDO), publication page <https://www.gov.uk/government/publications/the-uk-sanctions-list>.
- **Scope:** since 28 January 2026 the UK Sanctions List is the only source of UK sanctions designations; the OFSI Consolidated List has closed (note 1.1).
- **File:** one XML file at a fixed address, `https://sanctionslist.fcdo.gov.uk/docs/UK-Sanctions-List.xml`, described by the schema `SanctionsListSchema-4.33.3.xsd` (note 1.2). The schema holds no personal data and is committed next to the synthetic test fixture in `ingest/tests/fixtures/lists/gb_fcdo_sanctions/`, unchanged and with its notice (see `THIRD_PARTY_NOTICES.md`).
- **Updates:** several times a week, with no stated frequency (note 1.2). A download's version is the UTC date of the fetch; the list's own `DateGenerated` goes into the manifest notes and the build summary as `list_generated`.

## Licence and attribution

- **Licence:** [Open Government Licence v3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/), as the publication page states. Commercial use is allowed.
- **Attribution text** (written into every manifest):

  > Contains public sector information licensed under the Open Government Licence v3.0. Source: UK Sanctions List, Foreign, Commonwealth and Development Office. Converted to FollowTheMoney records by NeonRadar.

- **No endorsement:** the licence gives no right to suggest official status. NeonRadar's records are a conversion, not the list itself, and no endorsement by the FCDO is implied.

## Personal data

The Open Government Licence does not cover "personal data in the Information" (note 1.8). The list names living people with their dates of birth, passport numbers and addresses, so whoever loads it is a controller under UK GDPR Article 4(7) [uk_gdpr], and a designation may be criminal offence data under Article 10 (the analysis in note 8, which is not legal advice). Robotat is the controller for the copies its staff and interns load; every other organisation that runs the loader needs its own lawful basis. The list runs only when the data steward has put `gb_fcdo_sanctions` into `access.sanctions_lists` in `docs/build/project.yaml`, on a real profile, on an approved machine, after the data protection documents are filed (the real-data gate, [real-data-handling.md](../real-data-handling.md)). Everything it writes stays under `data/cache/real/`.

## How designations become records

One person or entity can have several designations, one Unique ID per sanctions regime, and the OFSI Group ID that groups them is absent for designations made since 28 January 2026 (note 1.7). The loader groups designations into parties in this order:

1. Designations with the same OFSI Group ID form one party: `uksl-g<OFSI Group ID>`.
2. A designation without a group id whose UN reference number is also on a grouped designation joins that group: one UN listing is one party. If two groups carry that reference, or the group is of another type, it joins neither and is counted as a group conflict.
3. The remaining designations with a UN reference number form one party per reference: `uksl-un-<reference>`, also when only one designation carries it (the id form of PHASE-2.md 4.4), so the id stays the same when the UK adds a second designation for that listing.
4. Every other designation is its own party: `uksl-<Unique ID>`.

The designations of a party are taken in Unique ID order: the first primary name of the smallest Unique ID becomes the name (with `firstName` from Name1 and `lastName` from Name6 for a person), and further primary names become aliases. A party without a primary name takes its first strong alias as the name; a weak alias never becomes the name, and a party with none is skipped and counted (`no_strong_name`). A native id outside the C1 id alphabet goes through `make_id` (`uksl-g-...`, `uksl-un-...`, `uksl-uid-...`).

Designations of one group that disagree on individual, entity or ship stay separate parties under their Unique IDs and are counted as group conflicts. A record of the last two forms may be one of several designations of one person under different regimes, so the resolver may still merge it with other UK records (cannot-link rule X6 applies only to `uksl-g` records, PHASE-2.md 7.1.3).

Each party becomes one `Person` (individuals) or `Organization` (entities) with `topics: ["sanction"]`, the topic the list itself states; each designation becomes one `Sanction` with the Unique ID as `authorityId`, the UN reference as `unscId`, the regime as `program`, the designation and last-update dates, and the sanctions imposed as `provisions`. Ships are skipped and counted. Names follow the list's own name types: primary names to `name`, spelling variations and good quality aliases to `alias`, low quality aliases to `weakAlias` (never matched on their own), and an alias without a quality to `alias` only when it has two or more words. Dates keep the precision the list gives (`dd/mm/1970` becomes `1970`). Countries go through `neonradar_keys.countries.country_code`; a value that does not map is counted, never guessed.

Business registration numbers are free text. The loader keeps a UK company number only when a company-number label and a UK register stand right next to it (for example "UK Company Number" before the number), and an LEI only when its check digits are valid; every other number is counted, not loaded, because a wrong number could merge a list entry into an unrelated real company.

## What is not loaded, and why

| Field | Why |
|---|---|
| Phone numbers, e-mail addresses, websites, other information | Data minimisation (note 8): matching does not use them |
| Crypto wallet addresses | Not a C1 schema; counted |
| Parent companies and subsidiaries | Given as names only; a name-only record would invite name-only matches and must never carry `sanction` (M2.6 rule 9); counted |
| Statements of reasons | Off by default; only with `keep_reasons: true`, and then only in `Sanction:reason`. They often describe alleged conduct |
| Titles and positions | Off by default; only with `keep_positions: true`. A title or position can reveal religious or political belief (special category data) |
| Passport and identity document additional information, type of entity, ship details | Not used for matching |

The profile block is `gb_fcdo_sanctions: { enabled: true, keep_reasons: false, keep_positions: false }`; unknown keys fail.

## Checks

The build fails with exit code 4 when the number of persons or organisations is outside the range in `ingest/src/neonradar_ingest/sources/lists/bounds.yaml` (3,000 to 7,200 persons, 900 to 3,000 organisations), unless a person who has read the publication page passes `--accept-size`. A fill rate of zero for persons with a birth date or for designations with a programme always fails with exit code 4: the format has changed or the parser is broken. The summary reports counts only: records per schema, parties of each form, group conflicts, skipped types, counts of values not loaded, fill rates and the list's `DateGenerated`.

## For developers

- `ingest/src/neonradar_ingest/sources/lists/common.py` is verbatim from PHASE-2.md M2.6a: pure functions, no I/O. Change it only through the spec.
- `shared.py` holds the builder plumbing every list loader uses: the profile block model `ListOptions`, `latest_download`, `check_size` (exit code 4), `write_records`, `list_stamp` and namespace-agnostic XML helpers.
- Parse with `defusedxml` one record element at a time and clear it; compare tags without their namespace.
- Fixtures under `ingest/tests/fixtures/lists/<slug>/` are hand-written with invented values (PHASE-2.md 2.9) and validated against the publisher's committed XSD, which `.gitattributes` keeps byte for byte.

## Commands

```bash
uv run neonradar data fetch --profile uk-tiny --dataset gb_fcdo_sanctions
uv run neonradar ingest build --profile uk-tiny --dataset gb_fcdo_sanctions
```

Both refuse to run (exit code 3) unless every condition of the real-data gate passes. The agent never runs them (G9); the operator does, and pastes the counts-only summary into the pull request.
