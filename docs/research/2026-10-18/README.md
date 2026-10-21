# NeonRadar research notes, 18 October 2026

These four notes are the evidence behind `docs/build/PHASE-2.md`. Research agents wrote them on 18 October 2026 by checking official sources (package registries, release tags, installed package code, publishers' pages and the legislation itself) and, where they could, by running code. Each fact carries a source tag, and the notes mark anything they could not confirm as UNVERIFIED. No note contains personal data: examples use invented values.

| Note | What it covers | Used by |
|---|---|---|
| `er-splink.md` | Splink 5.0.0 and DuckDB 1.5.6: exact signatures, verified traps, an end-to-end run with determinism checks, constraints and clustering, performance, phonetic keys, the Wilson interval and sample sizes | sections 3 and 7.1.5, M2.10b, M2.10c, 7.3 |
| `names-addresses.md` | rigour 2.5.0 and normality 3.1.0, Arabic, Cyrillic and Latin name handling with tested outputs, UK postcodes and addresses, nationality strings, the Companies House "same as" rules | M2.8, M2.9, 7.1.5 |
| `sanctions-peps.md` | The UK Sanctions List, OFAC SDN (advanced XML), UN and EU lists: downloads, formats, identifiers, licences, cross-list linking; PEP sources without OpenSanctions; data protection; the authorities' guidance on name matching | 3.3, 5.1, M2.6, 7.2 |
| `bulk-sources-loading.md` | Companies House Free Company Data and PSC snapshot, `natures_of_control` and the statutory bands, the officers API, the GLEIF Golden Copy, ICIJ, Neo4j 5.26 loading, DuckDB, data protection, statistics, corrections to Phase 1 | 3.3, 3.5, 5.1, M2.3, M2.4, M2.5, M2.11, M2.13 |

## Where the build spec decided differently

The spec wins where it differs from a note; the notes keep what was found on the day.

1. **Precision sample.** `er-splink.md` 9 recommends 400 labelled pairs per published figure. The spec plans 400 and accepts 250 as the minimum, with a stated reason in the report's first line (7.3).
2. **PEP source.** `sanctions-peps.md` 7.5 recommends loading the UK Parliament Members API in Phase 2. The spec builds it as an optional milestone (M2.6e) that does not block Gate 2, because the API gives no birth dates and PEP records will rarely reach the candidate threshold. It loads current members and ministers, and former ones only for `access.pep_former_months` after they leave (default 12, after MLR 2017 regulation 35(9)), so no one is flagged as a PEP years after leaving office.
3. **UN list.** `sanctions-peps.md` 3.5 lists three options. The spec relies on the UK and EU copies of UN listings by default, builds the loader, and runs it only after the data steward obtains written permission from the UN.
4. **Record ids for the lists.** The note suggests ids such as `nr-gb-fcdo-...`. The spec uses `uksl-`, `ofac-`, `unsc-` and `eufsf-` prefixes (4.4); they cannot collide with OpenSanctions ids, which NeonRadar re-ids with `os-`.
5. **OFAC relationships.** The note calls them direct inputs to the ownership graph. The spec loads them as `Control`, `Representation`, `Directorship`, `Membership`, `Associate`, `Family` or `UnknownLink`, never as `Ownership`, because they carry no share and the 50 Percent Rule "speaks only to ownership and not to control" (M2.6b).
6. **Bulk import.** `bulk-sources-loading.md` 8.5 proposes keeping `neo4j-admin database import` as an optional rebuild path with a CI gate at 6 minutes. The spec keeps the online loader as the only path in Phase 2 (decision 6 in 0.5) and measures it against the 10-minute target (M2.13).
7. **DuckDB for loading.** The note measured DuckDB as the fastest reader. The spec's loaders stream with Python (`csv`, `orjson`, `zipfile`) and keep their indexes in SQLite, which the measured rates make fast enough and which is simpler to test; DuckDB is used by the resolver through Splink.
8. **Phonetic keys.** `er-splink.md` 8 suggests the `Metaphone` package for Double Metaphone. The spec does not use Double Metaphone: name symbols, consonant skeletons and rigour's single Metaphone in `neonradar_keys` cover cross-spelling matches (7.1.5).
9. **Corporate PSCs.** `bulk-sources-loading.md` 3.6 gives a UK test over four fields. The spec's `identification.py` lets an explicit `country_registered` decide on its own, so a Jersey company with a London address is not treated as a UK company (M2.3b).
10. **GLEIF reporting exceptions.** The note describes the `repex` files; Phase 2 does not load them.
11. **Splink EM sampling.** The spec caps EM sessions with `max_pairs` (5 million); the note's spike ran EM without a cap on a small data set.
12. **Companies House person number.** `bulk-sources-loading.md` 5 says to treat `person_number` as "a strong but fallible blocking key for entity resolution, never as an identity". The spec keeps rule D3 on its first 8 characters but merges only when the names also agree, and ADR-0014 offers the tech lead the alternative of using it for blocking only.
13. **UK designations without an OFSI Group ID.** `sanctions-peps.md` 1.9 says to merge such designations "by entity resolution". The spec first groups them by UN reference number (`uksl-un-<ref>`), and otherwise lets the resolver merge them: the rule that keeps two entries of one list apart (X6) does not apply to them.
14. **ICIJ slice.** The spec's default for `uk-sample` is `district-linked`: only ICIJ addresses in the profile's postcode districts and the entities and officers around them, to keep the leak data in proportion to the register slice. The broader `gb-linked` selection stays available as a data steward decision (ADR-0013).
15. **Trust and firm interests.** The notes describe `-as-trust` and `-as-firm` natures of control. The spec records them as control over the trust or firm (`Control` of type `trust-or-firm`, with the band of what the trust or firm holds), not as the person's own shares, and keeps voting-rights bands on `Control` (M2.3b).

## Before you rely on a fact

These notes are a snapshot. Versions, formats, URLs, licences and guidance change. Re-check anything time-sensitive against its source before building on it, and record what changed in the pull request (PHASE-2.md 2.7). This is not legal advice: the licence and data protection sections are analysis for the data steward to decide on.
