# 0013. Data profiles and production sources

- **Status:** proposed
- **Date:** 2026-10-22
- **Deciders:** @robotat-com (data steward, tech lead)

## Context

Phase 2 replaces the Phase 1 spikes with production loaders for Companies House, GLEIF, the ICIJ Offshore Leaks Database and the official sanctions lists (`docs/build/PHASE-2.md` 0.4). These sources hold personal data, and whoever loads them is a controller under UK GDPR [uk_gdpr] (PHASE-2.md 3.3, which summarises the analysis in `docs/research/2026-10-18/bulk-sources-loading.md` section 10; not legal advice). The project plan sets a scale target of 500,000 nodes and 2 million relationships on a 16 GB laptop, which must leave room for Phase 3's synthetic transactions (PHASE-2.md 0.5, decision 1). Without one place that decides what is loaded, every loader would invent its own folders, slices, retention and checks, and a real-data command could start on a machine or in a session where it must not.

The full register does not fit the scale target with room to spare, and the full ICIJ database alone (about 2 million nodes and 3.3 million relationships) exceeds it (PHASE-2.md 0.5, decision 9). Data minimisation points the same way: records unrelated to the slice only add possible matches between unrelated people.

## Options considered

1. **Ad hoc commands per source** (as in the Phase 1 spikes): each loader takes its own flags. Simple, but nothing ties the sources of one load together, the slice is whatever someone typed, and every loader repeats the checks.
2. **The whole register and the full leak database.** The most complete graph, but over the scale target and contrary to data minimisation.
3. **Named profiles with bounded, neutral slices, behind one gate** (chosen). Each profile is a reviewed file that lists its sources and slices; the data manager owns downloads, folders, retention, purge and the real-data gate.

## Decision

We will describe every load as a named profile in `ingest/profiles/<name>.yaml`, reviewed by the data steward: `demo` (synthetic), `uk-tiny` (a small real slice for developers) and `uk-sample` (a bounded, neutral slice of the UK register for local investigation and the published entity resolution figure). See [docs/data/profiles.md](../data/profiles.md).

- **A bounded, neutral slice instead of the whole register.** `uk-sample` takes companies registered in eight city-centre postcode districts across the UK, at most 5,000 sampled deterministically per district and 50,000 in all, plus the parent companies its ownership chains add. The districts were chosen for spread, never because their companies look unusual.
- **ICIJ tied to the same districts.** For `uk-sample` the ICIJ part is `district-linked` (M2.5): addresses in the profile's districts, their entities and officers, and one hop more, at most 50,000 nodes. `gb-linked` (every UK-linked node and its neighbours, up to 150,000) is used only when the data steward decides so in a pull request that records the reason here; `full` is for local experiments only.
- **Bulk files where they exist.** Companies House companies and the PSC snapshot, the GLEIF Golden Copy and the ICIJ CSV archive are downloaded as files, with checksums, resumption and two versions kept per dataset and product; the Companies House API is used only for officers, within a request budget, because no bulk officer file is published (PHASE-2.md 0.5, decision 5).
- **The real-data gate.** Every real-profile command checks, before any request or write: the dataset's access rule in `project.yaml`, the profile in `access.real_data_profiles`, `access.data_protection_filed`, not CI or Codespaces, and `NR_REAL_DATA_MACHINE=approved`. Real profiles load only into the separate Neo4j instance `neo4j-real` (C2 rule L17, [ADR-0018](0018-real-data-handling.md)).
- **The online Python loader** stays the only loading path; `neo4j-admin import` is not used in Phase 2, because on Community Edition it needs a stopped server and an empty database (PHASE-2.md 0.5, decision 6).
- **Counts-only summaries.** Every command that touches a real profile prints counts, timings, rates, versions and settings, never a value from a record, and writes the same summary to `data/cache/reports/<profile>/`.

## Consequences

- Loader milestones (M2.3 to M2.7) implement a `SourceSpec` and a `Builder` and get folders, downloads, retention, the gate, the summary and the record-folder swap for free.
- What a real load contains is reviewable before it runs: a slice changes only through a pull request that the data steward reviews.
- The published entity resolution figure describes `uk-sample`, not the whole register; the Phase 2 report and the precision report say so.
- Downloads are shared between real profiles, so `uk-tiny` and `uk-sample` on one machine reuse the same files.
- Purging is by scope (`neonradar data purge`), and `--all-real --graph` removes every real file and the real Neo4j volume on a machine.
- Follow-up: M2.3a to M2.7 register their sources; M2.5 records here any change from `district-linked`; M2.13 replaces the resource estimates in `docs/data/profiles.md` with measurements.

## Sources

- `docs/build/PHASE-2.md` sections 0.4, 0.5 (decisions 1, 5, 6 and 9), 3.3, 4.5, 7.4, 7.8 and M2.2.
- `docs/research/2026-10-18/bulk-sources-loading.md` (bulk files, ICIJ sizes, data protection, section 10).
- UK GDPR [uk_gdpr].
- [ADR-0006](0006-data-licensing.md) (data licensing) and [ADR-0018](0018-real-data-handling.md) (real-data handling).
