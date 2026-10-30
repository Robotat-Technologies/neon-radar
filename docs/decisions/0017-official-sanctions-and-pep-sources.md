# 0017. Official sources for sanctions and PEP data

- **Status:** proposed
- **Date:** 2026-10-22
- **Deciders:** @robotat-com (data steward), @robotat-com (project lead)

## Context

Phase 1 planned to take sanctions and politically exposed person (PEP) data from OpenSanctions. OpenSanctions data needs a licence for any use inside a for-profit business (PHASE-1.md M1.8d), and the operator chose to seek an evaluation agreement first, so `access.opensanctions` stays `none` (operator decision OD-19). Phase 2 still needs sanctions flags on real entities to make the ownership graph useful, and a sanctions flag on the wrong person is the most harmful error this project can make (guardrails G1 and G8, PHASE-2.md 0.5 decision 3).

The governments publish their own lists. The research note [sanctions-peps.md](../research/2026-10-18/sanctions-peps.md) (checked on 18 October 2026) found that the UK Sanctions List is published under the Open Government Licence v3.0 (section 1.8), the OFAC SDN List is in the public domain (section 2.7), the EU Financial Sanctions Files may be reused under the Commission's reuse decision (section 4.6), and the UN Security Council Consolidated List comes only with website terms that allow "personal, non-commercial use" (section 3.5). Every list names living people, so whoever loads one is a controller under UK GDPR Article 4(7), and a designation may be criminal offence data under Article 10 [uk_gdpr] (section 8, an analysis that is not legal advice). For PEPs, the UK Parliament Members API is published under the Open Parliament Licence (section 7.2).

The lists also differ in quality. The UN marks some aliases as "probably insufficient alone for a positive identification" (section 9); the UK list carries business registration numbers as free text that mixes numbers from many registers (section 1.6); one UK person can have several designations, one per regime, and the OFSI Group ID that groups them is absent for designations made since 28 January 2026 (section 1.7).

## Options considered

1. **OpenSanctions for everything.** One format, cleaned and deduplicated; but a licence is needed inside a company, and its derived parent and subsidiary entities come from free-text names (section 1.3).
2. **The official lists, loaded by NeonRadar's own loaders** (chosen). Clear reuse terms for the UK, US and EU lists, no licence fee, and full control over what is loaded; but four formats to maintain, and grouping and cleaning are NeonRadar's own work.
3. **No sanctions data until a licence arrives.** No legal or quality risk, but no sanctions flags for Phase 3 and the graph loses its main use.

## Decision

We will take sanctions data from the official lists, through loaders built in PHASE-2.md M2.6a to M2.6d:

- **Which lists.** The UK Sanctions List (`gb_fcdo_sanctions`), the OFAC SDN List (`us_ofac_sdn`) and the EU Financial Sanctions Files (`eu_fsf`) are the default (`access.sanctions_lists`, OD-22). The UN list loader (`un_sc_sanctions`) is built and tested on synthetic data, but runs only after the UN has given written permission, filed in `docs/data/licences/un_sc_sanctions.md`, and the data steward has added it to `access.sanctions_lists`. OpenSanctions is used only where `access.opensanctions` allows it (M2.7).
- **Weak aliases never match on their own.** Low quality aliases (and UK aliases without a quality that have a single word) go to `weakAlias`, from which the resolver builds no name keys (M2.10a).
- **No stubs from free-text names.** Owners, parents and subsidiaries given only as names are counted, not loaded: a name-only record would invite name-only matches and must never carry the `sanction` topic (M2.6 rule 9).
- **UK company numbers from free text only with a label and a UK register next to them** (`common.uk_company_numbers`), and LEIs only with valid check digits, because a company number feeds the deterministic rule D1: a wrong number could merge a list entry into an unrelated real company.
- **Data minimisation.** Phone numbers, e-mail addresses, websites and other information are never loaded. Statements of reasons (`keep_reasons`) and titles and positions (`keep_positions`) are off by default in every list's profile block: matching does not use them, reasons often describe alleged conduct, and a title or position can reveal religious or political belief.
- **The UK grouping rule.** UK designations form one party by OFSI Group ID, then by UN reference number (`uksl-un-<reference>`, also for a single designation), else one party per Unique ID; designations of one group that disagree on individual, entity or ship stay apart and are counted. Only parties grouped by OFSI Group ID are kept apart from other UK records by cannot-link rule X6; the others may be merged by entity resolution ([gb_fcdo_sanctions.md](../data/sources/gb_fcdo_sanctions.md)).
- **Flags only from the lists.** Party records carry `topics: ["sanction"]` because the list itself states the designation; no loader infers a flag (G8).
- **PEPs.** PEP flags come from UK Parliament data (M2.6e, optional) when `access.pep_sources` includes `gb_parliament_members`, or from OpenSanctions where `access.opensanctions` allows it, and otherwise only from synthetic data. The data steward and the project lead decide `access.pep_sources` and `access.pep_former_months` (how long a former member keeps the flag; default 12, PHASE-2.md 1.2). The operator chose `access.pep_sources: []` for now (OD-22).
- **A lawful basis per deployment.** NeonRadar ships code, not data. Each organisation that loads a list is a controller and needs its own lawful basis and, for criminal offence data, a condition and where required an appropriate policy document [uk_gdpr]. Robotat files its own documents before the first real run ([ADR-0018](0018-real-data-handling.md)).

## Consequences

- Sanctions flags no longer wait for an OpenSanctions licence; the UK, US and EU lists can load as soon as the real-data gate opens.
- NeonRadar maintains four parsers. Size bounds and fill-rate checks (`bounds.yaml`, exit code 4) catch silent format changes, and each loader's fixture is validated against the publisher's schema where one can be downloaded.
- Cross-list links are weaker than in OpenSanctions: OFAC data carries no UN reference, and the EU field for it was empty in the records read, so UK and EU entries for one listing are mostly compared by the probabilistic model (PHASE-2.md 0.5 decision 2).
- Without a PEP source, `:PEP` flags appear only in synthetic data until the data steward and project lead enable one.
- Reasons, titles and positions are unavailable to analysts unless a profile turns them on, which needs a data protection reason.

## Sources

- `docs/build/PHASE-2.md` 0.5 decisions 2 and 3, 1.2, 3.3, M2.6 and M2.6a to M2.6e, 7.1.3.
- `docs/research/2026-10-18/sanctions-peps.md` sections 1 to 4 (the lists), 6 (cross-list linking), 7 (PEP sources), 8 (data protection) and 9 (name matching guidance).
- `docs/build/operator-decisions.md` OD-19 and OD-22.
- [DATA_SOURCES.md](../../DATA_SOURCES.md) and `contracts/datasets.yaml` (C1 1.1.0) for each dataset's licence and attribution.
